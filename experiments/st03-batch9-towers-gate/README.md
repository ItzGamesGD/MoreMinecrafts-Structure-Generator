# ST-03 batch 9: corner tower MT and gatehouse MG (candidate, owner screenshot approval pending)

Perimeter steps (2) and (3) of Q91: the four towers and the south gate with its upper observation room. Base: the
batch-8 tip `831e125` (`feat/st03-perimeter-walls-20261106`), unchanged. The walls used everywhere below are the
**batch-8** MW86 / MW31. The wall F prototype is not adopted (see `docs/st03/wall-lines-comparison-20261114.md`).

| module | size x×y×z | NBT | placements (st03_placements.json, unchanged) |
|---|---|---|---|
| MT | 13×24×13 | `out/st03_tower.nbt` | T-NW x0-12 z0-12 (turns 0), T-NE x99-111 z0-12 (1), T-SE x99-111 z99-111 (2), T-SW x0-12 z99-111 (3) |
| MG | 24×20×12 | `out/st03_gatehouse.nbt` | GATE x44-67 z100-111 (0) |

air = include (module table). In every tower placement, local x=0 and z=0 are the two outer faces of the corner. The
walls meet the tower on its local x=12 face (rows z0-4) and z=12 face (columns x0-4). For the gate, local z=11 is the
outside (south) and z=0 the compound. W-SW meets its x=0 face and W-SE its x=23 face, both over z7-11.

## Design (owner ledger Q80-Q90)

**MT corner tower** (one NBT for all four placements):

| part | design | ledger |
|---|---|---|
| body y0-13 | 2-thick stone shell around a 7×7 open shaft; footing course y0 | Q84 |
| exterior faces | corner quoins and a recessed panel with a weathered plinth and a corbel band | |
| compound faces | a smaller recessed panel, kept clear of the wall joints | |
| ground floor | dark-oak door in a 3-high recess on the compound side, lantern over it; barrels, a lantern and timber stores | Q81 independent access |
| ladder | one direct ladder from y1 through the lookout floor (y14); no intermediate floor | Q83 A |
| lookout y15-17 | open observation gaps on all four sides: one-block stone breastwork, eight dark-oak posts, knee braces, wall plate | Q84 |
| roof | dark-oak hipped (pitched) roof from y18 to the y23 finial, with explicit outer-corner stair shapes | Q84 |
| lanterns | 8 hanging under the eaves, 2 on a tie beam, 1 in the shaft, 1 on the stores, 1 in the door recess | |
| banners | 4: one on each exterior panel, one on each compound panel | |
| openings | arrow slits through the shell (y5-6 and y10-11) | Q82 |
| wall-top access | none; no patrol route | Q81 A |

**MG gatehouse:**

| part | design | ledger |
|---|---|---|
| passage | x9-14, clear 6 wide × 6 high (7 between the arch corbels), straight through z0-11, paved in mixed cobble / andesite / stone brick | Q86, Q88 |
| portals | andesite pillars at both ends, a massive dark-oak lintel and stone-brick arch corbels | Q86 |
| gate leaves | two dark-oak leaves (boards, a log hanging stile at the outer portal, iron strap bands). Solid blocks, fixed open against the passage sides; nothing moves or opens | Q86: permanently open, static, nonfunctional |
| core | upper gatehouse over the passage | |
| turrets | two front turrets reach the exterior face. Their front is set back between corner piers under a corbelled parapet; crenellations on the turrets and the core deck | Q86 |
| observation room y10-12 | 20×4 room, entered only by its own ladder (y1-9) in a west side shaft. The shaft has a door on the compound side | Q87 |
| room openings | toward the exterior approach (over the portal and through both turrets) and toward the checkpoint | Q87 |
| room furnishing | timber posts and beams, 2 lanterns, 1 ordinary chest (empty), 1 weapon rack (stripped logs + lightning-rod spears), 1 barrel | Q87 |
| checkpoint, inside (z0-3) | stone paving to the road, wall-post lanterns flanking the passage, two timber barriers, two weapon racks, banners on the gatehouse face, barrels and hay | Q80 |
| approach, outside (z10-11) | a forecourt between the turrets, **inside the 112×112 box** (Q88 forbids extension): banners on both turrets and over the portal, wall-post lanterns, a log pile, a barrel, a rack and a fence barricade beside the passage | Q88 |
| wall walkway | none | Q81 / Q87 |

Containers are empty (block-entity allow-list); loot is a runtime decision. No mobs, spawners, redstone or mechanics.

## Verification (all newly run 2026-11-14 on the pinned 26.3 server, sha1 33680f5f…)

| # | item | result | evidence |
|---|---|---|---|
| 1 | NBT size and block states | PASS | `check-result.json` `modules`: verify.py, 0 mismatches. MT: 4056 cells (2003 non-air), palette 43. MG: 5760 cells (2206 non-air), palette 41. Every authored state is in the NBT unchanged, with no extra non-air cell. Strict `place template`: 0 failures for both, every air cell included. |
| 2 | support | PASS | Every lantern, wall banner and ladder is supported: 0 unsupported. |
| 3 | Q86 static gate | PASS | No functional block in MG apart from the shaft door to the room: no fence gate, trapdoor, lever, button, plate, redstone or piston. Passage 6×6 clear over z0-11, paved floor without gaps. |
| 4 | traversal (template grid search) | PASS | MT: from outside the door to the lookout floor, 129 lookout cells reached; lookout headroom 2 everywhere; 48 open gap cells. MG: checkpoint → shaft door → ladder → room (84 room cells); straight through the passage from outside to the compound. |
| 5 | MT roof | PASS | All 169 columns covered by exactly one roof block. |
| 6 | boundaries, q=0-3 | PASS | No overlap with any of the 34 placements. Each tower abuts exactly its two walls; the gate abuts W-SW and W-SE. The tower door and gate passage open onto free compound ground inside the box (q=0: T-NW (13,8), T-NE (103,13), T-SE (98,103), T-SW (8,98), gate x53-58 z99). Exterior faces lie outside the box. |
| 7 | wall joints, q=0 assembly | PASS | All 10 wall ends: every solid end cell (48 per end) has a solid tower / gatehouse block directly behind it — no gap or slot. Also run offline against the wall F NBTs: 53/53 per end. |
| 8 | rotations q=1-3, every cell | PASS | `../st03-placement-check/place-check-result-towers-gate.json` live A: 28 placements per turn (towers, gate, walls, facilities), 0 failures. |
| 9 | integrated q=0, everything together | PASS for MT / MG / walls | Same file, live B: 0 failures in the 4 towers, the gate and the 5 walls. **2 failures in F06** (`grass_block` turned to dirt under F06's own stone floor): a pre-existing, intermittent F06 defect, see below. |
| 10 | 0-2 drop test terrain (live C) | PASS | Every placement, including MT / MG: 0 hollow cells, 0 template failures. |
| 11 | slope sites (Q89 fill, test terrain) | PASS | `check-result.json` `slope_sites`. For each site: placement at grade, the fill, then 0 template failures, 0 hollow cells, 0 cells changed outside the footprint. See the table below. |
| 12 | real 26.3 client screenshots | done | 58 F2 screenshots in `screenshots/` (`capture-info-all.json`; the four `pl_0[5-8]` tower-door views were retaken, `capture-info-door-retake.json`), 8 contact sheets in `approval/`. |
| – | natural worldgen (real seeds and biomes), ground / road modules, garrison, loot | UNTESTED / not built | |

Slope sites (item 11):

| site | module | ground relative to grade | columns filled | max fill | terrain above grade inside the box |
|---|---|---|---|---|---|
| T1 falls to the outer corner | MT | −5 to 0 | 163 | 5 | 0 |
| T2 undulating | MT | −4 to +2 | 84 | 4 | 73 cells cleared |
| G1 falls outward (approach side) | MG | −5 to 0 | 192 | 5 | 0 |
| G2 cross slope | MG | −4 to +3 | 144 | 4 | 192 cells cleared |

Because MT and MG are `air = include` in the module table, terrain above grade inside their box is cleared to air.
The walls are `air = omit` and bury their footing instead. This follows from the module table; it is not a choice
made here.

## Screenshots (`screenshots/`, contact sheets in `approval/`)

Unmodified 26.3 client, Mesa lavapipe under Xvfb, in-game F2, noon. NBT hashes in `capture-info-all.json` match `out/`.
- `mt_*`: isolated tower. Exterior corner and face, compound side and door, shaft and ladder, lookout, roof, aerial.
- `mg_*`: isolated gatehouse. Approach, forecourt, checkpoint, passage and leaves, shaft, room (both ends, openings),
  battlements.
- `rot_*`: each module placed in all four rotations and photographed from the same world direction, plus a row aerial.
- `pl_*`: the real q=0 layout, with all built modules together. Each tower is shown from outside and at its door; the
  gate from outside and inside.
- `jt_*`: wall/tower and wall/gate joints.
- `sl_*`: the four slope sites (test terrain, with an apron and ramp added for the pictures only).
- `ov_*`: the whole compound from three aerial positions. The ground / road modules are not built.

## Revisions made in this batch after looking at the client

- **Gate leaves:** they sat deep in the passage and were barely visible. They are now hinged at the outer portal and
  read from the approach.
- **Gate front:** it read as a flat slab. The turret fronts are now set back between corner piers under a corbelled
  parapet, with a dark-oak lintel over both portals.
- **Tower compound faces:** they were blank. Each now has a recessed panel with a banner, kept clear of the wall
  joints.
- **Tower door views in the real layout:** neighbouring houses and F07 blocked the first cameras. They were moved into
  the free strip between the wall and the facilities and retaken.

## Remaining weaknesses (seen in the client)

- The observation room is only 4 deep, so it reads as a gallery more than a room.
- `mt_08_lookout_from_ladder` looks at the shaft wall. The lookout itself is shown by `mt_07`.
- Banners render as the project's standard plain white wall banner, as in earlier batches.
- The tower's compound faces are still plainer than its exterior faces (by design: Q90 puts the decoration outside).

## Not part of this batch / UNTESTED / owner decisions

- **Ground and road modules MQ-NW/NE/SW/SE: not built.** The road masterplan (DESIGN_PACKAGE_V2, outside the
  repository) is required and is not available. The authority documents keep the road graph OPEN. Owner decision.
- **Q85 placement-specific variation:** not authored. One NBT serves all four towers, and the placement table has one
  MT module. Variation needs either four tower files (a placement-table change) or a placement-time processor in the
  Beta world generator. Owner decision.
- Natural worldgen on several seeds (Q92) and the generator hook for the Q89 fill: UNTESTED.
- Any combat, garrison or loot behaviour: none is authored.

## Reproduce

```
PYTHONPATH=. python experiments/st03-batch9-towers-gate/build.py
PYTHONPATH=. python experiments/st03-batch9-towers-gate/checks.py --server-jar server.jar --java java25 --work <dir>
PYTHONPATH=. python experiments/st03-placement-check/place_check.py --server-jar server.jar --java java25 --work <dir> \
    --out experiments/st03-placement-check/place-check-result-towers-gate.json
PYTHONPATH=. python experiments/st03-batch9-towers-gate/capture.py --server-jar server.jar --java java25 \
    --client-dir client --work <dir> --out experiments/st03-batch9-towers-gate/screenshots
python experiments/st03-batch9-towers-gate/sheet.py experiments/st03-batch9-towers-gate/screenshots \
    experiments/st03-batch9-towers-gate/approval
```
