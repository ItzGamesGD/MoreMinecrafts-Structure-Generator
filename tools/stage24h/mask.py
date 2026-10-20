"""Stage 24-H interior clearance masks for the eight approved modules.

Every cell of a template is put in exactly one class (see MASK.md for the rules):

  stored_architecture   the template stores a block here (incl. stored air, water, jigsaws)   never cleared
  room_interior         enclosed walkable column under a ceiling, floor -> ceiling, then spread sideways
                        within the same layer over furniture/corners of the enclosed, roofed room  CLEARED
  walkway               enclosed walkable cell open to the sky: body + one jump-headroom cell  CLEARED
  paved_walkway         walkable cell on the module's own stored floor outside any enclosure: body height only  CLEARED
  step_headroom         the cell above a walkable cell from which the walk climbs a step       CLEARED
  interaction_space     the cell above a chest (cannot open under a solid block) or a bed half (cannot sleep)  CLEARED
  pool_headroom         the two cells above stored water inside an enclosed space              CLEARED
  decorative_void       unstored cell inside the walls that nobody walks in (roof voids, cavities)  kept
  exterior              unstored cell reachable from the box boundary without passing a wall or a door  kept

"Enclosed" is decided per horizontal layer: flood from the box boundary through cells that store nothing or store a
passable non-door block (air, water, ladder, ...). Doors and every other stored block stop the flood; anything the
flood does not reach in that layer is inside the building.  Walkable cells come from the Stage 24-G reachability walk
(tools/stage24g/roles.py), so stairs, ladders and upper floors are included where a player can actually go.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, ROOT  # noqa: E402
from tools.stage24g.roles import Template, reachable, stand, ladder, short  # noqa: E402

D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
CLEARED = ("room_interior", "walkway", "paved_walkway", "step_headroom", "interaction_space", "pool_headroom")
H4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
OPEN_STORED = {"air", "cave_air", "water", "ladder", "soul_lantern", "white_candle", "iron_chain", "skeleton_skull"}


def solid(t: Template, p):
    st = t.at(p)
    return st is not None and short(st) not in OPEN_STORED


def doorway(t: Template, p):
    """A doorless opening: wall on both sides along one axis and a lintel within 3 blocks above."""
    x, y, z = p
    sides = (solid(t, (x - 1, y, z)) and solid(t, (x + 1, y, z))) or (solid(t, (x, y, z - 1)) and solid(t, (x, y, z + 1)))
    return sides and any(solid(t, (x, y + d, z)) for d in (1, 2, 3))


def open_for_flood(t: Template, p):
    if solid(t, p) or short(t.at(p) or "air").endswith("_door"):
        return False  # doors, jigsaws and all masonry stop the flood
    return not doorway(t, p)  # doorless openings and arches are closed for the enclosure test only


def exterior_layers(t: Template):
    sx, sy, sz = t.size
    ext = set()
    for y in range(sy):
        q = deque()
        for x in range(sx):
            for z in range(sz):
                if (x in (0, sx - 1) or z in (0, sz - 1)) and open_for_flood(t, (x, y, z)):
                    ext.add((x, y, z))
                    q.append((x, y, z))
        while q:
            x, _, z = q.popleft()
            for dx, dz in H4:
                n = (x + dx, y, z + dz)
                if 0 <= n[0] < sx and 0 <= n[2] < sz and n not in ext and open_for_flood(t, n):
                    ext.add(n)
                    q.append(n)
    return ext


def ceiling(t: Template, x, y, z):
    """y of the first stored, non-passable block above (x, y, z), or None when open to the sky."""
    for yy in range(y + 1, t.size[1]):
        st = t.at((x, yy, z))
        if st is not None and short(st) not in OPEN_STORED:
            return yy
    return None


def build_mask(t: Template):
    sx, sy, sz = t.size
    ext = exterior_layers(t)
    reach = reachable(t)
    walk = {p for p in reach if stand(t, p) and not ladder(t, p)}
    cls = {}

    def mark(p, c, enclosed_only=True):
        if 0 <= p[1] < sy and t.at(p) is None and p not in cls and not (enclosed_only and p in ext):
            cls[p] = c

    for x, y, z in sorted(walk):
        if (x, y, z) not in ext:
            top = ceiling(t, x, y, z)
            if top is not None:
                for yy in range(y, top):
                    mark((x, yy, z), "room_interior")
            else:
                for yy in (y, y + 1, y + 2):
                    mark((x, yy, z), "walkway")
        else:
            # walkable on the module's own paving (stand() requires a stored floor) but outside any enclosure:
            # body height only
            for yy in (y, y + 1):
                mark((x, yy, z), "paved_walkway", enclosed_only=False)
        for dx, dz in H4:  # a step up needs head room above the cell it is climbed from
            if (x + dx, y + 1, z + dz) in walk:
                mark((x, y + 2, z), "step_headroom", enclosed_only=False)
    # a room is its whole enclosed, roofed volume, not only the columns a player walks in: spread each room layer
    # sideways over furniture (bed tops must be free to sleep), table tops and corners, never outside the enclosure
    # and never into a column without a ceiling
    q = deque(p for p, c in cls.items() if c == "room_interior")
    while q:
        x, y, z = q.popleft()
        for dx, dz in H4:
            nb = (x + dx, y, z + dz)
            if (0 <= nb[0] < sx and 0 <= nb[2] < sz and nb not in cls and t.at(nb) is None and nb not in ext
                    and ceiling(t, *nb) is not None):
                cls[nb] = "room_interior"
                q.append(nb)
    for p, st in t.state.items():
        n = short(st)
        if n.endswith("_bed"):
            mark((p[0], p[1] + 1, p[2]), "interaction_space", enclosed_only=False)  # sleeping needs free cells above both halves
        if n == "chest":
            mark((p[0], p[1] + 1, p[2]), "interaction_space", enclosed_only=False)
        if n == "water" and t.at((p[0], p[1] + 1, p[2])) is None:
            for d in (1, 2):
                mark((p[0], p[1] + d, p[2]), "pool_headroom", enclosed_only=False)
    full = {}
    for x in range(sx):
        for y in range(sy):
            for z in range(sz):
                p = (x, y, z)
                if t.at(p) is not None:
                    full[p] = "stored_architecture"
                elif p in cls:
                    full[p] = cls[p]
                elif p in ext:
                    full[p] = "exterior"
                else:
                    full[p] = "decorative_void"
    return full


def build(src: Path = D24F):
    out = {}
    for m in MODULES:
        t = Template(src / m / "restored.nbt")
        full = build_mask(t)
        c = Counter(full.values())
        out[m] = {"size": list(t.size), "class_counts": dict(sorted(c.items())),
                  "cleared": {k: sorted([list(p) for p, v in full.items() if v == k]) for k in CLEARED},
                  "decorative_void": sorted([list(p) for p, v in full.items() if v == "decorative_void"])}
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    r = build()
    for m, v in r.items():
        print(m, v["size"], v["class_counts"], "cleared", sum(len(x) for x in v["cleared"].values()))
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1))
