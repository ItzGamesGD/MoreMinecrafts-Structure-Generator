"""V5: pristine restored NBT vs the same piece after real vanilla Ancient City generation (processors, sculk).

`extract` reads blocks of a generated piece from a Stage 24-C worldgen world (needs _work worlds, local only) and stores them under
generated-pieces/*.json (committed, so CI renders without a Minecraft server). `render` builds the comparison images.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24d.lib import *  # noqa
from tools.stage24d.config import CFG
from tools.stage24d.render_gallery import ASSET, font, TAG
from tools.stage24c.worldgen_analyze import rot, rotate_state, classify, ROT
from tools.stage24c.mcserver import World

GEN = D24 / "generated-pieces"
CRIT = ("ladder", "door", "bed", "soul_lantern", "chest", "barrel", "wall", "stairs")


def pick(analysis, m):
    best = None
    for s in analysis:
        for p in s["modules"]:
            if p["module"] != m:
                continue
            lost = sum(v[1] for v in p["critical_blocks_total_lost"].values())
            score = (lost, p["block_replacement"].get("removed_to_air", 0))
            if best is None or score > best[0]:
                best = (score, s["seed"], p)
    return best


def extract():
    analysis = json.loads((ROOT / "artifacts/ancient-city-restoration/stage-24c/worldgen/worldgen-analysis.json").read_text())
    work = ROOT / "artifacts/ancient-city-restoration/stage-24c/_work"
    GEN.mkdir(parents=True, exist_ok=True)
    for m in MODULES:
        score, seed, p = pick(analysis, m)
        w = World(work / f"wg-{seed}-candidate/world/dimensions/minecraft/overworld")
        bb = p["bb"]
        blocks = []
        for x in range(bb[0], bb[3] + 1):
            for y in range(bb[1], bb[4] + 1):
                for z in range(bb[2], bb[5] + 1):
                    st = w.block(x, y, z)
                    if st and st.split("[")[0] not in ("minecraft:air", "minecraft:cave_air"):
                        blocks.append([x - bb[0], y - bb[1], z - bb[2], st])
        (GEN / f"{m}.json").write_text(json.dumps({
            "module": m, "seed": seed, "rotation": p["rotation"], "origin": p["pos"], "bb": bb,
            "city_xz": next(s["city_xz"] for s in analysis if s["seed"] == seed),
            "critical_lost": p["critical_blocks_total_lost"], "block_replacement": p["block_replacement"],
            "blocks": blocks}))
        print(m, seed, p["rotation"], len(blocks), p["critical_blocks_total_lost"])


def render():
    PNG_V = BUILD / "png" / "v5"
    meta = {}
    jobs = []
    for m in MODULES:
        g = json.loads((GEN / f"{m}.json").read_text())
        deg = ROT[g["rotation"]]
        bb, origin = g["bb"], g["origin"]
        root = load_nbt(S24B / m / "restored.nbt")
        pal = [state_str(q) for q in root["palette"]]
        size = [bb[3] - bb[0] + 1, bb[4] - bb[1] + 1, bb[5] - bb[2] + 1]
        gen = {(b[0], b[1], b[2]): b[3] for b in g["blocks"]}
        pristine, lost, cracked = {}, [], 0
        for b in root["blocks"]:
            pos = tuple(int(v) for v in b["pos"])
            st = pal[int(b["state"])]
            nbt = b.get("nbt")
            if st.startswith("minecraft:jigsaw"):
                st = str(nbt["final_state"]) if nbt is not None and "final_state" in nbt else "minecraft:air"
            if st.split("[")[0] in ("minecraft:air", "minecraft:structure_void"):
                continue
            rx, ry, rz = rot(pos, deg)
            wp = (origin[0] + rx - bb[0], origin[1] + ry - bb[1], origin[2] + rz - bb[2])
            pst = rotate_state(st, deg)
            pristine[wp] = pst
            got = gen.get(wp)
            cls = classify(pst, got if got else "minecraft:air")
            name = st.split("[")[0].replace("minecraft:", "")
            if cls == "removed_to_air":
                lost.append((wp, name))
            elif cls == "cracked_by_processor":
                cracked += 1
        ps = write_scene(f"{m}-v5-pristine", scene_from_blocks(pristine, size))
        gs = write_scene(f"{m}-v5-generated", scene_from_blocks(gen, size))
        crit_lost = [(p, n) for p, n in lost if any(c in n for c in CRIT)]
        other_lost = [(p, n) for p, n in lost if not any(c in n for c in CRIT)]
        boxes = [{"type": "box", "min": list(p), "max": [p[0] + 1, p[1] + 1, p[2] + 1], "color": "#ff2d55"} for p, _ in crit_lost]
        boxes += [{"type": "box", "min": list(p), "max": [p[0] + 1, p[1] + 1, p[2] + 1], "color": "#ffb020"} for p, _ in other_lost]
        fa = (CFG[m]["front_az"] - deg) % 360
        for tag, az, el in (("a", (fa - 45) % 360, 36), ("b", (fa + 135) % 360, 36)):
            for which, scn, ex in (("pristine", ps, boxes), ("generated", gs, [])):
                jobs.append(dict(scene=str(scn), w=800, h=760, az=az, el=el, bounds=[[0, 0, 0], size], extras=ex, out=str(PNG_V / f"{m}-{tag}-{which}.png")))
        meta[m] = {"seed": g["seed"], "rotation": g["rotation"], "city_xz": g["city_xz"], "bb": bb, "lost_critical": [f"{n}@{list(p)}" for p, n in crit_lost],
                   "lost_other_blocks": len(other_lost), "cracked": cracked, "sculk_overlay": g["block_replacement"].get("sculk_feature_overlay", 0),
                   "blocks_checked": sum(g["block_replacement"].values())}
    rc = run_jobs(jobs, "v5")
    assert rc == 0
    for m in MODULES:
        for tag in "ab":
            a, b = (Image.open(PNG_V / f"{m}-{tag}-{w}.png").convert("RGB").resize((800, 760), Image.Resampling.LANCZOS) for w in ("pristine", "generated"))
            mt = meta[m]
            sheet = Image.new("RGB", (1600, 860), (30, 34, 41))
            sheet.paste(a, (0, 34)); sheet.paste(b, (800, 34))
            d = ImageDraw.Draw(sheet)
            d.text((12, 8), "PRISTINE restored NBT (red = lost critical block, amber = other block removed by vanilla)", fill=(140, 220, 160), font=font(13, True))
            d.text((812, 8), f"GENERATED in a real Ancient City (seed {mt['seed']}, rotation {mt['rotation']}) after vanilla processors + sculk", fill=(255, 190, 120), font=font(13, True))
            lost_txt = ", ".join(mt["lost_critical"]) if mt["lost_critical"] else "none of the lanterns/doors/beds/ladders/stairs/walls/containers in this piece"
            d.text((12, 800), f"{TITLES[m]} · lost critical: {lost_txt[:150]}", fill=(230, 235, 240), font=font(12))
            d.text((12, 822), f"{mt['cracked']} cracked-brick/tile substitutions, {mt['lost_other_blocks']} other blocks rotted to air, {mt['sculk_overlay']} blocks overlaid by sculk · {TAG}", fill=(160, 170, 182), font=font(11))
            out = ASSET / m / f"v5-degradation-{tag}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            sheet.save(out, "JPEG", quality=84, optimize=True, progressive=True)
    (D24 / "v5-data.json").write_text(json.dumps(meta, indent=1))
    print("v5 done")


if __name__ == "__main__":
    if sys.argv[1:] == ["extract"]:
        extract()
    else:
        render()
