"""Room-building DSL shared by the SG-03 lower and upper room modules.

Room frame: ``x`` lateral (0..W-1), ``y`` up (floor y=0), ``z`` depth. The entry doorway is on the
south wall (``z = D-1``) centred on ``x = W // 2``; the room extends north (toward z=0). All output is
deterministic: damage and variation use a seeded ``random.Random`` consumed in a fixed order.
"""

from __future__ import annotations

import random
from typing import Callable, Iterable

from kingdom_common import Entities, new_grid, place_jigsaw, set_block, stairs
from mcbuild.palette import get_block_by_index

DIRS = ("north", "east", "south", "west")
CW = {"north": "east", "east": "south", "south": "west", "west": "north"}
CCW = {v: k for k, v in CW.items()}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
DELTA = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}

Choice = str | Callable[[], str]


class Room:
    def __init__(self, size: tuple[int, int, int], seed: int):
        self.size = size
        self.w, self.h, self.d = size
        self.grid = new_grid(size)
        self.entities: Entities = {}
        self.rng = random.Random(seed)

    # --- primitives --------------------------------------------------------------------------
    def inside(self, x: int, y: int, z: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h and 0 <= z < self.d

    def put(self, x: int, y: int, z: int, block: Choice) -> None:
        if not self.inside(x, y, z):
            raise ValueError(f"block outside room {self.size}: {(x, y, z)} {block}")
        self.entities.pop((x, y, z), None)  # an overwritten block drops its block entity
        set_block(self.grid, x, y, z, block() if callable(block) else block)

    def get(self, x: int, y: int, z: int) -> str:
        index = self.grid.get(x, y, z)
        return "air" if index is None else get_block_by_index(index).name

    def fill(self, x0: int, y0: int, z0: int, x1: int, y1: int, z1: int, block: Choice) -> None:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                for x in range(min(x0, x1), max(x0, x1) + 1):
                    self.put(x, y, z, block)

    def clear(self, x0: int, y0: int, z0: int, x1: int, y1: int, z1: int) -> None:
        self.fill(x0, y0, z0, x1, y1, z1, "air")

    def weighted(self, *pairs: tuple[str, int]) -> Callable[[], str]:
        names = [p[0] for p in pairs]
        weights = [p[1] for p in pairs]
        return lambda: self.rng.choices(names, weights)[0]

    def stair(self, x: int, y: int, z: int, facing: str, *, half: str = "bottom", material: str = "deepslate_brick_stairs") -> None:
        self.put(x, y, z, stairs(facing, half=half, material=material))

    def slab(self, x: int, y: int, z: int, material: str = "deepslate_brick_slab", *, kind: str = "bottom") -> None:
        self.put(x, y, z, f"{material}[type={kind},waterlogged=false]")

    def chest(self, x: int, y: int, z: int, facing: str, loot: str | None = None) -> None:
        self.put(x, y, z, f"chest[facing={facing},type=single,waterlogged=false]")
        entity: dict[str, object] = {"id": "minecraft:chest"}
        if loot:
            entity["LootTable"] = loot
        self.entities[(x, y, z)] = entity

    def barrel(self, x: int, y: int, z: int, facing: str = "up", loot: str | None = None) -> None:
        self.put(x, y, z, f"barrel[facing={facing},open=false]")
        entity: dict[str, object] = {"id": "minecraft:barrel"}
        if loot:
            entity["LootTable"] = loot
        self.entities[(x, y, z)] = entity

    def bed(self, x: int, y: int, z: int, facing: str, color: str = "gray") -> None:
        """Foot at (x,y,z); the head is one block toward ``facing``."""
        dx, dz = DELTA[facing]
        self.put(x, y, z, f"{color}_bed[facing={facing},occupied=false,part=foot]")
        self.put(x + dx, y, z + dz, f"{color}_bed[facing={facing},occupied=false,part=head]")

    def lantern(self, x: int, y: int, z: int, *, hanging: bool = False, soul: bool = False) -> None:
        name = "soul_lantern" if soul else "lantern"
        self.put(x, y, z, f"{name}[hanging={'true' if hanging else 'false'},waterlogged=false]")

    def hang_lantern(self, x: int, y_top: int, z: int, length: int, *, soul: bool = False) -> None:
        """Chain of ``length`` links down from ``y_top`` with a lantern on the end."""
        for i in range(length):
            self.put(x, y_top - i, z, "chain[axis=y,waterlogged=false]")
        self.lantern(x, y_top - length, z, hanging=True, soul=soul)

    def pillar(self, x0: int, z0: int, x1: int, z1: int, y0: int, y1: int, *, base: str = "polished_deepslate",
               shaft: str = "deepslate_bricks", cap: str = "chiseled_tuff_bricks") -> None:
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.put(x, y0, z, base)
                for y in range(y0 + 1, y1):
                    self.put(x, y, z, shaft)
                self.put(x, y1, z, cap)

    def arch_x(self, x0: int, x1: int, z: int, y_top: int, *, material: str = "deepslate_bricks") -> None:
        """Arch in the x-z plane spanning the opening x0..x1 at depth z; lintel row at y_top."""
        for x in range(x0, x1 + 1):
            self.put(x, y_top, z, material)
        self.stair(x0, y_top - 1, z, "west", half="top")
        self.stair(x1, y_top - 1, z, "east", half="top")

    def arch_z(self, z0: int, z1: int, x: int, y_top: int, *, material: str = "deepslate_bricks") -> None:
        """Arch spanning z0..z1 at lateral position x; lintel row at y_top."""
        for z in range(z0, z1 + 1):
            self.put(x, y_top, z, material)
        self.stair(x, y_top - 1, z0, "north", half="top")
        self.stair(x, y_top - 1, z1, "south", half="top")

    def scatter(self, cells: Iterable[tuple[int, int, int]], block: Choice, chance: float) -> None:
        for cell in cells:
            if self.rng.random() < chance:
                self.put(*cell, block)

    # --- standard shell ------------------------------------------------------------------------
    def shell(self, *, floor: Choice, wall: Choice, roof: Choice, band: tuple[int, str] | None = None) -> None:
        w, h, d = self.size
        for x in range(w):
            for z in range(d):
                self.put(x, 0, z, floor)
                self.put(x, h - 1, z, roof)
        for y in range(1, h - 1):
            for x in range(w):
                for z in (0, d - 1):
                    self.put(x, y, z, wall)
            for z in range(d):
                for x in (0, w - 1):
                    self.put(x, y, z, wall)
        if band:
            y, material = band
            for x in range(w):
                for z in (0, d - 1):
                    self.put(x, y, z, material)
            for z in range(d):
                for x in (0, w - 1):
                    self.put(x, y, z, material)

    def door(self, width: int, height: int, entry: str, *, thickness: int = 1) -> None:
        cx = self.w // 2
        for dz in range(thickness):
            for dx in range(-(width // 2), width // 2 + 1):
                for y in range(1, height + 1):
                    self.put(cx + dx, y, self.d - 1 - dz, "air")
        place_jigsaw(self.grid, self.entities, (cx, 1, self.d - 1), orientation="south_up",
                     name=entry, target="minecraft:empty", pool="minecraft:empty")

    def trim_door(self, width: int, height: int, *, jamb: str = "polished_deepslate", lintel: str = "chiseled_deepslate", z: int | None = None) -> None:
        cx = self.w // 2
        z = self.d - 1 if z is None else z
        half = width // 2
        for y in range(1, height + 1):
            self.put(cx - half - 1, y, z, jamb)
            self.put(cx + half + 1, y, z, jamb)
        for dx in range(-half - 1, half + 2):
            self.put(cx + dx, height + 1, z, lintel)

    # --- finishing ----------------------------------------------------------------------------
    def finish(self):
        finish_stairs(self.grid)
        finish_connectables(self.grid)
        return self.grid, self.entities


def _state_of(grid, pos):
    index = grid.get(*pos)
    if index is None:
        return None, {}
    block = get_block_by_index(index)
    return block.name, dict(block.state)


def finish_stairs(grid) -> None:
    """Recompute stair ``shape`` exactly as vanilla's StairBlock would from neighbouring stairs."""
    stair_cells = {}
    for pos, index in grid.items():
        block = get_block_by_index(index)
        if block.name.endswith("_stairs"):
            stair_cells[pos] = (block.name, dict(block.state))

    def is_stairs(pos, half):
        other = stair_cells.get(pos)
        return other if other and other[1].get("half") == half else None

    for (x, y, z), (name, props) in stair_cells.items():
        facing, half = props["facing"], props["half"]
        fx, fz = DELTA[facing]
        shape = "straight"
        front = is_stairs((x + fx, y, z + fz), half)
        if front and DIRS.index(front[1]["facing"]) % 2 != DIRS.index(facing) % 2:
            dir1 = front[1]["facing"]
            nx, nz = DELTA[OPP[dir1]]
            same = stair_cells.get((x + nx, y, z + nz))
            if not (same and same[1]["facing"] == facing and same[1]["half"] == half):
                shape = "outer_left" if dir1 == CCW[facing] else "outer_right"
        if shape == "straight":
            back = is_stairs((x - fx, y, z - fz), half)
            if back and DIRS.index(back[1]["facing"]) % 2 != DIRS.index(facing) % 2:
                dir2 = back[1]["facing"]
                nx, nz = DELTA[dir2]
                same = stair_cells.get((x + nx, y, z + nz))
                if not (same and same[1]["facing"] == facing and same[1]["half"] == half):
                    shape = "inner_left" if dir2 == CCW[facing] else "inner_right"
        if shape != props["shape"]:
            set_block(grid, x, y, z, stairs(facing, half=half, shape=shape, material=name))


_NOT_FULL = ("stairs", "slab", "_wall", "jigsaw", "lantern", "fence", "door", "trapdoor", "bars", "button", "carpet",
             "bed", "pot", "chain", "candle", "cobweb", "ladder", "campfire", "cauldron", "lectern", "anvil",
             "grindstone", "torch", "pane", "head", "skull", "sign", "banner", "plate", "pressure", "air",
             "heavy_core", "vine", "azalea", "blossom", "chest")


def _is_full(name: str | None) -> bool:
    """True for blocks whose side faces are full-square (vanilla's ``isFaceSturdy``) in this build's palette."""
    return name is not None and not any(token in name for token in _NOT_FULL)


def _connects(name: str | None) -> bool:
    """Vanilla wall/iron-bars attachment: walls, iron bars and sturdy full faces."""
    return name is not None and (name.endswith("_wall") or name == "iron_bars" or _is_full(name))


def finish_connectables(grid) -> None:
    """Set connection states for deepslate-family walls and iron bars the way vanilla derives them."""
    names = {pos: get_block_by_index(i).name for pos, i in grid.items()}
    for pos, name in list(names.items()):
        x, y, z = pos
        if name.endswith("_wall"):
            above = names.get((x, y + 1, z))
            arm = "tall" if _is_full(above) else "low"
            sides = {side: (arm if _connects(names.get((x + dx, y, z + dz))) else "none") for side, (dx, dz) in DELTA.items()}
            n, e, s, w = (sides[k] != "none" for k in ("north", "east", "south", "west"))
            straight = (n and s and not e and not w) or (e and w and not n and not s)
            up = (not straight) or (above is not None and above.endswith("_wall"))
            set_block(grid, x, y, z,
                      f"{name}[east={sides['east']},north={sides['north']},south={sides['south']},"
                      f"up={'true' if up else 'false'},waterlogged=false,west={sides['west']}]")
        elif name == "iron_bars":
            flags = {side: ("true" if _connects(names.get((x + dx, y, z + dz))) else "false") for side, (dx, dz) in DELTA.items()}
            set_block(grid, x, y, z,
                      f"iron_bars[east={flags['east']},north={flags['north']},south={flags['south']},"
                      f"waterlogged=false,west={flags['west']}]")
