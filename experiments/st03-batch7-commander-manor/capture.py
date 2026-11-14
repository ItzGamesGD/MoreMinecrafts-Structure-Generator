"""Real Minecraft 26.3 client screenshots of the F01 commander manor NBT (in-game F2 screenshots, no renders).

Placed in one flat test world (pinned 26.3 server + unmodified 26.3 client, Xvfb / Mesa lavapipe):
  * an isolated copy (rotation none) at (0, 200) for elevations, roof and interiors;
  * the real q=0 layout: every built ST-03 module at its st03_placements.json origin/rotation (F01 with the Q63
    17x27x15 size), for context shots with F02/F03, F11-F15 and the W-N wall line.
After the plain views, two views with test entities for scale only (not template content): a NoAI pillager with
40 HP at the recorded commander position in the war room, and an armor stand at the recorded 3F position.

  PYTHONPATH=. python experiments/st03-batch7-commander-manor/capture.py \\
      --server-jar server.jar --java /path/to/java25 --client-dir client --work work --out screenshots
Env ST03_ONLY=<comma separated view-name prefixes> limits the views taken; ST03_TAG names the info file;
ST03_NO_TESTS=1 skips the test-entity views.
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
ISO = {"manor": (0, 200)}


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
    ox, oz = ISO["manor"]
    cx, cz = ox + 8.0, oz + 7.0
    p = lambda a, b, h: (cx + b, h, cz + a)  # a: toward the street (+z), b: east
    t = (cx, 11.0, cz)
    return {
        "f01_01_front": look(p(31, 0, 5.0), (cx, 12.0, cz)),
        "f01_02_front_left": look(p(23, -23, 9.0), t),
        "f01_03_front_right": look(p(23, 23, 9.0), t),
        "f01_04_side_west": look(p(0, -30, 7.0), t),
        "f01_05_side_east": look(p(0, 30, 7.0), t),
        "f01_06_rear": look(p(-31, 0, 5.0), (cx, 12.0, cz)),
        "f01_07_rear_diag": look(p(-23, 23, 10.0), t),
        "f01_08_roof_and_lookout": look(p(16, -12, 30.0), (cx, 19.0, cz)),
        "f01_09_entrance_porch": look((ox + 7.9, 1.2, oz + 23.0), (ox + 7.9, 4.0, oz + 13.0)),
    }


def interior_views():
    ox, oz = ISO["manor"]
    p = lambda x, y, z: (ox + x, y, oz + z)
    return {
        "f01_10_interior_hall_from_door": look(p(7.9, 0.4, 11.4), p(7.9, 4.0, 1.0)),
        "f01_11_interior_chandelier_from_hall": look(p(7.9, 0.2, 11.2), p(7.6, 8.8, 7.5)),
        "f01_12_interior_gallery_west_arm": look(p(2.6, 6.3, 11.3), p(9.0, 7.5, 5.0)),
        "f01_13_interior_war_room": look(p(12.7, 6.4, 4.7), p(6.5, 7.0, 1.5)),
        "f01_14_interior_stair_from_hall": look(p(7.5, 0.5, 10.6), p(12.5, 4.5, 6.5)),
        "f01_15_interior_hall_from_war_room": look(p(7.6, 6.4, 3.3), p(7.6, 3.0, 11.5)),
        "f01_16_interior_3F_bedroom": look(p(12.6, 12.3, 4.5), p(5.5, 13.2, 1.2)),
        "f01_17_interior_3F_study": look(p(12.3, 12.3, 10.6), p(2.0, 13.4, 8.0)),
        "f01_18_interior_attic_to_lookout": look(p(11.4, 18.2, 3.6), p(7.5, 21.6, 12.0)),
        "f01_19_interior_1F_guard_bay": look(p(6.5, 0.3, 9.6), p(1.5, 1.2, 8.5)),
    }


def context_views():
    """Real q=0 layout. F01 x=48..64 z=11..25; F12 x=26..34 / F15 x=76..84 at z=11..17; F02 x=24..36 / F03 x=75..87
    at z=24..34; the W-N wall line z=0..4 (not built)."""
    return {
        "ctx_01_f01_from_central_street": look((56.5, 3.5, 47.5), (56.5, 10, 18)),
        "ctx_02_f01_aerial_south_east": look((79.5, 24, 47.5), (56.5, 6, 18)),
        "ctx_03_f01_f02_f03_from_south": look((56.5, 14, 64.5), (56.5, 6, 26)),
        "ctx_04_f01_with_f12_west": look((37.5, 7, 31.5), (56.5, 9, 17)),
        "ctx_05_f01_with_f15_east": look((74.5, 6, 31.5), (56.5, 9, 17)),
        "ctx_06_north_quarter_aerial": look((56.5, 40, 66.5), (56.5, 0, 20)),
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

    global BUILD
    BUILD = _load(HERE / "build.py", "batch7_build")
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
        {"pack": {"description": "st03 batch7 commander manor", "min_format": [121, 0], "max_format": [121, 0]}}))

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
        shots, tests, state = [], [], {"nv": False}

        def shoot(name, x, dy, z, yaw, pitch, settle=12, barrier=True):
            y = FEET + dy
            want_nv = "interior" in name
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

        if not os.environ.get("ST03_NO_TESTS"):
            # test entities for scale only (not template content): commander stand-in and armor stand
            ox, oz = ISO["manor"]
            for cmd in ("gamerule spawn_mobs false", "gamerule doMobSpawning false", "difficulty easy"):
                server.cmd(cmd)  # monsters cannot be summoned in peaceful; natural spawning stays off
            bd = BUILD.BUILDINGS["manor"]
            cx, cy, cz = bd["commander_spawn"]
            print(server.cmd(f"summon minecraft:pillager {ox + cx} {GROUND + cy} {oz + cz} {{NoAI:1b,PersistenceRequired:1b,"
                             "Silent:1b,Rotation:[0f,0f],attributes:[{id:\"minecraft:max_health\",base:40d}],Health:40f,"
                             "equipment:{mainhand:{id:\"minecraft:crossbow\",count:1}}}}"), flush=True)
            sx, sy, sz = bd["armor_stand"]
            print(server.cmd(f"summon minecraft:armor_stand {ox + sx} {GROUND + sy} {oz + sz} {{Rotation:[90f,0f],"
                             "equipment:{head:{id:\"minecraft:iron_helmet\",count:1},chest:{id:\"minecraft:iron_chestplate\",count:1},"
                             "legs:{id:\"minecraft:iron_leggings\",count:1},feet:{id:\"minecraft:iron_boots\",count:1}}}"), flush=True)
            time.sleep(3)
            p = lambda x, y, z: (ox + x, y, oz + z)
            for name, (x, dy, z, yaw, pitch) in {
                "f01_20_interior_war_room_test_commander": look(p(11.6, 6.4, 4.6), p(7.6, 7.3, 1.5)),
                "f01_21_interior_bedroom_test_armor_stand": look(p(9.0, 12.4, 4.4), p(12.5, 13.0, 2.5)),
            }.items():
                shoot(name, x, dy, z, yaw, pitch)
            server.cmd("kill @e[type=minecraft:pillager]"); server.cmd("kill @e[type=minecraft:armor_stand]")

        files = ["st03_manor"]
        (a.out / ("capture-info-" + (os.environ.get("ST03_TAG") or "all") + ".json")).write_text(json.dumps({
            "minecraft": "26.3",
            "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
            "server_jar_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
            "nbt_sha256": {f: hashlib.sha256((OUT_DIR / f"{f}.nbt").read_bytes()).hexdigest() for f in files},
            "renderer": "Mesa lavapipe (Vulkan, llvmpipe) under Xvfb 1280x720, in-game F2 screenshots, HUD hidden (F1)",
            "world": "flat (bedrock/2 dirt/grass), plains, noon, clear; night_vision only for interior views; difficulty easy with "
                     "natural mob spawning off only for the two test-entity views; raised "
                     "camera positions stand on an invisible barrier block set only into air cells after placement",
            "placed": placed,
            "shots": shots,
            "test_entities": "two views only (f01_20, f01_21): NoAI pillager with 40 HP at the commander position, armor stand at the recorded 3F position",
        }, indent=2) + "\n")
    finally:
        client.terminate()
        xvfb.terminate()
        server.stop()


if __name__ == "__main__":
    main()
