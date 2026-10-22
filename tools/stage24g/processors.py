"""Exact re-implementation of the Minecraft 26.1.2 processors applied to the Ancient City `structures` pool.

Source (decompiled from server-26.1.2.jar, see docs in stage-24g/INVESTIGATION.md):
  * BlockRotProcessor.processBlock: random = settings.getRandom(pos); SinglePoolElement never sets a random, so
    getRandom(pos) = RandomSource.create(Mth.getSeed(pos)) -> a fresh LegacyRandomSource per *world* position.
    The block is dropped (null -> nothing is written, the pre-existing world block stays) when the ORIGINAL template
    state is in #ancient_city_replaceable and nextFloat() > integrity (0.95).
  * RuleProcessor.processBlock: random = RandomSource.create(Mth.getSeed(pos)) (again fresh per world position);
    rules are tested in order, RandomBlockMatchTest consumes a float only when the block matches.
  * ProtectedBlockProcessor: drops the template block when the block already in the world is in
    #features_cannot_replace.
"""
from __future__ import annotations

import struct

MASK48 = (1 << 48) - 1


def f32(v: float) -> float:
    return struct.unpack("f", struct.pack("f", v))[0]


def _i32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def _i64(v: int) -> int:
    v &= (1 << 64) - 1
    return v - (1 << 64) if v & (1 << 63) else v


def mth_seed(x: int, y: int, z: int) -> int:
    """Mth.getSeed(int,int,int): `x * 3129871` is an int multiply (32-bit overflow) before widening."""
    seed = _i64(_i32(x * 3129871) ^ _i64(z * 116129781) ^ y)
    seed = _i64(seed * seed * 42317861 + seed * 11)
    return seed >> 16


class LegacyRandom:
    def __init__(self, seed: int):
        self.seed = (seed ^ 25214903917) & MASK48

    def next(self, bits: int) -> int:
        self.seed = (self.seed * 25214903917 + 11) & MASK48
        return self.seed >> (48 - bits)

    def next_float(self) -> float:
        return self.next(24) * 5.9604645e-08  # exact: next(24) / 2**24


ANCIENT_CITY_REPLACEABLE = {f"minecraft:{b}" for b in (
    "deepslate", "deepslate_bricks", "deepslate_tiles", "deepslate_brick_slab", "deepslate_tile_slab",
    "deepslate_brick_stairs", "deepslate_tile_wall", "deepslate_brick_wall", "cobbled_deepslate",
    "cracked_deepslate_bricks", "cracked_deepslate_tiles", "gray_wool")}
FEATURES_CANNOT_REPLACE = {f"minecraft:{b}" for b in (
    "bedrock", "spawner", "chest", "end_portal_frame", "reinforced_deepslate", "trial_spawner", "vault")}
INTEGRITY = f32(0.95)
# minecraft:ancient_city_generic_degradation rule list (input block, probability, output)
GENERIC_RULES = [("minecraft:deepslate_bricks", f32(0.3), "minecraft:cracked_deepslate_bricks"),
                 ("minecraft:deepslate_tiles", f32(0.3), "minecraft:cracked_deepslate_tiles"),
                 ("minecraft:soul_lantern", f32(0.05), "minecraft:air")]


def name(state: str) -> str:
    return state.split("[")[0]


def rot_removed(state: str, world_pos) -> bool:
    """True when block_rot (integrity 0.95, #ancient_city_replaceable) drops this template block."""
    if name(state) not in ANCIENT_CITY_REPLACEABLE:
        return False
    return not (LegacyRandom(mth_seed(*world_pos)).next_float() <= INTEGRITY)


def rule_output(state: str, world_pos, rules=GENERIC_RULES):
    """Output state of the rule processor, or None when no rule fires (state kept)."""
    rnd = LegacyRandom(mth_seed(*world_pos))
    n = name(state)
    for block, p, out in rules:
        if n == block and rnd.next_float() < p:
            return out
    return None


def process(state: str, world_pos, world_block_before: str | None = None, block_rot=True):
    """Full generic-degradation chain for one (already jigsaw-replaced) template block.

    Returns ("dropped_rot" | "dropped_protected" | "placed", placed_state).  `state` must be the ORIGINAL template
    state for block_rot (jigsaws are not in the tag, so their final_state never rots)."""
    if block_rot and rot_removed(state, world_pos):
        return "dropped_rot", None
    out = rule_output(state, world_pos) or state
    if world_block_before is not None and name(world_block_before) in FEATURES_CANNOT_REPLACE:
        return "dropped_protected", None
    return "placed", out
