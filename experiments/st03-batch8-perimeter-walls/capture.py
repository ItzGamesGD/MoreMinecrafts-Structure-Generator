"""Real Minecraft 26.3 client screenshots of the perimeter wall NBTs MW86 / MW31 (in-game F2 screenshots, no renders).

Placed in one flat test world (pinned 26.3 server + unmodified 26.3 client, Xvfb / Mesa lavapipe):
  * isolated copies (rotation none, exterior face to the north) of MW86 at (0, 200) and MW31 at (100, 200);
  * the real q=0 layout: every built ST-03 module (F01-F20 facilities as approved / submitted, unchanged) plus the five
    wall placements at their st03_placements.json origin / rotation. The four tower squares and the gate rectangle are
    NOT built (no stand-in is placed): the pictures show the bare wall ends at those joints;
  * the three slope test sites of slope.py, built with a wider terrain apron and a ramp down to the flat world (only
    for the pictures), then the same strict placement at grade and Q89 footing fill as checks.py.

  PYTHONPATH=. python experiments/st03-batch8-perimeter-walls/capture.py \\
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


SL = _load(HERE / "slope.py", "b8slope")
GT = SL.GT - FEET  # slope-site grade as a camera dy


def look(cam, target):
    """(x, dy, z) camera and (x, dy, z) target -> (x, dy, z, yaw, pitch)."""
    dx, dy, dz = (t - c for t, c in zip(target, cam))
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return (cam[0], cam[1], cam[2], round(yaw, 1), round(pitch, 1))


def iso_views():
    v = {}
    for mid, L in (("MW86", 86), ("MW31", 31)):
        ox, oz = ISO[mid]
        n = mid.lower()
        p = lambda x, y, z: (ox + x, y, oz + z)
        mid_x = L / 2
        far = 62 if L == 86 else 30
        v.update({
            f"{n}_01_exterior_full": look(p(mid_x - L * 0.3, 10, -far * 0.7), p(mid_x, 5, 0)),
            f"{n}_02_exterior_front": look(p(mid_x, 6, -far * 0.8), p(mid_x, 6, 0)),
            f"{n}_03_exterior_close_end": look(p(13, 3.5, -9), p(3, 7, 0)),
            f"{n}_04_exterior_close_middle": look(p(mid_x - 7, 2.5, -8), p(mid_x + 1, 7.5, 0)),
            f"{n}_05_interior_full": look(p(mid_x + L * 0.3, 10, 4 + far * 0.8), p(mid_x, 5, 4)),
            f"{n}_06_interior_close_end": look(p(L - 13, 3, 13), p(L - 4, 5, 4)),
            f"{n}_07_parapet_walk": look(p(L - 2.5, 13.5, 4.5), p(L - 30 if L == 86 else 4, 9.0, 1.5)),
            f"{n}_08_end_section": look(p(L + 9, 7, -6), p(L - 0.5, 5.5, 2.5)),
        })
    return v


def placement_views():
    """Real q=0 layout. W-N x13-98 z0-4, W-E x107-111 z13-98, W-W x0-4 z13-98, W-SW x13-43 / W-SE x68-98 z107-111;
    towers T-* 13x13 at the corners and the gate x44-67 z100-111 are reserved and empty."""
    return {
        "pl_01_W-N_from_outside_north": look((40, 16, -42), (56, 5, 2)),
        "pl_02_W-E_from_outside_east": look((156, 16, 40), (109, 5, 56)),
        "pl_03_W-W_from_outside_west": look((-45, 16, 72), (2, 5, 56)),
        "pl_04_W-SW_W-SE_from_outside_south": look((56, 16, 160), (56, 4, 109)),
        "pl_05_W-N_from_inside": look((70, 20, 42), (56, 5, 2)),
        "pl_06_W-E_W-SE_from_inside": look((70, 22, 70), (109, 5, 100)),
        "jt_01_corner_NW_tower_square": look((-18, 14, -18), (6, 4, 6)),
        "jt_02_corner_NE_tower_square": look((130, 14, -18), (105, 4, 6)),
        "jt_03_corner_SE_tower_square": look((130, 14, 130), (105, 4, 105)),
        "jt_04_corner_SW_tower_square": look((-18, 14, 130), (6, 4, 105)),
        "jt_05_corner_NW_from_inside": look((22, 12, 22), (6, 5, 6)),
        "gt_01_gate_gap_from_outside": look((56, 5, 132), (56, 5, 108)),
        "gt_02_gate_west_end_W-SW": look((52, 3.5, 121), (43.5, 6, 109)),
        "gt_03_gate_east_end_W-SE": look((60, 3.5, 121), (68.5, 6, 109)),
        "gt_04_gate_gap_from_inside": look((56, 9, 88), (56, 5, 110)),
        "ov_01_whole_hq_aerial_south": look((56, 62, 150), (56, 0, 50)),
        "ov_02_whole_hq_aerial_north_west": look((-28, 55, -28), (60, 0, 60)),
        "ov_03_whole_hq_aerial_south_east": look((140, 55, 140), (52, 0, 52)),
    }


def slope_views():
    s1, s2, s3 = (SL.SITES[k]["origin"] for k in ("S1_long_valley", "S2_cross_slope", "S3_undulating"))
    p = lambda o, x, y, z: (o[0] + x, GT + y, o[1] + z)
    return {
        "sl_01_S1_valley_exterior": look(p(s1, 43, 4, -40), p(s1, 43, 2, 0)),
        "sl_02_S1_valley_exterior_close": look(p(s1, 36, -2, -9), p(s1, 43, 0, 0)),
        "sl_03_S1_valley_interior": look(p(s1, 50, 5, 28), p(s1, 43, 1, 4)),
        "sl_04_S2_cross_slope_exterior": look(p(s2, 6, 1, -14), p(s2, 16, 0, 0)),
        "sl_05_S2_cross_slope_profile": look(p(s2, -11, 1, -4), p(s2, 2, -1, 1.5)),
        "sl_06_S3_undulating_exterior": look(p(s3, 10, 3, -15), p(s3, 16, 1, 0)),
        "sl_07_S3_undulating_interior": look(p(s3, 22, 3, 16), p(s3, 14, 1, 4)),
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
    built = pc.built_modules(perimeter=True)
    tid = lambda m: "experimental:" + m.replace("-", "_").lower()
    pack = a.work / "pack"
    shutil.rmtree(pack, ignore_errors=True)
    for m, v in built.items():
        dest = pack / f"data/experimental/structure/{m.replace('-', '_').lower()}.nbt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(v["nbt"]).read_bytes())
    (pack / "pack.mcmeta").write_text(json.dumps(
        {"pack": {"description": "st03 batch8 perimeter walls", "min_format": [121, 0], "max_format": [121, 0]}}))

    views = {**iso_views(), **placement_views(), **slope_views()}
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
        for name, site in SL.SITES.items():
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
        (a.out / ("capture-info-" + (os.environ.get("ST03_TAG") or "all") + ".json")).write_text(json.dumps({
            "minecraft": "26.3",
            "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
            "server_jar_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
            "nbt_sha256": {f: hashlib.sha256((OUT_DIR / f"{f}.nbt").read_bytes()).hexdigest() for f in files},
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
