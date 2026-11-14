"""Synthetic module contents for the 25 ST-03 templates.

SYNTHETIC: no ST-03 NBT exists yet (design only). Every module gets a deterministic ring of connecting blocks, stairs and sturdy
blocks along its template perimeter, so each place where two footprints touch exercises the seam rules. This is a stress
fixture for the generator and the applier, not ST-03 content.
"""

# ruff: noqa: E501
from __future__ import annotations

import zlib

from . import assembly as A
from .stairs import stairs_shape

KINDS = (
    ("minecraft:stone_brick_wall", 2),
    ("minecraft:oak_fence", 1),
    ("minecraft:iron_bars", 1),
    ("minecraft:glass_pane", 1),
    ("minecraft:cobblestone_wall", 2),
    ("minecraft:oak_fence_gate", 1),
)
STONE = "minecraft:stone_bricks"
STAIR = "minecraft:stone_brick_stairs"


def ring(w: int, d: int) -> list[tuple[int, int]]:
    out = [(u, 0) for u in range(w)]
    out += [(w - 1, v) for v in range(1, d)]
    out += [(u, d - 1) for u in range(w - 2, -1, -1)]
    out += [(0, v) for v in range(d - 2, 0, -1)]
    return out


def source(module: dict) -> dict[tuple[int, int, int], tuple[str, dict[str, str]]]:
    """Template cells {(u, y, v): (block id, stated props)} of one module in its own frame."""
    w, h, d = module["size"]
    seed = zlib.crc32(module["id"].encode())
    cells: dict = {}
    cycle = [k for k, _ in KINDS]
    cells_ring = ring(w, d)
    for i, (u, v) in enumerate(cells_ring):
        run = (i // 5 + seed) % len(cycle)
        if i % 11 == 6:
            cells[(u, 1, v)] = (STONE, {})
        elif i % 7 in (3, 5):
            side = 0 if v == 0 else 1 if u == w - 1 else 2 if v == d - 1 else 3
            inward = ("south", "west", "north", "east")[side]  # i % 7 == 3: faces into the module
            along = ("east", "south", "west", "north")[side]  # i % 7 == 5: faces along the edge (corner partner)
            facing = inward if i % 7 == 3 else along
            half = "bottom" if (i // 7) % 2 == 0 else "top"
            cells[(u, 1, v)] = (STAIR, {"facing": facing, "half": half, "shape": "straight"})
        else:
            kind = cycle[run]
            if kind.endswith("fence_gate"):
                cells[(u, 1, v)] = (kind, {"facing": "north" if v in (0, d - 1) else "east"})
            else:
                cells[(u, 1, v)] = (kind, {})
                if "wall" in kind and h > 3:
                    cells[(u, 2, v)] = (kind, {})
    mid_u, mid_v = w // 2, d // 2
    for k in range(-1, 2):  # a module-internal wall line (no seam involved)
        if 1 <= mid_u + k < w - 1:
            cells[(mid_u + k, 1, mid_v)] = ("minecraft:stone_brick_wall", {})
    # author the stair shapes the game would give each stair in its module alone (no authored/vanilla gap inside a module)
    full = {
        p: (b, {"facing": "north", "half": "bottom", "shape": "straight", **pr}) if b == STAIR else (b, pr)
        for p, (b, pr) in cells.items()
    }
    for p, (b, _) in list(full.items()):
        if b == STAIR:
            cells[p] = (b, {**cells[p][1], "shape": stairs_shape(full, p)})
    return cells


def sources() -> dict[str, dict]:
    return {m["id"]: source(m) for m in A.plan()["modules"]}
