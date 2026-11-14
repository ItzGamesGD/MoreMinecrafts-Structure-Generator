"""Test-terrain sites for the wall footing (Q89) - shared by checks.py and capture.py.

The flat test world is solid only up to y=-61, so each site is a raised earth mound: the wall's grade (template y=0)
is GT = -55 and the terrain top of every column is GT + d(x, z) with d in -5..+2 (dirt, grass on top). The wall is
placed `strict` at GT (air=omit, so terrain inside the box where the template has no block is kept), then the
Q89 placement step fills every footprint column whose ground is below grade with the column's own footing block, from
the ground surface up to y=-1 below the template. Nothing outside the 86/31 x 5 footprint is touched. This is a
TEST of the footing rule on synthetic slopes, not natural worldgen.
"""

import math

G = -61
GT = G + 6


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


SITES = {
    # wall along x through a valley up to 5 blocks deep (and back up): longitudinal slope on both sides
    "S1_long_valley": dict(module="MW86", origin=(0, 300),
                           d=lambda x, z: -round(5 * math.sin(math.pi * _clamp(x + 2, 0, 89) / 89) ** 1.3)),
    # ground falling away to the outside: inside at grade, exterior plinth 3 below, 4 beyond it
    "S2_cross_slope": dict(module="MW31", origin=(0, 370),
                           d=lambda x, z: _clamp(round(min(0.0, (z - 4) * 0.75) - (0.6 + 0.6 * math.sin(x / 4.0))
                                                       * (z <= 2)), -5, 0)),
    # undulating ground partly ABOVE grade (footing buried) and partly below it
    "S3_undulating": dict(module="MW31", origin=(70, 370),
                          d=lambda x, z: _clamp(round(2.2 * math.sin(x / 3.2) - 0.8 + 0.7 * math.cos(z * 0.9 + x / 5)), -4, 2)),
}
MARGIN_X, Z0, Z1 = 3, -4, 8  # terrain area around the footprint (local frame)


def build_terrain(server, site, L, mx=MARGIN_X, z0=Z0, z1=Z1, skirt=0):
    """Mound of dirt with a grass top. `skirt` > 0 (screenshots only) adds a ramp falling 1 per block from the edge of
    the area down to the flat world, so the site does not end in a cliff in the pictures."""
    ox, oz = site["origin"]
    for x in range(-mx - skirt, L + mx + skirt):
        for z in range(z0 - skirt, z1 + 1 + skirt):
            cx, cz = max(-mx, min(L + mx - 1, x)), max(z0, min(z1, z))
            t = GT + site["d"](cx, cz) - max(abs(x - cx), abs(z - cz))
            if t <= G:
                continue
            if t - 1 > G:
                server.cmd(f"fill {ox + x} {G + 1} {oz + z} {ox + x} {t - 1} {oz + z} minecraft:dirt")
            server.cmd(f"setblock {ox + x} {t} {oz + z} minecraft:grass_block")
            server.cmd(f"fill {ox + x} {t + 1} {oz + z} {ox + x} {GT + 14} {oz + z} minecraft:air")


def _noise(x, z, n, salt=0):
    h = (x * 73856093) ^ (z * 19349663) ^ (salt * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return (h ^ (h >> 16)) % n


def fill_block(x, y, z):
    """Below-grade footing masonry (y < 0 relative to grade): rough stone in staggered horizontal patches - coursed,
    not one material per column (which reads as vertical stripes)."""
    patch = _noise((x + 3 * (y // 2)) // 3, y // 2, 6, 77 + z)
    r = _noise(x, y, 4, 13 + z) != 0
    return "minecraft:" + {0: ("cobblestone", "mossy_cobblestone"), 1: ("cobblestone", "mossy_cobblestone"),
                           2: ("andesite", "stone"), 3: ("stone_bricks", "mossy_stone_bricks"),
                           4: ("cobblestone", "andesite"), 5: ("stone_bricks", "cracked_stone_bricks")}[patch][0 if r else 1]


def footing_fill(server, site, template, L):
    """Q89 step: under every footprint column whose ground is below grade, replace the ground surface block and fill
    up to the template's footing course with masonry (fill_block). `template` is kept for the call signature."""
    ox, oz = site["origin"]
    cols = []
    for x in range(L):
        for z in range(5):
            t = GT + site["d"](x, z)
            if t >= GT:
                continue
            for y in range(t, GT):
                server.cmd(f"setblock {ox + x} {y} {oz + z} {fill_block(x, y - GT, z)}")
            cols.append((x, z, GT - t))
    return cols
