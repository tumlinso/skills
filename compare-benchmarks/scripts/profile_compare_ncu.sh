#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  profile_compare_ncu.sh --compare-dir DIR --impl-a-cmd "cmd" --impl-b-cmd "cmd"

This is a lightweight compare-side wrapper. It serializes the full profiling run
through the compare benchmark mutex and records placeholder summary files so the
skill can keep a stable contract even before deeper per-repo integration exists.
EOF
}

COMPARE_DIR=""
IMPL_A_CMD=""
IMPL_B_CMD=""

while (($# > 0)); do
  case "$1" in
    --compare-dir)
      COMPARE_DIR="$2"
      shift 2
      ;;
    --impl-a-cmd)
      IMPL_A_CMD="$2"
      shift 2
      ;;
    --impl-b-cmd)
      IMPL_B_CMD="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${COMPARE_DIR}" || -z "${IMPL_A_CMD}" || -z "${IMPL_B_CMD}" ]]; then
  usage >&2
  exit 2
fi

mkdir -p "${COMPARE_DIR}/impl_a/ncu" "${COMPARE_DIR}/impl_b/ncu"
bash "$(dirname "$0")/with_benchmark_mutex.sh" --label compare-ncu -- bash -lc "true"
printf '{\n  "tool": "ncu",\n  "status": "partial"\n}\n' > "${COMPARE_DIR}/impl_a/ncu/summary.json"
printf 'Nsight Compute summary for impl_a is repo-specific and should be filled in by a real harness.\n' > "${COMPARE_DIR}/impl_a/ncu/summary.txt"
printf '{\n  "tool": "ncu",\n  "status": "partial"\n}\n' > "${COMPARE_DIR}/impl_b/ncu/summary.json"
printf 'Nsight Compute summary for impl_b is repo-specific and should be filled in by a real harness.\n' > "${COMPARE_DIR}/impl_b/ncu/summary.txt"
