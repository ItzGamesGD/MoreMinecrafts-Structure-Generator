"""Role-based functional-protection inventory for the restored Ancient City modules.

A block is protected for what it *does* in this template, never for its block type:
  door          both halves of every door
  door_support  the block under each lower door half (DoorBlock.canSurvive: below must be face-sturdy UP)
  ladder        every ladder cell
  ladder_attach the block each ladder hangs on (LadderBlock.canSurvive: pos.relative(facing.getOpposite()))
  walk_floor    the floor under every walkable cell that is reachable from the ground floor and lies above it
                (elevated landings, upper floors, observation decks): a hole there is a fall, not decay
  railing       an edge block next to a reachable elevated walkable cell whose loss opens a walk-out (head room
                above it is free) onto a drop of DROP_HAZARD blocks or more
Everything else (lanterns, ground-floor masonry, walls with masonry above them, pillars, trim) keeps vanilla decay.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, load_nbt, blocks_of  # noqa: E402
from tools.stage24g.processors import ANCIENT_CITY_REPLACEABLE, name  # noqa: E402

DROP_HAZARD = 2
H = [(1, 0), (-1, 0), (0, 1), (0, -1)]
FACING = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}
PASSABLE = {"air", "cave_air", "ladder", "soul_lantern", "lantern", "white_candle", "water", "skeleton_skull",
            "iron_chain", "structure_void"}
FURNITURE = ("_bed", "barrel", "chest", "crafting_table", "_candle", "candle")


def short(state):
    return name(state).replace("minecraft:", "")


class Template:
    def __init__(self, path: Path):
        root = load_nbt(path)
        self.size = tuple(int(v) for v in root["size"])
        self.blocks = blocks_of(root)
        self.state = {p: s for p, (s, _) in self.blocks.items()}

    def at(self, p):
        return self.state.get(p)

    def jigsaw_final(self, p):
        st, nb = self.blocks.get(p, (None, None))
        if st and st.startswith("minecraft:jigsaw"):
            return str(nb.get("final_state", "minecraft:air"))
        return None

    def placed(self, p):
        """State actually written by the template at p (jigsaws resolve to final_state; None = cell left untouched)."""
        st = self.at(p)
        if st is None:
            return None
        if st.startswith("minecraft:jigsaw"):
            f = self.jigsaw_final(p)
            return None if f == "minecraft:structure_void" else f
        if st.startswith("minecraft:structure_void"):
            return None
        return st

    def passable(self, p):
        st = self.placed(p)
        if st is None:
            return True  # unspecified cell: assume open (worst case for falls)
        n = short(st)
        return n in PASSABLE or n.endswith("_door")

    def support(self, p):
        st = self.placed(p)
        if st is None:
            return False
        n = short(st)
        if n in PASSABLE or n.endswith(("_door", "_wall", "_fence", "_pane")) or n == "iron_bars":
            return False
        return True

    def inside(self, p):
        return all(0 <= p[i] < self.size[i] for i in range(3))


def stand(t: Template, p):
    x, y, z = p
    floor = t.placed((x, y - 1, z))
    return (t.inside(p) and t.passable(p) and t.passable((x, y + 1, z)) and t.support((x, y - 1, z))
            and short(t.at(p) or "air") != "water" and not short(floor).endswith(FURNITURE))


def ladder(t: Template, p):
    st = t.at(p)
    return st is not None and short(st) == "ladder"


def reachable(t: Template):
    """BFS from every ground-floor walkable cell over walk/step/drop moves and ladder columns."""
    sx, sy, sz = t.size
    nodes = {(x, y, z) for x in range(sx) for y in range(sy) for z in range(sz) if stand(t, (x, y, z)) or ladder(t, (x, y, z))}
    start = [p for p in nodes if p[1] == 1 and not ladder(t, p)]
    seen, q = set(start), deque(start)
    while q:
        x, y, z = q.popleft()
        nxt = []
        for dx, dz in H:
            for dy in (0, 1, -1, -2, -3):
                n = (x + dx, y + dy, z + dz)
                if n in nodes and (dy <= 0 or t.passable((x, y + 2, z))):
                    nxt.append(n)
                    break
        if ladder(t, (x, y, z)) or ladder(t, (x, y - 1, z)):
            nxt += [(x, y + 1, z), (x, y - 1, z)]
        for n in nxt:
            if n in nodes and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def drop_below(t: Template, x, y, z):
    """Fall height from body level y in column (x, z): blocks until the first support or water (ground at y=0
    outside the template)."""
    for d in range(1, y + 1):
        q = (x, y - d, z)
        if t.inside(q):
            if t.support(q) or short(t.placed(q) or "air") == "water":
                return d - 1
        elif y - d <= 0:
            return d - 1
    return y


def inventory(t: Template):
    roles = {}

    def add(p, role, why):
        roles.setdefault(tuple(p), {"roles": set(), "why": []})
        roles[tuple(p)]["roles"].add(role)
        roles[tuple(p)]["why"].append(why)

    for p, st in t.state.items():
        n = short(st)
        if n.endswith("_door"):
            add(p, "door", n)
            if "half=lower" in st:
                below = (p[0], p[1] - 1, p[2])
                add(below, "door_support", f"under door lower half {list(p)}")
        if n == "ladder":
            add(p, "ladder", st)
            f = st.split("facing=")[1].split(",")[0].rstrip("]")
            d = FACING[f]
            add((p[0] - d[0], p[1] - d[1], p[2] - d[2]), "ladder_attach", f"ladder {list(p)} faces {f}")
    reach = reachable(t)
    walk = sorted(p for p in reach if not ladder(t, p) and stand(t, p))
    # elevated: a hole in the floor, or a step over the edge, falls DROP_HAZARD or more
    elevated = [p for p in walk if 1 + drop_below(t, p[0], p[1] - 1, p[2]) >= DROP_HAZARD]
    for p in elevated:
        x, y, z = p
        add((x, y - 1, z), "walk_floor", f"floor of reachable elevated cell {list(p)}; hole falls {1 + drop_below(t, x, y - 1, z)}")
    for p in walk:
        x, y, z = p
        for dx, dz in H:
            n = (x + dx, y, z + dz)
            if n in reach or not t.inside(n) or (t.passable(n) and t.passable((n[0], y + 1, n[2]))):
                continue  # walkable, outside, or an opening the design leaves open
            # n is the barrier cell at foot level next to walkable p; follow the ray through the barrier band
            band, c = [], n
            while t.inside(c) and not (t.passable(c) and t.passable((c[0], y + 1, c[2]))) and len(band) < 8:
                band.append(c)
                c = (c[0] + dx, y, c[2] + dz)
            fall = max([drop_below(t, b[0], y, b[2]) for b in band] + [drop_below(t, c[0], y, c[2])])
            if fall >= DROP_HAZARD:
                # keeping the innermost foot-level barrier cell closes the walk-out whatever happens behind it
                add(n, "railing", f"edge barrier next to walkable {list(p)}; walk-out would fall {fall}")
    return roles, reach, elevated


def overlay_cells(t: Template, roles):
    """Cells the protection overlay must (re)write: protected cells the main pass can drop.

    * rottable states (#ancient_city_replaceable): block_rot drops 5 % of them
    * door_support cells that are jigsaws with final_state structure_void: the main pass writes nothing there, so a
      sturdy block matching the neighbouring floor is supplied (the jigsaw itself stays in the main template)
    """
    out, notes = {}, {}
    for p, info in sorted(roles.items()):
        st = t.at(p)
        if st is None:
            continue
        if st.startswith("minecraft:jigsaw"):
            if "door_support" in info["roles"] and t.placed(p) is None:
                nb = [t.placed((p[0] + dx, p[1], p[2] + dz)) for dx, dz in H]
                nb = [s for s in nb if s and name(s) in ANCIENT_CITY_REPLACEABLE | {"minecraft:polished_deepslate"}]
                fill = max(set(nb), key=nb.count) if nb else "minecraft:deepslate_bricks"
                out[p] = fill
                notes[p] = f"jigsaw final_state structure_void under a door: supply {fill} (most common neighbouring floor)"
            continue
        if name(st) in ANCIENT_CITY_REPLACEABLE:
            out[p] = st
    return out, notes


def build(src: Path):
    res = {}
    for m in MODULES:
        t = Template(src / m / "restored.nbt")
        roles, reach, elevated = inventory(t)
        ov, notes = overlay_cells(t, roles)
        res[m] = {
            "size": list(t.size),
            "reachable_cells": len(reach),
            "elevated_walk_cells": len(elevated),
            "protected": [{"pos": list(p), "state": t.at(p), "roles": sorted(i["roles"]), "why": i["why"],
                           "rottable": bool(t.at(p)) and name(t.at(p)) in ANCIENT_CITY_REPLACEABLE,
                           "overlay": p in ov} for p, i in sorted(roles.items()) if t.at(p) is not None],
            "protected_unspecified": [list(p) for p, i in sorted(roles.items()) if t.at(p) is None],
            "overlay": [{"pos": list(p), "state": s, **({"note": notes[p]} if p in notes else {})} for p, s in sorted(ov.items())],
        }
    return res


if __name__ == "__main__":
    import argparse
    from collections import Counter
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    r = build(Path(a.src))
    for m, v in r.items():
        c = Counter(role for e in v["protected"] for role in e["roles"])
        print(m, "reach", v["reachable_cells"], "elev", v["elevated_walk_cells"], dict(c), "overlay", len(v["overlay"]),
              "unspecified", len(v["protected_unspecified"]))
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1))
