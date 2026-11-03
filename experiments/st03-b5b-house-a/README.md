# ST-03 B3-05B — House A, autonomous design ("garrison house")

Stacked on `experiment/st03-b4-house-a-body` (Draft PR #52). This is a design experiment and an alternative to B3-05A; owner choice and visual review are pending. Not a main-merge candidate.

**NBT:** `st03_house_a.nbt` (module `M-house_a`, 9 × 10 × 7 x/y/z, `air=include`, DataVersion 5023). 348 authored non-air cells, 32 block types; 341 of the 630 cells differ from the B3-04 prototype.
Rebuild: `PYTHONPATH=. python experiments/st03-b5b-house-a/build.py`.

## Design

A small fortified quarters house: masonry below, timber above, a deep dark roof, a porch for the sentry.

| Element | Decision |
|---|---|
| Massing | Stone plinth (y 1–2) on the outer ring. The timber story is **set back one block** (x=1, x=7, z=1), so the deepslate roof gets a real one-block eave on both sides. The gables sit one block behind the roof's end rows. |
| Stone | Cobblestone with mossy patches, stone-brick quoins topped with chiseled stone bricks, and a sloped stone-brick water table (stairs) at y 3. Iron-bar arrow slits at eye height. |
| Timber | Dark-oak log posts, stripped dark-oak sill beams and plates, spruce-plank infill (lighter, so the frame reads). A clerestory window band under the eaves. |
| Roof | Deepslate tiles. Dark-oak barge rows on both overhanging ends, dark-oak ridge beam ends, two trapdoor vents in the back gable. |
| Entrance | Full-width **porch inside the box** (z=6): posts on stone footings in line with the door frame, a beam that carries the front roof row, fence rails in front of the windows, a lantern over the entry, and the ominous banner on the front gable. Floor flush with the ground, so no terrain correction is assumed. |
| Asymmetry | A stone chimney on the west side breaks the eave. Arrow slits differ per side (none where the chimney stands). The work corner is east and the hearth west. |
| Interior | Two-bed garrison room with a footlocker chest and an interior banner; hearth (furnace + cauldron) on the west; fletching table, crafting table, grindstone and stores on the east; anvil and stacked barrels; gray rug; hanging lantern plus a lantern on the stores. The 2-high alcoves under the set-back timber take the furniture. Containers are empty; loot is a runtime decision. |

## Contract compatibility

- Same module id, file, size and `air` as the contract.
- Nothing outside the 9×10×7 box. No 26th module and no placement change.
- The 112×112 layout and 25 / 34 table are untouched.
- The door stays on the south face (the side F11 / F14 face). The door moves from z=6 to z=5 because the porch takes the front row.
- Stair states are authored (facing / half / shape), and only straight runs are used.

## Reusable style rules for other headquarters buildings

1. Stone plinth 2 high (cobblestone + mossy, stone-brick quoins, chiseled caps), sloped stone-brick water table.
2. Timber story set back one block: dark-oak log posts, stripped dark-oak beams, spruce infill.
3. Deepslate-tile roofs with dark-oak barge boards and ridge ends; eaves overhang by one block.
4. Iron-bar arrow slits low, glass only in the timber band or under porches.
5. Ominous wall banner on the main facade, lanterns hung from beams or chains, stone chimneys off-centre.
6. Porches and overhangs are built inside the module box, never outside it.

## Verification (newly run on this branch, only on the new data)

`check-result.json` (from `checks.py`):
- Independent verifier: 630 cells, 0 mismatches.
- All 348 authored states are present (69 stairs; door south, lower + upper).
- Walk-in access: the door column is reachable from outside, and all 11 interactive blocks are reachable. This check caught a grindstone walled in by the anvil, which was fixed.
- Pinned 26.3 server, strict `place template`, rotation none: 630 cells, 0 failures.

## Real screenshots

`screenshots/` holds unmodified in-game F2 screenshots from the vanilla 26.3 client (Mesa lavapipe, Xvfb, 1280×720, HUD hidden). Setup: `capture.py`, `capture-info.json`. Views:
- front, back, left, right;
- three diagonals;
- entrance close-up;
- two interior views.

The first capture round showed porch posts hiding the front windows and an all-wood front; both were fixed before the final capture.

## Open

- Neighbour and terrain compatibility is untested (no other ST-03 NBT).
- Owner choice between 05A and 05B.
- B3-02 Q01 (external porch) is not met; this design uses an inside-the-box porch instead.
