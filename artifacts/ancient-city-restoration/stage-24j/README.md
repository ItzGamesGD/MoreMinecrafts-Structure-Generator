# Stage 24-J — Ancient City watchtower architectural review

Baseline: Stage 24-I Draft PR #33, head `73729f786167dcd2dfe2e187b96ccd8d1f7dbfd3` (CI green).
**Proposals only.** The approved Stage 24-F tower NBTs, the Stage 24-G/24-H/24-I packs and every other module are
unchanged. No option is chosen; the owner selects (or rejects) one per tower.

Owner decisions on the three blocked entrances are recorded in `../DESIGN-DECISIONS.md` (deferred, known
accessibility issues).

## The alternatives

All four options keep the template size, so the piece bounding box, jigsaw placement and collision behaviour are
unchanged; no height or footprint expansion is proposed. Jigsaws and block entities (incl. the medium-pillar skeleton
skull and barrel) are identical; the ladder shaft below each deck is untouched.

### large_pillar_1 (6 × 15 × 6)

The approved top is a solid 6×6 deepslate slab over a corbelled cap: it reads as a heavy lid, the player stands on top
of it (feet y15, above the template) and **the deck has no railing — 30 open drop edges** (static check).

| | current | A — open lookout | B — roofed belvedere |
|---|---|---|---|
| idea | solid capstone | the slab becomes a railed parapet (polished-deepslate walls between chiseled corner merlons) on the existing corbelled cap | floor lowered to y10 on the reused corbel ring; waist railing at y11; two-block open viewing band (y12–13) between polished-basalt corner posts; low tiled roof with stair eaves at y14; the basalt ladder spine rises to the roof as a central post; soul lanterns hang from the roof |
| deck feet / standable cells | y15 / 32 | y14 / 15 | y11 / 14 |
| fall protection | **30 open drops** | railing on every side | railing on every side |
| headroom above the template | 32 cells | 15 cells (one block lower than today) | **0** — deck and headroom inside the template |
| sightline | unobstructed, unprotected | over a 1.5-block railing, 360° | through a 2-block band, 360°, sheltered |
| changed cells / decay-eligible blocks | – / 142 | 47 / 95 | 148 / 99 |

### medium_pillar_1 (7 × 11 × 8)

The approved deck (5×6 outline, 11 standable cells, wall parapet) is recognisable; above it, loose vanilla deepslate
fragments project west, east and north and a deepslate arm floats at y10 over the south-west.

| | current | A — corbelled crown | B — south-west gallery |
|---|---|---|---|
| idea | parapet deck + loose fragments | fragments removed; corbel ring on the free footprint ring (x0/x6, z0/z7) widens the deck to the full 7×8 outline; wall parapet; two-block corner merlons, the south-west one left broken | fragments removed; the west/south projection becomes a cantilevered L-shaped gallery on corbels; north and east keep the existing parapet; a two-block corner post marks the south-west corner — deliberately asymmetric |
| deck feet / standable cells | y9 / 11 | y9 / 29 | y9 / 19 |
| fall protection | railing | railing on every side | railing on every side |
| changed cells / decay-eligible blocks | – / 196 | 79 / 184 | 46 / 183 |

Full numbers: `DIMENSIONS-MANIFEST.json`, `static-checks.json`.

## Verification

| check | result | evidence |
|---|---|---|
| template size, piece box, jigsaws, block entities | unchanged for all four options | `static-checks.json`, tests |
| ladder continuity (every rung backed) | continuous to the hatch in all options | `static-checks.json` |
| deck reachable from the ladder exit, two-block headroom | all expected deck cells reachable; large A keeps 15 head cells above the template (as today, one block lower) | `static-checks.json` |
| fall protection | 0 open drops in all options (approved large tower: 30) | `static-checks.json` |
| block states | all valid against the vanilla 26.1.2 block report (CI regenerates it from the pinned jar) | `static-checks.json`, CI |
| exact placement, 4 rotations, real 26.1.2 server | 24/24 placements (6 towers × 4 rotations) match the rotated template, 0 mismatching cells | `live/live-report.json` |
| bot: outside → ladder → deck → every deck edge, 4 rotations | **all four options: 16/16 runs, every step** (large A and B 37/37, medium A 49/49, medium B 39/39); approved medium tower 31/31; approved large tower: every deck-edge walk **falls 15 blocks** (no railing) — its `step_onto_deck` failure is this generic scenario aiming at the slab surface (the tower's own Stage 24-C scenario reaches it through the hatch pit and passed 32/32 in Stage 24-I) | `live/live-report.json`, `live/bot-*.json`, `tools/stage24j/check_live.py` |

Bot = mineflayer simulated player on a real server — **not Minecraft-client gameplay**. Renders are headless
block-model renders — **not client screenshots; client visual verification PENDING.**

## Gallery (`gallery/`)

Per tower, current | A | B at identical camera and scale (34 px/block; close-ups 56 px/block): front and rear
three-quarter, two side silhouettes, elevated view, observation-platform close-up with a player figure, interior
access cutaway, and a changed-cells view (orange = new or different block, red = removed). `overview-front34.jpg` and
`overview-side-a.jpg` show both towers and all options in one frame at the same scale.

## If an option is approved (not done here)

* Replace the approved NBT of that tower and rebuild the derived inventories from the new geometry: Stage 24-G
  protection roles (railing and ladder cells move: large A 7, large B 10, medium A 13, medium B 9 approved protected cells
  change), the Stage 24-H interior mask (new deck headroom) and the Stage 24-I roof rule; then rerun the 24-seed
  sweep, live placement and bot tests.
* Large B's roof is open at the sides, so the Stage 24-I roof rule (roofs over *enclosed* rooms) would not protect it;
  vanilla decay would open holes in it unless the owner extends roof protection to it.

## Owner decisions

1. large_pillar_1: approve A, approve B, or keep the approved tower (note: no deck railing today).
2. medium_pillar_1: approve A, approve B, or keep the approved tower.
3. Any refinement (materials, broken-merlon placement, lantern positions) before implementation.
