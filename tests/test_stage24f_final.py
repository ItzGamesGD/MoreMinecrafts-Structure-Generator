"""Stage 24-F: the owner-selected final candidate set is exact, immutable and keeps the Stage 24-C functional baseline."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import nbtlib
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.stage24c.common import blocks_of, load_nbt, state_str  # noqa: E402
from tools.stage24e.check import Grid, check  # noqa: E402
from tools.stage24e import designs  # noqa: E402
from tools.stage24f.assemble import (C_PATH, E_PATH, FINAL, MODULES, OUT, SELECTION, STAGE24C_HEAD,  # noqa: E402
                                     STAGE24E_HEAD, git_show)

MANIFEST = json.loads((OUT / "FINAL-CANDIDATES-MANIFEST.json").read_text())
REG = json.loads((ROOT / "tests/fixtures/stage24f_block_properties_26_1_2.json").read_text())


def blob(ref, path):
    return git_show(ref, path)


def test_manifest_and_sha256sums_match_the_files():
    sums = dict(reversed(line.split("  ")) for line in (FINAL / "SHA256SUMS").read_text().splitlines())
    assert set(MANIFEST["modules"]) == set(MODULES)
    for m in MODULES:
        data = (FINAL / m / "restored.nbt").read_bytes()
        h = hashlib.sha256(data).hexdigest()
        assert h == MANIFEST["modules"][m]["final_sha256"] == sums[f"{m}/restored.nbt"]


@pytest.mark.parametrize("module", MODULES)
def test_each_module_is_exactly_its_selected_source(module):
    src, opt, dims = SELECTION[module]
    data = (FINAL / module / "restored.nbt").read_bytes()
    base = blob(STAGE24C_HEAD, C_PATH.format(m=module))
    if src == "stage-24c":
        assert data == base
    else:
        assert data == blob(STAGE24E_HEAD, E_PATH.format(m=module, o=opt))
        assert hashlib.sha256(data).hexdigest() == MANIFEST["modules"][module]["reviewed_sha256"]
    size = [int(v) for v in load_nbt(FINAL / module / "restored.nbt")["size"]]
    base_size = [int(v) for v in nbtlib.File.parse(io.BytesIO(gzip.decompress(base)))["size"]]
    assert size == (dims or base_size)
    if module != "large_ruin_1":
        assert size == base_size, "only large_ruin_1 is authorised to grow"


@pytest.mark.parametrize("module,factory", [("large_ruin_1", designs.large_C), ("medium_ruin_2", designs.medium2_A)])
def test_selected_roof_geometry_is_reproduced_exactly(module, factory):
    v = factory()
    final = {p: s for p, (s, _) in blocks_of(load_nbt(FINAL / module / "restored.nbt")).items()}
    assert final == v.blocks
    assert [int(x) for x in load_nbt(FINAL / module / "restored.nbt")["size"]] == v.size


@pytest.mark.parametrize("module", MODULES)
def test_jigsaws_and_block_entities_identical_to_stage24c(module):
    b = {p: (s, str(n)) for p, (s, n) in blocks_of(nbtlib.File.parse(io.BytesIO(gzip.decompress(blob(STAGE24C_HEAD, C_PATH.format(m=module)))))).items() if n is not None}
    f = {p: (s, str(n)) for p, (s, n) in blocks_of(load_nbt(FINAL / module / "restored.nbt")).items() if n is not None}
    assert b == f


@pytest.mark.parametrize("module", MODULES)
def test_every_block_state_is_valid_for_26_1_2(module):
    """Every block exists in the 26.1.2 registry and every stored property/value is legal. Omitted properties are
    filled with the block default by NbtUtils.readBlockState (e.g. waterlogged=false), which the live placement confirms."""
    assert not REG["unknown"]
    for e in load_nbt(FINAL / module / "restored.nbt")["palette"]:
        name = str(e["Name"])
        allowed = REG["blocks"][name]
        props = {str(k): str(v) for k, v in e.get("Properties", {}).items()}
        assert set(props) <= set(allowed), (module, state_str(e), sorted(allowed))
        for k, v in props.items():
            assert v in allowed[k], (module, state_str(e), k, v)


@pytest.mark.parametrize("module", ["large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2"])
def test_houses_keep_the_stage24c_functional_baseline(tmp_path, module):
    base = tmp_path / "base.nbt"
    base.write_bytes(blob(STAGE24C_HEAD, C_PATH.format(m=module)))
    r = check(module, FINAL / module / "restored.nbt", Grid(base))
    assert r["static_pass"], r["failed_checks"]
    assert r["walkable_cells"] >= r["baseline_walkable_cells"]
    if module == "medium_ruin_2":
        assert r["upper_floor_stair_headroom"]
