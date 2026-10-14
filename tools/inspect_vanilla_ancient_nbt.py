#!/usr/bin/env python3
"""Inspect precisely the three vanilla Ancient City source templates.

Read-only research helper. Asset bytes fetched from pinned, published 26.1.2
Minecraft assets mirror, authenticated by their recorded Git blob SHA.
No generated assets are committed to this repository.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

import nbtlib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "ancient-city-source-inspection"
MIRROR_COMMIT = "bb6d6451fb5fff54d3930fd8bf19d81200f00e6d"
EXPECTED = {
    "barracks": "97173720e5896ba892222615caf9173b7db1aaaf",
    "ice_box_1": "e5d787760a4ee53f487d1d64ed226225887c7ad7",
    "small_statue": "9cf2d16d86c9eba18db019f91666bdfc7e9de681",
}
MARKERS = (
    "chest", "barrel", "jigsaw", "trapdoor", "ladder", "stair",
    "ice", "water", "door", "candle", "soul_fire", "skull",
    "lectern", "note_block", "calibrated_sculk_sensor", "redstone",
)


def load_template(name: str):
    path = f"data/minecraft/structure/ancient_city/structures/{name}.nbt"
    url = f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/{MIRROR_COMMIT}/{path}"
    request = Request(url, headers={"User-Agent": "MoreMinecrafts-source-inspector"})
    with urlopen(request, timeout=60) as response:
        data = response.read()
    sha = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    assert sha == EXPECTED[name], (name, sha)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / f"{name}.nbt"
        target.write_bytes(data)
        nbt = nbtlib.load(target)
        return nbt.root, url, sha


def analyse(name: str):
    root, url, sha = load_template(name)
    dims = [int(v) for v in root["size"]]
    palette = []
    for e in root["palette"]:
        base = str(e["Name"])
        state = e.get("Properties")
        props = {str(k): str(v) for k,v in state.items()} if state else {}
        palette.append({"name": base, "props": props})
    by_y = defaultdict(Counter)
    positions = {}
    markers = []
    count = Counter()
    for block in root["blocks"]:
        p = tuple(int(v) for v in block["pos"])
        sid = int(block["state"])
        info = palette[sid]
        mat = info["name"].removeprefix("minecraft:")
        positions[p] = mat
        count[mat] += 1
        by_y[p[1]][mat] += 1
        if any(token in mat for token in MARKERS):
            entry={"pos":p,"block":mat}
            if info["props"]:entry["state"] = info["props"]
            if "nbt" in block:
                special=block["nbt"]
                if "name" in special:entry["nbt_name"]=str(special["name"])
                if "target" in special:entry["nbt_target"]=str(special["target"])
                if "pool" in special:entry["nbt_pool"]=str(special["pool"])
            markers.append(entry)
    # compact, exact occupancy map: per vertical level full x-z grid.
    maps = {}
    for y in range(dims[1]):
        rows=[]
        for z in range(dims[2]):
            line=""
            for x in range(dims[0]):
                v=positions.get((x,y,z),"air")
                if v == "air": ch=" "
                elif v in ("deepslate","cobbled_deepslate"):ch="#"
                elif "ice" in v:ch="I"
                elif "jigsaw" in v:ch="J"
                elif "trapdoor" in v:ch="T"
                elif "ladder" in v:ch="L"
                elif "chest" in v:ch="C"
                elif "stair" in v:ch="s"
                elif "slab" in v:ch="="
                elif "candle" in v:ch="c"
                elif "wall" in v:ch="w"
                elif "deepslate" in v:ch="D"
                elif v in ("soul_fire","soul_sand"):ch="F"
                else:ch="o"
                line+=ch
            rows.append(line)
        maps[str(y)]=rows
    report={
        "module":name,"source_url":url,"source_blob_sha":sha,
        "size_xyz":dims,"blocks_in_template":len(root["blocks"]),
        "palette_size":len(palette),"material_counts":dict(count.most_common()),
        "by_y":{str(y):{"total":sum(c.values()),"materials":dict(c.most_common(12))} for y,c in sorted(by_y.items())},
        "markers":markers, "maps":maps,
        "jigsaw": [m for m in markers if m["block"]=="jigsaw"],
        "entities_count":len(root.get("entities", [])),
    }
    return report


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name in EXPECTED:
        report=analyse(name)
        (OUT/f"{name}.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        summary={
            "module":name,
            "size_xyz":report["size_xyz"],
            "blocks":report["blocks_in_template"],
            "materials":list(report["material_counts"].items())[:22],
            "markers":report["markers"],
            "jigsaw":report["jigsaw"],
            "per_y_counts":{k:v["total"] for k,v in report["by_y"].items()},
        }
        print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
    print("Source inspection finished; originals have not been edited.",flush=True)

if __name__=="__main__":
    main()
