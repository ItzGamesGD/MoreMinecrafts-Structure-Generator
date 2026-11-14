"""Fixed-coordinate batch assembly of the ST-03 placements in one global structure frame.

The placement table (`data/st03_placements.json`) is the q=0 masterplan of ST03_PHASE_B2_V2_AUDIT_20261029.zip
(DESIGN_PACKAGE_V2.md D6): 25 module templates, 34 placements, a 112 x 112 box. For a whole-structure quarter turn q
(0..3, clockwise seen from above, x east, z south, no mirroring) the structure is anchored with its rotated box at (0, 0).
`manifest(q)` re-derives origin, rotation and footprint of every placement from that table; the committed design manifests
(`tests/fixtures/seam01_design_manifests.json`) are the independent reference it is tested against.
"""

# ruff: noqa: E501
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from tools.structure_export.live import rotate_props

DATA = Path(__file__).resolve().parent / "data" / "st03_placements.json"
ROT_NAME = {0: "none", 1: "clockwise_90", 2: "180", 3: "counterclockwise_90"}
# StructureTemplate rotation of a template cell about its origin (x east, z south)
ROT = {0: lambda x, z: (x, z), 1: lambda x, z: (-z, x), 2: lambda x, z: (-x, -z), 3: lambda x, z: (z, -x)}
Pos = tuple[int, int, int]


@cache
def plan() -> dict:
    return json.loads(DATA.read_text())


def box_size() -> int:
    return plan()["box"]


def rot_cell(x: int, z: int, q: int) -> tuple[int, int]:
    """Quarter turns clockwise of a cell inside the N x N box: (x, z) -> (N-1-z, x)."""
    n = box_size()
    for _ in range(q % 4):
        x, z = n - 1 - z, x
    return x, z


def rot_rect(r, q: int):
    a, b = rot_cell(r[0], r[1], q), rot_cell(r[2], r[3], q)
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))


def origin_for(rect, turns: int, w: int, d: int) -> tuple[int, int]:
    """Template origin so that the template rotated by `turns` fills `rect` (the footprint after rotation)."""
    x0, z0 = rect[0], rect[1]
    return {0: (x0, z0), 1: (x0 + d - 1, z0), 2: (x0 + w - 1, z0 + d - 1), 3: (x0, z0 + w - 1)}[turns % 4]


def modules() -> dict[str, dict]:
    return {m["id"]: m for m in plan()["modules"]}


def manifest(q: int) -> list[dict]:
    """The 34 placements for whole-structure rotation q, in assembly order (order, placement id)."""
    mods, out = modules(), []
    for p in plan()["placements"]:
        m = mods[p["module"]]
        w, h, d = m["size"]
        turns = (p["local_turns"] + q) % 4
        rect = rot_rect(p["rect"], q)
        ox, oz = origin_for(rect, turns, w, d)
        out.append(
            {
                "placement": p["placement"],
                "module": m["id"],
                "file": f"{m['file']}.nbt",
                "order": m["order"],
                "rotation": ROT_NAME[turns],
                "origin": [ox, 0, oz],
                "size": [w, h, d],
                "footprint": list(rect),
                "air": m["air"],
            }
        )
    out.sort(key=lambda e: (e["order"], e["placement"]))
    return out


def height() -> int:
    return max(m["size"][1] for m in plan()["modules"])


def place_cell(entry: dict, cell: Pos) -> Pos:
    """Template cell -> structure frame for one manifest entry (StructureTemplate.transform + origin)."""
    turns = {v: k for k, v in ROT_NAME.items()}[entry["rotation"]]
    dx, dz = ROT[turns](cell[0], cell[2])
    return (entry["origin"][0] + dx, cell[1] + entry["origin"][1], entry["origin"][2] + dz)


def place_props(entry: dict, props: dict[str, str]) -> dict[str, str]:
    return rotate_props(props, entry["rotation"])


def assemble(q: int, templates: dict[str, dict[Pos, tuple[str, dict[str, str]]]]):
    """Place every template cell in manifest order, like `place template` (strict) does.

    `templates[module id]` holds template cells {(u, y, v): (block id, props)}; minecraft:air entries clear the cell.
    A module with air = "include" first clears its whole box. Returns {pos: (block id, props)} without air cells, and
    {pos: placement id} owner of every written cell (last writer wins).
    """
    cells: dict[Pos, tuple[str, dict[str, str]]] = {}
    owner: dict[Pos, str] = {}
    for e in manifest(q):
        w, h, d = e["size"]
        if e["air"] == "include":
            for u in range(w):
                for v in range(d):
                    for y in range(h):
                        p = place_cell(e, (u, y, v))
                        cells.pop(p, None)
                        owner[p] = e["placement"]
        for cell, (bid, props) in templates[e["module"]].items():
            p = place_cell(e, cell)
            if bid == "minecraft:air":
                cells.pop(p, None)
            else:
                cells[p] = (bid, place_props(e, props))
            owner[p] = e["placement"]
    return cells, owner
