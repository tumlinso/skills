#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  debug_cuda_gdb.sh [options] -- command [args...]

Options:
  --out-dir DIR         Output directory. Default: ./debug_out/cuda-gdb
  --label LABEL         Run label. Default: UTC timestamp
  --crash-summary PATH  Optional prior crash summary JSON to combine
  -h, --help            Show this help

The wrapper runs cuda-gdb in batch mode, captures a short backtrace-oriented
log, and emits a compact summary so the full debugger transcript rarely needs
to be read in-context.
EOF
}

OUT_DIR="./debug_out/cuda-gdb"
LABEL="$(date -u +%Y%m%dT%H%M%SZ)"
CRASH_SUMMARY=""

resolve_cuda_gdb() {
  local candidates=(
    "${CUDA_GDB_BIN:-}"
    "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/cuda/12.9/bin/cuda-gdb"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  if command -v cuda-gdb >/dev/null 2>&1; then
    command -v cuda-gdb
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
    --crash-summary)
      CRASH_SUMMARY="$2"
      shift 2
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
  printf 'Missing command to debug.\n\n' >&2
  usage >&2
  exit 2
fi

if ! CUDA_GDB_BIN="$(resolve_cuda_gdb)"; then
  printf 'Could not find cuda-gdb.\n' >&2
  exit 127
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${OUT_DIR%/}/${LABEL}"
SUMMARY_FILE="${RUN_DIR}/summary.txt"
SUMMARY_JSON="${RUN_DIR}/summary.json"
RAW_LOG="${RUN_DIR}/raw.log"
RUN_CONFIG="${RUN_DIR}/run_config.json"
GDB_COMMANDS="${RUN_DIR}/commands.gdb"
COMBINED_TEXT="${RUN_DIR}/combined_summary.txt"
COMBINED_JSON="${RUN_DIR}/combined_summary.json"

mkdir -p "${RUN_DIR}"

cat > "${GDB_COMMANDS}" <<'EOF'
set pagination off
set confirm off
set breakpoint pending on
set print thread-events off
set follow-fork-mode child
set detach-on-fork off
set width 0
handle SIGPIPE nostop noprint pass
handle SIGUSR1 nostop noprint pass
handle SIGUSR2 nostop noprint pass
catch signal SIGABRT
catch signal SIGSEGV
run
echo \n=== inferiors ===\n
info inferiors
echo \n=== backtrace ===\n
bt 8
echo \n=== threads ===\n
info threads
echo \n=== cuda kernels ===\n
info cuda kernels
echo \n=== cuda threads ===\n
info cuda threads
quit
EOF

{
  printf '{\n'
  printf '  "utc_timestamp": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '  "hostname": "%s",\n' "$(hostname)"
  printf '  "pwd": "%s",\n' "$(pwd)"
  printf '  "cuda_gdb_bin": "%s",\n' "${CUDA_GDB_BIN}"
  printf '  "command": '
  python3 - "$@" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1:]), end="")
PY
  printf '\n}\n'
} > "${RUN_CONFIG}"

env | sort > "${RUN_DIR}/process_env.txt"

set +e
"${CUDA_GDB_BIN}" --batch -x "${GDB_COMMANDS}" --args "$@" > "${RAW_LOG}" 2>&1
TARGET_STATUS=$?
set -e

python3 "${SCRIPT_DIR}/classify_cuda_failure.py" \
  --mode cuda-gdb \
  --log "${RAW_LOG}" \
  --exit-code "${TARGET_STATUS}" \
  --command "$(printf '%q ' "$@")" \
  --json-out "${SUMMARY_JSON}" \
  > "${SUMMARY_FILE}"

if [[ -n "${CRASH_SUMMARY}" && -f "${CRASH_SUMMARY}" ]]; then
  python3 "${SCRIPT_DIR}/combine_debug_summaries.py" \
    --crash "${CRASH_SUMMARY}" \
    --cuda-gdb "${SUMMARY_JSON}" \
    --json-out "${COMBINED_JSON}" \
    --text-out "${COMBINED_TEXT}" > /dev/null || true
fi

printf 'CUDA-GDB summary: %s\n\n' "${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
if [[ -f "${COMBINED_TEXT}" ]]; then
  printf '\nCombined summary: %s\n' "${COMBINED_TEXT}"
fi
printf '\nArtifacts:\n'
printf -- '- raw log: %s\n' "${RAW_LOG}"
printf -- '- command file: %s\n' "${GDB_COMMANDS}"

exit 0
