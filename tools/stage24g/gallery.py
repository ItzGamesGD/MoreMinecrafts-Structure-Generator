"""Stage 24-G before/after evidence: the same generated piece read back from the Stage 24-F and the Stage 24-G sweep
worlds (identical seed and layout, processors are position-seeded) rendered with the Stage 24-D block-model renderer.

These are model renders of real generated world blocks, NOT Minecraft-client screenshots (client verification PENDING).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import OUT  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24d.lib import scene_from_blocks, write_scene, run_jobs, BUILD, TITLES  # noqa: E402
from tools.stage24d.render_gallery import font  # noqa: E402
from tools.stage24g.build import D24G  # noqa: E402

D24F_WG = Path(__file__).resolve().parents[2] / "artifacts/ancient-city-restoration/stage-24f/worldgen"
GAL = D24G / "gallery"
SKIP = ("minecraft:air", "minecraft:cave_air", "minecraft:void_air")
NOTE = ("Real generated world blocks (26.1.2 server, same seed and layout) as 26.1.2 block models — NOT client screenshots · "
        "dark teal = vanilla sculk patches, which spread slightly differently in the two worlds")


def manifest(variant, seed):
    d = D24F_WG if variant == "f24" else D24G / "worldgen"
    return json.loads((d / f"manifest-{seed}-{variant}.json").read_text())


def region(variant, seed, bb, pad=1, y_max=None, terrain=True):
    w = World(OUT / f"_work/wg-{seed}-{variant}/world/dimensions/minecraft/overworld")
    x0, y0, z0, x1, y1, z1 = bb[0] - pad, bb[1] - 1, bb[2] - pad, bb[3] + pad, bb[4] + pad, bb[5] + pad
    if y_max is not None:
        y1 = min(y1, y_max)
    blocks = {}
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                inside = bb[0] <= x <= bb[3] and bb[2] <= z <= bb[5] and bb[1] <= y <= bb[4]
                if not terrain and not inside:
                    continue
                b = w.block(x, y, z)
                if b and b.split("[")[0] not in SKIP:
                    blocks[(x - x0, y - y0, z - z0)] = b
    return blocks, (x0, y0, z0), [x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1]


def case_list():
    f = json.loads((D24G / "investigation/f24-functional-survival.json").read_text())
    g = {(r["seed"], tuple(r["world"])): r for r in json.loads((D24G / "worldgen/g24-functional-survival.json").read_text())}
    by = defaultdict(list)
    for r in f:
        if r["status"] != "MISSING":
            continue
        gg = g.get((r["seed"], tuple(r["world"])))
        if not gg or gg["status"] not in ("present", "present_weathered"):
            continue
        by[(r["seed"], r["module"], r["piece_index"])].append(r)
    want = [("entrance", "medium_ruin_1", ("door_support", "door")), ("entrance", "small_ruin_1", ("door_support",)),
            ("ladder", "medium_pillar_1", ("ladder_attach",)), ("ladder", "large_pillar_1", ("ladder_attach",)),
            ("deck", "medium_pillar_1", ("walk_floor", "railing")), ("deck", "large_pillar_1", ("railing", "walk_floor")),
            ("railing", "medium_ruin_2", ("railing", "walk_floor")), ("railing", "sauna_1", ("railing", "walk_floor"))]
    cases = []
    for kind, m, roles in want:
        best = None
        for (seed, mod, idx), rows in sorted(by.items()):
            if mod != m:
                continue
            hit = [r for r in rows if set(r["roles"]) & set(roles)]
            # prefer the seed showing the 24-F door lower half actually gone
            score = len(hit) + (50 if any("door" in r["roles"] for r in hit) else 0)
            if hit and (best is None or score > best[0]):
                best = (score, seed, idx, hit)
        if best:
            cases.append({"kind": kind, "module": m, "seed": best[1], "piece_index": best[2], "cells": [r["world"] for r in best[3]],
                          "roles": sorted({x for r in best[3] for x in r["roles"]})})
    return cases


def piece(variant, seed, idx):
    return manifest(variant, seed)["cities"][0]["pieces"][idx]


LEGEND = "left: Stage 24-F world (red boxes = protected cells missing) · right: Stage 24-G world (green = same cells)"


def render_pair(name, seed, bb, cells, title, views, y_cut=None, terrain=False, scale=None, closeup=False, legend=LEGEND):
    jobs, sizes = [], {}
    for variant in ("f24", "g24"):
        blocks, o, size = region(variant, seed, bb, y_max=y_cut, terrain=terrain)
        sizes[variant] = (o, size)
        sp = write_scene(f"24g-{name}-{variant}", scene_from_blocks(blocks, size))
        extras = [{"type": "box", "min": [c[0] - o[0] - 0.04, c[1] - o[1] - 0.04, c[2] - o[2] - 0.04],
                   "max": [c[0] - o[0] + 1.04, c[1] - o[1] + 1.04, c[2] - o[2] + 1.04], "color": "#ff3355" if variant == "f24" else "#33dd77"}
                  for c in cells]
        for vn, az, el in views:
            j = dict(scene=str(sp), w=760, h=620, az=az, el=el, extras=extras, out=str(BUILD / "png24g" / name / f"{variant}-{vn}.png"),
                     target=[size[0] / 2, size[1] / 2, size[2] / 2])
            if scale:
                j["scale"] = scale
            if closeup:  # frame the protected cells with 3 blocks of context
                lo = [min(c[i] for c in cells) - o[i] - 3 for i in range(3)]
                hi = [max(c[i] for c in cells) - o[i] + 4 for i in range(3)]
                lo[1], hi[1] = max(lo[1], 0), hi[1] + 1
                j["bounds"] = [lo, hi]
                j["target"] = [(lo[i] + hi[i]) / 2 for i in range(3)]
                j["pad"] = False
            jobs.append(j)
    assert run_jobs(jobs, f"24g-{name}") == 0
    outs = []
    for vn, az, el in views:
        im = Image.new("RGB", (1520, 704), (30, 34, 41))
        d = ImageDraw.Draw(im)
        for i, variant in enumerate(("f24", "g24")):
            im.paste(Image.open(BUILD / "png24g" / name / f"{variant}-{vn}.png").convert("RGB").resize((760, 620)), (i * 760, 58))
        d.text((10, 6), title, fill=(236, 240, 245), font=font(15, True))
        d.text((10, 26), f"seed {seed} · {legend}", fill=(200, 208, 218), font=font(12))
        d.text((10, 42), NOTE, fill=(160, 170, 182), font=font(11))
        out = GAL / f"{name}-{vn}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "JPEG", quality=85, optimize=True, progressive=True)
        outs.append(out.relative_to(D24G).as_posix())
    return outs


def main():
    index = []
    for c in case_list():
        p = piece("g24", c["seed"], c["piece_index"])
        assert p == piece("f24", c["seed"], c["piece_index"]) or p["bb"] == piece("f24", c["seed"], c["piece_index"])["bb"]
        bb = p["bb"]
        ymax = max(cc[1] for cc in c["cells"]) + 1
        name = f"{c['kind']}-{c['module']}-{c['seed']}"
        title = f"{TITLES[c['module']]} — {c['kind']} ({', '.join(c['roles'])}) · {p['rotation']}"
        views = [("iso-ne", 45, 32), ("iso-se", 135, 32), ("iso-sw", 225, 32), ("iso-nw", 315, 32)]
        outs = render_pair(name, c["seed"], bb, c["cells"], title, views)
        outs += render_pair(name + "-closeup", c["seed"], bb, c["cells"], title + " · close-up on the protected cells",
                            [("close-ne", 45, 22), ("close-sw", 225, 22)], closeup=True)
        outs += render_pair(name + "-cutaway", c["seed"], bb, c["cells"], title + " · cutaway above the protected cells",
                            [("cut-iso", 35, 50), ("cut-top", 0, 89)], y_cut=ymax)
        index.append({**c, "rotation": p["rotation"], "bb": bb, "images": outs})
        print(name, len(outs), flush=True)
    # decorative decay kept: the same medium_ruin_2 piece, decorative rot cells highlighted in both worlds
    rep = json.loads((D24G / "worldgen/g24-processor-replay.json").read_text())
    for r in rep:
        rows = [x for x in r["losses"] if x["module"] == "large_ruin_1" and x["cause"] == "block_rot"]
        if len(rows) >= 6:
            idx = rows[0]["piece_index"]
            p = piece("g24", r["seed"], idx)
            cells = [x["world"] for x in rows if x["piece_index"] == idx]
            outs = render_pair(f"decay-large_ruin_1-{r['seed']}", r["seed"], p["bb"], cells,
                               f"{TITLES['large_ruin_1']} — decorative decay kept (block_rot cells, identical in both worlds)",
                               [("iso-a", 35, 35), ("iso-b", 215, 35)],
                               legend="left: Stage 24-F world · right: Stage 24-G world · boxes = decorative cells removed by block_rot (identical in both)")
            index.append({"kind": "decorative_decay", "module": "large_ruin_1", "seed": r["seed"], "piece_index": idx, "cells": cells,
                          "images": outs})
            break
    # large_ruin_1 terrain contact, seed 24004 (amethyst-geode shell block in the corner of the taller box)
    m = manifest("g24", 24004)
    for i, p in enumerate(m["cities"][0]["pieces"]):
        if p["template"].endswith("/large_ruin_1"):
            outs = render_pair("terrain-large_ruin_1-24004", 24004, p["bb"], [[-249, -40, -1035]],
                               f"{TITLES['large_ruin_1']} — terrain contact (-249,-40,-1035), surrounding cave terrain included",
                               [("corner", 225, 30), ("corner-high", 225, 60), ("opposite", 45, 30)], terrain=True,
                               legend="left: Stage 24-F world · right: Stage 24-G world · box = the smooth-basalt cell; cave terrain within 1 block of the box shown")
            index.append({"kind": "terrain_contact", "module": "large_ruin_1", "seed": 24004, "piece_index": i,
                          "cells": [[-249, -40, -1035]], "images": outs})
    (GAL / "INDEX.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
