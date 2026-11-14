"""Export the (synthetic) module sources with the real converter: the per-module states `place template` would write."""

# ruff: noqa: E501
from __future__ import annotations

import hashlib
from pathlib import Path

from tools.structure_export import convert as C
from tools.structure_export.live import _template_cells
from tools.structure_export.stair_live import SAMPLE, box_size, write_schem

from . import assembly as A
from . import synthetic


def state_text(bid: str, props: dict[str, str]) -> str:
    return bid + ("[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]" if props else "")


def export_module(module: dict, source: dict, pack: Path) -> C.Result:
    size = tuple(module["size"])
    assert tuple(box_size(source)) <= size, module["id"]
    states = {pos: state_text(b, pr) for pos, (b, pr) in source.items()}
    schem = write_schem(pack.parent / f"{module['file']}.schem", states, size)
    config = C.Config(
        path=SAMPLE,
        source=schem,
        source_sha256=hashlib.sha256(schem.read_bytes()).hexdigest(),
        source_data_version=3953,
        target="26.3",
        structure_id=f"moreminecrafts:seam01/{module['file']}",
        datapack=pack,
        reports=pack.parent / "reports",
        size=size,
        offset=(0, 0, 0),
        air=module["air"],
    )
    result = C.convert(config)
    C.write(result)
    return result


def export_all(pack: Path, sources: dict | None = None):
    """Returns ({module id: exported template cells}, {module id: convert Result})."""
    sources = sources or synthetic.sources()
    pack.mkdir(parents=True, exist_ok=True)
    results, templates = {}, {}
    for module in A.plan()["modules"]:
        results[module["id"]] = export_module(module, sources[module["id"]], pack)
        templates[module["id"]] = {
            pos: (bid, dict(props))
            for pos, (bid, props) in _template_cells(results[module["id"]].config.nbt_path).items()
        }
    return templates, results
