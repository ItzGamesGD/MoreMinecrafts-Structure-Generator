from pathlib import Path

import pytest

from tools.stage24b_source import MODULES, load_original
from tools.stage24b_candidate import Candidate, block_id
from tools.stage24b_layouts import RESTORERS
from tools.validate_stage24b import test_candidate as validate_candidate

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope="module")
def candidates():
    result = {}
    for name in MODULES:
        root, url, sha = load_original(name)
        c = Candidate(name, root, url, sha)
        RESTORERS[name](c)
        c.verify_protected()
        result[name] = c
    return result

def test_all_eight_have_complete_built_candidates(candidates):
    assert set(candidates) == set(RESTORERS)
    for name, c in candidates.items():
        assert c.added_positions or c.changed_original, name

def test_approved_dimensions_and_connector_metadata(candidates):
    for name, c in candidates.items():
        expected = (16, 8, 11) if name == "medium_ruin_2" else tuple(MODULES[name]["size"])
        assert c.size == expected
        assert c.connector_snapshot == c.current_connector_snapshot()

def test_house_interiors_have_usable_entrance_and_sleeping_space(candidates):
    for name in ("large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2"):
        c = candidates[name]
        assert c.get_block(c.entry_inside) in ("minecraft:air", "minecraft:spruce_door[open=true]")
        assert c.features["beds"], name
        assert c.features["doors"], name

def test_sauna_protects_water_rims_chests_and_stairs(candidates):
    c = candidates["sauna_1"]
    assert c.protected_snapshot == c.snapshot_protected_from_source()
    assert c.features["changing"] and c.features["bathing_access"] and c.features["resting"]

def test_large_tower_is_ladder_connected_and_has_observation_platform(candidates):
    c = candidates["large_pillar_1"]
    assert c.features["ladder_run"] == list(range(1, 14))
    assert c.features["observation_platform"]
    assert c.features["entrance"]

def test_medium_tower_has_lower_room_upper_deck_and_preserved_skull(candidates):
    c = candidates["medium_pillar_1"]
    assert c.features["ladder_run"]
    assert c.features["observation_platform"]
    assert c.features["guard_space"]

@pytest.mark.parametrize("module", list(MODULES))
def test_actual_candidate_block_states_pass_static_validation(candidates, module):
    report = validate_candidate(candidates[module])
    assert report["checks"]["candidate_bounds"] == "PASS"
    assert report["checks"]["blockstate_palette_resolution"] == "PASS"

def test_change_manifests_explain_edits_and_never_include_protected_connectors(candidates):
    for name, c in candidates.items():
        changes = c.block_change_manifest()
        assert changes, name
        assert all(change["reasons"] for change in changes), name
        changed_positions = {tuple(change["pos_xyz"]) for change in changes}
        connector_positions = {pos for pos in c.protected if block_id(c.get_block(pos)) == "minecraft:jigsaw"}
        assert not changed_positions.intersection(connector_positions)
    sauna = candidates["sauna_1"]
    original_water = {pos for pos in sauna.original_positions if sauna._block_key_at(pos) == "minecraft:water[level=0]"
                      or sauna._block_key_at(pos).startswith("minecraft:water[")}
    assert not original_water.intersection(tuple(change["pos_xyz"]) for change in sauna.block_change_manifest())
