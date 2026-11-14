"""Labelled contact sheets from the capture screenshots (no image content is altered, only scaled and tiled).

  python experiments/st03-batch7-commander-manor/sheet.py <screenshots dir> <out dir>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SHEETS = {
    "f01_exterior": ["f01_01_front", "f01_02_front_left", "f01_03_front_right", "f01_04_side_west", "f01_05_side_east",
                     "f01_06_rear", "f01_07_rear_diag", "f01_08_roof_and_lookout", "f01_09_entrance_porch"],
    "interiors": ["f01_10_interior_hall_from_door", "f01_11_interior_chandelier_from_hall",
                  "f01_12_interior_gallery_west_arm", "f01_13_interior_war_room", "f01_14_interior_stair_from_hall",
                  "f01_15_interior_hall_from_war_room", "f01_16_interior_3F_bedroom", "f01_17_interior_3F_study",
                  "f01_18_interior_attic_to_lookout", "f01_19_interior_1F_guard_bay"],
    "test_entities": ["f01_20_interior_war_room_test_commander", "f01_21_interior_bedroom_test_armor_stand"],
    "context": ["ctx_01_f01_from_central_street", "ctx_02_f01_aerial_south_east", "ctx_03_f01_f02_f03_from_south",
                "ctx_04_f01_with_f12_west", "ctx_05_f01_with_f15_east", "ctx_06_north_quarter_aerial"],
    "comparison_approval": ["f01_01_front", "f01_02_front_left", "f01_07_rear_diag", "f01_08_roof_and_lookout",
                            "ctx_01_f01_from_central_street", "f01_10_interior_hall_from_door",
                            "f01_11_interior_chandelier_from_hall", "f01_12_interior_gallery_west_arm",
                            "f01_13_interior_war_room", "f01_16_interior_3F_bedroom", "f01_17_interior_3F_study",
                            "f01_18_interior_attic_to_lookout"],
}
COLS = {"f01_exterior": 3, "interiors": 5, "test_entities": 2, "context": 3, "comparison_approval": 4}
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
        label = v + ("  (test entity, not template content)" if "_test_" in v else "")
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
