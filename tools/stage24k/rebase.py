"""Point the Stage 24-G/24-H/24-I tools at the Stage 24-K sources without editing them.

Those tools read the approved templates from `stage-24f/final-candidates` and the previous stage's output from fixed
`stage-24g|h|i` paths held in module-level Path constants. `activate()` rebinds exactly those constants (equal to one of
the old canonical paths) in the modules given, so the unchanged builders, live tests and checks run on the Stage 24-K
templates and derived data. Baselines that must stay on the old stages (comparisons) simply do not call it.
"""
from __future__ import annotations

import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "artifacts/ancient-city-restoration"
K = AR / "stage-24k"
OLD_TO_NEW = {
    AR / "stage-24f/final-candidates": K / "final-candidates",
    AR / "stage-24g": K / "derived-24g",
    AR / "stage-24g/datapack": K / "derived-24g/datapack",
    AR / "stage-24h": K / "derived-24h",
    AR / "stage-24h/datapack": K / "derived-24h/datapack",
    AR / "stage-24i": K / "derived-24i",
    AR / "stage-24i/datapack": K / "derived-24i/datapack",
}
MODULES = ("tools.stage24g.build", "tools.stage24g.live_processing", "tools.stage24h.build", "tools.stage24h.mask",
           "tools.stage24h.live_clearance", "tools.stage24h.gameplay_buried", "tools.stage24i.roof", "tools.stage24i.build",
           "tools.stage24i.live", "tools.stage24i.entrances")


def activate(modules=MODULES):
    rebound = {}
    for name in modules:
        mod = importlib.import_module(name)
        for k, v in list(vars(mod).items()):
            if isinstance(v, Path) and v in OLD_TO_NEW:
                setattr(mod, k, OLD_TO_NEW[v])
                rebound.setdefault(name, []).append(k)
    return rebound
