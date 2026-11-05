"""Real Minecraft 26.3 client screenshots of the F07/F08 warehouse NBTs (in-game F2 screenshots, no renders).

Two groups are placed in one flat test world (pinned 26.3 server + unmodified 26.3 client, Xvfb / Mesa lavapipe):
  * isolated copies (rotation none) for clean elevations and interiors: F07 at (0, 200), F08 at (60, 200);
  * the real q=0 layout: every built ST-03 module (houses, support buildings, F02-F06, F07/F08) at its
    st03_placements.json origin/rotation, for context shots with the direct neighbours (F19, F06; F04, F18, F09).

  PYTHONPATH=. python experiments/st03-batch5-warehouses/capture.py \
      --server-jar server.jar --java /path/to/java25 --client-dir client --work work --out screenshots
Env ST03_ONLY=<comma separated view-name prefixes> limits the views taken; ST03_TAG names the info file.
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
OUT_DIR = HERE / "out"
GROUND = -61
FEET = GROUND + 1
ISO = {"warehouse_a": (0, 200), "warehouse_b": (60, 200)}
SIZE = {"warehouse_a": (15, 13), "warehouse_b": (13, 15)}
FRONT = {"warehouse_a": (0, 1), "warehouse_b": (-1, 0)}  # street-face outward direction (x, z)
TAG = {"warehouse_a": "f07", "warehouse_b": "f08"}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def look(cam, target):
    """(x, dy, z) camera and (x, dy, z) target -> (x, dy, z, yaw, pitch)."""
    dx, dy, dz = (t - c for t, c in zip(target, cam))
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return (cam[0], cam[1], cam[2], round(yaw, 1), round(pitch, 1))


def iso_views():
    v = {}
    for key, (ox, oz) in ISO.items():
        t, (fx, fz), (w, d) = TAG[key], FRONT[key], SIZE[key]
        lx, lz = fz, -fx  # viewer's left when facing the street face
        cx, cz = ox + w / 2, oz + d / 2
        tgt = (cx, 5.0, cz)
        at = lambda a, b, h: (cx + fx * a + lx * b, h, cz + fz * a + lz * b)
        v[f"{t}_01_front"] = look(at(19, 0, 3.5), (cx, 5.2, cz))
        v[f"{t}_02_front_left"] = look(at(14, 14, 6), tgt)
        v[f"{t}_03_front_right"] = look(at(14, -14, 6), tgt)
        v[f"{t}_04_side_left"] = look(at(0, 19, 4), (cx, 5.0, cz))
        v[f"{t}_05_side_right"] = look(at(0, -19, 4), (cx, 5.0, cz))
        v[f"{t}_06_rear"] = look(at(-19, 0, 3.5), (cx, 5.2, cz))
        v[f"{t}_07_rear_diag"] = look(at(-14, 14, 7), tgt)
    return v


def interior_views():
    a, b = ISO["warehouse_a"], ISO["warehouse_b"]
    p = lambda o, x, y, z: (o[0] + x, y, o[1] + z)
    return {
        "f07_08_interior_aisle_from_porch": look(p(a, 7.0, 0.3, 10.5), p(a, 7.0, 2.0, 1.5)),
        "f07_09_interior_west_bay_loft": look(p(a, 9.5, 0.3, 4.5), p(a, 2.0, 2.4, 4.5)),
        "f07_10_interior_east_bay_racks": look(p(a, 4.5, 0.3, 5.5), p(a, 12.0, 2.3, 4.5)),
        "f07_11_interior_from_loft": look(p(a, 3.5, 4.0, 3.6), p(a, 3.0, 4.8, 8.0)),
        "f08_08_interior_from_unloading_door": look(p(b, 1.6, 0.3, 7.5), p(b, 10.5, 2.0, 7.5)),
        "f08_09_interior_bay_and_gallery": look(p(b, 2.6, 0.3, 7.5), p(b, 9.5, 3.5, 7.0)),
        "f08_10_interior_north_stores": look(p(b, 7.5, 0.3, 5.2), p(b, 4.0, 1.0, 2.0)),
        "f08_11_interior_gallery": look(p(b, 9.5, 5.2, 10.6), p(b, 3.5, 4.0, 3.5)),
        "f08_12_south_loft_stair": look(p(b, -6.0, 3.5, 21.0), p(b, 4.0, 4.0, 13.5)),
    }


def context_views():
    """Real q=0 layout. F07 x=10..24 z=79..91 (F19 x=28..36 z=79..87, F06 z<=72); F08 x=75..87 z=53..67 (F04 z<=49,
    F18 x>=92 z=50..58, F09 x>=92 z=62..74)."""
    return {
        "ctx_01_f07_from_south_lane": look((17.5, 3.5, 106.5), (17.5, 5, 85)),
        "ctx_02_f07_with_f19_smithy": look((34.5, 9, 103.5), (21.5, 4, 85)),
        "ctx_03_f07_neighbours_aerial": look((38.5, 17, 102.5), (19.5, 2, 83)),
        "ctx_04_f08_from_street": look((61.5, 4, 60.5), (81, 5, 60)),
        "ctx_05_f04_f08_street_nw": look((63.5, 8, 41.5), (81, 4, 56)),
        "ctx_06_f04_f08_gap_passage": look((68.5, 2.2, 51.5), (91, 2.0, 51.5)),
        "ctx_07_f08_neighbours_aerial": look((66.5, 16, 75.5), (82, 2, 58)),
    }


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
    built = pc.built_modules()
    tid = lambda m: "experimental:" + m.replace("-", "_").lower()
    pack = a.work / "pack"
    shutil.rmtree(pack, ignore_errors=True)
    for m, v in built.items():
        dest = pack / f"data/experimental/structure/{m.replace('-', '_').lower()}.nbt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(v["nbt"]).read_bytes())
    (pack / "pack.mcmeta").write_text(json.dumps(
        {"pack": {"description": "st03 batch5 warehouses", "min_format": [121, 0], "max_format": [121, 0]}}))

    views = {**iso_views(), **interior_views(), **context_views()}
    only = os.environ.get("ST03_ONLY")
    if only:
        views = {k: v for k, v in views.items() if k.startswith(tuple(only.split(",")))}

    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    (server.root / "server.properties").write_text("".join(f"{k}={v}\n" for k, v in {
        **server.props, "server-port": "25599", "gamemode": "creative", "force-gamemode": "true",
        "white-list": "false", "enforce-whitelist": "false"}.items()))
    server.start()
    game = a.work / "gamedir"
    shutil.rmtree(game, ignore_errors=True)
    (game / "screenshots").mkdir(parents=True)
    (game / "options.txt").write_text(
        "renderDistance:10\nguiScale:2\nmusic:0.0\nsoundCategory_master:0.0\nfov:70.0\nfullscreen:false\n")
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
        forceload(server, -48, -48, 200, 240)
        time.sleep(3)
        for key, (ox, oz) in ISO.items():
            r = server.cmd(f"place template experimental:m_{key} {ox} {GROUND} {oz} none none 1 0 strict")
            assert r.startswith("Loaded template"), (key, r)
            placed.append({"what": key, "origin": [ox, GROUND, oz], "rotation": "none"})
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
        shots, nv = [], False
        for name, (x, dy, z, yaw, pitch) in views.items():
            y = FEET + dy
            want_nv = "interior" in name
            if want_nv != nv:
                server.cmd("effect give Builder minecraft:night_vision 99999 0 true" if want_nv
                           else "effect clear Builder minecraft:night_vision")
                nv = want_nv
            bx, by, bz = math.floor(x), math.floor(y) - 1, math.floor(z)
            server.cmd(f"execute if block {bx} {by} {bz} minecraft:air run setblock {bx} {by} {bz} minecraft:barrier")
            print(server.cmd(f"tp Builder {x} {y} {z} {yaw} {pitch}"), flush=True)
            time.sleep(12)
            before = {p.name for p in (game / "screenshots").glob("*.png")}
            xd("key", "F2")
            for _ in range(60):
                new = {p.name for p in (game / "screenshots").glob("*.png")} - before
                if new:
                    break
                time.sleep(1)
            else:
                raise SystemExit(f"no screenshot for {name}")
            time.sleep(1)
            out = a.out / f"{name}.png"
            shutil.copyfile(game / "screenshots" / min(new), out)
            shots.append({"view": name, "tp": [x, y, z, yaw, pitch], "file": out.name,
                          "sha256": hashlib.sha256(out.read_bytes()).hexdigest()})
            print("shot", name, flush=True)
        files = ["st03_warehouse_a", "st03_warehouse_b"]
        (a.out / ("capture-info-" + (os.environ.get("ST03_TAG") or "all") + ".json")).write_text(json.dumps({
            "minecraft": "26.3",
            "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
            "server_jar_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
            "nbt_sha256": {f: hashlib.sha256((OUT_DIR / f"{f}.nbt").read_bytes()).hexdigest() for f in files},
            "renderer": "Mesa lavapipe (Vulkan, llvmpipe) under Xvfb 1280x720, in-game F2 screenshots, HUD hidden (F1)",
            "world": "flat (bedrock/2 dirt/grass), plains, noon, clear; night_vision only for interior views; raised "
                     "camera positions stand on an invisible barrier block set only into air cells after placement",
            "placed": placed,
            "shots": shots,
        }, indent=2) + "\n")
    finally:
        client.terminate()
        xvfb.terminate()
        server.stop()


if __name__ == "__main__":
    main()
