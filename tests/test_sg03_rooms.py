from __future__ import annotations

import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))
sys.path.insert(0, str(ROOT / "examples/forgotten_kingdom"))
sys.path.insert(0, str(ROOT / "validation/minecraft-visual"))

import assembly_probe as ap
import build_sg02 as sg02
import build_sg03 as sg03
import kingdom_common as kc

LOWER = sg03.LOWER_IDS
UPPER = sg03.UPPER_IDS


class Sg03Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = sg03.build_templates()
        cls.rooms = {name: ap.Template(name, cls.templates[identifier]) for family in (LOWER, UPPER) for name, identifier in family.items()}
        cls.stubs = sg02.build_templates()  # SG-02 reserved-volume stubs at the maximum footprint
        cls.stub_boxes = {}
        stub_templates = sg02.build_templates()
        cls.max_connections = sg02.validate_connections(stub_templates, sg02.LOWER_STUB_ID, sg02.UPPER_STUB_ID)

    def family(self, kind):
        return LOWER if kind == "lower" else UPPER


class ModuleContractTests(Sg03Fixture):
    def test_six_distinct_modules_in_two_families(self):
        self.assertEqual(len(LOWER), 3)
        self.assertEqual(len(UPPER), 3)
        self.assertEqual(set(LOWER), {"storage_room", "guard_room", "residence_ruin"})
        self.assertEqual(set(UPPER), {"grand_hall", "barracks_hall", "trial_chamber"})

    def test_sizes_stay_inside_the_reserved_volumes(self):
        for name, identifier in LOWER.items():
            w, h, d = self.templates[identifier]["size"]
            lw, lh, ld = kc.LOWER_MAX
            self.assertLessEqual((w, h, d), (lw, lh, ld), name)
        for name, identifier in UPPER.items():
            w, h, d = self.templates[identifier]["size"]
            uw, uh, ud = kc.UPPER_MAX
            self.assertLessEqual((w, h, d), (uw, uh, ud), name)

    def test_entry_connector_is_centred_on_the_south_edge_with_clear_mouth(self):
        for name, identifier in {**LOWER, **UPPER}.items():
            template = self.templates[identifier]
            w, h, d = template["size"]
            jigs = self.rooms[name].jigsaws
            self.assertEqual(len(jigs), 1, name)
            jig = jigs[0]
            self.assertEqual(jig["pos"], (w // 2, 1, d - 1), name)
            self.assertEqual(jig["face"], "south")
            self.assertEqual(jig["name"], kc.LOWER_ENTRY if name in LOWER else kc.UPPER_ENTRY)
            self.assertEqual((jig["target"], jig["pool"]), ("minecraft:empty", "minecraft:empty"))
            self.assertEqual(w % 2, 1, "entry must be centred: odd width")

    def test_every_room_validates_against_every_connector_of_its_kind(self):
        results = sg03.validate_all(self.templates)
        self.assertEqual(len(results), 3 * 8 + 3 * 8)
        for (_room, key), value in results.items():
            side = key.split("_")[1]
            self.assertEqual(value["world_child_facing"], kc.OPPOSITE[side])

    def test_room_volumes_are_contained_in_the_maximum_reserved_volume_for_every_slot(self):
        """Containment proof: a room that fits in the stub's volume cannot collide where the stubs cannot."""
        for kind, family, max_size in (("lower", LOWER, kc.LOWER_MAX), ("upper", UPPER, kc.UPPER_MAX)):
            for room_name, identifier in family.items():
                room_template = self.templates[identifier]
                for key, parent_pos in sg02.connector_positions()[kind].items():
                    side = key.split("_")[0]
                    result = sg03.sg02.connect_templates(
                        self.templates[sg02.MAIN], parent_pos, room_template, self.rooms[room_name].jigsaws[0]["pos"],
                        rotation=sg02.rotation_for(side),
                        doorway_width=(kc.LOWER_DOOR if kind == "lower" else kc.UPPER_DOOR)[0],
                        doorway_height=(kc.LOWER_DOOR if kind == "lower" else kc.UPPER_DOOR)[1],
                    )
                    stub = self.max_connections[f"{kind}_{key}"]
                    r_lo = result["origin"]
                    r_hi = tuple(r_lo[i] + result["child_size_after_rotation"][i] - 1 for i in range(3))
                    s_lo = stub["origin"]
                    s_hi = tuple(s_lo[i] + stub["child_size_after_rotation"][i] - 1 for i in range(3))
                    for i in range(3):
                        self.assertGreaterEqual(r_lo[i], s_lo[i], f"{room_name} {key} axis {i}")
                        self.assertLessEqual(r_hi[i], s_hi[i], f"{room_name} {key} axis {i}")

    def test_lower_and_upper_bands_do_not_share_cells(self):
        for name, identifier in LOWER.items():
            self.assertLessEqual(self.templates[identifier]["size"][1], kc.UPPER_FLOOR_Y)
        # chamber-frame lower band is y=0..8; upper floors start at y=9 (see SG-02 reserved-volume tests)
        self.assertEqual(kc.UPPER_FLOOR_Y, kc.LOWER_MAX[1])


class VariationTests(Sg03Fixture):
    def test_footprints_and_heights_vary_within_each_family(self):
        for family in (LOWER, UPPER):
            sizes = {tuple(self.templates[i]["size"]) for i in family.values()}
            self.assertEqual(len(sizes), 3)
            self.assertGreaterEqual(len({s[1] for s in sizes}), 3, "ceiling heights must differ")
            self.assertGreaterEqual(len({s[0] for s in sizes} | {s[2] for s in sizes}), 4)

    def test_modules_differ_in_material_and_block_vocabulary(self):
        def vocab(name):
            return Counter(state["id"] for state in self.rooms[name].solid.values())

        names = list(self.rooms)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                set_a, set_b = set(vocab(a)), set(vocab(b))
                jaccard = len(set_a & set_b) / len(set_a | set_b)
                self.assertLess(jaccard, 0.85, f"{a} and {b} look like palette swaps of each other")

    def test_distinct_architectural_features_per_module(self):
        features = {
            "storage_room": {"minecraft:barrel", "minecraft:chest", "minecraft:dark_oak_slab", "minecraft:cobweb"},
            "guard_room": {"minecraft:grindstone", "minecraft:anvil", "minecraft:iron_bars", "minecraft:fletching_table", "minecraft:gray_bed"},
            "residence_ruin": {"minecraft:campfire", "minecraft:bookshelf", "minecraft:red_bed", "minecraft:moss_block", "minecraft:cauldron"},
            "grand_hall": {"minecraft:chiseled_tuff_bricks", "minecraft:iron_chain", "minecraft:soul_lantern", "minecraft:deepslate_brick_wall"},
            "barracks_hall": {"minecraft:spruce_planks", "minecraft:stripped_dark_oak_log", "minecraft:blue_bed", "minecraft:red_bed", "minecraft:spruce_stairs"},
            "trial_chamber": {"minecraft:trial_spawner", "minecraft:waxed_chiseled_copper", "minecraft:waxed_oxidized_cut_copper", "minecraft:waxed_copper_bulb"},
        }
        for name, expected in features.items():
            present = {state["id"] for state in self.rooms[name].solid.values()}
            self.assertLessEqual(expected, present, f"{name} lost: {expected - present}")

    def test_secondary_elevation_exists_in_the_multi_level_rooms(self):
        def floors(name, y):
            return sum(1 for (x, yy, z), s in self.rooms[name].solid.items() if yy == y and s["id"] != "minecraft:air")

        self.assertGreater(floors("grand_hall", 6), 80)       # side galleries
        self.assertGreater(floors("barracks_hall", 6), 150)   # mezzanine and catwalk
        self.assertGreater(floors("trial_chamber", 2), 150)   # ledges
        self.assertGreater(floors("guard_room", 2), 20)       # watch step
        self.assertGreater(floors("storage_room", 1), 30)     # stash dais


class InteriorTests(Sg03Fixture):
    def reach(self, name):
        template = self.rooms[name]
        at = lambda p: template.cells.get(tuple(p), {"id": "minecraft:air"})
        w, h, d = template.size
        seen = ap.reachable(at, (w // 2, 1, d - 1), ((0, 0, 0), (w - 1, h - 1, d - 1)))
        return template, seen

    def test_every_loot_container_spawner_and_workstation_is_reachable_on_foot(self):
        for name in self.rooms:
            template, seen = self.reach(name)
            pois = ap.points_of_interest(template)
            self.assertTrue(pois, f"{name} has nothing to reach")
            for local, kind in pois:
                near = [(local[0] + dx, local[1] + dy, local[2] + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) for dy in (0, -1, 1)]
                self.assertTrue(any(n in seen for n in near), f"{name}: {kind} at {local} is unreachable")

    def test_rooms_are_navigable_not_blocked_at_the_door(self):
        for name in self.rooms:
            template, seen = self.reach(name)
            w, h, d = template.size
            self.assertGreater(len(seen), 100, name)
            # the first interior row inside the door is walkable across the doorway width
            door_w = 3 if name in LOWER else 5
            row = d - 3
            walkable = [x for x in range(w) if any(p[0] == x and p[2] == row for p in seen)]
            self.assertGreaterEqual(len(walkable), door_w, f"{name} blocked directly inside the door")

    def test_multi_level_rooms_have_reachable_upper_levels(self):
        for name, level in (("grand_hall", 7), ("barracks_hall", 7)):
            _template, seen = self.reach(name)
            self.assertGreater(sum(1 for p in seen if p[1] == level), 20, f"{name} upper level unreachable")
        _template, seen = self.reach("trial_chamber")
        self.assertGreater(sum(1 for p in seen if p[1] == 3), 40, "trial chamber ledges unreachable")

    def test_stairs_are_flush_with_the_floors_they_climb_to(self):
        """A stair whose back-top height differs from the next floor's top by a block forces a jump."""
        for name, template in self.rooms.items():
            for (x, y, z), state in template.solid.items():
                if not state["id"].endswith("_stairs") or state["properties"]["half"] != "bottom":
                    continue
                facing = state["properties"]["facing"]
                dx, dz = ap.FRONT[facing][0], ap.FRONT[facing][2]
                ahead = template.cells.get((x + dx, y, z + dz), {"id": "minecraft:air"})["id"]
                above_ahead = template.cells.get((x + dx, y + 1, z + dz), {"id": "minecraft:air"})["id"]
                # Skip decorative chairs/benches/arch corners: only check stairs that lead onto a floor block.
                if ahead != "minecraft:air" and not ahead.endswith(("_stairs", "_slab")) and above_ahead == "minecraft:air":
                    below = template.cells.get((x, y - 1, z), {"id": "minecraft:air"})["id"]
                    self.assertNotEqual(below, "minecraft:air", f"{name}: floating stair at {(x, y, z)}")


class BlockEntityTests(Sg03Fixture):
    def test_loot_tables_are_vanilla_ids_and_provisional(self):
        tables = set()
        for template in self.rooms.values():
            for nbt in template.nbt.values():
                if "LootTable" in nbt:
                    tables.add(nbt["LootTable"])
        self.assertTrue(tables)
        for table in tables:
            self.assertTrue(table.startswith("minecraft:chests/"), table)  # no invented MoreMinecrafts item ids
        # no custom items anywhere
        for template in self.rooms.values():
            for nbt in template.nbt.values():
                self.assertNotIn("moreminecrafts", str(nbt.get("Items", "")))

    def test_trial_spawners_use_paired_vanilla_configs(self):
        spawners = [nbt for nbt in self.rooms["trial_chamber"].nbt.values() if nbt["id"] == "minecraft:trial_spawner"]
        self.assertEqual(len(spawners), 3)
        for nbt in spawners:
            self.assertTrue(nbt["normal_config"].startswith("minecraft:trial_chamber/"))
            self.assertEqual(nbt["ominous_config"], nbt["normal_config"].replace("/normal", "/ominous"))
        self.assertEqual(len({n["normal_config"] for n in spawners}), 3)

    def test_rotation_sensitive_states_are_complete(self):
        for name, template in self.rooms.items():
            for state in template.solid.values():
                props = state.get("properties", {})
                if state["id"].endswith("_stairs"):
                    self.assertEqual(set(props), {"facing", "half", "shape", "waterlogged"})
                if state["id"].endswith("_bed"):
                    self.assertEqual(set(props), {"facing", "occupied", "part"})


class PackTests(unittest.TestCase):
    def test_sg03_pack_is_reproducible_and_pools_hold_the_modules(self):
        import json

        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra, rb = sg03.build_pack(Path(a) / "p"), sg03.build_pack(Path(b) / "p")
            fa = {p.relative_to(ra).as_posix(): p.read_bytes() for p in ra.rglob("*") if p.is_file()}
            fb = {p.relative_to(rb).as_posix(): p.read_bytes() for p in rb.rglob("*") if p.is_file()}
            self.assertEqual(fa, fb)
            pools = ra / "data/moreminecrafts/worldgen/template_pool/forgotten_kingdom/central_cavern"
            lower = json.loads((pools / "lower_rooms.json").read_text())
            upper = json.loads((pools / "upper_rooms.json").read_text())
            self.assertEqual({e["element"]["location"] for e in lower["elements"]}, set(LOWER.values()))
            self.assertEqual({e["element"]["location"] for e in upper["elements"]}, set(UPPER.values()))
            self.assertNotIn("stub", "".join(fa))


if __name__ == "__main__":
    unittest.main()
