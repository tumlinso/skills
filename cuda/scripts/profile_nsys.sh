#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  profile_nsys.sh [options] -- command [args...]

Options:
  --out-dir DIR            Output directory. Default: ./profile_out/nsys
  --label LABEL            Run label. Default: UTC timestamp
  --trace LIST             Nsight Systems trace set. Default: cuda,nvtx,osrt
  --sample MODE            Sampling mode. Default: none
  --gpu-metrics-device ID  Optional GPU metrics device selector
  --benchmark-summary P    Optional benchmark summary JSON to combine with this profile
  --show-command-output    Stream the target command output instead of capturing it to files
  --no-stats               Skip `nsys stats`
  -h, --help               Show this help

The wrapper prefers the full target-side `nsys` binary, captures noisy profiler
and command output to files, and prints a concise summary that says whether the
timeline is representative or should be rerun with cleaner steady-state data.
Benchmark-producing runs are serialized through the shared benchmark mutex.
EOF
}

OUT_DIR="./profile_out/nsys"
LABEL="$(date -u +%Y%m%dT%H%M%SZ)"
TRACE="cuda,nvtx,osrt"
SAMPLE="none"
GPU_METRICS_DEVICE=""
BENCHMARK_SUMMARY=""
RUN_STATS=1
SHOW_COMMAND_OUTPUT=0

resolve_nsys_bin() {
  local candidates=(
    "${NSYS_BIN:-}"
    "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/profilers/12.9/Nsight_Systems_2025.3/target-linux-x64/nsys"
    "/opt/nvidia/nsight-systems/2024.6.2/target-linux-x64/nsys"
    "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/compilers/bin/nsys"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  if command -v nsys >/dev/null 2>&1; then
    command -v nsys
    return 0
  fi
  return 1
}

while (($# > 0)); do
  case "$1" in
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --label)
      LABEL="$2"
      shift 2
      ;;
    --trace)
      TRACE="$2"
      shift 2
      ;;
    --sample)
      SAMPLE="$2"
      shift 2
      ;;
    --gpu-metrics-device)
      GPU_METRICS_DEVICE="$2"
      shift 2
      ;;
    --benchmark-summary)
      BENCHMARK_SUMMARY="$2"
      shift 2
      ;;
    --show-command-output)
      SHOW_COMMAND_OUTPUT=1
      shift
      ;;
    --no-stats)
      RUN_STATS=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if (($# == 0)); then
  printf 'Missing command to profile.\n\n' >&2
  usage >&2
  exit 2
fi

if ! NSYS_BIN="$(resolve_nsys_bin)"; then
  printf 'Could not find nsys. Set NSYS_BIN or install/add Nsight Systems to PATH.\n' >&2
  exit 127
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${OUT_DIR%/}/${LABEL}"
REPORT_PREFIX="${RUN_DIR}/report"
REPORT_FILE="${REPORT_PREFIX}.nsys-rep"
SUMMARY_FILE="${RUN_DIR}/summary.txt"
SUMMARY_JSON_FILE="${RUN_DIR}/summary.json"
ANALYSIS_FILE="${RUN_DIR}/analysis.txt"
COMBINED_SUMMARY_FILE="${RUN_DIR}/combined_summary.txt"
COMBINED_SUMMARY_JSON="${RUN_DIR}/combined_summary.json"
COMMAND_STDOUT="${RUN_DIR}/command.stdout.txt"
COMMAND_STDERR="${RUN_DIR}/command.stderr.txt"
PROFILER_STDOUT="${RUN_DIR}/profiler.stdout.txt"
PROFILER_STDERR="${RUN_DIR}/profiler.stderr.txt"
BENCHMARK_MUTEX_PATH="${CUDA_V100_BENCHMARK_MUTEX_PATH:-${TMPDIR:-/tmp}/cuda_v100_benchmark.lock}"
BENCHMARK_MUTEX_LABEL="nsys:${LABEL}"

mkdir -p "${RUN_DIR}"

{
  printf 'utc_timestamp=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'hostname=%s\n' "$(hostname)"
  printf 'pwd=%s\n' "$(pwd)"
  printf 'trace=%s\n' "${TRACE}"
  printf 'sample=%s\n' "${SAMPLE}"
  printf 'nsys_bin=%s\n' "${NSYS_BIN}"
  printf 'benchmark_summary=%s\n' "${BENCHMARK_SUMMARY}"
  printf 'benchmark_mutex_path=%s\n' "${BENCHMARK_MUTEX_PATH}"
  printf 'benchmark_mutex_label=%s\n' "${BENCHMARK_MUTEX_LABEL}"
  printf 'show_command_output=%s\n' "${SHOW_COMMAND_OUTPUT}"
  printf 'command='
  printf '%q ' "$@"
  printf '\n'
} > "${RUN_DIR}/run.env"

env | sort > "${RUN_DIR}/process_env.txt"

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L > "${RUN_DIR}/nvidia_smi_L.txt" || true
  nvidia-smi topo -m > "${RUN_DIR}/nvidia_smi_topo.txt" || true
  nvidia-smi --query-gpu=name,pci.bus_id,driver_version,memory.total --format=csv \
    > "${RUN_DIR}/nvidia_smi_query.csv" || true
fi

if command -v nvcc >/dev/null 2>&1; then
  nvcc --version > "${RUN_DIR}/nvcc_version.txt" || true
fi

"${NSYS_BIN}" --version > "${RUN_DIR}/nsys_version.txt" || true

NSYS_ARGS=(
  profile
  "--trace=${TRACE}"
  "--sample=${SAMPLE}"
  "-o" "${REPORT_PREFIX}"
)

if [[ -n "${GPU_METRICS_DEVICE}" ]]; then
  NSYS_ARGS+=("--gpu-metrics-device=${GPU_METRICS_DEVICE}")
fi

COMMAND=("$@")
if ((SHOW_COMMAND_OUTPUT)); then
  WRAPPED_COMMAND=("${COMMAND[@]}")
else
  WRAPPED_COMMAND=(
    bash
    -lc
    'out="$1"; err="$2"; shift 2; exec "$@" >"$out" 2>"$err"'
    bash
    "${COMMAND_STDOUT}"
    "${COMMAND_STDERR}"
    "${COMMAND[@]}"
  )
fi

"${SCRIPT_DIR}/with_benchmark_mutex.sh" \
  --lock-file "${BENCHMARK_MUTEX_PATH}" \
  --label "${BENCHMARK_MUTEX_LABEL}" \
  -- "${NSYS_BIN}" "${NSYS_ARGS[@]}" "${WRAPPED_COMMAND[@]}" \
  > "${PROFILER_STDOUT}" 2> "${PROFILER_STDERR}"

if [[ ! -f "${REPORT_FILE}" ]]; then
  printf 'Expected report file was not created: %s\n' "${REPORT_FILE}" >&2
  exit 1
fi

if ((RUN_STATS)); then
  if "${NSYS_BIN}" stats \
      --report cuda_api_sum,cuda_gpu_kern_sum,gpumemtimesum,nvtxsum \
      --format csv \
      --output "${RUN_DIR}/stats" \
      "${REPORT_FILE}" > "${RUN_DIR}/nsys_stats_stdout.txt" 2> "${RUN_DIR}/nsys_stats_stderr.txt"; then
    python3 "${SCRIPT_DIR}/analyze_nsys_stats.py" "${RUN_DIR}" --json-out "${SUMMARY_JSON_FILE}" \
      > "${SUMMARY_FILE}" || true
  fi
fi

if [[ ! -f "${SUMMARY_FILE}" ]]; then
  cat > "${SUMMARY_FILE}" <<EOF
V100 Nsight Systems Decision

status: partial
trace_valid: unknown
steady_state_timing_valid: unknown
needs_rerun_for_timing: yes
measurement_scope: timeline and setup behavior

decision:
- The wrapper did not produce a parsed summary. Inspect the raw report and stats files.

next_step: Open the report in the Nsight Systems UI or inspect profiler.stdout.txt and profiler.stderr.txt.
EOF
fi

cp "${SUMMARY_FILE}" "${ANALYSIS_FILE}"

if [[ -n "${BENCHMARK_SUMMARY}" && -f "${BENCHMARK_SUMMARY}" && -f "${SUMMARY_JSON_FILE}" ]]; then
  python3 "${SCRIPT_DIR}/combine_benchmark_summaries.py" \
    --benchmark "${BENCHMARK_SUMMARY}" \
    --nsys "${SUMMARY_JSON_FILE}" \
    --json-out "${COMBINED_SUMMARY_JSON}" \
    --text-out "${COMBINED_SUMMARY_FILE}" > /dev/null || true
fi

printf 'Nsight Systems summary: %s\n\n' "${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
if [[ -f "${COMBINED_SUMMARY_FILE}" ]]; then
  printf '\nCombined summary: %s\n' "${COMBINED_SUMMARY_FILE}"
fi
printf '\nArtifacts:\n'
printf -- '- report: %s\n' "${REPORT_FILE}"
printf -- '- command stdout: %s\n' "${COMMAND_STDOUT}"
printf -- '- command stderr: %s\n' "${COMMAND_STDERR}"
printf -- '- profiler stdout: %s\n' "${PROFILER_STDOUT}"
printf -- '- profiler stderr: %s\n' "${PROFILER_STDERR}"
