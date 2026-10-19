# SG-03-N7-A2 — Fabric protection guard validation and refinement

**Status: EXPERIMENTAL, not production. Verdict: PARTIAL. N7-B recommendation: CONDITIONAL GO (see the end). N7-B was not started.**

Stacked on PR #23 (N7-A spike, `experiment/sg03-n7a-fabric-spike` @ `2813d76`). Branch: `experiment/sg03-n7a2-guard-validation`.
Nothing in production datapacks, exports, geometry, the N4 step-10 fix, or the N4/N5 integrity checks was changed.
PRs #18–#23 were not modified and nothing was merged.

## Correction to the N7-A report (PR #23)

The N7-A report stated that the monster-room hook had been independently verified. That was not supported. In the N7-A runs the
geode guard alone already gave zero damage at seed 173 (-19,15), so the monster-room hook had not been shown to matter. This
report replaces that claim with the evidence below. The N7-A branch was not edited.

## What was tested (all newly run in this session, local official 26.3 server, N5 lab)

Sites: seed 173 (-19,15), seed 173 (-18,36), seed 42 (4,13), seed 42 (6,-19). Orders: the eight N5 orders. Repeats where noted.
Run count: 287 `lab.json` runs (see `docs/sg-03/evidence/n72-matrix.json`).

| Arm | Configuration | Runs | Corrupted | Notes |
|---|---|---|---|---|
| A | observe, nothing cancelled (vanilla baseline) | 32 | 16 | 1,858 geode-class cells in total across the 16 corrupted runs, plus monster-room damage |
| B | geode guard enforced only | 32 (+8 repeats) | 2 (+3 repeats) | **zero geode damage in any run**; residual damage is monster-room only |
| C | N7-A reach, both hooks enforced | 32 | 0 | 56–70 monster-room cancellations per run |
| D | refined monster guard, both enforced | 32 (+2 repeats) | 0 | 0–1 monster-room cancellations per run |
| M0 | geodes disabled by fixture, monster room unguarded | 32 (+8 repeats) | 3 of 8 at seed 173 (-19,15); repeats 3 of 4 and 3 of 4 | the monster-only baseline reproduces only at that site |
| M1 | geodes disabled by fixture, monster guard enforced | 32 | 0 | 452–560 monster cancellations per site (sum over 8 orders, 56–70 per run) |
| M2 | as M1 with the refined guard (seed 173 (-19,15)) | 8 | 0 | 4 cancellations in total |
| O / K | monster room unguarded, oracle classifies every attempt | 32 + 32 | 4 / 4 | confusion matrix below |
| F | fault injection (out_of_range, status_too_high, missing_start) | 3 | 0 | see below |

### Phase 2 — per-hook causal evidence

* **Geode hook: verified.** Vanilla (A) destroys amethyst-geode cells in 16 of 32 runs. With only the geode guard (B) there is no
  geode damage in any run across all four sites, eight orders and repeats. The geode guard alone prevents the geode overwrite.
* **Monster-room hook: verified only at seed 173 (-19,15), for three orders.** The baseline (M0, geodes disabled) reproduces
  monster-room damage at `colmajor_rev`, `random:1` and `random:2`, in 3 of 3 runs each. Monster guard enforced (M1, M2) removes
  it. Seed 173 (-18,36) and both seed-42 sites show no monster-only damage in any order, so the monster hook's necessity there is
  **not demonstrated**. Under the spec, this is PARTIAL for the monster hook.
* Per-hook combination (B vs C): the monster guard removes the residual monster damage that remains with only the geode guard
  active (5 runs in B and repeats, 0 in C).

### Phase 3 — over-cancellation and refinement

The N7-A reach is the union of every variant's footprint. Vanilla `MonsterRoomFeature.place` reads its footprint with a precheck
(rim solid, 1–5 holes) before it writes, and only writes if the precheck passes. `MonsterRoomGeometry.passingBoxes` replicates
that read-only precheck for each variant (`xr, zr` in {2,3}) and cancels only if a passing variant's box intersects a protected
piece box. The cancellation is therefore a subset of N7-A's, and it is never looser than vanilla's actual write footprint.

Per-attempt confusion matrix (oracle arm K, 32 runs, 140,000+ attempts, decisions taken before vanilla runs, truth = vanilla changed a
block inside a protected piece box):

| Decision | TP | FP (conservative) | FN | TN |
|---|---|---|---|---|
| N7-A reach | 4 | **2,040** | 0 | 138,068 |
| Refined precheck | 4 | **0** | 0 | 140,108 |

* N7-A's over-cancellation is measured here: 2,040 of its 2,044 monster-room cancellations (99.8%) were conservative (no protected write).
* The refined guard cancelled exactly the attempts where vanilla writes into protected cells, and nothing else, with zero false negatives.
* **Caveat:** only 4 positive attempts occurred in the sample, so zero false negatives is weak statistical evidence on its own. The
  soundness argument is the replicated precheck; the confusion data show no false alarms and no misses in this sample.
* Repeats of identical configurations do not always agree (see Determinism below). A discrepancy at `rowmajor_rev` (oracle
  14 vs 92 cells, refined 0 vs 1 cancellation across runs) is explained by the world diverging between runs. In the confusion arm
  the refined guard evaluated the same world at every attempt and had zero misses, including in the run with 92 damaged cells.

### Phase 4 — chunk-generation instrumentation (`Probe`, observe-only mixins)

Mechanism: `WorldGenRegion.hasChunk` and `getChunk(…STATUS…)` (region reads), `ServerChunkCache.getChunk` / `getChunkFuture` (blocking
and future requests), `ChunkMap.scheduleGenerationTask` and `GenerationChunkHolder.scheduleChunkGenerationTask` (generation
scheduling). Counters increment only while the guard runs on the worldgen thread (thread-local depth). No injector changes a result.

Results over all 284 non-fault runs (fault runs are reported separately):

* region reads: 190,920,036, **all served from data already available**; 0 returned below the requested status; 0 null.
* blocking `getChunk`: **0**; `getChunkFuture`: **0**; `ChunkMap` generation scheduling: **0**; holder generation scheduling: **0**.
* `hasChunk` false: 0 in normal runs (fault runs below).

Limitations: this instruments the entry points the guard uses. It does not prove the absence of waits inside vanilla code outside
the guard, and it counts scheduling calls rather than tracking every future. The `WorldGenRegion` snapshot design (no generation
path) is taken from the 26.3 source and is consistent with these counters.

### Phase 5 — extended regression matrix (4 sites × 8 orders, observe vs enforce)

* Integrity in enforced runs: arms C and D are 0/32 corrupted, with zero foreign blocks in template air, 21 pieces, and trial
  spawners matching the reference arm (block and entity counts equal, 3 at seed 173 and 12 at seed 42 (6,-19)). The start
  signatures (positions, rotations, bounding boxes) match the reference arm in every run.
* Observe vs enforce: vanilla (A) is corrupted in 16 of 32 runs; both enforced arms (C, D) in 0 of 32.
* Vanilla generation outside the protected region (proxy): far-from-structure amethyst blocks are identical between A and C at all
  four sites, and differ by one block in one run of D. This is one block type, not a full-world diff; it is a proxy, not proof.
* `docs/sg-03/evidence/n72-matrix.json` / `.md`: every run, with the start signature, pieces, spawners, geode and monster counters,
  confusion matrix and probe counts.

### Phase 6 — compatibility and failure review

* Fail-loud startup without the SG datapack: **PASS** (`n72-failure-review.json`): startup fails with "structure tag
  `#moreminecrafts:protected_from_overlays` resolves to no structure".
* A Mixin that cannot apply: observed in an earlier probe revision (a non-void method given the wrong callback type). The server
  refused to start with `InvalidInjectionException`, so the failure was loud, not silent. This is an observation from a smoke run,
  not a committed test.
* Missing or invalid start, out-of-range chunk, and status-too-high: fault injection (3 runs, `n72-failure-review.json`).
  Mismatch 0 in each. Each fault makes the affected features cancel, with explicit `unavailable` diagnostics. Probes: out_of_range
  returned `hasChunk` false 1,257 times and requested no chunk; status_too_high threw 1,257 times and generated nothing (blocking
  and scheduling counters stayed 0).
* Unsupported Minecraft version: `fabric.mod.json` pins `minecraft` to exactly `26.3` (static; not run).
* Unexpected registry entries: **not tested**.

## Determinism

Identical configurations do not always produce identical damage. Examples: `O s173a rowmajor_rev` gave 14 cells, then 92 cells in
a repeat; `B s173a random:1` was clean once and damaged once. Damage presence and size vary at the granularity of single attempts.
All numbers here are per-run observations; ranges are given where runs disagree. A stricter determinism test (more repeats, pinned
timing) is needed before any frequency claim.

## Verdict: PARTIAL

* PASS: Geode hook independently verified (4 sites, 8 orders, zero geode damage with the guard).
* PASS: Refined monster guard has zero false negatives and zero false positives in the 140k-attempt sample; N7-A's over-cancellation is
  quantified (99.8% conservative) and removed by the refinement.
* PASS: Lookups perform no chunk generation (instrumented, 191M reads, all served, 0 scheduling).
* PASS: Strict integrity in every enforced run; fail-loud startup; fault injection fail-closed.
* PARTIAL: Monster-room hook independently verified only at seed 173 (-19,15), three orders. Not demonstrated at the other sites.
* NOT RUN / NOT SHOWN: existing worlds, concurrent worldgen and other mods, other structures, performance and timing, full-world diff
  outside the protected region, unexpected registry entries, seed-level frequency, and reliability across more seeds.

## Performance observation (not timed)

The refined guard adds a read-only precheck: about 2.5 million extra region reads per run in arm D, versus about 11,000 per run in
arm C. Wall-clock overhead was not measured under controlled conditions. The read volume is a concern for N7-B.

## N7-B recommendation: CONDITIONAL GO

N7-B was not started. Conditions before any production implementation:

1. Demonstrate the monster-room hook's necessity at more sites and orders, or keep it as a conservative guard and say so explicitly.
2. Measure the precheck's cost under controlled timing and reduce it if needed (e.g. cache the per-variant result per chunk).
3. Test existing worlds, player modifications, concurrent worldgen and other mods.
4. Verify against a full-world diff, not only the amethyst proxy.
5. Keep fail-loud startup and fail-closed unknown worldgen state; no automatic repair.

## Files (this stage)

* `validation/fabric-protection-spike/src/main/java/dev/itzgamesgd/sg01spike/` — `Guard.java`, `GuardStats.java`, `Probe.java`,
  `MonsterRoomGeometry.java`, `MonsterRoomOracle.java`, `SpikeMod.java`, `mixin/MonsterRoomFeatureMixin.java`,
  `mixin/GeodeFeatureMixin.java`, `mixin/*ProbeMixin.java` (4 observe-only probe mixins).
* `validation/fabric-protection-spike/src/main/resources/sg01spike.mixins.json` (probe mixins listed).
* `validation/minecraft-visual/sg03-natural/collision_lab.py` (`--refine`, `--fixture`, `--oracle`), `n72_summary.py`, `n72_matrix.sh`.
* `tests/test_n72_spike_guard.py`, `tests/test_n7a_spike_config.py` (updated for the new mixins).
* `docs/sg-03/evidence/n72-matrix.json` / `.md`, `n72-failure-review.json`.
