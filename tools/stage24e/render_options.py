"""Render the current Stage 24-C house next to every Stage 24-E alternative at identical camera and scale."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24d.lib import scene_of_nbt, write_scene, run_jobs, BUILD, TITLES, S24B  # noqa
from tools.stage24d.config import CFG
from tools.stage24d.render_gallery import font
from tools.stage24e.designs import DESIGNS

D24E = Path(__file__).resolve().parents[2] / "artifacts/ancient-city-restoration/stage-24e"
OUT = D24E / "review/assets"
PNG = BUILD / "png24e"
SCALE = {"large_ruin_1": 22, "medium_ruin_1": 34, "medium_ruin_2": 26, "small_ruin_1": 44, "small_ruin_2": 44}
TAG = "Minecraft 26.1.2 block models + textures · studio lighting · not client screenshots"
VIEWS = {  # name: (label, az offset from the entrance side, elevation, filter)
    "front34": ("front three-quarter", -45, 28, None),
    "rear34": ("rear three-quarter", 135, 28, None),
    "street": ("street elevation (entrance side)", 0, 4, None),
    "side": ("side silhouette", -90, 0, None),
    "section": ("cutaway: front half removed", 150, 30, "section"),
}


def build_variants(only=None):
    rows = {}
    for m, fs in DESIGNS.items():
        if only and m not in only:
            continue
        items = [("current", "Current — Stage 24-C final", S24B / m / "restored.nbt", None)]
        for f in fs:
            v = f()
            p = v.save(D24E / "proposals" / m / v.variant / "candidate.nbt")
            items.append((v.variant, f"Option {v.variant} — {v.title}", p, v))
        rows[m] = items
    return rows


def render(rows):
    jobs, plan = [], []
    for m, items in rows.items():
        c = CFG[m]
        fa = c["front_az"]
        sizes = []
        for key, title, path, v in items:
            sc, size = scene_of_nbt(path)
            sizes.append(size)
            sp = write_scene(f"24e-{m}-{key}", sc)
            for vn, (lab, off, el, filt) in VIEWS.items():
                j = dict(scene=str(sp), w=760, h=620, az=(fa + off) % 360, el=el, scale=SCALE[m], out=str(PNG / m / f"{key}-{vn}.png"),
                         extras=[{"type": "figure", "pos": list(c["fig"][0]), "facing": c["fig"][1]}] if vn in ("front34", "street") else [])
                if filt == "section":
                    j["filter"] = {"remove": c["section"]}
                    j["az"] = c["section_az"]
                jobs.append(j)
        H = max(s[1] for s in sizes)
        for j in jobs[-len(items) * len(VIEWS):]:
            j["target"] = [sizes[0][0] / 2, H / 2 - 0.5, sizes[0][2] / 2]
        plan.append((m, items))
    rc = run_jobs(jobs, "24e")
    assert rc == 0
    return plan


def sheets(plan):
    made = []
    for m, items in plan:
        for vn, (lab, *_r) in VIEWS.items():
            n = len(items)
            cw, ch = 760, 620
            im = Image.new("RGB", (cw * n, ch + 76), (30, 34, 41))
            d = ImageDraw.Draw(im)
            d.text((12, 8), f"{TITLES[m]} — {lab} · current vs alternatives at identical camera and scale ({SCALE[m]} px/block)", fill=(236, 240, 245), font=font(16, True))
            for i, (key, title, path, v) in enumerate(items):
                t = Image.open(PNG / m / f"{key}-{vn}.png").convert("RGB").resize((cw, ch), Image.Resampling.LANCZOS)
                im.paste(t, (i * cw, 50))
                col = (255, 190, 120) if key == "current" else (140, 220, 160)
                dims = "×".join(map(str, v.size)) if v else "×".join(str(int(x)) for x in __import__("tools.stage24c.common", fromlist=["x"]).load_nbt(path)["size"])
                flag = "" if (v is None or not v.expanded) else "  ⚠ larger NBT — needs authorisation"
                d.text((i * cw + 10, 28), (("CURRENT" if key == "current" else f"OPTION {key}") + f" · {dims}{flag}"), fill=col, font=font(13, True))
            d.text((10, ch + 56), TAG, fill=(160, 170, 182), font=font(11))
            out = OUT / m / f"compare-{vn}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            im.save(out, "JPEG", quality=84, optimize=True, progressive=True)
            made.append(out)
        for key, title, path, v in items:   # individual images too (for the phone gallery)
            for vn in VIEWS:
                out = OUT / m / f"{key}-{vn}.jpg"
                Image.open(PNG / m / f"{key}-{vn}.png").convert("RGB").resize((760, 620), Image.Resampling.LANCZOS).save(out, "JPEG", quality=84, optimize=True, progressive=True)
                made.append(out)
    return made


if __name__ == "__main__":
    only = sys.argv[1:] or None
    rows = build_variants(only)
    made = sheets(render(rows))
    print("images", len(made))
