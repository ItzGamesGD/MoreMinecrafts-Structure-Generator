"""Build the Stage 24-G functional-protection datapack from the Stage 24-F final candidate set.

Mechanism (verified against the decompiled 26.1.2 engine, see stage-24g/INVESTIGATION.md):
  each of the eight restored entries of minecraft:ancient_city/structures becomes a minecraft:list_pool_element
      [ the unchanged single_pool_element (Stage 24-F NBT, minecraft:ancient_city_generic_degradation),
        a protection overlay single_pool_element (same size, only the role-protected cells,
        moreminecrafts:ancient_city_functional_protection = generic degradation WITHOUT block_rot) ]
  ListPoolElement places its elements in order with the same position/rotation, takes its jigsaws from the first
  element only and its bounding box as the union (identical sizes -> identical box), so jigsaw assembly is unchanged.
  The overlay re-writes the protected cells block_rot dropped; the rule list is kept, and because RuleProcessor seeds a
  fresh RandomSource from the world position the overlay cracks exactly the same bricks as the main pass.
Every other pool entry, the vanilla processor lists and the eight approved NBTs are left byte-for-byte unchanged.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

import nbtlib
from nbtlib import tag

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, ROOT, load_nbt, PACK_FORMAT  # noqa: E402
from tools.stage24g import roles as R  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24G = ROOT / "artifacts/ancient-city-restoration/stage-24g"
FIX = ROOT / "tests/fixtures/stage24g"
VANILLA_POOL = FIX / "vanilla-26.1.2-ancient_city-structures-pool.json"
VANILLA_GENERIC = FIX / "vanilla-26.1.2-ancient_city_generic_degradation.json"
NS = "moreminecrafts"
PROTECTION_LIST = f"{NS}:ancient_city_functional_protection"
OVERLAY_ID = NS + ":ancient_city/protection/{m}"
TEMPLATE_ID = "minecraft:ancient_city/structures/{m}"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_nbt(root: nbtlib.Compound, path: Path):
    """Deterministic gzip (mtime 0) so rebuilds are byte-identical."""
    buf = io.BytesIO()
    nbtlib.File(root).write(buf)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(buf.getvalue(), compresslevel=9, mtime=0))


def state_tag(state: str) -> tag.Compound:
    name, props = (state.split("[", 1) + [""])[:2]
    c = tag.Compound({"Name": tag.String(name)})
    if props:
        c["Properties"] = tag.Compound({k: tag.String(v) for k, v in (kv.split("=", 1) for kv in props.rstrip("]").split(","))})
    return c


def overlay_nbt(main_root, cells: dict) -> nbtlib.Compound:
    root = nbtlib.Compound()
    root["DataVersion"] = copy.deepcopy(main_root["DataVersion"])
    root["size"] = copy.deepcopy(main_root["size"])
    pal, idx, blocks = [], {}, []
    for pos in sorted(cells, key=lambda p: (p[1], p[2], p[0])):
        s = cells[pos]
        if s not in idx:
            idx[s] = len(pal)
            pal.append(state_tag(s))
        blocks.append(tag.Compound({"pos": tag.List[tag.Int](list(pos)), "state": tag.Int(idx[s])}))
    root["palette"] = tag.List[tag.Compound](pal)
    root["blocks"] = tag.List[tag.Compound](blocks)
    root["entities"] = tag.List[tag.Compound]([])
    return root


def protection_processor_list() -> dict:
    """minecraft:ancient_city_generic_degradation minus its block_rot entry (rule list and protected_blocks kept)."""
    generic = json.loads(VANILLA_GENERIC.read_text())
    procs = [p for p in generic["processors"] if p["processor_type"] != "minecraft:block_rot"]
    assert len(procs) == len(generic["processors"]) - 1
    return {"processors": procs}


def pool_override(selected=MODULES) -> dict:
    pool = json.loads(VANILLA_POOL.read_text())
    wrapped = 0
    for entry in pool["elements"]:
        el = entry["element"]
        loc = el.get("location", "")
        m = loc.rsplit("/", 1)[-1] if el.get("element_type") == "minecraft:single_pool_element" else None
        if m in selected and loc == TEMPLATE_ID.format(m=m):
            assert el["processors"] == "minecraft:ancient_city_generic_degradation" and el["projection"] == "rigid"
            entry["element"] = {
                "element_type": "minecraft:list_pool_element",
                "elements": [el, {"element_type": "minecraft:single_pool_element", "location": OVERLAY_ID.format(m=m),
                                  "processors": PROTECTION_LIST, "projection": "rigid"}],
                "projection": "rigid",
            }
            wrapped += 1
    assert wrapped == len(selected), wrapped
    return pool


def build(out: Path = D24G, src: Path = D24F):
    inv = R.build(src)
    ov_dir = out / "protection/overlays"
    pack = out / "datapack"
    shutil.rmtree(pack, ignore_errors=True)
    (pack / "pack.mcmeta").parent.mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(json.dumps({"pack": {"description": "Stage 24-G: restored Ancient City modules with role-based functional protection", **PACK_FORMAT}}, indent=1) + "\n")
    manifest = {"source_final_candidates": str(src.relative_to(ROOT)), "modules": {}}
    # StructureTemplate.placeInWorld returns false for an empty block list, so a module whose protected cells can never
    # be dropped keeps its plain pool entry instead of an empty overlay
    wrapped = [m for m in MODULES if inv[m]["overlay"]]
    shutil.rmtree(out / "protection/overlays", ignore_errors=True)
    for m in MODULES:
        main = src / m / "restored.nbt"
        dst = pack / "data/minecraft/structure/ancient_city/structures" / f"{m}.nbt"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(main, dst)
        if m not in wrapped:
            manifest["modules"][m] = {"structure_nbt": dst.relative_to(out).as_posix(), "structure_sha256": sha(dst),
                                      "stage24f_sha256": sha(main), "overlay_nbt": None, "overlay_cells": 0,
                                      "pool_entry": "unchanged single_pool_element (no protected cell can be dropped)"}
            continue
        cells = {tuple(c["pos"]): c["state"] for c in inv[m]["overlay"]}
        ov_root = overlay_nbt(load_nbt(main), cells)
        write_nbt(ov_root, ov_dir / f"{m}.nbt")
        odst = pack / f"data/{NS}/structure/ancient_city/protection/{m}.nbt"
        odst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ov_dir / f"{m}.nbt", odst)
        manifest["modules"][m] = {"structure_nbt": dst.relative_to(out).as_posix(), "structure_sha256": sha(dst),
                                  "stage24f_sha256": sha(main), "overlay_nbt": (ov_dir / f"{m}.nbt").relative_to(out).as_posix(),
                                  "overlay_sha256": sha(ov_dir / f"{m}.nbt"), "overlay_cells": len(cells),
                                  "pool_entry": "list_pool_element [restored template, protection overlay]"}
    pl = pack / f"data/{NS}/worldgen/processor_list/ancient_city_functional_protection.json"
    pl.parent.mkdir(parents=True, exist_ok=True)
    pl.write_text(json.dumps(protection_processor_list(), indent=2) + "\n")
    pp = pack / "data/minecraft/worldgen/template_pool/ancient_city/structures.json"
    pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_text(json.dumps(pool_override(wrapped), indent=2) + "\n")
    manifest["wrapped_modules"] = wrapped
    (out / "protection").mkdir(parents=True, exist_ok=True)
    (out / "protection/protected-cells.json").write_text(json.dumps(inv, indent=1) + "\n")
    manifest["processor_list_sha256"] = sha(pl)
    manifest["pool_override_sha256"] = sha(pp)
    manifest["vanilla_pool_sha256"] = sha(VANILLA_POOL)
    (out / "protection/BUILD-MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24G))
    a = ap.parse_args()
    print(json.dumps(build(Path(a.out)), indent=1))
