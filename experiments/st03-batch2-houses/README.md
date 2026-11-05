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
- **C:** asymmetric gable (ridge off-centre, steep west slope, long low east slope), recessed door between stone piers, timber walls with a partial stone west wall, three small asymmetric windows, one bed, bookshelves, chest, barrel.
- **D:** small hip roof with lantern finial, stone lower walls + timber upper, stone-framed defensive doorway, narrow barred windows, one guard bed, grindstone, fletching table, chest, barrel.
- Containers are real and EMPTY (loot is a runtime decision); no chimneys, no extra features. Conservative choices where the ledger is silent: single-block shutters, all doors on the +z face.

## Verification (newly run on these NBTs)
`check-result.json` (`checks.py`): independent NBT verification 0 mismatches; authored states equal the template; entrance-to-every-interactive-block floor access; strict `place template` on the pinned 26.3 server, rotation none, 0 failures — PASS.
Placement at the real coordinates, whole-structure turns and test terrain: see `../st03-placement-check/README.md`.

## Screenshots
`screenshots/`: unmodified in-game F2 captures from the vanilla 26.3 client (6 exterior + 2 interior per house). `approval/` has contact sheets for owner review.
