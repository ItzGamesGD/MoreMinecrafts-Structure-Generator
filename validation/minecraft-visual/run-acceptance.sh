#!/usr/bin/env bash
set -euo pipefail
repo=$1
pack=$2
fixture="$repo/validation/minecraft-visual"
run="$fixture/run/server"
evidence="$fixture/evidence"
mkdir -p "$run/world/datapacks" "$fixture/run/logs" "$evidence"
cp -a "$pack" "$run/world/datapacks/sg01"
printf 'eula=true\n' > "$run/eula.txt"
cat > "$run/server.properties" <<'PROPS'
level-name=world
level-seed=173
online-mode=false
enable-rcon=true
rcon.password=sg01-visual-ci-only
rcon.port=25575
server-port=25565
server-ip=127.0.0.1
motd=SG-01 disposable acceptance runtime
level-type=minecraft:flat
gamemode=creative
difficulty=peaceful
spawn-monsters=false
spawn-animals=false
view-distance=8
simulation-distance=6
allow-flight=true
PROPS
setsid bash -c 'cd "$1" && exec timeout 480s ./gradlew --no-daemon runServer' _ "$fixture" \
  > "$fixture/run/logs/server.log" 2>&1 &
server_pid=$!
echo "$server_pid" > "$fixture/run/server.pid"
cleanup() { kill -- "-$server_pid" 2>/dev/null || kill "$server_pid" 2>/dev/null || true; }
trap cleanup EXIT
ready=0
for _ in $(seq 1 180); do
  if grep -Fq 'Done (' "$fixture/run/logs/server.log"; then ready=1; break; fi
  if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then tail -200 "$fixture/run/logs/server.log"; exit 1; fi
# The enabled-pack query is the gate: no placement command is issued until the exact pack is live.
python3 "$fixture/rcon.py" <<'CMDS' | tee "$evidence/runtime-commands.log"
datapack list enabled
CMDS
grep -F 'file/sg01' "$evidence/runtime-commands.log"
# These IDs are the resources' paths in the exact loaded datapack. Each successful placement is recorded.
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
place template moreminecrafts:forgotten_kingdom/central_cavern/main_chamber 0 100 0
place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_north 100 100 0
place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_east 130 100 0
place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_south 160 100 0
place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_west 190 100 0
place structure moreminecrafts:forgotten_kingdom/central_cavern 0 100 0
time set noon
weather clear
CMDS
if grep -Eiq 'Unknown (structure|template)|Failed|Could not|Error executing|No key' "$evidence/runtime-commands.log"; then
  echo 'Minecraft reported a placement or registry error.' >&2
  exit 1
fi
echo 'runtime-place=PASS' | tee "$evidence/runtime-result.txt"
