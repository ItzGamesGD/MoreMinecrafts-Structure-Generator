# ST-03 facility batch 2 — houses B, C, D (F12/F15, F13/F16, F17)

Experimental assets stacked on `feat/st03-facility-batch1-20261105` (F18–F20) and House A (`62cec3e`); neither is changed. Owner visual review pending; not a main-merge candidate.

| Placements | Module | File | Size (x,y,z) |
|---|---|---|---|
| F12, F15 | M-house_b | `out/st03_house_b.nbt` | 9×10×7 |
| F13, F16 | M-house_c | `out/st03_house_c.nbt` | 7×9×7 |
| F17 | M-house_d | `out/st03_house_d.nbt` | 7×9×7 |

Placement table untouched (`air=include`, `local_turns=0`; front = +z). Rebuild: `PYTHONPATH=. python experiments/st03-batch2-houses/build.py`.

Design source: Q01–Q10 of the Beta ledger (`docs/planning/ST03_OWNER_APPROVED_DESIGN_Q01_Q42_2026-11-04.md`).
- **B:** regular spruce gable, covered porch inside the 9×10×7 bounds (two posts, beam, lanterns, banner), cobble base + spruce timber on a dark-oak frame, larger 2×2/3-wide shuttered windows, two-bed communal room (table, crafting table, furnace, chest, barrels).
- **C, D:** redesigned in v2 (ST03-BATCH2-REDESIGN, owner-delegated aesthetics); see below. The v1 C/D (commit `6421800`) is superseded.
- Containers are real and EMPTY (loot is a runtime decision); no chimneys, no extra features. Conservative choices where the ledger is silent: single-block shutters, all doors on the +z face.

## Verification (newly run on these NBTs)
`check-result.json` (`checks.py`): independent NBT verification 0 mismatches; authored states equal the template; entrance-to-every-interactive-block floor access; strict `place template` on the pinned 26.3 server, rotation none, 0 failures — PASS.
Placement at the real coordinates, whole-structure turns and test terrain: see `../st03-placement-check/README.md`.

## Screenshots
`screenshots/`: unmodified in-game F2 captures from the vanilla 26.3 client (6 exterior + 2 interior per house). `approval/` has contact sheets for owner review.

## v2 redesign of houses C and D (ST03-BATCH2-REDESIGN)

Only the integration constraints were kept: module sizes (7×9×7), placement table coordinates and rotations, collision-free footprints, a road-facing (+z) entrance, valid block states under rotation, walk-in access. Detailed palette/roof/window rules of Q01–Q10 were deliberately not enforced for C/D. House B is byte-identical (`ef2dd204…`).

Problems of v1: walls on the box edge left no eave or overhang, so both houses read as flat boxes; C's slab ledge looked unfinished; D was a squat box under a low roof.

- **C v2 — eave-front cottage.** Ridge turned east–west so the street sees the long eave; front and back eaves overhang the walls by one block; the gable triangles are set back one block behind a spruce barge so the roof reads as a separate mass; a small open cross-gable hood on fence posts shelters the door; stone lower story, spruce upper with dark-oak posts; window ledges; a stone chimney climbs the east gable end through the roof edge. Interior x1–5 × z2–4: bed, hearth furnace, crafting table, chest, barrel, bookshelves, banner, lanterns.
- **D v2 — fortified guard house.** A tall 5×5 stone body set one block inside the plot so a deepslate hip roof overhangs it on all four sides; sloped stone-brick plinth all round; dark-oak timber band under the eave; stone arch with chiseled keystone over the door; slit windows; banners on the front piers and lanterns under the front eave; lantern finial. Interior 3×3 (a compact guard room): bed, chest, stacked barrels, banner, lantern. The small room is the price of the all-round overhang.

Verification (newly run on v2 C/D only; unchanged structures not re-checked):
- `checks.py` with `ST03_ONLY=house_c,house_d` (entries merged into `check-result.json`): NBT verification 0 mismatches, authored states, entrance-to-every-container/workstation access, strict 26.3 placement — PASS. One real defect was found and fixed (C chest boxed in by the bookshelf and furnace; chest and bookshelf swapped).
- `../st03-placement-check/place_check.py --only M-house_c,M-house_d` → `place-check-result-cd-v2.json`: 0 footprint overlaps (q=0..3); rotations q=1..3 for F13/F16/F17 0 failures; all 10 built facilities placed together, 0 failures; test terrain footing 0 hollow cells — PASS.
- Screenshots: `screenshots/house_c_*`, `house_d_*` (front, front-left diagonal, front-right diagonal, back, back diagonal, entrance, 2 interior), vanilla 26.3 client; capture info in `capture-info-house_c-v2.json` / `capture-info-house_d-v2.json` (the older `capture-info.json` describes the v1 run). Owner sheets: `approval/house_c_v2_contact_sheet.png`, `approval/house_d_v2_contact_sheet.png`, `approval/houses_cd_before_after.png`.
- `capture.py` / `checks.py` accept `ST03_ONLY=<keys>` to limit a run to some houses.
