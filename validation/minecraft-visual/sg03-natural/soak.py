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

# Minecraft 26.x pauses an empty dedicated server after 60 s, which stops chunk loading; a long soak without players must disable that.
NO_PAUSE = {"pause-when-empty-seconds": "-1"}
SPIKE = HERE.parents[2] / "mod" / "sg-worldgen-protection"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--mode", choices=["guarded", "control", "write"], required=True)
    p.add_argument("--seed", type=int, default=173)
    p.add_argument("--sites", type=int, default=36)
    p.add_argument("--ring", type=int, default=6, help="N8: candidate ring radius (chunks of spacing) for site selection")
    p.add_argument("--site-file", type=Path, help="N8: JSON list of [cx, cz] sites to use instead of the ring selection (reproduction of damaged sites)")
    p.add_argument("--radius", type=int, default=5)
    p.add_argument("--settle", type=float, default=4.0)
    p.add_argument("--idle", type=float, default=90.0, help="seconds of idle sampling after the last site")
    p.add_argument("--port", type=int, default=41010)
    p.add_argument("--release", choices=["all", "area", "none"], default="all", help="how a finished site is released: 'forceload remove all', remove only its area, or keep it")
    p.add_argument("--vanilla", type=Path, help="N7-A4 isolation: run the plain vanilla server jar (no module, no sampler) instead of the Fabric module")
    p.add_argument("--no-sampler", action="store_true", help="N7-A4 isolation: run the module without the JVM sampler")
    p.add_argument("--min-separation", type=int, default=24, help="minimum Chebyshev distance in chunks between chosen sites (0 = none)")
    p.add_argument("--wait", type=float, default=120.0, help="seconds to wait for a site to load before diagnosing a stall")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    ordered = sorted((c for c in candidates_in_ring(a.seed, SG01, a.ring) if not exclusion_suppressed(a.seed, c)), key=lambda c: (c[0] ** 2 + c[1] ** 2, c))
    # Greedy selection with a minimum Chebyshev separation, so that the structure-start dependency zones (8 chunks) of two sites never touch.
    sites = []
    for c in ordered:
        if all(max(abs(c[0] - k[0]), abs(c[1] - k[1])) >= a.min_separation for k in sites):
            sites.append(c)
        if len(sites) == a.sites:
            break
    if a.site_file:
        sites = [tuple(s) for s in json.loads(a.site_file.read_text())]
    samples = (a.out / "samples.jsonl").resolve()
    report = (a.out / "spike-report.json").resolve()
    for f in (samples, report):
        f.unlink(missing_ok=True)
    run_dir = (SPIKE / "run" / "server").resolve()
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    env = {"SG01_SAMPLE_FILE": str(samples), "SG01_SAMPLE_MS": "5000", "SG_PROTECTION_REPORT": str(report)}  # guarded arm: the production configuration
    if a.mode == "control":
        env.update({"SG01_FEATURES": "none", "SG01_WRITE_GUARD": "0"})  # control arm: every guard disabled (lab setting)
    elif a.mode == "write":
        env.update({"SG01_FEATURES": "none"})  # N8-R: the write-level guard only
    if a.no_sampler:
        env.pop("SG01_SAMPLE_FILE")
    if a.vanilla:
        run_dir = (a.out / "vanilla-world").resolve()
        shutil.rmtree(run_dir, ignore_errors=True)
        run_dir.mkdir(parents=True)
        srv = Server("java", a.vanilla.resolve(), run_dir, a.seed, Path(os.environ["SG_PACK"]), port=a.port, xmx="3G", extra_props=NO_PAUSE)
    else:
        srv = Server("java", None, run_dir, a.seed, Path(os.environ["SG_PACK"]), port=a.port, launcher=["./gradlew", "--no-daemon", "runLabServer"],
                     launcher_cwd=SPIKE, start_timeout=600, env=env, extra_props=NO_PAUSE)
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
                loaded = {f"{x},{z}": "Test passed" in srv.cmd(f"execute if loaded {x * 16} 0 {z * 16}")
                          for x in range(cx - r, cx + r + 1) for z in range(cz - r, cz + r + 1)}
                diag["loaded_chunks_in_area"] = sum(loaded.values())
                diag["not_loaded"] = sorted(k for k, v in loaded.items() if not v)
                # does releasing and re-adding the area recover it?
                srv.cmd("forceload remove all")
                time.sleep(3)
                srv.cmd(f"forceload add {(cx - r) * 16} {(cz - r) * 16} {(cx + r) * 16} {(cz + r) * 16}")
                try:
                    wait_loaded(srv, (cx + r) * 16, (cz + r) * 16, seconds=60)
                    diag["recovered_after_readd"] = True
                except RuntimeError:
                    diag["recovered_after_readd"] = False
                (a.out / "stall.json").write_text(json.dumps(diag, indent=1) + "\n")
                import subprocess
                jpid = subprocess.run(["bash", "-c", "ps -eo pid,args | awk '/fabric\\.dli/ {print $1; exit}'"], capture_output=True, text=True).stdout.strip()
                if jpid:
                    (a.out / "threads.txt").write_text(subprocess.run(["jcmd", jpid, "Thread.print"], capture_output=True, text=True).stdout)
                shutil.copy2(run_dir / "server.log", a.out / "server.log")
                raise
            time.sleep(a.settle)
            if a.release == "all":
                srv.cmd("forceload remove all")
            elif a.release == "area":
                srv.cmd(f"forceload remove {(cx - r) * 16} {(cz - r) * 16} {(cx + r) * 16} {(cz + r) * 16}")
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
