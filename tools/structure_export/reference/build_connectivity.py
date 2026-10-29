#!/usr/bin/env python3
"""Regenerate the pinned block-connectivity reference from a real server jar.

The converter computes the neighbour-dependent properties of walls, fences, panes/bars and fence
gates (see connectivity.py). The rule code is transcribed from the 26.3 classes; every fact it
reads about a *neighbour* comes from this generated file, never from a hand-written list:

    python tools/structure_export/reference/build_connectivity.py \
        --server-jar server.jar --java /path/to/java25 --sha1 <expected jar sha1>

- ConnectivityProbe.java (run on the jar's own classes): per block the classes the rules test
  with instanceof plus Block.isExceptionForConnection; per state isFaceSturdy for the four
  horizontal sides and the DOWN face of the collision shape tested with WallBlock's own test shapes.
- data/minecraft/tags/block/*.json inside the jar: the block tags the rules test (tags are not
  bound in the probe because no datapack is loaded there).

States are stored compactly: a block whose facts are the same in every state has one fact string;
otherwise `keys` names the fewest properties that determine the facts and `facts` maps their
values (joined with ",", in `keys` order) to a fact string.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import tempfile
import zipfile
from pathlib import Path

from build_reference import run_probe

HERE = Path(__file__).resolve().parent
PROBE = HERE / "ConnectivityProbe.java"
TAGS = ("walls", "fences", "wooden_fences", "wall_post_override", "shulker_boxes")
KINDS = {"wall", "fence", "bars", "fence_gate", "exception", "dynamic_shape"}
# Properties the converter computes; a neighbour's sturdiness must not depend on them (see check below).
COMPUTED = {"north", "east", "south", "west", "up", "in_wall"}
FACTS_DOC = (
    "'ssss/ccccc': s = isFaceSturdy(EmptyBlockGetter, ZERO, side) for north,east,south,west; "
    "c = WallBlock.isCovered(collision DOWN face, test) for TEST_SHAPE_POST then TEST_SHAPES_WALL "
    "north,east,south,west; 1 = true"
)
_LINE = re.compile(r"MMST_(DATA_VERSION|BLOCK|STATE|END)\b ?(.*)$")


def _inner_jar(jar: Path) -> zipfile.ZipFile:
    outer = zipfile.ZipFile(jar)
    inner = [n for n in outer.namelist() if re.fullmatch(r"META-INF/versions/[^/]+/server-[^/]+\.jar", n)]
    if len(inner) != 1:
        raise SystemExit(f"expected one bundled server jar, found {inner}")
    return zipfile.ZipFile(io.BytesIO(outer.read(inner[0])))


def read_tags(jar: Path) -> dict[str, list[str]]:
    with _inner_jar(jar) as z:

        def resolve(name: str, seen: tuple[str, ...] = ()) -> set[str]:
            if name in seen:
                raise SystemExit(f"tag cycle {seen + (name,)}")
            data = json.loads(z.read(f"data/minecraft/tags/block/{name}.json"))
            out: set[str] = set()
            for value in data["values"]:
                entry = value if isinstance(value, str) else value["id"]
                if entry.startswith("#"):
                    namespace, path = entry[1:].split(":", 1)
                    if namespace != "minecraft":
                        raise SystemExit(f"tag {name} references non-vanilla tag {entry}")
                    out |= resolve(path, seen + (name,))
                else:
                    out.add(entry)
            return out

        return {name: sorted(resolve(name)) for name in TAGS}


def parse_probe(out: str) -> tuple[int, dict, dict]:
    data_version, kinds, states = None, {}, {}
    ended = False
    for line in out.splitlines():
        match = _LINE.search(line)
        if not match:
            continue
        tag, rest = match.groups()
        if tag == "DATA_VERSION":
            data_version = int(rest)
        elif tag == "BLOCK":
            block_id, flags = rest.split(" ")
            kinds[block_id] = [] if flags == "-" else flags.split(",")
            states[block_id] = []
        elif tag == "STATE":
            block_id, props, sturdy, cover, offset = rest.split(" ")
            state = {} if props == "-" else dict(p.split("=", 1) for p in props.split(","))
            states[block_id].append((state, f"{sturdy}/{cover}", offset == "offset"))
        else:
            ended = True
    if data_version is None or not ended:
        raise RuntimeError("connectivity probe produced no complete result:\n" + out[-2000:])
    return data_version, kinds, states


def _determined_by(states: list, keys: list[str]) -> dict[str, str] | None:
    table: dict[str, str] = {}
    for state, facts, _ in states:
        key = ",".join(state[k] for k in keys)
        if table.setdefault(key, facts) != facts:
            return None
    return table


def compact(block_id: str, kinds: list[str], states: list) -> dict:
    entry: dict = {"kinds": sorted(kinds)}
    if any(offset for _, _, offset in states):
        entry["offset"] = True  # collision shape depends on the block position (OffsetFunction)
    distinct = {facts for _, facts, _ in states}
    if len(distinct) == 1:
        entry["facts"] = distinct.pop()
        return entry
    keys = sorted(states[0][0])
    for key in list(keys):
        fewer = [k for k in keys if k != key]
        if _determined_by(states, fewer) is not None:
            keys = fewer
    entry["keys"] = keys
    entry["facts"] = dict(sorted(_determined_by(states, keys).items()))
    if set(kinds) & {"wall", "fence", "bars", "fence_gate"}:
        # connectivity.py resolves one layer at a time; that is only sound if what a computed block
        # offers its horizontal neighbours does not depend on the properties being computed.
        sturdy = [(state, facts[:4], offset) for state, facts, offset in states]
        if _determined_by(sturdy, sorted(set(states[0][0]) - COMPUTED)) is None:
            raise SystemExit(f"{block_id}: side sturdiness depends on computed properties")
    return entry


def build(jar: Path, java: str, expected_sha1: str) -> dict:
    actual = hashlib.sha1(jar.read_bytes()).hexdigest()
    if actual != expected_sha1:
        raise SystemExit(f"server jar sha1 {actual} != expected {expected_sha1}")
    with zipfile.ZipFile(jar) as z:
        version = json.loads(z.read("version.json"))
    with tempfile.TemporaryDirectory() as tmp:
        out = run_probe(java, jar, Path(tmp), PROBE)
    data_version, kinds, states = parse_probe(out)
    if data_version != version["world_version"]:
        raise SystemExit(f"probe DataVersion {data_version} != version.json {version['world_version']}")
    unknown = {k for flags in kinds.values() for k in flags} - KINDS
    if unknown:
        raise SystemExit(f"probe reported unknown kinds {sorted(unknown)}")
    tags = read_tags(jar)
    missing = {b for members in tags.values() for b in members} - set(kinds)
    if missing:
        raise SystemExit(f"tags name blocks the probe did not report: {sorted(missing)}")
    return {
        "minecraft_version": version["id"],
        "data_version": version["world_version"],
        "server_jar_sha1": actual,
        "source": "ConnectivityProbe.java on the server jar's classes + data/minecraft/tags/block/*.json in the jar",
        "facts_format": FACTS_DOC,
        "tags": tags,
        "blocks": {block_id: compact(block_id, kinds[block_id], states[block_id]) for block_id in sorted(kinds)},
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
    out = args.out or HERE / f"connectivity-{reference['minecraft_version']}.json"
    write(reference, out)
    print(f"wrote {out}: {len(reference['blocks'])} blocks, DataVersion {reference['data_version']}")


if __name__ == "__main__":
    main()
