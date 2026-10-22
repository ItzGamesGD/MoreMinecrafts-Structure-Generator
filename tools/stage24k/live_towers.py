"""Real 26.1.2 server test of the two production watchtowers (Stage 24-J Option A) on a flat world.

1. Exact placement (`/place template`) in all four rotations: every template cell read back and compared (0 mismatches).
2. Scripted player (mineflayer, NOT client gameplay): outside -> ladder base -> climb -> step onto the deck -> walk to
   EVERY standable observation cell of the deck -> walk outward from the cell just inside every deck edge on every row
   and column (any drop is a failure)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24k import rebase  # noqa: E402

TOWERS = ("large_pillar_1", "medium_pillar_1")


def towers_scenario(base_scenario):
    def scenario(v):
        steps = base_scenario(v)
        dy = v.meta["deck_y"]
        visits = [{"name": f"observe_cell_{x}_{z}", "type": "goto", "target": [x, dy, z], "range": 0, "timeout": 20}
                  for x, z in sorted(v.meta["deck"])]
        i = next(i for i, s in enumerate(steps) if s["name"] == "step_onto_deck") + 1
        return steps[:i] + visits + steps[i:]
    return scenario


def main(out_dir: Path, bot=True):
    rebase.activate()
    from tools.stage24j import designs as D, live as J
    final = rebase.K / "final-candidates"
    J.candidates = lambda: ((v, final / v.module / "restored.nbt") for v in (D.large_a(), D.medium_a()))
    J.scenario = towers_scenario(J.scenario)
    J.main(out_dir, bot=bot)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(rebase.K / "live/towers"))
    ap.add_argument("--no-bot", action="store_true")
    a = ap.parse_args()
    main(Path(a.out), not a.no_bot)
