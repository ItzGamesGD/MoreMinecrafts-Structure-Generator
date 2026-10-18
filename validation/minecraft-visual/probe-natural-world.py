#!/usr/bin/env python3
"""Inspect naturally generated terrain around a Minecraft-generated SG-01 structure."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_local(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe_world = load_local("probe_world", "probe-world.py")
probe_jigsaw = load_local("probe_jigsaw", "probe-jigsaw.py")

AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
LIQUID = {"minecraft:water", "minecraft:lava"}
NEIGHBORS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region-dir", type=Path, required=True)
    parser.add_argument("--template-dir", type=Path, required=True)
    parser.add_argument("--assembly-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    assembly = json.loads(args.assembly_report.read_text())
    if not assembly.get("pass"):
        raise SystemExit("Natural generation assembly report did not pass")

    found = assembly["found_bounds"]
    lo = found["min"]
    hi = found["max"]
    margin = 8
    bounds = (lo[0] - margin, lo[1] - margin, lo[2] - margin,
              hi[0] + margin, hi[1] + margin, hi[2] + margin)
    chunks = probe_world.load_regions(args.region_dir, bounds)

    templates = probe_jigsaw.load_templates(args.template_dir)
    model = probe_jigsaw.expected_model(templates)
    best = assembly["best"]
    turns = best["rotation_degrees_clockwise"] // 90
    shift = best["chamber_origin_after_rotation_shift"]
    chamber_size = templates["main_chamber"]["size"][0]
    placed = {
        tuple(probe_jigsaw.rotate(pos, turns, chamber_size)[i] + shift[i] for i in range(3))
        for pos in model
    }

    min_x, min_y, min_z = lo
    max_x, max_y, max_z = hi
    shell_counts = {"cave_air": 0, "water": 0, "lava": 0, "solid_terrain": 0, "other": 0}
    contacts = {"cave_air": 0, "water": 0, "lava": 0}
    examples = {key: [] for key in contacts}
    for x in range(min_x - 1, max_x + 2):
        for y in range(min_y - 1, max_y + 2):
            for z in range(min_z - 1, max_z + 2):
                if min_x <= x <= max_x and min_y <= y <= max_y and min_z <= z <= max_z:
                    continue
                state = probe_world.state_at(chunks, x, y, z)
                block_id = state["id"]
                if block_id == "minecraft:cave_air":
                    category = "cave_air"
                elif block_id == "minecraft:water":
                    category = "water"
                elif block_id == "minecraft:lava":
                    category = "lava"
                elif block_id in AIR or block_id == "minecraft:unloaded":
                    category = "other"
                else:
                    category = "solid_terrain"
                shell_counts[category] += 1
                touches_structure = any((x + dx, y + dy, z + dz) in placed for dx, dy, dz in NEIGHBORS)
                if touches_structure and category in contacts:
                    contacts[category] += 1
                    if len(examples[category]) < 12:
                        examples[category].append([x, y, z, block_id])

    # Probe the natural surface outside each corner and side of the generated bounds.
    surface_columns = [
        (min_x - 8, min_z - 8), (min_x - 8, max_z + 8),
        (max_x + 8, min_z - 8), (max_x + 8, max_z + 8),
        ((min_x + max_x) // 2, min_z - 8), ((min_x + max_x) // 2, max_z + 8),
        (min_x - 8, (min_z + max_z) // 2), (max_x + 8, (min_z + max_z) // 2),
    ]
    surfaces = []
    for x, z in surface_columns:
        top = None
        for y in range(319, -65, -1):
            block_id = probe_world.state_at(chunks, x, y, z)["id"]
            if block_id not in AIR | LIQUID | {"minecraft:unloaded"}:
                top = y
                break
        surfaces.append({"x": x, "z": z, "top_solid_y": top})

    available = [sample["top_solid_y"] for sample in surfaces if sample["top_solid_y"] is not None]
    min_surface = min(available) if available else None
    underground = min_surface is not None and max_y < min_surface
    report = {
        "worldgen_mode": "normal_overworld; structure set candidate located by Minecraft and its chunks generated from the saved seed",
        "seed": 173,
        "assembly_report": str(args.assembly_report),
        "found_bounds_inclusive": {"min": lo, "max": hi},
        "dimensions": [max_x - min_x + 1, max_y - min_y + 1, max_z - min_z + 1],
        "rotation_degrees_clockwise": best["rotation_degrees_clockwise"],
        "all_expected_structure_blocks_match": best["matched"] == best["expected"] and best["unexpected_extra"] == 0,
        "natural_surface_samples": surfaces,
        "minimum_sampled_surface_y": min_surface,
        "fully_below_sampled_surface": underground,
        "one_block_exterior_shell_counts": shell_counts,
        "direct_natural_contacts": {
            "cave_air": {"verdict": "PASS" if contacts["cave_air"] else "NOT RUN", "count": contacts["cave_air"], "examples": examples["cave_air"]},
            "water": {"verdict": "PASS" if contacts["water"] else "NOT RUN", "count": contacts["water"], "examples": examples["water"]},
            "lava": {"verdict": "PASS" if contacts["lava"] else "NOT RUN", "count": contacts["lava"], "examples": examples["lava"]},
        },
        "accessibility": "NOT RUN: saved block data and screenshots do not establish survival player traversal",
        "notes": "Terrain contact is measured in the one-block exterior shell. A NOT RUN fluid/cave verdict means this deterministic natural site did not present that contact; it is not evidence of fluid safety.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "fully_below_sampled_surface": underground,
        "direct_natural_contacts": {key: value["verdict"] for key, value in report["direct_natural_contacts"].items()},
        "report": str(args.output),
    }))
    if not underground:
        raise SystemExit("Naturally generated SG-01 is not fully below sampled terrain surface")


if __name__ == "__main__":
    main()
