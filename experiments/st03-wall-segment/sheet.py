"""Review sheets for the wall segment (images only scaled and tiled, never altered).

  python experiments/st03-wall-segment/sheet.py

review/evolution_*.png: v1 / v2 / v3 (final candidate) rows, the same camera per column.
review/final_*.png: the final candidate (v3).
"""

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SHOTS, OUT = HERE / "screenshots", HERE / "review"
TW, TH = 640, 360
STAGES = (("v1", "v1"), ("v2", "v2"), ("v3", "v3 final candidate"))
EVOLUTION = {
    "evolution_front_oblique_joint": ["01_front", "02_oblique_45", "04_stone_timber_joint"],
    "evolution_run_inside": ["10_run5_oblique", "09_run5_front_far", "05_inside_oblique"],
}
FINAL = {
    "final_exterior": ["01_front", "02_oblique_45", "03_side_depth_close", "04_stone_timber_joint",
                       "09_run5_front_far", "10_run5_oblique"],
    "final_inside_top_context": ["05_inside_oblique", "06_inside_close", "07_top_parapet", "08_walk_along",
                                 "11_context_outside", "12_context_aerial_inside"],
}


def tile(items, cols, out):
    rows = -(-len(items) // cols)
    sheet = Image.new("RGB", (cols * TW, rows * TH), "black")
    d = ImageDraw.Draw(sheet)
    for i, (p, label) in enumerate(items):
        x, y = (i % cols) * TW, (i // cols) * TH
        if p.exists():
            sheet.paste(Image.open(p).convert("RGB").resize((TW, TH), Image.LANCZOS), (x, y))
        d.rectangle([x, y, x + 7 * len(label) + 12, y + 20], fill="black")
        d.text((x + 5, y + 4), label, fill="white")
    sheet.save(out, optimize=True)
    print(out.relative_to(HERE))


def main():
    OUT.mkdir(exist_ok=True)
    for name, views in EVOLUTION.items():
        tile([(SHOTS / s / f"{v}.png", f"{t}: {v}") for s, t in STAGES for v in views], len(views), OUT / f"{name}.png")
    for name, views in FINAL.items():
        tile([(SHOTS / "v3" / f"{v}.png", f"v3: {v}") for v in views], 3, OUT / f"{name}.png")


if __name__ == "__main__":
    main()
