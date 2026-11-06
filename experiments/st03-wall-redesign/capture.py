"""Real Minecraft 26.3 client screenshots of ONE wall design prototype (A, B or C) - in-game F2 screenshots.

One flat test world per design (pinned 26.3 server + unmodified 26.3 client, Xvfb / Mesa lavapipe):
  * isolated copies (rotation none, exterior face to the north): MW86 at (0, 200), MW31 at (100, 200);
  * the real q=0 layout: every built ST-03 facility (unchanged) plus the five wall placements with this design's
    NBTs; tower squares and the gate rectangle stay empty;
  * the batch-8 slope site S1 (test terrain) with the Q89 footing fill under this design's MW86.

  PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/capture.py --design a \\
      --server-jar server.jar --java /path/to/java25 --client-dir client --work work --out screenshots
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
from tools.structure_export.live import _template_cells
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
OUT_DIR = HERE / "out"
GROUND = -61
FEET = GROUND + 1
ISO = {"MW86": (0, 200), "MW31": (100, 200)}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SL = _load(EXP / "st03-batch8-perimeter-walls" / "slope.py", "b8slope")
GT = SL.GT - FEET  # slope-site grade as a camera dy


def look(cam, target):
    """(x, dy, z) camera and (x, dy, z) target -> (x, dy, z, yaw, pitch)."""
    dx, dy, dz = (t - c for t, c in zip(target, cam))
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return (cam[0], cam[1], cam[2], round(yaw, 1), round(pitch, 1))


def views(d):
    v = {}
    p8 = lambda x, y, z: (ISO["MW86"][0] + x, y, ISO["MW86"][1] + z)
    p3 = lambda x, y, z: (ISO["MW31"][0] + x, y, ISO["MW31"][1] + z)
    s1 = SL.SITES["S1_long_valley"]["origin"]
    ps = lambda x, y, z: (s1[0] + x, GT + y, s1[1] + z)
    v.update({
        "mw86_01_front": look(p8(43, 7, -40), p8(43, 6, 0)),
        "mw86_02_oblique_exterior": look(p8(-12, 9, -26), p8(30, 5, 0)),
        "mw86_03_raking_exterior": look(p8(-5, 4.5, -6.5), p8(28, 6.5, 0)),
        "mw86_04_side_end": look(p8(-10, 7, -9), p8(1, 6, 2.5)),
        "mw86_05_top_aerial": look(p8(43, 30, 26), p8(43, 8, 2)),
        "mw86_06_oblique_interior": look(p8(70, 9, 24), p8(48, 5, 4)),
        "mw86_07_detail_exterior": look(p8(15, 4, -8), p8(9, 7, 0)),
        "mw86_08_detail_interior": look(p8(13, 3.5, 11), p8(7, 6, 4)),
        "mw86_09_detail_wall_top": look(p8(20, 13.5, 6.5), p8(36, 9.5, 0.5)),
        "mw31_01_front": look(p3(15.5, 6, -22), p3(15.5, 6, 0)),
        "mw31_02_oblique_exterior": look(p3(-8, 7, -14), p3(16, 5, 0)),
        "mw31_03_oblique_interior": look(p3(27, 7, 16), p3(12, 5, 4)),
        "ctx_01_hq_aerial": look((56, 62, 150), (56, 0, 50)),
        "ctx_02_gate_south": look((56, 6, 135), (56, 5, 108)),
        "ctx_03_corner_NW_outside": look((-14, 10, -14), (10, 5, 10)),
        "ctx_04_W-E_inside": look((88, 14, 66), (109, 6, 40)),
        "sl_01_S1_footing_close": look(ps(36, -2, -9), ps(43, 0, 0)),
    })
    return {f"{d}_{k}": val for k, val in v.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--client-dir", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--wait-join", type=int, default=420)
    ap.add_argument("--design", required=True, choices=["a", "b", "c", "b2"])
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    a.out.mkdir(parents=True, exist_ok=True)

    pc = _load(EXP / "st03-placement-check" / "place_check.py", "place_check")
    built = pc.built_modules(perimeter=True, perimeter_dir=HERE / "out" / a.design)
    tid = lambda m: "experimental:" + m.replace("-", "_").lower()
    pack = a.work / "pack"
    shutil.rmtree(pack, ignore_errors=True)
    for m, v in built.items():
        dest = pack / f"data/experimental/structure/{m.replace('-', '_').lower()}.nbt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(v["nbt"]).read_bytes())
    (pack / "pack.mcmeta").write_text(json.dumps(
        {"pack": {"description": "st03 wall redesign prototype", "min_format": [121, 0], "max_format": [121, 0]}}))

    views = globals()["views"](a.design)
    only = os.environ.get("ST03_ONLY")
    if only:
        views = {k: v for k, v in views.items() if k.startswith(tuple(only.split(",")))}

    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    (server.root / "server.properties").write_text("".join(f"{k}={v}\n" for k, v in {
        **server.props, "server-port": "25599", "gamemode": "creative", "force-gamemode": "true",
        "white-list": "false", "enforce-whitelist": "false",
        "view-distance": "12"}.items()))  # the default test-server 6 chunks cut off the far side of the aerial views
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
    client_log = (a.work / "client.log").open("w")
    client = subprocess.Popen(cmd, env=env, cwd=game, stdout=client_log, stderr=subprocess.STDOUT)
    placed = []
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
        print("joined after", int(time.time() - t0), "s", flush=True)
        for c in ("gamerule advance_time false", "time set noon", "weather clear", "gamerule advance_weather false"):
            server.cmd(c)
        forceload(server, -64, -64, 200, 420)
        time.sleep(3)
        for key, (ox, oz) in ISO.items():
            r = server.cmd(f"place template {tid(key)} {ox} {GROUND} {oz} none none 1 0 strict")
            assert r.startswith("Loaded template"), (key, r)
            placed.append({"what": key, "origin": [ox, GROUND, oz], "rotation": "none"})
        for name, site in [("S1_long_valley", SL.SITES["S1_long_valley"])]:
            mid, (ox, oz) = site["module"], site["origin"]
            L = A.modules()[mid]["size"][0]
            SL.build_terrain(server, site, L, mx=8, z0=-12, z1=16, skirt=7)
            r = server.cmd(f"place template {tid(mid)} {ox} {SL.GT} {oz} none none 1 0 strict")
            assert r.startswith("Loaded template"), (name, r)
            SL.footing_fill(server, site, _template_cells(built[mid]["nbt"]), L)
            placed.append({"what": name, "module": mid, "origin": [ox, SL.GT, oz], "rotation": "none",
                           "terrain": "slope.py site + capture apron/ramp, Q89 footing fill"})
        for e in A.manifest(0):
            if e["module"] in built:
                ox, _, oz = e["origin"]
                r = server.cmd(f"place template {tid(e['module'])} {ox} {GROUND} {oz} {e['rotation']} none 1 0 strict")
                assert r.startswith("Loaded template"), (e["placement"], r)
                placed.append({"what": e["placement"], "module": e["module"], "origin": [ox, GROUND, oz],
                               "rotation": e["rotation"]})
        time.sleep(8)
        xd = lambda *k: subprocess.run(["xdotool", *k], env=env, check=False)
        server.cmd(f"tp Builder 300 {FEET + 5} 300 0 -90")
        time.sleep(3)
        xd("mousemove", "640", "360"); xd("click", "1"); time.sleep(1)
        xd("key", "F1"); time.sleep(1)
        shots, tests, state = [], [], {"nv": False}

        def shoot(name, x, dy, z, yaw, pitch, settle=12, barrier=True):
            if name.startswith("ov_"):
                settle = 40  # high aerial views: let the client finish meshing every chunk of the compound
            y = FEET + dy
            want_nv = False
            if want_nv != state["nv"]:
                server.cmd("effect give Builder minecraft:night_vision 99999 0 true" if want_nv
                           else "effect clear Builder minecraft:night_vision")
                state["nv"] = want_nv
            if barrier:
                bx, by, bz = math.floor(x), math.floor(y) - 1, math.floor(z)
                server.cmd(f"execute if block {bx} {by} {bz} minecraft:air run setblock {bx} {by} {bz} minecraft:barrier")
            print(server.cmd(f"tp Builder {x} {y} {z} {yaw} {pitch}"), flush=True)
            time.sleep(settle)
            return snap(name, [x, y, z, yaw, pitch])

        def snap(name, tp):
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
            shots.append({"view": name, "tp": tp, "file": out.name,
                          "sha256": hashlib.sha256(out.read_bytes()).hexdigest()})
            print("shot", name, flush=True)

        for name, (x, dy, z, yaw, pitch) in views.items():
            shoot(name, x, dy, z, yaw, pitch)

        files = ["st03_wall_86", "st03_wall_31"]
        OUT = HERE / "out" / a.design
        (a.out / ("capture-info-" + (os.environ.get("ST03_TAG") or a.design) + ".json")).write_text(json.dumps({
            "minecraft": "26.3",
            "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
            "server_jar_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
            "design": a.design.upper(),
            "nbt_sha256": {f: hashlib.sha256((OUT / f"{f}.nbt").read_bytes()).hexdigest() for f in files},
            "renderer": "Mesa lavapipe (Vulkan, llvmpipe) under Xvfb 1280x720, in-game F2 screenshots, HUD hidden (F1)",
            "world": "flat (bedrock/2 dirt/grass), plains, noon, clear; slope sites are dirt/grass mounds built by slope.py "
                     "(test terrain, not natural worldgen); raised camera positions stand on an invisible barrier block "
                     "set only into air cells after placement",
            "placed": placed,
            "shots": shots,
            "not_built": "towers T-NW/T-NE/T-SE/T-SW and the gatehouse GATE: reserved areas left empty, no stand-in",
        }, indent=2) + "\n")
    finally:
        client.terminate()
        xvfb.terminate()
        server.stop()


if __name__ == "__main__":
    main()
