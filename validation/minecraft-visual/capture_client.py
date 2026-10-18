#!/usr/bin/env python3
"""Drive the Fabric validation client through a camera list and save native 1280x720 screenshots.

The server from ``run_runtime.py --keep-server`` must be running. Uses the existing test-only
mod's request-file protocol (``Screenshot.grab`` from the live frame buffer).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rcon_client import Rcon  # noqa: E402

PLAYER = "SG01Visual"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cameras", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--settle", type=float, default=10.0, help="seconds to wait after each teleport")
    args = parser.parse_args()

    fixture = HERE
    run = fixture / "run"
    logs = run / "logs"
    client_dir = run / "client"
    shots = client_dir / "screenshots"
    logs.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    out = args.evidence / "screenshots"
    out.mkdir(parents=True, exist_ok=True)
    request = run / "screenshot-request.txt"
    request.unlink(missing_ok=True)
    for png in shots.glob("*.png"):
        png.unlink()
    (client_dir / "options.txt").write_text("guiScale:2\ntutorialStep:none\nlang:en_us\nrenderDistance:10\nhideGui:true\n")
    client_log = logs / "client.log"
    env = dict(os.environ, SG01_SCREENSHOT_REQUEST=str(request), LIBGL_ALWAYS_SOFTWARE="1", MESA_LOADER_DRIVER_OVERRIDE="llvmpipe")
    icd = next(Path("/usr/share/vulkan/icd.d").glob("lvp_icd*.json"), None)
    if icd is None:
        print("lavapipe ICD not found", file=sys.stderr)
        return 2
    env["VK_ICD_FILENAMES"] = str(icd)
    cmd = (
        "xvfb-run -a -s '-screen 0 1280x720x24 +extension GLX +render -noreset' "
        f"{fixture}/gradlew --no-daemon -p {fixture} runClient "
        "--args='--quickPlayMultiplayer 127.0.0.1:25565 --username SG01Visual --version 26.3 --width 1280 --height 720'"
    )
    proc = subprocess.Popen(cmd, shell=True, env=env, stdout=open(client_log, "w"), stderr=subprocess.STDOUT,
                            start_new_session=True, cwd=fixture)
    result_file = args.evidence / "runtime-result.txt"

    def mark(name, verdict):
        lines = result_file.read_text().splitlines() if result_file.exists() else []
        lines = [l for l in lines if not l.startswith(name + "=")] + [f"{name}={verdict}"]
        result_file.write_text("\n".join(lines) + "\n")

    def kill():
        try:
            os.killpg(proc.pid, 15)
        except ProcessLookupError:
            pass

    try:
        for _ in range(240):
            text = client_log.read_text(errors="replace")
            if "SG01_CLIENT_JOINED" in text:
                break
            if proc.poll() is not None:
                break
            time.sleep(2)
        else:
            mark("client-startup", "FAIL")
            return 1
        if "SG01_CLIENT_JOINED" not in client_log.read_text(errors="replace"):
            mark("client-startup", "FAIL")
            print(client_log.read_text(errors="replace")[-3000:])
            return 1
        mark("client-startup", "PASS")
        mark("world-join", "PASS")
        rcon = Rcon()
        for cmd_text in (f"gamemode spectator {PLAYER}", "time set noon", "weather clear",
                         f"effect give {PLAYER} minecraft:night_vision infinite 0 true"):
            rcon.run(cmd_text)
        cameras = json.loads(args.cameras.read_text())
        log = open(args.evidence / "camera-positions.log", "a")
        failed = []
        for cam in cameras:
            if "commands" in cam:  # evidence-world edits (cutaways) applied after verification
                for command in cam["commands"]:
                    log.write(f"setup: {command} -> {rcon.run(command)[:120]}\n")
                time.sleep(args.settle)
                continue
            name = cam["name"]
            reply = rcon.run(f"tp {PLAYER} {cam['x']} {cam['y']} {cam['z']} {cam['yaw']} {cam['pitch']}")
            log.write(f"{name}: {cam} -> {reply}\n")
            time.sleep(args.settle)
            request.write_text(f"{name}.png\n")
            ok = False
            for _ in range(120):
                text = client_log.read_text(errors="replace")
                if f"SG01_CAPTURE_WRITTEN name={name}.png" in text:
                    ok = True
                    break
                if f"SG01_CAPTURE_FAILED name={name}.png" in text or proc.poll() is not None:
                    break
                time.sleep(1)
            src = shots / f"{name}.png"
            if not ok or not src.is_file() or src.stat().st_size == 0:
                failed.append(name)
                continue
            shutil.copy(src, out / f"{name}.png")
        mark("screenshots", "PASS" if not failed else "FAIL")
        if failed:
            print("capture failed:", failed)
            return 1
        return 0
    finally:
        kill()


if __name__ == "__main__":
    raise SystemExit(main())
