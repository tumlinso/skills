#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  open_nsys_ui.sh [report.nsys-rep]

Opens NVIDIA Nsight Systems UI, preferring explicit /opt/nvidia installs
before falling back to PATH. Pass an optional `.nsys-rep` file to open it
directly.
EOF
}

resolve_nsys_ui_bin() {
  local candidates=(
    "${NSYS_UI_BIN:-}"
    "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/compilers/bin/nsys-ui"
    "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/profilers/12.9/Nsight_Systems_2025.3/host-linux-x64/nsys-ui"
    "/opt/nvidia/nsight-systems/2024.6.2/host-linux-x64/nsys-ui"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  if command -v nsys-ui >/dev/null 2>&1; then
    command -v nsys-ui
    return 0
  fi
  return 1
}

if (($# > 0)) && [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

if ! NSYS_UI_BIN="$(resolve_nsys_ui_bin)"; then
  printf 'Could not find nsys-ui. Set NSYS_UI_BIN or install/add Nsight Systems UI.\n' >&2
  exit 127
fi

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  printf 'No DISPLAY or WAYLAND_DISPLAY detected. GUI launch may fail in this shell.\n' >&2
fi

if (($# > 1)); then
  usage >&2
  exit 2
fi

if (($# == 1)); then
  exec "${NSYS_UI_BIN}" "$1"
else
  exec "${NSYS_UI_BIN}"
fi
