#!/usr/bin/env python3
"""Render and validate staged Ancient City variant blueprints using vendored mcbuild.

This is an intermediate production probe. It deliberately does not declare
either iteration 'final' until the actual images have been visually inspected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.export.schem import export_schem
from mcbuild.palette import get_block_by_index
from mcbuild.render.views import build_contact_sheet
from mcbuild.voxel import VoxelGrid
import nbtlib

ROOT = Path(__file__).resolve().parents[1]
THEMES = ("death", "nether", "living")
VIEWS = [{"yaw": 0}, {"yaw": 1}, {"yaw": 2}, {"yaw": 3}, {"mode": "top-down"}]


def render_one(theme: str, iteration: int, *, output: Path) -> dict:
    src = ROOT / "artifacts" / "ancient-city-variants" / theme / f"iteration-{iteration}" / "blueprint.py"
    code = src.read_text(encoding="utf-8")
    grid = VoxelGrid()
    run_blueprint(code, grid, seed=20261014)
    assert grid.bounds is not None, (theme, iteration, "empty voxel grid")

    out_dir = output / theme / f"iteration-{iteration}"
    out_dir.mkdir(parents=True, exist_ok=True)
    image, labels, stats = build_contact_sheet(grid, VIEWS)
    assert image.getbbox() is not None
    image.save(out_dir / "render.png")

    export_schem(grid, str(out_dir / "candidate.schem"))
    schematic = nbtlib.load(out_dir / "candidate.schem")["Schematic"]
    assert int(schematic["Version"]) == 3
    dims = tuple(int(schematic[key]) for key in ("Width", "Height", "Length"))
    assert tuple(stats["dims"]) == dims
    palette = {str(key) for key in schematic["Blocks"]["Palette"]}
    assert "minecraft:air" in palette
    assert "minecraft:deepslate_tiles" in palette
    assert len(palette) > 3

    report = {
        "theme": theme,
        "iteration": iteration,
        "status": "RENDERED_PENDING_VISUAL_INSPECTION",
        "source": str(src.relative_to(ROOT)),
        "block_count": len(grid),
        "bounds": grid.bounds,
        "dimensions": dims,
        "top_materials": stats["top_materials"],
        "views": labels,
        "palette_size": len(palette),
        "schem_size": (out_dir / "candidate.schem").stat().st_size,
        "render_sha256": hashlib.sha256((out_dir / "render.png").read_bytes()).hexdigest(),
    }
    assert report["schem_size"] > 0
    (out_dir / "structure-report.txt").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "out" / "ancient-city-variants")
    args = parser.parse_args()

    reports = []
    for theme in THEMES:
        for iteration in (1, 2):
            reports.append(render_one(theme, iteration, output=args.output))

    (args.output / "summary.json").write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
