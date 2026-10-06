#include "common.hpp"

#include <cuda_fp16.h>
#include <mma.h>

#include <array>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <numeric>
#include <random>

namespace {
using namespace nvcuda;
__device__ unsigned pack_half2(__half lo, __half hi) {
    return static_cast<unsigned>(__half_as_ushort(lo)) |
           (static_cast<unsigned>(__half_as_ushort(hi)) << 16);
}
__global__ void wmma_matmul(const __half* a, const __half* b, float* c,
                            float* raw_fragment, int iterations) {
    if (threadIdx.x >= 32) return;
    const int tile = blockIdx.x;
    a += tile * 256;
    b += tile * 256;
    c += tile * 256;
    if (raw_fragment) raw_fragment += tile * 512;
    wmma::fragment<wmma::matrix_a, 16, 16, 16, __half, wmma::row_major> af;
    wmma::fragment<wmma::matrix_b, 16, 16, 16, __half, wmma::row_major> bf;
    wmma::fragment<wmma::accumulator, 16, 16, 16, float> cf;
    wmma::fill_fragment(cf, 0.0f);
    for (int r = 0; r < iterations; ++r) {
        wmma::load_matrix_sync(af, a, 16);
        wmma::load_matrix_sync(bf, b, 16);
        wmma::mma_sync(cf, af, bf, cf);
    }
    // Save the implementation's per-lane fragment slots before canonical store.
    if (raw_fragment) {
        const int lane = threadIdx.x & 31;
        for (int i = 0; i < cf.num_elements; ++i)
            raw_fragment[lane * 16 + i] = cf.x[i];
    }
    wmma::store_matrix_sync(c, cf, 16, wmma::mem_row_major);
}

// PTX ISA m8n8k4.f16 operand and accumulator layout experiment. The documented
// coordinate formulas are written alongside this kernel's raw register dump.
__global__ void ptx_mma_lane_map(const __half* a, const __half* b, float* raw,
                                 int* raw_lane, int* raw_slot) {
    const int lane = threadIdx.x & 31;
    const int arow = (lane & 3) + (lane >= 16 ? 4 : 0);
    const int bcol = (lane & 3) + (lane >= 16 ? 4 : 0);
    const unsigned a0 = pack_half2(a[arow * 4 + 0], a[arow * 4 + 1]);
    const unsigned a1 = pack_half2(a[arow * 4 + 2], a[arow * 4 + 3]);
    const unsigned b0 = pack_half2(b[0 * 8 + bcol], b[1 * 8 + bcol]);
    const unsigned b1 = pack_half2(b[2 * 8 + bcol], b[3 * 8 + bcol]);
    const int op = (lane >> 2) & 3;
    float d[8];
    #pragma unroll
    for (int i = 0; i < 8; ++i) {
        const int row = (lane & 1) + (i & 2) + (lane >= 16 ? 4 : 0);
        const int col = (i & 4) + (lane & 2) + (i & 1);
        d[i] = static_cast<float>(op * 1000 + row * 8 + col + 1);
    }
    asm volatile(
        "mma.sync.aligned.m8n8k4.row.col.f32.f16.f16.f32 "
        "{%0,%1,%2,%3,%4,%5,%6,%7}, {%8,%9}, {%10,%11}, "
        "{%0,%1,%2,%3,%4,%5,%6,%7};"
        : "+f"(d[0]), "+f"(d[1]), "+f"(d[2]), "+f"(d[3]),
          "+f"(d[4]), "+f"(d[5]), "+f"(d[6]), "+f"(d[7])
        : "r"(a0), "r"(a1), "r"(b0), "r"(b1));
    #pragma unroll
    for (int i = 0; i < 8; ++i) {
        const int row = (lane & 1) + (i & 2) + (lane >= 16 ? 4 : 0);
        const int col = (i & 4) + (lane & 2) + (i & 1);
        const int offset = op * 64 + row * 8 + col;
        raw[offset] = d[i];
        raw_lane[offset] = lane;
        raw_slot[offset] = i;
    }
}

__global__ void tensor_transform(const __half* matrix, const __half* input,
                                 float* output, int transforms, int iterations) {
    const int item = blockIdx.x;
    if (item >= transforms || threadIdx.x >= 32) return;
    wmma::fragment<wmma::matrix_a, 16, 16, 16, __half, wmma::row_major> af;
    wmma::fragment<wmma::matrix_b, 16, 16, 16, __half, wmma::row_major> bf;
    wmma::fragment<wmma::accumulator, 16, 16, 16, float> cf;
    wmma::fill_fragment(cf, 0.0f);
    for (int r = 0; r < iterations; ++r) {
        wmma::load_matrix_sync(af, matrix, 16);
        wmma::load_matrix_sync(bf, input + item * 256, 16);
        wmma::mma_sync(cf, af, bf, cf);
    }
    wmma::store_matrix_sync(output + item * 256, cf, 16, wmma::mem_row_major);
}

__global__ void butterfly_transform(const float* input, float* output,
                                    int transforms, int iterations) {
    const int tile = blockIdx.x;
    const int item = tile / 4;
    const int group = tile % 4;
    const int lane = threadIdx.x & 31;
    if (item >= transforms) return;
    const float x = lane < 4 ? input[item * 256 + (group * 4 + lane) * 16] : 0.f;
    float acc = 0.f;
    for (int it = 0; it < iterations; ++it) {
        const float partner1 = __shfl_xor_sync(0xffffffffu, x, 1);
        const float stage1 = (lane & 1) ? partner1 - x : x + partner1;
        const float partner2 = __shfl_xor_sync(0xffffffffu, stage1, 2);
        const float value = (lane & 2) ? partner2 - stage1 : stage1 + partner2;
        if (lane < 4) acc += value * 0.5f;
    }
    if (lane < 4) output[item * 256 + group * 4 + lane] = acc;
}

__global__ void bitset_pairs(const std::uint32_t* rows, std::uint32_t* out,
                             int words, int q) {
    const int pair = blockIdx.x * blockDim.x + threadIdx.x;
    if (pair >= q * q) return;
    const int a = pair / q, b = pair % q;
    std::uint32_t count = 0;
    for (int w = 0; w < words; ++w)
        count += __popc(rows[a * words + w] & rows[b * words + w]);
    out[pair] = count;
}

__global__ void dp4a_pairs(const std::uint32_t* packed, std::uint32_t* out,
                           int chunks4, int q) {
    const int pair = blockIdx.x * blockDim.x + threadIdx.x;
    if (pair >= q * q) return;
    const int a = pair / q, b = pair % q;
    int count = 0;
    for (int k = 0; k < chunks4; ++k)
        count = __dp4a(static_cast<int>(packed[a * chunks4 + k]),
                       static_cast<int>(packed[b * chunks4 + k]), count);
    out[pair] = static_cast<std::uint32_t>(count);
}

__global__ void tensor_pairs(const __half* a, const __half* b, float* out,
                             int chunks16, int iterations) {
    if (blockIdx.x || threadIdx.x >= 32) return;
    wmma::fragment<wmma::matrix_a, 16, 16, 16, __half, wmma::row_major> af;
    wmma::fragment<wmma::matrix_b, 16, 16, 16, __half, wmma::col_major> bf;
    wmma::fragment<wmma::accumulator, 16, 16, 16, float> cf;
    wmma::fill_fragment(cf, 0.0f);
    for (int it = 0; it < iterations; ++it) {
        for (int k = 0; k < chunks16; ++k) {
            wmma::load_matrix_sync(af, a + k * 16 * 16, 16);
            wmma::load_matrix_sync(bf, b + k * 16 * 16, 16);
            wmma::mma_sync(cf, af, bf, cf);
        }
    }
    wmma::store_matrix_sync(out, cf, 16, wmma::mem_row_major);
}

float half_round(float x) { return __half2float(__float2half_rn(x)); }

atlas::CaseResult base(const std::string& id, const std::string& variant,
                       const atlas::Options& o) {
    atlas::CaseResult result;
    result.experiment = id;
    result.variant = variant;
    result.configuration["device"] = std::to_string(o.device);
    result.configuration["iterations"] = std::to_string(o.iterations);
    result.configuration["size"] = std::to_string(o.size);
    result.configuration["architecture_gate"] = "sm_70_or_newer";
    return result;
}

void store_timing(atlas::CaseResult& r, const std::vector<double>& samples,
                  const char* key = "kernel_ms") {
    r.samples[key] = samples;
    std::vector<double> sorted = samples;
    std::sort(sorted.begin(), sorted.end());
    if (!sorted.empty()) {
        const std::size_t middle = sorted.size() / 2;
        r.metrics[std::string(key) + "_median"] = sorted.size() % 2
            ? sorted[middle]
            : sorted[middle - 1] + (sorted[middle] - sorted[middle - 1]) / 2.0;
        const std::size_t p95_index = static_cast<std::size_t>(std::ceil(0.95 * sorted.size())) - 1;
        r.metrics[std::string(key) + "_p95"] = sorted[p95_index];
    }
}

void gate_device(const atlas::Options& o) {
    ATLAS_CUDA(cudaSetDevice(o.device));
    cudaDeviceProp prop{};
    ATLAS_CUDA(cudaGetDeviceProperties(&prop, o.device));
    if (prop.major < 7) throw std::runtime_error("WMMA requires sm_70 or newer");
}

atlas::CaseResult run_e09_ptx(const atlas::Options& o) {
    auto r = base("E09", "ptx_m8n8k4_lane_map", o);
    std::vector<__half> a(32), b(32);
    for (int row = 0; row < 8; ++row) for (int k = 0; k < 4; ++k)
        a[row * 4 + k] = __float2half((row % 4) == k ? 1.f : 0.f);
    for (int k = 0; k < 4; ++k) for (int col = 0; col < 8; ++col)
        b[k * 8 + col] = __float2half(static_cast<float>(k * 8 + col + 1));
    atlas::DeviceBuffer<__half> da(32), db(32);
    atlas::DeviceBuffer<float> draw(256);
    atlas::DeviceBuffer<int> dlane(256), dslot(256);
    da.copy_from(a); db.copy_from(b);
    auto call = [&] { ptx_mma_lane_map<<<1, 32>>>(da.data(), db.data(), draw.data(), dlane.data(), dslot.data()); };
    call(); ATLAS_CUDA(cudaGetLastError()); ATLAS_CUDA(cudaDeviceSynchronize());
    const auto raw = draw.copy_to();
    const auto lanes = dlane.copy_to();
    const auto slots = dslot.copy_to();
    std::array<bool, 256> seen{};
    double max_error = 0.0;
    bool labels_valid = true;
    for (int lane = 0; lane < 32; ++lane) for (int slot = 0; slot < 8; ++slot) {
        const int op = (lane >> 2) & 3;
        const int row = (lane & 1) + (slot & 2) + (lane >= 16 ? 4 : 0);
        const int col = (slot & 4) + (lane & 2) + (slot & 1);
        const int index = op * 64 + row * 8 + col;
        if (index < 0 || index >= 256 || seen[index]) {
            labels_valid = false;
        } else {
            seen[index] = true;
            if (lanes[index] != lane || slots[index] != slot) labels_valid = false;
        }
    }
    for (int op = 0; op < 4; ++op) for (int row = 0; row < 8; ++row) for (int col = 0; col < 8; ++col) {
        const int index = op * 64 + row * 8 + col;
        const float expected = static_cast<float>(op * 1000 + row * 8 + col + 1 + ((row % 4) * 8 + col + 1));
        max_error = std::max(max_error, std::abs(double(raw[index]) - expected));
        if (lanes[index] < 0 || lanes[index] >= 32 || slots[index] < 0 || slots[index] >= 8) labels_valid = false;
    }
    r.metrics["max_abs_error_vs_cpu"] = max_error;
    r.metrics["documented_coordinates_covered"] = std::count(seen.begin(), seen.end(), true);
    r.configuration["ptx_form"] = "mma.sync.aligned.m8n8k4.row.col.f32.f16.f16.f32";
    r.configuration["b_fragment_layout"] = "column-major: register elements map to rows i=0..3 and column=(lane%4)+(lane>=16?4:0)";
    r.configuration["raw_outputs"] = "four PTX MMA operations; per-lane d0..d7 saved before canonicalization";
    r.configuration["coordinate_contract"] = "PTX ISA 7.0 section 9.7.13.4.1 documented accumulator mapping";
    r.configuration["oracle"] = "CPU matrix multiplication plus lane-independent unique accumulator labels";
    r.limitations.push_back("This directly tests the documented PTX form and register-coordinate formulas; it does not establish a general SASS encoding contract on other toolchains.");
    r.valid = labels_valid && max_error == 0.0 && r.metrics["documented_coordinates_covered"] == 256;
    if (!o.verify_only) store_timing(r, atlas::measure(o, call));
    return r;
}

atlas::CaseResult run_e09_wmma(const atlas::Options& o) {
    auto r = base("E09", "wmma_one_hot_lane_fragment", o);
    std::vector<__half> a(256), b(256);
    for (int row = 0; row < 16; ++row) {
        a[row * 16 + row] = __float2half(1.0f);
        for (int col = 0; col < 16; ++col)
            b[row * 16 + col] = __float2half(static_cast<float>(row * 16 + col + 1));
    }
    atlas::DeviceBuffer<__half> da(256), db(256);
    atlas::DeviceBuffer<float> dc(256), draw(512);
    da.copy_from(a); db.copy_from(b);
    draw.copy_from(std::vector<float>(512, std::numeric_limits<float>::quiet_NaN()));
    auto call = [&] { wmma_matmul<<<1, 32>>>(da.data(), db.data(), dc.data(), draw.data(), 1); };
    call(); ATLAS_CUDA(cudaGetLastError()); ATLAS_CUDA(cudaDeviceSynchronize());
    const auto actual = dc.copy_to();
    const auto raw = draw.copy_to();
    double max_error = 0.0;
    for (int i = 0; i < 256; ++i) {
        double expected = 0.0;
        for (int k = 0; k < 16; ++k) expected += double(half_round(__half2float(a[(i / 16) * 16 + k]))) * half_round(__half2float(b[k * 16 + i % 16]));
        max_error = std::max(max_error, std::abs(expected - actual[i]));
    }
    r.metrics["max_abs_error_vs_cpu"] = max_error;
    r.metrics["raw_fragment_slots_written"] = 0;
    int slots = 0;
    for (float x : raw) if (std::isfinite(x)) ++slots;
    r.metrics["raw_fragment_slots_written"] = slots;
    r.configuration["raw_fragment_layout"] = "lane-major; WMMA fragment element slots; implementation-specific";
    r.configuration["oracle"] = "double accumulation of exact FP16-converted inputs";
    r.limitations.push_back("WMMA fragment ownership is opaque API state; raw lane slots do not validate an explicit PTX fragment contract.");
    r.valid = max_error == 0.0 && slots > 0;
    if (!o.verify_only) store_timing(r, atlas::measure(o, call));
    return r;
}

atlas::CaseResult run_e10(const atlas::Options& o) {
    auto r = base("E10", "wmma_numerical_fingerprint", o);
    using Product = std::pair<float, float>;
    const std::vector<std::vector<Product>> corpus{
        {{65504.f, 1.f}, {-65504.f, 1.f}, {1.f, 0x1p-12f}},
        {{4096.f, 4096.f}, {1.f, 1.f}},
        {{1.f, 1.f}, {0x1p-12f, 0x1p-12f}},
        {{0x1p-24f, 1.f}, {0x1p-24f, 1.f}, {0x1p-24f, 1.f}, {0x1p-24f, 1.f}},
        {{-0.f, 1.f}, {0.f, 1.f}},
        {{1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f},
         {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}, {1.f, 1.f}},
        {{1.f, 1.f}, {0x1p-12f, 0x1p-12f}, {-1.f, 1.f}},
        {{-4096.f, 4096.f}, {1.f, 1.f}, {0x1p-24f, 1.f}},
        {{1.f, 1.f}, {4096.f, 4096.f}}
    };
    const std::array<const char*, 8> names{{"cancellation_order", "large_exponent_gap", "halfway_tie", "subnormal_inputs",
        "signed_zeros", "bounded_integer_count", "high_low_residual", "large_first_placement"}};
    std::vector<__half> a(8 * 256, __float2half(0.f)), b(8 * 256, __float2half(0.f));
    std::array<long double, 8> exact_reference{};
    std::array<long double, 8> abs_product_sum{};
    std::array<float, 8> serial{};
    for (int test = 0; test < 8; ++test) {
        for (std::size_t p = 0; p < corpus[test].size(); ++p) {
            const int k = (test + static_cast<int>(5 * p)) % 16;
            const __half x = __float2half(corpus[test][p].first);
            const __half y = __float2half(corpus[test][p].second);
            a[test * 256 + k] = x;
            b[test * 256 + k * 16] = y;
            const double xd = __half2float(x), yd = __half2float(y);
            exact_reference[test] += static_cast<long double>(xd) * yd;
            abs_product_sum[test] += std::abs(static_cast<long double>(xd) * yd);
        }
        // Match the kernel's repeated matrix operation order at the dot level:
        // each iteration accumulates this ordered product list into prior C.
        for (int iteration = 0; iteration < o.iterations; ++iteration)
            for (const auto& product : corpus[test]) {
                const float x = __half2float(__float2half(product.first));
                const float y = __half2float(__float2half(product.second));
                serial[test] = fmaf(x, y, serial[test]);
            }
    }
    atlas::DeviceBuffer<__half> da(a.size()), db(b.size());
    atlas::DeviceBuffer<float> dc(8 * 256);
    da.copy_from(a); db.copy_from(b);
    auto call = [&] { wmma_matmul<<<8, 32>>>(da.data(), db.data(), dc.data(), nullptr, o.iterations); };
    call(); ATLAS_CUDA(cudaGetLastError()); ATLAS_CUDA(cudaDeviceSynchronize());
    const auto actual = dc.copy_to();
    double max_abs = 0.0, max_rel = 0.0, max_serial_abs = 0.0;
    int exact_count = 0;
    bool finite = true;
    for (int test = 0; test < 8; ++test) {
        const float target = actual[test * 256];
        const long double exact_sum = exact_reference[test] * static_cast<long double>(o.iterations);
        const long double fp32_terms = 16.0L * o.iterations;
        const long double fp32_n_eps = fp32_terms * std::numeric_limits<float>::epsilon();
        const long double fp32_gamma_bound = fp32_n_eps < 1.0L
            ? (fp32_n_eps / (1.0L - fp32_n_eps)) * abs_product_sum[test] * o.iterations
            : std::numeric_limits<long double>::max();
        const float serial_sum = serial[test];
        finite = finite && std::isfinite(target);
        const double err = std::abs(static_cast<double>(exact_sum) - target);
        max_abs = std::max(max_abs, err);
        max_rel = std::max(max_rel, err / std::max(1.e-30, std::abs(static_cast<double>(exact_sum))));
        max_serial_abs = std::max(max_serial_abs, std::abs(double(target) - serial_sum));
        if (target == static_cast<float>(exact_sum)) ++exact_count;
        r.metrics[std::string("case_") + std::to_string(test) + "_actual"] = target;
        r.metrics[std::string("case_") + std::to_string(test) + "_reference"] = static_cast<double>(exact_sum);
        r.metrics[std::string("case_") + std::to_string(test) + "_placement"] = (test % 16);
        r.metrics[std::string("case_") + std::to_string(test) + "_fp32_gamma_bound"] = static_cast<double>(fp32_gamma_bound);
        r.metrics[std::string("case_") + std::to_string(test) + "_within_bound"] = err <= fp32_gamma_bound ? 1.0 : 0.0;
    }
    r.metrics["max_abs_error_vs_long_double"] = max_abs;
    r.metrics["max_relative_error_vs_long_double"] = max_rel;
    r.metrics["equal_outputs_vs_long_double_cast"] = exact_count;
    r.metrics["max_abs_delta_vs_serial_fma"] = max_serial_abs;
    r.metrics["output_count"] = 8;
    r.configuration["corpus"] = "cancellation_order, large_exponent_gap, halfway_tie, subnormal_inputs, signed_zeros, bounded_integer_count, high_low_residual, large_first_placement";
    std::string case_names;
    for (int i = 0; i < 8; ++i) { if (i) case_names += ","; case_names += names[i]; }
    r.configuration["case_names"] = case_names;
    r.configuration["reference"] = "long-double exact-input sum and explicit scalar FP32 FMA order for each distinct dot product";
    r.configuration["bound"] = "case-level diagnostic gamma16*sum(abs(products)) for FP32 accumulation; not a claimed guarantee for proprietary tensor ordering or subnormal handling";
    r.limitations.push_back("A targeted numerical fingerprint is evidence for this exact form and corpus only; it does not prove arbitrary FMA equivalence.");
    r.valid = finite;
    if (!o.verify_only) store_timing(r, atlas::measure(o, call));
    return r;
}

atlas::Cases run_e11(const atlas::Options& o, const std::string& requested) {
    const int universe = static_cast<int>(std::max<std::size_t>(16, std::min<std::size_t>(65536, o.size)));
    const int q = 16;
    const int words = (universe + 31) / 32;
    const int chunks4 = (universe + 3) / 4;
    const int chunks16 = (universe + 15) / 16;
    std::mt19937 rng(o.seed);
    std::vector<std::uint32_t> bits(q * words, 0);
    std::vector<std::uint32_t> expected(q * q, 0);
    for (int row = 0; row < q; ++row) for (int k = 0; k < universe; ++k) {
        const bool set = (rng() % 100) < 43;
        if (!set) continue;
        bits[row * words + k / 32] |= 1u << (k % 32);
    }
    auto encode_dp4a = [&] {
        std::vector<std::uint32_t> packed(q * chunks4, 0);
        for (int row = 0; row < q; ++row) for (int k = 0; k < universe; ++k)
            if ((bits[row * words + k / 32] >> (k % 32)) & 1u)
                packed[row * chunks4 + k / 4] |= 1u << ((k % 4) * 8);
        return packed;
    };
    auto encode_tensor = [&] {
        std::pair<std::vector<__half>, std::vector<__half>> encoded{
            std::vector<__half>(chunks16 * 256, __float2half(0.f)),
            std::vector<__half>(chunks16 * 256, __float2half(0.f))};
        for (int row = 0; row < q; ++row) for (int k = 0; k < universe; ++k) {
            if (!((bits[row * words + k / 32] >> (k % 32)) & 1u)) continue;
            const int ktile = k / 16, kin = k % 16;
            encoded.first[ktile * 256 + row * 16 + kin] = __float2half(1.f);
            // The WMMA fragment is loaded column-major: storage index is col*ld + k.
            encoded.second[ktile * 256 + row * 16 + kin] = __float2half(1.f);
        }
        return encoded;
    };
    double dp_encode_ms = 0.0, tensor_encode_ms = 0.0;
    const auto dp_encode_start = std::chrono::steady_clock::now();
    auto packed = encode_dp4a();
    dp_encode_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - dp_encode_start).count();
    const auto tensor_encode_start = std::chrono::steady_clock::now();
    auto tensor_encoded = encode_tensor();
    tensor_encode_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - tensor_encode_start).count();
    for (int a = 0; a < q; ++a) for (int b = 0; b < q; ++b) {
        std::uint32_t n = 0;
        for (int k = 0; k < words; ++k) n += __builtin_popcount(bits[a * words + k] & bits[b * words + k]);
        expected[a * q + b] = n;
    }

    atlas::Cases cases;
    atlas::DeviceBuffer<std::uint32_t> dbits(bits.size()), dpack(packed.size()), dcount(q * q);
    atlas::DeviceBuffer<__half> ta(tensor_encoded.first.size()), tb(tensor_encoded.second.size());
    atlas::DeviceBuffer<float> tout(256);
    double bit_transfer_ms = 0.0, dp_transfer_ms = 0.0, tensor_transfer_ms = 0.0;
    if (requested == "all" || requested == "packed_and_popc") {
        const auto start = std::chrono::steady_clock::now();
        dbits.copy_from(bits);
        bit_transfer_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
    }
    if (requested == "all" || requested == "dp4a") {
        const auto start = std::chrono::steady_clock::now();
        dpack.copy_from(packed);
        dp_transfer_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
    }
    if (requested == "all" || requested == "fp16_wmma") {
        const auto start = std::chrono::steady_clock::now();
        ta.copy_from(tensor_encoded.first); tb.copy_from(tensor_encoded.second);
        tensor_transfer_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
    }
    auto bitcall = [&] { bitset_pairs<<<(q * q + 127) / 128, 128>>>(dbits.data(), dcount.data(), words, q); };
    auto dpcall = [&] { dp4a_pairs<<<(q * q + 127) / 128, 128>>>(dpack.data(), dcount.data(), chunks4, q); };
    auto tcall = [&] { tensor_pairs<<<1, 32>>>(ta.data(), tb.data(), tout.data(), chunks16, 1); };
    auto bit_full = [&] { dbits.copy_from(bits); bitcall(); const auto values = dcount.copy_to(); (void)values; };
    auto dp_full = [&] { const auto encoded = encode_dp4a(); dpack.copy_from(encoded); dpcall(); const auto values = dcount.copy_to(); (void)values; };
    auto tensor_full = [&] {
        const auto encoded = encode_tensor();
        ta.copy_from(encoded.first); tb.copy_from(encoded.second);
        tcall(); const auto values = tout.copy_to(); (void)values;
    };
    if (requested == "all" || requested == "packed_and_popc") {
        atlas::CaseResult bit = base("E11", "packed_and_popc", o);
        bit.configuration["iterations"] = "1";
        bit.configuration["requested_iterations"] = std::to_string(o.iterations);
        bit.configuration["universe"] = std::to_string(universe);
        bit.configuration["query_count"] = "16";
        bit.metrics["representation_encoding_ms"] = 0.0;
        bit.metrics["host_to_device_ms"] = bit_transfer_ms;
        bit.configuration["complete_path_contract"] = "encode bitset from fixed query source, H2D, kernel, D2H; source generation excluded as common input setup";
        bitcall(); ATLAS_CUDA(cudaGetLastError()); ATLAS_CUDA(cudaDeviceSynchronize());
        const auto bit_copy_start = std::chrono::steady_clock::now();
        const auto bit_result = dcount.copy_to();
        const double bit_d2h_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - bit_copy_start).count();
        bit.metrics["device_to_host_ms"] = bit_d2h_ms;
        bit.valid = bit_result == expected;
        if (!o.verify_only) store_timing(bit, atlas::measure(o, bitcall));
        if (!o.verify_only) store_timing(bit, atlas::wall_measure(o, bit_full), "full_path_ms");
        cases.push_back(std::move(bit));
    }
    if (requested == "all" || requested == "dp4a") {
        atlas::CaseResult dp = base("E11", "dp4a", o);
        dp.configuration["iterations"] = "1";
        dp.configuration["requested_iterations"] = std::to_string(o.iterations);
        dp.configuration["universe"] = std::to_string(universe);
        dp.configuration["query_count"] = "16";
        dp.configuration["count_bound"] = "intersection count <= universe <= 65536 < 2^23; empirical check required";
        dp.metrics["representation_encoding_ms"] = dp_encode_ms;
        dp.metrics["host_to_device_ms"] = dp_transfer_ms;
        dp.configuration["complete_path_contract"] = "encode DP4A bytes from fixed query source, H2D, kernel, D2H; source generation excluded as common input setup";
        dpcall(); ATLAS_CUDA(cudaGetLastError()); ATLAS_CUDA(cudaDeviceSynchronize());
        const auto dp_copy_start = std::chrono::steady_clock::now();
        const auto dp_result = dcount.copy_to();
        const double dp_d2h_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - dp_copy_start).count();
        dp.metrics["device_to_host_ms"] = dp_d2h_ms;
        dp.valid = dp_result == expected;
        if (!o.verify_only) store_timing(dp, atlas::measure(o, dpcall));
        if (!o.verify_only) store_timing(dp, atlas::wall_measure(o, dp_full), "full_path_ms");
        cases.push_back(std::move(dp));
    }
    if (requested == "all" || requested == "fp16_wmma") {
        atlas::CaseResult tc = base("E11", "fp16_wmma", o);
        tc.configuration["iterations"] = "1";
        tc.configuration["requested_iterations"] = std::to_string(o.iterations);
        tc.configuration["universe"] = std::to_string(universe);
        tc.configuration["query_count"] = "16";
        tc.configuration["count_bound"] = "intersection count <= universe <= 65536 < 2^23; observed exactness only, no hardware theorem";
        tc.metrics["representation_encoding_ms"] = tensor_encode_ms;
        tc.metrics["host_to_device_ms"] = tensor_transfer_ms;
        tc.configuration["complete_path_contract"] = "encode FP16 matrices from fixed query source, H2D, WMMA kernel, D2H; source generation excluded as common input setup";
        tcall(); ATLAS_CUDA(cudaGetLastError()); ATLAS_CUDA(cudaDeviceSynchronize());
        const auto tensor_copy_start = std::chrono::steady_clock::now();
        const auto tensor_result = tout.copy_to();
        const double tensor_d2h_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - tensor_copy_start).count();
        tc.metrics["device_to_host_ms"] = tensor_d2h_ms;
        int tensor_exact = 0;
        for (int i = 0; i < 256; ++i) if (tensor_result[i] == static_cast<float>(expected[i])) ++tensor_exact;
        tc.metrics["exact_intersections"] = tensor_exact;
        tc.metrics["intersection_outputs"] = 256;
        tc.valid = tensor_exact == 256;
        tc.limitations.push_back("FP16 Tensor Core counts are empirically exact only over this tested nonnegative bounded domain; E10 is a targeted fingerprint, not a proof.");
        if (!o.verify_only) store_timing(tc, atlas::measure(o, tcall));
        if (!o.verify_only) store_timing(tc, atlas::wall_measure(o, tensor_full), "full_path_ms");
        cases.push_back(std::move(tc));
    }
    return cases;
}

atlas::CaseResult run_e12(const atlas::Options& o, const std::string& variant) {
    auto r = base("E12", variant, o);
    const int transforms = std::max(1, std::min(4096, static_cast<int>(o.size)));
    std::vector<float> matrix(256, 0.f), input(transforms * 256, 0.f);
    // Four independent normalized Hadamard transforms, padded into 16x16.
    for (int block = 0; block < 4; ++block) {
        for (int row = 0; row < 4; ++row) for (int col = 0; col < 4; ++col) {
            const int parity = __builtin_popcount(static_cast<unsigned>(row & col)) & 1;
            matrix[(block * 4 + row) * 16 + block * 4 + col] = parity ? -0.5f : 0.5f;
        }
    }
    std::mt19937 rng(o.seed);
    std::uniform_real_distribution<float> dist(-1.f, 1.f);
    for (int t = 0; t < transforms; ++t) for (int k = 0; k < 16; ++k) {
        const float x = dist(rng);
        // WMMA computes a 16x16 transform tile. Replicate the input vector into
        // every B column so each column independently contains the same vector.
        for (int col = 0; col < 16; ++col) input[t * 256 + k * 16 + col] = x;
    }
    std::vector<float> reference(transforms * 16, 0.f);
    for (int t = 0; t < transforms; ++t) for (int row = 0; row < 16; ++row)
        for (int col = 0; col < 16; ++col)
            reference[t * 16 + row] += matrix[row * 16 + col] * input[t * 256 + col * 16];
    atlas::DeviceBuffer<float> dm(256), di(input.size()), do_direct(transforms * 256);
    dm.copy_from(matrix); di.copy_from(input);
    if (variant == "shuffle_add") {
        // Warp shuffles implement a three-stage, normalized 4-point Hadamard butterfly.
        auto direct = [&] { butterfly_transform<<<transforms * 4, 32>>>(di.data(), do_direct.data(), transforms, o.iterations); };
        direct(); ATLAS_CUDA(cudaGetLastError()); ATLAS_CUDA(cudaDeviceSynchronize());
        const auto actual = do_direct.copy_to();
        double max_error = 0.0;
        for (int t = 0; t < transforms; ++t) for (int row = 0; row < 16; ++row)
            max_error = std::max(max_error, std::abs(double(actual[t * 256 + row] / o.iterations) - reference[t * 16 + row]));
        r.metrics["max_abs_error"] = max_error;
        r.configuration["normalization"] = "each 4x4 Hadamard block scaled by 1/2";
        r.configuration["padding"] = "16x16 tile; 4x4 block-diagonal transforms; zero-filled unused coefficients";
        r.valid = max_error < 2e-5;
        if (!o.verify_only) store_timing(r, atlas::measure(o, direct));
    } else if (variant == "fp16_wmma") {
        std::vector<__half> hm(256), hi(input.size());
        for (int i = 0; i < 256; ++i) hm[i] = __float2half(matrix[i]);
        for (std::size_t i = 0; i < input.size(); ++i) {
            hi[i] = __float2half(input[i]);
        }
        atlas::DeviceBuffer<__half> dhm(256), dhi(hi.size());
        atlas::DeviceBuffer<float> d_tensor(transforms * 256);
        dhm.copy_from(hm); dhi.copy_from(hi);
        auto tensor = [&] { tensor_transform<<<transforms, 32>>>(dhm.data(), dhi.data(), d_tensor.data(), transforms, o.iterations); };
        tensor(); ATLAS_CUDA(cudaGetLastError()); ATLAS_CUDA(cudaDeviceSynchronize());
        const auto actual = d_tensor.copy_to();
        double max_error = 0.0;
        for (int t = 0; t < transforms; ++t) for (int row = 0; row < 16; ++row)
            max_error = std::max(max_error, std::abs(double(actual[t * 256 + row * 16] / o.iterations) - reference[t * 16 + row]));
        r.metrics["max_abs_error"] = max_error;
        r.configuration["normalization"] = "each 4x4 Hadamard block scaled by 1/2";
        r.configuration["padding"] = "16x16 WMMA tile with zero coefficients outside 4x4 block-diagonal transform";
        r.configuration["output_extraction"] = "first column of row-major WMMA output at row*16";
        r.configuration["input_conversion"] = "FP32 to FP16; error includes conversion and output extraction";
        r.valid = max_error < 2e-3;
        if (!o.verify_only) store_timing(r, atlas::measure(o, tensor));
    } else {
        return atlas::skip("E12", variant, "supported variants are shuffle_add and fp16_wmma");
    }
    return r;
}
} // namespace

atlas::Cases run_tensor(const atlas::Options& options) {
    gate_device(options);
    const std::string variant = options.text("variant", "all");
    if (options.experiment == "E09") {
        if (variant == "all") return {run_e09_ptx(options), run_e09_wmma(options)};
        if (variant == "ptx_m8n8k4_lane_map") return {run_e09_ptx(options)};
        if (variant == "wmma_one_hot_lane_fragment") return {run_e09_wmma(options)};
        return {atlas::skip("E09", variant, "supported variants are ptx_m8n8k4_lane_map and wmma_one_hot_lane_fragment")};
    }
    if (options.experiment == "E10") {
        if (variant != "all" && variant != "wmma_numerical_fingerprint")
            return {atlas::skip("E10", variant, "supported variant is wmma_numerical_fingerprint")};
        return {run_e10(options)};
    }
    if (options.experiment == "E11") {
        if (variant != "all" && variant != "packed_and_popc" && variant != "dp4a" && variant != "fp16_wmma")
            return {atlas::skip("E11", variant, "supported variants are packed_and_popc, dp4a, and fp16_wmma")};
        return run_e11(options, variant);
    }
    if (options.experiment == "E12") {
        if (variant == "all") return {run_e12(options, "shuffle_add"), run_e12(options, "fp16_wmma")};
        return {run_e12(options, variant)};
    }
    throw std::invalid_argument("tensor module supports E09, E10, E11, and E12");
}

int main(int argc, char** argv) { return atlas::main(argc, argv, run_tensor); }
