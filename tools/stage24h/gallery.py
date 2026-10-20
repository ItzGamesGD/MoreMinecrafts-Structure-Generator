"""Stage 24-H evidence images (headless block-model renders, NOT Minecraft-client screenshots).

* before/after: the same generated piece read back from the Stage 24-G and Stage 24-H sweep worlds (same seed, same
  layout), full view + interior cutaways, for the rooms the sweep found obstructed
* mask visualisation: each template with its clearance mask drawn as stained glass by class
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, OUT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24d.lib import scene_from_blocks, write_scene, run_jobs, BUILD, TITLES  # noqa: E402
from tools.stage24d.render_gallery import font  # noqa: E402
from tools.stage24h.mask import CLEARED  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
GAL = D24H / "gallery"
MAN = {"g24": ROOT / "artifacts/ancient-city-restoration/stage-24g/worldgen", "h24": D24H / "worldgen",
       "f24": ROOT / "artifacts/ancient-city-restoration/stage-24f/worldgen"}
SKIP = ("minecraft:air", "minecraft:cave_air", "minecraft:void_air")
NOTE = ("Headless render of real generated world blocks (26.1.2 server, same seed and layout) with 26.1.2 block models — "
        "NOT a Minecraft-client screenshot")
GLASS = {"room_interior": "minecraft:light_blue_stained_glass", "walkway": "minecraft:lime_stained_glass",
         "paved_walkway": "minecraft:yellow_stained_glass", "step_headroom": "minecraft:orange_stained_glass",
         "interaction_space": "minecraft:magenta_stained_glass", "pool_headroom": "minecraft:cyan_stained_glass",
         "entrance_threshold": "minecraft:red_stained_glass"}


def piece(variant, seed, idx):
    return json.loads((MAN[variant] / f"manifest-{seed}-{variant}.json").read_text())["cities"][0]["pieces"][idx]


def region(variant, seed, bb, y_max=None, pad=1):
    w = World(OUT / f"_work/wg-{seed}-{variant}/world/dimensions/minecraft/overworld")
    x0, y0, z0 = bb[0] - pad, bb[1] - 1, bb[2] - pad
    x1, y1, z1 = bb[3] + pad, (min(bb[4] + pad, y_max) if y_max is not None else bb[4] + pad), bb[5] + pad
    blocks = {}
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                b = w.block(x, y, z)
                if b and b.split("[")[0] not in SKIP:
                    blocks[(x - x0, y - y0, z - z0)] = b
    return blocks, (x0, y0, z0), [x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1]


def pair(name, seed, idx, title, legend, views, y_cut=None, variants=("g24", "h24"), highlight=()):
    bb = piece("h24", seed, idx)["bb"]
    jobs = []
    for v in variants:
        blocks, o, size = region(v, seed, bb, y_max=y_cut)
        sp = write_scene(f"24h-{name}-{v}", scene_from_blocks(blocks, size))
        extras = [{"type": "box", "min": [c[0] - o[0] - 0.04, c[1] - o[1] - 0.04, c[2] - o[2] - 0.04],
                   "max": [c[0] - o[0] + 1.04, c[1] - o[1] + 1.04, c[2] - o[2] + 1.04], "color": "#ff9933"} for c in highlight]
        for vn, az, el in views:
            jobs.append(dict(scene=str(sp), w=760, h=620, az=az, el=el, extras=extras, target=[size[0] / 2, size[1] / 2, size[2] / 2],
                             out=str(BUILD / "png24h" / name / f"{v}-{vn}.png")))
    assert run_jobs(jobs, f"24h-{name}") == 0
    outs = []
    for vn, az, el in views:
        im = Image.new("RGB", (760 * len(variants), 704), (30, 34, 41))
        d = ImageDraw.Draw(im)
        for i, v in enumerate(variants):
            im.paste(Image.open(BUILD / "png24h" / name / f"{v}-{vn}.png").convert("RGB").resize((760, 620)), (i * 760, 58))
        d.text((10, 6), title, fill=(236, 240, 245), font=font(15, True))
        d.text((10, 26), f"seed {seed} · {legend}", fill=(200, 208, 218), font=font(12))
        d.text((10, 42), NOTE, fill=(160, 170, 182), font=font(11))
        out = GAL / f"{name}-{vn}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "JPEG", quality=85, optimize=True, progressive=True)
        outs.append(out.relative_to(D24H).as_posix())
    return outs


def mask_views():
    masks = json.loads((D24H / "mask/interior-masks.json").read_text())
    outs = []
    jobs, meta = [], []
    for m in MODULES:
        nbt = load_nbt(D24F / m / "restored.nbt")
        size = [int(v) for v in nbt["size"]]
        stored = blocks_of(nbt)
        cls = {tuple(p): k for k, v in masks[m]["cleared"].items() for p in v}
        if not cls:
            continue
        ys = sorted({p[1] for p in cls})
        for cut_name, ycut in (("full", size[1] - 1), ("cut", min(ys) + 2)):
            blocks = {p: v for p, v in stored.items() if p[1] <= ycut}
            blocks.update({p: GLASS[k] for p, k in cls.items() if p[1] <= ycut})
            sp = write_scene(f"24h-mask-{m}-{cut_name}", scene_from_blocks(blocks, size))
            for vn, az, el in (("iso", 35, 40), ("top", 0, 89)):
                jobs.append(dict(scene=str(sp), w=760, h=620, az=az, el=el, out=str(BUILD / "png24h" / "mask" / f"{m}-{cut_name}-{vn}.png")))
            meta.append((m, cut_name))
    assert run_jobs(jobs, "24h-mask") == 0
    for m, cut_name in meta:
        im = Image.new("RGB", (1520, 704), (30, 34, 41))
        d = ImageDraw.Draw(im)
        for i, vn in enumerate(("iso", "top")):
            im.paste(Image.open(BUILD / "png24h" / "mask" / f"{m}-{cut_name}-{vn}.png").convert("RGB").resize((760, 620)), (i * 760, 58))
        d.text((10, 6), f"{TITLES[m]} — Stage 24-H clearance mask ({'whole template' if cut_name == 'full' else 'cut 2 blocks above the lowest cleared layer'})",
               fill=(236, 240, 245), font=font(15, True))
        d.text((10, 26), "light blue = room interior · lime = enclosed walkway · yellow = paved walkway · orange = step headroom · magenta = bed/chest top · cyan = pool headroom · red = entrance threshold",
               fill=(200, 208, 218), font=font(12))
        d.text((10, 42), "Headless render of the template NBT with the mask drawn as stained glass — NOT a Minecraft-client screenshot", fill=(160, 170, 182), font=font(11))
        out = GAL / f"mask-{m}-{cut_name}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "JPEG", quality=85, optimize=True, progressive=True)
        outs.append(out.relative_to(D24H).as_posix())
    return outs


CASES = [("buried-medium_ruin_1", 24005, "medium_ruin_1", "buried by dripstone"),
         ("dripstone-large_ruin_1", 24009, "large_ruin_1", "dripstone cluster in the courtyard"),
         ("lava-small_ruin_1", 24008, "small_ruin_1", "lava in the room"),
         ("lava-sauna_1", 24014, "sauna_1", "lava column inside the box")]


def main():
    index = {"masks": mask_views(), "cases": []}
    comp = {r["seed"]: r for r in json.loads((D24H / "worldgen/fgh-comparison.json").read_text())}
    for name, seed, m, what in CASES:
        pcs = [p for p in comp[seed]["pieces"] if p["module"] == m]
        pc = max(pcs, key=lambda p: sum(p["mask_terrain_g24"].values()) + p.get("fluid", {}).get("cells_in_mask", 0))
        idx = pc["piece_index"]
        title = f"{TITLES[m]} — {what} · {pc['rotation']}"
        lg = "left: Stage 24-G world (no clearance) · right: Stage 24-H world (interior clearance)"
        ys = None
        outs = pair(name, seed, idx, title, lg, [("iso-a", 45, 32), ("iso-b", 225, 32)])
        outs += pair(name + "-cutaway", seed, idx, title + " · cutaway at walking height", lg,
                     [("cut-iso", 45, 50), ("cut-top", 0, 89)], y_cut=pc["bb"][1] + 2)
        index["cases"].append({"case": name, "seed": seed, "module": m, "piece_index": idx, "bb": pc["bb"], "images": outs})
        print(name, len(outs), flush=True)
    (GAL / "INDEX.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
