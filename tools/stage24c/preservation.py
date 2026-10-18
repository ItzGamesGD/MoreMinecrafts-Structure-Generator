"""Loot-table / jigsaw / skull / water preservation: original source vs restored NBT vs live placed world."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24b_candidate import Candidate
from tools.stage24b_source import load_original
from tools.stage24c.common import *  # noqa
from tools.stage24c.mcserver import World

KEYS = ("LootTable", "LootTableSeed", "name", "pool", "target", "final_state", "joint", "rotation", "SkullOwner", "profile")


def pick(nbt):
    d = {}
    for k in KEYS:
        if k in nbt:
            d[k] = str(nbt[k])
    return d


def main():
    world = World(OUT / "_work/placement-server/world/dimensions/minecraft/overworld")
    report = {}
    for i, m in enumerate(MODULES):
        root, _, _ = load_original(m)
        orig = {tuple(int(v) for v in b["pos"]): b for b in root["blocks"]}
        opal = [str(p["Name"]) for p in root["palette"]]
        rest = load_nbt(S24B / m / "restored.nbt")
        rb = {tuple(int(v) for v in b["pos"]): b for b in rest["blocks"]}
        rpal = [str(p["Name"]) for p in rest["palette"]]
        origin = (100 + i * 80, -60, 100)  # rotation none row in placement.py
        rows, ok = [], True
        for pos, b in sorted(orig.items()):
            if "nbt" not in b:
                continue
            name = opal[int(b["state"])]
            got_r = rb.get(pos)
            same_state = got_r is not None and rpal[int(got_r["state"])] == name
            same_nbt = got_r is not None and "nbt" in got_r and str(got_r["nbt"]) == str(b["nbt"])
            live = world.block_entity(origin[0] + pos[0], origin[1] + pos[1], origin[2] + pos[2])
            live_pick = pick(live) if live is not None else None
            live_match = live_pick is not None and all(live_pick.get(k) == v for k, v in pick(b["nbt"]).items())
            rows.append({"pos": list(pos), "block": name, "original": pick(b["nbt"]), "restored_identical": bool(same_state and same_nbt),
                         "live": live_pick, "live_matches_original": bool(live_match)})
            ok &= bool(same_state and same_nbt and live_match)
        wo = sum(1 for b in orig.values() if opal[int(b["state"])] == "minecraft:water")
        wr = sum(1 for b in rb.values() if rpal[int(b["state"])] == "minecraft:water")
        report[m] = {"block_entities_checked": len(rows), "all_preserved_and_live": ok, "water_original": wo, "water_restored": wr, "entries": rows}
        print(m, len(rows), ok, "water", wo, wr, flush=True)
    (OUT / "placement/preservation-report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
