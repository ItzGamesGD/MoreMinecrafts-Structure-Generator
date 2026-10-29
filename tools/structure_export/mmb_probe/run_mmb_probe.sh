#!/usr/bin/env bash
# Load one MM-ST export inside the real MoreMinecrafts-Beta runtime (Fabric gametest server).
# The MMB repository is cloned into a scratch directory; the source checkout is never modified.
#   run_mmb_probe.sh <config.toml> <mmb-repo-or-url> <mmb-commit> <work-dir>
# Needs JAVA_HOME pointing at a Java 25 JDK and network access for Gradle/Loom dependencies.
set -euo pipefail
CONFIG=$1 MMB=$2 COMMIT=$3 WORK=$4
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
CLONE="$WORK/mmb"
rm -rf "$CLONE" && git clone -q --no-hardlinks "$MMB" "$CLONE" && git -C "$CLONE" checkout -q "$COMMIT"
cd "$ROOT"
uv run --project vendor/mcbuild python - "$CONFIG" "$CLONE" <<'PY'
import json, shutil, sys
from pathlib import Path
from tools.structure_export.convert import load_config, load_reference, resolve_state
from tools.structure_export.schem import parse_state, read_schematic
config, clone = load_config(Path(sys.argv[1])), Path(sys.argv[2])
namespace, name = config.structure_id.split(":", 1)
target = clone / "src/main/resources/data" / namespace / "structure" / f"{name}.nbt"
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(config.nbt_path, target)
reference, schem = load_reference(config.target), read_schematic(config.source)
lines = [f"{config.structure_id} {' '.join(map(str, schem.size))}"]
for index, palette_index in enumerate(schem.cells):
    block_id, props = parse_state(schem.palette[palette_index])
    if config.air == "omit" and block_id == "minecraft:air":
        continue
    full, _ = resolve_state(block_id, props, reference)
    state = block_id + ("[" + ",".join(f"{k}={v}" for k, v in full) + "]" if full else "")
    lines.append(" ".join(map(str, schem.position(index))) + " " + state)
(clone / "src/gametest/resources/mmst").mkdir(parents=True, exist_ok=True)
(clone / "src/gametest/resources/mmst/expected.txt").write_text("\n".join(lines) + "\n")
mod = clone / "src/gametest/resources/fabric.mod.json"
data = json.loads(mod.read_text())
data["entrypoints"] = {"fabric-gametest": ["dev.itzgamesgd.moreminecrafts.mmstprobe.MmstExportProbeGameTests"]}
mod.write_text(json.dumps(data, indent=2))
PY
mkdir -p "$CLONE/src/gametest/java/dev/itzgamesgd/moreminecrafts/mmstprobe"
cp "$HERE/MmstExportProbeGameTests.java" "$CLONE/src/gametest/java/dev/itzgamesgd/moreminecrafts/mmstprobe/"
cd "$CLONE"
./gradlew runGameTest --no-daemon 2>&1 | tee "$WORK/mmb-probe.log" | grep -E "MMST_EXPORT_PROBE|GAME TESTS COMPLETE|required tests|BUILD"
