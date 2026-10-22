"""Stage 24-G sweep comparison (vanilla / Stage 24-F / Stage 24-G), issue register, terrain classification, matrix."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, ROOT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT, rot  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g.build import D24G, D24F  # noqa: E402

C_WG = ROOT / "artifacts/ancient-city-restoration/stage-24c/worldgen"
F_WG = ROOT / "artifacts/ancient-city-restoration/stage-24f/worldgen"
G_WG = D24G / "worldgen"
SEEDS = range(24001, 24025)
KEY = ("pos", "rotation", "bb", "ground_level_delta", "junction_count")


def j(p):
    return json.loads(Path(p).read_text())


def placements():
    rows, cities_same_f, cities_same_v = [], 0, 0
    for s in SEEDS:
        v = j(C_WG / f"manifest-{s}-vanilla.json")["cities"][0]["pieces"]
        f = j(F_WG / f"manifest-{s}-f24.json")["cities"][0]["pieces"]
        g = j(G_WG / f"manifest-{s}-g24.json")["cities"][0]["pieces"]
        same_f = len(f) == len(g) and all(all(a[k] == b[k] for k in KEY) and a["template"] == b["template"] for a, b in zip(f, g))
        vdiff = [(i, b["template"].rsplit("/", 1)[-1], k) for i, (a, b) in enumerate(zip(v, g)) for k in KEY if a[k] != b[k]]
        approved = all(t in ("large_ruin_1", "medium_ruin_2") and k == "bb" for _, t, k in vdiff)
        cities_same_f += same_f
        cities_same_v += len(v) == len(g) and approved
        rows.append({"seed": s, "pieces": len(g), "identical_to_stage24f": same_f, "identical_to_vanilla_except_approved_heights": len(v) == len(g) and approved,
                     "vanilla_differences": [{"index": i, "template": t, "field": k} for i, t, k in vdiff],
                     "protected_list_pieces": sum(1 for p in g if p.get("list_elements") and p["template"])})
    return rows, cities_same_f, cities_same_v


def decay(variant, inv):
    """Decorative decay as actually present in the saved worlds (model-verified cells only)."""
    man_dir = F_WG if variant == "f24" else G_WG
    replay = j((D24G / "investigation/f24-processor-replay.json") if variant == "f24" else G_WG / "g24-processor-replay.json")
    rotted = Counter()
    for r in replay:
        for x in r["losses"]:
            if x["cause"] == "block_rot":
                prot = {tuple(e["pos"]) for e in inv[x["module"]]["protected"]}
                rotted["protected" if tuple(x["template_pos"]) in prot else "decorative"] += 1
    total, lanterns, lantern_air, cracked, crackable = Counter(), 0, 0, 0, 0
    for s in SEEDS:
        for p in j(man_dir / f"manifest-{s}-{variant}.json")["cities"][0]["pieces"]:
            m = p["template"].rsplit("/", 1)[-1]
            if m not in MODULES:
                continue
            prot = {tuple(e["pos"]) for e in inv[m]["protected"]}
            r, o = ROT[p["rotation"]], p["pos"]
            for pos, (st, _) in blocks_of(load_nbt(D24F / m / "restored.nbt")).items():
                w = tuple(o[i] + rot(pos, r)[i] for i in range(3))
                if P.name(st) in P.ANCIENT_CITY_REPLACEABLE:
                    total["protected" if pos in prot else "decorative"] += 1
                if P.name(st) == "minecraft:soul_lantern":
                    lanterns += 1
                    lantern_air += P.rule_output(st, w) == "minecraft:air"
                if P.name(st) in ("minecraft:deepslate_bricks", "minecraft:deepslate_tiles") and not P.rot_removed(st, w):
                    crackable += 1
                    cracked += P.rule_output(st, w) is not None
    return {"decorative_rottable_cells": total["decorative"], "decorative_rotted": rotted["decorative"],
            "decorative_rot_rate": round(rotted["decorative"] / total["decorative"], 4),
            "protected_rottable_cells": total["protected"], "protected_rotted_and_left_missing": rotted["protected"],
            "soul_lanterns": lanterns, "soul_lanterns_to_air": lantern_air, "bricks_tiles_placed": crackable, "cracked": cracked}


def survival(path):
    d = j(path)
    st = Counter(r["status"] for r in d)
    by_role = defaultdict(Counter)
    for r in d:
        for role in r["roles"]:
            by_role[role][r["status"]] += 1
    bad = [r for r in d if r["status"] not in ("present", "present_weathered")]
    return {"cells": len(d), "status": dict(st), "by_role": {k: dict(v) for k, v in sorted(by_role.items())}}, bad


def cause_of(r):
    if r["status"] == "REPLACED" and P.name(r["got"] or "") in ("minecraft:tuff", "minecraft:gravel") or "ore" in (r["got"] or ""):
        return "ore/blob feature placed after the piece replaced plain deepslate (block is still solid)"
    if r["void_jigsaw"]:
        return "jigsaw final_state structure_void under the door: cell never written"
    if r["rot_predicted"]:
        return "block_rot (integrity 0.95) dropped the block"
    if "door" in r["roles"]:
        return "door lower half removed after placement: support cell not sturdy"
    return "later feature"


def main():
    inv = j(D24G / "protection/protected-cells.json")
    pl, same_f, same_v = placements()
    ana = j(G_WG / "g24-analysis.json")
    overlaps = [{"seed": c["seed"], "module": m["module"], "overlaps": m["overlapping_pieces"]} for c in ana for m in c["modules"] if m["overlapping_pieces"]]
    surv_f, bad_f = survival(D24G / "investigation/f24-functional-survival.json")
    surv_g, bad_g = survival(G_WG / "g24-functional-survival.json")
    dec_f, dec_g = decay("f24", inv), decay("g24", inv)
    terr_g = j(G_WG / "g24-terrain-classification.json")
    terr_f = j(D24G / "investigation/f24-terrain-classification.json")
    tkey = lambda r: (r["seed"], tuple(r["world"]), r["block"])  # noqa: E731
    terrain_same = sorted(map(tkey, terr_g)) == sorted(map(tkey, terr_f))
    terrain_diff = {"only_stage24g": sorted(set(map(tkey, terr_g)) - set(map(tkey, terr_f))),
                    "only_stage24f": sorted(set(map(tkey, terr_f)) - set(map(tkey, terr_g)))}
    rep_g = j(G_WG / "g24-processor-replay.json")
    unexpl = [x for r in rep_g for x in r["losses"] if x["cause"] != "block_rot"]
    tally = Counter()
    for r in rep_g:
        tally.update(r["tally"])
    issues = []
    for r in bad_g:
        issues.append({"seed": r["seed"], "world": r["world"], "structure": r["module"], "rotation": r["rotation"], "type": "protected_cell_" + r["status"].lower(),
                       "roles": r["roles"], "expected": r["expected"], "got": r["got"], "root_cause": cause_of(r)})
    for x in unexpl:
        issues.append({"seed": x["seed"], "world": x["world"], "structure": x["module"], "rotation": x["rotation"], "type": "unexpected_block_change",
                       "expected": x["expected"], "got": x["got"],
                       "root_cause": "candle state changed after placement" if "candle" in x["expected"] else
                       "ore/blob feature placed after the piece replaced plain deepslate"})
    for t in terr_g:
        issues.append({"seed": t["seed"], "world": t["world"], "structure": t["module"], "rotation": t["rotation"], "type": "terrain_" + t["class"],
                       "block": t["block"], "template_pos": t["template_pos"], "root_cause": t["reason"] + " (template stores no block in this cell)"})
    for c in ana:
        for m in c["modules"]:
            for jg in m["jigsaws"]:
                if not jg["connected"]:
                    issues.append({"seed": c["seed"], "world": jg["jigsaw_world"], "structure": m["module"], "type": "jigsaw_unconnected", "pool": jg["pool"],
                                   "root_cause": "vanilla ancient_city/sculk pool resolved to nothing (same as Stage 24-C/24-F)"})
    nav = [t for t in terr_g if t["class"] == "functional_obstruction"]
    summary = {
        "seeds": list(SEEDS), "cities": len(pl), "pieces": sum(p["pieces"] for p in pl),
        "cities_identical_to_stage24f": same_f, "cities_identical_to_vanilla_except_owner_approved_heights": same_v,
        "protected_list_pieces": sum(p["protected_list_pieces"] for p in pl),
        "bounding_box_overlaps": len(overlaps),
        "functional_survival": {"stage24f": surv_f, "stage24g": surv_g},
        "decorative_decay": {"stage24f": dec_f, "stage24g": dec_g},
        "processor_replay_stage24g": dict(tally), "unexpected_block_changes_stage24g": len(unexpl),
        "terrain_cells_stage24g": dict(Counter(t["class"] for t in terr_g)), "terrain_identical_to_stage24f": terrain_same, "terrain_difference_vs_stage24f": terrain_diff,
        "navigation_obstruction_cells_stage24g": len(nav),
        "placements": pl,
    }
    (G_WG / "g24-summary.json").write_text(json.dumps(summary, indent=1))
    (G_WG / "g24-issues.json").write_text(json.dumps(issues, indent=1))
    terrain_md(terr_g, terr_f, terrain_diff)
    print(json.dumps({k: v for k, v in summary.items() if k != "placements"}, indent=1))


def terrain_md(tg, tf, diff):
    groups = defaultdict(list)
    for t in tg:
        groups[(t["seed"], t["module"], t["rotation"], t["class"], t["block"])].append(t)
    note = {
        (24004, "large_ruin_1"): "One block of an amethyst geode's smooth-basalt shell reaching into the extreme corner of the taller Option C box "
                                 "(template (16,11,16): 5 blocks above the corner eave, no roof or wall block next to it). Does not touch the roof, a room or a path; "
                                 "visible only as part of the cave wall behind the corner.",
        (24005, "medium_ruin_1"): "Dripstone blocks (dripstone-caves features placed before the city) fill the room: the house is buried. Same cells in Stage 24-C/24-F.",
        (24009, "large_ruin_1"): "A dripstone cluster stands in the hall (12 walkable cells) plus 1 block outside; the 24-C sweep had 7 in this piece at another spot.",
        (24008, "small_ruin_1"): "Lava in the room (lava spring/flow after placement); a player entering takes fire damage.",
        (24014, "sauna_1"): "A 5-high lava column inside the box behind the masonry, not touching a walkable cell.",
        (24012, "sauna_1"): "One natural deepslate block in an unstored cell above the roof edge.",
        (24014, "medium_pillar_1"): "Three natural deepslate blocks in unstored cells beside the tower top (outside the walkable deck).",
    }
    out = ["# Stage 24-G — terrain and fluid intersections (24-seed sweep)", "",
           "Stage 24-F vs Stage 24-G: identical cells except "
           + ("; ".join(f"{len(v)} cell(s) {k.replace('_', ' ')}: " + ", ".join(f"seed {a} {b} {c}" for a, b, c in v) for k, v in diff.items() if v) or "none")
           + " — flowing lava spreads by fluid ticks after generation, so one flow cell more or less is timing, not protection. "
             "The protection overlay writes no cell that terrain occupies (it only re-writes blocks the template itself stores).",
           "",
           "Classes: functional obstruction (blocks a walkable/door cell), cosmetic intrusion, existing vanilla/environmental behaviour "
           "(cell the vanilla template also leaves unstored, natural terrain), potential generation hazard (fluid). Rule: "
           "`tools/stage24g/terrain.py`. No terrain is removed in Stage 24-G; see `OWNER-DECISION-interior-terrain.md`.", "",
           "| seed | structure | rotation | class | block | cells | world coordinates (first 3) | assessment |", "|---|---|---|---|---|---|---|---|"]
    for (seed, m, r, cls, b), rows in sorted(groups.items()):
        ws = "; ".join(str(tuple(x["world"])) for x in rows[:3])
        out.append(f"| {seed} | {m} | {r} | {cls.replace('_', ' ')} | {b} | {len(rows)} | {ws} | {note.get((seed, m), '')} |")
    out += ["", "Full cell list: `worldgen/g24-terrain-classification.json` (Stage 24-F: `investigation/f24-terrain-classification.json`)."]
    (D24G / "TERRAIN-CLASSIFICATION.md").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
