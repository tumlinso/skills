#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  open_ncu_ui.sh [report.ncu-rep]

Opens NVIDIA Nsight Compute UI, preferring explicit /opt/nvidia installs
before falling back to PATH. Pass an optional `.ncu-rep` file to open it
directly.
EOF
}

resolve_ncu_ui_bin() {
  local candidates=(
    "${NCU_UI_BIN:-}"
    "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/profilers/12.9/Nsight_Compute/ncu-ui"
    "/opt/nvidia/nsight-compute/2025.1.0/ncu-ui"
    "/opt/nvidia/nsight-compute/2025.1.0/host/linux-desktop-glibc_2_11_3-x64/ncu-ui"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  if command -v ncu-ui >/dev/null 2>&1; then
    command -v ncu-ui
    return 0
  fi
  return 1
}

if (($# > 0)) && [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

if ! NCU_UI_BIN="$(resolve_ncu_ui_bin)"; then
  printf 'Could not find ncu-ui. Set NCU_UI_BIN or install/add Nsight Compute UI.\n' >&2
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
  exec "${NCU_UI_BIN}" "$1"
else
  exec "${NCU_UI_BIN}"
fi
