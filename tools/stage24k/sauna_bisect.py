"""Bisect of the Stage 24-K sauna pool finding (seeds 24006 and 24007: one floor-level pool cell is a sculk catalyst).

Builds two scratch packs from the Stage 24-I and Stage 24-K packs — `kLonly` (large_pillar_1 from 24-K, medium_pillar_1
from 24-I) and `kMonly` (the reverse) — generates the two seeds with each, and records which pool cells of the sauna
hold no water. Result (committed as worldgen/sauna-bisect.json): kLonly keeps all pool cells wet, kMonly loses the same cell
as the full Stage 24-K pack — although seed 24007 has no medium_pillar_1 piece at all."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "artifacts/ancient-city-restoration"
K = AR / "stage-24k"
S1, S2 = "data/minecraft/structure/ancient_city/structures", "data/moreminecrafts/structure/ancient_city/protection"
SCRATCH = Path("/tmp/mc/bisect")


def packs():
    shutil.rmtree(SCRATCH, ignore_errors=True)
    for name, swap in (("kLonly", "medium_pillar_1"), ("kMonly", "large_pillar_1")):
        shutil.copytree(K / "derived-24i/datapack", SCRATCH / name)
        for sub in (S1, S2):
            shutil.copyfile(AR / "stage-24i/datapack" / sub / f"{swap}.nbt", SCRATCH / name / sub / f"{swap}.nbt")


def generate():
    py = str(ROOT / "vendor/mcbuild/.venv/bin/python")
    (SCRATCH / "out").mkdir(parents=True, exist_ok=True)
    for v in ("kLonly", "kMonly"):
        subprocess.run([py, "-I", "tools/stage24c/worldgen.py", "--seeds", "24006", "24007", "--variants", v, "--src", str(K / "final-candidates"),
                        "--pack", str(SCRATCH / v), "--out", str(SCRATCH / "out")], cwd=ROOT, check=True)


def read():
    from tools.stage24c.common import OUT, load_nbt, blocks_of
    from tools.stage24c.mcserver import World
    from tools.stage24c.worldgen_analyze import ROT, rot
    water = [p for p, (s, _) in blocks_of(load_nbt(K / "final-candidates/sauna_1/restored.nbt")).items() if s.startswith("minecraft:water")]
    wet = lambda b: bool(b) and (b.startswith("minecraft:water") or "waterlogged=true" in b)  # noqa: E731
    out = {}
    for seed, idx in ((24006, 47), (24007, 41)):
        pc = json.loads((K / f"worldgen/manifest-{seed}-k24.json").read_text())["cities"][0]["pieces"][idx]
        r, o = ROT[pc["rotation"]], pc["pos"]
        for v in ("i24", "kLonly", "kMonly", "k24"):
            w = World(OUT / f"_work/wg-{seed}-{v}/world/dimensions/minecraft/overworld")
            out[f"{seed}:{v}"] = [list(q) for q in water if not wet(w.block(*[o[i] + rot(q, r)[i] for i in range(3)]))]
    (K / "worldgen/sauna-bisect.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    if "--generate" in sys.argv:
        packs()
        generate()
    print(json.dumps(read(), indent=1))
