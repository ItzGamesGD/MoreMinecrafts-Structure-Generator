#!/usr/bin/env python3
"""N10-R: the built production jar on the INTEGRATED server (single-player), then the same world opened to LAN.
The integrated server runs inside a real graphical Minecraft 26.3 client (Xvfb + Mesa lavapipe). Sequence:
  1. prepare a seed-173 world with the SG-03 pack using a plain dedicated server (nothing generated near the structures), enable cheats in level.dat
  2. start the real client with the production jar as a mod and quick-play that world (single-player integrated server)
  3. through the client's own chat commands (IntegratedServerDriver in the validation mod): force-load the area of structure A (single-player),
     /publish the world to LAN, force-load the area of structure B (LAN-hosted), then stop the client gracefully
  4. assert from the module's shutdown report and the saved world: the mod loaded on the integrated server, the write guard was enabled and exercised
     both before and after publishing, nothing was unavailable, and both structures are intact (21 pieces, every template cell)
No second client connects to the LAN port; a server-list ping confirms that the LAN server answers. usage: integrated_server_check.py --out DIR  (env: JAVA_HOME, SG_PACK, SERVER_JAR)"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_natural import STRUCT, inspect  # noqa: E402
import assembly_probe as ap  # noqa: E402
from world import Server, World  # noqa: E402

REPO = HERE.parents[2]
MOD = REPO / "mod" / "sg-worldgen-protection"
VIS = REPO / "validation" / "minecraft-visual"
DISPLAY = ":78"
WORLD = "sg03int"
LAN_PORT = 25585
SITE_A = (-19, 15)   # seed 173
SITE_B = (-18, 36)   # seed 173


def version() -> str:
    import re
    return re.search(r"^version\s*=\s*'([^']+)'", (MOD / "build.gradle").read_text(), re.M).group(1)


def prepare_world(saves: Path, tmp: Path) -> None:
    run_dir = tmp / "prep"
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    srv = Server("java", Path(os.environ["SERVER_JAR"]), run_dir, 173, Path(os.environ["SG_PACK"]), port=25875, start_timeout=300)
    time.sleep(5)
    srv.stop()
    dest = saves / WORLD
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(run_dir / "world", dest)
    import nbtlib
    path = dest / "level.dat"
    nbt = nbtlib.load(path)
    data = nbt["Data"] if "Data" in nbt else nbt
    found = [k for k in data.keys() if "allow" in k.lower() and "command" in k.lower()]
    for k in found:
        data[k] = type(data[k])(1)
    if not found:
        data["allowCommands"] = nbtlib.Byte(1)
    nbt.save(path, gzipped=True)
    print("level.dat cheats keys:", found or ["allowCommands (added)"], flush=True)


def status_ping(port: int) -> dict:
    """Minecraft server-list ping (handshake + status request); returns the decoded status JSON."""
    def varint(n: int) -> bytes:
        out = b""
        while True:
            b = n & 0x7F
            n >>= 7
            out += bytes([b | (0x80 if n else 0)])
            if not n:
                return out
    host = b"127.0.0.1"
    handshake = varint(0) + varint(775) + varint(len(host)) + host + struct.pack(">H", port) + varint(1)
    with socket.create_connection(("127.0.0.1", port), timeout=10) as s:
        s.sendall(varint(len(handshake)) + handshake + varint(1) + varint(0))
        buf = b""
        s.settimeout(10)
        while len(buf) < 8:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            if b'"version"' in buf and buf.rstrip().endswith(b"}"):
                break
    text = buf.decode("utf-8", "replace")
    start = text.find("{")
    return json.loads(text[start:text.rfind("}") + 1]) if start >= 0 else {}


def main() -> int:
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--out", type=Path, required=True)
    a = ap_.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    jar = MOD / "build" / "libs" / f"sg-worldgen-protection-{version()}.jar"
    saves = VIS / "run" / "client" / "saves"
    client_dir = VIS / "run" / "client"
    shutil.rmtree(client_dir / "saves", ignore_errors=True)
    saves.mkdir(parents=True)
    (client_dir / "options.txt").write_text("guiScale:2\ntutorialStep:none\nlang:en_us\nrenderDistance:8\npauseOnLostFocus:false\n")
    prepare_world(saves, out)
    cmds = out / "commands.txt"
    report = out / "protection-report.json"
    client_log = out / "client.log"
    for f in (cmds, report):
        f.unlink(missing_ok=True)

    def rows(site, x0, x1, zc):  # one chunk row at a time (the L10 finding: a large single forceload stalls the server)
        return [f"/forceload add {x0} {zc + dz * 16} {x1} {zc + dz * 16}" for dz in range(-4, 5)]

    ax, az = SITE_A[0] * 16, SITE_A[1] * 16
    bx, bz = SITE_B[0] * 16, SITE_B[1] * 16
    lines = ["!info"] + rows("A", ax - 64, ax + 64, az) + ["!info"] * 20 + ["!info", f"/publish true {LAN_PORT}", "!info"] + rows("B", bx - 64, bx + 64, bz) + ["!info"] * 25 + ["!info", "!stop"]
    cmds.write_text("\n".join(lines) + "\n")

    xvfb = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", "1280x720x24", "+extension", "GLX", "+render", "-noreset"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    env = {**os.environ, "DISPLAY": DISPLAY, "LIBGL_ALWAYS_SOFTWARE": "1", "MESA_LOADER_DRIVER_OVERRIDE": "llvmpipe", "VK_ICD_FILENAMES": "/usr/share/vulkan/icd.d/lvp_icd.json",
           "SG01_IT_COMMANDS": str(cmds), "SG_PROTECTION_REPORT": str(report),
           "JAVA_TOOL_OPTIONS": (os.environ.get("JAVA_TOOL_OPTIONS", "") + f" -Dfabric.addMods={jar}").strip()}
    client = subprocess.Popen(["./gradlew", "--no-daemon", "-p", str(VIS), "runClient", f"--args=--quickPlaySingleplayer {WORLD} --username SG01Int --version 26.3 --width 1280 --height 720"],
                              cwd=VIS, env=env, stdout=client_log.open("w"), stderr=subprocess.STDOUT, start_new_session=True)
    ping = None
    deadline = time.time() + 1800
    published_seen = False
    start_t = time.time()
    try:
        while time.time() < deadline and client.poll() is None:
            text = client_log.read_text(errors="replace")
            if not published_seen and "SG01_IT_DONE" in text and f"/publish true {LAN_PORT}" in text:
                time.sleep(4)
                try:
                    ping = status_ping(LAN_PORT)
                    published_seen = True
                except OSError:
                    pass
            if "SG_PROTECTION protection contract OK" not in text and time.time() > start_t + 45:
                # a world with a custom datapack shows Minecraft's "experimental settings" confirmation: answer it with a real mouse click on "I Know What I'm Doing!"
                subprocess.run(["xdotool", "mousemove", "800", "273", "click", "1"], env={**os.environ, "DISPLAY": DISPLAY}, capture_output=True)
            time.sleep(8 if "SG_PROTECTION protection contract OK" not in text else 3)
        if client.poll() is None:
            os.killpg(client.pid, 15)
    finally:
        xvfb.terminate()
    text = client_log.read_text(errors="replace")
    infos = [ln.split("SG01_IT_INFO ", 1)[1] for ln in text.splitlines() if "SG01_IT_INFO" in ln]
    problems: list[str] = []
    if not report.exists():
        problems.append("no shutdown report was written (the module's SERVER_STOPPING hook did not run)")
        rep = {}
    else:
        rep = json.loads(report.read_text())
    wg = rep.get("write_guard", {})
    if "SG_PROTECTION mode=ENFORCE" not in text:
        problems.append("the module did not report starting on the integrated server")
    if not infos or "singleplayer=true" not in infos[0]:
        problems.append(f"not an integrated server: {infos[:1]}")
    if not any("published=true" in i for i in infos):
        problems.append("the world was never published to LAN")
    if ping is None or not ping.get("version"):
        problems.append(f"the LAN server did not answer a server-list ping: {ping}")
    if rep.get("lab"):
        problems.append("a lab mod was loaded")
    if not wg.get("enabled"):
        problems.append("write guard not enabled")
    if wg.get("unavailable", 1) != 0:
        problems.append(f"write guard reported unavailable regions: {wg.get('unavailable')} {wg.get('unavailable_causes')}")
    if not wg.get("regions_with_pieces") or not wg.get("blocked_writes"):
        problems.append(f"write guard not exercised: {wg}")
    # saved world: both structures intact
    templates, _ = ap.load_pack(Path(os.environ["SG_PACK"]))
    region = saves / WORLD / "dimensions" / "minecraft" / "overworld" / "region"
    if not region.is_dir():
        region = saves / WORLD / "region"
    world = World(region)
    sites = {}
    for name, (cx, cz) in (("A_singleplayer", SITE_A), ("B_lan", SITE_B)):
        start = None
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                ch = world.chunk(cx + dx, cz + dz)
                s = ((ch.nbt.get("structures") or {}).get("starts") or {}).get(STRUCT) if ch else None
                if s:
                    start = s
        if not start:
            problems.append(f"structure {name} did not generate")
            continue
        res = inspect(world, start, templates)
        sites[name] = {"pieces": res["piece_count"], "matched": res["matched"], "expected": res["expected"], "errors": res["errors"]}
        if res["matched"] != res["expected"] or res["piece_count"] != 21 or res["errors"]:
            problems.append(f"structure {name} not intact: {sites[name]}")
    result = {"jar": str(jar), "info_lines": infos, "lan_ping": ping, "write_guard": wg, "lab": rep.get("lab"), "sites": sites, "problems": problems}
    (out / "integrated_result.json").write_text(json.dumps(result, indent=1, default=str) + "\n")
    print("INTEGRATED_SERVER_CHECK", "PASS" if not problems else "FAIL", problems, flush=True)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
