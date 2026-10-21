#!/usr/bin/env python3
"""N8-A attribution helper: samples a plain vanilla server JVM from the outside (no module, no lab code in it). usage: ext_sampler.py OUT.jsonl JAR_PATH [SECONDS_PERIOD]
Writes one JSON line per period: uptime, RSS (kB, /proc/<pid>/status) and, from jstat -gc, young/old/metaspace usage (kB). It exits when the JVM ends."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

out, jar = Path(sys.argv[1]), sys.argv[2]
period = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
pid = None
while pid is None:
    ps = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout.splitlines()
    for line in ps:
        if jar in line and "-jar" in line and "ext_sampler" not in line and "soak.py" not in line:
            pid = int(line.split()[0])
            break
    time.sleep(1)
t0 = time.time()
while Path(f"/proc/{pid}").exists():
    try:
        rss = int([l for l in Path(f"/proc/{pid}/status").read_text().splitlines() if l.startswith("VmRSS:")][0].split()[1])
        js = subprocess.run(["jstat", "-gc", str(pid)], capture_output=True, text=True).stdout.splitlines()
        cols, vals = js[0].split(), js[1].split()
        g = dict(zip(cols, vals))
        row = {"uptime_s": round(time.time() - t0, 1), "rss_kb": rss, "eden_used_kb": float(g.get("EU", 0)), "old_used_kb": float(g.get("OU", 0)), "meta_used_kb": float(g.get("MU", 0)), "gc_count": float(g.get("YGC", 0)) + float(g.get("FGC", 0))}
        with out.open("a") as f:
            f.write(json.dumps(row) + "\n")
    except (OSError, IndexError, ValueError):
        pass
    time.sleep(period)
