#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  with_benchmark_mutex.sh [options] -- command [args...]

Options:
  --lock-file PATH   Mutex path. Default: $CUDA_V100_BENCHMARK_MUTEX_PATH or /tmp/cuda_v100_benchmark.lock
  --label LABEL      Human-readable run label. Default: command basename
  -h, --help         Show this help

Use this wrapper for any benchmark or profiler command that can skew results if
another agent is already driving the GPUs. The wrapper waits for the shared
mutex, runs the command, and then releases it.
EOF
}

LOCK_FILE="${CUDA_V100_BENCHMARK_MUTEX_PATH:-${TMPDIR:-/tmp}/cuda_v100_benchmark.lock}"
LABEL=""
LOCK_FD=""
LOCK_HELD=0
COORDINATION_MODE="${CUDA_BENCHMARK_COORDINATION_MODE:-foreground}"
FOREGROUND_MARKER="${CUDA_BENCHMARK_FOREGROUND_INTENT_PATH:-}"
FOREGROUND_MARKER_OWNED=0
GPU_LOCK_FDS=()
BACKGROUND_PID=""

terminate_background() {
  if [[ -z "${BACKGROUND_PID}" ]]; then
    return 0
  fi
  kill -TERM -- "-${BACKGROUND_PID}" 2>/dev/null || true
  for _ in {1..10}; do
    kill -0 "${BACKGROUND_PID}" 2>/dev/null || break
    sleep 0.1
  done
  kill -KILL -- "-${BACKGROUND_PID}" 2>/dev/null || true
  wait "${BACKGROUND_PID}" 2>/dev/null || true
  BACKGROUND_PID=""
  return 0
}

release_lock() {
  terminate_background
  if ((${#GPU_LOCK_FDS[@]} > 0)); then
    for fd in "${GPU_LOCK_FDS[@]}"; do
      flock -u "${fd}" 2>/dev/null || true
      eval "exec ${fd}>&-"
    done
  fi
  GPU_LOCK_FDS=()
  if [[ "${LOCK_HELD}" == "1" && -n "${LOCK_FD}" ]]; then
    flock -u "${LOCK_FD}" || true
    printf '[benchmark-mutex] released %s via %s\n' "${LABEL}" "${LOCK_FILE}" >&2
    eval "exec ${LOCK_FD}>&-"
    LOCK_HELD=0
  fi
  if [[ "${FOREGROUND_MARKER_OWNED}" == "1" ]]; then
    if [[ "$(cat "${FOREGROUND_MARKER}" 2>/dev/null || true)" == "$$" ]]; then
      rm -f -- "${FOREGROUND_MARKER}"
    fi
    FOREGROUND_MARKER_OWNED=0
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
FOREGROUND_MARKER="${FOREGROUND_MARKER:-${LOCK_FILE}.foreground-intent}"

if [[ "${COORDINATION_MODE}" == "background" ]]; then
  if ! command -v setsid >/dev/null 2>&1; then
    printf 'Could not find setsid. Install util-linux or add setsid to PATH.\n' >&2
    exit 127
  fi
  exec {LOCK_FD}> "${LOCK_FILE}"
  flock -s "${LOCK_FD}"
  LOCK_HELD=1
  if [[ -n "${CUDA_BACKGROUND_GPU_UUIDS:-}" ]]; then
    mapfile -t GPU_UUID_LIST < <(tr ',' '\n' <<<"${CUDA_BACKGROUND_GPU_UUIDS}" | sed '/^[[:space:]]*$/d' | sort -u)
    for uuid in "${GPU_UUID_LIST[@]}"; do
      safe_uuid="${uuid//[^A-Za-z0-9_.-]/_}"
      exec {gpu_fd}> "${LOCK_FILE}.gpu.${safe_uuid}.lock"
      flock "${gpu_fd}"
      GPU_LOCK_FDS+=("${gpu_fd}")
    done
  fi
  if [[ -e "${FOREGROUND_MARKER}" ]]; then
    exit 75
  fi
  printf '[benchmark-mutex] acquired %s via %s\n' "${LABEL}" "${LOCK_FILE}" >&2
  set +e
  (
    eval "exec ${LOCK_FD}>&-"
    for fd in "${GPU_LOCK_FDS[@]}"; do
      eval "exec ${fd}>&-"
    done
    exec setsid -- "$@"
  ) &
  BACKGROUND_PID=$!
  while kill -0 "${BACKGROUND_PID}" 2>/dev/null; do
    if [[ -e "${FOREGROUND_MARKER}" ]]; then
      terminate_background
      exit 75
    fi
    sleep 0.1
  done
  wait "${BACKGROUND_PID}"
  STATUS=$?
  BACKGROUND_PID=""
  set -e
  exit "${STATUS}"
fi

if [[ "${CUDA_BENCHMARK_FOREGROUND_INTENT_HELD:-0}" != "1" ]]; then
  printf '%s\n' "$$" > "${FOREGROUND_MARKER}"
  FOREGROUND_MARKER_OWNED=1
fi

exec {LOCK_FD}> "${LOCK_FILE}"
if ! flock -n "${LOCK_FD}"; then
  printf '[benchmark-mutex] waiting for %s via %s\n' "${LABEL}" "${LOCK_FILE}" >&2
  flock "${LOCK_FD}"
fi

LOCK_HELD=1
printf '[benchmark-mutex] acquired %s via %s\n' "${LABEL}" "${LOCK_FILE}" >&2

set +e
"$@"
STATUS=$?
set -e

exit "${STATUS}"
