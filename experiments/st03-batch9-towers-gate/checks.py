"""Checks for the corner tower MT and the gatehouse MG (new files only).

  PYTHONPATH=. python experiments/st03-batch9-towers-gate/checks.py --server-jar server.jar --java java25 --work <dir>

Writes check-result.json:
  nbt          independent verify.py (schema, every palette state valid for 26.3, cell-by-cell vs source, air=include),
               size equals the placement-table module size, every authored state present in the NBT unchanged
  support      every lantern, wall banner and ladder has the block it needs (batch-7 rule)
  static       Q86: no functional block in MG (no door on the gate passage, no fence gate, trapdoor, lever, button,
               pressure plate, redstone, piston); the gate passage is clear (air) 6 wide x 6 high over the full depth
  traversal    walking + ladder search on the template grid (feet and head cell passable, solid block or ladder
               underfoot, 1-block jump with headroom, ladders climbable): MT from outside its door to the lookout floor;
               MG from the checkpoint to the room above the gate (its own ladder), and straight through the passage
  roof         MT: every one of the 13x13 columns is covered by exactly one roof block above the eave
  boundaries   q=0..3: no overlap with any other placement; each tower abuts its two walls and each wall end its tower /
               gate (gap 0); the tower door and the gate passage open onto the compound (inside the box, not into another
               footprint); exterior faces outside the box
  joints       q=0 assembly of walls + towers + gate: every wall end cell (local x=0 / L-1) has a solid block of the
               tower / gatehouse right behind it at the same height (no gap or slot at the 10 wall ends)
  server       strict `place template` of both NBTs (rotation none) on the pinned 26.3 server, every non-air cell
               compared and every air cell confirmed air; then four slope sites (two per module): terrain built, module
               placed at grade, Q89 footing fill under every footprint column below grade, every template cell compared
               again, no hollow cell between ground and footing, terrain outside the footprint unchanged
Rotations of the real placements and the integrated q=0 layout with every built module: place_check.py.
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
SL = _load("b8slope", EXP / "st03-batch8-perimeter-walls" / "slope.py")
support_problems, solid = B7C.support_problems, B7C.solid
FUNCTIONAL = ("_door", "fence_gate", "_trapdoor", "lever", "_button", "pressure_plate", "redstone", "piston", "observer",
              "repeater", "comparator", "tripwire", "daylight_detector", "target")
PASSABLE = ("air", "_door", "ladder", "_carpet", "_banner")
WALL_ENDS = {"W-N": ("T-NW", "T-NE"), "W-E": ("T-NE", "T-SE"), "W-W": ("T-NW", "T-SW"),
             "W-SW": ("T-SW", "GATE"), "W-SE": ("GATE", "T-SE")}
TOWER_WALLS = {"T-NW": {"W-N", "W-W"}, "T-NE": {"W-N", "W-E"}, "T-SE": {"W-E", "W-SE"}, "T-SW": {"W-W", "W-SW"}}

# slope sites (local frame of the module, d = ground relative to grade); grade GT as in batch 8
SITES = {
    "T1_falls_to_outer_corner": dict(module="MT", origin=(0, 460),
                                     d=lambda x, z: max(-5, min(0, -round((24 - x - z) / 4.8)))),
    "T2_undulating": dict(module="MT", origin=(40, 460),
                          d=lambda x, z: max(-4, min(2, round(2.0 * math.sin(x / 2.5) + 1.5 * math.cos(z / 3.0) - 0.6)))),
    "G1_falls_outward": dict(module="MG", origin=(80, 460),
                             d=lambda x, z: max(-5, min(0, -round(max(0, z - 3) * 0.65)))),
    "G2_cross_slope": dict(module="MG", origin=(130, 460),
                           d=lambda x, z: max(-4, min(3, round((x - 13) / 3.5)))),
}
MARGIN = 3


def passable(cells, p):
    v = cells.get(p)
    return v is None or v[0].endswith(PASSABLE) or v[0] == "minecraft:air"


def ladder(cells, p):
    v = cells.get(p)
    return v is not None and v[0] == "minecraft:ladder"


def standable(cells, p, size):
    x, y, z = p
    if y < 1 or not (passable(cells, p) and passable(cells, (x, y + 1, z))):
        return False
    inside = 0 <= x < size[0] and 0 <= z < size[2]
    below = cells.get((x, y - 1, z))
    if not inside:
        return y == 1  # flat ground around the module
    return ladder(cells, p) or ladder(cells, (x, y - 1, z)) or solid(below)


def reach(cells, size, start, margin=2):
    """Breadth-first walk. Returns the set of reachable feet positions."""
    seen, q = {start}, deque([start])
    while q:
        x, y, z = q.popleft()
        nxt = []
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if not (-margin <= nx < size[0] + margin and -margin <= nz < size[2] + margin):
                continue
            nxt.append((nx, y, nz))
            if passable(cells, (x, y + 2, z)):
                nxt.append((nx, y + 1, nz))  # jump up one block
            for drop in (1, 2, 3):
                nxt.append((nx, y - drop, nz))
        if ladder(cells, (x, y, z)) or ladder(cells, (x, y - 1, z)):
            nxt += [(x, y + 1, z), (x, y - 1, z)]
        for p in nxt:
            if p not in seen and standable(cells, p, size):
                if p[1] < y - 1 and not all(passable(cells, (p[0], yy, p[2])) for yy in range(p[1], y + 2)):
                    continue
                seen.add(p)
                q.append(p)
    return seen


def static_gate(cells, b):
    bad = [[*p, v[0]] for p, v in cells.items() if v[0].split(":")[1].endswith(FUNCTIONAL) or
           any(f in v[0] for f in FUNCTIONAL[4:])]
    doors = [d for d in bad if d[3].endswith("_door")]
    shaft_door = [[*b.SHAFT_DOOR[:1], y, b.SHAFT_DOOR[1], "minecraft:dark_oak_door"] for y in (1, 2)]
    others = [d for d in bad if [d[0], d[1], d[2]] not in ([s[0], s[1], s[2]] for s in shaft_door)]
    p0, p1 = b.PASS_X
    blocked = [[x, y, z, cells[(x, y, z)][0]] for x in range(p0, p1 + 1) for y in range(1, 7) for z in range(b.GD)
               if (x, y, z) in cells and cells[(x, y, z)][0] != "minecraft:air"]
    floor = [[x, z] for x in range(p0, p1 + 1) for z in range(b.GD) if not solid(cells.get((x, 0, z)))]
    return {"functional_blocks_other_than_shaft_door": others, "shaft_door": len(doors),
            "passage_clear_width": p1 - p0 + 1, "passage_clear_height": 6, "passage_blocked_cells": blocked,
            "passage_floor_gaps": floor}


def roof_cover(cells, b):
    bad = []
    for x in range(b.TW):
        for z in range(b.TW):
            n = sum(1 for y in range(b.EAVE, b.TH) if (x, y, z) in cells and cells[(x, y, z)][0].startswith(
                ("minecraft:dark_oak_stairs", "minecraft:dark_oak_planks")))
            if n != 1:
                bad.append([x, z, n])
    return bad


def boundaries(b):
    rows, problems = {}, []
    for q in range(4):
        man = {e["placement"]: e for e in A.manifest(q)}
        fp = {k: e["footprint"] for k, e in man.items() if not k.startswith("GROUND")}
        own = lambda x, z: next((k for k, r in fp.items() if r[0] <= x <= r[2] and r[1] <= z <= r[3]), None)
        for name in ("T-NW", "T-NE", "T-SE", "T-SW", "GATE"):
            e = man[name]
            r = fp[name]
            ov = [k for k, o in fp.items() if k != name and not (r[2] < o[0] or o[2] < r[0] or r[3] < o[1] or o[3] < r[1])]
            ring = {own(x, z) for x in range(r[0] - 1, r[2] + 2) for z in range(r[1] - 1, r[3] + 2)
                    if not (r[0] <= x <= r[2] and r[1] <= z <= r[3]) and 0 <= x < 112 and 0 <= z < 112} - {None}
            if name == "GATE":
                ent_local = [(x, 0, -1) for x in range(b.PASS_X[0], b.PASS_X[1] + 1)]
                out_local = [(x, 0, b.GD) for x in range(b.PASS_X[0], b.PASS_X[1] + 1)]
                want = {"W-SW", "W-SE"}
            else:
                ent_local = [(b.TW, 0, b.DOOR_Z)]
                out_local = [(-1, 0, 6), (6, 0, -1)]
                want = TOWER_WALLS[name]
            ent = [A.place_cell(e, c) for c in ent_local]
            outs = [A.place_cell(e, c) for c in out_local]
            ent_ok = all(5 <= x <= 106 and 5 <= z <= 106 and own(x, z) is None for x, _, z in ent)
            out_ok = all(not (0 <= x < 112 and 0 <= z < 112) for x, _, z in outs)
            ok = not ov and ring == want and ent_ok and out_ok
            rows.setdefault(str(q), {})[name] = {"rotation": e["rotation"], "footprint": r, "overlaps": ov,
                                                 "abuts": sorted(ring), "expected": sorted(want),
                                                 "entrance_outside_cells": [[x, z] for x, _, z in ent],
                                                 "entrance_on_free_compound_ground": ent_ok,
                                                 "exterior_faces_outside_box": out_ok, "ok": ok}
            if not ok:
                problems.append(("boundary", q, name))
    return rows, problems


def joints(templates):
    """q=0: behind every wall end cell, the neighbouring module has a solid block at the same height."""
    man = {e["placement"]: e for e in A.manifest(0)}
    # only block identity matters here (solid or not), so states are dropped (assemble cannot turn facing=up)
    bare = {m: {p: (v[0], {}) for p, v in templates.get(m, {}).items()} for m in {e["module"] for e in man.values()}}
    cells, owner = A.assemble(0, bare)
    rows, open_cells = {}, []
    for w, ends in WALL_ENDS.items():
        e = man[w]
        L = e["size"][0]
        for lx, step in ((0, -1), (L - 1, 1)):
            n_ok = n = 0
            for (cx, y, cz), v in templates[e["module"]].items():
                if cx != lx or v[0] == "minecraft:air" or not solid(v):
                    continue
                bx, by, bz = A.place_cell(e, (lx + step, y, cz))
                n += 1
                if solid(cells.get((bx, by, bz))):
                    n_ok += 1
                else:
                    open_cells.append([w, bx, by, bz])
            rows[f"{w} x{lx}"] = {"wall_end_cells": n, "backed_by_solid": n_ok,
                                  "neighbour": owner.get(A.place_cell(e, (lx + step, 1, 2)))}
    return rows, open_cells


def build_terrain(server, site, w, d, h):
    ox, oz = site["origin"]
    for x in range(-MARGIN, w + MARGIN):
        for z in range(-MARGIN, d + MARGIN):
            cx, cz = max(0, min(w - 1, x)), max(0, min(d - 1, z))
            t = SL.GT + site["d"](cx, cz)
            if t - 1 > SL.G:
                server.cmd(f"fill {ox + x} {SL.G + 1} {oz + z} {ox + x} {t - 1} {oz + z} minecraft:dirt")
            server.cmd(f"setblock {ox + x} {t} {oz + z} minecraft:grass_block")
            server.cmd(f"fill {ox + x} {t + 1} {oz + z} {ox + x} {SL.GT + h} {oz + z} minecraft:air")


def footing_fill(server, site, w, d):
    ox, oz = site["origin"]
    cols = []
    for x in range(w):
        for z in range(d):
            t = SL.GT + site["d"](x, z)
            if t >= SL.GT:
                continue
            for y in range(t, SL.GT):
                server.cmd(f"setblock {ox + x} {y} {oz + z} {SL.fill_block(x, y - SL.GT, z)}")
            cols.append((x, z, SL.GT - t))
    return cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    b = _load("batch9_build", HERE / "build.py")
    sha = hashlib.sha1(a.server_jar.read_bytes()).hexdigest()
    assert sha == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c", sha
    r, problems, tmpl = {"server_sha1": sha, "modules": {}}, [], {}
    for key, bd in b.BUILDINGS.items():
        module = A.modules()[bd["module"]]
        nbt, schem = HERE / "out" / f"{module['file']}.nbt", HERE / "out" / f"{module['file']}.schem"
        m = {"placements": list(bd["placements"]), "nbt": nbt.name,
             "nbt_sha256": hashlib.sha256(nbt.read_bytes()).hexdigest()}
        s = V.verify(nbt, schem, C.load_reference("26.3"), "include", C.load_connectivity("26.3"),
                     block_entities.load("26.3"))
        assert list(s["size"]) == module["size"] == list(bd["size"]), s["size"]
        m["verify"] = {k: (list(s[k]) if k == "size" else s[k])
                       for k in ("size", "blocks", "non_air_blocks", "palette", "cells_compared", "mismatches")}
        if s["mismatches"]:
            problems.append(("verify", key, s["mismatches"]))
        cells = _template_cells(nbt)
        src = bd["design"]()
        bad = [list(p) for p, (bid, pr) in src.items()
               if cells.get(p, ("", {}))[0] != bid or any(cells[p][1].get(k) != v for k, v in pr.items())]
        extra = [list(p) for p, v in cells.items() if p not in src and v[0] != "minecraft:air"]
        m["states"] = {"authored_cells_checked": len(src), "mismatches": bad[:10], "non_air_cells_not_authored": extra[:10],
                       "air_cells_in_nbt": sum(1 for v in cells.values() if v[0] == "minecraft:air")}
        if bad or extra:
            problems.append(("states", key, len(bad), len(extra)))
        solid_cells = {p: v for p, v in cells.items() if v[0] != "minecraft:air"}
        tmpl[bd["module"]] = cells
        m["support"] = {"unsupported": support_problems(solid_cells)}
        if m["support"]["unsupported"]:
            problems.append(("support", key, m["support"]["unsupported"]))
        size = bd["size"]
        if key == "tower":
            seen = reach(solid_cells, size, (b.TW + 1, 1, b.DOOR_Z))
            top = sorted(p for p in seen if p[1] == b.LOOK + 1)
            m["traversal"] = {"start": [b.TW + 1, 1, b.DOOR_Z], "lookout_cells_reached": len(top),
                              "lookout_reached": bool(top), "ladder": [list(b.LADDER), 1, b.LOOK],
                              "headroom_lookout": all(passable(solid_cells, (x, y, z)) for x in range(2, 11)
                                                      for z in range(2, 11) for y in (b.LOOK + 1, b.LOOK + 2)
                                                      if (x, z) != b.LADDER)}
            m["observation_gaps"] = sum(1 for x in range(1, 12) for z in range(1, 12) for y in (b.LOOK + 2, b.LOOK + 3)
                                        if min(x, z, 12 - x, 12 - z) == 1 and (x, y, z) not in solid_cells)
            m["roof_cover_problems"] = roof_cover(solid_cells, b)
            if not top or not m["traversal"]["headroom_lookout"] or m["roof_cover_problems"]:
                problems.append(("tower traversal/roof", m["traversal"], len(m["roof_cover_problems"])))
        else:
            m["static"] = static_gate(solid_cells, b)
            st = m["static"]
            if st["functional_blocks_other_than_shaft_door"] or st["passage_blocked_cells"] or st["passage_floor_gaps"]:
                problems.append(("gate static/passage", st))
            seen = reach(solid_cells, size, (b.SHAFT_DOOR[0], 1, 0))
            room = sorted(p for p in seen if p[1] == b.ROOM_Y[0] + 1)
            through = reach(solid_cells, size, (11, 1, -2))
            m["traversal"] = {"room_cells_reached": len(room), "room_reached": bool(room),
                              "passage_through": (11, 1, b.GD + 1) in through,
                              "checkpoint_to_passage": (11, 1, 0) in seen}
            if not room or (11, 1, b.GD + 1) not in through:
                problems.append(("gate traversal", m["traversal"]))
        m["counts"] = {i: [v[0] for v in cells.values()].count("minecraft:" + i)
                       for i in ("lantern", "white_wall_banner", "barrel", "chest", "ladder", "dark_oak_door")}
        r["modules"][bd["module"]] = m
    r["boundaries"], bp = boundaries(b)
    problems += bp
    walls = _load("b8build", EXP / "st03-batch8-perimeter-walls" / "build.py")
    for wb in walls.BUILDINGS.values():
        f = A.modules()[wb["module"]]["file"]
        tmpl.setdefault(wb["module"], _template_cells(EXP / "st03-batch8-perimeter-walls" / "out" / f"{f}.nbt"))
    r["joints"], open_cells = joints(tmpl)
    r["joint_open_cells"] = open_cells[:20]
    if open_cells:
        problems.append(("joints", len(open_cells)))

    if a.offline:
        print(json.dumps({k: {kk: vv for kk, vv in v.items()} for k, v in r["modules"].items()}, default=list)[:6000])
        print(json.dumps(r["joints"])[:2000])
        print("PROBLEMS", json.dumps(problems, default=list) if problems else "none")
        return
    pack = a.work / "pack"
    (pack / "data/experimental/structure").mkdir(parents=True, exist_ok=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "batch9", "min_format": [121, 0], "max_format": [121, 0]}}))
    for mid in ("MT", "MG"):
        f = A.modules()[mid]["file"]
        (pack / f"data/experimental/structure/{mid.lower()}.nbt").write_bytes((HERE / "out" / f"{f}.nbt").read_bytes())
    server = make_server(a.work / "server", a.server_jar, a.java, pack)
    try:
        server.start()
        forceload(server, -16, 180, 200, 520)
        r["server_strict_placement"] = {}
        for i, mid in enumerate(("MT", "MG")):
            cells = tmpl[mid]
            o = (0, -40, 200 + 40 * i)
            reply = server.cmd(f"place template experimental:{mid.lower()} {o[0]} {o[1]} {o[2]} none none 1 0 strict")
            assert reply.startswith("Loaded template"), reply
            fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                     if "passed" not in server.cmd(f"execute if block {o[0] + p[0]} {o[1] + p[1]} {o[2] + p[2]} {_text(bid, pr)}")]
            r["server_strict_placement"][mid] = {"rotation": "none", "cells_including_air": len(cells),
                                                 "failures": fails[:10], "failure_count": len(fails)}
            if fails:
                problems.append(("strict placement", mid, len(fails)))
        r["slope_sites"] = {}
        for name, site in SITES.items():
            mid, (ox, oz) = site["module"], site["origin"]
            cells = tmpl[mid]
            w, h, d = A.modules()[mid]["size"]
            build_terrain(server, site, w, d, h)
            above = sum(max(0, site["d"](x, z)) for x in range(w) for z in range(d))
            reply = server.cmd(f"place template experimental:{mid.lower()} {ox} {SL.GT} {oz} none none 1 0 strict")
            assert reply.startswith("Loaded template"), reply
            cols = footing_fill(server, site, w, d)
            fails = [list(p) for p, (bid, pr) in sorted(cells.items())
                     if "passed" not in server.cmd(f"execute if block {ox + p[0]} {SL.GT + p[1]} {oz + p[2]} {_text(bid, pr)}")]
            hollow = []
            for x in range(w):
                for z in range(d):
                    t = SL.GT + site["d"](x, z)
                    for y in range(min(t, SL.GT), SL.GT):
                        if "passed" in server.cmd(f"execute if block {ox + x} {y} {oz + z} minecraft:air"):
                            hollow.append([x, y - SL.GT, z])
            changed = []
            for x in range(-MARGIN, w + MARGIN):
                for z in range(-MARGIN, d + MARGIN):
                    if 0 <= x < w and 0 <= z < d:
                        continue
                    cx, cz = max(0, min(w - 1, x)), max(0, min(d - 1, z))
                    t = SL.GT + site["d"](cx, cz)
                    if "passed" not in server.cmd(f"execute if block {ox + x} {t} {oz + z} minecraft:grass_block"):
                        changed.append([x, t - SL.GT, z])
            ds = [site["d"](x, z) for x in range(w) for z in range(d)]
            r["slope_sites"][name] = {
                "module": mid, "origin": [ox, SL.GT, oz], "ground_relative_to_grade_min_max": [min(ds), max(ds)],
                "footing_columns_filled": len(cols), "max_fill_depth": max((c[2] for c in cols), default=0),
                "fill_blocks": sum(c[2] for c in cols), "template_cells": len(cells), "template_failures": len(fails),
                "failures": fails[:10], "hollow_cells": hollow[:10], "hollow_count": len(hollow),
                "outside_footprint_columns_changed": changed[:10], "outside_changed_count": len(changed),
                "terrain_cells_above_grade_inside_box_replaced_by_air_include": above}
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
