#!/usr/bin/env python3
"""N7-A3 protection-tag and datapack-version variants (Phase 3). Each variant is a disposable copy of the SG datapack; the module is started on it.

Expected: missing, stale-only and unsupported-format variants fail at startup with an explicit diagnostic (no silent deactivation);
the superset variant starts and resolves both structures.
Environment: SG_PACK (built SG-03 datapack folder). Writes <out>/tag_variants.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from world import Server  # noqa: E402

REPO = HERE.parents[2]
SPIKE = REPO / "validation" / "fabric-protection-spike"
TAG = Path("data/moreminecrafts/tags/worldgen/structure/protected_from_overlays.json")


def variant(src: Path, dst: Path, name: str) -> Path:
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    tag = dst / TAG
    if name == "missing_tag":
        tag.unlink()
    elif name == "stale_only":
        tag.write_text(json.dumps({"values": [{"id": "moreminecrafts:forgotten_kingdom/removed_in_2_0", "required": False}]}))
    elif name == "superset":
        tag.write_text(json.dumps({"values": [{"id": "moreminecrafts:forgotten_kingdom/central_cavern", "required": False},
                                              {"id": "minecraft:stronghold", "required": False}]}))
    elif name == "unsupported_format":
        mcmeta = json.loads((dst / "pack.mcmeta").read_text())
        mcmeta["pack"]["min_format"] = mcmeta["pack"]["max_format"] = 999
        (dst / "pack.mcmeta").write_text(json.dumps(mcmeta))
    return dst


def run_variant(pack: Path, out: Path, name: str, port: int) -> dict:
    run = (SPIKE / "run" / "server").resolve()
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    result = {"variant": name}
    try:
        srv = Server("java", None, run, 173, pack, port=port, launcher=["./gradlew", "--no-daemon", "runServer"], launcher_cwd=SPIKE,
                     start_timeout=240, env={"SG01_GUARD_MODE": "enforce", "SG01_FEATURES": "both", "SG01_REFINE": "precheck"})
        result["outcome"] = "started"
        srv.stop()
    except RuntimeError as e:
        result["outcome"] = "startup failed"
        result["error_tail"] = str(e)[-400:]
    log = (run / "server.log").read_text(errors="replace") if (run / "server.log").exists() else ""
    result["log_lines"] = [ln.split("]: ", 1)[-1][:260] for ln in log.splitlines()
                           if "SG_SPIKE" in ln or "resolves to" in ln or "protected structures resolved" in ln or "Incompatible" in ln
                           or "pack" in ln.lower() and "error" in ln.lower()][:10]
    shutil.copy2(run / "server.log", out / f"{name}.log") if (run / "server.log").exists() else None
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    src = Path(__import__("os").environ["SG_PACK"])
    results = []
    for i, name in enumerate(["missing_tag", "stale_only", "unsupported_format", "superset"]):
        pack = variant(src, a.out / f"pack_{name}", name)
        results.append(run_variant(pack, a.out, name, 40960 + i))
    (a.out / "tag_variants.json").write_text(json.dumps(results, indent=1) + "\n")
    for r in results:
        print(r["variant"], r["outcome"])


if __name__ == "__main__":
    main()
