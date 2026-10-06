#pragma once

// Shared command-line, measurement, CUDA error, and JSON support for the
// executable V100 benchmark modules. Each executable writes exactly one JSON
// document to stdout; diagnostics belong on stderr.

#include <cuda_runtime.h>

#if __has_include(<nvtx3/nvToolsExt.h>)
#include <nvtx3/nvToolsExt.h>
#define ATLAS_HAS_NVTX 1
#elif __has_include(<nvToolsExt.h>)
#include <nvToolsExt.h>
#define ATLAS_HAS_NVTX 1
#else
#define ATLAS_HAS_NVTX 0
#endif

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace atlas {

template <class Integer>
inline Integer parse_integer(const std::string& value, const std::string& option) {
    static_assert(std::is_integral<Integer>::value, "parse_integer requires an integral type");
    std::size_t consumed = 0;
    try {
        if constexpr (std::is_unsigned<Integer>::value) {
            if (!value.empty() && value.front() == '-')
                throw std::invalid_argument("negative value");
            const unsigned long long parsed = std::stoull(value, &consumed, 10);
            if (consumed != value.size() || parsed > std::numeric_limits<Integer>::max())
                throw std::out_of_range("value out of range");
            return static_cast<Integer>(parsed);
        } else {
            const long long parsed = std::stoll(value, &consumed, 10);
            if (consumed != value.size() || parsed < std::numeric_limits<Integer>::min() ||
                parsed > std::numeric_limits<Integer>::max())
                throw std::out_of_range("value out of range");
            return static_cast<Integer>(parsed);
        }
    } catch (const std::exception&) {
        throw std::invalid_argument("--" + option + " requires a valid in-range integer");
    }
}

struct Options {
    std::string experiment;
    int warmup = 5;
    int repeats = 30;
    std::size_t size = 65536;
    int iterations = 1;
    int device = 0;
    int peer = 1;
    unsigned seed = 20261006;
    bool verify_only = false;
    bool profile_friendly = false;
    std::map<std::string, std::string> args;

    int integer(const std::string& key, int fallback) const {
        const auto it = args.find(key);
        if (it == args.end()) return fallback;
        return parse_integer<int>(it->second, key);
    }

    std::string text(const std::string& key, const std::string& fallback) const {
        const auto it = args.find(key);
        return it == args.end() ? fallback : it->second;
    }
};

struct CaseResult {
    std::string experiment;
    std::string variant;
    std::string status = "GPU_RUN";
    bool valid = true;
    std::map<std::string, std::string> configuration;
    std::map<std::string, double> metrics;
    std::map<std::string, std::vector<double>> samples;
    std::vector<std::string> limitations;
};

using Cases = std::vector<CaseResult>;

inline std::runtime_error cuda_error(cudaError_t error, const char* expression,
                                     const char* file, int line) {
    std::ostringstream out;
    out << file << ':' << line << ": " << expression << ": "
        << cudaGetErrorName(error) << " (" << cudaGetErrorString(error) << ')';
    return std::runtime_error(out.str());
}

#define ATLAS_CUDA(expr)                                                        \
    do {                                                                        \
        const cudaError_t atlas_cuda_error__ = (expr);                           \
        if (atlas_cuda_error__ != cudaSuccess)                                  \
            throw ::atlas::cuda_error(atlas_cuda_error__, #expr, __FILE__,      \
                                      __LINE__);                                \
    } while (false)

template <class T>
class DeviceBuffer {
    static_assert(!std::is_void<T>::value, "DeviceBuffer element type cannot be void");
public:
    explicit DeviceBuffer(std::size_t count) : count_(count) {
        if (count_ > std::numeric_limits<std::size_t>::max() / sizeof(T))
            throw std::overflow_error("DeviceBuffer byte size overflow");
        if (count_) ATLAS_CUDA(cudaMalloc(reinterpret_cast<void**>(&ptr_), count_ * sizeof(T)));
    }
    ~DeviceBuffer() { if (ptr_) cudaFree(ptr_); }
    DeviceBuffer(const DeviceBuffer&) = delete;
    DeviceBuffer& operator=(const DeviceBuffer&) = delete;
    DeviceBuffer(DeviceBuffer&& other) noexcept : ptr_(other.ptr_), count_(other.count_) {
        other.ptr_ = nullptr;
        other.count_ = 0;
    }
    DeviceBuffer& operator=(DeviceBuffer&& other) noexcept {
        if (this != &other) {
            if (ptr_) cudaFree(ptr_);
            ptr_ = other.ptr_;
            count_ = other.count_;
            other.ptr_ = nullptr;
            other.count_ = 0;
        }
        return *this;
    }

    T* data() noexcept { return ptr_; }
    const T* data() const noexcept { return ptr_; }
    std::size_t size() const noexcept { return count_; }

    void copy_from(const std::vector<T>& host) {
        if (host.size() != count_) throw std::invalid_argument("DeviceBuffer copy_from size mismatch");
        if (count_) ATLAS_CUDA(cudaMemcpy(ptr_, host.data(), count_ * sizeof(T), cudaMemcpyHostToDevice));
    }

    std::vector<T> copy_to() const {
        std::vector<T> host(count_);
        if (count_) ATLAS_CUDA(cudaMemcpy(host.data(), ptr_, count_ * sizeof(T), cudaMemcpyDeviceToHost));
        return host;
    }

private:
    T* ptr_ = nullptr;
    std::size_t count_ = 0;
};

template <class Callable>
std::vector<double> measure(const Options& options, Callable&& callable,
                            cudaStream_t stream = nullptr) {
    const int warmups = options.verify_only ? 0 : std::max(0, options.warmup);
    const int repeats = options.verify_only ? 1 : std::max(1, options.repeats);
    for (int i = 0; i < warmups; ++i) {
        callable();
        ATLAS_CUDA(cudaGetLastError());
    }
    ATLAS_CUDA(cudaStreamSynchronize(stream));

    cudaEvent_t start = nullptr, stop = nullptr;
    ATLAS_CUDA(cudaEventCreate(&start));
    try {
        ATLAS_CUDA(cudaEventCreate(&stop));
        std::vector<double> elapsed;
        elapsed.reserve(static_cast<std::size_t>(repeats));
        for (int i = 0; i < repeats; ++i) {
            ATLAS_CUDA(cudaEventRecord(start, stream));
            callable();
            ATLAS_CUDA(cudaGetLastError());
            ATLAS_CUDA(cudaEventRecord(stop, stream));
            ATLAS_CUDA(cudaEventSynchronize(stop));
            float milliseconds = 0.0f;
            ATLAS_CUDA(cudaEventElapsedTime(&milliseconds, start, stop));
            elapsed.push_back(static_cast<double>(milliseconds));
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

template <class Callable>
std::vector<double> wall_measure(const Options& options, Callable&& callable,
                                 cudaStream_t stream = nullptr) {
    const int warmups = options.verify_only ? 0 : std::max(0, options.warmup);
    const int repeats = options.verify_only ? 1 : std::max(1, options.repeats);
    for (int i = 0; i < warmups; ++i) {
        callable();
        ATLAS_CUDA(cudaGetLastError());
        ATLAS_CUDA(cudaStreamSynchronize(stream));
    }
    std::vector<double> elapsed;
    elapsed.reserve(static_cast<std::size_t>(repeats));
    for (int i = 0; i < repeats; ++i) {
        ATLAS_CUDA(cudaStreamSynchronize(stream));
        const auto begin = std::chrono::steady_clock::now();
        callable();
        ATLAS_CUDA(cudaGetLastError());
        ATLAS_CUDA(cudaStreamSynchronize(stream));
        const auto end = std::chrono::steady_clock::now();
        elapsed.push_back(std::chrono::duration<double, std::milli>(end - begin).count());
    }
    return elapsed;
}

class Phase {
public:
    explicit Phase(const std::string& name) {
#if ATLAS_HAS_NVTX
        range_ = nvtxRangeStartA(name.c_str());
#else
        (void)name;
#endif
    }
    ~Phase() {
#if ATLAS_HAS_NVTX
        if (range_) nvtxRangeEnd(range_);
#endif
    }
    Phase(const Phase&) = delete;
    Phase& operator=(const Phase&) = delete;
private:
#if ATLAS_HAS_NVTX
    nvtxRangeId_t range_ = 0;
#endif
};

inline CaseResult skip(const std::string& experiment, const std::string& variant,
                       const std::string& reason, const std::string& status = "NOT_RUN") {
    CaseResult result;
    result.experiment = experiment;
    result.variant = variant;
    result.status = status;
    result.valid = false;
    result.limitations.push_back(reason);
    return result;
}

inline std::string json_quote(const std::string& value) {
    std::ostringstream out;
    out << '"';
    for (const unsigned char c : value) {
        switch (c) {
        case '"': out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\b': out << "\\b"; break;
        case '\f': out << "\\f"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (c < 0x20) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c) << std::dec;
            else out << static_cast<char>(c);
        }
    }
    out << '"';
    return out.str();
}

inline bool is_known_case_status(const std::string& status) {
    return status == "GPU_RUN" || status == "CPU_ONLY" ||
           status == "COMPILED_ONLY" || status == "NOT_RUN" ||
           status == "INCONCLUSIVE";
}

inline void write_json(const Options& options, const Cases& cases) {
    bool all_valid = true;
    std::cout << "{\"experiment\":" << json_quote(options.experiment)
              << ",\"checks\":{\"valid\":";
    for (const auto& item : cases) {
        if (item.status == "NOT_RUN") continue;
        all_valid = all_valid && is_known_case_status(item.status) &&
                    item.status != "INCONCLUSIVE" && item.valid;
    }
    std::cout << (all_valid ? "true" : "false") << "},\"cases\":[";
    for (std::size_t i = 0; i < cases.size(); ++i) {
        const auto& item = cases[i];
        if (i) std::cout << ',';
        std::cout << "{\"experiment\":" << json_quote(item.experiment)
                  << ",\"variant\":" << json_quote(item.variant)
                  << ",\"status\":" << json_quote(item.status)
                  << ",\"checks\":{\"valid\":" << (item.valid ? "true" : "false") << "},\"configuration\":{";
        bool first = true;
        for (const auto& entry : item.configuration) {
            if (!first) std::cout << ',';
            first = false;
            std::cout << json_quote(entry.first) << ':' << json_quote(entry.second);
        }
        std::cout << "},\"metrics\":{";
        first = true;
        for (const auto& entry : item.metrics) {
            if (!first) std::cout << ',';
            first = false;
            std::cout << json_quote(entry.first) << ':';
            if (std::isfinite(entry.second)) std::cout << std::setprecision(17) << entry.second;
            else std::cout << "null";
        }
        std::cout << "},\"samples\":{";
        first = true;
        for (const auto& entry : item.samples) {
            if (!first) std::cout << ',';
            first = false;
            std::cout << json_quote(entry.first) << ":[";
            for (std::size_t j = 0; j < entry.second.size(); ++j) {
                if (j) std::cout << ',';
                if (std::isfinite(entry.second[j])) std::cout << std::setprecision(17) << entry.second[j];
                else std::cout << "null";
            }
            std::cout << ']';
        }
        std::cout << "},\"limitations\":[";
        for (std::size_t j = 0; j < item.limitations.size(); ++j) {
            if (j) std::cout << ',';
            std::cout << json_quote(item.limitations[j]);
        }
        std::cout << "]}";
    }
    std::cout << "]}\n";
}

inline Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        std::string key = argv[i];
        if (key.rfind("--", 0) != 0) throw std::invalid_argument("unexpected positional argument: " + key);
        key.erase(0, 2);
        if (key == "verify-only" || key == "profile-friendly") {
            if (key == "verify-only") options.verify_only = true;
            else options.profile_friendly = true;
            options.args[key] = "true";
            continue;
        }
        if (i + 1 >= argc || std::string(argv[i + 1]).rfind("--", 0) == 0)
            throw std::invalid_argument("--" + key + " requires a value");
        const std::string value = argv[++i];
        options.args[key] = value;
        if (key == "experiment") options.experiment = value;
        else if (key == "size") options.size = parse_integer<std::size_t>(value, key);
        else if (key == "iterations") options.iterations = parse_integer<int>(value, key);
        else if (key == "device") options.device = parse_integer<int>(value, key);
        else if (key == "peer") options.peer = parse_integer<int>(value, key);
        else if (key == "warmup") options.warmup = parse_integer<int>(value, key);
        else if (key == "repeats") options.repeats = parse_integer<int>(value, key);
        else if (key == "seed") options.seed = parse_integer<unsigned>(value, key);
    }
    if (options.experiment.empty()) throw std::invalid_argument("--experiment is required");
    if (options.size == 0 || options.iterations < 1 || options.warmup < 0 || options.repeats < 1)
        throw std::invalid_argument("size/repeats must be positive; iterations positive; warmup nonnegative");
    return options;
}

inline bool is_timing_sample_key(const std::string& key) {
    return key.size() >= 3 && key.compare(key.size() - 3, 3, "_ms") == 0;
}

template <class Runner>
int main(int argc, char** argv, Runner&& runner) {
    try {
        Options options = parse_options(argc, argv);
        Cases cases = runner(options);
        if (cases.empty()) throw std::runtime_error("benchmark produced no cases");
        for (auto& item : cases) {
            if (item.status == "GPU_RUN" || item.status == "CPU_ONLY") {
                bool invalid_timing = false;
                for (const auto& entry : item.samples) {
                    if (!is_timing_sample_key(entry.first)) continue;
                    for (const double value : entry.second)
                        invalid_timing = invalid_timing || !std::isfinite(value);
                }
                if (invalid_timing) {
                    item.valid = false;
                    item.limitations.push_back("non-finite timing sample");
                }
            }
            if (item.status == "INCONCLUSIVE" || !is_known_case_status(item.status))
                item.valid = false;
        }
        write_json(options, cases);
        for (const auto& item : cases)
            if ((item.status != "NOT_RUN" && !item.valid) ||
                !is_known_case_status(item.status))
                return 3;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "atlas benchmark error: " << error.what() << '\n';
        return 2;
    }
}

} // namespace atlas
