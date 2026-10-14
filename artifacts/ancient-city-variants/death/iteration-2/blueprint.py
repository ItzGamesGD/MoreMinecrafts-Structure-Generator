# Ancient City multi-district composition (representative scale, not vanilla template).
# x-east / y-up / z-south. Four distinct precincts linked by a cross-avenue.
THEME = "death"
ITERATION = 2
BASE = "deepslate_bricks"
TRIM = "polished_deepslate"
DAMAGE = "cracked_deepslate_bricks"
SCULK = "sculk"
# Continuous city foundation and civic avenues.
fill(0, 0, 0, 48, 0, 48, "deepslate_tiles")
fill(22, 1, 0, 26, 1, 48, TRIM)
fill(0, 1, 22, 48, 1, 26, TRIM)
# Four walled precincts, varied footprints and heights.
precincts = [(2, 2, 18, 18, 7), (31, 3, 46, 18, 10),
             (3, 31, 18, 46, 9), (31, 31, 46, 46, 6)]
for i, (x1, z1, x2, z2, h) in enumerate(precincts):
    fill(x1, 1, z1, x2, 1, z2, TRIM)
    for y in range(2, h + 2):
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                if x != x1 and x != x2 and z != z1 and z != z2:
                    continue
                if (x == x1 or x == x2) and z == (z1 + z2) // 2 and y <= 4:
                    continue
                if (z == z1 or z == z2) and x == (x1 + x2) // 2 and y <= 4:
                    continue
                if THEME == "death" and (x * 7 + z * 11 + y * 5 + i) % 17 < 3 and y >= 5:
                    continue
                block = BASE
                if THEME == "death" and (x + z + y + i) % 6 == 0:
                    block = DAMAGE
                if THEME == "nether" and (abs(x - 24) + abs(z - 24) < 22):
                    if (x * 3 + z * 7 + y) % 5 == 0:
                        block = "blackstone"
                if THEME == "living" and (x + z) % 5 == 0:
                    block = "polished_deepslate"
                set_block(x, y, z, block)
    # Primary upright corner piers.
    for x in (x1, x2):
        for z in (z1, z2):
            for y in range(2, h + 4):
                if THEME == "death" and (i + x + z) % 4 == 0 and y > h - 2:
                    continue
                set_block(x, y, z, "reinforced_deepslate" if THEME != "living" else TRIM)
    if THEME == "living":
        fill(x1 + 1, h + 2, z1 + 1, x2 - 1, h + 2, z2 - 1, "deepslate_tile_slab[type=bottom]")
        for x in range(x1 + 2, x2 - 1, 4):
            set_block(x, h + 3, z1 + 1, "soul_lantern")
    elif THEME == "death":
        for x in range(x1 + 2, x2 - 1, 3):
            set_block(x, 2, z1 + 2, "bone_block")
            set_block(x, 3, z1 + 2, "sculk_vein")
    else:
        for x in range(x1 + 2, x2 - 1, 4):
            set_block(x, h + 2, z1, "polished_blackstone_bricks")
# Architectural center: Warden-shaped silhouette/podium, not actual vanilla NBT.
fill(19, 1, 19, 29, 2, 29, "reinforced_deepslate")
for x in (19, 29):
    for z in (19, 29):
        fill(x, 2, z, x, 10, z, "reinforced_deepslate")
fill(20, 9, 19, 28, 9, 19, "deepslate_tiles")
fill(20, 9, 29, 28, 9, 29, "deepslate_tiles")
for z in (21, 27):
    fill(22, 2, z, 26, 8, z, "chiseled_deepslate")
fill(22, 2, 23, 26, 8, 25, "air")
if THEME == "death":
    # Central epicenter: black sculk, remains, shattered columns and sinkholes.
    for x in range(1, 48):
        for z in range(1, 48):
            d = abs(x - 24) + abs(z - 24)
            if (x * 17 + z * 13) % 11 < 4:
                set_block(x, 1, z, SCULK)
            if d < 18 and (x * 7 + z * 3) % 17 == 0:
                set_block(x, 2, z, "sculk_catalyst")
            if (x * 13 + z * 5) % 79 == 0:
                set_block(x, 2, z, "bone_block")
    for x in range(6, 45, 8):
        for z in range(6, 45, 9):
            if (x + z) % 3 == 0:
                fill(x, 1, z, x + 1, 1, z + 2, "sculk")
                set_block(x, 2, z, "soul_sand")
    if ITERATION >= 2:
        # Revision: legible destruction across multiple districts, not just moss-like recolor.
        for x in range(5, 44, 7):
            for z in range(5, 44, 8):
                if (x + z) % 4 == 0:
                    fill(x, 2, z, x, 4, z, "bone_block")
                    set_block(x, 5, z, "skeleton_skull")
                else:
                    fill(x, 1, z, x + 2, 1, z + 1, "sculk")
elif THEME == "nether":
    # Corruption is a radial gradient from the central landmark.
    for x in range(1, 48):
        for z in range(1, 48):
            d = abs(x - 24) + abs(z - 24)
            if d < 34 and (x * 11 + z * 17) % 38 < 34 - d:
                set_block(x, 1, z, "blackstone" if d > 12 else "crimson_nylium")
            if d < 21 and (x * 7 + z * 3) % 23 == 0:
                set_block(x, 2, z, "shroomlight")
    # Portal visual mockup in rectangular interior of central Warden-like structure.
    fill(21, 2, 24, 27, 9, 24, "obsidian")
    fill(22, 3, 24, 26, 8, 24, "purple_stained_glass")
    if ITERATION >= 2:
        for x in range(3, 46, 6):
            for z in range(3, 46, 6):
                d = abs(x - 24) + abs(z - 24)
                if d < 23 and (x + z) % 3 == 0:
                    set_block(x, 2, z, "nether_wart_block")
                    set_block(x, 3, z, "crimson_fence")
elif THEME == "living":
    # Occupied original city: connected streets, courtyards, light and maintained roofs.
    for x in range(3, 47, 5):
        for z in (24, 25):
            set_block(x, 2, z, "soul_lantern")
    for z in range(3, 47, 5):
        for x in (24, 25):
            set_block(x, 2, z, "soul_lantern")
    for x in range(4, 47, 6):
        for z in range(4, 47, 6):
            if (x + z) % 3 == 0:
                fill(x, 1, z, x + 2, 1, z + 2, "polished_deepslate")
                set_block(x + 1, 2, z + 1, "cyan_carpet")
    if ITERATION >= 2:
        # Revision: coherent inhabited streetscape with market/civic pavilions.
        for x in (7, 36):
            for z in (24,):
                fill(x, 2, z, x + 4, 2, z + 2, "dark_oak_planks")
                for px in (x, x + 4):
                    for pz in (z, z + 2):
                        fill(px, 3, pz, px, 5, pz, "dark_oak_fence")
                fill(x, 6, z, x + 4, 6, z + 2, "cyan_wool")
