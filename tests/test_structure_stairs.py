"""STAIR-01: explicit author states are a contract, not a shape solver."""

import gzip
import io
import itertools
import sys
from pathlib import Path

import nbtlib
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_structure_export import convert_file
from tools.structure_export import convert as C
from tools.structure_export.errors import BlockStateError
from tools.structure_export.live import ROTATIONS, rotate_props, transform
from tools.structure_export.verify import VerificationError, _complete, verify

FACING = ("north", "east", "south", "west")
SHAPES = ("straight", "inner_left", "inner_right", "outer_left", "outer_right")
REF = C.load_reference("26.3")


@pytest.mark.parametrize("facing,half,shape", list(itertools.product(FACING, ("top", "bottom"), SHAPES)))
def test_explicit_states_roundtrip_and_rotate(tmp_path, facing, half, shape):
    state = f"minecraft:oak_stairs[facing={facing},half={half},shape={shape}]"
    result = convert_file(tmp_path, [state], [0], size=(1, 1, 1))
    root = nbtlib.File.parse(io.BytesIO(gzip.decompress(result.nbt)))
    props = {k: str(v) for k, v in root["palette"][0]["properties"].items()}
    assert props == dict(REF["blocks"]["minecraft:oak_stairs"]["default"], facing=facing, half=half, shape=shape)
    verify(result.config.nbt_path, result.config.source, REF, "include")
    for q, rotation in enumerate(ROTATIONS):
        rotated = rotate_props(props, rotation)
        assert rotated["facing"] == FACING[(FACING.index(facing) + q) % 4]
        assert rotated["half"] == half and rotated["shape"] == shape
        assert transform((2, 3, 5), rotation)[1] == 3
    assert len(result.report["stair_boundary_review"]) == 4


@pytest.mark.parametrize("key", ("facing", "half", "shape"))
def test_missing_required_state_rejected_by_writer_and_independent_verifier(key):
    props = dict(facing="north", half="bottom", shape="straight")
    del props[key]
    with pytest.raises(BlockStateError, match="require explicit"):
        C.resolve_state("minecraft:oak_stairs", props, REF)
    text = "minecraft:oak_stairs[" + ",".join(f"{k}={v}" for k, v in props.items()) + "]"
    with pytest.raises(VerificationError, match="require explicit"):
        _complete(text, REF)


@pytest.mark.parametrize("key,value", [("facing", "up"), ("half", "middle"), ("shape", "corner")])
def test_invalid_state_rejected(key, value):
    props = dict(facing="north", half="bottom", shape="straight")
    props[key] = value
    with pytest.raises(BlockStateError, match="not valid"):
        C.resolve_state("minecraft:oak_stairs", props, REF)


def test_internal_corner_and_inverted_spiral_are_preserved(tmp_path):
    # Explicit authored shapes may intentionally differ from neighbour-derived shapes.
    palette = [f"minecraft:oak_stairs[facing={d},half=top,shape={s}]" for d, s in zip(FACING, SHAPES[1:], strict=True)]
    result = convert_file(tmp_path, palette, [0, 1, 2, 3], size=(2, 1, 2))
    verify(result.config.nbt_path, result.config.source, REF, "include", C.load_connectivity("26.3"))
    assert result.report["blocks"] == 4


def test_verifier_rejects_shape_tampering_even_with_connectivity(tmp_path):
    result = convert_file(
        tmp_path, ["minecraft:oak_stairs[facing=north,half=bottom,shape=inner_left]"], [0], size=(1, 1, 1)
    )
    root = nbtlib.File.parse(io.BytesIO(gzip.decompress(result.nbt)))
    root["palette"][0]["properties"]["shape"] = nbtlib.String("outer_right")
    root.gzipped = True
    root.save(result.config.nbt_path)
    with pytest.raises(VerificationError):
        verify(result.config.nbt_path, result.config.source, REF, "include", C.load_connectivity("26.3"))


def test_omitted_air_is_reported_and_internal_stair_needs_no_review(tmp_path):
    stair = "minecraft:oak_stairs[facing=north,half=bottom,shape=straight]"
    palette = ["minecraft:air", stair, "minecraft:stone"]
    cells = [2] * 9
    cells[4] = 1
    result = convert_file(tmp_path, palette, cells, size=(3, 1, 3))
    assert "stair_boundary_review" not in result.report
    cells[1] = 0
    result = convert_file(tmp_path, palette, cells, size=(3, 1, 3), air="omit")
    assert result.report["stair_boundary_review"] == [{"pos": [1, 0, 1], "side": "north", "reason": "omitted_air"}]


def test_spiral_rising_run_preserves_each_authored_step(tmp_path):
    points = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1)]
    palette = ["minecraft:air"] + [
        f"minecraft:oak_stairs[facing={FACING[(i + 1) % 4]},half=bottom,shape=straight]" for i in range(4)
    ]
    cells = [0] * (3 * 8 * 3)
    for y, (x, z) in enumerate(points):
        cells[x + z * 3 + y * 9] = y % 4 + 1
    result = convert_file(tmp_path, palette, cells, size=(3, 8, 3))
    verify(result.config.nbt_path, result.config.source, REF, "include")


def test_live_fixtures_are_inside_their_box_and_cover_every_shape_family():
    from tools.structure_export import stair_live as S

    for name, cells in {
        "pairs": S.fx_pairs(),
        "corners": S.fx_corners(),
        "spiral": S.fx_spiral(),
        "corbel": S.fx_corbel(),
        "roof": S.fx_roof(),
        "seam": S.fx_seam_whole(),
    }.items():
        assert cells and all(min(p) >= 0 for p in cells), name
        for _, facing, half in cells.values():
            assert facing in FACING and half in ("top", "bottom")
    matrix = S.fx_matrix_slots()
    assert len(matrix) == 40 and {(f, h, s) for _, f, h, s in matrix.values()} == set(
        itertools.product(FACING, ("bottom", "top"), SHAPES)
    )
