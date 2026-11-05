# ST-03 warehouse batch: F07 / F08 (candidate, awaiting owner approval)

Brief ST03-IMPLEMENT-06, built on `feat/st03-barracks-f02-f04-20261105` @ `9524790`. At the start of this task, the
branch existed locally and on the remote at that commit, and the working tree was clean.

The fixed contract is unchanged; `tools/seam01/data/st03_placements.json` is not modified:

| placement | module | size (x×y×z) | rect | street face | neighbours (gap) |
|---|---|---|---|---|---|
| F07 | `M-warehouse_a` | 15×12×13 | x 10..24, z 79..91 | +z (south): the open strip along the south wall toward the gate | F19 smithy east (3), W-W wall west (5), F06 yard north (6) |
| F08 | `M-warehouse_b` | 13×12×15 | x 75..87, z 53..67 | -x (west): the central street, like F03/F04 | F04 north (3), F18 / F09 east (4), F10 south (11) |

Both modules use `air = include`, floor y=0 and `local_turns` 0. No approved facility or NBT was changed. The only edit to shared tooling is `experiments/st03-placement-check/place_check.py`, which now also loads batch 5.

## Concepts

The two warehouses differ in mass, roof form, elevation and plan, not only in material.

### F07 "military depot": a buttressed stone tithe barn

**Exterior**
- Tall rubble-and-stone-brick walls (y1..6) with andesite quoins and clasping buttresses on all four sides.
- A **half-hipped (clipped-gable) deepslate roof**; the ridge course turns down over both gable ends.
- Paired high vents in the gables, barred ventilation slits in the long walls.

**Street side (Q42)**
- A projecting gabled **cart porch** with a stone-framed **2-block double dark-oak door** under an arched head.
- A timber gable (dark-oak frame, spruce boards, window).
- Illager banners and lantern posts.

**Interior**
- The porch opens into the hall through a wide timbered arch.
- Heavy dark-oak tie beams on knee braces span the hall, with king posts to the ridge; the floor is left free.
- A stone-brick **carrying aisle** runs from the porch to the back wall (banners, crates) between the two **storage bays**:
  - **West bay:** weapon chests and arrow crates under a railed **loft** (arrow stores, target, hay), reached by a ladder.
  - **East bay:** tall slab racks of barrels and crates, a spear barrel, shields on the wall, an anvil.

**Outside:** an east supply strip of barrels, hay and timber. The approach in front of the door is kept clear.

### F08 "timber stores": a tall timber-framed granary store

**Exterior**
- A two-course stone base.
- Dark-oak posts and wall plate, spruce board infill.
- A **steep dark-oak roof along the street, with a full-height cross gable** over the loading bay. Both roofs reach y=11, giving a vertical T-shaped silhouette.

**Street side (Q42)**
- A **3-wide × 3-high unloading opening** under a timber **awning** on brackets.
- A glazed loft door between two windows.
- A louvred apex vent.

**Other faces**
- Louvred vents in both gables.
- Shuttered rear windows (Q43).
- An **external timber stair** up the south gable to a loft door.

**Interior**
- A **double-height unloading bay** with a handcart, framed by a **U-shaped gallery loft**: north and south galleries plus a rear bridge, with a fence railing.
- Under the galleries: food barrels, composter grain bins, sacks, a pumpkin/melon rack, chests, hay.
- Loft stores: hay, sacks, barrels.
- Ways onto the loft: a ladder inside, or the outside stair.

**Outside:** barrels, a composter and hay stand beside the bay. The bay lane (z 6..8) is kept clear, and the north apron facing F04 is left empty.

## Contracts kept

- **Size and placement:** sizes as in the placement table; no move and no rotation change.
- **F04–F08 gap:** kept at 3 blocks, empty and walkable (checked below).
- **Containers:** all empty, using the block-entity allow-list. Q41 ordinary loot (F07 arrows/crossbows/iron/shields, F08 food/wood/coal/leather) is a runtime decision; no loot, item or probability is authored here.
- **Out of scope:** no mobs, AI, loot tables, roads or HQ-wide integration.

## Files

| file | what |
|---|---|
| `build.py` | `f07()`, `f08()`; `roof_layers()` lays the main roof under a cross roof so no gap opens between eave lines; `BUILDINGS` (entrances, wall boxes); writes `out/` |
| `out/st03_warehouse_{a,b}.*` | NBT, source .schem, export report |
| `checks.py` → `check-result.json` | NBT/state validity, walk access, storage counts, F04–F08 gap, strict 26.3 placement (`--offline` skips the server for iteration) |
| `capture.py` → `screenshots/` | real 26.3 client F2 screenshots: isolated copies plus the real q=0 layout with every built neighbour |
| `sheet.py` → `approval/*.png` | labelled contact sheets; `comparison_approval_contact_sheet.png` is the side-by-side approval image |
| `../st03-placement-check/place-check-result-f07-f08.json` | placement-table checks (`--only M-warehouse_a,M-warehouse_b`) |

NBT sha256: a `8bb4ea0061284596...`, b `503151fff5beb5de...`. They are identical in check-result, place-check and both capture-info files.

## Verification (run in this task on the pinned 26.3 server, sha1 33680f5f...)

### `checks.py`: PASS

- **verify.py:** 0 mismatches, every authored state present unchanged.

  | | size | cells compared | non-air cells | palette states |
  |---|---|---|---|---|
  | F07 | 15×12×13 | 2340 | 835 | 69 |
  | F08 | 13×12×15 | 2340 | 920 | 65 |

- **Strict `place template`** (rotation none), every cell compared: 0 failures for both.
- **Access**, from each entrance alone with no outside ground allowed. Every container and workstation inside the walls is reached, and every key point is reached:

  | | key points | interior feet cells | loft feet cells |
  |---|---|---|---|
  | F07, from either door leaf | porch, aisle head, west bay, east bay, loft walkway | 85 | 11 |
  | F08, from the unloading bay | bay, north/south stores, rear bay, north gallery, gallery bridge, south gallery, loft-door landing | 143 | 38 |

  F08's external loft stair reaches the same 38 loft cells on its own. Apron supplies are reachable from the open ground around each footprint.
- **Storage built:**

  | | chests | barrels | crate/sack blocks | walkable loft cells |
  |---|---|---|---|---|
  | F07 | 3 | 24 | 20 | 11 |
  | F08 | 2 | 16 | 33 | 38 |

- **F04–F08** (approved F04 NBT and F08 at their real offset, (0, 0, 14)):
  - The gap is global z 50..52, i.e. 3 blocks.
  - 0 blocks of either template are in it, at any height.
  - All of it is walkable (feet and head free) across F04's width ±1.
  - F08's north apron is empty at y1..3.

### `place_check.py --only M-warehouse_a,M-warehouse_b`: PASS

- **Footprint overlaps:** 0 for q=0..3.
- **Whole-structure turns q=1..3:** 0 failed cells (F07 835, F08 920 non-air cells).
- **All 17 built placements placed together at q=0:** 0 failures, so F07/F08 and their neighbours (F19, F06, F04, F18, …) do not overwrite each other.
- **Test terrain falling 0..2 blocks:** stone footing filled straight down (F07 150 columns, F08 156), 0 hollow, 0 template failures.
- **Entrances:**

  | entrance | outside cell | free run | direction |
  |---|---|---|---|
  | F07 cart porch | (16..17, 92) | 15 blocks | south, toward the south wall |
  | F08 unloading bay | (74, 60) | 38 blocks | west |
  | F08 loft stair | (75, 68) | 39 blocks | south |

### Screenshots

Unmodified 26.3 client, Xvfb / lavapipe, noon, HUD hidden.
- **Isolated elevations:** front, front-left, front-right, both sides, rear and rear diagonal for each warehouse.
- **Interiors:** night vision.
- **Context:** seven street-context views in the real q=0 layout, including the F04–F08 passage.
- **Pigs:** the pigs in some views are vanilla flat-world spawns, not template content.

**Interior retakes.** Some interior views were retaken with corrected cameras after the main run (`capture-info-all.json`).
- The second retake run (`capture-info-interior-retake.json`: `f07_11`, `f08_10`) overwrote the first run's info file.
- `f08_09_interior_bay_and_gallery.png` therefore comes from the first retake run. Its camera is the one in `capture.py`, and the file's sha256 is `52ebe7533b47b1ea...`, which differs from the main-run entry `c7dc86d6...`.
- All runs used the same NBT hashes.
- `f07_11_interior_from_loft` is kept but left out of the sheets because the loft's tie beam blocks the view. The loft is shown in `f07_09`.

## Design iterations (reviewed in real client screenshots)

1. **F07 half-hip** stepped down three courses and read as a chimney. It is now clipped to the ridge course, with tile ridge ends turned down. A dark porch-ridge slab that also read as a chimney was removed.
2. **F07 interior:** two rows of colonnade posts crowded the 10×6 hall. They were replaced by tie beams on knee braces with king posts, so the aisle is defined by the runner, the racks and the loft rail.
3. **F08 facade** had rails at y3, y5 and y8 plus the awning and lintel, and read as cluttered stripes. Rails are now only at the wall plate, and a two-course stone base was added.
4. **F08 spruce barge boards** matched the spruce gables, which read as stepped plank pyramids. The verges are now dark oak, so the roof outline is crisp.
5. **F08 external stair** had solid plank fill and read as a wedge. It now rests on two dark-oak posts.
6. **Offline access check** found:
   - crates boxed in by neighbouring barrels and anvils (F07);
   - the F08 inside ladder topping out under the low roof edge. It was moved to the north gable, where there is headroom.

   All were fixed before the checks above.

## Not covered / UNTESTED

- **Road connection: UNTESTED / not implemented.** The road masterplan and MQ ground modules are not in this repository.
- **F07's street face** is a design choice: the south strip leading to the gate. The east side (F19, 3 blocks) and the north side (F06, 6 blocks) are too tight for a cart entrance.
- **`BUILDINGS[...]["door"]`** for F08 is on the -x face. `place_check.py`'s legacy `front_free_blocks` field assumes +z for every module; use its `entrances` block.
- **Not authored:** loot contents, mob spawns and any loading mechanic.
