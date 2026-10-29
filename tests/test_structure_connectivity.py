"""Neighbour-dependent states (walls, fences, panes/bars, fence gates) computed by the converter.

Expected values follow the 26.3 rules transcribed in tools/structure_export/connectivity.py; the
committed testbed exports are additionally checked against the game itself by `live`.
"""

from __future__ import annotations

import gzip
import io
import sys
from pathlib import Path

import nbtlib
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_structure_export import convert_file  # noqa: E402

from tools.structure_export import convert as C  # noqa: E402
from tools.structure_export.live import rotate_props  # noqa: E402
from tools.structure_export.verify import VerificationError, verify  # noqa: E402

WALL = "minecraft:stone_brick_wall"
AIR = "minecraft:air"


def build(tmp_path, blocks: dict, size, air="include"):
    """Convert a layout {(x, y, z): state} (everything else air); return the result and its cells."""
    palette = [AIR] + sorted(set(blocks.values()) - {AIR})
    index = {state: i for i, state in enumerate(palette)}
    w, h, length = size
    cells = [0] * (w * h * length)
    for (x, y, z), state in blocks.items():
        cells[x + z * w + y * w * length] = index[state]
    tmp_path.mkdir(parents=True, exist_ok=True)
    result = convert_file(tmp_path, palette, cells, size=size, air=air)
    nbt = nbtlib.File.parse(io.BytesIO(gzip.decompress(result.nbt)))
    pal = [(str(e["id"]), {k: str(v) for k, v in e.get("properties", {}).items()}) for e in nbt["palette"]]
    out = {tuple(int(v) for v in b["pos"]): pal[int(b["state"])] for b in nbt["blocks"]}
    return result, out


def sides(cell, keys=("north", "east", "south", "west", "up")):
    return {k: cell[1][k] for k in keys if k in cell[1]}


def line(x0, x1, z=1, y=0, state=WALL):
    return {(x, y, z): state for x in range(x0, x1 + 1)}


def test_connectivity_reference_is_pinned_to_the_same_server_jar():
    connectivity, blocks = C.load_connectivity("26.3"), C.load_reference("26.3")
    assert connectivity["server_jar_sha1"] == blocks["server_jar_sha1"] == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c"
    assert connectivity["data_version"] == blocks["data_version"] == 5023
    assert set(connectivity["blocks"]) == set(blocks["blocks"])
    kinds = {k: sorted(b for b, e in connectivity["blocks"].items() if k in e["kinds"]) for k in ("wall", "bars")}
    assert set(kinds["wall"]) == set(connectivity["tags"]["walls"])
    assert {"minecraft:glass_pane", "minecraft:white_stained_glass_pane", "minecraft:iron_bars"} <= set(kinds["bars"])
    assert connectivity["blocks"]["minecraft:stone"]["facts"] == "1111/11111"


# --- walls: shapes of a run ---------------------------------------------------------------------


def test_straight_run(tmp_path):
    _, out = build(tmp_path, line(1, 3), (5, 1, 3))
    assert sides(out[1, 0, 1]) == {"north": "none", "east": "low", "south": "none", "west": "none", "up": "true"}
    assert sides(out[2, 0, 1]) == {"north": "none", "east": "low", "south": "none", "west": "low", "up": "false"}
    assert sides(out[3, 0, 1]) == {"north": "none", "east": "none", "south": "none", "west": "low", "up": "true"}


def test_corner(tmp_path):
    _, out = build(tmp_path, {**line(1, 2), (2, 0, 2): WALL}, (4, 1, 4))
    assert sides(out[2, 0, 1]) == {"north": "none", "east": "none", "south": "low", "west": "low", "up": "true"}


def test_t_junction_and_cross(tmp_path):
    blocks = {**line(0, 4, z=2), **{(2, 0, z): WALL for z in range(0, 5)}}
    _, out = build(tmp_path, blocks, (5, 1, 5))
    assert sides(out[2, 0, 2]) == {"north": "low", "east": "low", "south": "low", "west": "low", "up": "false"}
    t_blocks = {**line(0, 4, z=0), (2, 0, 1): WALL}
    _, out = build(tmp_path, t_blocks, (5, 1, 2))
    assert sides(out[2, 0, 0]) == {"north": "none", "east": "low", "south": "low", "west": "low", "up": "true"}


@pytest.mark.parametrize(
    "above, side, up",
    [
        (AIR, "low", "false"),
        ("minecraft:stone_bricks", "tall", "false"),
        ("minecraft:oak_slab[type=bottom]", "tall", "false"),
        ("minecraft:oak_slab[type=top]", "low", "false"),  # its collision box leaves the wall top open
        ("minecraft:torch", "low", "true"),  # #wall_post_override
        (WALL, "low", "true"),  # a lone wall above has a post
    ],
)
def test_block_above_decides_tall_and_post(tmp_path, above, side, up):
    blocks = {**line(0, 2), (1, 1, 1): above}
    _, out = build(tmp_path, blocks, (3, 2, 3))
    assert sides(out[1, 0, 1]) == {"north": "none", "east": side, "south": "none", "west": side, "up": up}


def test_two_high_run_lower_walls_are_tall(tmp_path):
    blocks = {**line(0, 2), **line(0, 2, y=1)}
    _, out = build(tmp_path, blocks, (3, 2, 3))
    assert sides(out[1, 0, 1]) == {"north": "none", "east": "tall", "south": "none", "west": "tall", "up": "false"}
    assert sides(out[0, 0, 1])["east"] == "tall" and out[0, 0, 1][1]["up"] == "true"  # end: corner -> post
    assert sides(out[1, 1, 1]) == {"north": "none", "east": "low", "south": "none", "west": "low", "up": "false"}


# --- what connects to what ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "neighbour, connects",
    [
        ("minecraft:stone", "low"),  # sturdy face
        ("minecraft:cobblestone_wall", "low"),  # #walls
        ("minecraft:iron_bars", "low"),  # IronBarsBlock
        ("minecraft:glass_pane", "low"),  # panes are IronBarsBlock too
        ("minecraft:oak_leaves[persistent=true]", "none"),  # isExceptionForConnection
        ("minecraft:pumpkin", "none"),  # sturdy but an exception
        ("minecraft:oak_fence", "none"),  # not a wall, not sturdy
        ("minecraft:oak_stairs[facing=west,half=bottom,shape=straight]", "low"),  # back of the stairs faces the wall
        ("minecraft:oak_stairs[facing=east,half=bottom,shape=straight]", "none"),
        ("minecraft:oak_fence_gate[facing=north]", "low"),  # gate spanning x connects along x
        ("minecraft:oak_fence_gate[facing=east]", "none"),
    ],
)
def test_wall_connects_by_vanilla_rules(tmp_path, neighbour, connects):
    _, out = build(tmp_path, {(0, 0, 0): WALL, (1, 0, 0): neighbour}, (2, 1, 1))
    assert out[0, 0, 0][1]["east"] == connects


@pytest.mark.parametrize(
    "neighbour, connects",
    [
        ("minecraft:oak_fence", "true"),
        ("minecraft:spruce_fence", "true"),  # both #wooden_fences
        ("minecraft:nether_brick_fence", "false"),  # #fences but not wooden
        ("minecraft:stone", "true"),
        ("minecraft:pumpkin", "false"),
        (WALL, "false"),
        ("minecraft:oak_fence_gate[facing=south]", "true"),
    ],
)
def test_fence_connects_by_vanilla_rules(tmp_path, neighbour, connects):
    _, out = build(tmp_path, {(0, 0, 0): "minecraft:oak_fence", (1, 0, 0): neighbour}, (2, 1, 1))
    assert out[0, 0, 0][1]["east"] == connects


def test_panes_and_bars(tmp_path):
    blocks = {
        (0, 0, 0): "minecraft:glass_pane",
        (1, 0, 0): "minecraft:iron_bars",
        (2, 0, 0): "minecraft:white_stained_glass_pane",
        (0, 0, 1): "minecraft:stone",
        (2, 0, 1): "minecraft:oak_fence",
        (1, 0, 1): WALL,
    }
    _, out = build(tmp_path, blocks, (3, 1, 2))
    assert sides(out[0, 0, 0], ("north", "east", "south", "west")) == {
        "north": "false",
        "east": "true",
        "south": "true",
        "west": "false",
    }
    assert out[1, 0, 0][1]["south"] == "true"  # bars attach to #walls
    assert out[2, 0, 0][1]["south"] == "false"  # not to fences
    assert out[1, 0, 1][1]["north"] == "low"  # and the wall connects back


def test_fence_gate_in_wall(tmp_path):
    blocks = {
        (0, 0, 0): WALL,
        (1, 0, 0): "minecraft:oak_fence_gate[facing=south]",
        (2, 0, 0): WALL,
        (0, 0, 2): WALL,
        (1, 0, 2): "minecraft:oak_fence_gate[facing=east]",
        (2, 0, 2): WALL,
    }
    result, out = build(tmp_path, blocks, (3, 1, 3))
    assert out[1, 0, 0][1]["in_wall"] == "true"
    assert out[1, 0, 2][1]["in_wall"] == "false"  # the walls are at its hinge ends, not its sides
    assert out[0, 0, 0][1]["east"] == "low" and out[0, 0, 2][1]["east"] == "none"
    assert result.report["connectivity"]["corrected_properties"]["in_wall"] == 1


# --- boundary, air, unresolved, explicit --------------------------------------------------------


def test_template_boundary_is_treated_as_air_and_reported(tmp_path):
    result, out = build(tmp_path, line(0, 1, z=0), (2, 1, 1))
    assert sides(out[1, 0, 0]) == {"north": "none", "east": "none", "south": "none", "west": "low", "up": "true"}
    boundary = {tuple(b["pos"]): b["unknown_neighbours"] for b in result.report["connectivity"]["boundary_unresolved"]}
    assert boundary[1, 0, 0] == {
        "east": "outside_template",
        "north": "outside_template",
        "south": "outside_template",
        "up": "outside_template",
    }
    assert any("border the template box" in w for w in result.report["warnings"])


def test_air_include_and_omit_give_the_same_connections(tmp_path):
    blocks = {**line(1, 3), (2, 0, 2): "minecraft:stone"}
    included, out_in = build(tmp_path / "in", blocks, (5, 2, 3), air="include")
    omitted, out_om = build(tmp_path / "om", blocks, (5, 2, 3), air="omit")
    assert {p: c for p, c in out_in.items() if c[0] != AIR} == out_om
    assert included.report["connectivity"]["boundary_unresolved"] == []
    reasons = {
        why for b in omitted.report["connectivity"]["boundary_unresolved"] for why in b["unknown_neighbours"].values()
    }
    assert reasons == {"omitted_air"}


def test_no_neighbours_keeps_the_default_post(tmp_path):
    result, out = build(tmp_path, {(1, 0, 1): WALL, (1, 0, 3): "minecraft:oak_fence"}, (3, 2, 5))
    assert sides(out[1, 0, 1]) == {"north": "none", "east": "none", "south": "none", "west": "none", "up": "true"}
    assert result.report["connectivity"]["computed_blocks"] == 2
    assert result.report["connectivity"]["corrected_blocks"] == 0


def test_stated_properties_are_kept_and_reported(tmp_path):
    blocks = {**line(0, 2), (1, 0, 1): WALL + "[up=true,north=tall]"}
    result, out = build(tmp_path, blocks, (3, 1, 3))
    assert sides(out[1, 0, 1]) == {"north": "tall", "east": "low", "south": "none", "west": "low", "up": "true"}
    differs = result.report["connectivity"]["explicit_differs_from_vanilla"]
    assert [(d["property"], d["source"], d["vanilla"]) for d in differs] == [
        ("north", "tall", "none"),
        ("up", "true", "false"),
    ]


def test_fully_stated_connections_are_untouched(tmp_path):
    state = WALL + "[east=none,north=none,south=none,up=true,waterlogged=false,west=none]"
    result, out = build(tmp_path, {(0, 0, 0): state, (1, 0, 0): state}, (2, 1, 1))
    assert out[0, 0, 0][1]["east"] == "none"
    assert result.report["connectivity"]["computed_blocks"] == 0
    assert len(result.report["connectivity"]["explicit_differs_from_vanilla"]) == 2


def test_dynamic_neighbour_leaves_only_that_side_at_the_default(tmp_path):
    result, out = build(tmp_path, {(0, 0, 0): "minecraft:oak_fence", (1, 0, 0): "minecraft:scaffolding"}, (2, 2, 1))
    unresolved = result.report["connectivity"]["unresolved"]
    assert len(unresolved) == 1 and "dynamic shape" in unresolved[0]["reason"]
    assert out[0, 0, 0][1]["east"] == "false"  # kept at the default
    assert any("kept default connections" in w for w in result.report["warnings"])


def test_position_dependent_block_above_keeps_wall_connections_and_verifies(tmp_path):
    # Regression (PR #47 audit): wall at (0,0,0) with bamboo above used to stay entirely at the default (east=none)
    # while its east neighbour computed west=low, so connectivity.py and verify.py disagreed.
    blocks = {(0, 0, 0): WALL, (1, 0, 0): WALL, (0, 1, 0): "minecraft:bamboo"}
    result, out = build(tmp_path, blocks, (2, 2, 1))
    unresolved = result.report["connectivity"]["unresolved"]
    assert len(unresolved) == 1 and unresolved[0]["pos"] == [0, 0, 0]
    assert "position-dependent" in unresolved[0]["reason"]
    assert out[0, 0, 0][1]["east"] == "low" and out[1, 0, 0][1]["west"] == "low"  # symmetric, height assumed low
    assert out[0, 0, 0][1]["up"] == "true"  # the post could not be resolved: default kept
    assert any("kept default connections" in w for w in result.report["warnings"])
    reference, connectivity = C.load_reference("26.3"), C.load_connectivity("26.3")
    verify(result.config.nbt_path, result.config.source, reference, "include", connectivity)


def test_unresolved_neighbour_side_does_not_break_the_other_sides(tmp_path):
    # wall between a wall (resolved) and scaffolding (dynamic): the wall side connects, the other side stays default
    blocks = {(0, 0, 0): WALL, (1, 0, 0): WALL, (2, 0, 0): "minecraft:scaffolding"}
    result, out = build(tmp_path, blocks, (3, 1, 1))
    assert out[0, 0, 0][1]["east"] == "low" and out[1, 0, 0][1]["west"] == "low" and out[1, 0, 0][1]["east"] == "none"
    reference, connectivity = C.load_reference("26.3"), C.load_connectivity("26.3")
    verify(result.config.nbt_path, result.config.source, reference, "include", connectivity)


def test_other_connection_properties_still_warn(tmp_path):
    result, _ = build(tmp_path, {(0, 0, 0): "minecraft:stone", (1, 0, 0): "minecraft:vine[up=true]"}, (2, 1, 1))
    assert any("minecraft:vine" in w and "not computed" in w for w in result.report["warnings"])


# --- rotation, determinism, verifier ------------------------------------------------------------


def _rotate_layout(blocks, size):
    """Turn a layout a quarter clockwise around y (x' = L-1-z, z' = x), states included."""
    w, h, length = size
    out = {}
    for (x, y, z), state in blocks.items():
        block_id, _, rest = state.partition("[")
        props = dict(p.split("=") for p in rest.rstrip("]").split(",")) if rest else {}
        props = rotate_props(props, "clockwise_90")
        text = block_id + ("[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]" if props else "")
        out[length - 1 - z, y, x] = text
    return out, (length, h, w)


def test_rotated_source_gives_rotated_connections(tmp_path):
    blocks = {
        **line(0, 3, z=0),
        (3, 0, 1): WALL,
        (3, 0, 2): "minecraft:oak_fence_gate[facing=east]",
        (3, 0, 3): WALL,
        (0, 1, 0): "minecraft:stone_bricks",
        (1, 0, 2): "minecraft:glass_pane",
        (1, 0, 3): "minecraft:iron_bars",
        (0, 0, 3): "minecraft:oak_fence",
        (0, 0, 2): "minecraft:oak_fence",
    }
    size = (4, 2, 5)
    _, out = build(tmp_path / "a", blocks, size)
    turned, turned_size = _rotate_layout(blocks, size)
    _, out_turned = build(tmp_path / "b", turned, turned_size)
    for (x, y, z), (block_id, props) in out.items():
        assert out_turned[size[2] - 1 - z, y, x] == (block_id, rotate_props(props, "clockwise_90"))


def test_conversion_is_deterministic(tmp_path):
    blocks = {**line(0, 3), (1, 1, 1): "minecraft:oak_slab[type=bottom]", (2, 0, 2): "minecraft:glass_pane"}
    first, _ = build(tmp_path / "a", blocks, (4, 2, 3))
    second, _ = build(tmp_path / "b", blocks, (4, 2, 3))
    assert first.nbt == second.nbt
    assert C.report_text(first.report).replace(str(tmp_path / "a"), "") == C.report_text(second.report).replace(
        str(tmp_path / "b"), ""
    )


def test_committed_testbed_exports_are_reproducible():
    for name in ("connectivity_testbed", "connectivity_testbed_air_omit"):
        config = C.load_config(ROOT / f"exports/structures/{name}.toml")
        result = C.convert(config)
        assert config.nbt_path.read_bytes() == result.nbt
        assert config.report_path.read_text() == C.report_text(result.report)
        summary = verify(
            config.nbt_path, config.source, C.load_reference("26.3"), config.air, C.load_connectivity("26.3")
        )
        assert summary["connection_cells_computed"] == 67


def _tamper(result, pos, **props):
    """Change properties of the (single-use) palette entry of the block at pos."""
    nbt = nbtlib.File.parse(io.BytesIO(gzip.decompress(result.nbt)))
    (state,) = [int(b["state"]) for b in nbt["blocks"] if tuple(int(v) for v in b["pos"]) == pos]
    assert [int(b["state"]) for b in nbt["blocks"]].count(state) == 1
    nbt["palette"][state]["properties"].update({k: nbtlib.String(v) for k, v in props.items()})
    raw = io.BytesIO()
    nbt.write(raw)
    result.config.nbt_path.write_bytes(gzip.compress(raw.getvalue(), mtime=0))


@pytest.mark.parametrize(
    "props, message",
    [
        ({"east": "low"}, "connects to nothing"),  # (1, 0, 1) east is air
        ({"west": "none"}, "does not connect west"),
        ({"waterlogged": "true"}, "changed"),
    ],
)
def test_verifier_checks_computed_connections(tmp_path, props, message):
    result, _ = build(tmp_path, line(0, 1), (3, 1, 3))
    reference, connectivity = C.load_reference("26.3"), C.load_connectivity("26.3")
    verify(result.config.nbt_path, result.config.source, reference, "include", connectivity)
    with pytest.raises(VerificationError, match="cells differ"):  # without the reference no change is allowed
        verify(result.config.nbt_path, result.config.source, reference, "include")
    _tamper(result, (1, 0, 1), **props)
    with pytest.raises(VerificationError, match=message):
        verify(result.config.nbt_path, result.config.source, reference, "include", connectivity)
