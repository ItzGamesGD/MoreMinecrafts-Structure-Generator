# Stage 24-G — terrain and fluid intersections (24-seed sweep)

Stage 24-F vs Stage 24-G: identical cells except 1 cell(s) only stage24g: seed 24008 (596, -50, 1281) lava — flowing lava spreads by fluid ticks after generation, so one flow cell more or less is timing, not protection. The protection overlay writes no cell that terrain occupies (it only re-writes blocks the template itself stores).

Classes: functional obstruction (blocks a walkable/door cell), cosmetic intrusion, existing vanilla/environmental behaviour (cell the vanilla template also leaves unstored, natural terrain), potential generation hazard (fluid). Rule: `tools/stage24g/terrain.py`. No terrain is removed in Stage 24-G; see `OWNER-DECISION-interior-terrain.md`.

| seed | structure | rotation | class | block | cells | world coordinates (first 3) | assessment |
|---|---|---|---|---|---|---|---|
| 24004 | large_ruin_1 | CLOCKWISE_180 | cosmetic intrusion | smooth_basalt | 1 | (-249, -40, -1035) | One block of an amethyst geode's smooth-basalt shell reaching into the extreme corner of the taller Option C box (template (16,11,16): 5 blocks above the corner eave, no roof or wall block next to it). Does not touch the roof, a room or a path; visible only as part of the cave wall behind the corner. |
| 24005 | medium_ruin_1 | NONE | existing vanilla behaviour | dripstone_block | 65 | (-1347, -49, 1033); (-1347, -48, 1024); (-1347, -48, 1025) | Dripstone blocks (dripstone-caves features placed before the city) fill the room: the house is buried. Same cells in Stage 24-C/24-F. |
| 24005 | medium_ruin_1 | NONE | functional obstruction | dripstone_block | 124 | (-1347, -50, 1024); (-1347, -50, 1025); (-1347, -50, 1026) | Dripstone blocks (dripstone-caves features placed before the city) fill the room: the house is buried. Same cells in Stage 24-C/24-F. |
| 24008 | small_ruin_1 | COUNTERCLOCKWISE_90 | potential generation hazard | lava | 6 | (596, -50, 1280); (596, -50, 1281); (597, -50, 1280) | Lava in the room (lava spring/flow after placement); a player entering takes fire damage. |
| 24009 | large_ruin_1 | CLOCKWISE_90 | existing vanilla behaviour | dripstone_block | 1 | (596, -48, 558) | A dripstone cluster stands in the hall (12 walkable cells) plus 1 block outside; the 24-C sweep had 7 in this piece at another spot. |
| 24009 | large_ruin_1 | CLOCKWISE_90 | functional obstruction | dripstone_block | 12 | (595, -50, 557); (595, -50, 558); (595, -49, 558) | A dripstone cluster stands in the hall (12 walkable cells) plus 1 block outside; the 24-C sweep had 7 in this piece at another spot. |
| 24012 | sauna_1 | CLOCKWISE_90 | existing vanilla behaviour | deepslate | 1 | (-1245, -42, 112) | One natural deepslate block in an unstored cell above the roof edge. |
| 24014 | medium_pillar_1 | COUNTERCLOCKWISE_90 | existing vanilla behaviour | deepslate | 3 | (1276, -41, -932); (1279, -43, -932); (1279, -42, -932) | Three natural deepslate blocks in unstored cells beside the tower top (outside the walkable deck). |
| 24014 | sauna_1 | CLOCKWISE_90 | potential generation hazard | lava | 5 | (1293, -46, -1017); (1293, -45, -1017); (1293, -44, -1017) | A 5-high lava column inside the box behind the masonry, not touching a walkable cell. |

Full cell list: `worldgen/g24-terrain-classification.json` (Stage 24-F: `investigation/f24-terrain-classification.json`).
