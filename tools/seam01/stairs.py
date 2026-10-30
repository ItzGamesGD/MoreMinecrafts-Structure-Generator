"""Vanilla stair shape rule (StairBlock.getStairsShape), used only to REPORT seam-dependent stairs.

SEAM-01 never overwrites an authored stair shape (STAIR-01 contract). This rule tells which stairs the game would shape
differently once the neighbouring module is present. The rule is checked against the real 26.3 server in `live.py`.
"""

from __future__ import annotations

STEP = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0)}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
AXIS = {"north": "z", "south": "z", "east": "x", "west": "x"}
CCW = {"north": "west", "west": "south", "south": "east", "east": "north"}


def is_stairs(cell) -> bool:
    return cell is not None and cell[0].endswith("_stairs")


def _at(pos, direction):
    d = STEP[direction]
    return (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])


def _can_take(cells, pos, state, face) -> bool:
    n = cells.get(_at(pos, face))
    return not is_stairs(n) or n[1]["facing"] != state["facing"] or n[1]["half"] != state["half"]


def stairs_shape(cells, pos) -> str:
    """The shape the game computes for the stair at `pos` from its neighbours in `cells` (missing = air)."""
    state = cells[pos][1]
    facing = state["facing"]
    front = cells.get(_at(pos, facing))
    if is_stairs(front) and front[1]["half"] == state["half"]:
        d2 = front[1]["facing"]
        if AXIS[d2] != AXIS[facing] and _can_take(cells, pos, state, OPPOSITE[d2]):
            return "outer_left" if d2 == CCW[facing] else "outer_right"
    back = cells.get(_at(pos, OPPOSITE[facing]))
    if is_stairs(back) and back[1]["half"] == state["half"]:
        d3 = back[1]["facing"]
        if AXIS[d3] != AXIS[facing] and _can_take(cells, pos, state, d3):
            return "inner_left" if d3 == CCW[facing] else "inner_right"
    return "straight"
