# Stage 24-G — Ancient City generation integrity and functional protection

Baseline: Stage 24-F Draft PR #26, head `b4f372e6eab2dc3160c7e883c0612547aada11ea` (CI run 39339262228). The
architectural authority is the Stage 24-F final candidate set; **all eight structure NBTs are byte-identical to it**
(large_ruin_1 Option C 17×14×17, medium_ruin_2 Option A 16×8×11, the six others Stage 24-C).

## Summary

| | Stage 24-F | Stage 24-G |
|---|---|---|
| protected cells missing after real generation (24 seeds, 5,006 cell instances) | 186 (+8 replaced) | **0** (5 replaced by later ore features, still solid) |
| doors standing on an unwritten cell (medium_ruin_1, small_ruin_1) | 48 / 48 | **0 / 48** |
| decorative cells removed by vanilla decay | 3,271 / 64,846 (5.04 %) | 3,271 / 64,846 (5.04 %) |
| soul lanterns removed / bricks cracked | 25 / 17,458 | 25 / 17,458 |
| city layouts identical to Stage 24-F (2,160 pieces) | — | 24 / 24 |
| bounding-box overlaps | 0 | 0 |
| live `/place jigsaw`, 8 modules × 4 rotations: protected cells lost | 58 in 29 of 63 placements | **0 in 59 placements** |
| player simulation on decayed placements, 4 rotations | — | **684 / 684** |

## What was wrong (`INVESTIGATION.md`)

1. `block_rot` (integrity 0.95, `#minecraft:ancient_city_replaceable`) removes 5 % of deepslate bricks/tiles/walls/
   slabs/plain deepslate with a random seeded only by the world position; removed cells are simply not written. That
   took railings, deck floors, upper-storey floors and ladder backing blocks. Adding blocks to a tag would not help:
   the tag is shared by the whole city and cannot tell a railing from decorative masonry.
2. `medium_ruin_1` and `small_ruin_1` stand their door on the module's entrance jigsaw, whose (vanilla) `final_state`
   is `structure_void`; `JigsawReplacementProcessor` returns `null`, so the cell under the door is never written. In
   seed 24007 the lower door half was gone (upper half floating) in both the Stage 24-C and 24-F worlds.
3. Rooms store no air (neither do the vanilla ruins), so terrain and fluids generated in those cells stay there.

## What changed (`PROTECTION-POLICY.md`)

* Role-based inventory (`tools/stage24g/roles.py`): doors + the block under them, ladders + the block they hang on,
  floors of reachable walkable cells where a hole falls ≥ 2, and the foot-level edge barrier where a walk-out falls ≥ 2.
  Lanterns, ground-floor floors, masonry above foot level, pillars, roofs and trim keep vanilla decay.
* Mechanism: six entries of `minecraft:ancient_city/structures` become `list_pool_element`s
  `[unchanged Stage 24-F element, protection overlay]`. The overlay template contains only the protected cells the main
  pass can lose (143 cells in total) and uses `ancient_city_generic_degradation` minus `block_rot`.
  `ListPoolElement` takes jigsaws from the first element and the union box, so assembly is unchanged — verified
  24/24. No vanilla processor list, tag or other pool entry is changed; large_ruin_1 and small_ruin_2 need no overlay.
* Two cells get a block the template does not write: the door supports of medium_ruin_1 (0,0,6) and small_ruin_1
  (0,0,3) get `deepslate_bricks` (their neighbouring floor), as the approved policy's "structural supports". The
  jigsaw blocks themselves are unchanged.

## Datapack

`datapack/` is the complete Stage 24-G datapack (the eight approved NBTs, six overlays, the processor list
`moreminecrafts:ancient_city_functional_protection`, the `ancient_city/structures` pool). Rebuild:
`vendor/mcbuild/.venv/bin/python tools/stage24g/build.py` (deterministic; CI checks it).

## Evidence

| path | content |
|---|---|
| `INVESTIGATION.md` | engine mechanism, confirmed vs hypothesis |
| `PROTECTION-POLICY.md`, `protection/` | exact policy, per-module table, every protected cell with its reason, build manifest |
| `investigation/` | JVM RNG cross-check, Stage 24-F processor replay, survival and terrain of the 24-F sweep |
| `live/live-processing-report.json` | real-server `/place jigsaw` of the 24-G and 24-F entries, 8 modules × 4 rotations |
| `live/gameplay/` | mineflayer results on decayed placements, 8 modules × 4 rotations |
| `worldgen/` | 24-seed sweep manifests, analysis, processor replay, functional survival, terrain classification, `g24-summary.json`, `g24-issues.json` (every failure with seed, coordinates, structure, root cause) |
| `TERRAIN-CLASSIFICATION.md` | every terrain/fluid intersection classified |
| `VALIDATION-MATRIX.md` | all checks with status |
| `gallery/` | 70 before/after images: entrances, ladders, decks, railings, decorative decay, the 24004 terrain contact |
| `OWNER-DECISION-interior-terrain.md` | options for terrain/fluids inside rooms |

The gallery shows real generated world blocks of the same piece in the Stage 24-F and Stage 24-G worlds rendered with the
26.1.2 block models — **simulated visual evidence, not Minecraft-client screenshots. Client verification: VISUAL PENDING.**

## Remaining limitations

* **OWNER DECISION REQUIRED** — terrain and fluids inside rooms: seed 24005 medium_ruin_1 buried by dripstone (124
  walkable cells), seed 24009 large_ruin_1 dripstone cluster in the hall (12), seed 24008 small_ruin_1 lava in the
  room (6), seed 24014 sauna_1 lava column behind masonry (5). Unchanged from Stage 24-C/24-F.
* Later ore features can still turn plain-deepslate blocks into tuff/gravel/ore after placement (5 large_pillar_1
  parapet cells in this sweep). They stay solid, so the parapet still works, but they cannot be prevented from the structure.
* Vanilla sculk patches cover many protected floors and railings (`present_weathered`); sculk is a full block and keeps
  the function.
* The exact update that removed the seed-24007 door lower half is a hypothesis; the fix removes its precondition
  (no sturdy support) and the door is present in the Stage 24-G world.
* 12 sauna sculk jigsaws stay unconnected (vanilla pool resolves to nothing), as in Stage 24-C/24-F.
* Minecraft-client visual verification: VISUAL PENDING.
* Not started, by instruction: city-wide integration, roads, plazas, monuments.
