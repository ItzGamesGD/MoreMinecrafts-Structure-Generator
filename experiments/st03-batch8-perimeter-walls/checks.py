"""Checks for the perimeter wall NBTs MW86 / MW31 (new files only).

  PYTHONPATH=. python experiments/st03-batch8-perimeter-walls/checks.py --server-jar server.jar --java java25 --work <dir>

Writes check-result.json:
  nbt          independent verify.py (schema, every palette state valid for 26.3, cell-by-cell vs source, air=omit),
               size equals the placement-table module size, every authored state present in the NBT unchanged
  support      every lantern and wall banner has the block it needs (batch-7 rule)
  silhouette   every x column: complete footing z0..4 at y0, curtain z1..3 up to y8, sill + inner lip at y9, exterior
               top at y12 (merlon) or y9 (crenel); same section along the whole module; end columns solid (no slit,
               no gap) from y0 to y9
  boundaries   q=0..3: each wall footprint against the four reserved tower squares and the gate rectangle - no
               overlap, gap 0 at both ends to the expected tower / gate, local z=0 face on the outside of the box, the
               wall top (y12) at the same elevation in all five placements
  server       strict `place template` of both NBTs (rotation none) on the pinned 26.3 server, every cell compared;
               then the three slope sites of slope.py: terrain built, wall placed at grade, Q89 footing fill, every
               template cell compared again, no hollow cell between the ground and the template in any footprint
               column, terrain outside the footprint left as it was
Rotations of the real placements and the integrated q=0 layout with every built facility: place_check.py.
"""

import argparse
import hashlib
import importlib.util
import json
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
SL = _load("b8slope", HERE / "slope.py")
support_problems, solid = B7C.support_problems, B7C.solid
# expected neighbours: (low-x/low-z end, high end) in the q=0 frame
ENDS = {"W-N": ("T-NW", "T-NE"), "W-E": ("T-NE", "T-SE"), "W-W": ("T-NW", "T-SW"),
        "W-SW": ("T-SW", "GATE"), "W-SE": ("GATE", "T-SE")}
RESERVED = ("T-NW", "T-NE", "T-SE", "T-SW", "GATE")


def silhouette(cells, L, merlon, slits):
    bad = []
    for x in range(L):
        col = lambda z: {y for (cx, y, cz) in cells if cx == x and cz == z}
        for z in range(5):
            if (x, 0, z) not in cells:
                bad.append([x, 0, z, "footing missing"])
        for z in (1, 2, 3):
            ys = col(z)
            want = set(range(0, 9)) - ({4, 5} if x in slits else set())
            if z == 3:
                want |= {9}
            if ys != want:
                bad.append([x, z, "curtain", sorted(ys)])
        top0 = max(col(0))
        if top0 != (12 if merlon(x, L) else 9):
            bad.append([x, 0, "exterior top", top0])
        if 9 not in col(0) or 8 not in col(0):
            bad.append([x, 0, "sill/corbel missing"])
    for x in (0, L - 1):
        for z in range(5):
            for y in range(0, 9 if z in (1, 2, 3) else 1):
                if not solid(cells.get((x, y, z))):
                    bad.append([x, y, z, "end column not solid"])
    return bad


def boundaries():
    rows, problems = {}, []
    for q in range(4):
        man = {e["placement"]: e for e in A.manifest(q)}
        for name, (lo, hi) in ENDS.items():
            e = man[name]
            fp = e["footprint"]
            ov = [r for r in RESERVED if not (fp[2] < man[r]["footprint"][0] or man[r]["footprint"][2] < fp[0]
                                              or fp[3] < man[r]["footprint"][1] or man[r]["footprint"][3] < fp[1])]
            # local x=0 / x=L-1 ends in the structure frame and the cell just beyond each
            L = e["size"][0]
            ends = {}
            for lx, step in ((0, -1), (L - 1, 1)):
                cells = [A.place_cell(e, (lx, 0, z)) for z in range(5)]
                beyond = [A.place_cell(e, (lx + step, 0, z)) for z in range(5)]
                owner = {next((r for r in RESERVED if man[r]["footprint"][0] <= bx <= man[r]["footprint"][2]
                               and man[r]["footprint"][1] <= bz <= man[r]["footprint"][3]), None) for bx, _, bz in beyond}
                ends["x0" if lx == 0 else "xL"] = {"end_cells": [[c[0], c[2]] for c in cells], "abuts": sorted(map(str, owner))}
            # outward face: local z=-1 next to z=0 must be outside the 112 box
            ox, _, oz = A.place_cell(e, (L // 2, 0, -1))
            outside = not (0 <= ox < 112 and 0 <= oz < 112)
            expect = {lo, hi}  # placement names rotate with the whole structure, so adjacency must survive every q
            got = set(ends["x0"]["abuts"]) | set(ends["xL"]["abuts"])
            ok = not ov and outside and got == expect and all(len(v["abuts"]) == 1 for v in ends.values())
            rows.setdefault(str(q), {})[name] = {"rotation": e["rotation"], "footprint": fp, "overlaps_reserved": ov,
                                                 "ends": ends, "exterior_face_outside_box": outside,
                                                 "expected_neighbours": sorted(expect), "ok": ok,
                                                 "top_y": e["origin"][1] + e["size"][1] - 1}
            if not ok:
                problems.append(("boundary", q, name))
    tops = {r["top_y"] for q in rows.values() for r in q.values()}
    if len(tops) != 1:
        problems.append(("top elevation differs", sorted(tops)))
    return rows, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    b = _load("batch8_build", HERE / "build.py")
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    r, problems, tmpl = {"server_sha1": sha, "modules": {}}, [], {}
    for key, bd in b.BUILDINGS.items():
        module = A.modules()[bd["module"]]
        L = bd["size"][0]
        nbt, schem = HERE / "out" / f"{module['file']}.nbt", HERE / "out" / f"{module['file']}.schem"
        m = {"placements": list(bd["placements"]), "nbt": nbt.name,
             "nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
        s = V.verify(nbt, schem, C.load_reference("26.3"), "omit", C.load_connectivity("26.3"), block_entities.load("26.3"))
        assert list(s["size"]) == module["size"] == list(bd["size"]), s["size"]
        assert s["mismatches"] == 0, s
        m["verify"] = {k: (list(s[k]) if k == "size" else s[k])
                       for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
        cells = _template_cells(nbt)
        tmpl[bd["module"]] = cells
        src = bd["design"]()
        bad = [list(p) for p, (bid, pr) in src.items()
               if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
        extra = [list(p) for p in cells if p not in src]
        assert not bad and not extra, (bad[:5], extra[:5])
        m["states"] = {"authored_cells_checked": len(src), "mismatches": 0, "cells_not_authored": 0,
                       "air_cells_in_nbt": sum(1 for v in cells.values() if v[0] == "minecraft:air")}
        m["support"] = {"unsupported": support_problems(cells)}
        if m["support"]["unsupported"]:
            problems.append(("support", key, m["support"]["unsupported"]))
        sil = silhouette(cells, L, b.merlon, set(b.slits(L)))
        m["silhouette"] = {"columns": L, "problems": sil[:20], "problem_count": len(sil),
                           "merlons": sum(1 for x in range(L) if b.merlon(x, L)),
                           "crenels": sum(1 for x in range(L) if not b.merlon(x, L)),
                           "arrow_slits": len(b.slits(L))}
        if sil:
            problems.append(("silhouette", key, len(sil)))
        m["counts"] = {i: [v[0] for v in cells.values()].count("minecraft:" + i)
                       for i in ("lantern", "white_wall_banner", "barrel", "dark_oak_log", "spruce_log", "moss_carpet")}
        m["materials"] = {}
        for v in cells.values():
            n = v[0].split(":")[1]
            m["materials"][n] = m["materials"].get(n, 0) + 1
        r["modules"][bd["module"]] = m
    r["boundaries"], bp = boundaries()
    problems += bp

    if a.offline:
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "materials"} for k, v in r["modules"].items()},
                         default=list)[:4000])
        print("PROBLEMS", json.dumps(problems, default=list) if problems else "none")
        return
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "batch8", "min_format": [121, 0], "max_format": [121, 0]}}))
    for mid in tmpl:
        f = A.modules()[mid]["file"]
        (pack / f"data/experimental/structure/{mid.lower()}.nbt").write_bytes((HERE / "out" / f"{f}.nbt").read_bytes())
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, -16, 180, 160, 400)
        r["server_strict_placement"] = {}
        for i, (mid, cells) in enumerate(tmpl.items()):
            o = (0, -40, 200 + 20 * i)
            reply = server.cmd(f"place template experimental:{mid.lower()} {o[0]} {o[1]} {o[2]} none none 1 0 strict")
            assert reply.startswith("Loaded template"), reply
            fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                     if "passed" not in server.cmd(f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}")]
            r["server_strict_placement"][mid] = {"rotation": "none", "cells": len(cells), "failures": fails[:10],
                                                 "failure_count": len(fails)}
            if fails:
                problems.append(("strict placement", mid, len(fails)))
        r["slope_sites"] = {}
        for name, site in SL.SITES.items():
            mid, (ox, oz) = site["module"], site["origin"]
            cells = tmpl[mid]
            L = A.modules()[mid]["size"][0]
            SL.build_terrain(server, site, L)
            reply = server.cmd(f"place template experimental:{mid.lower()} {ox} {SL.GT} {oz} none none 1 0 strict")
            assert reply.startswith("Loaded template"), reply
            cols = SL.footing_fill(server, site, cells, L)
            fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                     if "passed" not in server.cmd(f"execute if block {ox + p[0]} {SL.GT + p[1]} {oz + p[2]} {_text(bid, pr)}")]
            hollow = []
            for x in range(L):
                for z in range(5):
                    t = SL.GT + site["d"](x, z)
                    for y in range(min(t, SL.GT), SL.GT):
                        if "passed" in server.cmd(f"execute if block {ox + x} {y} {oz + z} minecraft:air"):
                            hollow.append([x, y - SL.GT, z])
            # terrain outside the footprint untouched: the top block of every surrounding column is still grass
            changed = []
            for x in range(-SL.MARGIN_X, L + SL.MARGIN_X):
                for z in range(SL.Z0, SL.Z1 + 1):
                    if 0 <= x < L and 0 <= z < 5:
                        continue
                    t = SL.GT + site["d"](x, z)
                    if "passed" not in server.cmd(f"execute if block {ox + x} {t} {oz + z} minecraft:grass_block"):
                        changed.append([x, t - SL.GT, z])
            ds = [site["d"](x, z) for x in range(L) for z in range(5)]
            buried = sum(1 for x in range(L) for z in range(5) for y in range(1, max(0, site["d"](x, z)) + 1)
                         if (x, y, z) not in cells)
            r["slope_sites"][name] = {
                "module": mid, "origin": [ox, SL.GT, oz], "ground_relative_to_grade_min_max": [min(ds), max(ds)],
                "footing_columns_filled": len(cols), "max_fill_depth": max((c[2] for c in cols), default=0),
                "fill_blocks": sum(c[2] for c in cols), "template_cells": len(cells), "template_failures": len(fails),
                "failures": fails[:10], "hollow_cells": hollow[:10], "hollow_count": len(hollow),
                "outside_footprint_columns_changed": changed[:10], "outside_changed_count": len(changed),
                "terrain_cells_kept_inside_box_above_grade": buried}
            if fails or hollow or changed:
                problems.append(("slope", name, len(fails), len(hollow), len(changed)))
    finally:
        server.stop()
    r["problems"] = problems
    (HERE / "check-result.json").write_text(json.dumps(r, indent=1, default=list) + "\n")
    print("PROBLEMS", json.dumps(problems, default=list) if problems else "none")
    print("PASS" if not problems else "FAIL")
    raise SystemExit(0 if not problems else 1)


if __name__ == "__main__":
    main()
