#include "common.hpp"

#include <cuda_runtime.h>
#include <cuda/atomic>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <numeric>
#include <random>
#include <sstream>
#include <vector>

#if defined(__linux__)
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <dirent.h>
#include <linux/mempolicy.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>
#endif

namespace atlas {
namespace {

class CurrentDevice {
public:
    explicit CurrentDevice(int device) {
        ATLAS_CUDA(cudaGetDevice(&previous_));
        if (previous_ != device) ATLAS_CUDA(cudaSetDevice(device));
    }
    ~CurrentDevice() { if (previous_ >= 0) cudaSetDevice(previous_); }
    CurrentDevice(const CurrentDevice&) = delete;
    CurrentDevice& operator=(const CurrentDevice&) = delete;
private:
    int previous_ = -1;
};

class Stream {
public:
    explicit Stream(unsigned flags = cudaStreamNonBlocking) {
        ATLAS_CUDA(cudaStreamCreateWithFlags(&value_, flags));
    }
    ~Stream() { if (value_) cudaStreamDestroy(value_); }
    Stream(const Stream&) = delete;
    Stream& operator=(const Stream&) = delete;
    operator cudaStream_t() const { return value_; }
    cudaStream_t get() const { return value_; }
private:
    cudaStream_t value_ = nullptr;
};

class Event {
public:
    explicit Event(unsigned flags = cudaEventDefault) { ATLAS_CUDA(cudaEventCreateWithFlags(&value_, flags)); }
    ~Event() { if (value_) cudaEventDestroy(value_); }
    Event(const Event&) = delete;
    Event& operator=(const Event&) = delete;
    cudaEvent_t get() const { return value_; }
private:
    cudaEvent_t value_ = nullptr;
};

template <class T>
class PinnedBuffer {
public:
    explicit PinnedBuffer(std::size_t n) : n_(n) {
        if (n_) ATLAS_CUDA(cudaHostAlloc(reinterpret_cast<void**>(&ptr_), n_ * sizeof(T), cudaHostAllocDefault));
    }
    ~PinnedBuffer() { if (ptr_) cudaFreeHost(ptr_); }
    PinnedBuffer(const PinnedBuffer&) = delete;
    PinnedBuffer& operator=(const PinnedBuffer&) = delete;
    T* data() { return ptr_; }
    const T* data() const { return ptr_; }
    std::size_t size() const { return n_; }
private:
    T* ptr_ = nullptr;
    std::size_t n_ = 0;
};

__global__ void increment_kernel(std::uint32_t* out, const std::uint32_t* in, std::size_t n) {
    const std::size_t i = static_cast<std::size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i < n) out[i] = in[i] + 1u;
}

__host__ __device__ inline std::uint32_t pattern(std::size_t i, unsigned seed);

__global__ void chain_kernel(const std::uint32_t* next, std::uint32_t* out,
                             std::size_t n, int steps, std::uint32_t start) {
    if (blockIdx.x || threadIdx.x) return;
    std::uint32_t p = start % static_cast<std::uint32_t>(n);
    for (int i = 0; i < steps; ++i) p = next[p];
    out[0] = p;
}

__global__ void independent_kernel(const std::uint32_t* values, std::uint32_t* out,
                                   std::size_t n, int rounds) {
    const std::size_t tid = static_cast<std::size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (tid >= n) return;
    std::uint32_t acc = static_cast<std::uint32_t>(tid);
    for (int r = 0; r < rounds; ++r) {
        const std::size_t i = (tid + static_cast<std::size_t>(r) * 997u) % n;
        acc += values[i];
    }
    out[tid] = acc;
}

__global__ void marker_kernel(std::uint32_t* p) {
    if (blockIdx.x == 0 && threadIdx.x == 0) ++(*p);
}

__global__ void increment_inplace_kernel(std::uint32_t* data, std::size_t n) {
    const std::size_t i = static_cast<std::size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i < n) ++data[i];
}

__global__ void peer_atomic_producer(std::uint32_t* remote_ready, std::uint32_t* remote_ack,
                                     std::uint32_t* payload, std::uint32_t* error,
                                     std::uint32_t phases, std::uint32_t base,
                                     std::uint32_t seed, unsigned long long timeout_cycles) {
    if (blockIdx.x != 0 || threadIdx.x != 0) return;
    cuda::atomic_ref<std::uint32_t, cuda::thread_scope_system> ready(*remote_ready);
    cuda::atomic_ref<std::uint32_t, cuda::thread_scope_system> ack(*remote_ack);
    for (std::uint32_t phase = 1; phase <= phases; ++phase) {
        const std::uint32_t ticket = phase;
        payload[0] = pattern(static_cast<std::size_t>(base) + phase, seed);
        // System-scope release publication makes the preceding payload store
        // visible before the consumer observes this ticket with acquire.
        ready.store(ticket, cuda::memory_order_release);
        const unsigned long long start = clock64();
        while (ack.load(cuda::memory_order_acquire) != ticket) {
            if (clock64() - start > timeout_cycles) { *error = phase; return; }
        }
    }
}

__global__ void peer_atomic_consumer(const std::uint32_t* remote_ready,
                                     const std::uint32_t* remote_payload,
                                     std::uint32_t* remote_ack,
                                     std::uint32_t* observed, std::uint32_t* error,
                                     std::uint32_t phases, std::uint32_t base,
                                     std::uint32_t seed, unsigned long long timeout_cycles) {
    if (blockIdx.x != 0 || threadIdx.x != 0) return;
    // This CTA is the only receiver and runs concurrently with exactly one
    // producer CTA on the peer GPU; both clocks are used only for local bounds.
    cuda::atomic_ref<std::uint32_t, cuda::thread_scope_system> ready(*const_cast<std::uint32_t*>(remote_ready));
    cuda::atomic_ref<std::uint32_t, cuda::thread_scope_system> ack(*remote_ack);
    for (std::uint32_t phase = 1; phase <= phases; ++phase) {
        const unsigned long long start = clock64();
        while (ready.load(cuda::memory_order_acquire) != phase) {
            if (clock64() - start > timeout_cycles) { *error = phase; return; }
        }
        const std::uint32_t value = remote_payload[0];
        observed[phase - 1] = value;
        const std::uint32_t expected = pattern(static_cast<std::size_t>(base) + phase, seed);
        if (value != expected) { *error = phase; return; }
        // The producer waits for this acknowledgement before overwriting payload.
        ack.store(phase, cuda::memory_order_release);
    }
}

#if defined(ATLAS_ENABLE_CDP)
__global__ void child_increment(std::uint32_t* data, std::size_t n) {
    const std::size_t i = static_cast<std::size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i < n) ++data[i];
}

__global__ void cdp_stage_parent(std::uint32_t* data, std::size_t n, int stages,
                                int* child_error) {
    if (blockIdx.x != 0 || threadIdx.x != 0) return;
    cudaStream_t children;
    const cudaError_t stream_status = cudaStreamCreateWithFlags(&children, cudaStreamNonBlocking);
    if (stream_status != cudaSuccess) { *child_error = static_cast<int>(stream_status); return; }
    // Explicitly serialize child stages in one device stream. Parent completion
    // waits for descendants; no device-side child synchronization is used.
    for (int stage = 0; stage < stages; ++stage) {
        child_increment<<<static_cast<unsigned>((n + 255u) / 256u), 256, 0, children>>>(data, n);
        const cudaError_t launch_status = cudaGetLastError();
        if (launch_status != cudaSuccess) {
            *child_error = static_cast<int>(launch_status);
            (void)cudaStreamDestroy(children);
            return;
        }
    }
    const cudaError_t destroy_status = cudaStreamDestroy(children);
    if (destroy_status != cudaSuccess) *child_error = static_cast<int>(destroy_status);
}
#endif

inline unsigned blocks(std::size_t n) {
    return static_cast<unsigned>((n + 255u) / 256u);
}

inline double median(std::vector<double> v) {
    if (v.empty()) return std::numeric_limits<double>::quiet_NaN();
    std::sort(v.begin(), v.end());
    const std::size_t m = v.size() / 2;
    return v.size() % 2 ? v[m] : (v[m - 1] + v[m]) * 0.5;
}

inline double p95(std::vector<double> v) {
    if (v.empty()) return std::numeric_limits<double>::quiet_NaN();
    std::sort(v.begin(), v.end());
    const std::size_t i = std::min(v.size() - 1, static_cast<std::size_t>(std::ceil(v.size() * .95) - 1));
    return v[i];
}

inline void summarize(CaseResult& c, const std::string& key, std::vector<double> samples) {
    c.samples[key + "_ms"] = samples;
    c.metrics[key + "_median_ms"] = median(samples);
    c.metrics[key + "_p95_ms"] = p95(samples);
}

inline bool selected(const Options& o, const std::string& variant) {
    const auto it = o.args.find("variant");
    return it == o.args.end() || it->second.empty() || it->second == variant;
}

inline CaseResult peer_gate_result(const std::string& experiment, const std::string& variant,
                                   const std::string& reason) {
    const bool absent = reason == "CUDA reports no direct peer access for this directed pair";
    return skip(experiment, variant, reason, absent ? "NOT_RUN" : "INCONCLUSIVE");
}

inline bool peer_supported(int from, int to, std::string* why = nullptr) {
    int can = 0;
    const cudaError_t e = cudaDeviceCanAccessPeer(&can, from, to);
    if (e != cudaSuccess) {
        if (why) *why = std::string("cudaDeviceCanAccessPeer failed: ") + cudaGetErrorString(e);
        cudaGetLastError();
        return false;
    }
    if (!can) {
        if (why) *why = "CUDA reports no direct peer access for this directed pair";
        return false;
    }
    int perf = 0;
    const cudaError_t a = cudaDeviceGetP2PAttribute(&perf, cudaDevP2PAttrPerformanceRank, from, to);
    if (a != cudaSuccess) {
        if (why) *why = std::string("peer is accessible but performance rank is unavailable: ") + cudaGetErrorString(a);
        cudaGetLastError();
        return false;
    }
    return true;
}

inline bool enable_peer(int device, int peer, std::string* reason = nullptr) {
    CurrentDevice guard(device);
    const cudaError_t e = cudaDeviceEnablePeerAccess(peer, 0);
    if (e == cudaSuccess) return true;
    if (e == cudaErrorPeerAccessAlreadyEnabled) {
        cudaGetLastError();
        return true;
    }
    if (reason) *reason = std::string("cudaDeviceEnablePeerAccess failed: ") + cudaGetErrorString(e);
    cudaGetLastError();
    return false;
}

class PeerAccessLease {
public:
    bool acquire(int first, int second, std::string* reason) {
        first_ = first; second_ = second;
        if (!acquire_one(first_, second_, &owned_first_, reason)) return false;
        if (!acquire_one(second_, first_, &owned_second_, reason)) {
            release();
            return false;
        }
        return true;
    }

    bool release() noexcept {
        bool ok = true;
        if (owned_second_) ok = disable_one(second_, first_) && ok;
        if (owned_first_) ok = disable_one(first_, second_) && ok;
        owned_first_ = owned_second_ = false;
        return ok;
    }
    ~PeerAccessLease() { if (owned_first_ || owned_second_) (void)release(); }
    PeerAccessLease() = default;
    PeerAccessLease(const PeerAccessLease&) = delete;
    PeerAccessLease& operator=(const PeerAccessLease&) = delete;

private:
    static bool acquire_one(int from, int to, bool* owned, std::string* reason) {
        CurrentDevice device(from);
        // AccessSupported is a link capability query in practice on this
        // runtime, not a reliable per-process enable-state check. Ask the
        // authoritative operation and use AlreadyEnabled for ownership.
        const cudaError_t e = cudaDeviceEnablePeerAccess(to, 0);
        if (e == cudaSuccess) { *owned = true; return true; }
        if (e == cudaErrorPeerAccessAlreadyEnabled) { *owned = false; cudaGetLastError(); return true; }
        if (reason) *reason = std::string("peer access enable failed: ") + cudaGetErrorString(e);
        cudaGetLastError(); return false;
    }

    static bool disable_one(int from, int to) noexcept {
        CurrentDevice device(from);
        const cudaError_t e = cudaDeviceDisablePeerAccess(to);
        if (e == cudaSuccess) return true;
        cudaGetLastError(); return false;
    }

    int first_ = -1, second_ = -1;
    bool owned_first_ = false, owned_second_ = false;
};

__host__ __device__ inline std::uint32_t pattern(std::size_t i, unsigned seed) {
    std::uint32_t x = static_cast<std::uint32_t>(i) ^ seed;
    x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15; x *= 0x846ca68bu; x ^= x >> 16;
    return x;
}

Cases run_e17(const Options& o) {
    Cases out;
    const std::size_t n = o.size;
    if (n > std::numeric_limits<std::size_t>::max() / sizeof(std::uint32_t))
        throw std::invalid_argument("E17 size overflows allocation");
    CurrentDevice device(o.device);
    const std::size_t bytes = n * sizeof(std::uint32_t);
    std::vector<std::uint32_t> pageable(n), pageable_out(n);
    PinnedBuffer<std::uint32_t> pinned(n), pinned_out(n);
    std::vector<std::uint32_t> expected(n);
    for (std::size_t i = 0; i < n; ++i) {
        const std::uint32_t v = pattern(i, o.seed);
        pageable[i] = v; pinned.data()[i] = v; expected[i] = v + 1u;
    }
    DeviceBuffer<std::uint32_t> d_in(n), d_out(n);
    Stream stream;
    for (const bool use_pinned : {false, true}) {
        CaseResult c; c.experiment = "E17"; c.variant = use_pinned ? "pinned_h2d_kernel_d2h_serial" : "pageable_h2d_kernel_d2h_serial";
        if (!selected(o, c.variant)) continue;
        c.configuration["device"] = std::to_string(o.device); c.configuration["bytes"] = std::to_string(bytes);
        c.configuration["buffer_depth"] = "1"; c.configuration["synchronization"] = "one_nonblocking_stream_completion";
        const void* src = use_pinned ? static_cast<const void*>(pinned.data()) : static_cast<const void*>(pageable.data());
        void* dst = use_pinned ? static_cast<void*>(pinned_out.data()) : static_cast<void*>(pageable_out.data());
        auto samples = wall_measure(o, [&] {
            ATLAS_CUDA(cudaMemcpyAsync(d_in.data(), src, bytes, cudaMemcpyHostToDevice, stream));
            increment_kernel<<<blocks(n), 256, 0, stream>>>(d_out.data(), d_in.data(), n);
            ATLAS_CUDA(cudaMemcpyAsync(dst, d_out.data(), bytes, cudaMemcpyDeviceToHost, stream));
        }, stream);
        const auto& actual = use_pinned ? std::vector<std::uint32_t>(pinned_out.data(), pinned_out.data() + n) : pageable_out;
        c.valid = actual == expected;
        if (!c.valid) c.limitations.emplace_back("H2D-kernel-D2H result differs from the independent host oracle");
        summarize(c, "complete_path", samples);
        out.push_back(std::move(c));
    }

    // Two independent slots have independent host and device storage. Each slot's
    // event chain protects its source and destination until DMA has completed.
    std::array<PinnedBuffer<std::uint32_t>, 2> inputs{{PinnedBuffer<std::uint32_t>(n), PinnedBuffer<std::uint32_t>(n)}};
    std::array<PinnedBuffer<std::uint32_t>, 2> outputs{{PinnedBuffer<std::uint32_t>(n), PinnedBuffer<std::uint32_t>(n)}};
    std::array<std::unique_ptr<DeviceBuffer<std::uint32_t>>, 2> din{{
        std::make_unique<DeviceBuffer<std::uint32_t>>(n), std::make_unique<DeviceBuffer<std::uint32_t>>(n)}};
    std::array<std::unique_ptr<DeviceBuffer<std::uint32_t>>, 2> dout{{
        std::make_unique<DeviceBuffer<std::uint32_t>>(n), std::make_unique<DeviceBuffer<std::uint32_t>>(n)}};
    std::array<std::unique_ptr<Stream>, 3> streams{{std::make_unique<Stream>(), std::make_unique<Stream>(), std::make_unique<Stream>()}};
    std::array<std::unique_ptr<Event>, 2> ready{{std::make_unique<Event>(), std::make_unique<Event>()}};
    std::array<std::unique_ptr<Event>, 2> computed{{std::make_unique<Event>(), std::make_unique<Event>()}};
    for (int slot = 0; slot < 2; ++slot) for (std::size_t i = 0; i < n; ++i) inputs[slot].data()[i] = pattern(i + slot * n, o.seed);
    CaseResult overlap; overlap.experiment = "E17"; overlap.variant = "pinned_two_slot_h2d_compute_d2h_pipeline";
    if (!selected(o, overlap.variant)) return out;
    overlap.configuration["device"] = std::to_string(o.device); overlap.configuration["bytes_per_slot"] = std::to_string(bytes);
    overlap.configuration["buffer_depth"] = "2"; overlap.configuration["synchronization"] = "per_slot_ready_and_computed_events";
    auto overlap_samples = wall_measure(o, [&] {
        for (int slot = 0; slot < 2; ++slot) {
            ATLAS_CUDA(cudaMemcpyAsync(din[slot]->data(), inputs[slot].data(), bytes, cudaMemcpyHostToDevice, streams[0]->get()));
            ATLAS_CUDA(cudaEventRecord(ready[slot]->get(), streams[0]->get()));
            ATLAS_CUDA(cudaStreamWaitEvent(streams[1]->get(), ready[slot]->get(), 0));
            increment_kernel<<<blocks(n), 256, 0, streams[1]->get()>>>(dout[slot]->data(), din[slot]->data(), n);
            ATLAS_CUDA(cudaEventRecord(computed[slot]->get(), streams[1]->get()));
            ATLAS_CUDA(cudaStreamWaitEvent(streams[2]->get(), computed[slot]->get(), 0));
            ATLAS_CUDA(cudaMemcpyAsync(outputs[slot].data(), dout[slot]->data(), bytes, cudaMemcpyDeviceToHost, streams[2]->get()));
        }
        ATLAS_CUDA(cudaStreamSynchronize(streams[2]->get()));
    });
    overlap.valid = true;
    for (int slot = 0; slot < 2 && overlap.valid; ++slot)
        for (std::size_t i = 0; i < n; ++i)
            if (outputs[slot].data()[i] != inputs[slot].data()[i] + 1u) { overlap.valid = false; break; }
    if (!overlap.valid) overlap.limitations.emplace_back("overlapped pipeline output differs from independent host oracle");
    overlap.limitations.emplace_back("concurrent execution is a legal dependency pipeline; actual physical overlap requires timeline evidence");
    summarize(overlap, "two_slot_complete_path", overlap_samples);
    out.push_back(std::move(overlap));
    return out;
}

Cases run_e18(const Options& o) {
    Cases out;
    std::string reason;
    if (!peer_supported(o.device, o.peer, &reason)) return {peer_gate_result("E18", "peer_access_gate", reason)};
    if (!enable_peer(o.device, o.peer, &reason)) return {skip("E18", "peer_access_enable", reason, "INCONCLUSIVE")};
    const std::size_t n = std::max<std::size_t>(1, std::min<std::size_t>(o.size, 1u << 24));
    const int steps = std::max(1, std::min(o.iterations, 1000)) * 1000;
    std::vector<std::uint32_t> indices(n);
    // A single deterministic cycle gives an exact pointer-chain oracle.
    for (std::size_t i = 0; i < n; ++i) indices[i] = static_cast<std::uint32_t>((i + 1) % n);
    CurrentDevice local_device(o.device);
    DeviceBuffer<std::uint32_t> local(n), result(1);
    local.copy_from(indices);
    CurrentDevice dev_peer(o.peer);
    DeviceBuffer<std::uint32_t> remote(n);
    remote.copy_from(indices);
    const std::size_t result_index = n ? (static_cast<std::size_t>(steps) % n) : 0;
    for (const auto& item : std::vector<std::pair<std::string, const std::uint32_t*>>{
             {"local_pointer_chain", local.data()}, {"peer_pointer_chain", remote.data()}}) {
        CurrentDevice dev(o.device);
        Stream stream;
        CaseResult c; c.experiment = "E18"; c.variant = item.first;
        if (!selected(o, c.variant)) continue;
        c.configuration["device"] = std::to_string(o.device); c.configuration["peer"] = std::to_string(o.peer);
        c.configuration["working_set_bytes"] = std::to_string(n * sizeof(std::uint32_t));
        c.configuration["dependent_steps"] = std::to_string(steps); c.configuration["access_pattern"] = "one_thread_cycle";
        auto samples = measure(o, [&] { chain_kernel<<<1, 1, 0, stream.get()>>>(item.second, result.data(), n, steps, 0u); }, stream.get());
        const auto got = result.copy_to()[0]; c.valid = got == result_index;
        if (!c.valid) c.limitations.emplace_back("pointer-chain terminal index differs from cycle oracle");
        summarize(c, "kernel", samples);
        out.push_back(std::move(c));
    }
    // Independent requests use a separate resident peer table and validate all outputs.
    if (selected(o, "peer_independent_loads")) {
        CurrentDevice dev(o.device);
        DeviceBuffer<std::uint32_t> results(n);
        Stream stream;
        const int rounds = std::max(1, std::min(o.iterations, 4096));
        CaseResult c; c.experiment = "E18"; c.variant = "peer_independent_loads";
        c.configuration["device"] = std::to_string(o.device); c.configuration["peer"] = std::to_string(o.peer);
        c.configuration["working_set_bytes"] = std::to_string(n * sizeof(std::uint32_t)); c.configuration["rounds"] = std::to_string(rounds);
        auto samples = measure(o, [&] { independent_kernel<<<blocks(n), 256, 0, stream.get()>>>(remote.data(), results.data(), n, rounds); }, stream.get());
        const auto actual = results.copy_to(); c.valid = actual.size() == n;
        for (std::size_t i = 0; i < n && c.valid; ++i) {
            std::uint32_t expected = static_cast<std::uint32_t>(i);
            for (int r = 0; r < rounds; ++r) expected += indices[(i + static_cast<std::size_t>(r) * 997u) % n];
            if (actual[i] != expected) c.valid = false;
        }
        if (!c.valid) c.limitations.emplace_back("independent peer loads differ from exact host oracle");
        summarize(c, "kernel", samples); out.push_back(std::move(c));
    }
    // Explicit peer copy is the staged baseline; report preparation and local access separately.
    if (selected(o, "peer_stage_then_local_chain")) {
        CurrentDevice dev(o.device);
        DeviceBuffer<std::uint32_t> staged(n);
        Stream stream;
        CaseResult c; c.experiment = "E18"; c.variant = "peer_stage_then_local_chain";
        c.configuration["device"] = std::to_string(o.device); c.configuration["peer"] = std::to_string(o.peer);
        c.configuration["working_set_bytes"] = std::to_string(n * sizeof(std::uint32_t)); c.configuration["route"] = "cudaMemcpyPeerAsync_then_local_pointer_chain";
        auto copy_samples = wall_measure(o, [&] {
            ATLAS_CUDA(cudaMemcpyPeerAsync(staged.data(), o.device, remote.data(), o.peer, n * sizeof(std::uint32_t), stream.get()));
            ATLAS_CUDA(cudaStreamSynchronize(stream.get()));
        });
        auto kernel_samples = measure(o, [&] { chain_kernel<<<1, 1, 0, stream.get()>>>(staged.data(), result.data(), n, steps, 0u); }, stream.get());
        c.valid = result.copy_to()[0] == result_index;
        summarize(c, "peer_stage_preparation", copy_samples); summarize(c, "resident_local_kernel", kernel_samples);
        out.push_back(std::move(c));
    }
    { CurrentDevice peer_cleanup(o.peer); remote = DeviceBuffer<std::uint32_t>(0); }
    return out;
}

inline std::string pointer_text(const void* pointer) {
    std::ostringstream out;
    out << "0x" << std::hex << reinterpret_cast<std::uintptr_t>(pointer);
    return out.str();
}

bool inspect_device_pointer(const void* pointer, int owner_device, int accessor_device,
                            const std::string& key, CaseResult& result,
                            void** accessible_alias, std::string* failure) {
    CurrentDevice device(accessor_device);
    cudaPointerAttributes attributes{};
    const cudaError_t e = cudaPointerGetAttributes(&attributes, pointer);
    if (e != cudaSuccess) {
        if (failure) *failure = std::string("cudaPointerGetAttributes(") + key + ") failed: " + cudaGetErrorString(e);
        cudaGetLastError();
        return false;
    }
    result.configuration[key + "_original_pointer"] = pointer_text(pointer);
    result.configuration[key + "_memory_type"] = std::to_string(static_cast<int>(attributes.type));
    result.configuration[key + "_owner_device"] = std::to_string(attributes.device);
    result.configuration[key + "_accessor_device"] = std::to_string(accessor_device);
    result.configuration[key + "_device_alias"] = pointer_text(attributes.devicePointer);
    if (attributes.type != cudaMemoryTypeDevice || attributes.device != owner_device) {
        if (failure) *failure = key + " allocation type/owner did not match its CUDA allocation context";
        return false;
    }
    if (!attributes.devicePointer) {
        if (failure) *failure = key + " has no devicePointer alias on the intended accessor GPU";
        return false;
    }
    *accessible_alias = attributes.devicePointer;
    return true;
}

CaseResult run_e19_atomic(const Options& o) {
    CaseResult result; result.experiment = "E19"; result.variant = "peer_system_scope_atomic_publication";
    auto not_run = [&](const std::string& why) {
        result.status = "NOT_RUN"; result.valid = false; result.limitations.push_back(why); return result;
    };
    auto inconclusive = [&](const std::string& why) {
        result.status = "INCONCLUSIVE"; result.valid = false; result.limitations.push_back(why); return result;
    };
    result.configuration["producer_device"] = std::to_string(o.device);
    result.configuration["consumer_device"] = std::to_string(o.peer);
    int can_forward = 0, can_reverse = 0;
    cudaError_t e = cudaDeviceCanAccessPeer(&can_forward, o.device, o.peer);
    if (e == cudaSuccess) e = cudaDeviceCanAccessPeer(&can_reverse, o.peer, o.device);
    if (e != cudaSuccess) {
        cudaGetLastError();
        return inconclusive(std::string("CUDA peer capability query failed: ") + cudaGetErrorString(e));
    }
    result.configuration["cudaDeviceCanAccessPeer_forward"] = std::to_string(can_forward);
    result.configuration["cudaDeviceCanAccessPeer_reverse"] = std::to_string(can_reverse);
    if (!can_forward || !can_reverse)
        return not_run("peer access unavailable in one or both directions; native atomic publication not run");

    int access_forward = 0, access_reverse = 0;
    e = cudaDeviceGetP2PAttribute(&access_forward, cudaDevP2PAttrAccessSupported, o.device, o.peer);
    if (e == cudaSuccess)
        e = cudaDeviceGetP2PAttribute(&access_reverse, cudaDevP2PAttrAccessSupported, o.peer, o.device);
    if (e != cudaSuccess) {
        const std::string message = std::string("peer access capability observation failed: ") + cudaGetErrorString(e);
        cudaGetLastError(); return inconclusive(message);
    }
    result.configuration["cudaDevP2PAttrAccessSupported_forward"] = std::to_string(access_forward);
    result.configuration["cudaDevP2PAttrAccessSupported_reverse"] = std::to_string(access_reverse);

    cudaDeviceProp producer_properties{}, consumer_properties{};
    e = cudaGetDeviceProperties(&producer_properties, o.device);
    if (e == cudaSuccess) e = cudaGetDeviceProperties(&consumer_properties, o.peer);
    if (e != cudaSuccess) {
        const std::string message = std::string("UVA device-property query failed: ") + cudaGetErrorString(e);
        cudaGetLastError(); return inconclusive(message);
    }
    result.configuration["unifiedAddressing_producer"] = producer_properties.unifiedAddressing ? "1" : "0";
    result.configuration["unifiedAddressing_consumer"] = consumer_properties.unifiedAddressing ? "1" : "0";
    if (!producer_properties.unifiedAddressing || !consumer_properties.unifiedAddressing)
        return not_run("UVA is unavailable on one or both GPUs; native peer pointer publication not run");

    int native_forward = 0, native_reverse = 0;
    e = cudaDeviceGetP2PAttribute(&native_forward, cudaDevP2PAttrNativeAtomicSupported, o.device, o.peer);
    if (e == cudaSuccess)
        e = cudaDeviceGetP2PAttribute(&native_reverse, cudaDevP2PAttrNativeAtomicSupported, o.peer, o.device);
    if (e != cudaSuccess) {
        const std::string message = std::string("native peer atomic capability query failed: ") + cudaGetErrorString(e);
        cudaGetLastError(); return inconclusive(message);
    }
    result.configuration["cudaDevP2PAttrNativeAtomicSupported_forward"] = std::to_string(native_forward);
    result.configuration["cudaDevP2PAttrNativeAtomicSupported_reverse"] = std::to_string(native_reverse);
    if (!native_forward || !native_reverse)
        return not_run("native system-scope peer atomic attribute is false for at least one direction");

    std::string peer_reason;
    PeerAccessLease peer_access;
    if (!peer_access.acquire(o.device, o.peer, &peer_reason)) return inconclusive(peer_reason);
    auto disposition = [&](const std::string& status, const std::string& why) {
        result.status = status;
        result.valid = false;
        result.limitations.push_back(why);
        if (!peer_access.release()) result.limitations.emplace_back("failed to restore peer access enabled by this case");
        return result;
    };

    const std::uint32_t phases = static_cast<std::uint32_t>(std::clamp(o.iterations, 1, 256));
    const std::uint32_t seed = o.seed;
    const unsigned long long deadline = static_cast<unsigned long long>(std::clamp(o.integer("deadline-cycles", 50000000), 1000000, 1000000000));
    result.configuration["phases_per_handshake"] = std::to_string(phases);
    result.configuration["deadline_cycles_per_phase"] = std::to_string(deadline);
    result.configuration["progress_proof"] = "one resident CTA per device; producer awaits consumer ack before payload overwrite; receiver acquire-loads ready then release-stores ack";
    result.configuration["memory_order"] = "cuda::atomic_ref<uint32_t, thread_scope_system> release/acquire";

    CurrentDevice producer_device(o.device);
    DeviceBuffer<std::uint32_t> payload(1), ready(1), producer_error(1);
    Stream producer_stream;
    ATLAS_CUDA(cudaMemset(payload.data(), 0, sizeof(std::uint32_t)));
    ATLAS_CUDA(cudaMemset(ready.data(), 0, sizeof(std::uint32_t)));
    ATLAS_CUDA(cudaMemset(producer_error.data(), 0, sizeof(std::uint32_t)));
    CurrentDevice consumer_device(o.peer);
    DeviceBuffer<std::uint32_t> ack(1), consumer_error(1), observed(phases);
    Stream consumer_stream;
    ATLAS_CUDA(cudaMemset(ack.data(), 0, sizeof(std::uint32_t)));
    ATLAS_CUDA(cudaMemset(consumer_error.data(), 0, sizeof(std::uint32_t)));
    void* ready_for_consumer = nullptr;
    void* payload_for_consumer = nullptr;
    void* ack_for_producer = nullptr;
    std::string pointer_problem;
    bool pointers_valid = true;
    {
        CurrentDevice producer_context(o.device);
        void* ready_owner_alias = nullptr;
        void* payload_owner_alias = nullptr;
        pointers_valid = inspect_device_pointer(ready.data(), o.device, o.device,
            "ready_owner", result, &ready_owner_alias, &pointer_problem) && pointers_valid;
        pointers_valid = inspect_device_pointer(payload.data(), o.device, o.device,
            "payload_owner", result, &payload_owner_alias, &pointer_problem) && pointers_valid;
        pointers_valid = inspect_device_pointer(ack.data(), o.peer, o.device,
            "ack_from_producer", result, &ack_for_producer, &pointer_problem) && pointers_valid;
    }
    {
        CurrentDevice consumer_context(o.peer);
        void* ack_owner_alias = nullptr;
        pointers_valid = inspect_device_pointer(ack.data(), o.peer, o.peer,
            "ack_owner", result, &ack_owner_alias, &pointer_problem) && pointers_valid;
        pointers_valid = inspect_device_pointer(ready.data(), o.device, o.peer,
            "ready_from_consumer", result, &ready_for_consumer, &pointer_problem) && pointers_valid;
        pointers_valid = inspect_device_pointer(payload.data(), o.device, o.peer,
            "payload_from_consumer", result, &payload_for_consumer, &pointer_problem) && pointers_valid;
    }
    if (!pointers_valid) {
        return disposition("INCONCLUSIVE",
            "pointer ownership/alias preflight failed: " + pointer_problem);
    }
    std::vector<std::uint32_t> expected(phases);
    for (std::uint32_t i = 0; i < phases; ++i) expected[i] = pattern(static_cast<std::size_t>(i) + 1u, seed);

    std::string failing_phase = "per-device flag initialization or launch submission";
    std::string runtime_failure;
    std::vector<double> samples;
    try { samples = wall_measure(o, [&] {
        if (!runtime_failure.empty()) return;
        {
            CurrentDevice producer_context(o.device);
            ATLAS_CUDA(cudaMemsetAsync(ready.data(), 0, sizeof(std::uint32_t), producer_stream.get()));
            ATLAS_CUDA(cudaMemsetAsync(producer_error.data(), 0, sizeof(std::uint32_t), producer_stream.get()));
            peer_atomic_producer<<<1, 1, 0, producer_stream.get()>>>(
                ready.data(), static_cast<std::uint32_t*>(ack_for_producer), payload.data(),
                producer_error.data(), phases, 0u, seed, deadline);
        }
        {
            CurrentDevice consumer_context(o.peer);
            ATLAS_CUDA(cudaMemsetAsync(ack.data(), 0, sizeof(std::uint32_t), consumer_stream.get()));
            ATLAS_CUDA(cudaMemsetAsync(consumer_error.data(), 0, sizeof(std::uint32_t), consumer_stream.get()));
            peer_atomic_consumer<<<1, 1, 0, consumer_stream.get()>>>(
                static_cast<const std::uint32_t*>(ready_for_consumer),
                static_cast<const std::uint32_t*>(payload_for_consumer), ack.data(),
                observed.data(), consumer_error.data(), phases, 0u, seed, deadline);
        }
        cudaError_t producer_status = cudaSuccess, consumer_status = cudaSuccess;
        failing_phase = "producer stream completion (includes remote acknowledgement load)";
        { CurrentDevice producer_context(o.device); producer_status = cudaStreamSynchronize(producer_stream.get()); }
        failing_phase = "consumer stream completion (includes remote ready atomic and payload load)";
        { CurrentDevice consumer_context(o.peer); consumer_status = cudaStreamSynchronize(consumer_stream.get()); }
        if (producer_status != cudaSuccess || consumer_status != cudaSuccess) {
            std::ostringstream message;
            message << "CUDA stream completion failed during " << failing_phase
                    << "; producer=" << cudaGetErrorName(producer_status)
                    << ", consumer=" << cudaGetErrorName(consumer_status);
            runtime_failure = message.str();
            cudaGetLastError();
        }
    }); } catch (const std::exception& e) {
        return disposition("INCONCLUSIVE", "native handshake runtime fault during " + failing_phase + ": " + e.what());
    }
    if (!runtime_failure.empty())
        return disposition("INCONCLUSIVE", "native handshake runtime fault: " + runtime_failure);
    std::uint32_t producer_failure = 0, receiver_failure = 0, final_ready = 0, final_ack = 0;
    { CurrentDevice producer_context(o.device); producer_failure = producer_error.copy_to()[0]; final_ready = ready.copy_to()[0]; }
    std::vector<std::uint32_t> actual;
    { CurrentDevice consumer_context(o.peer); receiver_failure = consumer_error.copy_to()[0]; final_ack = ack.copy_to()[0]; actual = observed.copy_to(); }
    result.valid = producer_failure == 0 && receiver_failure == 0 && final_ready == phases && final_ack == phases && actual == expected;
    result.metrics["producer_error_phase"] = static_cast<double>(producer_failure);
    result.metrics["consumer_error_phase"] = static_cast<double>(receiver_failure);
    if (!result.valid) {
        result.limitations.emplace_back("finite native atomic handshake timed out or failed sequence/payload CPU validation");
        result.configuration["producer_final_ticket"] = std::to_string(final_ready);
        result.configuration["consumer_final_ticket"] = std::to_string(final_ack);
    }
    summarize(result, "complete_handshake", samples);
    if (!peer_access.release()) {
        result.valid = false;
        result.limitations.emplace_back("could not restore process-local peer access enabled by this case");
    }
    return result;
}

Cases run_e19(const Options& o) {
    Cases out;
    if (selected(o, "peer_system_scope_atomic_publication")) out.push_back(run_e19_atomic(o));
    const bool do_event = selected(o, "public_cross_device_event_handshake");
    const bool do_staged = selected(o, "host_staged_completion_handshake");
    if (!do_event && !do_staged) return out;
    std::string reason;
    const bool event_peer_ready = peer_supported(o.device, o.peer, &reason);
    if (do_event && !event_peer_ready) {
        CaseResult unavailable; unavailable.experiment = "E19";
        unavailable.variant = "public_cross_device_event_handshake";
        unavailable.status = reason == "CUDA reports no direct peer access for this directed pair"
            ? "NOT_RUN" : "INCONCLUSIVE";
        unavailable.valid = false;
        unavailable.limitations.push_back(reason);
        out.push_back(std::move(unavailable));
        if (!do_staged) return out;
    }
    CurrentDevice source(o.device);
    Stream src;
    DeviceBuffer<std::uint32_t> marker_src(1);
    ATLAS_CUDA(cudaMemset(marker_src.data(), 0, sizeof(std::uint32_t)));
    Event published(cudaEventDisableTiming);
    CurrentDevice dest(o.peer);
    Stream dst;
    DeviceBuffer<std::uint32_t> marker_dst(1);
    ATLAS_CUDA(cudaMemset(marker_dst.data(), 0, sizeof(std::uint32_t)));
    Event done(cudaEventDisableTiming);
    CaseResult event_case; event_case.experiment = "E19"; event_case.variant = "public_cross_device_event_handshake";
    std::uint32_t src_mark = 0, dst_mark = 0;
    event_case.configuration["device"] = std::to_string(o.device); event_case.configuration["peer"] = std::to_string(o.peer);
    event_case.configuration["protocol"] = "host_enqueues_source_event_then_peer_stream_wait_then_destination_event";
    if (do_event && event_peer_ready) {
        try {
            auto samples = wall_measure(o, [&] {
                {
                    CurrentDevice source_enqueue(o.device);
                    marker_kernel<<<1, 1, 0, src.get()>>>(marker_src.data());
                    ATLAS_CUDA(cudaEventRecord(published.get(), src.get()));
                }
                {
                    CurrentDevice destination_enqueue(o.peer);
                    ATLAS_CUDA(cudaStreamWaitEvent(dst.get(), published.get(), 0));
                    marker_kernel<<<1, 1, 0, dst.get()>>>(marker_dst.data());
                    ATLAS_CUDA(cudaEventRecord(done.get(), dst.get()));
                    ATLAS_CUDA(cudaEventSynchronize(done.get()));
                }
            });
            { CurrentDevice source_copy(o.device); src_mark = marker_src.copy_to()[0]; }
            { CurrentDevice dest_copy(o.peer); dst_mark = marker_dst.copy_to()[0]; }
            event_case.valid = src_mark > 0 && dst_mark > 0;
            if (!event_case.valid) event_case.limitations.emplace_back("event handshake did not complete both local marker kernels");
            event_case.limitations.emplace_back("host wall time includes enqueue and synchronization; cross-device clocks are never subtracted");
            summarize(event_case, "complete_handshake", samples);
            out.push_back(std::move(event_case));
        } catch (const std::exception& e) {
            cudaGetLastError(); event_case.status = "INCONCLUSIVE"; event_case.valid = false;
            event_case.limitations.push_back(std::string("cross-device event wait/record failed: ") + e.what());
            out.push_back(std::move(event_case));
        }
    }
        // Host-staged event baseline; the host observes source completion before publishing to destination.
        CaseResult staged; staged.experiment = "E19"; staged.variant = "host_staged_completion_handshake";
        staged.configuration["device"] = std::to_string(o.device); staged.configuration["peer"] = std::to_string(o.peer);
        staged.configuration["protocol"] = "source_event_synchronize_then_destination_enqueue";
        if (do_staged) {
            try {
                auto staged_samples = wall_measure(o, [&] {
                    {
                        CurrentDevice source_enqueue(o.device);
                        marker_kernel<<<1, 1, 0, src.get()>>>(marker_src.data());
                        ATLAS_CUDA(cudaStreamSynchronize(src.get()));
                    }
                    {
                        CurrentDevice destination_enqueue(o.peer);
                        marker_kernel<<<1, 1, 0, dst.get()>>>(marker_dst.data());
                        ATLAS_CUDA(cudaStreamSynchronize(dst.get()));
                    }
                });
                { CurrentDevice source_copy(o.device); src_mark = marker_src.copy_to()[0]; }
                { CurrentDevice dest_copy(o.peer); dst_mark = marker_dst.copy_to()[0]; }
                staged.valid = src_mark > 0 && dst_mark > 0;
                summarize(staged, "complete_handshake", staged_samples); out.push_back(std::move(staged));
            } catch (const std::exception& e) {
                cudaGetLastError(); staged.status = "INCONCLUSIVE"; staged.valid = false;
                staged.limitations.push_back(std::string("host-staged handshake failed: ") + e.what());
                out.push_back(std::move(staged));
            }
        }
    return out;
}

Cases run_e20(const Options& o) {
    std::string reason;
    if (!peer_supported(o.device, o.peer, &reason)) return {peer_gate_result("E20", "directed_peer_copy", reason)};
    if (!enable_peer(o.device, o.peer, &reason)) return {skip("E20", "directed_peer_copy", reason, "INCONCLUSIVE")};
    if (!enable_peer(o.peer, o.device, &reason)) return {skip("E20", "reverse_peer_copy", reason, "INCONCLUSIVE")};
    const std::size_t n = o.size;
    if (n > std::numeric_limits<std::size_t>::max() / sizeof(std::uint32_t)) throw std::invalid_argument("E20 size overflows");
    const std::size_t bytes = n * sizeof(std::uint32_t);
    std::vector<std::uint32_t> src_data(n), reverse_data(n);
    for (std::size_t i = 0; i < n; ++i) { src_data[i] = pattern(i, o.seed); reverse_data[i] = pattern(i, o.seed ^ 0x9e3779b9u); }
    CurrentDevice source_context(o.device);
    DeviceBuffer<std::uint32_t> src_dev(n), reverse_dest(n);
    src_dev.copy_from(src_data);
    CurrentDevice peer(o.peer);
    DeviceBuffer<std::uint32_t> peer_src(n), peer_dst(n);
    peer_src.copy_from(reverse_data);
    CurrentDevice dev(o.device);
    const auto release_peer_buffers = [&] {
        CurrentDevice cleanup_peer(o.peer);
        peer_src = DeviceBuffer<std::uint32_t>(0);
        peer_dst = DeviceBuffer<std::uint32_t>(0);
    };
    Stream forward;
    Cases out;
    if (selected(o, "directed_peer_copy_one_way")) {
        CaseResult c; c.experiment = "E20"; c.variant = "directed_peer_copy_one_way";
        c.configuration["source"] = std::to_string(o.device); c.configuration["destination"] = std::to_string(o.peer);
        c.configuration["bytes"] = std::to_string(bytes); c.configuration["direction"] = "one_way";
        auto one_way = wall_measure(o, [&] {
            ATLAS_CUDA(cudaMemcpyPeerAsync(peer_dst.data(), o.peer, src_dev.data(), o.device, bytes, forward.get()));
            ATLAS_CUDA(cudaStreamSynchronize(forward.get()));
        });
        std::vector<std::uint32_t> one_actual;
        { CurrentDevice destination(o.peer); one_actual = peer_dst.copy_to(); }
        c.valid = one_actual == src_data;
        if (!c.valid) c.limitations.emplace_back("one-way peer destination does not match source bytes");
        summarize(c, "complete_transfer", one_way);
        const double med = median(one_way);
        c.metrics["payload_GB_per_s"] = med > 0 ? (static_cast<double>(bytes) / 1e6) / med : std::numeric_limits<double>::quiet_NaN();
        out.push_back(std::move(c));
    }
    CurrentDevice peer_ctx(o.peer);
    Stream reverse;
    CurrentDevice dev2(o.device);
    CaseResult bi; bi.experiment = "E20"; bi.variant = "directed_peer_copy_bidirectional";
    bi.configuration["device_a"] = std::to_string(o.device); bi.configuration["device_b"] = std::to_string(o.peer);
    bi.configuration["bytes_per_direction"] = std::to_string(bytes); bi.configuration["direction"] = "simultaneous_two_way";
    if (!selected(o, "directed_peer_copy_bidirectional")) { release_peer_buffers(); return out; }
    auto both = wall_measure(o, [&] {
        ATLAS_CUDA(cudaMemcpyPeerAsync(peer_dst.data(), o.peer, src_dev.data(), o.device, bytes, forward.get()));
        {
            CurrentDevice reverse_device(o.peer);
            ATLAS_CUDA(cudaMemcpyPeerAsync(reverse_dest.data(), o.device, peer_src.data(), o.peer, bytes, reverse.get()));
            ATLAS_CUDA(cudaStreamSynchronize(reverse.get()));
        }
        ATLAS_CUDA(cudaStreamSynchronize(forward.get()));
    });
    std::vector<std::uint32_t> forward_result;
    { CurrentDevice destination(o.peer); forward_result = peer_dst.copy_to(); }
    const auto back = reverse_dest.copy_to();
    bi.valid = forward_result == src_data && back == reverse_data;
    if (!bi.valid) bi.limitations.emplace_back("bidirectional peer destination validation failed");
    summarize(bi, "complete_transfer", both);
    const double bi_med = median(both);
    bi.metrics["aggregate_payload_GB_per_s"] = bi_med > 0 ? (2.0 * static_cast<double>(bytes) / 1e6) / bi_med : std::numeric_limits<double>::quiet_NaN();
    bi.limitations.emplace_back("bandwidth is payload rate; physical NVLink routing requires independent link telemetry");
    out.push_back(std::move(bi));
    release_peer_buffers();
    return out;
}

Cases run_e21(const Options& o) {
#if defined(__linux__) && defined(SYS_get_mempolicy) && defined(SYS_move_pages)
    // Allocate ordinary pages under a temporary thread-local bind policy, touch
    // them there, then restore the exact prior policy before CUDA registration.
    // Query move_pages afterwards; policy intent alone is never accepted as proof.
    const long configured = ::sysconf(_SC_PAGESIZE);
    if (configured <= 0) return {skip("E21", "numa_host_ingress", "OS did not report a valid page size")};
    if (o.size > std::numeric_limits<std::size_t>::max() / sizeof(std::uint32_t))
        return {skip("E21", "numa_host_ingress", "requested buffer size overflows host allocation")};
    const std::size_t bytes = o.size * sizeof(std::uint32_t);
    const std::size_t page = static_cast<std::size_t>(configured);
    if (bytes > std::numeric_limits<std::size_t>::max() - (page - 1))
        return {skip("E21", "numa_host_ingress", "page-rounded host allocation size overflows")};
    const std::size_t alloc_bytes = ((bytes + page - 1) / page) * page;
    DIR* dir = ::opendir("/sys/devices/system/node");
    if (!dir) return {skip("E21", "numa_host_ingress", "cannot inspect OS NUMA node inventory")};
    std::vector<int> nodes;
    while (dirent* entry = ::readdir(dir)) {
        if (std::strncmp(entry->d_name, "node", 4) == 0) {
            char* end = nullptr; long id = std::strtol(entry->d_name + 4, &end, 10);
            if (end && *end == '\0' && id >= 0 && id < 4096) nodes.push_back(static_cast<int>(id));
        }
    }
    ::closedir(dir);
    std::sort(nodes.begin(), nodes.end());
    if (nodes.empty()) return {skip("E21", "numa_host_ingress", "OS reports no NUMA nodes")};
    const unsigned long maxnode = static_cast<unsigned long>(nodes.back() + 1);
    std::vector<unsigned long> oldmask((maxnode + sizeof(unsigned long) * 8 - 1) / (sizeof(unsigned long) * 8), 0);
    int oldmode = 0;
    if (::syscall(SYS_get_mempolicy, &oldmode, oldmask.data(), maxnode, nullptr, 0) != 0)
        return {skip("E21", "numa_host_ingress", "get_mempolicy cannot verify or save current thread policy")};
    Cases out;
    for (int node : nodes) {
        if (node >= static_cast<int>(maxnode)) continue;
        std::vector<unsigned long> mask(oldmask.size(), 0);
        mask[static_cast<std::size_t>(node) / (sizeof(unsigned long) * 8)] |= 1ul << (node % (sizeof(unsigned long) * 8));
        if (::syscall(SYS_set_mempolicy, MPOL_BIND, mask.data(), maxnode) != 0) {
            out.push_back(skip("E21", "numa_node_" + std::to_string(node), std::string("set_mempolicy bind unavailable: ") + std::strerror(errno)));
            continue;
        }
        void* memory = nullptr;
        if (::posix_memalign(&memory, page, alloc_bytes) != 0) {
            ::syscall(SYS_set_mempolicy, oldmode, oldmask.data(), maxnode);
            out.push_back(skip("E21", "numa_node_" + std::to_string(node), "aligned host allocation failed"));
            continue;
        }
        std::memset(memory, 0, alloc_bytes); // first-touch while temporary bind is active
        const int restore_rc = static_cast<int>(::syscall(SYS_set_mempolicy, oldmode, oldmask.data(), maxnode));
        if (restore_rc != 0) { std::free(memory); throw std::runtime_error("failed to restore saved NUMA policy"); }
        if (cudaHostRegister(memory, alloc_bytes, cudaHostRegisterPortable) != cudaSuccess) {
            const std::string err = cudaGetErrorString(cudaGetLastError()); std::free(memory);
            out.push_back(skip("E21", "numa_node_" + std::to_string(node), "cudaHostRegister failed: " + err));
            continue;
        }
        const std::size_t page_count = alloc_bytes / page;
        std::vector<void*> page_addrs(page_count);
        std::vector<int> placement(page_count, -1);
        for (std::size_t i = 0; i < page_count; ++i) page_addrs[i] = static_cast<char*>(memory) + i * page;
        const long query = ::syscall(SYS_move_pages, 0, page_count, page_addrs.data(), nullptr, placement.data(), 0);
        if (query != 0 || std::any_of(placement.begin(), placement.end(), [node](int got) { return got != node; })) {
            cudaHostUnregister(memory); std::free(memory);
            out.push_back(skip("E21", "numa_node_" + std::to_string(node), query != 0
                ? std::string("move_pages placement query denied/unavailable: ") + std::strerror(errno)
                : "observed page placement differs from requested NUMA node"));
            continue;
        }
        CaseResult c; c.experiment = "E21"; c.variant = "verified_numa_node_" + std::to_string(node) + "_to_gpu_" + std::to_string(o.device);
        c.configuration["numa_node"] = std::to_string(node); c.configuration["gpu"] = std::to_string(o.device);
        c.configuration["bytes"] = std::to_string(bytes); c.configuration["placement"] = "all_pages_move_pages_verified";
        auto* values = static_cast<std::uint32_t*>(memory);
        for (std::size_t i = 0; i < o.size; ++i) values[i] = pattern(i, o.seed);
        try {
            CurrentDevice device(o.device);
            DeviceBuffer<std::uint32_t> gpu(o.size);
            Stream stream;
            auto samples = wall_measure(o, [&] {
                ATLAS_CUDA(cudaMemcpyAsync(gpu.data(), memory, bytes, cudaMemcpyHostToDevice, stream.get()));
                ATLAS_CUDA(cudaStreamSynchronize(stream.get()));
            });
            const auto actual = gpu.copy_to();
            c.valid = actual.size() == o.size;
            for (std::size_t i = 0; i < o.size && c.valid; ++i) if (actual[i] != pattern(i, o.seed)) c.valid = false;
            if (!c.valid) c.limitations.emplace_back("pinned host ingress differs from deterministic host bytes");
            summarize(c, "h2d", samples);
        } catch (...) { cudaHostUnregister(memory); std::free(memory); throw; }
        cudaHostUnregister(memory); std::free(memory); out.push_back(std::move(c));
    }
    if (out.empty()) return {skip("E21", "numa_host_ingress", "no NUMA node allowed verified pinned allocation")};
    return out;
#else
    (void)o;
    return {skip("E21", "numa_host_ingress", "Linux get_mempolicy/move_pages verification APIs are unavailable in this build")};
#endif
}

Cases run_e32(const Options& o) {
    CurrentDevice device(o.device);
    const std::size_t n = o.size;
    if (n > std::numeric_limits<std::size_t>::max() / sizeof(std::uint32_t)) throw std::invalid_argument("E32 size overflows allocation");
    std::vector<std::uint32_t> input(n);
    for (std::size_t i = 0; i < n; ++i) input[i] = pattern(i, o.seed);
    DeviceBuffer<std::uint32_t> a(n);
    a.copy_from(input);
    const int stages = std::max(1, std::min(o.iterations, 64));
    Stream stream;
    auto host_pipeline = [&] {
        for (int i = 0; i < stages; ++i) increment_inplace_kernel<<<blocks(n), 256, 0, stream.get()>>>(a.data(), n);
    };
    const std::uint32_t increment = static_cast<std::uint32_t>(stages);
    Cases out;
    const int timed_runs = o.verify_only ? 1 : std::max(0, o.warmup) + std::max(1, o.repeats);

    if (selected(o, "host_enqueued_kernel_pipeline")) {
        a.copy_from(input);
        CaseResult host; host.experiment = "E32"; host.variant = "host_enqueued_kernel_pipeline";
        host.configuration["device"] = std::to_string(o.device); host.configuration["elements"] = std::to_string(n);
        host.configuration["stages"] = std::to_string(stages); host.configuration["submission"] = "host_loop_same_stream_no_interstage_sync";
        auto samples = measure(o, host_pipeline, stream.get());
        const auto actual = a.copy_to(); host.valid = true;
        for (std::size_t i = 0; i < n && host.valid; ++i)
            if (actual[i] != input[i] + increment * static_cast<std::uint32_t>(timed_runs)) host.valid = false;
        if (!host.valid) host.limitations.emplace_back("host pipeline result differs from exact repeated-increment oracle");
        summarize(host, "pipeline", samples); out.push_back(std::move(host));
    }

    if (selected(o, "cuda_graph_replay_pipeline")) {
        a.copy_from(input);
        cudaGraph_t graph = nullptr; cudaGraphExec_t executable = nullptr;
        try {
            ATLAS_CUDA(cudaStreamBeginCapture(stream.get(), cudaStreamCaptureModeThreadLocal));
            for (int i = 0; i < stages; ++i) increment_inplace_kernel<<<blocks(n), 256, 0, stream.get()>>>(a.data(), n);
            ATLAS_CUDA(cudaStreamEndCapture(stream.get(), &graph));
            ATLAS_CUDA(cudaGraphInstantiate(&executable, graph, nullptr, nullptr, 0));
            CaseResult gc; gc.experiment = "E32"; gc.variant = "cuda_graph_replay_pipeline";
            gc.configuration["device"] = std::to_string(o.device); gc.configuration["elements"] = std::to_string(n);
            gc.configuration["stages"] = std::to_string(stages); gc.configuration["submission"] = "instantiated_cuda_graph_replay";
            auto samples = measure(o, [&] { ATLAS_CUDA(cudaGraphLaunch(executable, stream.get())); }, stream.get());
            const auto actual = a.copy_to(); gc.valid = true;
            for (std::size_t i = 0; i < n && gc.valid; ++i)
                if (actual[i] != input[i] + increment * static_cast<std::uint32_t>(timed_runs)) gc.valid = false;
            if (!gc.valid) gc.limitations.emplace_back("graph pipeline result differs from exact repeated-increment oracle");
            summarize(gc, "pipeline", samples); out.push_back(std::move(gc));
        } catch (...) {
            if (executable) cudaGraphExecDestroy(executable);
            if (graph) cudaGraphDestroy(graph);
            throw;
        }
        if (executable) ATLAS_CUDA(cudaGraphExecDestroy(executable));
        if (graph) ATLAS_CUDA(cudaGraphDestroy(graph));
    }

    if (selected(o, "device_side_child_launch_pipeline")) {
#if !defined(ATLAS_ENABLE_CDP)
        out.push_back(skip("E32", "device_side_child_launch_pipeline",
            "NOT_RUN: CUDA Dynamic Parallelism is built as a separate executable so race/synchronization tools can analyze ordinary variants"));
#else
        int major = 0, compute_mode = 0;
        ATLAS_CUDA(cudaDeviceGetAttribute(&major, cudaDevAttrComputeCapabilityMajor, o.device));
        ATLAS_CUDA(cudaDeviceGetAttribute(&compute_mode, cudaDevAttrComputeMode, o.device));
        if (major < 3 || compute_mode == cudaComputeModeProhibited) {
            out.push_back(skip("E32", "device_side_child_launch_pipeline",
                major < 3 ? "device compute capability does not support CUDA Dynamic Parallelism"
                          : "device compute mode prohibits kernel execution"));
        } else {
            a.copy_from(input);
            DeviceBuffer<int> child_error(1);
            ATLAS_CUDA(cudaMemset(child_error.data(), 0, sizeof(int)));
            CaseResult cdp; cdp.experiment = "E32"; cdp.variant = "device_side_child_launch_pipeline";
            cdp.configuration["device"] = std::to_string(o.device); cdp.configuration["elements"] = std::to_string(n);
            cdp.configuration["stages"] = std::to_string(stages);
            cdp.configuration["submission"] = "one_parent_CTA_launches_ordered_finite_child_grids_in_one_device_stream";
            auto samples = measure(o, [&] {
                ATLAS_CUDA(cudaMemsetAsync(child_error.data(), 0, sizeof(int), stream.get()));
                cdp_stage_parent<<<1, 1, 0, stream.get()>>>(a.data(), n, stages, child_error.data());
                ATLAS_CUDA(cudaGetLastError());
            }, stream.get());
            const auto actual = a.copy_to(); const int device_error = child_error.copy_to()[0];
            cdp.valid = device_error == 0;
            for (std::size_t i = 0; i < n && cdp.valid; ++i)
                if (actual[i] != input[i] + increment * static_cast<std::uint32_t>(timed_runs)) cdp.valid = false;
            cdp.metrics["device_launch_error"] = static_cast<double>(device_error);
            if (!cdp.valid) cdp.limitations.emplace_back("child-launch pipeline failed launch status or exact repeated-increment CPU oracle");
            summarize(cdp, "pipeline", samples); out.push_back(std::move(cdp));
        }
#endif
    }
    if (out.empty()) throw std::invalid_argument("unknown E32 transport variant requested");
    return out;
}

} // namespace

Cases run_transport(const Options& options) {
    if (options.experiment == "E17") return run_e17(options);
    if (options.experiment == "E18") return run_e18(options);
    if (options.experiment == "E19") return run_e19(options);
    if (options.experiment == "E20") return run_e20(options);
    if (options.experiment == "E21") return run_e21(options);
    if (options.experiment == "E32") return run_e32(options);
    throw std::invalid_argument("transport module supports E17-E21 and E32");
}

} // namespace atlas

int main(int argc, char** argv) { return atlas::main(argc, argv, atlas::run_transport); }
