import json
from pathlib import Path

import pytest

from tools.stage24b_source import BASELINE_SHA, MODULES, build_baseline_manifest, verify_source_bytes


def test_module_inventory_matches_approved_stage24b_mapping():
    assert tuple(MODULES) == (
        "large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1",
        "small_ruin_2", "sauna_1", "large_pillar_1", "medium_pillar_1",
    )
    assert BASELINE_SHA == "049c791ad8e7255d15c30f66774f427a343522e5"


def test_source_hash_rejects_unexpected_original_bytes():
    with pytest.raises(ValueError, match="source blob SHA mismatch"):
        verify_source_bytes("large_ruin_1", b"not the pinned NBT")


def test_baseline_manifest_revalidates_design_reports_and_all_source_invariants(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    manifest = build_baseline_manifest(repo, output=tmp_path / "baseline.json")
    saved = json.loads((tmp_path / "baseline.json").read_text())
    assert saved == manifest
    assert manifest["baseline_commit"] == BASELINE_SHA
    assert set(manifest["modules"]) == set(MODULES)
    assert all(item["source_verified"] for item in manifest["modules"].values())
    assert manifest["modules"]["medium_ruin_2"]["original_dimensions_xyz"] == [16, 5, 11]
    assert manifest["modules"]["sauna_1"]["protected_counts"]["minecraft:water"] == 43
    assert len(manifest["modules"]["sauna_1"]["jigsaws"]) == 5
    assert len(manifest["modules"]["medium_pillar_1"]["jigsaws"]) == 2
    assert manifest["modules"]["medium_pillar_1"]["block_entities"]
