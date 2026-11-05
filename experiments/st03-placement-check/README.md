# ST-03 placement check of the built facilities (2026-11-05)

`place_check.py` checks the facilities that are built today (House A, houses B/C/D, kitchen, smithy, cart shed) at their real positions from `tools/seam01/data/st03_placements.json`. Result: `place-check-result.json`.

| Check | Scope | Result |
|---|---|---|
| Footprint overlaps, all 34 placements, q=0..3 | offline | PASS (0 overlaps) |
| Free corridor in front of each entrance | offline | 3–19 blocks (F17 and F18: 3, nearest neighbour F18 / F09) |
| Whole-structure turns q=1,2,3: every cell of F12–F20 `place template` strict, compared with the rotated template (doors, workstations, containers, stairs, panes, logs) | live 26.3 server | PASS, 0 failures |
| q=0, all 10 built facilities placed together at real coordinates, every cell compared | live 26.3 server | PASS, 0 failures (no facility overwrites a neighbour) |
| TEST terrain falling 0–2 blocks to the north, floor kept at entrance-side ground, stone footing filled straight down, hollow-column scan | live 26.3 server, synthetic terrain | PASS (0 hollow cells, 0 template failures) |

Not covered: **road connection** (the road masterplan and ground modules MQ-* are not in this repository and not built, so only the free corridor can be reported: UNTESTED), natural worldgen, real-biome terrain, drops above 2 blocks, retaining walls and entrance stairs (not needed in the test), House A rotations (verified earlier, not repeated).

Tool notes (verification-side, not game defects): the repo helper `rotate_props` leaves horizontal `axis` (logs) and vertical `facing` untouched, so `rot()` in `place_check.py` adds x↔z axis swapping on 90° turns. Two script bugs were found and fixed while writing the check (a 1-block-drop `fill` that swapped its corners and overwrote the floor; the missing axis rotation). No NBT changed.
