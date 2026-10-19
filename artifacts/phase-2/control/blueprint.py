# Marker Tower: deterministic 7 x 7 x 12 control structure.
floor(0, 0, 6, 6, 0, "stone")
walls(0, 0, 6, 6, 1, 9, "cobblestone")

# A centered, unmistakable three-wide doorway in the south (z=0) wall.
clear(2, 1, 0, 4, 3, 0)

# Four contrasting corner pillars, one block above the wall line.
for x in (0, 6):
    for z in (0, 6):
        fill(x, 1, z, x, 10, z, "stone_bricks")

# Bright cap and corner finials make the top easy to identify in every view.
floor(0, 0, 6, 6, 10, "red_wool")
floor(1, 1, 5, 5, 11, "red_wool")
for x in (0, 6):
    for z in (0, 6):
        set_block(x, 11, z, "stone_bricks")
