#!/usr/bin/env python3
"""N7-A3 benchmark summary. Reads the runs of one benchmark directory (names CONFIG_SEED_CX_CZ_ORDER_rREP), drops warm-up repeat r0,
and reports per configuration: generation window, feature and decision latency percentiles, allocation, GC/CPU, guard attempts, cancellations
and region reads. Percentiles are per run; across runs the median and min..max are reported (raw samples are not pooled).
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def runs(root: Path):
    for d in sorted(root.iterdir()):
        f = d / "lab.json"
        if not f.exists() or d.name.count("_") < 5:
            continue
        parts = d.name.split("_")
        cfg, rep = parts[0], parts[-1]
        yield cfg, rep, d.name, json.loads(f.read_text())


def med(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {"median": round(statistics.median(xs), 3), "min": round(min(xs), 3), "max": round(max(xs), 3), "n": len(xs)}


def pct_of(perf: dict, key: str, phase: str, p: str):
    try:
        v = perf[key][phase][p]
        return v
    except (KeyError, TypeError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    by = defaultdict(list)
    for cfg, rep, name, n in runs(a.root):
        if rep == "r0":
            continue
        by[cfg].append((name, n))
    summary = {}
    for cfg in ["V", "A", "B", "C", "H", "HS"]:
        rows = by.get(cfg, [])
        if not rows:
            continue
        gen = [n.get("gen_window_s") for _, n in rows]
        entry = {"runs": len(rows), "gen_window_s": med(gen), "elapsed_s": med([n.get("elapsed_s") for _, n in rows])}
        perfs = [n["spike_report"]["perf"] for _, n in rows if n.get("spike_report") and n["spike_report"].get("perf")]
        if perfs:
            for key in ("monster_decision_ns", "monster_place_ns", "monster_vanilla_ns", "geode_decision_ns", "geode_place_ns", "geode_vanilla_ns"):
                entry[key] = {}
                for phase in ("all", "cold", "steady"):
                    entry[key][phase] = {p: med([pct_of(pf, key, phase, p) for pf in perfs]) for p in ("p50", "p95", "p99", "mean")}
            entry["monster_decision_bytes"] = {"all_mean": med([pct_of(pf, "monster_decision_bytes", "all", "mean") for pf in perfs])}
            entry["gc_count"] = med([pf["gc_count"] for pf in perfs])
            entry["gc_ms"] = med([pf["gc_ms"] for pf in perfs])
            entry["process_cpu_ms"] = med([pf["process_cpu_ms"] for pf in perfs])
            entry["heap_used_bytes"] = med([pf["heap_used_bytes"] for pf in perfs])
            sr = [n["spike_report"] for _, n in rows if n.get("spike_report")]
            entry["monster_attempts"] = med([s["monster_room"]["attempts"] for s in sr])
            entry["monster_cancelled"] = med([s["monster_room"]["cancelled"] for s in sr])
            entry["geode_attempts"] = med([s["geode"]["attempts"] for s in sr])
            entry["geode_cancelled"] = med([s["geode"]["cancelled"] for s in sr])
            entry["hybrid_skip"] = med([s["monster_room"].get("hybrid_skip", 0) for s in sr])
            entry["region_reads"] = med([s["probe"]["region_get_calls"] for s in sr])
            entry["scheduling_requests"] = sum(s["probe"]["chunkmap_schedule"] + s["probe"]["holder_schedule"] + s["probe"]["server_get_blocking"] +
                                               s["probe"]["server_get_future"] for s in sr)
            entry["region_reads_status_below_or_null"] = sum(s["probe"]["region_get_status_below"] + s["probe"]["region_get_null"] for s in sr)
        summary[cfg] = entry
    a.out.write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: {"runs": v["runs"], "gen_window_s": v["gen_window_s"]} for k, v in summary.items()}, indent=1))


if __name__ == "__main__":
    main()
