# SG-03 N10 — final disposition and merge-readiness report

**Verdict: CONDITIONAL.** Every item the owner assigned was handled, and nothing was merged, deployed or marked Ready. Two things stop a READY verdict: the independent review reported production-code findings that need the owner's approval before any change (section 3), and the corrected performance pairs no longer pass C2 (section 7). Evidence: `docs/sg-03/evidence/n10b/`. Earlier reports: `n10-release-audit.md`, `n9-live-acceptance.md`, `n8r-acceptance.md`.

**Release candidate.** Production artifact: `sg-worldgen-protection-0.3.0-n7e.jar`, SHA-256 `d64030ed2d46e4ededd944547a4170081bdba963f4a86aedb926744f47f77038` (two clean rebuilds byte-identical, same jar as the N9 runs). The production source (`mod/`) is unchanged by this stage: it is identical to PR #40's head `31f93f9413454d3d4a44b34d910738082dca18b1`. This PR adds only workflows, a harness script, tests and documents on top of #41.

## 1. Owner decisions applied

**1. Iron-bars exception (approved, narrowly scoped).** B1 stays FAIL under its strict zero rule; the exception covers exactly these three cells, observed in a write-guard world (new targeted run, seed 173):

| Site chunk | Cell | Piece (rotation) | Template | World | Neighbour that causes it |
|---|---|---|---|---|---|
| (188,52) | (2949,-20,841) | guard_room (COUNTERCLOCKWISE_90) | `west=false` | `west=true` | (2948,-20,841) natural sulfur, outside the piece box (box min x 2949) |
| (185,-90) | (2901,-35,-1447) | guard_room (COUNTERCLOCKWISE_90) | `west=false` | `west=true` | (2900,-35,-1447) natural deepslate, outside the box (min x 2901) |
| (522,-285) | (8363,-33,-4573) | guard_room (NONE) | `north=false` | `north=true` | (8363,-33,-4574) natural deepslate, outside the box (min z -4573) |

In all three the block is `iron_bars` on both sides, `waterlogged` and the other connection properties are unchanged, and all other template cells of the 21 pieces match. Functional assessment: the only difference is a bar connecting to a solid natural block on the structure's outer edge; no block is added, removed or replaced, and no passage, door or progression block changes. The exception is void for any other mismatch, any different property, or any other cell. Evidence: `n10/ironbars_write_world_cells.txt`, `n10/ironbars_write_world_audit.json`.

**2. B2 and resource criteria: NOT EVALUATED, accepted for this candidate.** They are not converted to PASS and long-term server stability is not claimed. For context only (indicator, not a verdict): heap after GC grows about 4.9 MB/min with the write guard and 4.8 MB/min in the control.

**3. N4 workflow separated** (section 4).

**4. SG-01 and SG-02 `top_layer_modification` (PR #19) reviewed** (section 5).

**5. #25/#27 discrepancy resolved with no change** (section 6).

**6. N9 L3 PARTIAL and the L10 setup-stall exception: preserved unchanged.**

## 2. Pre-merge requirements

| Requirement | Result |
|---|---|
| Independent review of the production change set | Done by a fresh read-only review agent that was given no conclusions (section 3). It is independent of my reasoning but is the same model family: it does not replace a human review, which is still absent on every PR |
| Final CI on #40 and the completed stress workflow | #40 head `31f93f9`: success: portable-export, clay-feature-ab, minecraft-26-3-stages (sg02, sg03), minecraft-26-3-visual, SG-03 natural-world integration (173, 42), **sg01-environment-stress (completed, success)**. Failure: SG-03-N4 clay resolution, natural-world (173) and (42) (vanilla, no module; addressed by the split below). #41 head: all checks completed so far are green |
| Automated test that the artifact loads the write guard | `production_module_check.py` plus workflow `sg03-production-module.yml`. Run locally (new): both sites PASS: 21 pieces, 55,305 of 55,305 cells at seed 173, write guard enabled with regions seen, writes blocked, 0 unavailable, hooks applied, fingerprints validated, contract OK. The check logic fails a real vanilla-jar result (139 cells overwritten, no guard) and each mutation of the criteria (`tests/test_n10_production_check.py`, 5 tests). The workflow itself has not yet run on GitHub: it runs when this PR opens |
| `.gitignore` conflict with the Ancient City stack | Resolved in a scratch merge: `docs/sg-03/evidence/n10b/gitignore_resolved_proposal.txt`; no rule from `main`, the SG-03 stack or the Ancient City stack is lost (section 6). Nothing was pushed to either stack |
| Merge order | section 8 |
| Risk classifications and rollback notes preserved | yes (sections 7 and 8) |

## 3. Independent review of the production code

Scope: `mod/sg-worldgen-protection/src/main`. Findings that I confirmed directly in the source are marked (confirmed). The others are the reviewer's, not re-verified by me.

**P1 (the reviewer's rating; production change, needs approval; none applied):**
1. (confirmed) Fail-open when structure data is unavailable. If a chunk of the 3x3 zone is missing, a referenced start is more than 8 chunks away, or a start is invalid, `Guard.pieceBoxes` returns null and `WriteGuard.boxesFor` returns an empty list. Boxes already found are discarded, the empty list is cached for the whole region, and only one ERROR line is logged. Observed `unavailable` is 0 in every run (matrix, N9, this stage), so this is a latent edge, not an observed failure. Suggested fix: keep and enforce the partial hits and count every incident.
2. (confirmed) `fabric.mod.json` and the mixin entry are `environment: server`: the mod does not load on an integrated (single-player/LAN) server, with no warning. It matters only if single-player is in scope; otherwise document it.

**P2:**
3. (confirmed by reading) The own-placement exemption re-evaluates "is this structure protected?" at enter and at exit. If the protected set is swapped between them (reload), the thread-local counter can stay above 0 on a worker thread and disable blocking there. Suggested fix: carry the enter-time decision to the exit.
4. The exemption is per structure type for the whole `placeInChunk`, so one protected start can overwrite pieces of another overlapping protected start; probably acceptable, should be a stated decision.
5. (confirmed) Any other mod registering the `sg_worldgen_protection:lab` entrypoint can switch the write guard off (it logs a WARN). Suggested fix: explicit opt-in or fail closed in a production build.
6. The drift fingerprints cover the feature hooks, not the write guard; the write-guard mixins rely on `require=1` and `required: true` to fail loudly at startup.
7. Only `WorldGenRegion.setBlock` is hooked; direct chunk writes, fluid ticks and neighbour updates are not covered.

**P3:** an unsynchronised read of the event list at shutdown (`WriteGuard.json`); linear scan of all piece boxes on every write in a protected region; per-region allocation (fine); log volume when the feature hooks are active; the report path from `SG_PROTECTION_REPORT` (overwrites any path, only if the operator sets it); non-atomic publish of config fields.

**Sound (reviewer):** thread safety of the drift levels and counters; the cached per-region box list; mixin failure behaviour; exemption balance within one structure; exact-coordinate blocking with no false-block path found; unbounded memory (the only accumulating list is capped at 200).

**Production-code changes that still require approval:** items 1, 3 and 5 (and 2 if single-player is in scope), each with a test for its failure path. Any such change alters the jar hash, so the artifact checks and the production-module check would be rerun.

## 4. The N4 clay workflow, separated

- `sg03-n4-clay.yml` (renamed "SG-03-N4 clay resolution (vanilla baseline)"): the blocking assertion is now the N4 claim only (`assert_n4.py --clay-only`: no clay-family overwrite, placement unchanged, piece count and spawner parity). The full strict assertion still runs as a non-blocking diagnostic (`continue-on-error`, a step summary, `strict-*.json` uploaded). Damage the module exists to prevent is reported there, not hidden. All historical failure evidence (run logs, artifacts) is untouched.
- `sg03-production-module.yml` (new): unit tests, committed-pack check, production jar build with `verify_artifacts.py` (12 checks), jar SHA-256, then `production_module_check.py` with **strict** integrity (every template cell, 21 pieces, no errors) and the write-guard assertions. Production integrity criteria are not weakened anywhere.
- Open: neither workflow's new form has run on GitHub yet; the first run is on this PR.

## 5. SG-01 and SG-02 `top_layer_modification` (PR #19, `4490d9d`)

- What changed: one shared constant moves the structure's generation step to `top_layer_modification` (step 10) in all three builders. Before: SG-01 `vegetal_decoration`, SG-02 and SG-03 `strongholds`. The N4 analysis also found that integration #18 had silently reverted SG-01-C's step change in the SG-02/03 packs.
- Necessity: demonstrated for SG-03 only. Lush-cave clay (step 9) overwrote the moss rooms; step 9 itself does not fix it, step 10 did (seed 42 site: fail 3 of 3 before, pass 3 of 3 after; `docs/sg-03/evidence/n4-step-repetitions.json`). No clay or other overwrite is demonstrated for SG-01 or SG-02.
- Compatibility: the server loads and generates the step-10 packs (N4 and all later runs); a test pins all three packs to the same constant (`tests/test_sg03_clay_resolution.py`), so reverting SG-01 or SG-02 alone also needs that test changed.
- Impact on previously approved behaviour: SG-01 moves one step later (still after the deep-dark sculk step, so the SG-01-C intent holds); SG-02 moves five steps later, so vanilla features no longer grow into or around its structure, and its structure now overwrites features instead of the reverse. Not verified: no natural-generation run of SG-01 or SG-02 with the new step exists (their CI jobs are structural).
- Not approved silently, no change made. Options for the owner: (a) accept as is, with the SG-01/SG-02 evidence gap recorded; (b) restore each pack's previous step through a per-pack step setting and adjust the test (a production-pack change needing approval, and a rerun of the pack checks).

## 6. Ancestry and `.gitignore`

- #25/#27: merging #25 into #27 in a scratch worktree is clean and its only net effect is the 2-line fix to `test_oracle_never_cancels`; that test is rewritten later in the stack, and the full suite passes at the final head (147 tests, plus 5 new here). Merging bottom-up (#25 before #27) already brings the hunk; no branch needs a change and no test is lost or duplicated.
- `.gitignore`: the SG-03 stack keeps every rule of `main` and adds Python caches, the Gradle/run directories of the module and the visual fixture. The Ancient City stack adds `tools/stage24d/node_modules/` but **drops** `*.pyc` and the three `artifacts/phase-2/control/` rules from `main`. Resolution (scratch merge, nothing pushed): the SG-03 file plus `tools/stage24d/node_modules/`. It loses no rule of any of the three; the owner should confirm the Ancient City stack did not drop those four rules on purpose.

## 7. Corrected measurement, approved exceptions, remaining debt

**Erratum (found in this stage).** The N8-R and N10 reports said the C2 overhead passed at a median of +7.1%. That is wrong: the "observe" baseline of those 12 pairs still had the write guard enabled (it blocked 1,099 writes), so it compared two guarded builds. Rerun with the baseline's write guard really off (new, 12 pairs, generation window of the same site): median **+11.9%** (13.6 s vs 11.3 s), range -37.8% to +91.6%. Against the pre-registered rule (median at most +10%) that is a literal FAIL, but the spread is far larger than the effect and the guarded side also carries lab instrumentation, so it is neither a clean measurement of the guard nor a pass. C2 is now recorded as FAIL (literal, noisy); the earlier PASS is withdrawn. The owner decision (B2 and resource criteria not evaluated) did not cover C2; a decision on C2 is requested. Evidence: `n10b/perf_pairs_corrected.json`. The soak control (guards off by `SG01_WRITE_GUARD=0`) was valid, so the heap/RSS indicator stands.

**Owner-approved or accepted (preserved):** iron_bars exception (three cells); B2 and resource criteria NOT EVALUATED; L3 PARTIAL; L10 setup-stall exception; write guard as the primary protection; inert feature-level code kept.

**Preserved as recorded:** B1 FAIL (literal); the 665-cell control/vanilla difference UNKNOWN; cancellation-rate comparison NOT EVALUATED; container restart cause UNKNOWN.

**Technical debt:** the review findings in section 3 that are not fixed; stale documents (`n7b-production-guard.md`, N6 notes, jar description); no operator guide for the jar plus pack; client frame-time stability not verified; a single seed and site for live acceptance; behaviour near other overlapping structures and on existing worlds untested; a human review of the stack.

## 8. Merge order and rollback

Merge order (nothing merged by this stage), each PR re-checked on its own head:
1. #18 into `main`.
2. Bottom-up, retargeting each PR to `main` after its base merges (merge commits, source branches kept): #19, #20, #21, #23, #25, #27, #29, #30, #32, #34, #36, #38, #39, #40, #41, then this PR.
3. The Ancient City stack independently; resolve `.gitignore` as in section 6 in whichever merges second.
4. Do not merge anything while the owner decisions in section 9 are open.

Rollback: remove the jar from the mods folder; the module stores nothing in the world and writes a file only if `SG_PROTECTION_REPORT` is set. Worlds stay valid vanilla worlds; chunks generated under the guard keep their structures, and structures whose neighbouring chunks generate after removal can be damaged again. The pack is independent of the jar. Reverting #19 restores the old generation step for new chunks of SG-01 and SG-02. Code rollback is a revert of the merge commits in reverse order, with no history rewrite.

## 9. Owner decisions still needed

1. Approve, reject or schedule the production changes for review findings 1, 3, 5 (and 2).
2. Decide C2 (literal FAIL at +11.9%, noisy): accept, rerun with a quieter method, or fix.
3. Decide SG-01 and SG-02: accept option (a) or choose (b).
4. Confirm the `.gitignore` resolution and that the Ancient City stack dropping four rules was unintended.
5. Arrange or waive a human review of the stack.
6. Authorize merging (and its order), the first run of the two new workflows on GitHub, and any Ready status.
