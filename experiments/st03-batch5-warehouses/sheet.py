"""Labelled contact sheets from the capture screenshots (no image content is altered, only scaled and tiled).

  python experiments/st03-batch5-warehouses/sheet.py <screenshots dir> <out dir>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SHEETS = {
    "f07_exterior": ["f07_01_front", "f07_02_front_left", "f07_03_front_right", "f07_04_side_left",
                     "f07_05_side_right", "f07_06_rear", "f07_07_rear_diag"],
    "f08_exterior": ["f08_01_front", "f08_02_front_left", "f08_03_front_right", "f08_04_side_left",
                     "f08_05_side_right", "f08_06_rear", "f08_07_rear_diag"],
    "interiors": ["f07_08_interior_aisle_from_porch", "f07_09_interior_west_bay_loft", "f07_10_interior_east_bay_racks",
                  "f08_08_interior_from_unloading_door", "f08_09_interior_bay_and_gallery", "f08_10_interior_north_stores",
                  "f08_11_interior_gallery", "f08_12_south_loft_stair"],
    "context": ["ctx_01_f07_from_south_lane", "ctx_02_f07_with_f19_smithy", "ctx_03_f07_neighbours_aerial",
                "ctx_04_f08_from_street", "ctx_05_f04_f08_street_nw", "ctx_06_f04_f08_gap_passage",
                "ctx_07_f08_neighbours_aerial"],
    "comparison_approval": [f"{t}_{v}" for t in ("f07", "f08")
                            for v in ("01_front", "02_front_left", "07_rear_diag")] +
                           ["f07_08_interior_aisle_from_porch", "f07_09_interior_west_bay_loft", "ctx_02_f07_with_f19_smithy",
                            "f08_09_interior_bay_and_gallery", "f08_11_interior_gallery", "ctx_05_f04_f08_street_nw"],
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
        cols = 3 if name in ("comparison_approval", "context") else 4 if name == "interiors" else 2
        p = build(src, out, name, views, cols=cols)
        print(p)


if __name__ == "__main__":
    main()
