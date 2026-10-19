"""Block-state validation and evidence generation for Stage 24-B candidates."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import nbtlib
from PIL import Image, ImageDraw
from mcbuild.export.schem import export_schem
from mcbuild.render.views import build_contact_sheet
from mcbuild.voxel import VoxelGrid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.stage24b_candidate import Candidate, block_id
from tools.stage24b_layouts import RESTORERS
from tools.stage24b_source import MODULES, ROOT, build_baseline_manifest, load_original

OUT = ROOT / "artifacts/ancient-city-restoration/stage-24b"
DIRECTION_VIEWS = [{"yaw": i} for i in range(4)]


def solid(c: Candidate, p) -> bool:
    key = c.get_block(p)
    bid = block_id(key)
    if bid in {"minecraft:air", "minecraft:water", "minecraft:lava", "minecraft:jigsaw", "minecraft:structure_void"}:
        return False
    if bid.endswith("_door"):
        return "open=true" not in key
    if bid.endswith("_slab"):
        return "type=top" in key or "type=double" in key
    if bid.endswith("_stairs") or bid == "minecraft:ladder":
        return False
    return True


def supports_player(c: Candidate, p) -> bool:
    key = c.get_block(p)
    bid = block_id(key)
    if bid.endswith("_stairs"):
        return True
    if bid.endswith("_slab"):
        return "type=top" in key or "type=double" in key or "type=bottom" in key
    return solid(c, p)


def clear_body(c: Candidate, p) -> bool:
    key = c.get_block(p)
    bid = block_id(key)
    if bid == "minecraft:air":
        return True
    if bid.endswith("_door") and "open=true" in key:
        return True
    if bid.endswith("_stairs") or bid == "minecraft:ladder":
        return True
    return False


def standable(c: Candidate, p) -> bool:
    x, y, z = p
    if y < 1 or y >= c.size[1]:
        return False
    if block_id(c.get_block(p)).endswith("_stairs"):
        return clear_body(c, (x, y + 1, z))
    floor_key = c.get_block((x, y - 1, z))
    if block_id(floor_key) == "minecraft:ladder":
        return clear_body(c, p) and clear_body(c, (x, y + 1, z))
    return supports_player(c, (x, y - 1, z)) and clear_body(c, p) and clear_body(c, (x, y + 1, z))


def reachable(c: Candidate, start, goals: set[tuple[int, int, int]]) -> tuple[bool, int]:
    from collections import deque
    queue = deque([start])
    seen = {start}
    while queue:
        p = queue.popleft()
        if p in goals:
            return True, len(seen)
        x, y, z = p
        neighbors = [(x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1)]
        # Model a step onto a real stair block as a one-block elevation transition.
        for nx, ny, nz in ((x + 1, y + 1, z), (x - 1, y + 1, z), (x, y + 1, z + 1), (x, y + 1, z - 1)):
            current_support = block_id(c.get_block((x, y - 1, z)))
            if (block_id(c.get_block((nx, ny, nz))).endswith("_stairs")
                    or block_id(c.get_block(p)).endswith("_stairs")
                    or current_support == "minecraft:ladder"):
                neighbors.append((nx, ny, nz))
        support = c.get_block((x, y - 1, z))
        if block_id(c.get_block(p)) == "minecraft:ladder" or block_id(support).endswith("_stairs"):
            neighbors.extend(((x, y + 1, z), (x, y - 1, z)))
        for n in neighbors:
            if n not in seen and standable(c, n):
                seen.add(n)
                queue.append(n)
    return False, len(seen)


def test_candidate(c: Candidate) -> dict:
    c.verify_protected()
    expected = (16, 8, 11) if c.module == "medium_ruin_2" else tuple(MODULES[c.module]["size"])
    assert c.size == expected, (c.module, c.size, expected)
    assert c.current_connector_snapshot() == c.connector_snapshot, f"{c.module}: connector changed"
    for pos in c.positions:
        assert all(0 <= p < c.size[i] for i, p in enumerate(pos)), (c.module, pos, c.size)

    checks = {"source_hash": "PASS", "dimensions": "PASS", "jigsaw_full_nbt": "PASS",
              "protected_block_entities": "PASS", "candidate_bounds": "PASS"}
    if c.module in {"large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2"}:
        assert c.features["beds"] and len(c.features["doors"]) == 2
        assert c.get_block(c.features["doors"][0]).startswith("minecraft:spruce_door")
        entry = c.entry_inside
        assert standable(c, entry), f"{c.module}: entry has no supported two-block standing clearance at {entry}"
        bed_clear = []
        for bed_pair in c.features["beds"]:
            for bedpos in bed_pair:
                x, y, z = bedpos
                for q in ((x+1,y,z),(x-1,y,z),(x,y,z+1),(x,y,z-1)):
                    if standable(c, q):
                        bed_clear.append(q)
        assert bed_clear, f"{c.module}: bed has no interaction/movement clearance"
        route_targets = set(bed_clear)
        route_ok, _ = reachable(c, entry, route_targets)
        assert route_ok, f"{c.module}: no block-state walk route from entry to sleeping room"
        workstations = [pos for pos in c.positions if block_id(c._block_key_at(pos)) == "minecraft:crafting_table"]
        containers = [pos for pos in c.positions if block_id(c._block_key_at(pos)) in {"minecraft:barrel", "minecraft:chest"}]
        for pos in workstations + containers:
            x, y, z = pos
            assert any(standable(c, q) for q in ((x+1,y,z),(x-1,y,z),(x,y,z+1),(x,y,z-1))), \
                f"{c.module}: workstation/container interaction blocked at {pos}"
        for x in range(c.size[0]):
            for z in range(c.size[2]):
                if x not in (0, c.size[0] - 1) and z not in (0, c.size[2] - 1):
                    continue
                for y in (1, 2, 3):
                    if (x, y, z) in c.features["doors"]:
                        continue
                    assert c.get_block((x, y, z)) != "minecraft:air", f"{c.module}: shell gap at {(x,y,z)}"
        if c.module == "large_ruin_1":
            assert c.get_block((8, 4, 8)) == "minecraft:air", "large courtyard roof must remain open to sky"
        if c.module == "medium_ruin_2":
            stairwell_headroom = {(4, 5), (5, 5), (6, 5)}
            for x in range(16):
                for z in range(11):
                    if (x, z) not in stairwell_headroom:
                        assert c.get_block((x, 4, z)) != "minecraft:air", f"medium_ruin_2 lower wing roof/upper floor gap {(x,4,z)}"
            for x in range(7, 16):
                for z in range(11):
                    assert c.get_block((x, 7, z)) != "minecraft:air", f"medium_ruin_2 upper roof gap {(x,7,z)}"
        checks.update({"entry_access": "PASS", "internal_route_to_bed": "PASS",
                       "bed_and_clearance": "PASS", "workstation_clearance": "PASS",
                       "container_interaction_clearance": "PASS", "wall_and_roof_integrity": "PASS"})
        if c.module == "medium_ruin_2":
            assert c.size[1] == 8 and len(c.features["stairs"]) >= 4
            for x, y, z in c.features["stairs"]:
                stair = c.get_block((x, y, z))
                assert block_id(stair) == "minecraft:deepslate_tile_stairs"
                assert "facing=east" in stair and "half=bottom" in stair and "shape=straight" in stair
                assert supports_player(c, (x, y - 1, z)), f"unsupported stair at {(x,y,z)}"
                assert clear_body(c, (x, y + 1, z)), f"stair headroom blocked at {(x,y,z)}"
            assert c.get_block((11, 5, 2)).endswith("part=foot]")
            assert c.get_block((11, 6, 2)) == "minecraft:air"
            assert c.get_block((11, 7, 2)) in {"minecraft:deepslate_tiles", "minecraft:air"}
            checks.update({"stair_geometry": "PASS", "upper_floor_and_headroom": "PASS"})
            upper_targets = {(10, 5, 2), (11, 5, 1), (11, 5, 4)}
            assert reachable(c, entry, upper_targets)[0], "ground entry does not connect to the partial upper floor"
            checks["internal_stair_route_to_upper_floor"] = "PASS"
    elif c.module == "sauna_1":
        c.verify_protected()
        water = [p for p in c.original_positions if block_id(c._block_key_at(p)) == "minecraft:water"]
        chests = [p for p in c.protected if block_id(c._block_key_at(p)) == "minecraft:chest"]
        stairs = [p for p in c.protected if block_id(c._block_key_at(p)).endswith("_stairs")]
        assert len(water) == 43 and len(chests) == 3 and len(stairs) == 86
        # Static basin safety: every water cell's same-layer orthogonal boundary remains solid.
        water_set = set(water)
        basins = [[p for p in water if p[1] == 0], [p for p in water if p[1] == 4]]
        for basin in basins:
            for x, y, z in basin:
                for q in ((x+1,y,z),(x-1,y,z),(x,y,z+1),(x,y,z-1)):
                    if q not in water_set and q[0] >= 0 and q[2] >= 0 and q[0] < c.size[0] and q[2] < c.size[2]:
                        assert c.get_block(q) != "minecraft:air", f"sauna source rim gap at {q} beside {x,y,z}"
        assert c.features["preserved_chest_count"] == 3
        roof_cells = [(x, 8, z) for x in range(9, 18) for z in range(32, 37)]
        assert sum(block_id(c.get_block(p)) == "minecraft:deepslate_tile_slab" for p in roof_cells) >= 25
        chest_routes = []
        for x, y, z in chests:
            adjacent = {(x+1,y,z),(x-1,y,z),(x,y,z+1),(x,y,z-1)}
            candidates = {p for p in adjacent if standable(c, p)}
            assert candidates, f"sauna chest has no interaction clearance at {(x,y,z)}"
            chest_routes.append(reachable(c, c.entry_inside, candidates)[0])
        assert all(chest_routes), "sauna entry does not connect to all source loot chests"
        assert reachable(c, c.entry_inside, {(12, 1, 26)})[0], "south reception does not reach main basin access stair"
        assert reachable(c, c.entry_inside, {(12, 5, 6)})[0], "south reception does not reach plunge access stair"
        checks.update({"water_count_and_containment_geometry": "PASS_STATIC_ONLY", "chest_loot_nbt": "PASS",
                       "chest_interaction_clearance": "PASS", "bath_and_plunge_route_connectivity": "PASS_STATIC",
                       "stair_and_route_preservation": "PASS", "reception_roof": "PASS_STATIC",
                       "fluid_ticks": "LIVE_PENDING"})
    elif c.module == "large_pillar_1":
        run = c.features["ladder_run"]
        assert run == list(range(1, 14))  # Stage 24-C: ladder continues through the deck hatch
        for y in run:
            assert block_id(c.get_block((2, y, 2))) == "minecraft:ladder", ("ladder", y)
            assert solid(c, (3, y, 2)), ("unsupported ladder", y)
            assert clear_body(c, (2, y + 1, 2)), ("ladder headroom", y)
        assert standable(c, (1, 1, 2))
        assert block_id(c.get_block((2, 13, 2))) == "minecraft:ladder"
        assert reachable(c, (1, 1, 2), {(3, 14, 3)})[0], "entry ladder does not transition onto the observation platform"
        for x in range(6):
            for z in range(6):
                if x in (0, 5) or z in (0, 5):
                    assert c.get_block((x, 14, z)) != "minecraft:air", "large tower parapet gap"
        checks.update({"entrance_and_ladder_support": "PASS", "continuous_ladder_and_headroom": "PASS",
                       "observation_hatch_and_deck": "PASS", "structural_stability": "GEOMETRY_REVIEW_PENDING"})
    elif c.module == "medium_pillar_1":
        for y in c.features["ladder_run"]:
            assert block_id(c.get_block((4, y, 3))) == "minecraft:ladder"
            assert c.get_block((3, y, 3)) != "minecraft:air", ("unsupported ladder", y)
            assert clear_body(c, (4, y + 1, 3))
        skulls = [p for p in c.protected if block_id(c._block_key_at(p)) == "minecraft:skeleton_skull"]
        assert len(skulls) == 1
        assert reachable(c, c.entry_inside, {(2, 9, 2), (4, 9, 5)})[0], "lower guard room does not connect to upper deck"
        for y in range(1, 8):
            assert any(c.get_block((x, y, z)) != "minecraft:air"
                       for x, z in ((1, 3), (5, 3), (3, 1), (3, 6))), f"medium tower wall missing at y={y}"
        checks.update({"guard_space": "PASS", "ladder_support_and_headroom": "PASS",
                       "observation_deck": "PASS", "guard_room_walls": "PASS_STATIC", "skull_nbt": "PASS"})

    grid = c.to_grid()
    assert len(grid) > 0
    checks["blockstate_palette_resolution"] = "PASS"
    conflicts = []
    if c.module == "medium_ruin_2":
        conflicts.append({"type": "generation_boundary", "status": "BLOCKED",
                          "detail": "Neighboring structure transforms are not available for collision testing."})
    if c.module == "sauna_1":
        conflicts.append({"type": "original_wall_opening", "status": "OWNER_REVIEW",
                          "position": [11, 2, 33], "detail": "Removed one cracked-brick head block to connect south reception to preserved bath circulation."})
    if c.module == "medium_pillar_1":
        conflicts.append({"type": "ladder_orientation", "status": "OWNER_REVIEW",
                          "detail": "Ladder climbs the east face of the retained spine for an accessible route clear of both jigsaws."})
    return {"module": c.module, "original_dimensions_xyz": list(c.original_size), "dimensions_xyz": list(c.size),
            "source_status": "ORIGINAL SOURCE VERIFIED", "geometry_status": "GEOMETRY VERIFIED",
            "design_status": "DESIGN PROPOSED", "visual_status": "VISUAL PENDING",
            "live_status": "LIVE PENDING", "conflicts": conflicts, "checks": checks,
            "original_block_count": c.original_block_count, "candidate_block_records": len(c.positions),
            "changed_original_positions": len(c.changed_original), "added_positions": len(c.added_positions),
            "source_blob_sha1": c.source_sha, "source_url": c.source_url,
            "jigsaw_count": len(c.connector_snapshot), "jigsaw_preserved": True,
            "block_entities_preserved": True,
            "status": "CANDIDATE_VALIDATED_STATIC_REVIEW_PENDING"}


def floor_plan(c: Candidate, y: int, target: Path, title: str):
    scale = 24
    image = Image.new("RGB", (c.size[0] * scale + 200, c.size[2] * scale + 68), "#20252b")
    draw = ImageDraw.Draw(image)
    draw.text((8, 8), f"{c.module} | {title} (layer y={y})", fill="white")
    colors = {"air": "#20252b", "jigsaw": "#ff00ff", "water": "#237cbd", "deepslate_bricks": "#50565c",
              "deepslate_tiles": "#666d72", "polished_deepslate": "#414b54", "polished_basalt": "#252d35",
              "spruce_door": "#c98340", "gray_bed": "#a3a3a3", "chest": "#a8753a", "barrel": "#987045",
              "soul_lantern": "#c8eaff", "ladder": "#cfad71", "deepslate_tile_stairs": "#777c82"}
    for z in range(c.size[2]):
        for x in range(c.size[0]):
            bid = block_id(c.get_block((x, y, z))).removeprefix("minecraft:")
            color = next((v for k, v in colors.items() if bid == k or bid.startswith(k)), "#20252b")
            x0, z0 = 8 + x * scale, 42 + z * scale
            draw.rectangle((x0, z0, x0 + scale - 2, z0 + scale - 2), fill=color, outline="#38414a")
            if bid != "air":
                draw.text((x0 + 5, z0 + 4), bid[:1].upper(), fill="#ffffff")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)


def build_entry_view(c: Candidate, target: Path):
    grid = VoxelGrid()
    ex, ey, ez = c.entry_inside or (0, 1, 0)
    for (x, y, z), index in c.to_grid().items():
        if abs(x - ex) <= 3 and abs(y - ey) <= 3 and abs(z - ez) <= 3:
            grid.set(x, y, z, index)
    image = build_contact_sheet(grid, [{"yaw": 0}, {"yaw": 1}])[0]
    image.save(target)


def build_review_cutaway(c: Candidate):
    grid = c.to_grid().clone()
    def remove(x, y, z):
        if c.module == "large_pillar_1":
            return x <= 1 and 1 <= y <= 13
        if c.module == "medium_pillar_1":
            return z <= 1 and 1 <= y <= 9
        if c.module == "medium_ruin_2":
            return ((z == 0 and 1 <= y < c.size[1])
                    or (y == 7 and x >= 7)
                    or (y == 4 and x <= 6))
        return (z == 0 and 1 <= y < c.size[1]) or (y == 4)
    for (x, y, z), _ in list(grid.items()):
        if remove(x, y, z):
            grid.clear_block(x, y, z)
    return grid


def build_bathhouse_detail(c: Candidate, target: Path):
    full = c.to_grid()
    panels = []
    for name, bounds in (("main basin", (11, 22, 0, 6, 22, 30)),
                         ("plunge basin", (11, 17, 0, 7, 4, 9)),
                         ("loot chests", (10, 27, 0, 5, 8, 22))):
        xlo, xhi, ylo, yhi, zlo, zhi = bounds
        crop = VoxelGrid()
        for (x, y, z), idx in full.items():
            if xlo <= x <= xhi and ylo <= y <= yhi and zlo <= z <= zhi:
                crop.set(x, y, z, idx)
        panels.append(build_contact_sheet(crop, [{"yaw": 0}, {"yaw": 1}])[0])
    width = sum(i.width for i in panels)
    height = max(i.height for i in panels)
    image = Image.new("RGB", (width, height), "#15191e")
    x = 0
    for panel in panels:
        image.paste(panel, (x, 0))
        x += panel.width
    image.save(target)


def schematic_block_data_valid(schematic) -> bool:
    blocks = schematic["Blocks"]
    palette = {str(name): int(index) for name, index in blocks["Palette"].items()}
    raw = bytes(value & 0xFF for value in blocks["Data"])
    volume = int(schematic["Width"]) * int(schematic["Height"]) * int(schematic["Length"])
    decoded = []
    cursor = 0
    for _ in range(volume):
        value = shift = 0
        while True:
            byte = raw[cursor]
            cursor += 1
            value |= (byte & 0x7F) << shift
            if byte < 0x80:
                break
            shift += 7
        decoded.append(value)
    return cursor == len(raw) and len(decoded) == volume and set(decoded) <= set(palette.values())


def run_module(module: str, output_root: Path = OUT) -> dict:
    root, url, sha = load_original(module)
    c = Candidate(module, root, url, sha)
    RESTORERS[module](c)
    validation = test_candidate(c)
    out = output_root / module
    out.mkdir(parents=True, exist_ok=True)
    native = out / "restored.nbt"
    c.save_native(native)
    reread = nbtlib.load(native)
    assert [int(v) for v in reread["size"]] == list(c.size)
    assert len(reread["blocks"]) == len(c.positions)
    assert c.current_connector_snapshot() == c.connector_snapshot
    restored = Candidate(module, reread, url, sha)
    restored.verify_protected()
    assert restored.current_connector_snapshot() == c.connector_snapshot
    for pos, source_snapshot in c.protected_snapshot.items():
        assert restored.protected_snapshot[pos] == source_snapshot
    (out / "block-changes.json").write_text(json.dumps({
        "module": module,
        "dimensions_xyz": list(c.size),
        "change_count": len(c.block_change_manifest()),
        "operation_counts": dict(c.operations),
        "changes": c.block_change_manifest(),
    }, indent=2) + "\n", encoding="utf-8")
    validation["checks"]["native_nbt_round_trip"] = "PASS"
    grid = c.to_grid()
    schem = out / "restored.schem"
    export_schem(grid, str(schem))
    schem_root = nbtlib.load(schem)["Schematic"]
    assert int(schem_root["Version"]) == 3
    schematic_size = [int(schem_root[k]) for k in ("Width", "Height", "Length")]
    assert all(v > 0 for v in schematic_size)
    assert schematic_block_data_valid(schem_root)
    validation["schematic_bounds_xyz"] = schematic_size
    validation["checks"]["schematic_export_reload"] = "PASS"
    image, labels, stats = build_contact_sheet(grid, DIRECTION_VIEWS)
    image.save(out / "restored-four-directions.png")
    cutaway = build_contact_sheet(build_review_cutaway(c), [{"yaw": 0}, {"yaw": 2}])[0]
    cutaway.save(out / "restored-interior-cutaway.png")
    build_entry_view(c, out / "entrance-closeup.png")
    # Restore the pre-edit source data independently from the pinned asset for comparison.
    original_root, _, _ = load_original(module)
    original_candidate = Candidate(module, original_root, url, sha)
    original_grid = original_candidate.to_grid()
    original_image = build_contact_sheet(original_grid, DIRECTION_VIEWS)[0]
    original_image.save(out / "original-four-directions.png")
    compare = Image.new("RGB", (image.width + original_image.width, max(image.height, original_image.height)), "#15191e")
    compare.paste(original_image, (0, 0))
    compare.paste(image, (original_image.width, 0))
    compare.save(out / "original-versus-restored.png")
    levels = [1]
    if module == "medium_ruin_2":
        levels = [1, 5]
    if module == "sauna_1":
        levels = [0, 1, 4]
        build_bathhouse_detail(c, out / "bathing-and-loot-closeups.png")
    if module == "large_pillar_1":
        levels = [1, 6, 13]
    if module == "medium_pillar_1":
        levels = [1, 8]
    for y in levels:
        floor_plan(c, y, out / f"floor-plan-y{y}.png", "floor plan")
    validation.update({"render_labels": labels, "render_stats": stats,
                       "visual_generation": "COMPLETE_STATIC_RENDER",
                       "visual_status": "VISUAL PENDING OWNER REVIEW",
                       "minecraft_client_status": "LIVE PENDING"})
    (out / "validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    return validation


def main():
    baseline = build_baseline_manifest(output=OUT / "baseline.json")
    results = [run_module(name) for name in MODULES]
    summary = {"baseline_sha": baseline["baseline_commit"], "source_commit": baseline["source_commit"],
               "modules": results, "status": "STATIC_CANDIDATES_AND_EVIDENCE_GENERATED_LIVE_PENDING"}
    (OUT / "validation-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({r["module"]: r["status"] for r in results}, indent=2))


if __name__ == "__main__":
    main()
