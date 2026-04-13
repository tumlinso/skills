#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  debug_compute_sanitizer.sh [options] -- command [args...]

Options:
  --out-dir DIR         Output directory. Default: ./debug_out/compute-sanitizer
  --label LABEL         Run label. Default: UTC timestamp
  --tool NAME           Sanitizer tool. Default: memcheck
  --crash-summary PATH  Optional prior crash summary JSON to combine
  -h, --help            Show this help

The wrapper runs compute-sanitizer (or cuda-memcheck as a memcheck fallback),
captures the raw log, and emits a compact summary before any raw artifact needs
to be read.
EOF
}

OUT_DIR="./debug_out/compute-sanitizer"
LABEL="$(date -u +%Y%m%dT%H%M%SZ)"
TOOL="memcheck"
CRASH_SUMMARY=""

resolve_sanitizer() {
  local candidates=(
    "${COMPUTE_SANITIZER_BIN:-}"
    "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/compilers/bin/compute-sanitizer"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  if command -v compute-sanitizer >/dev/null 2>&1; then
    command -v compute-sanitizer
    return 0
  fi
  if [[ "${TOOL}" == "memcheck" ]]; then
    if [[ -x "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/compilers/bin/cuda-memcheck" ]]; then
      printf '%s\n' "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/compilers/bin/cuda-memcheck"
      return 0
    fi
    if command -v cuda-memcheck >/dev/null 2>&1; then
      command -v cuda-memcheck
      return 0
    fi
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
    --tool)
      TOOL="$2"
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

if ! SANITIZER_BIN="$(resolve_sanitizer)"; then
  printf 'Could not find compute-sanitizer or compatible fallback.\n' >&2
  exit 127
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${OUT_DIR%/}/${LABEL}"
SUMMARY_FILE="${RUN_DIR}/summary.txt"
SUMMARY_JSON="${RUN_DIR}/summary.json"
RAW_LOG="${RUN_DIR}/raw.log"
COMMAND_STDOUT="${RUN_DIR}/stdout.txt"
COMMAND_STDERR="${RUN_DIR}/stderr.txt"
RUN_CONFIG="${RUN_DIR}/run_config.json"
COMBINED_TEXT="${RUN_DIR}/combined_summary.txt"
COMBINED_JSON="${RUN_DIR}/combined_summary.json"

mkdir -p "${RUN_DIR}"

{
  printf '{\n'
  printf '  "utc_timestamp": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '  "hostname": "%s",\n' "$(hostname)"
  printf '  "pwd": "%s",\n' "$(pwd)"
  printf '  "tool": "%s",\n' "${TOOL}"
  printf '  "sanitizer_bin": "%s",\n' "${SANITIZER_BIN}"
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
if [[ "$(basename "${SANITIZER_BIN}")" == "cuda-memcheck" ]]; then
  "${SANITIZER_BIN}" --log-file "${RAW_LOG}" \
    bash -lc 'out="$1"; err="$2"; shift 2; exec "$@" >"$out" 2>"$err"' \
    bash "${COMMAND_STDOUT}" "${COMMAND_STDERR}" "$@"
else
  "${SANITIZER_BIN}" --tool "${TOOL}" --log-file "${RAW_LOG}" --target-processes all \
    bash -lc 'out="$1"; err="$2"; shift 2; exec "$@" >"$out" 2>"$err"' \
    bash "${COMMAND_STDOUT}" "${COMMAND_STDERR}" "$@"
fi
TARGET_STATUS=$?
set -e

python3 "${SCRIPT_DIR}/classify_cuda_failure.py" \
  --mode compute-sanitizer \
  --stdout "${COMMAND_STDOUT}" \
  --stderr "${COMMAND_STDERR}" \
  --log "${RAW_LOG}" \
  --tool "${TOOL}" \
  --exit-code "${TARGET_STATUS}" \
  --command "$(printf '%q ' "$@")" \
  --json-out "${SUMMARY_JSON}" \
  > "${SUMMARY_FILE}"

if [[ -n "${CRASH_SUMMARY}" && -f "${CRASH_SUMMARY}" ]]; then
  python3 "${SCRIPT_DIR}/combine_debug_summaries.py" \
    --crash "${CRASH_SUMMARY}" \
    --sanitizer "${SUMMARY_JSON}" \
    --json-out "${COMBINED_JSON}" \
    --text-out "${COMBINED_TEXT}" > /dev/null || true
fi

printf 'Compute Sanitizer summary: %s\n\n' "${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
if [[ -f "${COMBINED_TEXT}" ]]; then
  printf '\nCombined summary: %s\n' "${COMBINED_TEXT}"
fi
printf '\nArtifacts:\n'
printf -- '- raw log: %s\n' "${RAW_LOG}"
printf -- '- stdout: %s\n' "${COMMAND_STDOUT}"
printf -- '- stderr: %s\n' "${COMMAND_STDERR}"

exit 0
