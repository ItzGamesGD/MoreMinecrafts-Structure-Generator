"""Real Minecraft 26.3 client screenshots of the representative wall segment (in-game F2, HUD hidden).

  PYTHONPATH=. python experiments/st03-wall-segment/capture.py --server-jar server.jar --java java25 \\
      --client-dir client --work <dir> --out experiments/st03-wall-segment/screenshots/<stage> [--tag <stage>]

Flat test world, noon, clear (the same lighting and cameras for every stage):
  * the segment alone (rotation none, exterior to the north) at (0, 200);
  * a run of 5 repeats (63 long) at (40, 200), to judge repetition;
  * context: every built ST-03 facility at its q=0 origin and rotation (unchanged NBTs, perimeter walls NOT placed),
    plus the run of 5 standing on the W-N wall line as a preview (x 25..87, z 0..4). Nothing replaces the wall NBTs.
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
SEG = (0, 200)
RUN = (40, 200)
CTX_RUN = (25, 0)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def look(cam, target):
    dx, dy, dz = (t - c for t, c in zip(target, cam))
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return (cam[0], cam[1], cam[2], round(yaw, 1), round(pitch, 1))


def views():
    s = lambda x, y, z: (SEG[0] + x, y, SEG[1] + z)
    r = lambda x, y, z: (RUN[0] + x, y, RUN[1] + z)
    return {
        "01_front": look(s(7.5, 6.5, -21), s(7.5, 6.3, 0)),
        "02_oblique_45": look(s(-9.5, 7, -15.5), s(7.5, 6, 2)),
        "03_side_depth_close": look(s(-3.5, 4.5, -3.5), s(9, 7.5, 1)),
        "04_stone_timber_joint": look(s(5.5, 4, -4.5), s(5.5, 9, 1.5)),
        "05_inside_oblique": look(s(17, 8, 13), s(6, 5, 4)),
        "06_inside_close": look(s(10.5, 4, 8.5), s(6, 6.5, 4)),
        "07_top_parapet": look(s(17, 15, 8), s(4, 10, 1)),
        "08_walk_along": look(s(-0.5, 11.2, 3), s(14, 10.5, 2)),
        "09_run5_front_far": look(r(31.5, 8, -58), r(31.5, 6, 0)),
        "10_run5_oblique": look(r(-11, 9, -24), r(28, 5, 0)),
        "11_context_outside": look((10, 10, -32), (56, 6, 2)),
        "12_context_aerial_inside": look((56, 34, 66), (56, 6, 4)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--client-dir", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tag", default="segment")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    a.out.mkdir(parents=True, exist_ok=True)
    pc = _load(EXP / "st03-placement-check" / "place_check.py", "place_check")
    built = pc.built_modules()  # facilities only, perimeter walls not included
    pack = a.work / "pack"
    shutil.rmtree(pack, ignore_errors=True)
    sdir = pack / "data/experimental/structure"
    sdir.mkdir(parents=True)
    for m, v in built.items():
        (sdir / f"{m.replace('-', '_').lower()}.nbt").write_bytes(Path(v["nbt"]).read_bytes())
    for n in ("st03_wall_segment", "st03_wall_segment_run5"):
        (sdir / f"{n}.nbt").write_bytes((HERE / "out" / f"{n}.nbt").read_bytes())
    (pack / "pack.mcmeta").write_text(json.dumps(
        {"pack": {"description": "st03 wall segment", "min_format": [121, 0], "max_format": [121, 0]}}))
    tid = lambda m: "experimental:" + m.replace("-", "_").lower()
    v = views()
    if a.only:
        v = {k: val for k, val in v.items() if k.startswith(tuple(a.only.split(",")))}

    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    (server.root / "server.properties").write_text("".join(f"{k}={val}\n" for k, val in {
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
    client = subprocess.Popen(cmd, env=env, cwd=game, stdout=(a.work / "client.log").open("w"),
                              stderr=subprocess.STDOUT)
    placed, shots = [], []
    try:
        t0 = time.time()
        while time.time() - t0 < 420:
            if "Builder" in server.cmd("list") and "0 of a max" not in server.cmd("list"):
                break
            if client.poll() is not None:
                raise SystemExit("client exited")
            time.sleep(3)
        else:
            raise SystemExit("client never joined")
        for c in ("gamerule advance_time false", "time set noon", "weather clear", "gamerule advance_weather false"):
            server.cmd(c)
        forceload(server, -64, -64, 200, 300)
        time.sleep(3)
        for name, (ox, oz) in (("st03_wall_segment", SEG), ("st03_wall_segment_run5", RUN),
                               ("st03_wall_segment_run5", CTX_RUN)):
            r = server.cmd(f"place template experimental:{name} {ox} {GROUND} {oz} none none 1 0 strict")
            assert r.startswith("Loaded template"), (name, r)
            placed.append({"what": name, "origin": [ox, GROUND, oz], "rotation": "none"})
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
        for name, (x, dy, z, yaw, pitch) in v.items():
            y = FEET + dy
            bx, by, bz = math.floor(x), math.floor(y) - 1, math.floor(z)
            server.cmd(f"execute if block {bx} {by} {bz} minecraft:air run setblock {bx} {by} {bz} minecraft:barrier")
            server.cmd(f"tp Builder {x} {y} {z} {yaw} {pitch}")
            time.sleep(25 if "aerial" in name or "far" in name or "context" in name else 12)
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
        (a.out / f"capture-info-{a.tag}.json").write_text(json.dumps({
            "minecraft": "26.3",
            "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
            "server_jar_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
            "nbt_sha256": {n: hashlib.sha256((HERE / "out" / f"{n}.nbt").read_bytes()).hexdigest()
                           for n in ("st03_wall_segment", "st03_wall_segment_run5")},
            "renderer": "Mesa lavapipe (Vulkan) under Xvfb 1280x720, in-game F2, HUD hidden",
            "world": "flat, plains, noon, clear; raised cameras stand on a barrier block placed only into air",
            "placed": placed, "shots": shots,
            "note": "perimeter wall NBTs are not placed; the run on the W-N line is a preview only",
        }, indent=2) + "\n")
    finally:
        client.terminate()
        xvfb.terminate()
        server.stop()


if __name__ == "__main__":
    main()
