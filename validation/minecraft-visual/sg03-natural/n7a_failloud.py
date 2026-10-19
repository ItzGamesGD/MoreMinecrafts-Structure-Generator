#!/usr/bin/env python3
"""N7-A: start the Fabric spike server WITHOUT the SG datapack; the protection tag then resolves to nothing and startup must fail loudly."""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from world import Server  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--jar", type=Path, required=True)
p.add_argument("--project", type=Path, required=True)
p.add_argument("--out", type=Path, required=True)
p.add_argument("--port", type=int, default=43000)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
empty = a.out / "empty-pack"
shutil.rmtree(empty, ignore_errors=True)
empty.mkdir()
(empty / "pack.mcmeta").write_text(json.dumps({"pack": {"description": "empty", "min_format": [121, 0], "max_format": [121, 0]}}))
run = (a.project / "run" / "server").resolve()
shutil.rmtree(run, ignore_errors=True)
run.mkdir(parents=True)
result = {"expected": "startup fails loudly"}
try:
    srv = Server("java", a.jar, run, 173, empty, port=a.port, launcher=["./gradlew", "--no-daemon", "runServer"], launcher_cwd=a.project.resolve(), start_timeout=240)
    result["outcome"] = "SERVER STARTED (unexpected: silent deactivation)"
    srv.stop()
except RuntimeError as e:
    result["outcome"] = "startup failed"
    result["message_tail"] = str(e)[-600:]
log = (run / "server.log").read_text(errors="replace") if (run / "server.log").exists() else ""
result["log_lines"] = [l.split("]: ", 1)[-1][:300] for l in log.splitlines() if "SG protection spike" in l or "SG_SPIKE" in l][:8]
result["pass"] = result["outcome"] == "startup failed" and any("resolves to no structure" in l for l in result["log_lines"])
(a.out / "failloud.json").write_text(json.dumps(result, indent=1) + "\n")
print(json.dumps(result, indent=1))
