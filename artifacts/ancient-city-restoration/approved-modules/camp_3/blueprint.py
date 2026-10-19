# camp_3: approved smithy silhouette revision.
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
# OPEN-AIR SMITHY: low storage shack and a wide side workyard with canopy.
foundation(0,0,12,8)
forge_shed(0,2,7,8,4)
set_block(4,1,2,"dark_oak_door[facing=south,half=lower]")
set_block(4,2,2,"dark_oak_door[facing=south,half=upper]")
floor(8,-1,13,8,0,"cobbled_deepslate")
for x in (8,13):
    for z in (-1,8):
        for y in range(1,5):set_block(x,y,z,"polished_basalt[axis=y]")
for x in range(8,14):
    for z in range(-1,9):
        set_block(x,5,z,"cyan_wool" if (x+z)%3 else "light_blue_wool")
set_block(10,1,2,"anvil")
set_block(10,1,5,"blast_furnace")
workbench(3,1,5)
set_block(5,1,6,"barrel")
set_block(12,1,7,"cauldron")
# Offset short stack on the outside workyard.
for y in range(1,10):set_block(12,y,7,"deepslate_bricks")
set_block(12,10,7,"deepslate_brick_wall")
clear(7,1,4,7,2,5)
set_block(8,3,1,"soul_lantern")
set_block(12,3,7,"soul_lantern")
camp_roof(0,7,2,8,5)
