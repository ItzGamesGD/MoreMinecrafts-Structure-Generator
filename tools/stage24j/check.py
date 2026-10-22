"""Static feasibility checks for the Stage 24-J watchtower alternatives (no approved NBT is written).

Per candidate (and the approved tower as the baseline):
  * template size unchanged (=> identical piece box, jigsaw placement and collision behaviour);
  * every jigsaw and block entity identical (position, state, NBT), incl. the medium-pillar skeleton skull;
  * ladder continuity: one unbroken ladder column from y1 to the hatch, every rung backed by a solid block;
  * deck: standable cells at the deck level, all reachable from the ladder exit; two-block headroom per cell, with the
    cells that lie above the template reported (they depend on the world above the box);
  * fall protection: every deck-cell side is deck, the ladder hatch, a wall/railing (1.5-block collision, cannot be
    jumped) or a full block; an open side over a drop is a failure; full-block sides are listed (they can be climbed);
  * every block state names a vanilla 26.1.2 block with known property values (omitted properties take the game default)
    per the block report (`--reports`, generated from the pinned server jar);
  * which Stage 24-G protected cells, Stage 24-H mask cells and Stage 24-I roof cells a variant touches (an approved
    variant would need those derived inventories rebuilt), and how many decay-eligible blocks it adds or removes.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import blocks_of, load_nbt  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24j.designs import DESIGNS, D24F  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24G = ROOT / "artifacts/ancient-city-restoration/stage-24g"
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"
D24J = ROOT / "artifacts/ancient-city-restoration/stage-24j"
PASSABLE = ("air", "cave_air", "ladder", "soul_lantern")
FACING_BACK = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}   # ladder facing -> wall direction
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def bid(s):
    return s.split("[")[0].replace("minecraft:", "")


def props(s):
    return dict(kv.split("=") for kv in s.split("[", 1)[1].rstrip("]").split(",")) if "[" in s else {}


class G:
    def __init__(self, path):
        r = load_nbt(path)
        self.size = [int(v) for v in r["size"]]
        self.raw = blocks_of(r)
        self.b = {p: s for p, (s, _) in self.raw.items()}

    def at(self, p):
        return self.b.get(tuple(p), "minecraft:air")

    def inside(self, p):
        return all(0 <= p[i] < self.size[i] for i in range(3))

    def passable(self, p):
        n = bid(self.at(p))
        return n in PASSABLE

    def floor(self, p):
        n = bid(self.at(p))
        return not (n in PASSABLE or n.endswith("_wall") or n == "water")

    def standable(self, p):
        x, y, z = p
        return self.floor((x, y - 1, z)) and self.passable(p) and self.passable((x, y + 1, z))


def check(v, path, base: G, reports, inv, masks, roofs):
    g = G(path)
    m = v.module
    r = {"variant": v.variant, "title": v.title, "dimensions": g.size, "approved_dimensions": base.size}
    r["size_unchanged"] = g.size == base.size
    ents = lambda gg: {p: (s, str(n)) for p, (s, n) in gg.raw.items() if n is not None}  # noqa: E731
    r["jigsaws_and_block_entities_identical"] = ents(g) == ents(base)
    r["block_entities"] = sorted(f"{list(p)} {bid(s)}" for p, (s, _) in ents(g).items())
    # ladder
    lx, lz = v.meta["ladder"]
    top = v.meta["ladder_top"]
    rungs = [g.at((lx, y, lz)) for y in range(1, top + 1)]
    backed = all(bid(s) == "ladder" and g.floor((lx + FACING_BACK[props(s)["facing"]][0], y, lz + FACING_BACK[props(s)["facing"]][1]))
                 for y, s in zip(range(1, top + 1), rungs))
    r["ladder"] = {"column": [lx, lz], "rungs": f"y1..y{top}", "continuous_and_backed": backed,
                   "above_hatch_clear": g.passable((lx, top + 1, lz))}
    # deck reachability from the ladder exit
    dy = v.meta["deck_y"]
    stand = {(x, z) for x in range(-1, g.size[0] + 1) for z in range(-1, g.size[2] + 1) if g.standable((x, dy, z))}
    start = [(lx + dx, lz + dz) for dx, dz in DIRS if (lx + dx, lz + dz) in stand]
    seen, q = set(start), deque(start)
    while q:
        x, z = q.popleft()
        for dx, dz in DIRS:
            n = (x + dx, z + dz)
            if n in stand and n not in seen:
                seen.add(n)
                q.append(n)
    deck = set(v.meta["deck"])
    r["deck"] = {"feet_y": dy, "standable_cells": len(stand), "reachable_from_ladder": len(seen), "expected": len(deck),
                 "all_expected_reachable": deck <= seen, "unexpected_reachable": sorted(seen - deck)}
    above = sorted({(x, z) for x, z in seen if not g.inside((x, dy + 1, z)) or not g.inside((x, dy, z))})
    r["deck"]["headroom_cells_above_template"] = len(above)
    # fall protection
    sides = Counter()
    open_edges, climbable = [], []
    for x, z in sorted(seen):
        for dx, dz in DIRS:
            n = (x + dx, z + dz)
            if n in seen:
                continue
            body = (n[0], dy, n[1])
            nm = bid(g.at(body))
            if n == (lx, lz):
                sides["ladder_hatch"] += 1
            elif nm.endswith(("_wall", "_fence")):
                sides["railing_wall"] += 1
            elif not g.passable(body):
                sides["full_block"] += 1
                if g.passable((n[0], dy + 1, n[1])) and g.passable((n[0], dy + 2, n[1])):
                    climbable.append([x, z, n[0], n[1]])
            elif g.floor((n[0], dy - 1, n[1])):
                sides["open_to_non_deck_floor"] += 1
            else:
                sides["OPEN_DROP"] += 1
                open_edges.append([x, z, n[0], n[1]])
    r["fall_protection"] = {"sides": dict(sides), "open_drops": open_edges, "climbable_full_block_sides": climbable}
    # valid states
    bad = []
    for p, s in g.b.items():
        rep = reports.get("minecraft:" + bid(s))
        if rep is None:
            bad.append([list(p), s, "unknown block"])
            continue
        pr = props(s)
        allowed = rep.get("properties", {})
        if not set(pr) <= set(allowed) or any(pr[k] not in allowed[k] for k in pr):   # omitted properties take the default
            bad.append([list(p), s, "properties"])
    r["invalid_states"] = bad
    # impact on derived inventories
    changed = {p for p in set(g.b) | set(base.b) if g.at(p) != base.at(p)}
    prot = {tuple(e["pos"]): e["roles"] for e in inv[m]["protected"]}
    r["changed_cells"] = len(changed)
    r["stage24g_protected_cells_changed"] = sorted(f"{list(p)} {','.join(prot[p])} {bid(base.at(p))}->{bid(g.at(p))}" for p in changed if p in prot)
    r["stage24h_mask_cells_changed"] = sum(1 for p in changed if p in masks[m])
    r["stage24i_roof_cells_changed"] = sum(1 for p in changed if p in roofs[m])
    rot = lambda gg: sum(1 for s in gg.b.values() if P.name(s) in P.ANCIENT_CITY_REPLACEABLE)  # noqa: E731
    r["decay_eligible_blocks"] = {"approved": rot(base), "variant": rot(g)}
    r["block_mix_changed"] = dict(Counter(bid(g.at(p)) for p in changed).most_common(10))
    keys = [r["size_unchanged"], r["jigsaws_and_block_entities_identical"], backed, r["ladder"]["above_hatch_clear"],
            r["deck"]["all_expected_reachable"], not open_edges, not bad]
    r["static_pass"] = all(keys)
    return r


def main(reports_path):
    reports = json.loads(Path(reports_path).read_text())
    inv = json.loads((D24G / "protection/protected-cells.json").read_text())
    masks = {m: {tuple(p) for vv in d["cleared"].values() for p in vv} for m, d in json.loads((D24H / "mask/interior-masks.json").read_text()).items()}
    roofs = {m: {tuple(e["pos"]) for e in d["roof_cells"]} for m, d in json.loads((D24I / "roof/roof-cells.json").read_text()).items()}
    out = {}
    for m, fs in DESIGNS.items():
        base = G(D24F / m / "restored.nbt")
        out[m] = {}
        for f in fs:
            v = f()
            path = D24F / m / "restored.nbt" if v.variant == "current" else D24J / "proposals" / m / v.variant / "candidate.nbt"
            r = check(v, path, base, reports, inv, masks, roofs)
            r["notes"] = v.notes
            out[m][v.variant] = r
            print(m, v.variant, "PASS" if r["static_pass"] else "FAIL", r["deck"], r["fall_protection"]["sides"], "invalid", len(r["invalid_states"]),
                  "24G", len(r["stage24g_protected_cells_changed"]), flush=True)
    (D24J / "static-checks.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default="/tmp/mc/reports/out/reports/blocks.json", help="vanilla blocks.json (server jar --reports)")
    a = ap.parse_args()
    main(a.reports)
