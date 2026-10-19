"""Derive player-simulation goals (entry, beds, containers, ladders, decks, bath edges) from an NBT."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import *  # noqa

NONSOLID = ("air", "water", "lava", "jigsaw", "ladder", "lantern", "torch", "button", "skull", "carpet")


def bid(state):
    return state.split("[", 1)[0].replace("minecraft:", "")


def derive(module: str, root_dir: Path = S24B) -> dict:
    root = load_nbt(root_dir / module / "restored.nbt")
    b = {p: s for p, (s, _) in blocks_of(root).items()}
    size = tuple(int(v) for v in root["size"])

    def at(p):
        return b.get(p, "minecraft:air")

    def solid(p):
        n = bid(at(p))
        return not (n in NONSOLID or n.endswith("_door") or n.endswith("_bed") or n.endswith(("_stairs", "_slab")) and False
                    or n in ("air", "water", "lava", "jigsaw", "ladder", "soul_lantern", "structure_void"))

    def clear_body(p):
        n = bid(at(p))
        return n in ("air", "ladder", "soul_lantern") or n.endswith("_stairs") or (n.endswith("_door") and "open=true" in at(p))

    def standable(p):
        x, y, z = p
        floor = at((x, y - 1, z))
        fn = bid(floor)
        ok_floor = (solid((x, y - 1, z)) or fn.endswith(("_slab", "_stairs", "_bed")) or fn == "ladder")
        return ok_floor and clear_body(p) and clear_body((x, y + 1, z))

    def neighbors_standable(p):
        x, y, z = p
        out = []
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                q = (x + dx, y + dy, z + dz)
                if standable(q):
                    out.append(list(q))
        return out

    goals = {"module": module, "size": list(size), "origin_y_offset": 0}
    doors = sorted(p for p, s in b.items() if bid(s).endswith("_door") and "half=lower" in s)
    goals["doors"] = [list(p) for p in doors]
    goals["beds"] = [{"pos": list(p), "access": neighbors_standable(p)} for p, s in sorted(b.items(), key=lambda kv: kv[0])
                     if bid(s).endswith("_bed") and "part=head" in s]
    goals["containers"] = [{"pos": list(p), "block": bid(s), "access": neighbors_standable(p)}
                           for p, s in sorted(b.items()) if bid(s) in ("chest", "barrel", "crafting_table", "furnace")]
    goals["ladders"] = [list(p) for p, s in sorted(b.items()) if bid(s) == "ladder"]
    # connected water bodies and a standable rim cell for each
    water = {p for p, st in b.items() if bid(st) == "water"}
    seen, comps = set(), []
    for w0 in sorted(water):
        if w0 in seen:
            continue
        comp, stack = [], [w0]
        seen.add(w0)
        while stack:
            q = stack.pop()
            comp.append(q)
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                n = (q[0] + d[0], q[1] + d[1], q[2] + d[2])
                if n in water and n not in seen:
                    seen.add(n)
                    stack.append(n)
        comps.append(comp)
    goals["water_bodies"] = []
    for comp in comps:
        rim = []
        for q in comp:
            rim.extend(tuple(r) for r in neighbors_standable(q) if tuple(r) not in water)
        rim = sorted(set(rim))
        goals["water_bodies"].append({"cells": len(comp), "sample_cell": list(comp[len(comp) // 2]),
                                      "rim_standable": [list(r) for r in rim][:12]})
    goals["jigsaws"] = [list(p) for p, s in sorted(b.items()) if bid(s) == "jigsaw"]
    goals["water"] = [list(p) for p, s in sorted(b.items()) if bid(s) == "water"]
    return goals


if __name__ == "__main__":
    for m in MODULES:
        g = derive(m)
        print(m, "doors", g["doors"], "beds", len(g["beds"]), "containers", [(c["block"], c["pos"]) for c in g["containers"]],
              "ladders", len(g["ladders"]))
