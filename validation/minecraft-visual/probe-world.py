#!/usr/bin/env python3
"""Compare exported structure samples with saved Minecraft region chunk data."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from structure_export.nbt import read_nbt


def normalize_palette_entry(entry: dict | str) -> dict:
    """Saved-chunk palette entries are {id, properties}; a block without properties is a bare string.

    Since 1.21.5 mixed-type NBT lists store a non-compound element wrapped as {"": value}.
    """
    if isinstance(entry, str):
        return {"id": entry}
    if "" in entry:
        return {"id": entry[""]}
    return entry


# Saved chunks omit properties that equal their default value, so an expected property
# missing from the saved state is accepted only if it equals the default listed here.
DEFAULT_PROPERTIES = {
    "facing": "north", "half": "bottom", "shape": "straight",
    "waterlogged": "false", "orientation": "north_up",
}


def state_matches(expected: dict, actual: dict) -> bool:
    """Same block id; every expected property equals the saved (or default) value.

    Properties the game derived itself (e.g. wall connections after neighbour updates)
    are not part of the template and are ignored.
    """
    if expected["id"] != actual["id"]:
        return False
    saved = actual.get("properties", {})
    return all(saved.get(key, DEFAULT_PROPERTIES.get(key)) == value for key, value in expected.get("properties", {}).items())


def unpack_state(section: dict, local_x: int, local_y: int, local_z: int) -> dict:
    block_states = section["block_states"]
    palette = block_states["palette"]
    index = (local_y << 8) | (local_z << 4) | local_x
    if len(palette) == 1:
        return palette[0]
    bits = max(4, (len(palette) - 1).bit_length())
    per_long = 64 // bits
    values = block_states.get("data", [])
    packed = values[index // per_long] & 0xFFFFFFFFFFFFFFFF
    palette_index = (packed >> ((index % per_long) * bits)) & ((1 << bits) - 1)
    return palette[palette_index]


def chunk_states(chunk: dict) -> dict[tuple[int, int, int], dict]:
    states = {}
    for section in chunk.get("sections", []):
        block_states = section.get("block_states")
        if not block_states:
            continue
        section_y = int(section["Y"])
        section = {**section, "block_states": {**block_states, "palette": [normalize_palette_entry(e) for e in block_states["palette"]]}}
        for local_y in range(16):
            y = section_y * 16 + local_y
            for local_z in range(16):
                for local_x in range(16):
                    state = unpack_state(section, local_x, local_y, local_z)
                    states[(local_x, y, local_z)] = state
    return states


def read_region_chunk(path: Path, chunk_x: int, chunk_z: int) -> dict | None:
    local_x, local_z = chunk_x % 32, chunk_z % 32
    slot = local_x + local_z * 32
    with path.open("rb") as stream:
        stream.seek(slot * 4)
        location = stream.read(4)
        if len(location) != 4:
            return None
        sector_offset = int.from_bytes(location[:3], "big")
        if sector_offset == 0:
            return None
        stream.seek(sector_offset * 4096)
        length_bytes = stream.read(4)
        if len(length_bytes) != 4:
            return None
        length = struct.unpack(">I", length_bytes)[0]
        compression = stream.read(1)[0]
        payload = stream.read(length - 1)
    if compression == 1:
        raw = gzip.decompress(payload)
    elif compression == 2:
        raw = zlib.decompress(payload)
    elif compression == 3:
        raw = payload
    else:
        raise ValueError(f"Unsupported Minecraft region compression {compression} in {path}")
    return read_nbt(raw)["value"]


def load_regions(region_dir: Path, bounds: tuple[int, int, int, int, int, int]) -> dict:
    min_x, min_y, min_z, max_x, max_y, max_z = bounds
    min_cx, max_cx = min_x // 16, max_x // 16
    min_cz, max_cz = min_z // 16, max_z // 16
    chunks = {}
    for region_path in sorted(region_dir.glob("r.*.*.mca")):
        match = re.fullmatch(r"r\.(-?\d+)\.(-?\d+)\.mca", region_path.name)
        if not match:
            continue
        region_x, region_z = map(int, match.groups())
        for chunk_x in range(max(min_cx, region_x * 32), min(max_cx, region_x * 32 + 31) + 1):
            for chunk_z in range(max(min_cz, region_z * 32), min(max_cz, region_z * 32 + 31) + 1):
                chunk = read_region_chunk(region_path, chunk_x, chunk_z)
                if chunk is not None:
                    chunks[(chunk_x, chunk_z)] = (chunk, chunk_states(chunk))
    return chunks


def state_at(chunks: dict, x: int, y: int, z: int) -> dict:
    chunk_x, chunk_z = x // 16, z // 16
    loaded = chunks.get((chunk_x, chunk_z))
    if loaded is None:
        return {"id": "minecraft:unloaded"}
    _chunk, states = loaded
    return states.get((x % 16, y, z % 16), {"id": "minecraft:air"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region-dir", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--origin", type=int, nargs=3, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--radius", type=int, default=64)
    parser.add_argument("--control-origin", type=int, nargs=3)
    args = parser.parse_args()

    template = read_nbt(args.template.read_bytes())["value"]
    origin_x, origin_y, origin_z = args.origin
    size_x, size_y, size_z = template["size"]
    bounds = (
        origin_x - args.radius, origin_y - 20, origin_z - args.radius,
        origin_x + size_x - 1 + args.radius, origin_y + size_y - 1 + 20,
        origin_z + size_z - 1 + args.radius,
    )
    load_bounds = bounds
    if args.control_origin:
        cx, cy, cz = args.control_origin
        load_bounds = (
            min(bounds[0], cx - 24), min(bounds[1], cy), min(bounds[2], cz - 24),
            max(bounds[3], cx + 24), max(bounds[4], cy + 40), max(bounds[5], cz + 24),
        )
    chunks = load_regions(args.region_dir, load_bounds)
    server_log = args.server_log.read_text(errors="replace")

    # Pick one deterministic solid point per palette state: all 15 non-air
    # states are sampled, including all stair facings and four jigsaw facings.
    samples_by_state = {}
    palette = template["palette"]
    for block in template["blocks"]:
        expected = palette[block["state"]]
        if expected["id"] == "minecraft:air":
            continue
        samples_by_state.setdefault(block["state"], (block["pos"], expected))

    samples = []
    for state_id, (local, expected) in samples_by_state.items():
        local_x, local_y, local_z = local
        world = [origin_x + local_x, origin_y + local_y, origin_z + local_z]
        actual = state_at(chunks, *world)
        index = len(samples)
        marker = f"SG01_TEMPLATE_PROBE_{index:02d}_MATCH"
        miss_marker = f"SG01_TEMPLATE_PROBE_{index:02d}_MISS"
        if marker in server_log:
            command_result = "MATCH"
        elif miss_marker in server_log:
            command_result = "MISS"
        else:
            command_result = "NO_MARKER"
        samples.append({
            "local": local,
            "expected_world": world,
            "expected_state": expected,
            "saved_world_state": actual,
            "saved_world_match": state_matches(expected, actual),
            "rcon_probe": command_result,
        })

    distinctive_names = {state["id"] for _pos, state in samples_by_state.values()}
    found = {name: [] for name in sorted(distinctive_names)}
    min_x, min_y, min_z, max_x, max_y, max_z = bounds
    for (chunk_x, chunk_z), (_chunk, states) in chunks.items():
        for (local_x, y, local_z), state in states.items():
            x, z = chunk_x * 16 + local_x, chunk_z * 16 + local_z
            if min_x <= x <= max_x and min_y <= y <= max_y and min_z <= z <= max_z:
                name = state.get("id")
                if name in found:
                    found[name].append([x, y, z])

    matches = sum(sample["saved_world_match"] for sample in samples)
    report = {
        "template": args.template.as_posix(),
        "data_version": template["DataVersion"],
        "size": template["size"],
        "local_origin": [0, 0, 0],
        "command_origin": [origin_x, origin_y, origin_z],
        "coordinate_mapping": "world = command_origin + local; rotation=none; mirror=none",
        "sample_count": len(samples),
        "saved_chunk_count": len(chunks),
        "saved_chunk_load_bounds_inclusive": {"min": [load_bounds[0], load_bounds[1], load_bounds[2]], "max": [load_bounds[3], load_bounds[4], load_bounds[5]]},
        "saved_world_samples_matched": matches,
        "samples": samples,
        "search_bounds_inclusive": {"min": [min_x, min_y, min_z], "max": [max_x, max_y, max_z]},
        "distinctive_palette_search": {name: {"count": len(points), "first_positions": points[:20]} for name, points in found.items()},
    }
    if args.control_origin:
        control_x, control_y, control_z = args.control_origin
        control_bounds = (control_x - 24, control_y, control_z - 24, control_x + 24, control_y + 40, control_z + 24)
        counts: dict[str, dict] = {}
        cmin_x, cmin_y, cmin_z, cmax_x, cmax_y, cmax_z = control_bounds
        for (chunk_x, chunk_z), (_chunk, states) in chunks.items():
            for (local_x, y, local_z), state in states.items():
                x, z = chunk_x * 16 + local_x, chunk_z * 16 + local_z
                if cmin_x <= x <= cmax_x and cmin_y <= y <= cmax_y and cmin_z <= z <= cmax_z:
                    name = state.get("id", "")
                    if name not in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
                        entry = counts.setdefault(name, {"count": 0, "first_positions": []})
                        entry["count"] += 1
                        if len(entry["first_positions"]) < 20:
                            entry["first_positions"].append([x, y, z])
        report["vanilla_control_search_bounds"] = {"min": [cmin_x, cmin_y, cmin_z], "max": [cmax_x, cmax_y, cmax_z]}
        report["vanilla_control_non_air_blocks"] = counts
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"sample_count": len(samples), "saved_chunk_count": len(chunks), "saved_world_samples_matched": matches, "report": str(args.output)}))
    if len(samples) < 10:
        raise SystemExit("Fewer than ten distinctive solid NBT samples were available")
    if matches != len(samples):
        raise SystemExit(f"Only {matches}/{len(samples)} NBT-derived saved-world probes matched")


if __name__ == "__main__":
    main()
