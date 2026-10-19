"""Per-site environmental analysis of a naturally generated SG-01 structure from saved chunk data."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np

from world import World, norm
from structure_export.nbt import read_nbt

STRUCT = "moreminecrafts:forgotten_kingdom/central_cavern"
AIRS = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
FLUIDS = {"minecraft:water": "water", "minecraft:lava": "lava"}
ROT = {"NONE": 0, "CLOCKWISE_90": 1, "CLOCKWISE_180": 2, "COUNTERCLOCKWISE_90": 3}
DIRS = ("north", "east", "south", "west")
FACE = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
NEIGH = tuple(FACE.values())
PIECE_TEMPLATE = {f"{STRUCT}/{n}": n for n in ("main_chamber", "tunnel_north", "tunnel_east", "tunnel_south", "tunnel_west")}


def load_templates(directory: Path) -> dict[str, dict]:
    return {n: read_nbt((directory / f"{n}.nbt").read_bytes())["value"] for n in PIECE_TEMPLATE.values()}


def rot_xz(x: int, z: int, turns: int) -> tuple[int, int]:
    for _ in range(turns % 4):
        x, z = -z, x
    return x, z


def rot_facing(value: str, turns: int) -> str:
    if value in DIRS:
        return DIRS[(DIRS.index(value) + turns) % 4]
    for suffix in ("_up", "_down"):  # jigsaw orientation, e.g. north_up
        if value.endswith(suffix) and value[: -len(suffix)] in DIRS:
            return rot_facing(value[: -len(suffix)], turns) + suffix
    return value


def piece_cells(template: dict, bb: list[int], turns: int):
    """Yield (world_pos, state) for every template cell (air included) placed with ``turns`` clockwise quarter-turns inside ``bb``."""
    palette = template["palette"]
    cells = []
    for block in template["blocks"]:
        x, y, z = block["pos"]
        rx, rz = rot_xz(x, z, turns)
        cells.append((rx, y, rz, palette[block["state"]]))
    mnx, mnz = min(c[0] for c in cells), min(c[2] for c in cells)
    for rx, y, rz, state in cells:
        props = {k: rot_facing(v, turns) if k in ("facing", "orientation") else v for k, v in state.get("properties", {}).items()}
        yield (bb[0] + rx - mnx, bb[1] + y, bb[2] + rz - mnz), {"id": state["id"], "properties": props}


def build_model(start: dict, templates: dict[str, dict]):
    """Return (solid, air, jigsaw) dicts keyed by world pos, from the structure start's own recorded pieces."""
    solid, air, jigsaw = {}, {}, {}
    air_piece: dict[tuple[int, int, int], str] = {}
    pieces = []
    for child in start["Children"]:
        name = PIECE_TEMPLATE[child["pool_element"]["location"]]
        turns = ROT[child["rotation"]]
        pieces.append({"template": name, "rotation": child["rotation"], "bb": child["BB"]})
        for pos, state in piece_cells(templates[name], child["BB"], turns):
            if state["id"] == "minecraft:jigsaw":
                jigsaw[pos] = state
                air[pos] = state  # jigsaw final_state is minecraft:air
                air_piece[pos] = name
            elif state["id"] in AIRS:
                air[pos] = state
                air_piece[pos] = name
            else:
                solid[pos] = state
    build_model.air_piece = air_piece
    return solid, air, jigsaw, pieces


def matches(expected: dict, actual: dict) -> bool:
    if expected["id"] != actual["id"]:
        return False
    saved = actual.get("properties", {})
    for key in ("facing", "half"):
        if key in expected["properties"] and saved.get(key, {"facing": "north", "half": "bottom"}[key]) != expected["properties"][key]:
            return False
    return True


def classify(block_id: str) -> str:
    if block_id in FLUIDS:
        return FLUIDS[block_id]
    if block_id in AIRS:
        return "air"
    if block_id == "minecraft:unloaded":
        return "unloaded"
    return "solid"


def heightmap(chunk, name: str):
    maps = chunk.nbt.get("Heightmaps", {})
    data = maps.get(name)
    if not data:
        return None
    vals = np.array([v & 0xFFFFFFFFFFFFFFFF for v in data], dtype=np.uint64)
    per = 64 // 9
    shifts = np.arange(per, dtype=np.uint64) * np.uint64(9)
    out = ((vals[:, None] >> shifts[None, :]) & np.uint64(511)).reshape(-1)[:256]
    return out.astype(int) + (-64)  # min_y = -64; value is first free y above the surface


def analyze(world: World, start: dict, templates: dict[str, dict], *, snapshot: str) -> dict:
    solid, air, jigsaw, pieces = build_model(start, templates)
    xs = [p[0] for p in solid]; ys = [p[1] for p in solid]; zs = [p[2] for p in solid]
    lo = (min(xs), min(ys), min(zs)); hi = (max(xs), max(ys), max(zs))

    # --- block integrity -------------------------------------------------------------
    mismatches = Counter(); matched = 0; missing_examples = []
    for pos, exp in solid.items():
        act = world.state(*pos)
        if matches(exp, act):
            matched += 1
        else:
            mismatches[f"{exp['id']} -> {act['id']}"] += 1
            if len(missing_examples) < 8:
                missing_examples.append([list(pos), exp["id"], act["id"]])

    # --- interior volume: template air cells -----------------------------------------
    interior = Counter(); interior_examples = {}
    by_piece: dict[str, Counter] = {}
    for pos in air:
        bid = world.block_id(*pos)
        piece_counts = by_piece.setdefault(build_model.air_piece[pos], Counter())
        if bid in AIRS:
            interior["air"] += 1
        else:
            piece_counts["fluid" if bid in FLUIDS else "other_block"] += 1
            kind = FLUIDS.get(bid, "other_block")
            interior[kind if kind != "other_block" else f"block:{bid}"] += 1
            interior_examples.setdefault(kind if kind != "other_block" else bid, []).append(list(pos))

    # --- boundary contact: cells adjacent to the structure but outside it ------------
    placed = set(solid) | set(air)
    shell = {}
    for pos in solid:
        for d in NEIGH:
            n = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])
            if n not in placed:
                shell[n] = None
    contact = Counter(); contact_examples = {}
    for n in shell:
        kind = classify(world.block_id(*n))
        contact[kind] += 1
        if kind in ("air", "water", "lava") and len(contact_examples.setdefault(kind, [])) < 6:
            contact_examples[kind].append(list(n))
    blocks_touching = Counter()
    touching = {"air": set(), "water": set(), "lava": set()}
    for pos in solid:
        for d in NEIGH:
            n = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])
            if n in shell:
                kind = classify(world.block_id(*n))
                if kind in touching:
                    touching[kind].add(pos)
    structure_blocks_touching = {k: len(v) for k, v in touching.items()}

    # --- open apertures (interior air cells with a neighbour outside the structure) ---
    apertures = {}
    open_cells = []
    for pos in air:
        for name, d in FACE.items():
            n = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])
            if n not in placed:
                open_cells.append((pos, n, name))
    # group by outward face direction + plane
    groups: dict[tuple, list] = {}
    for pos, n, name in open_cells:
        plane = n[0] if name in ("east", "west") else n[2] if name in ("north", "south") else n[1]
        groups.setdefault((name, plane), []).append((pos, n))
    for (name, plane), cells in sorted(groups.items()):
        outside = Counter(classify(world.block_id(*n)) for _p, n in cells)
        interior_flu = Counter(classify(world.block_id(*p)) for p, _n in cells)
        cave_cells = [n for _p, n in cells if classify(world.block_id(*n)) == "air"]
        apertures[f"{name}@{plane}"] = {
            "outward_face": name, "cell_count": len(cells), "outside_counts": dict(outside), "aperture_interior_counts": dict(interior_flu),
            "state": ("flooded" if outside.get("water") or outside.get("lava") else "open_to_cave" if outside.get("air") else "blocked_by_terrain"),
            "first_cell_outside": list(cells[0][1]),
            "reachable_cave_cells_bounded": flood_fill(world, cave_cells, limit=4000) if cave_cells else 0,
        }

    # --- environment ------------------------------------------------------------------
    cx = (lo[0] + hi[0]) // 2; cz = (lo[2] + hi[2]) // 2
    chamber = next(p for p in pieces if p["template"] == "main_chamber")["bb"]
    px = (chamber[0] + chamber[3]) // 2; pz = (chamber[2] + chamber[5]) // 2
    plaza_y = chamber[1] + 1
    biome_counts = Counter(world.biome(x, plaza_y, z) for x in range(lo[0], hi[0] + 1, 4) for z in range(lo[2], hi[2] + 1, 4))
    surf = []
    for x, z in [(px, pz), (lo[0] - 8, lo[2] - 8), (lo[0] - 8, hi[2] + 8), (hi[0] + 8, lo[2] - 8), (hi[0] + 8, hi[2] + 8)]:
        ch = world.chunk(x >> 4, z >> 4)
        if ch is None:
            continue
        hm = heightmap(ch, "WORLD_SURFACE") if heightmap(ch, "WORLD_SURFACE") is not None else heightmap(ch, "WORLD_SURFACE_WG")
        if hm is None:
            continue
        surf.append(int(hm[(z & 15) * 16 + (x & 15)]) - 1)
    surf_y = min(surf) if surf else None
    surf_biome = world.biome(px, surf[0] - 1, pz) if surf else "unknown"
    # fluid census inside the whole bounding volume, to see how much natural fluid the structure displaced
    return {
        "snapshot": snapshot,
        "pieces": pieces,
        "bounds_inclusive": {"min": list(lo), "max": list(hi)},
        "dimensions": [hi[i] - lo[i] + 1 for i in range(3)],
        "y_range": [lo[1], hi[1]],
        "chamber_rotation": next(p for p in pieces if p["template"] == "main_chamber")["rotation"],
        "plaza_center": [px, plaza_y, pz],
        "plaza_biome": world.biome(px, plaza_y, pz),
        "footprint_biomes": dict(biome_counts.most_common(6)),
        "surface_min_y_sampled": surf_y,
        "surface_biome_at_center": surf_biome,
        "integrity": {"expected_solid_blocks": len(solid), "matched": matched, "mismatched": len(solid) - matched,
                      "mismatch_kinds": dict(mismatches.most_common(10)), "examples": missing_examples},
        "interior": {"template_air_cells": len(air), "counts": dict(interior), "non_air_by_piece": {k: dict(v) for k, v in by_piece.items() if v}, "examples": {k: v[:6] for k, v in interior_examples.items()}},
        "boundary_contact": {"exterior_shell_cells": len(shell), "shell_counts": dict(contact),
                             "structure_blocks_touching": structure_blocks_touching, "examples": contact_examples},
        "apertures": apertures,
    }


def flood_fill(world: World, seeds: list, limit: int) -> int:
    seen = set(seeds); stack = list(seeds)
    while stack and len(seen) < limit:
        p = stack.pop()
        for d in NEIGH:
            n = (p[0] + d[0], p[1] + d[1], p[2] + d[2])
            if n in seen:
                continue
            if classify(world.block_id(*n)) == "air":
                seen.add(n); stack.append(n)
    return len(seen)
