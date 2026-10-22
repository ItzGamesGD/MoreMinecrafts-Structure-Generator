"""Stage 24-G functional protection: processor model, role inventory, overlay templates, pool override."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.stage24c.common import MODULES, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.worldgen_analyze import rot  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g import build as B  # noqa: E402
from tools.stage24g import roles as R  # noqa: E402

D24G = ROOT / "artifacts/ancient-city-restoration/stage-24g"
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
FIX = ROOT / "tests/fixtures/stage24g"
INV = json.loads((D24G / "protection/protected-cells.json").read_text())
MANIFEST = json.loads((D24G / "protection/BUILD-MANIFEST.json").read_text())
PACK = D24G / "datapack"


def jvm_rows():
    rows = []
    for line in (D24G / "investigation/jvm-rng-crosscheck.txt").read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        xyz, seed, a, b = line.split()
        rows.append((tuple(int(v) for v in xyz.split(",")), int(seed), float(a), float(b)))
    return rows


@pytest.mark.parametrize("row", jvm_rows())
def test_rng_matches_jvm(row):
    pos, seed, a, b = row
    assert P.mth_seed(*pos) == seed
    r = P.LegacyRandom(seed)
    assert abs(r.next_float() - a) < 1e-7 and abs(r.next_float() - b) < 1e-7


def test_tag_and_rules_match_vanilla_fixtures():
    tag = json.loads((FIX / "vanilla-26.1.2-tag-ancient_city_replaceable.json").read_text())["values"]
    assert set(tag) == P.ANCIENT_CITY_REPLACEABLE
    fcr = json.loads((FIX / "vanilla-26.1.2-tag-features_cannot_replace.json").read_text())["values"]
    assert set(fcr) == P.FEATURES_CANNOT_REPLACE
    generic = json.loads((FIX / "vanilla-26.1.2-ancient_city_generic_degradation.json").read_text())["processors"]
    rotp = [p for p in generic if p["processor_type"] == "minecraft:block_rot"]
    assert rotp == [{"integrity": 0.95, "processor_type": "minecraft:block_rot", "rottable_blocks": "#minecraft:ancient_city_replaceable"}]
    rules = next(p for p in generic if p["processor_type"] == "minecraft:rule")["rules"]
    assert [(r["input_predicate"]["block"], P.f32(r["input_predicate"]["probability"]), r["output_state"]["Name"]) for r in rules] == P.GENERIC_RULES


def test_structure_nbts_unchanged_from_stage24f():
    for m in MODULES:
        assert (PACK / f"data/minecraft/structure/ancient_city/structures/{m}.nbt").read_bytes() == (D24F / m / "restored.nbt").read_bytes()
        assert MANIFEST["modules"][m]["structure_sha256"] == MANIFEST["modules"][m]["stage24f_sha256"]


def test_build_is_deterministic(tmp_path):
    B.build(tmp_path)
    for f in sorted((D24G / "datapack").rglob("*")):
        if f.is_file():
            assert (tmp_path / "datapack" / f.relative_to(D24G / "datapack")).read_bytes() == f.read_bytes(), f
    for name in ("protected-cells.json", "BUILD-MANIFEST.json"):
        assert (tmp_path / "protection" / name).read_text() != ""


def test_pool_override_changes_only_wrapped_restored_entries():
    van = json.loads((FIX / "vanilla-26.1.2-ancient_city-structures-pool.json").read_text())
    new = json.loads((PACK / "data/minecraft/worldgen/template_pool/ancient_city/structures.json").read_text())
    assert {k: v for k, v in van.items() if k != "elements"} == {k: v for k, v in new.items() if k != "elements"}
    assert len(van["elements"]) == len(new["elements"])
    wrapped = set(MANIFEST["wrapped_modules"])
    seen = set()
    for a, b in zip(van["elements"], new["elements"]):
        assert a["weight"] == b["weight"]
        loc = a["element"].get("location", "")
        m = loc.rsplit("/", 1)[-1]
        if a["element"].get("element_type") == "minecraft:single_pool_element" and m in wrapped and loc == B.TEMPLATE_ID.format(m=m):
            seen.add(m)
            el = b["element"]
            assert el["element_type"] == "minecraft:list_pool_element" and el["projection"] == "rigid"
            assert el["elements"][0] == a["element"]  # the restored entry itself is untouched
            assert el["elements"][1] == {"element_type": "minecraft:single_pool_element", "location": B.OVERLAY_ID.format(m=m),
                                         "processors": B.PROTECTION_LIST, "projection": "rigid"}
        else:
            assert a == b
    assert seen == wrapped


def test_protection_processor_list_is_generic_without_block_rot():
    generic = json.loads((FIX / "vanilla-26.1.2-ancient_city_generic_degradation.json").read_text())["processors"]
    prot = json.loads((PACK / "data/moreminecrafts/worldgen/processor_list/ancient_city_functional_protection.json").read_text())["processors"]
    assert prot == [p for p in generic if p["processor_type"] != "minecraft:block_rot"]


@pytest.mark.parametrize("m", MODULES)
def test_overlay_template(m):
    main = load_nbt(D24F / m / "restored.nbt")
    mb = blocks_of(main)
    info = MANIFEST["modules"][m]
    if m not in MANIFEST["wrapped_modules"]:
        assert info["overlay_cells"] == 0 and not INV[m]["overlay"]
        assert not any(e["rottable"] for e in INV[m]["protected"])
        return
    ov = load_nbt(PACK / f"data/moreminecrafts/structure/ancient_city/protection/{m}.nbt")
    assert [int(v) for v in ov["size"]] == [int(v) for v in main["size"]]
    assert int(ov["DataVersion"]) == int(main["DataVersion"])
    assert len(ov["entities"]) == 0
    ob = blocks_of(ov)
    assert len(ob) == info["overlay_cells"] > 0
    prot = {tuple(e["pos"]): e for e in INV[m]["protected"]}
    for pos, (st, nbt) in ob.items():
        assert nbt is None, "overlay carries no block entities"
        assert pos in prot and prot[pos]["roles"], "every overlay cell has a functional role"
        src, src_nbt = mb[pos]
        if src.startswith("minecraft:jigsaw"):
            # door support supplied where the jigsaw resolves to structure_void
            assert str(src_nbt["final_state"]) == "minecraft:structure_void" and "door_support" in prot[pos]["roles"]
            assert P.name(st) in P.ANCIENT_CITY_REPLACEABLE
        else:
            assert st == src and P.name(st) in P.ANCIENT_CITY_REPLACEABLE
        assert not st.startswith(("minecraft:jigsaw", "minecraft:soul_lantern", "minecraft:air"))


@pytest.mark.parametrize("m", MODULES)
def test_inventory_covers_every_functional_block(m):
    b = blocks_of(load_nbt(D24F / m / "restored.nbt"))
    prot = {tuple(e["pos"]): e for e in INV[m]["protected"]}
    ov = {tuple(e["pos"]) for e in INV[m]["overlay"]}
    for pos, (st, nb) in b.items():
        n = P.name(st)
        if n.endswith("_door"):
            assert "door" in prot[pos]["roles"]
            if "half=lower" in st:
                below = (pos[0], pos[1] - 1, pos[2])
                assert "door_support" in prot[below]["roles"]
                bst, bnb = b[below]
                sturdy_always = (P.name(bst) not in P.ANCIENT_CITY_REPLACEABLE and not bst.startswith("minecraft:jigsaw")) or \
                    (bst.startswith("minecraft:jigsaw") and str(bnb["final_state"]) != "minecraft:structure_void")
                assert sturdy_always or below in ov
        if n == "minecraft:ladder":
            assert "ladder" in prot[pos]["roles"]
            f = st.split("facing=")[1].split(",")[0].rstrip("]")
            d = R.FACING[f]
            att = (pos[0] - d[0], pos[1], pos[2] - d[2])
            assert "ladder_attach" in prot[att]["roles"]
            assert P.name(b[att][0]) not in P.ANCIENT_CITY_REPLACEABLE or att in ov
    # every protected rottable cell is in the overlay
    for pos, e in prot.items():
        if e["rottable"]:
            assert pos in ov


@pytest.mark.parametrize("m", MODULES)
def test_decorative_decay_is_kept(m):
    b = blocks_of(load_nbt(D24F / m / "restored.nbt"))
    prot = {tuple(e["pos"]) for e in INV[m]["protected"]}
    rottable = [p for p, (s, _) in b.items() if P.name(s) in P.ANCIENT_CITY_REPLACEABLE]
    decorative = [p for p in rottable if p not in prot]
    assert len(decorative) >= 0.75 * len(rottable), (len(decorative), len(rottable))
    lanterns = [p for p, (s, _) in b.items() if P.name(s) == "minecraft:soul_lantern"]
    assert not any(p in prot for p in lanterns), "lanterns keep vanilla decay"


@pytest.mark.parametrize("m", MODULES)
def test_simulated_placements_keep_protected_cells_and_decay(m):
    """Deterministic engine model over 400 random positions x 4 rotations (complements the live server check)."""
    b = blocks_of(load_nbt(D24F / m / "restored.nbt"))
    prot = {tuple(e["pos"]) for e in INV[m]["protected"]}
    ov = {tuple(e["pos"]) for e in INV[m]["overlay"]}
    # a jigsaw resolving to structure_void is never written by the main pass (JigsawReplacementProcessor -> null)
    void = {p for p, (s, nb) in b.items() if s.startswith("minecraft:jigsaw") and str(nb["final_state"]) == "minecraft:structure_void"}
    rng = random.Random(24 + MODULES.index(m))
    dec_total = dec_rot = lost_f24 = 0
    for _ in range(400):
        o = (rng.randint(-3000, 3000), rng.randint(-60, -20), rng.randint(-3000, 3000))
        for r in (0, 90, 180, 270):
            for pos, (st, _) in b.items():
                q = rot(pos, r)
                w = (o[0] + q[0], o[1] + q[1], o[2] + q[2])
                dropped = P.rot_removed(st, w) or pos in void
                if pos in prot:
                    lost_f24 += dropped
                    assert not dropped or pos in ov, (m, pos, st)
                elif P.name(st) in P.ANCIENT_CITY_REPLACEABLE:
                    dec_total += 1
                    dec_rot += dropped
    assert 0.04 < dec_rot / dec_total < 0.06, dec_rot / dec_total
    if any(INV[m]["overlay"]):
        assert lost_f24 > 0, "without the overlay these cells would be lost"
