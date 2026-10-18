#!/usr/bin/env bash
set -euo pipefail
repo=$1
fixture="$repo/validation/minecraft-visual"
evidence="$fixture/evidence"
client_dir="$fixture/run/client"
result_file="$evidence/runtime-result.txt"
source "$fixture/stage-result.sh"
current_stage=client-startup
trap 'status=$?; mark_stage "$current_stage" FAIL "$result_file"; exit "$status"' ERR
mkdir -p "$evidence/screenshots" "$fixture/run/logs" "$client_dir/screenshots"
cd "$repo"
printf 'guiScale:2\ntutorialStep:none\nlang:en_us\nrenderDistance:8\n' > "$client_dir/options.txt"
rm -f "$SG01_SCREENSHOT_REQUEST" "$client_dir/screenshots"/*.png

setsid timeout 660s ./validation/minecraft-visual/gradlew --no-daemon -p validation/minecraft-visual runClient \
  --args='--quickPlayMultiplayer 127.0.0.1:25565 --username SG01Visual --version 26.3 --width 1280 --height 720' \
  > "$fixture/run/logs/client.log" 2>&1 &
client_pid=$!
cleanup() { kill -TERM -- "-$client_pid" 2>/dev/null || true; wait "$client_pid" 2>/dev/null || true; }
trap cleanup EXIT

client_started=0
joined=0
for _ in $(seq 1 180); do
  if grep -Fq 'Using graphics backend' "$fixture/run/logs/client.log" \
      && grep -Fq 'Reloading ResourceManager:' "$fixture/run/logs/client.log"; then
    client_started=1
  fi
  if grep -Fq 'SG01_CLIENT_JOINED' "$fixture/run/logs/client.log"; then
    joined=1
    break
  fi
  if ! kill -0 "$client_pid" 2>/dev/null; then break; fi
  sleep 2
done
if [ "$client_started" -ne 1 ]; then
  echo 'Minecraft renderer/resource initialization did not complete.' >&2
  tail -160 "$fixture/run/logs/client.log"
  mark_stage client-startup FAIL "$result_file"
  exit 1
fi
mark_stage client-startup PASS "$result_file"
if [ "$joined" -ne 1 ]; then
  echo 'Minecraft client did not report a loaded client world.' >&2
  tail -160 "$fixture/run/logs/client.log"
  mark_stage world-join FAIL "$result_file"
  exit 1
fi

server_joined=0
for _ in $(seq 1 30); do
  if python3 "$fixture/rcon.py" <<'CMDS' | grep -Fq 'SG01Visual'
list
CMDS
  then
    server_joined=1
    break
  fi
  sleep 2
done
if [ "$server_joined" -ne 1 ]; then
  echo 'Minecraft server did not list SG01Visual after client world-ready marker.' >&2
  mark_stage world-join FAIL "$result_file"
  exit 1
fi
mark_stage world-join PASS "$result_file"

python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/camera-positions.log"
time set noon
weather clear
effect give SG01Visual minecraft:night_vision infinite 0 true
CMDS

capture() {
  local name=$1 x=$2 y=$3 z=$4 yaw=$5 pitch=$6
  local src="$client_dir/screenshots/$name.png"
  python3 "$fixture/rcon.py" <<CMDS | tee -a "$evidence/camera-positions.log"
tp SG01Visual $x $y $z $yaw $pitch
data get entity SG01Visual Pos
data get entity SG01Visual Rotation
execute as SG01Visual at @s run data get block ~ ~-2 ~
CMDS
  # Allow the server's teleport and chunk updates to reach the client renderer.
  sleep 3
  printf '%s.png\n' "$name" > "$SG01_SCREENSHOT_REQUEST"

  local written=0
  for _ in $(seq 1 90); do
    if grep -Fq "SG01_CAPTURE_WRITTEN name=$name.png" "$fixture/run/logs/client.log"; then
      written=1
      break
    fi
    if grep -Fq "SG01_CAPTURE_FAILED name=$name.png" "$fixture/run/logs/client.log"; then
      break
    fi
    if ! kill -0 "$client_pid" 2>/dev/null; then break; fi
    sleep 2
  done
  if [ "$written" -ne 1 ] || [ ! -s "$src" ]; then
    {
      echo "native_capture_failed=$name.png"
      echo "request_file=$SG01_SCREENSHOT_REQUEST"
      ls -la "$client_dir/screenshots" 2>&1 || true
      tail -100 "$fixture/run/logs/client.log"
    } > "$evidence/capture-failure.log"
    echo "Minecraft Screenshot.grab did not produce $src" >&2
    if [ "$name" = plaza-eye ]; then mark_stage plaza-screenshot FAIL "$result_file"; else mark_stage screenshots FAIL "$result_file"; fi
    exit 1
  fi
  local description
  description=$(identify -format '%m %wx%h %b' "$src")
  colors=$(identify -format '%k' "$src")
  if [[ "$description" != PNG\ 1280x720* ]] || [ "$colors" -lt 100 ]; then
    echo "Unexpected native screenshot: $src ($description)" >&2
    if [ "$name" = plaza-eye ]; then mark_stage plaza-screenshot FAIL "$result_file"; else mark_stage screenshots FAIL "$result_file"; fi
    exit 1
  fi
  cp "$src" "$evidence/screenshots/$name.png"
  printf '%s %s\n' "$src" "$description" | tee -a "$evidence/screenshot-dimensions.txt"
}

# The plaza PNG is written and validated first. Remaining views run only after
# that native Minecraft framebuffer capture succeeds.
current_stage=plaza-screenshot
capture plaza-eye 20 102 20 0 0
mark_stage plaza-screenshot PASS "$result_file"
current_stage=screenshots
capture interior-overview 20 106 6 0 12
capture upper-balconies 6 110 20 -90 8
capture support-columns 12 105 20 90 5
capture ceiling-details 20 113 24 180 -55
capture entrance-north 20 105 4 0 5
capture entrance-east 36 105 20 90 5
capture entrance-south 20 105 36 180 5
capture entrance-west 4 105 20 -90 5
capture exterior-cutaway 70 124 70 135 22
mark_stage screenshots PASS "$result_file"
