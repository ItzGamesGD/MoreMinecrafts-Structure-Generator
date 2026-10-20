# SG-03-N7-A4 — Production readiness and branch recovery

**Status: EXPERIMENTAL validation, not production. N7-B was not started. No production datapack or structure geometry was changed. PRs #18–#27 were not modified by this stage.**

Branch: `experiment/sg03-n7a4-readiness`, stacked on PR #27 (`experiment/sg03-n7a3-performance-validation` @ `5660b44`).

## Summary of results

* **Branch audit:** the five N7-A3 commits (`d78820c`…`ee3cff2`) on PR #25 are all under `validation/`, form a linear chain below PR #27 and cannot be removed without breaking #27. Preserved original head at `anchor/sg03-n7a2-reviewed-head-cb5ec04`. **PR #25 was not modified**; the proposed change (R1) is documented and awaits owner approval.
* **Compatibility contract:** versioned manifest, owner-pack-scoped compatibility check, additive-only extension, loud failure, last-validated set kept on reload. 17 cases validated on a real server (one first-pass fixture error disclosed), including the N7-A3 "format 999 loads silently" gap; unrelated packs are not rejected.
* **Ownership model:** recommend **C (versioned manifest + validated additive extensions)**. The legacy `replace` hole is demonstrated: 226 protected mismatches with no startup error.
* **Monster-room hook:** keep, as the hybrid guard.
* **Memory:** four ≈9-minute multi-site single-JVM soaks (2 guarded, 2 control). Heap-after-GC ramps in all four, then shows no detectable positive trend in the guarded arm and no difference from the control; non-heap +1.1 MB/min in every arm. Not a stability claim.
* **World comparison:** vanilla differs from vanilla by 8–15 k blocks; decoration order is a partial cause; statistical comparison **inconclusive** (negative controls flag as many chunks as the guarded runs).
* **Regression:** 64/64 runs pass every strict assertion; all repository checks pass.
* **Verdict: PARTIAL. N7-B: CONDITIONAL GO** (section 10).

## 1. Branch contamination audit and proposed recovery (Phase 0)

Verified against the remote at the start of this stage (nothing had moved):

| PR | Branch | Remote HEAD | Base | State |
|---|---|---|---|---|
| #23 | `experiment/sg03-n7a-fabric-spike` | `2813d76` | `experiment/sg03-n6-fabric-hook-study` | open, draft |
| #25 | `experiment/sg03-n7a2-guard-validation` | `ee3cff2` (reviewed head was `cb5ec04`) | `experiment/sg03-n7a-fabric-spike` | open, draft |
| #27 | `experiment/sg03-n7a3-performance-validation` | `5660b44` | `experiment/sg03-n7a2-guard-validation` | open, draft |

The DAG is linear: `2813d76 → … → cb5ec04 → d78820c → 477993b → c04573e → 479f175 → ee3cff2 (PR #25) → 99caa7b → 7f993ee → 5660b44 (PR #27)`.

**The five unintended commits** are `d78820c`, `477993b`, `c04573e`, `479f175`, `ee3cff2`. They are N7-A3 work pushed to PR #25's branch: 14 files, +844/−22, all under `validation/fabric-protection-spike/` (spike sources, `build.gradle`) and `validation/minecraft-visual/sg03-natural/` (lab scripts). No production datapack, export or structure path is touched.

**Dependencies.** PR #27's own diff is 5 files only because its base is the contaminated branch. Its report and evidence depend on all five commits (the hybrid guard, the full-world, existing-world and tag-variant scripts), and `99caa7b` edits a file introduced by `479f175`. Removing any of the five from PR #25 would break PR #27's content.

**A concrete regression caused by the contamination.** `tests/test_n72_spike_guard.py::test_oracle_never_cancels` passes at `cb5ec04` and fails at `ee3cff2` and `5660b44`: commit `d78820c` refactored the monster-room mixin, and the test searched the source text for a line that no longer exists. The N7-A3 stage did not rerun it. It is fixed on this stage's branch only, not on PR #25.

**Preserved.** A new anchor branch `anchor/sg03-n7a2-reviewed-head-cb5ec04` points at the originally reviewed N7-A2 head. Creating it did not touch PR #25.

**Recovery options (none applied; every one that edits PR #25 needs the owner's approval):**

| Option | What changes | Effect on #27 | Verdict |
|---|---|---|---|
| R1. Keep, document | Owner edits PR #25's description to say it contains N7-A3 tooling (`d78820c`…`ee3cff2`) and that `cb5ec04` is the reviewed N7-A2 head (anchor branch above). Optionally cherry-pick the `test_n72` fix onto PR #25. | none | **Recommended.** No history change, nothing breaks. |
| R2. Revert in place | Add a revert commit on PR #25 undoing the five commits. | PR #27 would then re-introduce them on its next merge of #25, or lose its tooling | Not recommended; breaks the chain. |
| R3. Re-home | Open a new PR from the anchor branch for N7-A2, retarget #27 onto a new base that still carries the N7-A3 tooling, close #25 | needs retargeting #27 | Possible, but changes two PRs and loses #25's review thread. |
| R4. Force-push #25 back to `cb5ec04` | History rewrite | would orphan #27 | **Forbidden** (AGENTS.md). |

**Proposed exact change for R1 (pending approval, not applied):** (a) edit PR #25's description: add a section "Contains N7-A3 commits d78820c…ee3cff2 (pushed here by mistake); the reviewed head is cb5ec04, preserved at anchor/sg03-n7a2-reviewed-head-cb5ec04"; (b) merge or cherry-pick commit `a7d1e65`'s change to `tests/test_n72_spike_guard.py` into PR #25's branch. Both are edits to PR #25 and are therefore **stopped here**.

## 2. Datapack compatibility (Phase 1)

### What Minecraft 26.3 does (from the 26.3 sources and the runs)

* Each pack gets a `PackCompatibility` (`COMPATIBLE`, `TOO_OLD`, `TOO_NEW`, `UNKNOWN`) from its declared format range (`PackCompatibility.forVersion`).
* The server **does not refuse** an incompatible world datapack. In N7-A3, a copy of the SG datapack declaring format 999 was found, loaded and used with no warning. The only place the value is used on the server side is a `(incompatible)` label in a pack listing.
* So the module cannot rely on the server to reject incompatible protection data, and it must not infer compatibility from whether a tag happens to resolve.

### Contract (implemented as `ProtectionContract`, opt-in `SG01_PROTECTION=manifest`)

The structure-owning datapack ships `data/moreminecrafts/sg_protection/manifest.json`: `{"format": 1, "revision": N, "structures": [ids]}`. The module declares `SUPPORTED_FORMATS` and `MIN_REVISION`. Startup (and every reload) validates, in order:

1. exactly one pack provides the manifest (`getResourceStack`): none ⇒ `MANIFEST_MISSING`; more than one ⇒ `MANIFEST_CONFLICT`;
2. it parses and has integer `format` and `revision` ⇒ `MANIFEST_INVALID`;
3. `format` is supported ⇒ else `FORMAT_UNSUPPORTED`; `revision ≥ MIN_REVISION` ⇒ else `MANIFEST_STALE`;
4. the **owning pack's own** compatibility is `COMPATIBLE` ⇒ else `OWNER_PACK_INCOMPATIBLE` (scoped to the owner; other packs' declared formats are never read);
5. the list is non-empty ⇒ `MANIFEST_EMPTY`; every id resolves in the structure registry ⇒ else `REQUIRED_UNRESOLVED`.

All are `IllegalStateException`s with a stable code; none silently disables protection.

### Experimental validation (`contract_variants.py`, real module on a real server, fixture packs only)

17 cases: 15 first-pass cases passed as designed (`evidence/n7a4/contract_variants.json`). The 16th first-pass case (`extension_unresolvable`) was a fixture error (a required extension entry for an uninstalled structure is rejected by vanilla's loader before the module runs) and is recorded as failed there; it was replaced by two cases, required and optional, rerun separately (`contract_variants_rerun.json`, both as designed). All 17 behave as designed:

| Case | Outcome | Code |
|---|---|---|
| valid manifest | starts | — |
| no manifest | **fails** | `MANIFEST_MISSING` |
| `format: 2` | **fails** | `FORMAT_UNSUPPORTED` |
| `revision: 0` | **fails** | `MANIFEST_STALE` |
| required id not installed | **fails** | `REQUIRED_UNRESOLVED` |
| empty list / invalid JSON | **fails** | `MANIFEST_EMPTY` / `MANIFEST_INVALID` |
| owner pack declares format 999 | **fails** | `OWNER_PACK_INCOMPATIBLE` (closes the N7-A3 gap) |
| second pack also provides the manifest | **fails** | `MANIFEST_CONFLICT` |
| extension adds `minecraft:stronghold` | starts, 2 structures | — |
| extension `replace: true` with empty list | starts, required set intact | warning only |
| legacy tag replaced to empty by another pack | starts, required set intact | — |
| optional extension entry for an uninstalled structure | starts, warning | — |
| required extension entry for an uninstalled structure | **fails in vanilla's loader before the module runs** ("Unbound values in registry … can't proceed with server load") | vanilla |
| **unrelated** pack declaring format 999 | **starts** (not globally rejected) | — |
| reload that adds a conflicting provider | rejected, last validated set kept, error logged | `MANIFEST_CONFLICT` |
| reload after the manifest became stale | rejected, last validated set kept, error logged | `MANIFEST_STALE` |

Limits: the contract is validated on fixtures, not on a production manifest (the production datapack was not modified). The reload test shows the module's own behaviour; vanilla still reloads the other data.

## 3. Protection-list ownership model (Phase 2)

| | A. Mod-owned immutable list | B. Datapack-extensible (merged tag, N7-A/A3) | C. Versioned manifest + validated extensions (recommended) |
|---|---|---|---|
| Authority | the mod | whatever the merged tag resolves to | the structure-owning datapack's manifest; extensions additive |
| New protected structure | needs a mod release | any pack, silently | content release (manifest) |
| Another pack can remove a required entry | no | **yes**: `replace: true` with a different valid list silently drops it (an empty or all-missing list fails loudly only because it resolves empty) | **no**: required set comes from the manifest, extensions are additive-only and `replace` is ignored with a warning |
| Conflicting owner detected | n/a | no | yes (`MANIFEST_CONFLICT`) |
| Version mismatch reported | by mod/MC version only | no | yes (`FORMAT_UNSUPPORTED`, `MANIFEST_STALE`, `OWNER_PACK_INCOMPATIBLE`) |
| Cost | tight coupling of mod and content | fragile | one more file and a compatibility range in the mod |

**Recommendation: C.** The manifest is authoritative for required structures; third-party datapacks may add protected structures through the additive extension tag; they may not remove or replace required ones; a second manifest provider is a startup failure; unresolvable required ids fail startup; unresolvable optional extension ids warn. On reload, a contract violation is rejected loudly and the last validated set stays in force (protection is never weakened by a reload). Registry ids are validated at startup. A mod-side floor (a hard-coded minimum list) was **not** adopted: it would recreate model A's coupling; `MIN_REVISION` is the stale-data guard instead.

Not tested: a tampering pack that replaces the manifest *and* the owner pack in the same load order (the conflict check covers two providers, not a pack that deletes the owner); and the legacy-mode silent `replace` hole is demonstrated in section 7.

## 4. Monster-room hook decision (Phase 3)

**Decision: keep the hook enabled in N7-B, implemented as the hybrid guard.**

Evidence preserved from N7-A2/N7-A3 (unchanged):
* Geode hook independently verified at four sites × eight orders (zero geode damage with the guard).
* Monster-room hook independently verified at seed 173 (-19,15), three orders, 3 of 3 runs each (monster-only baseline reproduced there; guard enforced ⇒ 0/32).
* Other sites showed no monster-only baseline damage. That is "no collision observed", not "no risk": the hook costs nothing where nothing collides.

Assessment:
* **Benefit:** proven where a collision exists; the cancelled attempt is the only one that writes a protected cell.
* **False-negative risk:** the precheck repeats vanilla's read-only preconditions; confusion matrix over ~140,000 attempts has zero false negatives and zero false positives (4 positives; small, which is why soundness rests on the replicated logic and the shadow check, not on the sample alone). The remaining risk is **vanilla drift**: a Minecraft change to `MonsterRoomFeature` would invalidate the replication. Mitigations: the module pins `minecraft` to exactly 26.3, and N7-B should add a startup self-check that falls back to the conservative N7-A box (not to "disabled") if the assumptions cannot be verified.
* **Precision:** the N7-A reach cancelled 2,040 attempts that wrote nothing in the oracle sample (99.8% of its cancellations); the refined/hybrid decision cancels none of those.
* **Cost:** hybrid skips 98.5% of attempts at the broad phase; decision p99 about 100 µs, about 26× fewer reads than the always-precheck variant (N7-A3).
* **Vanilla compatibility:** the hook cancels a single feature instance only when it would write into a protected piece; other monster rooms are untouched.

This does not require proof of necessity where the baseline has no collision, and the hook is not removed on a small positive count.

## 5. Memory and stability (Phase 4)

### Method
`soak.py` loads 36 protected sites (minimum separation 24 chunks) one after another in a **single server JVM** (release strategy `all`, `pause-when-empty-seconds=-1`), about 9.3 minutes per run. The in-process `Sampler` (JSONL, one row per 5 s) reads the JVM MXBeans: heap after the last GC, non-heap, cumulative allocation, GC count/time/last pause, loaded chunks, and the guard's retained state (`guard_events_retained`, `perf_samples_retained`). Two **guarded** runs (manifest mode, hybrid guard) and two **control** runs (same server, same sites, no guard) were done in alternation (`guarded_1, control_1, guarded_2, control_2`). `soak_analyze.py` fits an ordinary-least-squares slope with a 95 % interval (normal approximation; successive samples are autocorrelated, so the intervals are optimistic) and reports "no detectable trend" when the interval includes zero. That is **not** reported as "stable".

### Results (newly run; raw rows in `evidence/n7a4-soak/`)

| Run | Duration | Heap-after-GC, whole post-warm-up slope | Steady-phase slope, last half | Steady-phase slope, last third | First / last third mean | GC time | Alloc | Loaded chunks (max) |
|---|---|---|---|---|---|---|---|---|
| guarded_1 | 9.4 min | +8.06 ± 1.85 MB/min | −4.08 ± 3.22 | −3.39 ± 5.47 (n.d.t.) | 330.6 / 370.4 MB | 0.8 % | 5.97 MB/s | 1369 |
| control_1 | 9.3 min | +6.83 ± 1.51 | +0.88 ± 3.56 (n.d.t.) | −5.06 ± 3.30 | 334.9 / 370.7 MB | 0.7 % | 6.38 MB/s | 1618 |
| guarded_2 | 9.3 min | +2.02 ± 1.84 | −2.78 ± 3.53 (n.d.t.) | −8.72 ± 4.96 | 335.8 / 345.4 MB | 0.9 % | 6.25 MB/s | 1392 |
| control_2 | 9.3 min | +8.41 ± 1.59 | +2.96 ± 3.00 (n.d.t.) | +5.36 ± 4.74 | 332.1 / 374.6 MB | 0.8 % | 6.19 MB/s | 1369 |

(n.d.t. = interval includes zero. Heap max is 3 GB; heap-after-GC stays at about 330–390 MB.)

Other signals, all four runs:
* **Non-heap** rises about +1.1 MB/min (1.07–1.14, interval ±0.11–0.13) in **every** run, **including the controls**: class/metaspace growth of the server itself, not attributable to the guard.
* **Guard retained state is bounded**: `guard_events_retained` ends at 76–77 in the guarded runs (0 in controls); `perf_samples_retained` rises to ≈584 k and then stops (the sample arrays are preallocated with a fixed capacity, so it is a counter, not heap growth).
* **GC**: 283–353 collections per run, GC time fraction 0.7–0.9 %, longest recorded pause 40–45 ms; no difference between arms.
* Loaded chunks plateau (about 1370–1620), i.e. the soak reaches a steady working set, and the heap curve levels out at about 4–5 minutes in every run.

### Reading
* Heap-after-GC **rises during the first ≈4 minutes in all four runs, guarded and control alike** (load ramp to the chunk plateau). The whole-window slope is therefore a ramp, not a leak signal.
* In the steady phase the slopes have mixed signs (guarded: −4.1, −2.8 over the last half; control: +0.9, +3.0) with intervals of about ±3 MB/min. **No sustained positive heap trend is detected in the guarded arm, and the guarded arm is not different from the control.**
* What this does **not** show: stability over hours. The window is ≈9 minutes, the detection resolution is about ±3–5 MB/min, and a slower leak (or one that only grows with chunk churn beyond this working set) would not be seen. This is "no detectable trend in a 9-minute multi-site soak", not a memory-stability claim.

### `Wrong max.bg.threads property value '0'`
Not caused by the module. The lab runner passed `0 0` to the harness as thread arguments, which sets `max.bg.threads=0`; `Util.getMaxThreads()` treats an invalid value by falling back to 255 and logging that message. Thread count was also tested as a cause of worldgen differences and ruled out (section 6). It does not affect the validity of the soak.

### Harness finding that affects earlier stages
A 26.x dedicated server **pauses itself 60 s after the last player leaves** (`pause-when-empty-seconds`), and a paused server stops loading chunks. The first soak attempts stalled at the seventh site for that reason (thread dump: no deadlock; vanilla without the module also stalled). All N7-A4 runs set `-1`. Earlier stages' runs longer than 60 s of empty-server uptime may have been affected; I did not re-check them, and this is flagged, not concluded.

## 6. Worldgen comparison validity (Phase 5)

### Why vanilla differs from vanilla
In this harness, **two vanilla runs of identical seed, site, chunk order and settings differ** (newly measured, `status=full` chunks only):

| Condition (seed 173, (-19,15), row-major reversed) | Pair | Chunks compared | Blocks differing | Chunks differing |
|---|---|---|---|---|
| settle before save (`SETTLE`) | a–b / a–c / b–c | 105 | 8,548 / 11,768 / 10,729 | 44 / 48 / 50 |
| `tick freeze` (no random ticks) | a–b / a–c / b–c | 191 | 8,416 / 15,511 / 15,225 | 58 / 74 / 74 |

Hypotheses tested and **rejected** as the cause: unfinished chunks (all numbers use `full` chunks only, `--require-full`); server thread count (single-thread runs also differ); pacing/settling time; random ticks (freeze). Hypothesis with **partial support**: the order in which neighbouring chunks run `applyBiomeDecoration` differs between runs (observe-only `DecorationOrderProbeMixin`). Across four same-configuration run pairs (`decoration_order_analysis.py`, reach 2): 111–123 of 2,586 adjacent chunk pairs have their relative decoration order swapped; 55–68 % of the chunks that belong to a swapped pair contain differences versus 29–38 % of those that do not; the differing-block counts are 8.8–12.4 k versus 4.1–6.3 k. So swapped order roughly doubles the chance a chunk differs, but **about a third of chunks with no swapped pair differ as well**: the decoration order is a contributing mechanism, not a full explanation. The remaining cause is **unexplained**.

A controlled (bit-identical) comparison could therefore **not** be obtained.

### Statistical comparison and its validity
`fullworld_stats.py` builds a per-chunk noise ceiling from the pairwise vanilla differences and flags chunks where the guarded run exceeds the ceiling against every vanilla replicate. **Negative controls show the method is not selective**: a held-out *vanilla* run compared against the other vanilla replicates is flagged "above noise" in 33 of 251 chunks (replicate d against a, b, c) and 22 of 251 chunks (replicate a against b, c, d), 21–26 of them far from any cancellation footprint. The guarded modes (zero or few cancellations) flag 13–34 chunks, i.e. **within the same range as the vanilla negative controls**:

| Run (vs 4 vanilla replicates) | Cancel footprint chunks | Chunks above noise | of which outside footprint ("unexpected") |
|---|---|---|---|
| A (guard observing, 0 cancellations) | 40 | 13 | 9 |
| B (N7-A broad box) | 57 | 16 | 6 |
| C (precheck) | 44 | 26 | 13 |
| H (hybrid) | 44 | 34 | 27 |
| negative control: vanilla d vs a, b, c | 40 | 33 | 26 |
| negative control: vanilla a vs b, c, d | 40 | 22 | 21 |

Run A cancels nothing and still shows "unexpected" chunks, which is the clearest sign that the flagged chunks are generation noise. With three or four replicates the ceiling is under-estimated, so the method cannot separate guard effects from noise. **Conclusion: the full-world statistical comparison is inconclusive.** It is not offered as evidence that outside-region changes are harmless, and it is not offered as evidence that they exist.

### What the classification can and cannot say
| Class | Status |
|---|---|
| Intended cancellations | Verified: every cancellation in the regression is a `collision` decision whose reach box intersects the protected piece it names (section 7). |
| Protected region | Verified exactly: zero mismatches against the template in all runs (section 7). |
| Noise floor | Measured above: 8.4–15.5 k blocks per vanilla pair. |
| Unexpected guard-attributable differences | **Not detected, and not excludable** by world comparison; the method has no power at this noise level. |
| Unexplained | Source of the vanilla-vs-vanilla differences (≈ one third of chunks with no swapped decoration order). |

The argument that the guard has no effect outside the cancelled feature is by **mechanism**, not by measurement: the guard is read-only and never requested or generated a chunk (`chunkmap_schedule`, `holder_schedule`, blocking/future server gets and unavailable reads are all 0 in every regression run) and its only action is returning from a feature instance before it writes. Vanilla seeds each feature's random separately (`setFeatureSeed` per feature), so skipping one instance should not shift the random sequence of later features; this was **not** verified experimentally here. A tighter check would need a deterministic harness (for example a single-threaded server with a fixed decoration order), which this stage did not obtain.

## 7. Final regression (Phase 6)

Configuration: spike jar, **manifest mode** (`SG01_PROTECTION=manifest`, fixture pack `pack_manifest` = the N7-A3 SG pack plus the test manifest; the production pack is untouched), hybrid guard, ENFORCE, both hooks. Four N5 sites × eight chunk orders × two repeats = **64 runs, all newly run** (`regression_verify.py`; per-run data in `evidence/n7a4/regression_runs.json`, verdict in `regression_verify.json`).

Per-run assertions (all must hold; the verifier was self-tested against deliberately damaged inputs before use):

| Assertion | Result |
|---|---|
| protected mismatches against the template = 0 | **64/64** |
| foreign blocks in template air = 0 | **64/64** |
| 21 Jigsaw pieces | **64/64** |
| trial spawner block count = entity count = site reference | **64/64** |
| identical start signature (pool elements, rotations, boxes) within each site | **64/64** |
| scheduling requests = 0, unavailable reads = 0 (no guard-induced neighbouring-chunk generation) | **64/64** (`chunkmap_schedule`, `holder_schedule`, `server_get_blocking/future`, `region_get_null/status_below` all 0) |
| every cancellation is a `collision` decision whose reach box intersects the protected piece it names | **64/64** (no unavailable-data cancellations, no cancellation without a piece in reach) |
| manifest contract OK at startup | **64/64** |

| Site | Runs | Geode attempts / cancelled | Monster-room attempts / cancelled |
|---|---|---|---|
| seed 173 (-19,15) | 16 | 160 / 32 | 73,248 / 5 |
| seed 173 (-18,36) | 16 | 160 / 32 | 70,112 / 0 |
| seed 42 (4,13) | 16 | 272 / 32 | 70,112 / 0 |
| seed 42 (6,-19) | 16 | 240 / 48 | 66,752 / 0 |
| **total** | **64** | **832 / 144** | **280,224 / 5** |

"No unexpected vanilla feature suppression" is shown as follows: 149 cancellations in 281,056 attempts, every one a protected-piece collision (assertion above); no cancellation for unavailable data. Features that never reached a protected piece were never cancelled. This does not prove that a feature other than geode and monster room is unaffected, because only those two are hooked.

**Fail-loud behaviour** is covered by the 17-case contract validation (section 2), not by these 64 runs. The regression queue was interrupted once by a worker restart (34 of 64 runs complete, none partial); the remaining 30 were run afterwards with the same script and settings, and the verifier ran over all 64.

**Legacy-mode ownership hole (new, `evidence/n7a4/legacy-replace/`).** Seed 173 (-19,15), hybrid guard, ENFORCE, legacy tag mode, one run each:

| Tag state | Startup | Log line | Cancellations (geode / monster) | Protected mismatches |
|---|---|---|---|---|
| intact (`#moreminecrafts:protected_from_overlays`) | OK | "1 structure(s)" | 2 / 2 | **0** |
| another pack ships the same tag with `"replace": true, "values": ["minecraft:stronghold"]` | **OK, no error** | "1 structure(s)" (identical) | **0 / 0** | **226**, plus foreign blocks in template air |

So in legacy mode a datapack that replaces the tag with any other valid structure silently removes SG protection and the server logs the same line as in the healthy case. This is the failure model A/B cannot rule out and C does (the manifest, not the tag, defines the required set; section 3).

## 8. Repository tests

| Check | Result | Run |
|---|---|---|
| `tests/test_block_states.py` | PASS (4) | newly run |
| `tests/test_datapack_builder.py` | PASS (3) | newly run |
| `tests/test_forgotten_kingdom_cavern.py` | PASS (6) | newly run |
| `tests/test_jigsaw.py` | PASS (4) | newly run |
| `tests/test_sg01_static_accessibility.py` | PASS (6) | newly run |
| `tests/test_sg02_cavern.py` | PASS (27) | newly run |
| `tests/test_sg03_rooms.py` | PASS (18) | newly run |
| `tests/test_structure_export.py` | PASS (7) | newly run |
| `tests/test_sg03_clay_resolution.py` | PASS (4) | newly run |
| `tests/test_n7a_spike_config.py` | PASS (6) | newly run |
| `tests/test_n72_spike_guard.py` | PASS (7) — failed at `ee3cff2`/`5660b44`, fixed here | newly run |
| `tests/test_n74_contract.py` | PASS (7) | newly run (new) |
| vendored mcbuild `uv run pytest -q` | PASS (162) | newly run |
| `ruff check .` / `ruff format --check .` (vendor/mcbuild) | PASS / PASS (52 files) | newly run |
| `tools/phase2_validate.py` | PASS | newly run |
| `tests/test_phase3_watchtower.py` | PASS (5) | newly run |
| `tools/phase3_validate.py` | PASS (648 blocks; regenerated NBT equals committed `final.schem`) | newly run |
| `git diff --check` against `origin/main` | PASS | newly run |
| Gradle build / jar of the spike | built by the lab runner for every run above | newly run |
| Contract variants on a real server | PASS (15 first-pass + 2 rerun = 17 as designed; 1 first-pass fixture error disclosed in section 2) | newly run |

Not run: nothing on the CI list was skipped.

## 9. Remaining risks

1. **PR #25 contamination is unresolved** and requires the owner's decision (section 1, R1 proposal not applied).
2. **Production manifest does not exist.** The contract was validated on fixtures; the production datapack was deliberately not modified. N7-B must add the manifest to the content pack.
3. **Soak is 9 minutes.** No hours-long run, no real player load; memory stability is not claimed.
4. **World comparison is inconclusive.** Outside-region neutrality rests on the mechanism argument plus the strict in-region assertions, not on a world diff.
5. **Vanilla drift** of `MonsterRoomFeature` (section 4); the self-check is proposed, not built.
6. **Legacy tag mode** (default in the spike) lets another pack replace the protection list silently; manifest mode closes it. N7-B should ship manifest mode only. The silent replace is now demonstrated (section 7: 226 protected mismatches, no error).
7. **Positive monster-room evidence is small** (one site). The hook is kept on the strength of the replicated logic, zero false negatives in ~140 k attempts and negligible cost, not on sample size.
8. **Possible earlier-stage effect of server auto-pause** (section 5), unverified.
9. **Mixin coupling** to Minecraft 26.3 (`required: true`, exact version pin): any Minecraft update needs a re-validation.

## 10. Verdict

**N7-A4 verdict: PARTIAL.**

| Gate | Result |
|---|---|
| Phase 0 branch audit | Done; recovery plan written; **PR #25 left unmodified, R1 awaits owner approval** (PARTIAL) |
| Phase 1 compatibility contract | Done and experimentally validated on fixtures (17/17); not yet on a production manifest |
| Phase 2 ownership model | Done; recommendation C, legacy hole demonstrated |
| Phase 3 monster-room hook | Decided: keep, hybrid, with a vanilla-drift self-check |
| Phase 4 memory | Done as far as a 9-minute, four-run multi-sample soak can go; **no guard-attributable trend detected; stability not claimed** (PARTIAL) |
| Phase 5 worldgen comparison | Cause of vanilla nondeterminism partially identified (decoration order); controlled comparison **not obtained**; statistical comparison **inconclusive** by negative control (PARTIAL) |
| Phase 6 regression | **PASS** 64/64 strict assertions; all repository checks PASS |

It is not BLOCKED: no unresolved P1 finding or security finding is known, and no test failed. It is not PASS: three gates (branch recovery, long-run memory, world-diff comparison) are not closed.

**N7-B recommendation: CONDITIONAL GO.** The guard itself is sound on every test that can distinguish it (zero protected-region damage, zero foreign blocks, zero chunk-generation side effects in 64 runs; the cancellation decision is exact in the oracle sample). N7-B may start once these conditions are accepted, and they should be written into the N7-B brief as exit gates:

1. **Owner decision on PR #25** (R1 or an alternative). Not a technical blocker for N7-B code, but N7-B must not be stacked further on a branch with undocumented contents.
2. **Ship manifest mode only.** Add the production manifest to the content pack in N7-B; remove legacy tag mode from the production module (section 3).
3. **Add the vanilla-drift self-check** (fall back to the conservative N7-A box, never to "off") and keep the exact Minecraft version pin.
4. **A long soak as an N7-B exit gate** (hours, real chunk churn, guarded vs control), because this stage only shows "no detectable trend in about 9 minutes".
5. **Do not rely on world-diff comparison** for outside-region claims; keep the strict in-region assertions and the mechanism argument, or build a deterministic harness first.

If the owner does not accept condition 4 or 5 as sufficient, the recommendation is NO-GO until a deterministic comparison or a long soak exists.

## 11. Reproduction

All scripts are under `validation/minecraft-visual/sg03-natural/`; the lab environment variables are those of `n73_run.sh` (`SERVER_JAR`, `JAVA_HOME`, `SG_PACK`). Raw outputs are under `docs/sg-03/evidence/n7a4-*`.

```
# contract (Phase 1)
SG_PACK=<built pack> python3 contract_variants.py --out OUT
# soak (Phase 4), four runs in alternation, then analysis
python3 soak.py --out OUT/guarded_1 --mode guarded ; python3 soak.py --out OUT/control_1 --mode control   # twice
python3 soak_analyze.py OUT/summary.json OUT/guarded_1 OUT/control_1 OUT/guarded_2 OUT/control_2
# vanilla noise and decoration order (Phase 5)
SETTLE=… FREEZE=… n73_run.sh OUT V 173 -19 15 rowmajor_rev REP 0
python3 fullworld_diff.py --base A/regions --other B/regions --other-lab B/lab.json --out OUT.json --require-full
python3 decoration_order_analysis.py OUT.json RUN_A RUN_B
python3 fullworld_stats.py OUT.json --guarded REGIONS --guarded-lab LAB --vanilla REGIONS …
# final regression (Phase 6)
SG01_PROTECTION=manifest n73_run.sh OUT H SEED CX CZ ORDER REP 0   # 4 sites x 8 orders x 2 repeats
python3 regression_verify.py OUT.json OUT_DIR
# repository tests: see section 8
```

