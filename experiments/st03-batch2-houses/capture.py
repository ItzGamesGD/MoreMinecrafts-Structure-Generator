"""Real Minecraft 26.3 client screenshots of the house B/C/D batch-2 NBTs (F2 in-game screenshots, no renders).

Starts the pinned 26.3 vanilla server (flat world, offline mode), places the template with `place template`
(strict, rotation none) so the template floor (y=0) is flush with the surrounding grass, launches the unmodified
26.3 client under Xvfb with Mesa lavapipe (Vulkan) and takes the views with xdotool F2 while the server teleports
the player. Needs: pinned server jar, JDK 25, a prepared client dir (client.jar, libraries, assets, classpath.txt),
xvfb-run, xdotool, mesa-vulkan-drivers.
  PYTHONPATH=. python <variant dir>/capture.py \
      --server-jar server.jar --java /path/to/java25 --client-dir client --work work --out screenshots
"""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "out"
ORIGIN_X = {"house_b": 0, "house_c": 80, "house_d": 160}
GROUND = -61  # flat world grass layer; template y=0 floor replaces it
FEET = GROUND + 1  # player standing on the floor/ground top


def views():
    """VIEWS from build.py in this folder: name -> (x, dy, z, yaw, pitch), y = FEET + dy (house at x 0..8, z 0..6)."""
    spec = importlib.util.spec_from_file_location("variant_build", HERE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = {}
    for key, b in mod.BUILDINGS.items():
        for k, (x, dy, z, yaw, pitch) in b["views"].items():
            out[f"{key}_{k}"] = (x + ORIGIN_X[key], FEET + dy, z, yaw, pitch)
    return dict(sorted(out.items(), key=lambda kv: "interior" in kv[0]))  # exteriors first


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
    pack = a.work / "pack"
    files = {"house_b": "st03_house_b", "house_c": "st03_house_c", "house_d": "st03_house_d"}
    for key, f in files.items():
        dest = pack / f"data/experimental/structure/{key}.nbt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((OUT_DIR / f"{f}.nbt").read_bytes())
    (pack / "pack.mcmeta").write_text(
        json.dumps(
            {
                "pack": {
                    "description": "st03 batch2 support",
                    "min_format": [121, 0],
                    "max_format": [121, 0],
                }
            }
        )
    )
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
        ["Xvfb", ":99", "-screen", "0", "1280x720x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    cd = a.client_dir.resolve()
    nat = a.work / "natives"
    nat.mkdir(exist_ok=True)
    cmd = [
        a.java,
        "-Xmx3G",
        "-XX:StackShadowPages=32",
        "--enable-native-access=ALL-UNNAMED",
        "--add-exports",
        "java.base/jdk.internal.misc=ALL-UNNAMED",
        f"-Djava.library.path={nat}/java",
        f"-Djna.tmpdir={nat}/jna",
        f"-Dorg.lwjgl.system.SharedLibraryExtractPath={nat}/lwjgl",
        f"-Dio.netty.native.workdir={nat}/netty",
        "-cp",
        (cd / "classpath.txt").read_text(),
        "net.minecraft.client.main.Main",
        "--username",
        "Builder",
        "--version",
        "26.3",
        "--gameDir",
        str(game),
        "--assetsDir",
        str(cd / "assets"),
        "--assetIndex",
        "34",
        "--uuid",
        "00000000-0000-0000-0000-000000000001",
        "--accessToken",
        "0",
        "--versionType",
        "release",
        "--width",
        "1280",
        "--height",
        "720",
        "--quickPlayMultiplayer",
        "localhost:25599",
    ]
    client_log = (a.work / "client.log").open("w")
    client = subprocess.Popen(
        cmd, env=env, cwd=game, stdout=client_log, stderr=subprocess.STDOUT
    )
    try:
        t0 = time.time()
        while time.time() - t0 < a.wait_join:
            if "Builder" in server.cmd("list") and "0 of a max" not in server.cmd(
                "list"
            ):
                break
            if client.poll() is not None:
                raise SystemExit("client exited: see client.log")
            time.sleep(3)
        else:
            raise SystemExit("client never joined")
        print("joined after", int(time.time() - t0), "s", flush=True)
        for c in (
            "gamerule advance_time false",
            "time set noon",
            "weather clear",
            "gamerule advance_weather false",
        ):
            print(c, "->", server.cmd(c))
        forceload(server, -30, -30, 220, 40)
        time.sleep(3)
        for key, ox in ORIGIN_X.items():
            print(server.cmd(f"place template experimental:{key} {ox} {GROUND} 0 none none 1 0 strict"))
        time.sleep(8)
        xd = lambda *k: subprocess.run(["xdotool", *k], env=env, check=False)
        # focus click while looking at the sky far from the house, so creative mode cannot break a block
        print(server.cmd(f"tp Builder 200 {FEET + 5} 200 0 -90"))
        time.sleep(3)
        xd("mousemove", "640", "360")
        xd("click", "1")
        time.sleep(1)
        xd("key", "F1")
        time.sleep(1)  # hide HUD
        shots = []
        nv_done = [False]
        for name, (x, y, z, yaw, pitch) in views().items():
            if "interior" in name and not nv_done[0]:
                nv_done[0] = True
                print(
                    server.cmd(
                        "effect give Builder minecraft:night_vision 99999 0 true"
                    )
                )
            print(server.cmd(f"tp Builder {x} {y} {z} {yaw} {pitch}"))
            time.sleep(12)  # lavapipe renders slowly; let chunks and light settle
            before = {p.name for p in (game / "screenshots").glob("*.png")}
            xd("key", "F2")
            for _ in range(60):
                new = {p.name for p in (game / "screenshots").glob("*.png")} - before
                if new:
                    break
                time.sleep(1)
            else:
                raise SystemExit(f"no screenshot for {name}")
            f = game / "screenshots" / min(new)
            time.sleep(1)
            out = a.out / f"{name}.png"
            shutil.copyfile(f, out)
            shots.append(
                {
                    "view": name,
                    "tp": [x, y, z, yaw, pitch],
                    "file": out.name,
                    "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                }
            )
            print("shot", name, flush=True)
        (a.out / "capture-info.json").write_text(
            json.dumps(
                {
                    "minecraft": "26.3",
                    "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
                    "server_jar_sha1": hashlib.sha1(
                        a.server_jar.read_bytes()
                    ).hexdigest(),
                    "nbt_sha256": {f: hashlib.sha256((OUT_DIR / f"{f}.nbt").read_bytes()).hexdigest() for f in files.values()},
                    "renderer": "Mesa lavapipe (Vulkan, llvmpipe) under Xvfb 1280x720, in-game F2 screenshots, HUD hidden (F1)",
                    "world": "flat (bedrock/2 dirt/grass), plains, noon, clear; night_vision effect applied from the first interior view on",
                    "placement": f"place template experimental:<key> x={ORIGIN_X} y={GROUND} z=0 rotation none (floor y=0 flush with grass; no terrain correction, no roads)",
                    "shots": shots,
                },
                indent=2,
            )
            + "\n"
        )
    finally:
        client.terminate()
        xvfb.terminate()
        server.stop()


if __name__ == "__main__":
    main()
