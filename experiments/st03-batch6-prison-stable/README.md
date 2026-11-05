# ST-03 batch 6: F09 prison / F10 ravager stable (candidate, awaiting owner approval)

Brief ST03-IMPLEMENT-07, built on `feat/st03-warehouses-f07-f08-20261105` @ `422941e`. At the start of this task, that branch existed locally and on the remote at that commit, and the working tree was clean.

The fixed contract is unchanged; `tools/seam01/data/st03_placements.json` is not modified:

| placement | module | size (x×y×z) | rect | street face | neighbours (gap) |
|---|---|---|---|---|---|
| F09 | `M-prison` | 11×10×13 | x 92..102, z 62..74 | +z (south): open south-east ground, free down to the south wall | F18 north (3), F08 west (4), W-E wall east (4), F10 south-west (4) |
| F10 | `M-stable` | 17×13×13 | x 77..93, z 79..91 | +z (south): the strip along the south wall that runs west to the gate | F09 north-east (4), F08 north (11) |

- Both modules use `air = include`, floor y=0 and `local_turns` 0.
- No approved facility or NBT was changed.
- The only edit to shared tooling is `experiments/st03-placement-check/place_check.py`, which now also loads batch 6.

**Design source:** the owner ledger, Q46–Q59 (Beta repo, `docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md`). Where the brief's directions and the ledger overlap, the ledger was followed (e.g. no guard room or loft in F09).

## Concepts

The two buildings share the ST-03 vocabulary (stone-brick family, dark oak, spruce) but are opposites in character:
- **F09** is closed and defensive: all stone, low and heavy.
- **F10** is open and large: stone below, timber above, a tall raised nave.

### F09 "cell block": a buttressed stone prison

**Exterior**
- Heavy stone-brick walls with sparing cracked and mossy variation, on a rubble course and a battered (sloped) plinth.
- Stepped buttresses at the cell partitions, full-height corner piers, and a corbelled cornice under the eaves.
- A low, dark rubble-slab gable roof (cobbled deepslate with deepslate tiles) over stone gables (Q51). On the street gable the roof runs out as a verge; at the rear it stops flush (z=0 is the module edge).
- Tall barred slits light each cell; there is a barred vent in each gable.

**Street side (Q50)**
- One iron door in a chiselled stone-brick frame, under a hood moulding with a lantern on it.
- A stone button on each side of the door: outside on the west jamb, inside on the east jamb.
- Two tiny barred windows, a string course and angle buttresses.
- No guard post, awning or banner.

**Interior (Q46–Q49)**
- A small vestibule (one barrel for confiscated gear), then a straight one-block corridor between iron-bar cell fronts, two cells on each side.
- **No guard room and no loft.**
- Each cell has an iron door under a stone lintel. Its button is on the lintel, on the corridor side only (the jailer's side).
- Each cell is slightly different:

  | cell | bed / straw | detail |
  |---|---|---|
  | NW | bed | chain |
  | NE | bed | slop cauldron, cobweb |
  | SW | straw pallet | chain |
  | SE | bed | straw, cobweb |

- Three dark-oak tie beams are the only roof wood, each carrying a hanging lantern over the corridor or vestibule.

### F10 "monitor stable": a raised-nave military stable

**Exterior (Q53, Q55, Q58)**
- Fortified stone lower walls (rubble course and stone brick, y1..3) with buttresses and stone quoins, under a dark-oak wall plate.
- Over the aisle, a raised central nave with a high spruce gable (dark-oak frame, king post, vents) and a clerestory vent strip on both sides.
- The pens sit under lower lean-to roofs on each side, so the silhouette is stepped. Two shuttered windows per side.

**Street side (Q57)**
- A 3-wide × 4-high stone-and-timber portal: stone jambs, a dark-oak lintel, and lantern pillars.
- Dark-oak gate leaves folded back against the wall; the passage is always open.
- An illager banner on the gable, with hay and barrels beside the portal.

**Interior (Q54, Q56, Q58)**
- A straight cobble aisle with a stone-brick runner, between two large open pens (4×7 each).
- Each pen entry is 3 wide and has **no gate, door or restraint**.
- Each pen has:
  - a feed bin (composter) in the low stone wall under a dark-oak rail;
  - a water trough (cauldron);
  - a coarse/packed-dirt floor with hay bedding.
- The pens are bounded at the back by a stacked hay store (west) and a feed store (east), both at least 2 high.
- At the head of the aisle, a small store and tack corner: a chest, two barrels and a lantern.
- Heavy tie beams with king posts, and pen beams with hanging lanterns. The nave is clear up to y7, the pens up to y4.
- **Ravager initial positions** (one per pen) are recorded in `BUILDINGS["stable"]["ravager_spawns"]` as entity centres in local coordinates: west (4.0, 1, 7.0), east (13.0, 1, 7.0). They are not placed as entities.

## Contracts kept

- **Size and placement:** sizes as in the placement table; no move and no rotation change.
- **Containers:** all empty, using the block-entity allow-list. No loot, mob, spawner, AI, road or HQ-wide integration is authored.
- **No added features:** nothing outside the ledger was added. There is no prisoner NPC or escape mechanic, and no feeding mechanic (the composter and cauldron are décor).

## Files

| file | what |
|---|---|
| `build.py` | `f09()`, `f10()`; `BUILDINGS` (entrances, wall boxes, ravager positions); writes `out/` |
| `out/st03_{prison,stable}.*` | NBT, source .schem, export report |
| `checks.py` → `check-result.json` | NBT/state validity, button-aware walk access, ravager clearance, strict 26.3 placement, vanilla-AI ravager probe (`--offline` skips the server) |
| `capture.py` → `screenshots/` | real 26.3 client F2 screenshots (isolated copies and the real q=0 layout), plus the F09 button test by real right-clicks |
| `sheet.py` → `approval/*.png` | labelled contact sheets; `comparison_approval_contact_sheet.png` is the side-by-side approval image |
| `../st03-placement-check/place-check-result-f09-f10.json` | placement-table checks (`--only M-prison,M-stable`) |

NBT sha256: prison `e3b9eb9f18add02f...`, stable `14255f69671efa17...`. They are identical in check-result, place-check and the capture info file.

## Verification (run in this task on the pinned 26.3 server, sha1 33680f5f...)

### `checks.py`: PASS

- **verify.py:** 0 mismatches, every authored state present unchanged.

  | | size | cells compared | non-air cells | palette states |
  |---|---|---|---|---|
  | F09 | 11×10×13 | 1430 | 759 | 49 |
  | F10 | 17×13×13 | 2873 | 956 | 48 |

- **Strict `place template`** (rotation none), every cell compared: 0 failures for both.

#### F09 access, iron doors closed by default

The walk search treats an iron door as closed unless a button the player can reach powers it: the button powers the block it is attached to, which powers the door next to it. The search repeats until nothing new opens. From the street entrance alone:
- each of the 6 buttons opens exactly one door: its own door, and only that one;
- all 5 iron doors open (front plus 4 cells);
- the vestibule, the corridor end and all four cells are reached, as are all 3 beds and the barrel (50 interior feet cells);
- from the vestibule, the inside button lets the player out again.

**Design choice to note:** from inside a cell with its door shut, there is no button, so the cell cannot be left without breaking the door or bars (jailer-side buttons only). This is reported in `check-result.json` (`from_inside_a_closed_cell`). Adding an inside button would be a one-line change if the owner prefers.

#### F09 buttons pressed in the real 26.3 client: PASS 6/6

`screenshots/capture-info-all.json`, `f09_button_test`. For each of the six buttons, the player was teleported in front of it and right-clicked it (xdotool mouse button 3). The server then read the states back. All six passed:
- the door was closed before the click;
- the button was powered right after the click;
- the door was open right after the click;
- the door was closed again 3 s later.

`f09_14_front_door_opened_by_button.png` was taken right after the outside click.

#### F10 player access

From the portal alone, every container and workstation inside is reached, as are the aisle, both pens and the store (96 interior feet cells). The supplies outside the walls are reachable from the open ground around the building.

#### F10 ravager space

**Geometric clearance.** The ravager hitbox (1.95 × 2.2) is tested as a 2×2×3 block box; only air, banner and button cells count as free.
- From each recorded pen position, the box reaches open ground beyond the portal (12 box steps each).
- 60 box positions inside the building are reachable.
- The portal cells x7..9, y1..4, z11..12 are all air, so it is 3 wide × 4 high.
- Both pen entries (x=6 / x=10, y1..3, z5..7) are all air, so each is 3 wide.
- There are no doors, fence gates or closed trapdoors inside.

**Vanilla-AI movement probe: PASS 4/4.** F10 was placed on flat ground. In each trial one real ravager was made to chase a NoAI villager (kept alive with Resistance V) by `damage <ravager> 0.5 minecraft:mob_attack by <villager>`, and its position was sampled every 0.25 s.

| pen | direction | closest distance to target | time |
|---|---|---|---|
| west | pen → outside | 1.63 | 4.8 s |
| west | outside → pen | 1.58 | 4.3 s |
| east | pen → outside | 1.65 | 5.1 s |
| east | outside → pen | 2.05 | 5.1 s |

- Every track crosses the portal line inside the portal width.
- Ravager health stayed at 99.5, i.e. only the 0.5 trigger damage, no damage from the building.
- This only shows that vanilla pathfinding gets a ravager in and out of each pen without being blocked. It is not the HQ spawn or garrison system.

**Storage built:**

| | chests | barrels | hay blocks | feed bins | water troughs |
|---|---|---|---|---|---|
| F09 | – | 1 | 3 | – | – |
| F10 | 1 | 10 | 46 | 2 | 2 |

F09 also has 3 beds and 1 straw pallet, 4 cell doors and the front door.

### `place_check.py --only M-prison,M-stable`: PASS

- **Footprint overlaps:** 0 for q=0..3.
- **Whole-structure turns q=1..3:** 0 failed cells (F09 759, F10 956 non-air cells).
- **All built placements placed together at q=0** (now including F09/F10): 0 failures, so F09/F10 and their neighbours (F08, F18, …) do not overwrite each other.
- **Test terrain falling 0..2 blocks:** stone footing filled (F09 110 columns, F10 170), 0 hollow, 0 template failures.
- **Entrances:**

  | entrance | outside cell | free run | direction |
  |---|---|---|---|
  | F09 front door | (97, 75) | 32 blocks | south, to the south wall |
  | F10 portal | (85, 92) | 15 blocks | south, to the south wall |

### Screenshots

Unmodified 26.3 client, Xvfb / lavapipe, noon, HUD hidden.
- **Isolated views:** front, both front diagonals, both sides, rear, rear diagonal and the entrance for each building.
- **Interiors:** night vision.
- **Context:** seven views in the real q=0 layout.
- **Ravagers:**
  - The two ravagers in `f10_14_interior_west_pen_test_ravager` and `f10_15_interior_east_pen_test_ravager` were summoned with NoAI at the recorded positions, only to show scale. Difficulty was set to easy, with natural mob spawning off, for those two views. They are not template content.
  - These two views were retaken with cameras looking through the pen entries, because in the main run the posts hid the ravagers. The retake is recorded in `capture-info-ravager-retake.json` (same NBT hashes; button test not repeated).
  - The main-run entries `f10_14_interior_pens_with_test_ravagers` and `f10_15_interior_west_pen_test_ravager_scale` in `capture-info-all.json` are those superseded shots; their files were removed.
  - Other animals in some views are vanilla flat-world spawns.

## Design iterations (reviewed in real client screenshots)

1. **F09 coped gables** had open half-cells, which read as gap teeth. The gables were then simplified to plain stone gables under the roof, with a projecting verge at the street gable.
2. **F09 grey-on-grey cobble roof** made the building a box. It became dark rubble slabs, with a battered plinth, a string course under the gable and taller 1×2 cell slits added.
3. **F09 cell fronts** were solid piers with buttons on them, which made the one-block corridor feel like a shaft. They became all bars, with each door's button on a lintel over the door. East and west doors are offset by one block, so each button opens only its own door.
4. **F10 walls** were spruce above two stone courses and read as a wooden barn. The lower walls are now stone up to y3, with spruce only in the gables and clerestory.
5. **F10 clerestory vents** were hidden under the nave eave. They moved down to the visible row.
6. **F10 feed barrels** behind the stack could not be reached. The rear stacks were rearranged so every barrel can be reached.
7. **Checks:**
   - The first ravager probe used an invulnerable villager, which vanilla never targets, so the ravagers never chose a target. It now uses a villager kept alive with Resistance V.
   - The first sampling interval (1 s) skipped the portal row. Sampling is now every 0.25 s, with an interpolated portal crossing test.

## Not covered / UNTESTED

- **Road connection: UNTESTED / not implemented.** The road masterplan and MQ ground modules are not in this repository.
- **Actual HQ ravager spawning:** the garrison system, two ravagers at worldgen, combat and persistence are **UNTESTED and not implemented**. Only the positions are recorded, and only the vanilla-AI movement probe above was run.
- **Not authored:** prisoner NPCs, escape mechanics, feeding mechanics, loot contents and mob spawns.
- **Natural hostile spawning** inside the buildings (light levels) was not tested. Every room has lanterns.
