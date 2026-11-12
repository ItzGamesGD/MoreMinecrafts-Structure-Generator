# ST-03 group 1 (living + support) — B3-06

Houses B / C / D (Q01–Q10) and the three support buildings, kitchen F18, smithy F19, cart shed F20 (Q11–Q17).
Base: `experiment/st03-b5a-house-a-formal` @ `62cec3eb5a503469ee940e798a68060070a0ff36`. **Experimental assets, owner visual review pending; not a merge candidate.**
`tools/seam01/data/st03_placements.json` is untouched (module ids, sizes, `air=include`, coordinates); `build.py` asserts every size against it.

Rebuild: `PYTHONPATH=. python experiments/st03-b6-group1/build.py`. Checks: `checks.py` (pinned 26.3 server, no client). Screenshots: `capture.py` (unmodified 26.3 client, Xvfb + Mesa lavapipe, F2).
Local frame as House A: +x east, +z south, y=0 floor; every door / open front faces south.

| Module | Size (x,y,z) | NBT | Cells | Design summary |
|---|---|---|---|---|
| `M-house_b` (F12/F15) | 9×10×7 | `st03_house_b.nbt` | 332 | cobblestone base, spruce panels, dark-oak frame; regular gable (dark-oak stairs, ridge along x); 1-deep covered porch inside the box (z=6) with 4 posts, 2 lanterns and an illager banner; shuttered windows (open trapdoors beside glass panes); two beds, bookshelves, table, crafting table, furnace, 2 barrels, chest |
| `M-house_c` (F13/F16) | 7×9×7 | `st03_house_c.nbt` | 206 | spruce timber on a stone-brick base, whole east wall stone + stone chimney; asymmetric (saltbox) gable: ridge x=2, short west slope, long low east slope; door recessed 1 block (alcove with lantern); 3 small windows at uneven positions; one bed, bookshelves, crafting table, furnace, barrel, chest |
| `M-house_d` (F17) | 7×9×7 | `st03_house_d.nbt` | 232 | stone-brick lower walls (mossy/cracked mix), spruce upper, dark-oak frame; small hip roof; stone-framed doorway with chiselled keystone; 9 single iron-bar slit windows; one guard bed, weapon rack (boards + bars), grindstone, chest, barrel |
| `M-kitchen` (F18) | 9×11×9 | `st03_kitchen.nbt` | 448 | closed stone-brick hall, dark-oak roof, tie beams + lanterns; back-wall fireplace (netherrack + fire, cauldron) with a chimney stack through the roof; west preparation counter (crafting table, furnace, planks counter, cake, lantern); east storage (3 barrels, 2 chests, hay); aisle x=3..5 |
| `M-smithy` (F19) | 9×11×9 | `st03_smithy.nbt` | 402 | open south front (two dark-oak posts + beam), stone back and sides, dark-oak roof; stone forge with furnace / blast furnace / furnace and chimney; anvil, smithing table, grindstone, water cauldron, coal; 2 chests + 2 barrels |
| `M-cart_shed` (F20) | 8×9×7 | `st03_cart_shed.nbt` | 234 | timber shed, open south front and open east side, spruce roof; back and west walls on a stone-brick course; small block cart (slab bed, rails, hay, 4 wheels, shafts); 3 barrels, chest, grindstone, tool rack |

## Result (PASS / FAIL / UNTESTED)

Newly run on these NBT hashes (`check-result.json`, `screenshots/capture-info.json`).

| Item | Result | Evidence |
|---|---|---|
| Actual size = approved module size, `air=include`, in-bounds | PASS | independent decoder: size and all cells equal the source (0 mismatches, 6 modules) |
| Every authored block state is in the template (stairs, doors, beds, trapdoors, …) | PASS | 1,854 cells checked, 0 mismatches |
| Strict `place template` on the pinned 26.3 server, all four rotations, every cell compared | PASS | 6 modules × 4 rotations, 0 failures |
| Appearance vs approved Q01–Q07 / Q11–Q14 (family, roofs, doorways, windows, bases, rooms) | PASS with notes | real 26.3 screenshots, 55 views (`screenshots/`); owner visual review still pending |
| Real 26.3 screenshots (exterior ×7 and interior ×2–3 per building) | PASS | unmodified vanilla client; one view (`smithy_interior_side`) re-shot after a bad camera angle |
| Entrance and circulation: walk-in from outside, every workstation / bed / container has a reachable neighbour column | PASS | BFS on the template cells (`access.unreachable` empty); this found and fixed 3 blocked items (see below) |
| Containers are real block entities and accept items (chest, barrel, furnace, blast furnace) | PASS | `item replace … container.0`, read back with `data get block`: 26 containers, all OK |
| Workstations present as real blocks | PASS | crafting table ×3, furnace ×5, blast furnace, anvil, grindstone ×3, smithing table, cauldron, water cauldron |
| Fire (kitchen hearth) and water cauldron placed correctly | PASS | present right after placement; fire seen burning in the client screenshot |
| Facing toward existing roads | UNTESTED | the repository has no road data (ground modules are unbuilt); all doors face south like House A (F11/F14) |
| Neighbour / terrain compatibility, collisions with other modules | UNTESTED | buildings were placed alone on a flat world; no other ST-03 NBT exists yet |
| Collision with a walking player / real entity pathing | UNTESTED | only geometric BFS was run; no entity was walked through |
| Loot tables | not in scope | all containers are empty (runtime decision) |

Fixes made after the first run (blocking defects only): House C (crafting table), House D (chest) and the cart shed (barrel) each had an item with no reachable neighbour cell (re-laid out); the hip roof corners were turned the wrong way (raised quarter at the outside corner), fixed in `lib.py`; `checks.py` uses its own rotation expectation because `live.rotate_props` handles neither log `axis` nor `facing=up`.

## Approved items not fully delivered (reported, not changed)

- **Q08 placement-specific cosmetic variants (F12/F15, F13/F16):** not built. The placement table maps both placements to one module (one NBT each); variants would need new modules, which changes the table. Needs an owner decision.
- **Q05 "lanterns" outside:** window and door lanterns hang inside the box only (the box has no cells outside the walls).
- **Q09 stone footings down to natural terrain:** not applicable inside the module (floor is y=0); this belongs to terrain adaptation / worldgen (excluded).
- **Q06 D "weapon decor", Q14 "tools":** block-only decor (boards, bars, hay). Item frames and armor stands are entities and cannot be exported.
- **Block-entity allow-list limits the design:** smoker, campfire, lectern and coloured banners are rejected by the exporter. The kitchen therefore uses a furnace as its workstation and a netherrack + fire hearth instead of a campfire; the only banner is the allow-listed illager `white_wall_banner` (House B).
- **House A** (F11/F14) is unchanged.

## Container inventory (for the later loot task)

| Module | chests | barrels | furnaces | blast furnaces |
|---|---|---|---|---|
| house_b | 1 | 2 | 1 | 0 |
| house_c | 1 | 1 | 1 | 0 |
| house_d | 1 | 1 | 0 | 0 |
| kitchen | 2 | 3 | 1 | 0 |
| smithy | 2 | 2 | 2 | 1 |
| cart_shed | 1 | 3 | 0 | 0 |

Cosmetic crates / racks (hay, coal blocks, boards, bars) are non-container blocks and create no loot rolls.
