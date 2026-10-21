"""Stage 24-K: the approved watchtower designs are integrated into production; everything else is unchanged."""
from __future__ import annotations

import filecmp
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.stage24c.common import MODULES, load_nbt, blocks_of  # noqa: E402
from tools.stage24k import build as B  # noqa: E402

AR = ROOT / "artifacts/ancient-city-restoration"
D24F, D24J, K = AR / "stage-24f/final-candidates", AR / "stage-24j", AR / "stage-24k"
TOWERS = ("large_pillar_1", "medium_pillar_1")
OTHERS = [m for m in MODULES if m not in TOWERS]
DIFF = json.loads((K / "DERIVATION-DIFF.json").read_text())
CHECKS = json.loads((K / "static-checks.json").read_text())
STRUCT = "data/minecraft/structure/ancient_city/structures/{m}.nbt"


def j(p):
    return json.loads(p.read_text())


@pytest.mark.parametrize("m", OTHERS)
def test_six_modules_byte_identical_to_stage24f(m):
    assert (K / "final-candidates" / m / "restored.nbt").read_bytes() == (D24F / m / "restored.nbt").read_bytes()


@pytest.mark.parametrize("m", TOWERS)
def test_towers_are_the_approved_option_a_candidates(m):
    assert (K / "final-candidates" / m / "restored.nbt").read_bytes() == (D24J / "proposals" / m / "A/candidate.nbt").read_bytes()
    assert (K / "final-candidates" / m / "restored.nbt").read_bytes() != (D24F / m / "restored.nbt").read_bytes()


def test_sums_and_sources_are_consistent():
    sums = dict(reversed(l.split("  ", 1)) for l in (K / "final-candidates/SHA256SUMS").read_text().splitlines())
    src = j(K / "SOURCES.json")
    for m in MODULES:
        assert sums[f"{m}/restored.nbt\n".strip()] == src[m]["sha256"] == B.sha(K / "final-candidates" / m / "restored.nbt")
        assert src[m]["byte_identical_to_stage24f"] == (m in OTHERS)


def test_assemble_is_reproducible(tmp_path):
    B.assemble(tmp_path / "final-candidates")
    for m in MODULES:
        assert (tmp_path / "final-candidates" / m / "restored.nbt").read_bytes() == (K / "final-candidates" / m / "restored.nbt").read_bytes()


@pytest.mark.parametrize("m", MODULES)
def test_production_pack_templates_equal_final_candidates(m):
    assert (K / "derived-24i/datapack" / STRUCT.format(m=m)).read_bytes() == (K / "final-candidates" / m / "restored.nbt").read_bytes()


def test_pack_differs_from_stage24i_only_in_the_two_towers():
    assert set(DIFF["_pack_files_vs_stage24i"]) == {STRUCT.format(m=m) for m in TOWERS} | \
        {f"data/moreminecrafts/structure/ancient_city/protection/{m}.nbt" for m in TOWERS}
    assert all(v == "differs" for v in DIFF["_pack_files_vs_stage24i"].values())
    pk_old, pk_new = AR / "stage-24i/datapack", K / "derived-24i/datapack"
    assert (pk_old / "data/minecraft/worldgen/template_pool/ancient_city/structures.json").read_bytes() == \
        (pk_new / "data/minecraft/worldgen/template_pool/ancient_city/structures.json").read_bytes()


@pytest.mark.parametrize("m", OTHERS)
def test_derived_data_of_the_six_modules_is_unchanged(m):
    d = DIFF[m]
    assert d["protected_cells"]["identical"] and d["mask"]["identical"] and d["roof"]["identical"]
    assert j(AR / "stage-24g/protection/protected-cells.json")[m] == j(K / "derived-24g/protection/protected-cells.json")[m]
    assert j(AR / "stage-24h/mask/interior-masks.json")[m] == j(K / "derived-24h/mask/interior-masks.json")[m]
    assert j(AR / "stage-24i/roof/roof-cells.json")[m] == j(K / "derived-24i/roof/roof-cells.json")[m]
    for sub in ("protection", "interior", "roof"):
        for f in (AR / "stage-24i/datapack/data/moreminecrafts/structure/ancient_city" / sub).glob(f"{m}.nbt"):
            assert filecmp.cmp(f, K / "derived-24i/datapack/data/moreminecrafts/structure/ancient_city" / sub / f.name, shallow=False)


def test_roof_protection_of_the_four_houses_is_preserved():
    new = j(K / "derived-24i/roof/roof-cells.json")
    assert {m: len(v["roof_cells"]) for m, v in new.items()} == {
        "large_ruin_1": 0, "medium_ruin_1": 64, "medium_ruin_2": 78, "small_ruin_1": 29, "small_ruin_2": 11,
        "sauna_1": 0, "large_pillar_1": 0, "medium_pillar_1": 0}
    old = j(AR / "stage-24i/roof/roof-cells.json")
    assert {m: v["roof_cells"] for m, v in new.items()} == {m: v["roof_cells"] for m, v in old.items()}   # the cell lists; decay statistics change with the towers


@pytest.mark.parametrize("m", TOWERS)
def test_tower_clearance_mask_cells_unchanged(m):
    assert DIFF[m]["mask"]["added"] == [] and DIFF[m]["mask"]["removed"] == []


@pytest.mark.parametrize("m", TOWERS)
def test_tower_size_jigsaws_block_entities_unchanged(m):
    old, new = load_nbt(D24F / m / "restored.nbt"), load_nbt(K / "final-candidates" / m / "restored.nbt")
    assert [int(s) for s in new["size"]] == [int(s) for s in old["size"]]
    ents = lambda r: {p: (s, str(n)) for p, (s, n) in blocks_of(r).items() if n is not None}  # noqa: E731
    assert ents(new) == ents(old)


@pytest.mark.parametrize("m", TOWERS)
def test_tower_static_checks(m):
    r = CHECKS[m]
    assert r["static_pass"] and r["identical_to_stage24j_option_a"]
    assert r["ladder"]["continuous_and_backed"] and r["deck"]["all_expected_reachable"]
    assert r["fall_protection"]["open_drops"] == [] and r["invalid_states"] == []


@pytest.mark.parametrize("m,deck_y", [("large_pillar_1", 14), ("medium_pillar_1", 9)])
def test_every_deck_edge_wall_is_a_protected_railing(m, deck_y):
    inv = j(K / "derived-24g/protection/protected-cells.json")[m]
    prot = {tuple(e["pos"]): e["roles"] for e in inv["protected"]}
    walls = [p for p, s in ((p, s) for p, (s, _) in blocks_of(load_nbt(K / "final-candidates" / m / "restored.nbt")).items())
             if p[1] == deck_y and s.startswith("minecraft:polished_deepslate_wall")]
    assert walls and all("railing" in prot.get(p, []) for p in walls), [p for p in walls if "railing" not in prot.get(p, [])]


@pytest.mark.parametrize("m", TOWERS)
def test_ladder_protection_is_preserved(m):
    roles = lambda inv: {tuple(e["pos"]) for e in inv[m]["protected"] if set(e["roles"]) & {"ladder", "ladder_attach"}}  # noqa: E731
    assert roles(j(AR / "stage-24g/protection/protected-cells.json")) <= roles(j(K / "derived-24g/protection/protected-cells.json"))
    assert DIFF[m]["protected_cells"]["role_changed"] == []
