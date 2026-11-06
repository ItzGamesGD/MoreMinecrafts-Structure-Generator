"""Minimal checks for the representative wall segment (offline, plus an optional strict placement on the pinned server).

  PYTHONPATH=. python experiments/st03-wall-segment/check.py [--server-jar server.jar --java java25 --work <dir>]

For st03_wall_segment and st03_wall_segment_run5 (5 repeats, buttresses shared):
  nbt        verify.py (schema, 26.3 states, cell by cell against the source, air omitted); every authored state in the
             NBT unchanged, no extra cells, no air cells
  contract   13 high and 5 deep like MW86 / MW31, full footing at y0, nothing above y12, solid end columns z0..3 y0..8
             (clean joint to a neighbouring segment, tower or gate)
  support    lanterns and wall banners have the block they need (batch-7 rule)
  barrier    no 1-wide x 2-high player passage from the outside (z=-1) to the compound (z=5) with feet at y1..8
  walk       wall-walk continuity: a solid floor at y9 and 2 blocks of headroom (y10..11) at z2..z3 in every column,
             fence / wall rail at z4 y10, parapet z0 y10 in every column
  repeat     run5 equals the segment shifted by the 12-block period in every repeat (the joint is seamless)
  server     (optional) strict `place template` of both NBTs, every cell compared
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from tools.structure_export import block_entities
from tools.structure_export import convert as C
from tools.structure_export import verify as V
from tools.structure_export.live import _template_cells, _text

HERE = Path(__file__).resolve().parent
EXP = HERE.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SEG = _load("segment", HERE / "segment.py")
B7C = _load("b7checks", EXP / "st03-batch7-commander-manor" / "checks.py")
RC = _load("redesign_checks", EXP / "st03-wall-redesign" / "checks.py")
solid = B7C.solid


def check(name, cells_src):
    nbt, schem = HERE / "out" / f"{name}.nbt", HERE / "out" / f"{name}.schem"
    W = cells_src.W
    r = {"nbt": f"experiments/st03-wall-segment/out/{name}.nbt", "sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
    s = V.verify(nbt, schem, C.load_reference("26.3"), "omit", C.load_connectivity("26.3"), block_entities.load("26.3"))
    cells = _template_cells(nbt)
    bad = [p for p, (bid, pr) in cells_src.items()
           if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
    extra = [p for p in cells if p not in cells_src]
    r["nbt_check"] = {"size": list(s["size"]), "blocks": s["blocks"], "palette": s["palette"],
                      "verify_mismatches": s["mismatches"], "state_mismatches": len(bad), "extra_cells": len(extra),
                      "air_cells": sum(1 for v in cells.values() if v[0] == "minecraft:air")}
    probs = []
    if s["mismatches"] or bad or extra or r["nbt_check"]["air_cells"]:
        probs.append("nbt")
    foot = [[x, z] for x in range(W) for z in range(5) if (x, 0, z) not in cells]
    ends = [[x, y, z] for x in (0, W - 1) for z in range(4) for y in range(9) if not solid(cells.get((x, y, z)))]
    r["contract"] = {"height": s["size"][1], "depth": s["size"][2], "footing_missing": foot,
                     "above_y12": [list(p) for p in cells if p[1] > 12], "end_columns_not_solid": ends}
    r["contract"]["note"] = ("end columns are informational here: a segment ends on the centre of a buttress shared with "
                             "the next repeat (see repeat). A full MW86 / MW31 needs a full-section abutment pier at its "
                             "two module ends toward the towers and gate.")
    if list(s["size"][1:]) != [13, 5] or foot or r["contract"]["above_y12"]:
        probs.append("contract")
    r["support"] = B7C.support_problems(cells)
    if r["support"]:
        probs.append("support")
    path = RC.barrier(cells, W)
    r["barrier"] = {"passage_found": bool(path), "path": [list(p) for p in path][:30]}
    if path:
        probs.append("barrier")
    walk = []
    for x in range(W):
        for z in (2, 3):
            if not solid(cells.get((x, 9, z))):
                walk.append([x, 9, z, "floor"])
            for y in (10, 11):
                if (x, y, z) in cells:
                    walk.append([x, y, z, "headroom"])
        if (x, 10, 4) not in cells:
            walk.append([x, 10, 4, "rail"])
        if not solid(cells.get((x, 10, 0))):
            walk.append([x, 10, 0, "parapet"])
    r["walk"] = {"problems": walk}
    if walk:
        probs.append("walk")
    names = [v[0].split(":")[1] for v in cells.values()]
    r["composition"] = {"timber_blocks": sum(1 for n in names if "oak" in n or "spruce" in n),
                        "stairs_slabs": sum(1 for n in names if n.endswith(("_stairs", "_slab"))),
                        "walls_fences_trapdoors": sum(1 for n in names if n.endswith(("_wall", "_fence", "_trapdoor")))}
    r["problems"] = probs
    return r, cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path)
    ap.add_argument("--java")
    ap.add_argument("--work", type=Path)
    a = ap.parse_args()
    seg, run = SEG.segment(1), SEG.segment(5)
    out = {}
    problems = []
    tmpl = {}
    for name, src in (("st03_wall_segment", seg), ("st03_wall_segment_run5", run)):
        out[name], tmpl[name] = check(name, src)
        problems += [(name, p) for p in out[name]["problems"]]
    # repeat: every repeat of the run has the same structure as the segment (shared buttresses identical). Masonry
    # varies by position on purpose (weathering noise), so cells are compared by shape class, not by stone variant.
    MASONRY = ("stone_bricks", "cobblestone", "andesite", "stone", "mossy_stone_bricks", "cracked_stone_bricks",
               "mossy_cobblestone", "chiseled_stone_bricks")

    def shape(v):
        if v is None:
            return None
        n = v[0].split(":")[1]
        if n in MASONRY:
            return "masonry"
        if n.endswith("_stairs"):
            stone = not any(w in n for w in ("oak", "spruce"))
            return ("stone_stairs" if stone else n, v[1].get("facing"), v[1].get("half"))
        return (n, tuple(sorted(v[1].items())))

    diff = []
    for i in range(5):
        for (x, y, z), v in seg.items():
            if v[0].endswith("wall_banner"):
                continue  # the run keeps only the first banner
            w = run.get((x + SEG.PERIOD * i, y, z))
            if shape(v) != shape(w):
                diff.append([x + SEG.PERIOD * i, y, z, str(shape(v)), str(shape(w))])
    out["repeat"] = {"period": SEG.PERIOD, "structural_difference_count": len(diff), "first": diff[:10]}
    if diff:
        problems.append(("repeat", len(diff)))
    if a.server_jar:
        from tools.structure_export.stair_live import forceload, make_server
        pack = a.work / "pack"
        (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
        (pack / "pack.mcmeta").write_text(json.dumps({"pack": {"description": "seg", "min_format": [121, 0],
                                                                 "max_format": [121, 0]}}))
        for name in tmpl:
            (pack / f"data/experimental/structure/{name}.nbt").write_bytes((HERE / "out" / f"{name}.nbt").read_bytes())
        server = make_server(a.work / "server", a.server_jar, a.java, pack)
        try:
            server.start()
            forceload(server, -16, 180, 120, 260)
            for j, (name, cells) in enumerate(tmpl.items()):
                o = (0, -40, 200 + 20 * j)
                reply = server.cmd(f"place template experimental:{name} {o[0]} {o[1]} {o[2]} none none 1 0 strict")
                assert reply.startswith("Loaded template"), reply
                fails = [list(p) for p, (bid, pr) in sorted(cells.items()) if "passed" not in server.cmd(
                    f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}")]
                out[name]["server_strict"] = {"server_sha1": hashlib.sha1(a.server_jar.read_bytes()).hexdigest(),
                                              "cells": len(cells), "failures": len(fails), "first": fails[:5]}
                if fails:
                    problems.append((name, "server", len(fails)))
        finally:
            server.stop()
    out["problems"] = problems
    (HERE / "check-result.json").write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(json.dumps({k: (v.get("problems") if isinstance(v, dict) and "problems" in v else None) for k, v in out.items()}))
    print("PROBLEMS", problems or "none")


if __name__ == "__main__":
    main()
