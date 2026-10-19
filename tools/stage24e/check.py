"""Static functional checks for every Stage 24-E proposal against the Stage 24-C baseline (no NBT is modified)."""
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, S24B, blocks_of, load_nbt  # noqa: E402
from tools.validate_stage24b import reachable, standable  # noqa: E402
from tools.stage24e.designs import DESIGNS  # noqa: E402

D24E = Path(__file__).resolve().parents[2] / "artifacts/ancient-city-restoration/stage-24e"
ROTTABLE = {"deepslate", "deepslate_bricks", "deepslate_tiles", "deepslate_brick_slab", "deepslate_tile_slab", "deepslate_brick_stairs",
            "deepslate_tile_wall", "deepslate_brick_wall", "cobbled_deepslate", "cracked_deepslate_bricks", "cracked_deepslate_tiles", "gray_wool"}


class Grid:
    def __init__(self, path):
        r = load_nbt(path)
        self.size = [int(v) for v in r["size"]]
        self.b = blocks_of(r)

    def get_block(self, p):
        return self.b.get(tuple(p), ("minecraft:air", None))[0]


def bid(s):
    return s.split("[")[0].replace("minecraft:", "")


def access_cells(g, pos):
    x, y, z = pos
    return {q for q in ((x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1)) if standable(g, q)}


def check(module, path, base: Grid):
    g = Grid(path)
    res = {"dimensions": g.size, "baseline_dimensions": base.size,
           "footprint_unchanged": g.size[0] == base.size[0] and g.size[2] == base.size[2],
           "height_change": g.size[1] - base.size[1]}
    ents_b = {p: (s, str(n)) for p, (s, n) in base.b.items() if n is not None}
    ents_g = {p: (s, str(n)) for p, (s, n) in g.b.items() if n is not None}
    res["jigsaw_and_block_entities_identical"] = ents_b == ents_g
    doors_b = {p: s for p, (s, _) in base.b.items() if bid(s).endswith("_door")}
    res["doors_unchanged"] = all(g.get_block(p) == s for p, s in doors_b.items())
    beds = [p for p, (s, _) in g.b.items() if bid(s).endswith("_bed")]
    res["beds_unchanged"] = sorted(beds) == sorted(p for p, (s, _) in base.b.items() if bid(s).endswith("_bed"))
    res["beds_unobstructed"] = all(bid(g.get_block((x, y + 1, z))) == "air" for x, y, z in beds)
    door = min(doors_b)
    entry = (door[0] + 1, 1, door[2])
    targets = {}
    for p, (s, _) in g.b.items():
        n = bid(s)
        if n.endswith("_bed") or n in ("barrel", "chest", "crafting_table"):
            targets[f"{n}@{list(p)}"] = access_cells(g, p)
    res["entry_standable"] = standable(g, entry)
    res["reach"] = {k: (reachable(g, entry, v)[0] if v else False) for k, v in targets.items()}
    res["all_furniture_reachable"] = all(res["reach"].values())
    # usable floor: cells reachable from the entry with the Stage 24-B walk model (stairs are the only step-ups)
    res["walkable_cells"], res["baseline_walkable_cells"] = reachable(g, entry, set())[1], reachable(base, entry, set())[1]
    lan = [(p, s) for p, (s, _) in g.b.items() if bid(s) == "soul_lantern"]
    res["lanterns_supported"] = all((g.get_block((p[0], p[1] + 1, p[2])) != "minecraft:air") if "hanging=true" in s else (g.get_block((p[0], p[1] - 1, p[2])) != "minecraft:air") for p, s in lan)
    if module == "medium_ruin_2":
        run = [(4, 1, 5), (5, 2, 5), (6, 3, 5), (7, 4, 5)]
        ok = all(bid(g.get_block(p)) == "deepslate_tile_stairs" for p in run)
        for i, (x, y, z) in enumerate(run):
            for dy in (1, 2) + ((3,) if i < 3 else ()):
                ok &= bid(g.get_block((x, y + dy, z))) == "air"
        res["upper_floor_stair_headroom"] = ok
    new = Counter(bid(s) for p, (s, _) in g.b.items() if base.b.get(p, ("",))[0] != s)
    res["changed_cells"] = sum(new.values())
    res["new_rot_eligible_blocks"] = sum(v for k, v in new.items() if k in ROTTABLE)
    res["new_block_mix"] = dict(new.most_common(8))
    keys = ["footprint_unchanged", "jigsaw_and_block_entities_identical", "doors_unchanged", "beds_unchanged", "beds_unobstructed",
            "entry_standable", "all_furniture_reachable", "lanterns_supported"] + (["upper_floor_stair_headroom"] if module == "medium_ruin_2" else [])
    res["failed_checks"] = [k for k in keys if not res[k]]
    res["static_pass"] = all(res[k] for k in keys) and res["walkable_cells"] >= res["baseline_walkable_cells"] * 0.95
    return res


def main():
    out = {}
    for m, fs in DESIGNS.items():
        base = Grid(S24B / m / "restored.nbt")
        out[m] = {"current": check(m, S24B / m / "restored.nbt", base)}
        for f in fs:
            v = f()
            p = v.save(D24E / "proposals" / m / v.variant / "candidate.nbt")
            r = check(m, p, base)
            r.update({"title": v.title, "requires_authorisation": v.expanded, "notes": v.notes})
            out[m][v.variant] = r
            print(m, v.variant, "PASS" if r["static_pass"] else "FAIL", r["dimensions"], r["walkable_cells"], "/", r["baseline_walkable_cells"],
                  r["failed_checks"])
    (D24E / "static-checks.json").write_text(json.dumps(out, indent=1, default=str))
    # harness trees for live tests: every variant letter becomes one module set (others = current Stage 24-C)
    sets = sorted({k for m in out for k in out[m] if k != "current"})
    for letter in sets:
        root = Path("/tmp/s24e-sets") / letter
        shutil.rmtree(root, ignore_errors=True)
        for mod in MODULES:
            src = D24E / "proposals" / mod / letter / "candidate.nbt"
            dst = root / mod / "restored.nbt"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src if src.exists() else S24B / mod / "restored.nbt", dst)
    print("sets", sets)


if __name__ == "__main__":
    main()
