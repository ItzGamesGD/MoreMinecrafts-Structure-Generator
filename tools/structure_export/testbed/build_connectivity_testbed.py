"""Build the connectivity testbed .schem with mcbuild's own exporter (bare block names, as mcbuild writes).

    uv run --project vendor/mcbuild python tools/structure_export/testbed/build_connectivity_testbed.py

Each case sits in its own 8x8 plot so cases do not touch. Only properties that have nothing to do
with connections are written (gate facing, slab type), plus one deliberate explicit `up` to show that
stated properties are kept. The committed .schem is the pinned source of
exports/structures/connectivity_testbed*.toml; rebuilding it changes its gzip header (nbtlib writes a
timestamp), so update the sha256 pins if you rebuild it on purpose.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))

from mcbuild.export.schem import export_schem  # noqa: E402
from mcbuild.palette import get_block  # noqa: E402
from mcbuild.voxel import VoxelGrid  # noqa: E402

OUT = ROOT / "artifacts/mmst-connectivity/connectivity_testbed.schem"
SIZE = (24, 3, 24)


def build() -> VoxelGrid:
    grid = VoxelGrid()

    def put(x, y, z, name):
        grid.set(x, y, z, get_block(name).index)

    # fix the box: unbuilt cells are exported as air either way
    put(0, 0, 0, "air")
    put(SIZE[0] - 1, SIZE[1] - 1, SIZE[2] - 1, "air")

    # plot (1, 1): straight run; the middle wall states up=true explicitly (vanilla would drop the post)
    for x in range(1, 6):
        put(x, 0, 1, "stone_brick_wall[up=true]" if x == 3 else "stone_brick_wall")
    # plot (9, 1): corner
    for x in range(9, 12):
        put(x, 0, 1, "stone_brick_wall")
    for z in range(2, 4):
        put(11, 0, z, "stone_brick_wall")
    # plot (17, 1): T junction
    for x in range(17, 22):
        put(x, 0, 1, "cobblestone_wall")
    for z in range(2, 4):
        put(19, 0, z, "cobblestone_wall")
    # plot (1, 9): cross
    for i in range(5):
        put(1 + i, 0, 11, "mossy_stone_brick_wall")
        put(3, 0, 9 + i, "mossy_stone_brick_wall")
    # plot (9, 9): what stands on a wall decides tall/low and the post
    for x in range(9, 14):
        put(x, 0, 9, "stone_brick_wall")
    put(9, 1, 9, "stone_bricks")  # full face: tall
    put(10, 1, 9, "oak_slab[type=bottom]")  # bottom slab covers the top: tall
    put(11, 1, 9, "torch")  # wall_post_override: post stays
    put(12, 1, 9, "oak_slab[type=top]")  # top slab leaves the top open: low
    put(13, 1, 9, "stone_brick_wall")  # wall on a wall
    for x in range(9, 14):  # two-high run
        put(x, 0, 11, "stone_brick_wall")
        put(x, 1, 11, "stone_brick_wall")
    # plot (17, 9): one wall, four different neighbours; fences next to a pumpkin and stone
    put(19, 0, 11, "stone_brick_wall")
    put(19, 0, 10, "stone")  # sturdy: connects
    put(20, 0, 11, "oak_leaves[persistent=true]")  # isExceptionForConnection: no (persistent: no decay)
    put(19, 0, 12, "oak_fence")  # not a wall, not sturdy: no
    put(18, 0, 11, "iron_bars")  # IronBarsBlock: yes
    put(21, 0, 9, "oak_fence")
    put(20, 0, 9, "pumpkin")  # sturdy but an exception: no
    put(21, 0, 10, "stone")  # sturdy: yes
    # plot (1, 17): fences and a gate
    for x, name in (
        (1, "oak_fence"),
        (2, "oak_fence"),
        (3, "oak_fence_gate[facing=north]"),
        (4, "spruce_fence"),
        (5, "nether_brick_fence"),
    ):
        put(x, 0, 17, name)
    for x in range(1, 4):
        put(x, 0, 19, "nether_brick_fence")
    # plot (9, 17): gates in walls
    put(9, 0, 17, "stone_brick_wall")
    put(10, 0, 17, "oak_fence_gate[facing=south]")  # spans x: walls on both sides -> in_wall
    put(11, 0, 17, "stone_brick_wall")
    put(9, 0, 19, "stone_brick_wall")
    put(10, 0, 19, "oak_fence_gate[facing=east]")  # spans z: the walls are at its ends
    put(11, 0, 19, "stone_brick_wall")
    # plot (17, 17): panes and bars
    for x, name in (
        (17, "glass_pane"),
        (18, "glass_pane"),
        (19, "glass_pane"),
        (20, "iron_bars"),
        (21, "white_stained_glass_pane"),
    ):
        put(x, 0, 17, name)
    for z in range(18, 20):
        put(17, 0, z, "glass_pane")
    put(21, 0, 18, "stone_bricks")
    put(20, 0, 19, "cobblestone_wall")
    put(20, 0, 18, "iron_bars")
    # template boundary: east edge, north edge and top layer
    for x in range(21, 24):
        put(x, 0, 5, "stone_brick_wall")
    put(13, 0, 0, "stone_brick_wall")
    put(5, 0, 5, "stone_bricks")
    put(5, 1, 5, "stone_bricks")
    put(5, 2, 5, "stone_brick_wall")
    put(6, 2, 5, "stone_brick_wall")
    return grid


def main() -> None:
    grid = build()
    (lo, hi) = grid.bounds
    assert lo == (0, 0, 0) and tuple(h + 1 for h in hi) == SIZE, grid.bounds
    OUT.parent.mkdir(parents=True, exist_ok=True)
    export_schem(grid, str(OUT))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
