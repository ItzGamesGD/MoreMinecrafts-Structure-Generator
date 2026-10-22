#!/usr/bin/env python3
"""N9 live Minecraft acceptance driver (criteria: docs/sg-03/n9-live-acceptance-criteria.md, fixed before any run).

Starts a fresh seed-173 world on the BUILT production jar (gradle runJarServer, no lab mod), a real graphical Minecraft 26.3 client (Xvfb, Mesa lavapipe
Vulkan) connected over TCP, and drives scenarios. Setup may use server commands; a scenario counts as LIVE only for the part done by input that the client
receives from the X server (xdotool keyboard / mouse). Every step is recorded with its evidence level (LIVE, SERVER-ONLY, SAVED-DATA, BLOCKED).
No /place command is used anywhere. usage: live_acceptance.py --out DIR   (env: JAVA_HOME, SG_PACK)"""
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
from run_natural import AIR, ROT, STRUCT, inspect  # noqa: E402
import assembly_probe as ap  # noqa: E402
from world import Server, World  # noqa: E402

MOD = REPO / "mod" / "sg-worldgen-protection"
VIS = REPO / "validation" / "minecraft-visual"
DISPLAY = ":77"
PLAYER = "SG01Live"
RESULTS: dict = {"steps": {}}
OUT: Path
SPAWNER_STATES = ("inactive", "waiting_for_players", "active", "waiting_for_reward_ejection", "ejecting_reward", "cooldown")


def log(step: str, level: str, ok: bool | None, detail) -> None:
    RESULTS["steps"][step] = {"level": level, "pass": ok, "detail": detail}
    print(f"[{step}] {level} {'PASS' if ok else ('FAIL' if ok is False else 'N/A')} {str(detail)[:220]}", flush=True)


def xdo(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["xdotool", *args], env={**os.environ, "DISPLAY": DISPLAY}, capture_output=True, text=True, timeout=30)


def client_window() -> str:
    """X window id of the Minecraft client; tries title, class and any visible window, and dumps the window tree when none is found."""
    for args in (("--name", "Minecraft"), ("--class", "Minecraft"), ("--classname", "Minecraft"), ("--onlyvisible", "--name", ".")):
        ids = xdo("search", *args).stdout.split()
        if ids:
            return ids[-1]
    tree = subprocess.run(["xwininfo", "-root", "-tree"], env={**os.environ, "DISPLAY": DISPLAY}, capture_output=True, text=True).stdout
    (OUT / "windows.txt").write_text(tree)
    raise RuntimeError("no client window found; see windows.txt")


def focus() -> None:
    # no mousemove here: with the cursor grabbed, an absolute warp is read as a look movement and rotates the camera (found in run 4)
    xdo("windowfocus", "--sync", client_window())


def pos(server: Server) -> tuple[float, float, float]:
    r = server.cmd(f"data get entity {PLAYER} Pos")
    m = re.search(r"\[(-?[\d.]+(?:E-?\d+)?)d, (-?[\d.]+(?:E-?\d+)?)d, (-?[\d.]+(?:E-?\d+)?)d\]", r)
    if not m:
        raise RuntimeError(f"no position in {r!r}")
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def tp(server: Server, x: float, y: float, z: float, facing: tuple | None = None) -> None:
    server.cmd(f"tp {PLAYER} {x} {y} {z}" + (f" facing {facing[0]} {facing[1]} {facing[2]}" if facing else ""))
    time.sleep(3)


def screenshot(client_log: Path, shots: Path, request: Path, name: str, wait_s: int = 120) -> dict:
    """Native Screenshot.grab through the test harness mod's request file."""
    time.sleep(2)
    t0 = time.time()
    request.write_text(f"{name}.png\n")
    deadline = time.time() + wait_s
    src = shots / f"{name}.png"
    while time.time() < deadline:
        text = client_log.read_text(errors="replace")
        if f"SG01_CAPTURE_WRITTEN name={name}.png" in text:
            break
        if f"SG01_CAPTURE_FAILED name={name}.png" in text:
            return {"name": name, "ok": False, "reason": "capture failed"}
        time.sleep(1.0)
    else:
        return {"name": name, "ok": False, "reason": "timeout"}
    colours = int(subprocess.run(["identify", "-format", "%k", str(src)], capture_output=True, text=True).stdout.strip() or 0)
    dest = OUT / "screenshots" / f"{name}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {"name": name, "ok": colours > 1000, "colours": colours, "size": src.stat().st_size, "latency_s": round(time.time() - t0, 1)}


def rotation(server: Server) -> tuple[float, float]:
    r = server.cmd(f"data get entity {PLAYER} Rotation")
    m = re.search(r"\[(-?[\d.]+(?:E-?\d+)?)f, (-?[\d.]+(?:E-?\d+)?)f\]", r)
    if not m:
        raise RuntimeError(f"no rotation in {r!r}")
    return float(m.group(1)), float(m.group(2))


AIM = {"real_mouse": 0, "tp_facing_fallback": 0}


def aim(server: Server, tx: float, tz: float) -> str:
    """Turn the camera towards (tx, tz) with real relative mouse motion (0.15 degrees per pixel at the default sensitivity); falls back to /tp facing (SERVER-ONLY, counted)."""
    for _ in range(5):
        yaw, _p = rotation(server)
        px, _py, pz = pos(server)
        want = math.degrees(math.atan2(-(tx - px), tz - pz))
        d = (want - yaw + 180) % 360 - 180
        if abs(d) < 5:
            AIM["real_mouse"] += 1
            return "real_mouse"
        focus()
        xdo("mousemove_relative", "--", str(round(d / 0.15)), "0")
        time.sleep(0.6)
    px, py, pz = pos(server)
    server.cmd(f"execute as {PLAYER} at @s run tp @s ~ ~ ~ facing {tx} {py} {tz}")
    AIM["tp_facing_fallback"] += 1
    return "tp_facing_fallback"


def walk_to(server: Server, target: tuple[float, float], seconds: float, until=None, sprint: bool = False, steer: bool = True, jump: bool = False) -> dict:
    """Walk towards target (x, z) holding W (jump on) in the client window; re-aim between 2.5 s segments; strafe with A/D when blocked. Returns server-side positions and the time held."""
    start = pos(server)
    t0 = time.time()
    modes, strafes = [], 0
    last_progress = start
    while time.time() - t0 < seconds:
        if until and until(pos(server)):
            break
        if steer:
            modes.append(aim(server, *target))
        focus()
        keys = ["w"] + (["ctrl"] if sprint else [])
        for k in keys:
            xdo("keydown", k)
        t1 = time.time()
        try:
            while time.time() - t1 < 2.5 and time.time() - t0 < seconds:
                if jump:
                    xdo("key", "space")
                time.sleep(0.4)
                if until and until(pos(server)):
                    break
        finally:
            for k in keys:
                xdo("keyup", k)
        now = pos(server)
        if math.dist((now[0], now[2]), (last_progress[0], last_progress[2])) < 0.6:
            side = "a" if strafes % 2 == 0 else "d"
            strafes += 1
            xdo("keydown", side)
            xdo("keydown", "w")
            xdo("key", "space")
            time.sleep(0.9)
            xdo("keyup", "w")
            xdo("keyup", side)
        last_progress = now
    time.sleep(1.0)
    end = pos(server)
    return {"start": start, "end": end, "held_s": round(time.time() - t0, 1), "aim_modes": {m: modes.count(m) for m in set(modes)}, "strafes": strafes}


def in_box(p, bb, pad: float = 0.0) -> bool:
    return bb[0] - pad <= p[0] <= bb[3] + 1 + pad and bb[1] - 2 <= p[1] <= bb[4] + 2 and bb[2] - pad <= p[2] <= bb[5] + 1 + pad


def passable(b: dict) -> bool:
    return b["id"] in AIR


def standing_cells(world: World, bb, centre, radius: int, y_lo: int | None = None):
    """Cells with a solid floor and two cells of headroom inside bb, nearest to centre first."""
    out = []
    cx, cy, cz = centre
    for x in range(int(cx) - radius, int(cx) + radius + 1):
        for z in range(int(cz) - radius, int(cz) + radius + 1):
            for y in range((y_lo if y_lo is not None else bb[1]), bb[4]):
                if passable(world.state(x, y, z)) and passable(world.state(x, y + 1, z)) and not passable(world.state(x, y - 1, z)) \
                        and world.state(x, y - 1, z)["id"] not in ("minecraft:lava", "minecraft:water"):
                    out.append((math.dist((x + .5, y, z + .5), (cx, cy, cz)), x, y, z))
    return [c[1:] for c in sorted(out)]


def clear_line(world: World, a, b, step: float = 0.25) -> bool:
    """True when every cell between a and b is passable; the cell that contains b (the target block itself) is not counted."""
    d = math.dist(a, b)
    n = max(1, int(d / step))
    target = tuple(math.floor(c) for c in b)
    for i in range(1, n):
        t = i / n
        cell = tuple(math.floor(a[k] + (b[k] - a[k]) * t) for k in range(3))
        if cell != target and not passable(world.state(*cell)):
            return False
    return True


def view_cell(world: World, target, lo: float = 2.0, hi: float = 6.0, radius: int = 7):
    """An air cell with headroom near target, with clear line of sight to it, nearest first within lo..hi blocks (a camera spot inside the room or cavity)."""
    tx, ty, tz = target
    best = []
    for x in range(tx - radius, tx + radius + 1):
        for y in range(ty - 4, ty + 5):
            for z in range(tz - radius, tz + radius + 1):
                d = math.dist((x + .5, y + 1.0, z + .5), (tx + .5, ty + .5, tz + .5))
                if lo <= d <= hi and passable(world.state(x, y, z)) and passable(world.state(x, y + 1, z)):
                    best.append((d, x, y, z))
    for d, x, y, z in sorted(best):
        if clear_line(world, (x + .5, y + 1.62, z + .5), (tx + .5, ty + .5, tz + .5)):
            return (x, y, z)
    return None


def find_blocks(world: World, chunks, ids: set[str], limit: int = 5):
    found = []
    for cx, cz in chunks:
        ch = world.chunk(cx, cz)
        if not ch:
            continue
        for sy, (palette, idx) in ch.sections.items():
            hit = {i for i, st in enumerate(palette) if st["id"] in ids}
            if not hit:
                continue
            for flat in range(4096):
                if int(idx[flat]) in hit:
                    found.append((cx * 16 + (flat & 15), sy * 16 + (flat >> 8), cz * 16 + ((flat >> 4) & 15), palette[int(idx[flat])]["id"]))
                    if len(found) >= limit:
                        return found
    return found


def main() -> None:
    global OUT
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--out", type=Path, required=True)
    ap_.add_argument("--seed", type=int, default=173)
    a = ap_.parse_args()
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
    templates, _ = ap.load_pack(Path(os.environ["SG_PACK"]))
    xvfb = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", "1280x720x24", "+extension", "GLX", "+render", "-noreset"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    server = client = None
    scenario_t0 = None
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
        (OUT / "windows-after-join.txt").write_text(subprocess.run(["xwininfo", "-root", "-tree"], env={**os.environ, "DISPLAY": DISPLAY}, capture_output=True, text=True).stdout)
        server.cmd("time set noon")
        server.cmd("weather clear")
        server.cmd(f"gamemode survival {PLAYER}")
        server.cmd(f"effect give {PLAYER} minecraft:night_vision infinite 0 true")
        server.cmd(f"effect give {PLAYER} minecraft:resistance infinite 4 true")
        server.cmd(f"give {PLAYER} minecraft:iron_sword")
        shot = screenshot(client_log, shots, request, "L1-spawn")
        log("L1_join", "LIVE", bool(joined and listed and render and shot["ok"]), {"renderer_started": render, "server_lists_player": listed, "screenshot": shot})
        scenario_t0 = time.time()
        server_log_mark = len((run_dir / "server.log").read_text(errors="replace"))

        # L2 locate a naturally generated structure
        r = server.cmd("execute in minecraft:overworld positioned 0 64 0 run locate structure moreminecrafts:forgotten_kingdom/central_cavern")
        m = re.search(r"\[(-?\d+), (~|-?\d+), (-?\d+)\]", r)
        if not m:
            log("L2_locate", "SERVER", False, r)
            raise SystemExit("no structure located")
        sx, sz = int(m.group(1)), int(m.group(3))
        # /locate only reports a candidate position; load the structure's area one chunk row at a time so the world generates it naturally (no /place anywhere)
        for row in range(-4, 5):
            server.cmd(f"forceload add {sx - 64} {sz + row * 16} {sx + 64} {sz + row * 16}")
            time.sleep(3)
        start = None
        world = None
        for _ in range(40):
            server.cmd("save-all flush")
            time.sleep(6)
            world = World(server.region_dir)
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    ch = world.chunk((sx >> 4) + dx, (sz >> 4) + dz)
                    s = ((ch.nbt.get("structures") or {}).get("starts") or {}).get(STRUCT) if ch else None
                    if s:
                        start = s
            if start:
                break
        boxes = [c["BB"] for c in start["Children"]] if start else []
        log("L2_locate", "SAVED-DATA", bool(start), {"locate_reply": r, "position": [sx, sz], "start_in_saved_world": bool(start), "pieces": len(boxes), "placed_with_command": False})
        if not start:
            raise SystemExit("start not in saved world")
        lo = [min(b[i] for b in boxes) for i in range(3)]
        hi = [max(b[i + 3] for b in boxes) for i in range(3)]
        cxm, cym, czm = (lo[0] + hi[0]) // 2, (lo[1] + hi[1]) // 2, (lo[2] + hi[2]) // 2
        children = start["Children"]
        leaf = lambda c: c["pool_element"]["location"].rsplit("/", 1)[-1]  # noqa: E731

        # L5 (SERVER-ONLY, saved data): every junction's doorway cells are passable. Connector y = ground y for flat junctions, ground y + |delta_y| for upper rooms.
        pairs, blocked = 0, []
        for i, c in enumerate(children):
            for j in c["junctions"]:
                y0 = j["source_ground_y"] + abs(j["delta_y"])
                col = [world.state(j["source_x"], y0 + k, j["source_z"])["id"] for k in (0, 1)]
                pairs += 1
                if not all(b in AIR for b in col):
                    blocked.append({"piece": i, "name": leaf(c), "cell": [j["source_x"], y0, j["source_z"]], "blocks": col})
        log("L5_connections", "SERVER-ONLY (saved data)", not blocked and pairs > 0, {"junction_entries": pairs, "blocked": blocked, "pieces": len(children)})

        # saved-data integrity of the live world: the same template audit as B1 (inspect)
        res = inspect(world, start, templates)
        log("integrity_audit", "SAVED-DATA", res["expected"] == res["matched"] and not res["errors"],
            {"pieces": res["piece_count"], "expected": res["expected"], "matched": res["matched"], "mismatch": res["expected"] - res["matched"], "trial_spawner_blocks": res["trial_spawners"],
             "trial_spawner_entities": res["trial_spawner_entities"], "errors": res["errors"], "mismatch_sample": res["mismatches"][:10]})

        server_log_after_l2 = len((run_dir / "server.log").read_text(errors="replace"))

        # L3 approach by real keyboard from the surface; up to four starting points, each attempt recorded
        attempts = []
        approach_ok = False
        for ang, (dx, dz) in enumerate(((90, 0), (0, 90), (-90, 0), (0, -90))):
            px, pz = cxm + dx, czm + dz
            server.cmd(f"forceload add {px - 32} {pz - 32} {px + 32} {pz + 32}")
            time.sleep(10)
            server.cmd(f"spreadplayers {px} {pz} 0 1 false {PLAYER}")
            time.sleep(4)
            server.cmd(f"execute as {PLAYER} at @s run tp @s ~ ~ ~ facing {cxm} 64 {czm}")
            time.sleep(2)
            shot1 = screenshot(client_log, shots, request, f"L3-approach-{ang + 1}-start")
            w3 = walk_to(server, (cxm, czm), 30.0, sprint=True, jump=True, until=lambda p, c0=pos(server): math.dist((p[0], p[2]), (c0[0], c0[2])) >= 28)
            before, after, held = w3["start"], w3["end"], w3["held_s"]
            moved = math.dist((before[0], before[2]), (after[0], after[2]))
            toward = math.dist((before[0], before[2]), (cxm, czm)) - math.dist((after[0], after[2]), (cxm, czm))
            shot2 = screenshot(client_log, shots, request, f"L3-approach-{ang + 1}-end")
            attempts.append({"attempt": ang + 1, "start": before, "end": after, "moved_blocks": round(moved, 1), "closer_by": round(toward, 1), "held_s": round(held, 1), "aim_modes": w3["aim_modes"], "strafes": w3["strafes"], "screenshots": [shot1, shot2]})
            server.cmd(f"forceload remove {px - 32} {pz - 32} {px + 32} {pz + 32}")
            if moved >= 20 and toward >= 15:
                approach_ok = True
                break
        log("L3_approach", "LIVE (surface approach); entry into the piece boxes is SERVER-ONLY", approach_ok,
            {"attempts": attempts, "note": "the structure lies 100+ blocks below the surface with no surface entrance; the final entry below is the L4 route (teleport setup)"})
        # L8 surface directly above the structure
        server.cmd(f"forceload add {cxm - 16} {czm - 16} {cxm + 16} {czm + 16}")
        time.sleep(6)
        server.cmd(f"spreadplayers {cxm} {czm} 0 1 false {PLAYER}")
        time.sleep(4)
        surf = pos(server)
        server.cmd(f"execute as {PLAYER} at @s run tp @s ~ ~ ~ 0 25")
        shot_above = screenshot(client_log, shots, request, "L8-surface-above-structure")

        # L8 saved data: columns above the structure footprint that are open air from the top of the pieces up to the surface heightmap (an "air pillar")
        shafts, columns, deepest = [], 0, 0
        for x in range(lo[0], hi[0] + 1, 2):
            for z in range(lo[2], hi[2] + 1, 2):
                ch = world.chunk(x >> 4, z >> 4)
                hm = (ch.nbt.get("Heightmaps") or {}).get("WORLD_SURFACE") if ch else None
                if hm is None:
                    continue
                columns += 1
                top = hi[1] + 1
                y, run = top, 0
                while y < top + 60 and passable(world.state(x, y, z)):
                    y, run = y + 1, run + 1
                deepest = max(deepest, run)
                if run >= 30:
                    shafts.append([x, z, run])
        log("L8_saved_columns", "SAVED-DATA", len(shafts) == 0, {"columns_sampled": columns, "open_air_columns_30_plus_above_pieces": shafts[:10], "longest_open_run_above_pieces": deepest,
                                                              "note": "checked up to 60 blocks above the highest piece; natural caves can produce air, so a nonzero count needs a look"})

        # L4 traversal: real keyboard along a straight line through three successive connected pieces. Two routes are tried (E->W and S->N through the main chamber).
        by_name = {}
        for i, c in enumerate(children):
            by_name.setdefault(leaf(c), []).append(i)
        main_i = by_name["main_chamber"][0]
        routes = []
        for first, last, axis in (("tunnel_east", "tunnel_west", "x"), ("tunnel_south", "tunnel_north", "z")):
            routes.append((first, last, axis))
        route_results = []
        for first, last, axis in routes:
            fi, li = by_name[first][0], by_name[last][0]
            seq = [fi, main_i, li]
            fb, lb = children[fi]["BB"], children[li]["BB"]
            if axis == "x":
                zc = (fb[2] + fb[5]) // 2
                sx0, sz0, tx, tz = fb[0] + 1.5, zc + 0.5, lb[3] - 0.5, zc + 0.5
            else:
                xc = (fb[0] + fb[3]) // 2
                sx0, sz0, tx, tz = xc + 0.5, fb[2] + 1.5, xc + 0.5, lb[5] - 0.5
            y = fb[1] + 1
            server.cmd(f"execute as {PLAYER} run tp @s {sx0} {y} {sz0} facing {tx} {y} {tz}")
            time.sleep(3)
            legs, entered = [], []
            for n_, pi in enumerate(seq):
                bb = children[pi]["BB"]
                if n_ == 0:
                    entered.append({"piece": leaf(children[pi]), "index": pi, "entered": "start (teleport setup)", "position": pos(server)})
                    shot = screenshot(client_log, shots, request, f"L4-{first}-{n_ + 1}-{leaf(children[pi])}")
                    legs.append({"piece": leaf(children[pi]), "screenshot": shot})
                    continue
                w4 = walk_to(server, ((bb[0] + bb[3]) / 2 + 0.5, (bb[2] + bb[5]) / 2 + 0.5) if pi != li else (tx, tz), 60.0, until=lambda p, bb=bb: in_box(p, bb, -1))
                before, after, held = w4["start"], w4["end"], w4["held_s"]
                ok = in_box(after, bb, -1)
                entered.append({"piece": leaf(children[pi]), "index": pi, "entered": ok, "position": after, "held_s": round(held, 1)})
                shot = screenshot(client_log, shots, request, f"L4-{first}-{n_ + 1}-{leaf(children[pi])}")
                legs.append({"piece": leaf(children[pi]), "entered_by_live_keys": ok, "from": before, "to": after, "held_s": round(held, 1), "aim_modes": w4["aim_modes"], "strafes": w4["strafes"], "screenshot": shot})
                if not ok:
                    break
            route_results.append({"route": f"{first}->main_chamber->{last}", "pieces_in_order_entered": sum(1 for e in entered if e["entered"] is True or e["entered"] == "start (teleport setup)"),
                                  "live_entries": sum(1 for e in entered if e["entered"] is True), "legs": legs})
        best = max(route_results, key=lambda r: r["live_entries"])
        log("L4_traverse", "LIVE", best["live_entries"] >= 2, {"routes": route_results,
            "note": "pass = 3 successive connected pieces: the first by teleport setup, the next two entered by live W-key walking (server-side position inside the next piece box)"})

        # L6 combat with real mouse clicks inside the structure
        mb = children[main_i]["BB"]
        cells = standing_cells(world, mb, ((mb[0] + mb[3]) / 2, mb[1] + 1, (mb[2] + mb[5]) / 2), 12, mb[1])
        combat = None
        for (x, y, z) in cells:
            for fx, fz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if all(passable(world.state(x + fx * k, y, z + fz * k)) and passable(world.state(x + fx * k, y + 1, z + fz * k)) for k in range(1, 5)):
                    combat = (x, y, z, fx, fz)
                    break
            if combat:
                break
        cres: dict = {"position": combat}
        if combat:
            x, y, z, fx, fz = combat
            server.cmd(f"execute as {PLAYER} run tp @s {x + .5} {y} {z + .5} {round(math.degrees(math.atan2(-fx, fz)), 1)} 0")
            time.sleep(3)
            server.cmd(f"execute as {PLAYER} at @s run summon minecraft:zombie ^ ^ ^2.5 {{NoAI:1b,PersistenceRequired:1b,Tags:[\"sg01combat\"]}}")
            time.sleep(2)
            hp0 = server.cmd("data get entity @e[tag=sg01combat,limit=1] Health")
            cres["player_rotation"] = rotation(server)
            cres["player_pos"] = pos(server)
            cres["zombie_pos"] = server.cmd("data get entity @e[tag=sg01combat,limit=1] Pos")[-60:]
            cres["screenshot_before"] = screenshot(client_log, shots, request, "L6-combat-before")
            focus()
            xdo("key", "1")
            hist = [hp0[-40:]]
            rounds = []
            n_ = 0
            for rnd in range(12):
                zp = server.cmd("data get entity @e[tag=sg01combat,limit=1] Pos")
                zm = re.search(r"\[(-?[\d.]+(?:E-?\d+)?)d, (-?[\d.]+(?:E-?\d+)?)d, (-?[\d.]+(?:E-?\d+)?)d\]", zp)
                if not zm:
                    break
                zx, zy, zz = float(zm.group(1)), float(zm.group(2)), float(zm.group(3))
                pp = pos(server)
                dist = math.dist((pp[0], pp[2]), (zx, zz))
                if dist > 2.6:  # natural mobs shoved the player away: close in with the W key before aiming
                    walk_to(server, (zx, zz), 8.0, until=lambda p, zx=zx, zz=zz: math.dist((p[0], p[2]), (zx, zz)) <= 2.0)
                mode = aim(server, zx, zz)
                rounds.append({"round": rnd + 1, "distance_before": round(dist, 2), "aim": mode, "player": pos(server), "rotation": rotation(server)})
                for _c in range(4):
                    xdo("mousedown", "1")
                    time.sleep(0.12)
                    xdo("mouseup", "1")
                    time.sleep(0.8)
                    n_ += 1
                hp = server.cmd("data get entity @e[tag=sg01combat,limit=1] Health")
                hist.append(hp[-40:])
                if "No entity" in hp or "Found no" in hp:
                    break
            cres["rounds"] = rounds
            gone = "Test passed" not in server.cmd("execute if entity @e[tag=sg01combat]")
            cres.update({"health_history": hist, "zombie_dead_after_clicks": gone, "clicks": n_, "weapon": "iron_sword (given by command)", "target": "NoAI zombie summoned 2.5 blocks ahead (SERVER-ONLY setup); aim and attacks are real input"})
            cres["screenshot_after"] = screenshot(client_log, shots, request, "L6-combat-after")
        log("L6_combat", "LIVE", bool(combat and cres.get("zombie_dead_after_clicks")), cres)

        # L7 trial spawner with the real player present, in line of sight of the spawner
        spawners = []
        for cx_ in range(lo[0] >> 4, (hi[0] >> 4) + 1):
            for cz_ in range(lo[2] >> 4, (hi[2] >> 4) + 1):
                ch = world.chunk(cx_, cz_)
                if ch:
                    spawners += [(be["x"], be["y"], be["z"]) for be in ch.nbt.get("block_entities", []) if be.get("id") == "minecraft:trial_spawner"]
        if not spawners:
            log("L7_trial_spawner", "SAVED-DATA", False, "no trial spawner block entity found")
        else:
            sxp, syp, szp = spawners[0]
            tb = next((c["BB"] for c in children if in_box((sxp, syp, szp), c["BB"])), mb)
            spot = None
            for (x, y, z) in standing_cells(world, tb, (sxp, syp, szp), 12, tb[1]):
                if 2.5 <= math.dist((x + .5, y, z + .5), (sxp + .5, syp, szp + .5)) <= 12 and clear_line(world, (x + .5, y + 1.62, z + .5), (sxp + .5, syp + .5, szp + .5)):
                    spot = (x, y, z)
                    break
            l7: dict = {"spawner": [sxp, syp, szp], "player_spot": spot, "line_of_sight": bool(spot)}
            if spot:
                x, y, z = spot
                server.cmd(f"execute as {PLAYER} run tp @s {x + .5} {y} {z + .5} facing {sxp + .5} {syp + .5} {szp + .5}")
                time.sleep(2)
                timeline = []
                last = None
                for _ in range(40):
                    st = next((s for s in SPAWNER_STATES if "Test passed" in server.cmd(f"execute if block {sxp} {syp} {szp} minecraft:trial_spawner[trial_spawner_state={s}]")), "unknown")
                    if st != last:
                        timeline.append({"t_s": _ * 3, "state": st})
                        last = st
                    time.sleep(3)
                data = server.cmd(f"data get block {sxp} {syp} {szp}")
                mobs = server.cmd(f"execute as @e[type=!minecraft:player,distance=..40] run data get entity @s id")
                l7.update({"state_timeline": timeline, "block_entity": data[:600], "nearby_mob_probe": mobs[:200]})
                l7["screenshot"] = screenshot(client_log, shots, request, "L7-trial-spawner")
                left_inactive = any(t["state"] not in ("inactive", "unknown") for t in timeline)
                spawned = bool(re.search(r"total_mobs_spawned|current_mobs", data))
                l7.update({"left_inactive": left_inactive, "mobs_spawned_per_block_entity": spawned})
                log("L7_trial_spawner", "SERVER-ONLY (the live client's player is present; state read with commands)", bool(left_inactive and spawned), l7)
            else:
                log("L7_trial_spawner", "BLOCKED", None, {**l7, "reason": "no standing cell with line of sight to the spawner within 12 blocks"})

        # L9 features: natural geode and monster room, plus the structure vicinity
        region_chunks = [(cx_, cz_) for cx_ in range((cxm >> 4) - 12, (cxm >> 4) + 13) for cz_ in range((czm >> 4) - 12, (czm >> 4) + 13)]
        geodes = find_blocks(world, region_chunks, {"minecraft:budding_amethyst"}, 1)
        spawn_cells = []
        for cx_, cz_ in region_chunks:
            ch = world.chunk(cx_, cz_)
            if ch:
                spawn_cells += [(be["x"], be["y"], be["z"]) for be in ch.nbt.get("block_entities", []) if be.get("id") in ("minecraft:mob_spawner", "minecraft:spawner")]

        def dist_to_pieces(p) -> float:
            return min(max(b[0] - p[0], 0, p[0] - b[3]) ** 2 + max(b[1] - p[1], 0, p[1] - b[4]) ** 2 + max(b[2] - p[2], 0, p[2] - b[5]) ** 2 for b in boxes) ** 0.5

        l9: dict = {"geode_budding_cells_found": len(geodes), "monster_room_spawners": [{"pos": list(s), "distance_to_nearest_piece_box": round(dist_to_pieces(s), 1)} for s in spawn_cells[:6]]}
        server.cmd(f"gamemode spectator {PLAYER}")
        shots9 = []
        if geodes:
            gx, gy, gz, _ = geodes[0]
            vc = view_cell(world, (gx, gy, gz), 2.0, 7.0, 8) or (gx + 3, gy + 2, gz)
            server.cmd(f"tp {PLAYER} {vc[0] + .5} {vc[1]} {vc[2] + .5} facing {gx + .5} {gy + .5} {gz + .5}")
            time.sleep(4)
            l9["geode_camera_cell"] = list(vc)
            l9["geode_distance_to_nearest_piece_box"] = round(dist_to_pieces((gx, gy, gz)), 1)
            shots9.append(screenshot(client_log, shots, request, "L9-natural-geode"))
            l9["geode_position"] = [gx, gy, gz]
        if spawn_cells:
            far = max(spawn_cells, key=dist_to_pieces)
            vc2 = view_cell(world, far, 2.0, 6.0, 7) or (far[0] + 2, far[1] + 1, far[2])
            l9["monster_room_camera_cell"] = list(vc2)
            server.cmd(f"tp {PLAYER} {vc2[0] + .5} {vc2[1]} {vc2[2] + .5} facing {far[0] + .5} {far[1] + .5} {far[2] + .5}")
            time.sleep(4)
            shots9.append(screenshot(client_log, shots, request, "L9-natural-monster-room"))
            l9["monster_room_position"] = list(far)
        server.cmd(f"gamemode survival {PLAYER}")
        l9["screenshots"] = shots9
        log("L9_features", "LIVE (screenshots) + SAVED-DATA", bool(shots9 and all(s["ok"] for s in shots9)), l9)

        # L10 stability
        tick = server.cmd("tick query")
        RESULTS["tick_query"] = tick[:300]
        RESULTS["aim_counts"] = dict(AIM)
        slog = (run_dir / "server.log").read_text(errors="replace")
        keep_up_lines = [ln for ln in slog[server_log_mark:].splitlines() if "Can't keep up" in ln]
        keep_up_after_l2 = [ln for ln in slog[server_log_after_l2:].splitlines() if "Can't keep up" in ln]
        clog = client_log.read_text(errors="replace")
        crash = "Exception in thread" in clog and "Render thread" in clog
        lat = [s["latency_s"] for st in RESULTS["steps"].values() for s in [st["detail"]] if isinstance(s, dict) and "latency_s" in s]
        log("L10_stability", "LIVE", not keep_up_lines and not crash and client.poll() is None,
            {"server_cant_keep_up": keep_up_lines, "server_cant_keep_up_after_L2_setup": keep_up_after_l2, "client_render_thread_exception": crash, "client_alive": client.poll() is None, "tick_query": tick[:200],
             "client_stall_over_5s": "NOT MEASURED (the client log has no per-frame markers; screenshot latencies are recorded per step)", "scenario_duration_s": round(time.time() - scenario_t0)})
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
        try:
            rep = json.loads((OUT / "protection-report.json").read_text())
            RESULTS["protection_report"] = {k: rep.get(k) for k in ("write_guard", "drift_guard", "geode", "monster_room", "contract", "lab")}
        except Exception as e:  # noqa: BLE001
            RESULTS["protection_report"] = f"unavailable: {e}"
        (OUT / "live-results.json").write_text(json.dumps(RESULTS, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
