"""Verify placed templates and Jigsaw assemblies against saved Minecraft chunk data.

``/place structure`` does not persist structure starts, so piece placement is *recovered* from
the world: the start chamber is located by matching its blocks (four rotations), then every
connector's child is looked up in its pool by testing which pool template reproduces the
saved blocks at the position and rotation implied by the vanilla adjacency rule. Every
non-air block in the search volume must be explained by exactly one recovered piece.
"""

from __future__ import annotations

import importlib.util
import json
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("probe_world", HERE / "probe-world.py")
probe_world = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe_world)
from structure_export.nbt import read_nbt  # noqa: E402

DIRECTIONS = ("north", "east", "south", "west")
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
FRONT = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0)}
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
SIDE_PROPS = ("north", "east", "south", "west")


def rot_pos(pos, size, turns):
    x, y, z = pos
    sx, sy, sz = size
    for _ in range(turns % 4):
        x, z = sz - 1 - z, x
        sx, sz = sz, sx
    return (x, y, z), (sx, sy, sz)


def rot_face(face, turns):
    return DIRECTIONS[(DIRECTIONS.index(face) + turns) % 4]


def rot_state(state, turns):
    """Rotate a block state clockwise by ``turns`` quarter turns (vanilla Rotation semantics)."""
    turns %= 4
    props = state.get("properties")
    if not turns or not props:
        return state
    new = dict(props)
    if props.get("facing") in DIRECTIONS:
        new["facing"] = rot_face(props["facing"], turns)
    if "orientation" in props:
        face, _, up = props["orientation"].partition("_")
        if face in DIRECTIONS:
            new["orientation"] = f"{rot_face(face, turns)}_{up}"
    if props.get("axis") in ("x", "z") and turns % 2:
        new["axis"] = "z" if props["axis"] == "x" else "x"
    if all(side in props for side in SIDE_PROPS):
        for side in SIDE_PROPS:
            new[rot_face(side, turns)] = props[side]
    if "rotation" in props and props["rotation"].isdigit():
        new["rotation"] = str((int(props["rotation"]) + 4 * turns) % 16)
    return {**state, "properties": new}


class Template:
    def __init__(self, identifier, nbt):
        self.identifier = identifier
        self.size = tuple(nbt["size"])
        self.palette = nbt["palette"]
        self.cells = {}
        self.jigsaws = []
        for block in nbt["blocks"]:
            state = self.palette[block["state"]]
            pos = tuple(block["pos"])
            if state["id"] == "minecraft:jigsaw":
                face = state["properties"]["orientation"].split("_")[0]
                self.jigsaws.append({"pos": pos, "face": face, **block["nbt"]})
                continue
            self.cells[pos] = state
        self.solid = {p: s for p, s in self.cells.items() if s["id"] not in AIR}


class Placed:
    """A template placed with ``turns`` clockwise quarter turns, min corner at ``origin``."""

    def __init__(self, template, turns, origin):
        self.template, self.turns, self.origin = template, turns % 4, tuple(origin)
        _, self.size = rot_pos((0, 0, 0), template.size, self.turns)

    def world(self, local):
        rotated, _ = rot_pos(local, self.template.size, self.turns)
        return tuple(self.origin[i] + rotated[i] for i in range(3))

    def bbox(self):
        return self.origin, tuple(self.origin[i] + self.size[i] - 1 for i in range(3))

    def blocks(self, include_air=False):
        source = self.template.cells if include_air else self.template.solid
        return {self.world(p): rot_state(s, self.turns) for p, s in source.items()}

    def jigsaws(self):
        out = []
        for j in self.template.jigsaws:
            out.append({**j, "world_pos": self.world(j["pos"]), "world_face": rot_face(j["face"], self.turns)})
        return out


class World:
    """Non-air blocks of a bounded volume, decoded straight from saved region files."""

    def __init__(self, region_dir, lo, hi):
        import re

        self.lo, self.hi = tuple(lo), tuple(hi)
        self.cells = {}
        for region in sorted(Path(region_dir).glob("r.*.*.mca")):
            rx, rz = map(int, re.fullmatch(r"r\.(-?\d+)\.(-?\d+)\.mca", region.name).groups())
            for cx in range(max(lo[0] // 16, rx * 32), min(hi[0] // 16, rx * 32 + 31) + 1):
                for cz in range(max(lo[2] // 16, rz * 32), min(hi[2] // 16, rz * 32 + 31) + 1):
                    chunk = probe_world.read_region_chunk(region, cx, cz)
                    if chunk is not None:
                        self._load_chunk(chunk, cx, cz)

    def _load_chunk(self, chunk, cx, cz):
        lo, hi = self.lo, self.hi
        for section in chunk.get("sections", []):
            block_states = section.get("block_states")
            if not block_states:
                continue
            section_y = int(section["Y"])
            if (section_y + 1) * 16 - 1 < lo[1] or section_y * 16 > hi[1]:
                continue
            palette = [probe_world.normalize_palette_entry(e) for e in block_states["palette"]]
            if len(palette) == 1 and palette[0]["id"] in AIR:
                continue
            packed = {**section, "block_states": {**block_states, "palette": palette}}
            for ly in range(16):
                y = section_y * 16 + ly
                if not lo[1] <= y <= hi[1]:
                    continue
                for lz in range(16):
                    z = cz * 16 + lz
                    if not lo[2] <= z <= hi[2]:
                        continue
                    for lx in range(16):
                        x = cx * 16 + lx
                        if not lo[0] <= x <= hi[0]:
                            continue
                        state = probe_world.unpack_state(packed, lx, ly, lz)
                        if state["id"] not in AIR:
                            self.cells[(x, y, z)] = state

    def state(self, pos):
        return self.cells.get(tuple(pos), {"id": "minecraft:air"})

    def non_air(self):
        return self.cells


def load_pack(pack_dir):
    pack_dir = Path(pack_dir)
    base = pack_dir / "data/moreminecrafts"
    templates = {}
    for path in sorted((base / "structure").rglob("*.nbt")):
        identifier = "moreminecrafts:" + path.relative_to(base / "structure").with_suffix("").as_posix()
        templates[identifier] = Template(identifier, read_nbt(path.read_bytes())["value"])
    pools = {}
    for path in sorted((base / "worldgen/template_pool").rglob("*.json")):
        identifier = "moreminecrafts:" + path.relative_to(base / "worldgen/template_pool").with_suffix("").as_posix()
        data = json.loads(path.read_text())
        pools[identifier] = [e["element"]["location"] for e in data["elements"]]
    return templates, pools


def match_fraction(placed, world_non_air, include_air=False, world=None):
    expected = placed.blocks(include_air)
    ok = 0
    bad = []
    for pos, state in expected.items():
        if state["id"] in AIR:
            actual = {"id": "minecraft:air"} if pos not in world_non_air else world_non_air[pos]
        else:
            actual = world_non_air.get(pos, {"id": "minecraft:air"})
        if probe_world.state_matches(state, actual):
            ok += 1
        elif len(bad) < 8:
            bad.append((pos, state, actual))
    return ok, len(expected), bad


def locate_start(template, world_cells, anchor_local, anchor_id):
    """Every (turns, origin) at which all probed solid blocks of ``template`` are present.

    A rotationally symmetric chamber matches several rotations; the caller disambiguates using
    the child pieces, which are not symmetric.
    """
    found = []
    anchors = [p for p, s in world_cells.items() if s["id"] == anchor_id]
    items = sorted(template.solid.items())
    stride = max(1, len(items) // 40)
    probes = items[::stride]
    for pos in anchors:
        for turns in range(4):
            rotated, _ = rot_pos(anchor_local, template.size, turns)
            origin = tuple(pos[i] - rotated[i] for i in range(3))
            placed = Placed(template, turns, origin)
            if all(
                probe_world.state_matches(rot_state(s, turns), world_cells.get(placed.world(p), {"id": "minecraft:air"}))
                for p, s in probes
            ):
                found.append(placed)
    return found


def recover_assembly(templates, pools, world_cells, start_id, anchor_local, anchor_id):
    """Recover every piece of one assembly starting from ``start_id``; returns pieces and slot report."""
    candidates = locate_start(templates[start_id], world_cells, anchor_local, anchor_id)
    if not candidates:
        raise SystemExit("start chamber was not found in the saved world")
    best = None
    for start in candidates:
        result = _recover_from(templates, pools, world_cells, start_id, start)
        score = (sum(1 for s in result[1] if s["filled_with"] is not None), len(result[0]))
        if best is None or score > best[0]:
            best = (score, result)
    return best[1]


def _recover_from(templates, pools, world_cells, start_id, start):
    pieces = [{"id": start_id, "placed": start, "parent": None, "slot": None}]
    slots = []
    queue = deque([0])
    while queue:
        index = queue.popleft()
        parent = pieces[index]["placed"]
        for jig in parent.jigsaws():
            pool = jig["pool"]
            if pool == "minecraft:empty" or pool not in pools:
                continue
            face = jig["world_face"]
            cell = tuple(jig["world_pos"][i] + FRONT[face][i] for i in range(3))
            found = None
            tried = []
            for member in pools[pool]:
                child_template = templates[member]
                for cj in child_template.jigsaws:
                    if cj["name"] != jig["target"]:
                        continue
                    turns = (DIRECTIONS.index(OPPOSITE[face]) - DIRECTIONS.index(cj["face"])) % 4
                    rotated, _ = rot_pos(cj["pos"], child_template.size, turns)
                    origin = tuple(cell[i] - rotated[i] for i in range(3))
                    candidate = Placed(child_template, turns, origin)
                    ok, total, bad = match_fraction(candidate, world_cells)
                    tried.append({"template": member, "matched": ok, "expected": total})
                    if ok == total:
                        found = {"id": member, "placed": candidate, "parent": index, "slot": jig["name"]}
                        break
                if found:
                    break
            slots.append({"slot": jig["name"], "parent": pieces[index]["id"], "pool": pool, "face": face,
                          "filled_with": found["id"] if found else None, "tried": tried})
            if found:
                pieces.append(found)
                queue.append(len(pieces) - 1)
    return pieces, slots


def bbox_overlap(a, b):
    (alo, ahi), (blo, bhi) = a, b
    return all(alo[i] <= bhi[i] and blo[i] <= ahi[i] for i in range(3))


def verify_assembly(pieces, slots, world_cells):
    expected = {}
    overlaps = []
    for i, piece in enumerate(pieces):
        for pos, state in piece["placed"].blocks().items():
            if pos in expected:
                overlaps.append((pos, i))
            expected[pos] = state
    boxes = [p["placed"].bbox() for p in pieces]
    bbox_overlaps = [(i, j) for i in range(len(boxes)) for j in range(i + 1, len(boxes)) if bbox_overlap(boxes[i], boxes[j])]
    extras = [p for p in world_cells if p not in expected]
    missing = [p for p, s in expected.items() if not probe_world.state_matches(s, world_cells.get(p, {"id": "minecraft:air"}))]
    return {
        "pieces": len(pieces),
        "expected_blocks": len(expected),
        "world_blocks": len(world_cells),
        "missing_or_wrong": len(missing),
        "missing_examples": [list(p) for p in missing[:5]],
        "unexplained_extra_blocks": len(extras),
        "extra_examples": [list(p) for p in extras[:5]],
        "block_overlaps": len(overlaps),
        "bounding_box_overlaps": bbox_overlaps,
        "unfilled_slots": [s["slot"] for s in slots if s["filled_with"] is None],
        "pass": not missing and not extras and not overlaps and not bbox_overlaps,
    }


# --- accessibility (conservative integer-cell walk model) ------------------------------------
# Stairs, slabs and walls are treated as full solid blocks (a real player can do at least this
# well), a player is two cells tall, climbs one block, and may drop up to three blocks.
_PASSABLE_NAMES = {"air", "cave_air", "void_air", "jigsaw", "chain", "cobweb", "lantern", "soul_lantern", "lever",
                   "tripwire", "glow_lichen", "sculk_vein", "hanging_roots", "light", "vine", "fern", "short_grass"}
_PASSABLE_SUFFIXES = ("_carpet", "_button", "_torch", "_sign", "_banner", "_pressure_plate", "_head", "_skull", "candle",
                      "_wall_torch", "_hanging_sign", "_wall_banner", "_wall_sign", "_wall_head", "_wall_skull")


def passable(state):
    name = state["id"].split(":", 1)[1]
    return name in _PASSABLE_NAMES or name.endswith(_PASSABLE_SUFFIXES)


def reachable(cells_fn, start, limit_box, max_nodes=2_000_000):
    """BFS over feet cells; needs 2 clear cells and a solid cell below; steps up 1, falls up to 3."""
    lo, hi = limit_box

    def free(p):
        return passable(cells_fn(p))

    def stand(p):
        x, y, z = p
        return free((x, y, z)) and free((x, y + 1, z)) and not passable(cells_fn((x, y - 1, z)))

    seen = {start}
    queue = deque([start])
    while queue and len(seen) < max_nodes:
        x, y, z = queue.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            for dy in (1, 0, -1, -2, -3):
                p = (nx, y + dy, nz)
                if p in seen or not all(lo[i] <= p[i] <= hi[i] for i in range(3)) or not stand(p):
                    continue
                if dy == 1 and not free((x, y + 2, z)):
                    continue
                if dy < 0 and not all(free((nx, k, nz)) for k in range(y + dy, y + 2)):
                    continue
                seen.add(p)
                queue.append(p)
                break
    return seen


POI_BLOCKS = {"chest", "barrel", "trapped_chest", "spawner", "trial_spawner", "vault", "lectern", "crafting_table",
              "furnace", "blast_furnace", "smoker", "enchanting_table", "anvil"}


def assembly_walk_report(pieces, world):
    """Walkability from the plaza to every connector, deck lane, and room point of interest."""
    cells = world.cells

    def at(p):
        return cells.get(tuple(p), {"id": "minecraft:air"})

    start = pieces[0]["placed"]
    lo = tuple(min(p["placed"].bbox()[0][i] for p in pieces) for i in range(3))
    hi = tuple(max(p["placed"].bbox()[1][i] for p in pieces) for i in range(3))
    seed = start.world((23, 1, 23))
    seen = reachable(at, seed, (lo, hi))
    report = {"reachable_cells": len(seen), "checks": {}}
    ok = True
    for index, piece in enumerate(pieces):
        placed = piece["placed"]
        template = placed.template
        if index == 0:
            for jig in placed.jigsaws():
                if jig["pool"] == "minecraft:empty":
                    continue
                cell = tuple(jig["world_pos"][i] + FRONT[jig["world_face"]][i] for i in range(3))
                good = jig["world_pos"] in seen or cell in seen
                report["checks"][f"connector {jig['name']} reachable"] = bool(good)
                ok &= bool(good)
            # every deck lane standing cell (feet y=9, side-local depth 5..8) must be reachable
            deck_total = deck_ok = 0
            size = template.size[0]
            for x in range(size):
                for z in range(size):
                    depth = min(x, z, size - 1 - x, size - 1 - z)
                    if 5 <= depth <= 8 and template.cells.get((x, 8, z), {"id": "minecraft:air"})["id"] != "minecraft:air" \
                            and template.cells.get((x, 9, z), {"id": "minecraft:air"})["id"] == "minecraft:air":
                        deck_total += 1
                        deck_ok += placed.world((x, 9, z)) in seen
            report["checks"]["deck lane cells reachable"] = f"{deck_ok}/{deck_total}"
            ok &= deck_total > 0 and deck_ok == deck_total
        else:
            poi_total = poi_ok = 0
            for local, state in template.solid.items():
                name = state["id"].split(":")[1]
                if name in POI_BLOCKS or name.endswith("_bed"):
                    wp = placed.world(local)
                    near = [(wp[0] + dx, wp[1] + dy, wp[2] + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) for dy in (0, -1, 1)]
                    poi_total += 1
                    poi_ok += any(n in seen for n in near)
            lo_b, hi_b = placed.bbox()
            inside = sum(1 for p in seen if all(lo_b[i] <= p[i] <= hi_b[i] for i in range(3)))
            report["checks"][f"room {index} {piece['id'].rsplit('/', 1)[-1]}"] = {
                "reachable_standing_cells": inside, "poi_reachable": f"{poi_ok}/{poi_total}"}
            ok &= inside > 0 and poi_ok == poi_total
    report["pass"] = bool(ok)
    return report
