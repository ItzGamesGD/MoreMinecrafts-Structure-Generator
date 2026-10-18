# SG-03 — Modular rooms and multi-level Jigsaw assembly

SG-03 fills the SG-02 lower and upper room interfaces with six modular rooms in two families and verifies
complete assemblies in a real Minecraft 26.3 server. It is stacked on SG-02 (PR #9): everything about the cavern,
platforms, rails, connector table and reserved volumes is defined in `docs/sg-02/README.md` and is unchanged here.

Generators: `examples/forgotten_kingdom/build_sg03.py` (`rooms_common.py`, `sg03_lower_rooms.py`,
`sg03_upper_rooms.py`). Output: `exports/sg-03/forgotten-underground-kingdom/datapack/`.
The pools hold only the six rooms — the SG-02 reserved-volume stubs are gone.

## Rooms

Every room is authored with its entry on the south edge, centred (odd width), floor at `y = 0`, entry connector at
`(W//2, 1, D-1)`, orientation `south_up`, name `…/lower_room_entry` or `…/upper_room_entry`. Vanilla Jigsaw rotates it
to whichever side it is attached to.

### Family A — lower, small (plaza level, ≤ 17 × 9 × 24)

| Module | Size (W×H×D) | Layout and features |
|---|---|---|
| **A1 `storage_room`** abandoned storage | 13×9×17 | Tall vault: side bays corbelled into a taller nave with two rib beams on pilasters; shelf bays on both walls (dark-oak boards, barrels, decorated pots, candles); a crate island with a loot chest; a raised stash dais with two chests and a lectern; one broken shelf, a collapsed north-east corner with a hole in the lowered ceiling, cobwebs. |
| **A2 `guard_room`** watch room | 15×8×13 | Gatehouse passage with a raised iron-bars portcullis in a slot above the inner doorway, murder-hole bars, polished jambs; two guard closets (cots, loot chest, barrels, grindstone); a raised two-block watch step with arrow-slit bars; armoury wall (iron-bar racks with chains, fletching and smithing tables, anvil); guard table with seats. |
| **A3 `residence_ruin`** small residence | 15×7×19 | Low hall and bedroom split by an arched, partly collapsed partition; hearth (unlit campfire, cauldron, stair surround); table and chairs, bookshelf wall with lectern, loom and cartography table; two beds, chest, wardrobe barrels; timber floor patches, moss, a rubble mound. |

### Family B — upper, large (≤ 23 × 17 × 32, 15 blocks of interior height)

| Module | Size (W×H×D) | Layout and features |
|---|---|---|
| **B1 `grand_hall`** | 23×17×31 | Nave and two aisles under high vaults; two arcaded colonnades of 2×2 piers with rounded arch heads, a chiseled frieze and a barred clerestory; two side galleries (floor at y=6, four lanes, rail) reached by six-step stair runs; a three-tier dais with a throne; chains with lanterns down the nave and soul lanterns in the aisles; a fallen column across the nave and a collapsed north bay of the east gallery. |
| **B2 `barracks_hall`** | 21×16×27 | Three functional zones south to north — mess hall (long tables and benches around a clear aisle), dormitory (two-tier bunks, each with a two-step stair to the upper deck), armoury under an **officers' mezzanine** (floor y=6, beds, desk, shelves, balustrade) joined to the dormitory by a west stair run and a partial **catwalk**; timber roof beams; a broken catwalk rail and rubble. |
| **B3 `trial_chamber`** | 23×15×29 | Entry hall opening onto a copper-grated arena with two-block ramped ledges on three sides, balustrades, symmetric cover walls and pillars; **three `minecraft:trial_spawner` blocks** with distinct vanilla configs (`ranged/skeleton` central, `melee/spider` and `melee/zombie` on the north ledge); a reserved reward alcove at the top of the north ramp holding a placeholder chest; waxed oxidized-copper trim, lit copper bulbs. |

Rewards are provisional: chests and barrels use vanilla loot tables only (`minecraft:chests/simple_dungeon`,
`abandoned_mineshaft`, `trial_chambers/corridor`); no MoreMinecrafts item ids are invented. The trial chamber's
reserved alcove and spawner configs are placeholders for later encounter balancing.

### Variation

Heights differ within each family (lower 9/8/7, upper 17/16/15); footprints differ; the structural idioms differ
(vault and ribs; gatehouse and cheeks; partition and arch; arcades and galleries; mezzanine and catwalk; sunken arena
and ledges); material accents differ (polished deepslate and dark oak; tuff and spruce; copper); each room carries
its own damage (collapsed corner, fallen column, broken rail, missing beams, moss and cobwebs). A test requires that
no two rooms share more than 85% of their block vocabulary.

## Jigsaw integration and spatial coexistence

* Pools: `central_cavern/lower_rooms` (A1–A3) and `central_cavern/upper_rooms` (B1–B3), equal weights, empty
  fallback. Connectors, targets, rotations and vertical offsets are exactly the SG-02 table; vanilla Jigsaw semantics
  and collision checks are untouched.
* **No relaxation was needed.** Every room is contained in the SG-02 maximum reserved volume for every slot and side
  (checked by `tests/test_sg03_rooms.py` by comparing each room's world bounding box with the stub's for all 16 slots),
  and the stubs were shown disjoint at SG-02. So any choice of rooms at any slots is collision-free by construction, and
  the real server confirms it: no piece overlaps in any assembly.
* Lower rooms occupy `y = 0..8` of the chamber frame, upper rooms start at `y = 9`; an upper room can sit directly
  above a lower room with the lower roof slab beneath the upper floor slab.
* Because pools have no deeper connectors, `size = 1` suffices; `max_distance_from_center = 112` fits the largest assembly.

## Verification

* `python3 -m unittest discover -s tests` — 18 SG-03 room tests (contracts, reserved-volume containment for all slots,
  variation, interior reachability of every loot container / spawner / workstation, stair flushness, block-entity
  rules, determinism) plus the SG-02 and palette-schema suites.
* `validation/minecraft-visual/run_runtime.py` — real Minecraft 26.3: every template placed with `/place template` and
  compared cell-for-cell (air included); block entities read back with `data get block` (loot tables, trial-spawner
  configs); every loot table exercised with `loot spawn` after a negative control proves the check can fail; eight
  `/place structure` assemblies recovered from saved chunks with every non-air block explained by exactly one piece,
  no overlapping bounding boxes, all 16 connectors filled, and a conservative walk model proving the plaza reaches
  every deck lane cell, every connector and every point of interest in every room.
* Native screenshots (`capture_client.py`) of the cavern with connections, a lower and an upper entrance, three
  interior views of every module, and a vertical section through the multi-level stack. The section and the elevated
  views are cut out of the evidence world *after* verification with `/fill … air`, to show the separation of the lower
  and upper bands; nothing in the packs is cut.

## Screenshot inspection

Committed native frames (1280×720, real Minecraft 26.3 client, software rendering) are in
`exports/sg-03/forgotten-underground-kingdom/evidence/local-runtime/screenshots/`; I opened each PNG and judged the content.
Room interiors come from the verified standalone placements (doorways plugged in the evidence world); cavern, entrance
and section views come from a real Jigsaw assembly (the section and elevated views are cut with `/fill` afterwards).

| Image | Verdict |
|---|---|
| `cavern-overview`, `cavern-lower-doors`, `cavern-upper-vestibules` | PASS — plaza and stairs unchanged; the lower doorway under the platform and the upper vestibule opening are visible (the vestibule sits at the frame edge) |
| `lower-entrance-guard_room` | PASS — door with polished frame, gatehouse, bars and lantern beyond |
| `lower-storage_room-a/b/c` | PASS — vault, shelf bays, crate island, chests, hanging lanterns, cobwebs |
| `lower-guard_room-a/b/c` | PASS — portcullis bars, watch step, armoury racks and workstations, cots |
| `lower-residence_ruin-a/b/c` | PASS — hall with table and bookshelf wall, bedroom, hearth and rubble |
| `upper-entrance-grand_hall` | PASS — vestibule stair sill leading into the nave |
| `upper-grand_hall-a/b/c` | PASS — arcaded colonnades and hanging lanterns, gallery corridor with rail, dais |
| `upper-barracks_hall-a/b/c` | PASS — mess hall and bunks, two-tier bunk with its stair, armoury |
| `upper-barracks_hall-d-mezzanine` | PARTIAL — looks up the dormitory at the armoury partition and roof beams; the mezzanine edge is just out of frame |
| `upper-trial_chamber-a/b/c` | PASS — copper-trimmed arena, grates, ledges, spawner, alcove |
| `section-multilevel`, `elevated-separation` | PASS — large upper rooms above, small lower rooms below, chamber and tunnel between; the two bands are visibly separate |

## Defects found by the runtime and fixed

| Finding | Cause | Fix |
|---|---|---|
| Hanging lanterns and chains vanished in the world | `minecraft:chain` does not exist in 26.3 (`iron_chain`); the vendored mcbuild registry predates it, so the id was placed as air and the lanterns lost their support | `ID_RENAMES_26_3` applied on export; `tests/test_block_states.py` checks every id/state against the 26.3 data-generator report |
| Trial chamber blocks changed after placement | unwaxed copper oxidizes on random ticks | waxed copper variants only |
| Ladder missing in the barracks | no support block behind it | bunks now use two-step stairs; no ladders |
| Barracks armoury unreachable on foot | bunk units stood directly in front of the armoury doorways | bunks moved one row south; walk model now proves reachability |
| Iron bars/walls differed from the template | vanilla connects bars and walls to each other and to sturdy blocks | the exporter's connection rule now follows vanilla's (`finish_connectables`) |
| Probe false alarms | saved chunks omit default-valued properties; trial spawner state is engine-managed; a vanilla village generated next to an assembly | probe uses the 26.3 default table, ignores `trial_spawner_state`, and counts extras only inside the assembly's own volume |
| Stairs ended one block below their landings | the same off-by-one as SG-01's run | final flush step added in the cavern (SG-02); rooms built and tested to the same rule |
| First screenshot showed a join toast | the client's one-time "chat can't be verified" toast | capture waits for it to expire |
| Blast furnace block-entity id mismatch | the exporter maps `blast_furnace` to `minecraft:furnace` but 26.3 uses `minecraft:blast_furnace` | no explicit block entity is written; the game creates it (the exporter is unchanged) |

## Known limitations

* Natural generation in varied terrain, cave intersections and liquids is not exercised; the test world is flat with the
  structure floating in air above ground.
* Mob behaviour was not tested: trial spawners are inert in the peaceful test world (placement and configuration only).
* The walk model is conservative but is not play-testing; ladders, door interaction and bed use are out of scope.
* `/place structure` does not persist starts, so assemblies are recovered from block data rather than read from engine records.
* Screenshots are from a local software-rendered (llvmpipe) run; lighting is dim because the test world is unlit
  underground and night vision is applied only to the capture player.
