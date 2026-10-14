# tall_ruin_4: user-approved Ancient City peak-era restoration concept.
# Independent Ancient City peak-era building concept.
# This is a NEW interpretation, not an edited/verified vanilla NBT.
# Entrance is centered on the SOUTH face (z=0); x east, y up.
# Only the selected structure is built; no city/worldgen/other modules.
def stone_floor(w, d):
    floor(0, 0, w - 1, d - 1, 0, "polished_deepslate")
    for x in range(w):
        for z in range(d):
            if x == 0 or z == 0 or x == w - 1 or z == d - 1:
                set_block(x, 0, z, "deepslate_tiles")

def doorway(cx):
    clear(cx, 1, 0, cx, 2, 0)
    set_block(cx, 1, 0, "dark_oak_door[facing=south,half=lower,hinge=left,open=false]")
    set_block(cx, 2, 0, "dark_oak_door[facing=south,half=upper,hinge=left,open=false]")
    set_block(cx, 3, 0, "chiseled_deepslate")

def window(x, y, z):
    set_block(x, y, z, "light_blue_stained_glass_pane")

def house_shell(w, d, h):
    stone_floor(w, d)
    walls(0, 0, w - 1, d - 1, 1, h, "deepslate_bricks")
    for y in range(1, h + 1):
        for x, z in ((0, 0), (w - 1, 0), (0, d - 1), (w - 1, d - 1)):
            set_block(x, y, z, "polished_basalt[axis=y]")
    for x in range(1, w - 1, 3):
        set_block(x, h, 0, "deepslate_tiles")
        set_block(x, h, d - 1, "deepslate_tiles")
    doorway(w // 2)
    for x in (2, w - 3):
        if x > 0 and x < w - 1 and x != w // 2:
            window(x, 2, 0)
            window(x, 2, d - 1)
    for z in (2, d - 3):
        if z > 0 and z < d - 1:
            window(0, 2, z)
            window(w - 1, 2, z)

def pitched_roof(w, d, eave):
    # Complete two-slope stone-tile roof with extended eaves and a ridge.
    middle = (w - 1) // 2
    for step in range(middle + 1):
        y = eave + step
        for z in range(-1, d + 1):
            set_block(step - 1, y, z, "deepslate_tile_stairs[facing=east,half=bottom,shape=straight]")
            set_block(w - step, y, z, "deepslate_tile_stairs[facing=west,half=bottom,shape=straight]")
    for z in range(-1, d + 1):
        set_block(middle, eave + middle + 1, z, "deepslate_tiles")
    # Fill front/back triangular gables below the pitched roof.
    for rise in range(1, middle + 1):
        for x in range(rise, w - rise):
            set_block(x, eave + rise, 0, "deepslate_bricks")
            set_block(x, eave + rise, d - 1, "deepslate_bricks")

def home_furniture(w, d):
    # Real bed footprint: two complementary blocks on solid ground.
    set_block(2, 1, d - 3, "blue_bed[facing=north,part=foot,occupied=false]")
    set_block(2, 1, d - 4, "blue_bed[facing=north,part=head,occupied=false]")
    set_block(w - 3, 1, d - 2, "chest[facing=north,type=single,waterlogged=false]")
    set_block(w - 3, 1, 2, "crafting_table")
    set_block(1, 1, d - 2, "bookshelf")
    set_block(1, 2, d - 2, "soul_lantern[hanging=false]")

def eave_trim(w, d, h):
    for x in range(1, w - 1):
        set_block(x, h + 1, 0, "deepslate_brick_slab[type=top]")
        set_block(x, h + 1, d - 1, "deepslate_brick_slab[type=top]")

# Two-story residence B: asymmetric roof, exterior stair porch, and upper balcony.
house_shell(9, 13, 9)
for x in range(1, 8):
    for z in range(1, 12):
        if not (x == 6 and 3 <= z <= 8):
            set_block(x, 5, z, "dark_oak_planks")
for step in range(5):
    set_block(6, 1 + step, 3 + step, "deepslate_brick_stairs[facing=south,half=bottom,shape=straight]")
for z in (3, 9):
    set_block(0, 7, z, "light_blue_stained_glass_pane")
    set_block(8, 7, z, "light_blue_stained_glass_pane")
for x in (2, 6):
    set_block(x, 7, 0, "light_blue_stained_glass_pane")
    set_block(x, 7, 12, "light_blue_stained_glass_pane")
home_furniture(9, 13)
set_block(2, 6, 9, "blue_bed[facing=north,part=foot,occupied=false]")
set_block(2, 6, 8, "blue_bed[facing=north,part=head,occupied=false]")
set_block(6, 6, 10, "chest")
floor(-2, 0, -1, 5, 5, "deepslate_tiles")
for z in range(0, 6):
    set_block(-2, 6, z, "polished_deepslate_wall")
set_block(0, 6, 3, "dark_oak_door[facing=west,half=lower,hinge=left,open=false]")
set_block(0, 7, 3, "dark_oak_door[facing=west,half=upper,hinge=left,open=false]")
# External upper balcony is decorative until an independent navigation pass.
pitched_roof(9, 13, 10)
