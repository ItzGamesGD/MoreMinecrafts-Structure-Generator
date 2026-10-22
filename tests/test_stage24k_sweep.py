"""Stage 24-K: guards over the committed 24-seed sweep and live-test evidence (no server needed)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AR = ROOT / "artifacts/ancient-city-restoration"
K = AR / "stage-24k"
TOWERS = ("large_pillar_1", "medium_pillar_1")


def j(p):
    return json.loads(Path(p).read_text())


CMP = j(K / "worldgen/ik-comparison.json")


def test_city_layouts_identical_to_stage24i_on_all_24_seeds():
    assert len(CMP) == 24 and all(s["layout_identical_i24_k24"] for s in CMP)
    assert sum(s["pieces_k24"] for s in CMP) == sum(s["pieces_i24"] for s in CMP) == 2160


def test_bounding_boxes_jigsaws_and_overlaps_unchanged():
    ai, ak = j(AR / "stage-24i/worldgen/i24-analysis.json"), j(K / "worldgen/k24-analysis.json")
    assert all(x["placements_identical_to_vanilla"] for x in ak)
    assert [x["bounding_box_differences"] for x in ai] == [x["bounding_box_differences"] for x in ak]
    jig = lambda a: [(x["seed"], m["module"], tuple(m["pos"]), json.dumps(m["jigsaws"], sort_keys=True)) for x in a for m in x["modules"]]  # noqa: E731
    assert jig(ai) == jig(ak)
    assert sum(len(m["overlapping_pieces"]) for x in ak for m in x["modules"]) == 0
    assert all(m["model_matches_piece_bb"] for x in ak for m in x["modules"])


def test_every_protected_cell_instance_survives():
    r = j(K / "worldgen/k24-functional-survival.json")
    assert len(r) == 9974 and {x["status"] for x in r} <= {"present", "present_weathered"}


def test_no_unexplained_architecture_difference_and_designed_cells_as_predicted():
    tot = Counter()
    for s in CMP:
        for p in s["pieces"]:
            tot.update(p["counts"])
            assert not p["unexplained"] and not p["design_unexplained"], (s["seed"], p["piece_index"])
    assert tot["diff_architecture_UNEXPLAINED"] == 0 and tot["DESIGN_CELL_UNEXPLAINED"] == 0
    assert tot["design_cell_as_predicted"] > 4000


def test_generated_towers_have_ladder_railing_and_a_reachable_clear_deck():
    n = 0
    for s in CMP:
        for p in s["pieces"]:
            t = p.get("tower")
            if not t:
                continue
            n += 1
            assert t["ladder_cells_missing"] == [] and t["railing_cells_missing"] == []
            assert t["ladder_exit_cells_clear"] >= 1
            assert t["deck_cells_reachable_from_ladder"] == t["deck_cells_clear"]
            assert set(t["deck_blockers"]) <= {"sculk_sensor", "sculk_catalyst", "sculk_shrieker"}   # vanilla sculk only
    assert n == 67


def test_decay_regression_six_modules_identical_towers_differ_only_at_designed_cells():
    r = j(K / "worldgen/decay-regression.json")
    for k, v in r.items():
        m, cause = k.split("/")
        if m not in TOWERS:
            assert v["cells_that_differ"] == 0, k
        elif cause == "block_rot":
            assert v["at_unchanged_cells"] == [], k
    assert sum(v["stage24i"] for k, v in r.items() if k.endswith("/block_rot")) == 3067
    assert sum(v["stage24k"] for k, v in r.items() if k.endswith("/block_rot")) == 2972


def test_entrance_deferrals_unchanged():
    ei, ek = j(AR / "stage-24i/worldgen/i24-entrance-survey.json"), j(K / "worldgen/k24-entrance-survey.json")
    key = lambda r: (r["seed"], r["piece_index"], r["module"], r["rotation"], r["status"], r["n_cells"], json.dumps(r["cells_to_clear"]))  # noqa: E731
    assert [key(r) for r in ei] == [key(r) for r in ek]
    assert sorted((r["seed"], r["module"]) for r in ek if r["n_cells"] or r["status"] != "ok") == [(24005, "medium_ruin_1"), (24009, "large_ruin_1"), (24015, "large_ruin_1")]


def test_known_open_item_sauna_pool_cells_are_documented():
    b = j(K / "worldgen/sauna-bisect.json")
    assert b["24006:i24"] == b["24007:i24"] == [] and b["24006:kLonly"] == b["24007:kLonly"] == []
    assert b["24006:kMonly"] == b["24006:k24"] == [[18, 0, 26]] and b["24007:kMonly"] == b["24007:k24"] == [[19, 0, 27]]
    lost = sum(p.get("pool_water_lost", 0) for s in CMP for p in s["pieces"])
    assert lost == 2


def test_live_pool_placements_8_modules_4_rotations_clean():
    rep = j(K / "live/live-pool-report.json")
    rots = {}
    for p in rep["placements"]:
        if p["kind"] == "i24":
            assert not p["analysis"]["violations"] and not p["roof"]["counts"].get("MISSING"), (p["module"], p["rotation"])
            rots.setdefault(p["module"], set()).add(p["rotation"])
    assert set(rots) == {"large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2", "sauna_1", "large_pillar_1", "medium_pillar_1"}
    assert all(len(v) == 4 for v in rots.values())


def test_live_tower_placement_and_scripted_player():
    rep = j(K / "live/towers/live-report.json")
    assert len(rep["placements"]) == 8 and {p["rotation"] for p in rep["placements"]} == {"NONE", "CLOCKWISE_90", "CLOCKWISE_180", "COUNTERCLOCKWISE_90"}
    for p in rep["placements"]:
        assert p["mismatches"] == 0 and p["bot"]["failed"] == [], p
    assert {p["module"]: p["bot"]["total"] for p in rep["placements"]} == {"large_pillar_1": 52, "medium_pillar_1": 78}


def test_buried_gameplay_32_of_32():
    s = j(K / "live/gameplay-buried/summary-buried-all.json")
    assert len(s) == 32 and all(not v["failed"] for v in s.values())
