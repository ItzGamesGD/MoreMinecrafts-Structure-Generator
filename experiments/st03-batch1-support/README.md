# ST-03 facility batch 1 — F18 kitchen, F19 smithy, F20 cart shed

Experimental assets stacked on `experiment/st03-b5a-house-a-formal` (House A is untouched and not rebuilt). Owner visual review pending; not a main-merge candidate.

| Placement | Module | File | Size (x,y,z) |
|---|---|---|---|
| F18 | M-kitchen | `out/st03_kitchen.nbt` | 9×11×9 |
| F19 | M-smithy | `out/st03_smithy.nbt` | 9×11×9 |
| F20 | M-cart_shed | `out/st03_cart_shed.nbt` | 8×9×7 |

Placement table (`tools/seam01/data/st03_placements.json`) is unchanged: `air=include`, `local_turns=0`. Each module's front is its +z face. Rebuild: `PYTHONPATH=. python experiments/st03-batch1-support/build.py`.

Design source: ST-03 owner ledger Q11–Q17 (Beta repo, `docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md`).
- F18: closed stone-brick kitchen, wall fireplace and chimney (netherrack + fire in a stone firebox), west-wall workstations (2 furnaces, crafting table, water cauldron, composter), preparation table, central aisle, east-wall storage.
- F19: stone back and side walls, open timber front, forge (blast furnace, furnace, lava cauldron) with stone chimney through the ridge, anvil, grindstone, smithing table, quench cauldron, storage.
- F20: open timber frame (front and sides open), closed spruce back wall, small cart model (slab bed, fence sides, trapdoor wheels, shafts), chests/barrel, grindstone, tool trapdoors.
- Containers (chest/barrel) are real and EMPTY. Loot tables and weights are still OPEN (runtime decision); decorative crates are not containers.

## Verification (newly run on these NBTs only)
`check-result.json` (`checks.py`): independent NBT verifier with 0 mismatches for all three; authored states equal the template; floor-level walk-in access from outside to every workstation/container; strict `place template` on the pinned 26.3 server (sha1 33680f5f…), rotation none, every cell compared, 0 failures. Two real access defects found by the check (kitchen east shelf blocked by the prep table; cart-shed grindstone walled in) were fixed before the final run.

## Screenshots
`screenshots/`: 24 unmodified in-game F2 captures from the vanilla 26.3 client (Mesa lavapipe under Xvfb, 1280×720, HUD hidden): 6 exterior + 2 interior views per building. `capture-info.json` lists tp positions and hashes.

## Not covered
Not done here: roads, terrain adaptation, rotation variants other than local_turns 0 for these placements, road-facing orientation check at the real placement, loot tables, spawns, worldgen. UNTESTED.
