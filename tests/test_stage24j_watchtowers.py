"""Stage 24-J watchtower alternatives: proposals only, approved files untouched, invariants of every candidate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.stage24c.common import MODULES, load_nbt, blocks_of  # noqa: E402
from tools.stage24j import designs as D  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"
D24J = ROOT / "artifacts/ancient-city-restoration/stage-24j"
CHECKS = json.loads((D24J / "static-checks.json").read_text())
PROPOSALS = [(m, f) for m, fs in D.DESIGNS.items() for f in fs if f.__name__ not in ("large_current", "medium_current")]


def test_approved_nbts_and_stage24i_pack_unchanged():
    for m in MODULES:
        assert (D24I / f"datapack/data/minecraft/structure/ancient_city/structures/{m}.nbt").read_bytes() == (D24F / m / "restored.nbt").read_bytes()
    assert not list((D24I / "datapack").rglob("*stage24j*")) and not list((D24I / "datapack").rglob("*s24j*"))


def test_proposals_rebuild_byte_identical(tmp_path):
    D.build(tmp_path)
    for m, f in PROPOSALS:
        v = f()
        assert (tmp_path / m / v.variant / "candidate.nbt").read_bytes() == (D24J / "proposals" / m / v.variant / "candidate.nbt").read_bytes()


@pytest.mark.parametrize("m,f", PROPOSALS, ids=[f"{m}-{f.__name__}" for m, f in PROPOSALS])
def test_candidate_keeps_size_jigsaws_and_block_entities(m, f):
    v = f()
    approved, cand = load_nbt(D24F / m / "restored.nbt"), load_nbt(D24J / "proposals" / m / v.variant / "candidate.nbt")
    assert [int(s) for s in cand["size"]] == [int(s) for s in approved["size"]]
    ents = lambda r: {p: (s, str(n)) for p, (s, n) in blocks_of(r).items() if n is not None}  # noqa: E731
    assert ents(cand) == ents(approved)
    assert int(cand["DataVersion"]) == int(approved["DataVersion"])


@pytest.mark.parametrize("m,f", PROPOSALS, ids=[f"{m}-{f.__name__}" for m, f in PROPOSALS])
def test_static_checks_pass(m, f):
    r = CHECKS[m][f().variant]
    assert r["static_pass"], r
    assert not r["fall_protection"]["open_drops"]
    assert r["ladder"]["continuous_and_backed"] and r["deck"]["all_expected_reachable"]
    assert r["invalid_states"] == []


def test_medium_pillar_skull_is_kept():
    for v in ("A", "B"):
        b = blocks_of(load_nbt(D24J / "proposals/medium_pillar_1" / v / "candidate.nbt"))
        assert b[(4, 1, 4)][0].startswith("minecraft:skeleton_skull")


def test_current_large_tower_finding_is_recorded():
    """the approved large tower's deck has no fall protection; both options close every open edge"""
    assert CHECKS["large_pillar_1"]["current"]["fall_protection"]["sides"].get("OPEN_DROP", 0) == 30
