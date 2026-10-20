"""Stage 24-H interior clearance: mask invariants, overlay templates, pool, determinism."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.stage24c.common import MODULES, load_nbt, blocks_of  # noqa: E402
from tools.stage24h import build as B  # noqa: E402
from tools.stage24h import mask as M  # noqa: E402
from tools.stage24g.roles import Template  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24G = ROOT / "artifacts/ancient-city-restoration/stage-24g"
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
PACK = D24H / "datapack"
MASKS = json.loads((D24H / "mask/interior-masks.json").read_text())
MAN = json.loads((D24H / "mask/BUILD-MANIFEST.json").read_text())


def cleared(m):
    return {tuple(p) for v in MASKS[m]["cleared"].values() for p in v}


def test_approved_nbts_and_stage24g_files_unchanged():
    for m in MODULES:
        assert (PACK / f"data/minecraft/structure/ancient_city/structures/{m}.nbt").read_bytes() == (D24F / m / "restored.nbt").read_bytes()
    for f in (D24G / "datapack").rglob("*"):
        rel = f.relative_to(D24G / "datapack")
        if f.is_file() and rel.as_posix() not in ("pack.mcmeta", "data/minecraft/worldgen/template_pool/ancient_city/structures.json"):
            assert (PACK / rel).read_bytes() == f.read_bytes(), rel


def test_build_is_deterministic(tmp_path):
    B.build(tmp_path)
    for f in PACK.rglob("*"):
        if f.is_file():
            assert (tmp_path / "datapack" / f.relative_to(PACK)).read_bytes() == f.read_bytes(), f
    assert json.loads((tmp_path / "mask/interior-masks.json").read_text()) == MASKS


def test_masks_match_the_rules():
    assert M.build(D24F) == MASKS


@pytest.mark.parametrize("m", MODULES)
def test_mask_never_touches_a_stored_cell_and_stays_in_the_box(m):
    t = Template(D24F / m / "restored.nbt")
    for p in cleared(m):
        assert t.inside(p)
        assert t.at(p) is None, (m, p, t.at(p))  # architecture, jigsaws, stored air/water are never in the mask


@pytest.mark.parametrize("m", MODULES)
def test_mask_classes_are_exclusive_and_complete(m):
    t = Template(D24F / m / "restored.nbt")
    full = M.build_mask(t)
    assert len(full) == t.size[0] * t.size[1] * t.size[2]
    assert {p for p, c in full.items() if c in M.CLEARED} == cleared(m)
    counts = MASKS[m]["class_counts"]
    assert sum(counts.values()) == len(full)


@pytest.mark.parametrize("m", MODULES)
def test_exterior_and_voids_are_not_cleared(m):
    t = Template(D24F / m / "restored.nbt")
    full = M.build_mask(t)
    for p, c in full.items():
        if c in ("exterior", "decorative_void"):
            assert p not in cleared(m)


@pytest.mark.parametrize("m", MODULES)
def test_clearance_template(m):
    main = load_nbt(D24F / m / "restored.nbt")
    ov = load_nbt(PACK / f"data/moreminecrafts/structure/ancient_city/interior/{m}.nbt")
    assert [int(v) for v in ov["size"]] == [int(v) for v in main["size"]]
    assert int(ov["DataVersion"]) == int(main["DataVersion"])
    assert len(ov["entities"]) == 0
    b = blocks_of(ov)
    assert set(b) == cleared(m)
    assert {s for s, nb in b.values()} == {"minecraft:air"} and all(nb is None for _, nb in b.values())
    assert not set(b) & set(blocks_of(main))


def test_pool_only_appends_the_clearance_element():
    g = json.loads((D24G / "datapack/data/minecraft/worldgen/template_pool/ancient_city/structures.json").read_text())
    h = json.loads((PACK / "data/minecraft/worldgen/template_pool/ancient_city/structures.json").read_text())
    assert len(g["elements"]) == len(h["elements"]) and g.get("fallback") == h.get("fallback")
    seen = set()
    for a, b in zip(g["elements"], h["elements"]):
        assert a["weight"] == b["weight"]
        ea, eb = a["element"], b["element"]
        first = ea["elements"][0] if ea.get("element_type") == "minecraft:list_pool_element" else ea
        m = first.get("location", "").rsplit("/", 1)[-1]
        if m in MODULES and first.get("location") == B.TEMPLATE_ID.format(m=m):
            seen.add(m)
            clear = {"element_type": "minecraft:single_pool_element", "location": B.CLEARANCE_ID.format(m=m),
                     "processors": B.CLEARANCE_LIST, "projection": "rigid"}
            prev = ea["elements"] if ea.get("element_type") == "minecraft:list_pool_element" else [ea]
            assert eb["element_type"] == "minecraft:list_pool_element" and eb["projection"] == "rigid"
            assert eb["elements"] == prev + [clear]
        else:
            assert a == b
    assert seen == set(MODULES)


def test_clearance_processor_list_only_protects_existing_special_blocks():
    pl = json.loads((PACK / "data/moreminecrafts/worldgen/processor_list/ancient_city_interior_clearance.json").read_text())
    assert pl == {"processors": [{"processor_type": "minecraft:protected_blocks", "value": "#minecraft:features_cannot_replace"}]}


def test_known_obstructions_are_inside_the_mask():
    """The Stage 24-F/24-G sweep obstructions (terrain in walkable cells) are all authorised cells."""
    rows = json.loads((D24G / "worldgen/g24-terrain-classification.json").read_text())
    obstr = [r for r in rows if r["class"] in ("functional_obstruction",) or (r["class"] == "potential_generation_hazard" and r["module"] == "small_ruin_1")]
    assert obstr
    for r in obstr:
        assert tuple(r["template_pos"]) in cleared(r["module"]), r


def test_sauna_water_and_protected_cells_untouched():
    inv = json.loads((D24G / "protection/protected-cells.json").read_text())
    for m in MODULES:
        b = blocks_of(load_nbt(D24F / m / "restored.nbt"))
        water = {p for p, (s, _) in b.items() if s.startswith("minecraft:water")}
        assert not water & cleared(m)
        assert not {tuple(e["pos"]) for e in inv[m]["protected"]} & cleared(m)
