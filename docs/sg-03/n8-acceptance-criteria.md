# SG-03 N8 — acceptance criteria (fixed before any N8 measurement)

These thresholds were written, committed and pushed before the first N8 soak, world or performance run. They are not adjusted after the results are seen; if a result is borderline it is reported as borderline.

## N8-A — long-duration soak (guarded vs control)
Workload: the lab soak (`soak.py`): one JVM per arm, `pause-when-empty-seconds=-1`, 5 s sampler, structure sites visited one after another with force-loaded areas, identical seed and site list for both arms. Guarded = production configuration; control = both hooks disabled (lab `SG01_FEATURES=none`). Each arm runs at least 45 minutes; the first 10 minutes are warm-up and excluded from slopes.
- A1 (activity): chunks keep being generated: the cumulative count of decorated chunks increases in at least 95% of 5-minute windows of the run, in both arms, and the server never pauses.
- A2 (heap): steady-state heap-after-GC OLS slope of the guarded arm is at most +2 MB/min, or its 95% interval includes zero, AND guarded minus control slope is below +3 MB/min; heap-after-GC never exceeds 80% of the heap maximum.
- A3 (retained guard state): `guard_events_retained` stays at or below its cap (800) and does not grow in steady state.
- A4 (GC): guarded GC time fraction at most control + 0.5 percentage points; longest recorded pause at most 200 ms.
- A5 (RSS/CPU): guarded minus control RSS slope below +5 MB/min; process CPU per decorated chunk of the guarded arm at most 1.25 times the control's.
- A6 (stability): no crash, no `OutOfMemoryError`, no `Can't keep up` message beyond the control's count + 10%.
- Non-heap growth is reported; it is not evidence of a leak without a heap trend, and not a pass criterion on its own.
- Repeat rule: if the guarded heap slope's 95% interval excludes zero on the positive side, both arms are repeated once; the verdict uses both runs.

## N8-B — world preservation
- B1 (protected regions): zero protected-block mismatches, zero foreign blocks in template air, 21 pieces, trial-spawner blocks equal to entities, across every site of every guarded run (zero tolerance).
- B2 (neighbourhood, statistical): for a ring of 2 chunks around each structure's pieces, per-world counts of geode blocks (smooth_basalt, calcite, amethyst_block, budding_amethyst), spawner blocks and mossy cobblestone are compared between the guarded world, the control world and at least 3 vanilla replicate worlds (same seed and area). Pass: the guarded totals lie within the vanilla replicates' min–max range widened by 10% (vanilla itself is not reproducible in this harness, so equality is not the criterion and is not claimed).
- B3 (intended differences): every difference attributable to a cancelled feature is listed; cancelled features are those recorded by the guard; no claim about cells outside rings.
- Deterministic comparison is used where feasible (protected regions against the exported templates); matching seeds alone are not treated as equivalence.

## N8-C — performance and generation impact (measured in the lab build, VERIFIED level)
- C1: guard decision time p99 at most 1 ms (VERIFIED/box), at most 2 ms (ZONE).
- C2: total generation time of a fixed site area, guarded vs control, at least 8 paired runs: median overhead at most +10%.
- C3 (suppression): 100% of cancellations have a reach box that intersects a protected piece (verifier assertion); monster-room cancellations at most 2% of all monster-room attempts over the 64-run matrix; geode cancellations at most 25% of geode attempts.
- C4: no protected-region damage (B1) caused by the conservative policy; cancellation-rate change reported against N7-B and N7-D.

## N8-D — repository integration
- D1: linear stacked ancestry #25 → #27 → #29 → #30 → #32 → #34 → N7-E; no merge or ready PR.
- D2: the production jar builds twice to byte-identical files.
- D3: every runtime dependency the production classes need (Fabric Loader, Fabric API lifecycle events, Minecraft 26.3, Java 25) is declared in `fabric.mod.json`.
- D4: production jar content checks (`verify_artifacts.py`) 100% pass; the manifest in the committed SG-03 pack is accepted; SG-02 tests and pack unchanged.
- D5: actual GitHub Actions results are listed per check; each failure is classified (regression, pre-existing/vanilla, or infrastructure) with evidence.

## N9 — live acceptance
Criteria are written separately once the available client tooling has been inspected, and also before any live run.
