"""Stage 24-F Phases 1-2: resolve the immutable baseline and assemble the owner-selected final candidate set.

Every input is read from git objects at pinned commits (never from the working tree), verified against the reviewed
manifests, and copied byte-for-byte into artifacts/ancient-city-restoration/stage-24f/final-candidates/.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import nbtlib

ROOT = Path(__file__).resolve().parents[2]
STAGE24C_HEAD = "b92a4be1e9e1b901a08f1629c4f19b63dab43dce"
STAGE24E_HEAD = "5a3a57186762a2e0fcb1489b60531e328c2457b2"
MODULES = ["large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2", "sauna_1", "large_pillar_1", "medium_pillar_1"]
# owner selection (Stage 24-F instruction): module -> (source, option, required dimensions)
SELECTION = {
    "large_ruin_1": ("stage-24e", "C", [17, 14, 17]),
    "medium_ruin_1": ("stage-24c", None, [8, 5, 13]),
    "medium_ruin_2": ("stage-24e", "A", [16, 8, 11]),
    "small_ruin_1": ("stage-24c", None, [7, 5, 8]),
    "small_ruin_2": ("stage-24c", None, [8, 5, 4]),
    "sauna_1": ("stage-24c", None, None),
    "large_pillar_1": ("stage-24c", None, None),
    "medium_pillar_1": ("stage-24c", None, None),
}
C_PATH = "artifacts/ancient-city-restoration/stage-24b/{m}/restored.nbt"
E_PATH = "artifacts/ancient-city-restoration/stage-24e/proposals/{m}/{o}/candidate.nbt"
OUT = ROOT / "artifacts/ancient-city-restoration/stage-24f"
FINAL = OUT / "final-candidates"


def git_show(ref, path) -> bytes:
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def size_of(b: bytes):
    f = nbtlib.File.parse(io.BytesIO(__import__("gzip").decompress(b)))
    return [int(v) for v in f["size"]]


class Stop(Exception):
    pass


def main():
    reviewed_md = git_show(STAGE24E_HEAD, "artifacts/ancient-city-restoration/stage-24e/PROPOSALS.md").decode()
    reviewed = json.loads(re.search(r"Proposal SHA-256: (\{.*?\n\})", reviewed_md, re.S).group(1))
    static = json.loads(git_show(STAGE24E_HEAD, "artifacts/ancient-city-restoration/stage-24e/static-checks.json"))
    live = json.loads(git_show(STAGE24E_HEAD, "artifacts/ancient-city-restoration/stage-24e/live-summary.json"))
    manifest = {"stage": "24-F", "stage_24c_head": STAGE24C_HEAD, "stage_24e_head": STAGE24E_HEAD,
                "selection_authority": "Owner selection in the Stage 24-F instruction; large_ruin_1 +9 height explicitly authorised; no other expansion",
                "baseline_stage24c_sha256": {}, "modules": {}}
    for m in MODULES:
        cbytes = git_show(STAGE24C_HEAD, C_PATH.format(m=m))
        manifest["baseline_stage24c_sha256"][m] = sha256(cbytes)
        src, opt, dims = SELECTION[m]
        if src == "stage-24e":
            rel = E_PATH.format(m=m, o=opt)
            data = git_show(STAGE24E_HEAD, rel)
            key = f"proposals/{m}/{opt}/candidate.nbt"
            if key not in reviewed:
                raise Stop(f"{m} option {opt} missing from the reviewed manifest")
            if reviewed[key] != sha256(data):
                raise Stop(f"{m} option {opt} differs from the reviewed version: {sha256(data)} != {reviewed[key]}")
            st = static[m][opt]
            if not st["static_pass"] or st["dimensions"] != dims:
                raise Stop(f"{m} option {opt}: reviewed static result/dimensions differ ({st['dimensions']} vs {dims})")
            origin = {"source": "Stage 24-E proposal", "commit": STAGE24E_HEAD, "path": rel, "option": opt,
                      "reviewed_sha256": reviewed[key], "reviewed_title": st["title"], "reviewed_live": live[m][opt]}
        else:
            data, rel = cbytes, C_PATH.format(m=m)
            origin = {"source": "Stage 24-C validated baseline", "commit": STAGE24C_HEAD, "path": rel}
        got_dims = size_of(data)
        if dims and got_dims != dims:
            raise Stop(f"{m}: dimensions {got_dims} != required {dims}")
        base_dims = size_of(cbytes)
        if m != "large_ruin_1" and got_dims != base_dims:
            raise Stop(f"{m}: unauthorised dimension change {base_dims} -> {got_dims}")
        dst = FINAL / m / "restored.nbt"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        manifest["modules"][m] = {**origin, "final_path": str(dst.relative_to(ROOT)), "final_sha256": sha256(data),
                                  "byte_identical_to_stage24c": data == cbytes, "dimensions": got_dims, "stage24c_dimensions": base_dims,
                                  "height_change": got_dims[1] - base_dims[1]}
        print(m, origin["source"], opt or "-", got_dims, sha256(data)[:16], "identical-to-24C" if data == cbytes else "SELECTED-CHANGE")
    (OUT / "FINAL-CANDIDATES-MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (FINAL / "SHA256SUMS").write_text("".join(f"{v['final_sha256']}  {m}/restored.nbt\n" for m, v in manifest["modules"].items()))


if __name__ == "__main__":
    try:
        main()
    except Stop as e:
        print("STOP:", e)
        sys.exit(3)
