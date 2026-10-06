#include "common.hpp"

#include <cuda.h>
#include <cuda/atomic>
#include <cooperative_groups.h>

#include <cstdint>
#include <limits>
#include <numeric>
#include <random>
#include <thread>

namespace cg = cooperative_groups;

namespace {

void cu_check(CUresult r, const char* what) {
    if (r == CUDA_SUCCESS) return;
    const char* name = nullptr;
    const char* message = nullptr;
    cuGetErrorName(r, &name);
    cuGetErrorString(r, &message);
    throw std::runtime_error(std::string(what) + ": " + (name ? name : "CUDA_ERROR") +
                             " (" + (message ? message : "unknown") + ")");
}

bool event_wait_bounded(cudaEvent_t event, double timeout_seconds = 30.0) {
    const auto deadline = std::chrono::steady_clock::now() +
                          std::chrono::duration<double>(timeout_seconds);
    for (;;) {
        const cudaError_t status = cudaEventQuery(event);
        if (status == cudaSuccess) return true;
        if (status != cudaErrorNotReady) ATLAS_CUDA(status);
        if (std::chrono::steady_clock::now() >= deadline) return false;
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}

template <class T>
void summarize(atlas::CaseResult& result, const std::vector<T>& values,
               const char* key = "latency_ms") {
    std::vector<double> raw(values.begin(), values.end());
    if (raw.empty()) return;
    std::vector<double> sorted = raw;
    std::sort(sorted.begin(), sorted.end());
    result.samples[key] = std::move(raw);
    const std::size_t middle = sorted.size() / 2;
    result.metrics[std::string(key) + "_median"] = sorted.size() % 2
        ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) * 0.5;
    const std::size_t p95 = (95 * sorted.size() + 99) / 100 - 1; // nearest rank: ceil(.95*n)-1
    result.metrics[std::string(key) + "_p95"] = sorted[p95];
}

__global__ void zero_u64(unsigned long long* p, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) p[i] = 0;
}

__global__ void atomic_each(unsigned long long* total, int count) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) atomicAdd(total, 1ULL);
}

// Volta supports match.sync. Each equal-key group emits one atomic update.
__global__ void atomic_warp_aggregate(unsigned long long* total, int count) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    const unsigned active = __ballot_sync(0xffffffffu, i < count);
    if (i >= count) return;
    const unsigned peers = __match_any_sync(active, 0); // controlled hot-line contention
    if ((threadIdx.x & 31) == __ffs(peers) - 1)
        atomicAdd(total, static_cast<unsigned long long>(__popc(peers)));
}

__global__ void atomic_spread(unsigned long long* bins, int count, int bin_count) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) atomicAdd(&bins[i % bin_count], 1ULL);
}

struct Published {
    unsigned long long payload;
    unsigned int epoch;
    int error;
};

// E15 legal publication litmus. The slot has one writer and one reader.
// Payload is stored before a device-scope release publication; the reader's
// matching device-scope acquire precedes its payload read. Reuse is avoided
// for the whole launch, so no overwrite/reclamation race is present.
// Progress argument: the cooperative launch is limited to the queried number
// of simultaneously resident blocks, so both CTAs are admitted at launch.
// There is no grid barrier and no wait on a CTA that has not been admitted.
// Producer work is finite; consumer polling is bounded by max_polls and has an
// explicit timeout result. This establishes a schedulable stop path and rules
// out oversubscribed-spin deadlock. The argument does not assume fairness for
// an unadmitted block, nor does stress testing replace the ordering proof.
__global__ void publication_litmus(Published* state, unsigned long long payload,
                                  unsigned int epoch, unsigned long long max_polls) {
    const int role = static_cast<int>(blockIdx.x);
    if (role == 0 && threadIdx.x == 0) {
        for (int i = 0; i < 64; ++i) asm volatile("" ::: "memory");
        state->payload = payload;
        cuda::atomic_ref<unsigned int, cuda::thread_scope_device> published(state->epoch);
        published.store(epoch, cuda::memory_order_release);
    } else if (role == 1 && threadIdx.x == 0) {
        cuda::atomic_ref<unsigned int, cuda::thread_scope_device> published(state->epoch);
        unsigned long long polls = 0;
        while (published.load(cuda::memory_order_acquire) != epoch && polls < max_polls)
            ++polls;
        if (polls == max_polls) state->error = 1;
        else if (state->payload != payload) state->error = 2;
    }
}

__global__ void publish_phase(Published* state, unsigned long long payload) {
    if (blockIdx.x == 0 && threadIdx.x == 0) {
        state->payload = payload;
        state->epoch = 1;
    }
}

__global__ void consume_phase(const Published* state, unsigned long long expected, int* error) {
    if (blockIdx.x == 0 && threadIdx.x == 0)
        *error = (state->epoch == 1 && state->payload == expected) ? 0 : 1;
}

__global__ void resident_work(unsigned long long* out, int tasks, int rounds,
                              int* stopped) {
    cg::grid_group grid = cg::this_grid();
    const int tid = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = gridDim.x * blockDim.x;
    for (int r = 0; r < rounds; ++r) {
        for (int task = tid + r * total; task < tasks; task += rounds * total)
            atomicAdd(out + (task & 255), static_cast<unsigned long long>(task + 1));
        grid.sync();
    }
    if (tid == 0) *stopped = 1; // explicit stop after all work is drained
}

__global__ void batched_work(unsigned long long* out, int tasks) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < tasks) atomicAdd(out + (i & 255), static_cast<unsigned long long>(i + 1));
}

__global__ void memop_consume32(const unsigned int* flag, unsigned int expected, int* error) {
    if (blockIdx.x == 0 && threadIdx.x == 0) *error = (*flag == expected) ? 0 : 1;
}

__global__ void memop_consume64(const unsigned long long* flag,
                                unsigned long long expected, int* error) {
    if (blockIdx.x == 0 && threadIdx.x == 0) *error = (*flag == expected) ? 0 : 1;
}

__global__ void memop_write32(unsigned int* flag, unsigned int value) {
    if (blockIdx.x == 0 && threadIdx.x == 0) *flag = value;
}

__global__ void phase_serial_grid(const int* input, int* output, int n) {
    // Small one-CTA implementation: avoids scheduling a large grid for short phases.
    for (int i = threadIdx.x; i < n; i += blockDim.x) output[i] = input[i] + 3;
}

__global__ void phase_parallel_grid(const int* input, int* output, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) output[i] = input[i] + 3;
}

} // namespace

namespace atlas {

Cases run_sync(const Options& o) {
    ATLAS_CUDA(cudaSetDevice(o.device));
    const std::string selected = o.experiment;
    const auto wants = [&](const char* id) { return selected == id || selected == "all"; };
    Cases cases;

    if (wants("E14")) {
        const int n = static_cast<int>(std::min<std::size_t>(o.size, 1u << 24));
        const int blocks = (n + 255) / 256;
        for (const std::string variant : {"contended_atomic", "warp_aggregated", "spread_16"}) {
            DeviceBuffer<unsigned long long> bins(variant == "spread_16" ? 16 : 1);
            auto launch = [&] {
                zero_u64<<<(static_cast<int>(bins.size()) + 255) / 256, 256>>>(
                    bins.data(), static_cast<int>(bins.size()));
                if (variant == "contended_atomic") atomic_each<<<blocks, 256>>>(bins.data(), n);
                else if (variant == "warp_aggregated") atomic_warp_aggregate<<<blocks, 256>>>(bins.data(), n);
                else atomic_spread<<<blocks, 256>>>(bins.data(), n, 16);
            };
            auto samples = measure(o, launch);
            launch(); // verify the final measured variant's complete counter state
            auto values = bins.copy_to();
            const unsigned long long sum = std::accumulate(values.begin(), values.end(), 0ULL);
            CaseResult r;
            r.experiment = "E14"; r.variant = variant;
            r.configuration["updates"] = std::to_string(n);
            r.configuration["semantic_contract"] = "one exact +1 completion per input";
            const int estimated_transactions = variant == "warp_aggregated" ?
                (n + 31) / 32 : n;
            r.configuration["transaction_count"] = "estimated from implementation structure; verify with profiler";
            r.metrics["estimated_atomic_transactions"] = estimated_transactions;
            r.metrics["useful_updates_per_atomic"] = static_cast<double>(n) / estimated_transactions;
            r.metrics["completed_updates"] = static_cast<double>(sum);
            r.valid = sum == static_cast<unsigned long long>(n);
            summarize(r, samples);
            cases.push_back(std::move(r));
        }
    }

    if (wants("E15")) {
        int coop = 0, multiprocessors = 0, active_per_sm = 0;
        ATLAS_CUDA(cudaDeviceGetAttribute(&coop, cudaDevAttrCooperativeLaunch, o.device));
        ATLAS_CUDA(cudaDeviceGetAttribute(&multiprocessors, cudaDevAttrMultiProcessorCount, o.device));
        ATLAS_CUDA(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&active_per_sm,
                    publication_litmus, 128, 0));
        if (!coop || active_per_sm * multiprocessors < 2) {
            cases.push_back(skip("E15", "release_acquire_cooperative",
                !coop ? "device reports cooperative launch unsupported" :
                "occupancy query admits fewer than two resident blocks"));
        } else {
            DeviceBuffer<Published> state(1);
            const unsigned long long expected = 0x91e10da5c79e7b1dULL ^ o.seed;
            const unsigned int epoch = 1;
            const unsigned long long poll_bound = static_cast<unsigned long long>(
                std::max(100000, o.integer("polls", 50000000)));
            auto litmus = [&] {
                const Published init{0ULL, 0U, 0};
                state.copy_from(std::vector<Published>{init});
                Published* state_ptr = state.data();
                unsigned long long payload_arg = expected;
                unsigned int epoch_arg = epoch;
                unsigned long long poll_arg = poll_bound;
                void* args[] = {&state_ptr, &payload_arg, &epoch_arg, &poll_arg};
                const dim3 grid(2), block(128);
                ATLAS_CUDA(cudaLaunchCooperativeKernel(reinterpret_cast<void*>(publication_litmus),
                    grid, block, args, 0, nullptr));
            };
            auto litmus_samples = measure(o, litmus);
            const auto check = state.copy_to()[0];
            CaseResult r; r.experiment = "E15"; r.variant = "release_acquire_cooperative";
            r.configuration["producer_consumer"] = "two admitted cooperative CTAs; one slot; no reuse";
            r.configuration["poll_bound"] = std::to_string(poll_bound);
            r.configuration["progress_proof"] = "admitted grid, finite producer, bounded consumer, no unadmitted dependency";
            r.metrics["poll_timeout"] = check.error == 1 ? 1.0 : 0.0;
            r.metrics["payload_mismatch"] = check.error == 2 ? 1.0 : 0.0;
            r.metrics["occupancy_blocks"] = active_per_sm * multiprocessors;
            r.valid = check.error == 0 && check.payload == expected && check.epoch == epoch;
            summarize(r, litmus_samples); cases.push_back(std::move(r));

            DeviceBuffer<int> error(1);
            cudaStream_t producer = nullptr, consumer = nullptr;
            ATLAS_CUDA(cudaStreamCreateWithFlags(&producer, cudaStreamNonBlocking));
            ATLAS_CUDA(cudaStreamCreateWithFlags(&consumer, cudaStreamNonBlocking));
            cudaEvent_t ready = nullptr, done = nullptr;
            ATLAS_CUDA(cudaEventCreateWithFlags(&ready, cudaEventDisableTiming));
            ATLAS_CUDA(cudaEventCreateWithFlags(&done, cudaEventDisableTiming));
            auto phased = [&] {
                publish_phase<<<1, 1, 0, producer>>>(state.data(), expected);
                ATLAS_CUDA(cudaEventRecord(ready, producer));
                ATLAS_CUDA(cudaStreamWaitEvent(consumer, ready, 0));
                consume_phase<<<1, 1, 0, consumer>>>(state.data(), expected, error.data());
                ATLAS_CUDA(cudaEventRecord(done, consumer));
                if (!event_wait_bounded(done))
                    throw std::runtime_error("E15 event-phased baseline exceeded 30-second host wait deadline");
                ATLAS_CUDA(cudaGetLastError());
            };
            phased();
            CaseResult b; b.experiment = "E15"; b.variant = "event_phased_baseline";
            b.configuration["ordering"] = "producer event recorded; consumer stream waits before payload read";
            summarize(b, wall_measure(o, phased, consumer));
            b.valid = error.copy_to()[0] == 0; // check the final measured sample
            cases.push_back(std::move(b));
            cudaEventDestroy(done); cudaEventDestroy(ready); cudaStreamDestroy(consumer); cudaStreamDestroy(producer);
        }
    }

    if (wants("E16")) {
        const int tasks = static_cast<int>(std::min<std::size_t>(o.size, 1u << 20));
        const int rounds = std::max(1, o.iterations);
        int coop = 0, sm = 0, active = 0;
        ATLAS_CUDA(cudaDeviceGetAttribute(&coop, cudaDevAttrCooperativeLaunch, o.device));
        ATLAS_CUDA(cudaDeviceGetAttribute(&sm, cudaDevAttrMultiProcessorCount, o.device));
        const int threads = 128;
        ATLAS_CUDA(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&active, resident_work, threads, 0));
        DeviceBuffer<unsigned long long> output(256);
        DeviceBuffer<int> stopped(1);
        const int grid_blocks = std::min(std::max(1, (tasks + threads - 1) / threads),
                                         std::max(1, active * sm));
        if (!coop || grid_blocks > active * sm) {
            cases.push_back(skip("E16", "cooperative_resident",
                !coop ? "device reports cooperative launch unsupported" :
                        "requested grid exceeds cooperative occupancy admission"));
        } else {
            auto resident = [&] {
                ATLAS_CUDA(cudaMemset(output.data(), 0, 256 * sizeof(unsigned long long)));
                ATLAS_CUDA(cudaMemset(stopped.data(), 0, sizeof(int)));
                unsigned long long* output_ptr = output.data();
                int* stopped_ptr = stopped.data();
                int tasks_arg = tasks, rounds_arg = rounds;
                void* args[] = {&output_ptr, &tasks_arg, &rounds_arg, &stopped_ptr};
                ATLAS_CUDA(cudaLaunchCooperativeKernel(reinterpret_cast<void*>(resident_work),
                    dim3(grid_blocks), dim3(threads), args, 0, nullptr));
            };
            resident();
            auto got = output.copy_to();
            const unsigned long long expected = static_cast<unsigned long long>(tasks) * (tasks + 1ULL) / 2ULL;
            const unsigned long long sum = std::accumulate(got.begin(), got.end(), 0ULL);
            CaseResult r; r.experiment = "E16"; r.variant = "cooperative_resident";
            r.configuration["tasks"] = std::to_string(tasks); r.configuration["rounds"] = std::to_string(rounds);
            r.configuration["termination"] = "all assigned tasks drained; kernel exits after final grid phase";
            r.metrics["admitted_blocks"] = grid_blocks; r.metrics["stopped"] = stopped.copy_to()[0];
            r.metrics["sum"] = static_cast<double>(sum); r.valid = sum == expected && stopped.copy_to()[0] == 1;
            summarize(r, measure(o, resident)); cases.push_back(std::move(r));
        }

        DeviceBuffer<unsigned long long> batched(256);
        const int batch_grid = (tasks + threads - 1) / threads;
        auto batch = [&] {
            ATLAS_CUDA(cudaMemset(batched.data(), 0, 256 * sizeof(unsigned long long)));
            batched_work<<<batch_grid, threads>>>(batched.data(), tasks);
        };
        batch();
        const auto batch_values = batched.copy_to();
        auto batch_sum = std::accumulate(batch_values.begin(), batch_values.end(), 0ULL);
        const unsigned long long expected = static_cast<unsigned long long>(tasks) * (tasks + 1ULL) / 2ULL;
        CaseResult b; b.experiment = "E16"; b.variant = "batched";
        b.configuration["termination"] = "one finite kernel per batch; no global spin barrier";
        b.metrics["sum"] = static_cast<double>(batch_sum); b.valid = batch_sum == expected;
        summarize(b, measure(o, batch)); cases.push_back(std::move(b));

        cudaStream_t stream = nullptr; ATLAS_CUDA(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking));
        cudaGraph_t graph = nullptr; cudaGraphExec_t executable = nullptr;
        try {
            ATLAS_CUDA(cudaStreamBeginCapture(stream, cudaStreamCaptureModeThreadLocal));
            ATLAS_CUDA(cudaMemsetAsync(batched.data(), 0, 256 * sizeof(unsigned long long), stream));
            batched_work<<<batch_grid, threads, 0, stream>>>(batched.data(), tasks);
            ATLAS_CUDA(cudaStreamEndCapture(stream, &graph));
            ATLAS_CUDA(cudaGraphInstantiate(&executable, graph, nullptr, nullptr, 0));
            auto graph_launch = [&] { ATLAS_CUDA(cudaGraphLaunch(executable, stream)); };
            graph_launch(); ATLAS_CUDA(cudaStreamSynchronize(stream));
            auto graph_values = batched.copy_to();
            const auto graph_sum = std::accumulate(graph_values.begin(), graph_values.end(), 0ULL);
            CaseResult g; g.experiment = "E16"; g.variant = "graph_replay";
            g.configuration["termination"] = "captured memset plus finite batch kernel";
            g.metrics["sum"] = static_cast<double>(graph_sum); g.valid = graph_sum == expected;
            summarize(g, measure(o, graph_launch, stream)); cases.push_back(std::move(g));
        } catch (...) {
            if (executable) cudaGraphExecDestroy(executable);
            if (graph) cudaGraphDestroy(graph);
            cudaStreamDestroy(stream);
            throw;
        }
        if (executable) cudaGraphExecDestroy(executable);
        if (graph) cudaGraphDestroy(graph);
        cudaStreamDestroy(stream);
    }

    if (wants("E22")) {
        cu_check(cuInit(0), "cuInit");
        CUdevice dev; cu_check(cuDeviceGet(&dev, o.device), "cuDeviceGet");
        int legacy_memops32 = 0, legacy_memops64 = 0, current_memops64 = 0;
        cu_check(cuDeviceGetAttribute(&legacy_memops32, CU_DEVICE_ATTRIBUTE_CAN_USE_STREAM_MEM_OPS_V1, dev), "legacy stream mem-op capability query");
        cu_check(cuDeviceGetAttribute(&legacy_memops64, CU_DEVICE_ATTRIBUTE_CAN_USE_64_BIT_STREAM_MEM_OPS_V1, dev), "legacy 64-bit stream mem-op capability query");
        cu_check(cuDeviceGetAttribute(&current_memops64, CU_DEVICE_ATTRIBUTE_CAN_USE_64_BIT_STREAM_MEM_OPS, dev), "current 64-bit stream mem-op capability query");
        // CUDA 12.9 has no current generic 32-bit capability attribute. The
        // public unsuffixed API macros resolve to the current v2 entry points;
        // a documented CUDA_ERROR_NOT_SUPPORTED result is the truthful gate.
        {
            unsigned int* flag = nullptr; int* error = nullptr;
            ATLAS_CUDA(cudaMalloc(reinterpret_cast<void**>(&flag), sizeof(*flag)));
            ATLAS_CUDA(cudaMalloc(reinterpret_cast<void**>(&error), sizeof(*error)));
            cudaStream_t writer = nullptr, waiter = nullptr;
            ATLAS_CUDA(cudaStreamCreateWithFlags(&writer, cudaStreamNonBlocking));
            ATLAS_CUDA(cudaStreamCreateWithFlags(&waiter, cudaStreamNonBlocking));
            cudaEvent_t memop_ready = nullptr, memop_done = nullptr;
            ATLAS_CUDA(cudaEventCreateWithFlags(&memop_ready, cudaEventDisableTiming));
            ATLAS_CUDA(cudaEventCreateWithFlags(&memop_done, cudaEventDisableTiming));
            constexpr unsigned int target = 0x51a7u;
            auto memop32 = [&]() -> bool {
                ATLAS_CUDA(cudaMemsetAsync(flag, 0, sizeof(*flag), writer));
                const CUresult write_status = cuStreamWriteValue32(reinterpret_cast<CUstream>(writer),
                    reinterpret_cast<CUdeviceptr>(flag), target, 0);
                if (write_status == CUDA_ERROR_NOT_SUPPORTED) return false;
                cu_check(write_status, "cuStreamWriteValue32_v2");
                // Stream-memop dependencies are invisible to CUDA's scheduler.
                // Publish an explicit CUDA-visible event edge before enqueueing
                // the value wait; the experiment therefore measures an already-
                // published value wait, including this event overhead.
                ATLAS_CUDA(cudaEventRecord(memop_ready, writer));
                ATLAS_CUDA(cudaStreamWaitEvent(waiter, memop_ready, 0));
                const CUresult wait_status = cuStreamWaitValue32(reinterpret_cast<CUstream>(waiter),
                    reinterpret_cast<CUdeviceptr>(flag), target, CU_STREAM_WAIT_VALUE_EQ);
                if (wait_status == CUDA_ERROR_NOT_SUPPORTED) return false;
                cu_check(wait_status, "cuStreamWaitValue32_v2");
                memop_consume32<<<1, 1, 0, waiter>>>(flag, target, error);
                ATLAS_CUDA(cudaEventRecord(memop_done, waiter));
                if (!event_wait_bounded(memop_done))
                    throw std::runtime_error("E22 32-bit stream memory handshake exceeded 30-second host wait deadline");
                return true;
            };
            const bool supported32 = memop32();
            if (!supported32) {
                std::ostringstream reason;
                reason << "CUDA 12.9 v2 32-bit stream-memory operation returned CUDA_ERROR_NOT_SUPPORTED (legacy V1 capability="
                       << legacy_memops32 << ", legacy 64-bit V1 capability=" << legacy_memops64
                       << ", current 64-bit capability=" << current_memops64
                       << "); no current generic 32-bit capability attribute exists";
                cases.push_back(skip("E22", "stream_memop_32", reason.str()));
            } else {
                CaseResult r; r.experiment = "E22"; r.variant = "stream_memop_32";
                r.configuration["allocation"] = "cudaMalloc device memory; managed memory excluded";
                r.configuration["api"] = "cuStreamWriteValue32_v2/cuStreamWaitValue32_v2";
                r.configuration["legacy_v1_capability"] = std::to_string(legacy_memops32);
                r.configuration["legacy_v1_64_bit_capability"] = std::to_string(legacy_memops64);
                r.configuration["current_64_bit_capability"] = std::to_string(current_memops64);
                r.configuration["ordering"] = "writer event then CUDA-visible waiter event edge, followed by wait on already-published equality value";
                int host_error = 1; ATLAS_CUDA(cudaMemcpy(&host_error, error, sizeof(int), cudaMemcpyDeviceToHost));
                r.valid = host_error == 0;
                auto checked_memop32 = [&] {
                    if (!memop32()) throw std::runtime_error("E22 v2 32-bit stream memory operation became unsupported during measurement");
                };
                auto memop32_samples = wall_measure(o, checked_memop32, waiter);
                ATLAS_CUDA(cudaMemcpy(&host_error, error, sizeof(int), cudaMemcpyDeviceToHost));
                r.valid = r.valid && host_error == 0;
                summarize(r, memop32_samples); cases.push_back(std::move(r));
            }

            cudaEvent_t ready = nullptr, done = nullptr;
            ATLAS_CUDA(cudaEventCreateWithFlags(&ready, cudaEventDisableTiming));
            ATLAS_CUDA(cudaEventCreateWithFlags(&done, cudaEventDisableTiming));
            auto event32 = [&] {
                ATLAS_CUDA(cudaMemsetAsync(flag, 0, sizeof(*flag), writer));
                memop_write32<<<1, 1, 0, writer>>>(flag, target);
                ATLAS_CUDA(cudaEventRecord(ready, writer));
                ATLAS_CUDA(cudaStreamWaitEvent(waiter, ready, 0));
                memop_consume32<<<1, 1, 0, waiter>>>(flag, target, error);
                ATLAS_CUDA(cudaEventRecord(done, waiter));
                if (!event_wait_bounded(done))
                    throw std::runtime_error("E22 event baseline exceeded 30-second host wait deadline");
            };
            event32(); int baseline_error = 1;
            ATLAS_CUDA(cudaMemcpy(&baseline_error, error, sizeof(int), cudaMemcpyDeviceToHost));
            CaseResult baseline; baseline.experiment = "E22"; baseline.variant = "event_baseline_32";
            baseline.configuration["ordering"] = "producer kernel completion visible through CUDA event dependency";
            baseline.configuration["legacy_v1_capability"] = std::to_string(legacy_memops32);
            baseline.configuration["legacy_v1_64_bit_capability"] = std::to_string(legacy_memops64);
            baseline.configuration["current_64_bit_capability"] = std::to_string(current_memops64);
            baseline.valid = baseline_error == 0;
            summarize(baseline, wall_measure(o, event32, waiter)); cases.push_back(std::move(baseline));
            cudaEventDestroy(done); cudaEventDestroy(ready);
            cudaEventDestroy(memop_done); cudaEventDestroy(memop_ready);
            cudaStreamDestroy(waiter); cudaStreamDestroy(writer); cudaFree(error); cudaFree(flag);
        }
        if (!current_memops64) {
            cases.push_back(skip("E22", "stream_memop_64",
                "CUDA driver reports current CAN_USE_64_BIT_STREAM_MEM_OPS=0 (legacy V1 capability=" +
                std::to_string(legacy_memops64) + ")"));
        } else {
            unsigned long long* flag = nullptr; int* error = nullptr;
            ATLAS_CUDA(cudaMalloc(reinterpret_cast<void**>(&flag), sizeof(*flag)));
            ATLAS_CUDA(cudaMalloc(reinterpret_cast<void**>(&error), sizeof(*error)));
            cudaStream_t writer = nullptr, waiter = nullptr;
            ATLAS_CUDA(cudaStreamCreateWithFlags(&writer, cudaStreamNonBlocking));
            ATLAS_CUDA(cudaStreamCreateWithFlags(&waiter, cudaStreamNonBlocking));
            cudaEvent_t memop_ready = nullptr, memop_done = nullptr;
            ATLAS_CUDA(cudaEventCreateWithFlags(&memop_ready, cudaEventDisableTiming));
            ATLAS_CUDA(cudaEventCreateWithFlags(&memop_done, cudaEventDisableTiming));
            constexpr unsigned long long target = 0x100000051a7ULL;
            auto memop64 = [&]() -> bool {
                ATLAS_CUDA(cudaMemsetAsync(flag, 0, sizeof(*flag), writer));
                const CUresult write_status = cuStreamWriteValue64(reinterpret_cast<CUstream>(writer), reinterpret_cast<CUdeviceptr>(flag), target, 0);
                if (write_status == CUDA_ERROR_NOT_SUPPORTED) return false;
                cu_check(write_status, "cuStreamWriteValue64_v2");
                // Retain the CUDA-visible edge required by the Driver API's
                // stream-memory-operation scheduling warning.
                ATLAS_CUDA(cudaEventRecord(memop_ready, writer));
                ATLAS_CUDA(cudaStreamWaitEvent(waiter, memop_ready, 0));
                const CUresult wait_status = cuStreamWaitValue64(reinterpret_cast<CUstream>(waiter), reinterpret_cast<CUdeviceptr>(flag), target, CU_STREAM_WAIT_VALUE_EQ);
                if (wait_status == CUDA_ERROR_NOT_SUPPORTED) return false;
                cu_check(wait_status, "cuStreamWaitValue64_v2");
                memop_consume64<<<1, 1, 0, waiter>>>(flag, target, error);
                ATLAS_CUDA(cudaEventRecord(memop_done, waiter));
                if (!event_wait_bounded(memop_done))
                    throw std::runtime_error("E22 64-bit stream memory handshake exceeded 30-second host wait deadline");
                return true;
            };
            if (!memop64()) {
                cases.push_back(skip("E22", "stream_memop_64",
                    "current CAN_USE_64_BIT_STREAM_MEM_OPS=1 but v2 operation returned CUDA_ERROR_NOT_SUPPORTED"));
            } else {
                int host_error = 1; ATLAS_CUDA(cudaMemcpy(&host_error, error, sizeof(int), cudaMemcpyDeviceToHost));
                CaseResult r; r.experiment = "E22"; r.variant = "stream_memop_64";
                r.configuration["allocation"] = "cudaMalloc device memory; managed memory excluded";
                r.configuration["api"] = "cuStreamWriteValue64_v2/cuStreamWaitValue64_v2";
                r.configuration["legacy_v1_capability"] = std::to_string(legacy_memops64);
                r.configuration["current_64_bit_capability"] = std::to_string(current_memops64);
                r.configuration["comparison"] = "EQ avoids cyclic GEQ wrap ambiguity";
                r.configuration["ordering"] = "writer event then CUDA-visible waiter event edge, followed by wait on already-published equality value; event overhead included";
                r.valid = host_error == 0;
                auto checked_memop64 = [&] {
                    if (!memop64()) throw std::runtime_error("E22 v2 64-bit stream memory operation became unsupported during measurement");
                };
                auto memop64_samples = wall_measure(o, checked_memop64, waiter);
                ATLAS_CUDA(cudaMemcpy(&host_error, error, sizeof(int), cudaMemcpyDeviceToHost));
                r.valid = r.valid && host_error == 0;
                summarize(r, memop64_samples); cases.push_back(std::move(r));
            }
            cudaEventDestroy(memop_done); cudaEventDestroy(memop_ready);
            cudaStreamDestroy(waiter); cudaStreamDestroy(writer); cudaFree(error); cudaFree(flag);
        }
    }

    if (wants("E25")) {
        const int n = static_cast<int>(std::min<std::size_t>(o.size, 1u << 22));
        std::vector<int> input(static_cast<std::size_t>(n));
        std::mt19937 rng(o.seed);
        for (int& v : input) v = static_cast<int>(rng() & 0x7fffffffU);
        DeviceBuffer<int> d_in(n), d_out(n); d_in.copy_from(input);
        const int phase_count = std::max(2, o.integer("phases", 8));
        const int small_phase = n <= 256 ? std::max(1, n / 4) :
            std::min(n - 1, std::max(256, o.integer("small-phase", 1024)));
        auto run_policy = [&](const std::string& policy, bool adapt) {
            std::vector<double> phase_ms, execution_samples, observation_samples, total_samples;
            std::vector<std::vector<double>> per_phase_completion(static_cast<std::size_t>(phase_count));
            std::vector<std::vector<double>> per_phase_policy_cost(static_cast<std::size_t>(phase_count));
            std::vector<int> choices;
            const int warmups = o.verify_only ? 0 : std::max(0, o.warmup);
            const int repeats = o.verify_only ? 1 : std::max(1, o.repeats);
            for (int sample_index = -warmups; sample_index < repeats; ++sample_index) {
              std::vector<int> run_choices;
              double observation_and_switch_ms = 0.0, execution_ms = 0.0;
              for (int p = 0; p < phase_count; ++p) {
                // The workload has an externally defined, alternating small/full phase schedule.
                // The policy only receives data/timings for the current phase.
                const int phase_n = (p & 1) ? n : small_phase;
                int choice = 0;
                double phase_observation_ms = 0.0;
                if (policy == "fixed_parallel") choice = 1;
                else if (adapt || policy == "offline_oracle") {
                    // Measure both semantically identical kernels on the phase's
                    // bounded workload. For adaptive policy, pilot execution,
                    // host decision, and dispatch are charged to observation.
                    // The offline oracle treats the same measurements as prior
                    // calibration and excludes them from its runtime cost.
                    cudaEvent_t a = nullptr, b = nullptr;
                    ATLAS_CUDA(cudaEventCreate(&a)); ATLAS_CUDA(cudaEventCreate(&b));
                    const auto start = std::chrono::steady_clock::now();
                    ATLAS_CUDA(cudaEventRecord(a));
                    phase_serial_grid<<<1, 256>>>(d_in.data(), d_out.data(), phase_n);
                    ATLAS_CUDA(cudaEventRecord(b));
                    if (!event_wait_bounded(b)) throw std::runtime_error("E25 serial pilot exceeded 30-second deadline");
                    float serial_ms = 0; ATLAS_CUDA(cudaEventElapsedTime(&serial_ms, a, b));
                    ATLAS_CUDA(cudaEventRecord(a));
                    phase_parallel_grid<<<(phase_n + 255) / 256, 256>>>(d_in.data(), d_out.data(), phase_n);
                    ATLAS_CUDA(cudaEventRecord(b));
                    if (!event_wait_bounded(b)) throw std::runtime_error("E25 parallel pilot exceeded 30-second deadline");
                    float parallel_ms = 0; ATLAS_CUDA(cudaEventElapsedTime(&parallel_ms, a, b));
                    cudaEventDestroy(a); cudaEventDestroy(b);
                    choice = parallel_ms < serial_ms ? 1 : 0;
                    if (adapt) {
                        phase_observation_ms = std::chrono::duration<double, std::milli>(
                            std::chrono::steady_clock::now() - start).count();
                        observation_and_switch_ms += phase_observation_ms;
                    }
                }
                run_choices.push_back(choice);
                const auto begin = std::chrono::steady_clock::now();
                if (choice) phase_parallel_grid<<<(phase_n + 255) / 256, 256>>>(d_in.data(), d_out.data(), phase_n);
                else phase_serial_grid<<<1, 256>>>(d_in.data(), d_out.data(), phase_n);
                ATLAS_CUDA(cudaGetLastError());
                cudaEvent_t finished = nullptr; ATLAS_CUDA(cudaEventCreateWithFlags(&finished, cudaEventDisableTiming));
                ATLAS_CUDA(cudaEventRecord(finished));
                const bool completed = event_wait_bounded(finished);
                cudaEventDestroy(finished);
                if (!completed) throw std::runtime_error("E25 selected phase kernel exceeded 30-second deadline");
                const double phase_elapsed = std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - begin).count();
                execution_ms += phase_elapsed;
                if (sample_index >= 0) {
                    phase_ms.push_back(phase_elapsed);
                    per_phase_completion[static_cast<std::size_t>(p)].push_back(phase_elapsed);
                    per_phase_policy_cost[static_cast<std::size_t>(p)].push_back(
                        phase_elapsed + phase_observation_ms);
                }
              }
              if (sample_index >= 0) {
                  observation_samples.push_back(observation_and_switch_ms);
                  execution_samples.push_back(execution_ms);
                  total_samples.push_back(observation_and_switch_ms + execution_ms);
                  choices = std::move(run_choices);
              }
            }
            CaseResult r; r.experiment = "E25"; r.variant = policy;
            std::ostringstream log; for (std::size_t i = 0; i < choices.size(); ++i) { if (i) log << ','; log << choices[i]; }
            r.configuration["phase_choices"] = log.str();
            r.configuration["phase_schedule"] = "known alternating small/full; adaptive policy sees only current-phase timing pilot";
            r.configuration["observation"] = adapt ? "times serial and parallel candidates per phase; pilot and switch dispatch included" :
                (policy == "offline_oracle" ? "candidate timings are run inline for dispatch but treated as prior offline calibration; calibration cost excluded" : "none");
            r.configuration["timing_contract"] = "host completion latency includes launch, event polling and host scheduling overhead; not kernel-only time";
            if (policy == "offline_oracle")
                r.limitations.push_back("in-sample offline oracle lower bound assumes candidate calibration is available at zero runtime cost; it is not an independent held-out policy");
            const auto median = [](std::vector<double> values) {
                if (values.empty()) return 0.0;
                std::sort(values.begin(), values.end()); return values[values.size() / 2];
            };
            r.metrics["observation_cost_ms"] = median(observation_samples);
            r.metrics["host_completion_latency_ms"] = median(execution_samples);
            r.metrics["total_host_cost_ms"] = median(total_samples);
            r.samples["observation_cost_ms"] = observation_samples;
            r.samples["host_completion_latency_ms"] = execution_samples;
            r.samples["total_host_cost_ms"] = total_samples;
            r.samples["phase_host_completion_latency_ms"] = phase_ms;
            for (int p = 0; p < phase_count; ++p) {
                const std::string phase = "phase_" + std::to_string(p);
                r.samples[phase + "_host_completion_latency_ms"] = per_phase_completion[static_cast<std::size_t>(p)];
                r.samples[phase + "_total_policy_cost_ms"] = per_phase_policy_cost[static_cast<std::size_t>(p)];
            }
            r.configuration["repeats"] = std::to_string(repeats);
            r.configuration["warmups"] = std::to_string(warmups);
            phase_serial_grid<<<1, 256>>>(d_in.data(), d_out.data(), n);
            ATLAS_CUDA(cudaGetLastError());
            cudaEvent_t verification_done = nullptr;
            ATLAS_CUDA(cudaEventCreateWithFlags(&verification_done, cudaEventDisableTiming));
            ATLAS_CUDA(cudaEventRecord(verification_done));
            bool correct = event_wait_bounded(verification_done);
            auto result = d_out.copy_to();
            for (int i = 0; correct && i < n; ++i) correct = result[i] == input[i] + 3;
            phase_parallel_grid<<<(n + 255) / 256, 256>>>(d_in.data(), d_out.data(), n);
            ATLAS_CUDA(cudaEventRecord(verification_done));
            correct = event_wait_bounded(verification_done) && correct;
            result = d_out.copy_to();
            for (int i = 0; correct && i < n; ++i) correct = result[i] == input[i] + 3;
            cudaEventDestroy(verification_done);
            r.valid = correct;
            return r;
        };
        cases.push_back(run_policy("fixed_serial", false));
        cases.push_back(run_policy("fixed_parallel", false));
        cases.push_back(run_policy("adaptive_pilot", true));
        cases.push_back(run_policy("offline_oracle", false));
    }

    const auto variant_it = o.args.find("variant");
    if (variant_it != o.args.end()) {
        Cases filtered;
        for (auto& result : cases)
            if (result.variant == variant_it->second) filtered.push_back(std::move(result));
        if (filtered.empty())
            throw std::invalid_argument("--variant '" + variant_it->second +
                                        "' is unavailable for experiment " + selected);
        return filtered;
    }
    return cases;
}

} // namespace atlas

int main(int argc, char** argv) {
    return atlas::main(argc, argv, atlas::run_sync);
}
