# SG-03 N10 — final release audit

**Release-readiness verdict: CONDITIONAL.** No defect was found that makes the release candidate unsafe to review for merge, and nothing was weakened. The candidate cannot be called released: four owner-gated items are open (section 7), and several pre-registered criteria remain NOT EVALUATED. This audit merges nothing, marks nothing Ready, and changes no production code.

Audited head: PR #40, `experiment/sg03-n9-live-acceptance` @ `31f93f9413454d3d4a44b34d910738082dca18b1`. This audit is stacked on it. Evidence: `docs/sg-03/evidence/n10/`.

**Requirement sources.** The repository has no committed N10 roadmap. The requirements used are `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md`, `docs/MAIN_INTEGRATION_PLAN.md` (dated 2026-10-18, it predates this stack and does not describe it), the committed criteria `docs/sg-03/n8-acceptance-criteria.md` and `docs/sg-03/n9-live-acceptance-criteria.md`, and the owner's N10 brief. No requirement was added or weakened.

"New" below means run during this audit; "inherited" means produced in an earlier stage and only reviewed here.

## 1. Branch and integration integrity

The release candidate is a 15-PR linear stack on `main` (`0ff40fb`, unchanged since the stack was cut): #18 (`integration/sg01c-sg02-sg03-20261019`) then #19, #20, #21, #23, #25, #27, #29, #30, #32, #34, #36, #38, #39, #40. All are Draft. The Ancient City stack (#22, #24, #26, #28, #31, #33, #35, #37) is separate and was not audited.

| Check (new) | Result |
|---|---|
| Each PR's base head is an ancestor of its head | 14 of 15. Exception: #27 (`5660b44`) does not contain #25's head (`51a48b9`) |
| #25's head commit | test-only (`tests/test_n72_spike_guard.py`, 2 lines); the full hunk exists as `a7d1e65` in the final head, so no content is missing, but `git cherry` lists `51a48b9` as not applied by patch id |
| Every other chain head is contained in #40's head | yes (13 of 13) |
| Simulated merge of each PR into its base, bottom-up | 15 of 15 clean |
| Simulated merge of #40 into current `main` | clean; #40 is 126 commits ahead and 0 behind |
| GitHub mergeable state | #18 and #38 clean; #39 and #40 "unstable" (only because of the CI failures in section 3) |
| Scope against AGENTS.md exclusions | no `vendor/mcbuild`, `artifacts/`, or Ancient City path is touched by the stack. 14 tracked bytecode files on `main` are untracked by N7-D (positive) |
| Conflict with the Ancient City stack | one: `.gitignore`. Whichever stack merges second needs a trivial resolution |
| Review activity | none: 0 reviews and 0 review comments on every PR in the chain. The `main` ruleset requires 0 approvals and no status checks, so nothing enforces review or CI |

Findings:
- **SG-01 and SG-02 are changed by this stack.** Commit `4490d9d` (PR #19, N4) moves the structure generation step of all three packs: SG-01 `vegetal_decoration` to `top_layer_modification`, SG-02 `strongholds` to `top_layer_modification`. PR #19 discloses this ("in all three builders", "owner decision"), but it conflicts with the mission rule to keep unrelated SG-02 unchanged. No SG-02 natural-generation run exists; SG-02 non-regression evidence is the structure-stage CI job only. Owner confirmation needed (section 7).
- **#25 is a contaminated review unit.** Its branch carries five N7-A3 lab commits (`docs/sg-03/n7a4-production-readiness.md`, section 1); the R1 recovery proposal was never applied and the owner decision is still open. They touch only `validation/` lab files, no pack or export. Merging the whole stack in order includes them.
- **Prerequisite:** nothing in #19 to #40 can merge before #18, which is the integration PR (SG-01c, SG-02, SG-03 content, 60 commits ahead of `main`).

## 2. Production artifact

All new, from a clean detached worktree of `31f93f9`:

- `gradlew clean jar labJar` run twice gives **byte-identical** jars: production `d64030ed2d46e4ededd944547a4170081bdba963f4a86aedb926744f47f77038`, lab `f58401e92c3642040f8ae7fde8d321de7a5dee5c688ab7b418aff0b84f3f5f0b`. This resolves the N8-D reproducibility item.
- The production jar contains `WriteGuard` and the two write-guard mixins (`StructureStartWriteGuardMixin`, `WorldGenRegionWriteGuardMixin`) next to the two feature mixins. `verify_artifacts.py` passes 12 of 12, and it selects the jar by project version.
- The jar used in the two N9 runs has the same SHA-256, and the N9 server logs list `sg_worldgen_protection 0.3.0-n7e` with no lab mod.
- Packaging facts: the jar ships no datapack. The pack (`exports/sg-03/...`, carrying `sg_protection/manifest.json`) is a separate artifact and the guard is useless without it. Dependencies: Minecraft exactly 26.3, Fabric Loader at least 0.19.5, Java 25 or later, `fabric-api` at any version (`"*"`). Server-side only. The mixins are `required`, so the module fails loudly on a vanilla change instead of running unprotected.
- Stale metadata: the jar's `description` still says it "cancels vanilla geode / monster room instances" and does not mention the write guard. Not changed here (it would change the artifact).

## 3. CI

Final state of #40's head (`31f93f9`), read at the end of this audit:

| Check | State |
|---|---|
| portable-export, clay-feature-ab, minecraft-26-3-stages (sg02, sg03), minecraft-26-3-visual, SG-03 natural-world integration (173, 42) | success |
| SG-03-N4 clay resolution: natural-world (173) and (42) | **failure** |
| sg01-environment-stress | see the note under the table |

`sg01-environment-stress` was still in progress when this report was written (started 01:17Z, previous runs took 19–28 minutes, no failing step so far). It must be re-read before any merge decision.

The N4 clay workflow:
- generates the pack on the plain vanilla 26.3 server, without the module, then asserts that "production" passes natural integrity. It therefore fails whenever vanilla damages the structure. The log of #39's failing run shows vanilla monster-room damage at site (-19,15) (23 cobblestone, 18 mossy cobblestone, 15 cave_air in place of template blocks) in replicate 1 and a pass in replicate 2.
- is red on 11 of 15 heads (#19, #20, #25, #27, #29, #30, #32, #34, #36, #39, #40) and green on #21, #23, #38 (and not triggered on #18). It is run to run, not a regression of one PR. Other transient failures in the history: the natural-world integration job on #19 and #29, and the visual job on #29; all green on later heads.
- is a vanilla-control instability, but not dismissible: it is the only automated check that measures structure integrity, and it never loads the module. **CI therefore contains no automated evidence that the protection works.** All protection evidence (N7 to N9) is lab evidence run by hand. The N4 workflow will keep failing or flapping after merge; it needs a decision (section 7). No ruleset enforces it today.

## 4. N8-R outstanding risks (classifications preserved)

| Item | Status | Release-critical? |
|---|---|---|
| B1 strict zero | **FAIL preserved**: 3 state-only `iron_bars` cells in 270 sites | No functional effect found; formal exception needed |
| Third iron_bars cell | **resolved by a new targeted run** (3 sites only, write guard, `docs/sg-03/evidence/n10/`): the same 3 cells reproduce deterministically. Each cell sits on the piece box's edge, the block id is `iron_bars` on both sides, and only the connection property differs, pointing at a solid natural block just outside the template (sulfur for (188,52); deepslate for the other two). The earlier "UNKNOWN" for (188,52) is now observed. It still does not reproduce in the four 24-site determinism worlds | No |
| 665-cell control vs vanilla | **UNKNOWN preserved** (attribution). The write arm matched the template at 24 of 24 sites; outside the expected region the write arm differs from vanilla less than a vanilla run differs from another | No: unshipped arm. Hypothesis (write ordering) untested |
| B2 neighbourhood | **NOT EVALUATED preserved** (24-site indicator only) | Open evidence gap |
| Resource criteria A1 to A6 on the write soak | **NOT EVALUATED preserved.** Indicator only (the evaluator also flags a required repeat that was never run): heap after GC grows 4.89 MB/min with the write guard and 4.79 MB/min in the control, RSS 5.8 vs 3.3 MB/min, GC fraction 0.74% vs 0.79%, CPU per chunk 48.2 vs 49.1 ms. The module's only accumulating state is a list capped at 200 entries (code review), so the growth is not module-held state, but vanilla attribution was never measured | **Open risk for long-running servers**: about 290 MB per hour under a forced chunk-generation load, unattributed |
| Cancellation-rate comparison vs N7-B/D/E | **NOT EVALUATED** (feature hooks made 0 attempts in the matrix) | No |
| Feature hooks inert in normal operation; drift level PROVISIONAL, 0 verified samples | as recorded in N8-R | Design fact: protection rests on the write guard alone until the drift guard reaches ZONE |
| Container restart during the N8-R queue | cause UNKNOWN | No |

Conclusion: nothing in this table makes the candidate unsafe; the resource-growth attribution is the one item that could matter for a long-running production server.

## 5. N9 live acceptance audit

Reviewed independently (new): both final run logs, results and screenshots; classifications are exactly as recorded in `docs/sg-03/n9-live-acceptance.md`: L1, L2, L4, L5, L6, L7 PASS at their stated levels; L3, L8, L9 PARTIAL; L10 FAIL (literal).

- Server logs of both runs: production mod `sg_worldgen_protection 0.3.0-n7e` loaded, no lab mod, fingerprints validated, contract OK, no `/place` command anywhere.
- L10 exception is limited to what is documented: each log has exactly one `Can't keep up` (3,500 ms in run 8, 2,742 ms in run 9), written immediately after the first setup forceload row that follows the `/locate`, and no other stall or error. Controls (inherited, two runs each): vanilla 2.9 and 3.2 s, production 3.2 and 3.3 s. Client frame-time stability and ordinary gameplay performance are **not verified**.
- Screenshots viewed (run 9): an active trial spawner in a cage under copper, a natural skeleton in a tunnel, the post-combat view inside the main chamber. They are real in-game images.
- Limits that stay visible: L3 entry is a teleport (owner-accepted as PARTIAL; not required to be repeated); a single seed and a single structure site; a software renderer; no cave-opening screenshot (L8); no per-refusal screenshots (L9).
- Observation (not a defect): hostile mobs (zombies, a witch, a skeleton) spawn in the unlit interior under normal difficulty.

## 6. Technical debt (deferred, none blocks review)

1. Stale documents: `docs/sg-03/n7b-production-guard.md` (module "still in `validation/fabric-protection-spike`"), the N6 design notes (write interception was the rejected design), and the jar description. No operator document exists for installing, configuring or removing the jar and the pack.
2. CI does not run the module; the N4 workflow assertion targets the wrong arm.
3. N7-D and N7-E artifact-check evidence names the stale `0.2.0-n7d` jar (disclosed on #36; corrected by `docs/sg-03/evidence/n8r/artifacts.json` and this audit).
4. Heap-growth attribution (section 4); B2 on write-guard worlds with at least 3 vanilla replicates.
5. The 665-cell attribution; spawner distance to the nearest piece; L8 and L9 screenshot gaps.
6. Behaviour not tested: other structures overlapping a protected piece box (the guard refuses their writes there by design), a world that already has chunks, other Minecraft versions (the version pin makes Fabric refuse to load).

## 7. Release blockers, owner-accepted exceptions, owner decisions

**Open until the owner acts (conditions for READY):**
1. No review of any kind exists on the stack, and the stack's 164,000 added lines on top of #18 are mostly docs, evidence and harness scripts; the 31 files under `mod/` (production and lab) have had no independent review. An explicit owner review or waiver is needed.
2. CI gate disposition: keep the N4 workflow red and non-required, repurpose it to load the module, or drop it. Also confirm `sg01-environment-stress` goes green on #40.
3. Strict B1 stays FAIL. Under the owner's rule, the three cells are now verified, boundary-adjacent and nonfunctional, so a separate owner exception can be recorded for exactly those three cells; none is recorded yet.
4. NOT EVALUATED pre-registered criteria (A1 to A6 on the write soak, B2): accept explicitly, or run the repeats (the heap-growth attribution is the one that matters for servers).

**Owner-accepted exceptions (preserved, narrowly scoped):** the L10 setup-command stall (literal FAIL kept); L3 PARTIAL (teleport entry); the write guard as primary protection, with the feature-level code kept inert.

**Decisions only the owner can make:** confirm that moving SG-01 and SG-02 to `top_layer_modification` (PR #19) is intended; decide the #25 contamination (R1); decide the order against the Ancient City stack (`.gitignore` conflict).

## 8. Proposed merge order and rollback

Merge order (after the conditions above; each PR must be re-checked on its own head, none is merged by this audit):
1. #18 into `main`. It is the prerequisite, clean and green.
2. Then bottom-up, retargeting each PR to `main` once its base is merged: #19, #20, #21, #23, #25, #27, #29, #30, #32, #34, #36, #38, #39, #40, each as a merge commit (`--no-ff`, per the workflow). Do not delete source branches (AGENTS.md).
3. The N10 audit PR last, or not at all (it adds documents and evidence only).
4. Merge the Ancient City stack independently; expect a `.gitignore` conflict on whichever merges second.

Rollback:
- The module is server-side, stores nothing in the world, and writes a file only if `SG_PROTECTION_REPORT` is set. Removing the jar from the mods folder rolls it back; worlds stay valid vanilla worlds.
- Chunks generated while the guard was active keep their intact structures. If the jar is removed before neighbouring chunks of an existing structure are generated, vanilla features can damage it again.
- The pack is independent of the jar. Reverting #19 would restore the old generation step of SG-01 and SG-02 for new chunks only.
- Code rollback is a revert of the merge commits in reverse order; no history rewrite is needed.

Not started and not authorized by this audit: any merge, Ready status, or release declaration.


## Erratum (N10 follow-up)
The C2 overhead recorded above (+7.1%, "PASS") compared two builds that both had the write guard enabled; it is withdrawn. The corrected pairs (baseline with the write guard off) give a median of +11.9%, a literal FAIL of the +10% rule, with a spread of -37.8% to +91.6%. See `docs/sg-03/n10-merge-readiness.md`, section 7. All other classifications in this record are unchanged.
