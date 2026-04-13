#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  with_benchmark_mutex.sh [options] -- command [args...]

Options:
  --lock-file PATH   Mutex path. Default: $COMPARE_BENCHMARK_MUTEX_PATH or /tmp/compare_benchmarks.lock
  --label LABEL      Human-readable run label. Default: command basename
  -h, --help         Show this help

Use this wrapper for any benchmark or profiler command that can skew results if
another agent is already driving the machine. The wrapper waits for the shared
mutex, runs the command, and then releases it.
EOF
}

LOCK_FILE="${COMPARE_BENCHMARK_MUTEX_PATH:-${TMPDIR:-/tmp}/compare_benchmarks.lock}"
LABEL=""
LOCK_FD=""
LOCK_HELD=0

release_lock() {
  if [[ "${LOCK_HELD}" == "1" && -n "${LOCK_FD}" ]]; then
    flock -u "${LOCK_FD}" || true
    printf '[compare-mutex] released %s via %s\n' "${LABEL}" "${LOCK_FILE}" >&2
    eval "exec ${LOCK_FD}>&-"
    LOCK_HELD=0
  fi
}

trap 'release_lock' EXIT
trap 'release_lock; exit 130' INT
trap 'release_lock; exit 143' TERM

while (($# > 0)); do
  case "$1" in
    --lock-file)
      LOCK_FILE="$2"
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
  printf 'Missing command to run under the benchmark mutex.\n\n' >&2
  usage >&2
  exit 2
fi

if ! command -v flock >/dev/null 2>&1; then
  printf 'Could not find flock. Install util-linux or add flock to PATH.\n' >&2
  exit 127
fi

LABEL="${LABEL:-$(basename "$1")}"
mkdir -p "$(dirname "${LOCK_FILE}")"

exec {LOCK_FD}> "${LOCK_FILE}"
if ! flock -n "${LOCK_FD}"; then
  printf '[compare-mutex] waiting for %s via %s\n' "${LABEL}" "${LOCK_FILE}" >&2
  flock "${LOCK_FD}"
fi

LOCK_HELD=1
printf '[compare-mutex] acquired %s via %s\n' "${LABEL}" "${LOCK_FILE}" >&2

set +e
"$@"
STATUS=$?
set -e

exit "${STATUS}"
