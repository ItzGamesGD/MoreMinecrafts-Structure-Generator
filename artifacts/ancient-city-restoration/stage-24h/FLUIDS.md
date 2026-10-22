# Stage 24-H — fluid behaviour with interior clearance

Statuses: VERIFIED (measured on the real 26.1.2 server or in the generated worlds) / OWNER DECISION REQUIRED.

## What the overlay does to fluids (VERIFIED)

* The clearance template stores `minecraft:air` at mask cells. `StructureTemplate.placeInWorld` writes it with flags 18
  (no neighbour updates); `air` is not a `LiquidBlockContainer`, so a lava or water block already in a mask cell is
  simply replaced by air at placement. Live test, every module, lava-filled surroundings, game clock frozen:
  every mask cell is air right after placement (`live/live-clearance-report-lava-frozen.json`, 8/8 placements).
* Stored water (sauna pools) is never in a mask and is never written by the clearance element: 387/387 pool cells hold
  water in the Stage 24-H sweep (387/387 in 24-F, 386/387 in 24-G where a vanilla sculk catalyst took one cell).
* Block-rot holes are not written by any element, so they keep whatever was there — including lava or water.

## What the overlay cannot do (VERIFIED)

Fluids that arrive **after** the piece is placed are not affected:

1. **Lava/water springs** (`minecraft:spring_lava`, `spring_water`) are decorated in the `fluid_springs` step, after the
   city (`underground_decoration`). Their sources start flowing on the first fluid ticks.
2. **Flow through openings**: lava/water flows into a room through a cell the module does not close — a block removed by
   vanilla `block_rot` (a "decay hole") or an open side of open-air paving.
3. **Fluids already in the surrounding terrain** flow back into cleared cells. Live test with lava fill, after 1,200
   ticks: lava re-entered through decay holes and the open stored-air shafts of the towers (`analysis_after_1200_ticks`
   in `live/live-clearance-report.json`).

## Observed in the 24-seed sweep

| seed | structure | Stage 24-F / 24-G | Stage 24-H | source | entry path | class |
|---|---|---|---|---|---|---|
| 24008 | small_ruin_1 (CCW 90) | 5 / 6 lava cells in the room | **5 lava cells** in the room (76 of 81 mask cells air) | lava spring at (596,-39,1278), rock on 5 sides, 12 blocks above the house | falls down the outside and enters through the roof tile at template (4,4,4) / world (597,-47,1280) that `block_rot` removed | potential generation hazard |
| 24012 | sauna_1 (CW 90) | 24 water cells on the paving | 18 water cells on the paving | falling water from outside the open perimeter (no source in the piece) | exterior side of the open-air paving and two decay holes | environmental; pre-existing in 24-F/24-G |
| 24014 | sauna_1 (CW 90) | 5-cell lava column | 6-cell lava column | lava flow behind the masonry | not in any mask, touches no walkable cell | environmental (one more flow cell: timing) |

No other mask cell in 24 cities holds a fluid (58,720 mask cells checked).

## Narrowest viable correction (OWNER DECISION REQUIRED — not implemented)

Lava reaches a room only through blocks the building does not keep. The narrowest structure-local fix is a
**roof role** in the Stage 24-G protection overlay: keep (exempt from `block_rot`) the rottable roof cells that have a
room-interior cell directly below and open space above. Sizing (`worldgen/late-fluid-correction-sizing.json`):

| module | roof cells | rottable cells keeping vanilla decay |
|---|---|---|
| medium_ruin_1 | 64 | 77.5 % (was 100 %) |
| medium_ruin_2 | 78 | 72.0 % (was 85.0 %) |
| small_ruin_1 | 29 | 82.4 % (was 100 %) |
| small_ruin_2 | 11 | 89.8 % (was 100 %) |
| large_ruin_1, sauna, towers | 0 (tile-stair roof is not rottable / open air) | unchanged |

It would have stopped the seed-24008 lava (entry through a rotted roof tile). It cannot stop flow through doorways,
the open sauna, or springs opening inside the walls, and it removes roof decay the owner asked to keep — hence an
owner decision. Protecting the full wall-and-roof envelope would keep only 27–49 % of house decay (rejected).
Global alternatives (disabling springs, fluid ticks) change all world generation and are out of scope.
