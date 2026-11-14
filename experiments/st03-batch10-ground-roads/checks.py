"""Checks for the ground / road modules MQ-NW, MQ-NE, MQ-SW, MQ-SE (new files only).

  PYTHONPATH=. python experiments/st03-batch10-ground-roads/checks.py --server-jar server.jar --java java25 --work <dir>

Writes check-result.json.
A static
  nbt          verify.py per module (schema, 26.3 states, cell-by-cell vs source, air=include), size = module table,
               every authored state present unchanged, palette
  ground       every y0 cell of every module is a block (no hole); no grass_block / dirt_path under a block and no
               exposed plain dirt (random ticks would change either)
  support      torches on a fence or solid block, weeds on soil, lanterns / banners (batch-7 rule)
  boundary     no road cell inside any other placement footprint; MQ rectangles tile x/z 5..106 exactly
B assembly (q=0, every built module: MQ, towers, walls, gate, F01-F20)
  network      road cells form one connected network from the gate passage; every entrance cell is a road cell
  widths       every main road / plaza / lane rectangle is paved over its full nominal width, with air above (y1-y2)
               in the assembled structure: nothing stands on a road
  decor        no decoration on a road, its fringe or within 2 blocks of an entrance or of a building footprint
  steps        micro-relief: neighbouring walkable surfaces differ by at most one block
  walk         walking search over the assembled structure (feet / head passable, solid underfoot, one-block jump):
               from outside the gate through the passage to every entrance cell, and one step into each building
C server
  strict `place template` of each module (rotation none), every cell compared (air included); a slope site for
  MQ-SE (ground -4..+3 around grade): placement at grade, Q89-style footing fill below grade, every template cell
  compared, no hollow column, terrain outside the footprint unchanged
Rotations q=1-3 and the integrated q=0 placement with every module: place_check.py (ground=True).
"""

import argparse
import hashlib
import importlib.util
import json
import math
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
CK9 = _load("b9checks", EXP / "st03-batch9-towers-gate" / "checks.py")
SL = CK9.SL
support_problems, solid = B7C.support_problems, B7C.solid
SOIL = ("grass_block", "dirt", "coarse_dirt", "rooted_dirt", "moss_block", "podzol", "mud", "packed_mud")
DECOR = ("barrel", "spruce_log", "spruce_fence", "torch", "hay_block", "stripped_spruce_log")
SITE = dict(module="MQ-SE", origin=(0, 600),
            d=lambda x, z: max(-4, min(3, round(2.6 * math.sin(x / 7.0) + 1.8 * math.cos(z / 9.0) - 0.4))))
MARGIN = 3


def world(b, mid, cells):
    ox, oz = b.MODULES[mid]
    return {(x + ox, y, z + oz): v for (x, y, z), v in cells.items()}


def extra_support(cells):
    bad = []
    for (x, y, z), (bid, _) in cells.items():
        n = bid.split(":")[1]
        below = cells.get((x, y - 1, z))
        if n == "torch" and not (below and (below[0].endswith(("_fence", "_wall")) or solid(below))):
            bad.append([x, y, z, n])
        if n in ("short_grass", "fern") and not (below and below[0].split(":")[1] in SOIL):
            bad.append([x, y, z, n])
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    b = _load("batch10_build", HERE / "build.py")
    G, info = b.designs()
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    r, problems, tmpl = {"server_sha1": sha, "modules": {}}, [], {}
    # ------------------------------------------------------------------ A static
    for key, bd in b.BUILDINGS.items():
        mid = bd["module"]
        module = A.modules()[mid]
        nbt, schem = HERE / "out" / f"{module['file']}.nbt", HERE / "out" / f"{module['file']}.schem"
        m = {"placement": bd["placements"][0], "nbt": nbt.name, "nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
        s = V.verify(nbt, schem, C.load_reference("26.3"), "include", C.load_connectivity("26.3"),
                     block_entities.load("26.3"))
        assert list(s["size"]) == module["size"] == list(bd["size"]), s["size"]
        m["verify"] = {k: (list(s[k]) if k == "size" else s[k])
                       for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
        if s["mismatches"]:
            problems.append(("verify", mid, s["mismatches"]))
        cells = _template_cells(nbt)
        src = bd["design"]()
        bad = [list(p) for p, (bid, pr) in src.items()
               if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
        extra = [list(p) for p, v in cells.items() if p not in src and v[0] != "minecraft:air"]
        m["states"] = {"authored_cells_checked": len(src), "mismatches": bad[:10], "non_air_not_authored": extra[:10]}
        if bad or extra:
            problems.append(("states", mid, len(bad), len(extra)))
        solid_cells = {p: v for p, v in cells.items() if v[0] != "minecraft:air"}
        tmpl[mid] = cells
        holes = [[x, z] for x in range(b.S) for z in range(b.S) if (x, 0, z) not in solid_cells]
        covered = [[*p, v[0]] for p, v in solid_cells.items() if v[0] in ("minecraft:grass_block", "minecraft:dirt_path")
                   and (p[0], p[1] + 1, p[2]) in solid_cells
                   and solid_cells[(p[0], p[1] + 1, p[2])][0] not in ("minecraft:short_grass", "minecraft:fern", "minecraft:torch")]
        exposed_dirt = [list(p) for p, v in solid_cells.items() if v[0] == "minecraft:dirt"
                        and (p[0], p[1] + 1, p[2]) not in solid_cells]  # grass would spread onto it
        covered += [[*c, "exposed plain dirt"] for c in exposed_dirt]
        sup = support_problems(solid_cells) + extra_support(solid_cells)
        m["ground"] = {"y0_holes": holes[:10], "hole_count": len(holes), "grass_or_path_under_block": covered[:10]}
        m["support"] = {"unsupported": sup}
        if holes or covered or sup:
            problems.append(("ground/support", mid, len(holes), len(covered), len(sup)))
        pal = {}
        for v in solid_cells.values():
            n = v[0].split(":")[1]
            pal[n] = pal.get(n, 0) + 1
        m["palette_counts"] = dict(sorted(pal.items(), key=lambda kv: -kv[1]))
        r["modules"][mid] = m
    # boundary: tiling and road clashes
    tiles = [A.manifest(0)[0]]
    cover = {}
    for e in A.manifest(0):
        if e["placement"].startswith("GROUND"):
            x0, z0, x1, z1 = e["footprint"]
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    cover[(x, z)] = cover.get((x, z), 0) + 1
    tiling_ok = all(cover.get((x, z)) == 1 for x in range(5, 107) for z in range(5, 107)) and len(cover) == 102 * 102
    _, owner, clash = b.plan()
    r["boundary"] = {"mq_tiling_5_106_exact": tiling_ok, "road_cells_in_other_footprints": clash[:10],
                     "road_clash_count": len(clash)}
    if not tiling_ok or clash:
        problems.append(("boundary", tiling_ok, len(clash)))
    # ------------------------------------------------------------------ B assembly
    pc = _load("place_check", EXP / "st03-placement-check" / "place_check.py")
    built = pc.built_modules(perimeter=True, towers=True, ground=True)
    bare = {}
    for mid2, v in built.items():
        cl = tmpl.get(mid2) or _template_cells(v["nbt"])
        bare[mid2] = {p: (q[0], {}) for p, q in cl.items()}
    for e in A.manifest(0):
        bare.setdefault(e["module"], {})
    asm, own = A.assemble(0, bare)
    road = info["road"]
    # network
    start = (56, 99)
    seen, q = {start}, deque([start])
    while q:
        x, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in road and n not in seen:
                seen.add(n)
                q.append(n)
    unreached_roads = [list(c) for c in road if c not in seen]
    ent_off = {k: [list(c) for c in v if c not in road] for k, v in b.ENTRANCES.items()}
    ent_off = {k: v for k, v in ent_off.items() if v}
    ent_unreached = {k: [list(c) for c in v if c not in seen] for k, v in b.ENTRANCES.items()}
    ent_unreached = {k: v for k, v in ent_unreached.items() if v}
    r["network"] = {"road_cells": len(road), "connected_from_gate": len(seen), "unreached_road_cells": unreached_roads[:10],
                    "entrances": len(b.ENTRANCES), "entrance_cells_not_on_road": ent_off,
                    "entrance_cells_not_connected": ent_unreached}
    if unreached_roads or ent_off or ent_unreached:
        problems.append(("network", len(unreached_roads), ent_off, ent_unreached))
    # widths: full nominal width paved with nothing standing on it (assembled)
    widths, blocked = {}, []
    for name, kind, rr in b.ROADS:
        w = min(rr[2] - rr[0], rr[3] - rr[1]) + 1
        widths[name] = {"kind": kind, "rect": list(rr), "nominal_width": w,
                        "length": max(rr[2] - rr[0], rr[3] - rr[1]) + 1}
        for x in range(rr[0], rr[2] + 1):
            for z in range(rr[1], rr[3] + 1):
                if not solid(asm.get((x, 0, z))):
                    blocked.append([name, x, 0, z, "surface missing"])
                for y in (1, 2):
                    if (x, y, z) in asm:
                        blocked.append([name, x, y, z, asm[(x, y, z)][0]])
    r["widths"] = widths
    r["road_obstructions"] = blocked[:20]
    if blocked:
        problems.append(("road obstructions", len(blocked)))
    bad_width = {k: v for k, v in widths.items() if (v["kind"] == "main" and not 5 <= v["nominal_width"] <= 6)
                 or (v["kind"] == "lane" and not 2 <= v["nominal_width"] <= 3)}
    r["width_rule_violations"] = bad_width
    if bad_width:
        problems.append(("widths", bad_width))
    # decor placement
    ent_cells = {c for v in b.ENTRANCES.values() for c in v}
    dec_bad = []
    for d in info["decor"]:
        for x, z in d["cells"]:
            if (x, z) in road or (x, z) in info["fringe"]:
                dec_bad.append([d["kind"], x, z, "on road"])
            if any(abs(x - ex) <= 2 and abs(z - ez) <= 2 for ex, ez in ent_cells):
                dec_bad.append([d["kind"], x, z, "near entrance"])
            if any((x + i, z + k) in owner for i in range(-2, 3) for k in range(-2, 3)):
                dec_bad.append([d["kind"], x, z, "within 2 of a building"])
    kinds = {}
    for d in info["decor"]:
        kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
    r["decor"] = {"clusters": len(info["decor"]), "by_kind": kinds, "problems": dec_bad[:10]}
    if dec_bad:
        problems.append(("decor", len(dec_bad)))
    # steps: walkable surface height inside the MQ ground (outside footprints)
    def surf(x, z):
        ys = [y for y in range(0, 8) if (x, y, z) in G and G[(x, y, z)][0] not in ("short_grass", "fern", "torch")
              and G[(x, y, z)][0] not in DECOR]
        return max(ys) if ys else None
    steps = []
    for x in range(5, 106):
        for z in range(5, 106):
            if (x, z) in owner or any(G.get((x, y, z), ("",))[0] in DECOR for y in (1, 2, 3)):
                continue
            for nx, nz in ((x + 1, z), (x, z + 1)):
                if (nx, nz) in owner or any(G.get((nx, y, nz), ("",))[0] in DECOR for y in (1, 2, 3)):
                    continue
                a1, a2 = surf(x, z), surf(nx, nz)
                if a1 is None or a2 is None or abs(a1 - a2) > 1:
                    steps.append([x, z, nx, nz, a1, a2])
    r["steps"] = {"max_neighbour_difference_ok": not steps, "violations": steps[:10],
                  "mound_cells": len(info["mound"]), "two_high_cells": sum(1 for v in info["mound"].values() if v == 2)}
    if steps:
        problems.append(("steps", len(steps)))
    # walk: gate -> every entrance -> one step inside
    seen_w = CK9.reach(asm, (112, 0, 112), (56, 1, 113), margin=3)
    walk = {}
    for k, v in b.ENTRANCES.items():
        rows = []
        for (x, z) in v:
            reach_out = any((x, y, z) in seen_w for y in (1, 2))
            inward = [(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, z + dz) in owner]
            reach_in = any((ix, y, iz) in seen_w for ix, iz in inward for y in (1, 2, 3))
            rows.append({"cell": [x, z], "outside_reached": reach_out, "inside_cell": [list(c) for c in inward],
                         "one_step_inside_reached": reach_in})
        walk[k] = rows
    walk_bad = {k: v for k, v in walk.items() if not all(rw["outside_reached"] and rw["one_step_inside_reached"] for rw in v)}
    r["walk"] = {"from": [56, 1, 113], "entrances": walk, "failures": list(walk_bad)}
    if walk_bad:
        problems.append(("walk", list(walk_bad)))

    if a.offline:
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("palette_counts",)} for k, v in r["modules"].items()})[:3000])
        for k in ("boundary", "network", "road_obstructions", "width_rule_violations", "decor", "steps"):
            print(k, json.dumps(r[k])[:800])
        print("walk failures", r["walk"]["failures"])
        for k in r["walk"]["failures"]:
            print(k, r["walk"]["entrances"][k])
        print("PROBLEMS", json.dumps(problems, default=list)[:2000] if problems else "none")
        return
    # ------------------------------------------------------------------ C server
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "batch10", "min_format": [121, 0], "max_format": [121, 0]}}))
    for mid in b.MODULES:
        f = A.modules()[mid]["file"]
        (pack / f"data/experimental/structure/{mid.replace('-', '_').lower()}.nbt").write_bytes(
            (HERE / "out" / f"{f}.nbt").read_bytes())
    tid = lambda m: "experimental:" + m.replace("-", "_").lower()
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, -16, 180, 260, 680)
        r["server_strict_placement"] = {}
        for i, mid in enumerate(b.MODULES):
            cells = tmpl[mid]
            o = (60 * i, -40, 200)
            reply = server.cmd(f"place template {tid(mid)} {o[0]} {o[1]} {o[2]} none none 1 0 strict")
            assert reply.startswith("Loaded template"), reply
            fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                     if "passed" not in server.cmd(f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}")]
            r["server_strict_placement"][mid] = {"rotation": "none", "cells_including_air": len(cells),
                                                 "failures": fails[:10], "failure_count": len(fails)}
            if fails:
                problems.append(("strict placement", mid, len(fails)))
        mid, (ox, oz) = SITE["module"], SITE["origin"]
        cells = tmpl[mid]
        CK9.build_terrain(server, SITE, b.S, b.S, b.H)
        above = sum(max(0, SITE["d"](x, z)) for x in range(b.S) for z in range(b.S))
        reply = server.cmd(f"place template {tid(mid)} {ox} {SL.GT} {oz} none none 1 0 strict")
        assert reply.startswith("Loaded template"), reply
        cols = CK9.footing_fill(server, SITE, b.S, b.S)
        fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                 if "passed" not in server.cmd(f"execute if block {ox + p[0]} {SL.GT + p[1]} {oz + p[2]} {_text(bid, pr)}")]
        hollow = []
        for x in range(b.S):
            for z in range(b.S):
                t = SL.GT + SITE["d"](x, z)
                for y in range(min(t, SL.GT), SL.GT):
                    if "passed" in server.cmd(f"execute if block {ox + x} {y} {oz + z} minecraft:air"):
                        hollow.append([x, y - SL.GT, z])
        changed = []
        for x in range(-MARGIN, b.S + MARGIN):
            for z in range(-MARGIN, b.S + MARGIN):
                if 0 <= x < b.S and 0 <= z < b.S:
                    continue
                cx, cz = max(0, min(b.S - 1, x)), max(0, min(b.S - 1, z))
                t = SL.GT + SITE["d"](cx, cz)
                if "passed" not in server.cmd(f"execute if block {ox + x} {t} {oz + z} minecraft:grass_block"):
                    changed.append([x, t - SL.GT, z])
        ds = [SITE["d"](x, z) for x in range(b.S) for z in range(b.S)]
        r["slope_site"] = {"module": mid, "origin": [ox, SL.GT, oz], "ground_relative_to_grade_min_max": [min(ds), max(ds)],
                           "footing_columns_filled": len(cols), "max_fill_depth": max((c[2] for c in cols), default=0),
                           "template_cells": len(cells), "template_failures": len(fails), "failures": fails[:10],
                           "hollow_count": len(hollow), "hollow_cells": hollow[:10], "outside_changed_count": len(changed),
                           "outside_changed": changed[:10],
                           "terrain_cells_above_grade_inside_box_replaced_by_air_include": above}
        if fails or hollow or changed:
            problems.append(("slope", len(fails), len(hollow), len(changed)))
    finally:
        server.stop()
    r["problems"] = problems
    (HERE / "check-result.json").write_text(json.dumps(r, indent=1, default=list) + "\n")
    print("PROBLEMS", json.dumps(problems, default=list)[:2000] if problems else "none")
    print("PASS" if not problems else "FAIL")
    raise SystemExit(0 if not problems else 1)


if __name__ == "__main__":
    main()
