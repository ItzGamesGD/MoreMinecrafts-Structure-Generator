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
python3 "$fixture/rcon.py" <<'CMDS' | tee "$evidence/runtime-commands.log"
datapack list enabled
CMDS
grep -F 'file/sg01' "$evidence/runtime-commands.log"
mark_stage datapack-load PASS "$result_file"

# NBT local origin is [0,0,0]. /place coordinates are absolute and use
# rotation=none, mirror=none, so world = [x, y+100, z].
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute in minecraft:overworld run forceload add -64 -64 64 64
execute in minecraft:overworld run time set noon
execute in minecraft:overworld run weather clear
CMDS
current_stage=template-placement
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute in minecraft:overworld run place template moreminecrafts:forgotten_kingdom/central_cavern/main_chamber 0 100 0
CMDS
grep -Fq 'RESULT Loaded template "moreminecrafts:forgotten_kingdom/central_cavern/main_chamber" at 0, 100, 0' "$evidence/runtime-commands.log"
mark_stage template-placement PASS "$result_file"

# Sample a point for each non-air block state, checking live world queries and
# then independently decoding the saved region MCA data.
current_stage=template-world-write
template_nbt="$repo/exports/sg-01/forgotten-underground-kingdom/datapack/data/moreminecrafts/structure/forgotten_kingdom/central_cavern/main_chamber.nbt"
python3 - "$template_nbt" "$evidence/template-probes.commands" <<'PY'
import sys
from structure_export.nbt import read_nbt
nbt = read_nbt(open(sys.argv[1], "rb").read())["value"]
samples = {}
for block in nbt["blocks"]:
    state = nbt["palette"][block["state"]]
    if state["Name"] == "minecraft:air":
        continue
    samples.setdefault(block["state"], (block["pos"], state))
with open(sys.argv[2], "w") as out:
    for i, (_state_id, (local, state)) in enumerate(samples.items()):
        x, y, z = local
        props = state.get("Properties", {})
        suffix = "[" + ",".join(f"{k}={v}" for k, v in props.items()) + "]" if props else ""
        block_id = state["Name"] + suffix
        out.write(f"execute in minecraft:overworld if block {x} {100+y} {z} {block_id} run say SG01_TEMPLATE_PROBE_{i:02d}_MATCH\n")
        out.write(f"execute in minecraft:overworld unless block {x} {100+y} {z} {block_id} run say SG01_TEMPLATE_PROBE_{i:02d}_MISS\n")
PY
python3 "$fixture/rcon.py" < "$evidence/template-probes.commands" | tee -a "$evidence/runtime-commands.log"
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
save-all flush
CMDS
mkdir -p "$evidence/world/template-only"
cp -a "$run/world/region/." "$evidence/world/template-only/"
python3 "$fixture/probe-world.py" \
  --region-dir "$evidence/world/template-only" \
  --template "$template_nbt" --origin 0 100 0 \
  --server-log "$fixture/run/logs/server.log" \
  --output "$evidence/template-world-probes.json"
python3 - "$evidence/template-world-probes.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
if r["saved_world_samples_matched"] != r["sample_count"]:
    raise SystemExit("Saved chunk palette does not match all NBT-derived states")
if any(s["rcon_probe"] != "MATCH" for s in r["samples"]):
    raise SystemExit("At least one live explicit-overworld block probe did not match")
PY
mark_stage template-world-write PASS "$result_file"

# Place connector templates separately to verify IDs, then verify the jigsaw
# assembled world after the direct-template checks have passed.
current_stage=connector-template-placement
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute in minecraft:overworld run place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_north 100 100 0
execute in minecraft:overworld run place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_east 130 100 0
execute in minecraft:overworld run place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_south 160 100 0
execute in minecraft:overworld run place template moreminecrafts:forgotten_kingdom/central_cavern/tunnel_west 190 100 0
CMDS
for template in tunnel_north tunnel_east tunnel_south tunnel_west; do
  grep -Fq "RESULT Loaded template \"moreminecrafts:forgotten_kingdom/central_cavern/$template\"" "$evidence/runtime-commands.log"
done
mark_stage connector-template-placement PASS "$result_file"

current_stage=jigsaw-placement
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute in minecraft:overworld run place structure moreminecrafts:forgotten_kingdom/central_cavern 0 100 0
CMDS
grep -Fq 'RESULT Generated structure "moreminecrafts:forgotten_kingdom/central_cavern"' "$evidence/runtime-commands.log"
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
save-all flush
CMDS
mkdir -p "$evidence/world/jigsaw-assembled"
cp -a "$run/world/region/." "$evidence/world/jigsaw-assembled/"
python3 "$fixture/probe-world.py" \
  --region-dir "$evidence/world/jigsaw-assembled" \
  --template "$template_nbt" --origin 0 100 0 \
  --server-log "$fixture/run/logs/server.log" \
  --jigsaw-transforms "$repo/exports/sg-01/forgotten-underground-kingdom/visual/validation-report.json" \
  --output "$evidence/jigsaw-world-probes.json"
python3 - "$evidence/jigsaw-world-probes.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
bad_passages = {d: p for d, p in r["jigsaw_passage_floor_probes"].items() if not p["match"]}
bad_pieces = {n: p for n, p in r["jigsaw_piece_samples"].items() if p["matched"] != p["sample_count"]}
if bad_passages or bad_pieces:
    raise SystemExit(f"Jigsaw world-data mismatch: passages={bad_passages}; pieces={bad_pieces}")
PY
mark_stage jigsaw-placement PASS "$result_file"
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute in minecraft:overworld run time set noon
execute in minecraft:overworld run weather clear
CMDS
echo 'runtime-place=PASS'
