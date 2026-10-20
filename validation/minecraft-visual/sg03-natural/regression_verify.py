#!/usr/bin/env python3
"""N7-A4 strict regression verifier. usage: regression_verify.py OUT.json RESULTS_DIR   (RESULTS_DIR holds one lab.json directory per run; names CONFIG_SEED_CX_CZ_ORDER_rREP)
Per run it asserts (all must hold):
  mismatch == 0                      no protected block differs from the template
  foreign blocks in template air == 0
  pieces == the site's reference count (21)
  trial spawner block count == entity count == the site's reference
  start signature (pool elements, rotations, boxes) == the site's reference
  scheduling requests == 0, unavailable reads == 0
  every cancellation is a 'collision' decision whose reach box intersects the protected piece it names (no unavailable-data cancellations,
  no cancellation without a protected piece in reach): unexpected vanilla feature suppression would show here.
The site reference is the first run of that site in the directory (all runs of a site must agree with it)."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BOX = re.compile(r"BoundingBox\{minX=(-?\d+), minY=(-?\d+), minZ=(-?\d+), maxX=(-?\d+), maxY=(-?\d+), maxZ=(-?\d+)\}")


def inter(a, b) -> bool:
    return a[0] <= b[3] and a[3] >= b[0] and a[1] <= b[4] and a[4] >= b[1] and a[2] <= b[5] and a[5] >= b[2]


def check_events(sr: dict) -> list[str]:
    problems = []
    for key in ("geode", "monster_room"):
        for ev in (sr.get(key) or {}).get("events", []):
            if "CANCELLED" not in ev:
                continue
            if "-> collision" not in ev:
                problems.append(f"{key}: cancellation that is not a collision: {ev[:140]}")
                continue
            reaches = [tuple(int(v) for v in m) for m in BOX.findall(ev.split("reaches=", 1)[1].split(" -> ", 1)[0])]
            piece = BOX.findall(ev.split("-> collision", 1)[1])
            if not reaches or not piece:
                problems.append(f"{key}: cannot parse boxes: {ev[:140]}")
                continue
            pb = tuple(int(v) for v in piece[0])
            if not any(inter(r, pb) for r in reaches):
                problems.append(f"{key}: named piece does not intersect any reach: {ev[:140]}")
    return problems


def main() -> None:
    out, root = Path(sys.argv[1]), Path(sys.argv[2])
    ref: dict = {}
    rows = []
    for f in sorted(root.glob("*/lab.json")):
        n = json.loads(f.read_text())
        a = n.get("before_ticks") or {}
        sr = n.get("spike_report") or {}
        site = f"{n['seed']}_{n['chunk'][0]}_{n['chunk'][1]}"
        ref.setdefault(site, {"pieces": a.get("pieces"), "spawners": a.get("trial_spawners"), "sig": n.get("start_signature")})
        r = ref[site]
        p = sr.get("probe") or {}
        problems = []
        if not n.get("generated"):
            problems.append("structure not generated")
        if (a.get("expected", 0) - a.get("matched", 0)) != 0:
            problems.append(f"mismatch {a.get('expected', 0) - a.get('matched', 0)}")
        if sum((a.get("interior_intrusions") or {}).values()):
            problems.append("foreign blocks in template air")
        if a.get("pieces") != r["pieces"] or a.get("pieces") != 21:
            problems.append(f"pieces {a.get('pieces')}")
        sp = a.get("trial_spawners")
        if sp != r["spawners"] or not sp or sp[0] != sp[1]:
            problems.append(f"trial spawners {sp} vs reference {r['spawners']}")
        if n.get("start_signature") != r["sig"]:
            problems.append("start signature differs")
        sched = sum(p.get(k, 0) for k in ("chunkmap_schedule", "holder_schedule", "server_get_blocking", "server_get_future"))
        if sched:
            problems.append(f"scheduling requests {sched}")
        if p.get("region_get_status_below", 0) or p.get("region_get_null", 0):
            problems.append("region read below requested status or null")
        unav = sum((sr.get(k) or {}).get("unavailable", 0) for k in ("geode", "monster_room"))
        if unav:
            problems.append(f"unavailable reads {unav}")
        problems += check_events(sr)
        rows.append({"run": f.parent.name, "site": site, "ok": not problems, "problems": problems,
                     "geode_cancelled": (sr.get("geode") or {}).get("cancelled"), "monster_cancelled": (sr.get("monster_room") or {}).get("cancelled")})
    by_site = defaultdict(lambda: [0, 0])
    for r in rows:
        by_site[r["site"]][0] += 1
        by_site[r["site"]][1] += int(r["ok"])
    out.write_text(json.dumps({"runs": len(rows), "passed": sum(r["ok"] for r in rows), "by_site": dict(by_site), "failures": [r for r in rows if not r["ok"]]}, indent=1) + "\n")
    print(f"{sum(r['ok'] for r in rows)}/{len(rows)} runs pass all assertions; by site {dict(by_site)}")
    for r in rows:
        if not r["ok"]:
            print("FAIL", r["run"], r["problems"][:3])


if __name__ == "__main__":
    main()
