# camp_1: approved smithy silhouette revision.
# Single Ancient City camp module, smithy exterior concept (no mechanics).
# Independent blueprint: NOT yet verified against vanilla NBT / jigsaw links.
def foundation(x1,z1,x2,z2):
    floor(x1,z1,x2,z2,0,"polished_deepslate")
    for x in range(x1,x2+1):
        for z in (z1,z2):set_block(x,0,z,"deepslate_tiles")
    for z in range(z1,z2+1):
        for x in (x1,x2):set_block(x,0,z,"deepslate_tiles")
def forge_shed(x1,z1,x2,z2,h):
    walls(x1,z1,x2,z2,1,h,"deepslate_bricks")
    for x in (x1,x2):
        for z in (z1,z2):
            for y in range(1,h+1):set_block(x,y,z,"polished_basalt[axis=y]")
def workbench(x,y,z):
    set_block(x,y,z,"smithing_table")
def camp_roof(x1,x2,z1,z2,eave):
    for x in range(x1-1,x2+2):
        level=max(0,min(x-x1+1,x2+1-x)//2)
        for z in range(z1-1,z2+2):
            set_block(x,eave+level,z,"deepslate_tile_stairs[facing=east]" if x<=(x1+x2)//2 else "deepslate_tile_stairs[facing=west]")
# OPEN SMITHY: thin covered street front with forge behind.
foundation(0,0,11,9)
forge_shed(0,3,11,9,4)
clear(3,1,3,8,3,3)
floor(-1,-3,12,2,0,"cobbled_deepslate")
for x in (0,11):
    for y in range(1,5):set_block(x,y,-2,"polished_basalt[axis=y]")
for x in range(-1,13):
    for z in (-3,-2,-1,0,1,2):
        set_block(x,5,z,"blue_wool" if (x+z)%4==0 else "cyan_wool")
# Off-center chimney extends beyond the tiled workshop roof.
for y in range(1,12):
    for x in (9,10):
        for z in (7,8):set_block(x,y,z,"deepslate_bricks")
set_block(9,12,7,"deepslate_brick_wall")
workbench(3,1,6)
set_block(6,1,5,"anvil")
set_block(8,1,6,"blast_furnace")
set_block(2,1,7,"barrel")
for x in (1,10):set_block(x,3,2,"soul_lantern")
camp_roof(0,11,3,9,5)
