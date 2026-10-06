#include "common.hpp"

#include <array>
#include <cstdint>
#include <cstring>
#include <functional>
#include <limits>
#include <numeric>
#include <time.h>

namespace {

using atlas::CaseResult;
using atlas::Cases;
using atlas::Options;

constexpr unsigned kFullWarp = 0xffffffffu;
constexpr int kThreads = 128;

bool selected(const Options& o, const std::string& name) {
    const std::string requested = o.text("variant", "");
    return requested.empty() || requested == name;
}

template <class F>
void each_selected(const Options& o, Cases& cases, const std::string& experiment,
                   const std::string& name, F&& f) {
    if (selected(o, name)) cases.push_back(f());
    (void)experiment;
}

void add_common(CaseResult& c, const Options& o, int iterations,
                std::size_t size, const std::string& numerical) {
    c.configuration["device"] = std::to_string(o.device);
    c.configuration["size"] = std::to_string(size);
    c.configuration["iterations"] = std::to_string(iterations);
    c.configuration["seed"] = std::to_string(o.seed);
    c.configuration["warmup"] = std::to_string(o.verify_only ? 0 : o.warmup);
    c.configuration["repeats"] = std::to_string(o.verify_only ? 1 : o.repeats);
    c.configuration["verification"] = numerical;
}

void time_case(CaseResult& c, const Options& o, const std::function<void()>& launch) {
    c.samples["event_ms"] = atlas::measure(o, launch);
    const auto& s = c.samples["event_ms"];
    if (!s.empty()) {
        std::vector<double> sorted = s;
        std::sort(sorted.begin(), sorted.end());
        const std::size_t middle = sorted.size() / 2;
        c.metrics["median_event_ms"] = sorted.size() % 2
            ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) * 0.5;
        const std::size_t nearest_rank = (95 * sorted.size() + 99) / 100;
        c.metrics["p95_event_ms"] = sorted[std::min(sorted.size() - 1, nearest_rank - 1)];
    }
}

// E02: each case keeps the operation result live. The dependent and independent
// kernels use the same add form; an empty volatile-asm loop measures loop cost.
__global__ void dependent_add_kernel(uint32_t* out, int iterations) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    uint32_t x = tid + 1u;
#pragma unroll 1
    for (int i = 0; i < iterations; ++i)
        asm volatile("add.u32 %0, %0, 1;" : "+r"(x));
    out[tid] = x;
}

template <int N>
__global__ void independent_add_kernel(uint32_t* out, int iterations) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    uint32_t a[N];
#pragma unroll
    for (int j = 0; j < N; ++j) a[j] = tid + static_cast<unsigned>(j + 1);
#pragma unroll 1
    for (int i = 0; i < iterations; ++i) {
#pragma unroll
        for (int j = 0; j < N; ++j)
            asm volatile("add.u32 %0, %0, 1;" : "+r"(a[j]));
    }
    uint32_t sum = 0;
#pragma unroll
    for (int j = 0; j < N; ++j) sum += a[j];
    out[tid] = sum;
}

__global__ void loop_control_clock_kernel(uint64_t* out, int iterations,
                                          uint32_t launched_threads) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    uint64_t first = 0;
    uint64_t last = 0;
#pragma unroll 1
    for (int i = 0; i < iterations; ++i) {
        uint64_t tick;
        asm volatile("mov.u64 %0, %%clock64;" : "=l"(tick));
        if (i == 0) first = tick;
        last = tick;
    }
    out[tid] = first;
    out[tid + launched_threads] = last;
}

template <int N>
CaseResult run_independent(const Options& o, int iterations) {
    const std::size_t n = std::min<std::size_t>(std::max<std::size_t>(o.size, 128), 4096);
    const int blocks = static_cast<int>((n + kThreads - 1) / kThreads);
    atlas::DeviceBuffer<uint32_t> d_out(static_cast<std::size_t>(blocks * kThreads));
    CaseResult c;
    c.experiment = "E02";
    c.variant = "independent_add_" + std::to_string(N);
    add_common(c, o, iterations, n, "uint32 modular addition; all accumulators consumed by sum");
    c.configuration["chains"] = std::to_string(N);
    auto launch = [&] { independent_add_kernel<N><<<blocks, kThreads>>>(d_out.data(), iterations); };
    launch(); ATLAS_CUDA(cudaDeviceSynchronize());
    const auto got = d_out.copy_to();
    for (int t = 0; t < blocks * kThreads; ++t) {
        uint32_t expected = 0;
        for (int j = 0; j < N; ++j) expected += static_cast<uint32_t>(t + j + 1) + static_cast<uint32_t>(iterations);
        if (got[static_cast<std::size_t>(t)] != expected) {
            c.valid = false; c.limitations.push_back("CPU oracle mismatch in independent accumulator"); break;
        }
    }
    c.metrics["correctness_checked_threads"] = static_cast<double>(got.size());
    time_case(c, o, launch);
    c.limitations.push_back("Single add form and fixed 128-thread blocks only; operand forms, register-pressure and warp-count sweep remain unimplemented.");
    c.limitations.push_back("sm_70 SASS loop body retains N independent IADD3 updates plus loop-counter IADD3, ISETP compare and conditional BRA; event timing includes this control work and does not subtract an executable empty-loop baseline. Static @!PT SHFL.IDX placeholder is unconditionally predicated off.");
    return c;
}

Cases run_e02(const Options& o) {
    Cases cases;
    const int iterations = std::min(o.iterations, 1000000);
    const std::size_t n = std::min<std::size_t>(std::max<std::size_t>(o.size, 128), 4096);
    const int blocks = static_cast<int>((n + kThreads - 1) / kThreads);
    atlas::DeviceBuffer<uint32_t> d_out(static_cast<std::size_t>(blocks * kThreads));
    each_selected(o, cases, "E02", "dependent_add", [&] {
        CaseResult c; c.experiment = "E02"; c.variant = "dependent_add";
        add_common(c, o, iterations, n, "uint32 modular addition; serial dependent chain consumed");
        auto launch = [&] { dependent_add_kernel<<<blocks, kThreads>>>(d_out.data(), iterations); };
        launch(); ATLAS_CUDA(cudaDeviceSynchronize());
        const auto got = d_out.copy_to();
        bool ok = true;
        for (int t = 0; t < blocks * kThreads; ++t)
            ok = ok && got[static_cast<std::size_t>(t)] == static_cast<uint32_t>(t + 1) + static_cast<uint32_t>(iterations);
        c.valid = ok; c.metrics["correctness_checked_threads"] = static_cast<double>(got.size());
        if (!ok) c.limitations.push_back("CPU oracle mismatch in dependent chain");
        time_case(c, o, launch);
        c.limitations.push_back("One integer add instruction form; no memory, SFU, conversion or register-pressure sweep.");
        c.limitations.push_back("sm_70 SASS loop body retains one dependent IADD3 per iteration plus loop-counter IADD3, ISETP compare and conditional BRA; event timing is a whole-kernel chain measurement, not isolated single-add latency. Static @!PT SHFL.IDX placeholder is unconditionally predicated off.");
        return c;
    });
    each_selected(o, cases, "E02", "loop_control_clock_read", [&] {
        CaseResult c; c.experiment = "E02"; c.variant = "loop_control_clock_read";
        const int clock_iterations = std::max(2, std::min(iterations, 1000000));
        const std::size_t launched_threads = static_cast<std::size_t>(blocks * kThreads);
        atlas::DeviceBuffer<uint64_t> d_clock(2 * launched_threads);
        add_common(c, o, clock_iterations, launched_threads,
                   "per-iteration clock64 samples; every launch thread's clock delta is checked for progress and boundedness");
        c.configuration["logical_threads"] = std::to_string(n);
        c.configuration["launched_threads"] = std::to_string(launched_threads);
        c.configuration["clock_reads_per_thread"] = std::to_string(clock_iterations);
        c.configuration["purpose"] = "clock-read loop-control characterization; not a pure empty-loop baseline";
        auto launch = [&] { loop_control_clock_kernel<<<blocks, kThreads>>>(d_clock.data(), clock_iterations, static_cast<uint32_t>(launched_threads)); };
        launch(); ATLAS_CUDA(cudaDeviceSynchronize());
        const auto got = d_clock.copy_to();
        std::vector<uint64_t> deltas(launched_threads);
        const uint64_t max_delta = static_cast<uint64_t>(clock_iterations) * 1024u + (1u << 20);
        bool ok = true;
        uint64_t min_delta = std::numeric_limits<uint64_t>::max(), max_seen = 0;
        for (std::size_t t = 0; t < launched_threads; ++t) {
            const uint64_t delta = got[t + launched_threads] - got[t];
            deltas[t] = delta;
            ok = ok && delta > 0 && delta <= max_delta;
            min_delta = std::min(min_delta, delta);
            max_seen = std::max(max_seen, delta);
        }
        std::sort(deltas.begin(), deltas.end());
        c.valid = ok;
        c.metrics["correctness_checked_threads"] = static_cast<double>(launched_threads);
        c.metrics["clock64_min_delta_cycles"] = static_cast<double>(min_delta);
        c.metrics["clock64_median_delta_cycles"] = static_cast<double>(deltas[deltas.size()/2]);
        c.metrics["clock64_max_delta_cycles"] = static_cast<double>(max_seen);
        c.metrics["clock64_progress_failures"] = ok ? 0.0 : 1.0;
        if (!ok) c.limitations.push_back("clock64 delta failed the positive and per-thread upper-bound progress check");
        time_case(c, o, launch);
        c.limitations.push_back("Clock reads add an instruction and observer work to each loop; this is not an empty-loop or directly subtractable add-latency baseline.");
        return c;
    });
    auto add_independent = [&](auto tag) {
        constexpr int N = decltype(tag)::value;
        const std::string name = "independent_add_" + std::to_string(N);
        if (selected(o, name)) cases.push_back(run_independent<N>(o, iterations));
    };
    add_independent(std::integral_constant<int, 1>{});
    add_independent(std::integral_constant<int, 2>{});
    add_independent(std::integral_constant<int, 4>{});
    add_independent(std::integral_constant<int, 8>{});
    if (cases.empty()) cases.push_back(atlas::skip("E02", o.text("variant", ""), "unknown E02 variant"));
    return cases;
}

// E03: equal iteration counts per family, identical useful outputs in every
// schedule. Integer and FP paths remain independent of one another.
__global__ void pipeline_kernel(uint32_t* int_out, float* fp_out, int iterations, int mode) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    uint32_t x = tid + 1u;
    float f = static_cast<float>(tid % 31u) * 0.03125f + 0.5f;
    if (mode == 0) {
        for (int i = 0; i < iterations; ++i) asm volatile("add.u32 %0, %0, 1;" : "+r"(x));
    } else if (mode == 1) {
        for (int i = 0; i < iterations; ++i) f = fmaf(f, 1.0001f, 0.0003f);
    } else if (mode == 2) {
        for (int i = 0; i < iterations; ++i) asm volatile("add.u32 %0, %0, 1;" : "+r"(x));
        for (int i = 0; i < iterations; ++i) f = fmaf(f, 1.0001f, 0.0003f);
    } else {
        for (int i = 0; i < iterations; ++i) {
            asm volatile("add.u32 %0, %0, 1;" : "+r"(x));
            f = fmaf(f, 1.0001f, 0.0003f);
        }
    }
    int_out[tid] = x;
    fp_out[tid] = f;
}

std::array<float,31> make_e03_fp_oracle(int iterations, int mode) {
    std::array<float,31> result{};
    for (std::size_t seed=0; seed<result.size(); ++seed) {
        float value=static_cast<float>(seed)*0.03125f+0.5f;
        if (mode!=0)
            for (int i=0;i<iterations;++i) value=std::fma(value,1.0001f,0.0003f);
        result[seed]=value;
    }
    return result;
}

bool verify_e03_outputs(int mode,int iterations,const std::vector<uint32_t>& got_int,
                        const std::vector<float>& got_fp,const std::array<float,31>& fp_oracle,
                        std::string* detail=nullptr) {
    bool ok=true;
    for (std::size_t t=0;t<got_int.size();++t) {
        const uint32_t expected_int=static_cast<uint32_t>(t+1)+
            static_cast<uint32_t>(mode==1?0:iterations);
        const float expected_fp=fp_oracle[t%fp_oracle.size()];
        const bool item_ok=got_int[t]==expected_int &&
            std::fabs(got_fp[t]-expected_fp)<=2.0e-6f*(1.0f+std::fabs(expected_fp));
        if (!item_ok && ok && detail) {
            std::ostringstream message;
            message << "E03 CPU oracle mismatch thread=" << t
                    << " observed_int=" << got_int[t] << " expected_int=" << expected_int
                    << " observed_fp=" << got_fp[t] << " expected_fp=" << expected_fp;
            *detail=message.str();
        }
        ok=ok&&item_ok;
    }
    return ok;
}

double monotonic_seconds() {
    struct timespec value{};
    if (clock_gettime(CLOCK_MONOTONIC,&value)!=0)
        throw std::runtime_error("clock_gettime(CLOCK_MONOTONIC) failed");
    return static_cast<double>(value.tv_sec)+static_cast<double>(value.tv_nsec)*1.0e-9;
}

std::string double_text(double value) {
    std::ostringstream out; out.precision(17); out<<value; return out.str();
}

CaseResult run_e03_steady(const Options& o,std::size_t n,int blocks,int iterations,
                          int mode,const std::string& variant,int steady_seconds) {
    ATLAS_CUDA(cudaSetDevice(o.device));
    const std::size_t launched_threads=static_cast<std::size_t>(blocks*kThreads);
    atlas::DeviceBuffer<uint32_t> d_int(launched_threads);
    atlas::DeviceBuffer<float> d_fp(launched_threads);
    CaseResult result; result.experiment="E03"; result.variant=variant;
    add_common(result,o,iterations,n,"uint32 modular adds and IEEE single-precision fmaf; full outputs checked before and after steady timing");
    result.configuration["requested_size"]=std::to_string(o.size);
    result.configuration["logical_threads"]=std::to_string(n);
    result.configuration["launched_threads"]=std::to_string(launched_threads);
    result.configuration["integer_work"]=std::to_string(mode==1?0:iterations);
    result.configuration["fp_work"]=std::to_string(mode==0?0:iterations);
    const std::size_t integer_work=launched_threads*static_cast<std::size_t>(mode==1?0:iterations);
    const std::size_t fp_work=launched_threads*static_cast<std::size_t>(mode==0?0:iterations);
    result.configuration["launched_integer_work_units"]=std::to_string(integer_work);
    result.configuration["launched_fp_work_units"]=std::to_string(fp_work);
    result.configuration["launched_total_work_units"]=std::to_string(integer_work+fp_work);
    result.configuration["steady_requested_seconds"]=std::to_string(steady_seconds);
    result.configuration["host_clock_source"]="CLOCK_MONOTONIC";
    result.configuration["steady_warmup_launches"]="5";
    result.metrics["actual_launched_threads"]=static_cast<double>(launched_threads);
    result.metrics["actual_iterations_per_working_thread"]=static_cast<double>(iterations);
    result.metrics["launched_integer_work_units"]=static_cast<double>(integer_work);
    result.metrics["launched_fp_work_units"]=static_cast<double>(fp_work);
    result.metrics["launched_total_work_units"]=static_cast<double>(integer_work+fp_work);
    result.metrics["steady_requested_seconds"]=static_cast<double>(steady_seconds);

    auto launch=[&]{pipeline_kernel<<<blocks,kThreads>>>(d_int.data(),d_fp.data(),iterations,mode);};
    const auto fp_oracle=make_e03_fp_oracle(iterations,mode);
    launch(); ATLAS_CUDA(cudaGetLastError()); ATLAS_CUDA(cudaDeviceSynchronize());
    std::string oracle_detail;
    bool valid=verify_e03_outputs(mode,iterations,d_int.copy_to(),d_fp.copy_to(),fp_oracle,&oracle_detail);
    result.metrics["pre_timing_correctness_checked_threads"]=static_cast<double>(launched_threads);
    if (!valid) {
        result.valid=false; result.limitations.push_back(oracle_detail);
        return result;
    }

    for (int i=0;i<5;++i) { launch(); ATLAS_CUDA(cudaGetLastError()); }
    ATLAS_CUDA(cudaDeviceSynchronize());
    cudaEvent_t start=nullptr,stop=nullptr;
    ATLAS_CUDA(cudaEventCreate(&start));
    try {
        ATLAS_CUDA(cudaEventCreate(&stop));
        std::vector<double> event_ms,host_start,host_end;
        const double interval_start=monotonic_seconds();
        const double deadline=interval_start+static_cast<double>(steady_seconds);
        do {
            const double t0=monotonic_seconds();
            ATLAS_CUDA(cudaEventRecord(start));
            launch(); ATLAS_CUDA(cudaGetLastError());
            ATLAS_CUDA(cudaEventRecord(stop));
            ATLAS_CUDA(cudaEventSynchronize(stop));
            const double t1=monotonic_seconds();
            float elapsed=0.0f; ATLAS_CUDA(cudaEventElapsedTime(&elapsed,start,stop));
            host_start.push_back(t0); host_end.push_back(t1); event_ms.push_back(static_cast<double>(elapsed));
        } while (monotonic_seconds()<deadline);
        const double interval_end=monotonic_seconds();
        ATLAS_CUDA(cudaEventDestroy(stop)); stop=nullptr;
        ATLAS_CUDA(cudaEventDestroy(start)); start=nullptr;
        result.samples["event_ms"]=event_ms;
        result.samples["host_start_monotonic_s"]=host_start;
        result.samples["host_end_monotonic_s"]=host_end;
        result.configuration["measurement_interval_start_monotonic_s"]=double_text(interval_start);
        result.configuration["measurement_interval_end_monotonic_s"]=double_text(interval_end);
        result.metrics["measurement_interval_duration_s"]=interval_end-interval_start;
        result.metrics["steady_sample_count"]=static_cast<double>(event_ms.size());
        result.metrics["post_timing_correctness_checked_threads"]=static_cast<double>(launched_threads);
        if (!event_ms.empty()) {
            auto sorted=event_ms; std::sort(sorted.begin(),sorted.end());
            const std::size_t middle=sorted.size()/2;
            result.metrics["median_event_ms"]=sorted.size()%2?sorted[middle]:(sorted[middle-1]+sorted[middle])*0.5;
            const std::size_t nearest_rank=(95*sorted.size()+99)/100;
            result.metrics["p95_event_ms"]=sorted[std::min(sorted.size()-1,nearest_rank-1)];
        }
        valid=event_ms.size()>=30 && host_start.size()==host_end.size() &&
              host_start.size()==event_ms.size();
        if (event_ms.size()<30) result.limitations.push_back("steady interval completed with fewer than 30 paired raw samples");
        if (host_start.size()!=host_end.size() || host_start.size()!=event_ms.size())
            result.limitations.push_back("host monotonic timestamp vectors are not paired one-to-one with CUDA event samples");
        for (std::size_t i=0;i<host_start.size();++i)
            valid=valid && std::isfinite(host_start[i]) && std::isfinite(host_end[i]) &&
                  host_end[i]>=host_start[i] && host_start[i]>=interval_start && host_end[i]<=interval_end;

        const auto final_int=d_int.copy_to(); const auto final_fp=d_fp.copy_to();
        std::string final_detail;
        const bool final_valid=verify_e03_outputs(mode,iterations,final_int,final_fp,fp_oracle,&final_detail);
        if (!final_valid) result.limitations.push_back(final_detail);
        valid=valid&&final_valid;
        result.valid=valid;
    } catch (...) {
        if (stop) cudaEventDestroy(stop);
        if (start) cudaEventDestroy(start);
        throw;
    }
    result.limitations.push_back("Steady timing uses continuous serial/interleaved GPU work with five warmup launches; event intervals exclude host orchestration, while host monotonic endpoints bracket each launch and completion. CUDA-event time includes the selected kernel's add/FMA loop controls.");
    return result;
}

Cases run_e03(const Options& o) {
    Cases cases;
    const std::size_t n = std::min<std::size_t>(std::max<std::size_t>(o.size, 128), 1u << 20);
    const int blocks = static_cast<int>((n + kThreads - 1) / kThreads);
    const int iterations = std::min(o.iterations, 100000);
    const int steady_seconds=o.integer("steady-seconds",0);
    if (steady_seconds<0 || steady_seconds>300)
        throw std::invalid_argument("--steady-seconds must be in [0,300]");
    if (steady_seconds>0) {
        const std::string variant=o.text("variant","");
        if (variant!="serial" && variant!="interleaved")
            throw std::invalid_argument("--steady-seconds requires an explicit --variant serial or interleaved");
        const int mode=variant=="serial"?2:3;
        return {run_e03_steady(o,n,blocks,iterations,mode,variant,steady_seconds)};
    }
    const std::size_t launched_threads = static_cast<std::size_t>(blocks * kThreads);
    atlas::DeviceBuffer<uint32_t> d_int(static_cast<std::size_t>(blocks * kThreads));
    atlas::DeviceBuffer<float> d_fp(static_cast<std::size_t>(blocks * kThreads));
    const std::array<std::pair<const char*, int>, 4> variants{{
        {"int_isolated", 0}, {"fp_isolated", 1}, {"serial", 2}, {"interleaved", 3}}};
    for (const auto& v : variants) each_selected(o, cases, "E03", v.first, [&] {
        CaseResult c; c.experiment = "E03"; c.variant = v.first;
        add_common(c, o, iterations, n, "uint32 modular adds and IEEE single-precision fmaf; both results retained");
        c.configuration["requested_size"] = std::to_string(o.size);
        c.configuration["logical_threads"] = std::to_string(n);
        c.configuration["launched_threads"] = std::to_string(launched_threads);
        c.configuration["integer_work"] = std::to_string(v.second == 1 ? 0 : iterations);
        c.configuration["fp_work"] = std::to_string(v.second == 0 ? 0 : iterations);
        const std::size_t int_work_per_thread = v.second == 1 ? 0u : static_cast<std::size_t>(iterations);
        const std::size_t fp_work_per_thread = v.second == 0 ? 0u : static_cast<std::size_t>(iterations);
        const std::size_t launched_int_work = launched_threads * int_work_per_thread;
        const std::size_t launched_fp_work = launched_threads * fp_work_per_thread;
        c.configuration["launched_integer_work_units"] = std::to_string(launched_int_work);
        c.configuration["launched_fp_work_units"] = std::to_string(launched_fp_work);
        c.configuration["launched_total_work_units"] = std::to_string(launched_int_work + launched_fp_work);
        auto launch = [&] { pipeline_kernel<<<blocks, kThreads>>>(d_int.data(), d_fp.data(), iterations, v.second); };
        launch(); ATLAS_CUDA(cudaDeviceSynchronize());
        const auto gi = d_int.copy_to(); const auto gf = d_fp.copy_to();
        std::array<float,31> fp_oracle{};
        for (std::size_t seed = 0; seed < fp_oracle.size(); ++seed) {
            float value = static_cast<float>(seed) * 0.03125f + 0.5f;
            if (v.second != 0)
                for (int i = 0; i < iterations; ++i) value = std::fma(value, 1.0001f, 0.0003f);
            fp_oracle[seed] = value;
        }
        bool ok = true;
        for (std::size_t t = 0; t < gi.size(); ++t) {
            const uint32_t ei = static_cast<uint32_t>(t + 1) + static_cast<uint32_t>(v.second == 1 ? 0 : iterations);
            const float ef = fp_oracle[t % fp_oracle.size()];
            ok = ok && gi[t] == ei && std::fabs(gf[t] - ef) <= 2.0e-6f * (1.0f + std::fabs(ef));
        }
        c.valid = ok; c.metrics["correctness_checked_threads"] = static_cast<double>(gi.size());
        c.metrics["actual_launched_threads"] = static_cast<double>(launched_threads);
        c.metrics["actual_iterations_per_working_thread"] = static_cast<double>(iterations);
        c.metrics["launched_integer_work_units"] = static_cast<double>(launched_int_work);
        c.metrics["launched_fp_work_units"] = static_cast<double>(launched_fp_work);
        c.metrics["launched_total_work_units"] = static_cast<double>(launched_int_work + launched_fp_work);
        if (!ok) c.limitations.push_back("CPU oracle mismatch in pipeline result");
        time_case(c, o, launch);
        c.limitations.push_back("Representative integer-add plus FP32-FMA only; tensor, conversion, load and work-ratio/live-register sweeps remain unimplemented.");
        return c;
    });
    if (cases.empty()) cases.push_back(atlas::skip("E03", o.text("variant", ""), "unknown E03 variant"));
    return cases;
}

__constant__ uint32_t c_lookup[32];

__global__ void shuffle_lookup_kernel(uint32_t* out, std::size_t n, int table_size,
                                      unsigned seed, bool uniform) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    const int lane = threadIdx.x & 31;
    const int query = uniform ? static_cast<int>(seed % table_size)
                              : (lane * 13 + static_cast<int>(seed % table_size)) % table_size;
    const uint32_t table_value = 1000u + static_cast<uint32_t>(lane);
    const uint32_t value = __shfl_sync(kFullWarp, table_value, query);
    if (tid < n) out[tid] = value;
}

__global__ void constant_lookup_kernel(uint32_t* out, std::size_t n, int table_size,
                                       unsigned seed, bool uniform) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    const int lane = threadIdx.x & 31;
    const int query = uniform ? static_cast<int>(seed % table_size)
                              : (lane * 13 + static_cast<int>(seed % table_size)) % table_size;
    if (tid < n) out[tid] = c_lookup[query];
}

__global__ void cached_global_lookup_kernel(uint32_t* out, std::size_t n,
                                            const uint32_t* table, int table_size,
                                            unsigned seed, bool uniform) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    const int lane = threadIdx.x & 31;
    const int query = uniform ? static_cast<int>(seed % table_size)
                              : (lane * 13 + static_cast<int>(seed % table_size)) % table_size;
    if (tid < n) out[tid] = __ldg(table + query);
}

__global__ void shared_lookup_kernel(uint32_t* out, std::size_t n, int table_size,
                                     unsigned seed, bool uniform) {
    __shared__ uint32_t table[32];
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    const int lane = threadIdx.x & 31;
    if (threadIdx.x < table_size)
        table[threadIdx.x] = 1000u + static_cast<uint32_t>(threadIdx.x);
    __syncthreads();
    const int query = uniform ? static_cast<int>(seed % table_size)
                              : (lane * 13 + static_cast<int>(seed % table_size)) % table_size;
    const uint32_t value = table[query];
    if (tid < n) out[tid] = value;
}

__global__ void per_lane_atomic_kernel(const uint32_t* keys, uint32_t* hist,
                                       std::size_t n, int cardinality) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid < n) atomicAdd(hist + (keys[tid] % static_cast<unsigned>(cardinality)), 1u);
}

__global__ void match_group_atomic_kernel(const uint32_t* keys, uint32_t* hist,
                                          std::size_t n, int cardinality) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    const bool valid = tid < n;
    const unsigned valid_mask = __ballot_sync(kFullWarp, valid);
    if (valid) {
        const uint32_t key = keys[tid] % static_cast<unsigned>(cardinality);
        const unsigned peers = __match_any_sync(valid_mask, key);
        const int leader = __ffs(static_cast<int>(peers)) - 1;
        if ((threadIdx.x & 31) == leader) atomicAdd(hist + key, __popc(peers));
    }
}

__device__ __forceinline__ int select_set_lane(unsigned mask, int ordinal) {
    int seen = 0;
#pragma unroll
    for (int lane = 0; lane < 32; ++lane) {
        if ((mask & (1u << lane)) != 0u) {
            if (seen == ordinal) return lane;
            ++seen;
        }
    }
    return -1;
}

__global__ void rank_select_kernel(uint32_t* ranks, uint32_t* selected,
                                   int small_mask_count, unsigned seed) {
    const unsigned tid = blockIdx.x * blockDim.x + threadIdx.x;
    const int lane = threadIdx.x & 31;
    const int warp = static_cast<int>(tid >> 5);
    constexpr int kSmallMasks = 256;
    constexpr int kPartialWidths[] = {1, 7, 17, 31, 32};
    unsigned candidate = 0;
    if (warp < kSmallMasks) {
        candidate = static_cast<unsigned>(warp) & 0xffu;
    } else {
        const int width_index = warp - kSmallMasks;
        candidate = width_index < 5 && lane < kPartialWidths[width_index]
                  ? (1u << lane) : 0u;
    }
    const bool member = warp < kSmallMasks
                      ? ((candidate & (1u << lane)) != 0u)
                      : (candidate != 0u);
    const unsigned members = __ballot_sync(kFullWarp, member);
    if (member) {
        const unsigned lower = lane == 0 ? 0u : ((1u << lane) - 1u);
        const unsigned rank = __popc(members & lower);
        const unsigned count = __popc(members);
        const int ordinal = static_cast<int>((static_cast<unsigned>(lane) + seed) % count);
        const int source_lane = select_set_lane(members, ordinal);
        // Only members call this shuffle, and its explicit mask is exactly the
        // ballot-derived logical group. No activemask is used as membership.
        const unsigned selected_lane = __shfl_sync(members, static_cast<unsigned>(lane), source_lane);
        const unsigned out_index = static_cast<unsigned>(warp * 32 + lane);
        ranks[out_index] = rank;
        selected[out_index] = selected_lane;
    }
}

CaseResult run_rank_select(const Options& o) {
    constexpr int kMasks = 256 + 5;
    constexpr int kTotal = kMasks * 32;
    constexpr int kBlocks = (kTotal + kThreads - 1) / kThreads;
    atlas::DeviceBuffer<uint32_t> d_ranks(kTotal), d_selected(kTotal);
    CaseResult c; c.experiment = "E05"; c.variant = "rank_select_small_masks";
    add_common(c, o, 1, kTotal, "rank equals popcount of preceding mask members; selected value matches CPU ordinal selection");
    c.configuration["exhaustive_masks"] = "all 256 membership masks over low eight warp lanes";
    c.configuration["partial_warp_widths"] = "1,7,17,31,32";
    auto launch = [&] { rank_select_kernel<<<kBlocks,kThreads>>>(d_ranks.data(),d_selected.data(),256,o.seed); };
    launch(); ATLAS_CUDA(cudaDeviceSynchronize());
    const auto ranks = d_ranks.copy_to(); const auto selected = d_selected.copy_to();
    std::size_t checked = 0;
    bool ok = true;
    for (int warp=0; warp<kMasks; ++warp) {
        unsigned mask = 0;
        if (warp < 256) mask = static_cast<unsigned>(warp);
        else {
            const int width[] = {1,7,17,31,32};
            mask = width[warp-256] == 32 ? 0xffffffffu : ((1u << width[warp-256]) - 1u);
        }
        const unsigned count = static_cast<unsigned>(__builtin_popcount(mask));
        for (int lane=0; lane<32; ++lane) if ((mask & (1u << lane)) != 0u) {
            const unsigned idx = static_cast<unsigned>(warp * 32 + lane);
            const unsigned expected_rank = static_cast<unsigned>(__builtin_popcount(mask & ((1u << lane) - 1u)));
            const unsigned ordinal = (static_cast<unsigned>(lane) + o.seed) % count;
            int expected_source = -1;
            for (int bit=0, seen=0; bit<32; ++bit) if ((mask & (1u<<bit)) != 0u) {
                if (seen == static_cast<int>(ordinal)) { expected_source = bit; break; }
                ++seen;
            }
            ok = ok && ranks[idx] == expected_rank && selected[idx] == static_cast<unsigned>(expected_source);
            ++checked;
        }
    }
    c.valid = ok; c.metrics["correctness_checked_active_lanes"] = static_cast<double>(checked);
    c.metrics["empty_membership_masks"] = 1.0;
    if (!ok) c.limitations.push_back("CPU rank/select oracle mismatch");
    time_case(c,o,launch);
    c.limitations.push_back("Selection uses a public ballot plus software ordinal scan; no payload shuffle, multiword selection, mask-size performance sweep or alternative instruction lowering is tested.");
    return c;
}

Cases run_e05(const Options& o) {
    Cases cases;
    const std::size_t n = std::min<std::size_t>(std::max<std::size_t>(o.size, 1), 1u << 20);
    const int blocks = static_cast<int>((n + kThreads - 1) / kThreads);
    atlas::DeviceBuffer<uint32_t> d_out(n), d_table(32), d_keys(n), d_hist(16);
    std::vector<uint32_t> table(32), keys(n);
    for (int i = 0; i < 32; ++i) table[static_cast<std::size_t>(i)] = 1000u + static_cast<uint32_t>(i);
    for (std::size_t i = 0; i < n; ++i) keys[i] = static_cast<uint32_t>((i + (o.seed % 16u)) % 16u);
    d_table.copy_from(table); d_keys.copy_from(keys);
    ATLAS_CUDA(cudaMemcpyToSymbol(c_lookup, table.data(), sizeof(uint32_t) * 32));
    for (int table_size : {8, 32}) for (bool uniform : {true, false}) {
        const std::string distribution = uniform ? "uniform" : "diverse";
        const std::array<const char*, 4> names{{"shuffle", "constant_cached", "global_cached", "shared_cached"}};
        for (const char* base : names) {
            const std::string name = std::string(base) + "_" + distribution + "_t" + std::to_string(table_size);
            each_selected(o, cases, "E05", name, [&] {
                CaseResult c; c.experiment = "E05"; c.variant = name;
                add_common(c, o, 1, n, "lookup equals CPU table value for every output lane; every lane participates in full-mask shuffle");
                c.configuration["table_size"] = std::to_string(table_size);
                c.configuration["query_distribution"] = distribution;
                auto launch = [&] {
                    if (std::string(base) == "shuffle") shuffle_lookup_kernel<<<blocks,kThreads>>>(d_out.data(),n,table_size,o.seed,uniform);
                    else if (std::string(base) == "constant_cached") constant_lookup_kernel<<<blocks,kThreads>>>(d_out.data(),n,table_size,o.seed,uniform);
                    else if (std::string(base) == "global_cached") cached_global_lookup_kernel<<<blocks,kThreads>>>(d_out.data(),n,d_table.data(),table_size,o.seed,uniform);
                    else shared_lookup_kernel<<<blocks,kThreads>>>(d_out.data(),n,table_size,o.seed,uniform);
                };
                launch(); ATLAS_CUDA(cudaDeviceSynchronize()); const auto got = d_out.copy_to();
                bool ok = true;
                for (std::size_t i = 0; i < n; ++i) {
                    const int lane = static_cast<int>(i % kThreads) & 31;
                    const int q = uniform ? static_cast<int>(o.seed % table_size)
                                          : (lane * 13 + static_cast<int>(o.seed % table_size)) % table_size;
                    ok = ok && got[i] == table[static_cast<std::size_t>(q)];
                }
                c.valid = ok; c.metrics["correctness_checked_outputs"] = static_cast<double>(n);
                if (!ok) c.limitations.push_back("CPU lookup oracle mismatch");
                time_case(c,o,launch);
                c.limitations.push_back("Fixed 32-lane warp table, 8/32-entry tables and two query distributions only; shared/constant setup and break-even reuse sweep are incomplete.");
                return c;
            });
        }
    }
    for (int cardinality : {2, 8, 16}) for (const std::string& base : {"per_lane_atomic", "match_group_atomic"}) {
        const std::string name = base + "_k" + std::to_string(cardinality);
        each_selected(o, cases, "E05", name, [&] {
            CaseResult c; c.experiment = "E05"; c.variant = name;
            add_common(c,o,1,n,"histogram exactly matches host counts; partial final warp excluded by explicit ballot membership");
            c.configuration["key_cardinality"] = std::to_string(cardinality);
            auto launch = [&] {
                if (base == "per_lane_atomic") per_lane_atomic_kernel<<<blocks,kThreads>>>(d_keys.data(),d_hist.data(),n,cardinality);
                else match_group_atomic_kernel<<<blocks,kThreads>>>(d_keys.data(),d_hist.data(),n,cardinality);
            };
            auto check = [&] {
                ATLAS_CUDA(cudaMemset(d_hist.data(),0,static_cast<std::size_t>(cardinality)*sizeof(uint32_t)));
                launch(); ATLAS_CUDA(cudaDeviceSynchronize()); const auto got = d_hist.copy_to();
                std::vector<uint32_t> expected(static_cast<std::size_t>(cardinality),0);
                for (auto k : keys) ++expected[k % static_cast<unsigned>(cardinality)];
                return std::equal(expected.begin(),expected.end(),got.begin());
            };
            c.valid = check(); c.metrics["correctness_checked_bins"] = cardinality;
            if (!c.valid) c.limitations.push_back("CPU histogram oracle mismatch");
            ATLAS_CUDA(cudaMemset(d_hist.data(),0,static_cast<std::size_t>(cardinality)*sizeof(uint32_t)));
            time_case(c,o,launch);
            c.limitations.push_back("Aggregated atomic baseline only; mask rank/select, payload widths, multiword selection and contention/uniformity sweeps remain incomplete.");
            return c;
        });
    }
    each_selected(o,cases,"E05","rank_select_small_masks",[&] { return run_rank_select(o); });
    if (cases.empty()) cases.push_back(atlas::skip("E05",o.text("variant",""),"unknown E05 variant"));
    return cases;
}

__global__ void shared_bank_kernel(uint32_t* out, int iterations, int mode) {
    __shared__ uint32_t data[1056];
    const int tid = threadIdx.x;
    for (int i = tid; i < 1056; i += blockDim.x) data[i] = static_cast<uint32_t>(i * 3 + 7);
    __syncthreads();
    const int lane = tid & 31;
    uint32_t acc = 0;
    for (int j = 0; j < iterations; ++j) {
        const int address = mode == 0 ? 0 : (mode == 1 ? lane * 32 : lane * 33);
        acc += data[address];
    }
    out[blockIdx.x * blockDim.x + tid] = acc;
}

__global__ void shared_warp_tile_kernel(const uint32_t* in, uint32_t* out, std::size_t n) {
    __shared__ uint32_t tile[128];
    const unsigned idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int warp_base = (threadIdx.x >> 5) << 5;
    const int lane = threadIdx.x & 31;
    const uint32_t value = idx < n ? in[idx] : 0u;
    tile[threadIdx.x] = value;
    __syncthreads();
    const int next = warp_base + ((lane + 1) & 31);
    if (idx < n) out[idx] = tile[next];
}

__global__ void shuffle_warp_tile_kernel(const uint32_t* in, uint32_t* out, std::size_t n) {
    const unsigned idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int lane = threadIdx.x & 31;
    const uint32_t value = idx < n ? in[idx] : 0u;
    const uint32_t next = __shfl_sync(kFullWarp, value, (lane + 1) & 31);
    if (idx < n) out[idx] = next;
}

Cases run_e06(const Options& o) {
    Cases cases;
    const int iterations = std::min(o.iterations, 100000);
    const std::size_t n = std::min<std::size_t>(std::max<std::size_t>(o.size, 128), 1u << 20);
    const int blocks = static_cast<int>((n + kThreads - 1) / kThreads);
    atlas::DeviceBuffer<uint32_t> d_out(static_cast<std::size_t>(blocks*kThreads));
    const std::array<const char*,3> bank_names{{"broadcast", "same_bank_conflict", "padded_banks"}};
    for (int mode=0; mode<3; ++mode) {
        const std::string name = std::string("bank_") + bank_names[mode];
        each_selected(o,cases,"E06",name,[&] {
            CaseResult c; c.experiment="E06"; c.variant=name;
            add_common(c,o,iterations,static_cast<std::size_t>(blocks*kThreads),"shared values initialized identically on CPU/GPU; all 128 CTA threads reach __syncthreads");
            c.configuration["address_pattern"] = bank_names[mode];
            auto launch=[&] { shared_bank_kernel<<<blocks,kThreads>>>(d_out.data(),iterations,mode); };
            launch(); ATLAS_CUDA(cudaDeviceSynchronize()); const auto got=d_out.copy_to();
            const uint32_t expected_unit = mode==0 ? 7u : (mode==1 ? 7u : 7u);
            bool ok=true;
            // Values use the addressed word index, so validate each lane's exact address.
            for (std::size_t i=0;i<got.size();++i) {
                const int lane=static_cast<int>(i%kThreads)&31;
                const int addr=mode==0?0:(mode==1?lane*32:lane*33);
                const uint32_t e=static_cast<uint32_t>(addr*3+7)*static_cast<uint32_t>(iterations);
                ok=ok && got[i]==e;
            }
            (void)expected_unit;
            c.valid=ok; c.metrics["correctness_checked_threads"]=static_cast<double>(got.size());
            if(!ok)c.limitations.push_back("CPU shared-memory pattern oracle mismatch");
            time_case(c,o,launch);
            c.limitations.push_back("Bank mapping cases are analytical address patterns; no profiler bank-conflict counters, stride sweep, carveout or payload-width sweep collected here.");
            return c;
        });
    }
    atlas::DeviceBuffer<uint32_t> d_in(n),d_tile_out(n);
    std::vector<uint32_t> input(n); for(std::size_t i=0;i<n;++i) input[i]=static_cast<uint32_t>(i*17u+o.seed);
    d_in.copy_from(input);
    const int tile_blocks=static_cast<int>((n+kThreads-1)/kThreads);
    for(const std::string& variant:{"shared_tile","shuffle_tile"}) each_selected(o,cases,"E06",variant,[&] {
        CaseResult c; c.experiment="E06"; c.variant=variant;
        add_common(c,o,1,n,"warp-local cyclic next-lane permutation; partial final warp participates with padded lanes");
        auto launch=[&] {
            if(variant=="shared_tile") shared_warp_tile_kernel<<<tile_blocks,kThreads>>>(d_in.data(),d_tile_out.data(),n);
            else shuffle_warp_tile_kernel<<<tile_blocks,kThreads>>>(d_in.data(),d_tile_out.data(),n);
        };
        launch(); ATLAS_CUDA(cudaDeviceSynchronize()); const auto got=d_tile_out.copy_to(); bool ok=true;
        for(std::size_t i=0;i<n;++i) {
            const std::size_t warp_start=(i/32)*32;
            const std::size_t src=warp_start+((i+1-warp_start)%32);
            const uint32_t expected=src<n?input[src]:0u;
            ok=ok && got[i]==expected;
        }
        c.valid=ok; c.metrics["correctness_checked_outputs"]=static_cast<double>(n);
        if(!ok)c.limitations.push_back("CPU tile permutation oracle mismatch");
        time_case(c,o,launch);
        c.limitations.push_back("One warp-local permutation and one CTA tile size; producer-consumer phase pipelines, swizzles, padding and barrier-placement sweep remain incomplete.");
        return c;
    });
    if(cases.empty())cases.push_back(atlas::skip("E06",o.text("variant",""),"unknown E06 variant"));
    return cases;
}

__device__ __forceinline__ uint32_t parity_expression(uint32_t a,uint32_t b,uint32_t c) {
    return (a ^ b) ^ c;
}

__global__ void lop3_boolop_kernel(const uint32_t* a,const uint32_t* b,const uint32_t* c,
                                   const uint32_t* q,uint32_t* out,uint32_t* pred,std::size_t n) {
    const unsigned tid=blockIdx.x*blockDim.x+threadIdx.x;
    if(tid<n) {
        uint32_t d=0, p=0;
        asm volatile("{ .reg .pred q, p; setp.ne.u32 q, %5, 0; "
                     "lop3.or.b32 %0|p, %2, %3, %4, 0x96, q; "
                     "selp.u32 %1, 1, 0, p; }"
                     : "=r"(d), "=r"(p)
                     : "r"(a[tid]), "r"(b[tid]), "r"(c[tid]), "r"(q[tid]));
        out[tid]=d; pred[tid]=p;
    }
}

__global__ void lop3_and_boolop_kernel(const uint32_t* a,const uint32_t* b,const uint32_t* c,
                                       const uint32_t* q,uint32_t* out,uint32_t* pred,std::size_t n) {
    const unsigned tid=blockIdx.x*blockDim.x+threadIdx.x;
    if(tid<n) {
        uint32_t d=0, p=0;
        asm volatile("{ .reg .pred q, p; setp.ne.u32 q, %5, 0; "
                     "lop3.and.b32 %0|p, %2, %3, %4, 0xE8, q; "
                     "selp.u32 %1, 1, 0, p; }"
                     : "=r"(d), "=r"(p)
                     : "r"(a[tid]), "r"(b[tid]), "r"(c[tid]), "r"(q[tid]));
        out[tid]=d; pred[tid]=p;
    }
}

__global__ void lop3_expression_kernel(const uint32_t* a,const uint32_t* b,const uint32_t* c,
                                       const uint32_t* q,uint32_t* out,uint32_t* pred,std::size_t n) {
    const unsigned tid=blockIdx.x*blockDim.x+threadIdx.x;
    if(tid<n) {
        const uint32_t d=parity_expression(a[tid],b[tid],c[tid]);
        out[tid]=d; pred[tid]=static_cast<uint32_t>((d!=0) || q[tid]);
    }
}

Cases run_e37(const Options& o) {
    Cases cases;
    const std::size_t n=64; // 16 exhaustive bit assignments plus arbitrary-word adversarial operands.
    std::vector<uint32_t> ha(n),hb(n),hc(n),hq(n);
    for(unsigned i=0;i<16;++i) { ha[i]=(i>>0)&1u; hb[i]=(i>>1)&1u; hc[i]=(i>>2)&1u; hq[i]=(i>>3)&1u; }
    uint32_t state=o.seed;
    auto next=[&] { state=state*1664525u+1013904223u; return state; };
    for(std::size_t i=16;i<n;++i){ha[i]=next();hb[i]=next();hc[i]=next();hq[i]=next()&1u;}
    atlas::DeviceBuffer<uint32_t> da(n),db(n),dc(n),dq(n),dout(n),dpred(n);
    da.copy_from(ha);db.copy_from(hb);dc.copy_from(hc);dq.copy_from(hq);
    const int blocks=static_cast<int>((n+kThreads-1)/kThreads);
    for(const std::string& variant:{"lop3_boolop_or_parity","lop3_boolop_and_majority","cuda_expression_parity"}) each_selected(o,cases,"E37",variant,[&] {
        CaseResult r;r.experiment="E37";r.variant=variant;
        add_common(r,o,1,n,"all 8 Boolean input triples and both predicate inputs checked, plus 48 seeded full-width operands");
        r.configuration["ptx_form"] = variant=="lop3_boolop_or_parity" ? "lop3.or.b32 d|p,a,b,c,0x96,q" : (variant=="lop3_boolop_and_majority" ? "lop3.and.b32 d|p,a,b,c,0xE8,q" : "CUDA XOR expression plus (d!=0)||q");
        auto launch=[&] {
            if(variant=="lop3_boolop_or_parity")lop3_boolop_kernel<<<blocks,kThreads>>>(da.data(),db.data(),dc.data(),dq.data(),dout.data(),dpred.data(),n);
            else if(variant=="lop3_boolop_and_majority")lop3_and_boolop_kernel<<<blocks,kThreads>>>(da.data(),db.data(),dc.data(),dq.data(),dout.data(),dpred.data(),n);
            else lop3_expression_kernel<<<blocks,kThreads>>>(da.data(),db.data(),dc.data(),dq.data(),dout.data(),dpred.data(),n);
        };
        launch();ATLAS_CUDA(cudaDeviceSynchronize());const auto got=dout.copy_to(),gp=dpred.copy_to();bool ok=true;
        for(std::size_t i=0;i<n;++i){
            const uint32_t d=variant=="lop3_boolop_and_majority" ? ((ha[i]&hb[i])|(ha[i]&hc[i])|(hb[i]&hc[i])) : ((ha[i]^hb[i])^hc[i]);
            const uint32_t p=variant=="lop3_boolop_and_majority" ? static_cast<uint32_t>((d!=0)&&(hq[i]!=0)) : static_cast<uint32_t>((d!=0)||(hq[i]!=0));
            const bool word_ok=got[i]==d&&gp[i]==p;
            if (!word_ok && ok) {
                std::ostringstream detail;
                detail << "CPU LUT/predicate oracle mismatch at word=" << i
                       << " a=" << ha[i] << " b=" << hb[i] << " c=" << hc[i]
                       << " q=" << hq[i] << " observed_result=" << got[i]
                       << " expected_result=" << d << " observed_predicate=" << gp[i]
                       << " expected_predicate=" << p;
                r.limitations.push_back(detail.str());
            }
            ok=ok&&word_ok;
        }
        r.valid=ok;r.metrics["correctness_checked_words"]=static_cast<double>(n);r.metrics["exhaustive_boolean_cases"]=16.0;
        if(!ok && r.limitations.empty())r.limitations.push_back("CPU LUT/predicate oracle mismatch");
        time_case(r,o,launch);
        r.limitations.push_back("Three representative truth functions only; not all 256 LUT immediates, SASS predicate-path inspection or broad expression/liveness sweep. PTX BoolOp acceptance is established only by successful compile/runtime on the selected toolchain.");
        return r;
    });
    if(cases.empty())cases.push_back(atlas::skip("E37",o.text("variant",""),"unknown E37 variant"));
    return cases;
}

} // namespace

atlas::Cases run_logic(const atlas::Options& options) {
    const std::string id=options.experiment;
    if(id=="E02")return run_e02(options);
    if(id=="E03")return run_e03(options);
    if(id=="E05")return run_e05(options);
    if(id=="E06")return run_e06(options);
    if(id=="E37")return run_e37(options);
    return {atlas::skip(id,"logic","logic module supports only E02,E03,E05,E06,E37")};
}

int main(int argc, char** argv) {
    return atlas::main(argc, argv, run_logic);
}
