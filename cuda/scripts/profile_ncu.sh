#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  profile_ncu.sh [options] -- command [args...]

Options:
  --out-dir DIR         Output directory. Default: ./profile_out/ncu
  --label LABEL         Run label. Default: UTC timestamp
  --set NAME            Nsight Compute set. Overrides the default compact V100 metric list
  --section NAME        Extra section to request. May be repeated.
  --metrics LIST        Explicit metrics list. Overrides both the default list and `--set`
  --kernel-name-base X  Kernel naming mode. Default: demangled
  --target-processes X  Nsight Compute target process mode. Default: all
  --launch-count N      Optional launch count limit
  --kernel-name X       Optional exact/regex kernel filter passed to NCU
  --benchmark-summary P Optional benchmark summary JSON to combine with this profile
  --show-command-output Stream the target command output instead of capturing it to files
  -h, --help            Show this help

The wrapper captures profiler chatter and command output to files, then prints a
short summary that says whether the counters are usable and what limiter is most
likely on V100. Throughput decisions should still come from the benchmark or
Nsight Systems because Nsight Compute replay distorts timing. Benchmark-producing
runs are serialized through the shared benchmark mutex.
EOF
}

OUT_DIR="./profile_out/ncu"
LABEL="$(date -u +%Y%m%dT%H%M%SZ)"
SET_NAME=""
KERNEL_NAME_BASE="demangled"
TARGET_PROCESSES="all"
LAUNCH_COUNT=""
KERNEL_NAME=""
METRICS=""
BENCHMARK_SUMMARY=""
SHOW_COMMAND_OUTPUT=0
SECTIONS=()
DEFAULT_METRICS="gpu__time_duration.sum,dram__throughput.avg.pct_of_peak_sustained_elapsed,sm__throughput.avg.pct_of_peak_sustained_elapsed,smsp__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_elapsed,launch__occupancy_per_sm,launch__registers_per_thread,launch__shared_mem_per_block_allocated"

resolve_ncu_bin() {
  local candidates=(
    "${NCU_BIN:-}"
    "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/profilers/12.9/Nsight_Compute/ncu"
    "/opt/nvidia/nsight-compute/2025.1.0/ncu"
    "/opt/nvidia/nsight-compute/2025.1.0/host/linux-desktop-glibc_2_11_3-x64/ncu"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  if command -v ncu >/dev/null 2>&1; then
    command -v ncu
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
    --set)
      SET_NAME="$2"
      shift 2
      ;;
    --section)
      SECTIONS+=("$2")
      shift 2
      ;;
    --metrics)
      METRICS="$2"
      shift 2
      ;;
    --kernel-name-base)
      KERNEL_NAME_BASE="$2"
      shift 2
      ;;
    --target-processes)
      TARGET_PROCESSES="$2"
      shift 2
      ;;
    --launch-count)
      LAUNCH_COUNT="$2"
      shift 2
      ;;
    --kernel-name)
      KERNEL_NAME="$2"
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

if ! NCU_BIN="$(resolve_ncu_bin)"; then
  printf 'Could not find ncu. Set NCU_BIN or install/add Nsight Compute to PATH.\n' >&2
  exit 127
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${OUT_DIR%/}/${LABEL}"
REPORT_PREFIX="${RUN_DIR}/report"
REPORT_FILE="${REPORT_PREFIX}.ncu-rep"
CSV_FILE="${RUN_DIR}/raw.csv"
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
BENCHMARK_MUTEX_LABEL="ncu:${LABEL}"

mkdir -p "${RUN_DIR}"

{
  printf 'utc_timestamp=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'hostname=%s\n' "$(hostname)"
  printf 'pwd=%s\n' "$(pwd)"
  printf 'set=%s\n' "${SET_NAME}"
  printf 'kernel_name_base=%s\n' "${KERNEL_NAME_BASE}"
  printf 'target_processes=%s\n' "${TARGET_PROCESSES}"
  printf 'ncu_bin=%s\n' "${NCU_BIN}"
  printf 'benchmark_summary=%s\n' "${BENCHMARK_SUMMARY}"
  printf 'benchmark_mutex_path=%s\n' "${BENCHMARK_MUTEX_PATH}"
  printf 'benchmark_mutex_label=%s\n' "${BENCHMARK_MUTEX_LABEL}"
  printf 'show_command_output=%s\n' "${SHOW_COMMAND_OUTPUT}"
  printf 'metrics=%s\n' "${METRICS:-${DEFAULT_METRICS}}"
  if [[ -n "${LAUNCH_COUNT}" ]]; then
    printf 'launch_count=%s\n' "${LAUNCH_COUNT}"
  fi
  if [[ -n "${KERNEL_NAME}" ]]; then
    printf 'kernel_name=%s\n' "${KERNEL_NAME}"
  fi
  printf 'command='
  printf '%q ' "$@"
  printf '\n'
} > "${RUN_DIR}/run.env"

env | sort > "${RUN_DIR}/process_env.txt"

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L > "${RUN_DIR}/nvidia_smi_L.txt" || true
  nvidia-smi topo -m > "${RUN_DIR}/nvidia_smi_topo.txt" || true
fi

if command -v nvcc >/dev/null 2>&1; then
  nvcc --version > "${RUN_DIR}/nvcc_version.txt" || true
fi

"${NCU_BIN}" --version > "${RUN_DIR}/ncu_version.txt" || true

NCU_ARGS=(
  "--export" "${REPORT_PREFIX}"
  "--force-overwrite"
  "--target-processes" "${TARGET_PROCESSES}"
  "--kernel-name-base" "${KERNEL_NAME_BASE}"
)

if [[ -n "${METRICS}" ]]; then
  NCU_ARGS+=("--metrics" "${METRICS}")
elif [[ -n "${SET_NAME}" ]]; then
  NCU_ARGS+=("--set" "${SET_NAME}")
else
  NCU_ARGS+=("--metrics" "${DEFAULT_METRICS}")
fi

if [[ -n "${LAUNCH_COUNT}" ]]; then
  NCU_ARGS+=("--launch-count" "${LAUNCH_COUNT}")
fi

if [[ -n "${KERNEL_NAME}" ]]; then
  NCU_ARGS+=("--kernel-name" "${KERNEL_NAME}")
fi

for section in "${SECTIONS[@]}"; do
  NCU_ARGS+=("--section" "${section}")
done

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
  -- "${NCU_BIN}" "${NCU_ARGS[@]}" "${WRAPPED_COMMAND[@]}" \
  > "${PROFILER_STDOUT}" 2> "${PROFILER_STDERR}"

if [[ ! -f "${REPORT_FILE}" ]]; then
  printf 'Expected report file was not created: %s\n' "${REPORT_FILE}" >&2
  exit 1
fi

"${NCU_BIN}" --import "${REPORT_FILE}" --csv --page raw > "${CSV_FILE}"
python3 "${SCRIPT_DIR}/analyze_ncu_csv.py" "${RUN_DIR}" --json-out "${SUMMARY_JSON_FILE}" > "${SUMMARY_FILE}" || true

if [[ ! -f "${SUMMARY_FILE}" ]]; then
  cat > "${SUMMARY_FILE}" <<EOF
V100 Nsight Compute Decision

status: partial
counter_valid: unknown
timing_valid: no
needs_more_data: yes
measurement_scope: kernel counters

decision:
- The wrapper did not produce a parsed summary. Inspect raw.csv and the report file.

next_step: Open the report in Nsight Compute UI or inspect profiler.stdout.txt and profiler.stderr.txt.
EOF
fi

cp "${SUMMARY_FILE}" "${ANALYSIS_FILE}"

if [[ -n "${BENCHMARK_SUMMARY}" && -f "${BENCHMARK_SUMMARY}" && -f "${SUMMARY_JSON_FILE}" ]]; then
  python3 "${SCRIPT_DIR}/combine_benchmark_summaries.py" \
    --benchmark "${BENCHMARK_SUMMARY}" \
    --ncu "${SUMMARY_JSON_FILE}" \
    --json-out "${COMBINED_SUMMARY_JSON}" \
    --text-out "${COMBINED_SUMMARY_FILE}" > /dev/null || true
fi

printf 'Nsight Compute summary: %s\n\n' "${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
if [[ -f "${COMBINED_SUMMARY_FILE}" ]]; then
  printf '\nCombined summary: %s\n' "${COMBINED_SUMMARY_FILE}"
fi
printf '\nArtifacts:\n'
printf -- '- report: %s\n' "${REPORT_FILE}"
printf -- '- raw csv: %s\n' "${CSV_FILE}"
printf -- '- command stdout: %s\n' "${COMMAND_STDOUT}"
printf -- '- command stderr: %s\n' "${COMMAND_STDERR}"
printf -- '- profiler stdout: %s\n' "${PROFILER_STDOUT}"
printf -- '- profiler stderr: %s\n' "${PROFILER_STDERR}"
