"""STATIC geometric reachability probe for the SG-01 templates (no Minecraft runtime involved).

Builds the unrotated assembled structure from the exported templates, approximates collision with half-block
resolution (full blocks 1.0, bottom stairs 0.5/1.0, walls 1.5), and searches standing positions for a 0.6 x 1.8 player.
Walk edges need a rise <= 0.6 (vanilla step height), jump edges a rise <= 1.0 (vanilla jump height is 1.25), and drops are
accepted up to 3.0 (no fall damage). Everything outside the structure's bounding box is treated as solid rock.

This is geometric reachability. It is NOT a live player traversal result and must be reported as such.
"""
from __future__ import annotations

import importlib.util
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("probe_jigsaw", HERE.parent / "probe-jigsaw.py")
probe_jigsaw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe_jigsaw)

PLAYER_HEIGHT = 1.8
STEP = 0.6
JUMP = 1.0
SAFE_DROP = 3.0
BACK = {"north": (None, 0), "south": (None, 1), "west": (0, None), "east": (1, None)}


def top_height(state: dict, i: int, j: int) -> float:
    """Collision top above the block base for half-block sub-column (i, j) in {0,1}^2."""
    block_id = state["id"]
    if block_id.endswith("_stairs"):
        props = state.get("properties", {})
        if props.get("half", "bottom") != "bottom":
            return 1.0
        bi, bj = BACK[props.get("facing", "north")]
        in_back = (bi is None or i == bi) and (bj is None or j == bj)
        return 1.0 if in_back else 0.5
    if block_id.endswith("_wall"):
        return 1.5
    return 1.0


class Assembly:
    def __init__(self, template_dir: Path, turns: int = 0) -> None:
        templates = probe_jigsaw.load_templates(template_dir)
        self.turns = turns
        self.chamber_cells = templates["main_chamber"]["size"][0]
        base = probe_jigsaw.expected_model(templates)  # solid blocks, chamber origin (0,0,0), rotation NONE
        self.model = {probe_jigsaw.rotate(p, turns, self.chamber_cells): probe_jigsaw.rotate_state(st, turns) for p, st in base.items()}
        self.lo = tuple(min(p[i] for p in self.model) for i in range(3))
        self.hi = tuple(max(p[i] for p in self.model) for i in range(3))
        self.chamber_size = templates["main_chamber"]["size"]
        self._levels: dict[tuple[int, int], list[float]] = {}

    def cell(self, x: int, y: int, z: int) -> tuple[int, int, int]:
        """Chamber-local cell -> assembly cell after this assembly's rotation."""
        return probe_jigsaw.rotate((x, y, z), self.turns, self.chamber_cells)

    def point(self, x: float, z: float) -> tuple[float, float]:
        """Chamber-local continuous (x, z) -> assembly coordinates (rotation is about the chamber's own cell grid)."""
        cx, _, cz = self.cell(int(x), 0, int(z))
        return cx + (x - int(x)), cz + (z - int(z))

    def inside(self, x: int, y: int, z: int) -> bool:
        return all(self.lo[k] <= v <= self.hi[k] for k, v in enumerate((x, y, z)))

    def occupant(self, x: int, y: int, z: int, i: int, j: int) -> float | None:
        """Collision top (relative to y) of the block at a cell/sub-column; terrain outside the box is full rock."""
        if not self.inside(x, y, z):
            return 1.0
        state = self.model.get((x, y, z))
        return None if state is None else top_height(state, i, j)

    def levels(self, sx: int, sz: int) -> list[float]:
        """Standing heights available in sub-column (sx, sz) (half-block units of the world x/z)."""
        key = (sx, sz)
        if key in self._levels:
            return self._levels[key]
        x, i = divmod(sx, 2)
        z, j = divmod(sz, 2)
        out = []
        for y in range(self.lo[1], self.hi[1] + 1):
            top = self.occupant(x, y, z, i, j)
            if top is None or top > 1.0:
                continue
            height = y + top
            ok = True
            for yy in range(y, y + 4):
                t = self.occupant(x, yy, z, i, j)
                if t is None:
                    continue
                if yy == y and t == top:
                    continue  # the supporting block itself
                if yy + t > height + 1e-9 and yy < height + PLAYER_HEIGHT - 1e-9:
                    ok = False
                    break
            if ok:
                out.append(height)
        self._levels[key] = out
        return out

    def search(self, starts, *, allow_jump: bool):
        seen = set(starts)
        queue = deque(starts)
        used_jump = set()
        while queue:
            sx, sz, h = queue.popleft()
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for h2 in self.levels(sx + dx, sz + dz):
                    rise = h2 - h
                    if rise > JUMP + 1e-9 or rise < -SAFE_DROP - 1e-9:
                        continue
                    if rise > STEP + 1e-9:
                        if not allow_jump:
                            continue
                        used_jump.add((sx, sz, h))
                    node = (sx + dx, sz + dz, h2)
                    if node not in seen:
                        seen.add(node)
                        queue.append(node)
        return seen, used_jump

    def node_at(self, x: float, y_stand: float, z: float):
        """Standing node under world (x, z) at the given standing height."""
        sx, sz = int(x * 2), int(z * 2)
        for h in self.levels(sx, sz):
            if abs(h - y_stand) < 1e-6:
                return (sx, sz, h)
        raise ValueError(f"No standing level {y_stand} at {x},{z}: {self.levels(sx, sz)}")


def mouth_nodes(asm: Assembly) -> dict[str, tuple[int, int, float]]:
    """Node at the far end of each tunnel (feet on the tunnel floor), keyed by the chamber-local direction."""
    n = asm.chamber_cells
    mid = n // 2
    far = {"north": (mid, -15 + 1), "south": (mid, n - 1 + 15 - 1), "west": (-15 + 1, mid), "east": (n - 1 + 15 - 1, mid)}
    out = {}
    for name, (x, z) in far.items():
        cx, _, cz = asm.cell(x, 1, z)
        out[name] = asm.node_at(cx + 0.5, 1.0, cz + 0.5)
    return out


RING = {"north": (20.5, 5.5), "south": (20.5, 35.5), "east": (35.5, 20.5), "west": (5.5, 20.5)}


def report(template_dir: Path, turns: int = 0) -> dict:
    asm = Assembly(template_dir, turns)
    mouths = mouth_nodes(asm)
    plaza = asm.node_at(*asm.point(20.5, 20.5)[:1], 1.0, asm.point(20.5, 20.5)[1])
    out = {"method": "static geometric reachability, half-block resolution, NOT live player traversal", "rotation_quarter_turns": turns,
           "mouths": {}}
    for name, start in mouths.items():
        for allow in (False, True):
            seen, jumps = asm.search([start], allow_jump=allow)
            key = "walk_and_jump" if allow else "walk_only"
            ring = {}
            for d, (x, z) in RING.items():
                px, pz = asm.point(x, z)
                ring[d] = asm.node_at(px, 9.0, pz) in seen
            out["mouths"].setdefault(name, {})[key] = {
                "reaches_plaza_centre": plaza in seen,
                "reaches_other_mouths": sorted(n for n, node in mouths.items() if node in seen and n != name),
                "reaches_ring": ring, "jump_edges_used": len(jumps), "reachable_standing_nodes": len(seen),
            }
    return out
