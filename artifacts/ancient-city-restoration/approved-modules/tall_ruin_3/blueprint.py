# tall_ruin_3 revised silhouette after user review
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
# CHURCH B: village church variant with a narrow high tower and side vestry.
footing(0,0,9,11)
shell(1,0,7,5,1,12)
shell(0,5,9,11,1,5)
clear(3,1,5,5,4,5)
door(4,0)
for y in (4,5,8,9):slit(4,y,0)
for z in (2,4):
    slit(1,4,z)
    slit(7,4,z)
for z in (7,9):
    slit(0,3,z)
    slit(9,3,z)
for z in (7,9):
    set_block(2,1,z,"dark_oak_stairs[facing=east]")
    set_block(7,1,z,"dark_oak_stairs[facing=west]")
set_block(4,1,10,"brewing_stand")
set_block(3,1,10,"bookshelf")
set_block(5,1,10,"chest")
for y in range(1,12):set_block(2,y,2,"ladder[facing=east]")
floor(2,1,6,4,11,"deepslate_tiles")
clear(2,11,2,2,11,2)
for z in (1,4):
    slit(1,11,z)
    slit(7,11,z)
# Open bell-chamber rim of a classic stone church tower.
floor(0,-1,8,6,13,"deepslate_tiles")
for x in (1,7):
    for z in (0,5):set_block(x,14,z,"deepslate_brick_wall")
for x in (1,4,7):
    for z in (0,5):set_block(x,14,z,"deepslate_brick_wall")
set_block(4,14,2,"chiseled_deepslate")
lantern(4,15,2)
roof(0,9,6,11,6)
# Modest side entry overhang, distinctive from Church A.
floor(-1,0,0,3,0,"deepslate_tiles")
for y in range(1,4):set_block(-1,y,1,"polished_basalt[axis=y]")
for x in (-1,0):
    for z in range(0,4):set_block(x,4,z,"deepslate_tile_slab[type=top]")
lantern(-1,3,2)
