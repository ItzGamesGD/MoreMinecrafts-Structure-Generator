"""Priority design questions V1-V5: uniform-scale comparison sheets (read-only)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.palette import get_block_by_index
from mcbuild.voxel import VoxelGrid
from tools.stage24d.lib import *  # noqa
from tools.stage24d.config import CFG, HOUSES, REFERENCE_HOMES
from tools.stage24d.render_gallery import ASSET, font, TAG, restored_scene, original_scene

REF_IN = ROOT / "artifacts/ancient-city-restoration/stage-24d/reference-inputs"  # approved prototypes (read-only copies)


def approved_scene(name):
    grid = VoxelGrid()
    run_blueprint((REF_IN / f"{name}.blueprint.py").read_text(encoding="utf8"), grid, seed=20261014)
    mn = grid.bounds[0]
    blocks = {(x - mn[0], y - mn[1], z - mn[2]): get_block_by_index(i).mc_id for (x, y, z), i in grid.items()}
    size = [grid.bounds[1][k] - mn[k] + 1 for k in range(3)]
    return write_scene(f"{name}-approved", scene_from_blocks(blocks, size)), size


def roof_profile(path_scene):
    sc = json.loads(Path(path_scene).read_text())
    top = {}
    for x, y, z, i in sc["blocks"]:
        top[(x, z)] = max(top.get((x, z), -1), y)
    c = Counter(top.values())
    return {"levels": len(c), "heights": dict(sorted(c.items())), "max_top": max(top.values()) + 1}


def sheet(cells, cols, cell_w, cell_h, out, title, sub=""):
    rows = -(-len(cells) // cols)
    im = Image.new("RGB", (cols * cell_w, rows * (cell_h + 26) + 44), (30, 34, 41))
    d = ImageDraw.Draw(im)
    d.text((12, 8), title, fill=(236, 240, 245), font=font(17, True))
    d.text((12, 28), sub, fill=(160, 170, 182), font=font(11))
    for i, (png, label, color) in enumerate(cells):
        r, c = divmod(i, cols)
        x, y = c * cell_w, 44 + r * (cell_h + 26)
        t = Image.open(png).convert("RGB").resize((cell_w, cell_h), Image.Resampling.LANCZOS)
        im.paste(t, (x, y + 26))
        d.text((x + 8, y + 5), label, fill=color, font=font(13, True))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "JPEG", quality=84, optimize=True, progressive=True)
    return out


def v1(jobs_out):
    """roof differentiation: five restored homes vs five previously designed residential prototypes at identical scale"""
    scenes = {m: restored_scene(m) for m in HOUSES}
    scenes.update({r: approved_scene(r) for r in REFERENCE_HOMES})
    prof = {k: roof_profile(v[0]) for k, v in scenes.items()}
    jobs = []
    SC = 13
    for k, (sp, size) in scenes.items():
        front = CFG[k]["front_az"] if k in CFG else 180
        for tag, az, el in (("q", (front - 45) % 360, 30), ("s", (front - 90) % 360, 0)):
            jobs.append(dict(scene=str(sp), w=380, h=340, ss=2, scale=SC, az=az, el=el, pad=False, out=str(PNG_V / f"v1-{k}-{tag}.png"),
                             target=[size[0] / 2, size[1] / 2, size[2] / 2]))
    run_jobs(jobs, "v1")
    outs = []
    for tag, name in (("q", "v1-roof-differentiation-threequarter.jpg"), ("s", "v1-roof-differentiation-side-silhouette.jpg")):
        cells = [(PNG_V / f"v1-{k}-{tag}.png", ("RESTORED · " if k in CFG else "APPROVED PROTOTYPE · ") + k.replace("_", " "),
                  (140, 220, 160) if k in CFG else (255, 190, 120)) for k in HOUSES + REFERENCE_HOMES]
        outs.append(sheet(cells, 5, 380, 340, ASSET / "priority" / name,
                          "V1 — Roof differentiation: restored houses (top row) vs previously designed residential prototypes (bottom row)",
                          f"Identical scale ({SC} px per block) and camera for every cell · {TAG}"))
    return prof, outs


def v2():
    m = "medium_ruin_2"
    c = CFG[m]
    sp, size = restored_scene(m)
    jobs = [
        dict(scene=str(sp), w=800, h=640, az=125, el=30, out=str(PNG_V / "v2-exterior-ne.png")),
        dict(scene=str(sp), w=800, h=640, az=250, el=56, filter={"ymax": 6}, out=str(PNG_V / "v2-dollhouse.png")),
        dict(scene=str(sp), w=800, h=640, az=200, el=26, filter={"remove": [{"axis": "z", "lt": 5}]}, out=str(PNG_V / "v2-section-stairs.png")),
        dict(scene=str(sp), w=800, h=640, az=270, el=58, filter={"ymin": 4, "ymax": 6}, out=str(PNG_V / "v2-upper-level-only.png")),
    ]
    run_jobs(jobs, "v2")
    cells = [(PNG_V / "v2-exterior-ne.png", "Exterior from the north-east: the east half rises to a second storey", (230, 235, 240)),
             (PNG_V / "v2-section-stairs.png", "Vertical section along the stair run (z = 5): four steps east, 2-high opening", (230, 235, 240)),
             (PNG_V / "v2-dollhouse.png", "Roof of the upper storey removed: bedroom + storage, ground floor beneath", (230, 235, 240)),
             (PNG_V / "v2-upper-level-only.png", "Upper level only (y 4–6): floor slab, bed, barrel, lantern, stair landing", (230, 235, 240))]
    return sheet(cells, 2, 800, 640, ASSET / "priority" / "v2-medium-ruin-2-second-floor.jpg",
                 "V2 — Medium Ruin 2: partial second floor", f"Same model as the gameplay-verified candidate · {TAG}")


def v3():
    jobs, SC = [], 30
    for m in ("large_pillar_1", "medium_pillar_1"):
        c = CFG[m]
        sp, size = restored_scene(m)
        fa = c["front_az"]
        deck_y = 14 if m == "large_pillar_1" else 9
        t = [size[0] / 2, size[1] / 2, size[2] / 2]
        jobs += [
            dict(scene=str(sp), w=520, h=520, scale=SC, az=fa, el=14, target=t, extras=[{"type": "figure", "pos": list(c["fig"][0]), "facing": c["fig"][1]}], out=str(PNG_V / f"v3-{m}-front.png")),
            dict(scene=str(sp), w=520, h=520, scale=SC, az=(fa - 45) % 360, el=26, target=t, out=str(PNG_V / f"v3-{m}-q.png")),
            dict(scene=str(sp), w=520, h=520, scale=70, az=(fa - 35) % 360, el=42, target=[size[0] / 2, deck_y, size[2] / 2], out=str(PNG_V / f"v3-{m}-deck.png")),
            dict(scene=str(sp), w=520, h=520, scale=SC, az=c["section_az"], el=14, target=t, filter={"remove": c["section"]}, out=str(PNG_V / f"v3-{m}-section.png")),
        ]
    run_jobs(jobs, "v3")
    cells = []
    for kind, lab in (("front", "front with 1.8-block figure"), ("q", "three-quarter silhouette"), ("deck", "observation deck, parapet and ladder exit"), ("section", "section through the ladder run")):
        for m, col in (("large_pillar_1", (140, 220, 160)), ("medium_pillar_1", (140, 200, 255))):
            cells.append((PNG_V / f"v3-{m}-{kind}.png", f"{m.replace('_', ' ')} — {lab}", col))
    return sheet(cells, 2, 520, 520, ASSET / "priority" / "v3-watchtower-silhouettes.jpg",
                 "V3 — Watchtowers side by side (left: large pillar, right: medium pillar)", f"Identical scale ({SC} px per block) except the deck close-ups · {TAG}")


def v4():
    m = "sauna_1"
    pos = (11, 2, 33)
    sp, size = restored_scene(m)
    orig = json.loads(original_scene(m)[0].read_text())
    rest = json.loads(sp.read_text())
    ob = blocks_of(load_nbt(BUILD / "originals" / f"{m}.nbt"))
    removed = ob.get(pos, ("minecraft:air", None))[0]
    assert removed != "minecraft:air", "expected the original head block at (11,2,33)"
    before = json.loads(sp.read_text())
    before["palette"].append(parse_state(removed))
    before["blocks"].append([*pos, len(before["palette"]) - 1])
    bp = write_scene("sauna-opening-before", before)
    box = [{"type": "box", "min": list(pos), "max": [pos[0] + 1, pos[1] + 1, pos[2] + 1], "color": "#ff3355"}]
    t = [pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5]
    views = [("from the reception (south side)", dict(az=0, el=10, scale=62)), ("from the bath side (north)", dict(az=180, el=10, scale=62)),
             ("oblique from the reception", dict(az=330, el=28, scale=52)), ("plan view (y ≤ 3), reception at the bottom", dict(az=0, el=90, scale=44, filter={"ymax": 3}))]
    jobs = []
    for i, (lab, kw) in enumerate(views):
        for tag, scn in (("before", bp), ("after", sp)):
            jobs.append(dict(scene=str(scn), w=700, h=520, target=t, extras=box, out=str(PNG_V / f"v4-{i}-{tag}.png"), **kw))
    run_jobs(jobs, "v4")
    cells = []
    for i, (lab, kw) in enumerate(views):
        cells.append((PNG_V / f"v4-{i}-before.png", f"BEFORE (original head block present) — {lab}", (255, 190, 120)))
        cells.append((PNG_V / f"v4-{i}-after.png", f"AFTER (Stage 24-B/24-C opening) — {lab}", (140, 220, 160)))
    return sheet(cells, 2, 700, 520, ASSET / "priority" / "v4-sauna-reception-opening.jpg",
                 f"V4 — Sauna reception opening at {pos}: removed block ({removed.replace('minecraft:', '')}) outlined in red", f"{TAG}"), removed


def main():
    global PNG_V
    PNG_V = BUILD / "png" / "priority"
    res = {}
    prof, outs = v1(None)
    res["v1_roof_profiles"] = prof
    res["v2"] = str(v2())
    res["v3"] = str(v3())
    s4, removed = v4()
    res["v4"] = str(s4)
    res["v4_removed_block"] = removed
    (D24 / "priority-data.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res["v1_roof_profiles"]))


if __name__ == "__main__":
    main()
