#!/usr/bin/env python3
"""N8-A evaluation exactly as fixed in docs/sg-03/n8-acceptance-criteria.md. usage: n8_soak_eval.py OUT.json --guarded RUN_DIR [RUN_DIR ...] --control RUN_DIR [...]
Each RUN_DIR holds samples.jsonl, soak.json and server.log from soak.py. Slopes are ordinary least squares over the samples after the first 10 minutes;
the 95% interval is the normal approximation (samples are autocorrelated, so intervals are optimistic)."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from soak_analyze import ols  # noqa: E402

WARM_MS = 10 * 60 * 1000


def load(run: Path) -> dict:
    rows = [json.loads(line) for line in (run / "samples.jsonl").read_text().splitlines() if line.strip()]
    steady = [r for r in rows if r["uptime_ms"] >= WARM_MS and r["heap_after_gc"] > 0]
    t = [r["uptime_ms"] / 60000 for r in steady]

    def slope(key, scale=1048576):
        s, c = ols(t, [r[key] / scale for r in steady])
        return {"slope_per_min": round(s, 3), "ci95": round(c, 3), "includes_zero": abs(s) <= c}

    last, first = rows[-1], steady[0]
    windows = {}
    for r in rows:
        windows.setdefault(r["uptime_ms"] // 300000, []).append(r["chunks_decorated"])
    active = [w for w in sorted(windows)[:-1] if max(windows[w]) > min(windows[w])]  # the last (partial) window is not counted
    log = (run / "server.log").read_text(errors="replace")
    return {
        "run": run.name, "samples": len(rows), "duration_min": round(last["uptime_ms"] / 60000, 1), "chunks_decorated": last["chunks_decorated"],
        "windows_5min": len(windows) - 1, "windows_with_generation": len(active),
        "heap_after_gc_MB": slope("heap_after_gc"), "rss_MB": slope("rss_kb", 1024), "non_heap_MB": slope("non_heap_used"),
        "heap_after_gc_max_fraction_of_max": round(max(r["heap_after_gc"] / r["heap_max"] for r in rows), 3),
        "guard_events_retained_max": max(r["guard_events_retained"] for r in rows),
        "guard_events_retained_last_third_growth": rows[-1]["guard_events_retained"] - rows[2 * len(rows) // 3]["guard_events_retained"],
        "gc_time_fraction": round(last["gc_ms"] / last["uptime_ms"], 4), "max_gc_pause_ms": max(r["last_gc_pause_ms"] for r in rows),
        "cpu_ms_per_decorated_chunk": round(last["process_cpu_ms"] / max(1, last["chunks_decorated"]), 1),
        "cant_keep_up_messages": len(re.findall(r"Can't keep up", log)), "oom": "OutOfMemoryError" in log, "crash": "Exception in thread" in log and "main" in log.split("Exception in thread")[-1][:30],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--guarded", type=Path, nargs="+", required=True)
    ap.add_argument("--control", type=Path, nargs="+", required=True)
    a = ap.parse_args()
    g = [load(r) for r in a.guarded]
    c = [load(r) for r in a.control]
    ctl = c[0]
    verdicts = []
    for gr in g:
        v = {"run": gr["run"]}
        v["A1_activity"] = gr["windows_with_generation"] >= math.ceil(0.95 * gr["windows_5min"]) and ctl["windows_with_generation"] >= math.ceil(0.95 * ctl["windows_5min"])
        h = gr["heap_after_gc_MB"]
        diff = h["slope_per_min"] - ctl["heap_after_gc_MB"]["slope_per_min"]
        v["A2_heap"] = (h["slope_per_min"] <= 2 or h["includes_zero"]) and diff < 3 and gr["heap_after_gc_max_fraction_of_max"] < 0.8
        v["A2_detail"] = {"guarded_slope": h, "control_slope": ctl["heap_after_gc_MB"], "difference": round(diff, 3)}
        v["A3_retained"] = gr["guard_events_retained_max"] <= 800 and gr["guard_events_retained_last_third_growth"] <= 0
        v["A4_gc"] = gr["gc_time_fraction"] <= ctl["gc_time_fraction"] + 0.005 and gr["max_gc_pause_ms"] <= 200
        rdiff = gr["rss_MB"]["slope_per_min"] - ctl["rss_MB"]["slope_per_min"]
        v["A5_rss_cpu"] = rdiff < 5 and gr["cpu_ms_per_decorated_chunk"] <= 1.25 * ctl["cpu_ms_per_decorated_chunk"]
        v["A5_detail"] = {"rss_slope_difference": round(rdiff, 3), "cpu_ratio": round(gr["cpu_ms_per_decorated_chunk"] / ctl["cpu_ms_per_decorated_chunk"], 3)}
        v["A6_stability"] = not gr["oom"] and not gr["crash"] and gr["cant_keep_up_messages"] <= ctl["cant_keep_up_messages"] * 1.1 + 10
        v["repeat_required"] = (not h["includes_zero"]) and h["slope_per_min"] > 0
        verdicts.append(v)
    a.out.write_text(json.dumps({"guarded": g, "control": c, "verdicts": verdicts}, indent=1) + "\n")
    for v in verdicts:
        print(v["run"], {k: v[k] for k in v if k.startswith("A") and not k.endswith("detail")}, "repeat_required", v["repeat_required"])
    for r in g + c:
        print(r["run"], "dur", r["duration_min"], "min decorated", r["chunks_decorated"], "heap", r["heap_after_gc_MB"], "rss", r["rss_MB"], "gc", r["gc_time_fraction"], "cpu/chunk", r["cpu_ms_per_decorated_chunk"], "cku", r["cant_keep_up_messages"])


if __name__ == "__main__":
    main()
