# camp_2: approved smithy silhouette revision.
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
# ENCLOSED SMITHY: masonry workshop with open overhanging forge awning.
foundation(0,0,11,11)
forge_shed(0,0,11,11,5)
set_block(4,1,0,"dark_oak_door[facing=south,half=lower]")
set_block(4,2,0,"dark_oak_door[facing=south,half=upper]")
for x in (2,8):
    set_block(x,3,0,"light_blue_stained_glass_pane")
    set_block(x,3,11,"light_blue_stained_glass_pane")
for z in (3,8):
    set_block(0,3,z,"light_blue_stained_glass_pane")
    set_block(11,3,z,"light_blue_stained_glass_pane")
floor(-1,-4,11,-1,0,"deepslate_tiles")
for x in (0,10):
    for y in range(1,5):set_block(x,y,-3,"dark_oak_log[axis=y]")
for z in range(-4,0):
    for x in range(-1,12):
        set_block(x,5,z,"light_blue_wool" if x%3==0 else "blue_wool")
# Side chimney breaks roof skyline, stays far below church towers.
for y in range(1,12):
    for x in (11,12):
        for z in (7,8):set_block(x,y,z,"polished_deepslate")
set_block(11,12,7,"deepslate_brick_wall")
workbench(3,1,7)
set_block(5,1,7,"anvil")
set_block(8,1,7,"blast_furnace")
set_block(8,1,3,"grindstone")
set_block(2,1,10,"barrel")
set_block(9,3,-2,"soul_lantern")
camp_roof(0,11,0,11,6)
