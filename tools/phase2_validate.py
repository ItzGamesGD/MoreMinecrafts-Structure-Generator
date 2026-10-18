#!/usr/bin/env python3
"""Run the deterministic mcbuild Phase 2 validation without an LLM."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import nbtlib

from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.export.schem import DATA_VERSION, export_schem
from mcbuild.palette import get_block_by_index
from mcbuild.render.views import build_contact_sheet
from mcbuild.voxel import VoxelGrid


ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "artifacts" / "phase-2" / "control"
BLUEPRINT = CONTROL / "blueprint.py"
RENDER = CONTROL / "render.png"
SCHEM = CONTROL / "final.schem"
REPORT = CONTROL / "structure-report.txt"


def main() -> None:
    CONTROL.mkdir(parents=True, exist_ok=True)
    source = BLUEPRINT.read_text(encoding="utf-8")
    grid = VoxelGrid()
    run_blueprint(source, grid, seed=0)

    assert grid.bounds == ((0, 0, 0), (6, 11, 6))
    dimensions = (7, 12, 7)
    names = Counter(get_block_by_index(index).mc_id for _, index in grid.items())
    for expected in ("minecraft:cobblestone", "minecraft:stone_bricks", "minecraft:red_wool"):
        assert names[expected] > 0

    # The south wall (z=0) has a centered 3x3 doorway, while its opposite
    # positions remain solid. The interior above the floor is unoccupied.
    for x in range(2, 5):
        for y in range(1, 4):
            assert grid.get(x, y, 0) is None
            assert grid.get(x, y, 6) is not None
    assert grid.get(3, 5, 3) is None

    views = [{"yaw": yaw} for yaw in range(4)]
    image, labels, render_stats = build_contact_sheet(grid, views)
    image.save(RENDER)
    assert image.getbbox() is not None

    export_schem(grid, str(SCHEM))
    assert SCHEM.stat().st_size > 0
    root = nbtlib.load(SCHEM)
    schematic = root["Schematic"]
    schem_dimensions = (
        int(schematic["Width"]),
        int(schematic["Height"]),
        int(schematic["Length"]),
    )
    assert schem_dimensions == dimensions
    assert int(schematic["Version"]) == 3
    assert int(schematic["DataVersion"]) == DATA_VERSION
    schem_palette = sorted(str(name) for name in schematic["Blocks"]["Palette"])
    for expected in names:
        assert expected in schem_palette

    result = {
        "seed": 0,
        "block_count": len(grid),
        "bounds": grid.bounds,
        "dimensions_width_height_length": dimensions,
        "materials": dict(sorted(names.items())),
        "doorway": "z=0, x=2..4, y=1..3 (empty); opposite wall populated",
        "interior_probe_3_5_3": "empty",
        "render_api": "mcbuild.render.views.build_contact_sheet",
        "render_views": labels,
        "render_resolution": list(image.size),
        "render_mode": "Pillow pure-software rasterization",
        "render_sha256": hashlib.sha256(RENDER.read_bytes()).hexdigest(),
        "render_stats": render_stats,
        "schematic_api": "mcbuild.export.schem.export_schem",
        "schematic_format": "Sponge Schematic v3",
        "schematic_dimensions": schem_dimensions,
        "schematic_palette": schem_palette,
        "schematic_size_bytes": SCHEM.stat().st_size,
        "round_trip": "nbtlib load and metadata/palette validation passed",
    }
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
