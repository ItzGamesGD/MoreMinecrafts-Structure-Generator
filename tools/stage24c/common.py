"""Shared constants/helpers for Stage 24-C validation."""
from __future__ import annotations

import json
import os
from pathlib import Path

import nbtlib

ROOT = Path(__file__).resolve().parents[2]
S24B = Path(os.environ.get("STAGE24B_DIR", ROOT / "artifacts/ancient-city-restoration/stage-24b"))
OUT = ROOT / "artifacts/ancient-city-restoration/stage-24c"
MODULES = ["large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2",
           "sauna_1", "large_pillar_1", "medium_pillar_1"]
MC_DIR = Path(os.environ.get("MC_DIR", "/tmp/mc"))
JAVA = os.environ.get("MC_JAVA", str(MC_DIR / "jdk/bin/java"))
JAR = Path(os.environ.get("MC_JAR", MC_DIR / "server.jar"))
PACK_FORMAT = {"min_format": 101, "max_format": 101}


def state_str(p) -> str:
    name = str(p["Name"])
    props = {str(k): str(v) for k, v in p.get("Properties", {}).items()}
    if props:
        return name + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"
    return name


def load_nbt(path):
    f = nbtlib.load(path)
    return f.root if hasattr(f, "root") else f


def blocks_of(root) -> dict:
    pal = [state_str(p) for p in root["palette"]]
    return {tuple(int(v) for v in b["pos"]): (pal[int(b["state"])], b.get("nbt")) for b in root["blocks"]}


def write_pack(dest: Path, variants: dict, description="Stage 24-C test pack"):
    """variants: {relative structure path under data/<ns>/structure : (namespace, nbt file)}"""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "pack.mcmeta").write_text(json.dumps({"pack": {"description": description, **PACK_FORMAT}}))
    for rel, (ns, src) in variants.items():
        target = dest / "data" / ns / "structure" / (rel + ".nbt")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(src).read_bytes())
