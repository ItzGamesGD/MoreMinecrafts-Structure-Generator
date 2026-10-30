#!/usr/bin/env python3
"""Regenerate the pinned block-entity reference (block_entities-26.3.json) from a real server jar.

Block entities are written into a template as `nbt` on the block, with NO x/y/z (the game adds them) and
with the contents generated at placement time, never copied from the source (see block_entities.py).
The allow-list below is the only place those NBT compounds are decided; every key in it must occur in
vanilla 26.3's own structure templates, which this script counts from the jar:

    python tools/structure_export/reference/build_block_entities.py --server-jar server.jar \
        --sha1 33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import io
import json
import zipfile
from pathlib import Path

import nbtlib

HERE = Path(__file__).resolve().parent
OUT = HERE / "block_entities-26.3.json"

# Ominous banner, exactly the eight layers Raid.getBannerComponentPatch builds in the 26.3 jar.
OMINOUS_PATTERNS = [
    {"pattern": "minecraft:rhombus", "color": "cyan"},
    {"pattern": "minecraft:stripe_bottom", "color": "light_gray"},
    {"pattern": "minecraft:stripe_center", "color": "gray"},
    {"pattern": "minecraft:border", "color": "light_gray"},
    {"pattern": "minecraft:stripe_middle", "color": "black"},
    {"pattern": "minecraft:half_horizontal", "color": "light_gray"},
    {"pattern": "minecraft:circle", "color": "light_gray"},
    {"pattern": "minecraft:border", "color": "black"},
]

# block id -> (vanilla family used as evidence, block-entity id, extra NBT, allowed values of block states).
# A block state property not listed is unconstrained. An empty `nbt` means the game creates an empty block entity.
ALLOW = {
    "minecraft:chest": ("chest", "minecraft:chest", {}, {"type": ["single"]}),  # double chests need a partner block
    "minecraft:barrel": ("barrel", "minecraft:barrel", {}, {"open": ["false"]}),
    "minecraft:furnace": ("furnace", "minecraft:furnace", {}, {"lit": ["false"]}),  # lit needs burn time in the BE
    "minecraft:blast_furnace": ("blast_furnace", "minecraft:blast_furnace", {}, {"lit": ["false"]}),
    "minecraft:white_wall_banner": ("wall_banner", "minecraft:banner", {"patterns": OMINOUS_PATTERNS}, {}),
}
# Vanilla family of each block (what the jar evidence counts). Standing banners have no evidence and are not allowed.
FAMILY_OF = {
    "chest": "chest",
    "barrel": "barrel",
    "furnace": "furnace",
    "blast_furnace": "blast_furnace",
    "wall_banner": "wall_banner",
}


INNER = "META-INF/versions/26.3/server-26.3.jar"  # the game's own jar inside the 26.3 bundler jar


def open_game_jar(jar: Path) -> zipfile.ZipFile:
    outer = zipfile.ZipFile(jar)
    if INNER not in outer.namelist():
        return outer
    return zipfile.ZipFile(io.BytesIO(outer.read(INNER)))


def survey(jar: Path) -> tuple[int, dict]:
    z = open_game_jar(jar)
    keys: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    occurrences: collections.Counter = collections.Counter()
    templates = 0
    for name in sorted(z.namelist()):
        if not (name.startswith("data/minecraft/structure/") and name.endswith(".nbt")):
            continue
        templates += 1
        f = nbtlib.File.parse(io.BytesIO(gzip.decompress(z.read(name))))
        palette = f["palette"] if "palette" in f else f["palettes"][0]
        for block in f["blocks"]:
            if "nbt" not in block:
                continue
            state = palette[int(block["state"])]
            block_id = str(state["Name"] if "Name" in state else state["id"])
            family = _family(block_id)
            if family is None:
                continue
            occurrences[family] += 1
            keys[family].update(str(k) for k in block["nbt"])
    return templates, {
        fam: {"occurrences": occurrences[fam], "keys": dict(sorted(keys[fam].items()))} for fam in sorted(occurrences)
    }


def _family(block_id: str) -> str | None:
    name = block_id.split(":", 1)[1]
    if name.endswith("_wall_banner"):
        return "wall_banner"
    return {"chest": "chest", "barrel": "barrel", "furnace": "furnace", "blast_furnace": "blast_furnace"}.get(name)


def _inner_sha1(jar: Path) -> str:
    outer = zipfile.ZipFile(jar)
    return hashlib.sha1(outer.read(INNER)).hexdigest() if INNER in outer.namelist() else ""


def build(jar: Path, sha1: str) -> dict:
    actual = hashlib.sha1(jar.read_bytes()).hexdigest()
    if actual != sha1:
        raise SystemExit(f"server jar sha1 {actual} is not {sha1}")
    templates, evidence = survey(jar)
    allow = {}
    for block_id, (family, be_id, extra, states) in ALLOW.items():
        nbt = {"id": be_id, **extra}
        assert FAMILY_OF[family] == family
        seen = evidence.get(family, {}).get("keys", {})
        unknown = sorted(set(nbt) - set(seen) - {"id"}) if seen else sorted(nbt)
        if unknown:
            raise SystemExit(f"{block_id}: keys {unknown} never occur in vanilla {family} templates")
        allow[block_id] = {"family": family, "be": be_id, "nbt": nbt, "states": states}
    return {
        "minecraft_version": "26.3",
        "server_jar_sha1": sha1,
        "game_jar_sha1": _inner_sha1(jar),
        "templates_scanned": templates,
        "evidence": evidence,
        "allow": allow,
        "rejected": {
            "standing banners (*_banner)": "no vanilla template evidence for their NBT",
            "every other block entity": "no design need; rejected by the allow-list",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--sha1", required=True, help="expected sha1 of the server jar")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    data = build(a.server_jar, a.sha1)
    a.out.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    print(a.out, {k: v["occurrences"] for k, v in data["evidence"].items()})


if __name__ == "__main__":
    main()
