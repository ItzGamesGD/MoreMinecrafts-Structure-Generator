"""NBT-derived review renders for Stage 24-C (original vs final restored, with a human-scale reference)."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mcbuild.palette import get_block
from mcbuild.render.views import render_view, BG
from mcbuild.voxel import VoxelGrid

from tools.stage24b_candidate import Candidate
from tools.stage24b_source import load_original
from tools.stage24c.common import *  # noqa
from tools.stage24c.goals import derive

OUTV = OUT / "visual"
HUMAN = get_block("pink_concrete").index  # 1x1x2 "player" column (Steve is 0.6 x 1.8)


def grid_of(path_or_root, module):
    return Candidate(module, load_nbt(path_or_root) if isinstance(path_or_root, Path) else path_or_root).to_grid()


def sheet(tiles, labels, cols=4, size=420, title=""):
    cell = size + 30
    rows = -(-len(tiles) // cols)
    img = Image.new("RGB", (cols * cell, rows * cell + 28), BG)
    d = ImageDraw.Draw(img)
    d.text((8, 6), title, fill="white")
    for i, (t, l) in enumerate(zip(tiles, labels)):
        r, c = divmod(i, cols)
        ratio = min(size / max(1, t.width), size / max(1, t.height))
        f = t.resize((max(1, int(t.width * ratio)), max(1, int(t.height * ratio))), Image.Resampling.LANCZOS)
        x, y = c * cell + (cell - f.width) // 2, 28 + r * cell + 18
        img.paste(f, (x, y), f if f.mode == "RGBA" else None)
        d.text((c * cell + 8, 28 + r * cell + 2), l, fill="#c8d0d8")
    return img


def with_human(grid, g, module):
    """add a pink 1x2 column beside the entrance, outside the structure, at floor level"""
    out = grid.clone()
    if g["doors"]:
        dx, dy, dz = g["doors"][0]
        pos = (dx - 2, 1, dz)
    elif module == "large_pillar_1":
        pos = (-2, 1, 2)
    elif module == "medium_pillar_1":
        pos = (3, 1, -2)
    else:
        pos = (13, 1, 38)
    for dy in (0, 1):
        out.set(pos[0], pos[1] + dy, pos[2], HUMAN)
    return out


def main(modules=None, final_dir=None):
    final_dir = final_dir or S24B
    for m in modules or MODULES:
        root, url, sha = load_original(m)
        orig = Candidate(m, root, url, sha).to_grid()
        fin = grid_of(final_dir / m / "restored.nbt", m)
        g = derive(m, final_dir)
        fin_h, orig_h = with_human(fin, g, m), with_human(orig, g, m)
        d = OUTV / m
        d.mkdir(parents=True, exist_ok=True)
        sy = int(load_nbt(final_dir / m / "restored.nbt")["size"][1])
        # 1. four exterior angles, restored (human reference included) and original
        for name, gr in (("restored", fin_h), ("original", orig_h)):
            labels, tiles = zip(*[render_view(gr, {"yaw": y}) for y in range(4)])
            sheet(list(tiles), list(labels), 4, 420, f"{m} {name}: four exterior angles (pink column = 1.8-block human)").save(d / f"{name}-four-exterior-angles.png")
        # 2. elevated / roof: top-down + two raised iso views
        t = [render_view(fin_h, {"mode": "top-down"}), render_view(fin_h, {"yaw": 1}), render_view(orig_h, {"mode": "top-down"})]
        sheet([x[1] for x in t], ["restored top-down (roof)", "restored elevated yaw90", "original top-down"], 3, 520, f"{m}: roof / elevated").save(d / "roof-and-elevated.png")
        # 3. entrance close-up: crop around the entry cell
        ex = (g["doors"][0] if g["doors"] else {"large_pillar_1": [0, 2, 2], "medium_pillar_1": [3, 1, 0], "sauna_1": [13, 1, 36]}[m])
        near = VoxelGrid()
        for (x, y, z), idx in fin_h.items():
            if abs(x - ex[0]) <= 4 and abs(z - ex[2]) <= 4 and y <= 5:
                near.set(x, y, z, idx)
        t = [render_view(near, {"yaw": y}) for y in range(4)]
        sheet([x[1] for x in t], [x[0] for x in t], 4, 420, f"{m}: entrance close-up with human scale").save(d / "entrance-closeup.png")
        # 4. interior cutaways, one per floor band plus mid-plane x/z cuts
        specs = [{"slice_axis": "y", "slice_at": y, "yaw": 0} for y in range(1, sy, max(1, (sy - 1) // 3))][:4]
        specs += [{"cutaway": "x", "yaw": 1}, {"cutaway": "z", "yaw": 0}]
        t = [render_view(fin, s) for s in specs]
        sheet([x[1] for x in t], [x[0] for x in t], 3, 420, f"{m}: interior cutaways (floor slices and mid-plane cuts)").save(d / "interior-cutaways.png")
        # 5. original-versus-restored
        a = render_view(orig_h, {"yaw": 0})[1]
        b = render_view(fin_h, {"yaw": 0})[1]
        c = render_view(orig_h, {"yaw": 2})[1]
        e = render_view(fin_h, {"yaw": 2})[1]
        sheet([a, b, c, e], ["original yaw0", "restored yaw0", "original yaw180", "restored yaw180"], 2, 520, f"{m}: original vs final").save(d / "original-versus-restored.png")
        print("rendered", m, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
