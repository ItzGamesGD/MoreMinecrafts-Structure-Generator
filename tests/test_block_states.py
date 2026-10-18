"""Every exported palette entry must be a real Minecraft 26.3 block state.

``validation/minecraft-visual/block-states-26.3.json`` is compacted from the 26.3 server's own
data-generator report (``--reports``), so unlike the vendored mcbuild registry it knows 26.3 renames
(e.g. ``minecraft:chain`` is ``minecraft:iron_chain``). A template that names a block the game does not
know is placed as air, which is how a hanging lantern silently disappears.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))
sys.path.insert(0, str(ROOT / "examples/forgotten_kingdom"))

import build_sg02 as sg02
from kingdom_common import ID_RENAMES_26_3

BLOCKS = json.loads((ROOT / "validation/minecraft-visual/block-states-26.3.json").read_text())


def all_templates():
    templates = dict(sg02.build_templates())
    try:
        import build_sg03
    except ImportError:  # SG-02 branch has no room modules
        return templates
    templates.update(build_sg03.build_templates())
    return templates


class PaletteSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = all_templates()

    def test_every_block_id_exists_in_26_3(self):
        unknown = {
            (name.rsplit("/", 1)[-1], entry["id"])
            for name, template in self.templates.items()
            for entry in template["palette"]
            if entry["id"] not in BLOCKS
        }
        self.assertEqual(unknown, set())

    def test_every_state_is_complete_and_uses_legal_values(self):
        problems = []
        for name, template in self.templates.items():
            for entry in template["palette"]:
                spec = BLOCKS[entry["id"]].get("properties", {})
                props = entry.get("properties", {})
                for key, value in props.items():
                    if key not in spec or value not in spec[key]:
                        problems.append((name.rsplit("/", 1)[-1], entry["id"], key, value))
                for key in set(spec) - set(props):
                    problems.append((name.rsplit("/", 1)[-1], entry["id"], "missing", key))
        self.assertEqual(problems, [])

    def test_renames_are_applied_and_the_legacy_ids_do_not_survive(self):
        for old, new in ID_RENAMES_26_3.items():
            self.assertNotIn(old, BLOCKS)
            self.assertIn(new, BLOCKS)
            for template in self.templates.values():
                self.assertNotIn(old, {entry["id"] for entry in template["palette"]})

    def test_block_entities_belong_to_their_blocks(self):
        expected = {
            "minecraft:chest": "minecraft:chest", "minecraft:barrel": "minecraft:barrel",
            "minecraft:trial_spawner": "minecraft:trial_spawner", "minecraft:lectern": "minecraft:lectern",
            "minecraft:campfire": "minecraft:campfire", "minecraft:decorated_pot": "minecraft:decorated_pot",
            "minecraft:jigsaw": "minecraft:jigsaw",
        }
        for name, template in self.templates.items():
            for block in template["blocks"]:
                nbt = block.get("nbt")
                if nbt is None:
                    continue
                block_id = template["palette"][block["state"]]["id"]
                self.assertEqual(nbt["id"], expected[block_id], f"{name} {block['pos']} {block_id}")


if __name__ == "__main__":
    unittest.main()
