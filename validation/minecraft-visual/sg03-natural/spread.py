"""Offline reimplementation of vanilla ``random_spread`` placement (LegacyRandomSource, linear spread).

Used only to enumerate *candidate* structure-start chunks deterministically. Whether a candidate
actually becomes a structure is decided by Minecraft itself and read back from saved chunks.
"""
from __future__ import annotations

MASK = (1 << 48) - 1
MULT = 0x5DEECE66D


def _wrap64(value: int) -> int:
    value &= (1 << 64) - 1
    return value - (1 << 64) if value >= (1 << 63) else value


class JavaRandom:
    def __init__(self, seed: int) -> None:
        self.seed = (seed ^ MULT) & MASK

    def _next(self, bits: int) -> int:
        self.seed = (self.seed * MULT + 0xB) & MASK
        value = self.seed >> (48 - bits)
        return value - (1 << bits) if value >= (1 << (bits - 1)) and bits == 32 else value

    def next_int(self, bound: int) -> int:
        if bound & (bound - 1) == 0:
            return (bound * self._next(31)) >> 31
        while True:
            bits = self._next(31)
            val = bits % bound
            if bits - val + (bound - 1) < (1 << 31):
                return val


def candidate_chunk(world_seed: int, region_x: int, region_z: int, spacing: int, separation: int, salt: int) -> tuple[int, int]:
    rng = JavaRandom(_wrap64(region_x * 341873128712 + region_z * 132897987541 + world_seed + salt))
    span = spacing - separation
    return region_x * spacing + rng.next_int(span), region_z * spacing + rng.next_int(span)


SG01 = dict(spacing=34, separation=12, salt=20261017)
TRIAL_CHAMBERS = dict(spacing=34, separation=12, salt=94251327)


def candidates_in_ring(world_seed: int, placement: dict, radius_regions: int) -> list[tuple[int, int]]:
    out = []
    for rx in range(-radius_regions, radius_regions + 1):
        for rz in range(-radius_regions, radius_regions + 1):
            out.append(candidate_chunk(world_seed, rx, rz, **placement))
    return out


if __name__ == "__main__":
    # Seed 173 natural site proven in PR #5 evidence: /locate reported block [5184, ~, 4944].
    cx, cz = candidate_chunk(173, 5184 // 16 // 34, 4944 // 16 // 34, **SG01)
    print("seed173 region(9,9) candidate chunk", (cx, cz), "block", (cx * 16, cz * 16))


def exclusion_suppressed(world_seed: int, chunk: tuple[int, int], radius: int = 12) -> bool:
    """True when a trial_chambers *candidate* chunk lies within ``radius`` chunks (Chebyshev) of an SG-01 candidate.

    Vanilla evaluates ExclusionZone against the other set's placement positions, not against structures that
    actually generated, so this is exactly predictable offline.
    """
    region_x, region_z = chunk[0] // 34, chunk[1] // 34
    for rx in range(region_x - 2, region_x + 3):
        for rz in range(region_z - 2, region_z + 3):
            tx, tz = candidate_chunk(world_seed, rx, rz, **TRIAL_CHAMBERS)
            if max(abs(tx - chunk[0]), abs(tz - chunk[1])) <= radius:
                return True
    return False
