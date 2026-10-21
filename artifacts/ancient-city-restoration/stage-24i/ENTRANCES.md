# Stage 24-I — Entrance accessibility (Part B) — **PARTIAL / OWNER DECISION REQUIRED**

## Survey (`tools/stage24i/entrances.py`)

For every house door in the Stage 24-H sweep (116 entrances, 24 seeds) a 0-1 shortest-path search starts at the door
cell, leaves through the door's outward side (rotated), moves ±1 block in height, needs a floor under every step, and
costs one per solid **natural** body cell that would have to be cleared (architecture is never cleared). The target is a
free walkable cell of an open component of ≥ 200 cells outside the house box (the city's path network), radius 14.

| result | entrances |
|---|---|
| already connected, nothing to clear | **113** |
| seed 24005 medium_ruin_1 #71 (NONE), door (-1348,-50,1029) | **14 cells**: x = -1349, y = -50..-49, z = 1029..1035 — all `dripstone_block`, a 2-high, 7-long strip along the outside of the house wall |
| seed 24009 large_ruin_1 #59 (CLOCKWISE_90), door (597,-50,551) | **6 cells**: x = 595..597, z = 550, y = -50..-49 — all `dripstone_block`, a 2-high, 3-long strip |
| seed 24015 large_ruin_1 #55 (COUNTERCLOCKWISE_90), door (-272,-50,-154) | **no connection within 14 blocks** — the door opens onto a drop, nothing to clear would fix it |

In template coordinates: medium_ruin_1 (-1, 1..2, 6..12); large_ruin_1 (-1, 1..2, 7..9) — **one block outside the
template box**. The cells lie inside the boxes of the neighbouring vanilla wall pieces
(`intact_horizontal_wall_1`, `ruined_horizontal_wall_stairs_4`); the dripstone is a natural feature that grew in the
city's open space. After Stage 24-I the survey is unchanged (`worldgen/i24-entrance-survey.json`): roof protection does
not affect entrances.

## Can the list-element overlay clear exterior cells? (tested, not assumed)

Code (26.1.2): `StructureTemplate.getBoundingBox` uses the declared `size` only, so cells stored outside the size do not
change the piece box, jigsaw collision or placement. But `StructureStart.placeInChunk` calls a piece only for chunks its
box intersects and the template write is clipped to that chunk, so an out-of-size cell is written only when it falls in
a chunk the box already touches.

Experiment (`tools/stage24i/entrance_experiment.py`, pack `experiment-entrance/datapack`, **not delivered**): an extra
element per affected module with the same declared size and `air` at the 14 / 6 out-of-size cells, processor
`rule: location #moreminecrafts:entrance_clearable → air, otherwise structure_void` + `block_ignore structure_void`
(writes only over natural terrain). Generated seeds 24005 and 24009 (`experiment-entrance/experiment-check.json`):

| check | result |
|---|---|
| city layout (positions, rotations, boxes) vs Stage 24-I | identical on both seeds |
| seed 24009 large_ruin_1 #59: 6 target cells | **6/6 cleared** |
| seed 24005 medium_ruin_1 #71: 14 target cells | 13 cleared, **1 refilled** by a `pointed_dripstone` tip (the dripstone features run in the same step and adapt to the cleared space) — the survey still needs 1 cell |
| other placements of the same modules (7) | no natural terrain removed in this run (cells were already air) |
| writable? — over all 46 medium_ruin_1 / large_ruin_1 placements in the 24-seed sweep | **3 placements (24003 #23, 24021 #55, 24024 #35) have every experiment cell in a chunk the piece box does not touch → never written** |

## Why it is not delivered

* **Unreliable** (stop condition): writing depends on where the chunk border falls (3/46 placements would get nothing)
  and same-step dripstone features can regrow into the cleared cells (24005).
* **Not targeted**: a pool element applies to every placement of the module; the cells are a fixed strip beside the
  wall, so it would clear natural terrain beside every medium_ruin_1 / large_ruin_1 in every world, not only where an
  entrance is blocked — the owner did not authorise clearing terrain merely because it is near a house.
* **Outside the piece**: the cells belong to neighbouring vanilla wall pieces' boxes.
* A reliable fix needs a different mechanism: a larger piece box (changes jigsaw collision → stop condition), or a
  post-generation pass / feature (the owner excluded a global excavator).

## Owner decisions

1. **24005 medium_ruin_1 (14 cells, 7-long strip) and 24009 large_ruin_1 (6 cells)** — options:
   * (a) accept as natural variation (113/116 entrances are open; the 24005 house is still reachable through its other
     openings? — see the city gameplay result in README);
   * (b) authorise a mechanism change: e.g. enlarge the house templates' declared size by one block on the door side so
     the clearance cells are inside the box (changes the box and jigsaw collision; requires re-running the full sweep
     and accepting possible layout changes);
   * (c) authorise a narrowly targeted structure-adjacent feature/post-process limited to "natural blocks in a
     2-high strip at a door" (not global, but a new system).
2. **24015 large_ruin_1** — the door opens onto a drop; there is no traversable connection to clear. Report only.
