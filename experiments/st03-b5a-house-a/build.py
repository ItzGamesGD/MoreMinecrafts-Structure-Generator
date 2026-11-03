"""ST-03 B3-05A: House A, formal build that keeps the existing design.

Kept from the contract and the earlier design: module M-house_a, 9 x 10 x 7 (x, y, z), air=include, floor y=0,
walls on the box edge (room x1..7, z1..5), south door at (4, 1..2, 6), cobblestone base + dark-oak upper story,
north-south gable ridge at x=4, y=9 with the 45-degree profile y = 5 + min(x, 8 - x), and the design-package decor
cells (bed, crafting table, furnace, barrel) at their exact positions and states. Porch: not built (B3-02 Q01 asks
for an external porch outside the box; its placement contract is still open).

Added within those rules: timber frame (log posts, stripped-log plates, door frame and lintel), gable infill set back
one block so the roof overhangs both gable ends, deepslate-tile roof with dark-oak barge boards, a stone chimney in the
east wall behind the furnace, an ominous banner and chain lanterns under the front overhang, and a furnished,
lit interior with garrison clutter.

  PYTHONPATH=. python experiments/st03-b5a-house-a/build.py
"""

import json
import shutil
import tempfile
from pathlib import Path

from tools.seam01 import assembly as A
from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent
W, H, D = 9, 10, 7
DOOR = (4, 6)
# interactive blocks that must be reachable from the floor (checks.py)
INTERACTIVE = {
    "bed": (2, 1, 1),
    "chest": (3, 1, 1),
    "crafting_table": (7, 1, 1),
    "fletching_table": (7, 1, 2),
    "furnace": (7, 1, 3),
    "anvil": (7, 1, 4),
    "barrel_east": (7, 1, 5),
    "barrel_decor": (1, 1, 5),
    "grindstone": (1, 1, 4),
}
# screenshot views: name -> (x, dy, z, yaw, pitch); y = feet level + dy. Exterior first, interior last.
VIEWS = {
    "01_front": (4.5, 3, 18.5, 180, 2),
    "02_back": (4.5, 3, -12.5, 0, 2),
    "03_left_west": (-11.5, 3, 3.5, -90, 2),
    "04_right_east": (20.5, 3, 3.5, 90, 2),
    "05_diagonal_southeast": (14.5, 4, 16.5, 135, 4),
    "06_diagonal_northwest": (-6.5, 4, -10.5, -45, 4),
    "07_entrance_closeup": (4.5, 0.5, 11.5, 180, 4),
    "08_interior_bed_side": (5.6, 0, 4.6, 135, 22),
    "09_interior_work_side": (2.4, 0, 4.6, -135, 22),
}


def design():
    cells = {}

    def put(x, y, z, block, **props):
        assert 0 <= x < W and 0 <= y < H and 0 <= z < D, (x, y, z)
        cells[(x, y, z)] = (
            "minecraft:" + block,
            {k: str(v).lower() for k, v in props.items()},
        )

    edge = lambda x, z: x in (0, W - 1) or z in (0, D - 1)
    corner = lambda x, z: x in (0, W - 1) and z in (0, D - 1)
    mossy = {
        (0, 1),
        (8, 5),
        (2, 6),
        (6, 0),
        (0, 5),
        (8, 1),
    }  # (x, z) of base-course weathering

    # floor: stone perimeter, plank room floor, stone-brick threshold
    for x in range(W):
        for z in range(D):
            put(x, 0, z, "cobblestone" if edge(x, z) else "dark_oak_planks")
    put(4, 0, 6, "stone_bricks")
    # walls y=1..4 on the box edge
    for x in range(W):
        for z in range(D):
            if not edge(x, z):
                continue
            for y in range(1, 5):
                if corner(x, z):
                    put(x, y, z, "dark_oak_log", axis="y")
                elif y == 1:
                    put(
                        x,
                        y,
                        z,
                        "mossy_cobblestone" if (x, z) in mossy else "cobblestone",
                    )
                elif y == 4:  # top plate runs along the wall
                    put(
                        x,
                        y,
                        z,
                        "stripped_dark_oak_log",
                        axis="z" if x in (0, W - 1) else "x",
                    )
                else:
                    put(x, y, z, "dark_oak_planks")
    # mid posts: west wall z=3, back wall x=4 (east wall z=3 is the chimney)
    for y in range(2, 5):
        put(0, y, 3, "dark_oak_log", axis="y")
        put(4, y, 0, "dark_oak_log", axis="y")
    # door frame: full-height posts, lintel, door
    for y in range(1, 4):
        put(3, y, 6, "dark_oak_log", axis="y")
        put(5, y, 6, "dark_oak_log", axis="y")
    put(4, 3, 6, "stripped_dark_oak_log", axis="x")
    put(
        4,
        1,
        6,
        "dark_oak_door",
        facing="south",
        half="lower",
        hinge="left",
        open=False,
        powered=False,
    )
    put(
        4,
        2,
        6,
        "dark_oak_door",
        facing="south",
        half="upper",
        hinge="left",
        open=False,
        powered=False,
    )
    # windows (same openings as B3-01)
    for y in (2, 3):
        for x, z in [(0, 2), (0, 4), (8, 2), (8, 4), (2, 0), (6, 0), (2, 6), (6, 6)]:
            put(x, y, z, "glass_pane")
    # ceiling / attic floor
    for x in range(1, W - 1):
        for z in range(1, D - 1):
            put(x, 5, z, "dark_oak_planks")
    # gable ends set back to z=1 and z=5: tie beam at y=5, king post, plank infill -> roof overhangs both ends
    for zg in (1, 5):
        for x in range(1, W - 1):
            put(x, 5, zg, "stripped_dark_oak_log", axis="x")
        for y in range(6, 9):
            for x in range(y - 4, 13 - y):
                put(
                    x,
                    y,
                    zg,
                    "dark_oak_log" if x == 4 else "dark_oak_planks",
                    **({"axis": "y"} if x == 4 else {}),
                )
    # roof: deepslate tiles, dark-oak barge boards on the overhanging end rows, ridge at x=4
    for x in range(W):
        y = 5 + min(x, 8 - x)
        for z in range(D):
            end = z in (0, D - 1)
            if x == 4:
                put(x, y, z, "dark_oak_log", axis="z") if end else put(
                    x, y, z, "deepslate_tiles"
                )
            else:
                put(
                    x,
                    y,
                    z,
                    "dark_oak_stairs" if end else "deepslate_tile_stairs",
                    facing="east" if x < 4 else "west",
                    half="bottom",
                    shape="straight",
                )
    # chimney in the east wall behind the furnace, through the eave, capped
    for y in range(1, 9):
        put(8, y, 3, "cobblestone" if y < 5 else "stone_bricks")
    put(8, 9, 3, "cobblestone_wall")
    # front overhang: ominous banner on the king post, chain lanterns over the two front windows
    put(4, 7, 6, "white_wall_banner", facing="south")
    for x in (2, 6):
        put(x, 6, 6, "iron_chain", axis="y")
        put(x, 5, 6, "lantern", hanging=True)

    # interior: design-package decor (exact cells and states) ...
    put(1, 1, 1, "red_bed", facing="east", occupied=False, part="foot")
    put(2, 1, 1, "red_bed", facing="east", occupied=False, part="head")
    put(7, 1, 1, "crafting_table")
    put(7, 1, 3, "furnace", facing="west", lit=False)
    put(1, 1, 5, "barrel", facing="east", open=False)
    put(4, 4, 3, "lantern", hanging=True)
    # ... and added garrison furnishing
    put(3, 1, 1, "chest", facing="south", type="single")
    put(7, 1, 2, "fletching_table")
    put(7, 1, 4, "chipped_anvil", facing="north")
    put(7, 1, 5, "barrel", facing="up", open=False)
    put(7, 2, 5, "barrel", facing="up", open=False)
    put(7, 3, 5, "lantern", hanging=False)
    put(1, 2, 5, "barrel", facing="up", open=False)
    put(1, 1, 4, "grindstone", face="floor", facing="east")
    put(4, 3, 1, "white_wall_banner", facing="south")
    for x in (3, 4, 5):
        for z in (2, 3, 4):
            put(x, 1, z, "gray_carpet")
    put(3, 3, 5, "wall_torch", facing="north")
    put(5, 3, 5, "wall_torch", facing="north")
    return cells


def main():
    module = A.modules()["M-house_a"]
    assert (
        module["size"] == [W, H, D]
        and module["air"] == "include"
        and module["file"] == "st03_house_a"
    ), module
    cells = design()
    with tempfile.TemporaryDirectory() as d:
        result = export_module(module, cells, Path(d) / "pack")
        shutil.copyfile(result.config.nbt_path, ROOT / "st03_house_a.nbt")
        shutil.copyfile(result.config.source, ROOT / "st03_house_a.schem")
        (ROOT / "export-report.json").write_text(
            json.dumps(result.report, indent=2, sort_keys=True) + "\n"
        )
    print(f"st03_house_a.nbt: {len(cells)} authored cells, size {module['size']}")


if __name__ == "__main__":
    main()
