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

Timed benchmarks take the host-wide exclusive gate. Controller-selected
device-scoped Nsight Compute captures take that gate shared and lock their
selected GPU UUIDs exclusively. Calls without an explicit device scope and
UUID list retain conservative host-wide exclusion.
EOF
}

LOCK_FILE="${CUDA_V100_BENCHMARK_MUTEX_PATH:-${TMPDIR:-/tmp}/cuda_v100_benchmark.lock}"
LABEL=""
LOCK_FD=""
LOCK_HELD=0
COORDINATION_MODE="${CUDA_BENCHMARK_COORDINATION_MODE:-foreground}"
FOREGROUND_MARKER="${CUDA_BENCHMARK_FOREGROUND_INTENT_PATH:-}"
INTENT_RECORDS_DIR="${CUDA_BENCHMARK_FOREGROUND_INTENT_RECORDS_DIR:-}"
LOCK_SCOPE="${CUDA_BENCHMARK_LOCK_SCOPE:-host}"
GPU_UUIDS="${CUDA_BENCHMARK_GPU_UUIDS:-${CUDA_BACKGROUND_GPU_UUIDS:-}}"
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

safe_uuid() {
  local value="$1"
  if [[ ! "${value}" =~ ^[A-Za-z0-9_.-]{1,256}$ ]]; then
    printf 'Invalid GPU UUID for benchmark coordination: %s\n' "${value}" >&2
    return 2
  fi
  printf '%s\n' "${value}"
}

has_any_record() {
  local pattern="$1" candidate
  shopt -s nullglob
  local matches=("${INTENT_RECORDS_DIR}"/${pattern})
  shopt -u nullglob
  for candidate in "${matches[@]}"; do
    [[ -f "${candidate}" ]] && return 0
  done
  return 1
}

has_host_intent() {
  # The legacy singleton marker remains a global priority signal.
  [[ -e "${FOREGROUND_MARKER}" ]] && return 0
  [[ -d "${INTENT_RECORDS_DIR}" ]] || return 1
  has_any_record '*.host' && return 0
  return 1
}

has_foreground_intent() {
  local candidate uuid safe
  has_host_intent && return 0
  if [[ "${LOCK_SCOPE}" != "device" ]]; then
    has_any_record '*.device.*' && return 0
    return 1
  fi
  while IFS= read -r uuid; do
    [[ -n "${uuid}" ]] || continue
    safe="$(safe_uuid "${uuid}")" || return 0
    shopt -s nullglob
    local matches=( "${INTENT_RECORDS_DIR}"/*.device."${safe}" )
    shopt -u nullglob
    for candidate in "${matches[@]}"; do
      [[ -f "${candidate}" ]] && return 0
    done
  done < <(tr ',' '\n' <<<"${GPU_UUIDS}" | sed '/^[[:space:]]*$/d' | sort -u)
  return 1
}

acquire_gpu_locks() {
  local uuid safe fd
  [[ -n "${GPU_UUIDS}" ]] || return 0
  mapfile -t GPU_UUID_LIST < <(tr ',' '\n' <<<"${GPU_UUIDS}" | sed '/^[[:space:]]*$/d' | sort -u)
  for uuid in "${GPU_UUID_LIST[@]}"; do
    safe="$(safe_uuid "${uuid}")" || return $?
    exec {fd}> "${LOCK_FILE}.gpu.${safe}.lock"
    if [[ "${COORDINATION_MODE}" == "background" ]]; then
      while ! flock -n "${fd}"; do
        if has_foreground_intent; then
          printf '[benchmark-mutex] yielding %s for foreground intent on %s\n' "${LABEL}" "${uuid}" >&2
          eval "exec ${fd}>&-"
          return 75
        fi
        sleep 0.1
      done
    else
      flock "${fd}"
    fi
    GPU_LOCK_FDS+=("${fd}")
  done
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
INTENT_RECORDS_DIR="${INTENT_RECORDS_DIR:-${FOREGROUND_MARKER}.owners}"

if [[ "${LOCK_SCOPE}" != "host" && "${LOCK_SCOPE}" != "device" ]]; then
  printf 'Unknown lock scope: %s\n' "${LOCK_SCOPE}" >&2
  exit 2
fi
if [[ "${LOCK_SCOPE}" == "device" && ( -z "${GPU_UUIDS//,/}" ||
      ( "${COORDINATION_MODE}" != "background" && "${CUDA_BENCHMARK_FOREGROUND_INTENT_HELD:-0}" != "1" ) ) ]]; then
  # A device scope is safe only with explicit identities and controller admission.
  LOCK_SCOPE="host"
fi

if [[ "${COORDINATION_MODE}" == "background" ]]; then
  if ! command -v setsid >/dev/null 2>&1; then
    printf 'Could not find setsid. Install util-linux or add setsid to PATH.\n' >&2
    exit 127
  fi
  exec {LOCK_FD}> "${LOCK_FILE}"
  if [[ "${LOCK_SCOPE}" == "device" ]]; then
    if has_host_intent; then
      printf '[benchmark-mutex] yielding %s for pending host measurement\n' "${LABEL}" >&2
      exit 75
    fi
    flock -s "${LOCK_FD}"
    LOCK_HELD=1
    # A host benchmark may publish its intent while this shared lock waits
    # behind earlier readers. Let the queued writer proceed before this capture
    # takes any device lock.
    if has_host_intent; then
      printf '[benchmark-mutex] yielding %s for pending host measurement\n' "${LABEL}" >&2
      exit 75
    fi
  else
    while ! flock -n "${LOCK_FD}"; do
      if has_foreground_intent; then
        printf '[benchmark-mutex] yielding %s for foreground intent\n' "${LABEL}" >&2
        exit 75
      fi
      sleep 0.1
    done
  fi
  LOCK_HELD=1
  if acquire_gpu_locks; then
    :
  else
    status=$?
    exit "${status}"
  fi
  if has_foreground_intent; then
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
    if has_foreground_intent; then
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

if [[ "${LOCK_SCOPE}" == "host" && "${CUDA_BENCHMARK_FOREGROUND_INTENT_HELD:-0}" != "1" ]]; then
  printf '%s\n' "$$" > "${FOREGROUND_MARKER}"
  FOREGROUND_MARKER_OWNED=1
fi

exec {LOCK_FD}> "${LOCK_FILE}"
if [[ "${LOCK_SCOPE}" == "device" ]]; then
  if has_host_intent; then
    printf '[benchmark-mutex] yielding %s for pending host measurement\n' "${LABEL}" >&2
    exit 75
  fi
  flock -s "${LOCK_FD}"
  LOCK_HELD=1
  if has_host_intent; then
    printf '[benchmark-mutex] yielding %s for pending host measurement\n' "${LABEL}" >&2
    exit 75
  fi
else
  if ! flock -n "${LOCK_FD}"; then
    printf '[benchmark-mutex] waiting for %s via %s\n' "${LABEL}" "${LOCK_FILE}" >&2
    flock "${LOCK_FD}"
  fi
fi
LOCK_HELD=1
if acquire_gpu_locks; then
  :
else
  status=$?
  exit "${status}"
fi
printf '[benchmark-mutex] acquired %s via %s\n' "${LABEL}" "${LOCK_FILE}" >&2
if ! command -v setsid >/dev/null 2>&1; then
  printf 'Could not find setsid. Install util-linux or add setsid to PATH.\n' >&2
  exit 127
fi
set +e
(
  eval "exec ${LOCK_FD}>&-"
  for fd in "${GPU_LOCK_FDS[@]}"; do
    eval "exec ${fd}>&-"
  done
  exec setsid -- "$@"
) &
BACKGROUND_PID=$!
wait "${BACKGROUND_PID}"
STATUS=$?
BACKGROUND_PID=""
set -e
exit "${STATUS}"
