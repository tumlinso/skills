#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  debug_perf.sh [options] -- command [args...]

Options:
  --out-dir DIR   Output directory. Default: ./debug_out/perf
  --label LABEL   Run label. Default: UTC timestamp
  --events LIST   Comma-separated perf stat events
  -h, --help      Show this help

The wrapper runs perf stat with a small default counter set and emits a compact
summary intended for quick CPU-side diagnosis rather than full benchmark work.
EOF
}

OUT_DIR="./debug_out/perf"
LABEL="$(date -u +%Y%m%dT%H%M%SZ)"
EVENTS="task-clock,cycles,instructions,branches,branch-misses,cache-references,cache-misses"

resolve_perf() {
  if [[ -n "${PERF_BIN:-}" && -x "${PERF_BIN}" ]]; then
    printf '%s\n' "${PERF_BIN}"
    return 0
  fi
  if command -v perf >/dev/null 2>&1; then
    command -v perf
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
    --events)
      EVENTS="$2"
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
  printf 'Missing command to profile.\n\n' >&2
  usage >&2
  exit 2
fi

if ! PERF_BIN="$(resolve_perf)"; then
  printf 'Could not find perf.\n' >&2
  exit 127
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${OUT_DIR%/}/${LABEL}"
SUMMARY_FILE="${RUN_DIR}/summary.txt"
SUMMARY_JSON="${RUN_DIR}/summary.json"
PERF_CSV="${RUN_DIR}/perf_stat.csv"
COMMAND_STDOUT="${RUN_DIR}/stdout.txt"
COMMAND_STDERR="${RUN_DIR}/stderr.txt"
RUN_CONFIG="${RUN_DIR}/run_config.json"

mkdir -p "${RUN_DIR}"

{
  printf '{\n'
  printf '  "utc_timestamp": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '  "hostname": "%s",\n' "$(hostname)"
  printf '  "pwd": "%s",\n' "$(pwd)"
  printf '  "perf_bin": "%s",\n' "${PERF_BIN}"
  printf '  "events": "%s",\n' "${EVENTS}"
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
"${PERF_BIN}" stat -x, -e "${EVENTS}" -o "${PERF_CSV}" -- "$@" > "${COMMAND_STDOUT}" 2> "${COMMAND_STDERR}"
TARGET_STATUS=$?
set -e

python3 "${SCRIPT_DIR}/classify_native_failure.py" \
  --mode perf \
  --log "${PERF_CSV}" \
  --stdout "${COMMAND_STDOUT}" \
  --stderr "${COMMAND_STDERR}" \
  --exit-code "${TARGET_STATUS}" \
  --tool "${EVENTS}" \
  --command "$(printf '%q ' "$@")" \
  --json-out "${SUMMARY_JSON}" \
  > "${SUMMARY_FILE}"

printf 'Perf summary: %s\n\n' "${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
printf '\nArtifacts:\n'
printf -- '- perf counters: %s\n' "${PERF_CSV}"
printf -- '- stdout: %s\n' "${COMMAND_STDOUT}"
printf -- '- stderr: %s\n' "${COMMAND_STDERR}"

exit 0
