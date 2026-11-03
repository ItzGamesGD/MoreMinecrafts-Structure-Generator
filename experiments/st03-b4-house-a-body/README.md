# ST-03 B3-04 — House A body (`st03_house_a.nbt`)

Stacked on `experiment/st03-b3-house-a` (Draft PR #51; its B3-01/B3-02 audit records are untouched). Not a main-merge candidate: owner visual review is still required.

**Status: BODY COMPLETE (experimental asset, owner review pending). PORCH NOT BUILT — tracked separately below.**

## What this is

`st03_house_a.nbt` is the Minecraft 26.3 template (DataVersion 5023) of module `M-house_a` from the committed 25-module / 34-placement table, built with the existing SEAM-01 export path (`tools.seam01.export.export_module`).

| Contract item | Value | Source |
|---|---|---|
| Module / file | `M-house_a` / `st03_house_a` | `tools/seam01/data/st03_placements.json` (unchanged) |
| Size (x, y, z) | 9 × 10 × 7, `air=include` | same; asserted at build time |
| Placements | F11 (14,0,11), F14 (89,0,11), rotation none, order 5 | same (unchanged) |
| Door | local (4,1..2,6), south, left hinge, closed | B3-01 authored cells |
| Cells | 311 authored non-air cells, 56 roof stairs (east x0..3 / west x5..8, bottom, straight) | `experiments/st03-b3-house-a/build.py::design()` (reused, not edited) |

The cell map is the B3-01 authored design reused unchanged: the NBT payload is byte-identical to `experiments/st03-b3-house-a/experimental_house_a.nbt` after gzip decoding (only the gzip OS header byte differs between platforms). No new design was added.

Rebuild: `PYTHONPATH=. python experiments/st03-b4-house-a-body/build_body.py` (needs `nbtlib`).

## Porch — NOT BUILT (separate open item)

B3-02 Q01-Q10 define the porch intent (3 deep, 5 wide, 7×4 with eaves, gable, separate accessory module), but the placement contract is not approved: no porch origin/bounding box, no absolute floor Y vs. the ground module (its NBT does not exist), no manifest rule for a 26th module or extra placements. The body therefore keeps its flush door and does **not** claim a porch. Nothing here changes the 25-module / 34-placement contract or the porch `air` decision.

## Verification (newly run, this branch)

| Check | Result |
|---|---|
| NBT generated, reproducible build | PASS |
| Size equals design [9,10,7], DataVersion 5023 | PASS |
| Independent verifier (`tools.structure_export.verify`) vs source: 630 cells, 0 mismatches, 16 palette states, 16 computed pane connections | PASS |
| Door south/lower+upper/hinge left/closed; all 56 roof stair facing/half/shape as authored | PASS |
| SEAM-01 `assemble(q)` q=0..3 with this template at F11 and F14: all 311 cells x2 land as expected | PASS |
| Contract unchanged: `tests/test_seam01.py` + `tests/test_structure_stairs.py` (79 tests) pass; placement table not modified | PASS |
| Pinned 26.3 server (jar sha1 `33680f5f…`), `place template … strict`, 4 rotations × 630 cells (`rotation-cell-result.json`) | PASS (0 failures) |

## Real client screenshots

`screenshots/*.png` are unmodified F2 screenshots from the vanilla 26.3 client (software Vulkan via Mesa lavapipe under Xvfb, 1280×720, HUD hidden). Setup and exact commands: `capture/capture_screenshots.py`, `screenshots/capture-info.json`. Views: front, back, west side, east side, interior (two), door close-up. The house is placed alone on a flat world with its floor flush with the grass (isolated module, no neighbours, no terrain correction). Interior views use a night-vision effect for brightness; exteriors do not. The door close-up shows the flush door; there is no porch to show.

## Not covered

Neighbouring ground modules / real assembly (no other ST-03 NBT exists), terrain interaction, porch, owner approval of the look (windows, roof, lantern, no chimney, as listed in the B3-01 README).
