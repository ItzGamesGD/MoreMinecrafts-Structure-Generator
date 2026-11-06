"""Contact sheets for the B -> B2 comparison (images only scaled and tiled, never altered).

  python experiments/st03-wall-redesign/sheet_b2.py <screenshots-b2 dir> <out dir>

Comparison sheets: row 1 = B (previous prototype), row 2 = B2, the same camera in each column.
B2 sheets: the requested review scenes of the revised design alone.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

TW, TH = 640, 360
COMPARE = {
    "b_vs_b2_front_oblique": ["mw86_01_front", "mw86_02_oblique_exterior", "mw86_03_raking_exterior"],
    "b_vs_b2_joint_top": ["mw86_07_detail_exterior", "mw86_10_joint_close", "mw86_09_detail_wall_top"],
    "b_vs_b2_inside": ["mw86_06_oblique_interior", "mw86_08_detail_interior", "mw86_11_walk_along_top"],
    "b_vs_b2_context": ["ctx_01_hq_aerial", "ctx_03_corner_NW_outside", "ctx_04_W-E_inside"],
    "b_vs_b2_mw31_gate": ["mw31_02_oblique_exterior", "ctx_05_gate_end_outside", "ctx_06_gate_end_inside"],
}
B2_ONLY = {
    "b2_review": ["mw86_01_front", "mw86_02_oblique_exterior", "mw86_10_joint_close", "mw86_06_oblique_interior",
                  "mw86_09_detail_wall_top", "mw31_02_oblique_exterior", "ctx_05_gate_end_outside", "ctx_01_hq_aerial",
                  "ctx_02_gate_south"],
}


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
    for name, views in COMPARE.items():
        paths, labels = [], []
        for d, title in (("b", "B"), ("b2", "B2")):
            paths += [src / f"{d}_{v}.png" for v in views]
            labels += [f"{title}: {v}" for v in views]
        tile(paths, labels, len(views), out / f"{name}.png")
    for name, views in B2_ONLY.items():
        tile([src / f"b2_{v}.png" for v in views], [f"B2: {v}" for v in views], 3, out / f"{name}.png")


if __name__ == "__main__":
    main()
