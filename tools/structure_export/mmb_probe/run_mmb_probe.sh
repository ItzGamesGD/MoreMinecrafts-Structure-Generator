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
from tools.structure_export.convert import load_config
from tools.structure_export.verify import plain, read_nbt
config, clone = load_config(Path(sys.argv[1])), Path(sys.argv[2])
namespace, name = config.structure_id.split(":", 1)
target = clone / "src/main/resources/data" / namespace / "structure" / f"{name}.nbt"
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(config.nbt_path, target)
# expected = the exported states (computed connections included; `verify` and `live` check those
# against the source and the vanilla game); this probe checks that MMB loads and places them as written
template = plain(read_nbt(config.nbt_path)[1])
palette = [
    e["id"] + ("[" + ",".join(f"{k}={v}" for k, v in sorted(e.get("properties", {}).items())) + "]" if e.get("properties") else "")
    for e in template["palette"]
]
lines = [f"{config.structure_id} {' '.join(map(str, template['size']))}"]
for block in template["blocks"]:
    lines.append(" ".join(map(str, block["pos"])) + " " + palette[block["state"]])
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
