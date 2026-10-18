import copy

import nbtlib
import pytest
from nbtlib import tag

from tools.stage24b_candidate import Candidate, ProtectedBlockError


def source_fixture():
    palette = tag.List[tag.Compound]([
        tag.Compound({"Name": tag.String("minecraft:cobbled_deepslate")}),
        tag.Compound({"Name": tag.String("minecraft:jigsaw"), "Properties": tag.Compound({"orientation": tag.String("west_up")})}),
    ])
    return nbtlib.File({
        "DataVersion": tag.Int(4790),
        "size": tag.List[tag.Int]([5, 5, 5]),
        "palette": palette,
        "blocks": tag.List[tag.Compound]([
            tag.Compound({"pos": tag.List[tag.Int]([0, 0, 2]), "state": tag.Int(1), "nbt": tag.Compound({"id": tag.String("minecraft:jigsaw"), "target": tag.String("minecraft:empty")})}),
            tag.Compound({"pos": tag.List[tag.Int]([2, 0, 2]), "state": tag.Int(0)}),
        ]),
        "entities": tag.List[tag.Compound]([]),
    }, gzipped=True)


def test_candidate_appends_palette_and_records_added_and_replaced_actual_blocks():
    candidate = Candidate("large_ruin_1", copy.deepcopy(source_fixture()))
    candidate.set_block(2, 1, 2, "minecraft:deepslate_bricks", reason="wall")
    candidate.set_block(2, 0, 2, "minecraft:air", replace=True, reason="doorway")
    assert candidate.get_block((2, 1, 2)) == "minecraft:deepslate_bricks"
    assert candidate.get_block((2, 0, 2)) == "minecraft:air"
    assert len(candidate.palette) == 4
    assert candidate.operations["added"] == 1
    assert candidate.operations["replaced"] == 1


def test_candidate_rejects_jigsaw_overwrite_and_out_of_bounds_blocks():
    candidate = Candidate("large_ruin_1", copy.deepcopy(source_fixture()))
    with pytest.raises(ProtectedBlockError, match="protected source block"):
        candidate.set_block(0, 0, 2, "minecraft:air", replace=True, reason="bad")
    with pytest.raises(ValueError, match="outside candidate dimensions"):
        candidate.set_block(5, 0, 0, "minecraft:deepslate_bricks", reason="bad")


def test_candidate_saves_and_reloads_jigsaw_state_and_full_nbt(tmp_path):
    candidate = Candidate("large_ruin_1", copy.deepcopy(source_fixture()))
    candidate.set_block(1, 1, 1, "minecraft:soul_lantern", reason="light")
    candidate.verify_protected()
    path = tmp_path / "candidate.nbt"
    candidate.save_native(path)
    loaded = Candidate.load(path)
    loaded.verify_protected()
    assert loaded.get_block((1, 1, 1)) == "minecraft:soul_lantern"
    assert loaded.get_block((0, 0, 2)) == "minecraft:jigsaw[orientation=west_up]"
