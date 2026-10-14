#!/usr/bin/env python3
"""Render ONLY the ten approved Ancient City peak-era module candidates."""
from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

import nbtlib
from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.export.schem import export_schem
from mcbuild.palette import get_block_by_index
from mcbuild.render.views import build_contact_sheet
from mcbuild.voxel import VoxelGrid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts" / "ancient-city-restoration" / "approved-modules"
OUTPUT = ROOT / "out" / "ancient-city-approved-modules"
APPROVED = (
    "chamber_1", "chamber_2", "chamber_3",
    "camp_1", "camp_2", "camp_3",
    "tall_ruin_1", "tall_ruin_2", "tall_ruin_3", "tall_ruin_4",
)
VIEWS = [{"yaw": 0}, {"yaw": 1}, {"yaw": 2}, {"yaw": 3}]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    found = {p.name for p in SOURCE.iterdir() if p.is_dir()}
    assert found == set(APPROVED), f"Unexpected or missing modules: {found ^ set(APPROVED)}"
    results = []
    for name in APPROVED:
        src_path = SOURCE / name / "blueprint.py"
        code = src_path.read_text(encoding="utf8")
        ast.parse(code, filename=str(src_path))
        grid = VoxelGrid()
        run_blueprint(code, grid, seed=20261014)
        assert len(grid) > 100, (name, "empty/suspiciously small")
        assert grid.bounds is not None
        out = OUTPUT / name
        out.mkdir(parents=True, exist_ok=True)

        material_counts = Counter(get_block_by_index(i).mc_id for _, i in grid.items())
        assert any("deepslate" in material for material in material_counts), name
        assert any("soul_lantern" in material for material in material_counts), name
        assert not any("sculk" in material for material in material_counts), name
        if name in ("tall_ruin_1", "tall_ruin_3"):
            assert any("brewing_stand" in material for material in material_counts), name
        if name.startswith(("camp_", "chamber_")) or name in ("tall_ruin_2", "tall_ruin_4"):
            assert any("_bed" in material for material in material_counts), name

        image, labels, render_stats = build_contact_sheet(grid, VIEWS)
        assert image.size[0] > 100 and image.size[1] > 100
        image.save(out / "render.png")
        export_schem(grid, str(out / "candidate.schem"))
        schematic = nbtlib.load(out / "candidate.schem")["Schematic"]
        assert int(schematic["Version"]) == 3
        dims = tuple(int(schematic[axis]) for axis in ("Width", "Height", "Length"))
        bounds = grid.bounds
        expected = tuple(bounds[1][i] - bounds[0][i] + 1 for i in range(3))
        assert dims == expected, (name, dims, expected)
        assert (out / "candidate.schem").stat().st_size > 100
        report = dict(
            module=name, source=str(src_path.relative_to(ROOT)),
            status="RENDERED_NOT_YET_VISUALLY_APPROVED",
            block_count=len(grid), bounds=bounds, dimensions=dims,
            materials=dict(sorted(material_counts.items())),
            render_views=labels,
            render_size=image.size,
            render_stats=render_stats,
            schem_version=int(schematic["Version"]),
        )
        (out / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf8")
        results.append(report)
        print(f"OK {name}: {len(grid)} voxels, {dims}, {image.size}", flush=True)
    (OUTPUT / "summary.json").write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
