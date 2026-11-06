"""Checks for the three wall design prototypes (same conditions as batch 8, plus a defence check).

  PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/checks.py \\
      --server-jar server.jar --java java25 --work <dir> [--offline] [--designs a,b,c]

Per design, per module (MW86, MW31), written to check-result.json:
  nbt         independent verify.py (schema, every state valid for 26.3, cell-by-cell vs source, air=omit), size =
              placement-table module size, every authored state in the NBT unchanged, no extra cells, no air cells
  support     every lantern and wall banner has the block it needs (batch-7 rule)
  footing     a footing block at y=0 under every one of the L x 5 columns (the Q89 below-grade fill builds on it)
  ends        both end columns solid over z0..3, y0..8 (clean abutment to the tower square / gate, no gap)
  top         every column reaches at least y9 (parapet sill / gallery) and nothing exceeds y12; both ends reach y12
  barrier     defence: no opening a player (1 wide x 2 high) can pass from the exterior (z=-1) to the compound side
              (z=5) with feet at y1..8 - i.e. below the wall-walk; vertical movement inside openings is allowed
              (pessimistic: climbing), banners / carpets / lanterns / open trapdoors count as passable
  boundaries  q=0..3 against the tower squares and the gate (batch-8 function, geometry only, design independent)
  server      strict `place template` of both NBTs (rotation none), every cell compared; the three slope sites of
              batch-8 slope.py with the Q89 footing fill: every template cell, no hollow cell, terrain outside untouched
Rotations and the integrated q=0 layout with every built facility: place_check.py --perimeter-dir out/<design>.
"""

import argparse
import hashlib
import importlib.util
import json
from collections import deque
from pathlib import Path

from tools.seam01 import assembly as A
from tools.structure_export import block_entities
from tools.structure_export import convert as C
from tools.structure_export import verify as V
from tools.structure_export.live import _template_cells, _text
from tools.structure_export.stair_live import forceload, make_server

HERE = Path(__file__).resolve().parent
EXP = HERE.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B7C = _load("b7checks", EXP / "st03-batch7-commander-manor" / "checks.py")
B8C = _load("b8checks", EXP / "st03-batch8-perimeter-walls" / "checks.py")
SL = B8C.SL
support_problems, solid = B7C.support_problems, B7C.solid
BUILD = _load("redesign_build", HERE / "build.py")
PASSABLE = ("_banner", "moss_carpet", "lantern")


def open_cell(cell):
    if cell is None or cell[0] == "minecraft:air":
        return True
    n = cell[0].split(":")[1]
    if n.endswith(PASSABLE):
        return True
    return n.endswith("_trapdoor") and cell[1].get("open") == "true"


def barrier(cells, L):
    """BFS over 1x2 player positions; returns the first passage found (list of positions) or []."""
    ok = lambda x, y, z: z in (-1, 5) or (open_cell(cells.get((x, y, z))) and open_cell(cells.get((x, y + 1, z))))
    start = [(x, y, -1) for x in range(L) for y in range(1, 9)]
    prev = {p: None for p in start}
    q = deque(start)
    while q:
        p = q.popleft()
        if p[2] == 5:
            path = []
            while p:
                path.append(p)
                p = prev[p]
            return path[::-1]
        x, y, z = p
        for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in prev or not (0 <= n[0] < L and 1 <= n[1] <= 8 and -1 <= n[2] <= 5):
                continue
            if ok(*n):
                prev[n] = p
                q.append(n)
    return []


def module_checks(key, mid, cells_src, nbt, schem):
    module = A.modules()[mid]
    L = module["size"][0]
    m = {"nbt": str(nbt.relative_to(EXP.parent)), "nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
    s = V.verify(nbt, schem, C.load_reference("26.3"), "omit", C.load_connectivity("26.3"), block_entities.load("26.3"))
    assert list(s["size"]) == module["size"], s["size"]
    m["verify"] = {k: (list(s[k]) if k == "size" else s[k])
                   for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
    cells = _template_cells(nbt)
    bad = [list(p) for p, (bid, pr) in cells_src.items()
           if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
    extra = [list(p) for p in cells if p not in cells_src]
    m["states"] = {"authored_cells_checked": len(cells_src), "mismatches": len(bad), "cells_not_authored": len(extra),
                   "air_cells_in_nbt": sum(1 for v in cells.values() if v[0] == "minecraft:air")}
    probs = []
    if s["mismatches"] or bad or extra or m["states"]["air_cells_in_nbt"]:
        probs.append("nbt/states")
    m["support"] = {"unsupported": support_problems(cells)}
    if m["support"]["unsupported"]:
        probs.append("support")
    miss = [[x, z] for x in range(L) for z in range(5) if (x, 0, z) not in cells]
    m["footing"] = {"columns": L * 5, "missing": miss}
    if miss:
        probs.append("footing")
    holes = [[x, y, z] for x in (0, L - 1) for z in range(4) for y in range(9) if not solid(cells.get((x, y, z)))]
    m["ends"] = {"not_solid": holes}
    if holes:
        probs.append("ends")
    tops = {x: max([y for (cx, y, cz), v in cells.items() if cx == x and solid(v)] or [-1]) for x in range(L)}
    over = [p for p in cells if p[1] > 12]
    m["top"] = {"min_column_top": min(tops.values()), "max": max(tops.values()), "end_tops": [tops[0], tops[L - 1]],
                "profile_counts": {str(k): list(tops.values()).count(k) for k in sorted(set(tops.values()))}}
    if min(tops.values()) < 9 or over or tops[0] != 12 or tops[L - 1] != 12:
        probs.append("top")
    path = barrier(cells, L)
    m["barrier"] = {"passage_found": bool(path), "path": [list(p) for p in path][:40]}
    if path:
        probs.append("barrier")
    names = [v[0].split(":")[1] for v in cells.values()]
    wood = sum(1 for n in names if any(w in n for w in ("oak", "spruce")))
    m["counts"] = {i: names.count(i) for i in ("lantern", "white_wall_banner", "barrel", "hay_block")}
    m["composition"] = {"blocks": len(names), "timber_blocks": wood, "timber_share": round(wood / len(names), 3),
                        "stairs_and_slabs": sum(1 for n in names if n.endswith(("_stairs", "_slab"))),
                        "fences_walls_trapdoors": sum(1 for n in names if n.endswith(("_fence", "_wall", "_trapdoor"))),
                        "distinct_states": s["palette"]}
    m["problems"] = probs
    return m, cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--designs", default="a,b,c")
    ap.add_argument("--out", type=Path, default=HERE / "check-result.json")
    a = ap.parse_args()
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    keys = a.designs.split(",")
    r = {"server_sha1": sha, "designs": {}}
    problems, tmpl = [], {}
    for key in keys:
        d = BUILD.design(key)
        r["designs"][key] = {}
        for mid, fn in (("MW86", d.mw86), ("MW31", d.mw31)):
            f = A.modules()[mid]["file"]
            out = HERE / "out" / key
            m, cells = module_checks(key, mid, fn(), out / f"{f}.nbt", out / f"{f}.schem")
            r["designs"][key][mid] = m
            tmpl[(key, mid)] = cells
            problems += [(key, mid, p) for p in m["problems"]]
    r["boundaries"], bp = B8C.boundaries()
    problems += bp
    if a.offline:
        for key in keys:
            for mid, m in r["designs"][key].items():
                print(key, mid, m["problems"] or "ok", m["top"], m["composition"], m["counts"],
                      m["support"]["unsupported"][:5], m["barrier"]["path"][:12])
        print("PROBLEMS", json.dumps(problems, default=list) if problems else "none")
        return
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "wall redesign", "min_format": [121, 0], "max_format": [121, 0]}}))
    for (key, mid) in tmpl:
        f = A.modules()[mid]["file"]
        (pack / f"data/experimental/structure/{key}_{mid.lower()}.nbt").write_bytes((HERE / "out" / key / f"{f}.nbt").read_bytes())
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, -16, 180, 500, 400)
        for i, key in enumerate(keys):
            ox0 = 160 * i
            r["designs"][key]["server"] = {}
            for j, mid in enumerate(("MW86", "MW31")):
                cells = tmpl[(key, mid)]
                o = (ox0, -40, 200 + 20 * j)
                reply = server.cmd(f"place template experimental:{key}_{mid.lower()} {o[0]} {o[1]} {o[2]} none none 1 0 strict")
                assert reply.startswith("Loaded template"), reply
                fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                         if "passed" not in server.cmd(f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}")]
                r["designs"][key]["server"][f"strict_{mid}"] = {"cells": len(cells), "failure_count": len(fails), "failures": fails[:10]}
                if fails:
                    problems.append((key, mid, "strict placement", len(fails)))
            for name, site in SL.SITES.items():
                mid = site["module"]
                cells = tmpl[(key, mid)]
                L = A.modules()[mid]["size"][0]
                st = dict(site, origin=(site["origin"][0] + ox0, site["origin"][1]))
                ox, oz = st["origin"]
                SL.build_terrain(server, st, L)
                reply = server.cmd(f"place template experimental:{key}_{mid.lower()} {ox} {SL.GT} {oz} none none 1 0 strict")
                assert reply.startswith("Loaded template"), reply
                cols = SL.footing_fill(server, st, cells, L)
                fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                         if "passed" not in server.cmd(f"execute if block {ox + p[0]} {SL.GT + p[1]} {oz + p[2]} {_text(bid, pr)}")]
                hollow = [[x, y - SL.GT, z] for x in range(L) for z in range(5)
                          for y in range(min(SL.GT + site["d"](x, z), SL.GT), SL.GT)
                          if "passed" in server.cmd(f"execute if block {ox + x} {y} {oz + z} minecraft:air")]
                changed = [[x, z] for x in range(-SL.MARGIN_X, L + SL.MARGIN_X) for z in range(SL.Z0, SL.Z1 + 1)
                           if not (0 <= x < L and 0 <= z < 5) and "passed" not in server.cmd(
                               f"execute if block {ox + x} {SL.GT + site['d'](x, z)} {oz + z} minecraft:grass_block")]
                r["designs"][key]["server"][name] = {
                    "module": mid, "origin": [ox, SL.GT, oz], "footing_columns_filled": len(cols),
                    "max_fill_depth": max((c[2] for c in cols), default=0), "template_failures": len(fails),
                    "failures": fails[:10], "hollow_count": len(hollow), "hollow": hollow[:10],
                    "outside_changed_count": len(changed)}
                if fails or hollow or changed:
                    problems.append((key, name, len(fails), len(hollow), len(changed)))
    finally:
        server.stop()
    r["problems"] = problems
    a.out.write_text(json.dumps(r, indent=1, default=list) + "\n")
    print("PROBLEMS", json.dumps(problems, default=list) if problems else "none")
    print("PASS" if not problems else "FAIL")
    raise SystemExit(0 if not problems else 1)


if __name__ == "__main__":
    main()
