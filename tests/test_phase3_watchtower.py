"""Structural and traversal regression tests for the Phase 3 Ruined Watchtower.

The walker is a deliberately small model, not Minecraft's physics. It works on half-block
sub-columns, allows steps up of at most 0.5 blocks (stairs, slabs), and requires 1.8 blocks of
clear headroom. It exists to catch an unreachable upper deck like the one reported on PR #2.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest
from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.palette import get_block_by_index
from mcbuild.voxel import VoxelGrid

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "artifacts" / "phase-3" / "final" / "blueprint.py"
ITERATION_2 = ROOT / "artifacts" / "phase-3" / "iteration-2" / "blueprint.py"

BODY_HEIGHT = 1.8
MAX_STEP_UP = 0.5
MAX_DROP = 1.0
EPS = 1e-6


def build(path: Path) -> VoxelGrid:
    grid = VoxelGrid()
    run_blueprint(path.read_text(encoding="utf-8"), grid, seed=0)
    return grid


def _intervals(grid: VoxelGrid, sx: int, sz: int, y_range: range) -> list[tuple[float, float]]:
    """Solid vertical intervals in the half-block sub-column (sx, sz)."""
    x, z = sx // 2, sz // 2
    out = []
    for y in y_range:
        index = grid.get(x, y, z)
        if index is None:
            continue
        block = get_block_by_index(index)
        state = dict(block.state)
        if block.name.endswith("_wall"):
            out.append((y, y + 1.5))
        elif block.name.endswith("_stairs") and state.get("half", "bottom") == "bottom":
            facing = state.get("facing", "east")
            high = {
                "east": sx % 2 == 1,
                "west": sx % 2 == 0,
                "south": sz % 2 == 1,
                "north": sz % 2 == 0,
            }[facing]
            out.append((y, y + (1.0 if high else 0.5)))
        elif block.name.endswith("_slab") and state.get("type", "bottom") == "bottom":
            out.append((y, y + 0.5))
        else:
            out.append((y, y + 1.0))
    return out


def standing_heights(grid: VoxelGrid, sx: int, sz: int) -> list[float]:
    (_, y0, _), (_, y1, _) = grid.bounds
    y_range = range(y0, y1 + 3)
    solids = _intervals(grid, sx, sz, y_range)
    heights = []
    for _, top in solids:
        if any(lo < top + BODY_HEIGHT - EPS and hi > top + EPS for lo, hi in solids):
            continue
        heights.append(top)
    return sorted(set(heights))


def reachable_nodes(grid: VoxelGrid, start: tuple[int, int, float]) -> set[tuple[int, int, float]]:
    seen = {start}
    queue = deque([start])
    (x0, _, z0), (x1, _, z1) = grid.bounds
    while queue:
        sx, sz, h = queue.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = sx + dx, sz + dz
            if not (x0 * 2 - 2 <= nx <= x1 * 2 + 3 and z0 * 2 - 2 <= nz <= z1 * 2 + 3):
                continue
            for nh in standing_heights(grid, nx, nz):
                if -MAX_DROP - EPS <= nh - h <= MAX_STEP_UP + EPS and (nx, nz, nh) not in seen:
                    seen.add((nx, nz, nh))
                    queue.append((nx, nz, nh))
    return seen


@pytest.fixture(scope="module")
def final_grid() -> VoxelGrid:
    return build(FINAL)


def test_footprint_and_block_count_preserved(final_grid):
    assert final_grid.bounds == ((0, 0, 0), (10, 16, 10))
    # Iteration-2 has 649 blocks; the PR #6 integration-time fix removes exactly one rail block.
    assert len(final_grid) == 648
    original = build(ITERATION_2)
    changed = {
        (x, y, z)
        for x in range(11)
        for y in range(17)
        for z in range(11)
        if final_grid.get(x, y, z) != original.get(x, y, z)
    }
    assert changed == {(7, 7, 4), (7, 8, 4)}


def test_entrance_doorway_is_open(final_grid):
    for x in (4, 5, 6):
        for y in (1, 2, 3):
            assert final_grid.get(x, y, 9) is None


def test_stair_flight_has_headroom(final_grid):
    for step in range(6):
        x, y = 2 + step, 1 + step
        block = get_block_by_index(final_grid.get(x, y, 5))
        assert block.name == "stone_brick_stairs"
        assert dict(block.state)["facing"] == "east"
        for dy in (1, 2):
            assert final_grid.get(x, y + dy, 5) is None, f"no headroom above stair ({x},{y},5)"


def test_upper_deck_reachable_from_entrance(final_grid):
    start = (10, 16, 1.0)  # inside the south doorway on the ground floor
    assert 1.0 in standing_heights(final_grid, 10, 16)
    nodes = reachable_nodes(final_grid, start)
    deck = [n for n in nodes if n[2] == 8.0 and 3 <= n[0] // 2 <= 7 and 3 <= n[1] // 2 <= 7]
    assert deck, "upper deck is not reachable by walking from the entrance"


def test_walker_detects_the_original_defect():
    """The unmodified iteration-2 blueprint (as reviewed on PR #2) must NOT pass the walker."""
    grid = build(ITERATION_2)
    nodes = reachable_nodes(grid, (10, 16, 1.0))
    assert not [n for n in nodes if n[2] == 8.0 and 3 <= n[0] // 2 <= 7 and 3 <= n[1] // 2 <= 7]
    # The exact finding: the landing at (8,7,5) has solid blocks directly above it.
    assert grid.get(8, 7, 5) is not None
    assert grid.get(8, 8, 5) is not None
    assert grid.get(8, 9, 5) is not None
