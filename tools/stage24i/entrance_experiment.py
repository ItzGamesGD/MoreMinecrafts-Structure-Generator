"""EXPERIMENT (not part of the Stage 24-I deliverable): can a list-element overlay clear terrain OUTSIDE its piece box?

The minimal clearance cells measured for the two blocked entrances (seed 24005 medium_ruin_1, seed 24009
large_ruin_1; tools/stage24i/entrances.py) are converted to template coordinates and stored as air in an extra
template whose declared size equals the module's (so the piece bounding box cannot change). Its processor list writes
air only where the world block is natural terrain:
    rule: location tag_match #moreminecrafts:entrance_clearable -> air ; otherwise -> structure_void
    block_ignore structure_void  (-> the template block is dropped, nothing is written)
The resulting pack (Stage 24-I + these elements) is generated on seeds 24005 and 24009 and compared with Stage 24-I.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import nbtlib
from nbtlib import tag

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import ROOT, load_nbt  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT  # noqa: E402
from tools.stage24g.build import write_nbt, TEMPLATE_ID  # noqa: E402
from tools.stage24g.terrain import inv_rot  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"
EXP = D24I / "experiment-entrance"
CLEARABLE = ["dripstone_block", "pointed_dripstone", "tuff", "calcite", "smooth_basalt", "amethyst_block", "budding_amethyst",
             "stone", "granite", "diorite", "andesite", "gravel", "clay", "sculk"]
ENTRANCE_ID = "moreminecrafts:ancient_city/entrance_experiment/{m}"
LIST_ID = "moreminecrafts:entrance_clearance_experiment"


def cells_in_template():
    survey = json.loads((D24I / "investigation/h24-entrance-survey.json").read_text())
    man = {}
    out = {}
    for r in survey:
        if r["status"] != "ok" or not r["n_cells"]:
            continue
        key = (r["seed"], r["piece_index"])
        if key not in man:
            man[key] = json.loads((ROOT / f"artifacts/ancient-city-restoration/stage-24h/worldgen/manifest-{r['seed']}-h24.json").read_text())["cities"][0]["pieces"][r["piece_index"]]
        p = man[key]
        rr, o = ROT[p["rotation"]], p["pos"]
        rel = [inv_rot((c[0] - o[0], c[1] - o[1], c[2] - o[2]), rr) for c in r["cells_to_clear"]]
        out.setdefault(r["module"], set()).update(rel)
    return {m: sorted(v) for m, v in out.items()}


def build():
    cells = cells_in_template()
    pack = EXP / "datapack"
    shutil.rmtree(pack, ignore_errors=True)
    shutil.copytree(D24I / "datapack", pack)
    (pack / "data/moreminecrafts/tags/block").mkdir(parents=True, exist_ok=True)
    (pack / "data/moreminecrafts/tags/block/entrance_clearable.json").write_text(json.dumps({"values": [f"minecraft:{b}" for b in CLEARABLE]}, indent=1))
    pl = {"processors": [
        {"processor_type": "minecraft:rule", "rules": [
            {"input_predicate": {"predicate_type": "minecraft:always_true"},
             "location_predicate": {"predicate_type": "minecraft:tag_match", "tag": "moreminecrafts:entrance_clearable"},
             "output_state": {"Name": "minecraft:air"}},
            {"input_predicate": {"predicate_type": "minecraft:always_true"},
             "location_predicate": {"predicate_type": "minecraft:always_true"},
             "output_state": {"Name": "minecraft:structure_void"}}]},
        {"processor_type": "minecraft:block_ignore", "blocks": [{"Name": "minecraft:structure_void"}]}]}
    (pack / "data/moreminecrafts/worldgen/processor_list/entrance_clearance_experiment.json").write_text(json.dumps(pl, indent=1))
    pool_p = pack / "data/minecraft/worldgen/template_pool/ancient_city/structures.json"
    pool = json.loads(pool_p.read_text())
    for m, cs in cells.items():
        main = load_nbt(D24F / m / "restored.nbt")
        root = nbtlib.Compound()
        root["DataVersion"] = copy.deepcopy(main["DataVersion"])
        root["size"] = copy.deepcopy(main["size"])  # same declared size: the piece box cannot change
        root["palette"] = tag.List[tag.Compound]([tag.Compound({"Name": tag.String("minecraft:air")})])
        root["blocks"] = tag.List[tag.Compound]([tag.Compound({"pos": tag.List[tag.Int](list(c)), "state": tag.Int(0)}) for c in cs])
        root["entities"] = tag.List[tag.Compound]([])
        write_nbt(root, pack / f"data/moreminecrafts/structure/ancient_city/entrance_experiment/{m}.nbt")
        for e in pool["elements"]:
            el = e["element"]
            if el.get("element_type") == "minecraft:list_pool_element" and el["elements"][0].get("location") == TEMPLATE_ID.format(m=m):
                el["elements"].append({"element_type": "minecraft:single_pool_element", "location": ENTRANCE_ID.format(m=m),
                                       "processors": LIST_ID, "projection": "rigid"})
    pool_p.write_text(json.dumps(pool, indent=2) + "\n")
    (EXP / "entrance-cells-template.json").write_text(json.dumps({m: [list(c) for c in v] for m, v in cells.items()}, indent=1))
    return cells


if __name__ == "__main__":
    print(build())
