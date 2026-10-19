#!/usr/bin/env python3
"""Natural 26.3 SG-03 generation: reconstruct 21 pieces from saved vanilla starts."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter

import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE), str(ROOT / "validation/minecraft-visual")]

import assembly_probe as ap  # noqa: E402
from spread import SG01, candidates_in_ring, exclusion_suppressed  # noqa: E402
from world import Server, World  # noqa: E402

STRUCT = "moreminecrafts:forgotten_kingdom/central_cavern"
ROT = {"NONE": 0, "CLOCKWISE_90": 1, "CLOCKWISE_180": 2, "COUNTERCLOCKWISE_90": 3}
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
FLUID = {"minecraft:water", "minecraft:lava"}
NEIGHBORS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def overlay_kind(actual: str) -> str:
    if actual.startswith("minecraft:sculk"):
        return "sculk"
    if actual in {"minecraft:amethyst_block", "minecraft:budding_amethyst",
                  "minecraft:calcite", "minecraft:smooth_basalt"}:
        return "geode"
    if actual in {"minecraft:cobblestone", "minecraft:mossy_cobblestone"}:
        return "monster_room"
    return "unexplained"


def count_clay_outside(world: World, boxes: list, inside: set, margin: int = 64) -> dict:
    """Natural `minecraft:clay` blocks near (but never inside) the structure.

    Proves vanilla lush-cave clay generation still runs around the structure, i.e. the integrity result is not
    obtained by suppressing the feature. Only already-saved chunks in the margin are read.
    """
    if not boxes:
        return {"count": 0, "chunks_read": 0, "biomes": {}, "margin_blocks": margin}
    lo = [min(b[0][i] for b in boxes) for i in range(3)]
    hi = [max(b[1][i] for b in boxes) for i in range(3)]
    count, biomes, chunks = 0, Counter(), 0
    for cx in range((lo[0] - margin) >> 4, ((hi[0] + margin) >> 4) + 1):
        for cz in range((lo[2] - margin) >> 4, ((hi[2] + margin) >> 4) + 1):
            chunk = world.chunk(cx, cz)
            if chunk is None:
                continue
            chunks += 1
            for sec_y, (palette, idx) in chunk.sections.items():
                clay = [i for i, st in enumerate(palette) if st["id"] == "minecraft:clay"]
                if not clay:
                    continue
                for flat in np.flatnonzero(np.isin(idx, clay)):
                    x, y, z = cx * 16 + (flat & 15), sec_y * 16 + (flat >> 8), cz * 16 + ((flat >> 4) & 15)
                    if (x, y, z) in inside:
                        continue
                    count += 1
                    biomes[world.biome(x, y, z)] += 1
    return {"count": count, "chunks_read": chunks, "biomes": dict(biomes.most_common(5)), "margin_blocks": margin}


def inspect(world: World, start: dict, templates: dict) -> dict:
    children = start.get("Children", [])
    result = {"piece_count": len(children), "pieces": {}, "rooms": {}, "matched": 0,
              "expected": 0, "overwrites": {}, "missing_or_other": 0,
              "examples": [], "mismatches": [], "interior_fluids": {}, "exterior_contacts": {},
              "trial_spawners": 0, "trial_spawner_entities": 0, "errors": []}
    solids, inside, empty = {}, set(), {}
    boxes = []
    for i, child in enumerate(children):
        name = child.get("pool_element", {}).get("location")
        rotation = child.get("rotation")
        if name not in templates or rotation not in ROT:
            result["errors"].append(f"unknown template/rotation at piece {i}: {name}, {rotation}")
            continue
        bbox = tuple(child["BB"])
        placed = ap.Placed(templates[name], ROT[rotation], bbox[:3])
        if placed.bbox() != (bbox[:3], bbox[3:]):
            result["errors"].append(f"incorrect bounding box at piece {i}: {name}")
        if any(ap.bbox_overlap(placed.bbox(), old) for old in boxes):
            result["errors"].append(f"bounding box overlap at piece {i}: {name}")
        boxes.append(placed.bbox())
        leaf = name.rsplit("/", 1)[-1]
        result["pieces"][leaf] = result["pieces"].get(leaf, 0) + 1
        if "/rooms/" in name:
            result["rooms"][leaf] = result["rooms"].get(leaf, 0) + 1
        for pos, state in placed.blocks(include_air=True).items():
            if pos in inside:
                result["errors"].append(f"duplicate template cell at {pos}")
                break
            inside.add(pos)
            if state["id"] in AIR:
                empty[pos] = "main" if name.endswith("/main_chamber") else leaf
            else:
                solids[pos] = (state, "main" if name.endswith("/main_chamber") else leaf)
    overwrites = Counter()
    transitions = Counter()
    affected_biomes = Counter()
    affected_owners = Counter()
    affected_y = Counter()
    clay_positions = []
    fluid = Counter()
    for pos, (expected, owner) in solids.items():
        actual = world.state(*pos)
        result["expected"] += 1
        if ap.state_matches(expected, actual):
            result["matched"] += 1
        else:
            category = overlay_kind(actual["id"])
            overwrites[category] += 1
            transitions[(expected["id"], actual["id"])] += 1
            if expected["id"] == "minecraft:moss_block" and actual["id"] == "minecraft:clay":
                affected_biomes[world.biome(*pos)] += 1
                affected_owners[owner] += 1
                affected_y[pos[1]] += 1
                clay_positions.append(pos)
            if category == "unexplained":
                result["missing_or_other"] += 1
            if len(result["mismatches"]) < 20000:
                result["mismatches"].append([pos[0], pos[1], pos[2], owner, expected["id"], actual["id"]])
            if len(result["examples"]) < 12:
                result["examples"].append({"pos": pos, "room": owner,
                    "expected": expected["id"], "actual": actual["id"], "type": category})
        if expected["id"] == "minecraft:trial_spawner" and actual["id"] == expected["id"]:
            result["trial_spawners"] += 1
            chunk = world.chunk(pos[0] >> 4, pos[2] >> 4)
            if chunk and any(e.get("id") == "minecraft:trial_spawner"
                             and (e.get("x"), e.get("y"), e.get("z")) == pos
                             for e in chunk.nbt.get("block_entities", [])):
                result["trial_spawner_entities"] += 1
    intrusions = Counter()
    for pos, owner in empty.items():
        state = world.block_id(*pos)
        if state in FLUID:
            fluid[(owner, state.rsplit(":", 1)[-1])] += 1
        elif state not in AIR and state != "minecraft:unloaded":
            intrusions[state] += 1
    shell = set()
    for x, y, z in solids:
        for dx, dy, dz in NEIGHBORS:
            other = (x + dx, y + dy, z + dz)
            if other not in inside:
                shell.add(other)
    contacts = Counter()
    for pos in shell:
        name = world.block_id(*pos)
        if name == "minecraft:cave_air":
            contacts["cave_air"] += 1
        elif name in FLUID:
            contacts[name.rsplit(":", 1)[-1]] += 1
        elif name in AIR:
            contacts["other_air"] += 1
        elif name == "minecraft:unloaded":
            contacts["unloaded"] += 1
        else:
            contacts["solid"] += 1
    result["overwrites"] = dict(overwrites)
    result["state_transitions"] = [
        {"expected": src, "actual": dst, "count": n}
        for (src, dst), n in sorted(transitions.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    result["clay_replacement_diagnostics"] = {
        "count": len(clay_positions),
        "biomes": dict(sorted(affected_biomes.items())),
        "rooms": dict(sorted(affected_owners.items())),
        "y_levels": {str(k): v for k, v in sorted(affected_y.items())},
        "bounds": [
            [min(p[i] for p in clay_positions) for i in range(3)],
            [max(p[i] for p in clay_positions) for i in range(3)]
        ] if clay_positions else None,
        "positions": [list(p) for p in sorted(clay_positions)],
    }
    result["interior_intrusions"] = dict(intrusions.most_common())
    result["vanilla_clay_outside_structure"] = count_clay_outside(world, boxes, inside)
    result["interior_fluids"] = {f"{k[0]}:{k[1]}": v for k, v in sorted(fluid.items())}
    result["exterior_contacts"] = dict(contacts)
    result["pass"] = (len(children) == 21 and sum(result["rooms"].values()) == 16
                      and result["pieces"].get("main_chamber") == 1
                      and sum(count for name, count in result["pieces"].items()
                              if name.startswith("tunnel_")) == 4
                      and not result["errors"] and result["missing_or_other"] == 0
                      and contacts["unloaded"] == 0
                      and not fluid[("main", "water")] and not fluid[("main", "lava")]
                      and result["trial_spawners"] == result["trial_spawner_entities"])
    return result


def wait_loaded(srv: Server, x: int, z: int, seconds=240):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if "Test passed" in srv.cmd(f"execute if loaded {x} 0 {z}"):
            return
        time.sleep(1)
    raise RuntimeError(f"chunk never loaded: {x},{z}")


def run(args, templates):
    candidates = sorted((p for p in candidates_in_ring(args.seed, SG01, args.ring)
                         if not exclusion_suppressed(args.seed, p)),
                        key=lambda p: (p[0] ** 2 + p[1] ** 2, p))[:args.sites]
    if not candidates:
        raise RuntimeError("no candidate sites in bounded search")
    folder = args.out / f"seed-{args.seed}-world"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    server = Server("java", args.jar.resolve(), folder, args.seed, args.pack.resolve(), port=args.port,
                    extra_props={"difficulty": "normal", "spawn-monsters": "true", "max-tick-time": "-1"})
    result = {"seed": args.seed, "method": "normal terrain + vanilla starts (no /place)",
              "candidates": candidates, "sites": [],
              "real_player_traversal": "NOT RUN",
              "trial_spawner_activation": "NOT RUN: no player entered the generated rooms",
              "vanilla_trial_chambers_coexistence": "NOT RUN"}
    try:
        for cx, cz in candidates:
            x, z = cx * 16, cz * 16
            response = server.cmd(f"forceload add {x-112} {z-112} {x+112} {z+112}")
            if "Too many" in response or "Failed" in response:
                raise RuntimeError(response)
            wait_loaded(server, x, z)
        server.save()
        world = World(server.region_dir)
        generated = []
        for cx, cz in candidates:
            chunk = world.chunk(cx, cz)
            start = ((chunk.nbt.get("structures") or {}).get("starts") or {}).get(STRUCT) if chunk else None
            site = {"candidate_chunk": [cx, cz], "generated": bool(start),
                    "chunk_status": chunk.status if chunk else "unloaded"}
            # Full placement identity, not merely the count of Jigsaw pieces.
            # The A/B comparison must reject changes to any room or bounding box.
            site["start_signature"] = [
                {"location": c.get("pool_element", {}).get("location"),
                 "rotation": c.get("rotation"), "bb": list(c.get("BB", [])),
                 "pos": list(c.get("Pos", []))}
                for c in (start.get("Children", []) if start else [])
            ]
            result["sites"].append(site)
            if not start:
                continue
            generated.append((site, start))
        # Generate all adjacent chunks spanning the actual recorded 21 pieces.
        for site, start in generated:
            boxes = [c["BB"] for c in start.get("Children", [])]
            if not boxes:
                raise RuntimeError("empty vanilla structure start")
            bounds = [min(b[i] for b in boxes) for i in range(3)] + [
                      max(b[i+3] for b in boxes) for i in range(3)]
            site["bbox"] = bounds
            response = server.cmd(f"forceload add {bounds[0]-16} {bounds[2]-16} {bounds[3]+16} {bounds[5]+16}")
            if "Too many" in response or "Failed" in response:
                raise RuntimeError(response)
            wait_loaded(server, bounds[0]-16, bounds[2]-16)
            wait_loaded(server, bounds[3]+16, bounds[5]+16)
        server.save()
        world = World(server.region_dir)
        for site, start in generated:
            site["before_ticks"] = inspect(world, start, templates)
        if args.ticks:
            log_offset = server.log_path.stat().st_size
            result["tick_command"] = server.cmd(f"tick sprint {args.ticks}")[:160]
            deadline = time.time() + 240
            while time.time() < deadline:
                if "Sprint completed" in server.log_path.read_text(errors="replace")[log_offset:]:
                    break
                time.sleep(2)
            else:
                raise TimeoutError("tick sprint incomplete")
            server.save()
            world = World(server.region_dir)
            for site, start in generated:
                site["after_ticks"] = inspect(world, start, templates)
        result["generated_sites"] = len(generated)
        result["pass"] = bool(generated) and all(
            site["before_ticks"]["pass"] and site.get("after_ticks", site["before_ticks"])["pass"]
            for site, _start in generated)
        return result
    finally:
        server.stop()
        shutil.copy2(server.log_path, args.out / f"server-{args.seed}.log")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--sites", type=int, default=2)
    parser.add_argument("--ring", type=int, default=4)
    parser.add_argument("--ticks", type=int, default=200)
    parser.add_argument("--port", type=int, default=25575, help="RCON port (server port is this minus 100)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        templates, _pools = ap.load_pack(args.pack)
        if len(templates) != 11:
            raise RuntimeError(f"expected 11 stage templates, got {len(templates)}")
        report = run(args, templates)
    except Exception as e:
        report = {"seed": args.seed, "pass": False, "error": f"{type(e).__name__}: {e}"}
    path = args.out / f"natural-{args.seed}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pass": report["pass"], "report": str(path),
                      "generated_sites": report.get("generated_sites"), "error": report.get("error")}))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
