"""Stage 24-J comparison renders: current vs Option A vs Option B of both watchtowers at identical camera and scale.

Headless renders of the candidate NBTs with Minecraft 26.1.2 block models and textures (Stage 24-D viewer) — NOT
Minecraft-client screenshots. Every view uses one fixed orthographic scale for both towers, so differences between
columns are geometry, not camera or lighting.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import blocks_of, load_nbt  # noqa: E402
from tools.stage24d.lib import scene_from_blocks, write_scene, run_jobs, BUILD, TITLES  # noqa: E402
from tools.stage24d.render_gallery import font  # noqa: E402
from tools.stage24j.designs import DESIGNS, D24F  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24J = ROOT / "artifacts/ancient-city-restoration/stage-24j"
GAL = D24J / "gallery"
PNG = BUILD / "png24j"
NOTE = "Headless render of the candidate NBT · Minecraft 26.1.2 block models + textures · studio lighting · NOT a Minecraft-client screenshot"
FRONT = {"large_pillar_1": 270, "medium_pillar_1": 180}            # azimuth of the entrance side (Stage 24-D config)
SECTION = {"large_pillar_1": [{"axis": "z", "lt": 2}], "medium_pillar_1": [{"axis": "z", "lt": 3}]}
SCALE, CLOSE = 34, 56                                             # px per block, identical for both towers
H_TARGET = 7.5                                                    # common vertical centre: both towers share one frame
VIEWS = {  # name: (label, az offset, elevation, scale, kind)
    "front34": ("front three-quarter (entrance side)", -45, 25, SCALE, None),
    "rear34": ("rear three-quarter", 135, 25, SCALE, None),
    "side-a": ("side silhouette (entrance on the left)", -90, 0, SCALE, None),
    "side-b": ("side silhouette (rotated 90°)", 0, 0, SCALE, None),
    "elevated": ("elevated view", -45, 58, SCALE, None),
    "deck": ("observation platform close-up", -45, 42, CLOSE, "deck"),
    "cutaway": ("interior access cutaway (front of the shaft removed, ladder in view)", None, 22, SCALE, "section"),
    "changes": ("changed cells outlined (orange = new or different block, red = removed)", -45, 30, SCALE, "diff"),
}


def candidates():
    out = {}
    for m, fs in DESIGNS.items():
        rows = []
        for f in fs:
            v = f()
            path = D24F / m / "restored.nbt" if v.variant == "current" else D24J / "proposals" / m / v.variant / "candidate.nbt"
            rows.append((v, path))
        out[m] = rows
    return out


def figure_on_deck(v):
    x, z = sorted(v.meta["deck"], key=lambda c: (abs(c[0] - 2.5) + abs(c[1] - 2.5)))[-1]
    return {"type": "figure", "pos": [x, v.meta["deck_y"], z], "facing": 0}


def main():
    cands = candidates()
    jobs = []
    for m, rows in cands.items():
        base = {p: s for p, (s, _) in blocks_of(load_nbt(D24F / m / "restored.nbt")).items()}
        for v, path in rows:
            root = load_nbt(path)
            size = [int(s) for s in root["size"]]
            blocks = blocks_of(root)
            sp = write_scene(f"24j-{m}-{v.variant}", scene_from_blocks(blocks, size))
            cur = {p: s for p, (s, _) in blocks.items()}
            changed = [p for p, s in cur.items() if base.get(p, "minecraft:air") != s and not (s == "minecraft:air" and p not in base)]
            removed = [p for p, s in base.items() if s != "minecraft:air" and cur.get(p, "minecraft:air") == "minecraft:air"]
            for vn, (lab, off, el, sc, kind) in VIEWS.items():
                az = (FRONT[m] + off) % 360 if off is not None else 215
                j = dict(scene=str(sp), w=760, h=900, az=az, el=el, scale=sc, out=str(PNG / m / f"{v.variant}-{vn}.png"),
                         target=[size[0] / 2, H_TARGET, size[2] / 2], extras=[])
                if kind == "deck":
                    j["target"] = [size[0] / 2, v.meta["deck_y"], size[2] / 2]
                    j["h"] = 620
                    j["extras"].append(figure_on_deck(v))
                if kind == "section":
                    j["filter"] = {"remove": SECTION[m]}
                if kind == "diff" and v.variant != "current":
                    j["extras"] = [{"type": "box", "min": [p[0] - .03, p[1] - .03, p[2] - .03], "max": [p[0] + 1.03, p[1] + 1.03, p[2] + 1.03],
                                    "color": "#ff9933"} for p in changed] + \
                                  [{"type": "box", "min": [p[0] - .03, p[1] - .03, p[2] - .03], "max": [p[0] + 1.03, p[1] + 1.03, p[2] + 1.03],
                                    "color": "#ff3344"} for p in removed]
                if vn in ("front34", "side-a"):
                    j["extras"].append({"type": "figure", "pos": [-2, 1, 2] if m == "large_pillar_1" else [3, 1, -2], "facing": 0})
                jobs.append(j)
    assert run_jobs(jobs, "24j") == 0
    index = {}
    for m, rows in cands.items():
        for vn, (lab, off, el, sc, kind) in VIEWS.items():
            h = 620 if kind == "deck" else 900
            im = Image.new("RGB", (760 * len(rows), h + 96), (30, 34, 41))
            d = ImageDraw.Draw(im)
            d.text((12, 8), f"{TITLES[m]} — {lab} · identical camera and scale ({sc} px/block) in every column", fill=(236, 240, 245), font=font(16, True))
            for i, (v, path) in enumerate(rows):
                im.paste(Image.open(PNG / m / f"{v.variant}-{vn}.png").convert("RGB").resize((760, h), Image.Resampling.LANCZOS), (760 * i, 60))
                head = "CURRENT — Stage 24-F approved" if v.variant == "current" else f"OPTION {v.variant} — {v.title.split(' — ')[0]}"
                d.text((760 * i + 12, 36), head, fill=(140, 220, 160) if v.variant == "current" else (255, 196, 120), font=font(14, True))
            d.text((12, h + 68), NOTE, fill=(160, 170, 182), font=font(12))
            out = GAL / m / f"{vn}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            im.save(out, "JPEG", quality=86, optimize=True, progressive=True)
            index.setdefault(m, []).append({"view": vn, "label": lab, "image": out.relative_to(D24J).as_posix()})
    # both towers, every option, one frame: identical scale and vertical centre, so heights compare directly
    cols = [("current", "CURRENT"), ("A", "OPTION A"), ("B", "OPTION B")]
    for vn in ("front34", "side-a"):
        im = Image.new("RGB", (760 * 3, 2 * 900 + 120), (30, 34, 41))
        d = ImageDraw.Draw(im)
        d.text((12, 8), f"Both watchtowers — {VIEWS[vn][0]} · same camera and scale ({SCALE} px/block) for every tower and option",
               fill=(236, 240, 245), font=font(16, True))
        for row, m in enumerate(cands):
            titles = {v.variant: v.title.split(" — ")[0] for v, _ in cands[m]}
            for i, (key, head) in enumerate(cols):
                im.paste(Image.open(PNG / m / f"{key}-{vn}.png").convert("RGB").resize((760, 900), Image.Resampling.LANCZOS), (760 * i, 40 + row * 900))
                lab = f"{TITLES[m].split(' — ')[1]} · {head}" + ("" if key == "current" else f" — {titles[key]}")
                d.text((760 * i + 12, 44 + row * 900), lab, fill=(140, 220, 160) if key == "current" else (255, 196, 120), font=font(14, True))
        d.text((12, 2 * 900 + 92), NOTE, fill=(160, 170, 182), font=font(12))
        out = GAL / f"overview-{vn}.jpg"
        im.save(out, "JPEG", quality=86, optimize=True, progressive=True)
        index.setdefault("overview", []).append({"view": vn, "image": out.relative_to(D24J).as_posix()})
    (GAL / "INDEX.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
