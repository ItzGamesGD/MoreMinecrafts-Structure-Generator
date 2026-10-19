#!/usr/bin/env bash
set -euo pipefail
repo=$1
pack=$2
keep_server=${3:-}
fixture="$repo/validation/minecraft-visual"
run=${SG01_RUN_DIR:-$fixture/run/server}
server_log=${SG01_SERVER_LOG:-$fixture/run/logs/server.log}
evidence="$fixture/evidence"
result_file="$evidence/runtime-result.txt"
source "$fixture/stage-result.sh"
current_stage=server-startup
trap 'status=$?; mark_stage "$current_stage" FAIL "$result_file"; exit "$status"' ERR
mkdir -p "$run/world/datapacks" "$(dirname "$server_log")" "$fixture/run" "$evidence"
cp -a "$pack" "$run/world/datapacks/sg01"
# Minimal exporter-built control pack, kept outside the SG-01 pack under test.
PYTHONPATH="$repo" python3 "$fixture/build-control-pack.py" "$run/world/datapacks/sg01_control" > /dev/null
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
# SG01_SERVER_CMD lets a vanilla server jar replace the Fabric Loom launcher (cwd = $run).
if [ -n "${SG01_SERVER_CMD:-}" ]; then
  setsid bash -c 'cd "$1" && exec timeout 480s bash -c "$2"' _ "$run" "$SG01_SERVER_CMD" > "$server_log" 2>&1 &
else
  setsid bash -c 'cd "$1" && exec timeout 480s ./gradlew --no-daemon runServer' _ "$fixture" > "$server_log" 2>&1 &
fi
server_pid=$!
echo "$server_pid" > "$fixture/run/server.pid"
cleanup() { kill -- "-$server_pid" 2>/dev/null || kill "$server_pid" 2>/dev/null || true; }
if [ "$keep_server" != "--keep-server" ]; then trap cleanup EXIT; fi
ready=0
for _ in $(seq 1 180); do
  if grep -Fq 'Done (' "$server_log"; then ready=1; break; fi
  if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then tail -200 "$server_log"; mark_stage "$current_stage" FAIL "$result_file"; exit 1; fi
mark_stage server-startup PASS "$result_file"
current_stage=datapack-load
python3 "$fixture/rcon.py" <<'CMDS' | tee "$evidence/runtime-commands.log"
datapack list enabled
CMDS
grep -F 'file/sg01 (world)' "$evidence/runtime-commands.log"
grep -F 'file/sg01_control (world)' "$evidence/runtime-commands.log"
mark_stage datapack-load PASS "$result_file"

# Minecraft 26.x stores each dimension under world/dimensions/<namespace>/<name>/;
# older layouts used world/region. Resolve explicitly and fail loudly if neither exists.
current_stage=region-dir
if [ -d "$run/world/dimensions/minecraft/overworld/region" ]; then
  region_dir="$run/world/dimensions/minecraft/overworld/region"
elif [ -d "$run/world/region" ]; then
  region_dir="$run/world/region"
else
  find "$run/world" -maxdepth 5 -type d | head -40
  false
fi
echo "region_dir=$region_dir" | tee -a "$evidence/runtime-commands.log"

# NBT local origin is [0,0,0]. /place coordinates are absolute and use
# rotation=none, mirror=none, so world = [x, y+100, z].
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute in minecraft:overworld run forceload add -64 -64 64 64
execute in minecraft:overworld run time set noon
execute in minecraft:overworld run weather clear
CMDS
# Known-good controls, placed before SG-01 so a harness or probe fault is not
# mistaken for an SG-01 fault. Both must be seen in the world with a probe.
#  1. vanilla minecraft:igloo/top, shipped in the game jar (local [0,0,3] is snow_block)
#  2. a 3x3x3 template written by this repo's exporter into a separate control pack
current_stage=control-placement
control_probe() {
  local tag=$1 x=$2 y=$3 z=$4 block=$5
  python3 "$fixture/rcon.py" <<CMDS | tee -a "$evidence/runtime-commands.log" > /dev/null
execute in minecraft:overworld if block $x $y $z $block run say SG01_CONTROL_${tag}_MATCH
execute in minecraft:overworld unless block $x $y $z $block run say SG01_CONTROL_${tag}_MISS
CMDS
  sleep 1
  grep -Fq "SG01_CONTROL_${tag}_MATCH" "$server_log" && ! grep -Fq "SG01_CONTROL_${tag}_MISS" "$server_log"
}
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute in minecraft:overworld run forceload add 296 0 311 15
execute in minecraft:overworld run forceload add 392 0 407 15
execute in minecraft:overworld run place template minecraft:igloo/top 300 100 0
execute in minecraft:overworld run place template sg01_control:cube 400 100 0
CMDS
control_probe VANILLA_IGLOO 300 100 3 minecraft:snow_block
control_probe EXPORTER_0 400 100 0 minecraft:polished_deepslate
control_probe EXPORTER_1 401 100 0 'minecraft:stone_brick_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]'
control_probe EXPORTER_2 402 102 2 minecraft:sea_lantern
mark_stage control-placement PASS "$result_file"

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
    if state["id"] == "minecraft:air":
        continue
    samples.setdefault(block["state"], (block["pos"], state))
with open(sys.argv[2], "w") as out:
    for i, (_state_id, (local, state)) in enumerate(samples.items()):
        x, y, z = local
        props = state.get("properties", {})
        suffix = "[" + ",".join(f"{k}={v}" for k, v in props.items()) + "]" if props else ""
        block_id = state["id"] + suffix
        out.write(f"execute in minecraft:overworld if block {x} {100+y} {z} {block_id} run say SG01_TEMPLATE_PROBE_{i:02d}_MATCH\n")
        out.write(f"execute in minecraft:overworld unless block {x} {100+y} {z} {block_id} run say SG01_TEMPLATE_PROBE_{i:02d}_MISS\n")
PY
python3 "$fixture/rcon.py" < "$evidence/template-probes.commands" | tee -a "$evidence/runtime-commands.log"
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
save-all flush
CMDS
mkdir -p "$evidence/world/template-only"
cp -a "$region_dir/." "$evidence/world/template-only/"
python3 "$fixture/probe-world.py" \
  --region-dir "$evidence/world/template-only" \
  --template "$template_nbt" --origin 0 100 0 \
  --server-log "$server_log" \
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
execute in minecraft:overworld run forceload add 96 0 223 47
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
# /place structure picks its own start height (start_height -40..-20) and rotation, so it is
# placed in a clean, force-loaded area and located from the saved chunks by probe-jigsaw.py.
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute in minecraft:overworld run forceload add 920 920 1080 1080
execute in minecraft:overworld run place structure moreminecrafts:forgotten_kingdom/central_cavern 1000 100 1000
CMDS
grep -Fq 'RESULT Generated structure "moreminecrafts:forgotten_kingdom/central_cavern"' "$evidence/runtime-commands.log"
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
save-all flush
CMDS
mkdir -p "$evidence/world/jigsaw-assembled"
cp -a "$region_dir/." "$evidence/world/jigsaw-assembled/"
python3 "$fixture/probe-jigsaw.py" \
  --region-dir "$evidence/world/jigsaw-assembled" \
  --template-dir "$(dirname "$template_nbt")" \
  --search-min 900 -64 900 --search-max 1100 100 1100 \
  --output "$evidence/jigsaw-world-probes.json"
mark_stage jigsaw-placement PASS "$result_file"
python3 "$fixture/rcon.py" <<'CMDS' | tee -a "$evidence/runtime-commands.log"
execute in minecraft:overworld run time set noon
execute in minecraft:overworld run weather clear
CMDS
echo 'runtime-place=PASS'
