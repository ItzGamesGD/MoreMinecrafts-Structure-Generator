"""Real 26.1.2 server test of the interior-clearance overlay (8 modules x 4 rotations).

For each placement the volume around the anchor is first filled with a "terrain" block (deepslate, or lava source
blocks), then the pool entry is placed with `/place jigsaw` (real JigsawPlacement + real processor lists). Every cell
of the piece box and a 1-block ring around it is then classified:
  stored cell        must match the 26.1.2 processor model (incl. Stage 24-G protection); a block_rot drop keeps the fill
  mask cell          must be air (Stage 24-H) / keeps the fill (Stage 24-G, the "before" state)
  other cell         unstored non-mask cell or the ring outside the box: must still hold the fill (no excavation)
Lava mode additionally ticks the world (fluid flow) and records which mask cells hold lava afterwards.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, JAR, JAVA, OUT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.mcserver import Server, World  # noqa: E402
from tools.stage24c.worldgen_analyze import rot, rotate_state  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g.build import TEMPLATE_ID  # noqa: E402
from tools.stage24g.live_processing import FLAT, Y0, ROTS, locate, same  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24F = ROOT / "artifacts/ancient-city-restoration/stage-24f/final-candidates"
D24G = ROOT / "artifacts/ancient-city-restoration/stage-24g"
D24H = ROOT / "artifacts/ancient-city-restoration/stage-24h"
SCULK = {"minecraft:sculk", "minecraft:sculk_vein", "minecraft:sculk_catalyst", "minecraft:sculk_shrieker", "minecraft:sculk_sensor"}


def pool_entries(pack: Path):
    pool = json.loads((pack / "data/minecraft/worldgen/template_pool/ancient_city/structures.json").read_text())
    out = {}
    for e in pool["elements"]:
        el = e["element"]
        loc = el.get("location") or (el.get("elements") or [{}])[0].get("location", "")
        for m in MODULES:
            if loc == TEMPLATE_ID.format(m=m):
                out[m] = el
    return out


def test_pack(dest: Path):
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(D24H / "datapack", dest)
    for kind, src in (("h24", D24H / "datapack"), ("g24", D24G / "datapack")):
        for m, el in pool_entries(src).items():
            p = dest / f"data/s24htest/worldgen/template_pool/{kind}/{m}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"fallback": "minecraft:empty", "elements": [{"element": el, "weight": 1}]}, indent=1))


def fill(srv, x0, y0, z0, x1, y1, z1, block):
    for y in range(y0, y1 + 1):  # one layer per command keeps every fill under the 32768-block limit
        srv.cmd(f"fill {x0} {y} {z0} {x1} {y} {z1} {block}")


def analyse(world, m, kind, loc, inv, mask, fill_block, after_ticks=False):
    blocks = blocks_of(load_nbt(D24F / m / "restored.nbt"))
    size = [int(v) for v in load_nbt(D24F / m / "restored.nbt")["size"]]
    r, o = loc["rotation"], loc["origin"]
    W = lambda p: tuple(o[i] + rot(p, r)[i] for i in range(3))  # noqa: E731
    prot = {tuple(e["pos"]) for e in inv[m]["protected"]}
    ov = {tuple(e["pos"]): e["state"] for e in inv[m]["overlay"]}
    c, bad = Counter(), []
    fill_name = "minecraft:" + fill_block

    def flag(kind_, p, w, exp, got):
        c[kind_] += 1
        if len(bad) < 40:
            bad.append({"type": kind_, "template_pos": list(p), "world": list(w), "expected": exp, "got": got})

    for x in range(-1, size[0] + 1):
        for y in range(0, size[1] + 1):
            for z in range(-1, size[2] + 1):
                p = (x, y, z)
                w = W(p)
                got = world.block(*w)
                gn = P.name(got or "minecraft:air")
                inside = 0 <= x < size[0] and 0 <= z < size[2] and y < size[1]
                if p in blocks:
                    st, nb = blocks[p]
                    if st.startswith("minecraft:jigsaw"):
                        f = str(nb.get("final_state", "minecraft:air"))
                        exp = ov.get(p) if f == "minecraft:structure_void" else f
                        if exp is None:
                            continue  # unwritten jigsaw cell with no supplied support: keeps the fill
                        exp = P.rule_output(exp, w) or exp
                    else:
                        dropped = P.rot_removed(st, w) and p not in ov
                        if dropped:
                            c["stored_rot_dropped_keeps_fill" if gn == fill_name else "stored_rot_dropped_other"] += 1
                            continue
                        exp = P.rule_output(st, w) or st
                        exp = rotate_state(exp, r) if exp == st else exp
                    if same(got, exp):
                        c["stored_ok"] += 1
                    elif gn in SCULK:
                        c["stored_later_sculk"] += 1  # sculk-patch children of the sauna's sculk jigsaws (vanilla)
                    elif P.name(exp) in ("minecraft:air",) and gn == fill_name:
                        flag("STORED_AIR_NOT_WRITTEN", p, w, exp, got)
                    elif after_ticks and gn in ("minecraft:lava", "minecraft:obsidian", "minecraft:cobblestone", "minecraft:stone"):
                        c["stored_changed_by_fluid_after_ticks"] += 1
                    else:
                        flag("ARCHITECTURE_MISMATCH", p, w, exp, got)
                    if p in prot and not same(got, exp) and gn not in SCULK:
                        flag("PROTECTED_CELL_LOST", p, w, exp, got)
                elif inside and p in mask:
                    if kind == "h24":
                        if gn == "minecraft:air":
                            c["mask_cleared"] += 1
                        elif gn in SCULK:
                            c["mask_later_sculk"] += 1
                        elif after_ticks and gn in ("minecraft:lava", "minecraft:water"):
                            flag("MASK_FLUID_RETURNED", p, w, "air", got)
                        else:
                            flag("MASK_NOT_CLEARED", p, w, "air", got)
                    else:
                        c["mask_keeps_fill_g24" if gn == fill_name else "mask_other_g24"] += 1
                else:
                    if gn == fill_name:
                        c["outside_mask_untouched"] += 1
                    elif after_ticks and gn in ("minecraft:lava", "minecraft:air", "minecraft:obsidian", "minecraft:cobblestone", "minecraft:stone"):
                        c["outside_mask_fluid_flow"] += 1
                    else:
                        flag("EXCAVATED_OUTSIDE_MASK", p, w, fill_name, got)
    return {"counts": dict(c), "violations": bad}


def main(out_dir: Path, max_attempts=12, lava_per_module=1):
    work = OUT / "_work/s24h-live"
    pack = work / "pack"
    test_pack(pack)
    inv = json.loads((D24G / "protection/protected-cells.json").read_text())
    masks = json.loads((D24H / "mask/interior-masks.json").read_text())
    srv = Server(work / "server", JAR, JAVA, {"level-type": "minecraft\\:flat", "generator-settings": FLAT,
                                               "generate-structures": "false"}, datapack=pack, heap="3G").start()
    report = {"datapack_list": srv.cmd("datapack list"), "placements": []}
    try:
        for mi, m in enumerate(MODULES):
            root = load_nbt(D24F / m / "restored.nbt")
            size = [int(v) for v in root["size"]]
            blocks = blocks_of(root)
            mask = {tuple(p) for v in masks[m]["cleared"].values() for p in v}
            span = max(size[0], size[2]) + 3
            plan = [("h24", "deepslate")] * max_attempts + [("g24", "deepslate")] + [("h24", "lava")] * lava_per_module
            seen = set()
            for k, (kind, fb) in enumerate(plan):
                if kind == "h24" and fb == "deepslate" and len(seen) == 4:
                    continue
                x, z = 4000 + mi * 200, 4000 + k * (2 * span + 30)
                srv.cmd(f"forceload add {x - span - 2} {z - span - 2} {x + span + 2} {z + span + 2}")
                time.sleep(0.4)
                fill(srv, x - span, Y0, z - span, x + span, Y0 + size[1] + 1, z + span, fb)
                outp = srv.cmd(f"place jigsaw s24htest:{kind}/{m} minecraft:connect_structure 1 {x} {Y0 + 1} {z}")
                srv.flush()
                w = World(srv.root / "world/dimensions/minecraft/overworld")
                loc = locate(w, blocks, (x, Y0 + 1, z), None)
                rec = {"module": m, "kind": kind, "fill": fb, "command_pos": [x, Y0 + 1, z], "place_output": outp, **loc}
                rec["analysis"] = analyse(w, m, kind, loc, inv, mask, fb)
                if fb == "lava":
                    srv.cmd("tick sprint 1200")
                    time.sleep(15)
                    srv.flush()
                    rec["analysis_after_1200_ticks"] = analyse(World(srv.root / "world/dimensions/minecraft/overworld"), m, kind, loc, inv, mask, fb, after_ticks=True)
                if kind == "h24" and fb == "deepslate":
                    seen.add(loc["rotation"])
                report["placements"].append(rec)
                a = rec["analysis"]
                print(m, kind, fb, ROTS[loc["rotation"]], loc["match"], "/", loc["probe"],
                      {k_: v for k_, v in a["counts"].items()}, "VIOL", Counter(v["type"] for v in a["violations"]),
                      rec.get("analysis_after_1200_ticks", {}).get("counts", ""), flush=True)
    finally:
        srv.stop()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "live-clearance-report.json").write_text(json.dumps(report, indent=1, default=list))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24H / "live"))
    ap.add_argument("--max", type=int, default=12)
    a = ap.parse_args()
    main(Path(a.out), a.max)
