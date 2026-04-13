#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  check_debug_toolchain.sh [--json-out PATH] [--text-out PATH]

Report installed and missing native debugging tools that this skill expects on
Ubuntu-like systems. The text summary is always printed to stdout.
EOF
}

JSON_OUT=""
TEXT_OUT=""

while (($# > 0)); do
  case "$1" in
    --json-out)
      JSON_OUT="$2"
      shift 2
      ;;
    --text-out)
      TEXT_OUT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

write_group() {
  local name="$1"
  local out="${TMP_DIR}/${name}.tsv"
  shift
  : > "${out}"
  local tool path
  for tool in "$@"; do
    if path="$(command -v "${tool}" 2>/dev/null)"; then
      printf '%s\tinstalled\t%s\n' "${tool}" "${path}" >> "${out}"
    else
      printf '%s\tmissing\t\n' "${tool}" >> "${out}"
    fi
  done
}

write_group required g++ gdb addr2line c++filt readelf objdump nm strace perf cmake
write_group optional gcc clang++ llvm-symbolizer lldb valgrind rr ninja
write_group cuda_follow_on cuda-gdb compute-sanitizer nsys ncu

TEXT="$(
python3 - "${TMP_DIR}" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])

def load(name: str):
    rows = []
    for line in (root / f"{name}.tsv").read_text().splitlines():
        tool, status, path = line.split("\t")
        rows.append((tool, status, path))
    return rows

sections = [
    ("required", "Required"),
    ("optional", "Optional"),
    ("cuda_follow_on", "CUDA follow-on"),
]

lines = ["Native Debug Toolchain Check", ""]
for key, title in sections:
    rows = load(key)
    lines.append(f"{title}:")
    for tool, status, path in rows:
        if status == "installed":
            lines.append(f"- {tool}: installed ({path})")
        else:
            lines.append(f"- {tool}: missing")
    lines.append("")
print("\n".join(lines).rstrip() + "\n", end="")
PY
)"

printf '%s' "${TEXT}"

if [[ -n "${TEXT_OUT}" ]]; then
  printf '%s' "${TEXT}" > "${TEXT_OUT}"
fi

if [[ -n "${JSON_OUT}" ]]; then
  python3 - "${TMP_DIR}" "${JSON_OUT}" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
out = Path(sys.argv[2])

def load(name: str):
    rows = []
    for line in (root / f"{name}.tsv").read_text().splitlines():
        tool, status, path = line.split("\t")
        rows.append({"tool": tool, "status": status, "path": path})
    return rows

payload = {
    "required": load("required"),
    "optional": load("optional"),
    "cuda_follow_on": load("cuda_follow_on"),
}
out.write_text(json.dumps(payload, indent=2) + "\n")
PY
fi
