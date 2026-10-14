# tall_ruin_4 revised silhouette after user review
# Individual Ancient City structure prototype, not a vanilla NBT copy.
# Entrance towards z=0; the Warden monument / worldgen is out of scope.
def footing(x1,z1,x2,z2):
    floor(x1,z1,x2,z2,0,"polished_deepslate")
    for x in range(x1,x2+1):
        for z in (z1,z2):set_block(x,0,z,"deepslate_tiles")
    for z in range(z1,z2+1):
        for x in (x1,x2):set_block(x,0,z,"deepslate_tiles")
def shell(x1,z1,x2,z2,y1,y2):
    walls(x1,z1,x2,z2,y1,y2,"deepslate_bricks")
    for x in (x1,x2):
        for z in (z1,z2):
            for y in range(y1,y2+1):set_block(x,y,z,"polished_basalt[axis=y]")
def door(x,z):
    set_block(x,1,z,"dark_oak_door[facing=south,half=lower]")
    set_block(x,2,z,"dark_oak_door[facing=south,half=upper]")
    set_block(x,3,z,"chiseled_deepslate")
def roof(x1,x2,z1,z2,eave):
    # Low stepped gable avoids a fantasy cathedral silhouette.
    for x in range(x1-1,x2+2):
        rise=max(0,min(x-x1+1,x2+1-x)//2)
        for z in range(z1-1,z2+2):
            block="deepslate_tile_stairs[facing=east]" if x<=(x1+x2)//2 else "deepslate_tile_stairs[facing=west]"
            set_block(x,eave+rise,z,block)
    for z in (z1,z2):
        for x in range(x1,x2+1):
            rise=max(0,min(x-x1+1,x2+1-x)//2)
            for y in range(eave,eave+rise):
                set_block(x,y,z,"deepslate_bricks")
def slit(x,y,z):
    set_block(x,y,z,"light_blue_stained_glass_pane")
def lantern(x,y,z):
    set_block(x,y,z,"soul_lantern")
# TWO-STOREY HOUSE B: L-shaped upper house, terrace, side staircase, asymmetry.
footing(1,1,10,13)
shell(1,1,10,13,1,4)
door(4,1)
for x in (3,8):slit(x,2,13)
for z in (4,10):
    slit(1,2,z)
    slit(10,2,z)
set_block(8,1,11,"barrel")
set_block(8,1,3,"crafting_table")
set_block(3,1,11,"blue_bed[facing=north,part=foot]")
set_block(3,1,10,"blue_bed[facing=north,part=head]")
floor(0,0,11,13,5,"dark_oak_planks")
shell(0,0,10,8,6,9)
shell(6,8,11,13,6,9)
clear(7,6,8,9,8,8)
# Open raised terrace at back-left, in deliberate contrast with house A.
for x in range(0,6):set_block(x,6,13,"deepslate_brick_wall")
for z in range(9,14):set_block(0,6,z,"deepslate_brick_wall")
for x in range(1,6):set_block(x,6,9,"deepslate_brick_wall")
set_block(6,6,11,"dark_oak_door[facing=west,half=lower]")
set_block(6,7,11,"dark_oak_door[facing=west,half=upper]")
for step in range(4):set_block(8,1+step,3+step,"deepslate_brick_stairs[facing=south]")
for z in range(3,7):set_block(8,5,z,"air")
set_block(8,5,7,"dark_oak_planks")
for x in (2,5,8):
    for y in (7,8):slit(x,y,0)
for z in (3,6):
    for y in (7,8):slit(0,y,z)
for z in (10,12):
    for y in (7,8):slit(11,y,z)
set_block(3,6,6,"blue_bed[facing=north,part=foot]")
set_block(3,6,5,"blue_bed[facing=north,part=head]")
set_block(8,6,12,"bookshelf")
lantern(4,7,7)
lantern(5,6,11)
roof(0,10,0,8,10)
# Offset smaller wing has flat stone roofing, keeps L roofline legible.
floor(6,8,11,13,10,"deepslate_tiles")
for x in range(6,12):
    for z in (8,13):set_block(x,11,z,"deepslate_tile_slab[type=top]")
for z in range(8,14):
    for x in (6,11):set_block(x,11,z,"deepslate_tile_slab[type=top]")
for x in (2,6):
    for y in range(1,4):set_block(x,y,0,"polished_basalt[axis=y]")
lantern(5,4,0)
