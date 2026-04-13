#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  debug_strace.sh [options] -- command [args...]

Options:
  --out-dir DIR         Output directory. Default: ./debug_out/strace
  --label LABEL         Run label. Default: UTC timestamp
  --crash-summary PATH  Optional prior crash summary JSON to combine
  -h, --help            Show this help

The wrapper runs strace with fork following, captures stdout and stderr from the
target, and emits a compact summary so the full syscall trace only needs to be
read when the summary remains ambiguous.
EOF
}

OUT_DIR="./debug_out/strace"
LABEL="$(date -u +%Y%m%dT%H%M%SZ)"
CRASH_SUMMARY=""

resolve_strace() {
  if [[ -n "${STRACE_BIN:-}" && -x "${STRACE_BIN}" ]]; then
    printf '%s\n' "${STRACE_BIN}"
    return 0
  fi
  if command -v strace >/dev/null 2>&1; then
    command -v strace
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

if ! STRACE_BIN="$(resolve_strace)"; then
  printf 'Could not find strace.\n' >&2
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
  printf '  "strace_bin": "%s",\n' "${STRACE_BIN}"
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
"${STRACE_BIN}" -f -tt -s 160 -o "${RAW_LOG}" -- "$@" > "${COMMAND_STDOUT}" 2> "${COMMAND_STDERR}"
TARGET_STATUS=$?
set -e

python3 "${SCRIPT_DIR}/classify_native_failure.py" \
  --mode strace \
  --log "${RAW_LOG}" \
  --stdout "${COMMAND_STDOUT}" \
  --stderr "${COMMAND_STDERR}" \
  --exit-code "${TARGET_STATUS}" \
  --command "$(printf '%q ' "$@")" \
  --json-out "${SUMMARY_JSON}" \
  > "${SUMMARY_FILE}"

if [[ -n "${CRASH_SUMMARY}" && -f "${CRASH_SUMMARY}" ]]; then
  python3 "${SCRIPT_DIR}/combine_debug_summaries.py" \
    --crash "${CRASH_SUMMARY}" \
    --strace "${SUMMARY_JSON}" \
    --json-out "${COMBINED_JSON}" \
    --text-out "${COMBINED_TEXT}" > /dev/null || true
fi

printf 'Strace summary: %s\n\n' "${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
if [[ -f "${COMBINED_TEXT}" ]]; then
  printf '\nCombined summary: %s\n' "${COMBINED_TEXT}"
fi
printf '\nArtifacts:\n'
printf -- '- raw log: %s\n' "${RAW_LOG}"
printf -- '- stdout: %s\n' "${COMMAND_STDOUT}"
printf -- '- stderr: %s\n' "${COMMAND_STDERR}"

exit 0
