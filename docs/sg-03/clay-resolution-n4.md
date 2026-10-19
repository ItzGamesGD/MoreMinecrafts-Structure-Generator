# SG-03-N4 — Natural worldgen clay overwrite resolution

**Draft PR** based on the verified integration baseline (PR #18, `282b74d`). PRs #12, #13, #15 and #18 are not modified.
Verdict labels: **CODE VERIFIED** (unit/pytest), **SERVER VERIFIED** (official Minecraft 26.3 server, natural generation, no `/place`),
**VISUAL PENDING**, **BLOCKED**. Nothing here is owner-approved.

## 1. What the A/B artifacts show (PR #15, run 39124119497)

* Control (production datapack) at seed 42, chunk (4,13): 52,397 / 52,443 expected blocks matched, **46** mismatches, all `moss_block` →
  35 `clay`, 10 `water`, 1 `big_dripleaf` (`state_transitions`). Treatment (`lush_caves_clay` placement `count: 0`): 52,443 / 52,443,
  0 transitions.
* Same Jigsaw start signatures, same chunk load order, same expected-solid and piece counts; the 35 enumerated clay coordinates were all
  restored (`removed` 35, `introduced` 0, `remaining` 0), tick-stable before and after 200 ticks; the other site (6,-19) passed in both arms.
* All 46 positions were therefore restored (matched == expected). The artifact enumerates coordinates only for the clay cells; the 11
  water/dripleaf cells are known by count. `treatment_other_unexplained` = 0. Terrain outside the expected blocks was not diffed, so
  "no unrelated change" is established for the structure's expected volume only.
* **46, not 47.** The N2 reproduction artifact (run 39117590198) has the same 35/10/1 = 46. My local repetitions on the integration pack
  gave 33, 46 and 45 clay-family cells (plus 38 and 46 in other runs): the count varies with chunk decoration order. "47" is the same
  phenomenon; no hard-coded count is used anywhere.

## 2. Root cause (26.3 data)

`minecraft:lush_caves_clay` is a `random_boolean_selector` of `clay_with_dripleaves` and `clay_pool_with_dripleaves`: patches of clay, optional
water pools and big dripleaf over lush ground (moss blocks are replaceable ground). It is placed 62 times per chunk in the lush-caves biome,
in **feature step 9 (`vegetal_decoration`)**. Minecraft places a step's structures *before* that step's features and later steps afterwards.
SG-02/SG-03 production packs declared the structure in step 5 (`strongholds`), so clay always ran after the structure and overwrote its moss
(the SG-03 rooms use moss blocks). Related vanilla steps: `amethyst_geode` 2, `monster_room` 3, `sculk_patch_deep_dark` 7.

**Also found:** `build_sg02.py` hard-coded `strongholds`, so integration #18 silently reverted SG-01-C's F-2 step change (`vegetal_decoration`) in the
SG-02/03 packs; SG-01-C's sculk protection was not active in the integrated production pack.

## 3. Candidates

| Candidate | Complexity | Compatibility | Worldgen cost | Regression risk | Result |
|---|---|---|---|---|---|
| **A. Structure step `top_layer_modification` (10)** | one constant in three builders | no vanilla/other-pack file touched | none | removes cave vegetation growing into template air (aesthetic); cross-chunk ordering can still let a *neighbouring* chunk's feature write later | **chosen, SERVER VERIFIED** |
| B. Step `vegetal_decoration` (9, SG-01-C value) | trivial | same | none | structure still precedes step-9 features | **does not fix clay** (seed 42 FAIL, 34–45 cells) |
| C. Override `placed_feature/lush_caves_clay` with a structure-aware filter | high | global vanilla override, conflicts with any pack touching it | per-attempt volume scans (62 attempts/chunk) | there is no structure predicate in 26.3; a block-marker heuristic (e.g. deepslate tiles) also hits Ancient Cities | rejected |
| D. Remove `moss_block` from `lush_ground_replaceable` | low | global tag change, alters all vanilla lush caves | none | changes vanilla clay/moss behaviour | rejected |
| E. Replace moss with non-replaceable blocks | medium | design change to SG-03 rooms | none | not an approved art change | **design decision if A is rejected** |
| F. Disable `lush_caves_clay` (the A/B treatment) | trivial | global | none | forbidden by this stage | experiment only |

## 4. Server verification (local, official 26.3 jar, seeds 173 and 42, 2 sites each, 200 ticks)

Three independent repetitions per arm (`evidence/n4-step-repetitions.json`):

| Arm | Seed 173 (-19,15) | Seed 173 (-18,36) | Seed 42 (4,13) | Seed 42 (6,-19) |
|---|---|---|---|---|
| integration step 5 (`strongholds`) | PASS 3/3 | PASS 3/3 | **FAIL 3/3** (clay family 33, 46, 45) | PASS 3/3 |
| **step 10 (fix)** | PASS 3/3 | PASS 3/3 | **PASS 3/3** | PASS 3/3 |
| step 9 (single run) | PASS | PASS | FAIL (45 clay family) | PASS |

Every passing site had 21 recorded Jigsaw pieces with identical start signatures to the control, expected blocks fully matched before and
after 200 ticks, trial spawner blocks == spawner block entities (3 / 3 and 12 / 12), and rotations unchanged (placement does not depend on the
step). Natural lush-cave clay remains: 156,967 clay blocks in the lush-caves biome within 64 blocks of seed 42 site (4,13) (`vanilla_clay_outside_structure`).
Control arm (pre-fix ordering `vegetal_decoration` on the final pack) at seed 42: 40 clay-family overwrites, 0 others.

Observation, not part of N4: in one run with three servers generating concurrently, seed 173 (-18,36) showed 139 geode overlays
(amethyst, calcite, smooth basalt, air) under steps 5 and 10 but not under step 9; 12 later runs at normal load passed. Geodes (step 2) can only overwrite
through cross-chunk ordering, which is timing dependent. The integrity assertion was **not** relaxed for it (geode air is classed "unexplained").

## 5. Regression tests

* `tests/test_sg03_clay_resolution.py` (CODE VERIFIED): all three shipped packs use the shared `STRUCTURE_STEP`, and it follows the vanilla step of
  `amethyst_geode`, `monster_room`, sculk and `lush_caves_clay`; no pack contains `data/minecraft` overrides or mentions the clay feature; biome tag,
  height range, encapsulate, spacing, separation and the 12-chunk Trial Chambers exclusion are unchanged.
* `validation/minecraft-visual/sg03-natural/test_clay_regression.py` (CODE VERIFIED): the new `count_clay_outside` diagnostic counts natural clay
  and ignores clay inside template cells.
* `sg03-n4-clay.yml` (SERVER VERIFIED when CI is green): production arm twice plus a pre-fix control arm per seed; `assert_n4.py` requires full integrity, no
  clay-family transition, 21 pieces, spawners, natural lush-cave clay beside the structure (seed 42), and identical start signatures in control and
  production, so the fix cannot be a changed placement or a suppressed feature. If the control fails to overwrite it is flagged INCONCLUSIVE rather than silently accepted.
* Existing assertions (`inspect()` pass rules, overlay classes) are unchanged.

## 6. Compatibility with integration PR #18

The branch is stacked on `282b74d`; the only exported-file changes are the `step` field and checksums of three structure JSONs and manifests (no NBT,
pools, sets, previews). `pytest tests` (139) pass. SG-01-C's F-2 intent is restored by the same change (step 10 follows step 7 sculk).

## 7. Remaining risks and recommendation

* Step 10 also removes lush vegetation (glow lichen, vines, spore blossom) that would otherwise grow into template air: **VISUAL PENDING**, owner decision.
* Cross-chunk ordering can still let a neighbouring chunk's feature overwrite blocks (geodes, monster rooms observed earlier); not solved, no global suppression added.
* The fix is empirical on 2 seeds / 4 sites x 3 repetitions locally; CI repeats it. Ancient City overlap, performance and live-player traversal are **NOT RUN**.
* Merge recommendation: **do not merge automatically**. Recommend approving candidate A after owner confirms the vegetation trade-off; if rejected, choose
  E (material change) rather than any global feature override.
