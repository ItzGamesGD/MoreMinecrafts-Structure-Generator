# ST-03 batch 8: perimeter walls MW86 / MW31 (candidate, owner screenshot approval pending)

Perimeter step (1) of Q91: the wall and its locally adapted stone footing. Towers, gatehouse and ground / road modules
are later batches; their reserved areas are left empty here (no stand-in structure).

| module | size x×y×z | NBT | placements (st03_placements.json, unchanged) |
|---|---|---|---|
| MW86 | 86×13×5 | `out/st03_wall_86.nbt` | W-N x13-98 z0-4 (turns 0), W-E x107-111 z13-98 (1), W-W x0-4 z13-98 (3) |
| MW31 | 31×13×5 | `out/st03_wall_31.nbt` | W-SW x13-43 z107-111 (2), W-SE x68-98 z107-111 (2) |

air = omit (module table): the NBTs contain no air cells, so terrain in front of the recessed face stays as it is.
Every rotation maps local z=0 onto the outside of the 112×112 box, so z=0 is always the exterior face. Both ends of
both modules meet a tower square or the gate, so the two ends are built identically (MW31 meets the gate with its
x=0 end at W-SW and with its x=30 end at W-SE).

## Design (owner ledger Q81, Q82, owner stone principle, Q89, Q90)

Section, from the outside (z0) to the compound side (z4):

- **y0 footing course** over the full depth: cobblestone, mossy cobblestone, andesite, stone, stone bricks. It projects
  one block on both sides of the curtain.
- **y1 battered plinth**: stone-brick, cobblestone and andesite stairs leaning on the wall, outside and inside.
- **Curtain**, z1-3, y1-8. The outer face sits back behind the plinth and the parapet. Weathering comes in staggered
  patches, not per-block speckle: mossy low down and near the ends, cracked stone bricks anywhere, cobble and andesite
  repairs low on the wall. The end columns and the top course stay clean stone brick.
- **y8 corbel table** at z0: upside-down stone-brick stairs carrying the projecting parapet.
- **y9 parapet sill** at z0 and an inner lip at z3.
- **y10-11 merlons and crenels**, with merlon caps at y12, so the 13-high silhouette is constant.
  - MW86: 2-wide merlons and 1-wide crenels, symmetric, 58 merlon and 28 crenel columns.
  - MW31: 3-wide end merlons as piers, 22 merlon and 9 crenel columns.
- **Pilaster buttresses**: MW86 at x 12-13, 26-27, 42-43, 58-59 and 72-73; MW31 at x 14-16. Each tie the plinth to
  the parapet outside and is capped inside. The two end columns are piers.
- **Arrow slits**, 1 wide × 2 high through the wall at y4-5: MW86 x21, 36, 49, 68; MW31 x12, 18.
- **End zones** (9 blocks at each end, toward a tower or the gate; Q90 puts the military decoration here):
  - Outside: a dark-oak beam in place of the corbels on two timber brackets, a hanging lantern, an illager banner, and
    at the base either barrels or a log pile.
  - Inside: a dark-oak beam on three brackets under the inner lip, a hanging lantern, a banner, a barrel, a log pile
    and moss.
- **Between the end zones** (restrained): MW86 has two hanging lanterns, three banners, a barrel and moss carpets; MW31
  has moss carpets.
- **No continuous patrol route is required (Q81).** The channel between the sill and the inner lip is just the top of
  the wall.
- Containers are empty barrels (cosmetic; block-entity allow-list). No mobs, spawners, loot or mechanics.

Counts per module:

| | lantern | wall banner | barrel |
|---|---|---|---|
| MW86 | 6 | 7 | 5 |
| MW31 | 4 | 4 | 4 |

### Footing on slopes (Q89): a placement step, tested on test terrain only

The NBT is fixed: its y0 course sits at grade and the wall top is always grade + 12, in all five placements.
- **Ground below grade:** every footprint column is filled with masonry from the ground surface up to the footing
  course. The masonry is coursed rough stone in staggered horizontal patches (`slope.py`, `fill_block`); one material
  per column read as vertical stripes in the first draft.
- **Ground above grade:** the terrain is kept, because air is omitted, and the footing is buried.
- **Outside the footprint:** nothing is touched, and nothing is flattened.

This is the rule as it would be applied at generation time. **Hooking it into real worldgen is not part of this batch
(UNTESTED).**

## Verification (all newly run for this batch on the pinned 26.3 server, sha1 33680f5f…)

| # | item | result | evidence |
|---|---|---|---|
| 1 | NBT size and block states | PASS | `check-result.json` `modules`: verify.py, 0 mismatches. MW86: 3246 cells, palette 26. MW31: 1198 cells, palette 26. Every authored state is in the NBT unchanged, no extra cells, no air cells. Strict `place template` (rotation none): 0 failures for both. Lanterns and banners: 0 unsupported. Silhouette: 0 problems in every column (complete footing, curtain to y8, sill and lip at y9, top at y12 or y9, solid end columns). |
| 2 | W-N, W-E, W-W, W-SW, W-SE placement | PASS | `../st03-placement-check/place-check-result-walls.json`, live B (q=0): all 5 walls placed together with every built facility (F01-F20 and House A) at their real origins and rotations. 0 failures in all 5 walls; every other facility cell also compared, 0 failures. |
| 3 | turns 90, 180 and 270 | PASS | Same file, live A: the whole-structure turns q=1-3, every wall cell compared with the rotated state (stairs, banners, logs). 0 failures in 15 placements. |
| 4 | clash with F01-F20 | PASS | Offline: 0 footprint overlaps among all 34 placements for q=0-3. Nearest facility to each wall: W-E–F09 4 blocks, W-W–F07 5, W-N–F01/F11/F12 6, W-SW–F07 15, W-SE–F10 15. Live B: no facility cell overwritten. |
| 5 | boundaries of the tower squares and the gate | PASS | `check-result.json` `boundaries`, q=0-3: no overlap with T-NW, T-NE, T-SE, T-SW or GATE. Both ends of each wall abut exactly the expected tower or gate (gap 0): W-SW x43 meets GATE x44, and W-SE x68 meets GATE x67. The exterior face is outside the box, and the top is at y12 in every placement. |
| 6 | footing on test slopes | PASS (test terrain) | `check-result.json` `slope_sites`. For each site: strict placement at grade, the Q89 fill, then every template cell compared (0 failures), every cell between the ground and the template checked (0 hollow), and the terrain outside the footprint unchanged (0 changed). See the slope sites table below. |
| 7 | real 26.3 client exterior views | done | 41 F2 screenshots and 7 contact sheets in `approval/` (see below) |
| 8 | visual check of ends, corners and footing | done, defects fixed | See defects found and fixed below. |
| – | natural worldgen: real seeds and terrain, generator hook-up, joins to towers and gate that do not exist yet | UNTESTED | |

Slope sites (item 6):

| site | wall | ground relative to grade | columns filled | maximum fill depth |
|---|---|---|---|---|
| S1 longitudinal valley | MW86 | −5 to 0 | 400 | 5 |
| S2 cross slope, outside lower | MW31 | −4 to 0 | 124 | 4 |
| S3 undulating, partly above grade | MW31 | −4 to +2 | 64 | 4 |

S3 also keeps 5 terrain cells above grade inside the box.

The earlier place_check live C was also run for the walls only (`--only MW86,MW31`). Its fixed 0-2 drop test terrain
gave 0 hollow cells and 0 template failures.

## Screenshots (`screenshots/`, contact sheets in `approval/`)

Unmodified 26.3 client, Mesa lavapipe under Xvfb, in-game F2, noon. NBT hashes in `capture-info-*.json` match `out/`.
- `mw86_*` and `mw31_*`: isolated copies, full exterior, exterior front, close end, close middle, full interior, close
  interior end, parapet, end section.
- `pl_*`: the five placements from outside and inside in the real q=0 layout.
- `jt_*`: the four corner tower squares (empty) and the NW corner from inside.
- `gt_*`: the gate gap from outside and inside, and the west (W-SW) and east (W-SE) wall ends.
- `sl_*`: the three slope sites. Test terrain mounds; for the pictures only, a wider apron and a ramp down to the
  flat world are added.
- `ov_*`: the whole 112×112 compound from three aerial positions. **Retaken** (`capture-info-overview-retake.json`)
  with server view distance 12 and render distance 12. At the test server's default of 6 chunks, part of the compound
  was never sent to the client.

## Defects found and fixed in this batch

- **Interior end timber:** two full-height posts with a beam read as a doorway from a distance. Replaced by a beam on
  three brackets under the inner lip.
- **Footing fill:** one material per column gave vertical stripes. It is now coursed rough masonry in horizontal
  patches.
- **Cross-slope test terrain:** the S2 terrain had a regular pit pattern. It now has a smooth profile.
- **Decoration clashes:** a banner hung in front of an arrow slit. The slits were moved clear of banners, lanterns and
  timber.
- **Wall ends:** the end columns are now solid piers, so the cross-section shows a clean edge toward the future tower
  or gate.
- **Aerial screenshots:** cut off by the server view distance; retaken (see above).

## Not part of this batch / UNTESTED

- Towers (MT), gatehouse (MG), ground and road modules (MQ-*), and how the wall joins them visually.
- Generating the footing fill in real worldgen.
- Natural terrain on several world seeds (Q92). Only the synthetic slope sites S1-S3 and the place_check drop terrain
  were tested.
- Any combat or spawn behaviour on or around the walls: none is authored.

## Reproduce

```
PYTHONPATH=. python experiments/st03-batch8-perimeter-walls/build.py
PYTHONPATH=. python experiments/st03-batch8-perimeter-walls/checks.py --server-jar server.jar --java java25 --work <dir>
PYTHONPATH=. python experiments/st03-placement-check/place_check.py --server-jar server.jar --java java25 --work <dir> \
    --only MW86,MW31 --out experiments/st03-placement-check/place-check-result-walls.json
PYTHONPATH=. python experiments/st03-batch8-perimeter-walls/capture.py --server-jar server.jar --java java25 \
    --client-dir client --work <dir> --out experiments/st03-batch8-perimeter-walls/screenshots
python experiments/st03-batch8-perimeter-walls/sheet.py experiments/st03-batch8-perimeter-walls/screenshots \
    experiments/st03-batch8-perimeter-walls/approval
```
