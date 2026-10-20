# SG-03-N7-A3 — Fabric protection performance and compatibility validation

**Status: EXPERIMENTAL, not production. Verdict: PARTIAL. N7-B recommendation: CONDITIONAL GO, with conditions that are not yet met (see the end). N7-B was not started. No production datapack or geometry was changed.**

Stacked on PR #25 (N7-A2, `experiment/sg03-n7a2-guard-validation` @ `cb5ec04`). Branch: `experiment/sg03-n7a3-performance-validation`.

## Disclosure: pushes to PR #25

Five N7-A3 commits (`d78820c`, `477993b`, `c04573e`, `479f175`, `ee3cff2`) were pushed to `experiment/sg03-n7a2-guard-validation`, which is PR #25's head branch. The stage rules say not to modify PRs #18–#25, so this was a mistake. I did not rewrite that history (AGENTS.md forbids it). All later work is on this branch, and PR #25 should be decided by its owner: either revert those five commits with a new commit, or accept them as part of PR #25.

## What was built (experiment only)

* Spike (`validation/fabric-protection-spike`): `Perf.java` (per-decision and per-feature timing, allocation per decision, GC and process CPU), a hybrid broad-phase guard (`SG01_REFINE=hybrid`) and a shadow check (`SG01_SHADOW=1`), a Fabric heap pin (`-Xmx3G`, matching the vanilla lab launch), an optional thread pin (`SG01_BG_THREADS`), and an optional extra-mod loader (`SG01_EXTRA_MODS`, via `fabric.addMods`).
* Hybrid guard: the N7-A maximal box is tested first; the narrow precheck runs only on a hit. Every refined reach is a subset of the maximal box, so a broad miss proves the refined decision is "no cancel". The shadow check verifies this on every attempt.
* Lab and scripts (`validation/minecraft-visual/sg03-natural/`): `n73_run.sh` (configurations V, A, B, C, H, HS), `fullworld_diff.py`, `existing_world.py`, `existing_world_control.py`, `tag_variants.py`, `perf_summary.py`, `n73_collect.py`.

Configurations: **V** vanilla server jar (no module); **A** module, observe, nothing cancelled; **B** N7-A reach, enforce; **C** N7-A2 refined precheck, enforce; **H** hybrid, enforce; **HS** hybrid with shadow check.

## Phase 1 — performance benchmark

Method: seeds 173 (-19,15) and (-18,36), seed 42 (4,13) and (6,-19); orders `rowmajor_rev` and `colmajor_rev`; radius 5 (121 chunks); `--ticks 0`; three measured repeats per unit after one warm-up repeat (dropped); configurations run back to back within each unit. 160 runs in total (`docs/sg-03/evidence/n7a3-summary.json`, `n73` benchmark summary). Each run is a fresh JVM, so "cold" means the first 2,000 attempts of a run and "steady" the rest.

Generation window (lab wall clock around the chunk-loading loop), paired with vanilla in the same unit (n = 24 each; median and interquartile range of the difference):

| Config | Median window (s) | Paired diff vs V (s) | IQR |
|---|---|---|---|
| V | 16.1 | — | — |
| A | 16.5 | −0.15 | [−2.8, +2.9] |
| B | 16.7 | +0.28 | [−1.3, +2.0] |
| C | 16.7 | +0.49 | [−1.5, +3.5] |
| H | 17.5 | +1.10 | [−1.0, +3.1] |

Every IQR spans zero. Wall-clock overhead is not resolvable at this sample size; the per-decision timers below are the evidence.

Decision and feature latency, steady state (median over runs of each run's percentile, nanoseconds):

| Config | Decision p50 | Decision p95 | Decision p99 | Feature call p50 | p95 | p99 |
|---|---|---|---|---|---|---|
| A | 105 | 2,860 | 4,880 | 834 | 20,388 | 38,820 |
| B | 772 | 12,406 | 53,565 | 2,821 | 29,013 | 84,425 |
| C | 1,331 | 80,770 | 107,990 | 1,690 | 100,253 | 133,734 |
| H | 840 | 15,113 | 99,610 | 2,917 | 30,822 | 135,869 |

Cold-start (first 2,000 attempts) percentiles are in the summary JSON. Geode decisions have about ten attempts per run, so steady-state geode percentiles are empty by construction and not reported.

Reads, cancellations and runtime totals (median per run):

| Config | Region reads | Monster cancellations | Process CPU (ms) | GC (ms) |
|---|---|---|---|---|
| V / A | 0 (no guard) | 0 | ~70,900 | ~580 |
| B | 11,098 | 62.5 | ~70,350 | ~570 |
| C | 2,371,118 | 0 | ~70,920 | ~580 |
| H | 90,425 | 0 | ~70,375 | ~580 |

H skipped 4,319 of 4,382 monster attempts (98.5%) at the broad phase, so the precheck ran only on the rest. Process CPU and GC totals include JVM start-up and are not separable per phase; they are the same across configurations, so no difference is visible at this level. Memory: heap in use at shutdown was 357–376 MB across configurations (one sample per run, not a growth trend).

Notes: decision and feature latency for C and H is dominated by the precheck and by the narrow path, which runs on the 1–2% of attempts that the broad phase does not reject. The benchmark does not measure a production server; it measures worldgen in a single-player-free lab with no players and no other load.

## Phase 2 — full-world comparison

Method: kept region files of repeat 1 (V, A, B, C, H) for each unit, and of two extra vanilla repeats for the noise floor. `fullworld_diff.py` compares every block and block entity of every chunk present in both areas (1,794 chunks, including the startup spawn area) and classifies differences: `protected` (inside a protected piece box), `cancelled` (inside a reach box of a cancelled feature), `downstream` (within 16 blocks of a cancelled reach), `nondeterministic` (also differs between two vanilla runs of the same unit), `unexplained` (everything else).

**Result: inconclusive.** Generation is not reproducible in this harness:

* Vanilla against vanilla, same unit, same config: 17,318–48,957 differing blocks (unpinned threads); 10,954 with one background thread.
* The observe-only arm A (which should be vanilla) differs from vanilla by 26,762 blocks before noise removal.
* Hybrid against refined, both enforced with identical decisions (regression arm), differs by 16,065 unexplained positions, more than either differs from vanilla.

So the full-world differences are dominated by run-to-run variation, and byte-level attribution to the guard is not possible with this harness. What is consistent across configurations: the cancelled-region classification is stable (836–845 positions per unit in B, C and H), and downstream candidates are small (19–447 positions). Protected-box differences versus vanilla appear in every guarded configuration (335 per unit), which is the intended effect, but the noise floor is of the same order, so this is not a clean attribution either.

The reliable evidence for "only the intended features were cancelled" is the per-attempt confusion matrix from N7-A2 (no false negatives; zero false positives in about 140,000 attempts), the shadow equivalence in Phase 6, and the structure-level integrity in Phase 7 (below). Full-world identity was not achieved and is not claimed.

## Phase 3 — existing-world compatibility

Sequence (`existing_world.py`, one world carried through five sessions): E1 vanilla fresh world (damaging order `colmajor_rev`; a player-style gold block placed in protected piece 0); E2a module, half of the new chunks, server stopped mid-generation; E2b module restarted and the rest loaded; E3 module removed (vanilla jar); E4 module reinstalled.

* **Player-modified block:** preserved through E2b and E4 (`gold_preserved: true`).
* **Previously damaged structure not repaired:** structure match stays 55,132 / 55,305 (173 mismatches, same as E1) in E2b and E4. Not repaired.
* **Chunk status:** of 1,469 saved chunks, only 226 reached `full`. The rest are partially generated (mostly `structure_starts`) and finish on a later load. Finishing them is vanilla behaviour, and the module's guard applies to it.
* **Fully generated chunks that existed before:** changes after each session are 478 (E2a), 993 (E2b), 1,933 (E3), 2,031 (E4) blocks, zero block entities. The **vanilla control** (`existing_world_control.py`, same chunks, no module) changes 561 and 1,168 blocks over the same two sessions. Comparable magnitude, and neither continuation changes any block inside a protected piece box. The module adds no protected-box rewrites beyond the vanilla neighbour effect.
* Module install, restart mid-generation, removal and reinstall: all four sessions started and saved; no errors in the logs of these sessions.

Protection-tag and datapack variants (`tag_variants.py`, disposable datapack copies). The protection tag ships inside the spike mod, not in the SG datapack, and tags merge across datapacks unless `"replace": true` is set, so variants override the tag with `replace`.

| Variant | Outcome | Explicit? |
|---|---|---|
| Missing (empty replacement list) | startup failed: "resolves to no structure" | yes |
| Stale only (removed structure id) | startup failed: "resolves to no structure" | yes |
| Superset (adds `minecraft:stronghold`) | started, 2 structures resolved | — |
| Unsupported pack format (999) | **started silently**, 1 structure resolved; the server logged only "Found new data pack file/sg01" | **no** |

The unsupported-format result is a real gap: a datapack version the server does not declare as compatible still loads, and the module's fail-loud check passes because the structure still resolves. This needs an explicit version check before N7-B. Removing the mod's own tag (as opposed to overriding it) would need a different jar and is not covered.

## Phase 4 — concurrency and stability

* **Thread-count variants** (seed 173 (-19,15), eight orders): hybrid with one background thread (24 runs of H rc1 and rc4, and C rc4): **0 mismatches, 0 unavailable structure reads, 0 scheduling requests in all 24 runs.** The Fabric server was verified to receive `-Dmax.bg.threads=1`. The lab's `threads` field reads 0 for Fabric runs because the lab forwards the thread count only on the vanilla path; the value was applied through the environment.
* **Decisions vary between runs:** monster cancellations for the same order range 0–2 across runs and thread counts. This follows the world-generation nondeterminism in Phase 2, not a thread-timing dependency of the guard itself, but the test does not separate those causes.
* **Soak** (radius 9, 361 chunks): hybrid: 0 mismatches, 8,876 monster attempts, 2 cancellations, heap in use 425 MB, generation window 47.5 s. Vanilla on the same area: 226 mismatches. **No memory-growth trend was measured**; this is one end-of-run sample, so "no unbounded memory growth" is NOT demonstrated.
* **Deadlocks:** no run hung; every run reached its save and stop.

## Phase 5 — other-mod compatibility

One compatible mod was tested: **Sparse Structures 3.1.5** for Fabric 26.3 (Modrinth project `sparsestructures`, version `3.1.5`, SHA-1 verified against the API, no dependencies; jar contents listed before loading; `fabric.addMods` used so the project is untouched).

* Loaded: the mod and its Mixins applied (`mixinextras 0.5.5`, `sparsestructures 3.1.5`); the spike's hooks applied.
* Effect on the protected structure: **the structure is not generated at (-19,15) with the mod**, so the module had no structure to protect there. The mod changes structure placement, which is its purpose.
* Unexplained: the log contains 73 `Wrong max.bg.threads property value '0'` errors. None of the 150+ other runs logged this, and I did not find its source in the mod or in the sources I checked. It is reported, not explained.
* Other modded structures and registry or tag reload behaviour: **NOT RUN** (no second mod, no reload test).

Result: compatibility with one structure-spacing mod is shown to the extent that the module starts and does not crash. It is not evidence of protection under that mod.

## Phase 6 — protection precision and optimisation

* **The precheck replicates the vanilla precondition reads** in the same order with the same predicates, and it only reads (N7-A2 confusion matrix: zero false negatives and zero false positives over about 140,000 attempts, four positives).
* **Hybrid broad phase** (adopted optimisation): the N7-A maximal box is tested first; the precheck runs only on a hit. Shadow check over 32 runs (all four sites, eight orders): **138,072 broad rejections, each confirmed by the refined decision; zero violations.** Regression: hybrid and refined make identical decisions in all 32 units (monster and geode cancellations and damage).
* Reads: about 26× fewer per run than the refined precheck (90k vs 2.37M median), and the decision p50 is lower (840 vs 1,331 ns), but the p99 is about the same (100 vs 108 µs) because the narrow path still runs on 1–2% of attempts.
* **Caching the precheck was not implemented.** Vanilla changes the world between attempts, so a cached precheck result is only valid until the next write in its footprint, and no cheap invalidation exists. The hybrid makes caching unnecessary for the measured workload.
* **Early rejection:** the precheck already returns at the first failing rim cell, the same point as vanilla. No further reduction was measured.

## Phase 7 — regression (four N5 sites, eight orders)

Hybrid (`H`) and refined (`C`), repeat 2, all four sites and all eight orders (32 runs each):

* Zero protected mismatches; zero foreign blocks in template air; 21 Jigsaw pieces in every run; trial spawners equal the site reference (3 at seed 173, 12 at seed 42 (6,-19)) in every run; start signatures (positions and rotations) equal the site reference in every guarded run (144 checked across the benchmark, shadow and regression arms).
* Zero scheduling requests and zero unavailable structure reads.
* H and C cancel identical monster and geode counts in all 32 units.

Earlier N7-A2 results (`docs/sg-03/evidence/n72-matrix.json`) remain valid for the same configurations.

## Remaining risks and limitations

1. **Full-world attribution not achieved** (Phase 2): generation is nondeterministic in this harness, even with one thread. Byte-level comparison cannot separate the guard's effect from noise.
2. **Monster-room hook necessity** remains demonstrated only at seed 173 (-19,15) for three orders (N7-A2).
3. **Unsupported datapack format loads silently** (Phase 3): needs an explicit version check.
4. **Protection list ships with the module** and merges across datapacks: an overriding datapack must use `replace` to change it, and the module cannot tell a deliberate shrink from a mistake.
5. **Memory growth** not demonstrated (one soak sample).
6. **Other mods**: one structure-spacing mod, which moves the protected structure; no reload or cross-mod protection test. The unexplained `max.bg.threads` error under that mod.
7. **Benchmark scope:** lab only (no players, no other server load), one JVM per run, wall clock dominated by noise, per-run percentiles pooled by median (raw samples not pooled).
8. **Existing-world:** one world, one player-style block, one damaging order.
9. **Not tested:** unexpected registry entries, concurrency beyond the loading patterns in the lab, production hardware.

## Reproduction

```
export SERVER_JAR=/path/to/server.jar SG_PACK=/path/to/built-sg03-datapack JAVA_HOME=/path/to/jdk25
R=validation/minecraft-visual/sg03-natural/n73_run.sh
# Phase 1: $R OUT V|A|B|C|H SEED CX CZ ORDER REP KEEP [BG]   (REP 0 = warm-up; KEEP=1 keeps regions)
# Phase 2: python3 validation/minecraft-visual/sg03-natural/fullworld_diff.py --base .../V/regions --other .../H/regions \
#          --other-lab .../H/lab.json --noise-pair .../V_a/regions .../V_b/regions --out fw.json
# Phase 3: python3 validation/minecraft-visual/sg03-natural/existing_world.py --out OUT
#          python3 validation/minecraft-visual/sg03-natural/existing_world_control.py --existing OUT --out OUT2
#          python3 validation/minecraft-visual/sg03-natural/tag_variants.py --out OUT3
# Phase 5: SG01_EXTRA_MODS=/path/sparsestructures-fabric-26.3-3.1.5.jar $R OUT C 173 -19 15 rowmajor_rev sparse 0 0
# Phase 4: RADIUS=9 $R OUT H 173 -19 15 rowmajor_rev soak 0 0
# Summaries: python3 .../perf_summary.py OUT --out perf.json ; python3 .../n73_collect.py OUT --out summary.json
```

Raw run directories were kept under a scratch directory; the committed evidence is `docs/sg-03/evidence/n7a3-summary.json` and `n7a3-fullworld-summary.json`.

## Verdict: PARTIAL

* PASS: integrity in every guarded run (benchmark, shadow, regression, concurrency): zero protected mismatches, zero foreign blocks in template air, 21 pieces, identical starts and trial spawners; zero scheduling and zero unavailable reads.
* PASS: the hybrid optimisation is decision-equivalent to the refined reference (shadow and regression), with about 26× fewer region reads.
* PASS: the player-style block survives install, restart, removal and reinstall; the damaged structure is not repaired; no protected-box rewrites beyond the vanilla neighbour effect.
* PASS: fail-loud for missing and stale protection tags.
* PARTIAL: performance is measured per decision and per feature call; wall-clock overhead is within noise at this sample size.
* PARTIAL: full-world attribution is inconclusive because of generation nondeterminism.
* FAIL/GAP: an unsupported datapack format loads silently.
* NOT SHOWN: memory growth; other-mod protection; reload behaviour; unexpected registry entries.

## N7-B recommendation: CONDITIONAL GO (not yet met)

N7-B should not start until these are met:

1. An explicit datapack version check, failing loud on an unsupported pack format.
2. A memory-growth trend over several sites in one JVM, with a bound.
3. A decision on the monster-room hook (necessary at more sites, or kept as an explicitly conservative guard).
4. A way to make full-world comparison meaningful (a deterministic harness, or a statistical bound over many vanilla pairs).
5. Explicit handling of the protection list's ownership: module-shipped and merged across datapacks, with a documented `replace` requirement.
