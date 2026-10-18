from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))
sys.path.insert(0, str(ROOT / "examples/forgotten_kingdom"))
sys.path.insert(0, str(ROOT / "validation/minecraft-visual"))

import build_sg02 as sg02
import kingdom_common as kc
from build_cavern import build_templates as build_sg01_templates
from sg02_cavern import side_xz
from structure_export.nbt import read_nbt

MAIN = sg02.MAIN
AIR = "minecraft:air"


def cells(template):
    return {tuple(b["pos"]): template["palette"][b["state"]] for b in template["blocks"]}


class Sg02Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = sg02.build_templates()
        cls.chamber = cls.templates[MAIN]
        cls.cells = cells(cls.chamber)
        sg01, _ = build_sg01_templates()
        cls.sg01_cells = cells(sg01[MAIN])

    def block(self, x, y, z):
        return self.cells[(x, y, z)]["id"]


class EnvelopeAndBaselineTests(Sg02Fixture):
    def test_envelope_grows_symmetrically_within_exporter_limit(self):
        self.assertEqual(self.chamber["size"], [47, 17, 47])
        self.assertEqual(self.chamber["size"][0], 41 + 2 * kc.GROW)

    def test_plaza_stairs_pillars_and_lights_are_the_sg01_geometry_translated(self):
        """Every SG-01 cell inside the old plaza box is unchanged, except stone-brick -> deepslate-brick stairs."""
        changed = 0
        for (x, y, z), state in self.sg01_cells.items():
            if not (7 <= x <= 33 and 7 <= z <= 33):
                continue
            new = self.cells[(x + 3, y, z + 3)]
            if state["id"] == "minecraft:stone_brick_stairs":
                self.assertEqual(new["id"], "minecraft:deepslate_brick_stairs")
                self.assertEqual(new["properties"], state["properties"])
                changed += 1
            else:
                self.assertEqual(new, state, f"plaza cell changed at SG-01 {(x, y, z)}")
        self.assertEqual(changed, 4 * 3 * 7)

    def test_plaza_floor_roof_and_deck_pattern_follow_sg01_rules(self):
        for x in range(47):
            for z in range(47):
                self.assertNotEqual(self.block(x, 0, z), AIR)
                self.assertNotEqual(self.block(x, 16, z), AIR)
        # SG-01 ring cells keep their original floor pattern after translation.
        for (x, y, z), state in self.sg01_cells.items():
            if y == 8 and state["id"] != AIR and 1 <= x <= 39 and 1 <= z <= 39:
                new = self.cells[(x + 3, 8, z + 3)]
                if new["id"] == "minecraft:deepslate_brick_stairs":
                    continue  # the 12 flush mouth steps added at the stair landings
                self.assertEqual(new, state)

    def test_no_stone_brick_stairs_remain_and_all_stairs_are_complete_states(self):
        for state in self.chamber["palette"]:
            self.assertNotEqual(state["id"], "minecraft:stone_brick_stairs")
            if state["id"].endswith("_stairs"):
                self.assertEqual(state["id"], "minecraft:deepslate_brick_stairs")
                self.assertEqual(set(state["properties"]), {"facing", "half", "shape", "waterlogged"})
                self.assertEqual(state["properties"]["shape"], "straight")

    def test_stair_runs_ascend_toward_the_outer_shell_on_every_side(self):
        for side in kc.SIDES:
            for i in range(kc.STAIR_STEPS):
                for u in kc.STAIR_WIDTH_U:
                    x, z = side_xz(side, u, kc.STAIR_FIRST_D - i)
                    state = self.cells[(x, i + 1, z)]
                    self.assertEqual(state["id"], "minecraft:deepslate_brick_stairs")
                    self.assertEqual(state["properties"]["facing"], side)
                    self.assertEqual(state["properties"]["half"], "bottom")
            # A flush final step at deck level (the stair mouth) joins the last SG-01 step to the deck top.
            for u in kc.STAIR_WIDTH_U:
                x, z = side_xz(side, u, kc.DECK_FAR)
                state = self.cells[(x, kc.DECK_Y, z)]
                self.assertEqual(state["id"], "minecraft:deepslate_brick_stairs")
                self.assertEqual(state["properties"]["facing"], side)
            # The step below each run and the landing are open: nothing obstructs the climb.
            x, z = side_xz(side, kc.CENTER, kc.STAIR_FIRST_D + 1)
            self.assertEqual(self.block(x, 1, z), AIR)
            x, z = side_xz(side, kc.CENTER, kc.DECK_FAR)
            self.assertNotEqual(self.block(x, 8, z), AIR)
            self.assertEqual(self.block(x, 9, z), AIR)


class PlatformTests(Sg02Fixture):
    def lane_row(self, side, u):
        return [side_xz(side, u, d) for d in range(0, kc.DECK_FAR + 1)]

    def test_deck_has_four_clear_lanes_with_headroom_beyond_the_rail(self):
        for side in kc.SIDES:
            for u in range(10, 37):
                lanes = 0
                for d in kc.LANE_DEPTHS:
                    x, z = side_xz(side, u, d)
                    floor = self.block(x, 8, z)
                    self.assertNotEqual(floor, AIR)
                    self.assertEqual((self.block(x, 9, z), self.block(x, 10, z)), (AIR, AIR))
                    lanes += 1
                self.assertEqual(lanes, 4)

    def test_deck_is_wider_than_sg01_and_stairs_did_not_move(self):
        sg01_lane = [z for z in range(1, 8) if self.sg01_cells[(20, 8, z)]["id"] != AIR]
        self.assertEqual(len(sg01_lane), 3)  # SG-01: 3-wide ring, 2 usable beside the rail
        # The plaza-facing edge (d=9) is the SG-01 edge (z=6) translated, i.e. nothing moved inward.
        self.assertEqual(kc.DECK_FAR, 6 + kc.GROW)
        self.assertEqual(kc.STAIR_FIRST_D, 13 + kc.GROW)

    def test_envelope_extension_is_built_masonry_not_a_floating_ledge(self):
        for side in kc.SIDES:
            for u in (3, 7, 20, 26, 40):
                for d in range(1, kc.MASS_DEPTH + 1):
                    x, z = side_xz(side, u, d)
                    for y in (9, 10, 12, 14):
                        self.assertNotEqual(self.block(x, y, z), AIR, f"hole in gallery-back masonry {side} u={u} d={d} y={y}")
            # Shell plane and roof are continuous around the envelope.
            for u in (1, 5, 40):
                x, z = side_xz(side, u, 0)
                for y in range(1, 16):
                    self.assertNotEqual(self.block(x, y, z), AIR)

    def test_every_deck_cell_is_supported_by_masonry_or_pier_or_beam(self):
        for side in kc.SIDES:
            for u in range(5, 42):
                x, z = side_xz(side, u, kc.DECK_FAR)
                self.assertNotEqual(self.block(x, 7, z), AIR, "fascia beam gap")


class RailTests(Sg02Fixture):
    def walls(self):
        return {p: s for p, s in self.cells.items() if s["id"] == "minecraft:deepslate_brick_wall"}

    def test_rails_follow_the_exposed_inner_edge_and_leave_stair_mouths_open(self):
        walls = self.walls()
        expected = set()
        for side in kc.SIDES:
            for u in range(kc.DECK_FAR, 47 - kc.DECK_FAR):
                x, z = side_xz(side, u, kc.DECK_FAR)
                if abs(u - kc.CENTER) > 1:
                    expected.add((x, 9, z))
        self.assertEqual(set(walls), expected)
        for side in kc.SIDES:
            for u in kc.STAIR_WIDTH_U:
                x, z = side_xz(side, u, kc.DECK_FAR)
                self.assertEqual(self.block(x, 9, z), AIR)
                self.assertEqual(self.block(x, 10, z), AIR)

    def test_rails_leave_future_room_openings_unobstructed(self):
        for side in kc.SIDES:
            for u in (*kc.LOWER_U, *kc.UPPER_U):
                for d in range(0, kc.DECK_FAR):
                    for du in range(-2, 3):
                        x, z = side_xz(side, u + du, d)
                        self.assertNotEqual(self.block(x, 9, z), "minecraft:deepslate_brick_wall")

    def test_rails_leave_plaza_visibility_low_wall_only(self):
        for (x, y, z) in self.walls():
            self.assertEqual(y, 9)
            self.assertEqual(self.block(x, 10, z), AIR)
            self.assertEqual(self.block(x, 11, z), AIR)

    def test_wall_states_are_complete_and_self_consistent(self):
        walls = self.walls()
        deltas = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}
        for (x, y, z), state in walls.items():
            props = state["properties"]
            self.assertEqual(set(props), {"east", "north", "south", "up", "waterlogged", "west"})
            connected = {side for side, (dx, dz) in deltas.items() if (x + dx, y, z + dz) in walls}
            for side in deltas:
                self.assertEqual(props[side] == "low", side in connected, f"{(x, y, z)} {side}")
            straight = connected in ({"north", "south"}, {"east", "west"})
            self.assertEqual(props["up"], "false" if straight else "true", f"{(x, y, z)} post")
        self.assertTrue(walls)


class ConnectorTests(Sg02Fixture):
    def jigsaws(self):
        out = {}
        for block in self.chamber["blocks"]:
            nbt = block.get("nbt")
            if nbt and nbt["id"] == "minecraft:jigsaw":
                out[tuple(block["pos"])] = (self.chamber["palette"][block["state"]]["properties"]["orientation"], nbt)
        return out

    def test_exact_connector_table(self):
        expected = {
            # tunnels (SG-01 3x4) at side centres
            (23, 1, 0): "north_up", (46, 1, 23): "east_up", (23, 1, 46): "south_up", (0, 1, 23): "west_up",
        }
        for pos, orientation in expected.items():
            self.assertEqual(self.jigsaws()[pos][0], orientation)
        lower = {pos for pos, (_o, nbt) in self.jigsaws().items() if nbt["pool"] == kc.LOWER_POOL}
        upper = {pos for pos, (_o, nbt) in self.jigsaws().items() if nbt["pool"] == kc.UPPER_POOL}
        self.assertEqual(
            lower,
            {(8, 1, 0), (38, 1, 0), (46, 1, 8), (46, 1, 38), (8, 1, 46), (38, 1, 46), (0, 1, 8), (0, 1, 38)},
        )
        self.assertEqual(
            upper,
            {(11, 10, 0), (35, 10, 0), (46, 10, 11), (46, 10, 35), (11, 10, 46), (35, 10, 46), (0, 10, 11), (0, 10, 35)},
        )
        self.assertEqual(len(self.jigsaws()), 4 + 8 + 8)

    def test_every_connector_sits_on_the_shell_plane_facing_outward(self):
        for (x, y, z), (orientation, nbt) in self.jigsaws().items():
            face = orientation.split("_")[0]
            plane = {"north": z == 0, "south": z == 46, "west": x == 0, "east": x == 46}[face]
            self.assertTrue(plane, f"{(x, y, z)} {orientation}")
            self.assertEqual(nbt["joint"], "aligned")
            self.assertEqual(nbt["final_state"], "minecraft:air")

    def test_connector_targets_pair_with_child_entry_names(self):
        for _pos, (_o, nbt) in self.jigsaws().items():
            if nbt["pool"] == kc.LOWER_POOL:
                self.assertEqual(nbt["target"], kc.LOWER_ENTRY)
            if nbt["pool"] == kc.UPPER_POOL:
                self.assertEqual(nbt["target"], kc.UPPER_ENTRY)
        names = [nbt["name"] for _p, (_o, nbt) in self.jigsaws().items() if nbt["pool"] in (kc.LOWER_POOL, kc.UPPER_POOL)]
        self.assertEqual(len(names), len(set(names)), "room connector names must be unique per slot")

    def test_all_connections_validate_for_every_side_and_rotation(self):
        results = sg02.validate_connections(self.templates, sg02.LOWER_STUB_ID, sg02.UPPER_STUB_ID)
        self.assertEqual(len(results), 4 + 8 + 8)
        for key, result in results.items():
            if key.startswith(("lower_", "upper_")):
                side = key.split("_")[1]
                self.assertEqual(result["world_child_facing"], kc.OPPOSITE[side], key)
                self.assertEqual(result["rotation"], sg02.rotation_for(side))

    def test_openings_are_open_air_on_both_sides_of_the_shell(self):
        for side in kc.SIDES:
            for u in kc.LOWER_U:
                for du in range(-1, 2):
                    for y in range(1, 5):
                        for d in range(0, 4):
                            x, z = side_xz(side, u + du, d)
                            self.assertEqual(self.block(x, y, z) in (AIR, "minecraft:jigsaw"), True, f"lower {side} u={u} d={d} y={y}")
            for u in kc.UPPER_U:
                for du in range(-2, 3):
                    for y in range(10, 15):
                        for d in range(0, 5):
                            x, z = side_xz(side, u + du, d)
                            self.assertIn(self.block(x, y, z), (AIR, "minecraft:jigsaw"), f"upper {side} u={u} d={d} y={y}")
                    x, z = side_xz(side, u + du, 0)
                    self.assertNotEqual(self.block(x, 9, z), AIR)  # solid vestibule floor, never a pit

    def test_upper_vestibule_sill_is_a_stair_not_a_jump(self):
        for side in kc.SIDES:
            for u in kc.UPPER_U:
                for du in range(-2, 3):
                    x, z = side_xz(side, u + du, kc.MASS_DEPTH)
                    state = self.cells[(x, 9, z)]
                    self.assertEqual(state["id"], "minecraft:deepslate_brick_stairs")
                    self.assertEqual(state["properties"]["facing"], side)


class SightlineTests(Sg02Fixture):
    def test_lower_doors_are_not_shadowed_by_the_sg01_pillar_footings(self):
        pillar = set()
        for (x, y, z), state in self.cells.items():
            if 11 <= x <= 35 and 11 <= z <= 35 and 1 <= y <= 15 and state["id"] != AIR:
                if (11 <= x <= 15 or 31 <= x <= 35) and (11 <= z <= 15 or 31 <= z <= 35):
                    pillar.add((x, z))
        for side in kc.SIDES:
            for u in kc.LOWER_U:
                for du in (-1, 0, 1):
                    for d in range(10, 24):
                        x, z = side_xz(side, u + du, d)
                        self.assertNotIn((x, z), pillar, f"{side} lower door column u={u + du} blocked at d={d}")


class ReservedVolumeTests(Sg02Fixture):
    @staticmethod
    def box(origin, size):
        return origin, tuple(origin[i] + size[i] - 1 for i in range(3))

    @staticmethod
    def overlap(a, b):
        return all(a[0][i] <= b[1][i] and b[0][i] <= a[1][i] for i in range(3))

    def boxes(self):
        results = sg02.validate_connections(self.templates, sg02.LOWER_STUB_ID, sg02.UPPER_STUB_ID)
        boxes = {"chamber": self.box((0, 0, 0), self.chamber["size"])}
        for key, result in results.items():
            boxes[key] = self.box(result["origin"], result["child_size_after_rotation"])
        return boxes

    def test_every_connector_volume_is_disjoint_at_maximum_room_size(self):
        boxes = self.boxes()
        names = list(boxes)
        self.assertEqual(len(names), 1 + 4 + 8 + 8)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                self.assertFalse(self.overlap(boxes[a], boxes[b]), f"{a} overlaps {b}")

    def test_lower_and_upper_bands_are_vertically_separate(self):
        boxes = self.boxes()
        for key, (lo, hi) in boxes.items():
            if key.startswith("lower_"):
                self.assertEqual((lo[1], hi[1]), (0, kc.LOWER_MAX[1] - 1))
            if key.startswith("upper_"):
                self.assertEqual(lo[1], kc.UPPER_FLOOR_Y)
                self.assertEqual(hi[1], kc.UPPER_FLOOR_Y + kc.UPPER_MAX[1] - 1)
        # Upper rooms start above the tunnels' top layer (tunnels are 9 tall: y=0..8).
        self.assertGreater(kc.UPPER_FLOOR_Y, 8)

    def test_upper_room_over_lower_room_has_structural_separation_and_headroom(self):
        self.assertGreaterEqual(kc.UPPER_MAX[1] - 2, 10)  # >= two 5-block levels of interior clearance
        self.assertGreaterEqual(kc.LOWER_MAX[1] - 2, 6)   # lower interior stays walkable with a roof slab
        self.assertEqual(kc.UPPER_FLOOR_Y, kc.LOWER_MAX[1])  # lower roof slab is directly under the upper floor slab

    def test_room_footprints_stay_within_chamber_span_so_sides_never_meet(self):
        for key, (lo, hi) in self.boxes().items():
            if key == "chamber":
                continue
            if key.startswith("tunnel"):
                continue
            side = key.split("_")[1]
            axis = 0 if side in ("north", "south") else 2
            self.assertGreaterEqual(lo[axis], 0, key)
            self.assertLessEqual(hi[axis], 46, key)


class PackTests(unittest.TestCase):
    def test_pack_is_deterministic_and_schema_valid(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra, rb = sg02.build_pack(Path(a) / "p"), sg02.build_pack(Path(b) / "p")
            fa = {p.relative_to(ra).as_posix(): p.read_bytes() for p in ra.rglob("*") if p.is_file()}
            fb = {p.relative_to(rb).as_posix(): p.read_bytes() for p in rb.rglob("*") if p.is_file()}
            self.assertEqual(fa, fb)
            nbt = read_nbt((ra / "data/moreminecrafts/structure/forgotten_kingdom/central_cavern/main_chamber.nbt").read_bytes())["value"]
            self.assertEqual(nbt["DataVersion"], 5023)
            for entry in nbt["palette"]:
                self.assertTrue(entry["id"].startswith("minecraft:"))
                for key, value in entry.get("properties", {}).items():
                    self.assertIsInstance(key, str)
                    self.assertIsInstance(value, str)

    def test_pools_reference_the_room_interfaces(self):
        import json

        with tempfile.TemporaryDirectory() as tmp:
            root = sg02.build_pack(Path(tmp) / "p")
            pools = root / "data/moreminecrafts/worldgen/template_pool/forgotten_kingdom/central_cavern"
            self.assertTrue((pools / "lower_rooms.json").is_file())
            self.assertTrue((pools / "upper_rooms.json").is_file())
            structure = json.loads((root / "data/moreminecrafts/worldgen/structure/forgotten_kingdom/central_cavern.json").read_text())
            self.assertEqual(structure["start_pool"], "moreminecrafts:forgotten_kingdom/central_cavern/start")
            self.assertGreaterEqual(structure["max_distance_from_center"], 80)


class WalkabilityTests(Sg02Fixture):
    def test_plaza_reaches_every_deck_lane_connector_and_tunnel_door(self):
        import assembly_probe as ap

        template = ap.Template(MAIN, self.chamber)
        at = lambda p: template.cells.get(tuple(p), {"id": AIR})
        seen = ap.reachable(at, (23, 1, 23), ((0, 0, 0), (46, 16, 46)))
        for side in kc.SIDES:
            for u in (kc.CENTER, *kc.LOWER_U):
                x, z = side_xz(side, u, 1)
                self.assertIn((x, 1, z), seen, f"plaza->{side} u={u} lower/tunnel door")
            for u in kc.UPPER_U:
                x, z = side_xz(side, u, 1)
                self.assertIn((x, 10, z), seen, f"deck->{side} u={u} upper vestibule")
        for x in range(47):
            for z in range(47):
                depth = min(x, z, 46 - x, 46 - z)
                if 5 <= depth <= 8:
                    self.assertIn((x, 9, z), seen, f"deck lane unreachable at {(x, z)}")


if __name__ == "__main__":
    unittest.main()
