#include "common.hpp"

#include <array>
#include <cstdint>
#include <limits>
#include <memory>
#include <random>
#include <numeric>

namespace {

constexpr unsigned kWarpWidth = 32;
constexpr unsigned kFullWarp = 0xffffffffu;

__constant__ uint8_t kNibbleAdd[512];

template <int Steps>
__global__ void native_add(uint32_t* x, const uint32_t* b, uint32_t* carry,
                           std::size_t n) {
    const std::size_t i = static_cast<std::size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i >= n) return;
    uint32_t value = x[i];
    uint32_t c = carry[i];
    const uint32_t addend = b[i];
#pragma unroll
    for (int step = 0; step < Steps; ++step) {
        const uint64_t sum = static_cast<uint64_t>(value) + addend + c;
        value = static_cast<uint32_t>(sum);
        c = static_cast<uint32_t>(sum >> 32);
    }
    x[i] = value;
    carry[i] = c;
}

// Each warp holds 32 independent scalar instances in the bits of a uint32_t
// mask. The loop over bit positions is the carry chain; each Boolean operation
// advances 32 values at once without allowing carries between instances.
__global__ void bitplane_add(uint32_t* xplanes, const uint32_t* bplanes,
                             uint32_t* carryplanes, std::size_t groups,
                             int steps) {
    const unsigned lane = threadIdx.x & (kWarpWidth - 1);
    const unsigned warp_in_block = threadIdx.x / kWarpWidth;
    const std::size_t group = static_cast<std::size_t>(blockIdx.x) *
                              (blockDim.x / kWarpWidth) + warp_in_block;
    if (group >= groups) return;

    uint32_t xplane = xplanes[group * 32 + lane];
    const uint32_t bplane = bplanes[group * 32 + lane];
    uint32_t carrymask = carryplanes[group];
    for (int step = 0; step < steps; ++step) {
        uint32_t carry = carrymask;
        for (unsigned bit = 0; bit < 32; ++bit) {
            const uint32_t xb = __shfl_sync(kFullWarp, xplane, bit);
            const uint32_t bb = __shfl_sync(kFullWarp, bplane, bit);
            const uint32_t sum = xb ^ bb ^ carry;
            carry = (xb & bb) | (xb & carry) | (bb & carry);
            if (lane == bit) xplane = sum;
        }
        carrymask = carry;
    }
    xplanes[group * 32 + lane] = xplane;
    if (lane == 0) carryplanes[group] = carrymask;
}

__global__ void encode_bitplanes(const uint32_t* x, const uint32_t* b,
                                 const uint32_t* carry, uint32_t* xplanes,
                                 uint32_t* bplanes, uint32_t* carryplanes,
                                 std::size_t n) {
    const unsigned lane = threadIdx.x & (kWarpWidth - 1);
    const unsigned warp_in_block = threadIdx.x / kWarpWidth;
    const std::size_t group = static_cast<std::size_t>(blockIdx.x) *
                              (blockDim.x / kWarpWidth) + warp_in_block;
    const std::size_t groups = (n + kWarpWidth - 1) / kWarpWidth;
    // This predicate is uniform for the warp. Entire inactive warps must exit
    // before lane 0 writes the group's bitplanes and carry mask.
    if (group >= groups) return;
    const std::size_t i = group * kWarpWidth + lane;
    const bool valid = i < n;
    const uint32_t xv = valid ? x[i] : 0u;
    const uint32_t bv = valid ? b[i] : 0u;
    const uint32_t cv = valid ? carry[i] : 0u;
    for (unsigned bit = 0; bit < 32; ++bit) {
        const uint32_t xmask = __ballot_sync(kFullWarp, (xv >> bit) & 1u);
        const uint32_t bmask = __ballot_sync(kFullWarp, (bv >> bit) & 1u);
        if (lane == 0) {
            xplanes[group * 32 + bit] = xmask;
            bplanes[group * 32 + bit] = bmask;
        }
    }
    const uint32_t cmask = __ballot_sync(kFullWarp, cv & 1u);
    if (lane == 0) carryplanes[group] = cmask;
}

__global__ void decode_bitplanes(const uint32_t* xplanes,
                                 const uint32_t* carryplanes,
                                 uint32_t* x, uint32_t* carry,
                                 std::size_t n) {
    const unsigned lane = threadIdx.x & (kWarpWidth - 1);
    const unsigned warp_in_block = threadIdx.x / kWarpWidth;
    const std::size_t group = static_cast<std::size_t>(blockIdx.x) *
                              (blockDim.x / kWarpWidth) + warp_in_block;
    const std::size_t i = group * kWarpWidth + lane;
    if (i >= n) return;
    uint32_t value = 0;
    for (unsigned bit = 0; bit < 32; ++bit) {
        const uint32_t plane = xplanes[group * 32 + bit];
        value |= ((plane >> lane) & 1u) << bit;
    }
    x[i] = value;
    carry[i] = (carryplanes[group] >> lane) & 1u;
}

__global__ void nibble_lookup_add(uint32_t* x, const uint32_t* b,
                                  uint32_t* carry, std::size_t n, int steps) {
    const std::size_t i = static_cast<std::size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i >= n) return;
    uint32_t value = x[i];
    uint32_t c = carry[i];
    const uint32_t addend = b[i];
    for (int step = 0; step < steps; ++step) {
        uint32_t next = 0;
        for (unsigned nibble = 0; nibble < 8; ++nibble) {
            const unsigned shift = nibble * 4;
            const unsigned a4 = (value >> shift) & 0xfu;
            const unsigned b4 = (addend >> shift) & 0xfu;
            const unsigned index = (a4 << 5) | (b4 << 1) | c;
            const uint8_t result = kNibbleAdd[index];
            next |= static_cast<uint32_t>(result & 0xfu) << shift;
            c = result >> 4;
        }
        value = next;
    }
    x[i] = value;
    carry[i] = c;
}

std::vector<uint32_t> make_pattern(std::size_t n, const std::string& pattern,
                                   unsigned seed, unsigned field) {
    std::vector<uint32_t> values(n);
    std::mt19937 generator(seed ^ (field * 0x9e3779b9u));
    switch (pattern.c_str()[0]) {
    default:
        if (pattern == "random") {
            for (auto& v : values) v = generator();
            break;
        }
        throw std::invalid_argument("pattern must be random, zero, ones, alternating, or carry-heavy");
    case 'z':
        if (pattern != "zero") throw std::invalid_argument("unknown data pattern: " + pattern);
        break;
    case 'o':
        if (pattern != "ones") throw std::invalid_argument("unknown data pattern: " + pattern);
        std::fill(values.begin(), values.end(), 0xffffffffu);
        break;
    case 'a':
        if (pattern != "alternating") throw std::invalid_argument("unknown data pattern: " + pattern);
        std::fill(values.begin(), values.end(), field == 0 ? 0xaaaaaaaau : 0x55555555u);
        break;
    case 'c':
        if (pattern != "carry-heavy") throw std::invalid_argument("unknown data pattern: " + pattern);
        std::fill(values.begin(), values.end(), 0xffffffffu);
        break;
    case 'r':
        if (pattern != "random") throw std::invalid_argument("unknown data pattern: " + pattern);
        for (auto& v : values) v = generator();
        break;
    }
    return values;
}

struct Inputs {
    std::vector<uint32_t> x;
    std::vector<uint32_t> b;
    std::vector<uint32_t> carry;
};

Inputs make_inputs(std::size_t n, const std::string& pattern, unsigned seed) {
    Inputs input;
    input.x = make_pattern(n, pattern, seed, 0);
    input.b = make_pattern(n, pattern, seed, 1);
    input.carry.assign(n, 0);
    if (pattern == "random") {
        std::mt19937 generator(seed ^ 0xd1b54a35u);
        for (auto& c : input.carry) c = generator() & 1u;
    } else if (pattern == "ones" || pattern == "carry-heavy") {
        std::fill(input.carry.begin(), input.carry.end(), pattern == "carry-heavy" ? 1u : 0u);
    } else if (pattern == "alternating") {
        for (std::size_t i = 0; i < n; ++i) input.carry[i] = static_cast<uint32_t>(i & 1u);
    }
    return input;
}

std::pair<uint32_t, uint32_t> cpu_transition(uint32_t x, uint32_t b,
                                             uint32_t carry, int steps) {
    for (int i = 0; i < steps; ++i) {
        const uint64_t total = static_cast<uint64_t>(x) +
                               static_cast<uint64_t>(b) + carry;
        x = static_cast<uint32_t>(total);
        carry = static_cast<uint32_t>(total >> 32);
    }
    return {x, carry};
}

std::pair<double, double> distribution(std::vector<double> samples) {
    if (samples.empty()) return {0.0, 0.0};
    std::sort(samples.begin(), samples.end());
    const std::size_t middle = samples.size() / 2;
    const double median = samples.size() % 2
        ? samples[middle]
        : (samples[middle - 1] + samples[middle]) / 2.0;
    const std::size_t p95_index = static_cast<std::size_t>(
        std::ceil(0.95 * static_cast<double>(samples.size()))) - 1;
    return {median, samples[std::min(p95_index, samples.size() - 1)]};
}

void add_measurements(atlas::CaseResult& result, const std::string& prefix,
                      const std::vector<double>& samples) {
    result.samples[prefix + "_ms"] = samples;
    const auto stats = distribution(samples);
    result.metrics[prefix + "_median_ms"] = stats.first;
    result.metrics[prefix + "_p95_ms"] = stats.second;
}

std::vector<int> reuse_sweep(const atlas::Options& options) {
    const auto require_supported = [](int value) {
        if (value != 1 && value != 8 && value != 64)
            throw std::invalid_argument("reuse must be one of 1, 8, or 64");
        return value;
    };
    const auto reuse = options.args.find("reuse");
    if (reuse != options.args.end()) return {require_supported(std::stoi(reuse->second))};
    if (options.args.find("iterations") != options.args.end()) {
        return {require_supported(options.iterations)};
    }
    return {1, 8, 64};
}

std::vector<std::string> selected_variants(const atlas::Options& options) {
    static const std::vector<std::string> all{"native", "bitplane", "nibble512"};
    const auto selected = options.args.find("variant");
    if (selected == options.args.end()) return all;
    for (const auto& value : all) if (value == selected->second) return {value};
    throw std::invalid_argument("--variant must be native, bitplane, or nibble512");
}

void initialize_lookup() {
    std::array<uint8_t, 512> table{};
    for (unsigned a = 0; a < 16; ++a) {
        for (unsigned b = 0; b < 16; ++b) {
            for (unsigned carry = 0; carry < 2; ++carry) {
                const unsigned sum = a + b + carry;
                table[(a << 5) | (b << 1) | carry] =
                    static_cast<uint8_t>((sum & 0xfu) | ((sum >> 4) << 4));
            }
        }
    }
    ATLAS_CUDA(cudaMemcpyToSymbol(kNibbleAdd, table.data(), table.size() * sizeof(uint8_t)));
}

atlas::CaseResult run_case(const atlas::Options& options, const Inputs& input,
                           const std::string& variant, int reuse,
                           double host_prepare_ms) {
    const std::size_t n = input.x.size();
    constexpr int threads = 128;
    const unsigned blocks = static_cast<unsigned>((n + threads - 1) / threads);
    const std::size_t groups = (n + kWarpWidth - 1) / kWarpWidth;
    const unsigned warp_groups_per_block = threads / kWarpWidth;
    const unsigned group_blocks = static_cast<unsigned>((groups + warp_groups_per_block - 1) /
                                                        warp_groups_per_block);

    atlas::DeviceBuffer<uint32_t> dx(n), db(n), dc(n);
    std::unique_ptr<atlas::DeviceBuffer<uint32_t>> outx, outc;
    std::unique_ptr<atlas::DeviceBuffer<uint32_t>> xplanes, bplanes, carryplanes;
    if (variant == "bitplane") {
        outx.reset(new atlas::DeviceBuffer<uint32_t>(n));
        outc.reset(new atlas::DeviceBuffer<uint32_t>(n));
        xplanes.reset(new atlas::DeviceBuffer<uint32_t>(groups * 32));
        bplanes.reset(new atlas::DeviceBuffer<uint32_t>(groups * 32));
        carryplanes.reset(new atlas::DeviceBuffer<uint32_t>(groups));
    }
    std::vector<uint32_t> host_x, host_c;

    double lookup_setup_ms = 0.0;
    if (variant == "nibble512") {
        const auto begin = std::chrono::steady_clock::now();
        initialize_lookup();
        const auto end = std::chrono::steady_clock::now();
        lookup_setup_ms = std::chrono::duration<double, std::milli>(end - begin).count();
    }

    auto h2d = [&] {
        atlas::Phase range(options.experiment + "." + variant + ".h2d");
        dx.copy_from(input.x);
        db.copy_from(input.b);
        dc.copy_from(input.carry);
    };
    auto encode = [&] {
        atlas::Phase range(options.experiment + ".bitplane.encode");
        encode_bitplanes<<<group_blocks, threads>>>(dx.data(), db.data(), dc.data(),
                                                   xplanes->data(), bplanes->data(),
                                                   carryplanes->data(), n);
        ATLAS_CUDA(cudaGetLastError());
    };
    auto compute = [&] {
        atlas::Phase range(options.experiment + "." + variant + ".compute");
        if (variant == "native") {
            if (reuse == 1) native_add<1><<<blocks, threads>>>(dx.data(), db.data(), dc.data(), n);
            else if (reuse == 8) native_add<8><<<blocks, threads>>>(dx.data(), db.data(), dc.data(), n);
            else if (reuse == 64) native_add<64><<<blocks, threads>>>(dx.data(), db.data(), dc.data(), n);
            else throw std::invalid_argument("native arithmetic supports reuse counts 1, 8, or 64");
        } else if (variant == "bitplane") {
            bitplane_add<<<group_blocks, threads>>>(xplanes->data(), bplanes->data(),
                                                    carryplanes->data(), groups, reuse);
        } else {
            nibble_lookup_add<<<blocks, threads>>>(dx.data(), db.data(), dc.data(), n, reuse);
        }
        ATLAS_CUDA(cudaGetLastError());
    };
    auto decode = [&] {
        atlas::Phase range(options.experiment + ".bitplane.decode");
        decode_bitplanes<<<group_blocks, threads>>>(xplanes->data(), carryplanes->data(),
                                                    outx->data(), outc->data(), n);
        ATLAS_CUDA(cudaGetLastError());
    };
    auto d2h = [&] {
        atlas::Phase range(options.experiment + "." + variant + ".d2h_materialize");
        if (variant == "bitplane") {
            host_x = outx->copy_to();
            host_c = outc->copy_to();
        } else {
            host_x = dx.copy_to();
            host_c = dc.copy_to();
        }
    };

    // The correctness gate is independent of timing and validates every output
    // element, including groups with fewer than 32 valid lanes.
    h2d();
    if (variant == "bitplane") encode();
    ATLAS_CUDA(cudaGetLastError());
    compute();
    ATLAS_CUDA(cudaGetLastError());
    if (variant == "bitplane") decode();
    ATLAS_CUDA(cudaDeviceSynchronize());
    d2h();
    bool valid = true;
    for (std::size_t i = 0; i < n; ++i) {
        const auto expected = cpu_transition(input.x[i], input.b[i], input.carry[i], reuse);
        valid = valid && host_x[i] == expected.first && host_c[i] == expected.second;
    }

    // Reinitialize resident state before collecting separate phase samples.
    h2d();
    if (variant == "bitplane") {
        encode();
        ATLAS_CUDA(cudaGetLastError());
        ATLAS_CUDA(cudaDeviceSynchronize());
    }
    const std::vector<double> compute_samples = atlas::measure(options, compute);

    std::vector<double> encode_samples;
    std::vector<double> decode_samples;
    if (variant == "bitplane") {
        encode_samples = atlas::measure(options, encode);
        decode_samples = atlas::measure(options, decode);
    }

    const std::vector<double> h2d_samples = atlas::wall_measure(options, h2d);
    if (variant == "bitplane") {
        const std::vector<double> d2h_samples = atlas::wall_measure(options, [&] {
            decode();
            d2h();
        });
        atlas::CaseResult result;
        result.experiment = options.experiment;
        result.variant = variant;
        result.valid = valid;
        result.configuration = {{"size", std::to_string(n)}, {"reuse", std::to_string(reuse)},
                                {"pattern", options.text("pattern", "random")},
                                {"seed", std::to_string(options.seed)},
                                {"representation", "32 scalar instances per bitplane word"},
                                {"partial_group", std::to_string(n % 32)}};
        result.metrics["host_prepare_ms"] = host_prepare_ms;
        result.metrics["correctness_checked_values"] = static_cast<double>(n);
        result.configuration["numerical_contract"] = "u64(x)+u64(b)+carry; low32 becomes x and high32 becomes carry after each transition";
        result.configuration["state_contract"] = "initial x,b,carry transferred to device; final x,carry materialized on host; b is immutable";
        result.configuration["workspace_allocation"] = "device workspaces allocated before timed paths; allocation time excluded";
        result.metrics["host_input_bytes"] = static_cast<double>(3 * n * sizeof(uint32_t));
        result.metrics["host_output_bytes"] = static_cast<double>(2 * n * sizeof(uint32_t));
        result.metrics["device_workspace_bytes_estimate"] = static_cast<double>(
            3 * n * sizeof(uint32_t) + 2 * n * sizeof(uint32_t) +
            2 * groups * 32 * sizeof(uint32_t) + groups * sizeof(uint32_t));
        add_measurements(result, "encode_kernel", encode_samples);
        add_measurements(result, "resident_compute", compute_samples);
        add_measurements(result, "decode_and_materialize", d2h_samples);
        add_measurements(result, "h2d", h2d_samples);
        result.samples["decode_kernel_ms"] = decode_samples;
        const auto decode_stats = distribution(decode_samples);
        result.metrics["decode_kernel_median_ms"] = decode_stats.first;
        result.metrics["decode_kernel_p95_ms"] = decode_stats.second;
        const std::vector<double> full_samples = atlas::wall_measure(options, [&] {
            atlas::Phase path(options.experiment + ".bitplane.full_path");
            h2d();
            encode();
            compute();
            decode();
            ATLAS_CUDA(cudaStreamSynchronize(nullptr));
            d2h();
        });
        add_measurements(result, "full_path", full_samples);
        result.limitations.push_back("Energy is not measured in this kernel module; treat it as unknown below the platform sensor resolution.");
        result.limitations.push_back("Device workspace allocation is outside timed paths; allocation cost is not amortized or compared here.");
        return result;
    }

    const std::vector<double> d2h_samples = atlas::wall_measure(options, [&] {
        d2h();
    });
    atlas::CaseResult result;
    result.experiment = options.experiment;
    result.variant = variant;
    result.valid = valid;
    result.configuration = {{"size", std::to_string(n)}, {"reuse", std::to_string(reuse)},
                            {"pattern", options.text("pattern", "random")},
                            {"seed", std::to_string(options.seed)},
                            {"partial_group", std::to_string(n % 32)}};
    result.metrics["host_prepare_ms"] = host_prepare_ms;
    if (variant == "nibble512") result.metrics["lookup_table_setup_wall_ms"] = lookup_setup_ms;
    result.metrics["correctness_checked_values"] = static_cast<double>(n);
    result.configuration["numerical_contract"] = "u64(x)+u64(b)+carry; low32 becomes x and high32 becomes carry after each transition";
    result.configuration["state_contract"] = "initial x,b,carry transferred to device; final x,carry materialized on host; b is immutable";
    result.configuration["workspace_allocation"] = "device workspaces allocated before timed paths; allocation time excluded";
    if (variant == "nibble512") result.configuration["lookup_table_entries"] = "512 (constant memory; static operator table)";
    result.metrics["host_input_bytes"] = static_cast<double>(3 * n * sizeof(uint32_t));
    result.metrics["host_output_bytes"] = static_cast<double>(2 * n * sizeof(uint32_t));
    result.metrics["device_workspace_bytes_estimate"] = static_cast<double>(3 * n * sizeof(uint32_t));
    add_measurements(result, "resident_compute", compute_samples);
    add_measurements(result, "h2d", h2d_samples);
    add_measurements(result, "d2h_and_materialize", d2h_samples);
    const std::vector<double> full_samples = atlas::wall_measure(options, [&] {
        atlas::Phase path(options.experiment + "." + variant + ".full_path");
        h2d();
        compute();
        ATLAS_CUDA(cudaStreamSynchronize(nullptr));
        d2h();
    });
    add_measurements(result, "full_path", full_samples);
    result.limitations.push_back("Energy is not measured in this kernel module; treat it as unknown below the platform sensor resolution.");
    result.limitations.push_back("Device workspace allocation is outside timed paths; allocation cost is not amortized or compared here.");
    if (variant == "nibble512") result.limitations.push_back("The fixed 512-entry operator table is uploaded before timed paths and reused; one-time table setup is excluded from full_path_ms.");
    return result;
}

} // namespace

atlas::Cases run_composition(const atlas::Options& options) {
    if (options.experiment != "E13" && options.experiment != "E39")
        throw std::invalid_argument("composition supports E13 and E39");
    ATLAS_CUDA(cudaSetDevice(options.device));
    const std::string pattern = options.text("pattern", "random");
    const auto prep_start = std::chrono::steady_clock::now();
    const Inputs input = make_inputs(options.size, pattern, options.seed);
    const auto prep_end = std::chrono::steady_clock::now();
    const double host_prepare_ms = std::chrono::duration<double, std::milli>(
        prep_end - prep_start).count();

    atlas::Cases results;
    for (const std::string& variant : selected_variants(options)) {
        for (const int reuse : reuse_sweep(options)) {
            results.push_back(run_case(options, input, variant, reuse, host_prepare_ms));
        }
    }
    return results;
}

int main(int argc, char** argv) {
    return atlas::main(argc, argv, run_composition);
}
