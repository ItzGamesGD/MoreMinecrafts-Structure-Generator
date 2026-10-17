#!/usr/bin/env bash
set -euo pipefail
repo=$1
fixture="$repo/validation/minecraft-visual"
mkdir -p "$fixture/run/logs"
export LIBGL_ALWAYS_SOFTWARE=1 MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
exec timeout 720s xvfb-run -a -s '-screen 0 1280x720x24 +extension GLX +render' \
  env LIBGL_ALWAYS_SOFTWARE=1 MESA_LOADER_DRIVER_OVERRIDE=llvmpipe \
  bash "$fixture/capture-session.sh" "$repo"
