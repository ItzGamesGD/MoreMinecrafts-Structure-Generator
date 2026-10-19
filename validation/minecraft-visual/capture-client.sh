#!/usr/bin/env bash
set -euo pipefail
repo=$1
fixture="$repo/validation/minecraft-visual"
mkdir -p "$fixture/run/logs" "$fixture/evidence/screenshots"
export LIBGL_ALWAYS_SOFTWARE=1 MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
vulkan_icd=$(find /usr/share/vulkan/icd.d -maxdepth 1 -name 'lvp_icd*.json' -print -quit)
if [ -z "$vulkan_icd" ]; then
  echo 'Mesa lavapipe Vulkan ICD was not found.' >&2
  exit 1
fi
export VK_ICD_FILENAMES="$vulkan_icd"
export SG01_SCREENSHOT_REQUEST="$fixture/run/screenshot-request.txt"
exec timeout 720s xvfb-run -a -s '-screen 0 1280x720x24 +extension GLX +render -noreset' \
  bash "$fixture/capture-session.sh" "$repo"
