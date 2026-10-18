"""Isolated placement of the restored NBTs on a real Minecraft server (flat world)."""
from __future__ import annotations

import json
import sys
import time
from collections import Counter

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from tools.stage24c.common import *  # noqa
from tools.stage24c.mcserver import Server, World

FLAT = '{"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:stone","height":3}],"biome":"minecraft:plains"}'
ROT = {"none": 0, "clockwise_90": 90, "180": 180, "counterclockwise_90": 270}


def norm(state):
    """Drop the explicit default waterlogged=false the server adds when it re-saves a block."""
    if state is None or "waterlogged=false" not in state:
        return state
    s = state.replace(",waterlogged=false", "").replace("waterlogged=false,", "").replace("[waterlogged=false]", "")
    return s


def rotate(pos, size, rot):
    x, y, z = pos
    sx, _, sz = size
    # StructureTemplate rotates about the placement origin (pivot 0,0) without re-translating.
    return {0: (x, y, z), 90: (-z, y, x), 180: (-x, y, -z), 270: (z, y, -x)}[rot]


def main(variant="candidate", src_root=None):
    src_root = src_root or S24B
    pack = OUT / "_work/pack"
    import shutil
    shutil.rmtree(pack, ignore_errors=True)
    write_pack(pack, {m: ("s24c", src_root / m / "restored.nbt") for m in MODULES})
    srv = Server(OUT / "_work/placement-server", JAR, JAVA,
                 {"level-type": "minecraft\\:flat", "generator-settings": FLAT, "generate-structures": "false"},
                 datapack=pack).start()
    results = {}
    try:
        print(srv.cmd("datapack list"))
        y0 = -60
        row = 0
        for mi, m in enumerate(MODULES):
            for rname, rdeg in ROT.items():
                x0 = 100 + mi * 80
                z0 = 100 + list(ROT).index(rname) * 80
                srv.cmd(f"forceload add {x0-16} {z0-16} {x0+60} {z0+60}")
                time.sleep(0.3)
                out = srv.cmd(f"place template s24c:{m} {x0} {y0} {z0} {rname}")
                results[(m, rdeg)] = {"origin": [x0, y0, z0], "place_output": out}
        srv.cmd("tick sprint 1200")
        time.sleep(25)
        srv.flush()
        w = World(srv.root / "world/dimensions/minecraft/overworld") if (srv.root / "world/dimensions").exists() else World(srv.root / "world")
        report = {}
        for (m, rdeg), info in results.items():
            root = load_nbt(src_root / m / "restored.nbt")
            size = tuple(int(v) for v in root["size"])
            exp = blocks_of(root)
            ox, oy, oz = info["origin"]
            mism, missing_be, checked = [], [], 0
            for pos, (st, nbt) in exp.items():
                rx, ry, rz = rotate(pos, size, rdeg)
                got = w.block(ox + rx, oy + ry, oz + rz)
                checked += 1
                if rdeg == 0:
                    ok = norm(got) == norm(st)
                else:
                    ok = got is not None and got.split("[")[0] == st.split("[")[0]
                if not ok:
                    mism.append({"pos": pos, "expected": st, "got": got})
                if nbt is not None and w.block_entity(ox + rx, oy + ry, oz + rz) is None:
                    missing_be.append(pos)
            # water containment: every water block present after fluid ticks must be in the NBT's water set
            exp_water = {rotate(p, size, rdeg) for p, (s, _) in exp.items() if s.startswith("minecraft:water")}
            corners = [rotate((cx, 0, cz), size, rdeg) for cx in (0, size[0] - 1) for cz in (0, size[2] - 1)]
            xs, zs = [c[0] for c in corners], [c[2] for c in corners]
            stray = []
            for dx in range(min(xs) - 3, max(xs) + 4):
                for dy in range(-1, size[1] + 3):
                    for dz in range(min(zs) - 3, max(zs) + 4):
                        b = w.block(ox + dx, oy + dy, oz + dz)
                        if b and b.startswith("minecraft:water") and (dx, dy, dz) not in exp_water:
                            stray.append((dx, dy, dz))
            water_now = sum(1 for p in exp_water if (w.block(ox + p[0], oy + p[1], oz + p[2]) or "").startswith("minecraft:water"))
            report[f"{m}@{rdeg}"] = {
                "origin": info["origin"], "rotation": rdeg, "place_output": info["place_output"],
                "blocks_checked": checked, "mismatches": len(mism), "mismatch_list": mism,
                "block_entities_missing": missing_be, "exact_compare": rdeg == 0,
                "expected_water": len(exp_water), "water_present_after_1200_ticks": water_now,
                "stray_water_blocks": len(stray), "stray_water_list": stray,
            }
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "placement").mkdir(exist_ok=True)
        (OUT / f"placement/placement-report-{variant}.json").write_text(json.dumps(
            {"minecraft": "26.1.2", "server_jar_sha1": "97ccd4c0ed3f81bbb7bfacddd1090b0c56f9bc51",
             "world": "flat (bedrock+3 stone, surface y=-60), peaceful, structures off",
             "results": report}, indent=1, default=list))
        for k, v in report.items():
            print(k, "mismatch", v["mismatches"], "noBE", len(v["block_entities_missing"]), "water", v["water_present_after_1200_ticks"], "/", v["expected_water"], "stray", v["stray_water_blocks"], v["place_output"][:60])
    finally:
        srv.stop()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="candidate")
    ap.add_argument("--src", default=None)
    a = ap.parse_args()
    main(a.variant, __import__("pathlib").Path(a.src) if a.src else None)
