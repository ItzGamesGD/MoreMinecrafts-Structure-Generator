#!/usr/bin/env bash
set -euo pipefail
repo=$1
fixture="$repo/validation/minecraft-visual"
evidence="$fixture/evidence"
mkdir -p "$evidence/screenshots"
cd "$repo"
mkdir -p validation/minecraft-visual/run/client
printf 'guiScale:2\n' > validation/minecraft-visual/run/client/options.txt
./validation/minecraft-visual/gradlew --no-daemon -p validation/minecraft-visual runClient \
  --args='--quickPlayMultiplayer 127.0.0.1:25565 --username SG01Visual --version 26.3' \
  > "$fixture/run/logs/client.log" 2>&1 &
client_pid=$!
trap 'kill "$client_pid" 2>/dev/null || true' EXIT
window=''
for _ in $(seq 1 180); do
  window=$(xdotool search --onlyvisible --name '.*' 2>/dev/null | tail -1 || true)
  [ -n "$window" ] && break
  sleep 2
done
if [ -z "$window" ]; then
  xwininfo -root -tree > "$evidence/client-windows.txt" 2>&1 || true
  tail -160 "$fixture/run/logs/client.log"
  exit 1
fi
printf 'window_id=%s\nwindow_title=%s\n' "$window" "$(xdotool getwindowname "$window" 2>/dev/null || true)" > "$evidence/client-windows.txt"
echo 'client-startup=PASS' >> "$evidence/runtime-result.txt"
xdotool windowactivate --sync "$window" || true
sleep 40
joined=0
for _ in $(seq 1 30); do
  if python3 "$fixture/rcon.py" <<'CMDS' | grep -Fq 'SG01Visual'
list
CMDS
  then joined=1; break; fi
  sleep 2
done
if [ "$joined" -ne 1 ]; then echo 'The Minecraft client did not join the acceptance server.' >&2; exit 1; fi
echo 'world-join=PASS' >> "$evidence/runtime-result.txt"
capture() {
  local name=$1 x=$2 y=$3 z=$4 yaw=$5 pitch=$6
  python3 "$fixture/rcon.py" <<CMDS >> "$evidence/camera-positions.log"
tp SG01Visual $x $y $z $yaw $pitch
CMDS
  sleep 3
  xdotool key --clearmodifiers F2
  sleep 2
  local src
  src=$(find "$fixture/run/client/screenshots" -type f -name '*.png' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
  [ -n "$src" ] || { echo "No Minecraft screenshot after $name" >&2; exit 1; }
  cp "$src" "$evidence/screenshots/$name.png"
}
capture plaza-eye 20 106 20 0 8
capture interior-overview 20 112 20 0 35
capture upper-balconies 20 117 14 0 20
capture support-columns 12 105 20 90 5
capture ceiling-details 20 113 24 180 -55
capture entrance-north 20 105 4 0 5
capture entrance-east 36 105 20 90 5
capture entrance-south 20 105 36 180 5
capture entrance-west 4 105 20 -90 5
capture exterior-cutaway 48 126 48 -135 35
identify "$evidence/screenshots"/*.png | tee "$evidence/screenshot-dimensions.txt"
grep -q '1280x720' "$evidence/screenshot-dimensions.txt"
echo 'screenshots=PASS' >> "$evidence/runtime-result.txt"
echo 'minecraft-client-screenshots=PASS' >> "$evidence/runtime-result.txt"
