"""Stage 24-I roof protection: roof rule, roof templates, pool, determinism; earlier files unchanged."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.stage24c.common import MODULES, load_nbt, blocks_of  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g.roles import Template  # noqa: E402
from tools.stage24h import build as HB  # noqa: E402
from tools.stage24h.mask import build_mask  # noqa: E402
from tools.stage24i import build as B  # noqa: E402
from tools.stage24i import roof as R  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24G = ROOT / "artifacts/ancient-city-restoration/stage-24g"
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"
PACK = D24I / "datapack"
ROOFS = json.loads((D24I / "roof/roof-cells.json").read_text())
POOL = "data/minecraft/worldgen/template_pool/ancient_city/structures.json"


def cells(m):
    return {tuple(e["pos"]): e["state"] for e in ROOFS[m]["roof_cells"]}


def test_approved_nbts_and_stage24h_files_unchanged():
    for m in MODULES:
        assert (PACK / f"data/minecraft/structure/ancient_city/structures/{m}.nbt").read_bytes() == (D24F / m / "restored.nbt").read_bytes()
    for f in (D24H / "datapack").rglob("*"):
        rel = f.relative_to(D24H / "datapack")
        if f.is_file() and rel.as_posix() not in ("pack.mcmeta", POOL):
            assert (PACK / rel).read_bytes() == f.read_bytes(), rel


def test_build_is_deterministic(tmp_path):
    B.build(tmp_path)
    for f in PACK.rglob("*"):
        if f.is_file():
            assert (tmp_path / "datapack" / f.relative_to(PACK)).read_bytes() == f.read_bytes(), f
    assert json.loads((tmp_path / "roof/roof-cells.json").read_text()) == ROOFS


def test_roof_counts_are_the_verified_ones():
    assert {m: len(v["roof_cells"]) for m, v in ROOFS.items()} == {
        "large_ruin_1": 0, "medium_ruin_1": 64, "medium_ruin_2": 78, "small_ruin_1": 29, "small_ruin_2": 11,
        "sauna_1": 0, "large_pillar_1": 0, "medium_pillar_1": 0}
    assert (4, 4, 4) in cells("small_ruin_1")  # the seed 24008 lava entry point


@pytest.mark.parametrize("m", MODULES)
def test_roof_cells_follow_the_rule(m):
    t = Template(D24F / m / "restored.nbt")
    mask = build_mask(t)
    inv = json.loads((D24G / "protection/protected-cells.json").read_text())
    prot = {tuple(e["pos"]) for e in inv[m]["protected"]}
    cleared = {tuple(p) for v in json.loads((D24H / "mask/interior-masks.json").read_text())[m]["cleared"].values() for p in v}
    for p, st in cells(m).items():
        assert t.at(p) == st
        assert P.name(st) in P.ANCIENT_CITY_REPLACEABLE and p not in prot and p not in cleared
        assert mask[(p[0], p[1] - 1, p[2])] == "room_interior"
        above = (p[0], p[1] + 1, p[2])
        assert not t.inside(above) or mask[above] in ("exterior", "decorative_void")
    assert list(cells(m)) == R.roof_cells(t, mask, prot)


@pytest.mark.parametrize("m", [m for m in MODULES if ROOFS[m]["roof_cells"]])
def test_roof_template_holds_only_roof_cells(m):
    main = load_nbt(D24F / m / "restored.nbt")
    ov = load_nbt(PACK / f"data/moreminecrafts/structure/ancient_city/roof/{m}.nbt")
    assert [int(v) for v in ov["size"]] == [int(v) for v in main["size"]]
    assert int(ov["DataVersion"]) == int(main["DataVersion"]) and len(ov["entities"]) == 0
    b = {p: s for p, (s, _) in blocks_of(ov).items()}
    assert b == cells(m)


def test_pool_only_inserts_roof_elements_before_the_clearance_element():
    h = json.loads((D24H / "datapack" / POOL).read_text())
    i = json.loads((PACK / POOL).read_text())
    assert len(h["elements"]) == len(i["elements"]) and h.get("fallback") == i.get("fallback")
    seen = set()
    for a, b in zip(h["elements"], i["elements"]):
        ea, eb = a["element"], b["element"]
        if ea != eb:
            m = ea["elements"][0]["location"].rsplit("/", 1)[-1]
            roof = {"element_type": "minecraft:single_pool_element", "location": B.ROOF_ID.format(m=m),
                    "processors": B.PROTECTION_LIST, "projection": "rigid"}
            k = [e.get("location") for e in ea["elements"]].index(HB.CLEARANCE_ID.format(m=m))
            assert eb["elements"] == ea["elements"][:k] + [roof] + ea["elements"][k:]
            assert {x: y for x, y in eb.items() if x != "elements"} == {x: y for x, y in ea.items() if x != "elements"}
            seen.add(m)
    assert seen == {m for m in MODULES if ROOFS[m]["roof_cells"]}


def test_roof_never_covers_sauna_water_or_jigsaws():
    for m in MODULES:
        for p, st in cells(m).items():
            assert not st.startswith(("minecraft:water", "minecraft:jigsaw"))
