"""Stage 24-L Phase 0: read-only pedestrian connectivity measurement of the generated Ancient City (Stage 24-K pack).

READ-ONLY. Reads saved worlds (`World`, Anvil files) and generation manifests. It clears, carves and replaces nothing, enlarges no
template box and writes no NBT / datapack / production file; the only outputs are JSON / Markdown audit evidence.

This is a static geometric model of the saved world. It is NOT a Minecraft client and NOT a physics simulation; the scripted
navigation of Stage 24-I (mineflayer) is a separate, weaker-than-client check. See the assumptions in `MODEL` below.

Model (same block classes as `tools/stage24i/entrances.py`, so the numbers are comparable with the 24-I survey):
  * free cell  = air / water / the survey's NONSOLID set, plus doors and fence gates (a player passes a door);
  * walkable cell (a player's feet cell) = feet and head cell free, floor cell solid and not lava / magma / fire;
  * two-way step = 4-neighbour move with a height change of -1, 0 or +1; a +-1 step needs the cell above the LOWER cell's head free;
  * one-way drop = 4-neighbour move to a cell 2 or 3 blocks lower (survivable fall, the column between must be free);
  * NOT modelled: ladders, vines, elevators, boats, swimming up, upper floors that are only reachable by ladder, mobs.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import OUT  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT, rot, TARGET  # noqa: E402
from tools.stage24i import entrances as E  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "artifacts/ancient-city-restoration"
VARIANT = "k24"
HOUSES = E.HOUSES
MARGIN = 10
BAD_FLOOR = {"lava", "magma_block", "fire", "soul_fire", "cactus", "sweet_berry_bush", "campfire", "soul_campfire", "powder_snow"}
DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

def category(template: str, element_type: str) -> str:
    """Coarse piece category from the template path (used to say what a route runs through)."""
    t = template.replace("minecraft:ancient_city/", "").replace("moreminecrafts:ancient_city/", "")
    if not t:
        return "feature" if "feature" in element_type else "other"
    if t.startswith("city_center/walls/"):
        return "city_center_wall"
    if t.startswith("city_center/"):
        return "city_center"
    if t.startswith("city/entrance/"):
        return "entrance_path"
    if t.startswith("walls/"):
        return "wall_stairs" if "stairs" in t else "wall_bridge" if "bridge" in t else "wall_passage" if "passage" in t else "wall"
    m = t.split("/")[-1]
    if m in HOUSES:
        return "house"
    if m.endswith("_pillar_1"):
        return "tower"
    if m == "sauna_1":
        return "sauna"
    if m.startswith(("chamber", "barracks")):
        return "chamber"
    if m.startswith(("tall_ruin", "small_statue")):
        return "monument"
    return "other"


def nm(b):
    return (b or "minecraft:air").split("[")[0].replace("minecraft:", "")


# ---------------------------------------------------------------------------------------------------------------- grid
class Grid3:
    """Block-name ids of a box of the world as a numpy array [x, y, z]."""

    def __init__(self, w: World, box):
        self.x0, self.y0, self.z0, x1, y1, z1 = box
        self.shape = (x1 - self.x0 + 1, y1 - self.y0 + 1, z1 - self.z0 + 1)
        self.names = ["unknown"]
        self.ids = np.zeros(self.shape, np.uint16)
        lut = {"unknown": 0}
        for cx in range(self.x0 >> 4, (x1 >> 4) + 1):
            for cz in range(self.z0 >> 4, (z1 >> 4) + 1):
                ch = w.chunk(cx, cz)
                if ch is None:
                    continue
                for sec in ch["sections"]:
                    sy = int(sec["Y"])
                    if (sy * 16 + 15) < self.y0 or sy * 16 > y1:
                        continue
                    bs = sec.get("block_states")
                    pal = [nm(str(p["Name"])) for p in bs["palette"]] if bs is not None else ["air"]
                    pid = []
                    for n in pal:
                        if n not in lut:
                            lut[n] = len(self.names)
                            self.names.append(n)
                        pid.append(lut[n])
                    pid = np.array(pid, np.uint16)
                    if bs is None or len(pal) == 1 or "data" not in bs:
                        blk = np.full((16, 16, 16), pid[0], np.uint16)
                    else:
                        bits = max(4, (len(pal) - 1).bit_length())
                        per = 64 // bits
                        longs = np.array([int(v) & 0xFFFFFFFFFFFFFFFF for v in bs["data"]], np.uint64)
                        idx = np.empty(4096, np.uint64)
                        mask = np.uint64((1 << bits) - 1)
                        for j in range(per):
                            part = idx[j::per]
                            part[:] = (longs[:len(part)] >> np.uint64(j * bits)) & mask
                        blk = pid[idx.astype(np.intp)].reshape(16, 16, 16)       # [y][z][x]
                    blk = np.transpose(blk, (2, 0, 1))                          # [x][y][z]
                    # intersect the 16^3 block with the box
                    bx0, bz0, by0 = cx * 16, cz * 16, sy * 16
                    ax0, ax1 = max(bx0, self.x0), min(bx0 + 15, x1)
                    az0, az1 = max(bz0, self.z0), min(bz0 + 15, z1)
                    ay0, ay1 = max(by0, self.y0), min(by0 + 15, y1)
                    self.ids[ax0 - self.x0:ax1 - self.x0 + 1, ay0 - self.y0:ay1 - self.y0 + 1, az0 - self.z0:az1 - self.z0 + 1] = \
                        blk[ax0 - bx0:ax1 - bx0 + 1, ay0 - by0:ay1 - by0 + 1, az0 - bz0:az1 - bz0 + 1]
        # a section absent from a loaded chunk is air (as in World.block); a missing chunk stays "unknown" = solid wall
        self.loaded = np.zeros(self.shape[0:1] + self.shape[2:3], bool)
        for cx in range(self.x0 >> 4, (x1 >> 4) + 1):
            for cz in range(self.z0 >> 4, (z1 >> 4) + 1):
                if w.chunk(cx, cz) is not None:
                    xs = slice(max(cx * 16, self.x0) - self.x0, min(cx * 16 + 15, x1) - self.x0 + 1)
                    zs = slice(max(cz * 16, self.z0) - self.z0, min(cz * 16 + 15, z1) - self.z0 + 1)
                    self.loaded[xs, zs] = True
        air = self._id("air")
        zero = self.ids == 0
        fill = zero & self.loaded[:, None, :]
        self.ids[fill] = air
        self.free = np.zeros(len(self.names), bool)
        self.floor_ok = np.zeros(len(self.names), bool)
        for i, n in enumerate(self.names):
            if n == "unknown":
                continue
            self.free[i] = n in E.NONSOLID or n.endswith("_door") or n.endswith("_fence_gate")
            self.floor_ok[i] = (not self.free[i]) and n not in BAD_FLOOR
        self.F = self.free[self.ids]
        self.FL = self.floor_ok[self.ids]

    def _id(self, name):
        if name not in self.names:
            self.names.append(name)
        return self.names.index(name)

    def local(self, c):
        return (c[0] - self.x0, c[1] - self.y0, c[2] - self.z0)

    def inside(self, c):
        loc = self.local(c)
        return all(0 <= loc[i] < self.shape[i] for i in range(3))

    def name(self, c):
        return self.names[self.ids[self.local(c)]] if self.inside(c) else "outside"


# ------------------------------------------------------------------------------------------------------------- graph
def walkable(F, FL):
    w = np.zeros_like(F)
    w[:, 1:-1, :] = F[:, 1:-1, :] & F[:, 2:, :] & FL[:, :-2, :]
    return w


def shifted_free(F, k):
    """H[x, y, z] = F[x, y+k, z] (False beyond the top)."""
    H = np.zeros_like(F)
    H[:, :F.shape[1] - k, :] = F[:, k:, :]
    return H


def two_way_edges(W, F):
    """Index arrays (u, v) of undirected two-way steps between walkable cells; ids = rank among walkable cells."""
    nx, ny, nz = W.shape
    idm = np.full(W.shape, -1, np.int64)
    idm[W] = np.arange(int(W.sum()))
    H2 = shifted_free(F, 2)
    us, vs = [], []
    for dx, dz in ((1, 0), (0, 1)):
        for dy in (-1, 0, 1):
            xa, xb = (slice(0, nx - dx), slice(dx, nx))
            za, zb = (slice(0, nz - dz), slice(dz, nz))
            ya, yb = (slice(max(0, -dy), ny - max(0, dy)), slice(max(0, dy), ny - max(0, -dy)))
            A, B = W[xa, ya, za], W[xb, yb, zb]
            m = A & B
            if dy == 1:
                m &= H2[xa, ya, za]                  # lower cell = A
            elif dy == -1:
                m &= H2[xb, yb, zb]                  # lower cell = B
            ia, ib = idm[xa, ya, za][m], idm[xb, yb, zb][m]
            us.append(ia)
            vs.append(ib)
    return idm, np.concatenate(us), np.concatenate(vs)


def drop_edges(W, F, idm, depths=(2, 3)):
    """Directed one-way drops a -> b, b 2..3 blocks lower and the column between free."""
    nx, ny, nz = W.shape
    us, vs = [], []
    for dx, dz in DIRS4:
        xa = slice(max(0, -dx), nx - max(0, dx))
        xb = slice(max(0, dx), nx - max(0, -dx))
        za = slice(max(0, -dz), nz - max(0, dz))
        zb = slice(max(0, dz), nz - max(0, -dz))
        for d in depths:
            A = W[xa, d:, za]                      # a at y
            B = W[xb, :ny - d, zb]                 # b at y-d
            m = A & B
            for k in range(2, d + 2):              # cells (b.x, b.y+k) for k in 2..d+1 must be free (feet & head of the falling player)
                Hk = shifted_free(F, k)
                m &= Hk[xb, :ny - d, zb]
            us.append(idm[xa, d:, za][m])
            vs.append(idm[xb, :ny - d, zb][m])
    return np.concatenate(us), np.concatenate(vs)


def components(n, u, v):
    p = np.arange(n)
    while len(u):
        pu, pv = p[u], p[v]
        m = pu != pv
        if not m.any():
            break
        u, v, pu, pv = u[m], v[m], pu[m], pv[m]
        np.minimum.at(p, np.maximum(pu, pv), np.minimum(pu, pv))
        while True:
            pp = p[p]
            if (pp == p).all():
                break
            p = pp
    return p


class Net:
    """Walkable cells, two-way graph, components and one-way drops of one generated city."""

    def __init__(self, g: Grid3):
        self.g = g
        self.W = walkable(g.F, g.FL)
        self.idm, self.u, self.v = two_way_edges(self.W, g.F)
        self.n = int(self.W.sum())
        self.cells = np.argwhere(self.W)                  # local coords, row index == id
        self.comp = components(self.n, self.u, self.v)
        self.sizes = Counter(self.comp.tolist())
        self.main = self.sizes.most_common(1)[0][0] if self.sizes else -1
        du, dv = drop_edges(self.W, g.F, self.idm)
        self.drops = defaultdict(set)
        for a, b in zip(self.comp[du].tolist(), self.comp[dv].tolist()):
            if a != b:
                self.drops[a].add(b)
        # CSR adjacency for BFS
        both_u = np.concatenate([self.u, self.v])
        both_v = np.concatenate([self.v, self.u])
        order = np.argsort(both_u, kind="stable")
        self.adj = both_v[order]
        self.off = np.searchsorted(both_u[order], np.arange(self.n + 1))

    def cid(self, c):
        """Cell id of the walkable cell at world coordinates c, or -1."""
        loc = self.g.local(c)
        if not self.g.inside(c):
            return -1
        return int(self.idm[loc])

    def world(self, i):
        x, y, z = self.cells[i]
        return (int(x) + self.g.x0, int(y) + self.g.y0, int(z) + self.g.z0)

    def nearest_walkable(self, c, up=1, down=8):
        """Id of the walkable cell in the column of c nearest to c.y (search y+up .. y-down), or -1."""
        best = -1
        for dy in sorted(range(-down, up + 1), key=abs):
            i = self.cid((c[0], c[1] + dy, c[2]))
            if i >= 0:
                return i
        return best

    def bfs(self, src, targets, want, max_nodes=200000):
        """Two-way BFS from cell id src; returns [(target_key, dist, path_ids)] for the first `want` distinct target keys found."""
        seen = {src: -1}
        q = deque([(src, 0)])
        found, keys = [], set()
        while q and len(seen) < max_nodes:
            i, d = q.popleft()
            k = targets.get(i)
            if k is not None and k not in keys:
                keys.add(k)
                path, cur = [], i
                while cur != -1:
                    path.append(cur)
                    cur = seen[cur]
                found.append((k, d, path[::-1]))
                if len(found) >= want:
                    break
            for j in self.adj[self.off[i]:self.off[i + 1]].tolist():
                if j not in seen:
                    seen[j] = i
                    q.append((j, d + 1))
        return found


# ------------------------------------------------------------------------------------------------------------- measurement
def piece_at(pieces, c):
    best = None
    for j, p in enumerate(pieces):
        b = p["bb"]
        if b[0] <= c[0] <= b[3] and b[1] <= c[1] <= b[4] and b[2] <= c[2] <= b[5]:
            vol = (b[3] - b[0] + 1) * (b[4] - b[1] + 1) * (b[5] - b[2] + 1)
            if best is None or vol < best[1]:
                best = (j, vol)
    return best[0] if best else None


def route_stats(net, pieces, path_ids):
    cells = [net.world(i) for i in path_ids]
    dys = [b[1] - a[1] for a, b in zip(cells, cells[1:])]
    comp = Counter()
    floors = Counter()
    for c in cells[1:]:
        j = piece_at(pieces, c)
        comp[category(pieces[j]["template"], pieces[j]["element_type"]) if j is not None else "natural_terrain"] += 1
        floors[net.g.name((c[0], c[1] - 1, c[2]))] += 1
    return {"steps": len(dys), "up": sum(1 for d in dys if d > 0), "down": sum(1 for d in dys if d < 0),
            "net_dy": cells[-1][1] - cells[0][1] if cells else 0, "path_height_range": (max(c[1] for c in cells) - min(c[1] for c in cells)) if cells else 0,
            "on": dict(comp), "floor_top": dict(floors.most_common(4))}


def door_front(net, door, out):
    """Walkable cell just outside the doorway (door.y +1 .. -8) or None, with the vertical offset."""
    o = (door[0] + out[0], door[1], door[2] + out[2])
    i = net.nearest_walkable(o, up=1, down=8)
    if i < 0:
        return None, None, None
    c = net.world(i)
    return i, c, c[1] - door[1]


def measure_seed(seed, manifests: Path, survey_rows=None):
    pieces = json.loads((manifests / f"manifest-{seed}-{VARIANT}.json").read_text())["cities"][0]["pieces"]
    w = World(OUT / f"_work/wg-{seed}-{VARIANT}/world/dimensions/minecraft/overworld")
    bbs = [p["bb"] for p in pieces]
    box = (min(b[0] for b in bbs) - MARGIN, min(b[1] for b in bbs) - 8, min(b[2] for b in bbs) - MARGIN,
           max(b[3] for b in bbs) + MARGIN, max(b[4] for b in bbs) + 4, max(b[5] for b in bbs) + MARGIN)
    g = Grid3(w, box)
    net = Net(g)
    main = net.main
    # --- buildings (the eight Ancient City modules) and their entrances
    entrance_targets, buildings, doors = {}, [], []
    for pi, p in enumerate(pieces):
        m = TARGET.get(p["template"])
        if not m:
            continue
        r, o = ROT[p["rotation"]], p["pos"]
        out = rot((-1, 0, 0), r)
        bld = {"piece_index": pi, "module": m, "rotation": p["rotation"], "bb": p["bb"], "doors": []}
        if m in HOUSES:
            for d in E.door_cells(m):
                q = rot(d, r)
                dw = (o[0] + q[0], o[1] + q[1], o[2] + q[2])
                inward = (dw[0] - out[0], dw[1], dw[2] - out[2])
                fi, fc, fdy = door_front(net, dw, out)
                di = net.cid(dw)
                ii = net.nearest_walkable(inward, up=0, down=2)
                comp_front = int(net.comp[fi]) if fi is not None and fi >= 0 else None
                comp_door = int(net.comp[di]) if di >= 0 else None
                comp_in = int(net.comp[ii]) if ii >= 0 else None
                if comp_front == main and comp_door == main:
                    status = "open_to_main"
                elif comp_in == main:
                    status = "door_blocked_building_reachable_elsewhere"
                elif comp_front is None:
                    status = "no_walkable_cell_outside_door"
                else:
                    status = "cut_off_from_main"
                oc = (dw[0] + out[0], dw[1], dw[2] + out[2])
                oj = piece_at(pieces, oc)
                bbx = p["bb"]
                touched = {(cx, cz) for cx in range(bbx[0] >> 4, (bbx[3] >> 4) + 1) for cz in range(bbx[2] >> 4, (bbx[5] >> 4) + 1)}
                row = {"front_cell_chunk_touched_by_house_box": (oc[0] >> 4, oc[2] >> 4) in touched,
                       "front_cell_owner": category(pieces[oj]["template"], pieces[oj]["element_type"]) if oj is not None else "none",
                       "front_cell_owner_piece": oj,
                       "seed": seed, "piece_index": pi, "module": m, "rotation": p["rotation"], "door_world": list(dw), "outward": list(out),
                       "doorway_walkable": di >= 0, "door_front": list(fc) if fc else None, "front_dy": fdy,
                       "comp_front": comp_front, "comp_doorway": comp_door, "comp_interior": comp_in, "main": main, "status": status}
                if comp_front is not None and comp_front != main:
                    row["front_comp_size"] = net.sizes[comp_front]
                    row["front_comp_drops_to_main"] = main in net.drops.get(comp_front, ())
                    row["main_drops_to_front_comp"] = comp_front in net.drops.get(main, ())
                doors.append(row)
                bld["doors"].append(len(doors) - 1)
                if fi is not None and fi >= 0 and comp_front == comp_door and comp_front is not None:
                    entrance_targets[fi] = pi
        buildings.append(bld)
    # --- component structure
    top = net.sizes.most_common(6)
    comps = []
    for cid, size in top:
        owners = Counter()
        for dr in doors:
            if dr["comp_front"] == cid:
                owners[dr["module"]] += 1
        idx = np.flatnonzero(net.comp == cid)
        sample = idx[:: max(1, len(idx) // 1500)]
        boxes = Counter()
        for i in sample:
            j = piece_at(pieces, net.world(int(i)))
            boxes[category(pieces[j]["template"], pieces[j]["element_type"]) if j is not None else "natural_terrain"] += 1
        ys = net.cells[idx][:, 1] + g.y0
        comps.append({"component": int(cid), "walkable_cells": size, "is_main": cid == main, "house_doors_in_front_comp": dict(owners),
                      "y_range": [int(ys.min()), int(ys.max())], "sampled_piece_boxes": dict(boxes.most_common(5)),
                      "drops_to_main": main in net.drops.get(cid, ()), "main_drops_to_it": cid in net.drops.get(main, ())})
    # --- routes between buildings (nearest 3 other buildings' door fronts) and to the city entrance path
    entrance_cells = {}
    for pi, p in enumerate(pieces):
        if category(p["template"], p["element_type"]) == "entrance_path":
            b = p["bb"]
            sub = net.W[b[0] - g.x0:b[3] - g.x0 + 1, max(b[1] - g.y0, 0):b[4] - g.y0 + 1, b[2] - g.z0:b[5] - g.z0 + 1]
            for lx, ly, lz in np.argwhere(sub)[:2000]:
                entrance_cells[int(net.idm[lx + b[0] - g.x0, ly + max(b[1] - g.y0, 0), lz + b[2] - g.z0])] = "entrance_path"
    routes = []
    for fi, pi in list(entrance_targets.items()):
        t = {k: v for k, v in entrance_targets.items() if v != pi}
        for key, dist, path in net.bfs(fi, t, want=3):
            rs = route_stats(net, pieces, path)
            routes.append({"from_piece": pi, "to_piece": key, "kind": "building_to_building", **rs})
        if entrance_cells:
            for key, dist, path in net.bfs(fi, entrance_cells, want=1, max_nodes=400000):
                rs = route_stats(net, pieces, path)
                routes.append({"from_piece": pi, "to_piece": "entrance_path", "kind": "building_to_city_entrance", **rs})
    # --- other buildings (sauna, towers): reach main?
    others = []
    for b in buildings:
        if b["module"] in HOUSES:
            continue
        bb = b["bb"]
        lo = g.local((bb[0], bb[1], bb[2]))
        hi = g.local((bb[3], bb[4], bb[5]))
        sub = net.W[max(lo[0], 0):hi[0] + 1, max(lo[1], 0):hi[1] + 1, max(lo[2], 0):hi[2] + 1]
        ids = net.idm[max(lo[0], 0):hi[0] + 1, max(lo[1], 0):hi[1] + 1, max(lo[2], 0):hi[2] + 1][sub]
        cs = Counter(int(net.comp[i]) for i in ids)
        others.append({"piece_index": b["piece_index"], "module": b["module"], "rotation": b["rotation"], "walkable_cells_in_box": int(len(ids)),
                       "components": dict(cs.most_common(4)), "touches_main": main in cs})
    return {"seed": seed, "variant": VARIANT, "region_box": list(box), "unknown_columns": int((~g.loaded).sum()), "walkable_cells": net.n,
            "components": comps, "n_components": len(net.sizes), "main_component": int(main), "main_cells": net.sizes[main],
            "main_share": round(net.sizes[main] / max(net.n, 1), 4), "doors": doors, "buildings_other": others, "routes": routes,
            "piece_categories": dict(Counter(category(p["template"], p["element_type"]) for p in pieces))}



FOCUS = {24005: 71, 24009: 59, 24015: 55}                 # deferred entrances: seed -> piece index of the house
ARCH_OR_NATURAL = lambda n: "natural" if n in E.NATURAL else "architecture"  # noqa: E731


def column(g, x, z, y0, y1):
    return [[y, g.name((x, y, z))] for y in range(y1, y0 - 1, -1)]


def focus_case(seed, manifests: Path, survey_rows, radius=12):
    """Precise obstruction / terrain measurement at one deferred entrance (read-only)."""
    pi = FOCUS[seed]
    pieces = json.loads((manifests / f"manifest-{seed}-{VARIANT}.json").read_text())["cities"][0]["pieces"]
    w = World(OUT / f"_work/wg-{seed}-{VARIANT}/world/dimensions/minecraft/overworld")
    bbs = [p["bb"] for p in pieces]
    box = (min(b[0] for b in bbs) - MARGIN, min(b[1] for b in bbs) - 8, min(b[2] for b in bbs) - MARGIN,
           max(b[3] for b in bbs) + MARGIN, max(b[4] for b in bbs) + 4, max(b[5] for b in bbs) + MARGIN)
    g = Grid3(w, box)
    net = Net(g)
    row = next(r for r in survey_rows if r["seed"] == seed and r["piece_index"] == pi and (r["status"] != "ok" or r["n_cells"]))
    door, out = tuple(row["door_world"]), tuple(row["outward"])
    res = {"seed": seed, "piece_index": pi, "module": row["module"], "rotation": row["rotation"], "door_world": list(door), "outward": list(out),
           "survey_status": row["status"], "survey_cells_to_clear": row["cells_to_clear"], "survey_blocks": row["blocks"], "survey_owners": row["owners"]}
    # cells the 24-I survey says must be cleared: block, class, which piece box holds them
    cells = []
    for c in row["cells_to_clear"]:
        j = piece_at(pieces, tuple(c))
        cells.append({"cell": c, "block": g.name(tuple(c)), "class": ARCH_OR_NATURAL(g.name(tuple(c))),
                      "owner_piece": j, "owner_template": pieces[j]["template"].split("/")[-1] if j is not None else None,
                      "inside_house_box": _in_box(pieces[pi]["bb"], c)})
    res["obstruction_cells"] = cells
    res["obstruction_summary"] = {"n": len(cells), "natural": sum(1 for c in cells if c["class"] == "natural"),
                                  "architecture": sum(1 for c in cells if c["class"] == "architecture"),
                                  "owner_templates": dict(Counter(c["owner_template"] for c in cells)),
                                  "inside_house_box": sum(1 for c in cells if c["inside_house_box"])}
    if cells:
        xs, ys, zs = ([c["cell"][k] for c in cells] for k in range(3))
        res["obstruction_extent"] = {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)], "z": [min(zs), max(zs)]}
    # outward column profiles (what stands in front of the door)
    res["profiles"] = {f"out+{k}": column(g, door[0] + out[0] * k, door[2] + out[2] * k, door[1] - 10, door[1] + 3) for k in range(1, 6)}
    # walkable map around the door: height of the walkable cell nearest to door.y and its component class
    dyrows, cmprows = [], []
    fi, fc, fdy = door_front(net, door, out)
    front_comp = int(net.comp[fi]) if fi is not None and fi >= 0 else None
    for dz in range(-radius, radius + 1):
        a, b = [], []
        for dx in range(-radius, radius + 1):
            x, z = door[0] + dx, door[2] + dz
            best = None
            for ddy in sorted(range(-12, 4), key=abs):
                i = net.cid((x, door[1] + ddy, z))
                if i >= 0:
                    best = (ddy, i)
                    break
            if best is None:
                a.append(" .")
                b.append(".")
            else:
                a.append(f"{best[0]:+d}" if best[0] else " 0")
                cmp_ = int(net.comp[best[1]])
                b.append("M" if cmp_ == net.main else ("F" if cmp_ == front_comp else "o"))
        if dz == 0:
            b[radius] = "D"
        dyrows.append("".join(f"{t:>3}" for t in a))
        cmprows.append("".join(b))
    res["map_dy_rel_to_door"] = dyrows
    res["map_component"] = cmprows
    res["map_legend"] = "rows = z from door.z-%d..+%d, columns = x from door.x-%d..+%d; M main component, F component in front of the door, o other, . no walkable cell within -12..+3 of the door height, D the door column" % (radius, radius, radius, radius)
    res["door_front"] = {"cell": list(fc) if fc else None, "front_dy": fdy, "front_component": front_comp,
                         "front_component_cells": net.sizes[front_comp] if front_comp is not None else None, "main_component_cells": net.sizes[net.main]}
    # distance from the door-front (or the doorway) to the nearest main-component cell, and the drop it needs
    near, near_level = None, None
    origin = fc or door
    for i in np.flatnonzero(net.comp == net.main):
        c = net.world(int(i))
        d = abs(c[0] - origin[0]) + abs(c[2] - origin[2])
        if d <= 40 and (near is None or d < near["horizontal_manhattan"]):
            near = {"cell": list(c), "horizontal_manhattan": d, "dy": c[1] - origin[1]}
        if d <= 40 and abs(c[1] - origin[1]) <= 1 and (near_level is None or d < near_level["horizontal_manhattan"]):
            near_level = {"cell": list(c), "horizontal_manhattan": d, "dy": c[1] - origin[1]}
    res["nearest_main_cell"] = near
    res["minimum_change"] = {
        "clear_only": min_intervention(net, pieces, pieces[pi]["bb"], door, out, place=False),
        "place_only": min_intervention(net, pieces, pieces[pi]["bb"], door, out, clear=False),
        "clear_and_place": min_intervention(net, pieces, pieces[pi]["bb"], door, out)}
    res["nearest_main_cell_within_1_block_height"] = near_level
    for v in res["minimum_change"].values():
        if v:
            v["place_cell_owners"] = [{"cell": c, "owner_piece": (piece_at(pieces, tuple(c))),
                                       "owner_template": (pieces[piece_at(pieces, tuple(c))]["template"].split("/")[-1] if piece_at(pieces, tuple(c)) is not None else None),
                                       "block_now": g.name(tuple(c))} for c in v["place"]]
    if front_comp is not None and front_comp != net.main:
        res["front_comp_drops_to_main"] = net.main in net.drops.get(front_comp, ())
        res["main_drops_to_front_comp"] = front_comp in net.drops.get(net.main, ())
    return res


def min_intervention(net, pieces, house_bb, door, out, radius=14, clear=True, place=True):
    """Cheapest set of block changes that gives the doorway a two-way walk to the main component (Dijkstra; READ-ONLY, nothing is changed).

    cost 1 per natural body cell cleared (if `clear`), 1 per floor block placed on a missing floor (if `place`); architecture of any
    piece (incl. the house itself) can neither be cleared nor passed. Returns {"cost", "clear", "place"} or None."""
    import heapq
    g = net.g
    nat = np.array([n in E.NATURAL for n in g.names])

    def cell(c, k):                                     # (cost, is_clear) of a body cell, None if impassable
        if not g.inside(c):
            return None
        i = g.ids[g.local(c)]
        if g.F[g.local(c)]:
            return 0
        return 1 if (clear and nat[i]) else None

    def floor(c):
        loc = g.local(c)
        if not g.inside(c):
            return None
        if g.FL[loc]:
            return 0
        if g.F[loc] and place:
            return 1
        return None

    start = door
    dist, prev = {start: 0}, {start: None}
    pq = [(0, start)]
    while pq:
        d, c = heapq.heappop(pq)
        if d > dist.get(c, 1e9):
            continue
        i = net.cid(c)
        if c != start and i >= 0 and int(net.comp[i]) == net.main and d == dist[c]:
            changes_clear, changes_place, cur = [], [], c
            while cur is not None:
                for yy in (0, 1):
                    q = (cur[0], cur[1] + yy, cur[2])
                    if g.inside(q) and not g.F[g.local(q)]:
                        changes_clear.append(list(q))
                fl = (cur[0], cur[1] - 1, cur[2])
                if g.inside(fl) and g.F[g.local(fl)] and cur != start:
                    changes_place.append(list(fl))
                cur = prev[cur]
            return {"cost": d, "clear": sorted(changes_clear), "place": sorted(changes_place), "reached": list(c)}
        for dx, dz in DIRS4:
            for dy in (-1, 0, 1):
                n = (c[0] + dx, c[1] + dy, c[2] + dz)
                if abs(n[0] - door[0]) > radius or abs(n[2] - door[2]) > radius or _in_box(house_bb, n):
                    continue
                costs = [cell(n, 0), cell((n[0], n[1] + 1, n[2]), 1), floor((n[0], n[1] - 1, n[2]))]
                if dy == 1:
                    costs.append(cell((c[0], c[1] + 2, c[2]), 1))
                if c == start and (dx, dz) != (out[0], out[2]):
                    continue
                if any(x is None for x in costs):
                    continue
                nd = d + sum(costs)
                if nd < dist.get(n, 1e9):
                    dist[n], prev[n] = nd, c
                    heapq.heappush(pq, (nd, n))
    return None


def _in_box(bb, c):
    return bb[0] <= c[0] <= bb[3] and bb[1] <= c[1] <= bb[4] and bb[2] <= c[2] <= bb[5]


def survey_equal(a, b):
    keys = ("seed", "piece_index", "module", "rotation", "door_world", "outward", "status", "n_cells", "cells_to_clear", "path")
    return all(a[k] == b[k] for k in keys)


def reproduce_survey(seeds, manifests: Path, baseline_path: Path):
    base = {(r["seed"], r["piece_index"], tuple(r["door_world"])): r for r in json.loads(baseline_path.read_text())}
    rows = []
    for s in seeds:
        rows += E.survey(s, VARIANT, manifests)
    res = {"observations": len(rows), "baseline_observations": len([k for k in base if k[0] in set(seeds)]), "identical": 0, "differences": []}
    for r in rows:
        k = (r["seed"], r["piece_index"], tuple(r["door_world"]))
        if k in base and survey_equal(r, base[k]):
            res["identical"] += 1
        else:
            res["differences"].append({"key": list(k[:2]) + list(k[2]), "new": r["status"], "baseline": base.get(k, {}).get("status")})
    return rows, res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifests", required=True, help="directory with manifest-<seed>-k24.json of the regenerated sweep")
    ap.add_argument("--out", required=True, help="output directory for the JSON evidence")
    ap.add_argument("--seeds", type=int, nargs="*", default=list(range(24001, 24025)))
    ap.add_argument("--skip-survey", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    manifests = Path(a.manifests)
    if not a.skip_survey:
        rows, res = reproduce_survey(a.seeds, manifests, AR / "stage-24k/worldgen/k24-entrance-survey.json")
        (out / "survey-reproduction.json").write_text(json.dumps({"summary": res, "rows": rows}, indent=1))
        print("survey reproduction:", {k: v for k, v in res.items() if k != "differences"}, "differences", len(res["differences"]), flush=True)
    if not a.skip_survey:
        for s in FOCUS:
            if s in a.seeds:
                f = focus_case(s, manifests, rows)
                (out / f"focus-{s}.json").write_text(json.dumps(f, indent=1))
                print("focus", s, f["obstruction_summary"], f["door_front"], f["nearest_main_cell"], flush=True)
    for s in a.seeds:
        r = measure_seed(s, manifests)
        (out / f"seed-{s}.json").write_text(json.dumps(r, indent=1))
        st = Counter(d["status"] for d in r["doors"])
        print(s, "walkable", r["walkable_cells"], "components", r["n_components"], "main_share", r["main_share"], dict(st), flush=True)


if __name__ == "__main__":
    main()
