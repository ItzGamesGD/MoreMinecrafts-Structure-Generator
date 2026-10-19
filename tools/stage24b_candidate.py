"""Lossless, source-derived NBT candidate editor for Stage 24-B."""
from __future__ import annotations

from collections import Counter
from collections import defaultdict
from pathlib import Path

import nbtlib
from nbtlib import tag

from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid

from tools.stage24b_source import block_key


class ProtectedBlockError(ValueError):
    """An edit tried to alter a source block locked by the approved spec."""


def state_tag(key: str):
    if "[" not in key:
        return tag.Compound({"Name": tag.String(key if ":" in key else f"minecraft:{key}")})
    base, suffix = key.split("[", 1)
    props = dict(piece.split("=", 1) for piece in suffix.rstrip("]").split(","))
    return tag.Compound({
        "Name": tag.String(base if ":" in base else f"minecraft:{base}"),
        "Properties": tag.Compound({key: tag.String(value) for key, value in props.items()}),
    })


def block_id(key: str) -> str:
    return key.split("[", 1)[0]


class Candidate:
    """Editable structure palette/block table with explicit protected-source invariants."""

    def __init__(self, module: str, root, source_url: str = "", source_sha: str = ""):
        self.module = module
        self.root = root
        self.source_url = source_url
        self.source_sha = source_sha
        self.original_size = tuple(int(value) for value in root["size"])
        self.size = self.original_size
        self.palette = root["palette"]
        self.indices = {block_key(state): index for index, state in enumerate(self.palette)}
        self.positions = {tuple(int(v) for v in item["pos"]): item for item in root["blocks"]}
        self.original_positions = set(self.positions)
        self.original_block_count = len(self.positions)
        self.original_states = {pos: self._snapshot(item) for pos, item in self.positions.items()}
        self.protected = self._protected_coordinates()
        self.protected_snapshot = {pos: self.original_states[pos] for pos in self.protected}
        self.connector_snapshot = self.current_connector_snapshot()
        self.operations: Counter[str] = Counter()
        self.changed_original: dict[tuple[int, int, int], dict] = {}
        self.added_positions: set[tuple[int, int, int]] = set()
        self.change_reasons: dict[tuple[int, int, int], set[str]] = defaultdict(set)
        self.features: dict[str, object] = {}
        self.entry_inside = None

    def current_connector_snapshot(self) -> list[dict]:
        result = []
        for pos in sorted(self.original_positions):
            item = self.positions.get(pos)
            if item is None or block_id(block_key(self.palette[int(item["state"])])) != "minecraft:jigsaw":
                continue
            result.append({"pos": pos, "state": block_key(self.palette[int(item["state"])]),
                           "nbt": str(item.get("nbt", ""))})
        return result

    def snapshot_protected_from_source(self) -> dict:
        return dict(self.protected_snapshot)

    @staticmethod
    def _snapshot(item) -> dict:
        return {
            "state": int(item["state"]),
            "nbt": str(item["nbt"]) if "nbt" in item else None,
        }

    def _block_key_at(self, pos: tuple[int, int, int]) -> str:
        item = self.positions.get(pos)
        if item is None:
            return "minecraft:air"
        return block_key(self.palette[int(item["state"])])

    def _protected_coordinates(self) -> set[tuple[int, int, int]]:
        protected = set()
        sauna_water = []
        for pos, item in self.positions.items():
            key = self._block_key_at(pos)
            block = block_id(key)
            if block == "minecraft:jigsaw":
                protected.add(pos)
            if self.module == "sauna_1" and (
                block in {"minecraft:water", "minecraft:chest"}
                or "_stairs" in block or "_slab" in block
            ):
                protected.add(pos)
            if self.module == "sauna_1" and block == "minecraft:water":
                sauna_water.append(pos)
            if self.module == "medium_pillar_1" and block == "minecraft:skeleton_skull":
                protected.add(pos)
        if self.module == "sauna_1":
            for x, y, z in sauna_water:
                for rim in ((x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1)):
                    if rim in self.positions:
                        protected.add(rim)
        return protected

    def get_block(self, pos) -> str:
        return self._block_key_at(tuple(pos))

    def set_dimensions(self, size) -> None:
        target = tuple(int(v) for v in size)
        if len(target) != 3 or any(v <= 0 for v in target):
            raise ValueError(f"Invalid candidate dimensions: {target}")
        if target != self.original_size:
            approved = self.module == "medium_ruin_2" and target == (16, 8, 11)
            if not approved:
                raise ValueError(f"Unapproved size change for {self.module}: {self.original_size} -> {target}")
        for pos in self.original_positions:
            if any(coord < 0 or coord >= target[i] for i, coord in enumerate(pos)):
                raise ValueError(f"Dimension change excludes source position {pos}")
        self.size = target

    def set_block(self, x: int, y: int, z: int, key: str, *, replace: bool = False, reason: str):
        pos = (int(x), int(y), int(z))
        if any(coord < 0 or coord >= self.size[i] for i, coord in enumerate(pos)):
            raise ValueError(f"{self.module} block {pos} outside candidate dimensions {self.size}")
        canonical = block_key(state_tag(key))
        current = self._block_key_at(pos)
        if pos in self.protected and current != canonical:
            raise ProtectedBlockError(f"{self.module} protected source block at {pos}: {current} -> {canonical}")
        if current == canonical:
            return False
        exists = pos in self.positions
        if exists and not replace:
            raise ValueError(f"{self.module} replacing source/candidate block at {pos} requires replace=True ({current} -> {canonical})")
        if canonical not in self.indices:
            self.indices[canonical] = len(self.palette)
            self.palette.append(state_tag(canonical))
        index = self.indices[canonical]
        if exists:
            original = self.original_states.get(pos)
            if original is not None and pos not in self.changed_original:
                self.changed_original[pos] = {"before": original, "after": canonical, "reason": reason}
            self.operations["replaced"] += 1
            item = self.positions[pos]
            item["state"] = tag.Int(index)
            item.pop("nbt", None)
        else:
            item = tag.Compound({"pos": tag.List[tag.Int](pos), "state": tag.Int(index)})
            self.positions[pos] = item
            self.added_positions.add(pos)
            self.operations["added"] += 1
        if canonical == "minecraft:air":
            self.operations["carved"] += 1
        self.operations[reason] += 1
        self.change_reasons[pos].add(reason)
        return True

    def carve(self, x: int, y: int, z: int, *, reason: str):
        return self.set_block(x, y, z, "minecraft:air", replace=True, reason=reason)

    def verify_protected(self) -> None:
        for pos, expected in self.protected_snapshot.items():
            item = self.positions.get(pos)
            if item is None:
                raise AssertionError(f"{self.module} removed protected source block at {pos}")
            state = block_key(self.palette[int(item["state"])])
            actual = {"state": int(item["state"]), "nbt": str(item["nbt"]) if "nbt" in item else None}
            expected_index = self.original_states[pos]["state"]
            expected_state = block_key(self.root["palette"][int(expected_index)])
            if actual["state"] != expected_index or state != expected_state or actual["nbt"] != expected["nbt"]:
                raise AssertionError(f"{self.module} protected source block changed at {pos}: {actual} != {expected}")
        for pos, item in self.positions.items():
            if any(coord < 0 or coord >= self.size[i] for i, coord in enumerate(pos)):
                raise AssertionError(f"{self.module} contains out-of-bounds block {pos} for {self.size}")

    def save_native(self, path: Path) -> None:
        self.root["size"] = tag.List[tag.Int](self.size)
        self.root["palette"] = tag.List[tag.Compound](self.palette)
        ordered = [self.positions[pos] for pos in sorted(self.positions, key=lambda p: (p[1], p[2], p[0]))]
        self.root["blocks"] = tag.List[tag.Compound](ordered)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.root.save(path, gzipped=True)

    @classmethod
    def load(cls, path: Path, module: str = "large_ruin_1"):
        return cls(module, nbtlib.load(path))

    def to_grid(self) -> VoxelGrid:
        grid = VoxelGrid()
        for pos, item in self.positions.items():
            key = block_key(self.palette[int(item["state"])])
            if block_id(key) in {"minecraft:air", "minecraft:jigsaw", "minecraft:structure_void"}:
                continue
            grid.set(*pos, get_block(key).index)
        return grid

    def state_counts(self) -> Counter:
        return Counter(self._block_key_at(pos) for pos in self.positions)

    def report_changes(self) -> list[dict]:
        return [{"pos": list(pos), **detail} for pos, detail in sorted(self.changed_original.items())]

    def block_change_manifest(self) -> list[dict]:
        changes = []
        for pos in sorted(self.original_positions | set(self.positions)):
            if pos in self.original_states:
                before = block_key(self.root["palette"][self.original_states[pos]["state"]])
            else:
                before = "minecraft:air"
            after = self._block_key_at(pos)
            if before == after:
                continue
            action = "add" if pos not in self.original_positions else ("remove" if after == "minecraft:air" else "replace")
            changes.append({"pos_xyz": list(pos), "action": action, "original_state": before,
                            "restored_state": after, "reasons": sorted(self.change_reasons.get(pos, ()))})
        return changes
