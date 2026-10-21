# Stage 24-I — Ancient City roof protection & entrance accessibility

Baseline: Stage 24-H Draft PR #31, head `568ad3ffe77b9b7bfaf3ea66d3c8e01b199ce0e1` (CI run 39481676168, green).
The eight approved structure NBTs are byte-identical to Stage 24-F; every Stage 24-G and Stage 24-H file is unchanged.

| part | status |
|---|---|
| A — roof protection | **VERIFIED** (delivered) |
| B — entrance clearance | **PARTIAL / OWNER DECISION REQUIRED** — investigated and tested; no reliable narrow mechanism, nothing delivered |
| C — regression preservation | **VERIFIED** |
| D — real generation verification | **VERIFIED** (bot checks; client gameplay not performed) |
| client visuals | **VISUAL PENDING** |

## Result

| | Stage 24-H | Stage 24-I |
|---|---|---|
| protected roof cells (medium_ruin_1 / medium_ruin_2 / small_ruin_1 / small_ruin_2) | 0 | 64 / 78 / 29 / 11 (rule-derived; equal to the 24-H estimate) |
| roof cells present in the 24-seed sweep | — | 4,170 / 4,170 |
| decorative `block_rot` losses (24 seeds) | 3,271 | **3,067 (−204, −6.2 %)**; all other decay at identical positions |
| seed 24008 small_ruin_1: lava in the room | 5 | **0** (9 lava cells remain outside the template) |
| seed 24008: bot enters from the city path, reaches bed, sleeps, opens barrel | no | **yes** |
| city layouts identical (2,160 pieces) / overlaps | — | 24/24 / 0 |
| protected cells missing | 0 / 5,006 | 0 / 9,176 (incl. roof) |
| sauna pool water | 387/387 | 387/387 |
| live placements 8 modules × 4 rotations / buried bot | 32/32 | 86 placements 0 violations / 32/32 all steps |
| house entrances open to the city (116) | 113 | 113 — unchanged; 2 blocked by dripstone outside the box, 1 opens onto a drop |
| terrain removed beyond the 24-H masks | — | **none** |

## How the roof protection works

See `ROOF.md`. One more element in each roofed `list_pool_element` — `moreminecrafts:ancient_city/roof/<module>`
with the Stage 24-G processor list (vanilla degradation without `block_rot`) — inserted before the Stage 24-H clearance
element. The roof template stores only the roof cells (rottable, directly above a room interior, open above). Same
size, same box, same jigsaws.

## Entrances

See `ENTRANCES.md`. The obstruction is outside the house's piece box (in the neighbouring wall pieces' boxes). An
out-of-size overlay cell does not change the box or jigsaws, but the engine writes it only in chunks the box already
touches: in 3 of 46 sweep placements nothing would be written, and at 24005 a dripstone feature regrew into the cleared
strip. The experiment pack is kept as evidence (`experiment-entrance/`) and is **not** part of the deliverable.

## Evidence

| path | content |
|---|---|
| `ROOF.md`, `roof/` | rule, cells, build manifest, remaining decay openings, inventory incl. roof |
| `ENTRANCES.md`, `investigation/`, `experiment-entrance/` | entrance survey, overlay experiment pack, generated-world check |
| `live/live-roof-report*.json` | real-server `/place jigsaw`, buried, 8 modules × 4 rotations, roof continuity, 24-H controls |
| `live/gameplay-buried/` | bot in buried placements, 8 modules × 4 rotations |
| `live/city-gameplay/` | bot in the generated cities (24008 24-H vs 24-I; 24005/24009 24-H vs 24-I vs experiment; open-door controls); `-approach` = start on the real ground outside and jump the door step |
| `live/entrance-nav/` | bot from the open city path through the door (24005/24009 blocked and experiment, 24008 24-H vs 24-I, open-door controls) |
| `worldgen/` | 24-seed sweep: manifests, analysis, survival, processor replay, 24-H vs 24-I cell comparison, terrain classes, entrance survey |
| `VALIDATION-MATRIX.md` | every check with status |
| `gallery/` | headless renders |

Gallery images are headless renders of real generated blocks or template NBTs — **not Minecraft-client screenshots.
Client verification: VISUAL PENDING.** Bot results are scripted mineflayer checks, not client gameplay.

## Reproduce

```
vendor/mcbuild/.venv/bin/python tools/stage24i/build.py                 # roof inventory + datapack
vendor/mcbuild/.venv/bin/python tools/stage24i/entrance_experiment.py   # experiment pack (evidence only)
vendor/mcbuild/.venv/bin/python -m pytest tests/test_stage24i_roof.py
vendor/mcbuild/.venv/bin/python tools/stage24i/live.py && tools/stage24i/check_live.py stage-24i/live/live-roof-report.json
tools/stage24c/worldgen.py --seeds 24001..24024 --variants i24 --pack stage-24i/datapack --out stage-24i/worldgen
tools/stage24i/compare.py; tools/stage24i/entrances.py --variant i24 ...; tools/stage24i/experiment_check.py
tools/stage24h/gameplay_buried.py --stage i24; tools/stage24h/city_gameplay.py --approach ...; tools/stage24i/entrance_nav.py ...
tools/stage24i/gallery.py
```

## Owner decisions

1. **Entrances 24005 medium_ruin_1 (14 cells) and 24009 large_ruin_1 (6 cells)** — options in `ENTRANCES.md`
   (accept / enlarge the house box on the door side / a targeted door-strip feature). Each needs approval because it
   changes jigsaw collision or adds a new generation system.
2. **Entrance 24015 large_ruin_1** — door opens onto a drop; nothing to clear. Report only.
3. **Fluids** — roof protection fixes the documented 24008 intrusion; walls, floors and doorways still decay or stay
   open as in vanilla, so later springs can still reach interiors elsewhere. No universal lava immunity.
