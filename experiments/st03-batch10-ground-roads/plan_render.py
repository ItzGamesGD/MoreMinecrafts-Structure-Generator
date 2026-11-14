"""Top-down plan of the MQ design (q=0, 1 cell = 7 px): surface material, decoration (red), mounds (dark green),
other placements (grey boxes, labelled) and entrance cells (yellow). A schematic from the source data, not a render
of the game.

  PYTHONPATH=. python experiments/st03-batch10-ground-roads/plan_render.py <out.png>
"""

import importlib.util
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b10", HERE / "build.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

COL = {"grass_block": (96, 150, 60), "dirt": (120, 85, 55), "coarse_dirt": (110, 80, 55), "moss_block": (80, 120, 50),
       "dirt_path": (160, 130, 80), "gravel": (140, 135, 130), "cobblestone": (115, 115, 115),
       "mossy_cobblestone": (100, 120, 95), "andesite": (150, 150, 150), "stone": (125, 125, 125),
       "stone_bricks": (170, 170, 170), "mossy_stone_bricks": (130, 150, 120), "cracked_stone_bricks": (155, 155, 155),
       "polished_andesite": (175, 175, 175), "packed_mud": (140, 105, 75), "rooted_dirt": (130, 95, 65)}
DECOR = ("barrel", "spruce_log", "hay_block", "spruce_fence", "torch", "stripped_spruce_log")


def main():
    out = Path(sys.argv[1])
    G, info = b.designs()
    s = 7
    im = Image.new("RGB", (112 * s, 112 * s), (40, 40, 40))
    d = ImageDraw.Draw(im)
    top = {}
    for (x, y, z), (blk, _) in G.items():
        if blk in ("short_grass", "fern"):
            continue
        if (x, z) not in top or y > top[(x, z)][0]:
            top[(x, z)] = (y, blk)
    for (x, z), (y, blk) in top.items():
        c = (220, 60, 60) if blk in DECOR else COL.get(blk, (255, 0, 255))
        if y >= 1 and blk == "grass_block":
            c = (60, 110, 40)
        d.rectangle([x * s, z * s, x * s + s - 1, z * s + s - 1], fill=c)
    for k, r in b.footprints().items():
        d.rectangle([r[0] * s, r[1] * s, (r[2] + 1) * s - 1, (r[3] + 1) * s - 1], fill=(60, 60, 80), outline=(0, 0, 0))
        d.text((r[0] * s + 2, r[1] * s + 2), k, fill=(255, 255, 255))
    for v in b.ENTRANCES.values():
        for x, z in v:
            d.rectangle([x * s + 2, z * s + 2, x * s + s - 3, z * s + s - 3], fill=(255, 230, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print(out)


if __name__ == "__main__":
    main()
