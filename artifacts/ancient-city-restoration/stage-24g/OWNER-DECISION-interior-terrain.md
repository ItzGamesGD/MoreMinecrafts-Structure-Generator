# OWNER DECISION REQUIRED — natural terrain and fluids inside restored rooms

**Not implemented.** The brief stops before large-scale terrain changes; this note documents the mechanism and the
options. The same buried room appears with the Stage 24-C, 24-F and 24-G sets; functional protection does not change it.

## What happens (VERIFIED)

* The restored templates — like the vanilla ruins they replace, which store 16–38 blocks and no air — do not store air
  in their rooms. `StructureTemplate.placeInWorld` only writes stored blocks, so every unstored cell keeps whatever was
  generated there.
* The city's `beard_box` terrain adaptation carves *noise* terrain around piece boxes, but features are not beard-aware:
  dripstone clusters and amethyst geodes (placed before the city in their decoration steps) stay, and lava/water springs
  and ore blobs placed after the city can spill in.
* With a vanilla ruin fragment that is invisible — the "inside" of the box is open cave. With a restored house the same
  terrain fills a room.

Cells of each module where a player stands or walks and the template stores nothing (terrain can stay there):
large_ruin_1 370, medium_ruin_1 124, medium_ruin_2 361, small_ruin_1 54, small_ruin_2 20, sauna_1 1544,
large_pillar_1 39, medium_pillar_1 8.

Observed in the 24-seed sweeps (identical in Stage 24-F and 24-G, see `TERRAIN-CLASSIFICATION.md`):

| seed | module | what | class |
|---|---|---|---|
| 24005 | medium_ruin_1 | 124 dripstone blocks fill the room (+65 outside the walls) | functional obstruction |
| 24009 | large_ruin_1 | 12-block dripstone cluster in the hall (+1 outside) | functional obstruction |
| 24008 | small_ruin_1 | 5 lava cells in the room | potential generation hazard |
| 24014 | sauna_1 | 5-high lava column inside the box, not touching a walkable cell | potential generation hazard |

## Options

| option | what changes | trade-offs |
|---|---|---|
| **A. Interior clearance overlay** (recommended if the owner wants rooms always usable) | add `air` for the walkable cells of each room to the Stage 24-G protection overlay (same list-element mechanism; the approved NBTs stay byte-identical, dimensions unchanged) | removes dripstone/geode/terrain from room interiors at placement time; does **not** stop fluids or ore blobs placed later in generation (lava from a spring can still flow in); rooms look less "reclaimed by the cave" than vanilla ruins; ~2,500 cells across the eight modules (sauna 1,544) |
| B. Store interior air in the templates | the same effect written into the NBTs | changes the approved structure NBT hashes; not recommended |
| C. Accept as environmental behaviour | nothing | about 2 of 24 cities had a blocked room and 1 lava in a room in this sweep |
| D. Change placement / terrain adaptation | city-wide generation change | out of scope (global Ancient City behaviour), not recommended |

Decision needed: A, C, or another rule (for example clearing only doorways and the paths to beds/containers).
