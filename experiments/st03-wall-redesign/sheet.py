"""Labelled contact sheets of the prototype screenshots (images only scaled and tiled, never altered).

  python experiments/st03-wall-redesign/sheet.py <screenshots dir> <out dir>

Per design: <d>_mw86, <d>_mw31_context. Comparison: compare_exterior / compare_interior_top / compare_context - one
row per design (A, B, C), the same camera in each column.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

TW, TH = 640, 360
PER_DESIGN = {
    "mw86": ["mw86_01_front", "mw86_02_oblique_exterior", "mw86_03_raking_exterior", "mw86_04_side_end",
             "mw86_05_top_aerial", "mw86_06_oblique_interior", "mw86_07_detail_exterior", "mw86_08_detail_interior",
             "mw86_09_detail_wall_top"],
    "mw31_context": ["mw31_01_front", "mw31_02_oblique_exterior", "mw31_03_oblique_interior", "ctx_01_hq_aerial",
                     "ctx_02_gate_south", "ctx_03_corner_NW_outside", "ctx_04_W-E_inside", "sl_01_S1_footing_close"],
}
COMPARE = {
    "compare_exterior": ["mw86_02_oblique_exterior", "mw86_03_raking_exterior", "mw86_07_detail_exterior",
                         "mw86_04_side_end"],
    "compare_interior_top": ["mw86_06_oblique_interior", "mw86_08_detail_interior", "mw86_05_top_aerial",
                             "mw86_09_detail_wall_top"],
    "compare_context": ["mw31_02_oblique_exterior", "ctx_01_hq_aerial", "ctx_02_gate_south", "sl_01_S1_footing_close"],
}
NAMES = {"a": "A_counterfort_arcade", "b": "B_hoarded_wall", "c": "C_scarp_and_casemates"}


def tile(paths, labels, cols, out):
    rows = -(-len(paths) // cols)
    sheet = Image.new("RGB", (cols * TW, rows * TH), "black")
    d = ImageDraw.Draw(sheet)
    for i, (p, label) in enumerate(zip(paths, labels)):
        x, y = (i % cols) * TW, (i // cols) * TH
        if p.exists():
            sheet.paste(Image.open(p).convert("RGB").resize((TW, TH), Image.LANCZOS), (x, y))
        d.rectangle([x, y, x + 7 * len(label) + 12, y + 20], fill="black")
        d.text((x + 5, y + 4), label, fill="white")
    sheet.save(out, optimize=True)
    print(out)


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for d, name in NAMES.items():
        for sheet, views in PER_DESIGN.items():
            tile([src / f"{d}_{v}.png" for v in views], [f"{name}: {v}" for v in views], 3,
                 out / f"{d}_{sheet}_contact_sheet.png")
    for sheet, views in COMPARE.items():
        paths, labels = [], []
        for d, name in NAMES.items():
            paths += [src / f"{d}_{v}.png" for v in views]
            labels += [f"{name}: {v}" for v in views]
        tile(paths, labels, len(views), out / f"{sheet}_contact_sheet.png")


if __name__ == "__main__":
    main()
