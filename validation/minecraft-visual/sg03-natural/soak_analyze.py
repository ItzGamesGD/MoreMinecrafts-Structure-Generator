#!/usr/bin/env python3
"""N7-A4 soak analysis. usage: soak_analyze.py OUT.json RUN_DIR [RUN_DIR ...]   (RUN_DIR holds samples.jsonl and soak.json from soak.py)
Per run: ordinary-least-squares slope (with a 95% confidence interval from the residual standard error) of heap-after-GC and non-heap memory over
the samples after the first 20% (warm-up), first-third vs last-third means, GC time fraction, allocation rate, peak loaded chunks, and the guard's
retained-state counters. A slope whose interval includes zero is reported as 'no detectable trend', not as 'stable'."""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from pathlib import Path


def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    s2 = sum(r * r for r in resid) / max(1, n - 2)
    se = math.sqrt(s2 / sxx)
    # 1.96 is a normal approximation; n is >100 samples in every run here (successive samples are autocorrelated, so the interval is optimistic)
    return slope, 1.96 * se


def analyse(run: Path) -> dict:
    rows = [json.loads(line) for line in (run / "samples.jsonl").read_text().splitlines() if line.strip()]
    meta = json.loads((run / "soak.json").read_text())
    t = [r["uptime_ms"] / 60000.0 for r in rows]  # minutes
    warm = int(len(rows) * 0.2)
    use = [r for r in rows[warm:] if r["heap_after_gc"] > 0]
    tm = [r["uptime_ms"] / 60000.0 for r in use]
    out = {"run": run.name, "mode": meta["mode"], "samples": len(rows), "duration_min": round(t[-1], 2), "sites": len(meta["sites"])}
    for key, label in (("heap_after_gc", "heap_after_gc_MB_per_min"), ("non_heap_used", "non_heap_MB_per_min")):
        ys = [r[key] / 1048576 for r in use]
        slope, ci = ols(tm, ys)
        out[label] = {"slope": round(slope, 3), "ci95": round(ci, 3), "includes_zero": abs(slope) <= ci, "n": len(ys)}
    third = max(1, len(use) // 3)
    out["heap_after_gc_MB_first_third_mean"] = round(st.mean(r["heap_after_gc"] for r in use[:third]) / 1048576, 1)
    out["heap_after_gc_MB_last_third_mean"] = round(st.mean(r["heap_after_gc"] for r in use[-third:]) / 1048576, 1)
    out["heap_after_gc_MB_max"] = round(max(r["heap_after_gc"] for r in use) / 1048576, 1)
    last, first = rows[-1], rows[0]
    out["gc_count"] = last["gc_count"]
    out["gc_time_fraction"] = round(last["gc_ms"] / max(1, last["uptime_ms"]), 4)
    out["max_last_gc_pause_ms"] = max(r["last_gc_pause_ms"] for r in rows)
    out["allocation_MB_per_s"] = round((last["allocated_bytes"] - first["allocated_bytes"]) / 1048576 / max(1, (last["uptime_ms"] - first["uptime_ms"]) / 1000), 2)
    out["loaded_chunks_max"] = max(r["loaded_chunks"] for r in rows)
    out["loaded_chunks_final"] = last["loaded_chunks"]
    out["guard_attempts_final"] = last["guard_attempts"]
    out["guard_events_retained_final"] = last["guard_events_retained"]
    out["perf_samples_retained_final"] = last["perf_samples_retained"]
    out["perf_samples_retained_max"] = max(r["perf_samples_retained"] for r in rows)
    return out


def main() -> None:
    out = Path(sys.argv[1])
    runs = [analyse(Path(p)) for p in sys.argv[2:]]
    out.write_text(json.dumps(runs, indent=1) + "\n")
    for r in runs:
        h = r["heap_after_gc_MB_per_min"]
        print(f"{r['run']:18} {r['mode']:8} {r['duration_min']:6.1f} min  heap-after-GC slope {h['slope']:+.2f}±{h['ci95']:.2f} MB/min "
              f"({'no detectable trend' if h['includes_zero'] else 'TREND'})  first/last third {r['heap_after_gc_MB_first_third_mean']}/{r['heap_after_gc_MB_last_third_mean']} MB  "
              f"gc {r['gc_time_fraction']:.3f}  alloc {r['allocation_MB_per_s']} MB/s  chunks max {r['loaded_chunks_max']}")


if __name__ == "__main__":
    main()
