"""Labelled contact sheets from the capture screenshots (no image content is altered, only scaled and tiled).

  python experiments/st03-batch4-barracks/sheet.py <screenshots dir> <out dir>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SHEETS = {
    "f02_exterior": ["f02_01_front", "f02_02_front_left", "f02_03_front_right", "f02_04_rear", "f02_05_rear_diag", "f02_06_side"],
    "f03_exterior": ["f03_01_front", "f03_02_front_left", "f03_03_front_right", "f03_04_rear", "f03_05_rear_diag", "f03_06_side"],
    "f04_exterior": ["f04_01_front", "f04_02_front_left", "f04_03_front_right", "f04_04_rear", "f04_05_rear_diag", "f04_06_side"],
    "interiors": ["f02_07_interior_from_door", "f02_08_interior_bunks", "f02_09_interior_loft",
                  "f03_07_interior_from_door", "f03_08_interior_bunks", "f03_09_interior_loft",
                  "f04_07_interior_from_door", "f04_08_interior_beds", "f04_09_interior_loft"],
    "context": ["ctx_01_f02_from_street", "ctx_02_f02_street_ne", "ctx_03_f02_neighbours_aerial",
                "ctx_04_f03_f04_from_street", "ctx_05_f03_f04_street_sw", "ctx_06_f03_f04_aerial"],
    "comparison_approval": [f"{t}_{v}" for t in ("f02", "f03", "f04")
                            for v in ("01_front", "02_front_left", "05_rear_diag", "07_interior_from_door")],
}
TW, TH = 800, 450


def build(src, out, name, views, cols=None):
    views = [v for v in views if (src / f"{v}.png").exists()]
    if not views:
        return None
    cols = cols or (3 if len(views) % 3 == 0 else 2)
    rows = -(-len(views) // cols)
    sheet = Image.new("RGB", (cols * TW, rows * TH), "black")
    d = ImageDraw.Draw(sheet)
    for i, v in enumerate(views):
        im = Image.open(src / f"{v}.png").convert("RGB").resize((TW, TH), Image.LANCZOS)
        x, y = (i % cols) * TW, (i // cols) * TH
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 8 * len(v) + 10, y + 20], fill="black")
        d.text((x + 5, y + 4), v, fill="white")
    path = out / f"{name}_contact_sheet.png"
    sheet.save(path, optimize=True)
    return path


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for name, views in SHEETS.items():
        cols = 4 if name == "comparison_approval" else 3 if name in ("interiors", "context") else 2
        p = build(src, out, name, views, cols=cols)
        print(p)


if __name__ == "__main__":
    main()
