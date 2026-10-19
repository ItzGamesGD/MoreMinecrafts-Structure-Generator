"""Phase 1: reproducible input manifest (source/candidate hashes, dimensions, jigsaw + block-entity preservation, 24-C repair diff)."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24d.lib import *  # noqa
from tools.stage24b_source import MODULES as SRC, download_original, git_blob_sha1  # noqa

PR10 = "b750da2e06cb646c63283603a7fec4ee93a33db7"
PR16 = "b92a4be1e9e1b901a08f1629c4f19b63dab43dce"


def git_show(ref, path):
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout


def load_bytes(data: bytes, tmp: Path):
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    return load_nbt(tmp)


def compound_str(item):
    return str(item["nbt"]) if "nbt" in item else None


def main():
    out = {"stage": "24-D", "stage_24c_head": PR16, "implementation_pr10_head": PR10,
           "minecraft": "26.1.2", "source_repository": "InventivetalentDev/minecraft-assets",
           "head_at_generation": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
           "modules": {}}
    for m in MODULES:
        rel = f"artifacts/ancient-city-restoration/stage-24b/{m}/restored.nbt"
        final_bytes = (S24B / m / "restored.nbt").read_bytes()
        at_pr16 = git_show(PR16, rel)
        pr10_bytes = git_show(PR10, rel)
        src_bytes, src_url = download_original(m)
        BUILD.mkdir(parents=True, exist_ok=True)
        (BUILD / "originals").mkdir(exist_ok=True)
        (BUILD / "originals" / f"{m}.nbt").write_bytes(src_bytes)
        orig = load_bytes(src_bytes, BUILD / "originals" / f"{m}.nbt")
        fin = load_bytes(final_bytes, BUILD / "tmp" / f"{m}-final.nbt")
        pr10 = load_bytes(pr10_bytes, BUILD / "tmp" / f"{m}-pr10.nbt")
        ob, fb, pb = blocks_of(orig), blocks_of(fin), blocks_of(pr10)
        # jigsaw + block-entity preservation: original -> final
        def entities(root):
            pal = [state_str(p) for p in root["palette"]]
            return {tuple(int(v) for v in b["pos"]): (pal[int(b["state"])], str(b["nbt"])) for b in root["blocks"] if "nbt" in b}
        oe, fe = entities(orig), entities(fin)
        jig_o = {p: v for p, v in oe.items() if v[0].startswith("minecraft:jigsaw")}
        jig_f = {p: v for p, v in fe.items() if v[0].startswith("minecraft:jigsaw")}
        # 24-C repair manifest = PR #10 candidate -> final candidate
        changes = []
        for pos in sorted(set(pb) | set(fb)):
            a = pb.get(pos, ("minecraft:air", None))[0]
            b = fb.get(pos, ("minecraft:air", None))[0]
            if a != b:
                changes.append({"pos": list(pos), "pr10": a, "final": b})
        summary = Counter(f"{c['pr10'].split('[')[0].replace('minecraft:', '')} -> {c['final'].split('[')[0].replace('minecraft:', '')}" for c in changes)
        out["modules"][m] = {
            "title": TITLES[m],
            "source_url": src_url, "source_blob_sha1": git_blob_sha1(src_bytes), "source_blob_sha1_expected": SRC[m]["sha1"],
            "source_sha1_verified": git_blob_sha1(src_bytes) == SRC[m]["sha1"],
            "candidate_path": rel, "candidate_sha256": hashlib.sha256(final_bytes).hexdigest(),
            "candidate_git_blob_sha1": git_blob_sha1(final_bytes),
            "candidate_identical_to_stage24c_head": final_bytes == at_pr16,
            "pr10_candidate_sha256": hashlib.sha256(pr10_bytes).hexdigest(),
            "original_dimensions_xyz": [int(v) for v in orig["size"]], "final_dimensions_xyz": [int(v) for v in fin["size"]],
            "dimensions_as_expected": [int(v) for v in fin["size"]] == ([16, 8, 11] if m == "medium_ruin_2" else SRC[m]["size"]),
            "jigsaws": {"original": len(jig_o), "final": len(jig_f), "metadata_identical": jig_o == {p: jig_f.get(p) for p in jig_o} and len(jig_o) == len(jig_f)},
            "block_entities": {"original": len(oe), "final": len(fe), "all_original_entities_identical": all(fe.get(p) == v for p, v in oe.items())},
            "stage24c_repair": {"changed_cells_vs_pr10": len(changes), "by_kind": dict(summary.most_common()), "cells": changes},
        }
        print(m, out["modules"][m]["source_sha1_verified"], out["modules"][m]["candidate_identical_to_stage24c_head"],
              out["modules"][m]["jigsaws"]["metadata_identical"], out["modules"][m]["block_entities"]["all_original_entities_identical"], len(changes))
    D24.mkdir(parents=True, exist_ok=True)
    (D24 / "INPUT-MANIFEST.json").write_text(json.dumps(out, indent=1))
    assert all(v["source_sha1_verified"] and v["candidate_identical_to_stage24c_head"] and v["dimensions_as_expected"]
               and v["jigsaws"]["metadata_identical"] and v["block_entities"]["all_original_entities_identical"] for v in out["modules"].values())


if __name__ == "__main__":
    main()
