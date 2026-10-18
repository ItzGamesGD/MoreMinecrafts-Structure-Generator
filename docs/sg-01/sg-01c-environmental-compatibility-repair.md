# SG-01-C — Environmental compatibility and accessibility repair (experimental)

**Draft PR:** [#14](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/pull/14), stacked on PR #5. SG-02 / SG-03 PRs were not modified; compatibility with them has **not** been checked.
**Nothing here is owner-approved.** Experimentally confirmed repairs are separated from decisions still awaiting approval.

Verdict words: **PASS**, **FAIL**, **BLOCKED**, **NOT RUN**.

## Repairs

| ID | Change | Status |
|---|---|---|
| F-2 | Structure `step` `strongholds` → `vegetal_decoration`. Biome tag, height range, materials, spacing/salt untouched. | Confirmed to remove ~99.9 % of sculk intrusion and all interior shriekers (16 seeds). Not a complete fix: see below. **Design decision pending.** |
| F-4 | Each stair run gets an eighth step in the ring's inner band (12 blocks `deepslate_tiles` → `stone_brick_stairs`). | Confirmed walk-only in static and runtime probes, all four stairs, all four rotations. **Design decision pending** (small geometry change). |
| F-1, F-3, F-5 | Deferred as instructed. | Unchanged. |

## F-2 investigation

**Ordering (26.3 data).** Biome feature steps (index): 2 local_modifications → `amethyst_geode`; 3 underground_structures → `monster_room`; 6 underground_ores; 7 underground_decoration → `sculk_vein`, `sculk_patch_deep_dark`; 9 vegetal_decoration → `glow_lichen`, `cave_vines`, `spore_blossom`. Within a step the game places structures first, then that step's features. With the old step (5, strongholds) the structure was placed *before* the step-7 sculk features, so sculk (and its sensors / `can_summon=true` shriekers) grew over it. Geodes (2) and monster rooms (3) are *earlier* than the structure within a chunk, so they can only overwrite it through cross-chunk decoration order (a neighbouring chunk decorated later writes into this chunk).

**Experiment.** The CI baseline sweep (16 fixed seeds, 129 sites, 97 generated, `--ticks 2400`, same parameters and pinned site) was repeated with only `step` changed (original geometry). Placement, rotation, bounds and Trial Chambers results were identical at all 97 generated sites in every variant. Tool: `variant_pack.py`, `compare_variants.py`; data: `evidence/sg01-c-f2-step-*`.

| Step | All-8,575-match sites | Sculk blocks replaced (sites) | Interior sculk sensors / shriekers | Geode / monster-room overlays (sites) | Cave-vegetation blocks inside | Interior fluid sites |
|---|---|---|---|---|---|---|
| strongholds (baseline) | 87 / 97 | 4,357 (7) | 112 / 14 | 24 (2) / 7 (1) | 1,313 | 5 |
| underground_decoration | 88 | 4,318 (7) | 105 / 13 | 41 (2) / 7 (1) | 1,296 | 4 |
| **vegetal_decoration** | 91 | **4 (2)** | **0 / 0** | 68 (3) / 7 (1) | 1,316 | 2 |
| top_layer_modification | 93 | 2 (1) | 0 / 0 | 33 (2) / 7 (1) | **0** | 2 |

* **Prevented, not just reduced?** For deep-dark sculk and shriekers the effect is large but not absolute: 4 sculk blocks and a few sculk veins remain at 2 sites (cross-chunk). No interior shrieker appeared in any later-step run. Absence in 16 seeds does not prove impossibility.
* **Geodes and monster rooms are not fixed by any step** (cross-chunk ordering); they remain **FAIL (documented limitation)**. No global feature suppression or chunk rewriting was introduced.
* **Cave vegetation** is a separate aesthetic category. `vegetal_decoration` leaves it as before; `top_layer_modification` removes it entirely, so it was not chosen.
* **Fluid:** fewer sites had fluid entering a tunnel mouth under later steps (2 instead of 5; one pinned lava site stays dry). The cause was not established; F-1 stays accepted/deferred and this is reported as an observation only.
* Placement success, suppression (32 of 129 loaded), Jigsaw assembly and Trial Chambers coexistence (33 pairs, min gap 73) did not change.

## F-4

Stair runs previously ended at back-surface 8.0 under a 9.0 ring surface (static model). The eighth step's back is flush with the ring.

* **Static (collision model, not runtime):** walk-only reachability of all four ring landings from all four mouths, rotations 0–3; per-step rise ≤ 0.5; headroom ≥ 1.8; unchanged architecture (8,575 solid blocks, 9 lanterns, 100 walls, 41×17×41 chamber, pillar footings). `tests/test_sg01_static_accessibility.py`.
* **Runtime probe, jumping disabled (player-width mob, not a live player).** New geometry: 7 pinned natural sites, stair legs 84/84 PASS, ring-lap legs 56/56 PASS (every non-fluid interior leg PASS; the one FAIL ends in a water-filled tunnel mouth). **Control:** the old geometry from PR #5 `1759b13` on seed 173 site -19,15: all 4 stair-up legs FAIL (mob stops one block below the ring), proving the walk-only probe can fail.
* **Correction to SG-01-B:** the claim that the runtime probe showed jumps were needed was wrong, because the probe's mob also hops on valid half-block stairs. The probe now disables jumping by default. The static model and the control run support the original finding.

## Report

| Item | Verdict | Evidence |
|---|---|---|
| Naturally generated structures | **PASS** | 97 generated of 129 loaded, 16 seeds |
| Suppressed candidates | **PASS** (as designed) | 32 loaded suppressed; 1,811 of 2,704 scanned candidates (67 %) predicted suppressed; 0 prediction mismatches |
| Expected-block integrity | **PASS** with overlays | 93 / 97 sites exactly 8,575/8,575 under the new geometry and step; 4 sites carry overlays |
| Sculk / summon-capable shriekers | **PASS** (sample) | 1 site with 2 sculk blocks; 0 shriekers (baseline: 7 sites, 4,357 blocks, 14 shriekers at 5 sites) |
| Other vanilla overlays | **FAIL** (known limitation) | amethyst geodes 2 sites, monster room 1 site; unchanged |
| Cave-vegetation inside | Observed (aesthetic) | 75 sites, unchanged |
| Fluid penetration | Accepted (F-1) | tunnel mouths: 4 flooded of 388 (baseline 7); 2 sites with fluid cells in a tunnel |
| Plaza protection | **PASS** | 0 sites with fluid in the main chamber; synthetic water 33 / lava 21 cells in tunnels only |
| Walk-only staircase and ring access | **PASS** | static all rotations; runtime 84/84 stair, 56/56 ring |
| Trial Chambers exclusion and overlap | **PASS** | 12-chunk exclusion preserved; 33 pairs, no overlap, min gap 73 blocks |
| Generation frequency | Unchanged | identical candidate positions, placement and suppression |
| Ancient City overlap | **NOT RUN** | |
| Performance | **NOT RUN** | |
| Live-player traversal | **NOT RUN** | |
| Surface access (F-5) | **BLOCKED** (deferred) | 94 % of mouths remain sealed; reserved for a future entrance module; district Jigsaw sockets unchanged |
| SG-02 / SG-03 compatibility | **NOT RUN** | |

Final CI numbers for this PR's head are in the PR description.
