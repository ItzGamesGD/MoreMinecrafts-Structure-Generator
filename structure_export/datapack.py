"""Deterministic vanilla datapack builder for Jigsaw structures."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from structure_export.nbt import read_nbt
from structure_export.structure import structure_bytes, validate_structure

MINECRAFT_VERSION = "26.3"
WORLD_VERSION = 5023
DATA_PACK_FORMAT = 121
_ID_PART = re.compile(r"^[a-z0-9._/-]+$")


def _resource_id(value: str, *, allow_external: bool = True) -> tuple[str, str]:
    if not isinstance(value, str) or value.count(":") > 1:
        raise ValueError(f"Invalid resource identifier: {value!r}")
    if ":" in value:
        namespace, path = value.split(":", 1)
    elif allow_external:
        namespace, path = "minecraft", value
    else:
        raise ValueError(f"Resource identifier must include a namespace: {value!r}")
    if not namespace or not re.fullmatch(r"[a-z0-9._-]+", namespace) or not _ID_PART.fullmatch(path):
        raise ValueError(f"Invalid resource identifier: {value!r}")
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise ValueError(f"Invalid resource path: {value!r}")
    return namespace, path


class DatapackBuilder:
    """Collect resources and emit a complete, reproducible Minecraft data pack."""

    def __init__(self, root: Path | str, *, namespace: str, pack_format: int = DATA_PACK_FORMAT):
        self.root = Path(root)
        if not re.fullmatch(r"[a-z0-9._-]+", namespace):
            raise ValueError(f"Invalid datapack namespace: {namespace!r}")
        self.namespace = namespace
        self.pack_format = pack_format
        self.resources: dict[str, bytes] = {}
        self.references: dict[str, list[str]] = {}
        self.structures: set[str] = set()
        self.pools: set[str] = set()
        self.worldgen_structures: set[str] = set()
        self.structure_sets: set[str] = set()

    def _resource_path(self, kind: str, identifier: str, *, namespace: str | None = None) -> str:
        found_namespace, path = _resource_id(identifier, allow_external=False)
        if namespace is not None and found_namespace != namespace:
            raise ValueError(f"Resource {identifier!r} must use the {namespace} namespace")
        return f"data/{found_namespace}/{kind}/{path}"

    def _put_json(self, path: str, value: dict[str, Any], *, references: list[str] | None = None) -> None:
        self.resources[path] = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.references[path] = sorted(set(references or []))

    def add_structure(self, identifier: str, template: dict[str, object]) -> None:
        path = self._resource_path("structure", identifier, namespace=self.namespace) + ".nbt"
        if path in self.resources:
            raise ValueError(f"Duplicate structure resource: {identifier}")
        validate_structure(template)
        self.resources[path] = structure_bytes(template)
        self.references[path] = []
        self.structures.add(identifier)

    def add_template_pool(
        self,
        identifier: str,
        locations: list[str],
        *,
        fallback: str = "minecraft:empty",
        projection: str = "rigid",
    ) -> None:
        if not locations:
            raise ValueError("A template pool must have at least one element")
        if projection not in {"rigid", "terrain_matching"}:
            raise ValueError(f"Unsupported template projection: {projection}")
        namespace, _ = _resource_id(identifier, allow_external=False)
        if namespace != self.namespace:
            raise ValueError(f"Template pool {identifier!r} must use the {self.namespace} namespace")
        entries = []
        for location in locations:
            _resource_id(location)
            entries.append(
                {
                    "element": {
                        "element_type": "minecraft:single_pool_element",
                        "location": location,
                        "processors": {"processors": []},
                        "projection": projection,
                    },
                    "weight": 1,
                }
            )
        _resource_id(fallback)
        path = self._resource_path("worldgen/template_pool", identifier, namespace=self.namespace) + ".json"
        if path in self.resources:
            raise ValueError(f"Duplicate template pool: {identifier}")
        self._put_json(path, {"elements": entries, "fallback": fallback}, references=[*locations, fallback])
        self.pools.add(identifier)

    def add_jigsaw_structure(
        self,
        identifier: str,
        *,
        start_pool: str,
        size: int,
        step: str,
        terrain_adaptation: str,
        max_distance_from_center: int,
        start_height: dict[str, object] | None = None,
        biome_tag: str = "#minecraft:is_overworld",
        dimension_padding: int = 10,
    ) -> None:
        namespace, _ = _resource_id(identifier, allow_external=False)
        if namespace != self.namespace:
            raise ValueError(f"Worldgen structure {identifier!r} must use the {self.namespace} namespace")
        _resource_id(start_pool)
        if not 0 <= size <= 20:
            raise ValueError("Jigsaw size must be in the range 0..20")
        if step not in {"raw_generation", "lakes", "local_modifications", "underground_structures", "surface_structures", "strongholds", "underground_decoration", "fluid_springs", "vegetal_decoration", "top_layer_modification"}:
            raise ValueError(f"Unsupported generation step: {step}")
        if terrain_adaptation not in {"none", "bury", "beard_thin", "beard_box", "encapsulate"}:
            raise ValueError(f"Unsupported terrain adaptation: {terrain_adaptation}")
        if max_distance_from_center <= 0 or max_distance_from_center > 116:
            raise ValueError("max_distance_from_center must be in the range 1..116")
        if dimension_padding < 0 or dimension_padding > 16:
            raise ValueError("dimension_padding must be in the range 0..16")
        if not biome_tag.startswith("#"):
            raise ValueError("biome_tag must be a biome tag reference beginning with #")
        _resource_id(biome_tag[1:])
        height = start_height or {
            "type": "minecraft:uniform",
            "min_inclusive": {"absolute": -40},
            "max_inclusive": {"absolute": -20},
        }
        definition = {
            "type": "minecraft:jigsaw",
            "biomes": biome_tag,
            "dimension_padding": dimension_padding,
            "liquid_settings": "ignore_waterlogging",
            "max_distance_from_center": max_distance_from_center,
            "pool_aliases": [],
            "size": size,
            "spawn_overrides": {},
            "start_height": height,
            "start_pool": start_pool,
            "step": step,
            "terrain_adaptation": terrain_adaptation,
            "use_expansion_hack": False,
        }
        path = self._resource_path("worldgen/structure", identifier, namespace=self.namespace) + ".json"
        if path in self.resources:
            raise ValueError(f"Duplicate worldgen structure: {identifier}")
        self._put_json(path, definition, references=[start_pool, biome_tag])
        self.worldgen_structures.add(identifier)

    def add_random_spread_set(
        self,
        identifier: str,
        *,
        structure: str,
        spacing: int,
        separation: int,
        salt: int,
        biome_tag: str,
        exclusion_structure: str,
        exclusion_chunk_radius: int,
    ) -> None:
        namespace, _ = _resource_id(identifier, allow_external=False)
        if namespace != self.namespace:
            raise ValueError(f"Structure set {identifier!r} must use the {self.namespace} namespace")
        _resource_id(structure)
        _resource_id(exclusion_structure)
        if spacing <= 0 or separation < 0 or separation >= spacing:
            raise ValueError("Structure set requires spacing > separation >= 0")
        if not 0 <= salt <= 2**31 - 1:
            raise ValueError("Structure set salt must be a non-negative 32-bit integer")
        if exclusion_chunk_radius <= 0:
            raise ValueError("exclusion_chunk_radius must be positive")
        if not biome_tag.startswith("#"):
            raise ValueError("biome_tag must be a biome tag reference beginning with #")
        _resource_id(biome_tag[1:])
        placement = {
            "type": "minecraft:random_spread",
            "salt": salt,
            "spacing": spacing,
            "separation": separation,
            "exclusion_zone": {"other_set": exclusion_structure, "chunk_count": exclusion_chunk_radius},
        }
        definition = {
            "placement": placement,
            "structures": [{"structure": structure, "weight": 1}],
        }
        path = self._resource_path("worldgen/structure_set", identifier, namespace=self.namespace) + ".json"
        if path in self.resources:
            raise ValueError(f"Duplicate structure set: {identifier}")
        self._put_json(path, definition, references=[structure, exclusion_structure, biome_tag])
        self.structure_sets.add(identifier)

    def _validate_references(self) -> None:
        template_documents = {}
        for path, content in self.resources.items():
            if path.startswith(f"data/{self.namespace}/structure/") and path.endswith(".nbt"):
                relative = Path(path).relative_to(f"data/{self.namespace}/structure").with_suffix("").as_posix()
                identifier = f"{self.namespace}:{relative}"
                template_documents[identifier] = read_nbt(content)["value"]
        pool_documents = {}
        for path in self.resources:
            if path.startswith(f"data/{self.namespace}/worldgen/template_pool/"):
                relative = Path(path).relative_to(f"data/{self.namespace}/worldgen/template_pool").with_suffix("").as_posix()
                pool_documents[f"{self.namespace}:{relative}"] = json.loads(self.resources[path])

        for path in self.resources:
            if path.startswith(f"data/{self.namespace}/worldgen/template_pool/"):
                pool = json.loads(self.resources[path])
                if pool["fallback"].startswith(f"{self.namespace}:") and pool["fallback"] not in pool_documents:
                    raise ValueError(f"Template pool {path} references missing fallback pool {pool['fallback']}")
                for element in pool["elements"]:
                    location = element["element"]["location"]
                    if location.startswith(f"{self.namespace}:") and location not in template_documents:
                        raise ValueError(f"Template pool {path} references missing structure template {location}")
            if path.startswith(f"data/{self.namespace}/worldgen/structure/"):
                structure = json.loads(self.resources[path])
                if structure["start_pool"] not in pool_documents:
                    raise ValueError(f"Worldgen structure {path} references missing start pool {structure['start_pool']}")
            if path.startswith(f"data/{self.namespace}/worldgen/structure_set/"):
                structure_set = json.loads(self.resources[path])
                for entry in structure_set["structures"]:
                    structure_id = entry["structure"]
                    if structure_id.startswith(f"{self.namespace}:") and structure_id not in self.worldgen_structures:
                        raise ValueError(f"Structure set {path} references missing worldgen structure {structure_id}")
                exclusion = structure_set["placement"].get("exclusion_zone")
                if exclusion:
                    other_set = exclusion["other_set"]
                    if other_set.startswith(f"{self.namespace}:") and other_set not in self.structure_sets:
                        raise ValueError(f"Structure set {path} references missing exclusion set {other_set}")

        for template_id, template in template_documents.items():
            palette = template["palette"]
            template_path = self._resource_path("structure", template_id, namespace=self.namespace) + ".nbt"
            references = set(self.references.get(template_path, []))
            for block in template["blocks"]:
                entity = block.get("nbt", {})
                if palette[block["state"]]["id"] != "minecraft:jigsaw" or entity.get("id") != "minecraft:jigsaw":
                    continue
                pool_id = entity.get("pool")
                target = entity.get("target")
                if isinstance(target, str) and target != "minecraft:empty":
                    references.add(f"connector_target:{target}")
                if not isinstance(pool_id, str):
                    raise ValueError(f"Jigsaw block in {template_id} is missing its pool reference")
                references.add(f"template_pool:{pool_id}")
                if pool_id == "minecraft:empty" or pool_id.startswith("minecraft:"):
                    continue
                if pool_id not in pool_documents:
                    raise ValueError(f"Jigsaw in {template_id} references missing template pool {pool_id}")
                provided_names = set()
                for element in pool_documents[pool_id]["elements"]:
                    location = element["element"]["location"]
                    target_template = template_documents.get(location)
                    if target_template is None:
                        continue
                    target_palette = target_template["palette"]
                    for target_block in target_template["blocks"]:
                        target_entity = target_block.get("nbt", {})
                        if (
                            target_palette[target_block["state"]]["id"] == "minecraft:jigsaw"
                            and target_entity.get("id") == "minecraft:jigsaw"
                        ):
                            provided_names.add(target_entity.get("name"))
                if target not in provided_names:
                    raise ValueError(
                        f"Jigsaw in {template_id} targets {target!r}, but pool {pool_id} has no matching connector name"
                    )
            self.references[template_path] = sorted(references)

    def write(self) -> Path:
        """Write all pack files and a manifest with checksums and resource references."""
        self._validate_references()
        resources = dict(self.resources)
        pack_meta = {
            "pack": {
                "description": "MoreMinecrafts Forgotten Underground Kingdom — SG-01 prototype",
                "min_format": self.pack_format,
                "max_format": self.pack_format,
            }
        }
        resources["pack.mcmeta"] = (json.dumps(pack_meta, indent=2, sort_keys=True) + "\n").encode("utf-8")
        entries = []
        for path, content in sorted(resources.items()):
            role = "data_pack_metadata" if path == "pack.mcmeta" else _resource_role(path)
            entries.append(
                {
                    "path": path,
                    "role": role,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size_bytes": len(content),
                    "references": self.references.get(path, []),
                }
            )
        manifest = {
            "minecraft_version": MINECRAFT_VERSION,
            "world_version": WORLD_VERSION,
            "data_pack_format": self.pack_format,
            "namespace": self.namespace,
            "resources": [*entries, {"path": "manifest.json", "role": "resource_manifest", "references": []}],
        }
        resources["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        for relative_path, content in sorted(resources.items()):
            destination = self.root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        return self.root / "manifest.json"


def _resource_role(path: str) -> str:
    if "/worldgen/structure_set/" in path:
        return "structure_set"
    if "/template_pool/" in path:
        return "template_pool"
    if "/worldgen/structure/" in path:
        return "worldgen_structure"
    if "/structure/" in path:
        return "structure_template_nbt"
    return "resource"
