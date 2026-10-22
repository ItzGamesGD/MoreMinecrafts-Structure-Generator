"""Entrance EXPERIMENT evidence: does the out-of-size overlay change the layout, clear the target cells, or touch
anything else? Compares the i24x worlds (Stage 24-I + experiment element) with the i24 worlds, same seed."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import OUT  # noqa: E402
from tools.stage24c.mcserver import World  # noqa: E402
from tools.stage24c.worldgen_analyze import ROT, rot, TARGET  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D24I = ROOT / "artifacts/ancient-city-restoration/stage-24i"
EXP = D24I / "experiment-entrance"


def chunk(x, z):
    return (x >> 4, z >> 4)


def main(seeds=(24005, 24009)):
    rel = {m: [tuple(c) for c in v] for m, v in json.loads((EXP / "entrance-cells-template.json").read_text()).items()}
    survey = json.loads((D24I / "investigation/h24-entrance-survey.json").read_text())
    out = []
    for seed in seeds:
        pi = json.loads((D24I / f"worldgen/manifest-{seed}-i24.json").read_text())["cities"][0]["pieces"]
        px = json.loads((EXP / f"worldgen/manifest-{seed}-i24x.json").read_text())["cities"][0]["pieces"]
        key = lambda p: (p["pos"], p["rotation"], p["bb"], p["template"])  # noqa: E731
        wi = World(OUT / f"_work/wg-{seed}-i24/world/dimensions/minecraft/overworld")
        wx = World(OUT / f"_work/wg-{seed}-i24x/world/dimensions/minecraft/overworld")
        targets = {tuple(c) for r in survey if r["seed"] == seed for c in r["cells_to_clear"]}
        res = {"seed": seed, "layout_identical_i24_i24x": [key(a) for a in pi] == [key(b) for b in px], "placements": []}
        for idx, p in enumerate(px):
            m = TARGET.get(p["template"])
            if m not in rel:
                continue
            r, o, bb = ROT[p["rotation"]], p["pos"], p["bb"]
            box_chunks = {(cx, cz) for cx in range(bb[0] >> 4, (bb[3] >> 4) + 1) for cz in range(bb[2] >> 4, (bb[5] >> 4) + 1)}
            c = Counter()
            cells = []
            for q in rel[m]:
                t = rot(q, r)
                w = (o[0] + t[0], o[1] + t[1], o[2] + t[2])
                a, b = wi.block(*w), wx.block(*w)
                in_box_chunk = chunk(w[0], w[2]) in box_chunks
                kind = ("same" if a == b else "cleared_to_air" if (b or "").startswith("minecraft:air") else "changed_other")
                c[f"{kind}|{'in' if in_box_chunk else 'outside'}_piece_box_chunks"] += 1
                cells.append({"world": list(w), "template": list(q), "i24": a, "i24x": b, "in_piece_box_chunk": in_box_chunk,
                              "survey_target": w in targets})
            res["placements"].append({"piece_index": idx, "module": m, "rotation": p["rotation"], "bb": bb, "counts": dict(c),
                                      "is_blocked_entrance": any(x["survey_target"] for x in cells), "cells": cells})
        # every block outside the experiment cells, inside a 24-block box around each experiment placement
        diff = Counter()
        expw = {tuple(x["world"]) for pl in res["placements"] for x in pl["cells"]}
        for pl in res["placements"]:
            bb = pl["bb"]
            for x in range(bb[0] - 4, bb[3] + 5):
                for y in range(bb[1] - 1, bb[4] + 2):
                    for z in range(bb[2] - 4, bb[5] + 5):
                        if (x, y, z) in expw:
                            continue
                        a, b = wi.block(x, y, z), wx.block(x, y, z)
                        if a != b:
                            diff[(a or "?").split("[")[0] + " -> " + (b or "?").split("[")[0]] += 1
        res["other_differences_near_experiment_pieces"] = dict(diff.most_common(30))
        res["other_differences_total"] = sum(diff.values())
        out.append(res)
        print(seed, res["layout_identical_i24_i24x"], [(pl["piece_index"], pl["module"], pl["counts"], pl["is_blocked_entrance"]) for pl in res["placements"]],
              res["other_differences_total"], flush=True)
    (EXP / "experiment-check.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
