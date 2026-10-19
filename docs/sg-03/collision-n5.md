# SG-03-N5 — Natural worldgen collision investigation (geodes and monster rooms)

**Verdict: PARTIAL. Root cause CONFIRMED (SERVER VERIFIED). No safe fix exists inside the current datapack architecture: BLOCKED pending a design decision.**
Draft PR stacked on PR #19 (SG-03-N4). The N4 step-10 fix is intact. No production datapack or geometry was changed in this PR.
Labels: CODE VERIFIED, SERVER VERIFIED (official 26.3 server, natural generation, never `/place`), VISUAL PENDING, BLOCKED.

## 1. Evidence from PR #19 CI

* Run 39193076516 (`sg03-natural`, seed 173): site (-18,36) 53,113 / 53,252 matched; 131 amethyst-geode-class replacements (smooth basalt,
  calcite, amethyst block, budding amethyst) + 8 cells replaced by air (the geode's hollow core), all in chunk (-17,32). Identical numbers appeared in
  three separate CI executions and in local runs.
* Run 39193076530 (N4 workflow, seed 173, prod-1): site (-19,15) 92 corrupted cells: 60 monster-room-class (deepslate bricks → cobblestone 23,
  deepslate tiles → mossy cobblestone 18, polished deepslate / deepslate bricks → cave air 29 ...) plus 32 others. Prod-2 of the same job passed.
* The same N4 job also passed seed 42 (4,13) **with 2 geode cells replaced**: `inspect()` classifies geode / sculk / monster-room overlays as explained and
  does not fail on them, so those cells were silently accepted. `assert_n4.py` now additionally requires `matched == expected` and no foreign
  block inside template air (see section 6).

## 2. Root cause (vanilla 26.3 behaviour, not a harness artefact)

1. A structure piece is written into a chunk only while *that chunk* is decorated (the piece is clipped to the chunk being decorated).
2. Biome features write across chunk borders into already-decorated neighbours. `amethyst_geode` (feature step 2) is a sphere of up to ~12 blocks,
   `monster_room` (step 3) a 5-9 wide box. Both only test the *current* block states, so a structure that already exists looks like solid rock.
3. Within one chunk the structure (step 10) is placed after all of them, which is why N4 fixed clay. But when a neighbouring chunk is decorated
   **after** the structure's chunk, its geode or dungeon overwrites the structure. The structure step cannot change this: cross-chunk decoration order
   is decided by the chunk scheduler, i.e. by the order in which chunks are requested (player movement) and by thread timing.
4. Geodes only form in solid mass (the placement aborts if more than one sampled point is air or ice/water/lava/bedrock); that is why they land in thick
   floors, walls and tunnel masses of the structure. Dungeons need a solid floor and ceiling and one to five openings.

## 3. Reproduction (SERVER VERIFIED)

`validation/minecraft-visual/sg03-natural/collision_lab.py` loads the 11x11 chunks around one named site chunk-by-chunk in a chosen order (with
`-Dmax.bg.threads=1`), then the structure bounding box, saves, and reports every overwritten block with chunk, room and suspected feature.
32 runs (4 sites x 8 orders) on the PR #19 pack, `evidence/n5-collision-lab.json`:

| Site | corrupted / 8 orders | affected chunks / rooms (examples) |
|---|---|---|
| seed 173 (-19,15) | 5 / 8 (120-212 cells) | (-21,12), (-21,13), (-22,13); main chamber |
| seed 173 (-18,36) | 5 / 8 (139 cells, every time identical) | (-17,32); barracks hall, trial chamber, east tunnel |
| seed 42 (4,13) | 4 / 8 (26-484 cells) | (2,15), (2,16), (3,14), (4,13), (4,14); main, barracks, storage |
| seed 42 (6,-19) | 3 / 8 (81 cells) | one chunk |

17 of 32 runs (53 %) corrupted; clean runs also exist for the same site, so order matters. Spiral-out (the shape of a player's loading ring) corrupted
3 of 4 sites. Single-threaded scheduling is **not** fully deterministic: seed 173 (-18,36) row-major corrupted in the matrix but was clean in three later
runs while other servers were running. So both chunk order and timing matter; neither is a defect of the harness, both are normal for players.

## 4. Which feature caused what (A/B, same site and order; override file = placed feature with `count: 0`, experiment only)

| Arm | (173,-18,36) | (173,-19,15) | (42,4,13) | (42,6,-19) |
|---|---|---|---|---|
| control | ok | 226 (geode 90 + room 73 + air 62) | 678 (geode) | 81 (geode) |
| geodes off | ok | **ok** | **ok** | **ok** |
| monster rooms off | ok | 58 (geode only) | 484 (geode only) | 81 (geode only) |
| both off | ok | ok | ok | ok |

* F-1 **CONFIRMED**: `minecraft:amethyst_geode` explains all geode-class replacements and the hollow-core air cells; with it disabled every
  corrupted site is clean.
* F-2 **CONFIRMED (not only a hypothesis)**: with monster rooms disabled the cobblestone / mossy cobblestone / cave-air overwrites at (-19,15) disappear
  (226 → 58, geode only). In this sample the dungeon only appeared when geodes were active, which suggests it uses the geode-created cavity; that part is
  an observation from one site, not established.
* The A/B arms are experiment fixtures only. Nothing disables a vanilla feature in a shipped pack.

## 5. Candidates

| Candidate | Result | Why |
|---|---|---|
| A. Later or different structure step | rejected | cross-chunk order is independent of the step (N4 data and this lab) |
| B. Append structure-exclusive blocks (deepslate / tuff brick families) to `#minecraft:features_cannot_replace` | **tested, insufficient** | runs of 3 sites: 678→111, 226→5, 212→0 but 111 remain at seed 42 (4,13): planks, stairs, barrels, beds, cobbled deepslate; geode-filled calcite/basalt still intrudes into template air (277-474 blocks); it is also a global tag change |
| C. Protect all 57 template block ids via that tag | rejected | planks, logs, beds, barrels, copper would become unreplaceable for every vanilla structure and feature |
| D. Hidden `geode_invalid_blocks` markers | rejected | the geode checks only a handful of sample points near its centre; no marker lattice can be guaranteed |
| E. Disable / override `amethyst_geode` or `monster_room` | rejected by constraint | global feature suppression |
| F. Post-generation repair, runtime chunk rewrite, mod hook | rejected by constraint | overwrites player changes / not datapack architecture |
| G. Redesign with `features_cannot_replace` material skin (e.g. reinforced deepslate) | not tested | design and material change; geode spheres still fill interior cells |
| H. Accept as vanilla-style overlap and document | available | vanilla Ancient Cities and mineshafts are cut by the same features; but SG-03 rooms/spawners are gameplay content, and monster-room spawners and chests can appear inside rooms |

No candidate preserves vanilla geodes and monster rooms outside the structure, keeps the SG-01/02/03 geometry and satisfies strict integrity.

## 6. Changes in this PR (tooling only; CODE VERIFIED)

* `collision_lab.py`: order-controlled reproduction with per-position output.
* `run_natural.py`: records every mismatching position and reports foreign blocks inside template air (`interior_intrusions`); pass rules unchanged.
* `assert_n4.py`: now fails on any mismatch (`matched != expected`) and on any foreign block inside template air, closing the silent acceptance of
  overlay-classified cells. **The N4 CI job can therefore go red intermittently until a design decision is made; that is the truthful state.**
* `docs/sg-03/evidence/n5-collision-lab.json`: matrix, A/B and tag-candidate data.

## 7. Decision needed

1. **Accept and bound the risk** (H): keep strict reporting, treat geode/dungeon overlap as a known vanilla-like hazard, make CI classify instead of fail (needs approval since it relaxes a gate).
2. **Change the design** so features cannot damage it: for example a reinforced skin and material changes (G), or reducing solid mass; requires art approval.
3. **Leave the datapack architecture**: a small Fabric/NeoForge mod that registers the structure with a custom post-processing guard (best technical fix, outside the approved architecture).
4. **Global narrow tag edits** (B) only if the owner accepts a global worldgen rule change and partial protection.

## 8. Remaining risks / verification debt

* Tool-verified on 4 sites x 8 orders + 16 attribution and 16 tag runs locally; no final-head CI result for a fix exists because none was implemented.
* Dungeon spawners and chests inside rooms were not observed in these runs (no spawner/chest in `interior_intrusions`), but nothing prevents them.
* Vanilla Trial Chambers, Ancient Cities and other structures were not measured under the same orders.
* VISUAL PENDING: how geode-damaged rooms look in game.
