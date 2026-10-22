"""Stage 24-L Phase 0 (design-only): graph rules of the connectivity model, committed evidence, and the read-only / design-only guards."""
import json
from pathlib import Path

import numpy as np

from tools.stage24l import phase0 as P

ROOT = Path(__file__).resolve().parents[1]
S24L = ROOT / "artifacts/ancient-city-restoration/stage-24l"
EV = S24L / "phase0"


def grid(rows):
    """rows: list of columns; each column is a string bottom->top, '#' solid, '.' free. Returns (F, FL) for a 1-D corridor along x."""
    nx, ny = len(rows), max(len(r) for r in rows)
    F = np.zeros((nx, ny, 1), bool)
    for x, col in enumerate(rows):
        for y in range(ny):
            F[x, y, 0] = y >= len(col) or col[y] == "."
    return F, ~F


def comps(rows):
    F, FL = grid(rows)
    W = P.walkable(F, FL)
    idm, u, v = P.two_way_edges(W, F)
    c = P.components(int(W.sum()), u, v)
    return W, idm, c, F


def test_flat_corridor_is_one_component():
    W, idm, c, _ = comps(["###......"] * 6)
    assert int(W.sum()) == 6 and len(set(c.tolist())) == 1


def test_one_block_step_connects_both_ways_but_two_blocks_do_not():
    W, idm, c, _ = comps(["###......", "###......", "####.....", "####.....", "####....."])
    assert len(set(c.tolist())) == 1                     # +1 step
    W, idm, c, _ = comps(["###......", "###......", "#####....", "#####....", "#####...."])
    assert len(set(c.tolist())) == 2                     # +2 step is not walkable


def test_step_needs_headroom_above_the_lower_cell():
    W, idm, c, _ = comps(["###......", "###......", "####.....", "####....."])
    assert len(set(c.tolist())) == 1
    W, idm, c, _ = comps(["###......", "###..#####", "####.....", "####....."])   # ceiling above the lower cell's head
    assert len(set(c.tolist())) == 2


def drops(rows):
    F, FL = grid(rows)
    W = P.walkable(F, FL)
    idm, u, v = P.two_way_edges(W, F)
    comp = P.components(int(W.sum()), u, v)
    du, dv = P.drop_edges(W, F, idm)
    return comp, du, dv


def test_drops_are_one_way_and_limited_to_three_blocks():
    comp, du, dv = drops(["######....", "######....", "###.......", "###......."])    # 3 blocks down, x=1 -> x=2
    assert len(set(comp.tolist())) == 2 and len(du) == 1 and comp[du[0]] != comp[dv[0]]
    assert (du[0], dv[0]) == (1, 2)                                                    # high -> low only, never back up
    comp, du, dv = drops(["#######...", "#######...", "###......."])                    # 4 blocks: not a safe drop
    assert len(du) == 0


def test_survey_reproduction_is_complete():
    s = json.loads((EV / "survey-reproduction.json").read_text())["summary"]
    assert s["observations"] == s["baseline_observations"] == s["identical"] == 116 and not s["differences"]


def test_committed_phase0_results_are_consistent():
    o = json.loads((EV / "results-summary.json").read_text())
    assert o["doors"] == 116 and sum(o["status"].values()) == 116
    assert o["status"]["open_to_main"] == 113
    assert {(r["seed"], r["piece_index"]) for r in o["not_open"]} == {(24005, 71), (24009, 59), (24015, 55)}
    assert set(o["seeds"]) == set(range(24001, 24025))
    assert o["non_main_components"]["with_house_doors"] == 0
    f = o["focus"]
    assert f["24005"]["obstruction_summary"]["n"] == 14 and f["24009"]["obstruction_summary"]["n"] == 6
    assert f["24005"]["obstruction_summary"]["architecture"] == f["24009"]["obstruction_summary"]["architecture"] == 0
    assert f["24015"]["minimum_change"]["place_only"]["cost"] == 1 and f["24015"]["minimum_change"]["clear_only"] is None


def test_phase0_is_read_only_and_design_only():
    src = (ROOT / "tools/stage24l/phase0.py").read_text()
    assert "import Server" not in src and "Server(" not in src                   # never starts a server
    assert "rmtree" not in src and "unlink" not in src
    bad = [p.name for p in S24L.rglob("*") if p.suffix in {".nbt", ".mcmeta", ".mca"} or p.name == "pack.mcmeta"]
    assert not bad, bad                                                           # no template, datapack or world data in the design-only stage
