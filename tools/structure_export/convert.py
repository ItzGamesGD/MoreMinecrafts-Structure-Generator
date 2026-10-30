"""Sponge v3 .schem -> Minecraft structure template .nbt, driven by one TOML config per structure.

Output schema (verified against the vanilla 26.3 server jar's own data/minecraft/structure/*.nbt
and the MoreMinecrafts-Beta templates under src/main/resources/data/moreminecrafts/structure/):
gzipped unnamed root {DataVersion: int, size: [int x3], palette: [{id, properties?}],
blocks: [{pos: [int x3], state: int, nbt?}], entities: []}. Block-state property values are strings.

Version handling: the target DataVersion and every block id/property/value come from the pinned
reference generated from the real server jar (reference/minecraft-<target>.json). A source state
that does not exist in the target version is an error; nothing is renamed or relabelled.
Properties the source leaves out are filled with the target's default state, which is what the
game itself does when it reads a partial state, and every such fill is listed in the report.
Left-out connection properties of walls, fences, panes/bars and fence gates are then computed from
the neighbouring cells by the vanilla rules (connectivity.py), because jigsaw world generation does
not recompute them.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import nbtlib
from nbtlib.tag import Compound, Int, List, String

from . import block_entities
from .connectivity import Rules, connect, load_connectivity
from .errors import BlockStateError, ConfigError, UnsupportedFeature
from .schem import Schematic, parse_state, read_schematic

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
CONVERTER_VERSION = 2
_ID_RE = re.compile(r"^([a-z0-9_.-]+):([a-z0-9_-]+(?:/[a-z0-9_.-]+)*)$")

# Extension point. Blocks whose correct conversion needs more than an id and properties are
# classified into a feature; a feature without a registered handler is rejected. A handler
# will receive (block_id, resolved state, target) and return the block-entity `nbt` compound to
# attach (or raise). "block_entity" is registered (block_entities.py: allow-listed chests, barrels, furnaces,
# banners). Planned: "jigsaw" (connector data), "structure_void" (omit the cell instead of placing a block).
# Entities and multi-piece structures are rejected earlier, in the schem reader and the config loader.
# Neighbour-dependent properties. Jigsaw pool elements are placed with StructurePlaceSettings.knownShape
# = true (SinglePoolElement in the 26.3 jar), so the game does not recompute them. connectivity.py
# computes them for walls, fences, panes/bars and fence gates; on any other block (vines, chorus,
# redstone wire, ...) a default here is what generates in the world, and the report warns.
CONNECTION_PROPERTIES = {"north", "east", "south", "west", "up", "down"}

FEATURE_HANDLERS: dict[str, Callable[[str, dict[str, str], str], Compound]] = {"block_entity": block_entities.handler}


@cache
def load_reference(target: str) -> dict:
    path = REFERENCE_DIR / f"minecraft-{target}.json"
    if not path.is_file():
        raise ConfigError(f"no pinned block reference for Minecraft {target!r} ({path.name})")
    return json.loads(path.read_text())


def feature_of(block_id: str, entry: dict) -> str | None:
    if block_id == "minecraft:structure_void":
        return "structure_void"
    if block_id == "minecraft:jigsaw":
        return "jigsaw"
    if entry["block_entity"]:
        return "block_entity"
    return None


def resolve_state(
    block_id: str, props: dict[str, str], reference: dict
) -> tuple[tuple[tuple[str, str], ...], list[str]]:
    """Validate a state against the target version and complete it with default properties."""
    entry = reference["blocks"].get(block_id)
    if entry is None:
        raise BlockStateError(f"{block_id} does not exist in Minecraft {reference['minecraft_version']}")
    valid = entry["properties"]
    for key, value in props.items():
        if key not in valid:
            raise BlockStateError(
                f"{block_id} has no property {key!r} in Minecraft {reference['minecraft_version']} "
                f"(valid: {sorted(valid)})"
            )
        if value not in valid[key]:
            raise BlockStateError(f"{block_id}[{key}={value}] is not valid (allowed: {valid[key]})")
    defaulted = sorted(set(valid) - set(props))
    complete = dict(entry["default"])
    complete.update(props)
    return tuple(sorted(complete.items())), defaulted


@dataclass(frozen=True)
class Config:
    path: Path
    source: Path
    source_sha256: str
    source_data_version: int
    target: str
    structure_id: str
    datapack: Path
    reports: Path
    size: tuple[int, int, int]
    offset: tuple[int, int, int]
    air: str

    @property
    def nbt_path(self) -> Path:
        namespace, name = self.structure_id.split(":", 1)
        return self.datapack / "data" / namespace / "structure" / f"{name}.nbt"

    @property
    def report_path(self) -> Path:
        namespace, name = self.structure_id.split(":", 1)
        return self.reports / namespace / f"{name}.json"


def _table(data: dict, key: str, allowed: set[str], where: str) -> dict:
    table = data.get(key)
    if not isinstance(table, dict):
        raise ConfigError(f"{where}: missing [{key}] table")
    unknown = set(table) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown keys in [{key}]: {sorted(unknown)}")
    missing = allowed - set(table)
    if missing:
        raise ConfigError(f"{where}: missing keys in [{key}]: {sorted(missing)}")
    return table


def _repo_path(value: str, where: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ConfigError(f"{where}: path {value!r} leaves the repository")
    return path


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def _triple(value, name: str, where: str) -> tuple[int, int, int]:
    if not (isinstance(value, list) and len(value) == 3 and all(isinstance(v, int) for v in value)):
        raise ConfigError(f"{where}: {name} must be a list of three integers")
    return tuple(value)


def load_config(path: Path) -> Config:
    path = Path(path).resolve()
    where = str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    data = tomllib.loads(path.read_text())
    if "pieces" in data:
        raise UnsupportedFeature(
            "multi_piece", f"{where}: one config converts one template; multi-piece structures are not supported yet"
        )
    unknown = set(data) - {"format", "target", "source", "output", "expect", "options"}
    if unknown:
        raise ConfigError(f"{where}: unknown top-level keys {sorted(unknown)}")
    if data.get("format") != 1:
        raise ConfigError(f"{where}: format must be 1")
    if not isinstance(data.get("target"), str):
        raise ConfigError(f"{where}: target (Minecraft version of the pinned reference) is required")
    source = _table(data, "source", {"path", "sha256", "data_version"}, where)
    output = _table(data, "output", {"id", "datapack", "reports"}, where)
    expect = _table(data, "expect", {"size", "offset"}, where)
    options = _table(data, "options", {"air"}, where)
    match = _ID_RE.match(str(output["id"]))
    if not match or ".." in output["id"]:
        raise ConfigError(f"{where}: output id {output['id']!r} is not a valid namespace:path resource id")
    if options["air"] not in ("include", "omit"):
        raise ConfigError(f"{where}: options.air must be 'include' or 'omit'")
    size = _triple(expect["size"], "expect.size", where)
    if min(size) < 1:
        raise ConfigError(f"{where}: expect.size must be positive")
    return Config(
        path=path,
        source=_repo_path(source["path"], where),
        source_sha256=str(source["sha256"]),
        source_data_version=int(source["data_version"]),
        target=data["target"],
        structure_id=output["id"],
        datapack=_repo_path(output["datapack"], where),
        reports=_repo_path(output["reports"], where),
        size=size,
        offset=_triple(expect["offset"], "expect.offset", where),
        air=options["air"],
    )


def _check_source(config: Config, raw: bytes, schem: Schematic) -> None:
    digest = hashlib.sha256(raw).hexdigest()
    if digest != config.source_sha256:
        raise ConfigError(f"{config.source.name}: sha256 {digest} != pinned {config.source_sha256}")
    if schem.data_version != config.source_data_version:
        raise ConfigError(
            f"{config.source.name}: DataVersion {schem.data_version} != configured {config.source_data_version}"
        )
    if schem.size != config.size:
        raise ConfigError(f"{config.source.name}: size {schem.size} != expected {config.size}")
    if schem.offset != config.offset:
        raise ConfigError(f"{config.source.name}: offset {schem.offset} != expected {config.offset}")


@dataclass(frozen=True)
class Result:
    config: Config
    nbt: bytes
    report: dict
    block_entities: dict[tuple[int, int, int], Compound] = field(default_factory=dict)


def convert(config: Config) -> Result:
    reference = load_reference(config.target)
    raw = config.source.read_bytes()
    schem = read_schematic(config.source)
    _check_source(config, raw, schem)

    used = sorted(set(schem.cells))
    rules = Rules(load_connectivity(config.target))
    resolved: dict[int, tuple[str, tuple[tuple[str, str], ...]] | None] = {}
    block_nbt: dict[int, Compound] = {}
    explicit: dict[int, set[str]] = {}
    defaulted: dict[str, list[str]] = {}
    warnings: list[str] = []
    for index in used:
        text = schem.palette[index]
        block_id, props = parse_state(text)
        state, filled = resolve_state(block_id, props, reference)
        feature = feature_of(block_id, reference["blocks"][block_id])
        if feature is not None:
            if feature not in FEATURE_HANDLERS:
                raise UnsupportedFeature(feature, f"{text} (palette index {index}) needs '{feature}' handling")
            block_nbt[index] = FEATURE_HANDLERS[feature](block_id, dict(state), config.target)
        if filled:
            defaulted[text] = filled
            unconnected = sorted(set(filled) & CONNECTION_PROPERTIES)
            if unconnected and rules.kind(block_id) is None:
                warnings.append(
                    f"{text}: connection properties {unconnected} defaulted and not computed for this block; "
                    "jigsaw worldgen places templates without neighbour shape updates, so these stay unconnected"
                )
        explicit[index] = set(props)
        resolved[index] = None if (config.air == "omit" and block_id == "minecraft:air") else (block_id, state)

    found, stated, nbts = {}, {}, {}
    for index, palette_index in enumerate(schem.cells):
        state = resolved[palette_index]
        if state is not None:
            pos = schem.position(index)
            found[pos] = (state[0], dict(state[1]))
            stated[pos] = explicit[palette_index]
            if palette_index in block_nbt:
                nbts[pos] = block_nbt[palette_index]
    if not found:
        raise ConfigError(f"{config.source.name}: no blocks left to export")
    found, connectivity = connect(found, stated, schem.size, load_connectivity(config.target))
    cells = {pos: (block_id, tuple(sorted(props.items()))) for pos, (block_id, props) in found.items()}
    if connectivity["boundary_unresolved"]:
        warnings.append(
            f"{len(connectivity['boundary_unresolved'])} connecting blocks border the template box or omitted air; "
            "their connections toward that unknown terrain were computed as if it were air "
            "(connectivity.boundary_unresolved)"
        )
    if connectivity["unresolved"]:
        warnings.append(
            f"{len(connectivity['unresolved'])} connecting blocks kept default connections because a neighbour's "
            "shape depends on its position or block entity (connectivity.unresolved)"
        )

    palette: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    lookup: dict = {}
    blocks = []
    for pos in sorted(cells):
        key = cells[pos]
        if key not in lookup:
            lookup[key] = len(palette)
            palette.append(key)
        entry = Compound({"pos": List[Int](pos), "state": Int(lookup[key])})
        if pos in nbts:
            entry["nbt"] = nbts[pos]
        blocks.append(entry)
    palette_nbt = []
    for block_id, state in palette:
        entry = Compound({"id": String(block_id)})
        if state:
            entry["properties"] = Compound({k: String(v) for k, v in state})
        palette_nbt.append(entry)
    root = nbtlib.File(
        {
            "DataVersion": Int(reference["data_version"]),
            "size": List[Int](schem.size),
            "palette": List[Compound](palette_nbt),
            "blocks": List[Compound](blocks),
            "entities": List[Compound]([]),
        },
        root_name="",
    )
    buffer = io.BytesIO()
    root.write(buffer)
    nbt = gzip.compress(buffer.getvalue(), mtime=0)

    counts: dict[str, int] = {}
    for block_id, state in cells.values():
        text = block_id + ("[" + ",".join(f"{k}={v}" for k, v in state) + "]" if state else "")
        counts[text] = counts.get(text, 0) + 1
    report = {
        "converter_version": CONVERTER_VERSION,
        "config": _rel(config.path),
        "structure_id": config.structure_id,
        "output": _rel(config.nbt_path),
        "output_sha256": hashlib.sha256(nbt).hexdigest(),
        "source": {
            "path": _rel(config.source),
            "sha256": config.source_sha256,
            "data_version": schem.data_version,
            "size": list(schem.size),
            "offset": list(schem.offset),
            "palette_entries": len(schem.palette),
            "unused_palette_entries": [schem.palette[i] for i in range(len(schem.palette)) if i not in resolved],
            "metadata_keys_ignored": list(schem.metadata_keys),
        },
        "target": {
            "minecraft_version": reference["minecraft_version"],
            "data_version": reference["data_version"],
            "server_jar_sha1": reference["server_jar_sha1"],
        },
        "air": config.air,
        "size": list(schem.size),
        "cells": len(schem.cells),
        "blocks": len(blocks),
        "palette": len(palette),
        "defaulted_properties": defaulted,
        "connectivity": connectivity,
        "warnings": warnings,
        "state_counts": dict(sorted(counts.items())),
    }
    return Result(config=config, nbt=nbt, report=report, block_entities=nbts)


def report_text(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def write(result: Result) -> None:
    for path, data in (
        (result.config.nbt_path, result.nbt),
        (result.config.report_path, report_text(result.report).encode()),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
