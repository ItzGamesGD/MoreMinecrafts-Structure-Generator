"""Labelled contact sheets from the capture screenshots (no image content is altered, only scaled and tiled).
Sheets are made from view-name prefixes, so every screenshot of a group is included.

  python experiments/st03-batch10-ground-roads/sheet.py <screenshots dir> <out dir>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SHEETS = {  # name: (view-name prefixes, columns)
    "overview": (("ov_",), 2),
    "rotations": (("rot_",), 3),
    "roads": (("rd_",), 4),
    "entrances": (("en_",), 3),
    "decor_slope": (("dc_", "sl_"), 3),
}
TW, TH = 800, 450


def build(src, out, name, prefixes, cols):
    views = sorted(p.stem for p in src.glob("*.png") if p.stem.startswith(prefixes))
    if not views:
        return None
    rows = -(-len(views) // cols)
    sheet = Image.new("RGB", (cols * TW, rows * TH), "black")
    d = ImageDraw.Draw(sheet)
    for i, v in enumerate(views):
        im = Image.open(src / f"{v}.png").convert("RGB").resize((TW, TH), Image.LANCZOS)
        x, y = (i % cols) * TW, (i // cols) * TH
        sheet.paste(im, (x, y))
        label = v + ("  (test terrain, not worldgen)" if v.startswith("sl_") else "")
        d.rectangle([x, y, x + 7 * len(label) + 12, y + 20], fill="black")
        d.text((x + 5, y + 4), label, fill="white")
    path = out / f"{name}_contact_sheet.png"
    sheet.save(path, optimize=True)
    return path


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for name, (prefixes, cols) in SHEETS.items():
        print(build(src, out, name, prefixes, cols))


if __name__ == "__main__":
    main()
