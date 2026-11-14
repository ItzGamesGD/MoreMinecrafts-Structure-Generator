# ST-03 B3-05A — House A, formal build (keeps the existing design)

Stacked on `experiment/st03-b4-house-a-body` (Draft PR #52), which is stacked on #51. Experimental asset: owner visual review pending, not a main-merge candidate. B3-05B (separate branch) is the free-design alternative.

**NBT:** `st03_house_a.nbt` (module `M-house_a`, 9 × 10 × 7 x/y/z, `air=include`, DataVersion 5023). 326 authored non-air cells, 25 block types; 183 of the 630 cells differ from the B3-04 prototype.
Rebuild: `PYTHONPATH=. python experiments/st03-b5a-house-a/build.py`.

## Kept (existing design, unchanged)

| Rule | Where it comes from | In this build |
|---|---|---|
| 9×10×7 box, `air=include`, F11/F14 placements, 25 modules / 34 placements | `tools/seam01/data/st03_placements.json` | asserted at build time; table untouched |
| Walls on the box edge, room x1..7 × z1..5, floor y=0 | B3-01 README (package) | same |
| South door at (4, 1..2, 6) | B3-01 / package | same door, same states |
| Stone base, dark-oak upper story, gable | package "existing design" | cobblestone base course; dark-oak planks + dark-oak frame |
| N-S gable, ridge x=4 y=9, profile y = 5 + min(x, 8−x) | B3-01 geometry | same profile and stair facings (east / west, bottom, straight) |
| Bed (1–2,1,1) east, crafting table (7,1,1), furnace (7,1,3) west, barrel (1,1,5) east | package `decor.py` | exact cells and states |
| Porch: B3-02 Q01-Q10 intent, external, separate module | B3-02 decisions | **not built** (see blockers) |

## Changed / added (detail, within those rules)

- **Timber frame:** dark-oak log corner, mid and door posts; stripped-log top plates; door lintel.
- **Gable set back one block (z=1 / z=5):** the roof now overhangs both gable ends. Each gable has a tie beam, a king post and plank infill.
- **Roof:** deepslate-tile stairs, with dark-oak barge rows on the overhanging ends and a dark-oak ridge beam end.
- **Chimney:** stone, in the east wall behind the furnace, breaking the eave, with a wall cap.
- **Front overhang:** an ominous (illager) wall banner on the king post, and chain-hung lanterns over the front windows.
- **Interior:**
  - furniture: chest, fletching table, chipped anvil, grindstone, stacked barrels;
  - decoration: a gray rug and an interior ominous banner;
  - lighting: a lantern on a barrel and two wall torches by the door, alongside the original hanging lantern.
  - All containers are empty; loot is a runtime decision.

## Limits of the existing design (reported, not changed)

- Walls sit on the box edge, so the side walls can have **no eave overhang** and no window frames that stick out. Depth only comes from the gable setback and the timber frame.
- The base course is only one block high, so the stone base reads thin.
- B3-05B shows what a set-back wall would allow.

## Verification (newly run on this branch, only on the new data)

`check-result.json` (from `checks.py`):
- Independent verifier: 630 cells, 0 mismatches, 35 palette states.
- All 326 authored states are present in the template (including 55 stairs and the door: south, lower + upper).
- Walk-in access: the door column is reachable from outside, and every interactive block is reachable.
- Pinned 26.3 server, strict `place template`, rotation none: 630 cells compared, 0 failures.
- The exporter and rotation code are unchanged, so the earlier rotation checks were not repeated.

## Real screenshots

`screenshots/` holds unmodified in-game F2 screenshots from the vanilla 26.3 client (Mesa lavapipe under Xvfb, 1280×720, HUD hidden). Setup: `capture.py`, `screenshots/capture-info.json`. Views:
- front, back, left (west), right (east);
- two diagonals;
- entrance close-up;
- two interior views (night vision applied only for the interior).

The house stands alone on a flat world, floor flush with the grass. There are no neighbours and no terrain correction.

## Blockers

- **Porch:** needs an approved placement contract: origin and bounding box, absolute floor Y against the ground module, and the manifest rule for a porch module. Nothing that counts as a porch fits inside the box under Q01 (external).
- Neighbour and terrain compatibility is not tested, because there is no other ST-03 NBT yet.
