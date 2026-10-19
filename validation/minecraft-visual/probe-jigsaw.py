#!/usr/bin/env python3
"""Verify a /place structure Jigsaw assembly against the exported templates in saved chunk data.

/place structure chooses its own start height (the structure's start_height) and rotation, so
the assembly cannot be probed at a fixed origin. Instead this reconstructs the expected block
set from the five exported templates using vanilla Jigsaw rules (child connector in the cell in
front of the parent connector, no overlap) and finds the rotation and offset that place it in
the saved world. Every expected block must match and no further block of a structure palette
id may be present in the search volume.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("probe_world", HERE / "probe-world.py")
probe_world = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe_world)
from structure_export.nbt import read_nbt  # noqa: E402  (probe_world adds the repo root to sys.path)

DIRECTIONS = ("north", "east", "south", "west")
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
FRONT = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0)}
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def load_templates(directory: Path) -> dict[str, dict]:
    names = ("main_chamber", *(f"tunnel_{d}" for d in DIRECTIONS))
    return {name: read_nbt((directory / f"{name}.nbt").read_bytes())["value"] for name in names}


def jigsaw_pos(template: dict, face: str) -> tuple[int, int, int]:
    for block in template["blocks"]:
        state = template["palette"][block["state"]]
        if state["id"] == "minecraft:jigsaw" and state["properties"]["orientation"].startswith(face):
            return tuple(block["pos"])
    raise ValueError(f"No {face}-facing jigsaw block")


def expected_model(templates: dict[str, dict]) -> dict[tuple[int, int, int], dict]:
    """Solid blocks of the unrotated assembly, chamber origin at (0, 0, 0)."""
    model: dict[tuple[int, int, int], dict] = {}

    def add(template: dict, origin: tuple[int, int, int]) -> None:
        for block in template["blocks"]:
            state = template["palette"][block["state"]]
            if state["id"] in AIR or state["id"] == "minecraft:jigsaw":
                continue
            pos = tuple(origin[i] + block["pos"][i] for i in range(3))
            if pos in model:
                raise ValueError(f"Assembled templates overlap at {pos}")
            model[pos] = state

    chamber = templates["main_chamber"]
    add(chamber, (0, 0, 0))
    for direction in DIRECTIONS:
        tunnel = templates[f"tunnel_{direction}"]
        parent = jigsaw_pos(chamber, direction)
        child = jigsaw_pos(tunnel, OPPOSITE[direction])
        add(tunnel, tuple(parent[i] + FRONT[direction][i] - child[i] for i in range(3)))
    return model


def rotate(pos: tuple[int, int, int], turns: int, chamber_size: int) -> tuple[int, int, int]:
    x, y, z = pos
    for _ in range(turns):
        x, z = chamber_size - 1 - z, x
    return x, y, z


def rotate_state(state: dict, turns: int) -> dict:
    """Rotate a horizontal ``facing`` property clockwise; other properties are rotation-invariant here."""
    facing = state.get("properties", {}).get("facing")
    if facing not in DIRECTIONS:
        return state
    rotated = DIRECTIONS[(DIRECTIONS.index(facing) + turns) % 4]
    return {**state, "properties": {**state["properties"], "facing": rotated}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region-dir", type=Path, required=True)
    parser.add_argument("--template-dir", type=Path, required=True)
    parser.add_argument("--search-min", type=int, nargs=3, required=True)
    parser.add_argument("--search-max", type=int, nargs=3, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    templates = load_templates(args.template_dir)
    model = expected_model(templates)
    chamber_size = templates["main_chamber"]["size"][0]
    structure_ids = {state["id"] for state in model.values()}
    lo, hi = args.search_min, args.search_max
    chunks = probe_world.load_regions(args.region_dir, (*lo, *hi))
    actual: dict[tuple[int, int, int], dict] = {}
    for (chunk_x, chunk_z), (_chunk, states) in chunks.items():
        for (local_x, y, local_z), state in states.items():
            pos = (chunk_x * 16 + local_x, y, chunk_z * 16 + local_z)
            if all(lo[i] <= pos[i] <= hi[i] for i in range(3)) and state["id"] in structure_ids:
                actual[pos] = state
    if not actual:
        raise SystemExit("No structure palette blocks found in the search volume: /place structure wrote nothing")
    actual_min = tuple(min(p[i] for p in actual) for i in range(3))
    actual_max = tuple(max(p[i] for p in actual) for i in range(3))

    results = []
    for turns in range(4):
        rotated = {rotate(p, turns, chamber_size): rotate_state(s, turns) for p, s in model.items()}
        shift = tuple(actual_min[i] - min(p[i] for p in rotated) for i in range(3))
        placed = {tuple(p[i] + shift[i] for i in range(3)): s for p, s in rotated.items()}
        matched = sum(1 for p, s in placed.items() if p in actual and probe_world.state_matches(s, actual[p]))
        results.append({"rotation_degrees_clockwise": turns * 90, "chamber_origin_after_rotation_shift": list(shift),
                        "matched": matched, "expected": len(placed), "unexpected_extra": len([p for p in actual if p not in placed])})
    best = max(results, key=lambda r: r["matched"])
    report = {"search_volume": {"min": list(lo), "max": list(hi)}, "structure_block_count_found": len(actual),
              "found_bounds": {"min": list(actual_min), "max": list(actual_max)}, "expected_block_count": len(model),
              "candidates": results, "best": best,
              "pass": best["matched"] == best["expected"] and best["unexpected_extra"] == 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"best": best, "pass": report["pass"], "report": str(args.output)}))
    if not report["pass"]:
        raise SystemExit(f"Jigsaw assembly mismatch: best candidate matched {best['matched']}/{best['expected']} blocks")


if __name__ == "__main__":
    main()
