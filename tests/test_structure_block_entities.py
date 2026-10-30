"""Block entities in exported templates: the allow-list, what the converter writes, what the verifier accepts,
and what is refused. The live game check (live.py, `block_entity_failures`) is the oracle for the 26.3 behaviour."""

from __future__ import annotations

import gzip
import io
import json
import sys
from pathlib import Path

import nbtlib
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_structure_export import convert_file  # noqa: E402

from tools.structure_export import block_entities as BE  # noqa: E402
from tools.structure_export import convert as C  # noqa: E402
from tools.structure_export import live  # noqa: E402
from tools.structure_export.errors import UnsupportedFeature  # noqa: E402
from tools.structure_export.verify import VerificationError, verify  # noqa: E402

REF = ROOT / "tools/structure_export/reference/block_entities-26.3.json"
STONE = "minecraft:stone"


def _allow():
    return json.loads(REF.read_text())


def _template(result) -> dict:
    nbt = nbtlib.File.parse(io.BytesIO(gzip.decompress(result.nbt)))
    pal = [(str(e["id"]), {k: str(v) for k, v in e.get("properties", {}).items()}) for e in nbt["palette"]]
    out = {}
    for b in nbt["blocks"]:
        pos = tuple(int(v) for v in b["pos"])
        out[pos] = (pal[int(b["state"])], b.get("nbt"))
    return out


def _verify(result, air="include"):
    return verify(
        result.config.nbt_path,
        result.config.source,
        C.load_reference("26.3"),
        air,
        C.load_connectivity("26.3"),
        BE.load("26.3"),
    )


# ---- the allow-list itself ------------------------------------------------------------------------------------


def test_allow_list_is_the_builder_policy_and_every_key_is_vanilla_evidence():
    data = _allow()
    assert data["server_jar_sha1"] == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c"
    assert data["game_jar_sha1"] == "cc3964451a3b32a0488110d5e3e6ad8d75fe6a66" and data["templates_scanned"] == 1511
    for block, spec in data["allow"].items():
        evidence = data["evidence"][spec["family"]]["keys"]
        assert set(spec["nbt"]) <= set(evidence), block
        assert spec["nbt"]["id"] == spec["be"]
        assert not {"x", "y", "z", "Items", "LootTable", "components"} & set(spec["nbt"]), block


def test_allow_list_blocks_are_block_entities_in_26_3():
    ref = json.loads((ROOT / "tools/structure_export/reference/minecraft-26.3.json").read_text())["blocks"]
    for block in _allow()["allow"]:
        assert ref[block]["block_entity"] is True, block


def test_standing_banners_and_other_block_entities_are_not_allowed():
    assert "minecraft:white_banner" not in _allow()["allow"]
    assert "minecraft:spawner" not in _allow()["allow"]
    assert "minecraft:trapped_chest" not in _allow()["allow"]


# ---- conversion ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state, be",
    [
        ("minecraft:chest[facing=north,type=single,waterlogged=false]", "minecraft:chest"),
        ("minecraft:barrel[facing=up,open=false]", "minecraft:barrel"),
        ("minecraft:furnace[facing=south,lit=false]", "minecraft:furnace"),
        ("minecraft:blast_furnace[facing=east,lit=false]", "minecraft:blast_furnace"),
        ("minecraft:white_wall_banner[facing=west]", "minecraft:banner"),
    ],
)
def test_allowed_block_entity_gets_exactly_the_policy_nbt(tmp_path, state, be):
    result = convert_file(tmp_path, [STONE, state], [1, 1], size=(2, 1, 1))
    (block, nbt) = _template(result)[(0, 0, 0)]
    assert block[0] == state.split("[")[0]
    assert nbt is not None and str(nbt["id"]) == be
    assert set(nbt) == ({"id", "patterns"} if be == "minecraft:banner" else {"id"})
    assert "x" not in nbt and "Items" not in nbt and "LootTable" not in nbt
    _verify(result)


def test_banner_carries_the_ominous_pattern_list(tmp_path):
    result = convert_file(tmp_path, [STONE, "minecraft:white_wall_banner[facing=north]"], [1, 1], size=(2, 1, 1))
    nbt = _template(result)[(0, 0, 0)][1]
    patterns = [(str(p["pattern"]), str(p["color"])) for p in nbt["patterns"]]
    assert (
        len(patterns) == 8
        and patterns[0] == ("minecraft:rhombus", "cyan")
        and patterns[-1] == ("minecraft:border", "black")
    )


def test_block_entity_nbt_does_not_depend_on_the_template_rotation(tmp_path):
    # the states rotate with the structure (the game does that); the NBT has no orientation, so it is identical
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = convert_file(tmp_path / "a", [STONE, "minecraft:chest[facing=north]"], [1, 1], size=(2, 1, 1))
    b = convert_file(tmp_path / "b", [STONE, "minecraft:chest[facing=east]"], [1, 1], size=(2, 1, 1))
    assert _template(a)[(0, 0, 0)][1] == _template(b)[(0, 0, 0)][1]
    assert _template(a)[(0, 0, 0)][0] != _template(b)[(0, 0, 0)][0]  # but the state carries the facing


def test_block_entities_are_written_without_contents_or_positions(tmp_path):
    result = convert_file(tmp_path, [STONE, "minecraft:barrel[facing=up,open=false]"], [1, 1], size=(2, 1, 1))
    assert set(_template(result)[(0, 0, 0)][1]) == {"id"}


def test_block_entity_cells_are_listed_in_the_result(tmp_path):
    result = convert_file(tmp_path, [STONE, "minecraft:chest[facing=north]"], [0, 1], size=(2, 1, 1))
    assert list(result.block_entities) == [(1, 0, 0)]


# ---- refusals (rejected with UnsupportedFeature, never dropped) -------------------------------------------------


@pytest.mark.parametrize(
    "state, reason",
    [
        ("minecraft:chest[facing=north,type=left]", "type"),
        ("minecraft:chest[facing=north,type=right]", "type"),
        ("minecraft:furnace[facing=north,lit=true]", "lit"),
        ("minecraft:blast_furnace[facing=north,lit=true]", "lit"),
        ("minecraft:barrel[facing=up,open=true]", "open"),
        ("minecraft:white_banner[rotation=4]", "allow-list"),
        ("minecraft:trapped_chest[facing=north]", "allow-list"),
        ("minecraft:spawner", "allow-list"),
        ("minecraft:oak_sign[rotation=0]", "allow-list"),
    ],
)
def test_block_entities_outside_the_allow_list_or_states_are_refused(tmp_path, state, reason):
    with pytest.raises(UnsupportedFeature) as error:
        convert_file(tmp_path, [STONE, state], [0, 1])
    assert error.value.feature == "block_entity" and reason in str(error.value)


def test_source_block_entity_data_is_still_rejected_not_copied(tmp_path):
    # the source's own BlockEntities (with Items) must never reach the template
    chest = nbtlib.Compound({"Id": nbtlib.String("minecraft:chest"), "Items": nbtlib.List[nbtlib.Compound]([])})
    with pytest.raises(UnsupportedFeature) as error:
        convert_file(tmp_path, [STONE], [0], block_entities=[chest])
    assert error.value.feature == "block_entities"


# ---- verifier -------------------------------------------------------------------------------------------------


def _edit(result, mutate):
    """Rewrite the template NBT with `mutate(nbtlib.File)` and write it back."""
    nbt = nbtlib.File.parse(io.BytesIO(gzip.decompress(result.nbt)))
    mutate(nbt)
    raw = io.BytesIO()
    nbt.write(raw)
    result.config.nbt_path.write_bytes(gzip.compress(raw.getvalue(), mtime=0))


def _block_at(nbt, pos):
    return [b for b in nbt["blocks"] if tuple(int(v) for v in b["pos"]) == pos][0]


def _palette_entry(nbt, block_id):
    return [e for e in nbt["palette"] if str(e["id"]) == block_id][0]


@pytest.fixture
def chest_layout(tmp_path):
    return convert_file(tmp_path, [STONE, "minecraft:chest[facing=north]"], [1, 1], size=(2, 1, 1))


def test_verifier_accepts_the_policy_block_entity(chest_layout):
    assert _verify(chest_layout)["blocks"] == 2


def test_verifier_rejects_missing_block_entity_data(chest_layout):
    _edit(chest_layout, lambda n: _block_at(n, (1, 0, 0)).pop("nbt"))
    with pytest.raises(VerificationError, match="block-entity data None"):
        _verify(chest_layout)


def test_verifier_rejects_contents_or_position_in_the_template(chest_layout):
    _edit(
        chest_layout,
        lambda n: _block_at(n, (0, 0, 0)).update(
            {"nbt": nbtlib.Compound({"id": nbtlib.String("minecraft:chest"), "x": nbtlib.Int(0)})}
        ),
    )
    with pytest.raises(VerificationError, match="block-entity data"):
        _verify(chest_layout)


def test_verifier_rejects_loot_stored_in_the_template(chest_layout):
    def add_loot(n):
        _block_at(n, (0, 0, 0))["nbt"]["LootTable"] = nbtlib.String("minecraft:chests/simple_dungeon")

    _edit(chest_layout, add_loot)
    with pytest.raises(VerificationError, match="block-entity data"):
        _verify(chest_layout)


def test_verifier_rejects_block_entity_data_on_a_plain_block(tmp_path):
    result = convert_file(tmp_path, [STONE, "minecraft:chest[facing=north]"], [0, 1], size=(2, 1, 1))

    def add_nbt(n):  # the stone cell gets a chest's NBT
        _block_at(n, (0, 0, 0))["nbt"] = nbtlib.Compound({"id": nbtlib.String("minecraft:chest")})

    _edit(result, add_nbt)
    with pytest.raises(VerificationError, match="block-entity data"):
        _verify(result)


def test_verifier_without_the_policy_refuses_block_entities(chest_layout):
    with pytest.raises(VerificationError, match="allow-list"):
        verify(chest_layout.config.nbt_path, chest_layout.config.source, C.load_reference("26.3"), "include")


def test_verifier_rejects_a_disallowed_state_inside_the_policy(tmp_path):
    result = convert_file(tmp_path, [STONE, "minecraft:furnace[facing=north,lit=false]"], [1, 1], size=(2, 1, 1))

    def light(n):
        _palette_entry(n, "minecraft:furnace")["properties"]["lit"] = nbtlib.String("true")

    _edit(result, light)
    with pytest.raises(VerificationError, match="allowed block-entity state"):
        _verify(result)


# ---- live-check plumbing (no server here; the oracle runs in live.py, see the PR) ----------------------------------


def test_live_snbt_matches_the_policy_syntax(tmp_path):
    result = convert_file(tmp_path, [STONE, "minecraft:white_wall_banner[facing=north]"], [1, 1], size=(2, 1, 1))
    text = live._snbt(result.block_entities[(0, 0, 0)])
    assert text.startswith('{id:"minecraft:banner",patterns:[{color:"cyan",pattern:"minecraft:rhombus"}')
