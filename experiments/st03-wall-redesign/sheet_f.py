"""Contact sheets for design F (images only scaled and tiled, never altered).

  python experiments/st03-wall-redesign/sheet_f.py experiments/st03-wall-redesign/screenshots-f \
      experiments/st03-wall-redesign/approval-f

screenshots-f/{draft,rev1,final}: the same cameras for the draft, revision 1 and the final (revision 2).
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

TW, TH = 640, 360
STAGES = (("draft", "draft"), ("rev1", "revision 1"), ("final", "final (revision 2)"))
EVOLUTION = {
    "f_evolution_exterior": ["mw86_01_front", "mw86_02_oblique_exterior", "mw86_07_detail_exterior"],
    "f_evolution_side_top_inside": ["mw86_04_side_end", "mw86_05_top_aerial", "mw86_06_oblique_interior"],
    "f_evolution_mw31_context": ["mw31_02_oblique_exterior", "mw86_10_joint_close", "ctx_01_hq_aerial"],
}
FINAL = {
    "f_final_mw86": ["mw86_01_front", "mw86_02_oblique_exterior", "mw86_03_raking_exterior", "mw86_04_side_end",
                     "mw86_05_top_aerial", "mw86_09_detail_wall_top", "mw86_07_detail_exterior",
                     "mw86_10_joint_close", "mw86_11_walk_along_top"],
    "f_final_inside": ["mw86_06_oblique_interior", "mw86_08_detail_interior", "mw31_03_oblique_interior"],
    "f_final_mw31_gate_context": ["mw31_01_front", "mw31_02_oblique_exterior", "ctx_05_gate_end_outside",
                                  "ctx_06_gate_end_inside", "ctx_02_gate_south", "ctx_01_hq_aerial",
                                  "ctx_03_corner_NW_outside", "ctx_04_W-E_inside", "sl_01_S1_footing_close"],
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
    for name, views in EVOLUTION.items():
        paths, labels = [], []
        for stage, title in STAGES:
            paths += [src / stage / f"f_{v}.png" for v in views]
            labels += [f"{title}: {v}" for v in views]
        tile(paths, labels, len(views), out / f"{name}.png")
    for name, views in FINAL.items():
        tile([src / "final" / f"f_{v}.png" for v in views], [f"final: {v}" for v in views], 3, out / f"{name}.png")


if __name__ == "__main__":
    main()
