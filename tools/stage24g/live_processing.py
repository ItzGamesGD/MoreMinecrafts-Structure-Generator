"""Real-server check of the Stage 24-G pool elements with the actual 26.1.2 processors, all eight modules x 4 rotations.

`/place jigsaw` runs JigsawPlacement + PoolElementStructurePiece.place exactly as world generation does (the element's
processor lists apply).  Two test pools per module reference the same templates:
  s24gtest:g24/<m>  the Stage 24-G entry (list element with the protection overlay where the module has one)
  s24gtest:f24/<m>  the Stage 24-F entry (plain single element, ancient_city_generic_degradation)
The layer under the placement is cleared to air first so a cell the template leaves unwritten (jigsaw with
final_state structure_void) stays visibly empty, as it does over a cave.  Rotation is random per placement; placements
repeat until every rotation has been seen, then rotation/origin are recovered by matching the template.
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
from tools.stage24c.worldgen_analyze import rot, rotate_state, sort_props, norm  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402
from tools.stage24g.build import D24G, D24F, OVERLAY_ID, TEMPLATE_ID, PROTECTION_LIST  # noqa: E402

FLAT = '{"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:stone","height":3}],"biome":"minecraft:plains"}'
Y0 = -61
ROTS = {0: "NONE", 90: "CLOCKWISE_90", 180: "CLOCKWISE_180", 270: "COUNTERCLOCKWISE_90"}
SCULK = {"minecraft:sculk", "minecraft:sculk_vein", "minecraft:sculk_catalyst", "minecraft:sculk_shrieker", "minecraft:sculk_sensor"}


def same(a, b):
    return a is not None and b is not None and sort_props(norm(a)) == sort_props(norm(b))


def test_pack(dest: Path, pack_src: Path):
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(pack_src, dest)
    pool = json.loads((pack_src / "data/minecraft/worldgen/template_pool/ancient_city/structures.json").read_text())
    entries = {}
    for e in pool["elements"]:
        el = e["element"]
        loc = el.get("location") or (el.get("elements") or [{}])[0].get("location", "")
        for m in MODULES:
            if loc == TEMPLATE_ID.format(m=m):
                entries[m] = el
    for m in MODULES:
        f24 = {"element_type": "minecraft:single_pool_element", "location": TEMPLATE_ID.format(m=m),
               "processors": "minecraft:ancient_city_generic_degradation", "projection": "rigid"}
        for kind, el in (("g24", entries[m]), ("f24", f24)):
            p = dest / f"data/s24gtest/worldgen/template_pool/{kind}/{m}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"fallback": "minecraft:empty", "elements": [{"element": el, "weight": 1}]}, indent=1))


def locate(world, blocks, cmd_pos, size):
    """Recover rotation and origin: try every rotation and every connect_structure jigsaw as the anchor."""
    anchors = [p for p, (s, nb) in blocks.items() if s.startswith("minecraft:jigsaw") and str(nb.get("name")) == "minecraft:connect_structure"]
    probe = [(p, s) for p, (s, _) in blocks.items() if not s.startswith(("minecraft:jigsaw", "minecraft:air", "minecraft:structure_void"))
             and not P.name(s) in P.ANCIENT_CITY_REPLACEABLE][:400]
    best = None
    for r in ROTS:
        for a in anchors:
            ra = rot(a, r)
            # JigsawPlacement.addPieces anchors the named jigsaw on the position, then moves the start piece down by
            # its groundLevelDelta (1 for single and list elements)
            o = (cmd_pos[0] - ra[0], cmd_pos[1] - ra[1] - 1, cmd_pos[2] - ra[2])
            hit = 0
            for p, s in probe:
                q = rot(p, r)
                if same(world.block(o[0] + q[0], o[1] + q[1], o[2] + q[2]), rotate_state(s, r)):
                    hit += 1
            if best is None or hit > best[0]:
                best = (hit, r, o)
    return {"rotation": best[1], "origin": list(best[2]), "match": best[0], "probe": len(probe)}


def analyse(world, m, kind, loc, protected, overlay_cells, fill_cells):
    blocks = blocks_of(load_nbt(D24F / m / "restored.nbt"))
    r, o = loc["rotation"], loc["origin"]
    W = lambda p: tuple(o[i] + rot(p, r)[i] for i in range(3))  # noqa: E731
    c = Counter()
    prot_lost, unexplained = [], []
    for p, (st, nb) in blocks.items():
        if st.startswith("minecraft:structure_void"):
            continue
        w = W(p)
        got = world.block(*w)
        if st.startswith("minecraft:jigsaw"):
            final = str(nb.get("final_state", "minecraft:air"))
            if final == "minecraft:structure_void":
                if kind == "g24" and p in fill_cells:
                    exp = P.rule_output(fill_cells[p], w) or fill_cells[p]
                    ok = same(got, exp)
                    c["void_support_filled" if ok else "void_support_FILL_MISSING"] += 1
                    if not ok:
                        prot_lost.append({"pos": list(p), "world": list(w), "expected": exp, "got": got, "role": "door_support"})
                else:
                    c["void_left_unwritten"] += 1
                    if p in protected:
                        prot_lost.append({"pos": list(p), "world": list(w), "expected": "sturdy support", "got": got, "role": "door_support",
                                          "cause": "jigsaw final_state structure_void leaves the cell unwritten"})
            continue
        rotted = P.rot_removed(st, w)
        restored = rotted and kind == "g24" and p in overlay_cells
        out = None if (rotted and not restored) else (P.rule_output(st, w) or st)
        exp = None if out is None else (rotate_state(out, r) if out == st else out)
        is_prot = p in protected
        rottable = P.name(st) in P.ANCIENT_CITY_REPLACEABLE
        if exp is None:
            ok = got is None or not same(got, rotate_state(st, r))
            c["rot_removed_protected" if is_prot else "rot_removed_decorative"] += 1
            if is_prot:
                prot_lost.append({"pos": list(p), "world": list(w), "expected": st, "got": got, "role": protected[p], "cause": "block_rot"})
        else:
            ok = same(got, exp)
            if restored:
                c["rot_then_restored_by_overlay"] += 1
            if out != st:
                c["rule_" + P.name(out).replace("minecraft:", "")] += 1
        if rottable and not is_prot:
            c["decorative_rottable_cells"] += 1
        if rottable and is_prot:
            c["protected_rottable_cells"] += 1
        c["cells"] += 1
        if not ok and got and P.name(got) in SCULK:
            c["later_sculk_feature_overlay"] += 1  # sculk patch features of the sauna's ancient_city/sculk jigsaw children
            ok = True
        if not ok:
            unexplained.append({"pos": list(p), "world": list(w), "expected": exp, "got": got})
    # final functional state of protected cells as actually present in the world
    present = sum(1 for p in protected if p in blocks and not blocks[p][0].startswith(("minecraft:jigsaw", "minecraft:structure_void"))
                  and (world.block(*W(p)) or "minecraft:air").split("[")[0] not in ("minecraft:air", "minecraft:cave_air"))
    return {"counts": dict(c), "protected_lost": prot_lost, "unexplained": unexplained[:20], "unexplained_count": len(unexplained),
            "protected_cells": len(protected), "protected_non_air_present": present}


def main(out_dir: Path, per_module_max=16, modules=None, kinds=("g24", "f24"), x_base=300):
    work = OUT / "_work/s24g-live"
    pack = work / "pack"
    test_pack(pack, D24G / "datapack")
    inv = json.loads((D24G / "protection/protected-cells.json").read_text())
    srv = Server(work / "server", JAR, JAVA, {"level-type": "minecraft\\:flat", "generator-settings": FLAT,
                                               "generate-structures": "false"}, datapack=pack).start()
    report = {"datapack_list": srv.cmd("datapack list"), "placements": []}
    try:
        plan = []
        for mi, m in enumerate(MODULES):
            if modules and m not in modules:
                continue
            size = [int(v) for v in load_nbt(D24F / m / "restored.nbt")["size"]]
            span = max(size[0], size[2]) + 6
            for kind in kinds:
                for k in range(per_module_max):
                    x = x_base + mi * 160 + (0 if kind == "g24" else 80)
                    z = 300 + k * (span + 40)
                    plan.append((m, kind, k, (x, Y0, z), span))
        seen = {}
        for m, kind, k, pos, span in plan:
            if len(seen.get((m, kind), set())) == 4 and k >= 4:
                continue
            x, y, z = pos
            srv.cmd(f"forceload add {x - span} {z - span} {x + span} {z + span}")
            time.sleep(0.4)
            srv.cmd(f"fill {x - span} {y} {z - span} {x + span} {y} {z + span} minecraft:air")
            # command one above Y0: after the groundLevelDelta shift the template floor (y=0) occupies the cleared layer
            outp = srv.cmd(f"place jigsaw s24gtest:{kind}/{m} minecraft:connect_structure 1 {x} {y + 1} {z}")
            srv.flush()
            w = World(srv.root / "world/dimensions/minecraft/overworld")
            blocks = blocks_of(load_nbt(D24F / m / "restored.nbt"))
            loc = locate(w, blocks, (x, y + 1, z), None)
            seen.setdefault((m, kind), set()).add(loc["rotation"])
            report["placements"].append({"module": m, "kind": kind, "attempt": k, "command_pos": list(pos), "place_output": outp, **loc})
            print(m, kind, k, ROTS[loc["rotation"]], loc["match"], "/", loc["probe"], outp[:50], flush=True)
        srv.cmd("tick sprint 400")
        time.sleep(12)
        srv.flush()
        w = World(srv.root / "world/dimensions/minecraft/overworld")
        for pl in report["placements"]:
            m = pl["module"]
            protected = {tuple(e["pos"]): e["roles"] for e in inv[m]["protected"]}
            ov = {tuple(e["pos"]): e["state"] for e in inv[m]["overlay"]}
            fill = {p: s for p, s in ov.items() if blocks_of(load_nbt(D24F / m / "restored.nbt")).get(p, ("",))[0].startswith("minecraft:jigsaw")}
            pl["analysis"] = analyse(w, m, pl["kind"], pl, protected, ov, fill)
            a = pl["analysis"]
            print(m, pl["kind"], ROTS[pl["rotation"]], "prot_lost", len(a["protected_lost"]), "unexpl", a["unexplained_count"],
                  {k: v for k, v in a["counts"].items() if k.startswith(("rot_", "void", "rule_"))}, flush=True)
    finally:
        srv.stop()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "live-processing-report.json").write_text(json.dumps(report, indent=1, default=list))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(D24G / "live"))
    ap.add_argument("--max", type=int, default=16)
    ap.add_argument("--modules", nargs="*")
    ap.add_argument("--kinds", nargs="*", default=["g24", "f24"])
    ap.add_argument("--x-base", type=int, default=300)
    a = ap.parse_args()
    main(Path(a.out), a.max, a.modules, a.kinds, a.x_base)
