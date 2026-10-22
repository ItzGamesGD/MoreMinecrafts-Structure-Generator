# SG-03 N10-R — production safety repairs: verification report

**Status: repairs implemented and verified; verdict CONDITIONAL (section 7).** Nothing merged, deployed or marked Ready. Stacked on PR #43. Evidence: `docs/sg-03/evidence/n10r/` (final jar results in `final/`).

**Release candidate artifact:** `sg-worldgen-protection-0.3.1-n10r.jar`, SHA-256 `5bd47417809b88c5ea4391426163215c444685f975651fb3d6ec4150d154dbaf` (built from commit `888e6f0`; the same hash was produced on the CI runner for the earlier commit `c7f2e59` as `907e4910…`, see section 5). Lab jar is separate and never shipped.

## 1. Defects fixed

| Id | Defect | Fix (commit) | Evidence |
|---|---|---|---|
| P1-A | Unavailable structure data silently disabled protection for the whole region and discarded boxes already found | `Guard.scanZone` keeps every box found and records a bounded footprint; `WriteGuard` refuses non-exempt writes only inside it. Footprint = the unreadable chunk column, or the part of the 3x3 write zone within 8 chunks of an unreadable start; never more than 9 columns. Counted by cause in the report (`unavailable_causes`, `uncertain_refused_writes`); logging bounded (first 10 incidents, then every 100th). Only cached chunks are read; no new lookups, no loading, nothing cached beyond the per-region zone (`d95a324`) | unit tests of the footprint maths (negative coordinates, bounds, 20,000 random cases); fault runs below |
| P1-B | `environment: "server"`: not loaded on integrated (single-player/LAN) servers | `fabric.mod.json` and mixin config `"*"`; no client class referenced (jar check) (`d95a324`) | integrated-server run below |
| P2-A | Exemption counter could leak across reload/exception | `ExemptionScope.enter` returns a token carried to `exit` in `finally`; the decision is taken once at entry (`d95a324`) | unit tests: nesting, exception, Error, simulated reload, thread isolation |
| P2-B | Any mod could switch the write guard off through the lab entrypoint | Honoured only with `-Dsg_worldgen_protection.lab=true` and the lab mod's own id; `LabHooks` installation made package-private after the follow-up review found a public `install` bypass (`d95a324`, `c7f2e59`) | packaged-jar test, 3 cases |
| Steps | PR #19 moved SG-01 and SG-02 without demonstrated necessity | `SG01_STEP = vegetal_decoration`, `SG02_STEP = strongholds`, per-pack `structure_step`; SG-03 keeps the function default `top_layer_modification` (`d95a324`) | regenerated packs byte-identical to the pre-#19 baseline `282b74d`; SG-03 pack rebuilt byte-identical; tests pin all three |
| Test hook | The lab fault `STATUS_TOO_HIGH` called the engine's `getChunk`; on the one-worker CI runner it stalled generation | now a simulated failed read, no engine call (`888e6f0`); lab-only branch | CI failure reproduced twice, then green |

Also: additive `.gitignore` (adds `tools/stage24d/node_modules/`, keeps every rule of both stacks); version `0.3.1-n10r`; artifact verifier now 14 checks (new classes, lab opt-in and id, no client class); `n73_run.sh` fault configs `WM`, `WO`, `WS`.

## 2. Dedicated, integrated and LAN servers (new, final jar)

- **Dedicated** (built jar via `runJarServer`): production-module check PASS at seed 173 chunk (-19,15) and seed 42 chunk (4,13): 21 pieces, every template cell, write guard enabled, exercised, 0 unavailable, no lab mod. Also green in GitHub's `production-module` job.
- **Single-player integrated**: the jar loaded inside a real Minecraft 26.3 client (Xvfb + lavapipe), world opened by quick-play, commands issued through the client's own chat. The module reported ENFORCE with hooks applied on the integrated server thread; structure A (-19,15): 55,305 of 55,305 cells, 21 pieces.
- **LAN**: `/publish true 25585` from the same session, then structure B (-18,36) generated after publishing: 53,252 of 53,252 cells, 21 pieces. A server-list ping to the LAN port answered (version 26.3, one player). Write guard (aggregate over both phases): enabled, 141 regions with pieces, 23 blocked writes, 0 unavailable, lab false. The blocked-write coordinates include the B area, generated after publishing.
- Limits: no second client joined the LAN server; the answer to the world's "experimental settings" confirmation was a real mouse click, and gameplay input was not exercised. This is integrated/LAN **generation** evidence, not a real-client gameplay PASS.

## 3. P1-A under injected faults (new, final jar, lab run configuration)

Each fault makes the referenced start missing, beyond the chunk cache, or unreadable, for every region near the structure (a worst case). Result at seed 173 and 42: structure fully intact (55,305/55,305 and 52,443/52,443 cells, 21 pieces), the incident is counted by its cause (121 affected regions of 327 and 313 for the first two faults; not every region), and 86,000 to 121,000 writes were refused in the unreadable footprints. Without faults: 0 unavailable. The criteria are in `fault_policy_check.py`; they fail an ordinary run. Trade-off recorded for the owner: under a total data failure, vanilla features (trees, ores, other structures' pieces) are suppressed in the affected footprint instead of the structure being damaged. Vanilla also logs an ERROR ("Failed to fetch mob spawner entity") when a monster-room spawner write is refused.
Not exercised by injection: `chunk_missing` and `references_failed` (no fault hook for them); covered by the footprint unit tests and code review only.

## 4. Lab isolation on the packaged jar (new)

Real server runs of the built production jar with the lab jar installed and a hostile lab environment (`SG01_WRITE_GUARD=0`): no opt-in -> ignored, write guard on, structure intact; a copy of the lab jar under another mod id with the opt-in -> ignored, same; the genuine lab jar with the opt-in -> honoured (legitimate lab use still works). Residual (reviewer, P2): a mod can still reach the guard by reflection or its own mixins; the gate stops accidental or entrypoint misuse, not a hostile mod.

## 5. CI and regression results

- Unit suite: 160 tests OK (new: 6 repair tests, 5 production-check tests; updated tests that pinned the old behaviour are listed in the commits).
- GitHub, PR #44 head `888e6f0`: portable-export, clay-feature-ab, minecraft-26-3-stages (sg02, sg03), minecraft-26-3-visual, SG-03 natural-world (both workflows, both seeds), and the new `production-module` job (14 artifact checks, both sites, lab isolation 3 cases, fault policy 3 cases) all success; `sg01-environment-stress` was still running when this was written and must be re-read. The vanilla N4 workflow is green in its split form (blocking claim clay-only, strict result diagnostic).
- Earlier head `c7f2e59` failed only the WS fault case on the runner (twice, reproducible); its cause was the lab fault's engine call (section 1, last row). The jar hash `907e4910…` was identical on the runner and locally.
- No new progression-critical structure defect: every generation run (dedicated, integrated, LAN, faults, isolation) kept 21 pieces and every template cell; the three accepted iron_bars cells are not in these sites.

## 6. C2 performance (new; not weakened, no exception)

Method: the same site (seed 173 chunk (-19,15)), `spiral_out`, same lab instrumentation, 12 pairs with alternating order. Guard ON = write guard enabled (median 1,099 writes blocked per run); guard OFF = `SG01_WRITE_GUARD=0` (enabled False, 0 blocked), confirmed per run. Measured on the jar built at `c7f2e59` (`907e4910…`); the only later change is an inert lab-fault branch.
- Median paired overhead **-6.8%** (10.4 s vs 11.6 s median generation window); mean +0.8%; range -43.9% to +111.2%; interquartile -23.8% to +20.9%.
- Noise floor (the same guard-OFF configuration run twice, 6 pairs): +6.7% to +133% (median +55.7%, always the first-run side slower).
- Secondary (production jar vs vanilla jar, 8 pairs): median -7.7%, range -47.5% to +66.4%.
- **Verdict: INCONCLUSIVE.** The literal median (-6.8%) is below the +10% limit, but the measurement noise is an order of magnitude larger than the threshold, so this method cannot show whether the guard costs more or less than 10%. It is not recorded as a PASS, and the +10% criterion is unchanged. The earlier +7.1% PASS stays withdrawn; the +11.9% FAIL from the first corrected run is superseded by this larger set, not erased. A resolving measurement needs in-process timing or CPU time per chunk instead of wall-clock windows on a shared machine.

## 7. Remaining findings, blockers, merge sequence

**Independent follow-up review** (fresh read-only agent; same model family; not a human review): no P1. Claims verified: bounded footprint, integrated loading, exemption token, SG-03 unchanged; the lab seam claim was refuted until `LabHooks.install` was made package-private (done). Open items (none fixed): P2 the footprint refuses every non-exempt write in it (documented trade-off); P2 regression coverage of the wiring is thin (string tests; real checks are the Minecraft runs above); P3 counters and event caps are per JVM, not reset per integrated world; P3 the cached zone ignores a datapack reload during one step; P3 `enterPlacement` catches only `IllegalStateException`; the exemption covers every write on the placing thread, not only the start's own boxes (unchanged from before).

**Still open from earlier stages (unchanged):** B1 strict FAIL with the approved three-cell exception; B2 and resource criteria NOT EVALUATED; L3 PARTIAL and the L10 setup-stall exception; the 665-cell control/vanilla difference UNKNOWN; no human review; `sg01-environment-stress` on #44 to be re-read.

**Release blockers:** (1) human review of the production change set (not waived); (2) C2 inconclusive; (3) owner approval of the new behaviour on unavailable data (section 3 trade-off) and of the `"*"` environment (the module now also loads in a pure client JVM, where it does nothing).

**Merge sequence (unchanged, after authorization):** #18; then #19, #20, #21, #23, #25, #27, #29, #30, #32, #34, #36, #38, #39, #40, #41, #43; then this PR (#44); the Ancient City stack independently (resolve `.gitignore` as proposed). Re-run this PR's checks on the merged head.

**Rollback:** remove the jar; the module stores nothing in the world. To undo only the repairs, revert the merge commit of this PR (this restores the previous jar behaviour, including the old fail-open behaviour and `environment: "server"`). Reverting the pack-step restoration would move SG-01/SG-02 back to step 10 for new chunks.
