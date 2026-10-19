"""Render the per-module image set for the Stage 24-D gallery (read-only on all NBT inputs)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24d.lib import *  # noqa
from tools.stage24d.config import CFG, HOUSES

ASSET = D24 / "gallery/assets"
PNG = BUILD / "png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TAG = "Minecraft 26.1.2 block models + textures · studio lighting (not in-game light)"


def font(sz, bold=False):
    try:
        return ImageFont.truetype(FONTB if bold else FONT, sz)
    except OSError:
        return ImageFont.load_default()


def restored_scene(m):
    sc, size = scene_of_nbt(S24B / m / "restored.nbt")
    return write_scene(f"{m}-restored", sc), size


def original_scene(m):
    sc, size = scene_of_nbt(BUILD / "originals" / f"{m}.nbt")
    return write_scene(f"{m}-original", sc), size


def caption(png: Path, out: Path, title: str, tag: str = TAG, size=None):
    im = Image.open(png).convert("RGB")
    if size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    w, h = im.size
    band = 30 if w >= 900 else 24
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, h - band, w, h), fill=(14, 17, 22, 220))
    d.text((10, h - band + 6), title, fill=(236, 240, 245), font=font(14 if w >= 900 else 11, True))
    tw = d.textlength(tag, font=font(11))
    if tw + d.textlength(title, font=font(14, True)) + 40 < w:
        d.text((w - tw - 10, h - band + 9), tag, fill=(160, 170, 182), font=font(11))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "JPEG", quality=84, optimize=True, progressive=True)
    return out


def main(only=None):
    jobs, meta = [], []
    modules = only or MODULES
    for m in modules:
        c = CFG[m]
        rs, size = restored_scene(m)
        os_, osize = original_scene(m)
        fa = c["front_az"]
        sx, sy, sz = size
        ctr = [sx / 2, sy / 2, sz / 2]
        base = dict(scene=str(rs), w=1200, h=900)
        figs = [{"type": "figure", "pos": list(c["fig"][0]), "facing": c["fig"][1]}]

        def add(name, title, **kw):
            j = {**base, **kw}
            j["out"] = str(PNG / m / f"{name}.png")
            jobs.append(j)
            meta.append({"module": m, "name": name, "title": f"{TITLES[m]} — {title}", "png": j["out"], "size": [j["w"], j["h"]]})

        add("front", "front exterior", az=fa, el=20, extras=figs)
        add("rear", "rear exterior", az=(fa + 180) % 360, el=20)
        add("left", "left exterior", az=(fa - 90) % 360, el=20)
        add("right", "right exterior", az=(fa + 90) % 360, el=20)
        add("elevated", "elevated three-quarter view", az=(fa - 45) % 360, el=38, extras=figs)
        add("roof", "roof view (plan from above)", az=fa, el=90)
        ex, ey, ez = c["entry"]
        add("entrance", "entrance close-up (figure ≈ 1.8 blocks)", az=(fa + 20) % 360, el=14, scale=84,
            target=[ex + 0.5, ey + 0.8, ez + 0.5], extras=figs)
        add("interior-dollhouse", f"interior cutaway — roof removed (y ≤ {c['dollhouse']})", az=(fa - 30) % 360, el=60,
            filter={"ymax": c["dollhouse"]})
        add("interior-section", "interior cutaway — vertical section", az=c["section_az"], el=30,
            filter={"remove": c["section"]})
        for i, (label, ymax) in enumerate(c["floors"], 1):
            add(f"floor-{i}", f"floor-by-floor {i}/{len(c['floors'])}: {label}", az=fa, el=58, filter={"ymax": ymax})
        # original vs restored: same camera and the same bounds so the scale is identical
        for tag_, az_, el_ in (("a", (fa - 45) % 360, 36), ("b", (fa + 135) % 360, 36)):
            for which, scn in (("original", os_), ("restored", rs)):
                jobs.append(dict(scene=str(scn), w=800, h=800, az=az_, el=el_, bounds=[[0, 0, 0], [sx, sy, sz]],
                                 out=str(PNG / m / f"cmp-{tag_}-{which}.png"), extras=[]))
    sel = BUILD / "jobs" / "meta.json"
    sel.parent.mkdir(parents=True, exist_ok=True)
    sel.write_text(json.dumps(meta))
    rc = run_jobs(jobs, "gallery-" + ("all" if not only else "_".join(only)))
    if rc:
        raise SystemExit(rc)
    n = 0
    for e in meta:
        caption(Path(e["png"]), ASSET / e["module"] / f"{e['name']}.jpg", e["title"], size=tuple(e["size"]))
        n += 1
    for m in modules:
        for tag_ in "ab":
            a, b = (Image.open(PNG / m / f"cmp-{tag_}-{w}.png").convert("RGB") for w in ("original", "restored"))
            a, b = (x.resize((800, 800), Image.Resampling.LANCZOS) for x in (a, b))
            sheet = Image.new("RGB", (1600, 860), (30, 34, 41))
            sheet.paste(a, (0, 30)); sheet.paste(b, (800, 30))
            d = ImageDraw.Draw(sheet)
            d.text((12, 6), "ORIGINAL — vanilla 26.1.2 NBT (pinned source)", fill=(255, 190, 120), font=font(15, True))
            d.text((812, 6), "RESTORED — Stage 24-C final candidate", fill=(140, 220, 160), font=font(15, True))
            d.text((12, 838), f"{TITLES[m]} · identical camera and scale · {TAG}", fill=(160, 170, 182), font=font(12))
            out = ASSET / m / f"compare-{tag_}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            sheet.save(out, "JPEG", quality=84, optimize=True, progressive=True)
            n += 1
    print("images", n)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
