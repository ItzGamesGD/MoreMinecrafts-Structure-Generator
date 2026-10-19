"""Stage 24-F visual evidence: re-run the Stage 24-D model-render gallery on the FINAL candidate set (read-only)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f"
FINAL = D24F / "final-candidates"
ENV = {**os.environ, "STAGE24B_DIR": str(FINAL), "S24D_ROOT": str(D24F), "S24D_BUILD": os.environ.get("S24F_BUILD", "/tmp/s24f-build"),
       "S24D_WG_ANALYSIS": str(D24F / "worldgen/f24-analysis.json"), "S24D_WG_VARIANT": "f24"}
PY = sys.executable

DESIGN = {
    "large_ruin_1": ["Owner-selected Stage 24-E option C, the lancet gatehouse (17×14×17; the +9 height is explicitly authorised).",
                     "Courtyard house with 5-high walls and a low double-pitched ring roof around the open court.",
                     "A steep pointed gable over the entrance range carries a tall lancet window above a polished-basalt portal."],
    "medium_ruin_2": ["Owner-selected Stage 24-E option A, the saltbox (16×8×11, unchanged bounds).",
                      "The hall roof climbs in a long 1:2 slope into a two-step hipped upper storey, so the two masses read as one form.",
                      "The upper floor and its stair run are unchanged and remain reachable."],
}
LIMITS = {
    "large_ruin_1": ["Taller NBT (+9) changes the structure bounding box; see the Stage 24-F generation evidence.",
                     "Interior lanterns hang on iron chains from the new roof; vanilla decay still removes ~5 % of lanterns."],
    "medium_ruin_2": ["The stair-run headroom and upper floor were re-verified with the final roof."],
}
STATUS = ["CODE VERIFIED", "GEOMETRY VERIFIED", "VISUAL PENDING (model renders only)", "LIVE PASS (server + simulated player; real client PENDING)",
          "WORLDGEN — see Stage 24-F evidence", "OWNER REVIEW PENDING"]


def run(*args):
    r = subprocess.run([PY, *args], cwd=ROOT, env=ENV, capture_output=True, text=True)
    print(" ".join(args), "->", r.returncode, r.stdout.strip().splitlines()[-1:] if r.stdout.strip() else "")
    if r.returncode:
        print(r.stderr[-3000:])
        raise SystemExit(r.returncode)


def manifest():
    from tools.stage24b_source import MODULES as SRC, download_original, git_blob_sha1
    from tools.stage24c.common import blocks_of, load_nbt, state_str
    fm = json.loads((D24F / "FINAL-CANDIDATES-MANIFEST.json").read_text())
    build = Path(ENV["S24D_BUILD"])
    (build / "originals").mkdir(parents=True, exist_ok=True)
    out = {"stage": "24-F", "stage_label": "24-F", "storage_key": "stage24f-decisions-v1",
           "gallery_title": "Ancient City restoration — Stage 24-F final candidates",
           "gallery_subtitle": f"Stage 24-F · Minecraft Java 26.1.2 · owner-selected final set (large_ruin_1 option C, medium_ruin_2 option A; others = Stage 24-C {fm['stage_24c_head'][:10]})",
           "repair_label": "Changes vs the Stage 24-C candidate", "zip_name": "stage-24f-final-gallery.zip", "stage_24c_head": fm["stage_24c_head"], "modules": {}}
    for m, v in fm["modules"].items():
        data, url = download_original(m)
        (build / "originals" / f"{m}.nbt").write_bytes(data)
        orig = load_nbt(build / "originals" / f"{m}.nbt")
        fin = load_nbt(FINAL / m / "restored.nbt")
        base = load_nbt(ROOT / "artifacts/ancient-city-restoration/stage-24b" / m / "restored.nbt")

        def ents(r):
            pal = [state_str(p) for p in r["palette"]]
            return {tuple(int(x) for x in b["pos"]): (pal[int(b["state"])], str(b["nbt"])) for b in r["blocks"] if "nbt" in b}
        oe, fe = ents(orig), ents(fin)
        bb, fb = blocks_of(base), blocks_of(fin)
        changes = [p for p in set(bb) | set(fb) if bb.get(p, ("minecraft:air",))[0] != fb.get(p, ("minecraft:air",))[0]]
        kinds = {}
        for p in changes:
            k = f"{bb.get(p, ('minecraft:air',))[0].split('[')[0][10:]} -> {fb.get(p, ('minecraft:air',))[0].split('[')[0][10:]}"
            kinds[k] = kinds.get(k, 0) + 1
        out["modules"][m] = {"candidate_sha256": v["final_sha256"], "source_blob_sha1": git_blob_sha1(data), "source_url": url,
                             "final_dimensions_xyz": v["dimensions"], "original_dimensions_xyz": [int(x) for x in orig["size"]],
                             "jigsaws": {"original": sum(1 for s, _ in oe.values() if "jigsaw" in s), "final": sum(1 for s, _ in fe.values() if "jigsaw" in s)},
                             "block_entities": {"original": len(oe), "final": len(fe), "all_original_entities_identical": all(fe.get(p) == x for p, x in oe.items())},
                             "stage24c_repair": {"changed_cells_vs_pr10": len(changes), "by_kind": dict(sorted(kinds.items(), key=lambda kv: -kv[1]))}}
        assert git_blob_sha1(data) == SRC[m]["sha1"] and out["modules"][m]["block_entities"]["all_original_entities_identical"]
    (D24F / "INPUT-MANIFEST.json").write_text(json.dumps(out, indent=1))
    (D24F / "content-overrides.json").write_text(json.dumps({"DESIGN": DESIGN, "LIMITS": LIMITS, "STATUS": STATUS}, indent=1))


def stage24c_vs_final():
    """Stage 24-C candidate vs final candidate for the two changed modules, identical camera and scale"""
    code = r'''
import sys, json
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
from tools.stage24d.lib import scene_of_nbt, write_scene, run_jobs, BUILD, TITLES, D24
from tools.stage24d.config import CFG
from tools.stage24d.render_gallery import font
ROOT = Path(".")
OUT = D24 / "gallery/assets"
views = [("front34", -45, 28), ("rear34", 135, 28), ("street", 0, 4), ("side", -90, 0)]
jobs = []
for m, scale in (("large_ruin_1", 22), ("medium_ruin_2", 26)):
    fa = CFG[m]["front_az"]
    sizes = {}
    for key, path in (("stage24c", ROOT / "artifacts/ancient-city-restoration/stage-24b" / m / "restored.nbt"), ("final", D24 / "final-candidates" / m / "restored.nbt")):
        sc, size = scene_of_nbt(path); sizes[key] = size
        sp = write_scene(f"24f-{m}-{key}", sc)
        for vn, off, el in views:
            jobs.append(dict(scene=str(sp), w=760, h=620, az=(fa + off) % 360, el=el, scale=scale, out=str(BUILD / "png24f" / m / f"{key}-{vn}.png")))
    H = max(s[1] for s in sizes.values())
    for j in jobs[-8:]:
        j["target"] = [sizes["final"][0] / 2, H / 2 - 0.5, sizes["final"][2] / 2]
assert run_jobs(jobs, "24f-vs") == 0
for m in ("large_ruin_1", "medium_ruin_2"):
    for vn, off, el in views:
        im = Image.new("RGB", (1520, 690), (30, 34, 41)); d = ImageDraw.Draw(im)
        for i, key in enumerate(("stage24c", "final")):
            im.paste(Image.open(BUILD / "png24f" / m / f"{key}-{vn}.png").convert("RGB").resize((760, 620)), (i * 760, 44))
        d.text((10, 6), f"{TITLES[m]} — Stage 24-C candidate (left) vs Stage 24-F final (right), identical camera and scale", fill=(236, 240, 245), font=font(15, True))
        d.text((10, 26), "Minecraft 26.1.2 block models + textures · studio lighting · model renders, NOT client screenshots", fill=(160, 170, 182), font=font(11))
        out = OUT / m / f"stage24c-vs-final-{vn}.jpg"; out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "JPEG", quality=84, optimize=True, progressive=True)
print("ok")
'''
    r = subprocess.run([PY, "-c", code], cwd=ROOT, env=ENV, capture_output=True, text=True)
    print("stage24c-vs-final ->", r.returncode, r.stdout.strip()[-80:])
    if r.returncode:
        print(r.stderr[-3000:])
        raise SystemExit(1)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("all", "render"):
        manifest()
        run("tools/stage24d/render_gallery.py")
        run("tools/stage24d/priority.py")
        stage24c_vs_final()
    if step in ("all", "v5-extract"):
        run("tools/stage24d/v5.py", "extract")
    if step in ("all", "finish"):
        run("tools/stage24d/v5.py")
        run("tools/stage24d/build_gallery.py")
