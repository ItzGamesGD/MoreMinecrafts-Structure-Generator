# tall_ruin_2 revised silhouette after user review
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
# TWO-STOREY HOUSE A: broad overhanging second floor and framed street arcade.
footing(1,1,11,10)
shell(1,1,11,10,1,4)
door(6,1)
for x in (3,9):slit(x,2,1)
for z in (4,8):
    slit(1,2,z)
    slit(11,2,z)
# Portico creates readable ground/upper depth.
floor(3,-2,9,0,0,"deepslate_tiles")
for x in (3,9):
    for y in range(1,5):set_block(x,y,-1,"polished_basalt[axis=y]")
for x in range(3,10):set_block(x,4,-1,"dark_oak_log[axis=x]")
lantern(4,3,-1)
lantern(8,3,-1)
# Upper floor overhangs the ground footprint by 1 block on every side.
floor(0,0,12,11,5,"dark_oak_planks")
shell(0,0,12,11,6,9)
for x in (0,3,9,12):
    for y in range(6,10):set_block(x,y,0,"dark_oak_log[axis=y]")
for x in (2,6,10):
    for y in (7,8):
        slit(x,y,0)
        slit(x,y,11)
for z in (3,8):
    for y in (7,8):
        slit(0,y,z)
        slit(12,y,z)
for x in range(13):
    for y in (6,9):set_block(x,y,0,"dark_oak_log[axis=x]")
# Internal stair, 4 rising steps and opening above flight.
for step in range(4):
    set_block(3+step,1+step,7,"deepslate_brick_stairs[facing=east]")
for x in range(3,7):
    set_block(x,5,7,"air")
set_block(7,5,7,"dark_oak_planks")
set_block(2,1,8,"blue_bed[facing=north,part=foot]")
set_block(2,1,7,"blue_bed[facing=north,part=head]")
set_block(9,1,8,"crafting_table")
set_block(9,6,8,"blue_bed[facing=north,part=foot]")
set_block(9,6,7,"blue_bed[facing=north,part=head]")
set_block(9,6,10,"chest")
lantern(6,7,6)
roof(0,12,0,11,10)
# Front dormer offsets the roof and breaks the formerly plain box.
for x in range(4,9):
    for y in (11,12):set_block(x,y,-2,"deepslate_bricks")
for x in (5,6,7):slit(x,11,-2)
for x in range(4,9):set_block(x,13,-2,"deepslate_tile_stairs[facing=south]")
set_block(6,14,-2,"chiseled_deepslate")
