#!/usr/bin/env python3
"""N9 live Minecraft acceptance driver (criteria: docs/sg-03/n9-live-acceptance-criteria.md, fixed before any run).

Starts a fresh seed-173 world on the BUILT production jar (gradle runJarServer, no lab mod), a real graphical Minecraft 26.3 client (Xvfb, Mesa lavapipe
Vulkan) connected over TCP, and drives scenarios. Setup may use server commands; a scenario counts as LIVE only for the part done by input that the client
receives from the X server (xdotool keyboard / mouse). Every step is recorded with its evidence level (LIVE, SERVER-ONLY, SAVED-DATA, BLOCKED).
usage: live_acceptance.py --out DIR   (env: JAVA_HOME, SG_PACK)"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
from run_natural import STRUCT  # noqa: E402
from world import Server, World  # noqa: E402

MOD = REPO / "mod" / "sg-worldgen-protection"
VIS = REPO / "validation" / "minecraft-visual"
DISPLAY = ":77"
PLAYER = "SG01Live"
RESULTS: dict = {"steps": {}}
OUT: Path


def log(step: str, level: str, ok: bool | None, detail) -> None:
    RESULTS["steps"][step] = {"level": level, "pass": ok, "detail": detail}
    print(f"[{step}] {level} {'PASS' if ok else ('FAIL' if ok is False else 'N/A')} {str(detail)[:200]}", flush=True)


def xdo(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["xdotool", *args], env={**os.environ, "DISPLAY": DISPLAY}, capture_output=True, text=True, timeout=30)


def pos(server: Server) -> tuple[float, float, float]:
    r = server.cmd(f"data get entity {PLAYER} Pos")
    m = re.search(r"\[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]", r)
    if not m:
        raise RuntimeError(f"no position in {r!r}")
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def tp(server: Server, x: float, y: float, z: float, facing: tuple | None = None) -> None:
    server.cmd(f"tp {PLAYER} {x} {y} {z}" + (f" facing {facing[0]} {facing[1]} {facing[2]}" if facing else ""))
    time.sleep(3)


def screenshot(client_log: Path, shots: Path, request: Path, name: str, wait_s: int = 120) -> dict:
    """Native Screenshot.grab through the test harness mod's request file."""
    time.sleep(3)
    request.write_text(f"{name}.png\n")
    deadline = time.time() + wait_s
    src = shots / f"{name}.png"
    while time.time() < deadline:
        text = client_log.read_text(errors="replace")
        if f"SG01_CAPTURE_WRITTEN name={name}.png" in text:
            break
        if f"SG01_CAPTURE_FAILED name={name}.png" in text:
            return {"name": name, "ok": False, "reason": "capture failed"}
        time.sleep(1.5)
    else:
        return {"name": name, "ok": False, "reason": "timeout"}
    colours = int(subprocess.run(["identify", "-format", "%k", str(src)], capture_output=True, text=True).stdout.strip() or 0)
    dest = OUT / "screenshots" / f"{name}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {"name": name, "ok": colours > 1000, "colours": colours, "size": src.stat().st_size}


def walk(server: Server, seconds: float, sprint: bool = True, jump: bool = True) -> tuple[tuple, tuple]:
    """Hold W (and sprint/jump) in the client window for `seconds`; returns the player's server-side position before and after."""
    a = pos(server)
    wid = xdo("search", "--name", "Minecraft").stdout.split()[-1]
    xdo("windowfocus", "--sync", wid)
    xdo("mousemove", "640", "360")
    keys = ["w"] + (["ctrl"] if sprint else [])
    for k in keys:
        xdo("keydown", k)
    t0 = time.time()
    while time.time() - t0 < seconds:
        if jump:
            xdo("key", "space")
        time.sleep(0.45)
    for k in keys:
        xdo("keyup", k)
    time.sleep(1.0)
    return a, pos(server)


def main() -> None:
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=173)
    a = ap.parse_args()
    OUT = a.out.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    env_common = {**os.environ}
    run_dir = (MOD / "run" / "server").resolve()
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    client_dir = VIS / "run" / "client"
    shots = client_dir / "screenshots"
    request = VIS / "run" / "screenshot-request.txt"
    client_log = OUT / "client.log"
    xvfb = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", "1280x720x24", "+extension", "GLX", "+render", "-noreset"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    server = client = None
    try:
        report = OUT / "protection-report.json"
        server = Server("java", None, run_dir, a.seed, Path(os.environ["SG_PACK"]), port=25665, launcher=["./gradlew", "--no-daemon", "jar", "runJarServer"],
                        launcher_cwd=MOD, start_timeout=900, env={"SG_PROTECTION_REPORT": str(report)},
                        extra_props={"difficulty": "normal", "spawn-monsters": "true", "spawn-animals": "false", "view-distance": "6", "simulation-distance": "6",
                                     "pause-when-empty-seconds": "-1", "max-tick-time": "-1", "gamemode": "survival", "spawn-protection": "0"})
        log("server_start", "SERVER", True, "production jar, fresh world, seed %d" % a.seed)
        client_dir.mkdir(parents=True, exist_ok=True)
        (client_dir / "options.txt").write_text("guiScale:2\ntutorialStep:none\nlang:en_us\nrenderDistance:8\npauseOnLostFocus:false\n")
        shutil.rmtree(shots, ignore_errors=True)
        shots.mkdir(parents=True)
        request.unlink(missing_ok=True)
        cenv = {**env_common, "DISPLAY": DISPLAY, "LIBGL_ALWAYS_SOFTWARE": "1", "MESA_LOADER_DRIVER_OVERRIDE": "llvmpipe",
                "VK_ICD_FILENAMES": "/usr/share/vulkan/icd.d/lvp_icd.json", "SG01_SCREENSHOT_REQUEST": str(request)}
        client = subprocess.Popen(["./gradlew", "--no-daemon", "-p", str(VIS), "runClient", f"--args=--quickPlayMultiplayer 127.0.0.1:25565 --username {PLAYER} --version 26.3 --width 1280 --height 720"],
                                  cwd=VIS, env=cenv, stdout=client_log.open("w"), stderr=subprocess.STDOUT, start_new_session=True)
        joined = False
        for _ in range(450):
            t = client_log.read_text(errors="replace")
            if "SG01_CLIENT_JOINED" in t:
                joined = True
                break
            if client.poll() is not None:
                break
            time.sleep(2)
        listed = PLAYER in server.cmd("list")
        render = "Using graphics backend" in client_log.read_text(errors="replace")
        if not (joined and listed):
            log("L1_join", "LIVE", False, {"joined": joined, "listed": listed, "renderer_started": render})
            raise SystemExit("client did not join")
        server.cmd("time set noon")
        server.cmd("weather clear")
        server.cmd(f"gamemode survival {PLAYER}")
        server.cmd(f"effect give {PLAYER} minecraft:night_vision infinite 0 true")
        server.cmd(f"effect give {PLAYER} minecraft:resistance infinite 4 true")
        server.cmd(f"give {PLAYER} minecraft:iron_sword")
        shot = screenshot(client_log, shots, request, "L1-spawn")
        log("L1_join", "LIVE", bool(joined and listed and render and shot["ok"]), {"renderer_started": render, "server_lists_player": listed, "screenshot": shot})

        # L2 locate a naturally generated structure
        r = server.cmd(f"execute in minecraft:overworld positioned 0 64 0 run locate structure moreminecrafts:forgotten_kingdom/central_cavern")
        m = re.search(r"\[(-?\d+), (~|-?\d+), (-?\d+)\]", r)
        if not m:
            log("L2_locate", "SERVER", False, r)
            raise SystemExit("no structure located")
        sx, sz = int(m.group(1)), int(m.group(3))
        server.cmd("save-all flush")
        time.sleep(5)
        world = World(server.region_dir)
        start = None
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                ch = world.chunk((sx >> 4) + dx, (sz >> 4) + dz)
                s = ((ch.nbt.get("structures") or {}).get("starts") or {}).get(STRUCT) if ch else None
                if s:
                    start = s
        boxes = [c["BB"] for c in start["Children"]] if start else []
        log("L2_locate", "SAVED-DATA", bool(start), {"locate_reply": r, "position": [sx, sz], "start_in_saved_world": bool(start), "pieces": len(boxes), "placed_with_command": False})
        if not start:
            raise SystemExit("start not in saved world")
        lo = [min(b[i] for b in boxes) for i in range(3)]
        hi = [max(b[i + 3] for b in boxes) for i in range(3)]
        cxm, cym, czm = (lo[0] + hi[0]) // 2, (lo[1] + hi[1]) // 2, (lo[2] + hi[2]) // 2

        # L3 approach by real keyboard from the surface
        px, pz = cxm + 90, czm
        server.cmd(f"forceload add {px - 32} {pz - 32} {px + 32} {pz + 32}")
        time.sleep(10)
        server.cmd(f"spreadplayers {px} {pz} 0 1 false {PLAYER}")
        time.sleep(4)
        server.cmd(f"execute as {PLAYER} at @s run tp @s ~ ~ ~ facing {cxm} 64 {czm}")
        time.sleep(2)
        shot1 = screenshot(client_log, shots, request, "L3-approach-start")
        before, after = walk(server, 7.0)
        moved = math.dist((before[0], before[2]), (after[0], after[2]))
        toward = math.dist((before[0], before[2]), (cxm, czm)) - math.dist((after[0], after[2]), (cxm, czm))
        shot2 = screenshot(client_log, shots, request, "L3-approach-end")
        log("L3_approach", "LIVE", moved >= 20 and toward >= 15, {"moved_blocks": round(moved, 1), "closer_by": round(toward, 1), "start": before, "end": after, "screenshots": [shot1, shot2],
                                                                  "note": "surface approach by W+sprint+jump key events; the structure lies deep underground, entry below is SERVER-ONLY (teleport)"})
        shot_ext = screenshot(client_log, shots, request, "L8-surface-above")

        # L4 traversal of tunnel pieces by real keyboard input
        tunnels = [(i, c) for i, c in enumerate(start["Children"]) if "tunnel_" in c["pool_element"]["location"]]
        legs = []
        for i, c in tunnels[:4]:
            bb = c["BB"]
            lx, lz = bb[3] - bb[0], bb[5] - bb[2]
            along_x = lx >= lz
            y = bb[1] + 1
            if along_x:
                x0, x1, z0 = bb[0] + 1, bb[3] - 1, (bb[2] + bb[5]) / 2 + 0.5
                tp(server, x0, y, z0, (x1, y, z0))
                length = abs(x1 - x0)
            else:
                z0, z1, x0 = bb[2] + 1, bb[5] - 1, (bb[0] + bb[3]) / 2 + 0.5
                tp(server, x0, y, z0, (x0, y, z1))
                length = abs(z1 - z0)
            server.cmd(f"execute as {PLAYER} at @s run tp @s ~ ~ ~ facing {(x1 if along_x else x0)} {y} {(z0 if along_x else z1)}")
            time.sleep(1)
            before, after = walk(server, max(3.0, length / 4.0), sprint=False, jump=False)
            progress = math.dist((before[0], before[2]), (after[0], after[2]))
            inside = bb[0] - 1 <= after[0] <= bb[3] + 2 and bb[2] - 1 <= after[2] <= bb[5] + 2
            shot = screenshot(client_log, shots, request, f"L4-tunnel-{len(legs) + 1}")
            legs.append({"piece": c["pool_element"]["location"].rsplit("/", 1)[-1], "length": length, "progress": round(progress, 1), "ended_inside_piece_box": inside, "ok": progress >= 0.5 * length and inside, "screenshot": shot})
        log("L4_traverse", "LIVE", sum(l["ok"] for l in legs) >= 3, {"legs": legs, "note": "each leg: teleport to the piece start (SERVER-ONLY setup), then W held in the client; success = progress along the corridor"})

        # L6 combat with real mouse clicks inside the structure
        bb = start["Children"][0]["BB"]
        cx, cy, cz = (bb[0] + bb[3]) // 2, bb[1] + 1, (bb[2] + bb[5]) // 2
        tp(server, cx + 0.5, cy, cz + 0.5, (cx + 0.5, cy + 1.6, cz + 5.5))
        server.cmd(f"execute as {PLAYER} at @s run tp @s ~ ~ ~ facing {cx + 0.5} {cy + 1.6} {cz + 5.5}")
        server.cmd(f"execute as {PLAYER} at @s run summon minecraft:zombie ^ ^ ^2 {{NoAI:1b,PersistenceRequired:1b,Tags:[\"sg01combat\"]}}")
        time.sleep(2)
        alive0 = "Test passed" in server.cmd("execute if entity @e[tag=sg01combat]")
        wid = xdo("search", "--name", "Minecraft").stdout.split()[-1]
        xdo("windowfocus", "--sync", wid)
        xdo("mousemove", "640", "360")
        xdo("key", "1")
        for _ in range(16):
            xdo("click", "1")
            time.sleep(0.8)
        time.sleep(1)
        alive1 = "Test passed" in server.cmd("execute if entity @e[tag=sg01combat]")
        log("L6_combat", "LIVE", alive0 and not alive1, {"zombie_alive_before_clicks": alive0, "zombie_alive_after_16_left_clicks": alive1, "weapon": "iron_sword (given by command)", "target": "NoAI zombie 2 blocks ahead"})

        # L7 trial spawner with the real player present
        spawners = []
        for x in range(lo[0] >> 4, (hi[0] >> 4) + 1):
            for z in range(lo[2] >> 4, (hi[2] >> 4) + 1):
                ch = world.chunk(x, z)
                if ch:
                    spawners += [(be["x"], be["y"], be["z"]) for be in ch.nbt.get("block_entities", []) if be.get("id") == "minecraft:trial_spawner"]
        if not spawners:
            log("L7_trial_spawner", "SAVED-DATA", False, "no trial spawner block entity found")
        else:
            sxp, syp, szp = spawners[0]
            server.cmd(f"effect give {PLAYER} minecraft:resistance infinite 4 true")
            tp(server, sxp + 0.5, syp + 2, szp + 3.5)
            before_state = server.cmd(f"data get block {sxp} {syp} {szp}")[:400]
            time.sleep(25)
            after_state = server.cmd(f"data get block {sxp} {syp} {szp}")[:400]
            mobs = server.cmd(f"execute if entity @e[type=!minecraft:player,type=!minecraft:zombie,distance=..16]")
            shot = screenshot(client_log, shots, request, "L7-trial-spawner")
            active = re.search(r'spawn_data|current_mobs|total_mobs_spawned', after_state) is not None
            log("L7_trial_spawner", "SERVER-ONLY (player entity of the live client present)", before_state != after_state or active,
                {"spawner": [sxp, syp, szp], "before": before_state, "after": after_state, "nearby_non_player_entities": mobs[:100], "screenshot": shot})

        # L9 geode / monster-room interaction: cancelled features recorded by the guard, and natural ones away from the structure
        shot_g = screenshot(client_log, shots, request, "L9-structure-vicinity")
        log("L9_features_screens", "LIVE", shot_g["ok"], {"screenshot": shot_g, "note": "cancellation locations come from the shutdown report (see protection-report.json)"})

        # L10 stability
        tick = server.cmd("tick query")
        RESULTS["tick_query"] = tick[:300]
        slog = (run_dir / "server.log").read_text(errors="replace")
        clog = client_log.read_text(errors="replace")
        keep_up = len(re.findall(r"Can't keep up", slog))
        crash = "Exception in thread" in clog and "Render thread" in clog
        log("L10_stability", "LIVE", keep_up == 0 and not crash and client.poll() is None, {"server_cant_keep_up": keep_up, "client_render_thread_exception": crash, "client_alive": client.poll() is None, "tick_query": tick[:200]})
    finally:
        try:
            if server:
                server.cmd("save-all flush")
        except Exception:
            pass
        if client and client.poll() is None:
            try:
                os.killpg(client.pid, 15)
            except ProcessLookupError:
                pass
        if server:
            server.stop()
            shutil.copy2(run_dir / "server.log", OUT / "server.log")
        xvfb.terminate()
        (OUT / "live-results.json").write_text(json.dumps(RESULTS, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
