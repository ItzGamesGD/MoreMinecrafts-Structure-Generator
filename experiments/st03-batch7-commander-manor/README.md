# ST-03 batch 7: F01 commander manor (candidate, awaiting owner approval)

Brief ST03-IMPLEMENT-08, built on `feat/st03-prison-stable-f09-f10-20261105` @ `7faa754`. At the start of this task, that branch existed locally and on the remote at that commit, and the working tree was clean.

The design authority is the owner ledger Q60–Q73 (Beta repo, `docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md`). No new design question was opened.

## Contract and the one placement-table change

| placement | module | size (x×y×z) | rect | street face | nearest neighbours |
|---|---|---|---|---|---|
| F01 | `M-manor` / `st03_manor.nbt` | **17×27×15** | x 48..64, z 11..25 | +z (south): the central street to the gate | W-N wall line north (6), F12 / F15 west / east, F02 / F03 south-west / south-east |

- **Q63 size change.** Q63 changed F01 from 17×23×15 to 17×27×15. That one value is the only edit to `tools/seam01/data/st03_placements.json`: the `M-manor` size, 23 → 27. The rect, rotation (0) and every other module and placement are unchanged.
- **Test reference fixture.** The seam01 reference fixture `tests/fixtures/seam01_design_manifests.json` carries the module sizes. Its four F01 entries (q=0..3) were updated to 27 to match. `tests/test_seam01.py`: 28 passed.
- **`air = include`, floor y=0.** The building, its porch and its chimney stay inside the 17×15 rect.
- **No approved facility, NBT or test result was changed.** `experiments/st03-placement-check/place_check.py` now also loads batch 7, which is its only change.

## Design (Q60–Q73)

The body is x=0..15. That makes it 16 wide and symmetric about x=7.5, so the 2-wide door sits exactly on the axis. The chimney stands at x=16.

| level | floor y | use |
|---|---|---|
| 1F | 0 | stone storey: hall, guards, supplies |
| 2F | 6 | timber: gallery and war room |
| 3F | 12 | timber: bedroom and study |
| attic | 18 | lookout |

The eaves are at y19 and the ridge at y26, so the building uses the full 27-block height.

**Exterior (Q60, Q66–Q68)**
- **1F:** a stone ground storey (rubble course, stone brick with cracked / mossy variation, andesite quoins).
- **2F and 3F:** dark-oak frame with spruce infill and dark-oak girts at every floor.
- **Roof:** a high deepslate-tile gable with dark-oak barge boards.
- **Street gable:** jettied one block on a sill beam and brackets. It holds the central lookout window, with a sill and shutters. More brackets sit under the 3F girt.
- **Porch:** a projecting timber porch on two thick (1×2) stone pillars, with a shed roof, two hanging lanterns and two illager banners. Two lantern posts stand at the forecourt corners.
- **Door:** a 2-wide dark-oak double door in a chiselled stone frame.
- **Windows:**
  - tall paired hall windows over the porch;
  - narrow barred 1F windows;
  - 2F gallery windows;
  - wider 3F windows with shutters;
  - a small rear attic window.
- **East side:** a stone chimney.

**1F: grand hall (Q61, Q63, Q69, Q70)**
- **Hall void:** x5..10 × z6..11, open from the floor to the 3F floor (y1..11).
- **Floor motif:** symmetric, with an andesite border and cross, a chiselled 2×2 centre and four chiselled corner accents. A runner leads to the rear wall.
- **Columns:** stone base with a dark-oak shaft, carrying the gallery rims.
- **Chandelier, two tiers:**
  - a square ring 4 across at y10 and a stepped ring 6 across at y8 (the even grid gives 4 / 6 instead of Q69's ~3 / ~5);
  - four chain lines from the ceiling through both rings;
  - 8 hanging lanterns.
- **Around the hall:** illager banners and lanterns. The west guard bay under the gallery has supplies, a fletching table and a guard table. Rear supplies sit under the mezzanine, and the east room has a stove in the chimney breast.

**2F: command level (Q64, Q71)**
- **U gallery:** a west arm (x2..3, rail at x=4) and a rear arm along z=4 (rail at z=5) overlook the hall. The third side is the stair, which rises beside the hall.
- **War room:** the rear arm opens into the war room, a mezzanine across the back of the house. It has:
  - a war table with a carpet map;
  - a terracotta map mural;
  - a cartography table;
  - banners;
  - military containers: chests, barrels and a smithing table.
- **Commander initial position:** recorded behind the war table at local (7.5, 7, 1.5), facing the hall: `BUILDINGS["manor"]["commander_spawn"]`.

**3F: private quarters (Q65)**
- **Bedroom (rear):** a double bed, nightstands with lanterns, a rug and bookshelves.
- **Rare-reward chest:** at (5, 13, 1).
- **Armor stand:** its position (12.5, 13, 2.5) is recorded in `BUILDINGS["manor"]["armor_stand"]`. It is not in the NBT, because the export pipeline (`schem.py`) rejects entities.
- **Open study (front):** bookshelves, a desk with candles, a map table and a lantern.
- **Attic ladder:** on the partition's south face.

**Stair (Q62)**
- **Flight 1:** 2 wide, x11..12, on a stone base. It rises north from the hall to the 2F landing (z4..5), which is part of the rear gallery.
- **Flight 2:** 2 wide, x13..14. It rises south against the east wall to the 3F.
- **Steps:** each storey takes six half-block steps, so there is no full-block step at any landing.
- **Balustrade:** a timber screen and rail between the flights, placed above flight 1's head room.
- **3F opening:** railed on its open sides.
- **Attic:** reached by ladder.

**Attic (Q66)**
- Tie beams with king posts.
- A lantern hanging from the ridge.
- An ordinary chest and a barrel.
- A raised lookout platform with two steps and side rails, so the eye is level with the lookout window.

**Containers (Q72):** all empty, using the block-entity allow-list.

| level | ordinary containers |
|---|---|
| 1F | 3 chests, 5 barrels |
| 2F | 3 chests, 6 barrels |
| 3F | only the rare-reward chest |
| attic | 1 chest, 1 barrel |

No loot, reward roll or once-only logic is authored.

## Files

| file | what |
|---|---|
| `build.py` | `f01()`; `BUILDINGS` (entrances, wall box, commander / armor-stand positions, rare chest); writes `out/` |
| `out/st03_manor.*` | NBT, source .schem, export report |
| `checks.py` → `check-result.json` | NBT/state validity, block support, walk access, stair width, gallery / chandelier clearance, entity positions, strict 26.3 placement, vanilla-AI probe (`--offline` skips the server) |
| `capture.py` → `screenshots/` | real 26.3 client F2 screenshots (isolated copy and the real q=0 layout), plus two test-entity views |
| `sheet.py` → `approval/*.png` | labelled contact sheets; `comparison_approval_contact_sheet.png` is the approval image |
| `../st03-placement-check/place-check-result-f01.json` | placement-table checks (`--only M-manor`) |

NBT sha256: `f0e21133f6baab46...`. It is identical in check-result, place-check and the capture info file.

## Verification (run in this task on the pinned 26.3 server, sha1 33680f5f...)

### `checks.py`: PASS

- **verify.py:** 17×27×15, 6885 cells compared, 2652 non-air, 88 palette states, 0 mismatches. Every authored state is present unchanged.
- **Strict `place template`** (rotation none), every cell compared: 0 failures.
- **Support:** every lantern (25), wall banner (9) and ladder has the block it needs. None is unsupported.
- **Access**, from the porch alone:
  - all 28 containers and workstations are reached, and so is the rare-reward chest;
  - all 17 key points are reached: hall, guard bay, rear supplies, east room, stair foot, landing, war room, commander position, both gallery arms, 3F arrival, study, bedroom, armor-stand position, attic hatch, lookout platform, attic rear.

  | | 1F | 2F | 3F | attic |
  |---|---|---|---|---|
  | walkable feet cells | 122 | 63 | 109 | 126 |

- **Stairs:** both flights are 2 wide with 6 steps each, and both cells of every step can be walked with head room.
- **Gallery and chandelier:**
  - all 26 listed gallery cells are reached;
  - 48 chandelier blocks with 8 lanterns, none in any walkable feet or head cell;
  - the closest chandelier block is 1.41 blocks (horizontally) from a walkable gallery or stair cell.
- **Entity positions:** the commander and armor-stand positions are 2 cells clear on a solid floor and reachable.

### Vanilla-AI probe (test entities): PASS 4/4

Each test entity was started at the commander position and made to chase a NoAI villager by `damage … by <villager>`. Positions were sampled every 0.25 s.

| test entity | target | result |
|---|---|---|
| vindicator, 40 HP, iron axe | west gallery far end | reached (1.01 blocks) in 3.5 s |
| vindicator | hall floor by the door, down flight 1 | reached (1.68) in 4.3 s |
| vindicator | 3F study, up flight 2 | reached (1.41) in 5.5 s |
| pillager, 40 HP, crossbow | hall floor | walked out of the war room to the head of flight 1 and shot it: villager 20 → 16 HP in 5.5 s |

The vindicator's follow range was raised from its vanilla 12 to the pillager's 32: with 12, vanilla gives up on paths as long as the one down the stair. Weapons are given explicitly, because `/summon` with NBT skips spawn equipment.

These are vanilla-AI test entities in a test world. They are **not** the commander, its spawn system, or the reward rules.

### `place_check.py --only M-manor`: F01 PASS; tool exit FAIL 1 because of a pre-existing F06 cell (details below)

- **Footprint overlaps:** 0 for q=0..3.
- **Whole-structure turns q=1..3:** F01 0 failed cells (2652 non-air cells).
- **All 20 built placements together at q=0:** F01 has 0 failures, so it neither overwrites nor is overwritten by any neighbour. The other 18 buildings other than F06 also have 0.
- **F06 (approved training yard, far from F01) has 1 failed cell:** a `grass_block` at world (15, 0, 62). That cell was correct when placed, then changed to dirt by the game while the 20 buildings were being compared.
  - F06's approved NBT has 33 `grass_block` cells directly under solid blocks (for example spruce planks), and vanilla random ticks turn covered grass into dirt.
  - The same thing hit a different F06 cell, (33, 0, 65), in an earlier run during this task.
  - This is a latent issue in an approved NBT, not caused by F01, and it was not changed here: approved NBTs are out of scope. Fixing it (dirt instead of grass under those blocks) needs the owner's decision.
- **Test terrain falling 0..2 blocks:** 204 footing columns filled, 0 hollow, 0 template failures.
- **Entrance:** the porch's outside cells (55, 26) / (56, 26) have a 74-block free run south, ending at the gate.

### `tests/test_seam01.py`: 28 passed (after the Q63 fixture update)

### Screenshots

Unmodified 26.3 client, Xvfb / lavapipe, noon, HUD hidden; interiors with night vision.
- **Isolated views:** front, both front diagonals, both sides, rear, rear diagonal, roof and lookout, porch.
- **Interiors:** hall from the door, chandelier, west gallery, war room, stair, hall seen from the war room, 3F bedroom, 3F study, attic and lookout, 1F guard bay.
- **Context:** six views in the real q=0 layout.
- **Attic retake:** `f01_18_interior_attic_to_lookout` was retaken with a better camera (`capture-info-attic-retake.json`, same NBT hash, file sha256 `6dcb5a9471bec637...`). The entry for it in `capture-info-all.json` is the superseded first shot.
- **Test entities:** `f01_20` (a NoAI 40-HP pillager at the commander position) and `f01_21` (an armor stand at its recorded position). They are shown for scale only and are not template content.

## Defects found and fixed during the task

1. **Stair flights** had 5 steps for a 6-block storey, so a full-block step was left at each landing. In the probe, real mobs could not path down the stair. Each flight now has 6 steps with half-block rises.
2. **3F floor edge over flight 2:** the head of a player stepping up flight 2 hit it (z=8). The opening was widened to z8..10.
3. **Wall banners on glass:** two banners hung on glass panes and one on a new window. They would drop on a block update; all were moved onto posts or solid wall.
4. **Attic lookout window** was 3 blocks above eye level. A raised platform with steps was added, the tie beams were moved up to y22, and the street gable was jettied to hold the window.
5. **Upper storeys read as a flat box.** Fixes: a jettied gable with brackets, brackets under the 3F girt, middle side windows, and a stone base under flight 1.
6. **Cartography table** sat on the walking line from the commander position to the landing, and the test pillager climbed over it. It was moved into the corner.
7. **Checker and probe fixes, verification side:**
   - the gallery cell list (x=1 holds the gallery's storage);
   - the chandelier distance is limited to 2F and stair cells;
   - follow range and weapons for the test entities.

## Not covered / UNTESTED

- **Commander spawn, 40-HP commander, combat AI and the independent 10% special drop:** UNTESTED, not implemented. Only the position is recorded, and only the test-entity probe above was run.
- **Rare reward:** the 65% roll once per structure, the no-reroll rule across reloads and chunk reloads, and ordinary loot are all UNTESTED, not implemented. The rare-reward chest is an empty slot.
- **Persistence after a server restart:** UNTESTED.
- **Armor stand:** not in the NBT, because the exporter rejects entities. Runtime placement at the recorded position is UNTESTED.
- **Whole HQ:** worldgen, roads, walls, towers and the gate are not implemented, and the road connection is UNTESTED.
- **Natural hostile spawning** inside the building (light levels) was not tested. Every room has lanterns.
