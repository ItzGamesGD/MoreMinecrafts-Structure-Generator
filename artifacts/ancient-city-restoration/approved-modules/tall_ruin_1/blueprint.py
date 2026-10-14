# tall_ruin_1 revised silhouette after user review
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
# CHURCH A: classic small vanilla-village church, modest square tower.
footing(0,0,9,12)
shell(0,0,6,6,1,11)
shell(1,6,9,12,1,5)
clear(3,1,6,5,4,6)
door(3,0)
for y in (3,7):
    slit(0,y,3)
    slit(6,y,3)
for z in (8,10):
    slit(1,3,z)
    slit(9,3,z)
for z in (8,10):
    set_block(3,1,z,"dark_oak_stairs[facing=east]")
    set_block(7,1,z,"dark_oak_stairs[facing=west]")
set_block(5,1,11,"brewing_stand")
set_block(4,1,11,"bookshelf")
lantern(2,2,10)
for y in range(1,11):
    set_block(1,y,2,"ladder[facing=east]")
floor(1,1,5,5,10,"deepslate_tiles")
clear(1,10,2,1,10,2)
for x in (2,4):
    slit(x,11,0)
for z in (2,4):
    slit(0,11,z)
# Bell-tower cap - four gentle layers, not a giant spire.
floor(-1,-1,7,7,12,"deepslate_tiles")
floor(0,0,6,6,13,"deepslate_tile_stairs")
floor(1,1,5,5,14,"deepslate_tiles")
floor(2,2,4,4,15,"deepslate_tiles")
lantern(3,16,3)
# Side nave roof; church skyline stays modest.
roof(1,9,7,12,6)
for x in (3,7):slit(x,3,12)
