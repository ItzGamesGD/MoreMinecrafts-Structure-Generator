"""Neighbour-dependent block states: what vanilla 26.3 would compute for walls, fences, panes/bars and
fence gates from the other blocks of the template.

Why: jigsaw world generation places pool elements with StructurePlaceSettings.knownShape = true and
update flags 18 (SinglePoolElement), so the game writes template states as they are and never runs
the neighbour shape update (`/place template ... strict` is the same: flags 2|816). A wall that
mcbuild wrote as a bare `stone_brick_wall` therefore generates as a lone post unless the template
already carries its connections.

The rules are transcribed from the 26.3 server classes (unobfuscated; decompiled for reading):
- WallBlock.connectsTo / updateShape / shouldRaisePost / makeWallState      -> _wall
- FenceBlock.connectsTo / isSameFence                                     -> _fence
- IronBarsBlock.attachsTo (glass panes, stained panes, iron and copper bars) -> _bars
- FenceGateBlock.updateShape (in_wall) and connectsToDirection             -> _fence_gate, _gate_connects
- Block.isExceptionForConnection                                          -> Facts.exception
Everything those rules read about a neighbour (isFaceSturdy, the collision shape's DOWN face against
WallBlock's test shapes, instanceof checks, block tags) comes from reference/connectivity-<v>.json,
which build_connectivity.py generates from the server jar. Nothing here is a hand-made table.

Only properties the source left out are computed; a property the source states is kept as written.
The result is the state the game itself settles on (Block.updateFromNeighbourShapes on every block):
none of the four rules reads the block below, the side rules read only facts that the computed
properties cannot change (checked when the reference is built), and walls read the block above, so
resolving from the top layer down sees every neighbour in its final state in one pass.

A neighbour outside the template box, or an air cell dropped by `air = "omit"`, is world terrain
that is unknown at conversion time; it is treated as air (no connection, nothing above) and every
block whose result depended on it is listed in the report. A neighbour whose relevant shape depends
on its position or block entity (offset or dynamic-shape blocks) makes only the property that
depends on it unresolved, never the whole block: that property keeps its default and the block is
listed with the reason, while every property that does not depend on it is still computed. In
particular a wall whose block above has a position-dependent shape still connects to its wall
neighbours (a connection never depends on the block above); only the height of those connections
(tall/low, assumed `low`) and the post (`up`, kept at the default) are unresolved. This keeps the
result symmetric: a neighbour that connects to this block is connected back (verify.py checks it).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
SIDES = ("north", "east", "south", "west")
STEP = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0), "up": (0, 1, 0)}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
AXIS = {"north": "z", "south": "z", "east": "x", "west": "x"}
CLOCKWISE = {"north": "east", "east": "south", "south": "west", "west": "north"}
KINDS = ("wall", "fence", "bars", "fence_gate")
COMPUTED = {
    "wall": ("north", "east", "south", "west", "up"),
    "fence": SIDES,
    "bars": SIDES,
    "fence_gate": ("in_wall",),
}

Cell = tuple[str, dict[str, str]]
Pos = tuple[int, int, int]


@cache
def load_connectivity(target: str) -> dict:
    return json.loads((REFERENCE_DIR / f"connectivity-{target}.json").read_text())


@dataclass(frozen=True)
class Facts:
    """What the connection rules may read about one block state."""

    block_id: str
    kinds: frozenset[str]
    tags: frozenset[str]
    sturdy: dict[str, bool]  # isFaceSturdy per horizontal side
    covers: dict[str, bool]  # WallBlock.isCovered of the DOWN face: "post" and per side
    sturdy_exact: bool  # False for dynamic-shape blocks (no shape cache; level-dependent)
    covers_exact: bool  # False for dynamic-shape and offset blocks (position-dependent collision)

    @property
    def exception(self) -> bool:  # Block.isExceptionForConnection
        return "exception" in self.kinds or "shulker_boxes" in self.tags


class Rules:
    def __init__(self, reference: dict):
        self.blocks = reference["blocks"]
        self.tags: dict[str, set[str]] = {}
        for tag, members in reference["tags"].items():
            for block_id in members:
                self.tags.setdefault(block_id, set()).add(tag)

    def kind(self, block_id: str) -> str | None:
        kinds = set(self.blocks[block_id]["kinds"]) & set(KINDS)
        if len(kinds) > 1:
            raise ValueError(f"{block_id} has several connection kinds {sorted(kinds)}")
        return kinds.pop() if kinds else None

    def facts(self, cell: Cell | None) -> Facts:
        block_id, props = cell if cell is not None else ("minecraft:air", {})
        entry = self.blocks[block_id]
        facts = entry["facts"]
        if isinstance(facts, dict):
            facts = facts[",".join(props[k] for k in entry["keys"])]
        sturdy, covers = facts.split("/")
        dynamic = "dynamic_shape" in entry["kinds"]
        return Facts(
            block_id=block_id,
            kinds=frozenset(entry["kinds"]),
            tags=frozenset(self.tags.get(block_id, ())),
            sturdy={side: sturdy[i] == "1" for i, side in enumerate(SIDES)},
            covers={key: covers[i] == "1" for i, key in enumerate(("post",) + SIDES)},
            sturdy_exact=not dynamic,
            covers_exact=not (dynamic or entry.get("offset", False)),
        )


class Unresolved(Exception):
    """A fact the rule needs depends on the neighbour's position or block entity."""


def _sturdy(nb: Facts, face: str) -> bool:
    if not nb.sturdy_exact:
        raise Unresolved(f"{nb.block_id} has a dynamic shape; its {face} face support cannot be known")
    return nb.sturdy[face]


def _covers(above: Facts) -> dict[str, bool]:
    if not above.covers_exact:
        raise Unresolved(f"{above.block_id} above has a position-dependent collision shape")
    return above.covers


def _gate_connects(nb: Cell, nb_facts: Facts, face: str) -> bool:
    # FenceGateBlock.connectsToDirection(state, face): FACING axis == face.getClockWise() axis
    return "fence_gate" in nb_facts.kinds and AXIS[nb[1]["facing"]] == AXIS[CLOCKWISE[face]]


def _wall_connects(nb: Cell | None, f: Facts, face: str) -> bool:
    # WallBlock.connectsTo: is(WALLS) || !exception && faceSolid || instanceof IronBarsBlock || gate
    if "walls" in f.tags or "bars" in f.kinds or (nb is not None and _gate_connects(nb, f, face)):
        return True
    return not f.exception and _sturdy(f, face)


def _fence_connects(own: Facts, nb: Cell | None, f: Facts, face: str) -> bool:
    # FenceBlock.connectsTo: !exception && faceSolid || isSameFence || gate
    same = "fences" in f.tags and ("wooden_fences" in f.tags) == ("wooden_fences" in own.tags)
    if same or (nb is not None and _gate_connects(nb, f, face)):
        return True
    return not f.exception and _sturdy(f, face)


def _bars_connects(f: Facts, face: str) -> bool:
    # IronBarsBlock.attachsTo: !exception && faceSolid || instanceof IronBarsBlock || is(WALLS)
    if "bars" in f.kinds or "walls" in f.tags:
        return True
    return not f.exception and _sturdy(f, face)


class Connector:
    def __init__(self, rules: Rules, cells: dict[Pos, Cell], size: tuple[int, int, int]):
        self.rules, self.cells, self.size = rules, cells, size

    def neighbour(self, pos: Pos, direction: str) -> tuple[Cell | None, str | None]:
        """The neighbour cell, or None and why it is unknown."""
        step = STEP[direction]
        npos = (pos[0] + step[0], pos[1] + step[1], pos[2] + step[2])
        if not all(0 <= npos[i] < self.size[i] for i in range(3)):
            return None, "outside_template"
        if npos not in self.cells:
            return None, "omitted_air"
        return self.cells[npos], None

    def compute(self, pos: Pos, kind: str, keep: set[str]) -> tuple[dict[str, str], dict[str, str], list[str]]:
        """Vanilla values for the computed properties not in `keep`, the unknown neighbours used, and the
        reasons for every property that could not be resolved (those are absent from the values)."""
        block_id, props = self.cells[pos]
        own = self.rules.facts(self.cells[pos])
        unknown: dict[str, str] = {}
        reasons: list[str] = []

        def look(direction: str) -> tuple[Cell | None, Facts]:
            cell, why = self.neighbour(pos, direction)
            if why:
                unknown[direction] = why
            return cell, self.rules.facts(cell)

        out: dict[str, str] = {}
        if kind == "fence_gate":
            if "in_wall" not in keep:
                # FenceGateBlock.updateShape: on the facing.getClockWise() axis, in_wall = either side is(WALLS)
                sides = [s for s in SIDES if AXIS[s] == AXIS[CLOCKWISE[props["facing"]]]]
                out["in_wall"] = str(any("walls" in look(s)[1].tags for s in sides)).lower()
            return out, unknown, reasons
        if kind == "wall":
            above_cell, above = look("up")
            conn = {}
            for side in SIDES:
                if side in keep:
                    continue
                nb, f = look(side)
                try:
                    conn[side] = _wall_connects(nb, f, OPPOSITE[side])
                except Unresolved as reason:  # this side only: it keeps the default
                    reasons.append(str(reason))
            covers = None
            if any(conn.values()):
                try:
                    covers = _covers(above)
                except Unresolved as reason:  # connections are known, only their height is not (assume low)
                    reasons.append(str(reason))
            sides = {}
            for side in SIDES:
                if side in keep:
                    sides[side] = props[side]
                elif side in conn:  # WallBlock.makeWallState
                    sides[side] = ("tall" if covers and covers[side] else "low") if conn[side] else "none"
                    out[side] = sides[side]
                else:
                    sides[side] = props[side]
            if "up" not in keep:
                try:
                    if any(side not in conn and side not in keep for side in SIDES) or (
                        covers is None and any(conn.values())
                    ):  # the post reads every side's final state, including the assumed height
                        raise Unresolved("the post depends on a side or a height that cannot be resolved")
                    out["up"] = str(self._raise_post(sides, above_cell, above)).lower()
                except Unresolved as reason:
                    if str(reason) not in reasons:
                        reasons.append(str(reason))
            return out, unknown, reasons
        for side in SIDES:
            if side in keep:
                continue
            nb, f = look(side)
            face = OPPOSITE[side]
            try:
                connected = _fence_connects(own, nb, f, face) if kind == "fence" else _bars_connects(f, face)
            except Unresolved as reason:
                reasons.append(str(reason))
                continue
            out[side] = str(connected).lower()
        return out, unknown, reasons

    @staticmethod
    def _raise_post(sides: dict[str, str], above_cell: Cell | None, above: Facts) -> bool:
        # WallBlock.shouldRaisePost
        if "wall" in above.kinds and above_cell[1]["up"] == "true":
            return True
        none = {side: sides[side] == "none" for side in SIDES}
        if all(none.values()) or none["north"] != none["south"] or none["west"] != none["east"]:
            return True
        if (sides["north"] == sides["south"] == "tall") or (sides["east"] == sides["west"] == "tall"):
            return False
        return "wall_post_override" in above.tags or _covers(above)["post"]


def _state_text(cell: Cell) -> str:
    block_id, props = cell
    return block_id + ("[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]" if props else "")


def connect(
    cells: dict[Pos, Cell], explicit: dict[Pos, set[str]], size: tuple[int, int, int], reference: dict
) -> tuple[dict[Pos, Cell], dict]:
    """Return the cells with computed connection properties, and the report section."""
    rules = Rules(reference)
    out = dict(cells)
    connector = Connector(rules, out, size)
    changed: dict[str, int] = {}
    corrected = computed = 0
    boundary, unresolved, differs = [], [], []
    # Top layer first: walls read the block above (see module docstring); x/z order is irrelevant.
    for pos in sorted(cells, key=lambda p: (-p[1], p[2], p[0])):
        block_id, props = cells[pos]
        kind = rules.kind(block_id)
        if kind is None:
            continue
        keep = set(explicit.get(pos, ())) & set(COMPUTED[kind])
        if keep:  # stated values are kept; note where vanilla would have computed something else
            vanilla, _, _ = connector.compute(pos, kind, set())
            for key in sorted(k for k in keep if k in vanilla and props[k] != vanilla[k]):
                differs.append(
                    {
                        "pos": list(pos),
                        "block": block_id,
                        "property": key,
                        "source": props[key],
                        "vanilla": vanilla[key],
                    }
                )
        if len(keep) == len(COMPUTED[kind]):
            continue
        computed += 1
        values, unknown, reasons = connector.compute(pos, kind, keep)
        if reasons:
            unresolved.append(
                {"pos": list(pos), "state": _state_text(cells[pos]), "reason": "; ".join(dict.fromkeys(reasons))}
            )
        if unknown:
            boundary.append({"pos": list(pos), "block": block_id, "unknown_neighbours": dict(sorted(unknown.items()))})
        diff = sorted(k for k, v in values.items() if props[k] != v)
        if diff:
            corrected += 1
            for key in diff:
                changed[key] = changed.get(key, 0) + 1
            out[pos] = (block_id, {**props, **values})
    report = {
        "reference": f"tools/structure_export/reference/connectivity-{reference['minecraft_version']}.json",
        "computed_blocks": computed,
        "corrected_blocks": corrected,
        "corrected_properties": dict(sorted(changed.items())),
        "boundary_unresolved": boundary,
        "unresolved": unresolved,
        "explicit_differs_from_vanilla": differs,
    }
    return out, report
