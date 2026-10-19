#!/usr/bin/env python3
"""SG-02/SG-03 runtime acceptance: real Minecraft 26.3 server placement of every template and assemblies.

1. start a disposable flat-world server with the pack enabled;
2. ``/place template`` every exported template at a clear origin and compare *every cell* (air
   included) with the saved region data;
3. ``/place structure`` the Jigsaw structure at several locations, recover each assembly from the
   saved world, prove every non-air block is explained by exactly one piece, that no bounding
   boxes overlap, that every connector is filled, and that routes are walkable;
4. write evidence JSON and stage results; optionally leave the server running for screenshots.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import assembly_probe as ap  # noqa: E402
from rcon_client import Rcon, start_server  # noqa: E402

START = "moreminecrafts:forgotten_kingdom/central_cavern/main_chamber"
STRUCTURE = "moreminecrafts:forgotten_kingdom/central_cavern"
ASSEMBLY_ORIGINS = [(1000, 1000), (1400, 1000), (1800, 1000), (1000, 1400), (1400, 1400), (1800, 1400),
                    (1000, 1800), (1400, 1800)]


def mark(result_file: Path, name: str, verdict: str) -> None:
    lines = result_file.read_text().splitlines() if result_file.exists() else []
    lines = [line for line in lines if not line.startswith(name + "=")]
    lines.append(f"{name}={verdict}")
    result_file.write_text("\n".join(lines) + "\n")


def check_block_entities(rcon, templates, origins, failures):
    """Read block-entity data back from the running server and compare with the template contract."""
    import re

    results = []
    tables = set()
    for identifier, (ox, oy, oz) in origins.items():
        t = templates[identifier]
        for local, nbt in sorted(t.nbt.items()):
            if nbt["id"] == "minecraft:jigsaw":
                continue
            wx, wy, wz = ox + local[0], oy + local[1], oz + local[2]
            text = rcon.run(f"data get block {wx} {wy} {wz}")
            entry = {"template": identifier.rsplit("/", 1)[-1], "pos": list(local), "id": nbt["id"], "pass": True}
            if f'id: "{nbt["id"]}"' not in text:
                entry["pass"] = False
                entry["actual"] = text[:200]
            for key in ("LootTable", "normal_config", "ominous_config"):
                if key in nbt:
                    match = re.search(rf'{key}: "([^"]+)"', text)
                    entry[key] = match.group(1) if match else None
                    if key == "LootTable":
                        tables.add(nbt[key])
                    # A config equal to the game's default is omitted from the readback; only a *different* value is an error.
                    if entry[key] is not None and entry[key] != nbt[key]:
                        entry["pass"] = False
                    if key == "LootTable" and entry[key] != nbt[key]:
                        entry["pass"] = False
            results.append(entry)
            if not entry["pass"]:
                failures.append(f"block entity mismatch {entry}")
    # Negative control first: the checker must reject a table that does not exist.
    control = rcon.run("execute in minecraft:overworld run loot spawn 0 120 3000 loot minecraft:chests/sg_control_does_not_exist")
    control_rejected = "Dropped" not in control and "dropped" not in control
    results.append({"loot_table_negative_control": "minecraft:chests/sg_control_does_not_exist", "rejected": control_rejected, "reply": control[:120], "pass": control_rejected})
    if not control_rejected:
        failures.append("loot-table check accepted a nonexistent table: checker is not trustworthy")
    for table in sorted(tables):
        out = rcon.run(f"execute in minecraft:overworld run loot spawn 0 120 3000 loot {table}")
        ok = "Dropped" in out or "dropped" in out
        results.append({"loot_table": table, "pass": ok, "reply": out[:120]})
        if not ok:
            failures.append(f"loot table {table} rejected: {out}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--java-cmd", default="java -Xmx3G -jar server.jar nogui")
    parser.add_argument("--assemblies", type=int, default=6)
    parser.add_argument("--keep-server", action="store_true")
    parser.add_argument("--label", default="sg")
    args = parser.parse_args()

    evidence = args.evidence
    evidence.mkdir(parents=True, exist_ok=True)
    result_file = evidence / "runtime-result.txt"
    templates, pools = ap.load_pack(args.pack)
    log = args.run_dir.parent / "logs" / "server.log"
    proc = start_server(args.run_dir, {"sg": args.pack}, args.java_cmd, log)
    (args.run_dir.parent / "server.pid").write_text(str(proc.pid))
    mark(result_file, "server-startup", "PASS")
    rcon = Rcon()
    report: dict = {"label": args.label, "templates": {}, "assemblies": []}
    failures: list[str] = []
    try:
        enabled = rcon.run("datapack list enabled")
        if "file/sg" not in enabled:
            raise SystemExit("datapack not enabled: " + enabled)
        mark(result_file, "datapack-load", "PASS")
        region_dir = args.run_dir / "world/dimensions/minecraft/overworld/region"

        # --- individual templates -------------------------------------------------------
        origins = {}
        for index, identifier in enumerate(sorted(templates)):
            ox, oy, oz = 64 * index, 100, 3000
            origins[identifier] = (ox, oy, oz)
            t = templates[identifier]
            rcon.run(f"forceload add {ox - 16} {oz - 16} {ox + t.size[0] + 16} {oz + t.size[2] + 16}")
        for identifier, (ox, oy, oz) in origins.items():
            out = rcon.run(f"execute in minecraft:overworld run place template {identifier} {ox} {oy} {oz}")
            if "Loaded template" not in out:
                failures.append(f"place template {identifier}: {out}")
        rcon.run("save-all flush")
        time.sleep(1)
        report["standalone_origins"] = {k: list(v) for k, v in origins.items()}
        world = ap.World(region_dir, (-32, 90, 2980), (64 * len(origins) + 80, 140, 3100))
        all_ok = True
        for identifier, (ox, oy, oz) in origins.items():
            t = templates[identifier]
            placed = ap.Placed(t, 0, (ox, oy, oz))
            ok, total, bad = ap.match_fraction(placed, world.cells, include_air=True)
            entry = {"size": list(t.size), "cells_matched": ok, "cells_expected": total, "pass": ok == total,
                     "solid_blocks": len(t.solid)}
            if bad:
                entry["mismatch_examples"] = [[list(p), s, a] for p, s, a in bad]
            report["templates"][identifier] = entry
            all_ok &= ok == total
        mark(result_file, "template-placement", "PASS" if all_ok and not failures else "FAIL")
        if not all_ok:
            failures.append("template world comparison failed")

        # --- block entities the game must have accepted (loot tables, trial spawner configs) ----
        report["block_entities"] = check_block_entities(rcon, templates, origins, failures)
        mark(result_file, "block-entities", "PASS" if not any(e["pass"] is False for e in report["block_entities"]) else "FAIL")

        # --- jigsaw assemblies ----------------------------------------------------------
        origins_xz = ASSEMBLY_ORIGINS[: args.assemblies]
        for x, z in origins_xz:
            rcon.run(f"forceload add {x - 96} {z - 96} {x + 96} {z + 96}")
        for x, z in origins_xz:
            out = rcon.run(f"execute in minecraft:overworld run place structure {STRUCTURE} {x} 100 {z}")
            if "Generated structure" not in out:
                failures.append(f"place structure at {x},{z}: {out}")
        rcon.run("save-all flush")
        time.sleep(1)
        assembly_ok = True
        for x, z in origins_xz:
            lo, hi = (x - 100, -58, z - 100), (x + 100, 60, z + 100)
            world = ap.World(region_dir, lo, hi)
            entry: dict = {"requested_at": [x, z], "blocks_in_volume": len(world.cells)}
            try:
                pieces, slots = ap.recover_assembly(
                    templates, pools, world.cells, START, (23, 0, 23), "minecraft:polished_deepslate")
            except SystemExit as exc:
                entry["error"] = str(exc)
                entry["pass"] = False
                report["assemblies"].append(entry)
                assembly_ok = False
                continue
            verdict = ap.verify_assembly(pieces, slots, world.cells)
            start = pieces[0]["placed"]
            entry.update({
                "start_rotation_turns": start.turns, "start_origin": list(start.origin),
                "pieces": [{"template": p["id"], "origin": list(p["placed"].origin), "turns": p["placed"].turns,
                            "bbox": [list(b) for b in p["placed"].bbox()], "slot": p["slot"]} for p in pieces],
                "slots": [{k: v for k, v in s.items() if k != "tried"} for s in slots],
                "verification": verdict,
            })
            if verdict["unfilled_slots"]:
                verdict["pass"] = False
            walk = ap.assembly_walk_report(pieces, world)
            entry["accessibility"] = walk
            entry["pass"] = verdict["pass"] and walk["pass"]
            assembly_ok &= entry["pass"]
            report["assemblies"].append(entry)
        mark(result_file, "jigsaw-placement", "PASS" if assembly_ok and not failures else "FAIL")
        report["failures"] = failures
        report["pass"] = all_ok and assembly_ok and not failures
    finally:
        (evidence / "runtime-report.json").write_text(json.dumps(report, indent=2, default=list) + "\n")
        if not args.keep_server:
            try:
                rcon.run("stop")
                proc.wait(60)
            except Exception:
                proc.kill()
    print(json.dumps({"pass": report.get("pass"), "failures": failures}))
    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
