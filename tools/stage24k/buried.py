"""Scripted player in BURIED placements of the Stage 24-K production pool entries (8 modules x 4 rotations).

The unchanged Stage 24-I buried-gameplay harness (deepslate fill, `/place jigsaw` with the real processors, bot walks in
from outside), run on the Stage 24-K templates. The six unchanged modules use their Stage 24-C scenarios; the two towers
use the Stage 24-J tower scenario (climb to the deck, visit every observation cell, walk every deck edge). For
medium_pillar_1 the top fill layer is left open: the headroom cell above deck cell (4,2) is not stored in the template
(it was not in the approved Stage 24-F tower either); the 24-seed sweep checks that cell is air in every generated tower."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24k import rebase  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(rebase.K / "live/gameplay-buried"))
    ap.add_argument("--max", type=int, default=20)
    ap.add_argument("--modules", nargs="*")
    a = ap.parse_args()
    rebase.activate()
    from tools.stage24h import gameplay_buried as GB
    from tools.stage24j import designs as D, live as J
    from tools.stage24k.live_towers import towers_scenario
    tower = towers_scenario(J.scenario)
    original = GB.scenario
    GB.scenario = lambda module, o, g: tower(D.large_a() if module == "large_pillar_1" else D.medium_a()) \
        if module in ("large_pillar_1", "medium_pillar_1") else original(module, o, g)
    GB.main(Path(a.out), a.max, a.modules, "summary-buried.json", "i24", open_top={"medium_pillar_1": 1})
