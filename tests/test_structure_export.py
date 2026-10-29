"""Structure export MVP: .schem -> 26.3 structure template conversion, rejection paths, verifier."""

from __future__ import annotations

import dataclasses
import gzip
import io
import sys
from pathlib import Path

import nbtlib
import pytest
from nbtlib.tag import ByteArray, Compound, Int, IntArray, List, Short, String

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.structure_export import convert as C  # noqa: E402
from tools.structure_export.errors import BlockStateError, ConfigError, SchemError, UnsupportedFeature  # noqa: E402
from tools.structure_export.verify import VerificationError, read_nbt, verify  # noqa: E402

SAMPLE = ROOT / "exports/structures/ruined_watchtower.toml"


def _varints(values):
    out = []
    for v in values:
        while True:
            b, v = v & 0x7F, v >> 7
            out.append(b | 0x80 if v else b)
            if not v:
                break
    return [b - 256 if b > 127 else b for b in out]


def write_schem(path: Path, palette: list[str], cells: list[int], size=(2, 1, 1), **extra) -> Path:
    blocks = Compound(
        {
            "Palette": Compound({s: Int(i) for i, s in enumerate(palette)}),
            "Data": ByteArray(_varints(cells)),
            "BlockEntities": List[Compound](extra.pop("block_entities", [])),
        }
    )
    schematic = Compound(
        {
            "Version": Int(extra.pop("version", 3)),
            "DataVersion": Int(3953),
            "Width": Short(size[0]),
            "Height": Short(size[1]),
            "Length": Short(size[2]),
            "Offset": IntArray([0, 0, 0]),
            "Blocks": blocks,
            "Entities": List[Compound](extra.pop("entities", [])),
        }
    )
    schematic.update(extra)
    nbtlib.File(Compound({"Schematic": schematic}), gzipped=True, root_name="").save(path)
    return path


def config_for(schem: Path, tmp_path: Path, size=(2, 1, 1), air="include") -> C.Config:
    import hashlib

    return C.Config(
        path=SAMPLE,
        source=schem,
        source_sha256=hashlib.sha256(schem.read_bytes()).hexdigest(),
        source_data_version=3953,
        target="26.3",
        structure_id="moreminecrafts:test/sample",
        datapack=tmp_path / "pack",
        reports=tmp_path / "reports",
        size=size,
        offset=(0, 0, 0),
        air=air,
    )


def convert_file(tmp_path, palette, cells, size=(2, 1, 1), air="include", **extra):
    schem = write_schem(tmp_path / "in.schem", palette, cells, size, **extra)
    result = C.convert(config_for(schem, tmp_path, size, air))
    C.write(result)
    return result


# --- the committed sample -----------------------------------------------------------------------


def test_sample_is_reproducible_and_matches_committed_outputs():
    config = C.load_config(SAMPLE)
    first, second = C.convert(config), C.convert(config)
    assert first.nbt == second.nbt
    assert config.nbt_path.read_bytes() == first.nbt
    assert config.report_path.read_text() == C.report_text(first.report)


def test_sample_verifies_cell_for_cell_against_source():
    config = C.load_config(SAMPLE)
    summary = verify(config.nbt_path, config.source, C.load_reference(config.target), config.air)
    assert summary["size"] == [11, 17, 11]
    assert summary["blocks"] == summary["source_cells"] == summary["cells_compared"] == 11 * 17 * 11
    assert summary["mismatches"] == 0


def test_sample_uses_the_vanilla_26_3_template_schema():
    name, root = read_nbt(C.load_config(SAMPLE).nbt_path)
    assert name == ""
    assert set(root.value) == {"DataVersion", "size", "palette", "blocks", "entities"}
    assert root.value["DataVersion"].value == 5023
    for entry in root.value["palette"].value:
        assert set(entry.value) <= {"id", "properties"}  # 26.3 layout, not legacy Name/Properties


def test_sample_report_flags_unconnected_walls():
    report = C.convert(C.load_config(SAMPLE)).report
    assert report["defaulted_properties"]["minecraft:stone_brick_wall"] == [
        "east",
        "north",
        "south",
        "up",
        "waterlogged",
        "west",
    ]
    assert any("stone_brick_wall" in w for w in report["warnings"])


def test_reference_is_pinned_to_the_26_3_server_jar():
    ref = C.load_reference("26.3")
    assert ref["data_version"] == 5023
    assert ref["server_jar_sha1"] == "33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c"
    assert ref["blocks"]["minecraft:chest"]["block_entity"] is True
    assert ref["blocks"]["minecraft:stone"]["block_entity"] is False
    assert "minecraft:chain" not in ref["blocks"] and "minecraft:iron_chain" in ref["blocks"]


# --- conversion rules ---------------------------------------------------------------------------


def test_layout_and_state_completion(tmp_path):
    # x + z*W + y*W*L ordering with W=2, H=2, L=1: cells are (0,0,0) (1,0,0) (0,1,0) (1,1,0)
    result = convert_file(
        tmp_path,
        [
            "minecraft:stone",
            "minecraft:oak_stairs[facing=east]",
            "minecraft:oak_stairs[facing=east,half=bottom]",
            "minecraft:air",
        ],
        [0, 1, 2, 3],
        size=(2, 2, 1),
    )
    nbt = nbtlib.File.parse(io.BytesIO(gzip.decompress(result.nbt)))
    states = {tuple(int(v) for v in b["pos"]): nbt["palette"][int(b["state"])] for b in nbt["blocks"]}
    assert str(states[0, 0, 0]["id"]) == "minecraft:stone" and "properties" not in states[0, 0, 0]
    stairs = dict(states[1, 0, 0]["properties"])
    assert stairs == {"facing": "east", "half": "bottom", "shape": "straight", "waterlogged": "false"}
    assert states[1, 0, 0] == states[0, 1, 0]  # two source spellings of one state share one palette entry
    assert len(nbt["palette"]) == 3
    assert str(states[1, 1, 0]["id"]) == "minecraft:air"
    verify(result.config.nbt_path, result.config.source, C.load_reference("26.3"), "include")


def test_air_omit_leaves_cells_empty(tmp_path):
    result = convert_file(tmp_path, ["minecraft:stone", "minecraft:air"], [0, 1], air="omit")
    assert result.report["blocks"] == 1
    verify(result.config.nbt_path, result.config.source, C.load_reference("26.3"), "omit")


@pytest.mark.parametrize(
    "state, message",
    [
        ("minecraft:chain", "does not exist in Minecraft 26.3"),  # 1.21.1 name; 26.3 calls it iron_chain
        ("minecraft:oak_stairs[facing=up]", "is not valid"),
        ("minecraft:stone[color=red]", "has no property"),
    ],
)
def test_states_missing_from_the_target_version_are_rejected(tmp_path, state, message):
    with pytest.raises(BlockStateError, match=message):
        convert_file(tmp_path, ["minecraft:stone", state], [0, 1])


@pytest.mark.parametrize(
    "state, feature",
    [
        ("minecraft:chest[facing=north]", "block_entity"),
        ("minecraft:jigsaw", "jigsaw"),
        ("minecraft:structure_void", "structure_void"),
    ],
)
def test_blocks_needing_feature_handlers_are_rejected(tmp_path, state, feature):
    with pytest.raises(UnsupportedFeature) as error:
        convert_file(tmp_path, ["minecraft:stone", state], [0, 1])
    assert error.value.feature == feature


@pytest.mark.parametrize(
    "extra, feature",
    [
        ({"block_entities": [Compound({"Id": String("minecraft:chest")})]}, "block_entities"),
        ({"entities": [Compound({"Id": String("minecraft:pig")})]}, "entities"),
        ({"Biomes": Compound({})}, "biomes"),
        ({"version": 2}, "sponge_version"),
    ],
)
def test_schematic_features_are_rejected_not_dropped(tmp_path, extra, feature):
    with pytest.raises(UnsupportedFeature) as error:
        convert_file(tmp_path, ["minecraft:stone"], [0, 0], **extra)
    assert error.value.feature == feature


def test_truncated_block_data_is_rejected(tmp_path):
    with pytest.raises(SchemError, match="holds 1 blocks"):
        convert_file(tmp_path, ["minecraft:stone"], [0], size=(2, 1, 1))


def test_source_pins_are_enforced(tmp_path):
    schem = write_schem(tmp_path / "in.schem", ["minecraft:stone"], [0, 0])
    good = config_for(schem, tmp_path)
    for change, message in (
        ({"source_sha256": "0" * 64}, "sha256"),
        ({"size": (1, 1, 2)}, "size"),
        ({"offset": (1, 0, 0)}, "offset"),
        ({"source_data_version": 5023}, "DataVersion"),
    ):
        with pytest.raises(ConfigError, match=message):
            C.convert(dataclasses.replace(good, **change))


def test_config_rejects_multi_piece_unknown_keys_and_escaping_paths(tmp_path):
    base = SAMPLE.read_text()
    for text, error in (
        (base + "\n[[pieces]]\nid = 'x'\n", UnsupportedFeature),
        (base + "\nextra = 1\n", ConfigError),
        (base.replace('datapack = "exports/datapack"', 'datapack = "../outside"'), ConfigError),
    ):
        path = ROOT / "exports/structures/_tmp_test_config.toml"
        path.write_text(text)
        try:
            with pytest.raises(error):
                C.load_config(path)
        finally:
            path.unlink()


def test_verifier_detects_a_tampered_template(tmp_path):
    result = convert_file(tmp_path, ["minecraft:stone", "minecraft:dirt"], [0, 1])
    nbt = nbtlib.File.parse(io.BytesIO(gzip.decompress(result.nbt)))
    nbt["palette"][0]["id"] = String("minecraft:cobblestone")
    raw = io.BytesIO()
    nbt.write(raw)
    result.config.nbt_path.write_bytes(gzip.compress(raw.getvalue(), mtime=0))
    with pytest.raises(VerificationError, match="cells differ"):
        verify(result.config.nbt_path, result.config.source, C.load_reference("26.3"), "include")
