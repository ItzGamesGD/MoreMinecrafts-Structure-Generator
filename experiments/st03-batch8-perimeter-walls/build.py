"""ST-03 batch 8: perimeter wall modules MW86 (86x13x5, st03_wall_86) and MW31 (31x13x5, st03_wall_31).

Contract kept (tools/seam01/data/st03_placements.json, untouched): sizes above (x, y, z), air=omit, y=0 at grade.
  MW86 -> W-N  x=13..98,  z=0..4     local_turns 0
          W-E  x=107..111, z=13..98  local_turns 1
          W-W  x=0..4,    z=13..98   local_turns 3
  MW31 -> W-SW x=13..43,  z=107..111 local_turns 2  (local x=0 at the gate, x=30 at T-SW)
          W-SE x=68..98,  z=107..111 local_turns 2  (local x=0 at T-SE, x=30 at the gate)
Every turn maps the local -z face onto the outside of the 112x112 box, so local z=0 is ALWAYS the exterior face and
z=4 the compound side. Both ends of both modules abut a reserved tower (T-*, 13x13) or the gatehouse (GATE x=44..67):
the ends are therefore treated identically (MW31 is used once with its x=0 end at the gate, once at a tower).

Design source: owner ledger (Beta repo, docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md)
  Q81 A  no continuous wall-top patrol route is required (the towers are reached independently)
  Q82 B  stone crenellations and arrow openings, military decoration, lanterns, banners, timber details,
         no shooting mechanic; owner stone principle: stone / andesite / cobblestone / stone bricks / cracked and
         mossy variants mixed naturally, no fixed ratio, coherent structural edges, contextual weathering
  Q89 B  partly projecting masonry footing adapting to the slope; ground-to-wall gaps filled with supporting masonry,
         wall top elevation and coordinates unchanged, no global flattening (the per-column fill below y=0 is a
         placement step: test terrain only, see checks.py; natural worldgen hookup is not part of this batch)
  Q90 B  irregular illager banners; lanterns and timber reinforcement concentrated near the gate / towers (= both ends
         of every module), restrained in between; occasional wood piles, barrels and crates at the wall base; moss
         at the terrain transition. Decorative only.

Section (local z: 0 exterior .. 4 compound side), y = height above grade:
  y0      footing course, full depth z0..4 (rough cobble / andesite / mossy mix) - projects 1 on both sides
  y1      battered plinth: stairs leaning on the wall at z0 (exterior) and z4 (inside)
  y1..8   curtain z1..3 (3 thick), exterior face z1 set back behind the plinth and the parapet
  y8      corbel table at z0 (upside-down stairs) carrying the projecting parapet
  y9      parapet sill at z0, inner lip at z3 (the z1..2 channel between them is open)
  y10..11 merlons (2 wide) and crenels (1 wide) at z0; y12 merlon caps -> constant 13-high silhouette
  pilaster buttresses tie the plinth to the parapet at fixed, symmetric positions; through-wall arrow slits at y4..5
  end zones (9 blocks at each end): dark-oak timber beam instead of the corbels, timber brackets, hanging lantern,
  banner; inside: a dark-oak beam on three brackets under the inner lip, hanging lantern, banner, barrel and log pile.

All containers empty (block-entity allow-list). No mobs, spawners, loot or mechanics authored.

  PYTHONPATH=. python experiments/st03-batch8-perimeter-walls/build.py
"""

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

from tools.seam01 import assembly as A
from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B4 = _load("batch4_build", ROOT.parent / "st03-batch4-barracks" / "build.py")
Cells, noise, stairs = B4.Cells, B4.noise, B4.stairs

H, D = 13, 5
END = 9  # length of the decorated end zone at each end (tower / gate joints)
SILL, CAP = 9, 12


def foot(x, y, z):
    """Rough footing / fill masonry (also used for the below-grade fill on slopes)."""
    return ["cobblestone", "mossy_cobblestone", "andesite", "cobblestone", "stone_bricks", "mossy_stone_bricks",
            "cobblestone", "andesite", "stone", "cobblestone"][noise(x, z, 10, y + 31)]


def face(x, y, z, L):
    """Curtain masonry. Weathering comes in staggered patches (not per-block speckle): mossy low down and near the
    ends, cracked anywhere, cobble / andesite repairs low on the wall; the ends and the top course stay clean."""
    if x in (0, L - 1) or y == 8:
        return "cracked_stone_bricks" if noise(x, z, 13, y + 3) == 0 else "stone_bricks"
    patch = noise((x + 2 * (y // 3)) // 4, y // 3, 9, 41 + z)
    hit = noise(x, y, 3, 17 + z) != 0
    if patch == 0 and hit:
        return "cracked_stone_bricks"
    if patch == 1 and hit and (y <= 5 or min(x, L - 1 - x) < END):
        return "mossy_stone_bricks"
    if patch == 2 and hit and y <= 5:
        return ("cobblestone", "andesite", "mossy_cobblestone")[noise(x, y, 3, 5)]
    if patch == 3 and noise(x, y, 4, 9) == 0:
        return "andesite" if y <= 5 else "cracked_stone_bricks"
    return "stone_bricks"


def merlon(x, L):
    """Crenel columns: MW86 every 3rd from x=2 (2-wide merlons, symmetric ends); MW31 every 3rd from x=3 (3-wide end
    merlons as end piers). Both patterns are symmetric about the middle of the module."""
    if L == 86:
        return not (x % 3 == 2 and 2 <= x <= 83)
    return not (x % 3 == 0 and 3 <= x <= 27)


def buttresses(L):
    """x of the 2-wide (MW31: 3-wide) pilaster buttresses, symmetric, plus the 1-wide end piers."""
    inner = [12, 13, 26, 27, 42, 43, 58, 59, 72, 73] if L == 86 else [14, 15, 16]
    return [0, *inner, L - 1]  # the two end columns are piers too (clean edge toward the tower / gate)


def slits(L):
    """Through-wall arrow slits (y4..5), placed clear of banners, lanterns and posts."""
    return [21, 36, 49, 68] if L == 86 else [12, 18]


def wall(L):
    c = Cells((L, H, D))
    butt = set(buttresses(L))
    slit = set(slits(L))
    for x in range(L):
        for z in range(D):
            c.put(x, 0, z, foot(x, 0, z))
        # curtain z1..3, y1..8
        for y in range(1, 9):
            for z in (1, 2, 3):
                if z == 2 and x not in (0, L - 1):
                    c.put(x, y, z, "cobblestone")  # hidden core
                else:
                    c.put(x, y, z, face(x, y, z, L))
        if x in slit:
            for y in (4, 5):
                for z in (1, 2, 3):
                    del c[(x, y, z)]
        # exterior plinth / buttress
        if x in butt:
            for y in range(1, 8):
                c.put(x, y, 0, face(x, y, 0, L) if y > 2 else foot(x, y, 0))
            c.put(x, 8, 0, "stone_bricks")
        else:
            m = ("stone_brick", "cobblestone", "mossy_cobblestone", "stone_brick", "mossy_stone_brick")[noise(x, 1, 5, 2)]
            stairs(c, x, 1, 0, m, "south")
            cm = "mossy_stone_brick" if noise(x, 8, 7, 3) == 0 else "stone_brick"
            stairs(c, x, 8, 0, cm, "south", half="top")  # corbel table
        # interior plinth / buttress
        if x in butt:
            for y in range(1, 6):
                c.put(x, y, 4, face(x, y, 4, L) if y > 2 else foot(x, y, 4))
            stairs(c, x, 6, 4, "stone_brick", "north")
        else:
            m = ("cobblestone", "stone_brick", "andesite", "cobblestone", "mossy_cobblestone")[noise(x, 1, 5, 8)]
            stairs(c, x, 1, 4, m, "north")
        # parapet: sill, inner lip, merlons and caps
        c.put(x, SILL, 0, face(x, SILL, 0, L))
        c.put(x, SILL, 3, "stone_bricks" if noise(x, 3, 11, 1) else "cracked_stone_bricks")
        if merlon(x, L):
            for y in (10, 11, CAP):
                c.put(x, y, 0, face(x, y, 0, L) if y < CAP else "stone_bricks")
    for side in (0, 1):
        end_zone(c, L, side)
    middle(c, L)
    return c


def end_zone(c, L, side):
    """Decorated joint toward a tower or the gate. side 0: x=0 end, side 1: x=L-1 end (mirrored)."""
    X = (lambda i: i) if side == 0 else (lambda i: L - 1 - i)
    # exterior: dark-oak beam in place of the corbels, timber brackets, hanging lantern, banner
    for i in range(1, 8):
        c.put(X(i), 8, 0, "dark_oak_log", axis="x")
    for i in (1, 7):
        stairs(c, X(i), 7, 0, "dark_oak", "south", half="top")
    c.put(X(4), 7, 0, "lantern", hanging=True, waterlogged=False)
    c.put(X(10), 6, 0, "white_wall_banner", facing="north")
    # inside: a timber beam on dark-oak brackets along the top of the curtain (no full-height posts, so it does not
    # read as a doorway), hanging lantern, banner, base stores
    for i in range(1, 8):
        c.put(X(i), 8, 4, "dark_oak_log", axis="x")
    for i in (1, 4, 7):
        stairs(c, X(i), 7, 4, "dark_oak", "north", half="top")
    c.put(X(2), 7, 4, "lantern", hanging=True, waterlogged=False)
    c.put(X(10), 6, 4, "white_wall_banner", facing="south")
    c.put(X(3), 1, 4, "barrel", facing="up", open=False)
    for i in (5, 6):
        c.put(X(i), 1, 4, "spruce_log", axis="x")
    c.put(X(5), 2, 4, "spruce_log", axis="x")
    c.put(X(4), 1, 4, "moss_carpet")
    # exterior base: a barrel at one end, a log pile at the other (irregular)
    if side == 0:
        c.put(X(3), 1, 0, "barrel", facing="up", open=False)
        c.put(X(5), 1, 0, "barrel", facing="up", open=False)
    else:
        for i in (3, 4, 5):
            c.put(X(i), 1, 0, "spruce_log", axis="x")
        c.put(X(4), 2, 0, "spruce_log", axis="x")


def middle(c, L):
    """Restrained decoration between the end zones (Q90): a few irregular banners, two lanterns, moss, one crate."""
    if L == 86:
        for x in (19, 64):
            c.put(x, 6, 0, "white_wall_banner", facing="north")
        c.put(47, 6, 4, "white_wall_banner", facing="south")
        for x in (33, 52):
            c.put(x, 8, 0, "stone_bricks")  # full corbel so the lantern has a solid block to hang from
            c.put(x, 7, 0, "lantern", hanging=True, waterlogged=False)
        for x in (22, 39, 61):
            c.put(x, 1, 4, "moss_carpet")
        for x in (17, 30, 70):
            c.put(x, 1, 0, "moss_carpet")
        c.put(55, 1, 4, "barrel", facing="up", open=False)
    else:
        c.put(12, 1, 4, "moss_carpet")
        c.put(18, 1, 0, "moss_carpet")


def mw86():
    return wall(86)


def mw31():
    return wall(31)


BUILDINGS = {
    "wall_86": dict(module="MW86", placements=("W-N", "W-E", "W-W"), design=mw86, size=(86, H, D), door=None),
    "wall_31": dict(module="MW31", placements=("W-SW", "W-SE"), design=mw31, size=(31, H, D), door=None),
}


def main():
    mods = A.modules()
    (ROOT / "out").mkdir(exist_ok=True)
    for key, b in BUILDINGS.items():
        module = mods[b["module"]]
        assert module["size"] == list(b["size"]) and module["air"] == "omit", (key, module)
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
