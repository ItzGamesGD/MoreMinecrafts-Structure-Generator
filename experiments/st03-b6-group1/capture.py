"""Real Minecraft 26.3 client screenshots of the six group-1 templates (F2 in-game screenshots, no renders).

Same method as experiments/st03-b5a-house-a/capture.py: pinned 26.3 vanilla server (flat world), `place template`
(strict, rotation none, floor y=0 flush with the grass), unmodified 26.3 client under Xvfb + Mesa lavapipe, xdotool F2.
All six buildings stand 30 blocks apart on one flat world; no neighbours, no terrain correction.
  PYTHONPATH=. python <dir>/capture.py --server-jar server.jar --java java25 --client-dir client --work work --out screenshots
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
GROUND = -61
FEET = GROUND + 1
SIZES = {
    "house_b_f12": (9, 7), "house_b_f15": (9, 7), "house_c_f13": (7, 7), "house_c_f16": (7, 7),
    "house_d": (7, 7), "kitchen": (9, 9), "smithy": (9, 9), "cart_shed": (8, 7),
}  # fmt: skip
ORDER = list(SIZES)
# interior views: (rel x, dy, rel z, yaw, pitch)
INTERIOR = {
    "house_b_f12": [("interior_beds", (6.5, 0, 4.5, 135, 20)), ("interior_work", (1.5, 0, 4.5, -135, 20))],
    "house_b_f15": [("interior_beds", (6.5, 0, 4.5, 135, 20)), ("interior_work", (1.5, 0, 4.5, -135, 20))],
    "house_c_f13": [("interior_bed", (5.5, 0, 4.5, 135, 20)), ("interior_hearth", (1.5, 0, 4.5, -120, 15))],
    "house_c_f16": [("interior_bed", (5.5, 0, 4.5, 135, 20)), ("interior_hearth", (1.5, 0, 4.5, -120, 15))],
    "house_d": [("interior_guard", (5.5, 0, 4.5, 135, 20)), ("interior_door", (1.5, 0, 1.5, -45, 10))],
    "kitchen": [("interior_hearth", (4.5, 0, 6.5, 180, 12)), ("interior_storage", (3.0, 0, 4.5, -90, 12)),
                ("interior_counter", (6.0, 0, 4.5, 90, 12))],
    "smithy": [("interior_forge", (4.5, 0, 6.5, 180, 12)), ("interior_side", (6.5, 0, 5.5, 90, 12))],
    "cart_shed": [("interior_cart", (2.5, 0, 5.5, -135, 15)), ("interior_storage", (5.5, 0, 5.5, 135, 15))],
}


def views(name, ox):
    w, d = SIZES[name]
    cx = w / 2
    ex = [
        ("front", (cx, 3, d + 10.5, 180, 6)),
        ("back", (cx, 3, -10.5, 0, 6)),
        ("west", (-10.5, 3, d / 2, -90, 6)),
        ("east", (w + 9.5, 3, d / 2, 90, 6)),
        ("diag_se", (w + 6.5, 4, d + 7.5, 135, 10)),
        ("diag_nw", (-7.5, 4, -7.5, -45, 10)),
        ("entrance", (cx, 0.5, d + 5.0, 180, 4)),
    ]
    return [(f"{name}_{n}", (ox + x, FEET + dy, z, yaw, pit)) for n, (x, dy, z, yaw, pit) in ex], [
        (f"{name}_{n}", (ox + x, FEET + dy, z, yaw, pit)) for n, (x, dy, z, yaw, pit) in INTERIOR[name]
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--client-dir", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", nargs="*", default=ORDER)
    ap.add_argument("--wait-join", type=int, default=420)
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    a.out.mkdir(parents=True, exist_ok=True)
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    for n in ORDER:
        (pack / f"data/experimental/structure/{n}.nbt").write_bytes((HERE / f"st03_{n}.nbt").read_bytes())
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "st03 group1", "min_format": [121, 0], "max_format": [121, 0]}})
    )
    shutil.copytree(HERE / "datapack/data/moreminecrafts", pack / "data/moreminecrafts", dirs_exist_ok=True)  # empty loot tables
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    server.props["server-port"] = "25599"
    (server.root / "server.properties").write_text(
        "".join(
            f"{k}={v}\n"
            for k, v in {
                **server.props,
                "server-port": "25599",
                "gamemode": "creative",
                "force-gamemode": "true",
                "white-list": "false",
                "enforce-whitelist": "false",
            }.items()
        )
    )
    server.start()
    game = a.work / "gamedir"
    shutil.rmtree(game, ignore_errors=True)
    (game / "screenshots").mkdir(parents=True)
    (game / "options.txt").write_text(
        "renderDistance:8\nguiScale:2\nmusic:0.0\nsoundCategory_master:0.0\nfov:70.0\nfullscreen:false\n"
    )
    env = dict(
        os.environ,
        VK_ICD_FILENAMES="/usr/share/vulkan/icd.d/lvp_icd.json",
        LIBGL_ALWAYS_SOFTWARE="1",
        DISPLAY=":99",
    )
    xvfb = subprocess.Popen(
        ["Xvfb", ":99", "-screen", "0", "1280x720x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    cd = a.client_dir.resolve()
    nat = a.work / "natives"
    nat.mkdir(exist_ok=True)
    cmd = [
        a.java, "-Xmx3G", "-XX:StackShadowPages=32", "--enable-native-access=ALL-UNNAMED",
        "--add-exports", "java.base/jdk.internal.misc=ALL-UNNAMED",
        f"-Djava.library.path={nat}/java", f"-Djna.tmpdir={nat}/jna",
        f"-Dorg.lwjgl.system.SharedLibraryExtractPath={nat}/lwjgl", f"-Dio.netty.native.workdir={nat}/netty",
        "-cp", (cd / "classpath.txt").read_text(), "net.minecraft.client.main.Main",
        "--username", "Builder", "--version", "26.3", "--gameDir", str(game), "--assetsDir", str(cd / "assets"),
        "--assetIndex", "34", "--uuid", "00000000-0000-0000-0000-000000000001", "--accessToken", "0",
        "--versionType", "release", "--width", "1280", "--height", "720", "--quickPlayMultiplayer", "localhost:25599",
    ]  # fmt: skip
    client_log = (a.work / "client.log").open("w")
    client = subprocess.Popen(cmd, env=env, cwd=game, stdout=client_log, stderr=subprocess.STDOUT)
    try:
        t0 = time.time()
        while time.time() - t0 < a.wait_join:
            lst = server.cmd("list")
            if "Builder" in lst and "0 of a max" not in lst:
                break
            if client.poll() is not None:
                raise SystemExit("client exited: see client.log")
            time.sleep(3)
        else:
            raise SystemExit("client never joined")
        print("joined after", int(time.time() - t0), "s", flush=True)
        for c in ("gamerule advance_time false", "time set noon", "weather clear", "gamerule advance_weather false"):
            print(c, "->", server.cmd(c))
        forceload(server, -20, -20, 30 * len(ORDER) + 20, 40)
        time.sleep(3)
        for i, n in enumerate(ORDER):
            print(server.cmd(f"place template experimental:{n} {i * 30} {GROUND} 0 none none 1 0 strict"))
        time.sleep(8)
        xd = lambda *k: subprocess.run(["xdotool", *k], env=env, check=False)
        print(server.cmd(f"tp Builder 400 {FEET + 5} 400 0 -90"))
        time.sleep(3)
        xd("mousemove", "640", "360")
        xd("click", "1")
        time.sleep(1)
        xd("key", "F1")
        time.sleep(1)
        shots = []
        night = False
        for n in a.only:
            ox = ORDER.index(n) * 30
            ext, inte = views(n, ox)
            for name, (x, y, z, yaw, pitch) in ext + inte:
                if "interior" in name and not night:
                    print(server.cmd("effect give Builder minecraft:night_vision 99999 0 true"))
                    night = True
                print(server.cmd(f"tp Builder {x} {y} {z} {yaw} {pitch}"))
                time.sleep(11)
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
                              "sha256": hashlib.sha256(out.read_bytes()).hexdigest()})  # fmt: skip
                print("shot", name, flush=True)
            if night:
                server.cmd("effect clear Builder minecraft:night_vision")
                night = False
        info = {
            "minecraft": "26.3",
            "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
            "server_jar_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
            "nbt_sha256": {n: hashlib.sha256((HERE / f"st03_{n}.nbt").read_bytes()).hexdigest() for n in ORDER},
            "renderer": "Mesa lavapipe (Vulkan, llvmpipe) under Xvfb 1280x720, in-game F2 screenshots, HUD hidden (F1)",
            "world": "flat, plains, noon, clear; night_vision applied for the interior views only",
            "placement": "place template experimental:<name> <30*i> -61 0 none (floor y=0 flush with grass; no terrain correction)",
            "shots": shots,
        }
        prev = a.out / "capture-info.json"
        if prev.exists():  # recapture of changed modules only: keep the other modules' entries
            old = json.loads(prev.read_text())
            keep = [x for x in old["shots"] if not any(x["view"].startswith(n + "_") for n in a.only)]
            info["shots"] = keep + info["shots"]
            info["captured_nbt_sha256"] = {**old.get("captured_nbt_sha256", {}), **{n: info["nbt_sha256"][n] for n in a.only}}
        else:
            info["captured_nbt_sha256"] = {n: info["nbt_sha256"][n] for n in a.only}
        info["current_nbt_sha256"] = info.pop("nbt_sha256")
        (a.out / "capture-info.json").write_text(json.dumps(info, indent=1) + "\n")
    finally:
        client.terminate()
        xvfb.terminate()
        server.stop()


if __name__ == "__main__":
    main()
