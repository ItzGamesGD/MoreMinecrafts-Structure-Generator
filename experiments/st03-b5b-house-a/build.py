"""ST-03 B3-05B: House A, autonomous design experiment ("garrison house").

Fixed: module M-house_a, 9 x 10 x 7 (x, y, z), air=include, floor y=0 flush with the ground, nothing outside the
box, door on the south face (the side the B3-01 house and its two placements F11/F14 face). Everything else is a new
design; the B3-01 cell map was used only as a reference.

Massing (x east, z south):
  * stone plinth (y 1..2) on the outer ring x=0, x=8, z=0, capped by a sloped stone-brick water table (y 3),
    with iron-bar arrow slits at eye height;
  * a dark-oak timber frame with spruce infill set back one block (x=1, x=7, z=1) on top of it, so the deepslate
    roof's lowest course (x=0 / x=8, y 5) forms a real one-block eave over the walls, and the gables (z=1, z=5)
    sit one block behind the roof's end rows;
  * a full-width covered porch inside the box at z=6: four posts, a beam that carries the front roof row,
    fence rails, a lantern over the entry, ominous banner on the front gable;
  * an off-centre stone chimney on the west side breaking the eave;
  * inside: two-bed garrison room with footlocker, smithing/fletching corner, stores, hearth.

  PYTHONPATH=. python experiments/st03-b5b-house-a/build.py
"""

import json
import shutil
import tempfile
from pathlib import Path

from tools.seam01 import assembly as A
from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent
W, H, D = 9, 10, 7
DOOR = (4, 5)  # door column; the porch (z=6) is between the door and the outside
INTERACTIVE = {
    "bed_west": (3, 1, 2),
    "bed_east": (5, 1, 2),
    "footlocker_chest": (4, 1, 1),
    "furnace": (1, 1, 2),
    "grindstone": (7, 1, 1),
    "fletching_table": (7, 1, 2),
    "crafting_table": (7, 1, 3),
    "barrel_stores": (7, 1, 4),
    "anvil": (2, 1, 1),
    "barrel_west": (1, 1, 4),
}
VIEWS = {
    "01_front": (4.5, 3, 18.5, 180, 2),
    "02_back": (4.5, 3, -12.5, 0, 2),
    "03_left_west": (-11.5, 3, 3.5, -90, 2),
    "04_right_east": (20.5, 3, 3.5, 90, 2),
    "05_diagonal_southeast": (14.5, 4, 16.5, 135, 4),
    "06_diagonal_southwest": (-5.5, 4, 16.5, -135, 4),
    "07_diagonal_northwest": (-6.5, 4, -10.5, -45, 4),
    "08_entrance_closeup": (4.5, 0.5, 11.5, 180, 4),
    "09_interior_beds": (4.5, 0, 4.4, 180, 25),
    "10_interior_work_corner": (2.5, 0, 4.4, -125, 22),
}

PLANK, LOG, STRIP = "spruce_planks", "dark_oak_log", "stripped_dark_oak_log"


def design():
    cells = {}

    def put(x, y, z, block, **props):
        assert 0 <= x < W and 0 <= y < H and 0 <= z < D, (x, y, z)
        cells[(x, y, z)] = (
            "minecraft:" + block,
            {k: str(v).lower() for k, v in props.items()},
        )

    def stairs(x, y, z, block, facing, half="bottom"):
        put(x, y, z, block, facing=facing, half=half, shape="straight")

    ring = lambda x, z: (x in (0, 8) and z <= 5) or z == 0
    quoin = {(0, 0), (8, 0), (0, 5), (8, 5)}
    mossy = {(0, 1, 3), (8, 1, 1), (3, 1, 0), (6, 2, 0), (0, 2, 5), (8, 1, 4)}
    slits = {(0, 4), (8, 2), (8, 4), (2, 0), (6, 0)}  # (x, z) arrow slits at y=2

    # ---- ground (y=0): plinth footing, spruce room floor, stone-brick porch paving
    for x in range(W):
        for z in range(D):
            if z == 6:
                put(
                    x,
                    0,
                    z,
                    "mossy_stone_bricks"
                    if x in (1, 7)
                    else ("cracked_stone_bricks" if x == 5 else "stone_bricks"),
                )
            elif ring(x, z) or z == 5:
                put(x, 0, z, "cobblestone")
            else:
                put(x, 0, z, "spruce_planks")
    put(4, 0, 5, "stone_bricks")  # threshold
    # ---- stone plinth y=1..2 with quoins, arrow slits; water table y=3
    for x in range(W):
        for z in range(6):
            if not ring(x, z):
                continue
            for y in (1, 2):
                if (x, z) in quoin:
                    put(x, y, z, "stone_bricks")
                elif y == 2 and (x, z) in slits:
                    put(x, y, z, "iron_bars")
                else:
                    put(
                        x,
                        y,
                        z,
                        "mossy_cobblestone" if (x, y, z) in mossy else "cobblestone",
                    )
            if (x, z) in quoin:
                put(x, 3, z, "chiseled_stone_bricks")
            elif x == 0:
                stairs(x, 3, z, "stone_brick_stairs", "east")
            elif x == 8:
                stairs(x, 3, z, "stone_brick_stairs", "west")
            else:
                stairs(x, 3, z, "stone_brick_stairs", "south")
    # ---- timber frame set back on x=1, x=7, z=1; front wall z=5
    for x, z in ((1, 1), (7, 1), (1, 5), (7, 5)):
        for y in range(1, 5):
            put(x, y, z, LOG, axis="y")
    for z in (2, 3, 4):  # side walls: sill beam, band, plate
        for x in (1, 7):
            put(x, 3, z, STRIP, axis="z")
            put(
                x,
                4,
                z,
                LOG if z == 3 else "glass_pane",
                **({"axis": "y"} if z == 3 else {}),
            )
    for x in (2, 3, 4, 5, 6):  # back wall
        put(x, 3, 1, STRIP, axis="x")
        put(
            x,
            4,
            1,
            {2: PLANK, 3: "glass_pane", 4: LOG, 5: "glass_pane", 6: PLANK}[x],
            **({"axis": "y"} if x == 4 else {}),
        )
    for x in (1, 7):  # top plates of the side walls
        for z in range(1, 6):
            put(x, 5, z, STRIP, axis="z")
    for z in (1, 5):
        for x in range(2, 7):
            put(x, 5, z, STRIP, axis="x")
    # front wall (under the porch): stone course, windows, door frame, lintel
    for x in (2, 6):
        put(x, 1, 5, "cobblestone")
        put(x, 2, 5, "glass_pane")
        put(x, 3, 5, "glass_pane")
        put(x, 4, 5, PLANK)
    for x in (3, 5):
        for y in range(1, 5):
            put(x, y, 5, LOG, axis="y")
    put(
        4,
        1,
        5,
        "dark_oak_door",
        facing="south",
        half="lower",
        hinge="right",
        open=False,
        powered=False,
    )
    put(
        4,
        2,
        5,
        "dark_oak_door",
        facing="south",
        half="upper",
        hinge="right",
        open=False,
        powered=False,
    )
    put(4, 3, 5, STRIP, axis="x")
    put(4, 4, 5, PLANK)
    # ceiling over the main room
    for x in range(2, 7):
        for z in range(2, 5):
            put(x, 5, z, "dark_oak_planks")
    # ---- gables on z=1 and z=5 (one block behind the roof end rows)
    for zg in (1, 5):
        for y in range(6, 9):
            for x in range(y - 4, 13 - y):
                if x == 4:
                    put(x, y, zg, LOG, axis="y")
                else:
                    put(x, y, zg, PLANK)
    put(
        3,
        7,
        1,
        "spruce_trapdoor",
        facing="north",
        half="bottom",
        open=True,
        powered=False,
        waterlogged=False,
    )
    put(
        5,
        7,
        1,
        "spruce_trapdoor",
        facing="north",
        half="bottom",
        open=True,
        powered=False,
        waterlogged=False,
    )
    # ---- roof: deepslate tiles, dark-oak barge rows at both ends, ridge at x=4
    for x in range(W):
        y = 5 + min(x, 8 - x)
        for z in range(D):
            end = z in (0, 6)
            if x == 4:
                put(x, y, z, LOG, axis="z") if end else put(x, y, z, "deepslate_tiles")
            else:
                stairs(
                    x,
                    y,
                    z,
                    "dark_oak_stairs" if end else "deepslate_tile_stairs",
                    "east" if x < 4 else "west",
                )
    # ---- porch at z=6: posts, beam, rails, lanterns, banner
    for x in (
        0,
        3,
        5,
        8,
    ):  # posts on stone footings, in line with the door frame and the corners
        put(x, 1, 6, "stone_bricks")
        for y in (2, 3):
            put(x, y, 6, LOG, axis="y")
    for x in range(W):
        put(x, 4, 6, STRIP, axis="x")
    for x in (1, 2, 6, 7):  # rails in front of the windows; entry at x=4
        put(x, 1, 6, "dark_oak_fence")
    put(4, 3, 6, "lantern", hanging=True)
    put(4, 7, 6, "white_wall_banner", facing="south")
    # ---- chimney on the west side (breaks the eave), stack above the roof line
    for y in range(1, 9):
        put(0, y, 2, "cobblestone" if y < 5 else "stone_bricks")
    put(0, 9, 2, "cobblestone_wall")
    # ---- interior
    put(3, 1, 1, "gray_bed", facing="north", occupied=False, part="head")
    put(3, 1, 2, "gray_bed", facing="north", occupied=False, part="foot")
    put(5, 1, 1, "gray_bed", facing="north", occupied=False, part="head")
    put(5, 1, 2, "gray_bed", facing="north", occupied=False, part="foot")
    put(4, 1, 1, "chest", facing="south", type="single")
    put(4, 4, 2, "white_wall_banner", facing="south")
    put(2, 1, 1, "chipped_anvil", facing="east")
    put(1, 1, 2, "furnace", facing="east", lit=False)
    put(1, 1, 3, "cauldron")
    put(1, 1, 4, "barrel", facing="up", open=False)
    put(1, 2, 4, "barrel", facing="up", open=False)
    put(7, 1, 1, "grindstone", face="floor", facing="west")
    put(7, 1, 2, "fletching_table")
    put(7, 1, 3, "crafting_table")
    put(7, 1, 4, "barrel", facing="west", open=False)
    put(7, 2, 4, "lantern", hanging=False)
    put(4, 4, 3, "lantern", hanging=True)
    for x in (3, 4, 5):
        for z in (3, 4):
            put(x, 1, z, "gray_carpet")
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
