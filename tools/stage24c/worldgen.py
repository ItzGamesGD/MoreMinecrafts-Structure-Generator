"""Real Ancient City generation on Minecraft 26.1.2 with the restored NBTs injected as vanilla overrides."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import *  # noqa
from tools.stage24c.mcserver import Server, World

TEMPLATE_PREFIX = "minecraft:ancient_city/structures/"


def make_pack(dest: Path, src_root: Path):
    shutil.rmtree(dest, ignore_errors=True)
    write_pack(dest, {f"ancient_city/structures/{m}": ("minecraft", src_root / m / "restored.nbt") for m in MODULES},
               "Stage 24-C: restored Ancient City modules overriding vanilla NBTs")


def piece_record(p):
    el = p.get("pool_element", {})
    bb = [int(v) for v in p["BB"]]
    extra = {}
    if str(el.get("element_type", "")) == "minecraft:list_pool_element":
        # Stage 24-G: [restored template, protection overlay]; the first element carries the template and jigsaws
        subs = [str(e.get("location", "")) for e in el.get("elements", [])]
        extra = {"list_elements": subs}
        el = {**el, "location": subs[0] if subs else ""}
    return {
        **extra,
        "template": str(el.get("location", "")),
        "element_type": str(el.get("element_type", "")),
        "rotation": str(p.get("rotation", "")),
        "pos": [int(p["PosX"]), int(p["PosY"]), int(p["PosZ"])],
        "bb": bb,
        "ground_level_delta": int(p.get("groundLevelDelta", p.get("ground_level_delta", 0))),
        "junction_count": len(p.get("junctions", [])),
    }


def run(seed: int, variant: str, src_root: Path | None, city_xz=None, radius=128, prebuilt_pack: Path | None = None):
    work = OUT / "_work" / f"wg-{seed}-{variant}"
    pack = None
    if prebuilt_pack is not None and src_root is not None:
        pack = prebuilt_pack
    elif src_root is not None:
        pack = OUT / "_work" / f"pack-{variant}"
        make_pack(pack, src_root)
    srv = Server(work, JAR, JAVA, {"level-seed": str(seed), "generate-structures": "true",
                                   "view-distance": "4", "simulation-distance": "2"}, datapack=pack, heap="3G").start()
    info = {"seed": seed, "variant": variant}
    try:
        if city_xz is None:
            t0 = time.time()
            out = srv.cmd("locate structure minecraft:ancient_city")
            m = re.search(r"\[(-?\d+), ~, (-?\d+)\]", out)
            info["locate_output"] = out
            info["locate_seconds"] = round(time.time() - t0, 1)
            if not m:
                return info
            city_xz = (int(m.group(1)), int(m.group(2)))
        info["city_xz"] = list(city_xz)
        cx, cz = city_xz
        x0, z0 = cx - radius, cz - radius
        srv.cmd(f"forceload add {x0} {z0} {x0 + 2 * radius - 1} {z0 + 2 * radius - 1}")
        t0 = time.time()
        while time.time() - t0 < 900:
            a = srv.cmd(f"execute if loaded {x0} 0 {z0}")
            b = srv.cmd(f"execute if loaded {x0 + 2 * radius - 1} 0 {z0 + 2 * radius - 1}")
            c = srv.cmd(f"execute if loaded {cx} 0 {cz}")
            if all("passed" in s.lower() for s in (a, b, c)):
                break
            time.sleep(3)
        info["gen_seconds"] = round(time.time() - t0, 1)
        srv.cmd("tick sprint 200")
        time.sleep(8)
        srv.flush()
        dim = work / "world/dimensions/minecraft/overworld"
        w = World(dim)
        cities = []
        for name, chx, chz, st in w.structure_starts(((cx - radius) // 16, (cz - radius) // 16, (cx + radius) // 16, (cz + radius) // 16)):
            if "ancient_city" not in name:
                continue
            kids = st.get("Children", st.get("children", []))
            cities.append({"start_chunk": [chx, chz], "pieces": [piece_record(k) for k in kids]})
        info["cities"] = cities
        return info
    finally:
        srv.stop()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--variants", nargs="+", default=["vanilla", "candidate"])
    ap.add_argument("--src", default=None, help="stage-24b style dir holding <module>/restored.nbt")
    ap.add_argument("--pack", default=None, help="prebuilt datapack used for every non-vanilla variant")
    ap.add_argument("--out", default=None, help="directory for manifest-<seed>-<variant>.json (default stage-24c/worldgen)")
    a = ap.parse_args()
    src = Path(a.src) if a.src else S24B
    out = Path(a.out) if a.out else OUT / "worldgen"
    out.mkdir(parents=True, exist_ok=True)
    for seed in a.seeds:
        city = None
        for variant in a.variants:
            path = out / f"manifest-{seed}-{variant}.json"
            info = run(seed, variant, None if variant == "vanilla" else src, city, prebuilt_pack=Path(a.pack) if a.pack else None)
            city = tuple(info["city_xz"]) if "city_xz" in info else None
            path.write_text(json.dumps(info, indent=1))
            n = sum(len(c["pieces"]) for c in info.get("cities", []))
            print(seed, variant, info.get("city_xz"), "pieces", n, info.get("locate_seconds"), info.get("gen_seconds"), flush=True)
            if city is None:
                break


if __name__ == "__main__":
    main()
