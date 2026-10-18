#!/usr/bin/env python3
"""Build a minimal known-good control datapack with the same exporter as SG-01.

The control is deliberately tiny and independent of SG-01 content. If the control
places but SG-01 does not, the fault is in SG-01; if the control fails too, the
exporter or the harness is at fault.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))

from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid
from structure_export.structure import grid_to_structure, structure_bytes

DATA_VERSION = 5023
PACK_FORMAT = 121
TEMPLATE_ID = "sg01_control:cube"

# (local x, y, z, block id) -> checked by the acceptance script at origin + local.
CONTROL_BLOCKS = [
    (0, 0, 0, "polished_deepslate"),
    (1, 0, 0, "stone_brick_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]"),
    (2, 2, 2, "sea_lantern"),
]


def build(output: Path) -> None:
    grid = VoxelGrid()
    air = get_block("air").index
    for z in range(3):
        for y in range(3):
            for x in range(3):
                grid.set(x, y, z, air)
    for x, y, z, block_id in CONTROL_BLOCKS:
        grid.set(x, y, z, get_block(block_id).index)
    data = structure_bytes(grid_to_structure(grid, data_version=DATA_VERSION))
    path = output / "data/sg01_control/structure/cube.nbt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    (output / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "SG-01 control", "min_format": PACK_FORMAT, "max_format": PACK_FORMAT}}, indent=2) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
    print(TEMPLATE_ID)
