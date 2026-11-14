"""Labelled contact sheets from the capture screenshots (no image content is altered, only scaled and tiled).

  python experiments/st03-batch6-prison-stable/sheet.py <screenshots dir> <out dir>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

EXT = ("01_front", "02_front_left", "03_front_right", "04_side_left", "05_side_right", "06_rear", "07_rear_diag",
       "08_entrance_door")
SHEETS = {
    "f09_exterior": [f"f09_{v}" for v in EXT],
    "f10_exterior": [f"f10_{v.replace('08_entrance_door', '08_entrance_portal')}" for v in EXT],
    "interiors": ["f09_09_interior_corridor_from_vestibule", "f09_10_interior_cell_nw_through_bars",
                  "f09_11_interior_cell_se_through_bars", "f09_12_interior_inside_cell_ne",
                  "f09_13_interior_vestibule_to_door", "f09_14_front_door_opened_by_button",
                  "f10_09_interior_aisle_from_portal", "f10_10_interior_west_pen", "f10_11_interior_east_pen",
                  "f10_12_interior_aisle_head_store", "f10_13_interior_nave_beams", "f10_16_interior_west_pen_from_corner"],
    "ravager_space": ["f10_14_interior_west_pen_test_ravager", "f10_15_interior_east_pen_test_ravager"],
    "context": ["ctx_01_f09_from_south", "ctx_02_f09_f10_aerial_se", "ctx_03_f10_from_south_strip",
                "ctx_04_f10_f09_from_south_west", "ctx_05_f08_f09_lane", "ctx_06_f10_f08_from_nw",
                "ctx_07_south_east_quarter_aerial"],
    "comparison_approval": ["f09_01_front", "f09_02_front_left", "f09_07_rear_diag",
                            "f09_09_interior_corridor_from_vestibule", "f09_10_interior_cell_nw_through_bars",
                            "f10_01_front", "f10_02_front_left", "f10_07_rear_diag",
                            "f10_09_interior_aisle_from_portal", "f10_14_interior_west_pen_test_ravager"],
}
COLS = {"comparison_approval": 5, "ravager_space": 2, "f09_exterior": 4, "f10_exterior": 4, "interiors": 4,
        "context": 4}
TW, TH = 800, 450


def build(src, out, name, views, cols):
    views = [v for v in views if (src / f"{v}.png").exists()]
    if not views:
        return None
    rows = -(-len(views) // cols)
    sheet = Image.new("RGB", (cols * TW, rows * TH), "black")
    d = ImageDraw.Draw(sheet)
    for i, v in enumerate(views):
        im = Image.open(src / f"{v}.png").convert("RGB").resize((TW, TH), Image.LANCZOS)
        x, y = (i % cols) * TW, (i // cols) * TH
        sheet.paste(im, (x, y))
        label = v + ("  (test entities, NoAI)" if "test_ravager" in v else "")
        d.rectangle([x, y, x + 7 * len(label) + 12, y + 20], fill="black")
        d.text((x + 5, y + 4), label, fill="white")
    path = out / f"{name}_contact_sheet.png"
    sheet.save(path, optimize=True)
    return path


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for name, views in SHEETS.items():
        print(build(src, out, name, views, COLS[name]))


if __name__ == "__main__":
    main()
