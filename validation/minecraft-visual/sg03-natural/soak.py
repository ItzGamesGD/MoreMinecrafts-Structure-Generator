#!/usr/bin/env python3
"""N7-A4 multi-site single-JVM soak. One Fabric server (module loaded, manifest mode) cycles through many SG candidate sites: load the 11x11
chunk area around a site, let it settle, release it (forceload remove all), repeat. The module's JVM sampler (SG01_SAMPLE_FILE) records the
trend. MODE guarded = enforce both hooks with the hybrid guard; MODE control = same module and sampler, guard decisions disabled
(SG01_FEATURES=none). Environment: SG_PACK (a pack that already contains the test manifest), JAVA_HOME.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_natural import wait_loaded  # noqa: E402
from spread import SG01, candidates_in_ring, exclusion_suppressed  # noqa: E402
from world import Server  # noqa: E402

SPIKE = HERE.parents[2] / "validation" / "fabric-protection-spike"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--mode", choices=["guarded", "control"], required=True)
    p.add_argument("--seed", type=int, default=173)
    p.add_argument("--sites", type=int, default=36)
    p.add_argument("--radius", type=int, default=5)
    p.add_argument("--settle", type=float, default=4.0)
    p.add_argument("--idle", type=float, default=90.0, help="seconds of idle sampling after the last site")
    p.add_argument("--port", type=int, default=41010)
    p.add_argument("--wait", type=float, default=120.0, help="seconds to wait for a site to load before diagnosing a stall")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    sites = sorted((c for c in candidates_in_ring(a.seed, SG01, 6) if not exclusion_suppressed(a.seed, c)), key=lambda c: (c[0] ** 2 + c[1] ** 2, c))[:a.sites]
    samples = (a.out / "samples.jsonl").resolve()
    report = (a.out / "spike-report.json").resolve()
    for f in (samples, report):
        f.unlink(missing_ok=True)
    run_dir = (SPIKE / "run" / "server").resolve()
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    env = {"SG01_PROTECTION": "manifest", "SG01_GUARD_MODE": "enforce", "SG01_REFINE": "hybrid", "SG01_SAMPLE_FILE": str(samples), "SG01_SAMPLE_MS": "5000",
           "SG01_SPIKE_REPORT": str(report), "SG01_FEATURES": "both" if a.mode == "guarded" else "none"}
    srv = Server("java", None, run_dir, a.seed, Path(os.environ["SG_PACK"]), port=a.port, launcher=["./gradlew", "--no-daemon", "runServer"],
                 launcher_cwd=SPIKE, start_timeout=600, env=env)
    steps = []
    t0 = time.time()
    try:
        for i, (cx, cz) in enumerate(sites):
            r = a.radius
            reply = srv.cmd(f"forceload add {(cx - r) * 16} {(cz - r) * 16} {(cx + r) * 16} {(cz + r) * 16}")
            if "Marked" not in reply and "chunk" not in reply.lower():
                print(f"step {i + 1}: unexpected forceload reply: {reply!r}", flush=True)
            try:
                wait_loaded(srv, (cx + r) * 16, (cz + r) * 16, seconds=a.wait)
            except RuntimeError:
                # Diagnose before giving up: command replies and a thread dump of the server JVM.
                diag = {"step": i + 1, "site": [cx, cz], "forceload_reply": reply, "forceload_list": srv.cmd("forceload query"),
                        "loaded_check": srv.cmd(f"execute if loaded {(cx + r) * 16} 0 {(cz + r) * 16}")}
                (a.out / "stall.json").write_text(json.dumps(diag, indent=1) + "\n")
                import subprocess
                jpid = subprocess.run(["bash", "-c", "ps -eo pid,args | awk '/fabric\\.dli/ {print $1; exit}'"], capture_output=True, text=True).stdout.strip()
                if jpid:
                    (a.out / "threads.txt").write_text(subprocess.run(["jcmd", jpid, "Thread.print"], capture_output=True, text=True).stdout)
                shutil.copy2(run_dir / "server.log", a.out / "server.log")
                raise
            time.sleep(a.settle)
            srv.cmd("forceload remove all")
            if i % 8 == 7:
                srv.save()
            time.sleep(a.settle)
            steps.append({"step": i, "site": [cx, cz], "t_s": round(time.time() - t0, 1)})
            print(f"step {i + 1}/{len(sites)} site=({cx},{cz}) t={time.time() - t0:.0f}s", flush=True)
        time.sleep(a.idle)
    finally:
        srv.stop()
    (a.out / "soak.json").write_text(json.dumps({"mode": a.mode, "seed": a.seed, "sites": sites, "steps": steps, "radius": a.radius,
                                                 "wall_s": round(time.time() - t0, 1)}, indent=1) + "\n")
    shutil.copy2(run_dir / "server.log", a.out / "server.log")


if __name__ == "__main__":
    main()
