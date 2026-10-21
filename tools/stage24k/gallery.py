"""Stage 24-K comparison renders (headless block-model renders, NOT Minecraft-client screenshots).

* templates/: the approved Stage 24-F tower (BEFORE) next to the production Stage 24-K tower (AFTER) at identical camera
  and scale: front and rear three-quarter, side silhouettes, elevated, platform close-up, access cutaway, changed cells
  (orange = new or different block, red = removed); both towers in one frame
* world/: the same tower piece read back from the Stage 24-I and Stage 24-K sweep worlds (same seed, same layout):
  full view, and a cutaway at deck level
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
from tools.stage24h import gallery as HG  # noqa: E402
from tools.stage24j import render as R  # noqa: E402
from tools.stage24j.designs import large_a, medium_a, large_current, medium_current  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "artifacts/ancient-city-restoration"
D24F, D24I, K = AR / "stage-24f/final-candidates", AR / "stage-24i", AR / "stage-24k"
GAL = K / "gallery"
PNG = BUILD / "png24k"
NOTE = "Headless render of NBT / generated world blocks · Minecraft 26.1.2 block models + textures · studio lighting · NOT a Minecraft-client screenshot"
PAIRS = {"large_pillar_1": (large_current, large_a), "medium_pillar_1": (medium_current, medium_a)}


def template_sheets():
    jobs, items = [], {}
    for m, (fc, fa) in PAIRS.items():
        base = {p: s for p, (s, _) in blocks_of(load_nbt(D24F / m / "restored.nbt")).items()}
        rows = []
        for tag, v, path in (("before", fc(), D24F / m / "restored.nbt"), ("after", fa(), K / "final-candidates" / m / "restored.nbt")):
            root = load_nbt(path)
            size = [int(s) for s in root["size"]]
            blocks = blocks_of(root)
            sp = write_scene(f"24k-{m}-{tag}", scene_from_blocks(blocks, size))
            cur = {p: s for p, (s, _) in blocks.items()}
            changed = [p for p, s in cur.items() if base.get(p, "minecraft:air") != s and not (s == "minecraft:air" and p not in base)]
            removed = [p for p, s in base.items() if s != "minecraft:air" and cur.get(p, "minecraft:air") == "minecraft:air"]
            for vn, (lab, off, el, sc, kind) in R.VIEWS.items():
                az = (R.FRONT[m] + off) % 360 if off is not None else 215
                j = dict(scene=str(sp), w=760, h=900, az=az, el=el, scale=sc, out=str(PNG / m / f"{tag}-{vn}.png"),
                         target=[size[0] / 2, R.H_TARGET, size[2] / 2], extras=[])
                if kind == "deck":
                    j["target"] = [size[0] / 2, v.meta["deck_y"], size[2] / 2]
                    j["h"] = 620
                    j["extras"].append(R.figure_on_deck(v))
                if kind == "section":
                    j["filter"] = {"remove": R.SECTION[m]}
                if kind == "diff" and tag == "after":
                    box = lambda p, c: {"type": "box", "min": [p[0] - .03, p[1] - .03, p[2] - .03], "max": [p[0] + 1.03, p[1] + 1.03, p[2] + 1.03], "color": c}  # noqa: E731
                    j["extras"] = [box(p, "#ff9933") for p in changed] + [box(p, "#ff3344") for p in removed]
                if vn in ("front34", "side-a"):
                    j["extras"].append({"type": "figure", "pos": [-2, 1, 2] if m == "large_pillar_1" else [3, 1, -2], "facing": 0})
                jobs.append(j)
            rows.append(tag)
        items[m] = rows
    assert run_jobs(jobs, "24k") == 0
    index = []
    heads = {"before": ("BEFORE — approved Stage 24-F tower", (140, 220, 160)), "after": ("AFTER — production Stage 24-K tower (approved Option A)", (255, 196, 120))}
    for m in PAIRS:
        for vn, (lab, off, el, sc, kind) in R.VIEWS.items():
            h = 620 if kind == "deck" else 900
            im = Image.new("RGB", (760 * 2, h + 96), (30, 34, 41))
            d = ImageDraw.Draw(im)
            d.text((12, 8), f"{TITLES[m]} — {lab} · identical camera and scale ({sc} px/block)", fill=(236, 240, 245), font=font(16, True))
            for i, tag in enumerate(("before", "after")):
                im.paste(Image.open(PNG / m / f"{tag}-{vn}.png").convert("RGB").resize((760, h), Image.Resampling.LANCZOS), (760 * i, 60))
                d.text((760 * i + 12, 36), heads[tag][0], fill=heads[tag][1], font=font(14, True))
            d.text((12, h + 68), NOTE, fill=(160, 170, 182), font=font(12))
            out = GAL / "templates" / m / f"{vn}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            im.save(out, "JPEG", quality=86, optimize=True, progressive=True)
            index.append({"module": m, "view": vn, "label": lab, "image": out.relative_to(K).as_posix()})
    for vn in ("front34", "side-a"):
        im = Image.new("RGB", (760 * 4, 900 + 96), (30, 34, 41))
        d = ImageDraw.Draw(im)
        d.text((12, 8), f"Both watchtowers, before and after — {R.VIEWS[vn][0]} · same camera and scale ({R.SCALE} px/block)", fill=(236, 240, 245), font=font(16, True))
        for i, (m, tag) in enumerate([(m, t) for m in PAIRS for t in ("before", "after")]):
            im.paste(Image.open(PNG / m / f"{tag}-{vn}.png").convert("RGB").resize((760, 900), Image.Resampling.LANCZOS), (760 * i, 60))
            d.text((760 * i + 12, 36), f"{TITLES[m].split(' — ')[1]} · {tag.upper()}", fill=heads[tag][1], font=font(14, True))
        d.text((12, 900 + 68), NOTE, fill=(160, 170, 182), font=font(12))
        out = GAL / "templates" / f"overview-{vn}.jpg"
        im.save(out, "JPEG", quality=86, optimize=True, progressive=True)
        index.append({"module": "both", "view": f"overview-{vn}", "image": out.relative_to(K).as_posix()})
    return index


def world_sheets():
    HG.piece = lambda variant, seed, idx: json.loads((K / f"worldgen/manifest-{seed}-k24.json").read_text())["cities"][0]["pieces"][idx]  # layout identical in i24 and k24
    HG.GAL, HG.D24H = GAL / "world", K
    index = []
    for m in PAIRS:
        for seed in range(24001, 24025):
            pcs = [(i, p) for i, p in enumerate(json.loads((K / f"worldgen/manifest-{seed}-k24.json").read_text())["cities"][0]["pieces"])
                   if "pillar" in p["template"] and p["template"].endswith(m)]
            if pcs:
                break
        idx, p = pcs[0]
        title = f"{TITLES[m]} as generated — seed {seed}, piece #{idx} · {p['rotation']}"
        lg = "left: Stage 24-I world (approved Stage 24-F tower) · right: Stage 24-K world (approved Option A tower)"
        outs = HG.pair(f"{m}-generated", seed, idx, title, lg, [("iso-a", 45, 32), ("iso-b", 225, 32)], variants=("i24", "k24"))
        outs += HG.pair(f"{m}-generated-top", seed, idx, title + " · from above", lg, [("top", 45, 70)], variants=("i24", "k24"))
        index.append({"module": m, "seed": seed, "piece_index": idx, "bb": p["bb"], "images": outs})
    return index


def main():
    index = {"templates": template_sheets(), "world": world_sheets()}
    (GAL / "INDEX.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
