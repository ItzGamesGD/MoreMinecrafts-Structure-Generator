#!/usr/bin/env python3
"""N10-R: the PACKAGED production jar must not let another mod weaken the write guard through the lab entrypoint.
usage: lab_isolation_check.py --out DIR   (env: SERVER_JAR, SG_PACK, JAVA_HOME; needs the built production and lab jars)
Cases, each a real server run of the built production jar on seed 173 chunk (-19,15):
  A  the genuine lab jar is installed, NO operator opt-in, hostile lab environment (SG01_WRITE_GUARD=0, SG01_MODE=observe)  -> ignored, write guard on
  B  a copy of the lab jar under another mod id, WITH the opt-in property                                                   -> ignored, write guard on
  C  the genuine lab jar WITH the opt-in and the same environment                                                           -> honoured (legitimate lab use still works)"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from production_module_check import problems  # noqa: E402

MOD = HERE.parents[2] / "mod" / "sg-worldgen-protection"
OPT_IN = "-Dsg_worldgen_protection.lab=true"


def version() -> str:
    import re
    return re.search(r"^version\s*=\s*'([^']+)'", (MOD / "build.gradle").read_text(), re.M).group(1)


def renamed_lab(src: Path, dest: Path) -> Path:
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in zi.infolist():
            data = zi.read(item)
            if item.filename == "fabric.mod.json":
                meta = json.loads(data)
                meta["id"] = "evil_lab"
                data = json.dumps(meta).encode()
            zo.writestr(item.filename, data)
    return dest


def run_case(out: Path, tag: str, extra_jar: Path, opt_in: bool) -> dict:
    env = dict(os.environ, SG01_EXTRA_MODS=str(extra_jar), SG01_WRITE_GUARD="0", SG01_MODE="observe", SG01_FEATURES="none")
    base = os.environ.get("JAVA_TOOL_OPTIONS", "")
    env["JAVA_TOOL_OPTIONS"] = (base + " " + OPT_IN).strip() if opt_in else base
    case_out = out / tag
    subprocess.run(["bash", str(HERE / "n73_run.sh"), str(case_out), "PJ", "173", "-19", "15", "rowmajor_rev", "1", "0"], env=env, check=False)
    path = case_out / "PJ_173_-19_15_rowmajor_rev_r1" / "lab.json"
    return json.loads(path.read_text()) if path.exists() else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    lab = MOD / "build" / "libs" / f"sg-worldgen-protection-{version()}-lab.jar"
    evil = renamed_lab(lab, a.out / "evil-lab.jar")
    results, failed = {}, 0
    for tag, jar, opt_in, expect_ignored in (("A_genuine_lab_no_opt_in", lab, False, True), ("B_foreign_id_with_opt_in", evil, True, True), ("C_genuine_lab_with_opt_in", lab, True, False)):
        lab_json = run_case(a.out, tag, jar, opt_in)
        log = "\n".join(lab_json.get("mixin_log", []))
        rep = lab_json.get("spike_report", {})
        if expect_ignored:
            why = problems(lab_json) if lab_json else ["no result"]
            if "ignored the lab entrypoint" not in log:
                why.append("the ignored lab entrypoint was not reported in the log")
        else:
            why = []
            if not lab_json:
                why.append("no result")
            elif not rep.get("lab") or rep.get("write_guard", {}).get("enabled") is not False:
                why.append(f"the lab opt-in did not take effect (lab={rep.get('lab')}, write_guard={rep.get('write_guard', {}).get('enabled')})")
        results[tag] = {"expect": "ignored" if expect_ignored else "honoured", "problems": why, "lab": rep.get("lab"), "write_guard_enabled": rep.get("write_guard", {}).get("enabled"),
                        "blocked_writes": rep.get("write_guard", {}).get("blocked_writes")}
        print(f"LAB_ISOLATION {tag} {'PASS' if not why else 'FAIL'} {why}", flush=True)
        failed += bool(why)
    (a.out / "lab_isolation.json").write_text(json.dumps(results, indent=1) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
