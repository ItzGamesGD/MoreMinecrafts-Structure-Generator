#!/usr/bin/env bash
set -euo pipefail
repo=$1
pack=$2
keep_server=${3:-}
fixture="$repo/validation/minecraft-visual"
run="$fixture/run/server"
evidence="$fixture/evidence"
result_file="$evidence/runtime-result.txt"
source "$fixture/stage-result.sh"
current_stage=server-startup
trap 'status=$?; mark_stage "$current_stage" FAIL "$result_file"; exit "$status"' ERR
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
white-list=false
PROPS
setsid bash -c 'cd "$1" && exec timeout 480s ./gradlew --no-daemon runServer' _ "$fixture" \
  > "$fixture/run/logs/server.log" 2>&1 &
server_pid=$!
echo "$server_pid" > "$fixture/run/server.pid"
cleanup() { kill -- "-$server_pid" 2>/dev/null || kill "$server_pid" 2>/dev/null || true; }
if [ "$keep_server" != "--keep-server" ]; then trap cleanup EXIT; fi
ready=0
for _ in $(seq 1 180); do
  if grep -Fq 'Done (' "$fixture/run/logs/server.log"; then ready=1; break; fi
  if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then tail -200 "$fixture/run/logs/server.log"; mark_stage "$current_stage" FAIL "$result_file"; exit 1; fi
mark_stage server-startup PASS "$result_file"
current_stage=datapack-load
# The enabled-pack query is the gate: no placement command is issued until the exact pack is live.
python3 "$fixture/rcon.py" <<'CMDS' | tee "$evidence/runtime-commands.log"
datapack list enabled
CMDS
grep -F 'file/sg01' "$evidence/runtime-commands.log"
mark_stage datapack-load PASS "$result_file"
# Offline-mode test clients require an explicit whitelist entry on the hosted runner.
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
whitelist add SG01Visual
CMDS
# PlaceCommand rejects positions outside loaded chunks. Force-load only the test coordinates
# so command results prove template/structure resolution rather than merely accepting syntax.
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
forceload add -64 -64 64 64
forceload add 0 0
forceload add 100 0
forceload add 130 0
forceload add 160 0
forceload add 190 0
CMDS
# These IDs are the resource paths in the exact loaded datapack.
current_stage=template-placement
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
place template moreminecrafts:forgotten_kingdom/central_cavern/main_chamber 0 100 0
place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_north 100 100 0
place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_east 130 100 0
place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_south 160 100 0
place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_west 190 100 0
CMDS
if grep -Eiq 'Unknown (structure|template)|Failed|Could not|Error executing|No key|That position is not loaded' "$evidence/runtime-commands.log"; then
  echo 'Minecraft reported a placement or registry error.' >&2
  exit 1
fi
for template in main_chamber tunnel_north tunnel_east tunnel_south tunnel_west; do
  grep -Fq "RESULT Loaded template \"moreminecrafts:forgotten_kingdom/central_cavern/$template\"" "$evidence/runtime-commands.log"
done
mark_stage template-placement PASS "$result_file"
current_stage=jigsaw-placement
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
place structure moreminecrafts:forgotten_kingdom/central_cavern 0 100 0
time set noon
weather clear
CMDS
grep -Fq 'RESULT Generated structure "moreminecrafts:forgotten_kingdom/central_cavern"' "$evidence/runtime-commands.log"
mark_stage jigsaw-placement PASS "$result_file"
# A successful command response proves resource lookup, but also verify that the
# generated template's known floor block reached the actual world at its NBT
# coordinates. This catches false-positive captures of the untouched flat map.
current_stage=world-block-verification
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute unless block 20 100 20 minecraft:polished_deepslate run say SG01_CHAMBER_FLOOR_MISSING
CMDS
if grep -Fq 'RESULT Test passed' "$evidence/runtime-commands.log"; then
  echo 'The expected chamber floor is absent at its source NBT coordinate.' >&2
  exit 1
fi
grep -Fq 'RESULT Test failed' "$evidence/runtime-commands.log"
mark_stage world-block-verification PASS "$result_file"
echo 'runtime-place=PASS'
