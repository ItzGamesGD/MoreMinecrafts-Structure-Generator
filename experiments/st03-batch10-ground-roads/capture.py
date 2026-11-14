"""Real Minecraft 26.3 client screenshots of the ground / road modules MQ-* in the assembled ST-03 (F2 screenshots).

One flat test world (pinned 26.3 server + unmodified 26.3 client, Xvfb / Mesa lavapipe):
  * the whole structure (MQ x4, towers, walls, gate, F01-F20, House A) at q=0 with its box at (0, 0), and the same
    structure turned q=1, 2, 3 (every placement at its manifest origin / rotation) with its box at x=160, 320, 480;
  * a slope site: MQ-SE on test terrain -4..+3 around grade with the footing fill, at (0, 250) (apron and ramp for
    the pictures only).

  PYTHONPATH=. python experiments/st03-batch10-ground-roads/capture.py \\
      --server-jar server.jar --java /path/to/java25 --client-dir client --work work --out screenshots
Env ST03_ONLY=<comma separated view-name prefixes> limits the views; ST03_TAG names the info file.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

from tools.seam01 import assembly as A
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
GROUND = -61
FEET = GROUND + 1
QX = {0: 0, 1: 160, 2: 320, 3: 480}
SLOPE = (0, 250)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CK = _load(HERE / "checks.py", "b10checks")
CAP9 = _load(EXP / "st03-batch9-towers-gate" / "capture.py", "b9capture")
look, SL = CAP9.look, CK.SL


def views():
    v = {
        "ov_01_aerial_from_south_over_gate": look((56, 75, 165), (56, 0, 52)),
        "ov_02_aerial_from_north_west": look((-35, 62, -35), (58, 0, 58)),
        "ov_03_aerial_from_south_east": look((147, 62, 147), (54, 0, 54)),
        "ov_04_high_plan_view": look((56, 150, 70), (56, 0, 56)),
        "rd_01_avenue_from_gate_north": look((56, 3.5, 96), (56, 3, 40)),
        "rd_02_avenue_to_plaza_and_manor": look((56, 6, 60), (56, 6, 20)),
        "rd_03_plaza_from_south_west": look((42, 7, 42), (58, 3, 28)),
        "rd_04_barracks_street_west": look((70, 4, 29), (36, 3, 29)),
        "rd_05_middle_road_east": look((40, 4, 75), (95, 2, 75)),
        "rd_06_south_road_west": look((60, 4, 95), (8, 2, 95)),
        "rd_07_south_road_east": look((52, 4, 95), (99, 2, 95)),
        "rd_08_east_service_lane": look((90, 4, 76), (90, 3, 22)),
        "rd_09_north_west_houses_lane": look((48, 5, 19), (12, 3, 19)),
        "rd_10_north_east_houses_lane": look((64, 5, 19), (104, 3, 19)),
        "rd_11_yard_lane_and_F05": look((38, 5, 70), (32, 3, 40)),
        "rd_12_depot_lane_F04_F08": look((73, 5, 72), (73, 3, 34)),
        "en_01_F01_porch_on_plaza": look((56, 3, 34), (55.5, 2, 25)),
        "en_02_F07_porch_south_road": look((20, 3, 99), (16.5, 2, 90)),
        "en_03_F19_F20_fronts": look((40, 4, 100), (40, 2, 87)),
        "en_04_F10_stable_portal": look((80, 3, 99), (85, 2, 90)),
        "en_05_F13_and_F11_lanes": look((17.5, 2.5, 36), (17.5, 1.5, 29)),
        "en_06_F17_F18_fronts": look((88, 4, 64), (95, 2, 48)),
        "en_07_T-NW_door_lane": look((27, 2.5, 8.5), (13, 1.5, 8.5)),
        "en_08_T-SE_door_lane": look((92, 4, 92), (98, 2, 103)),
        "en_09_F09_front": look((97.5, 2.5, 85), (97.5, 1.5, 75)),
        "dc_01_roadside_decor_south": look((30, 3, 101), (30, 1, 94)),
        "dc_02_roadside_decor_middle": look((60, 3, 82), (66, 1, 76)),
        "dc_03_mounds_and_weeds": look((50, 4, 48), (40, 0, 58)),
    }
    for q in (1, 2, 3):
        ox = QX[q]
        v[f"rot_q{q}_aerial"] = look((ox + 56, 80, 170), (ox + 56, 0, 52))
    p = lambda x, y, z: (SLOPE[0] + x, SL.GT - FEET + y, SLOPE[1] + z)
    v["sl_01_MQ-SE_slope_site_oblique"] = look(p(-14, 14, -14), p(25, 0, 25))
    v["sl_02_MQ-SE_slope_site_low"] = look(p(60, 4, 25), p(25, 1, 25))
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--client-dir", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--wait-join", type=int, default=420)
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    a.out.mkdir(parents=True, exist_ok=True)
    pc = _load(EXP / "st03-placement-check" / "place_check.py", "place_check")
    built = pc.built_modules(perimeter=True, towers=True, ground=True)
    tid = lambda m: "experimental:" + m.replace("-", "_").lower()
    pack = a.work / "pack"
    shutil.rmtree(pack, ignore_errors=True)
    for m, v in built.items():
        dest = pack / f"data/experimental/structure/{m.replace('-', '_').lower()}.nbt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(v["nbt"]).read_bytes())
    (pack / "pack.mcmeta").write_text(json.dumps(
        {"pack": {"description": "st03 batch10 ground roads", "min_format": [121, 0], "max_format": [121, 0]}}))
    vs = views()
    only = os.environ.get("ST03_ONLY")
    if only:
        vs = {k: v for k, v in vs.items() if k.startswith(tuple(only.split(",")))}
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    (server.root / "server.properties").write_text("".join(f"{k}={v}\n" for k, v in {
        **server.props, "server-port": "25599", "gamemode": "creative", "force-gamemode": "true",
        "white-list": "false", "enforce-whitelist": "false", "view-distance": "12"}.items()))
    server.start()
    game = a.work / "gamedir"
    shutil.rmtree(game, ignore_errors=True)
    (game / "screenshots").mkdir(parents=True)
    (game / "options.txt").write_text(
        "renderDistance:12\nguiScale:2\nmusic:0.0\nsoundCategory_master:0.0\nfov:70.0\nfullscreen:false\n")
    env = dict(os.environ, VK_ICD_FILENAMES="/usr/share/vulkan/icd.d/lvp_icd.json", LIBGL_ALWAYS_SOFTWARE="1",
               DISPLAY=":99")
    xvfb = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1280x720x24"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    time.sleep(2)
    cd = a.client_dir.resolve()
    nat = a.work / "natives"
    nat.mkdir(exist_ok=True)
    cmd = [a.java, "-Xmx3G", "-XX:StackShadowPages=32", "--enable-native-access=ALL-UNNAMED",
           "--add-exports", "java.base/jdk.internal.misc=ALL-UNNAMED",
           f"-Djava.library.path={nat}/java", f"-Djna.tmpdir={nat}/jna",
           f"-Dorg.lwjgl.system.SharedLibraryExtractPath={nat}/lwjgl", f"-Dio.netty.native.workdir={nat}/netty",
           "-cp", (cd / "classpath.txt").read_text(), "net.minecraft.client.main.Main",
           "--username", "Builder", "--version", "26.3", "--gameDir", str(game), "--assetsDir", str(cd / "assets"),
           "--assetIndex", "34", "--uuid", "00000000-0000-0000-0000-000000000001", "--accessToken", "0",
           "--versionType", "release", "--width", "1280", "--height", "720", "--quickPlayMultiplayer",
           "localhost:25599"]
    client = subprocess.Popen(cmd, env=env, cwd=game, stdout=(a.work / "client.log").open("w"), stderr=subprocess.STDOUT)
    placed, shots = [], []
    try:
        t0 = time.time()
        while time.time() - t0 < a.wait_join:
            if "Builder" in server.cmd("list") and "0 of a max" not in server.cmd("list"):
                break
            if client.poll() is not None:
                raise SystemExit("client exited: see client.log")
            time.sleep(3)
        else:
            raise SystemExit("client never joined")
        for c in ("gamerule advance_time false", "time set noon", "weather clear", "gamerule advance_weather false",
                  "gamerule random_tick_speed 0"):
            print(c, server.cmd(c), flush=True)
        forceload(server, -64, -64, 640, 330)
        time.sleep(3)
        for q, ax in QX.items():
            for e in A.manifest(q):
                if e["module"] in built:
                    ox, _, oz = e["origin"]
                    r = server.cmd(f"place template {tid(e['module'])} {ax + ox} {GROUND} {oz} {e['rotation']} none 1 0 strict")
                    assert r.startswith("Loaded template"), (q, e["placement"], r)
                    placed.append({"q": q, "placement": e["placement"], "module": e["module"],
                                   "origin": [ax + ox, GROUND, oz], "rotation": e["rotation"]})
        site = dict(CK.SITE, origin=SLOPE)
        CAP9.slope_terrain(server, site, 51, 51, 8)
        r = server.cmd(f"place template {tid('MQ-SE')} {SLOPE[0]} {SL.GT} {SLOPE[1]} none none 1 0 strict")
        assert r.startswith("Loaded template"), r
        CK.CK9.footing_fill(server, site, 51, 51)
        placed.append({"what": "slope site", "module": "MQ-SE", "origin": [SLOPE[0], SL.GT, SLOPE[1]],
                       "terrain": "checks.py SITE profile + capture apron/ramp, footing fill below grade"})
        time.sleep(8)
        xd = lambda *k: subprocess.run(["xdotool", *k], env=env, check=False)
        server.cmd(f"tp Builder 300 {FEET + 5} 300 0 -90")
        time.sleep(3)
        xd("mousemove", "640", "360"); xd("click", "1"); time.sleep(1)
        xd("key", "F1"); time.sleep(1)
        for name, (x, dy, z, yaw, pitch) in vs.items():
            settle = 45 if name.startswith(("ov_", "rot_")) else 12
            y = FEET + dy
            bx, by, bz = math.floor(x), math.floor(y) - 1, math.floor(z)
            server.cmd(f"execute if block {bx} {by} {bz} minecraft:air run setblock {bx} {by} {bz} minecraft:barrier")
            server.cmd(f"tp Builder {x} {y} {z} {yaw} {pitch}")
            time.sleep(settle)
            before = {p.name for p in (game / "screenshots").glob("*.png")}
            xd("key", "F2")
            for _ in range(60):
                new = {p.name for p in (game / "screenshots").glob("*.png")} - before
                if new:
                    break
                time.sleep(0.2)
            else:
                raise SystemExit(f"no screenshot for {name}")
            time.sleep(1)
            out = a.out / f"{name}.png"
            shutil.copyfile(game / "screenshots" / min(new), out)
            shots.append({"view": name, "tp": [x, y, z, yaw, pitch], "file": out.name,
                          "sha256": hashlib.sha256(out.read_bytes()).hexdigest()})
            print("shot", name, flush=True)
        files = ["st03_ground_nw", "st03_ground_ne", "st03_ground_sw", "st03_ground_se"]
        (a.out / ("capture-info-" + (os.environ.get("ST03_TAG") or "all") + ".json")).write_text(json.dumps({
            "minecraft": "26.3",
            "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
            "server_jar_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
            "nbt_sha256": {f: hashlib.sha256((HERE / "out" / f"{f}.nbt").read_bytes()).hexdigest() for f in files},
            "renderer": "Mesa lavapipe (Vulkan, llvmpipe) under Xvfb 1280x720, in-game F2 screenshots, HUD hidden (F1)",
            "world": "flat (bedrock/2 dirt/grass), plains, noon, clear, random ticks off (grass under blocks is not "
                     "converted during the session); raised cameras stand on a barrier block set only into air cells",
            "walls": "batch-8 MW86 / MW31 (the owner-adopted wall F is not swapped in by this batch)",
            "placed": placed, "shots": shots,
        }, indent=2) + "\n")
    finally:
        client.terminate()
        xvfb.terminate()
        server.stop()


if __name__ == "__main__":
    main()
