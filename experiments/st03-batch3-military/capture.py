"""Real Minecraft 26.3 client screenshots of the F05 armory + F06 yard NBTs (F2 in-game screenshots, no renders).

Both templates are placed together with their real relative offset from st03_placements.json (F05 x=12..28,
z=39..51; F06 x=12..36, z=52..72 -> yard origin = armory origin + (0, 0, 13)), rotation none, floor y=0 flush with
the flat-world grass. Pinned 26.3 server + unmodified 26.3 client under Xvfb / Mesa lavapipe, xdotool F2.
  PYTHONPATH=. python experiments/st03-batch3-military/capture.py \
      --server-jar server.jar --java /path/to/java25 --client-dir client --work work --out screenshots
Env ST03_ONLY=<comma separated view-name prefixes> limits the views taken.
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
OUT_DIR = HERE / "out"
PLACE = {"armory": ("st03_armory", 0, 0), "yard": ("st03_yard", 0, 13)}
GROUND = -61
FEET = GROUND + 1
# name -> (x, dy, z, yaw, pitch) in the shared frame (armory x 0..16, z 0..12; yard x 0..24, z 13..33)
VIEWS = {
    "f05_01_front_east": (27.5, 3, 6.5, 90, -4),
    "f05_02_front_left_diag_ne": (26.5, 4, -8.5, 51, 2),
    "f05_03_front_right_diag_se": (27.5, 5, 19.5, 128, 6),
    "f05_04_side_south_yard": (8.5, 4, 22.5, 180, 12),
    "f05_05_back_diag_nw": (-9.5, 5, -9.5, -45, 6),
    "f05_06_back_west": (-12.5, 3, 6.5, -90, -2),
    "f06_01_aerial_se": (30.5, 13, 40.5, 136, 30),
    "f06_02_aerial_south": (12.5, 17, 46.5, 180, 40),
    "f06_03_front_gate_east": (33.5, 2, 23.5, 90, 2),
    "f06_04_left_diag_ne": (31.5, 6, 9.5, 55, 12),
    "f06_05_right_diag_se": (31.5, 6, 39.5, 130, 12),
    "f06_06_side_south": (12.5, 5, 41.5, 180, 12),
    "f06_07_archery_range": (3.5, 1, 29.5, -90, 4),
    "f06_08_targets_close": (14.5, 2, 31.5, -115, 6),
    "f06_09_sparring_ring": (16.5, 3, 25.5, 180, 22),
    "f06_10_command_dais": (10.5, 1, 23.5, 90, 0),
    "f06_11_equipment_shelter": (8.5, 1, 18.5, 115, 12),
    "f05_07_interior_hall_axis": (11.6, 1.2, 4.5, 90, 16),
    "f05_08_interior_weapon_wall": (10.5, 0, 6.6, 135, 14),
    "f05_09_interior_strongroom": (7.5, 0, 4.5, 90, 12),
    "f05_10_interior_loggia": (14.6, 0, 10.0, 90, 10),
    "f05_11_loggia_bay_from_yard": (8.5, 0, 16.5, 180, 2),
}
_ONLY = os.environ.get("ST03_ONLY")
if _ONLY:
    VIEWS = {k: v for k, v in VIEWS.items() if k.startswith(tuple(_ONLY.split(",")))}


def views():
    return {k: (x, FEET + dy, z, yaw, pitch) for k, (x, dy, z, yaw, pitch) in VIEWS.items()}


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
    files = {k: v[0] for k, v in PLACE.items()}
    for key, f in files.items():
        dest = pack / f"data/experimental/structure/{key}.nbt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((OUT_DIR / f"{f}.nbt").read_bytes())
    (pack / "pack.mcmeta").write_text(
        json.dumps(
            {
                "pack": {
                    "description": "st03 batch3 military",
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
        forceload(server, -40, -40, 80, 80)
        time.sleep(3)
        for key, (_, ox, oz) in PLACE.items():
            print(server.cmd(f"place template experimental:{key} {ox} {GROUND} {oz} none none 1 0 strict"))
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
            # an invisible barrier under the feet keeps the (non-flying) creative player at the camera height
            bx, by, bz = int(x // 1), int(y // 1) - 1, int(z // 1)
            server.cmd(f"execute if block {bx} {by} {bz} minecraft:air run setblock {bx} {by} {bz} minecraft:barrier")
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
        (a.out / ("capture-info-" + (os.environ.get("ST03_TAG") or "all") + ".json")).write_text(
            json.dumps(
                {
                    "minecraft": "26.3",
                    "client": "unmodified vanilla 26.3 client.jar (sha1 e877b6a07acd633fb3bb475002175cec036e7b87)",
                    "server_jar_sha1": hashlib.sha1(
                        a.server_jar.read_bytes()
                    ).hexdigest(),
                    "nbt_sha256": {f: hashlib.sha256((OUT_DIR / f"{f}.nbt").read_bytes()).hexdigest() for f in files.values()},
                    "renderer": "Mesa lavapipe (Vulkan, llvmpipe) under Xvfb 1280x720, in-game F2 screenshots, HUD hidden (F1)",
                    "world": "flat (bedrock/2 dirt/grass), plains, noon, clear; night_vision effect applied from the first interior view on; raised camera positions stand on an invisible barrier block set only into air cells after placement (never replaces a template block)",
                    "placement": f"place template experimental:<key> at {PLACE} y={GROUND} rotation none (real F05/F06 relative offset; floor y=0 flush with grass; no terrain correction, no roads)",
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
