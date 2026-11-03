"""ST-03 B3-04: build the House A *body* module `st03_house_a.nbt` (M-house_a, 9 x 10 x 7, air=include).

The cell map is the B3-01 authored design (`experiments/st03-b3-house-a/build.py::design`), unchanged. Only the
module id, file name, size and air mode are taken from the committed 25-module / 34-placement table
(`tools/seam01/data/st03_placements.json`), so this file cannot drift from the contract. The porch is NOT part of
this module (see README.md).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

from tools.seam01 import assembly as A
from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent
B3 = ROOT.parent / "st03-b3-house-a" / "build.py"


def design() -> dict:
    spec = importlib.util.spec_from_file_location("st03_b3_house_a_build", B3)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.design()


def main() -> None:
    module = A.modules()["M-house_a"]
    assert (
        module["size"] == [9, 10, 7]
        and module["air"] == "include"
        and module["file"] == "st03_house_a"
    ), module
    cells = design()
    with tempfile.TemporaryDirectory() as d:
        result = export_module(module, cells, Path(d) / "pack")
        shutil.copyfile(result.config.nbt_path, ROOT / "st03_house_a.nbt")
        shutil.copyfile(result.config.source, ROOT / "st03_house_a.schem")
        (ROOT / "export-report.json").write_text(
            json.dumps(result.report, indent=2, sort_keys=True) + "\n"
        )
    print(
        f"st03_house_a.nbt: {len(cells)} non-air authored cells, size {module['size']}, air={module['air']}"
    )


if __name__ == "__main__":
    main()
