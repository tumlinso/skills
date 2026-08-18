#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  debug_crash.sh [options] -- command [args...]

Options:
  --out-dir DIR   Output directory. Default: ./debug_out/crash
  --label LABEL   Run label. Default: UTC timestamp
  -h, --help      Show this help

The wrapper captures stdout, stderr, exit status, and a compact crash summary
for a potentially failing command. It does not require the target to exit
cleanly in order to produce artifacts.
EOF
}

OUT_DIR="./debug_out/crash"
LABEL="$(date -u +%Y%m%dT%H%M%SZ)"

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${OUT_DIR%/}/${LABEL}"
SUMMARY_FILE="${RUN_DIR}/summary.txt"
SUMMARY_JSON="${RUN_DIR}/summary.json"
COMMAND_STDOUT="${RUN_DIR}/stdout.txt"
COMMAND_STDERR="${RUN_DIR}/stderr.txt"
RUN_CONFIG="${RUN_DIR}/run_config.json"

mkdir -p "${RUN_DIR}"

{
  printf '{\n'
  printf '  "utc_timestamp": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '  "hostname": "%s",\n' "$(hostname)"
  printf '  "pwd": "%s",\n' "$(pwd)"
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
"$@" > "${COMMAND_STDOUT}" 2> "${COMMAND_STDERR}"
TARGET_STATUS=$?
set -e

SIGNAL_NAME=""
SIGNAL_NUM=""
if ((TARGET_STATUS > 128)); then
  SIGNAL_NUM="$((TARGET_STATUS - 128))"
  if SIGNAL_NAME="$(kill -l "${SIGNAL_NUM}" 2>/dev/null)"; then
    :
  else
    SIGNAL_NAME="SIG${SIGNAL_NUM}"
  fi
fi

python3 "${SCRIPT_DIR}/classify_cuda_failure.py" \
  --mode crash \
  --stdout "${COMMAND_STDOUT}" \
  --stderr "${COMMAND_STDERR}" \
  --exit-code "${TARGET_STATUS}" \
  --signal "${SIGNAL_NAME}" \
  --command "$(printf '%q ' "$@")" \
  --json-out "${SUMMARY_JSON}" \
  > "${SUMMARY_FILE}"

printf 'Crash summary: %s\n\n' "${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
printf '\nArtifacts:\n'
printf -- '- stdout: %s\n' "${COMMAND_STDOUT}"
printf -- '- stderr: %s\n' "${COMMAND_STDERR}"

exit 0
