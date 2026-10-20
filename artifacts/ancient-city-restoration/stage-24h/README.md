# Stage 24-H — Ancient City interior terrain clearance (owner Option A)

Baseline: Stage 24-G Draft PR #28, head `33b96c615314a23b01b39e21551820b1c67e6319` (CI run 39410115991).
The eight approved structure NBTs are byte-identical to Stage 24-F; the Stage 24-G protection files are unchanged.

## Result

| | Stage 24-G | Stage 24-H |
|---|---|---|
| terrain cells blocking a walkable cell (24 seeds) | 136 | **0** |
| seed 24005 medium_ruin_1: dripstone in the house | 189 | **0** — bot reaches the bed, sleeps, opens the barrel in the generated city |
| seed 24009 large_ruin_1: dripstone in the courtyard | 13 | **0** |
| seed 24008 small_ruin_1: lava in the room | 6 | 5 — late spring through a rotted roof tile (owner decision) |
| protected cells missing (5,006) | 0 | 0 |
| decorative block-rot cells | 3,271 | 3,271, identical positions |
| city layouts identical (2,160 pieces) / overlaps | — | 24/24 / 0 |
| sauna pool water | 386/387 | 387/387 |
| buried placements, simulated player, 8 modules × 4 rotations | — | 32/32 all steps |

## How it works

* **Masks** (`MASK.md`, `mask/interior-masks.json`, `tools/stage24h/mask.py`): every template cell gets one class.
  Cleared: room interiors (enclosed, roofed; floor to ceiling, spread over furniture), enclosed walkways (open courtyards:
  body + one headroom cell only), the module's own paving outside an enclosure (body height), step headroom, bed/chest
  tops, pool headroom, entrance thresholds (≤ 2 cells from a wall-gap entrance to the box edge). Never cleared: any
  stored cell (architecture, jigsaws, stored air/water), exterior, decorative voids. "Enclosed" = not reachable from the
  box edge in its layer without passing masonry or a door (doorless arches are closed for this test only).
* **Generation** (`tools/stage24h/build.py`): each restored pool entry gets one more list element,
  `moreminecrafts:ancient_city/interior/<module>` with processor list `moreminecrafts:ancient_city_interior_clearance`
  (`protected_blocks #features_cannot_replace` only). The template stores `air` at the mask cells and nothing else.
* **Semantics** (26.1.2 code + live tests): `ListPoolElement` places its elements in order at the same position and
  rotation, jigsaws from the first element only, box = union (identical sizes). `StructureTemplate.placeInWorld` writes
  stored air like any block (only structure blocks are ignored), flags 18, no shape/neighbour updates, so the overlay
  replaces terrain or fluid in mask cells and nothing else; `protected_blocks` keeps chests, spawners, trial spawners,
  vaults, bedrock, end portal frames and reinforced deepslate already in the world; block entities in mask cells (only
  possible from earlier world content) are removed with their block. The mask never holds a stored cell, so the
  building's own blocks cannot be erased; the template cannot reach outside the piece box, and the 24-seed sweep has 0
  box overlaps, so adjacent city pieces are not touched.

## Evidence

| path | content |
|---|---|
| `MASK.md`, `mask/` | rules, per-module layer maps, every cleared cell, build manifest |
| `live/live-clearance-report*.json` | real-server `/place jigsaw` on buried placements (deepslate / lava), 8 modules × 4 rotations |
| `live/gameplay-buried/` | simulated player in buried placements, 8 modules × 4 rotations |
| `live/city-gameplay/` | simulated player inside the generated cities of seeds 24005, 24009, 24008 (24-G vs 24-H) |
| `worldgen/` | 24-seed sweep manifests, analysis, survival, processor replay, F/G/H cell comparison, terrain classes, fluid traces, reproducibility, summary, issue register |
| `FLUIDS.md` | fluid behaviour and the narrowest correction |
| `VALIDATION-MATRIX.md` | every check with status |
| `gallery/` | before/after (24-G vs 24-H) of the four cases with cutaways, mask visualisations |

Gallery images are headless renders of real generated blocks or template NBTs — **not Minecraft-client screenshots.
Client verification: VISUAL PENDING.**

## Outstanding issues and owner decisions

1. **OWNER DECISION — late lava/water (seed 24008).** Springs are decorated after the city and their fluid enters through
   blocks vanilla decay removed. Narrowest correction: a roof role in the Stage 24-G overlay (64/78/29/11 roof cells on
   medium_ruin_1/medium_ruin_2/small_ruin_1/small_ruin_2; their decay share drops to 77.5/72.0/82.4/89.8 %). Not
   implemented — it reduces decay the owner asked to keep. See `FLUIDS.md`.
2. **OWNER DECISION — entrances blocked outside the piece box (seeds 24005, 24009).** In dripstone-cave cities the door
   opens onto solid dripstone in the city-path space beyond the box; the interior is usable once inside. Clearing it
   would excavate exterior/city space (not authorised; city-wide work is out of scope).
3. **Side effect — natural features adapt to cleared rooms.** Dripstone features are decorated in the same step as the
   city and, in cross-chunk order, after parts of it; around the cleared seed-24005 house they grow differently
   (1,532 natural blocks within 12 blocks, reproducible on a second run). No architecture is involved; generation also
   shows run-to-run noise (`worldgen/reproducibility.json`).
4. **Vanilla sculk** grows into cleared rooms (sensors, shriekers, catalysts, veins) after the city is placed.
5. **Tower deck headroom** lies above the large watchtower's box; never obstructed in the sweep (192/192 air), but
   unclearable without a taller box (stop condition).
6. Sauna water from outside the open perimeter (seed 24012) flows onto the paving as in 24-F/24-G.
7. Minecraft-client visual verification: VISUAL PENDING.
