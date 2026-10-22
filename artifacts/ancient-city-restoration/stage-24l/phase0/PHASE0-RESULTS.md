# Stage 24-L Phase 0 - Ancient City pedestrian connectivity (READ-ONLY measurement)

Static geometric model of the saved worlds of the Stage 24-K pack (24 seeds). **Not Minecraft-client gameplay**; not a physics simulation.
No gameplay content, NBT, datapack, processor or worldgen change. Model assumptions: see `tools/stage24l/phase0.py` docstring.

## 1. Reproduction of the Stage 24-I entrance survey

Observations regenerated: **116**; baseline (`stage-24k/worldgen/k24-entrance-survey.json`): 116; byte-equal rows (seed, piece, module, rotation, door, status, cells, path): **116**; differences: **0**.

## 2. Door status in the walkable-area graph (graph main component = largest two-way component of the city)

| status | doors |
|---|---|
| cut_off_from_main | 1 |
| no_walkable_cell_outside_door | 2 |
| open_to_main | 113 |
| **total** | **116** |

Door-front height relative to the door (floor step you take leaving the house), all doors:

| dy | -1 | -4 | 0 | None |
|---|---|---|---|---|
| doors | 96 | 1 | 17 | 2 |

Owner (smallest piece box containing it) of the cell directly outside the doorway - this is what a one-block growth of the house box on the door side would collide with:

| owner | doors |
|---|---|
| wall_stairs | 83 |
| wall_passage | 16 |
| wall | 12 |
| wall_bridge | 5 |

Doors whose outside cell lies in a chunk the house box does not touch (an out-of-box write there would be clipped, cf. Stage 24-I): **5** of 116.

## 3. Per-seed access and connectivity

| seed | walkable cells | components | main component share | house doors | open to main | not open | towers touching main |
|---|---|---|---|---|---|---|---|
| 24001 | 50718 | 1078 | 0.637 | 4 | 4 | 0 | 5/5 |
| 24002 | 47398 | 831 | 0.644 | 1 | 1 | 0 | 2/2 |
| 24003 | 55889 | 989 | 0.686 | 5 | 5 | 0 | 5/5 |
| 24004 | 62654 | 1357 | 0.523 | 3 | 3 | 0 | 0/0 |
| 24005 | 64949 | 1748 | 0.662 | 8 | 7 | 1 | 2/2 |
| 24006 | 45350 | 1029 | 0.614 | 4 | 4 | 0 | 3/3 |
| 24007 | 58341 | 1179 | 0.633 | 2 | 2 | 0 | 4/4 |
| 24008 | 52810 | 1166 | 0.714 | 9 | 9 | 0 | 3/3 |
| 24009 | 55169 | 1415 | 0.665 | 11 | 10 | 1 | 3/3 |
| 24010 | 59162 | 1264 | 0.681 | 3 | 3 | 0 | 3/3 |
| 24011 | 51120 | 933 | 0.686 | 6 | 6 | 0 | 3/3 |
| 24012 | 54717 | 1215 | 0.676 | 6 | 6 | 0 | 7/7 |
| 24013 | 51403 | 1157 | 0.713 | 2 | 2 | 0 | 4/4 |
| 24014 | 56614 | 1256 | 0.644 | 8 | 8 | 0 | 3/3 |
| 24015 | 56713 | 1067 | 0.687 | 7 | 6 | 1 | 2/2 |
| 24016 | 53923 | 971 | 0.723 | 2 | 2 | 0 | 5/5 |
| 24017 | 50706 | 1067 | 0.698 | 5 | 5 | 0 | 5/6 |
| 24018 | 54992 | 1113 | 0.663 | 4 | 4 | 0 | 4/4 |
| 24019 | 46616 | 970 | 0.606 | 1 | 1 | 0 | 2/2 |
| 24020 | 57238 | 1234 | 0.689 | 7 | 7 | 0 | 1/1 |
| 24021 | 51267 | 884 | 0.720 | 6 | 6 | 0 | 3/3 |
| 24022 | 56057 | 1253 | 0.682 | 4 | 4 | 0 | 1/1 |
| 24023 | 53916 | 1089 | 0.731 | 6 | 6 | 0 | 4/4 |
| 24024 | 50996 | 1180 | 0.681 | 2 | 2 | 0 | 1/1 |

Every seed has all house doors that are open in the same component (`front_components` has a single id) unless listed in section 4.

## 4. Doors that are not open to the main component

| seed | piece | module | rotation | door | status | interior in main? | front comp cells | drops front->main | drops main->front |
|---|---|---|---|---|---|---|---|---|---|
| 24005 | 71 | medium_ruin_1 | NONE | (-1348, -50, 1029) | no_walkable_cell_outside_door | False | None | None | None |
| 24009 | 59 | large_ruin_1 | CLOCKWISE_90 | (597, -50, 551) | no_walkable_cell_outside_door | False | None | None | None |
| 24015 | 55 | large_ruin_1 | COUNTERCLOCKWISE_90 | (-272, -50, -154) | cut_off_from_main | False | 27 | False | True |

## 5. Precise measurements at the deferred entrances

### Seed 24005 medium_ruin_1 (NONE), door (-1348, -50, 1029)

* 24-I survey: `ok`; obstruction cells: {'n': 14, 'natural': 14, 'architecture': 0, 'owner_templates': {'intact_horizontal_wall_1': 14}, 'inside_house_box': 0}
* obstruction extent: {'x': [-1349, -1349], 'y': [-50, -49], 'z': [1029, 1035]}
* door front: {'cell': None, 'front_dy': None, 'front_component': None, 'front_component_cells': None, 'main_component_cells': 42969}
* nearest main-component cell: {'cell': [-1348, -45, 1034], 'horizontal_manhattan': 5, 'dy': 5}; within 1 block of door height: {'cell': [-1348, -50, 1036], 'horizontal_manhattan': 7, 'dy': 0}
* minimum change that would give the doorway a two-way walk to the main component (computed, **nothing applied**):
  * `clear_only`: cost 14 (14 natural cells cleared, 0 floor blocks placed []; joins main at [-1349, -51, 1036]; cells to place are owned by: [])
  * `place_only`: impossible
  * `clear_and_place`: cost 14 (14 natural cells cleared, 0 floor blocks placed []; joins main at [-1349, -51, 1036]; cells to place are owned by: [])

```
dy of the nearest walkable cell relative to the door height (3 chars per column):
 +1  . +1 +1  0 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1
 +1  . +1 +1 +1 -1 -1 -1 -1 -1 -1 -1  0 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1
 +1  . +1 +1  . -1 -1 -1 -1  0 +1 +1 +2 +2 +1 +1  0 -1 -1 -1 -1 -1 -1 -1 -1
 +1  . +1 +1 +2 -1 -1 +1 +2 +3  .  .  .  .  . +3 +2  0 -1 -1 -1 -1 -1 -1 -1
 +1  .  0 +1 +1 -1 +1 +2  .  .  .  .  .  .  .  .  . +2 +1 -1 -1 -1 -1 -1 -1
 +1  . +1 +1 +2  0 +2  .  .  .  .  .  .  .  .  .  .  . +2 +1 -1 -1 -1 -1 -1
 +1  . +1 +1 +1 +2  .  .  .  .  .  .  .  .  .  .  .  .  .  .  0 -1 -1 -1 -1
 +1  . +1 +1  .  .  .  .  .  .  .  .  .  0  0  0  0  0  0  . +1 -1 -1 -1 -1
 +1  . +1  0 +1  .  .  .  .  .  .  .  .  0  0  0  0 +1 +1  . +1 -1 -1  0 +1
 +1  . +1 +1 +2  .  .  .  .  .  .  .  .  0  0  0  0  0  0  . +2 -1 -1 +2 +3
 +1  . +1 +1 +2  .  .  .  .  .  .  .  .  0  0  0  0  0  0  . +2 -1  0  . +3
 +1  . +1 +1 +2  .  .  .  .  .  .  .  .  0  0  0  0  0  0  . +2 -1  0 +2 +3
 +1  . +1 +1 +1  .  .  .  .  .  .  .  0  0  0  0  0 +1 +1  . +1 -1 -1  0  0
 +1  . +1 +1  . +2  .  .  .  .  .  .  .  0  0  0  0  0  0  . +1 -1 -1 -1  0
 +1  . +1 +1 +1 +2  .  .  .  .  .  .  .  0  0  0  0  0  0  .  0 -1 +1 +2 +2
 +1  . +1 +1 +2 +1 +2  .  .  .  .  .  .  0  0  0  0  0  0  . -1 +1 +3  .  .
 +1  . +1 +1 +1 -1 +1 +2  .  .  .  .  . +1 +1  0  0  0  0  . -1 +1  .  .  .
 +1  .  0 +1 +2 -1 -1 +1 +2 +3  .  .  .  0  0  0  0  0  0  .  0  .  .  .  .
 +1  . +1 +1 +1 -1 -1 -1  0  0 +1 +2  .  .  .  .  .  .  .  . -1 +2 +3  .  .
 +1  . +1 +1  . -1 -1 -1 -1 -1 -1 -1  0 -1  0 -1  0 -1 -1 -1 -1 +1 +3  .  .
 +1  . +1 +1 +1 -1  0  0 +1 -1 -1 -1 -1 -1 -1 -1 -1 +3 -1 -1 -1 -1  0 +1 +2
 +1  . +1 +1 +2 +1 +2 +2 +2 +1  0  0 -1  0 -1 -1 +3 +3 -1 -1 -1 -1 -1 -1  0
 +1  . +1 +1 +2  . +3  .  . +3 +2 +1  0 -1 -1 +3 -1 -1 -1 -1 -2 -1 -2 -1 -1
 +1  . +1 +2  .  .  .  .  .  .  . +1  0 +3 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1
 +1  . +2  .  .  .  .  .  .  .  .  . +1 +1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1

component class (rows = z from door.z-12..+12, columns = x from door.x-12..+12; M main component, F component in front of the door, o other, . no walkable cell within -12..+3 of the door height, D the door column):
M.MMMMMMMMMMMMMMMMMMMMMMM
M.MMMMMMMMMMMMMMMMMMMMMMM
M.MM.MMMMMMMMMMMMMMMMMMMM
M.MMMMMooo.....ooMMMMMMMM
M.MMMMoo.........ooMMMMMM
M.MMMMo...........ooMMMMM
M.MMMM..............MMMMM
M.MM.........oooooo.MMMMM
M.MMM........oooooo.MMMMM
M.MMM........oooooo.MMMoo
M.MMM........oooooo.MMM.o
M.MMM........oooooo.MMMoo
M.MMM.......Doooooo.MMMMM
M.MM.M.......oooooo.MMMMM
M.MMMM.......oooooo.MMMMM
M.MMMMM......oooooo.Moo..
M.MMMMMM.....oooooo.Mo...
M.MMMMMMMM...oooooo.M....
M.MMMMMMMMMM........Moo..
M.MM.MMMMMMMMMMMMMMMMoo..
M.MMMMMMMMMMMMMMMoMMMMMMM
M.MMMMMMMMMMMMMMooMMMMMMM
M.MMM.M..MMMMMMoMMMMMMMMM
M.MM.......MMoMMMMMMMMMMM
M.M.........MMMMMMMMMMMMM
```

### Seed 24009 large_ruin_1 (CLOCKWISE_90), door (597, -50, 551)

* 24-I survey: `ok`; obstruction cells: {'n': 6, 'natural': 6, 'architecture': 0, 'owner_templates': {'ruined_horizontal_wall_stairs_4': 6}, 'inside_house_box': 0}
* obstruction extent: {'x': [595, 597], 'y': [-50, -49], 'z': [550, 550]}
* door front: {'cell': None, 'front_dy': None, 'front_component': None, 'front_component_cells': None, 'main_component_cells': 36670}
* nearest main-component cell: {'cell': [594, -50, 550], 'horizontal_manhattan': 4, 'dy': 0}; within 1 block of door height: {'cell': [594, -50, 550], 'horizontal_manhattan': 4, 'dy': 0}
* minimum change that would give the doorway a two-way walk to the main component (computed, **nothing applied**):
  * `clear_only`: cost 6 (6 natural cells cleared, 0 floor blocks placed []; joins main at [594, -50, 550]; cells to place are owned by: [])
  * `place_only`: impossible
  * `clear_and_place`: cost 6 (6 natural cells cleared, 0 floor blocks placed []; joins main at [594, -50, 550]; cells to place are owned by: [])

```
dy of the nearest walkable cell relative to the door height (3 chars per column):
  0 +1 +1 -1 +1  0 -1 -1 -1 -1  0 -1  0 -1 +1 +3  .  .  . +3 +3 +1 -1 +1 +2
  .  .  .  .  .  . +3  0 -1 -1 -1 -1  0 -1 -1 +1 +2 +1 +2 +1  0 -1  0 +1 +2
 +1 +1 +1 +1 +1 +1 +1 -1 -1 -1 -1 -1 -1 -1  0 -1  0  0 -1 +2 -1 -1 -1  0 +2
 +1 +1 +1  0 +1 +1  0 -1 -1 -1 -1 -1 -1 -2 -1 -1  0 -1  0  .  0 -1  0  0 +2
 +1  . +1 +1  . +1 +2 +1 +2  0  0 -1 -1 -1 -1 -1 -1 -1 +2 +1 +2  . +1 +1 +2
 -1 -1 -1  0  0 -1  0  0  0  0  0 -1 +1  0 -1 -1 -1 +1 +1 -1  0 -1 +2  0 +2
 -1 -1 -1  0  0  0  0  0  0  0  0 +1 +2 +1  0 -1  0  0  0  0  0 -1  0 +1 +3
 -1 -1 -1  0 -1 -1  0 -1  0  0 +2  .  .  . +3  0  0  0  0  0 +3 -1  0 +1 +2
 -1 -1 -1  0  0  0  0  0  0 +1  .  .  .  .  . +2  0 -1  0  0  0 -1 +3  0 +2
 -1 -1 -1 -1  0 -1  0  0  0 +1  .  .  .  .  . +3  . -1  0  0 -2  0 -1 +1 +1
 -1 -1 -1 -1 -1 -1 -1 -1 -1 +1  .  .  .  .  . +1 -1 -1 -1 -1  0 +1 +3 +1 +1
 -1 -1 -1 -1 -1 -1 -1 -1 -1  0 +3  .  .  . +2 +1 -1 -1 +1  0 -1 -1  0  0 +2
 -1 -1 -1  .  .  .  .  .  .  .  .  .  0  .  .  .  .  .  .  . -1 -1 -1 +1 +2
 -1 -1 -1  .  0  0  0  0  0  0  0  0  0  0  0  0 -1  0  0  . -1 -1  0  0 +2
 -1 -1 -1  .  0  0  0  0  0  0  0  0  0  0  0 +1  0 +1  0  . -1 -1  0  0 +3
  0 -1 -1  .  0  0  0  0  0 +1  0  0  0  0  0  0  0  0  0  . -1 -1  0 +1  .
  0 -1 -1  .  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  . -1  0  0 +2  .
  0 -1 -1  .  .  .  .  . +3  .  0  0  0  .  .  .  .  .  .  . -1  0  0 +2  .
  0 -1 -1  .  0  0  0  0  .  0  0  0  0  0  .  0  0  0  0  . -1  0  0 +3  .
  0 -1 -1  .  0  0  0  0  .  0  0  0  0  0  .  0  0  0  0  . -1  0  0 +3  .
 -1 -1 -1  .  0  0  0  0  .  0  0  0  0  0  .  0  0  0  0  . -1  0  0 +3  .
 -1 -1 -1  .  0  0  0  0  .  0  0  0  0  0  .  0  0  0  0  . -1  0  0 +3  .
 -1 -1 -1  .  0  0  0  0  .  0  0  0  0  0  .  0  0 -1  0  . -1  0  0 +3  .
 -1 -1 -1  .  .  .  .  .  .  .  0  0  0  .  .  .  .  .  .  . -1  0  0 +3  .
 -1 -1 -1  .  0 -1  0  0 +1 +1  0 +1  0  0  0 +1 +1  0  0  . -1  0  0 +2  .

component class (rows = z from door.z-12..+12, columns = x from door.x-12..+12; M main component, F component in front of the door, o other, . no walkable cell within -12..+3 of the door height, D the door column):
MMMoMMMMMMMMMMMo...ooMMMM
......MMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMM.MMMMM
M.MM.MMMMMMMMMMMMMMMM.MMM
MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMo...oMMMMMoMMMM
MMMMMMMMMM.....oMMMMMMoMM
MMMMMMMMMM.....o.MMMoMMMM
MMMMMMMMMM.....oMMMMMMoMM
MMMMMMMMMMo...ooMMMMMMMMM
MMM.........D.......MMMMM
MMM.ooooooooooooooo.MMMMM
MMM.ooooooooooooooo.MMMMM
MMM.ooooooooooooooo.MMMM.
MMM.ooooooooooooooo.MMMM.
MMM.....o.ooo.......MMMM.
MMM.oooo.ooooo.oooo.MMMM.
MMM.oooo.ooooo.oooo.MMMM.
MMM.oooo.ooooo.oooo.MMMM.
MMM.oooo.ooooo.oooo.MMMM.
MMM.oooo.ooooo.oooo.MMMM.
MMM.......ooo.......MMMM.
MMM.ooooooooooooooo.MMMM.
```

### Seed 24015 large_ruin_1 (COUNTERCLOCKWISE_90), door (-272, -50, -154)

* 24-I survey: `no_connection_within_radius`; obstruction cells: {'n': 0, 'natural': 0, 'architecture': 0, 'owner_templates': {}, 'inside_house_box': 0}
* obstruction extent: None
* door front: {'cell': [-272, -54, -153], 'front_dy': -4, 'front_component': 10298, 'front_component_cells': 27, 'main_component_cells': 38952}
* nearest main-component cell: {'cell': [-272, -51, -152], 'horizontal_manhattan': 1, 'dy': 3}; within 1 block of door height: {'cell': [-284, -53, -153], 'horizontal_manhattan': 12, 'dy': 1}
* front component can drop to main: False; main can drop into front component: True
* minimum change that would give the doorway a two-way walk to the main component (computed, **nothing applied**):
  * `clear_only`: impossible
  * `place_only`: cost 1 (0 natural cells cleared, 1 floor blocks placed [[-272, -52, -153]]; joins main at [-272, -51, -152]; cells to place are owned by: [(None, 'air')])
  * `clear_and_place`: cost 1 (0 natural cells cleared, 1 floor blocks placed [[-272, -52, -153]]; joins main at [-272, -51, -152]; cells to place are owned by: [(None, 'air')])

```
dy of the nearest walkable cell relative to the door height (3 chars per column):
  0  0 -1 -1 -1  .  0  0 +1 +1  0 -1  0 +1  0 +1 +1  0  0  0  0  . -1 -1 -1
  0  0 -1 -1 -1  .  .  .  .  .  . +3  0  0  0  .  .  .  .  .  .  . -1 -1 -1
  0  0 -1 -1 -1  .  0  0  0  0  .  0 -1  0  0  0  .  0  0  0  0  . -1 -1 -1
  0  0 -1 -1 -1  .  0  0  0  0  .  0  0  0  0  0  .  0  0 +1  0  . -1 -1 -1
  0  0 -1 -1 -1  .  0  0 -1  0  .  0  0 -1  0  0  .  0 -1  0  0  . -1 -1 -1
  0  0 -1 -1 -1  .  0  0  0  0  .  0  0  0  0  0  .  0  0 -1  0  . -1 -1 -1
  0  0 -1 -1 -1  .  0  0  0  0  .  0  0  0 -1  0  .  0  0  0 -1  . -1 -1 -1
  0  0 -1 -1 -1  .  .  .  .  .  .  .  0  0  0  .  .  .  .  .  .  . -1 -1 -1
  0 -1 -1 -1 -1  .  0  0 -1  0  0  0  0  0  0  0  0  0  0  0  0  . -1 -1 -1
 -1 -1 -1 -1 -1  .  0  0  0  0  0 -3  0  0  0 +1  0  0  0  0  0  . -1 -1 -1
 -1 -1 -1 -1 -1  .  0 +1  0 +1  0  0  0  0  0  0  0  0  0  0  0  . -1 -1 -1
 -3 -1 -1 -1 -1  .  0  0  0  0  0  0  0  0  0  0  0  0  0  0 -1  . -1 -1 -1
 -3 -1 -1 -1 -1  .  .  .  .  .  . -3  0 -4 -4 -4  .  .  .  .  .  . -1 -1 -1
 -3 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -3 -4 -4 -4 -4 -1 -1 -1 -1 -1 -1 -1 -1 -1
 -3 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -4 -4  . -1 -1 -1 -1 -1 -1 -1 -1 -1
 -3 -3 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1  .  . -1 -1 -1 -1 -1 -1 -1 -1 -1
 -4 -4 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1
 -4 -4 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1
 -4 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1
 -4 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1
 +1 +2 +1 +2 +2 +1 +2 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 +1 +2 +1  . +1 +1  . +1
 +1 +1 +1 +1 +1 +1  0 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1  0 +1 +1 +1 +1 +1 +1 +1
 +1 +1 +1 +1 +1 +1  0 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1  0 +1 +1 +1 +1 +1 +1 +1
  .  . -4  .  .  .  .  . -1 -1 -1 -1 -1 -1 -1 -1  .  .  .  .  .  .  .  .  .
 +1 +1 +1 +1 +1 +1  0 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1  0 +1 +1 +1 +1 +1 +1 +1

component class (rows = z from door.z-12..+12, columns = x from door.x-12..+12; M main component, F component in front of the door, o other, . no walkable cell within -12..+3 of the door height, D the door column):
MMMMM.ooooooooooooooo.MMM
MMMMM......oooo.......MMM
MMMMM.oooo.ooooo.oooo.MMM
MMMMM.oooo.ooooo.oooo.MMM
MMMMM.oooo.ooooo.oooo.MMM
MMMMM.oooo.ooooo.oooo.MMM
MMMMM.oooo.ooooo.oooo.MMM
MMMMM.......ooo.......MMM
MMMMM.ooooooooooooooo.MMM
MMMMM.oooooFooooooooo.MMM
MMMMM.ooooooooooooooo.MMM
MMMMM.ooooooooooooooo.MMM
MMMMM......FDFFF......MMM
MMMMMMMMMMMFFFFFMMMMMMMMM
MMMMMMMMMMMMMFF.MMMMMMMMM
MMMMMMMMMMMMMM..MMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMM.MM.M
MMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMM
..M.....MMMMMMMM.........
MMMMMMMMMMMMMMMMMMMMMMMMM
```

## 6. Routes between buildings (two-way graph, nearest 3 other buildings' doors from each building)

* building-to-building routes: 311, steps (blocks walked) {'median': 94, 'p90': 184, 'max': 263}
* route height range (max-min along the path): {0: 26, 1: 69, 2: 113, 3: 61, 4: 28, 5: 12, 7: 1, 8: 1}
* routes through a `wall_stairs` piece box: 307
* share of route steps by piece box: {'wall_stairs': 0.3629, 'natural_terrain': 0.2172, 'city_center_wall': 0.145, 'wall': 0.122, 'entrance_path': 0.0499, 'wall_passage': 0.0497, 'wall_bridge': 0.0186, 'chamber': 0.0146, 'monument': 0.0111, 'other': 0.0056, 'sauna': 0.0034}
* floor blocks under routes: {'sculk': 13157, 'deepslate': 11657, 'gray_wool': 2165, 'tuff': 676, 'deepslate_bricks': 633, 'deepslate_tile_stairs': 280, 'deepslate_tiles': 249, 'cracked_deepslate_bricks': 187}
* building-to-city-entrance routes: 113, steps {'median': 76, 'p90': 135, 'max': 168}

## 6b. The other walkable components (largest 5 per seed, 120 in total)

* none of them contains a house door (all 113 open doors lead to the main component); 120 components, 131659 cells
* what they lie in (sampled): {'natural_terrain': 91131, 'wall': 6009, 'wall_stairs': 4375, 'city_center': 3504, 'city_center_wall': 3136, 'wall_passage': 929, 'monument': 569, 'wall_bridge': 383, 'sauna': 10}
* can drop onto the main component (one-way): 29; main can drop into them: 1

## 7. Variation by module and rotation (door status counts)

| module | rotation | status counts |
|---|---|---|
| large_ruin_1 | CLOCKWISE_180 | {'open_to_main': 7} |
| large_ruin_1 | CLOCKWISE_90 | {'open_to_main': 4, 'no_walkable_cell_outside_door': 1} |
| large_ruin_1 | COUNTERCLOCKWISE_90 | {'open_to_main': 4, 'cut_off_from_main': 1} |
| large_ruin_1 | NONE | {'open_to_main': 3} |
| medium_ruin_1 | CLOCKWISE_180 | {'open_to_main': 4} |
| medium_ruin_1 | CLOCKWISE_90 | {'open_to_main': 4} |
| medium_ruin_1 | COUNTERCLOCKWISE_90 | {'open_to_main': 12} |
| medium_ruin_1 | NONE | {'no_walkable_cell_outside_door': 1, 'open_to_main': 5} |
| medium_ruin_2 | CLOCKWISE_180 | {'open_to_main': 2} |
| medium_ruin_2 | CLOCKWISE_90 | {'open_to_main': 4} |
| medium_ruin_2 | COUNTERCLOCKWISE_90 | {'open_to_main': 6} |
| medium_ruin_2 | NONE | {'open_to_main': 8} |
| small_ruin_1 | CLOCKWISE_180 | {'open_to_main': 7} |
| small_ruin_1 | CLOCKWISE_90 | {'open_to_main': 5} |
| small_ruin_1 | COUNTERCLOCKWISE_90 | {'open_to_main': 4} |
| small_ruin_1 | NONE | {'open_to_main': 6} |
| small_ruin_2 | CLOCKWISE_180 | {'open_to_main': 8} |
| small_ruin_2 | CLOCKWISE_90 | {'open_to_main': 6} |
| small_ruin_2 | COUNTERCLOCKWISE_90 | {'open_to_main': 7} |
| small_ruin_2 | NONE | {'open_to_main': 7} |

