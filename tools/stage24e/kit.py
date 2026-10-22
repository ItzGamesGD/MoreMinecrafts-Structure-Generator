"""Stage 24-E design kit: editable copy of a final Stage 24-C house NBT with roof/massing helpers.

Proposals never touch the Stage 24-C files: each Variant loads the final NBT, edits an in-memory block map and
writes a new NBT elsewhere. Jigsaws and block entities from the source are locked (any edit raises).
"""
from __future__ import annotations

import copy
from pathlib import Path

import nbtlib
from nbtlib import tag

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import S24B, load_nbt, state_str  # noqa: E402

AIR = "minecraft:air"
DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
CCW = {"north": "west", "west": "south", "south": "east", "east": "north"}
TILE_ST = "deepslate_tile_stairs"
BRICK = "deepslate_bricks"
TILE = "deepslate_tiles"
POL = "polished_deepslate"


def mc(s):
    return s if s.startswith("minecraft:") else "minecraft:" + s


def props(state):
    if "[" not in state:
        return {}
    return dict(p.split("=", 1) for p in state.split("[", 1)[1].rstrip("]").split(","))


def with_props(name, kv):
    return mc(name) + ("[" + ",".join(f"{k}={v}" for k, v in sorted(kv.items())) + "]" if kv else "")


def stair(facing, half="bottom", mat=TILE_ST):
    return with_props(mat, {"facing": facing, "half": half, "shape": "straight", "waterlogged": "false"})


def slab(kind="bottom", mat="polished_deepslate_slab"):
    return with_props(mat, {"type": kind, "waterlogged": "false"})


class Locked(Exception):
    pass


class Variant:
    def __init__(self, module: str, variant: str, title: str, src: Path | None = None):
        self.module, self.variant, self.title = module, variant, title
        self.src = src or (S24B / module / "restored.nbt")
        self.root = load_nbt(self.src)
        self.orig_size = tuple(int(v) for v in self.root["size"])
        self.size = list(self.orig_size)
        pal = [state_str(p) for p in self.root["palette"]]
        self.blocks = {}   # pos -> state string
        self.nbt = {}      # pos -> nbt compound (locked)
        for b in self.root["blocks"]:
            pos = tuple(int(v) for v in b["pos"])
            self.blocks[pos] = pal[int(b["state"])]
            if "nbt" in b:
                self.nbt[pos] = b["nbt"]
        self.locked = set(self.nbt)
        self.src_air = {p for p, s in self.blocks.items() if s == AIR}
        self.notes = []

    # ---- basic access ----
    def get(self, p):
        return self.blocks.get(tuple(p), AIR)

    def get_block(self, p):  # duck-typed for tools/validate_stage24b.standable/reachable
        return self.get(p)

    def name(self, p):
        return self.get(p).split("[")[0].replace("minecraft:", "")

    def set(self, p, state):
        p = tuple(p)
        if p in self.locked:
            if self.get(p) == mc(state):
                return
            raise Locked(f"{self.module}/{self.variant}: protected block at {p}")
        if any(c < 0 for c in p) or p[0] >= self.size[0] or p[2] >= self.size[2]:
            raise ValueError(f"{p} outside footprint {self.size}")
        if p[1] >= self.size[1]:
            self.size[1] = p[1] + 1   # height grows; recorded as a proposal requiring authorization
        if mc(state) == AIR:
            # keep explicit air only where the source carried it; elsewhere an absent cell does not carve terrain
            if p in self.src_air:
                self.blocks[p] = AIR
            else:
                self.blocks.pop(p, None)
        else:
            self.blocks[p] = mc(state)

    def clear(self, p):
        self.set(p, AIR)

    def is_solid(self, p):
        n = self.name(p)
        return n not in ("air", "water", "jigsaw", "ladder", "soul_lantern", "iron_chain") and not n.endswith(("_door", "_bed"))

    def fill(self, x0, y0, z0, x1, y1, z1, state):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set((x, y, z), state)

    # ---- massing helpers ----
    def raise_walls(self, from_y, to_y, top_y, material=None):
        """extend every column that is solid at from_y (walls/partitions) up to top_y with the same (or given) material"""
        cols = [(x, z) for (x, y, z), s in list(self.blocks.items()) if y == from_y and self.is_solid((x, y, z))]
        for x, z in cols:
            src = self.get((x, from_y, z)) if material is None else mc(material)
            if "stairs" in src or "slab" in src:
                src = mc(BRICK)
            for y in range(to_y, top_y + 1):
                self.set((x, y, z), src)

    def clear_layer(self, y, keep=lambda p: False):
        for p in [p for p in list(self.blocks) if p[1] == y]:
            if not keep(p) and p not in self.locked:
                self.clear(p)

    def roof_surface(self, cells, height_of, base_y, top_block=TILE, mat=TILE_ST, fill_under=False, ridge=None):
        """cells: iterable (x,z); height_of(x,z) -> integer step h; stairs face toward the higher neighbour."""
        cells = set(cells)
        H = {c: height_of(*c) for c in cells}
        for (x, z), h in H.items():
            best, bd = None, None
            for d, (dx, dz) in DIRS.items():
                n = (x + dx, z + dz)
                if n in H and H[n] > h and (best is None or H[n] > best):
                    best, bd = H[n], d
            y = base_y + h
            if bd is None:   # local maximum: ridge cell
                self.set((x, y, z), ridge or top_block)
            else:
                self.set((x, y, z), stair(bd, mat=mat))
            if fill_under:
                for yy in range(base_y, y):
                    self.set((x, yy, z), top_block)
        return H

    def gable_fill(self, x_or_z, axis, coord, lo, hi, base_y, profile, material=BRICK):
        """fill a gable-end triangle in the vertical plane axis=coord: profile(t) gives the roof y at position t"""
        for t in range(lo, hi + 1):
            top = profile(t)
            for y in range(base_y, top):
                p = (coord, y, t) if axis == "x" else (t, y, coord)
                if self.get(p) == AIR or p not in self.blocks:
                    self.set(p, material)

    # ---- finishing passes ----
    def fix_stair_shapes(self):
        """vanilla StairBlock.getStairsShape for every non-protected stair"""
        def st(p):
            s = self.get(p)
            return props(s) if s.split("[")[0].endswith("_stairs") else None
        for p, s in list(self.blocks.items()):
            if p in self.locked or not s.split("[")[0].endswith("_stairs"):
                continue
            pr = props(s)
            f, half = pr["facing"], pr["half"]
            shape = "straight"
            dx, dz = DIRS[f]
            behind = st((p[0] + dx, p[1], p[2] + dz))
            front = st((p[0] - dx, p[1], p[2] - dz))

            def can_take(face):
                ddx, ddz = DIRS[face]
                n = st((p[0] + ddx, p[1], p[2] + ddz))
                return n is None or n["facing"] != f or n["half"] != half
            if behind and behind["half"] == half and behind["facing"] not in (f, OPP[f]) and can_take(OPP[behind["facing"]]):
                shape = "outer_left" if behind["facing"] == CCW[f] else "outer_right"
            elif front and front["half"] == half and front["facing"] not in (f, OPP[f]) and can_take(front["facing"]):
                shape = "inner_left" if front["facing"] == CCW[f] else "inner_right"
            pr["shape"] = shape
            self.blocks[p] = with_props(s.split("[")[0], pr)

    def fix_walls(self):
        names = ("_wall",)
        for p, s in list(self.blocks.items()):
            n = s.split("[")[0]
            if p in self.locked or not n.endswith("_wall"):
                continue
            conn = {}
            for d, (dx, dz) in DIRS.items():
                q = (p[0] + dx, p[1], p[2] + dz)
                conn[d] = self.get(q).split("[")[0].endswith("_wall") or (self.is_solid(q) and self.get(q) != AIR)
            straight = (conn["north"] and conn["south"] and not conn["east"] and not conn["west"]) or \
                       (conn["east"] and conn["west"] and not conn["north"] and not conn["south"])
            kv = {d: ("low" if conn[d] else "none") for d in DIRS}
            kv.update({"up": "false" if straight and self.get((p[0], p[1] + 1, p[2])) == AIR else "true", "waterlogged": "false"})
            self.blocks[p] = with_props(n, kv)

    def fix_lanterns(self, chain_reach=6):
        """every soul lantern must stand on a block or hang from one; if its ceiling moved up, hang it on an iron chain"""
        for p, s in sorted(self.blocks.items()):
            if s.split("[")[0] != "minecraft:soul_lantern" or p in self.locked:
                continue
            x, y, z = p
            if props(s).get("hanging") == "true":
                if self.is_solid((x, y + 1, z)):
                    continue
                for k in range(1, chain_reach + 1):
                    if self.is_solid((x, y + k, z)):
                        for yy in range(y + 1, y + k):
                            self.set((x, yy, z), with_props("iron_chain", {"axis": "y", "waterlogged": "false"}))
                        self.notes.append(f"lantern {p} hung on {k - 1} chain block(s) from the new roof")
                        break
                else:
                    raise ValueError(f"{self.module}/{self.variant}: lantern {p} lost its ceiling")
            elif not self.is_solid((x, y - 1, z)):
                raise ValueError(f"{self.module}/{self.variant}: standing lantern {p} lost its floor")

    def finish(self):
        self.fix_stair_shapes()
        self.fix_walls()
        self.fix_lanterns()

    # ---- output ----
    def save(self, path: Path):
        root = copy.deepcopy(self.root)
        pal, idx, out = [], {}, []
        for pos in sorted(self.blocks, key=lambda p: (p[1], p[2], p[0])):
            s = self.blocks[pos]
            if s not in idx:
                idx[s] = len(pal)
                name, kv = s.split("[")[0], props(s)
                c = tag.Compound({"Name": tag.String(name)})
                if kv:
                    c["Properties"] = tag.Compound({k: tag.String(v) for k, v in kv.items()})
                pal.append(c)
            b = tag.Compound({"pos": tag.List[tag.Int](list(pos)), "state": tag.Int(idx[s])})
            if pos in self.nbt:
                b["nbt"] = self.nbt[pos]
            out.append(b)
        root["size"] = tag.List[tag.Int](self.size)
        root["palette"] = tag.List[tag.Compound](pal)
        root["blocks"] = tag.List[tag.Compound](out)
        path.parent.mkdir(parents=True, exist_ok=True)
        root.save(path, gzipped=True)
        return path

    @property
    def expanded(self):
        return tuple(self.size) != self.orig_size
