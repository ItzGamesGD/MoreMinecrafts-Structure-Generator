#!/usr/bin/env bash
set -euo pipefail
repo=$1
fixture="$repo/validation/minecraft-visual"
mkdir -p "$fixture/run/logs"
export LIBGL_ALWAYS_SOFTWARE=1 MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
exec timeout 720s xvfb-run -a -s '-screen 0 1280x720x24 +extension GLX +render' \
  env LIBGL_ALWAYS_SOFTWARE=1 MESA_LOADER_DRIVER_OVERRIDE=llvmpipe \
  bash -c '
    set -euo pipefail
    session=$1
    repository=$2
    evidence=$3
    openbox --sm-disable > "$evidence/window-manager.log" 2>&1 &
    wm_pid=$!
    cleanup() { kill "$wm_pid" 2>/dev/null || true; }
    trap cleanup EXIT
    for _ in $(seq 1 40); do
      xprop -root _NET_SUPPORTING_WM_CHECK >/dev/null 2>&1 && break
      sleep 0.25
    done
    bash "$session" "$repository"
  ' _ "$fixture/capture-session.sh" "$repo" "$fixture/evidence"
