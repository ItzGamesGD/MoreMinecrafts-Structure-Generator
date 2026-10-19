#!/usr/bin/env bash
# SG-02/SG-03 acceptance on one machine: vanilla 26.3 server placement + jigsaw assemblies +
# native Minecraft client screenshots. Usage: run-stage.sh <repo> <sg02|sg03> <pack-dir> [evidence-dir]
set -euo pipefail
repo=$1
stage=$2
pack=$3
fixture="$repo/validation/minecraft-visual"
evidence=${4:-$fixture/evidence/$stage}
work="$fixture/run/$stage"
java_bin=${JAVA_BIN:-java}
mkdir -p "$evidence" "$work"

# Vanilla server jar straight from Mojang's version manifest (26.3).
if [ ! -f "$work/server.jar" ]; then
  python3 - "$work/server.jar" <<'PY'
import json, sys, urllib.request
manifest = json.load(urllib.request.urlopen("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))
url = next(v["url"] for v in manifest["versions"] if v["id"] == "26.3")
server = json.load(urllib.request.urlopen(url))["downloads"]["server"]["url"]
urllib.request.urlretrieve(server, sys.argv[1])
PY
fi
cd "$repo"
python3 "$fixture/run_runtime.py" --pack "$pack" --evidence "$evidence" --run-dir "$work/server" \
  --java-cmd "$java_bin -Xmx3G -jar $work/server.jar nogui" --assemblies "${ASSEMBLIES:-6}" --keep-server --label "$stage"
echo 'runtime-place=PASS'
stop_server() { kill "$(cat "$work/server.pid")" 2>/dev/null || true; }
trap stop_server EXIT
python3 "$fixture/plan_cameras.py" --pack "$pack" --report "$evidence/runtime-report.json" --stage "$stage" --output "$evidence/cameras.json"
export LIBGL_ALWAYS_SOFTWARE=1 MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
python3 "$fixture/capture_client.py" --cameras "$evidence/cameras.json" --evidence "$evidence" --settle "${SETTLE:-10}"
