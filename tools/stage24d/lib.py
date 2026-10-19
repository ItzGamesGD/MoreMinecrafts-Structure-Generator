"""Shared helpers for the Stage 24-D gallery pipeline (read-only: never writes structure NBTs)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.stage24c.common import MODULES, S24B, blocks_of, load_nbt, state_str  # noqa: E402

D24 = ROOT / "artifacts/ancient-city-restoration/stage-24d"
BUILD = Path(os.environ.get("S24D_BUILD", "/tmp/s24d-build"))
ASSETS = Path(os.environ.get("MC_ASSETS", "/tmp/mc/client/x/assets"))
PYMOD = sys.executable

TITLES = {
    "large_ruin_1": "Large Ruin — Courtyard House",
    "medium_ruin_1": "Medium Ruin 1 — Single-story House",
    "medium_ruin_2": "Medium Ruin 2 — Partial Two-story House",
    "small_ruin_1": "Small Ruin 1 — Small House A",
    "small_ruin_2": "Small Ruin 2 — Small House B",
    "sauna_1": "Sauna — Public Bathhouse",
    "large_pillar_1": "Large Pillar — Large Watchtower",
    "medium_pillar_1": "Medium Pillar — Medium Watchtower",
}


def parse_state(s: str):
    name, props = (s.split("[", 1) + [""])[:2]
    kv = {}
    if props:
        for p in props.rstrip("]").split(","):
            k, v = p.split("=", 1)
            kv[k] = v
    return {"name": name if ":" in name else "minecraft:" + name, "props": kv}


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def scene_from_blocks(blocks: dict, size, jigsaw_final=True):
    """blocks: {(x,y,z): state_string or (state, nbt)} -> viewer scene JSON dict"""
    pal, idx, out = [], {}, []
    for pos, v in sorted(blocks.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
        st, nbt = (v if isinstance(v, tuple) else (v, None))
        if st.startswith("minecraft:jigsaw"):
            fs = str(nbt["final_state"]) if (nbt is not None and "final_state" in nbt) else "minecraft:air"
            st = fs if jigsaw_final else st
        if st.split("[")[0] in ("minecraft:air", "minecraft:structure_void"):
            continue
        if st not in idx:
            idx[st] = len(pal)
            pal.append(parse_state(st))
        out.append([pos[0], pos[1], pos[2], idx[st]])
    return {"size": list(size), "palette": pal, "blocks": out}


def scene_of_nbt(path: Path, rot=0):
    root = load_nbt(path)
    size = [int(v) for v in root["size"]]
    return scene_from_blocks(blocks_of(root), size), size


def write_scene(name: str, scene: dict) -> Path:
    p = BUILD / "scenes" / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(scene))
    return p


def run_jobs(jobs: list, tag: str):
    jp = BUILD / "jobs" / f"{tag}.json"
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(jobs))
    r = subprocess.run(["node", "render_jobs.mjs", str(ASSETS), str(jp)], cwd=ROOT / "tools/stage24d", capture_output=True, text=True)
    sys.stdout.write(r.stdout[-600:])
    if r.returncode:
        sys.stderr.write(r.stderr[-2000:])
    return r.returncode
