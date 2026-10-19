#!/usr/bin/env python3
"""Read-only, hash-pinned inspection of the eight deferred Ancient City NBTs."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

import nbtlib
from mcbuild.palette import get_block
from mcbuild.render.views import build_contact_sheet
from mcbuild.voxel import VoxelGrid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "ancient-city-stage-24a"
MIRROR_COMMIT = "bb6d6451fb5fff54d3930fd8bf19d81200f00e6d"
FILES = {
    "large_ruin_1": "3ce04aa7cd68ab706ed7e7910cbf8453f090fb39",
    "medium_ruin_1": "c476ea76624d25ac483f723c55ef39695ac86aee",
    "medium_ruin_2": "0f8b01b7aff4bd43c8e5ecc18292940ca648bf03",
    "small_ruin_1": "b1b9c2ac7c4b06a1a80e53adf4dd4fd706f2a799",
    "small_ruin_2": "34d14f95c92675e6d97d212baf88e84c4f506fbd",
    "sauna_1": "ef56d35f13f3acb8d62095ccc2f7e85d58d253b1",
    "large_pillar_1": "4d619829f48909054996945d01a77d949946e678",
    "medium_pillar_1": "38ece3d8a57c9fed3f2a050ffd21b5b636121bbe",
}
VIEWS = [{"yaw": n} for n in range(4)]
STATE_GLYPHS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def plain(value):
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "items"):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return str(value)


def load(name: str):
    rel = f"data/minecraft/structure/ancient_city/structures/{name}.nbt"
    url = f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/{MIRROR_COMMIT}/{rel}"
    req = Request(url, headers={"User-Agent": "MoreMinecrafts-Stage-24A-Inspector"})
    data = urlopen(req, timeout=60).read()
    sha = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    if sha != FILES[name]:
        raise ValueError(f"{name}: source blob SHA mismatch: expected {FILES[name]}, got {sha}")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / f"{name}.nbt"
        p.write_bytes(data)
        return nbtlib.load(p), url, sha, len(data)


def inspect(name: str):
    root, url, sha, byte_count = load(name)
    size = [int(v) for v in root["size"]]
    palette = []
    for item in root["palette"]:
        palette.append({"name": str(item["Name"]), "properties": plain(item.get("Properties", {}))})
    counts = Counter()
    layers = defaultdict(Counter)
    blocks = {}
    states = {}
    jigsaws = []
    functional = []
    block_entities = []
    for item in root["blocks"]:
        pos = tuple(int(v) for v in item["pos"])
        info = palette[int(item["state"])]
        block_name = info["name"].removeprefix("minecraft:")
        counts[info["name"]] += 1
        layers[pos[1]][info["name"]] += 1
        blocks[pos] = block_name
        states[pos] = int(item["state"])
        entry = {"pos": list(pos), "block": info["name"], "properties": info["properties"]}
        if "nbt" in item:
            entry["nbt"] = plain(item["nbt"])
        if block_name == "jigsaw":
            jigsaws.append(entry)
        elif any(key in block_name for key in ("chest", "barrel", "ladder", "trapdoor", "stairs", "candle", "water", "skull", "lantern", "door", "bed", "campfire", "chain")):
            functional.append(entry)
        if "nbt" in item:
            block_entities.append(entry)

    # Full exact coordinate occupancy; symbols encode block family, while JSON keeps full identity/state.
    def symbol(block):
        if block is None:
            return " "
        if block == "jigsaw":
            return "J"
        if "water" in block:
            return "~"
        if "stair" in block:
            return "s"
        if "slab" in block:
            return "="
        if "candle" in block:
            return "c"
        if any(x in block for x in ("chest", "barrel", "skull", "lantern", "ladder", "trapdoor")):
            return block[0].upper()
        if "deepslate" in block or "basalt" in block:
            return "#"
        return "o"

    maps = {}
    state_maps = {}
    for y in range(size[1]):
        rows = ["".join(symbol(blocks.get((x, y, z))) for x in range(size[0])) for z in range(size[2])]
        maps[str(y)] = rows
        state_maps[str(y)] = [
            "".join("." if states.get((x, y, z)) is None else STATE_GLYPHS[states[(x, y, z)]] for x in range(size[0]))
            for z in range(size[2])
        ]

    grid = VoxelGrid()
    renderable = True
    try:
        for item in root["blocks"]:
            pos = tuple(int(v) for v in item["pos"])
            info = palette[int(item["state"])]
            state = info["name"].removeprefix("minecraft:")
            if info["properties"]:
                state += "[" + ",".join(f"{k}={v}" for k, v in sorted(info["properties"].items())) + "]"
            block = get_block(state)
            grid.set(*pos, block.index)
    except Exception as exc:  # Preserve source report even when preview palette lacks a newer block.
        renderable = False
        render_error = f"{type(exc).__name__}: {exc}"
    else:
        render_error = None

    report = {
        "module": name,
        "source_url": url,
        "source_repository": "InventivetalentDev/minecraft-assets",
        "source_commit": MIRROR_COMMIT,
        "source_blob_sha1": sha,
        "source_bytes": byte_count,
        "verified": True,
        "size_xyz": size,
        "block_count": len(root["blocks"]),
        "palette_size": len(palette),
        "palette": palette,
        "material_counts": dict(counts.most_common()),
        "per_y_counts": {str(y): {"total": sum(c.values()), "materials": dict(c.most_common())} for y, c in sorted(layers.items())},
        "occupancy_maps_x_by_z_per_y": maps,
        "palette_index_maps_x_by_z_per_y": state_maps,
        "palette_index_symbol_legend": {STATE_GLYPHS[i]: i for i in range(len(palette))},
        "jigsaws": jigsaws,
        "functional_blocks": functional,
        "block_entities": block_entities,
        "entity_count": len(root.get("entities", [])),
        "entities": [plain(e) for e in root.get("entities", [])],
        "render": {"generated": renderable, "method": "mcbuild color voxel preview; source block states preserved in report but non-cube block shapes are approximated as cubes", "error": render_error},
    }
    module_out = OUT / name
    module_out.mkdir(parents=True, exist_ok=True)
    (module_out / "source.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if renderable:
        image, labels, stats = build_contact_sheet(grid, VIEWS)
        image.save(module_out / "original-four-view.png")
        report["render"].update({"file": "original-four-view.png", "views": labels, "stats": stats})
        (module_out / "source.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reports = [inspect(name) for name in FILES]
    index = [{key: report[key] for key in ("module", "source_url", "source_blob_sha1", "source_bytes", "size_xyz", "block_count", "palette_size", "material_counts", "jigsaws", "render")} for report in reports]
    (OUT / "summary.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps([{k: r[k] for k in ("module", "source_blob_sha1", "size_xyz", "block_count", "palette_size", "jigsaws")} for r in reports], indent=2))


if __name__ == "__main__":
    main()
