"""Decorative-decay regression of the two towers (Stage 24-I vs Stage 24-K processor replay on the 24-seed sweep).

block_rot (and every other processor) is position-seeded, so a template block that is identical in both templates at the
same world position must meet the same fate in both sweeps. Every changed loss cell must therefore be a designed cell
(template block differs, or protection role changed). The six unchanged modules must not differ at all."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES, load_nbt, blocks_of  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "artifacts/ancient-city-restoration"
K = AR / "stage-24k"
TOWERS = ("large_pillar_1", "medium_pillar_1")


def tmpl(d, m):
    return {p: s for p, (s, _) in blocks_of(load_nbt(d / m / "restored.nbt")).items()}


def losses(f):
    out = []
    for x in json.loads(f.read_text()):
        for l in x["losses"]:
            out.append((x["seed"], l["piece_index"], l["module"], tuple(l["template_pos"]), l["cause"]))
    return out


def main():
    old, new = {m: tmpl(AR / "stage-24f/final-candidates", m) for m in TOWERS}, {m: tmpl(K / "final-candidates", m) for m in TOWERS}
    design = {m: {p for p in set(old[m]) | set(new[m]) if old[m].get(p) != new[m].get(p)} for m in TOWERS}
    inv_o = json.loads((AR / "stage-24g/protection/protected-cells.json").read_text())
    inv_n = json.loads((K / "derived-24g/protection/protected-cells.json").read_text())
    prot = {m: {tuple(e["pos"]) for e in inv_o[m]["protected"]} ^ {tuple(e["pos"]) for e in inv_n[m]["protected"]} for m in TOWERS}
    Li, Lk = losses(AR / "stage-24i/worldgen/i24-processor-replay.json"), losses(K / "worldgen/k24-processor-replay.json")
    res = {}
    for m in MODULES:
        for cause in ("block_rot", "unexplained_by_processors"):
            si = {(s, i, p) for s, i, mm, p, c in Li if mm == m and c == cause}
            sk = {(s, i, p) for s, i, mm, p, c in Lk if mm == m and c == cause}
            diff = si ^ sk
            chg = design.get(m, set()) | prot.get(m, set())
            at_design = [x for x in diff if x[2] in chg]
            res[f"{m}/{cause}"] = {"stage24i": len(si), "stage24k": len(sk), "cells_that_differ": len(diff),
                                   "at_designed_or_newly_protected_cells": len(at_design),
                                   "at_unchanged_cells": sorted(list(x) for x in diff if x not in at_design)[:40]}
    (K / "worldgen/decay-regression.json").write_text(json.dumps(res, indent=1) + "\n")
    tot_i, tot_k = Counter(), Counter()
    for k, v in res.items():
        m, c = k.split("/")
        tot_i[c] += v["stage24i"]
        tot_k[c] += v["stage24k"]
    for k, v in res.items():
        print(k, v["stage24i"], "->", v["stage24k"], "differ", v["cells_that_differ"], "at designed/new-protected", v["at_designed_or_newly_protected_cells"], "at UNCHANGED", len(v["at_unchanged_cells"]))
    print("totals I", dict(tot_i), "K", dict(tot_k))


if __name__ == "__main__":
    main()
