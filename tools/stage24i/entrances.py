"""Minimal entrance clearance per house door in a generated sweep.

From each door (lower half, outward = template -x, rotated) a 0-1 shortest-path search runs over player positions
(feet cell; body = feet + head) outside the house box, within RADIUS blocks of the door:
  * the search starts in the doorway and leaves it outwards; moves: 4 horizontal neighbours with a height change of
    -1, 0 or +1 (a two-way walkable step) (a +1 step also needs the head cell above the
    current position); the destination must stand on a solid floor block,
  * cost: the number of body cells that are solid NATURAL terrain and would have to be cleared (0 for free cells);
    a body cell holding any other solid block (architecture of any city piece) can never be cleared -> blocked,
  * target: a free walkable cell that belongs to open city space = a walkable component of at least OPEN_MIN cells
    reachable without clearing anything.
Result per entrance: minimal number of cells to clear, the exact cells (with owning pieces and blocks), the path length.
"""
from __future__ import annotations

import argparse
import heapq
import json
import sys
from collections import Counter, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import OUT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT, rot, TARGET  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
HOUSES = ("large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2")
NONSOLID = {"air", "cave_air", "water", "sculk_vein", "glow_lichen", "soul_lantern", "lantern", "light", "sculk_sensor", "candle",
            "white_candle", "small_amethyst_bud", "medium_amethyst_bud", "large_amethyst_bud", "amethyst_cluster"}
NATURAL = {"dripstone_block", "pointed_dripstone", "tuff", "calcite", "smooth_basalt", "amethyst_block", "budding_amethyst", "stone",
           "granite", "diorite", "andesite", "gravel", "clay", "dirt", "deepslate", "cobblestone", "sculk", "moss_block",
           "deepslate_coal_ore", "deepslate_iron_ore", "deepslate_gold_ore", "deepslate_copper_ore", "deepslate_redstone_ore",
           "deepslate_lapis_ore", "deepslate_diamond_ore", "magma_block", "obsidian", "lava"}
OPEN_MIN = 200
RADIUS = 14
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def nm(b):
    return (b or "minecraft:air").split("[")[0].split(":")[1]


class Grid:
    def __init__(self, w, box):
        self.w, self.box, self.cache = w, box, {}

    def b(self, c):
        if c not in self.cache:
            self.cache[c] = nm(self.w.block(*c))
        return self.cache[c]

    def free(self, c):
        return self.b(c) in NONSOLID

    def in_house(self, c):
        x0, y0, z0, x1, y1, z1 = self.box
        return x0 <= c[0] <= x1 and z0 <= c[2] <= z1 and y0 <= c[1] <= y1

    def floor(self, c):
        return not self.free((c[0], c[1] - 1, c[2]))

    def walkable_free(self, c):
        return self.free(c) and self.free((c[0], c[1] + 1, c[2])) and self.floor(c)


def open_component(g, start, limit=OPEN_MIN):
    seen, q = {start}, deque([start])
    while q and len(seen) < limit:
        x, y, z = q.popleft()
        for dx, dz in DIRS:
            for dy in (0, -1, 1, -2, -3):
                n = (x + dx, y + dy, z + dz)
                if n in seen or g.in_house(n) or not g.walkable_free(n):
                    continue
                if dy == 1 and not g.free((x, y + 2, z)):
                    continue
                seen.add(n)
                q.append(n)
                break
    return len(seen) >= limit


def door_cells(module):
    b = blocks_of(load_nbt(D24F / module / "restored.nbt"))
    return sorted(p for p, (s, _) in b.items() if s.split("[")[0].endswith("_door") and "half=lower" in s)


def solve(g, door, out):
    start = tuple(door)  # the doorway itself (both door halves are passable for a player)
    open_cache = {}

    def cell_cost(c):
        cost, cells = 0, []
        for yy in (0, 1):
            q = (c[0], c[1] + yy, c[2])
            n = g.b(q)
            if n in NONSOLID:
                continue
            if n not in NATURAL:
                return None, None
            cost += 1
            cells.append(q)
        return cost, cells

    first = (door[0] + out[0], door[1], door[2] + out[2])
    dist = {start: 0}
    prev = {start: None}
    clears = {start: []}
    pq = [(0, 0, start)]
    while pq:
        d, steps, c = heapq.heappop(pq)
        if d > dist.get(c, 1e9):
            continue
        if c != start and not clears[c] and g.walkable_free(c):
            if c not in open_cache:
                open_cache[c] = open_component(g, c)
            if open_cache[c]:
                path, cur, cells = [], c, []
                while cur is not None:
                    path.append(cur)
                    cells += clears[cur]
                    cur = prev[cur]
                return {"status": "ok", "cells_to_clear": sorted({tuple(x) for x in cells}), "cost": d, "path": path[::-1], "reached": list(c)}
        if steps > 3 * RADIUS:
            continue
        for dx, dz in DIRS:
            for dy in (0, -1, 1):
                n = (c[0] + dx, c[1] + dy, c[2] + dz)
                if c == start and (dx, dz) != (out[0], out[2]):
                    continue  # leave the doorway outwards only
                if g.in_house(n) or abs(n[0] - door[0]) > RADIUS or abs(n[2] - door[2]) > RADIUS:
                    continue
                if not g.floor(n):
                    continue
                cc, cl = cell_cost(n)
                if cc is None:
                    continue
                extra = []
                if dy == 1:
                    hq = (c[0], c[1] + 2, c[2])
                    hn = g.b(hq)
                    if hn not in NONSOLID:
                        if hn not in NATURAL:
                            continue
                        extra = [hq]
                nd = d + cc + len(extra)
                if nd < dist.get(n, 1e9):
                    dist[n] = nd
                    prev[n] = c
                    clears[n] = cl + extra
                    heapq.heappush(pq, (nd, steps + 1, n))
    return {"status": "no_connection_within_radius"}


def survey(seed, variant, manifests: Path):
    ps = json.loads((manifests / f"manifest-{seed}-{variant}.json").read_text())["cities"][0]["pieces"]
    w = World(OUT / f"_work/wg-{seed}-{variant}/world/dimensions/minecraft/overworld")
    rows = []
    for i, p in enumerate(ps):
        m = TARGET.get(p["template"])
        if m not in HOUSES:
            continue
        r, o = ROT[p["rotation"]], p["pos"]
        out = rot((-1, 0, 0), r)
        g = Grid(w, p["bb"])
        for d in door_cells(m):
            q = rot(d, r)
            dw = (o[0] + q[0], o[1] + q[1], o[2] + q[2])
            res = solve(g, dw, out)
            cells = [tuple(c) for c in res.get("cells_to_clear", [])]
            own = Counter()
            for c in cells:
                for j, x in enumerate(ps):
                    if x["bb"][0] <= c[0] <= x["bb"][3] and x["bb"][2] <= c[2] <= x["bb"][5] and x["bb"][1] <= c[1] <= x["bb"][4]:
                        own[x["template"].split("/")[-1] or x["element_type"].split(":")[1]] += 1
            rows.append({"seed": seed, "piece_index": i, "module": m, "rotation": p["rotation"], "door_world": list(dw), "outward": list(out),
                         "status": res["status"], "cells_to_clear": [list(c) for c in cells], "n_cells": len(cells) if res["status"] == "ok" else None,
                         "blocks": dict(Counter(g.b(c) for c in cells)), "owners": dict(own), "path": [list(x) for x in res.get("path", [])]})
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="h24")
    ap.add_argument("--manifests", default=str(ROOT / "artifacts/ancient-city-restoration/stage-24h/worldgen"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, nargs="*", default=list(range(24001, 24025)))
    a = ap.parse_args()
    allr = []
    for s in a.seeds:
        allr += survey(s, a.variant, Path(a.manifests))
    Path(a.out).write_text(json.dumps(allr, indent=1))
    c = Counter()
    for r in allr:
        c[r["status"] if r["status"] != "ok" else f"clear_{r['n_cells']}"] += 1
        if r["status"] != "ok" or r["n_cells"]:
            print(r["seed"], r["module"], r["rotation"], r["door_world"], r["status"], r["n_cells"], r["blocks"], r["owners"])
    print(len(allr), dict(sorted(c.items())))
