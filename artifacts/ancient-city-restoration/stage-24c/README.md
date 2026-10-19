# Stage 24-C — Ancient City restoration: visual & live validation

* Implementation baseline (PR #10 HEAD, verified unchanged on the remote): `b750da2e06cb646c63283603a7fec4ee93a33db7`
* Stacked on PR #10's branch `stage-24b-eight-module-restoration`. PR #10, PR #8 and PR #4 are **not** modified. Nothing is merged; every PR stays Draft.
* Validation HEAD: see the PR description (the final commit SHA is quoted there).
* Runtime: **real Minecraft Java 26.1.2 dedicated server** (jar sha1 `97ccd4c0…0bc51`, JDK 25), driven over RCON. Player behaviour was
  simulated with a **mineflayer** bot (protocol 775). **No Minecraft client with rendering was run → no in-game screenshots exist.**

Evidence index: `EVIDENCE-TABLES.md` (generated), `DEFECTS.md`, `VERIFICATION-MATRIX.md`, `MANUAL-TEST-PROCEDURE.md`,
`placement/`, `gameplay/`, `worldgen/` (24 seeds), `visual/<module>/`. Re-run: `.github/workflows/stage24c-validation.yml`
or `tools/stage24c/{placement,gameplay,worldgen,worldgen_analyze,preservation,render_review,make_report}.py`.

## Headline

The static Stage 24-B checks reported every module `GEOMETRY VERIFIED`. Placing the actual NBTs on a real server and walking them
with a simulated player exposed **reproducible defects (five repair groups below)** that static geometry could not see.
All were repaired minimally in the layout generator, regenerated, and covered by regression tests that fail on PR #10's NBTs and pass now.

## Status (categories are deliberately not collapsed)

| module | CODE | GEOMETRY | VISUAL | LIVE (server + simulated player) | WORLDGEN | OWNER |
|---|---|---|---|---|---|---|
| `large_ruin_1` | VERIFIED | VERIFIED | PENDING (note V1) | PASS 20/20 (+lantern fix) | PASS (20 pieces) | REVIEW PENDING |
| `medium_ruin_1` | VERIFIED | VERIFIED | PENDING | PASS 17/17 | PASS (26 pieces) | REVIEW PENDING |
| `medium_ruin_2` | VERIFIED | VERIFIED (Y=8) | PENDING (note V1) | PASS 28/28 after stair-headroom repair; **upper floor genuinely usable** (walked up/down, slept upstairs, opened upstairs barrel) | **PASS** (20 pieces, 0 overlaps, placements identical to vanilla in 24/24 cities) | REVIEW PENDING |
| `small_ruin_1` | VERIFIED | VERIFIED | PENDING | PASS 17/17 | PASS (22) | REVIEW PENDING |
| `small_ruin_2` | VERIFIED | VERIFIED | PENDING | PASS 17/17 after bed repair | PASS (28) | REVIEW PENDING |
| `sauna_1` | VERIFIED | VERIFIED | PENDING (opening at (11,2,33) needs owner eyes) | PASS 12/12; 3 chests roll loot; both basins swimmable; 43/43 water, 0 stray after 1200 ticks | PASS (9 pieces, only 9 samples) | REVIEW PENDING |
| `large_pillar_1` | VERIFIED | VERIFIED | PENDING | PASS 13/13 after ladder repairs | PASS (32) | REVIEW PENDING |
| `medium_pillar_1` | VERIFIED | VERIFIED | PENDING | PASS 47/47 after parapet repair; east ladder kept (climbs fine) | PASS (35) | REVIEW PENDING |

* **VISUAL PENDING everywhere**: renders are generated from the NBT block states by the vendored software renderer (low fidelity: no wall/stair
  shapes, no lighting). I looked at them but that is not owner approval. Observations for the owner (not repaired, role/design is theirs):
  * V1 (P3): `large_ruin_1` and `medium_ruin_2` read as flat tile-slab roofs from outside; the five houses are differentiated mainly by footprint.
  * V2 (P3): the `medium_ruin_2` upper floor is not visible from outside except as a taller east block.
* **Not claimed**: client screenshots, real pointer/keyboard controls, in-game lighting appearance. See `MANUAL-TEST-PROCEDURE.md`.
* The simulated player is a re-implementation of client physics. I checked it against a plain open-air stair run (it climbs) and it
  was blocked by the real headroom defect in `medium_ruin_2`, so it is a meaningful, but not a vanilla-client, oracle.

## Repairs (each demonstrated live on PR #10's NBT; see `DEFECTS.md`)

1. 15 soul lanterns `hanging=false` with no floor popped off on placement (7 modules). → hang from ceiling / stand on wall tops (sauna).
2. `large_pillar_1`: ladders y1–2 faced east into the open entrance tunnel and popped → ladder mounted on the basalt support (faces west);
   ladder also stopped 1 block under the deck → extended through the hatch to y=13. Climb now reaches deck.
3. `small_ruin_2`: both bed halves sat under wall blocks ("This bed is obstructed") → bed moved onto the open north row.
4. `medium_ruin_2`: stair run needed 2–3 clear cells of headroom (roof tile at (4,4,5),(5,4,5), wall at (7,6,5)); upper floor was unreachable → cleared.
5. `medium_pillar_1`: deck had no edge protection (12 of 22 probes fell 8 blocks) → 18-segment `polished_deepslate_wall` parapet at y=9
   (polished deepslate is outside `#ancient_city_replaceable`, so the vanilla 5 % block_rot cannot punch holes: 0/630 lost vs 27/630 for tile walls).

Constraints respected: footprints and heights unchanged (medium_ruin_2 stays 16×8×11), all jigsaws / skull / chests / loot NBT / 43 waters untouched
(`placement/preservation-report.json`: source = restored = live for all 15 block entities), no roads/city/Warden/PR #4 changes.

## Remaining risks (documented, not masked)

* P3 vanilla decay still removes ~5 % of lanterns and (rarely) supporting blocks: 1/52 `medium_ruin_1` doors and 20 of ~440 lanterns lost across 192 generated pieces.
* P3 `large_pillar_1` deck ring is rot-eligible `deepslate`; a hole in the 2-thick ring is unlikely to open a drop but was not probed under real generation.
* P3 seed 24005: one `medium_ruin_1` is buried in a dripstone cave (190/191 free cells are `dripstone_block`) — vanilla terrain adaptation, same for the original NBT.
* Synthetic setup: restored NBTs were registered by overriding `data/minecraft/structure/ancient_city/structures/*.nbt` in a datapack; vanilla pool weights
  decide selection, so pieces appear naturally but rarely (sauna only 9 times in 24 cities). Pieces are sampled from a 256×256-block forceload around each city.
