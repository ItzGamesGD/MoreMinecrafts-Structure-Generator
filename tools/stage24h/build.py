"""Build the Stage 24-H datapack: Stage 24-G functional protection + interior clearance overlays.

Each restored entry of minecraft:ancient_city/structures becomes (or stays) a list_pool_element and gains one more
element, appended last:
    { "location": "moreminecrafts:ancient_city/interior/<module>",
      "processors": "moreminecrafts:ancient_city_interior_clearance" }
The clearance template has the module's size and DataVersion and stores minecraft:air at exactly the cells of the
module's clearance mask (tools/stage24h/mask.py) — never at a cell the module's own template stores, so it cannot
overwrite the building. Its processor list is only `protected_blocks #features_cannot_replace`: it never replaces a
chest, spawner, trial spawner, vault, bedrock, end portal frame or reinforced deepslate already in the world.
The eight approved NBTs and the six Stage 24-G overlays are copied byte-for-byte.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

import nbtlib
from nbtlib import tag

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, ROOT, load_nbt, PACK_FORMAT  # noqa: E402
from tools.stage24g.build import write_nbt, sha, TEMPLATE_ID  # noqa: E402
from tools.stage24h import mask as M  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
G_PACK = ROOT / "artifacts/ancient-city-restoration/stage-24g/datapack"
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
NS = "moreminecrafts"
CLEARANCE_LIST = f"{NS}:ancient_city_interior_clearance"
CLEARANCE_ID = NS + ":ancient_city/interior/{m}"


def clearance_nbt(main_root, cells) -> nbtlib.Compound:
    root = nbtlib.Compound()
    root["DataVersion"] = copy.deepcopy(main_root["DataVersion"])
    root["size"] = copy.deepcopy(main_root["size"])
    root["palette"] = tag.List[tag.Compound]([tag.Compound({"Name": tag.String("minecraft:air")})])
    root["blocks"] = tag.List[tag.Compound]([tag.Compound({"pos": tag.List[tag.Int](list(p)), "state": tag.Int(0)})
                                             for p in sorted(cells, key=lambda p: (p[1], p[2], p[0]))])
    root["entities"] = tag.List[tag.Compound]([])
    return root


def clearance_processor_list() -> dict:
    return {"processors": [{"processor_type": "minecraft:protected_blocks", "value": "#minecraft:features_cannot_replace"}]}


def pool_override(g_pool: dict, wrapped) -> dict:
    pool = copy.deepcopy(g_pool)
    done = set()
    for entry in pool["elements"]:
        el = entry["element"]
        first = el["elements"][0] if el.get("element_type") == "minecraft:list_pool_element" else el
        loc = first.get("location", "")
        m = loc.rsplit("/", 1)[-1]
        if m not in wrapped or loc != TEMPLATE_ID.format(m=m) or first.get("element_type") != "minecraft:single_pool_element":
            continue
        clear = {"element_type": "minecraft:single_pool_element", "location": CLEARANCE_ID.format(m=m),
                 "processors": CLEARANCE_LIST, "projection": "rigid"}
        if el.get("element_type") == "minecraft:list_pool_element":
            el["elements"].append(clear)
        else:
            entry["element"] = {"element_type": "minecraft:list_pool_element", "elements": [el, clear], "projection": "rigid"}
        done.add(m)
    assert done == set(wrapped), (done, wrapped)
    return pool


def build(out: Path = D24H):
    masks = M.build(D24F)
    pack = out / "datapack"
    shutil.rmtree(pack, ignore_errors=True)
    shutil.copytree(G_PACK, pack)  # Stage 24-G pack: approved NBTs, protection overlays, protection processor list
    meta = json.loads((pack / "pack.mcmeta").read_text())
    meta["pack"]["description"] = "Stage 24-H: restored Ancient City modules with functional protection and interior clearance"
    (pack / "pack.mcmeta").write_text(json.dumps(meta, indent=1) + "\n")
    wrapped = [m for m in MODULES if any(masks[m]["cleared"].values())]
    man = {"stage24g_pack": str(G_PACK.relative_to(ROOT)), "modules": {}, "clearance_modules": wrapped}
    for m in MODULES:
        cells = [tuple(p) for v in masks[m]["cleared"].values() for p in v]
        info = {"structure_sha256": sha(pack / f"data/minecraft/structure/ancient_city/structures/{m}.nbt"),
                "stage24f_sha256": sha(D24F / m / "restored.nbt"), "cleared_cells": len(cells),
                "cleared_by_class": {k: len(v) for k, v in masks[m]["cleared"].items() if v}}
        if cells:
            dst = pack / f"data/{NS}/structure/ancient_city/interior/{m}.nbt"
            dst.parent.mkdir(parents=True, exist_ok=True)
            write_nbt(clearance_nbt(load_nbt(D24F / m / "restored.nbt"), cells), dst)
            info["clearance_nbt"] = dst.relative_to(out).as_posix()
            info["clearance_sha256"] = sha(dst)
        man["modules"][m] = info
    pl = pack / f"data/{NS}/worldgen/processor_list/ancient_city_interior_clearance.json"
    pl.write_text(json.dumps(clearance_processor_list(), indent=2) + "\n")
    pp = pack / "data/minecraft/worldgen/template_pool/ancient_city/structures.json"
    pp.write_text(json.dumps(pool_override(json.loads((G_PACK / "data/minecraft/worldgen/template_pool/ancient_city/structures.json").read_text()), wrapped), indent=2) + "\n")
    man["pool_sha256"] = sha(pp)
    (out / "mask").mkdir(parents=True, exist_ok=True)
    (out / "mask/interior-masks.json").write_text(json.dumps(masks, indent=1) + "\n")
    (out / "mask/BUILD-MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24H))
    a = ap.parse_args()
    print(json.dumps(build(Path(a.out)), indent=1))
