"""Real Minecraft 26.3 client screenshots of the F09 prison / F10 ravager stable NBTs (in-game F2 screenshots, no
renders), plus the F09 iron-door button test done in the real client (right-clicks on the buttons).

Two groups are placed in one flat test world (pinned 26.3 server + unmodified 26.3 client, Xvfb / Mesa lavapipe):
  * isolated copies (rotation none) for clean elevations and interiors: F09 at (0, 200), F10 at (40, 200);
  * the real q=0 layout: every built ST-03 module at its st03_placements.json origin/rotation, for context shots with
    the direct neighbours (F08, F18, the east wall; F09, the south strip to the gate).
After the plain views: the button test (each of the six buttons is right-clicked by the player; the door state is read
back from the server before, right after and 3 s after the click), and two views with two ravagers summoned with NoAI
at the recorded pen positions - test entities for scale only, not template content.

  PYTHONPATH=. python experiments/st03-batch6-prison-stable/capture.py \
      --server-jar server.jar --java /path/to/java25 --client-dir client --work work --out screenshots
Env ST03_ONLY=<comma separated view-name prefixes> limits the views taken; ST03_TAG names the info file;
ST03_NO_TESTS=1 skips the button test and the ravager views; ST03_SKIP_BUTTONS=1 skips only the button test.
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
EYE = 1.62
ISO = {"prison": (0, 200), "stable": (40, 200)}
SIZE = {"prison": (11, 13), "stable": (17, 13)}
FRONT = {"prison": (0, 1), "stable": (0, 1)}  # street-face outward direction (x, z)
TAG = {"prison": "f09", "stable": "f10"}


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


def aim(feet, target):
    """Player standing with feet at (x, dy, z), eyes 1.62 higher, looking at target (x, dy, z)."""
    x, dy, z, yaw, pitch = look((feet[0], feet[1] + EYE, feet[2]), target)
    return (x, feet[1], z, yaw, pitch)


def iso_views():
    v = {}
    for key, (ox, oz) in ISO.items():
        t, (fx, fz), (w, d) = TAG[key], FRONT[key], SIZE[key]
        lx, lz = fz, -fx  # viewer's left when facing the street face
        cx, cz = ox + w / 2, oz + d / 2
        r = 16 if key == "prison" else 20
        tgt = (cx, 4.0 if key == "prison" else 5.0, cz)
        at = lambda a, b, h: (cx + fx * a + lx * b, h, cz + fz * a + lz * b)
        v[f"{t}_01_front"] = look(at(r, 0, 3.0), (cx, tgt[1] + 0.2, cz))
        v[f"{t}_02_front_left"] = look(at(r * 0.75, r * 0.75, 5.5), tgt)
        v[f"{t}_03_front_right"] = look(at(r * 0.75, -r * 0.75, 5.5), tgt)
        v[f"{t}_04_side_left"] = look(at(0, r, 3.5), tgt)
        v[f"{t}_05_side_right"] = look(at(0, -r, 3.5), tgt)
        v[f"{t}_06_rear"] = look(at(-r, 0, 3.0), (cx, tgt[1] + 0.2, cz))
        v[f"{t}_07_rear_diag"] = look(at(-r * 0.75, r * 0.75, 6.5), tgt)
    return v


def interior_views():
    a, b = ISO["prison"], ISO["stable"]
    p = lambda o, x, y, z: (o[0] + x, y, o[1] + z)
    return {
        "f09_08_entrance_door": look(p(a, 5.5, 0.6, 17.0), p(a, 5.5, 2.4, 11.5)),
        "f09_09_interior_corridor_from_vestibule": look(p(a, 5.5, 0.4, 9.7), p(a, 5.5, 1.4, 0.5)),
        "f09_10_interior_cell_nw_through_bars": look(p(a, 5.5, 0.5, 4.3), p(a, 2.4, 0.6, 1.6)),
        "f09_11_interior_cell_se_through_bars": look(p(a, 5.5, 0.5, 4.5), p(a, 8.2, 0.5, 6.8)),
        "f09_12_interior_inside_cell_ne": look(p(a, 7.4, 0.4, 3.65), p(a, 8.5, 0.6, 1.0)),
        "f09_13_interior_vestibule_to_door": look(p(a, 5.5, 0.3, 8.6), p(a, 5.5, 1.6, 11.5)),
        "f10_08_entrance_portal": look(p(b, 8.5, 1.0, 20.0), p(b, 8.5, 3.5, 11.5)),
        "f10_09_interior_aisle_from_portal": look(p(b, 8.5, 1.2, 13.3), p(b, 8.5, 2.6, 2.0)),
        "f10_10_interior_west_pen": look(p(b, 8.8, 0.6, 7.0), p(b, 2.5, 1.0, 6.0)),
        "f10_11_interior_east_pen": look(p(b, 8.2, 0.6, 7.0), p(b, 14.5, 1.0, 6.0)),
        "f10_12_interior_aisle_head_store": look(p(b, 8.5, 0.4, 6.0), p(b, 8.0, 1.0, 1.5)),
        "f10_13_interior_nave_beams": look(p(b, 8.5, 0.3, 10.5), p(b, 8.5, 9.0, 3.0)),
        "f10_16_interior_west_pen_from_corner": look(p(b, 2.6, 0.4, 9.4), p(b, 6.5, 1.5, 5.0)),
    }


def context_views():
    """Real q=0 layout. F09 x=92..102 z=62..74 (F18 x=92..100 z=50..58, F08 x=75..87 z=53..67, W-E wall x>=107);
    F10 x=77..93 z=79..91 (south strip z=92..106 to the gate x=44..67)."""
    return {
        "ctx_01_f09_from_south": look((98.5, 3.5, 88.5), (97.5, 4, 68)),
        "ctx_02_f09_f10_aerial_se": look((108.5, 19, 101.5), (89, 2, 76)),
        "ctx_03_f10_from_south_strip": look((85.5, 3.5, 105.5), (85.5, 5, 85)),
        "ctx_04_f10_f09_from_south_west": look((68.5, 6, 101.5), (88, 4, 80)),
        "ctx_05_f08_f09_lane": look((89.5, 6, 77.5), (89.5, 2, 55)),
        "ctx_06_f10_f08_from_nw": look((68.5, 10, 70.5), (86, 3, 84)),
        "ctx_07_south_east_quarter_aerial": look((62.5, 28, 110.5), (88, 0, 72)),
    }


# F09 button test: (button local pos, door local pos, player feet local pos, label)
BUTTONS = [
    ("front_outside", (4, 2, 12), "south", (5, 11), (5.2, 1.0, 15.9)),  # from 3.9 blocks: the shot shows the door
    ("front_inside", (6, 2, 10), "north", (5, 11), (6.5, 1.0, 9.35)),
    ("cell_nw", (5, 3, 2), "east", (4, 2), (5.5, 1.0, 4.2)),
    ("cell_ne", (5, 3, 3), "west", (6, 3), (5.5, 1.0, 5.2)),
    ("cell_sw", (5, 3, 6), "east", (4, 6), (5.5, 1.0, 8.3)),
    ("cell_se", (5, 3, 7), "west", (6, 7), (5.5, 1.0, 9.2)),
]
FACE = {"south": (0.5, 0.06), "north": (0.5, 0.94), "east": (0.06, 0.5), "west": (0.94, 0.5)}


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
    BUILD = _load(HERE / "build.py", "batch6_build")
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
        {"pack": {"description": "st03 batch6 prison stable", "min_format": [121, 0], "max_format": [121, 0]}}))

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
            # ---- F09 button test in the real client: right-click each button, read the door back from the server
            ox, oz = ISO["prison"]
            server.cmd("effect give Builder minecraft:night_vision 99999 0 true"); state["nv"] = True
            for label, (bx, by, bz), facing, (dx_, dz_), feet in ([] if os.environ.get("ST03_SKIP_BUTTONS") else BUTTONS):
                fx, fz = FACE[facing]
                tgt = (ox + bx + fx, by - 0.5, oz + bz + fz)  # local y -> dy = y - 1
                x, dy, z, yaw, pitch = aim((ox + feet[0], feet[1] - 1, oz + feet[2]), tgt)
                door_at = f"{ox + dx_} {FEET} {oz + dz_}"
                q = lambda: "passed" in server.cmd(f"execute if block {door_at} minecraft:iron_door[open=true]")
                server.cmd(f"tp Builder {x} {FEET + dy} {z} {yaw} {pitch}")
                time.sleep(4)
                before = q()
                xd("click", "3")
                time.sleep(0.25)
                pressed = "passed" in server.cmd(
                    f"execute if block {ox + bx} {FEET + by - 1} {oz + bz} minecraft:stone_button[powered=true]")
                opened = q()
                if label == "front_outside":
                    snap("f09_14_front_door_opened_by_button", [x, FEET + dy, z, yaw, pitch])
                time.sleep(3)
                after = q()
                ok = (not before) and pressed and opened and (not after)
                tests.append({"button": label, "button_local": [bx, by, bz], "door_local": [dx_, 1, dz_],
                              "player_feet_local": list(feet), "door_open_before_click": before,
                              "button_powered_after_click": pressed, "door_open_after_click": opened,
                              "door_open_3s_later": after, "pass": ok})
                print("button", label, tests[-1], flush=True)
            # ---- two ravagers (NoAI test entities, not template content) at the recorded pen positions
            sx, sz = ISO["stable"]
            for cmd in ("gamerule spawn_mobs false", "gamerule doMobSpawning false", "difficulty easy"):
                server.cmd(cmd)  # monsters cannot be summoned in peaceful; natural spawning stays off
            for name, (rx, ry, rz) in BUILD.BUILDINGS["stable"]["ravager_spawns"].items():
                yaw = 90 if rx < 8.5 else -90  # as rendered by the client: faces the aisle
                print(server.cmd(f"summon minecraft:ravager {sx + rx} {FEET} {sz + rz} "
                                 f"{{NoAI:1b,PersistenceRequired:1b,Silent:1b,Rotation:[{yaw}f,0f]}}"), flush=True)
            time.sleep(3)
            for name, (x, dy, z, yaw, pitch) in {
                "f10_14_interior_west_pen_test_ravager": look((sx + 9.3, 1.6, sz + 6.5), (sx + 3.0, 1.0, sz + 7.0)),
                "f10_15_interior_east_pen_test_ravager": look((sx + 7.7, 1.6, sz + 6.5), (sx + 14.0, 1.0, sz + 7.0)),
            }.items():
                shoot(name, x, dy, z, yaw, pitch)
            server.cmd("kill @e[type=minecraft:ravager]")

        files = ["st03_prison", "st03_stable"]
        (a.out / ("capture-info-" + (os.environ.get("ST03_TAG") or "all") + ".json")).write_text(json.dumps({
            "minecraft": "26.3",
            "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
            "server_jar_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
            "nbt_sha256": {f: hashlib.sha256((OUT_DIR / f"{f}.nbt").read_bytes()).hexdigest() for f in files},
            "renderer": "Mesa lavapipe (Vulkan, llvmpipe) under Xvfb 1280x720, in-game F2 screenshots, HUD hidden (F1)",
            "world": "flat (bedrock/2 dirt/grass), plains, noon, clear; night_vision only for interior views; difficulty easy with "
                     "natural mob spawning off only for the two NoAI test-ravager views; raised "
                     "camera positions stand on an invisible barrier block set only into air cells after placement",
            "placed": placed,
            "shots": shots,
            "f09_button_test": {"skipped": bool(os.environ.get("ST03_SKIP_BUTTONS")), "method": "player right-click (xdotool mouse button 3) in the real client on each "
                                          "stone button; iron door state read back with execute if block",
                                "results": tests, "pass": bool(tests) and all(t["pass"] for t in tests)},
        }, indent=2) + "\n")
    finally:
        client.terminate()
        xvfb.terminate()
        server.stop()


if __name__ == "__main__":
    main()
