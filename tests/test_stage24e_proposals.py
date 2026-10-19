"""Stage 24-E: roof/massing proposals keep the Stage 24-C functional baseline and never touch the approved candidates."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.stage24c.common import S24B  # noqa: E402
from tools.stage24e.check import Grid, check  # noqa: E402
from tools.stage24e.designs import DESIGNS  # noqa: E402

STAGE24C_HEAD = "b92a4be1e9e1b901a08f1629c4f19b63dab43dce"
CASES = [(m, f) for m, fs in DESIGNS.items() for f in fs]


@pytest.mark.parametrize("module,design", CASES, ids=[f"{m}-{f.__name__}" for m, f in CASES])
def test_proposal_keeps_functional_baseline(tmp_path, module, design):
    v = design()
    path = v.save(tmp_path / f"{module}-{v.variant}.nbt")
    r = check(module, path, Grid(S24B / module / "restored.nbt"))
    assert r["static_pass"], r["failed_checks"]
    assert r["footprint_unchanged"]
    assert r["walkable_cells"] >= r["baseline_walkable_cells"]
    # a taller NBT is always flagged as needing authorisation; nothing ever shrinks
    assert r["height_change"] >= 0
    assert v.expanded == (r["height_change"] > 0)


def test_large_ruin_1_has_a_genuinely_taller_option():
    heights = [f().size[1] for f in DESIGNS["large_ruin_1"]]
    assert max(heights) >= 10


@pytest.mark.parametrize("module", list(DESIGNS))
def test_stage24c_candidates_are_untouched(module):
    rel = f"artifacts/ancient-city-restoration/stage-24b/{module}/restored.nbt"
    head = subprocess.run(["git", "show", f"{STAGE24C_HEAD}:{rel}"], cwd=ROOT, capture_output=True, check=True).stdout
    assert hashlib.sha256(head).hexdigest() == hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def test_every_house_has_at_least_two_distinct_alternatives():
    for module, fs in DESIGNS.items():
        variants = [f() for f in fs]
        assert len(variants) >= 2
        roofs = {frozenset((p, s) for p, s in v.blocks.items() if p[1] >= 3) for v in variants}
        assert len(roofs) == len(variants), module
