"""Static feasibility checks of the two production watchtowers (the Stage 24-K final candidates) against the approved
Stage 24-F towers: size, jigsaws and block entities, ladder continuity, deck reachability and headroom, fall protection,
valid block states (vanilla 26.1.2 block report), changed cells and what they touch in the derived inventories."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24j import check as J, designs as D  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "artifacts/ancient-city-restoration"
K = AR / "stage-24k"


def main(reports_path):
    reports = json.loads(Path(reports_path).read_text())
    inv = json.loads((AR / "stage-24g/protection/protected-cells.json").read_text())
    masks = {m: {tuple(p) for vv in d["cleared"].values() for p in vv} for m, d in json.loads((AR / "stage-24h/mask/interior-masks.json").read_text()).items()}
    roofs = {m: {tuple(e["pos"]) for e in d["roof_cells"]} for m, d in json.loads((AR / "stage-24i/roof/roof-cells.json").read_text()).items()}
    out = {}
    for m, f in (("large_pillar_1", D.large_a), ("medium_pillar_1", D.medium_a)):
        base = J.G(AR / "stage-24f/final-candidates" / m / "restored.nbt")
        v = f()
        r = J.check(v, K / "final-candidates" / m / "restored.nbt", base, reports, inv, masks, roofs)
        cand = AR / "stage-24j/proposals" / m / "A/candidate.nbt"
        r["identical_to_stage24j_option_a"] = (K / "final-candidates" / m / "restored.nbt").read_bytes() == cand.read_bytes()
        r["static_pass"] = r["static_pass"] and r["identical_to_stage24j_option_a"]
        out[m] = r
        print(m, "PASS" if r["static_pass"] else "FAIL", r["deck"], r["fall_protection"]["sides"], "invalid", len(r["invalid_states"]), flush=True)
    (K / "static-checks.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default="/tmp/mc/reports/out/reports/blocks.json")
    main(ap.parse_args().reports)
