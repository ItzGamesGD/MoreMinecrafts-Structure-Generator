# ST-03 military batch: F05 armory + F06 training yard (candidate, awaiting owner approval)

Free-design brief ST03-IMPLEMENT-04. Fixed contract kept unchanged (`tools/seam01/data/st03_placements.json` is
not modified): `M-armory` 17x12x13 at F05 (x 12..28, z 39..51), `M-yard` 25x5x21 at F06 (x 12..36, z 52..72),
`air = include`, floor y=0, `local_turns` 0. F05's +z face touches F06's -z edge along yard x 0..16.

## Concepts

**F05 armory - fortified arsenal.** A long, heavy stone hall (dark deepslate plinth, mixed stone-brick walls,
dark-oak wall plate) under a deep deepslate-tile roof. On the road side (+x) a square **gate tower** rises above
the ridge to a corbelled, crenellated parapet (y 9..11). This is the facility's landmark and main entrance. On the
yard side (+z) the hall roof sweeps down as a catslide over a low **maintenance loggia** of stone bases, dark-oak
posts and a continuous lintel that opens onto the training yard.
- Inside, the tower portal starts a processional axis (polished-deepslate runner).
- The axis passes between weapon tables (breastplates, mail, blades) and weapon walls (round shields, spears
  standing in barrels under banners, hauberk chains).
- The axis ends at a **barred strongroom** with the premium chest between two soul-lantern pedestals under a banner.
- The workstations sit in the loggia: anvil, grindstones, smithing, fletching and crafting tables, quench
  cauldron, tool pegs.
- Entrances: tower portal (east, road side), loggia bay (south, to F06), loggia service door (east).

**F06 training yard - open drill ground.** Deliberately the opposite of F05: no building mass, timber only, and
everything at or below y=4.
- A dark-oak post-and-rail enclosure with lantern posts.
- A stone parade path runs from the timber **road gate** (east; log posts, beam, white banners, hanging lantern),
  through banner posts, to a canopied **command dais** (west; stone base, plank deck, commander's seat and map
  table, banner backdrop).
- A stone spur leads to the armory loggia.
- Zones:
  - **Sparring ring** (north-east): stone-edged worn-earth ring with three straw pells and a practice-weapon rack.
  - **Equipment shelter** (north-west, beside the armory): spear rack, shields, banner, barrels, grindstone.
  - **Archery range** (south): fenced off from the path, stone firing line with quivers, fletching table and bench;
    worn lanes on packed mud; a hay butt with exactly **3 targets** (Q33) under a small roof; a timber arrow
    screen behind it.

## Gameplay contracts kept

- F05 premium reward: **slot only**. The chest at `PREMIUM_CHEST = (2, 1, 4)` in the strongroom is the only
  chest there.
  - Its 35 %, once-per-structure roll and its contents stay runtime decisions.
  - No loot, item or probability is authored here.
- All containers are empty, using the block-entity allow-list: chest[type=single], barrel[open=false].
- F06 has exactly three `target` blocks.

## Files

| file | what |
|---|---|
| `build.py` | `armory()`, `yard()` designs, `BUILDINGS` (entrances, interactive blocks), `PREMIUM_CHEST`; writes `out/` |
| `out/st03_armory.*`, `out/st03_yard.*` | NBT, source .schem, export report |
| `checks.py` -> `check-result.json` | NBT/state validity, per-entrance 3-D walk access, F05-F06 joint access, premium slot, strict 26.3 placement |
| `capture.py` -> `screenshots/` | real 26.3 client F2 screenshots, both templates at their real relative offset |
| `approval/*.png` | labelled contact sheets of the screenshots |
| `../st03-placement-check/place-check-result-f05-f06.json` | placement-table checks for F05/F06 (`--only M-armory,M-yard`) |

NBT sha256: armory `b597abcc...7e1cc`, yard `4ccd7a62...db6cc` (identical in check-result, place-check and capture-info).

## Verification (run in this task on the pinned 26.3 server, sha1 33680f5f...)

- `checks.py`: PASS.
  - **verify.py**: 0 mismatches. Armory 2652 cells / 71 palette states; yard 2625 cells / 59 states. Every
    authored state is present unchanged (1159 / 869 cells).
  - **Strict `place template`** (rotation none), every cell compared: 0 failures (armory 2652, yard 2625).
  - **Access**: each entrance is tested alone, so the search may not use outside ground beyond that entrance cell.
    Every interactive block and every chest/barrel is reached from each entrance. Armory: 3 entrances, 109
    interior feet cells. Yard: 2 entrances, 385 cells. The dais is reached by its stairs.
  - **Joint F05 + F06** at the real offset (0, 0, 13): the loggia bay (8,1,12) and the yard apron (8,1,13) are both
    walkable. From the yard's road gate alone, every armory interactive block, including the premium chest, is
    reached through the bay. From the armory tower portal alone, all three targets and every yard interactive
    block are reached.
- `place_check.py --only M-armory,M-yard`: PASS.
  - Footprint overlaps: 0 for q=0..3.
  - Whole-structure turns q=1..3: 0 failed cells (F05 1009, F06 869 non-air cells).
  - All 12 built placements placed together at q=0: 0 failures, so F05 and F06 do not overwrite each other or
    their neighbours.
  - Test terrain falling 0..2 blocks: 0 hollow footing columns, 0 template failures.
  - Entrances:
    - The tower portal and service door face 46 free blocks east before F04.
    - The yard's road gate faces 38 free blocks east before F08.
    - The loggia bay opens directly into F06, by design.

## Not covered / notes

- **Road connection: UNTESTED.** The road masterplan and MQ ground modules are not in this repository. The east
  faces of F05 and F06 open onto the free central area, which is the expected road side.
- F06's road entrance is its **east gate**, not its +z face. `BUILDINGS["yard"]["door"]` = (24, 10) records that.
- F05's +z "front" (the loggia bay) intentionally opens into F06. Its road entrance is the tower portal on +x.
- No worldgen, mob spawns, combat or loot systems are in scope.
