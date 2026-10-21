"""Stage 24-I evidence images (headless block-model renders, NOT Minecraft-client screenshots).

* seed 24008 small_ruin_1: Stage 24-H vs Stage 24-I world (same seed, same layout), roof and cutaway at walking height
* the two blocked entrances (seed 24005 medium_ruin_1, seed 24009 large_ruin_1): Stage 24-I vs the entrance
  EXPERIMENT world, with the minimal clearance cells outlined in orange
* roof visualisation: each roofed template with its protected roof cells drawn as glass
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, load_nbt, blocks_of  # noqa: E402
from tools.stage24d.lib import scene_from_blocks, write_scene, run_jobs, BUILD, TITLES  # noqa: E402
from tools.stage24d.render_gallery import font  # noqa: E402
from tools.stage24h import gallery as HG  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"
GAL = D24I / "gallery"
HG.MAN.update({"i24": D24I / "worldgen", "i24x": D24I / "experiment-entrance/worldgen"})


def pair(name, seed, idx, title, legend, views, variants, y_cut=None, highlight=()):
    HG.GAL, HG.D24H = GAL, D24I
    outs = HG.pair(name, seed, idx, title, legend, views, y_cut=y_cut, variants=variants, highlight=highlight)
    return outs


def roof_views():
    roofs = json.loads((D24I / "roof/roof-cells.json").read_text())
    jobs, meta, outs = [], [], []
    for m in MODULES:
        cells = {tuple(e["pos"]) for e in roofs[m]["roof_cells"]}
        if not cells:
            continue
        nbt = load_nbt(D24F / m / "restored.nbt")
        size = [int(v) for v in nbt["size"]]
        blocks = dict(blocks_of(nbt))
        blocks.update({p: "minecraft:orange_stained_glass" for p in cells})
        sp = write_scene(f"24i-roof-{m}", scene_from_blocks(blocks, size))
        for vn, az, el in (("iso", 35, 40), ("top", 0, 89)):
            jobs.append(dict(scene=str(sp), w=760, h=620, az=az, el=el, out=str(BUILD / "png24i" / "roof" / f"{m}-{vn}.png")))
        meta.append((m, len(cells)))
    assert run_jobs(jobs, "24i-roof") == 0
    for m, k in meta:
        im = Image.new("RGB", (1520, 704), (30, 34, 41))
        d = ImageDraw.Draw(im)
        for i, vn in enumerate(("iso", "top")):
            im.paste(Image.open(BUILD / "png24i" / "roof" / f"{m}-{vn}.png").convert("RGB").resize((760, 620)), (i * 760, 58))
        d.text((10, 6), f"{TITLES[m]} — Stage 24-I protected roof cells ({k})", fill=(236, 240, 245), font=font(15, True))
        d.text((10, 26), "orange glass = roof cell protected from block_rot (rottable, directly above a room interior, open above); every other block decays as in vanilla",
               fill=(200, 208, 218), font=font(12))
        d.text((10, 42), "Headless render of the template NBT — NOT a Minecraft-client screenshot", fill=(160, 170, 182), font=font(11))
        out = GAL / f"roof-{m}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "JPEG", quality=85, optimize=True, progressive=True)
        outs.append(out.relative_to(D24I).as_posix())
    return outs


def main():
    index = {"roofs": roof_views(), "cases": []}
    p = HG.piece("i24", 24008, 93)
    t = f"{TITLES['small_ruin_1']} — seed 24008 roof decay / lava case · {p['rotation']}"
    lg = "left: Stage 24-H world (roof decays) · right: Stage 24-I world (roof protected)"
    outs = pair("roof-lava-small_ruin_1", 24008, 93, t, lg, [("iso-a", 45, 32), ("top", 0, 89)], ("h24", "i24"))
    outs += pair("roof-lava-small_ruin_1-cutaway", 24008, 93, t + " · cutaway at walking height", lg,
                 [("cut-iso", 45, 50), ("cut-top", 0, 89)], ("h24", "i24"), y_cut=p["bb"][1] + 2)
    index["cases"].append({"case": "roof-lava-small_ruin_1", "seed": 24008, "piece_index": 93, "images": outs})
    survey = json.loads((D24I / "investigation/h24-entrance-survey.json").read_text())
    for seed, m, idx in ((24005, "medium_ruin_1", 71), (24009, "large_ruin_1", 59)):
        cells = [tuple(c) for r in survey if r["seed"] == seed and r["piece_index"] == idx and r.get("n_cells") for c in r["cells_to_clear"]]
        p = HG.piece("i24", seed, idx)
        t = f"{TITLES[m]} — seed {seed} blocked entrance · {p['rotation']}"
        lg = "left: Stage 24-I world · right: entrance EXPERIMENT world (out-of-box clearance cells) · orange outline = minimal clearance cells"
        outs = pair(f"entrance-{m}", seed, idx, t, lg, [("cut-iso", 45, 50), ("cut-iso-b", 225, 50), ("cut-top", 0, 89)],
                    ("i24", "i24x"), y_cut=p["bb"][1] + 3, highlight=cells)
        index["cases"].append({"case": f"entrance-{m}", "seed": seed, "piece_index": idx, "cells": cells, "images": outs})
    (GAL / "INDEX.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
