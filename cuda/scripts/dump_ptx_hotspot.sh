#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  dump_ptx_hotspot.sh [options] source.{cu|ptx}

Options:
  --out-dir DIR       Output directory. Default: ./ptx_out
  --label LABEL       Run label. Default: UTC timestamp
  --arch ARCH         GPU target. Default: sm_70
  --symbol NAME       Focus PTX/SASS output on one symbol when possible
  --nvcc-flag FLAG    Extra flag for nvcc. May be repeated for .cu inputs
  -h, --help          Show this help

The wrapper compiles one focused CUDA or PTX source, captures PTX, cubin,
resource-usage chatter, cuobjdump, and nvdisasm outputs, and emits summary.txt
plus summary.json first. Prefer isolated hot-path harnesses or narrow
translation units over monolithic library builds. For multi-kernel `.cu`
sources, run `split_cuda_translation_unit.py` first and dump the generated
focused source instead of the original translation unit.
EOF
}

OUT_DIR="./ptx_out"
LABEL="$(date -u +%Y%m%dT%H%M%SZ)"
ARCH="sm_70"
SYMBOL=""
NVCC_FLAGS=()

resolve_bin() {
  local preferred="$1"
  if [[ -n "${preferred}" && -x "${preferred}" ]]; then
    printf '%s\n' "${preferred}"
    return 0
  fi
  local name="$2"
  if command -v "${name}" >/dev/null 2>&1; then
    command -v "${name}"
    return 0
  fi
  return 1
}

extract_ptx_symbol() {
  local input_file="$1"
  local symbol="$2"
  local output_file="$3"
  python3 - "${input_file}" "${symbol}" "${output_file}" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

input_path = Path(sys.argv[1])
symbol = sys.argv[2]
output_path = Path(sys.argv[3])
text = input_path.read_text()
lines = text.splitlines(keepends=True)
pattern = re.compile(rf"(?:^|\s)(?:\.entry|\.func)\b.*\b{re.escape(symbol)}\b")
start = None
seen_brace = False
for index, line in enumerate(lines):
    if start is None:
        if pattern.search(line):
            start = index
            seen_brace = "{" in line
        continue
    if "{" in line:
        seen_brace = True
    if seen_brace and line.strip() == "}":
        output_path.write_text("".join(lines[start:index + 1]))
        raise SystemExit(0)
if start is not None:
    output_path.write_text("".join(lines[start:]))
    raise SystemExit(0)
raise SystemExit(1)
PY
}

fallback_focus_text() {
  local input_file="$1"
  local symbol="$2"
  local output_file="$3"
  python3 - "${input_file}" "${symbol}" "${output_file}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

input_path = Path(sys.argv[1])
symbol = sys.argv[2]
output_path = Path(sys.argv[3])
lines = input_path.read_text().splitlines()
hits = [index for index, line in enumerate(lines) if symbol in line]
if not hits:
    raise SystemExit(1)
start = max(0, hits[0] - 8)
end = min(len(lines), hits[-1] + 80)
output_path.write_text("\n".join(lines[start:end]) + "\n")
PY
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
    --arch)
      ARCH="$2"
      shift 2
      ;;
    --symbol)
      SYMBOL="$2"
      shift 2
      ;;
    --nvcc-flag)
      NVCC_FLAGS+=("$2")
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
    -*)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if (($# != 1)); then
  printf 'Pass exactly one source file.\n\n' >&2
  usage >&2
  exit 2
fi

SOURCE_PATH="$(python3 - "$1" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"

if [[ ! -f "${SOURCE_PATH}" ]]; then
  printf 'Source file not found: %s\n' "${SOURCE_PATH}" >&2
  exit 2
fi

INPUT_EXT="${SOURCE_PATH##*.}"
case "${INPUT_EXT}" in
  cu|ptx)
    ;;
  *)
    printf 'Unsupported input type: %s\n' "${SOURCE_PATH}" >&2
    exit 2
    ;;
esac

if ! CUOBJDUMP_BIN="$(resolve_bin "${CUOBJDUMP_BIN:-}" "cuobjdump")"; then
  printf 'Could not find cuobjdump. Set CUOBJDUMP_BIN or install/add it to PATH.\n' >&2
  exit 127
fi
if ! NVDISASM_BIN="$(resolve_bin "${NVDISASM_BIN:-}" "nvdisasm")"; then
  printf 'Could not find nvdisasm. Set NVDISASM_BIN or install/add it to PATH.\n' >&2
  exit 127
fi
if [[ "${INPUT_EXT}" == "cu" ]]; then
  if ! NVCC_BIN="$(resolve_bin "${NVCC_BIN:-}" "nvcc")"; then
    printf 'Could not find nvcc. Set NVCC_BIN or install/add it to PATH.\n' >&2
    exit 127
  fi
  PTXAS_BIN=""
else
  if ! PTXAS_BIN="$(resolve_bin "${PTXAS_BIN:-}" "ptxas")"; then
    printf 'Could not find ptxas. Set PTXAS_BIN or install/add it to PATH.\n' >&2
    exit 127
  fi
  NVCC_BIN=""
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${OUT_DIR%/}/${LABEL}"
SUMMARY_FILE="${RUN_DIR}/summary.txt"
SUMMARY_JSON="${RUN_DIR}/summary.json"
FULL_PTX="${RUN_DIR}/full.ptx"
FULL_CUBIN="${RUN_DIR}/kernel.cubin"
FULL_CUOBJDUMP="${RUN_DIR}/full.cuobjdump.sass"
FULL_NVDISASM="${RUN_DIR}/full.nvdisasm.sass"
FOCUSED_PTX="${RUN_DIR}/focused.ptx"
FOCUSED_CUOBJDUMP="${RUN_DIR}/focused.cuobjdump.sass"
FOCUSED_NVDISASM="${RUN_DIR}/focused.nvdisasm.sass"
COMPILE_STDOUT="${RUN_DIR}/compile.stdout.txt"
COMPILE_STDERR="${RUN_DIR}/compile.stderr.txt"
PTX_COMPILE_STDOUT="${RUN_DIR}/ptx_compile.stdout.txt"
PTX_COMPILE_STDERR="${RUN_DIR}/ptx_compile.stderr.txt"
CUOBJDUMP_STDERR="${RUN_DIR}/cuobjdump.stderr.txt"
NVDISASM_STDERR="${RUN_DIR}/nvdisasm.stderr.txt"
RUN_CONFIG="${RUN_DIR}/run.env"

mkdir -p "${RUN_DIR}"
cp "${SOURCE_PATH}" "${RUN_DIR}/source.${INPUT_EXT}"

{
  printf 'utc_timestamp=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'hostname=%s\n' "$(hostname)"
  printf 'pwd=%s\n' "$(pwd)"
  printf 'source_path=%s\n' "${SOURCE_PATH}"
  printf 'input_kind=%s\n' "${INPUT_EXT}"
  printf 'arch=%s\n' "${ARCH}"
  printf 'symbol=%s\n' "${SYMBOL}"
  printf 'nvcc_bin=%s\n' "${NVCC_BIN}"
  printf 'ptxas_bin=%s\n' "${PTXAS_BIN}"
  printf 'cuobjdump_bin=%s\n' "${CUOBJDUMP_BIN}"
  printf 'nvdisasm_bin=%s\n' "${NVDISASM_BIN}"
  printf 'nvcc_flags=%s\n' "${NVCC_FLAGS[*]:-}"
} > "${RUN_CONFIG}"

env | sort > "${RUN_DIR}/process_env.txt"

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L > "${RUN_DIR}/nvidia_smi_L.txt" || true
fi

if [[ -n "${NVCC_BIN}" ]]; then
  "${NVCC_BIN}" --version > "${RUN_DIR}/nvcc_version.txt" || true
fi
if [[ -n "${PTXAS_BIN}" ]]; then
  "${PTXAS_BIN}" --version > "${RUN_DIR}/ptxas_version.txt" || true
fi
"${CUOBJDUMP_BIN}" --version > "${RUN_DIR}/cuobjdump_version.txt" 2>&1 || true
"${NVDISASM_BIN}" --version > "${RUN_DIR}/nvdisasm_version.txt" 2>&1 || true

if [[ "${INPUT_EXT}" == "cu" ]]; then
  "${NVCC_BIN}" -std=c++17 -arch="${ARCH}" -lineinfo --resource-usage -Xptxas=-v \
    "${NVCC_FLAGS[@]}" -cubin "${SOURCE_PATH}" -o "${FULL_CUBIN}" \
    > "${COMPILE_STDOUT}" 2> "${COMPILE_STDERR}"

  "${NVCC_BIN}" -std=c++17 -arch="${ARCH}" -lineinfo \
    "${NVCC_FLAGS[@]}" -ptx "${SOURCE_PATH}" -o "${FULL_PTX}" \
    > "${PTX_COMPILE_STDOUT}" 2> "${PTX_COMPILE_STDERR}"
else
  cp "${SOURCE_PATH}" "${FULL_PTX}"
  "${PTXAS_BIN}" --gpu-name "${ARCH}" -v "${SOURCE_PATH}" -o "${FULL_CUBIN}" \
    > "${COMPILE_STDOUT}" 2> "${COMPILE_STDERR}"
fi

"${CUOBJDUMP_BIN}" -sass "${FULL_CUBIN}" > "${FULL_CUOBJDUMP}" 2> "${CUOBJDUMP_STDERR}"
"${NVDISASM_BIN}" "${FULL_CUBIN}" > "${FULL_NVDISASM}" 2> "${NVDISASM_STDERR}"

if [[ -n "${SYMBOL}" ]]; then
  set +e
  "${CUOBJDUMP_BIN}" -sass -fun "${SYMBOL}" "${FULL_CUBIN}" > "${FOCUSED_CUOBJDUMP}" 2>> "${CUOBJDUMP_STDERR}"
  CUOBJDUMP_STATUS=$?
  "${NVDISASM_BIN}" -fun "${SYMBOL}" "${FULL_CUBIN}" > "${FOCUSED_NVDISASM}" 2>> "${NVDISASM_STDERR}"
  NVDISASM_STATUS=$?
  set -e

  if [[ ${CUOBJDUMP_STATUS} -ne 0 || ! -s "${FOCUSED_CUOBJDUMP}" ]]; then
    rm -f "${FOCUSED_CUOBJDUMP}"
    fallback_focus_text "${FULL_CUOBJDUMP}" "${SYMBOL}" "${FOCUSED_CUOBJDUMP}" || true
  fi
  if [[ ${NVDISASM_STATUS} -ne 0 || ! -s "${FOCUSED_NVDISASM}" ]]; then
    rm -f "${FOCUSED_NVDISASM}"
    fallback_focus_text "${FULL_NVDISASM}" "${SYMBOL}" "${FOCUSED_NVDISASM}" || true
  fi
  if ! extract_ptx_symbol "${FULL_PTX}" "${SYMBOL}" "${FOCUSED_PTX}"; then
    rm -f "${FOCUSED_PTX}"
    fallback_focus_text "${FULL_PTX}" "${SYMBOL}" "${FOCUSED_PTX}" || true
  fi
fi

python3 "${SCRIPT_DIR}/summarize_ptx_dump.py" "${RUN_DIR}" --json-out "${SUMMARY_JSON}" > "${SUMMARY_FILE}"

printf 'PTX dump summary: %s\n\n' "${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
printf '\nArtifacts:\n'
printf -- '- full PTX: %s\n' "${FULL_PTX}"
printf -- '- cubin: %s\n' "${FULL_CUBIN}"
printf -- '- full cuobjdump SASS: %s\n' "${FULL_CUOBJDUMP}"
printf -- '- full nvdisasm SASS: %s\n' "${FULL_NVDISASM}"
if [[ -s "${FOCUSED_PTX}" ]]; then
  printf -- '- focused PTX: %s\n' "${FOCUSED_PTX}"
fi
if [[ -s "${FOCUSED_CUOBJDUMP}" ]]; then
  printf -- '- focused cuobjdump SASS: %s\n' "${FOCUSED_CUOBJDUMP}"
fi
if [[ -s "${FOCUSED_NVDISASM}" ]]; then
  printf -- '- focused nvdisasm SASS: %s\n' "${FOCUSED_NVDISASM}"
fi
