#include "common.hpp"

#include <cuda.h>

#include <algorithm>
#include <cstdint>
#include <limits>
#include <numeric>
#include <random>
#include <sstream>

namespace {

bool selected(const atlas::Options& o, const std::string& variant) {
    const auto requested = o.text("variant", "all");
    return requested == "all" || requested == variant;
}

void summarize(atlas::CaseResult& r, const std::vector<double>& ms) {
    if (ms.empty()) return;
    r.samples["device_ms"] = ms;
    auto sorted = ms;
    std::sort(sorted.begin(), sorted.end());
    const std::size_t middle = sorted.size() / 2;
    r.metrics["median_ms"] = sorted.size() % 2
        ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) * 0.5;
    const auto p95 = static_cast<std::size_t>(std::ceil(0.95 * sorted.size())) - 1;
    r.metrics["p95_ms"] = sorted[std::min(p95, sorted.size() - 1)];
}

atlas::CaseResult measured(const atlas::Options& o, const std::string& e,
                           const std::string& v, const std::vector<double>& ms) {
    atlas::CaseResult r;
    r.experiment = e;
    r.variant = v;
    summarize(r, ms);
    r.configuration["device"] = std::to_string(o.device);
    r.configuration["warmup"] = std::to_string(o.verify_only ? 0 : o.warmup);
    r.configuration["repeats"] = std::to_string(o.verify_only ? 1 : o.repeats);
    return r;
}

__global__ void stream_load(const uint32_t* input, uint64_t n, uint64_t stride,
                            uint64_t passes, uint64_t* output) {
    const uint64_t tid = static_cast<uint64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const uint64_t step = static_cast<uint64_t>(gridDim.x) * blockDim.x;
    uint64_t sum = 0;
    for (uint64_t i = tid; i < n; i += step)
        for (uint64_t p = 0; p < passes; ++p) sum += input[i * stride];
    if (tid < step) output[tid] = sum;
}

__global__ void pointer_chase(const uint32_t* next, uint32_t start,
                              uint64_t steps, uint32_t* output) {
    if (blockIdx.x == 0 && threadIdx.x == 0) {
        uint32_t cursor = start;
        for (uint64_t i = 0; i < steps; ++i) cursor = next[cursor];
        output[0] = cursor;
    }
}

__global__ void displace_cache(uint32_t* scratch, uint64_t n) {
    const uint64_t tid = static_cast<uint64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const uint64_t step = static_cast<uint64_t>(gridDim.x) * blockDim.x;
    for (uint64_t i = tid; i < n; i += step) scratch[i] = scratch[i] + 1u;
}

__global__ void footprint_walk(const uint32_t* input, uint32_t pages,
                               uint32_t words_per_page, uint32_t accesses,
                               uint32_t order_stride, uint64_t* output) {
    if (blockIdx.x == 0 && threadIdx.x == 0) {
        uint64_t sum = 0;
        for (uint32_t i = 0; i < accesses; ++i) {
            const uint32_t page = (i * order_stride) % pages;
            sum += input[static_cast<uint64_t>(page) * words_per_page];
        }
        output[0] = sum;
    }
}

__global__ void fill_values(uint32_t* p, uint64_t n) {
    const uint64_t tid = static_cast<uint64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const uint64_t step = static_cast<uint64_t>(gridDim.x) * blockDim.x;
    for (uint64_t i = tid; i < n; i += step) p[i] = static_cast<uint32_t>(i + 1);
}

__global__ void alias_walk(const uint32_t* aliased, uint64_t n, uint64_t accesses,
                           uint64_t* output) {
    if (blockIdx.x == 0 && threadIdx.x == 0) {
        uint64_t sum = 0;
        const uint64_t window = 2 * n;
        for (uint64_t begin = 0; begin < accesses; begin += window) {
            const uint64_t count = min(window, accesses - begin);
            for (uint64_t offset = 0; offset < count; ++offset) sum += aliased[offset];
        }
        output[0] = sum;
    }
}

__global__ void ring_walk(const uint32_t* values, uint64_t n, uint64_t accesses,
                          uint64_t* output) {
    if (blockIdx.x == 0 && threadIdx.x == 0) {
        uint64_t sum = 0;
        for (uint64_t i = 0; i < accesses; ++i) sum += values[i % n];
        output[0] = sum;
    }
}

__global__ void reduce_u32(const uint32_t* input, uint64_t n, uint64_t* output) {
    if (blockIdx.x == 0 && threadIdx.x == 0) {
        uint64_t sum = 0;
        for (uint64_t i = 0; i < n; ++i) sum += input[i];
        output[0] = sum;
    }
}

__global__ void evaluate_sinf(const float* x, float* y, uint64_t n, bool intrinsic) {
    const uint64_t i = static_cast<uint64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i < n) y[i] = intrinsic ? __sinf(x[i]) : sinf(x[i]);
}

__global__ void evaluate_lut(const float* x, float* y, uint64_t n,
                             const float* table, uint32_t table_size) {
    const uint64_t i = static_cast<uint64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i < n) {
        constexpr float pi = 3.14159265358979323846f;
        const float position = (x[i] + pi) * (static_cast<float>(table_size - 1) / (2.0f * pi));
        const uint32_t lo = min(static_cast<uint32_t>(fmaxf(position, 0.0f)), table_size - 1);
        const uint32_t hi = min(lo + 1, table_size - 1);
        const float fraction = fminf(fmaxf(position - lo, 0.0f), 1.0f);
        y[i] = table[lo] + fraction * (table[hi] - table[lo]);
    }
}

__global__ void evaluate_texture(const float* x, float* y, uint64_t n,
                                 cudaTextureObject_t texture, uint32_t table_size) {
    const uint64_t i = static_cast<uint64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i < n) {
        constexpr float pi = 3.14159265358979323846f;
        const float domain_fraction = (x[i] + pi) / (2.0f * pi);
        // Place the normalized coordinate at texel centers so the sampled
        // interval matches the manually interpolated table endpoints.
        const float coordinate = (0.5f + domain_fraction * (table_size - 1)) / table_size;
        y[i] = tex1D<float>(texture, coordinate);
    }
}

std::vector<double> measure_after_displacement(const atlas::Options& o,
                                                uint32_t* scratch,
                                                uint64_t scratch_words,
                                                const uint32_t* next,
                                                uint64_t steps,
                                                uint32_t* output) {
    const int warmups = o.verify_only ? 0 : std::max(0, o.warmup);
    const int repeats = o.verify_only ? 1 : std::max(1, o.repeats);
    const unsigned blocks = static_cast<unsigned>(std::min<uint64_t>(4096, (scratch_words + 255) / 256));
    auto displace = [&] { displace_cache<<<blocks, 256>>>(scratch, scratch_words); };
    for (int i = 0; i < warmups; ++i) {
        displace();
        pointer_chase<<<1, 1>>>(next, 0, steps, output);
        ATLAS_CUDA(cudaGetLastError());
        ATLAS_CUDA(cudaDeviceSynchronize());
    }
    cudaEvent_t start = nullptr, stop = nullptr;
    ATLAS_CUDA(cudaEventCreate(&start));
    try {
        ATLAS_CUDA(cudaEventCreate(&stop));
        std::vector<double> elapsed;
        elapsed.reserve(static_cast<std::size_t>(repeats));
        for (int i = 0; i < repeats; ++i) {
            displace();
            ATLAS_CUDA(cudaGetLastError());
            ATLAS_CUDA(cudaEventRecord(start));
            pointer_chase<<<1, 1>>>(next, 0, steps, output);
            ATLAS_CUDA(cudaGetLastError());
            ATLAS_CUDA(cudaEventRecord(stop));
            ATLAS_CUDA(cudaEventSynchronize(stop));
            float milliseconds = 0.0f;
            ATLAS_CUDA(cudaEventElapsedTime(&milliseconds, start, stop));
            elapsed.push_back(milliseconds);
        }
        cudaEventDestroy(stop);
        cudaEventDestroy(start);
        return elapsed;
    } catch (...) {
        if (stop) cudaEventDestroy(stop);
        if (start) cudaEventDestroy(start);
        throw;
    }
}

template <class Prepare, class Callable>
std::vector<double> wall_measure_prepared(const atlas::Options& o,
                                          Prepare&& prepare,
                                          Callable&& callable,
                                          cudaStream_t stream = nullptr) {
    const int warmups = o.verify_only ? 0 : std::max(0, o.warmup);
    const int repeats = o.verify_only ? 1 : std::max(1, o.repeats);
    for (int i = 0; i < warmups; ++i) {
        prepare();
        callable();
        ATLAS_CUDA(cudaStreamSynchronize(stream));
    }
    std::vector<double> elapsed;
    elapsed.reserve(static_cast<std::size_t>(repeats));
    for (int i = 0; i < repeats; ++i) {
        ATLAS_CUDA(cudaStreamSynchronize(stream));
        prepare();
        ATLAS_CUDA(cudaStreamSynchronize(stream));
        const auto begin = std::chrono::steady_clock::now();
        callable();
        ATLAS_CUDA(cudaStreamSynchronize(stream));
        const auto end = std::chrono::steady_clock::now();
        elapsed.push_back(std::chrono::duration<double, std::milli>(end - begin).count());
    }
    return elapsed;
}

struct DriverMemory {
    CUdeviceptr address = 0;
    size_t bytes = 0;
    CUmemGenericAllocationHandle allocation = 0;
    bool created = false;
    std::vector<CUdeviceptr> mappings;

    ~DriverMemory() {
        for (auto it = mappings.rbegin(); it != mappings.rend(); ++it) cuMemUnmap(*it, bytes);
        if (created) cuMemRelease(allocation);
        if (address) cuMemAddressFree(address, bytes * 2);
    }
};

std::string driver_error(CUresult result) {
    const char* name = nullptr;
    const char* description = nullptr;
    cuGetErrorName(result, &name);
    cuGetErrorString(result, &description);
    std::ostringstream out;
    out << (name ? name : "unknown") << ": " << (description ? description : "no detail");
    return out.str();
}

CUresult map_vmm(CUdevice device, size_t bytes, DriverMemory& region) {
    CUmemAllocationProp prop{};
    prop.type = CU_MEM_ALLOCATION_TYPE_PINNED;
    prop.location.type = CU_MEM_LOCATION_TYPE_DEVICE;
    prop.location.id = device;
    size_t granularity = 0;
    CUresult status = cuMemGetAllocationGranularity(&granularity, &prop,
                                                   CU_MEM_ALLOC_GRANULARITY_MINIMUM);
    if (status != CUDA_SUCCESS) return status;
    region.bytes = ((bytes + granularity - 1) / granularity) * granularity;
    status = cuMemAddressReserve(&region.address, region.bytes * 2, granularity, 0, 0);
    if (status != CUDA_SUCCESS) return status;
    status = cuMemCreate(&region.allocation, region.bytes, &prop, 0);
    if (status != CUDA_SUCCESS) return status;
    region.created = true;
    for (int alias = 0; alias < 2; ++alias) {
        const CUdeviceptr address = region.address + static_cast<CUdeviceptr>(alias) * region.bytes;
        status = cuMemMap(address, region.bytes, 0, region.allocation, 0);
        if (status != CUDA_SUCCESS) return status;
        region.mappings.push_back(address);
        CUmemAccessDesc access{};
        access.location.type = CU_MEM_LOCATION_TYPE_DEVICE;
        access.location.id = device;
        access.flags = CU_MEM_ACCESS_FLAGS_PROT_READWRITE;
        status = cuMemSetAccess(address, region.bytes, &access, 1);
        if (status != CUDA_SUCCESS) return status;
    }
    return CUDA_SUCCESS;
}

} // namespace

atlas::Cases run_memory(const atlas::Options& o) {
    atlas::Cases cases;
    ATLAS_CUDA(cudaSetDevice(o.device));

    if (o.experiment == "E07") {
        const uint64_t n = std::max<uint64_t>(4096, std::min<uint64_t>(o.size, 1u << 22));
        const uint64_t passes = static_cast<uint64_t>(o.iterations);
        constexpr uint32_t blocks = 256;
        atlas::DeviceBuffer<uint64_t> sums(static_cast<uint64_t>(blocks) * 256);
        for (const auto& pattern : std::vector<std::pair<std::string, uint32_t>>{{"stream_contiguous", 1}, {"stream_scattered", 16}}) {
            if (!selected(o, pattern.first)) continue;
            const uint64_t stride = pattern.second;
            std::vector<uint32_t> host(static_cast<size_t>(n * stride));
            for (uint64_t i = 0; i < n; ++i) host[static_cast<size_t>(i * stride)] = static_cast<uint32_t>(i * 3 + 1);
            atlas::DeviceBuffer<uint32_t> input(host.size());
            input.copy_from(host);
            const auto timing = atlas::measure(o, [&] {
                stream_load<<<blocks, 256>>>(input.data(), n, stride, passes, sums.data());
            });
            const auto observed = sums.copy_to();
            uint64_t actual = 0;
            for (uint64_t x : observed) actual += x;
            uint64_t expected = 0;
            for (uint64_t i = 0; i < n; ++i) expected += static_cast<uint64_t>(host[static_cast<size_t>(i * stride)]) * passes;
            auto result = measured(o, "E07", pattern.first, timing);
            result.valid = (actual == expected);
            result.configuration["useful_loads_per_pass"] = std::to_string(n);
            result.configuration["stride_elements"] = std::to_string(stride);
            result.configuration["passes"] = std::to_string(passes);
            result.metrics["useful_bytes_per_pass"] = static_cast<double>(n * sizeof(uint32_t));
            result.metrics["bytes_addressed_per_pass"] = static_cast<double>(n * stride * sizeof(uint32_t));
            result.metrics["checksum"] = static_cast<double>(actual);
            result.limitations.push_back("A stride or timing plateau does not identify a cache level or physical transaction mapping.");
            cases.push_back(std::move(result));
        }

        for (const auto& variant : std::vector<std::pair<std::string, uint32_t>>{{"chase_warm", 1}, {"chase_scattered", 17}, {"chase_cold_displaced", 17}}) {
            if (!selected(o, variant.first)) continue;
            uint32_t step = variant.second;
            while (std::gcd(step, static_cast<uint32_t>(n)) != 1) ++step;
            std::vector<uint32_t> next(static_cast<size_t>(n));
            for (uint64_t i = 0; i < n; ++i) next[static_cast<size_t>(i)] = static_cast<uint32_t>((i + step) % n);
            atlas::DeviceBuffer<uint32_t> dnext(n), output(1);
            dnext.copy_from(next);
            const uint64_t steps = std::max<uint64_t>(256, std::min<uint64_t>(static_cast<uint64_t>(o.iterations) * 4096, 1ull << 28));
            std::vector<double> timing;
            int l2_bytes = 0;
            if (variant.first == "chase_cold_displaced") {
                const cudaError_t query = cudaDeviceGetAttribute(&l2_bytes, cudaDevAttrL2CacheSize, o.device);
                if (query != cudaSuccess || l2_bytes <= 0) {
                    cases.push_back(atlas::skip("E07", variant.first, std::string("L2 size query required for bounded cache displacement failed: ") + cudaGetErrorString(query)));
                    continue;
                }
                const uint64_t scratch_words = std::max<uint64_t>(n, std::min<uint64_t>((2ull * static_cast<uint64_t>(l2_bytes) + 3) / 4, 1ull << 26));
                atlas::DeviceBuffer<uint32_t> scratch(scratch_words);
                ATLAS_CUDA(cudaMemset(scratch.data(), 0, scratch_words * sizeof(uint32_t)));
                timing = measure_after_displacement(o, scratch.data(), scratch_words, dnext.data(), steps, output.data());
            } else {
                timing = atlas::measure(o, [&] { pointer_chase<<<1, 1>>>(dnext.data(), 0, steps, output.data()); });
            }
            const uint32_t actual = output.copy_to()[0];
            const uint32_t expected = static_cast<uint32_t>((static_cast<uint64_t>(steps % n) * step) % n);
            auto result = measured(o, "E07", variant.first, timing);
            result.valid = actual == expected;
            result.configuration["nodes"] = std::to_string(n);
            result.configuration["dependent_loads"] = std::to_string(steps);
            result.configuration["cycle_step"] = std::to_string(step);
            if (variant.first == "chase_cold_displaced") {
                result.configuration["reported_l2_bytes"] = std::to_string(l2_bytes);
                result.configuration["cache_displacement"] = "separate scratch traversal larger than reported L2; pointer chase interval excludes displacement";
            }
            result.metrics["ns_per_dependent_load"] = result.metrics["median_ms"] * 1.0e6 / steps;
            result.metrics["final_node"] = actual;
            if (variant.first == "chase_cold_displaced")
                result.limitations.push_back("Scratch traversal is a cache-displacement control, not a guarantee that every pointer node is cold or a measurement of a specific cache level.");
            else
                result.limitations.push_back("The warm chain remains in a changing cache state; its timing is not a fixed cache-hit latency measurement.");
            result.limitations.push_back("Allocation-dependent timing cannot establish physical cache or HBM address bits.");
            cases.push_back(std::move(result));
        }
        return cases;
    }

    if (o.experiment == "E08") {
        constexpr uint32_t words_per_page = 1024; // 4 KiB VA spacing; not a claim about hardware translation granularity.
        const uint32_t accesses = static_cast<uint32_t>(std::max<uint64_t>(1024, std::min<uint64_t>(o.size, 1u << 20)));
        const uint64_t pass_count = static_cast<uint64_t>(o.iterations);
        for (uint32_t pages : {1u, 4u, 16u, 64u, 256u}) {
            const std::string variant = "footprint_" + std::to_string(pages) + "p";
            if (!selected(o, variant)) continue;
            const uint64_t count = static_cast<uint64_t>(pages) * words_per_page;
            std::vector<uint32_t> host(static_cast<size_t>(count), 1u);
            for (uint32_t p = 0; p < pages; ++p) host[static_cast<size_t>(p) * words_per_page] = p + 1;
            atlas::DeviceBuffer<uint32_t> input(count);
            atlas::DeviceBuffer<uint64_t> output(1);
            input.copy_from(host);
            const uint32_t stride = (pages > 1 && std::gcd(17u, pages) == 1) ? 17u : 1u;
            const auto timing = atlas::measure(o, [&] {
                for (uint64_t pass = 0; pass < pass_count; ++pass)
                    footprint_walk<<<1, 1>>>(input.data(), pages, words_per_page, accesses, stride, output.data());
            });
            const uint64_t actual = output.copy_to()[0];
            uint64_t expected = 0;
            for (uint32_t i = 0; i < accesses; ++i) expected += ((i * stride) % pages) + 1;
            auto result = measured(o, "E08", variant, timing);
            result.valid = actual == expected;
            result.configuration["virtual_page_spacing_bytes"] = "4096";
            result.configuration["footprint_pages"] = std::to_string(pages);
            result.configuration["useful_loads_per_pass"] = std::to_string(accesses);
            result.configuration["pass_count"] = std::to_string(pass_count);
            result.configuration["traversal"] = (stride == 1 ? "page_local_order" : "strided_page_order");
            result.metrics["useful_bytes_per_pass"] = static_cast<double>(accesses * sizeof(uint32_t));
            result.metrics["checksum"] = static_cast<double>(actual);
            result.limitations.push_back("The 4 KiB spacing is a virtual-address test stride, not a query or claim about V100 TLB page size.");
            result.limitations.push_back("This single-allocation sweep cannot isolate translation effects from cache, page allocation, or address hashing.");
            cases.push_back(std::move(result));
        }
        return cases;
    }

    if (o.experiment == "E23") {
        const std::string ring_variant = "ring_modulo_baseline";
        const std::string alias_variant = "vmm_fixed_alias_window";
        const bool want_ring = selected(o, ring_variant);
        const bool want_alias = selected(o, alias_variant);
        const uint64_t requested_n = std::max<uint64_t>(1024, std::min<uint64_t>(o.size, 1u << 20));
        CUresult vmm_query = cuInit(0);
        CUdevice device{};
        if (vmm_query == CUDA_SUCCESS) vmm_query = cuDeviceGet(&device, o.device);
        int vmm_support = 0;
        if (vmm_query == CUDA_SUCCESS)
            vmm_query = cuDeviceGetAttribute(&vmm_support, CU_DEVICE_ATTRIBUTE_VIRTUAL_MEMORY_MANAGEMENT_SUPPORTED, device);
        size_t granularity = 0;
        if (vmm_query == CUDA_SUCCESS && vmm_support != 0) {
            CUmemAllocationProp prop{};
            prop.type = CU_MEM_ALLOCATION_TYPE_PINNED;
            prop.location.type = CU_MEM_LOCATION_TYPE_DEVICE;
            prop.location.id = device;
            vmm_query = cuMemGetAllocationGranularity(&granularity, &prop, CU_MEM_ALLOC_GRANULARITY_MINIMUM);
        }
        uint64_t logical_n = requested_n;
        if (vmm_query == CUDA_SUCCESS && vmm_support != 0 && granularity != 0) {
            const uint64_t requested_bytes = requested_n * sizeof(uint32_t);
            logical_n = ((requested_bytes + granularity - 1) / granularity) * granularity / sizeof(uint32_t);
        }
        const uint64_t logical_bytes = logical_n * sizeof(uint32_t);
        const uint64_t accesses = std::max<uint64_t>(4096, std::min<uint64_t>(static_cast<uint64_t>(o.iterations) * logical_n, 1ull << 26));
        atlas::DeviceBuffer<uint64_t> output(1);
        const auto ring_setup_begin = std::chrono::steady_clock::now();
        atlas::DeviceBuffer<uint32_t> ring(logical_n);
        std::vector<uint32_t> host(static_cast<size_t>(logical_n));
        for (uint64_t i = 0; i < logical_n; ++i) host[static_cast<size_t>(i)] = static_cast<uint32_t>(i + 1);
        ring.copy_from(host);
        ATLAS_CUDA(cudaDeviceSynchronize());
        const double ring_setup_ms = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - ring_setup_begin).count();
        auto ring_run = [&] { ring_walk<<<1, 1>>>(ring.data(), logical_n, accesses, output.data()); };
        if (want_ring) {
            const auto timing = atlas::measure(o, ring_run);
            const uint64_t actual = output.copy_to()[0];
            uint64_t expected = 0;
            for (uint64_t i = 0; i < accesses; ++i) expected += (i % logical_n) + 1;
            auto result = measured(o, "E23", ring_variant, timing);
            result.valid = actual == expected;
            result.configuration["elements"] = std::to_string(logical_n);
            result.configuration["accesses"] = std::to_string(accesses);
            result.configuration["logical_domain_bytes"] = std::to_string(logical_bytes);
            result.configuration["requested_elements"] = std::to_string(requested_n);
            if (granularity != 0) result.configuration["allocation_granularity_bytes"] = std::to_string(granularity);
            result.configuration["setup_scope"] = "ring allocation, host initialization, host-to-device copy, and synchronization; excluded from kernel timing";
            result.metrics["setup_wall_ms"] = ring_setup_ms;
            result.samples["setup_wall_ms"] = {ring_setup_ms};
            result.metrics["checksum"] = static_cast<double>(actual);
            result.limitations.push_back("The ring baseline includes modulo address generation and is not an isolated address-generation instruction benchmark.");
            cases.push_back(std::move(result));
        }
        if (want_alias) {
            auto skip_setup_unknown = [&](const std::string& reason) {
                auto skipped = atlas::skip("E23", alias_variant, reason);
                skipped.configuration["setup_wall_ms"] = "null";
                skipped.configuration["setup_error"] = reason;
                cases.push_back(std::move(skipped));
            };
            if (vmm_query != CUDA_SUCCESS || vmm_support == 0) {
                std::string reason = vmm_query == CUDA_SUCCESS ? "Driver reports virtual memory management unsupported." :
                    "VMM capability or granularity query failed: " + driver_error(vmm_query);
                skip_setup_unknown(reason);
            } else {
                DriverMemory region;
                const auto vmm_setup_begin = std::chrono::steady_clock::now();
                CUresult status = map_vmm(device, static_cast<size_t>(logical_bytes), region);
                if (status != CUDA_SUCCESS) {
                    skip_setup_unknown("Public VMM allocation or fixed mapping failed: " + driver_error(status));
                } else if (region.bytes / sizeof(uint32_t) != logical_n || region.bytes != logical_bytes) {
                    skip_setup_unknown("VMM mapping granularity did not match the baseline logical domain.");
                } else {
                        const uint64_t mapped_n = logical_n;
                        auto* alias = reinterpret_cast<uint32_t*>(static_cast<uintptr_t>(region.address));
                        fill_values<<<256, 256>>>(alias, mapped_n);
                        ATLAS_CUDA(cudaGetLastError());
                        ATLAS_CUDA(cudaDeviceSynchronize());
                        const double vmm_setup_ms = std::chrono::duration<double, std::milli>(
                            std::chrono::steady_clock::now() - vmm_setup_begin).count();
                        auto alias_run = [&] { alias_walk<<<1, 1>>>(alias, mapped_n, accesses, output.data()); };
                        const auto timing = atlas::measure(o, alias_run);
                        const uint64_t actual = output.copy_to()[0];
                        uint64_t expected = 0;
                        for (uint64_t i = 0; i < accesses; ++i) expected += (i % mapped_n) + 1;
                        auto result = measured(o, "E23", alias_variant, timing);
                        result.valid = actual == expected;
                        result.configuration["allocation_granularity_bytes"] = std::to_string(granularity);
                        result.configuration["mapped_bytes_per_alias"] = std::to_string(region.bytes);
                        result.configuration["logical_domain_elements"] = std::to_string(logical_n);
                        result.configuration["logical_domain_bytes"] = std::to_string(logical_bytes);
                        result.configuration["accesses"] = std::to_string(accesses);
                        result.configuration["aliases"] = "2 fixed mappings of one allocation";
                        result.configuration["mapping_changes_during_access"] = "false";
                        result.configuration["setup_scope"] = "VMM address reservation, physical allocation, two mappings, access permissions, initialization, and synchronization; excluded from kernel timing";
                        result.metrics["setup_wall_ms"] = vmm_setup_ms;
                        result.samples["setup_wall_ms"] = {vmm_setup_ms};
                        result.metrics["checksum"] = static_cast<double>(actual);
                        result.limitations.push_back("The two fixed aliases share one physical allocation; only kernel-separated accesses are used and no mapping changes while accesses are live.");
                        result.limitations.push_back("VMM granularity is not assumed to equal hardware translation-page size; timings do not establish TLB capacity or physical address bits.");
                        cases.push_back(std::move(result));
                }
            }
        }
        return cases;
    }

    if (o.experiment == "E24") {
        const uint64_t n = std::max<uint64_t>(4096, std::min<uint64_t>(o.size, 1u << 22));
        const size_t bytes = static_cast<size_t>(n * sizeof(uint32_t));
        atlas::DeviceBuffer<uint64_t> output(1);
        std::vector<uint32_t> initial(static_cast<size_t>(n));
        for (uint64_t i = 0; i < n; ++i) initial[static_cast<size_t>(i)] = static_cast<uint32_t>(i * 5 + 3);

        for (const std::string variant : {"managed_cpu_first", "managed_prefetch", "managed_advised_prefetch", "explicit_device_copy"}) {
            if (!selected(o, variant)) continue;
            auto result = measured(o, "E24", variant, {});
            result.configuration["elements"] = std::to_string(n);
            result.configuration["bytes"] = std::to_string(bytes);
            result.configuration["iterations_per_sample"] = std::to_string(o.iterations);
            result.configuration["measurement_scope"] = "host_end_to_end_latency_only";
            result.configuration["migration_attribution"] = "not observed here; requires supported managed-memory profiler trace";
            result.limitations.push_back("CUDA managed-memory migration policy is driver/platform dependent; the test records public API behavior and does not inspect page tables or infer fault-counter completeness.");
            result.limitations.push_back("These cases report host end-to-end latency, not migration-fault attribution; migration and notification claims require managed-memory tracing where the available profiler supports it.");
            std::vector<double> timings;
            uint64_t expected = 0;
            for (uint32_t value : initial) expected += value;
            if (variant == "explicit_device_copy") {
                atlas::DeviceBuffer<uint32_t> device(n);
                auto call = [&] {
                    device.copy_from(initial);
                    for (int i = 0; i < o.iterations; ++i)
                        reduce_u32<<<1, 1>>>(device.data(), n, output.data());
                };
                timings = atlas::wall_measure(o, call);
                result.samples["host_end_to_end_ms"] = timings;
                auto sorted = timings;
                std::sort(sorted.begin(), sorted.end());
                result.metrics["median_ms"] = sorted[sorted.size() / 2];
                const auto p95 = static_cast<size_t>(std::ceil(0.95 * sorted.size())) - 1;
                result.metrics["p95_ms"] = sorted[std::min(p95, sorted.size() - 1)];
                const auto observed = output.copy_to()[0];
                result.valid = observed == expected;
                result.metrics["checksum"] = static_cast<double>(observed);
                result.configuration["placement"] = "explicit cudaMalloc plus host-to-device copy on each timed call";
            } else {
                uint32_t* managed = nullptr;
                ATLAS_CUDA(cudaMallocManaged(&managed, bytes, cudaMemAttachGlobal));
                for (uint64_t i = 0; i < n; ++i) managed[i] = initial[static_cast<size_t>(i)];
                ATLAS_CUDA(cudaDeviceSynchronize());
                if (variant == "managed_advised_prefetch") {
                    const auto advise = cudaMemAdvise(managed, bytes, cudaMemAdviseSetPreferredLocation, o.device);
                    if (advise != cudaSuccess) {
                        cudaFree(managed);
                        cases.push_back(atlas::skip("E24", variant, std::string("cudaMemAdvise preferred-location request failed: ") + cudaGetErrorString(advise)));
                        continue;
                    }
                }
                auto prepare = [&] {
                    ATLAS_CUDA(cudaMemPrefetchAsync(managed, bytes, cudaCpuDeviceId, nullptr));
                    ATLAS_CUDA(cudaDeviceSynchronize());
                };
                const cudaError_t preflight = cudaMemPrefetchAsync(managed, bytes, cudaCpuDeviceId, nullptr);
                if (preflight != cudaSuccess) {
                    cudaFree(managed);
                    cases.push_back(atlas::skip("E24", variant, std::string("Managed-memory CPU placement preparation failed: ") + cudaGetErrorString(preflight)));
                    continue;
                }
                ATLAS_CUDA(cudaDeviceSynchronize());
                auto call = [&] {
                    if (variant != "managed_cpu_first")
                        ATLAS_CUDA(cudaMemPrefetchAsync(managed, bytes, o.device, nullptr));
                    for (int i = 0; i < o.iterations; ++i)
                        reduce_u32<<<1, 1>>>(managed, n, output.data());
                };
                try {
                    timings = wall_measure_prepared(o, prepare, call);
                    result.samples["host_end_to_end_ms"] = timings;
                    if (!timings.empty()) {
                        auto sorted = timings;
                        std::sort(sorted.begin(), sorted.end());
                        result.metrics["median_ms"] = sorted[sorted.size() / 2];
                        const auto p95 = static_cast<size_t>(std::ceil(0.95 * sorted.size())) - 1;
                        result.metrics["p95_ms"] = sorted[std::min(p95, sorted.size() - 1)];
                    }
                    const uint64_t observed = output.copy_to()[0];
                    result.valid = observed == expected;
                    result.metrics["checksum"] = static_cast<double>(observed);
                    result.configuration["placement"] = variant == "managed_cpu_first" ? "CPU first-touch, then GPU" : "CPU first-touch, GPU prefetch before kernel";
                    if (variant == "managed_advised_prefetch") result.configuration["advice"] = "preferred location = selected GPU";
                } catch (...) {
                    cudaFree(managed);
                    throw;
                }
                ATLAS_CUDA(cudaDeviceSynchronize());
                ATLAS_CUDA(cudaFree(managed));
            }
            if (variant == "explicit_device_copy") {
            result.limitations.push_back("All placements use host end-to-end timing; explicit placement includes one host-to-device copy per sample, managed prefetch placements include one prefetch per sample, and all run the same number of reduction kernels.");
            result.limitations.push_back("Managed samples restore CPU residency before timing; that restoration cost is excluded, while the timed CPU-to-GPU demand migration or prefetch and GPU work are included.");
            }
            cases.push_back(std::move(result));
        }
        return cases;
    }

    if (o.experiment == "E26") {
        const uint64_t n = std::max<uint64_t>(4097, std::min<uint64_t>(o.size, 1u << 20));
        constexpr float pi = 3.14159265358979323846f;
        std::vector<float> input(static_cast<size_t>(n));
        for (uint64_t i = 0; i < n; ++i) {
            // Uniform held-out corpus, with exact domain endpoints and extrema.
            input[static_cast<size_t>(i)] = -pi + (2.0f * pi * static_cast<float>(i) / static_cast<float>(n - 1));
        }
        input.front() = -pi;
        input.back() = pi;
        input[n / 4] = -pi / 2.0f;
        input[n / 2] = 0.0f;
        input[(3 * n) / 4] = pi / 2.0f;
        atlas::DeviceBuffer<float> x(n), y(n);
        x.copy_from(input);
        std::vector<double> reference(static_cast<size_t>(n));
        for (uint64_t i = 0; i < n; ++i) reference[static_cast<size_t>(i)] = std::sin(static_cast<double>(input[static_cast<size_t>(i)]));

        for (const std::string variant : {"sinf_reference", "sfu_sinf", "manual_linear_table", "texture_linear"}) {
            if (!selected(o, variant)) continue;
            constexpr uint32_t table_size = 1025;
            std::vector<float> table(table_size);
            for (uint32_t i = 0; i < table_size; ++i)
                table[i] = std::sin(-pi + 2.0f * pi * static_cast<float>(i) / static_cast<float>(table_size - 1));
            atlas::DeviceBuffer<float> dtable(table_size);
            dtable.copy_from(table);
            cudaTextureObject_t texture = 0;
            cudaArray_t array = nullptr;
            cudaError_t texture_error = cudaSuccess;
            if (variant == "texture_linear") {
                cudaChannelFormatDesc channel = cudaCreateChannelDesc<float>();
                texture_error = cudaMallocArray(&array, &channel, table_size);
                if (texture_error == cudaSuccess)
                    texture_error = cudaMemcpyToArray(array, 0, 0, table.data(), table.size() * sizeof(float), cudaMemcpyHostToDevice);
                cudaResourceDesc resource{};
                resource.resType = cudaResourceTypeArray;
                resource.res.array.array = array;
                cudaTextureDesc desc{};
                desc.addressMode[0] = cudaAddressModeClamp;
                desc.filterMode = cudaFilterModeLinear;
                desc.readMode = cudaReadModeElementType;
                desc.normalizedCoords = 1;
                if (texture_error == cudaSuccess) texture_error = cudaCreateTextureObject(&texture, &resource, &desc, nullptr);
                if (texture_error != cudaSuccess) {
                    if (array) cudaFreeArray(array);
                    cases.push_back(atlas::skip("E26", variant, std::string("Documented CUDA texture object setup failed: ") + cudaGetErrorString(texture_error)));
                    continue;
                }
            }
            auto call = [&] {
                if (variant == "sinf_reference") evaluate_sinf<<<static_cast<unsigned>((n + 255) / 256), 256>>>(x.data(), y.data(), n, false);
                else if (variant == "sfu_sinf") evaluate_sinf<<<static_cast<unsigned>((n + 255) / 256), 256>>>(x.data(), y.data(), n, true);
                else if (variant == "manual_linear_table") evaluate_lut<<<static_cast<unsigned>((n + 255) / 256), 256>>>(x.data(), y.data(), n, dtable.data(), table_size);
                else evaluate_texture<<<static_cast<unsigned>((n + 255) / 256), 256>>>(x.data(), y.data(), n, texture, table_size);
            };
            const auto timing = atlas::measure(o, call);
            const auto observed = y.copy_to();
            double max_abs = 0.0, rms = 0.0;
            bool finite = true;
            for (uint64_t i = 0; i < n; ++i) {
                const double error = std::abs(static_cast<double>(observed[static_cast<size_t>(i)]) - reference[static_cast<size_t>(i)]);
                max_abs = std::max(max_abs, error);
                rms += error * error;
                finite = finite && std::isfinite(observed[static_cast<size_t>(i)]);
            }
            rms = std::sqrt(rms / n);
            auto result = measured(o, "E26", variant, timing);
            const double tolerance = variant == "manual_linear_table" || variant == "texture_linear" ? 1.0e-4 : 2.0e-6;
            result.valid = finite && max_abs <= tolerance;
            result.configuration["domain"] = "[-pi, pi] inclusive";
            result.configuration["input_points"] = std::to_string(n);
            result.configuration["table_samples"] = std::to_string(table_size);
            result.configuration["absolute_error_tolerance"] = std::to_string(tolerance);
            result.metrics["max_absolute_error_vs_cpu_double"] = max_abs;
            result.metrics["rms_error_vs_cpu_double"] = rms;
            result.metrics["evaluations"] = static_cast<double>(n);
            result.limitations.push_back("The finite uniform corpus includes endpoints and extrema but is not a proof of the global error bound or derivative error.");
            result.limitations.push_back("Texture interpolation reflects the CUDA texture-object path only; graphics-engine access is not assumed.");
            result.limitations.push_back("The CPU double-precision sine is the oracle; measured error includes input conversion to float.");
            cases.push_back(std::move(result));
            if (texture) cudaDestroyTextureObject(texture);
            if (array) cudaFreeArray(array);
        }
        return cases;
    }

    throw std::invalid_argument("run_memory supports E07, E08, E23, E24, and E26");
}

int main(int argc, char** argv) { return atlas::main(argc, argv, run_memory); }
