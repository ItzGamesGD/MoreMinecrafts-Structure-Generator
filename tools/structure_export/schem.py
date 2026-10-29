"""Strict reader for Sponge Schematic v3 (.schem) files as written by vendored mcbuild.

Layout (Sponge Schematic Specification v3, and mcbuild's export/schem.py):
an unnamed gzipped root compound holding one `Schematic` compound with `Version`=3,
`DataVersion`, unsigned-short `Width`/`Height`/`Length`, int[3] `Offset`, and `Blocks` =
{`Palette`: {state string -> int}, `Data`: varint byte array, `BlockEntities`: list}.
Block indexes are ordered x + z*Width + y*Width*Length.

Anything this MVP cannot carry into a structure template is rejected, never dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import nbtlib

from .errors import SchemError, UnsupportedFeature

_SCHEMATIC_KEYS = {
    "Version",
    "DataVersion",
    "Width",
    "Height",
    "Length",
    "Offset",
    "Blocks",
    "Entities",
    "Metadata",
    "Biomes",
}
_BLOCKS_KEYS = {"Palette", "Data", "BlockEntities"}
_STATE_RE = re.compile(r"^([a-z0-9_.-]+):([a-z0-9_./-]+)(?:\[(.*)\])?$")


@dataclass(frozen=True)
class Schematic:
    data_version: int
    size: tuple[int, int, int]  # (x, y, z) = (Width, Height, Length)
    offset: tuple[int, int, int]
    palette: tuple[str, ...]  # palette index -> block-state string
    cells: tuple[int, ...]  # dense palette indexes, x + z*W + y*W*L
    metadata_keys: tuple[str, ...] = field(default=())

    def position(self, index: int) -> tuple[int, int, int]:
        w, _, length = self.size
        y, rest = divmod(index, w * length)
        z, x = divmod(rest, w)
        return x, y, z


def parse_state(text: str) -> tuple[str, dict[str, str]]:
    """Split `ns:name[k=v,...]` into the block id and its property map."""
    match = _STATE_RE.match(text)
    if not match:
        raise SchemError(f"malformed block state {text!r} (expected namespace:name[key=value,...])")
    block_id = f"{match.group(1)}:{match.group(2)}"
    props: dict[str, str] = {}
    if match.group(3) is not None:
        if not match.group(3):
            raise SchemError(f"empty property list in {text!r}")
        for part in match.group(3).split(","):
            key, sep, value = part.partition("=")
            if not sep or not key or not value:
                raise SchemError(f"malformed property {part!r} in {text!r}")
            if key in props:
                raise SchemError(f"duplicate property {key!r} in {text!r}")
            props[key] = value
    return block_id, props


def _decode_varints(data: bytes, expected: int) -> list[int]:
    values, value, shift, length = [], 0, 0, 0
    for byte in data:
        value |= (byte & 0x7F) << shift
        length += 1
        if length > 5:
            raise SchemError("varint longer than 5 bytes in Blocks.Data")
        if byte & 0x80:
            shift += 7
            continue
        values.append(value)
        value, shift, length = 0, 0, 0
    if length:
        raise SchemError("Blocks.Data ends inside a varint")
    if len(values) != expected:
        raise SchemError(f"Blocks.Data holds {len(values)} blocks, Width*Height*Length is {expected}")
    return values


def read_schematic(path: Path) -> Schematic:
    root = nbtlib.load(path)
    if "Schematic" not in root:
        if "Version" in root:
            raise UnsupportedFeature(
                "sponge_v1_v2", f"{path}: flat Sponge v{int(root['Version'])} layout; only v3 is supported"
            )
        raise SchemError(f"{path}: no Schematic compound")
    if set(root) != {"Schematic"}:
        raise SchemError(f"{path}: unexpected root tags {sorted(set(root) - {'Schematic'})}")
    s = root["Schematic"]
    unknown = set(s) - _SCHEMATIC_KEYS
    if unknown:
        raise SchemError(f"{path}: unknown Schematic tags {sorted(unknown)}")
    if int(s["Version"]) != 3:
        raise UnsupportedFeature(
            "sponge_version", f"{path}: Sponge schematic version {int(s['Version'])}; only 3 is supported"
        )
    if "Biomes" in s:
        raise UnsupportedFeature("biomes", f"{path}: biome data has no structure-template equivalent")
    if len(s.get("Entities", [])):
        raise UnsupportedFeature("entities", f"{path}: {len(s['Entities'])} entities")
    size = tuple(int(s[k]) & 0xFFFF for k in ("Width", "Height", "Length"))
    if min(size) < 1:
        raise SchemError(f"{path}: empty schematic size {size}")
    offset = tuple(int(v) for v in s.get("Offset", [0, 0, 0]))
    if len(offset) != 3:
        raise SchemError(f"{path}: Offset must hold 3 ints")
    blocks = s["Blocks"]
    unknown = set(blocks) - _BLOCKS_KEYS
    if unknown:
        raise SchemError(f"{path}: unknown Blocks tags {sorted(unknown)}")
    if len(blocks.get("BlockEntities", [])):
        raise UnsupportedFeature("block_entities", f"{path}: {len(blocks['BlockEntities'])} block entities")
    by_index: dict[int, str] = {}
    for state, index in blocks["Palette"].items():
        index = int(index)
        if index in by_index:
            raise SchemError(f"{path}: palette index {index} used by {by_index[index]!r} and {state!r}")
        by_index[index] = str(state)
    if sorted(by_index) != list(range(len(by_index))):
        raise SchemError(f"{path}: palette indexes are not contiguous from 0")
    palette = tuple(by_index[i] for i in range(len(by_index)))
    cells = _decode_varints(bytes(b & 0xFF for b in blocks["Data"]), size[0] * size[1] * size[2])
    bad = {v for v in cells if v >= len(palette)}
    if bad:
        raise SchemError(f"{path}: Blocks.Data references palette indexes {sorted(bad)} beyond the palette")
    return Schematic(
        data_version=int(s["DataVersion"]),
        size=size,
        offset=offset,
        palette=palette,
        cells=tuple(cells),
        metadata_keys=tuple(sorted(s.get("Metadata", {}))),
    )
