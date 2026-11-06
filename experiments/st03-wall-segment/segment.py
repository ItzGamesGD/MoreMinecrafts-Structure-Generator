"""ST-03 perimeter wall: representative segment (new design study, not a full wall).

  PYTHONPATH=. python experiments/st03-wall-segment/segment.py      -> out/st03_wall_segment.nbt (+ run of 5)

Section fixed by the existing wall contract (MW86 / MW31): 13 high (y0 at grade, top y12), 5 deep, local z=0 the
exterior face, z=4 the compound side, air omitted, a full footing course at y0.

Segment: 15 long = buttress (3) + bay (9) + buttress (3). Repeats share a buttress, so the repeat period is 12. The
design is "a corbelled gallery wall":
- outside, three depths:
  - z0: buttresses and the foot of the talus;
  - z1: the upper talus step, the buttresses' upper stage and the gallery brackets;
  - z2: the curtain;
- buttresses: set back by a sloped weathering at mid height, then carried up on a corbel into a head that stands one
  course above the battlement;
- the parapet is corbelled out two stages over the curtain. In the shadow under it, a gallery of brackets carries
  it: stone corbels at the ends and the centre, dark-oak joists on dark-oak brackets between them. The slots between
  the brackets are machicolations closed by spruce hatches. The timber is set back inside the stone line and does
  the work of carrying the parapet;
- a cross-shaped crossbow loop in the curtain;
- inside, stone pilasters answer the buttresses. Between them two Y-shaped dark-oak posts and a beam carry a plank
  widening of the wall-walk behind a fence.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "experiments" / "st03-wall-redesign")]

from common import Cells, ashlar, ashlar_stair, banner, lantern, log, noise, rubble, rubble_stair, stairs, trap  # noqa: E402

H, D = 13, 5
BUTTRESS, BAY = 3, 9
L = BUTTRESS + BAY + BUTTRESS  # 15
PERIOD = BUTTRESS + BAY  # 12


def edge(x, y, z):
    """Buttress / parapet masonry: clean stone brick, sparse cracked blocks, mossy only near the ground."""
    n = noise(x, y, 13, 7 + z)
    if n == 0:
        return "cracked_stone_bricks"
    if n == 1 and y <= 2:
        return "mossy_stone_bricks"
    return "stone_bricks"


def curtain(x, y, z):
    """Curtain face: dressed stone brick with patches of older rubble repair (andesite / stone / cobble)."""
    patch = noise((x + y // 2) // 3, y // 2, 7, 19 + z)
    if patch == 0 and y <= 6:
        return ("andesite", "stone", "cobblestone")[noise(x, y, 3, 5)]
    return ashlar(x, y, z)


def buttress(c, a):
    b = a + BUTTRESS - 1
    m = a + 1
    for x in range(a, b + 1):
        for z in (0, 1):
            for y in range(1, 6):
                c.put(x, y, z, edge(x, y, z))
        stairs(c, x, 6, 0, "stone_brick", "south")  # weathering of the lower stage
        for y in range(6, 10):
            c.put(x, y, 1, edge(x, y, 1))
        stairs(c, x, 9, 0, "stone_brick", "south", half="top")  # corbel under the head
        for z in (0, 1):
            for y in (10, 11):
                c.put(x, y, z, edge(x, y, z))
            if x == m:
                c.put(x, 12, z, "stone_bricks")
            else:
                stairs(c, x, 12, z, "stone_brick", "east" if x < m else "west")  # pitched cap of the head
        # inside pilaster and wall-walk rail
        for y in range(1, 9):
            c.put(x, y, 4, edge(x, y, 4))
        c.put(x, 9, 4, "stone_bricks")
        c.put(x, 10, 4, "stone_brick_wall")


def bay(c, a):
    b = a + BAY - 1
    m = a + BAY // 2
    stone_brackets = {a, m, b}
    timber_brackets = {a + 2, b - 2}
    for x in range(a, b + 1):
        # two-step talus
        c.put(x, 1, 0, rubble(x, 1, 0))
        stairs(c, x, 2, 0, rubble_stair(x, 2, 0), "south")
        for y in (1, 2, 3):
            c.put(x, y, 1, rubble(x, y, 1) if y <= 2 else ashlar(x, y, 1))
        stairs(c, x, 4, 1, ashlar_stair(x, 4, 1), "south")
        # gallery under the corbelled parapet (z1, y8..9)
        if x in stone_brackets:
            stairs(c, x, 8, 1, "stone_brick", "south", half="top")
            c.put(x, 9, 1, "stone_bricks")
        elif x in timber_brackets:
            stairs(c, x, 8, 1, "dark_oak", "south", half="top")
            log(c, x, 9, 1, "z")  # joist, its end grain under the parapet
        else:
            trap(c, x, 9, 1, "spruce", "north", False, half="top")  # machicolation hatch
        # parapet corbelled out to z0
        stairs(c, x, 9, 0, "stone_brick", "south", half="top")
        c.put(x, 10, 0, edge(x, 10, 0))
        if (x - a) % 4:
            c.put(x, 11, 0, edge(x, 11, 0))  # 3-wide merlons; crenels over the bay ends and the loop
        # inside: beam, plank widening, fence
        log(c, x, 8, 4, "x")
        c.put(x, 9, 4, "spruce_planks")
        c.put(x, 10, 4, "dark_oak_fence")
    # cross loop: a cross in the face (z2), only its centre goes through the core (z3) - not a passage
    for x, y in ((m, 5), (m, 6), (m, 7), (m - 1, 6), (m + 1, 6)):
        del c[(x, y, 2)]
    del c[(m, 6, 3)]
    # inside: two Y-shaped dark-oak posts on stone pads, clear of the loop
    for p in (a + 2, b - 2):
        c.put(p, 1, 4, "stone_bricks")
        for y in range(2, 8):
            log(c, p, y, 4, "y")
        stairs(c, p - 1, 7, 4, "dark_oak", "east", half="top")
        stairs(c, p + 1, 7, 4, "dark_oak", "west", half="top")
    lantern(c, m, 7, 4)


def segment(n=1):
    """n bays: buttress, (bay, buttress) * n. n=1 is the representative segment; n>1 shows repetition."""
    length = BUTTRESS + PERIOD * n
    c = Cells((length, H, D))
    for x in range(length):
        for z in range(D):
            c.put(x, 0, z, rubble(x, 0, z))
        for y in range(1, 9):
            for z in (2, 3):
                c.put(x, y, z, rubble(x, y, z) if y <= 2 else curtain(x, y, z))
        for z in (2, 3):
            c.put(x, 9, z, "stone_bricks")
        stairs(c, x, 1, 4, rubble_stair(x, 1, 4), "north")
    for i in range(n + 1):
        buttress(c, PERIOD * i)
    for i in range(n):
        bay(c, PERIOD * i + BUTTRESS)
    banner(c, BUTTRESS, 5, 0, "east")  # one banner on the first buttress flank
    return c


def export(cells, name, outdir):
    from tools.seam01.export import export_module
    module = {"id": name, "file": name, "size": [cells.W, cells.H, cells.D], "air": "omit"}
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        result = export_module(module, dict(cells), Path(d) / "pack")
        shutil.copyfile(result.config.nbt_path, outdir / f"{name}.nbt")
        shutil.copyfile(result.config.source, outdir / f"{name}.schem")
        (outdir / f"{name}.export-report.json").write_text(json.dumps(result.report, indent=2, sort_keys=True) + "\n")
    print(f"{name}.nbt: {len(cells)} cells, size {[cells.W, cells.H, cells.D]}")


def main():
    export(segment(1), "st03_wall_segment", HERE / "out")
    export(segment(5), "st03_wall_segment_run5", HERE / "out")


if __name__ == "__main__":
    main()
