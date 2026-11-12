# ST-03 group 1 (living + support) — B3-06

Houses B / C / D (Q01–Q10, Q08 variants) and the three support buildings, kitchen F18, smithy F19, cart shed F20 (Q11–Q17).
Base of the first build: `experiment/st03-b5a-house-a-formal` @ `62cec3eb5a503469ee940e798a68060070a0ff36`; this follow-up continues
`claude/moreminecrafts-setup-review-1ictwo` from `b0c8644`. **Experimental assets, owner visual review pending; not a merge candidate.**
`tools/seam01/data/st03_placements.json` is untouched (module ids, sizes, `air=include`, coordinates); `build.py` asserts every size.

Rebuild: `PYTHONPATH=. python experiments/st03-b6-group1/build.py`. Checks: `checks.py` (pinned 26.3 server, no client). Fire test: `fire_safety.py`.
Screenshots: `capture.py` (unmodified 26.3 client, Xvfb + Mesa lavapipe, F2). Local frame: +x east, +z south, y=0 floor; every door / open front faces south.

## Template ↔ facility (Q08) and loot table (Q16)

| Template | Module (size x,y,z) | Placement | Loot table id (chests + barrels) |
|---|---|---|---|
| `st03_house_b_f12.nbt` | `M-house_b` 9×10×7 | **F12** | `moreminecrafts:chests/pillager_headquarters/house_b` |
| `st03_house_b_f15.nbt` | `M-house_b` 9×10×7 | **F15** | same (one id per house type) |
| `st03_house_c_f13.nbt` | `M-house_c` 7×9×7 | **F13** | `moreminecrafts:chests/pillager_headquarters/house_c` |
| `st03_house_c_f16.nbt` | `M-house_c` 7×9×7 | **F16** | same |
| `st03_house_d.nbt` | `M-house_d` 7×9×7 | F17 | `…/house_d` |
| `st03_kitchen.nbt` | `M-kitchen` 9×11×9 | F18 | `…/kitchen` |
| `st03_smithy.nbt` | `M-smithy` 9×11×9 | F19 | `…/smithy` |
| `st03_cart_shed.nbt` | `M-cart_shed` 8×9×7 | F20 | `…/cart_shed` |

`st03_house_b.nbt` and `st03_house_c.nbt` are byte-identical copies of the F12 / F13 templates. The unchanged placement table still names one
file per module (`st03_house_b`, `st03_house_c`); using the F15 / F16 templates needs a per-placement file mapping there (not changed here).

Loot tables: `datapack/data/moreminecrafts/loot_table/chests/pillager_headquarters/{house_b,house_c,house_d,kitchen,smithy,cart_shed}.json`
— type `minecraft:chest`, `random_sequence` = own id, **`pools: []`** (weights and quantities are not approved; an opened container yields nothing).
Namespace/path follow the mod's `moreminecrafts:chests/<area>/<name>` convention. The files live here because the Beta repo is out of scope;
the runtime task copies them into the mod's resources.

Only `chest` and `barrel` carry a table (the two loot-capable containers): 25 containers across the 8 templates, each with exactly one `LootTable`
tag and no `Items`. Furnaces, blast furnace, smoker, campfire, lectern, banners and all cosmetic blocks (hay, coal blocks, boards, bars, planters, potted
plants) carry none.

## Changes in this follow-up

1. **Loot binding** — exporter option `[options] loot_table` (below); every template is exported with its facility's id.
2. **Kitchen fire safety** — found a real hazard and fixed it (see the test table). Final design has no fire block at all.
3. **Exporter allow-list** — smoker, campfire, lectern and the 15 coloured `*_wall_banner` blocks. Kitchen restored: smoker on the counter,
   lit campfire hearth (stone floor, flue open up through the roof) instead of netherrack + fire. Standing banners stay refused (no vanilla evidence).
4. **Q08 variants** — F15 (house B) and F16 (house C) as separate templates; same shell, bounds, footprint, door, windows, roof and room program
   (beds, crafting table, furnace, barrels, chest in the same cells). Differences are decoration only:
   - **F12 / F13** (unchanged look): F12 has window lanterns, an illager banner over the door, bookshelf wall, brown rug, red + blue beds. F13 has a
     wall-capped chimney, brown rug, bookshelves, a ridge lantern.
   - **F15**: black banner, lanterns at the porch ends, two planters and a hay bale on the porch, study corner (lectern + short shelf), blue rug, two
     hanging lanterns, blue + red beds. **F16**: campfire smoking on the chimney top, lectern + one-bay shelf, grey rug, red wall banner, blue bed, lantern by the bed.

## Exporter change (tools/structure_export) and what it affects

- `reference/build_block_entities.py`: new allow-list entries (all evidence-checked against the 1511 vanilla templates: campfire 128, lectern 11, smoker 9
  occurrences) and a `loot_table` flag on `chest` / `barrel` (vanilla templates carry `LootTable` on 301 of 424 chests and 207 of 226 barrels).
  `reference/block_entities-26.3.json` regenerated; the previous 5 entries are unchanged.
- `Config.loot_table` (optional, default `None`) read from `[options] loot_table`, validated as a resource id; `block_entities.handler/expected_nbt`
  write one `LootTable` string on chests and barrels only; `verify(..., loot_table=…)` accepts exactly that id and still rejects any other contents;
  `live.block_entity_failures` accepts the bound `LootTable` (matched exactly) and still fails on any `Items[0]`.
- `tools/seam01/export.py::export_module` gained optional `loot_table` and `file` arguments (defaults keep the old behaviour).
- Tests: `tests/test_structure_block_entities.py` +28 cases (30 → 58; new blocks, state restrictions, coloured banners, loot only on chest/barrel, verifier needs the
  declared id exactly, option validation, no-loot default). 58 pass.
- **Other behaviour affected:** (a) the five blocks above, previously `UnsupportedFeature`, now convert; (b) the verifier and live check are stricter
  about a `LootTable` only when a template declares one, otherwise unchanged; (c) no other tool in the repository reads the allow-list
  (stage24* tools only read block entities from sources). Pre-existing, unrelated: `test_sample_is_reproducible_and_matches_committed_outputs` and
  `test_committed_testbed_exports_are_reproducible` fail on the base commit as well (gzip header OS byte differs in this environment);
  `tests/test_phase3_watchtower.py` needs the `mcbuild` module (not installed here).

## Result (PASS / FAIL / UNTESTED) — newly run on the current NBT hashes

| Item | Result | Evidence |
|---|---|---|
| Size = approved module size, `air=include`, every cell vs source, block-entity data incl. LootTable | PASS | independent verifier, 8 templates, 0 mismatches (`check-result.json`) |
| Every authored block state in the template | PASS | 2,392 cells, 0 mismatches |
| Strict placement on the pinned 26.3 server, all four rotations, every cell compared | PASS | 8 templates × 4 rotations = 32 placements, 0 failures |
| Walk-in access; every workstation / bed / container has a reachable neighbour column | PASS | BFS; 1 blocked item found and fixed (F15 stool/lectern layout) |
| **Q16:** every chest / barrel carries its facility's `LootTable` in the game; exactly one tag; no `Items` | PASS | `data get block` on all 25 loot containers + `block_entity_failures` on all 40 block entities in all four rotations, 0 failures |
| **Q16:** the six tables load on the server and give nothing | PASS | `loot replace block … loot <id>` → "Dropped 0 items" for all 25 containers |
| **Q16:** no duplicated rolls; one id per facility; cosmetic blocks loot-free | PASS | table files have empty pools and unique `random_sequence`; each id used by one facility; BE data checked on the template |
| Containers / smoker / furnaces take items | PASS | 33 containers accept `item replace`, read back |
| **Fire safety, kitchen before the fix** | FAIL (fixed) | as placed the template's fire never ticks (age stays 0) → no spread (80,000-tick sprint). But when relit (a player re-lights it) the hearth fire ignited the roof stair left inside the flue at (4,7,1) within 60,000 ticks (`fire-safety-before-fix-relit.json`). Positive controls (fire next to planks; plank 4 above and 1 beside the fire) burned |
| **Fire safety, after the fix** | PASS | flue column cleared of the roof stair, plate behind the flue (3..5,5,0) made stone; relit fire for 80,000 ticks changes no cell (`fire-safety-after-fix-relit.json`) |
| **Fire safety, final kitchen** | PASS | no `fire` block in the template (campfire hearth; a campfire does not spread fire); 40,000-tick sprint with game fire rules on changes no cell (`fire-safety-final-kitchen.json`) |
| Q08: variants have identical size, door, beds, container/workstation cells, shell | PASS | F12↔F15: 27 differing cells (4 = bed colour); F13↔F16: 11 (2 = bed colour); all decoration |
| Appearance vs approved Q07 (orderly, lived-in, house-specific) | PASS with notes | real 26.3 screenshots; owner visual review pending |
| Look of unchanged modules vs `b0c8644` | PASS | block states identical (F12, F13, house D, smithy, cart shed); only the LootTable tags are new → no recapture |
| Screenshots of changed modules (kitchen, F15, F16) | PASS | 27 new in-game F2 views, unmodified client |
| Facing toward existing roads; neighbours / terrain; entity pathing | UNTESTED | no road data, no neighbouring NBT; all doors south as before |
| Loot contents, weights, quantities, premium pool | not in scope | tables are empty by design |

Screenshots: `screenshots/` + `capture-info.json` (`captured_nbt_sha256` vs `current_nbt_sha256`). F12, F13, house D, smithy and cart shed images are from
the previous run (block states proven identical above; the only later change is the invisible LootTable tag). Kitchen, F15 and F16 were recaptured.

## Not done / reported

- Standing banners remain refused by the allow-list (no vanilla template evidence); only coloured **wall** banners were added.
- The placement table (`st03_placements.json`) maps both houses' placements to one file per module; per-placement file names are an integration step.
- The loot-table JSON files must be copied into the mod's data (Beta repo, out of scope).
- Lecterns are placed without a book (`has_book=false` is the only allowed state).
- The fire test needed `fire_spread_radius_around_player = -1` (26.3's replacement for `doFireTick`; default 128 blocks around a player) because the headless
  server has no player; this equals a player standing next to the kitchen.
