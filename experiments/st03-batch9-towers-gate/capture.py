"""Real Minecraft 26.3 client screenshots of the corner tower MT and the gatehouse MG (in-game F2 screenshots, no renders).

One flat test world (pinned 26.3 server + unmodified 26.3 client, Xvfb / Mesa lavapipe):
  * isolated copies, rotation none: MT at (0, 200), MG at (40, 200);
  * rotation rows: MT and MG each placed in all four rotations (none, clockwise_90, 180, counterclockwise_90), MT at
    z 260, MG at z 300, photographed from the same world direction so every turn shows a different face;
  * the real q=0 layout: every built ST-03 module (F01-F20 facilities, House A, the five batch-8 walls) plus the four
    towers and the gate at their st03_placements.json origin / rotation (the ground / road modules MQ-* are not built);
  * the four slope sites of checks.py, with a terrain apron and a ramp down to the flat world (pictures only), the
    same strict placement at grade and the Q89 footing fill as checks.py.

  PYTHONPATH=. python experiments/st03-batch9-towers-gate/capture.py \\
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
ISO = {"MT": (0, 200), "MG": (40, 200)}
ROWS = {"MT": (260, 30), "MG": (300, 40)}  # z of the row, x spacing
TURNS = ("none", "clockwise_90", "180", "counterclockwise_90")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CK = _load(HERE / "checks.py", "b9checks")
SL = CK.SL
GT = SL.GT - FEET  # slope-site grade as a camera dy


def look(cam, target):
    dx, dy, dz = (t - c for t, c in zip(target, cam))
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return (cam[0], cam[1], cam[2], round(yaw, 1), round(pitch, 1))


def row_rect(mid, i):
    z, step = ROWS[mid]
    w, _, d = A.modules()[mid]["size"]
    fw, fd = (w, d) if i % 2 == 0 else (d, w)
    x0 = i * step
    return (x0, z, x0 + fw - 1, z + fd - 1), A.origin_for((x0, z), i, w, d)


def iso_views():
    tx, tz = ISO["MT"]
    t = lambda x, y, z: (tx + x, y, tz + z)
    gx, gz = ISO["MG"]
    g = lambda x, y, z: (gx + x, y, gz + z)
    return {
        # MT: local x=0 / z=0 are the exterior faces, x=12 carries the door
        "mt_01_exterior_corner": look(t(-14, 12, -14), t(6, 11, 6)),
        "mt_02_exterior_face_west": look(t(-22, 8, 6.5), t(0, 11, 6.5)),
        "mt_03_compound_side_door": look(t(30, 9, 22), t(12, 8, 7)),
        "mt_04_compound_corner": look(t(28, 14, 28), t(6, 11, 6)),
        "mt_05_door_close": look(t(17, 2.5, 8.5), t(12, 2, 8.5)),
        "mt_06_shaft_ladder_up": look(t(8.5, 0.0, 8.5), t(3.5, 10, 5.5)),
        "mt_07_lookout_interior": look(t(9.5, 14.0, 9.5), t(2.5, 14.5, 2.5)),
        "mt_08_lookout_from_ladder": look(t(3.5, 13.2, 5.5), t(9, 14.5, 9)),
        "mt_09_roof_and_gaps_close": look(t(-6, 19, 18), t(4, 17, 8)),
        "mt_10_aerial": look(t(-10, 40, 24), t(6, 18, 6)),
        # MG: local z=11 exterior (approach), z=0 compound (checkpoint)
        "mg_01_exterior_approach": look(g(12, 6, 42), g(12, 8, 6)),
        "mg_02_exterior_oblique": look(g(-14, 9, 30), g(12, 8, 6)),
        "mg_03_forecourt_close": look(g(12, 2.5, 20), g(12, 4, 9)),
        "mg_04_compound_side_checkpoint": look(g(12, 7, -24), g(12, 6, 4)),
        "mg_05_checkpoint_close": look(g(3, 2.5, -7), g(12, 2, 3)),
        "mg_06_passage_through": look(g(12, 1.5, -6), g(12, 3, 14)),
        "mg_07_gate_leaves_close": look(g(13.5, 1.5, 2), g(8.5, 3, 6)),
        "mg_08_shaft_ladder": look(g(3.5, 0.5, 5.5), g(3.5, 8, 8.5)),
        "mg_09_room_west": look(g(4.5, 9.0, 7.5), g(20, 10.0, 6)),
        "mg_10_room_east_chest_rack": look(g(13.5, 9.0, 7.5), g(21, 9.5, 5.5)),
        "mg_11_room_openings_to_approach": look(g(12, 9.0, 5.5), g(12, 10.0, 12)),
        "mg_12_battlements_aerial": look(g(-12, 32, -16), g(12, 12, 6)),
    }


def row_views():
    v = {}
    for mid in ("MT", "MG"):
        for i, turn in enumerate(TURNS):
            (x0, z0, x1, z1), _ = row_rect(mid, i)
            cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
            v[f"rot_{mid.lower()}_{i}_{turn}"] = look((cx + 22, 16, cz + 26), (cx, 7, cz))
        z, step = ROWS[mid]
        v[f"rot_{mid.lower()}_row_aerial"] = look((60, 45, z - 40), (60, 0, z + 8))
    return v


def placement_views():
    return {
        "pl_01_T-NW_outside": look((-24, 14, -24), (6, 10, 6)),
        "pl_02_T-NE_outside": look((136, 14, -24), (105, 10, 6)),
        "pl_03_T-SE_outside": look((136, 14, 136), (105, 10, 105)),
        "pl_04_T-SW_outside": look((-24, 14, 136), (6, 10, 105)),
        "pl_05_T-NW_inside_door": look((25, 3, 7.5), (12, 3, 8.5)),
        "pl_06_T-NE_inside_door": look((103.5, 3, 25), (103.5, 3, 12)),
        "pl_07_T-SE_inside_door": look((86, 3, 103.5), (99, 3, 103.5)),
        "pl_08_T-SW_inside_door": look((8.5, 3, 94), (8.5, 3, 99)),
        "pl_09_GATE_outside_approach": look((56, 8, 146), (56, 7, 106)),
        "pl_10_GATE_inside": look((56, 10, 80), (56, 6, 104)),
        "jt_01_W-N_T-NW_joint": look((20, 6, -10), (12, 7, 2)),
        "jt_02_W-W_T-NW_joint": look((-10, 6, 20), (2, 7, 12)),
        "jt_03_W-SW_GATE_joint": look((36, 5, 124), (44, 7, 110)),
        "jt_04_W-SE_GATE_joint": look((76, 5, 124), (67, 7, 110)),
        "jt_05_T-NE_from_wall_top_inside": look((92, 16, 12), (104, 14, 4)),
        "ov_01_whole_hq_aerial_south": look((56, 70, 160), (56, 0, 50)),
        "ov_02_whole_hq_aerial_north_west": look((-30, 60, -30), (60, 0, 60)),
        "ov_03_whole_hq_aerial_south_east": look((142, 60, 142), (52, 0, 52)),
    }


def slope_views():
    v = {}
    for name, site in CK.SITES.items():
        ox, oz = site["origin"]
        w, _, d = A.modules()[site["module"]]["size"]
        p = lambda x, y, z: (ox + x, GT + y, oz + z)
        tag = name.split("_")[0]
        if site["module"] == "MT":
            v[f"sl_{tag}_exterior_corner"] = look(p(-12, 5, -12), p(6, 2, 6))
            v[f"sl_{tag}_compound_side"] = look(p(24, 4, 24), p(6, 2, 6))
        else:
            v[f"sl_{tag}_exterior"] = look(p(w / 2 + 6, 3, d + 20), p(w / 2, 2, d - 1))
            v[f"sl_{tag}_side_profile"] = look(p(-14, 2, d / 2 + 6), p(2, 0, d / 2))
    return v


def slope_terrain(server, site, w, d, h, skirt=7):
    ox, oz = site["origin"]
    m = CK.MARGIN
    for x in range(-m - skirt, w + m + skirt):
        for z in range(-m - skirt, d + m + skirt):
            ax, az = max(-m, min(w + m - 1, x)), max(-m, min(d + m - 1, z))
            cx, cz = max(0, min(w - 1, ax)), max(0, min(d - 1, az))
            t = SL.GT + site["d"](cx, cz) - max(abs(x - ax), abs(z - az))
            if t <= SL.G:
                continue
            if t - 1 > SL.G:
                server.cmd(f"fill {ox + x} {SL.G + 1} {oz + z} {ox + x} {t - 1} {oz + z} minecraft:dirt")
            server.cmd(f"setblock {ox + x} {t} {oz + z} minecraft:grass_block")
            server.cmd(f"fill {ox + x} {t + 1} {oz + z} {ox + x} {SL.GT + h} {oz + z} minecraft:air")


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
    built = pc.built_modules(perimeter=True, towers=True)
    tid = lambda m: "experimental:" + m.replace("-", "_").lower()
    pack = a.work / "pack"
    shutil.rmtree(pack, ignore_errors=True)
    for m, v in built.items():
        dest = pack / f"data/experimental/structure/{m.replace('-', '_').lower()}.nbt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(v["nbt"]).read_bytes())
    (pack / "pack.mcmeta").write_text(json.dumps(
        {"pack": {"description": "st03 batch9 towers gate", "min_format": [121, 0], "max_format": [121, 0]}}))

    views = {**iso_views(), **row_views(), **placement_views(), **slope_views()}
    only = os.environ.get("ST03_ONLY")
    if only:
        views = {k: v for k, v in views.items() if k.startswith(tuple(only.split(",")))}

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
        forceload(server, -64, -64, 220, 520)
        time.sleep(3)

        def put(mid, ox, y, oz, rot, what, **extra):
            r = server.cmd(f"place template {tid(mid)} {ox} {y} {oz} {rot} none 1 0 strict")
            assert r.startswith("Loaded template"), (what, r)
            placed.append({"what": what, "module": mid, "origin": [ox, y, oz], "rotation": rot, **extra})

        for mid, (ox, oz) in ISO.items():
            put(mid, ox, GROUND, oz, "none", f"isolated {mid}")
        for mid in ("MT", "MG"):
            for i, turn in enumerate(TURNS):
                rect, (ox, oz) = row_rect(mid, i)
                put(mid, ox, GROUND, oz, turn, f"rotation row {mid} {turn}", footprint=list(rect))
        for name, site in CK.SITES.items():
            mid, (ox, oz) = site["module"], site["origin"]
            w, h, d = A.modules()[mid]["size"]
            slope_terrain(server, site, w, d, h)
            put(mid, ox, SL.GT, oz, "none", name,
                terrain="checks.py site + capture apron/ramp, strict placement at grade, Q89 footing fill")
            CK.footing_fill(server, site, w, d)
        for e in A.manifest(0):
            if e["module"] in built:
                ox, _, oz = e["origin"]
                put(e["module"], ox, GROUND, oz, e["rotation"], e["placement"])
        time.sleep(8)
        xd = lambda *k: subprocess.run(["xdotool", *k], env=env, check=False)
        server.cmd(f"tp Builder 300 {FEET + 5} 300 0 -90")
        time.sleep(3)
        xd("mousemove", "640", "360"); xd("click", "1"); time.sleep(1)
        xd("key", "F1"); time.sleep(1)
        shots = []

        def shoot(name, x, dy, z, yaw, pitch, settle=12):
            if name.startswith(("ov_", "rot_") ) and "aerial" in name:
                settle = 40
            y = FEET + dy
            bx, by, bz = math.floor(x), math.floor(y) - 1, math.floor(z)
            server.cmd(f"execute if block {bx} {by} {bz} minecraft:air run setblock {bx} {by} {bz} minecraft:barrier")
            print(server.cmd(f"tp Builder {x} {y} {z} {yaw} {pitch}"), flush=True)
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

        for name, (x, dy, z, yaw, pitch) in views.items():
            shoot(name, x, dy, z, yaw, pitch)

        files = ["st03_tower", "st03_gatehouse"]
        (a.out / ("capture-info-" + (os.environ.get("ST03_TAG") or "all") + ".json")).write_text(json.dumps({
            "minecraft": "26.3",
            "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
            "server_jar_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
            "nbt_sha256": {f: hashlib.sha256((OUT_DIR / f"{f}.nbt").read_bytes()).hexdigest() for f in files},
            "renderer": "Mesa lavapipe (Vulkan, llvmpipe) under Xvfb 1280x720, in-game F2 screenshots, HUD hidden (F1)",
            "world": "flat (bedrock/2 dirt/grass), plains, noon, clear; slope sites are dirt/grass mounds (test terrain, "
                     "not natural worldgen); raised camera positions stand on an invisible barrier block set only into "
                     "air cells after placement",
            "placed": placed,
            "shots": shots,
            "not_built": "ground / road modules MQ-NW/NE/SW/SE (road masterplan not in the repository; owner decision)",
        }, indent=2) + "\n")
    finally:
        client.terminate()
        xvfb.terminate()
        server.stop()


if __name__ == "__main__":
    main()
