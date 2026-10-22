"""Check the processor re-implementation cell by cell against real 26.1.2 worlds, and root-cause every lost block.

For each restored piece in each generated city the template is transformed to world space, every block is run through
tools.stage24g.processors, and the prediction is compared with the block actually present in the saved world.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import OUT, load_nbt, blocks_of  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24c.worldgen_analyze import TARGET, ROT, rot, rotate_state, sort_props, norm  # noqa: E402
from tools.stage24g import processors as P  # noqa: E402

SCULK = ("minecraft:sculk", "minecraft:sculk_vein", "minecraft:sculk_catalyst", "minecraft:sculk_shrieker",
         "minecraft:sculk_sensor")


def same(a, b):
    return a is not None and b is not None and sort_props(norm(a)) == sort_props(norm(b))


MANIFESTS = [OUT / "worldgen"]


def pieces_world(seed, variant):
    f = next(d / f"manifest-{seed}-{variant}.json" for d in MANIFESTS + [OUT / "worldgen"]
             if (d / f"manifest-{seed}-{variant}.json").exists())
    m = json.loads(f.read_text())
    if not m.get("cities"):
        return None, []
    return m, m["cities"][0]["pieces"]


def check(seed, variant, src_root, overlay=None):
    """overlay: {module: set(template positions)} re-placed without block_rot (Stage 24-G list element)."""
    m, pieces = pieces_world(seed, variant)
    wdir = OUT / f"_work/wg-{seed}-{variant}/world/dimensions/minecraft/overworld"
    if m is None or not wdir.exists():
        return None
    world = World(wdir)
    tally, losses = Counter(), []
    piece_cells = []
    for idx, p in enumerate(pieces):
        mod = TARGET.get(p["template"]) or TARGET.get(p.get("overlay_of", ""))
        if not mod:
            continue
        blocks = blocks_of(load_nbt(src_root / mod / "restored.nbt"))
        r, o = ROT[p["rotation"]], p["pos"]
        ov = (overlay or {}).get(mod, set())
        for pos, (st, nb) in blocks.items():
            if st.startswith(("minecraft:jigsaw", "minecraft:structure_void")):
                continue
            rx, ry, rz = rot(pos, r)
            w = (o[0] + rx, o[1] + ry, o[2] + rz)
            got = world.block(*w)
            exp_template = rotate_state(st, r)
            rotted = P.rot_removed(st, w)
            if rotted and pos in ov:
                rotted = False  # overlay pass re-places the block without block_rot
            out = None if rotted else (P.rule_output(st, w) or st)
            if rotted:
                verdict = "pred_rot__world_differs" if not same(got, exp_template) else "pred_rot__world_equal_by_coincidence"
            else:
                exp = rotate_state(out, r) if out == st else out
                if same(got, exp):
                    verdict = "pred_placed__match"
                elif got and P.name(got) in SCULK:
                    verdict = "pred_placed__later_sculk_feature"
                else:
                    verdict = "pred_placed__MISMATCH"
            tally[verdict] += 1
            if not same(got, exp_template) and P.name(st) not in ("minecraft:air", "minecraft:cave_air"):
                if verdict in ("pred_rot__world_differs", "pred_placed__MISMATCH"):
                    rule_air = (not rotted) and out == "minecraft:air"
                    losses.append({"seed": seed, "piece_index": idx, "module": mod, "rotation": p["rotation"],
                                   "template_pos": list(pos), "world": list(w), "expected": st, "got": got,
                                   "cause": "block_rot" if rotted else ("rule_processor_to_air" if rule_air else "unexplained_by_processors")})
        piece_cells.append(mod)
    return {"seed": seed, "variant": variant, "tally": dict(tally), "losses": losses, "modules": piece_cells}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--variant", default="f24")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifests", default=None, help="directory holding manifest-<seed>-<variant>.json")
    ap.add_argument("--inventory", default=None, help="protected-cells.json: model the Stage 24-G overlay pass")
    a = ap.parse_args()
    if a.manifests:
        MANIFESTS.insert(0, Path(a.manifests))
    overlay = None
    if a.inventory:
        overlay = {m: {tuple(e["pos"]) for e in v["overlay"]} for m, v in json.loads(Path(a.inventory).read_text()).items()}
    res = []
    for s in a.seeds:
        r = check(s, a.variant, Path(a.src), overlay)
        if r:
            res.append(r)
            print(s, r["tally"], "losses", Counter(x["cause"] for x in r["losses"]), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1))





def functional_survival(seed, variant, src_root, inv):
    """State of every role-protected cell of every restored piece in a generated city."""
    m_, pieces = pieces_world(seed, variant)
    wdir = OUT / f"_work/wg-{seed}-{variant}/world/dimensions/minecraft/overworld"
    if m_ is None or not wdir.exists():
        return None
    world = World(wdir)
    rows = []
    for idx, p in enumerate(pieces):
        mod = TARGET.get(p["template"])
        if not mod:
            continue
        blocks = blocks_of(load_nbt(src_root / mod / "restored.nbt"))
        fills = {tuple(e["pos"]): e["state"] for e in inv[mod]["overlay"] if blocks[tuple(e["pos"])][0].startswith("minecraft:jigsaw")}
        r, o = ROT[p["rotation"]], p["pos"]
        for e in inv[mod]["protected"]:
            pos = tuple(e["pos"])
            st, nb = blocks[pos]
            if st.startswith("minecraft:jigsaw"):
                if str(nb.get("final_state")) != "minecraft:structure_void":
                    continue  # resolves to a fixed block, never dropped
                st = fills.get(pos, "sturdy support")
            q = rot(pos, r)
            w = (o[0] + q[0], o[1] + q[1], o[2] + q[2])
            got = world.block(*w)
            gn = P.name(got or "minecraft:air")
            want = P.name(st)
            if same(got, rotate_state(st, r)) or gn == want:
                status = "present"
            elif gn == want.replace("minecraft:", "minecraft:cracked_") or gn in SCULK and gn in ("minecraft:sculk",):
                status = "present_weathered"  # cracked by the rule processor or turned to sculk (still a full block)
            elif gn in ("minecraft:air", "minecraft:cave_air") or gn in SCULK:
                status = "MISSING"
            else:
                status = "REPLACED"
            rows.append({"seed": seed, "piece_index": idx, "module": mod, "rotation": p["rotation"], "template_pos": list(pos),
                         "world": list(w), "roles": e["roles"], "expected": st, "got": got, "status": status,
                         "rot_predicted": P.rot_removed(blocks[pos][0], w), "void_jigsaw": blocks[pos][0].startswith("minecraft:jigsaw")})
    return rows


def survival_main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--manifests", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(sys.argv[2:])
    MANIFESTS.insert(0, Path(a.manifests))
    inv = json.loads(Path(a.inventory).read_text())
    rows = []
    for s in a.seeds:
        r = functional_survival(s, a.variant, Path(a.src), inv)
        if r:
            rows += r
            print(s, Counter(x["status"] for x in r), flush=True)
    Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "survival":
        survival_main()
    else:
        main()
