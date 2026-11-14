"""SEAM-01 patch generator, validator and applier.

Whole structure (all 34 placements' SOURCE states assembled, connection states computed once on the whole) versus the
module-by-module result (what `place template` writes: each module's own export, PR #47 connect + PR #49 stairs):
the cells where they differ are the seam patches. Only connecting blocks (wall, fence, bars/panes, fence gate) are patched, only in
properties the connectivity rules compute and the author did not state. Stairs are never patched (see `stair_report`).
"""

# ruff: noqa: E501
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from tools.structure_export.connectivity import COMPUTED, Rules, connect, load_connectivity
from tools.structure_export.convert import load_reference, resolve_state
from tools.structure_export.live import ROTATIONS, rotate_props

from . import assembly as A
from .stairs import stairs_shape

TARGET = "26.3"
Pos = tuple[int, int, int]
FORMAT = 1


class SeamError(Exception):
    pass


def order_key(p: Pos):
    return (p[1], p[2], p[0])  # y, z, x: the one application order


@dataclass(frozen=True)
class Patch:
    pos: Pos
    block: str
    state: tuple[tuple[str, str], ...]  # complete target state
    was: tuple[tuple[str, str], ...]  # properties that change: (key, module-export value)

    def to_json(self) -> dict:
        return {"pos": list(self.pos), "block": self.block, "state": dict(self.state), "was": dict(self.was)}


def box() -> tuple[int, int, int]:
    return (A.box_size(), A.height(), A.box_size())


def whole_structure(q: int, sources: dict, vanilla_stairs: bool = False) -> tuple[dict, dict, dict]:
    """Connection states computed once on the assembled source states of all placements.

    Authored stair shapes are kept (strict placement, the STAIR-01 contract). With `vanilla_stairs` every stair takes the shape the
    game computes in the assembled structure instead: that is what a normal (non-strict) neighbour update ends in, and it is only
    used to measure how far stair shapes at a seam reach into the connections of neighbouring walls, fences and bars.
    """
    reference = load_reference(TARGET)
    stated, _ = A.assemble(q, sources)
    if vanilla_stairs:
        full = {p: (b, {**pr}) for p, (b, pr) in stated.items()}
        for pos, (bid, props) in full.items():
            if bid.endswith("_stairs"):
                stated[pos] = (bid, {**props, "shape": stairs_shape(full, pos)})
    cells, explicit = {}, {}
    for pos, (bid, props) in stated.items():
        state, _ = resolve_state(bid, props, reference)
        cells[pos] = (bid, dict(state))
        explicit[pos] = set(props)
    out, report = connect(cells, explicit, box(), load_connectivity(TARGET))
    return out, explicit, report


def module_result(q: int, exported: dict) -> dict:
    cells, _ = A.assemble(q, exported)
    return cells


def generate(q: int, sources: dict, exported: dict) -> list[Patch]:
    rules = Rules(load_connectivity(TARGET))
    whole, explicit, _ = whole_structure(q, sources)
    placed = module_result(q, exported)
    if set(whole) != set(placed):
        extra = sorted(set(whole) ^ set(placed), key=order_key)[:5]
        raise SeamError(f"q={q}: whole structure and module assembly cover different cells, e.g. {extra}")
    patches = []
    for pos in sorted(whole, key=order_key):
        bid, props = whole[pos]
        mbid, mprops = placed[pos]
        if mbid != bid:
            raise SeamError(f"q={q}: {pos} is {mbid} in the module assembly but {bid} in the whole structure")
        kind = rules.kind(bid)
        if mprops == props:
            continue
        if kind is None:
            raise SeamError(f"q={q}: {pos} {bid} differs from its module export but is not a connecting block")
        changed = {k for k in props if props[k] != mprops[k]}
        if not changed <= set(COMPUTED[kind]) or changed & explicit.get(pos, set()):
            raise SeamError(f"q={q}: {pos} {bid} would change {sorted(changed)}: not computed, or author-stated")
        patches.append(Patch(pos, bid, tuple(sorted(props.items())), tuple(sorted((k, mprops[k]) for k in changed))))
    return patches


# ---------------------------------------------------------------- serialisation, rotation, checks
def patchset(q: int, patches: list[Patch]) -> dict:
    body = {
        "format": FORMAT,
        "target": TARGET,
        "frame": "structure frame for whole-structure rotation q; add the world anchor of the rotated box corner",
        "q": q,
        "box": list(box()),
        "order": "y, z, x ascending; patches are independent strict state writes",
        "patches": [p.to_json() for p in patches],
    }
    body["sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body


def from_json(ps: dict) -> list[Patch]:
    return [
        Patch(tuple(p["pos"]), p["block"], tuple(sorted(p["state"].items())), tuple(sorted(p["was"].items())))
        for p in ps["patches"]
    ]


def rotate(patches: list[Patch], quarter: int) -> list[Patch]:
    """The q=0 patches turned with the structure: positions inside the box, directional properties with them."""
    out = []
    for p in patches:
        x, z = A.rot_cell(p.pos[0], p.pos[2], quarter)
        rotation = ROTATIONS[quarter % 4]
        out.append(
            Patch(
                (x, p.pos[1], z),
                p.block,
                tuple(sorted(rotate_props(dict(p.state), rotation).items())),
                tuple(sorted(rotate_props(dict(p.was), rotation).items())),
            )
        )
    return sorted(out, key=lambda p: order_key(p.pos))


def validate(patches: list[Patch], placed: dict, whole: dict) -> list[str]:
    """Missing / duplicate / conflicting / misplaced patches, found independently of how they were generated."""
    problems = []
    seen: dict[Pos, Patch] = {}
    bx, by, bz = box()
    for p in patches:
        if p.pos in seen:
            problems.append(
                f"duplicate patch at {p.pos}" + ("" if seen[p.pos] == p else " with a different state (conflict)")
            )
        seen[p.pos] = p
        if not (0 <= p.pos[0] < bx and 0 <= p.pos[1] < by and 0 <= p.pos[2] < bz):
            problems.append(f"patch outside the box at {p.pos}")
        elif p.pos not in placed:
            problems.append(f"patch at {p.pos} targets an empty cell")
        elif placed[p.pos][0] != p.block:
            problems.append(f"patch at {p.pos} is for {p.block} but the cell holds {placed[p.pos][0]}")
    if [p.pos for p in patches] != sorted((p.pos for p in patches), key=order_key):
        problems.append("patches are not in the deterministic application order")
    after = apply(placed, patches)
    for pos in sorted(whole, key=order_key):
        if after.get(pos) != whole[pos]:
            problems.append(
                f"{pos}: after patching {after.get(pos)} != whole-structure {whole[pos]} (missing or wrong patch)"
            )
            if len(problems) > 20:
                break
    return problems


def apply(cells: dict, patches: list[Patch]) -> dict:
    out = dict(cells)
    for p in patches:
        out[p.pos] = (p.block, dict(p.state))
    return out


def stair_report(q: int, sources: dict, exported: dict) -> dict:
    """Stairs whose game shape changes because of a neighbour in another module (never patched; PR #49 reconciliation)."""
    placed = module_result(q, exported)
    out = []
    for pos in sorted(placed, key=order_key):
        bid, props = placed[pos]
        if not bid.endswith("_stairs"):
            continue
        shape = stairs_shape(placed, pos)
        if shape != props["shape"]:
            out.append(
                {
                    "pos": list(pos),
                    "block": bid,
                    "facing": props["facing"],
                    "half": props["half"],
                    "authored": props["shape"],
                    "assembled_vanilla": shape,
                }
            )
    return {"q": q, "stairs": sum(1 for b, _ in placed.values() if b.endswith("_stairs")), "seam_dependent": out}


def reconcile_stairs(q: int, report: dict, results: dict) -> dict:
    """Every seam-dependent stair must be named by the stair_boundary_review (PR #49) of the placement that wrote it."""
    from .stairs import OPPOSITE

    turn = {
        name: dict(zip(("north", "east", "south", "west"), order, strict=True))
        for name, order in (
            ("none", ("north", "east", "south", "west")),
            ("clockwise_90", ("east", "south", "west", "north")),
            ("180", ("south", "west", "north", "east")),
            ("counterclockwise_90", ("west", "north", "east", "south")),
        )
    }
    reviewed = set()
    for e in A.manifest(q):
        for item in results[e["module"]].report.get("stair_boundary_review", []):
            pos = A.place_cell(e, tuple(item["pos"]))
            reviewed.add((pos, turn[e["rotation"]][item["side"]]))
    uncovered = []
    for s in report["seam_dependent"]:
        pos = tuple(s["pos"])
        # the stair's own facing is in the module-assembled state; recompute from the report entry
        facing = s["facing"]
        if (pos, facing) not in reviewed and (pos, OPPOSITE[facing]) not in reviewed:
            uncovered.append(s)
    return {"seam_dependent": len(report["seam_dependent"]), "not_in_stair_boundary_review": uncovered}
