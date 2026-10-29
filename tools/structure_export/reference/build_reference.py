#!/usr/bin/env python3
"""Regenerate the pinned Minecraft block reference from a real server jar.

The reference is the converter's only source of truth for block ids, block-state properties,
default states, block-entity blocks and the target DataVersion. It is generated, never edited:

    python tools/structure_export/reference/build_reference.py \
        --server-jar server.jar --java /path/to/java25 --sha1 <expected jar sha1>

Data comes from the jar itself: `version.json` (DataVersion), the vanilla data generator's
`--reports` blocks report (properties, valid values, default state) and BlockEntityProbe.java
(which blocks implement EntityBlock). The probe needs the unobfuscated 26.x class names.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "BlockEntityProbe.java"


def _sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _probe(java: str, jar: Path, work: Path) -> tuple[int, list[str]]:
    lib_dir = work / "classpath"
    with zipfile.ZipFile(jar) as outer:
        members = [m for m in outer.namelist() if m.startswith("META-INF/") and m.endswith(".jar")]
        for member in members:
            outer.extract(member, lib_dir)
    classpath = ":".join(str(p) for p in sorted(lib_dir.rglob("*.jar")))
    out = subprocess.run(
        [java, "-cp", classpath, str(PROBE)], cwd=work, capture_output=True, text=True, check=True
    ).stdout
    version = re.search(r"MMST_DATA_VERSION (\d+)", out)
    blocks = re.search(r"MMST_BLOCK_ENTITY_BLOCKS (\S+)", out)
    if not version or not blocks:
        raise RuntimeError("block-entity probe produced no result:\n" + out[-2000:])
    return int(version.group(1)), blocks.group(1).split(",")


def build(jar: Path, java: str, expected_sha1: str) -> dict:
    actual = _sha1(jar)
    if actual != expected_sha1:
        raise SystemExit(f"server jar sha1 {actual} != expected {expected_sha1}")
    with zipfile.ZipFile(jar) as z:
        version = json.loads(z.read("version.json"))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        subprocess.run(
            [
                java,
                "-DbundlerMainClass=net.minecraft.data.Main",
                "-jar",
                str(jar),
                "--reports",
                "--output",
                str(work / "generated"),
            ],
            cwd=work,
            capture_output=True,
            check=True,
        )
        report = json.loads((work / "generated/reports/blocks.json").read_text())
        probe_version, entity_blocks = _probe(java, jar, work)
    if probe_version != version["world_version"]:
        raise SystemExit(f"probe DataVersion {probe_version} != version.json {version['world_version']}")
    unknown = set(entity_blocks) - set(report)
    if unknown:
        raise SystemExit(f"probe reported blocks missing from the blocks report: {sorted(unknown)}")
    blocks = {}
    for block_id in sorted(report):
        entry = report[block_id]
        defaults = [s for s in entry["states"] if s.get("default")]
        if len(defaults) != 1:
            raise SystemExit(f"{block_id}: expected one default state, found {len(defaults)}")
        blocks[block_id] = {
            "properties": entry.get("properties", {}),
            "default": defaults[0].get("properties", {}),
            "block_entity": block_id in entity_blocks,
        }
    return {
        "minecraft_version": version["id"],
        "data_version": version["world_version"],
        "server_jar_sha1": actual,
        "source": "vanilla data generator --reports blocks.json + BlockEntityProbe.java (EntityBlock)",
        "blocks": blocks,
    }


def write(reference: dict, path: Path) -> None:
    head = {k: v for k, v in reference.items() if k != "blocks"}
    lines = [json.dumps(head, sort_keys=True)[:-1] + ', "blocks": {']
    items = list(reference["blocks"].items())
    for i, (block_id, entry) in enumerate(items):
        sep = "," if i < len(items) - 1 else ""
        lines.append(f"  {json.dumps(block_id)}: {json.dumps(entry, sort_keys=True)}{sep}")
    lines.append("}}")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--server-jar", type=Path, required=True)
    parser.add_argument("--java", default="java", help="a Java runtime the server jar supports")
    parser.add_argument("--sha1", required=True, help="expected sha1 of the server jar")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    reference = build(args.server_jar, args.java, args.sha1)
    out = args.out or HERE / f"minecraft-{reference['minecraft_version']}.json"
    write(reference, out)
    print(f"wrote {out}: {len(reference['blocks'])} blocks, DataVersion {reference['data_version']}")


if __name__ == "__main__":
    main()
