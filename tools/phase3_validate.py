#!/usr/bin/env python3
"""Regenerate the Phase 3 watchtower from its blueprint and compare it to the committed schematic.

The comparison is on decoded NBT, not file bytes: the exporter writes a gzip stream and the
Sponge Schematic v3 format does not require deterministic compressed bytes. Output goes to a
temporary directory so nothing generated is left in the working tree. Traversal/headroom is
checked separately by tests/test_phase3_watchtower.py.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import nbtlib

from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.export.schem import export_schem
from mcbuild.voxel import VoxelGrid

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "artifacts" / "phase-3" / "final"
ITERATION_2 = ROOT / "artifacts" / "phase-3" / "iteration-2"


def main() -> int:
    blueprint = FINAL / "blueprint.py"
    # final/ is iteration-2 plus the PR #6 integration-time stair-exit correction, so the two
    # blueprints are expected to differ; iteration-2 itself is left as originally reviewed.
    if blueprint.read_bytes() == (ITERATION_2 / "blueprint.py").read_bytes():
        print("FAIL: final/blueprint.py is missing the integration-time stair-exit correction")
        return 1

    grid = VoxelGrid()
    run_blueprint(blueprint.read_text(encoding="utf-8"), grid, seed=0)
    if len(grid) != 648 or grid.bounds != ((0, 0, 0), (10, 16, 10)):
        print(f"FAIL: unexpected geometry: {len(grid)} blocks, bounds {grid.bounds}")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        regenerated = Path(tmp) / "regenerated.schem"
        export_schem(grid, str(regenerated))
        new = nbtlib.load(regenerated)["Schematic"]
        committed = nbtlib.load(FINAL / "final.schem")["Schematic"]

    if new != committed:
        print("FAIL: regenerated schematic NBT differs from committed final.schem")
        return 1
    print(f"OK: {len(grid)} blocks; regenerated schematic NBT equals committed final.schem")
    return 0


if __name__ == "__main__":
    sys.exit(main())
