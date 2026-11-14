"""ST-03 facility batch 1 (living/support group, Q74/Q17): F18 kitchen, F19 smithy, F20 cart shed.

Contract kept (tools/seam01/data/st03_placements.json, untouched): modules M-kitchen 9x11x9, M-smithy 9x11x9,
M-cart_shed 8x9x7 (x, y, z), air=include, floor y=0, local_turns 0 for F18/F19/F20. Each module's own front
(door side) is its +z face; the placement rotation (none) is not changed here.

Owner decisions applied (docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md):
  Q11 distinct identities: closed stone kitchen / stone forge+chimney smithy / open timber cart shed.
  Q12 kitchen: wall fireplace + chimney, preparation counter, storage, central aisle.
  Q13 smithy: open front, stone back and sides, forge + chimney, anvil and grindstone.
  Q14 cart shed: front and sides open, small cart model, storage and tools inside the bounds.
  Q15 usable workstations and real inventory-bearing containers (chest/barrel). Containers stay EMPTY: ordinary loot
      tables per facility are a runtime/mod decision (item weights and quantities are still OPEN); no cosmetic crate
      is a container, so no extra loot rolls.
  Shared: stone-brick family + spruce and dark oak; naturally mixed stone variants, no fixed ratio.

  PYTHONPATH=. python experiments/st03-batch1-support/build.py
"""

import json
import shutil
import tempfile
from pathlib import Path

from tools.seam01 import assembly as A
from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent

BUILDINGS = {}  # key -> dict(module, file, size, door, design, interactive, views)


class Cells(dict):
    def __init__(self, size):
        super().__init__()
        self.W, self.H, self.D = size

    def put(self, x, y, z, block, **props):
        assert 0 <= x < self.W and 0 <= y < self.H and 0 <= z < self.D, (x, y, z, block)
        self[(x, y, z)] = (
            "minecraft:" + block,
            {k: str(v).lower() for k, v in props.items()},
        )

    def box(self, x0, x1, y0, y1, z0, z1, block, **props):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    self.put(x, y, z, block, **props)


def stone(x, y, z):
    """Naturally mixed stone family, deterministic, no fixed ratio; rarer mixing high on the wall."""
    h = (x * 31 + y * 17 + z * 13 + x * z) % 11
    if h == 0:
        return "cracked_stone_bricks"
    if h == 1:
        return "mossy_stone_bricks"
    if h == 2 and y <= 2:
        return "andesite"
    if h == 3 and y <= 2:
        return "cobblestone"
    return "stone_bricks"


def floor_stone(x, z):
    h = (x * 7 + z * 11 + x * z) % 9
    return ["stone_bricks", "cobblestone", "andesite", "stone_bricks", "mossy_cobblestone",
            "stone_bricks", "stone_bricks", "cracked_stone_bricks", "gravel"][h] if h != 8 else "coarse_dirt"


def roof(c, y0, wood, barge, ridge_block, ends=(0, None), flush_ends=False):
    """Gable roof along z, rising 1 per x toward the centre. Returns roof height per x."""
    W, D = c.W, c.D
    z_end = D - 1 if ends[1] is None else ends[1]
    ry = {}
    for x in range(W):
        y = y0 + min(x, W - 1 - x)
        ry[x] = y
        for z in range(D):
            end = z in (ends[0], z_end)
            if W % 2 == 1 and x == (W - 1) // 2:
                if end:
                    c.put(x, y, z, "dark_oak_log", axis="z")
                else:
                    c.put(x, y, z, ridge_block)
                continue
            c.put(
                x, y, z, barge if end else wood,
                facing="east" if x < W / 2 else "west", half="bottom", shape="straight",
            )
    return ry


def gable_fill(c, zg, plate_y, ry, planks="spruce_planks", post="dark_oak_log"):
    """Triangular infill at z=zg between the tie beam (plate_y) and the roof underside."""
    W = c.W
    for x in range(1, W - 1):
        c.put(x, plate_y, zg, "stripped_dark_oak_log", axis="x")
    top = max(ry.values())
    for y in range(plate_y + 1, top):
        for x in range(1, W - 1):
            if ry[x] > y:
                mid = W % 2 == 1 and x == (W - 1) // 2
                if mid:
                    c.put(x, y, zg, post, axis="y")
                else:
                    c.put(x, y, zg, planks)


# --------------------------------------------------------------------------------------------- F18 kitchen
def kitchen():
    c = Cells((9, 11, 9))
    W, D = 9, 9
    # floor
    for x in range(W):
        for z in range(D):
            c.put(x, 0, z, floor_stone(x, z))
    for z in range(1, D - 1):  # central aisle: tidy stone-brick runner
        c.put(4, 0, z, "stone_bricks")
    c.put(4, 0, D - 1, "stone_bricks")
    # closed stone walls y=1..4, spruce plate band y=5, dark-oak corner posts
    for x in range(W):
        for z in range(D):
            if x in (0, W - 1) or z in (0, D - 1):
                corner = x in (0, W - 1) and z in (0, D - 1)
                for y in range(1, 5):
                    c.put(x, y, z, "dark_oak_log" if corner else stone(x, y, z), **({"axis": "y"} if corner else {}))
                c.put(x, 5, z, "stripped_spruce_log", axis="z" if x in (0, W - 1) else "x")
    # door in the south face: stone-brick frame, spruce door
    for y in (1, 2):
        c.put(3, y, D - 1, "stone_bricks")
        c.put(5, y, D - 1, "stone_bricks")
    c.put(3, 3, D - 1, "stone_bricks"); c.put(4, 3, D - 1, "stone_bricks"); c.put(5, 3, D - 1, "stone_bricks")
    c.put(4, 1, D - 1, "spruce_door", facing="south", half="lower", hinge="left", open=False, powered=False)
    c.put(4, 2, D - 1, "spruce_door", facing="south", half="upper", hinge="left", open=False, powered=False)
    # small windows
    for z in (3, 6):
        for y in (2, 3):
            c.put(0, y, z, "glass_pane"); c.put(W - 1, y, z, "glass_pane")
    for x in (2, 6):
        for y in (2, 3):
            c.put(x, y, D - 1, "glass_pane")
    # timber roof (spruce) with dark-oak barge/ridge, gable ends set back one block
    ry = roof(c, 6, "spruce_stairs", "dark_oak_stairs", "spruce_planks")
    gable_fill(c, 1, 5, ry)
    gable_fill(c, D - 2, 5, ry)
    # rafters / tie beams across the hall (hanging lanterns)
    for z in (3, 6):
        for x in range(1, W - 1):
            c.put(x, 5, z, "stripped_spruce_log", axis="x")
    # ---- wall fireplace + chimney, north wall centre (x 3..5, z 0..1)
    for x in (3, 4, 5):
        for z in (0, 1):
            for y in range(1, 11):
                c.pop((x, y, z), None)
    c.box(3, 5, 1, 10, 0, 1, "stone_bricks")
    for y in range(1, 11):  # breast weathering
        c.put(3, y, 0, stone(3, y, 0)); c.put(5, y, 0, stone(5, y, 0))
    c.put(4, 1, 1, "netherrack")
    c.put(4, 2, 1, "fire", age=0, north=False, east=False, south=False, west=False, up=False)
    for y in range(3, 10):  # flue
        c.pop((4, y, 1), None)
        c.put(4, y, 1, "air")
    c.put(4, 3, 1, "stone_brick_slab", type="bottom")  # damper shelf above the firebox, flue above is open
    for x in (3, 4, 5):  # chimney cap
        for z in (0, 1):
            if (x, z) != (4, 1):
                c.put(x, 10, z, "stone_brick_slab", type="bottom")
    c.put(4, 10, 0, "stone_brick_slab", type="bottom")
    c.pop((4, 10, 1), None)
    c.put(2, 1, 1, "stone_bricks"); c.put(6, 1, 1, "stone_bricks")
    c.put(3, 1, 2, "stone_brick_stairs", facing="north", half="bottom", shape="straight")
    c.put(5, 1, 2, "stone_brick_stairs", facing="north", half="bottom", shape="straight")
    # ---- preparation counter + workstations along the west wall (x=1, z 2..7)
    c.put(1, 1, 2, "furnace", facing="east", lit=False)
    c.put(1, 1, 3, "furnace", facing="east", lit=False)
    c.put(1, 1, 4, "crafting_table")
    c.put(1, 1, 5, "water_cauldron", level=3)
    c.put(1, 1, 6, "composter", level=0)
    c.put(1, 2, 3, "spruce_pressure_plate", powered=False)
    c.put(1, 2, 2, "spruce_pressure_plate", powered=False)
    c.put(1, 2, 4, "spruce_pressure_plate", powered=False)
    # preparation table (island, off the central aisle)
    for z in (4, 5):
        c.put(6, 1, z, "spruce_planks")
        c.put(6, 2, z, "spruce_pressure_plate", powered=False)
    # ---- storage along the east wall (real containers, empty)
    c.put(7, 1, 2, "barrel", facing="west", open=False)
    c.put(7, 2, 2, "barrel", facing="west", open=False)
    c.put(7, 1, 3, "chest", facing="west", type="single")
    c.put(7, 1, 7, "chest", facing="west", type="single")
    c.put(7, 1, 6, "barrel", facing="up", open=False)
    c.put(7, 1, 1, "hay_block", axis="y")
    c.put(1, 1, 7, "hay_block", axis="y")
    # lighting + decor
    for x, z in ((3, 3), (5, 3), (3, 6), (5, 6)):
        c.put(x, 4, z, "lantern", hanging=True)
    c.put(2, 3, D - 2, "wall_torch", facing="north")
    c.put(6, 3, D - 2, "wall_torch", facing="north")
    return c


# --------------------------------------------------------------------------------------------- F19 smithy
def smithy():
    c = Cells((9, 11, 9))
    W, D = 9, 9
    for x in range(W):
        for z in range(D):
            c.put(x, 0, z, floor_stone(x, z))
    for z in range(1, D):
        c.put(4, 0, z, "stone_bricks")
    # stone back (north) and side walls, y=1..4, plate band y=5
    for x in range(W):
        for z in range(D):
            if x in (0, W - 1) or z == 0:
                corner = x in (0, W - 1) and z == 0
                for y in range(1, 5):
                    c.put(x, y, z, "dark_oak_log" if corner else stone(x, y, z), **({"axis": "y"} if corner else {}))
                c.put(x, 5, z, "stripped_dark_oak_log", axis="z" if x in (0, W - 1) else "x")
    # open front (south): corner + two intermediate dark-oak posts, low stone walls in the side bays, lintel beam
    for x in (0, 2, 6, 8):
        for y in range(1, 5):
            c.put(x, y, D - 1, "dark_oak_log", axis="y")
    for x in (1, 7):
        c.put(x, 1, D - 1, "stone_bricks")
    for x in range(W):
        c.put(x, 4, D - 1, "dark_oak_planks") if x in (1, 3, 4, 5, 7) else None
        c.put(x, 5, D - 1, "stripped_dark_oak_log", axis="x")
    # windows: narrow slits in the side walls
    for z in (3, 6):
        c.put(0, 3, z, "iron_bars"); c.put(W - 1, 3, z, "iron_bars")
    # roof (deepslate tile) over the whole box, open front gable (king post only), closed back gable
    ry = roof(c, 6, "deepslate_tile_stairs", "dark_oak_stairs", "deepslate_tiles")
    gable_fill(c, 1, 5, ry, planks="dark_oak_planks")
    for z in (3, 6):  # tie beams
        for x in range(1, W - 1):
            c.put(x, 5, z, "stripped_dark_oak_log", axis="x")
    # front gable: open, only a king post and tie beam show
    for y in range(6, 9):
        c.put(4, y, D - 2, "dark_oak_log", axis="y")
    for x in range(1, W - 1):
        c.put(x, 5, D - 2, "stripped_dark_oak_log", axis="x")
    # ---- forge + chimney: north wall centre, stack rises through the ridge
    for x in (3, 4, 5):
        for z in (0, 1):
            for y in range(1, 11):
                c.pop((x, y, z), None)
    c.box(3, 5, 1, 10, 0, 1, "stone_bricks")
    for y in range(1, 11):
        c.put(3, y, 0, stone(3, y, 0)); c.put(5, y, 0, stone(5, y, 0))
    c.put(4, 1, 1, "blast_furnace", facing="south", lit=False)
    c.put(3, 1, 1, "furnace", facing="south", lit=False)
    c.put(5, 1, 1, "lava_cauldron")
    for y in range(2, 10):  # flue above the blast furnace
        c.put(4, y, 1, "air")
    c.put(3, 2, 1, "stone_brick_stairs", facing="south", half="top", shape="straight")
    c.put(5, 2, 1, "stone_brick_stairs", facing="south", half="top", shape="straight")
    c.put(4, 2, 1, "iron_bars")
    for x in (3, 4, 5):
        for z in (0, 1):
            if (x, z) != (4, 1):
                c.put(x, 10, z, "stone_brick_slab", type="bottom")
    c.pop((4, 10, 1), None)
    # ---- anvil, grindstone, smithing table, quench cauldron
    c.put(4, 1, 4, "anvil", facing="east")
    c.put(1, 1, 1, "grindstone", face="floor", facing="south")
    c.put(2, 1, 1, "smithing_table")
    c.put(6, 1, 1, "stone_bricks")
    c.put(7, 1, 1, "water_cauldron", level=3)
    c.put(7, 1, 3, "stone_bricks")
    # storage (real containers, empty) on the west and east walls
    c.put(1, 1, 3, "chest", facing="east", type="single")
    c.put(1, 1, 4, "barrel", facing="east", open=False)
    c.put(1, 2, 4, "barrel", facing="east", open=False)
    c.put(7, 1, 4, "barrel", facing="west", open=False)
    c.put(7, 1, 5, "chest", facing="west", type="single")
    c.put(1, 1, 6, "hay_block", axis="y")
    # tool rack on the east wall (decor only): chains and iron bars
    c.put(7, 3, 2, "iron_bars"); c.put(7, 2, 2, "iron_bars")
    # coal supply
    c.put(7, 1, 6, "coal_block")
    # lighting
    for x, z in ((3, 3), (5, 3), (4, 6)):
        c.put(x, 4, z, "lantern", hanging=True)
    c.put(2, 3, 1, "wall_torch", facing="south")
    c.put(6, 3, 1, "wall_torch", facing="south")
    return c


# ------------------------------------------------------------------------------------------ F20 cart shed
def cart_shed():
    c = Cells((8, 9, 7))
    W, D = 8, 7
    for x in range(W):
        for z in range(D):
            h = (x * 5 + z * 3 + x * z) % 6
            c.put(x, 0, z, ["coarse_dirt", "gravel", "dirt_path", "gravel", "cobblestone", "coarse_dirt"][h])
    # closed spruce back wall (north) on a stone base
    for x in range(W):
        c.put(x, 1, 0, "cobblestone" if x % 3 else "mossy_cobblestone")
        for y in (2, 3):
            c.put(x, y, 0, "spruce_planks")
        c.put(x, 4, 0, "stripped_spruce_log", axis="x")
    # open timber frame: posts at the corners and one pair mid-way; side and front remain open
    for x in (0, 7):
        for z in (0, 3, 6):
            for y in range(1, 5):
                c.put(x, y, z, "dark_oak_log", axis="y")
    for z in range(D):
        for x in (0, 7):
            c.put(x, 4, z, "stripped_dark_oak_log", axis="z")
    for x in range(1, 7):
        c.put(x, 4, D - 1, "stripped_dark_oak_log", axis="x")
        c.put(x, 4, 3, "stripped_dark_oak_log", axis="x")
    # roof: 8 wide -> two-wide ridge pair at x=3,4 (both y=8), spruce with dark-oak barge ends
    for x in range(W):
        y = 5 + min(x, W - 1 - x)
        for z in range(D):
            end = z in (0, D - 1)
            c.put(x, y, z, "dark_oak_stairs" if end else "spruce_stairs",
                  facing="east" if x < W / 2 else "west", half="bottom", shape="straight")
    # ---- small cart model: bed on slabs, side boards (fences), two wheels, shafts toward the front
    for x in (3, 4):
        for z in (2, 3, 4):
            c.put(x, 1, z, "spruce_slab", type="bottom")
    for z in (2, 4):
        for x in (3, 4):
            c.put(x, 2, z, "spruce_fence", north=False, east=False, south=False, west=False)
    c.put(2, 1, 3, "dark_oak_trapdoor", facing="east", half="bottom", open=True)
    c.put(5, 1, 3, "dark_oak_trapdoor", facing="west", half="bottom", open=True)
    c.put(2, 2, 3, "dark_oak_trapdoor", facing="east", half="bottom", open=True)
    c.put(5, 2, 3, "dark_oak_trapdoor", facing="west", half="bottom", open=True)
    c.put(3, 1, 5, "stripped_spruce_log", axis="z")
    c.put(4, 1, 5, "stripped_spruce_log", axis="z")
    c.put(3, 2, 3, "hay_block", axis="y")
    # storage + tools at the back wall (real containers, empty)
    c.put(1, 1, 1, "chest", facing="south", type="single")
    c.put(2, 1, 1, "chest", facing="south", type="single")
    c.put(6, 1, 1, "barrel", facing="south", open=False)
    c.put(6, 2, 1, "barrel", facing="up", open=False)
    c.put(1, 2, 1, "hay_block", axis="y")
    c.put(3, 1, 1, "grindstone", face="floor", facing="south")
    # tools on the back wall: trapdoor racks + hanging lantern
    c.put(3, 3, 1, "dark_oak_trapdoor", facing="south", half="top", open=True)
    c.put(4, 3, 1, "dark_oak_trapdoor", facing="south", half="top", open=True)
    c.put(6, 3, 1, "lantern", hanging=False)
    c.put(1, 3, 1, "lantern", hanging=False)
    return c


BUILDINGS = {
    "kitchen": dict(module="M-kitchen", design=kitchen, door=(4, 8), size=(9, 11, 9),
                    interactive={"furnace_a": (1, 1, 2), "furnace_b": (1, 1, 3), "crafting_table": (1, 1, 4),
                                 "cauldron": (1, 1, 5), "composter": (1, 1, 6), "barrel_a": (7, 1, 2),
                                 "chest_a": (7, 1, 3), "barrel_b": (7, 1, 6), "chest_b": (7, 1, 7)},
                    views={"01_front": (4.5, 3, 20.5, 180, 4), "02_back": (4.5, 3, -12.5, 0, 6),
                           "03_west": (-12.5, 3, 4.5, -90, 4), "04_east": (21.5, 3, 4.5, 90, 4),
                           "05_diag_se": (16.5, 5, 18.5, 135, 8), "06_diag_nw": (-8.5, 5, -10.5, -45, 8),
                           "07_interior_fireplace": (4.5, 0, 7.0, 180, 12),
                           "08_interior_counter": (6.5, 0, 7.0, 112, 20)}),
    "smithy": dict(module="M-smithy", design=smithy, door=(4, 8), size=(9, 11, 9),
                   interactive={"anvil": (4, 1, 4), "grindstone": (1, 1, 1), "smithing_table": (2, 1, 1),
                                "blast_furnace": (4, 1, 1), "furnace": (3, 1, 1), "chest_w": (1, 1, 3),
                                "barrel_w": (1, 1, 4), "barrel_e": (7, 1, 4), "chest_e": (7, 1, 5)},
                   views={"01_front": (4.5, 3, 20.5, 180, 4), "02_back": (4.5, 3, -12.5, 0, 6),
                          "03_west": (-12.5, 3, 4.5, -90, 4), "04_east": (21.5, 3, 4.5, 90, 4),
                          "05_diag_se": (16.5, 5, 18.5, 135, 8), "06_diag_nw": (-8.5, 5, -10.5, -45, 8),
                          "07_interior_forge": (4.5, 0, 7.0, 180, 12),
                          "08_interior_side": (6.5, 0, 7.0, 125, 18)}),
    "cart_shed": dict(module="M-cart_shed", design=cart_shed, door=(3, 6), size=(8, 9, 7),
                      interactive={"chest_a": (1, 1, 1), "chest_b": (2, 1, 1), "grindstone": (3, 1, 1),
                                   "barrel_a": (6, 1, 1)},
                      views={"01_front": (3.5, 3, 18.5, 180, 4), "02_back": (3.5, 3, -12.5, 0, 6),
                             "03_west": (-12.5, 3, 3.5, -90, 4), "04_east": (19.5, 3, 3.5, 90, 4),
                             "05_diag_se": (14.5, 5, 16.5, 135, 8), "06_diag_nw": (-8.5, 5, -9.5, -45, 8),
                             "07_interior_cart": (3.5, 0, 9.5, 180, 10),
                             "08_interior_storage": (6.5, 0, 4.5, 128, 15)}),
}


def main():
    mods = A.modules()
    (ROOT / "out").mkdir(exist_ok=True)
    for key, b in BUILDINGS.items():
        module = mods[b["module"]]
        assert module["size"] == list(b["size"]) and module["air"] == "include", (key, module)
        cells = b["design"]()
        assert (cells.W, cells.H, cells.D) == tuple(b["size"])
        with tempfile.TemporaryDirectory() as d:
            result = export_module(module, dict(cells), Path(d) / "pack")
            shutil.copyfile(result.config.nbt_path, ROOT / "out" / f"{module['file']}.nbt")
            shutil.copyfile(result.config.source, ROOT / "out" / f"{module['file']}.schem")
            (ROOT / "out" / f"{module['file']}.export-report.json").write_text(
                json.dumps(result.report, indent=2, sort_keys=True) + "\n"
            )
        print(f"{module['file']}.nbt: {len(cells)} authored cells, size {module['size']}")


if __name__ == "__main__":
    main()
