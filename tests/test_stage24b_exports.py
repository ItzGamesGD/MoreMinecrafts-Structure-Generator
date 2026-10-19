"""Round-trip native structure NBT and Sponge schematic exports for every candidate."""
import pytest
import nbtlib

from mcbuild.export.schem import export_schem

from tools.stage24b_candidate import Candidate
from tools.stage24b_layouts import RESTORERS
from tools.stage24b_source import MODULES, load_original


def decode_varints(raw: bytes, count: int) -> list[int]:
    decoded = []
    cursor = 0
    for _ in range(count):
        value = shift = 0
        while True:
            byte = raw[cursor]
            cursor += 1
            value |= (byte & 0x7F) << shift
            if byte < 0x80:
                break
            shift += 7
        decoded.append(value)
    assert cursor == len(raw)
    return decoded


@pytest.mark.parametrize("module", list(MODULES))
def test_native_nbt_and_schematic_reload_every_module(tmp_path, module):
    root, url, sha = load_original(module)
    candidate = Candidate(module, root, url, sha)
    RESTORERS[module](candidate)
    candidate.verify_protected()

    nbt_path = tmp_path / f"{module}.nbt"
    candidate.save_native(nbt_path)
    reloaded = Candidate(module, nbtlib.load(nbt_path), url, sha)
    reloaded.verify_protected()
    assert reloaded.size == candidate.size
    assert reloaded.current_connector_snapshot() == candidate.connector_snapshot
    for pos, source_snapshot in candidate.protected_snapshot.items():
        assert reloaded.protected_snapshot[pos] == source_snapshot

    schem_path = tmp_path / f"{module}.schem"
    export_schem(candidate.to_grid(), str(schem_path))
    schematic = nbtlib.load(schem_path)["Schematic"]
    assert int(schematic["Version"]) == 3
    assert all(int(schematic[key]) > 0 for key in ("Width", "Height", "Length"))
    palette = {str(name): int(index) for name, index in schematic["Blocks"]["Palette"].items()}
    volume = int(schematic["Width"]) * int(schematic["Height"]) * int(schematic["Length"])
    raw = bytes(value & 0xFF for value in schematic["Blocks"]["Data"])
    decoded = decode_varints(raw, volume)
    assert set(decoded) <= set(palette.values())
