"""Independent validation of an exported structure template against its source .schem.

Deliberately shares no code with the writer: it decodes both gzipped NBT files with its own
minimal reader (no nbtlib), re-decodes the Sponge varints itself, and only reuses the pinned
block reference JSON. It checks the template schema, every palette state against the target
version, bounds/duplicates/palette indexes, and cell-by-cell equivalence with the source.

Computed connection properties (connectivity.py) are the one allowed difference, and only when the
connectivity reference is passed: a cell may differ from its default-completed source state only in
connection properties of a wall/fence/pane/bars/fence-gate that the source left out. Those cells are
then checked against invariants of the vanilla rules that need no shape data: a connected side faces
a block inside the template, two neighbouring walls (or bars, or same-material fences) whose shared
sides were both computed connect to each other, and in_wall is true exactly when a wall flanks the gate.
The game itself is the full oracle for these values (live.py).
"""

from __future__ import annotations

import gzip
import json
import struct
from pathlib import Path

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, BYTE_ARRAY, STRING, LIST, COMPOUND, INT_ARRAY, LONG_ARRAY = range(13)


class VerificationError(Exception):
    """The exported template is invalid or differs from its source."""


def _check(condition, message) -> None:
    if not condition:
        raise VerificationError(message)


class Tagged:
    """A decoded value together with its NBT tag type (and list element type)."""

    __slots__ = ("type", "value", "element")

    def __init__(self, tag_type: int, value, element: int | None = None):
        self.type, self.value, self.element = tag_type, value, element


class _Reader:
    def __init__(self, data: bytes):
        self.data, self.at = data, 0

    def take(self, fmt: str):
        size = struct.calcsize(fmt)
        values = struct.unpack_from(">" + fmt, self.data, self.at)
        self.at += size
        return values[0] if len(values) == 1 else values

    def string(self) -> str:
        length = self.take("H")
        text = self.data[self.at : self.at + length].decode("utf-8")
        self.at += length
        return text

    def payload(self, tag_type: int) -> Tagged:
        simple = {BYTE: "b", SHORT: "h", INT: "i", LONG: "q", FLOAT: "f", DOUBLE: "d"}
        if tag_type in simple:
            return Tagged(tag_type, self.take(simple[tag_type]))
        if tag_type == STRING:
            return Tagged(tag_type, self.string())
        if tag_type in (BYTE_ARRAY, INT_ARRAY, LONG_ARRAY):
            n = self.take("i")
            fmt = {BYTE_ARRAY: "b", INT_ARRAY: "i", LONG_ARRAY: "q"}[tag_type]
            values = struct.unpack_from(f">{n}{fmt}", self.data, self.at)
            self.at += struct.calcsize(f">{n}{fmt}")
            return Tagged(tag_type, list(values))
        if tag_type == LIST:
            element, n = self.take("b"), self.take("i")
            return Tagged(LIST, [self.payload(element) for _ in range(n)], element)
        if tag_type == COMPOUND:
            out = {}
            while True:
                child = self.take("b")
                if child == END:
                    return Tagged(COMPOUND, out)
                name = self.string()
                if name in out:
                    raise ValueError(f"duplicate compound key {name!r}")
                out[name] = self.payload(child)
        raise ValueError(f"unknown tag type {tag_type}")


def read_nbt(path: Path) -> tuple[str, Tagged]:
    raw = Path(path).read_bytes()
    if raw[:2] != b"\x1f\x8b":
        raise ValueError(f"{path}: not gzip-compressed")
    reader = _Reader(gzip.decompress(raw))
    if reader.take("b") != COMPOUND:
        raise ValueError(f"{path}: root is not a compound")
    name = reader.string()
    root = reader.payload(COMPOUND)
    if reader.at != len(reader.data):
        raise ValueError(f"{path}: {len(reader.data) - reader.at} trailing bytes")
    return name, root


def plain(tag: Tagged):
    if tag.type == COMPOUND:
        return {k: plain(v) for k, v in tag.value.items()}
    if tag.type == LIST:
        return [plain(v) for v in tag.value]
    return tag.value


def _source_cells(schem_path: Path) -> tuple[tuple[int, int, int], dict[tuple[int, int, int], str]]:
    _, root = read_nbt(schem_path)
    s = root.value["Schematic"].value
    w, h, length = (s[k].value & 0xFFFF for k in ("Width", "Height", "Length"))
    palette = {v.value: k for k, v in s["Blocks"].value["Palette"].value.items()}
    data = bytes(b & 0xFF for b in s["Blocks"].value["Data"].value)
    values, value, shift = [], 0, 0
    for byte in data:
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
        else:
            values.append(value)
            value, shift = 0, 0
    _check(len(values) == w * h * length, "source block count mismatch")
    cells = {}
    for i, v in enumerate(values):
        y, rest = divmod(i, w * length)
        z, x = divmod(rest, w)
        cells[(x, y, z)] = palette[v]
    return (w, h, length), cells


def _complete(text: str, reference: dict) -> tuple[str, dict[str, str]]:
    block_id, _, rest = text.partition("[")
    props = dict(p.split("=", 1) for p in rest.rstrip("]").split(",")) if rest else {}
    if block_id.endswith("_stairs"):
        _check({"facing", "half", "shape"} <= set(props), f"{block_id}: stairs require explicit facing, half, shape")
    full = dict(reference["blocks"][block_id]["default"])
    full.update(props)
    return block_id, full


_SIDES = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0)}
_OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
_COMPUTED = {
    "wall": {"north", "east", "south", "west", "up"},
    "fence": {"north", "east", "south", "west"},
    "bars": {"north", "east", "south", "west"},
    "fence_gate": {"in_wall"},
}


def _check_connections(placed: dict, expected: dict, source: dict, changed: set, connectivity: dict) -> None:
    blocks = connectivity["blocks"]
    tags = {name: set(members) for name, members in connectivity["tags"].items()}

    def kind(block_id):
        found = set(blocks[block_id]["kinds"]) & set(_COMPUTED)
        return found.pop() if found else None

    def stated(pos):
        text = source[pos]
        rest = text.partition("[")[2]
        return {p.split("=", 1)[0] for p in rest.rstrip("]").split(",")} if rest else set()

    def computed(pos):
        block_id = placed[pos][0]
        k = kind(block_id)
        return (_COMPUTED[k] - stated(pos)) if k else set()

    def neighbour(pos, side):
        npos = tuple(pos[i] + _SIDES[side][i] for i in range(3))
        return placed.get(npos), npos

    def family(block_id):
        k = kind(block_id)
        if k == "fence":
            return ("fence", block_id in tags["wooden_fences"])
        return k if k in ("wall", "bars") else None

    for pos in changed:
        block_id, props = placed[pos]
        diff = {key for key in props if props[key] != expected[pos][1][key]}
        _check(diff <= computed(pos), f"{pos} {block_id}: properties {sorted(diff)} changed")
    for pos, (block_id, props) in placed.items():
        k = kind(block_id)
        if k is None:
            continue
        mine = computed(pos)
        for side in _SIDES:
            if side not in mine:
                continue
            nb, npos = neighbour(pos, side)
            connected = props[side] not in ("none", "false")
            if connected:
                _check(
                    nb is not None and nb[0] not in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"),
                    f"{pos} {block_id}: {side} connects to nothing",
                )
            pair = nb is not None and family(block_id) is not None and family(nb[0]) == family(block_id)
            if pair and _OPPOSITE[side] in computed(npos):
                _check(connected, f"{pos} {block_id}: does not connect {side} to {nb[0]} at {npos}")
        if "in_wall" in mine:
            axis = ("east", "west") if props["facing"] in ("north", "south") else ("north", "south")
            flanked = any((neighbour(pos, side)[0] or ("",))[0] in tags["walls"] for side in axis)
            _check(props["in_wall"] == str(flanked).lower(), f"{pos} {block_id}: in_wall={props['in_wall']}")


def verify(
    nbt_path: Path,
    schem_path: Path,
    reference: dict,
    air: str,
    connectivity: dict | None = None,
    block_entities: dict | None = None,
) -> dict:
    """Return a summary dict; raise VerificationError on the first violation.

    `block_entities` is the pinned block-entity allow-list (reference/block_entities-26.3.json). Without it no
    block entity is accepted, so a template with block entities cannot pass a check that did not name the policy.
    """
    name, root = read_nbt(nbt_path)
    _check(name == "", f"root name {name!r} (vanilla templates use an empty name)")
    r = root.value
    _check(set(r) == {"DataVersion", "size", "palette", "blocks", "entities"}, f"root keys {sorted(r)}")
    _check(r["DataVersion"].type == INT and r["DataVersion"].value == reference["data_version"], "DataVersion")
    _check(r["size"].type == LIST and r["size"].element == INT and len(r["size"].value) == 3, "size must be 3 ints")
    size = tuple(v.value for v in r["size"].value)
    _check(r["entities"].type == LIST and not r["entities"].value, "entities must be empty")
    _check(r["palette"].type == LIST and r["palette"].element == COMPOUND, "palette must be a compound list")
    palette = []
    for entry in r["palette"].value:
        e = entry.value
        _check(set(e) <= {"id", "properties"} and "id" in e, f"palette entry keys {sorted(e)}")
        _check(e["id"].type == STRING, "palette id must be a string")
        block_id = e["id"].value
        ref = reference["blocks"].get(block_id)
        _check(ref is not None, f"{block_id} unknown in Minecraft {reference['minecraft_version']}")
        props = {}
        if "properties" in e:
            _check(e["properties"].type == COMPOUND, f"{block_id}: properties must be a compound")
            for k, v in e["properties"].value.items():
                _check(v.type == STRING, f"{block_id}.{k} must be a string")
                props[k] = v.value
        _check(set(props) == set(ref["properties"]), f"{block_id}: incomplete state {props}")
        for k, v in props.items():
            _check(v in ref["properties"][k], f"{block_id}[{k}={v}] invalid")
        allowed = block_entities is not None and block_id in block_entities["allow"]
        _check(
            allowed or (not ref["block_entity"] and block_id not in ("minecraft:jigsaw", "minecraft:structure_void")),
            f"{block_id} needs feature handling outside the block-entity allow-list",
        )
        if allowed:
            for k, values in block_entities["allow"][block_id]["states"].items():
                _check(props.get(k) in values, f"{block_id}[{k}={props.get(k)}] is not an allowed block-entity state")
        palette.append((block_id, props))
    _check(len({(b, tuple(sorted(p.items()))) for b, p in palette}) == len(palette), "duplicate palette states")
    _check(r["blocks"].type == LIST and r["blocks"].element == COMPOUND, "blocks must be a compound list")
    placed, used, placed_nbt = {}, set(), {}
    for entry in r["blocks"].value:
        e = entry.value
        _check(set(e) <= {"pos", "state", "nbt"} and {"pos", "state"} <= set(e), f"block entry keys {sorted(e)}")
        _check(e["pos"].element == INT and e["state"].type == INT, "pos must be an int list and state an int")
        pos = tuple(v.value for v in e["pos"].value)
        _check(len(pos) == 3 and all(0 <= pos[i] < size[i] for i in range(3)), f"{pos} outside {size}")
        _check(pos not in placed, f"duplicate block at {pos}")
        state = e["state"].value
        _check(0 <= state < len(palette), f"state index {state} out of range")
        placed[pos] = palette[state]
        used.add(state)
        if "nbt" in e:
            _check(e["nbt"].type == COMPOUND, f"{pos}: nbt must be a compound")
            placed_nbt[pos] = plain(e["nbt"])
    _check(used == set(range(len(palette))), "unused palette entries")

    source_size, source = _source_cells(schem_path)
    _check(size == source_size, f"size {size} != source {source_size}")
    expected = {}
    for pos, text in source.items():
        block_id, props = _complete(text, reference)
        if air == "omit" and block_id == "minecraft:air":
            continue
        expected[pos] = (block_id, props)
    missing = sorted(set(expected) - set(placed))
    extra = sorted(set(placed) - set(expected))
    _check(not missing and not extra, f"missing {missing[:5]} extra {extra[:5]}")
    for pos, (block_id, _) in expected.items():
        want = (
            block_entities["allow"][block_id]["nbt"] if block_entities and block_id in block_entities["allow"] else None
        )
        have = placed_nbt.get(pos)
        _check(have == want, f"{pos} {block_id}: block-entity data {have} != {want}")
    wrong = [p for p in expected if expected[p] != placed[p]]
    changed = set()
    if connectivity is not None:
        changed = {p for p in wrong if expected[p][0] == placed[p][0]}
        wrong = [p for p in wrong if p not in changed]
    if wrong:
        first = wrong[0]
        raise VerificationError(f"{len(wrong)} cells differ, first {first}: {expected[first]} != {placed[first]}")
    if connectivity is not None:
        _check_connections(placed, expected, source, changed, connectivity)
    non_air = sum(1 for b, _ in placed.values() if b != "minecraft:air")
    return {
        "size": list(size),
        "blocks": len(placed),
        "non_air_blocks": non_air,
        "palette": len(palette),
        "source_cells": len(source),
        "cells_compared": len(expected),
        "mismatches": 0,
        "connection_cells_computed": len(changed),
    }


def load_reference_json(path: Path) -> dict:
    return json.loads(Path(path).read_text())
