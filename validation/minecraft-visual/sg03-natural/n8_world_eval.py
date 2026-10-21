#!/usr/bin/env python3
"""N8-B evaluation exactly as fixed in docs/sg-03/n8-acceptance-criteria.md. usage: n8_world_eval.py OUT.json --guarded AUDIT.json --control AUDIT.json --vanilla AUDIT.json [AUDIT.json ...] [--first N]
B1: guarded arm, all sites: zero mismatch, 21 pieces, trial spawner blocks == entities, no inspect errors, every site has a structure start.
B2: over the first N sites (the vanilla replicates cover only those): per feature category the guarded total must lie within [min, max] of the vanilla replicates widened by 10%."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CATS = ["smooth_basalt", "calcite", "amethyst_block", "budding_amethyst", "mossy_cobblestone", "spawner"]


def totals(audit: dict, first: int) -> dict:
    out = {c: 0 for c in CATS}
    chunks = 0
    for row in audit["sites"][:first]:
        for c in CATS:
            out[c] += row.get("ring", {}).get(c, 0)
        chunks += row.get("ring_full_chunks", 0)
    out["ring_full_chunks"] = chunks
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--guarded", type=Path, required=True)
    ap.add_argument("--control", type=Path, required=True)
    ap.add_argument("--vanilla", type=Path, nargs="+", required=True)
    ap.add_argument("--first", type=int, default=24)
    a = ap.parse_args()
    g, c = json.loads(a.guarded.read_text()), json.loads(a.control.read_text())
    v = [json.loads(p.read_text()) for p in a.vanilla]
    t = g["totals"]
    b1 = {"sites": t.get("sites", 0), "sites_without_start": t.get("sites_without_start", 0), "mismatch_blocks": t.get("mismatch", 0), "sites_with_mismatch": t.get("sites_with_mismatch", 0),
          "bad_piece_count": t.get("bad_piece_count", 0), "trial_spawner_mismatch": t.get("trial_spawner_mismatch", 0), "errors": t.get("errors", 0)}
    b1["pass"] = b1["sites"] > 0 and b1["sites_without_start"] == 0 and all(b1[k] == 0 for k in ("mismatch_blocks", "sites_with_mismatch", "bad_piece_count", "trial_spawner_mismatch", "errors"))
    control_damage = {"sites": c["totals"].get("sites", 0), "sites_with_mismatch": c["totals"].get("sites_with_mismatch", 0), "mismatch_blocks": c["totals"].get("mismatch", 0)}
    gt, ct, vt = totals(g, a.first), totals(c, a.first), [totals(x, a.first) for x in v]
    b2 = {}
    for cat in CATS:
        lo, hi = min(x[cat] for x in vt), max(x[cat] for x in vt)
        wlo, whi = lo * 0.9, hi * 1.1
        b2[cat] = {"guarded": gt[cat], "control": ct[cat], "vanilla": [x[cat] for x in vt], "accepted_range": [round(wlo), round(whi)], "guarded_in_range": wlo <= gt[cat] <= whi,
                   "control_in_range": wlo <= ct[cat] <= whi, "guarded_vs_vanilla_mean": round(gt[cat] / (sum(x[cat] for x in vt) / len(vt)), 3) if sum(x[cat] for x in vt) else None}
    res = {"B1": b1, "control_damage_for_reference": control_damage, "B2_first_sites": a.first, "B2": b2, "B2_pass": all(x["guarded_in_range"] for x in b2.values()),
           "ring_full_chunks": {"guarded": gt["ring_full_chunks"], "control": ct["ring_full_chunks"], "vanilla": [x["ring_full_chunks"] for x in vt]}}
    a.out.write_text(json.dumps(res, indent=1) + "\n")
    print("B1", b1, "| control damage", control_damage)
    for cat, x in b2.items():
        print(f"B2 {cat:18} guarded={x['guarded']:>7} control={x['control']:>7} vanilla={x['vanilla']} range={x['accepted_range']} -> {'ok' if x['guarded_in_range'] else 'OUT'}")
    print("B2_pass", res["B2_pass"])


if __name__ == "__main__":
    main()
