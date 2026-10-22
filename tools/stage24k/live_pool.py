"""Real 26.1.2 server test of the Stage 24-K production pool entries: 8 modules x 4 rotations on buried placements.

The unchanged Stage 24-I live test (`tools/stage24i/live.py`: deepslate fill, `/place jigsaw` with the real processors,
protected-cell, clearance-mask and roof-cell checks, Stage 24-I control placements) run against the Stage 24-K templates
and derived data."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24k import rebase  # noqa: E402

if __name__ == "__main__":
    import argparse
    rebase.activate()
    from tools.stage24i import live
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(rebase.K / "live"))
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--modules", nargs="*", default=live.MODULES)
    ap.add_argument("--report-name", default="live-pool-report.json")
    a = ap.parse_args()
    live.main(Path(a.out), a.max, a.modules, a.report_name)
