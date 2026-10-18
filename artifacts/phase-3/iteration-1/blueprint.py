# Ruined Watchtower — iteration 1
# Coordinate convention: x east, y up, z south; the entrance faces +z.

# Broad stone footing and continuous lower-room floor.
fill(1, 0, 1, 9, 0, 9, "stone_bricks")
for x in range(0, 11):
    for z in range(0, 11):
        if x == 0 or x == 10 or z == 0 or z == 10:
            if (x + z) % 3 == 0:
                set_block(x, 0, z, "cobblestone")
            else:
                set_block(x, 0, z, "stone_bricks")

# Lower masonry shaft. The south opening remains three blocks high and three wide.
for y in range(1, 8):
    for x in range(1, 10):
        for z in range(1, 10):
            if not (x == 1 or x == 9 or z == 1 or z == 9):
                continue
            if z == 9 and (x == 4 or x == 5 or x == 6) and y <= 3:
                continue
            if x == 1 and z == 4 and (y == 4 or y == 5):
                continue
            if x == 9 and z == 6 and (y == 4 or y == 5):
                continue
            if z == 1 and x == 5 and (y == 4 or y == 5):
                continue
            material = "stone_bricks"
            if y <= 2 and (x + z) % 5 == 0:
                material = "cobblestone"
            elif y >= 4 and (x * 3 + z * 2 + y) % 13 == 0:
                material = "mossy_stone_bricks"
            elif y >= 5 and (x * 2 + z + y) % 17 == 0:
                material = "cracked_stone_bricks"
            set_block(x, y, z, material)

# Corner piers and a worn but readable entrance arch.
for y in range(1, 5):
    set_block(0, y, 1, "cobblestone")
    set_block(1, y, 0, "stone_bricks")
    set_block(10, y, 1, "stone_bricks")
    set_block(9, y, 0, "cobblestone")
    set_block(0, y, 9, "stone_bricks")
    set_block(1, y, 10, "cobblestone")
    set_block(10, y, 9, "cobblestone")
    set_block(9, y, 10, "stone_bricks")
for x in range(3, 8):
    set_block(x, 4, 9, "stone_bricks")
    set_block(x, 5, 9, "cracked_stone_bricks" if x == 6 else "stone_bricks")
fill(4, 0, 10, 6, 0, 10, "cobblestone")

# Four interior piers carry the upper deck without filling the room.
for y in range(1, 7):
    set_block(2, y, 2, "stone_bricks")
    set_block(8, y, 2, "stone_bricks")
    set_block(2, y, 8, "cobblestone")
    set_block(8, y, 8, "stone_bricks")

# Upper floor with a narrow stairwell slot.
for x in range(2, 9):
    for z in range(2, 9):
        if z == 5 and x <= 7:
            continue
        set_block(x, 7, z, "stone_bricks")

# Continuous east-rising stair flight from the ground floor to the upper landing.
for step in range(0, 6):
    set_block(2 + step, 1 + step, 5, "stone_brick_stairs[facing=east,half=bottom,shape=straight]")
    set_block(2 + step, 8, 4, "stone_brick_wall")
    set_block(2 + step, 8, 6, "stone_brick_wall")

# A one-sided lookout ledge, carried by stone brackets and tied into the shaft.
for z in range(3, 8):
    if z == 3 or z == 5 or z == 7:
        set_block(10, 7, z, "stone_brick_wall")
    set_block(10, 8, z, "stone_bricks")

# Smaller upper watch room, with a south-facing doorway and narrow slit windows.
for y in range(8, 14):
    for x in range(2, 9):
        for z in range(2, 9):
            if not (x == 2 or x == 8 or z == 2 or z == 8):
                continue
            if z == 8 and (x == 4 or x == 5 or x == 6) and y <= 11:
                continue
            if z == 2 and x == 5 and (y == 10 or y == 11):
                continue
            if x == 2 and z == 4 and (y == 10 or y == 11):
                continue
            if x == 8 and z == 6 and (y == 10 or y == 11):
                continue
            # The north-west corner has lost two upper stones.
            if x == 2 and z == 2 and y >= 12:
                continue
            material = "stone_bricks"
            if y >= 11 and (x + z + y) % 9 == 0:
                material = "mossy_stone_bricks"
            elif y >= 12 and (x * 2 + z + y) % 7 == 0:
                material = "cracked_stone_bricks"
            set_block(x, y, z, material)

# Stone lintels keep both openings legible; the north-west break exposes rubble.
for x in range(3, 8):
    set_block(x, 12, 8, "stone_bricks")
for z in range(2, 5):
    set_block(1, 1, z, "cobblestone")
set_block(0, 1, 2, "cobblestone")
set_block(0, 2, 2, "stone_bricks")

# Spruce gable cap, intentionally missing part of the west/south eave.
for z in range(1, 10):
    if z < 7:
        set_block(2, 14, z, "spruce_stairs[facing=east,half=bottom,shape=straight]")
    if z < 8:
        set_block(3, 15, z, "spruce_stairs[facing=east,half=bottom,shape=straight]")
    set_block(4, 16, z, "spruce_stairs[facing=east,half=bottom,shape=straight]")
    set_block(5, 16, z, "spruce_planks")
    set_block(6, 16, z, "spruce_stairs[facing=west,half=bottom,shape=straight]")
    set_block(7, 15, z, "spruce_stairs[facing=west,half=bottom,shape=straight]")
    if z < 9:
        set_block(8, 14, z, "spruce_stairs[facing=west,half=bottom,shape=straight]")

# Exposed ridge and rafters remain attached to the watch-room walls.
for z in range(2, 9):
    set_block(5, 15, z, "spruce_log[axis=z]")
    set_block(4, 14, z, "spruce_log[axis=z]")
    set_block(6, 14, z, "spruce_log[axis=z]")
