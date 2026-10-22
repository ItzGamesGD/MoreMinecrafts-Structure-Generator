"""Build the Stage 24-I datapack: Stage 24-H (protection + interior clearance) + roof protection overlays.

For each module with protected roof cells (tools/stage24i/roof.py) the restored pool entry gains one element,
inserted directly before the Stage 24-H clearance element:
    { "location": "moreminecrafts:ancient_city/roof/<module>",
      "processors": "moreminecrafts:ancient_city_functional_protection" }
The roof template has the module's size and DataVersion and stores exactly the roof cells with their Stage 24-F
states; the processor list is the Stage 24-G one (generic degradation without block_rot), so a roof cell that the main
pass rotted is written back and cracks exactly as the main pass would have cracked it. Approved NBTs, Stage 24-G and
Stage 24-H files are copied byte-for-byte.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, ROOT, load_nbt  # noqa: E402
from tools.stage24g.build import write_nbt, sha, TEMPLATE_ID, PROTECTION_LIST, overlay_nbt  # noqa: E402
from tools.stage24h.build import CLEARANCE_ID  # noqa: E402
from tools.stage24i import roof as R  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
H_PACK = ROOT / "artifacts/ancient-city-restoration/stage-24h/datapack"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"
ROOF_ID = "moreminecrafts:ancient_city/roof/{m}"


def pool_override(h_pool: dict, roofed) -> dict:
    pool = copy.deepcopy(h_pool)
    done = set()
    for entry in pool["elements"]:
        el = entry["element"]
        if el.get("element_type") != "minecraft:list_pool_element":
            continue
        first = el["elements"][0]
        m = first.get("location", "").rsplit("/", 1)[-1]
        if m not in roofed or first.get("location") != TEMPLATE_ID.format(m=m):
            continue
        locs = [e.get("location") for e in el["elements"]]
        i = locs.index(CLEARANCE_ID.format(m=m))
        el["elements"].insert(i, {"element_type": "minecraft:single_pool_element", "location": ROOF_ID.format(m=m),
                                  "processors": PROTECTION_LIST, "projection": "rigid"})
        done.add(m)
    assert done == set(roofed), (done, roofed)
    return pool


def build(out: Path = D24I):
    roofs = R.build()
    pack = out / "datapack"
    shutil.rmtree(pack, ignore_errors=True)
    shutil.copytree(H_PACK, pack)
    meta = json.loads((pack / "pack.mcmeta").read_text())
    meta["pack"]["description"] = "Stage 24-I: restored Ancient City modules with functional protection, interior clearance and roof protection"
    (pack / "pack.mcmeta").write_text(json.dumps(meta, indent=1) + "\n")
    roofed = [m for m in MODULES if roofs[m]["roof_cells"]]
    man = {"stage24h_pack": str(H_PACK.relative_to(ROOT)), "roofed_modules": roofed, "modules": {}}
    for m in MODULES:
        cells = {tuple(c["pos"]): c["state"] for c in roofs[m]["roof_cells"]}
        info = {k: v for k, v in roofs[m].items() if k != "roof_cells"}
        info["roof_cells"] = len(cells)
        if cells:
            dst = pack / f"data/moreminecrafts/structure/ancient_city/roof/{m}.nbt"
            dst.parent.mkdir(parents=True, exist_ok=True)
            write_nbt(overlay_nbt(load_nbt(D24F / m / "restored.nbt"), cells), dst)
            info["roof_nbt"] = dst.relative_to(out).as_posix()
            info["roof_sha256"] = sha(dst)
        man["modules"][m] = info
    pp = pack / "data/minecraft/worldgen/template_pool/ancient_city/structures.json"
    pp.write_text(json.dumps(pool_override(json.loads((H_PACK / "data/minecraft/worldgen/template_pool/ancient_city/structures.json").read_text()), roofed), indent=2) + "\n")
    man["pool_sha256"] = sha(pp)
    (out / "roof").mkdir(parents=True, exist_ok=True)
    (out / "roof/roof-cells.json").write_text(json.dumps(roofs, indent=1) + "\n")
    (out / "roof/BUILD-MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24I))
    a = ap.parse_args()
    print(json.dumps(build(Path(a.out)), indent=1)[:1500])
