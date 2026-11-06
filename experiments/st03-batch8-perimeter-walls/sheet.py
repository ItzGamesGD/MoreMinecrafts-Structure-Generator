"""Labelled contact sheets from the capture screenshots (no image content is altered, only scaled and tiled).

  python experiments/st03-batch8-perimeter-walls/sheet.py <screenshots dir> <out dir>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SHEETS = {
    "mw86": ["mw86_01_exterior_full", "mw86_02_exterior_front", "mw86_03_exterior_close_end", "mw86_04_exterior_close_middle",
             "mw86_05_interior_full", "mw86_06_interior_close_end", "mw86_07_parapet_walk", "mw86_08_end_section"],
    "mw31": ["mw31_01_exterior_full", "mw31_02_exterior_front", "mw31_03_exterior_close_end", "mw31_04_exterior_close_middle",
             "mw31_05_interior_full", "mw31_06_interior_close_end", "mw31_07_parapet_walk", "mw31_08_end_section"],
    "placements": ["pl_01_W-N_from_outside_north", "pl_02_W-E_from_outside_east", "pl_03_W-W_from_outside_west",
                   "pl_04_W-SW_W-SE_from_outside_south", "pl_05_W-N_from_inside", "pl_06_W-E_W-SE_from_inside"],
    "joints_gate": ["jt_01_corner_NW_tower_square", "jt_02_corner_NE_tower_square", "jt_03_corner_SE_tower_square",
                    "jt_04_corner_SW_tower_square", "jt_05_corner_NW_from_inside", "gt_01_gate_gap_from_outside",
                    "gt_02_gate_west_end_W-SW", "gt_03_gate_east_end_W-SE", "gt_04_gate_gap_from_inside"],
    "slope_footing": ["sl_01_S1_valley_exterior", "sl_02_S1_valley_exterior_close", "sl_03_S1_valley_interior",
                      "sl_04_S2_cross_slope_exterior", "sl_05_S2_cross_slope_profile", "sl_06_S3_undulating_exterior",
                      "sl_07_S3_undulating_interior"],
    "overview": ["ov_01_whole_hq_aerial_south", "ov_02_whole_hq_aerial_north_west", "ov_03_whole_hq_aerial_south_east"],
    "comparison_approval": ["mw86_01_exterior_full", "mw86_03_exterior_close_end", "mw86_05_interior_full",
                            "mw31_02_exterior_front", "pl_04_W-SW_W-SE_from_outside_south", "jt_01_corner_NW_tower_square",
                            "gt_02_gate_west_end_W-SW", "sl_02_S1_valley_exterior_close", "sl_05_S2_cross_slope_profile",
                            "ov_01_whole_hq_aerial_south", "ov_02_whole_hq_aerial_north_west", "mw86_08_end_section"],
}
COLS = {"mw86": 4, "mw31": 4, "placements": 3, "joints_gate": 3, "slope_footing": 4, "overview": 3, "comparison_approval": 4}
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
        label = v + ("  (test terrain, not worldgen)" if v.startswith("sl_") else "")
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
