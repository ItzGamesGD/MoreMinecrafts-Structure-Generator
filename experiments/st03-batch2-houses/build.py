"""ST-03 facility batch 2 (living group): houses B, C and D (F12/F15, F13/F16, F17).

Contract kept (tools/seam01/data/st03_placements.json, untouched): M-house_b 9x10x7, M-house_c 7x9x7, M-house_d 7x9x7
(x, y, z), air=include, floor y=0, local_turns 0 for all five placements. Front (door side) is the module's +z face.
House A (experiment/st03-b5a-house-a-formal) and F18-F20 (batch 1) are not touched.

Owner decisions applied (Beta docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md, Q01-Q10):
  Q01 one architectural family, distinct detail      Q02 B regular gable / C asymmetric gable / D small hip roof
  Q03 B covered porch inside bounds / C recessed door / D stone-framed defensive doorway
  Q04 B timber on cobble base / C timber with partial stone / D stone lower + timber upper
  Q05 B larger shuttered windows / C 2-3 small asymmetric windows / D narrow barred windows; lanterns
  Q06 B two-bed communal / C one bed + shelves / D one guard bed + weapon decor; one passable story
  Q07 orderly lived-in exterior decoration           Q09 level floor, stone footing, no global levelling
Conservative choices where the ledger is silent: single-block shutters, no chimney, empty containers (loot is a
runtime decision), no cosmetic crates, all doors on the +z face.

  PYTHONPATH=. python experiments/st03-batch2-houses/build.py
"""

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

from tools.seam01 import assembly as A
from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "batch1_build", ROOT.parent / "st03-batch1-support" / "build.py"
)
B1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B1)
Cells, stone, roof = B1.Cells, B1.stone, B1.roof


def cobble(x, z):
    return "mossy_cobblestone" if (x * 5 + z * 3) % 7 == 0 else "cobblestone"


# ---------------------------------------------------------------------------------------------- house B
def house_b():
    c = Cells((9, 10, 7))
    W, D = 9, 7
    for x in range(W):
        for z in range(D):
            if z == 6:
                c.put(x, 0, z, "stone_bricks" if 2 <= x <= 6 else cobble(x, z))
            elif x in (0, W - 1) or z in (0, 5):
                c.put(x, 0, z, cobble(x, z))
            else:
                c.put(x, 0, z, "spruce_planks")
    # walls: body z=0..5 (front wall at z=5, porch z=6 under the roof). Cobble base, spruce timber, plate y=4
    for x in range(W):
        for z in range(6):
            if x not in (0, W - 1) and z not in (0, 5):
                continue
            corner = x in (0, W - 1) and z in (0, 5)
            c.put(x, 1, z, "dark_oak_log" if corner else cobble(x, z), **({"axis": "y"} if corner else {}))
            for y in (2, 3):
                c.put(x, y, z, "dark_oak_log" if corner else "spruce_planks", **({"axis": "y"} if corner else {}))
            c.put(x, 4, z, "dark_oak_log" if corner else "stripped_dark_oak_log",
                  **({"axis": "y"} if corner else {"axis": "z" if x in (0, W - 1) else "x"}))
    # mid timber posts
    for y in (2, 3):
        c.put(0, y, 3, "dark_oak_log", axis="y"); c.put(8, y, 3, "dark_oak_log", axis="y")
    # larger windows (2x2 panes) on both side walls, single-block shutters beside them
    for x, face in ((0, "east"), (8, "west")):
        for y in (2, 3):
            c.put(x, y, 2, "glass_pane")
            c.put(x, y, 4, "glass_pane")
            c.put(x, y, 1, "spruce_trapdoor", facing=face, half="bottom", open=True)
        c.pop((x, 2, 3), None); c.pop((x, 3, 3), None)
        for y in (2, 3):
            c.put(x, y, 3, "glass_pane")
    # front: door at (4, 1..2, 5), windows with shutters beside it
    for y in (1, 2, 3):
        c.put(3, y, 5, "dark_oak_log", axis="y"); c.put(5, y, 5, "dark_oak_log", axis="y")
    c.put(4, 3, 5, "stripped_dark_oak_log", axis="x")
    c.put(4, 1, 5, "spruce_door", facing="south", half="lower", hinge="left", open=False, powered=False)
    c.put(4, 2, 5, "spruce_door", facing="south", half="upper", hinge="left", open=False, powered=False)
    for x in (2, 6):
        for y in (2, 3):
            c.put(x, y, 5, "glass_pane")
    for x in (1, 7):
        for y in (2, 3):
            c.put(x, y, 5, "spruce_trapdoor", facing="north", half="bottom", open=True)
    # back wall window
    for y in (2, 3):
        c.put(4, y, 0, "glass_pane")
    # roof: regular gable along z, spruce shingles, dark-oak barge, ridge x=4
    ry = roof(c, 5, "spruce_stairs", "dark_oak_stairs", "spruce_planks")
    for zg in (1, 5):
        for x in range(1, W - 1):
            c.put(x, 4, zg, "stripped_dark_oak_log", axis="x")
        for y in range(5, 9):
            for x in range(1, W - 1):
                if ry[x] > y:
                    c.put(x, y, zg, "dark_oak_log" if x == 4 else "spruce_planks", **({"axis": "y"} if x == 4 else {}))
    # covered porch: posts, beam, lanterns, banner
    for x in (2, 6):
        for y in (1, 2, 3):
            c.put(x, y, 6, "dark_oak_log", axis="y")
    for x in range(2, 7):
        c.put(x, 4, 6, "stripped_dark_oak_log", axis="x")
    for x in (3, 5):
        c.put(x, 3, 6, "lantern", hanging=True)
    c.put(4, 3, 6, "white_wall_banner", facing="south")
    # interior: two-bed communal room, table, workstations, storage (containers empty)
    c.put(1, 1, 1, "red_bed", facing="east", occupied=False, part="foot")
    c.put(2, 1, 1, "red_bed", facing="east", occupied=False, part="head")
    c.put(7, 1, 1, "red_bed", facing="west", occupied=False, part="foot")
    c.put(6, 1, 1, "red_bed", facing="west", occupied=False, part="head")
    c.put(4, 1, 1, "chest", facing="south", type="single")
    c.put(4, 1, 3, "spruce_fence", north=False, east=False, south=False, west=False)
    c.put(4, 2, 3, "spruce_pressure_plate", powered=False)
    c.put(1, 1, 4, "crafting_table")
    c.put(2, 1, 4, "furnace", facing="north", lit=False)
    c.put(7, 1, 4, "barrel", facing="north", open=False)
    c.put(7, 1, 3, "barrel", facing="west", open=False)
    for x in (3, 4, 5):
        c.put(x, 1, 2, "gray_carpet")
    c.put(4, 3, 3, "lantern", hanging=True)
    c.pop((4, 4, 3), None)
    for x in range(1, W - 1):
        c.put(x, 4, 3, "stripped_spruce_log", axis="x")
    c.put(4, 4, 3, "stripped_spruce_log", axis="x")
    return c


# ---------------------------------------------------------------------------------------------- house C
def house_c():
    c = Cells((7, 9, 7))
    W, D = 7, 7
    for x in range(W):
        for z in range(D):
            c.put(x, 0, z, "cobblestone" if x in (0, W - 1) or z in (0, 5, 6) else "spruce_planks")
    c.put(3, 0, 6, "stone_bricks"); c.put(2, 0, 6, "cobblestone"); c.put(4, 0, 6, "cobblestone")
    # body z=0..5; piers at z=6 (x 0..1, 5..6) frame a recessed door (door plane z=5)
    for x in range(W):
        for z in range(6):
            if x not in (0, W - 1) and z not in (0, 5):
                continue
            corner = x in (0, W - 1) and z in (0, 5)
            west_stone = x == 0 and z <= 2  # partial stone: west wall back half
            c.put(x, 1, z, "dark_oak_log" if corner else stone(x, 1, z), **({"axis": "y"} if corner else {}))
            for y in (2, 3):
                if corner:
                    c.put(x, y, z, "dark_oak_log", axis="y")
                else:
                    c.put(x, y, z, stone(x, y, z) if west_stone else "spruce_planks")
            c.put(x, 4, z, "dark_oak_log" if corner else "stripped_dark_oak_log",
                  **({"axis": "y"} if corner else {"axis": "z" if x in (0, W - 1) else "x"}))
    for x in (0, 1, 5, 6):  # piers of the recess
        for y in (1, 2):
            c.put(x, y, 6, stone(x, y, 6))
        c.put(x, 3, 6, "spruce_planks"); c.put(x, 4, 6, "stripped_dark_oak_log", axis="x")
    for x in (2, 3, 4):
        c.put(x, 4, 6, "stripped_dark_oak_log", axis="x")
    # recessed door at z=5
    for y in (1, 2, 3):
        c.put(2, y, 5, "dark_oak_log", axis="y"); c.put(4, y, 5, "dark_oak_log", axis="y")
    c.put(3, 3, 5, "stripped_dark_oak_log", axis="x")
    c.put(3, 1, 5, "spruce_door", facing="south", half="lower", hinge="left", open=False, powered=False)
    c.put(3, 2, 5, "spruce_door", facing="south", half="upper", hinge="left", open=False, powered=False)
    c.put(3, 3, 6, "lantern", hanging=True)
    # 3 small asymmetric windows
    c.put(0, 2, 2, "glass_pane"); c.put(6, 3, 3, "glass_pane"); c.put(2, 3, 0, "glass_pane")
    # asymmetric gable: ridge x=2; left steep, right long low slope ending in a slab ledge
    ry = {0: 5, 1: 6, 2: 7, 3: 6, 4: 5, 5: 5, 6: 5}
    for z in range(D):
        end = z in (0, 6)
        stairs = "dark_oak_stairs" if end else "spruce_stairs"
        c.put(0, 5, z, stairs, facing="east", half="bottom", shape="straight")
        c.put(1, 6, z, stairs, facing="east", half="bottom", shape="straight")
        c.put(2, 7, z, "dark_oak_log" if end else "spruce_planks", **({"axis": "z"} if end else {}))
        c.put(3, 6, z, stairs, facing="west", half="bottom", shape="straight")
        c.put(4, 5, z, stairs, facing="west", half="bottom", shape="straight")
        c.put(5, 5, z, "dark_oak_slab" if end else "spruce_slab", type="bottom")
        c.put(6, 5, z, "dark_oak_slab" if end else "spruce_slab", type="bottom")
    for zg in (1, 5):
        for x in range(1, 5):
            c.put(x, 4, zg, "stripped_dark_oak_log", axis="x")
            for y in range(5, 7):
                if ry[x] > y:
                    c.put(x, y, zg, "spruce_planks")
    # interior: one bed, shelves, storage (empty containers)
    c.put(1, 1, 1, "red_bed", facing="east", occupied=False, part="foot")
    c.put(2, 1, 1, "red_bed", facing="east", occupied=False, part="head")
    for y in (1, 2):
        c.put(5, y, 1, "bookshelf")
    c.put(5, 1, 2, "bookshelf")
    c.put(5, 1, 3, "chest", facing="west", type="single")
    c.put(1, 1, 4, "barrel", facing="east", open=False)
    c.put(3, 1, 2, "gray_carpet")
    c.put(3, 4, 3, "lantern", hanging=True)
    for x in range(1, 6):
        c.put(x, 4, 3, "stripped_spruce_log", axis="x")
    return c


# ---------------------------------------------------------------------------------------------- house D
def house_d():
    c = Cells((7, 9, 7))
    W, D = 7, 7
    for x in range(W):
        for z in range(D):
            edge = x in (0, W - 1) or z in (0, D - 1)
            c.put(x, 0, z, stone(x, 0, z) if edge else "dark_oak_planks")
    c.put(3, 0, 6, "stone_bricks")
    for x in range(W):
        for z in range(D):
            if x not in (0, W - 1) and z not in (0, D - 1):
                continue
            corner = x in (0, W - 1) and z in (0, D - 1)
            for y in (1, 2):
                c.put(x, y, z, "stone_bricks" if corner else stone(x, y, z))
            for y in (3,):
                c.put(x, y, z, "dark_oak_log" if corner else "spruce_planks", **({"axis": "y"} if corner else {}))
            c.put(x, 4, z, "dark_oak_log" if corner else "stripped_dark_oak_log",
                  **({"axis": "y"} if corner else {"axis": "z" if x in (0, W - 1) else "x"}))
    # stone-framed defensive doorway
    for y in (1, 2, 3):
        c.put(2, y, 6, "stone_bricks"); c.put(4, y, 6, "stone_bricks")
    c.put(3, 3, 6, "stone_bricks")
    c.put(3, 1, 6, "dark_oak_door", facing="south", half="lower", hinge="left", open=False, powered=False)
    c.put(3, 2, 6, "dark_oak_door", facing="south", half="upper", hinge="left", open=False, powered=False)
    # narrow barred windows
    for x, z in ((0, 2), (0, 4), (6, 2), (6, 4), (3, 0), (1, 6), (5, 6)):
        c.put(x, 3, z, "iron_bars")
    # small hip roof (spruce), 7x7 rings, lantern finial
    def ring(y, lo, hi):
        for x in range(lo, hi + 1):
            for z in range(lo, hi + 1):
                if lo < x < hi and lo < z < hi:
                    continue
                n, s, w_, e = z == lo, z == hi, x == lo, x == hi
                if (n or s) and (w_ or e):
                    if s:
                        facing, shape = "north", "outer_left" if w_ else "outer_right"
                    else:
                        facing, shape = "south", "outer_left" if e else "outer_right"
                elif s:
                    facing, shape = "north", "straight"
                elif n:
                    facing, shape = "south", "straight"
                elif w_:
                    facing, shape = "east", "straight"
                else:
                    facing, shape = "west", "straight"
                c.put(x, y, z, "spruce_stairs", facing=facing, half="bottom", shape=shape)
    ring(5, 0, 6); ring(6, 1, 5); ring(7, 2, 4)
    c.put(3, 7, 3, "spruce_planks")
    c.put(3, 8, 3, "lantern", hanging=False)
    # interior: one guard bed, weapon decor, storage
    c.put(1, 1, 1, "red_bed", facing="east", occupied=False, part="foot")
    c.put(2, 1, 1, "red_bed", facing="east", occupied=False, part="head")
    c.put(5, 1, 1, "grindstone", face="floor", facing="south")
    c.put(5, 1, 2, "fletching_table")
    c.put(1, 1, 4, "chest", facing="east", type="single")
    c.put(1, 1, 5, "barrel", facing="east", open=False)
    c.put(3, 3, 1, "white_wall_banner", facing="south")
    c.put(5, 3, 1, "wall_torch", facing="south")
    c.put(5, 3, 5, "wall_torch", facing="north")
    c.put(2, 1, 5, "gray_carpet"); c.put(3, 1, 5, "gray_carpet"); c.put(4, 1, 5, "gray_carpet")
    return c


def _views(w, d, tall=3, ia=None, ib=None):
    cx, cz = w / 2, d / 2
    return {
        "01_front": (cx, tall, d + 11.5, 180, 4),
        "02_back": (cx, tall, -11.5, 0, 6),
        "03_west": (-11.5, tall, cz, -90, 4),
        "04_east": (w + 11.5, tall, cz, 90, 4),
        "05_diag_se": (w + 7.5, 5, d + 9.5, 135, 8),
        "06_diag_nw": (-7.5, 5, -8.5, -45, 8),
        "07_interior_a": ia or (cx, 0, d - 1.4, 180, 14),
        "08_interior_b": ib or (w - 1.5, 0, d - 1.5, 140, 18),
    }


BUILDINGS = {
    "house_b": dict(module="M-house_b", design=house_b, door=(4, 6), size=(9, 10, 7),
                    interactive={"bed_w": (2, 1, 1), "bed_e": (6, 1, 1), "chest": (4, 1, 1), "crafting_table": (1, 1, 4),
                                 "furnace": (2, 1, 4), "barrel_n": (7, 1, 4), "barrel_w": (7, 1, 3)},
                    views=_views(9, 7, ia=(4.5, 0, 4.4, 180, 14), ib=(6.5, 0, 4.4, 150, 18))),
    "house_c": dict(module="M-house_c", design=house_c, door=(3, 6), size=(7, 9, 7),
                    interactive={"bed": (2, 1, 1), "chest": (5, 1, 3), "barrel": (1, 1, 4)},
                    views=_views(7, 7, ia=(3.5, 0, 4.4, 180, 14), ib=(5.5, 0, 4.4, 135, 18))),
    "house_d": dict(module="M-house_d", design=house_d, door=(3, 6), size=(7, 9, 7),
                    interactive={"bed": (2, 1, 1), "grindstone": (5, 1, 1), "fletching_table": (5, 1, 2),
                                 "chest": (1, 1, 4), "barrel": (1, 1, 5)},
                    views=_views(7, 7)),
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
