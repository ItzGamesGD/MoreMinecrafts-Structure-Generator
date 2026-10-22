# SG-03 N8-R — critical-risk triage, conditional acceptance and N9 readiness

**Record status: N8-R CONDITIONALLY ACCEPTED BY OWNER. N9: READY FOR IMPLEMENTATION (not started).**
This is an explicit owner risk decision. It is not a retroactive PASS: every FAIL, UNKNOWN and NOT EVALUATED finding below is preserved as it was reported.

Evidence: `docs/sg-03/evidence/n8r/`. "New" = produced in this triage or in the N8-R recovery run; "inherited" = produced earlier in the session and not re-run.

## 1. Critical-risk triage (read-only, preserved data only)

No production code, no PR state and no test configuration was changed. No soak, matrix or performance run was repeated.

### A. The three iron_bars cells (B1)

| Site | Cell | Room |
|---|---|---|
| (188, 52) | (2949, -20, 841) | guard_room |
| (185, -90) | (2901, -35, -1447) | guard_room |
| (522, -285) | (8363, -33, -4573) | guard_room |

- In each case the block id is `minecraft:iron_bars` in the template and in the world. Only the state differs, so there is no missing, replaced or extra block.
- The 270-site write-guard world no longer exists (the queue deleted it after the audit), so its properties cannot be read back. The coordinates are identical in the retained reproduction world `n8/repro/region`, which is the earlier feature-level build (no write guard), so that is **indirect** evidence only (`ironbars_cells.txt`):
  - (185, -90): `west=true` in the world, `west=false` in the template. The cell west of the piece box is natural deepslate.
  - (522, -285): `north=true` in the world, `north=false` in the template. The cell north of the piece box is natural deepslate.
  - (188, 52): the cell matches the template in that world; its properties in the write world are **UNKNOWN**.
- None of the four 24-site determinism worlds (vanilla A, vanilla B, control, write) contains a state-only mismatch, so the effect is not reproducible across runs (`statediff.py`).
- Assessment: the bars stay iron bars; the differing property is a connection toward solid natural rock at the edge of the structure box. No evidence of a functional effect (no passage opened or closed, no block removed). Cause in the write world: UNKNOWN. Hypothesis, untested: vanilla edge shape updates when the template is placed against existing terrain.
- Verdict: **B1 stays FAIL** under its strict zero-tolerance rule. Classified state-only, no functional problem found.

### B. The 665 inside-piece-box differences, control vs vanilla

Method: for the 24 preserved determinism sites, every cell of every piece (template placed with the saved rotation and box) was compared between two worlds and related to the template's expected state (`boxdiff.py`, `inbox_diff_*.json`).

| Pair | Cells differing inside piece boxes | Relation to the template |
|---|---|---|
| vanilla A vs vanilla B | 4 | 4 lava cells in `trial_chamber`, template air; A deviates, B matches |
| vanilla A vs write guard | 635 | **635 of 635**: vanilla deviates from the template, write guard matches it (343 template-air, 292 template-solid) |
| vanilla A vs control | 665 | 428 cells where vanilla matches and control deviates; 237 where control matches and vanilla deviates |

- Control-vs-vanilla by piece: grand_hall 645, barracks_hall 13, tunnel_west 6, residence_ruin 1. By block: feature and sculk/lava blocks written into the structure (air to calcite, smooth_basalt, amethyst_block; deepslate_bricks to calcite; deepslate_tiles to air, and similar). There is no state-only difference.
- Progression-critical elements: **no** trial_spawner, vault, chest, barrel, door or spawner cell differs in any pair. The only critical-class cells are `iron_bars` (4 cells, control-only damage: replaced by smooth_basalt in grand_hall) and stairs (3 cells, vanilla-only damage). The write guard restored both, and no entrance or path piece shows a difference other than feature or sculk blocks in the unguarded arms (tunnel_west: 6 cells damaged in control; 2 cells damaged in vanilla and restored by the write guard).
- Template deviations per arm over the 24 sites (id changes): vanilla A 292, vanilla B 292, control 389, **write guard 0**.
- Whole-area comparison: vanilla A vs B differs by 332,816 blocks (219,322 inside the expected region E, 113,494 outside); vanilla A vs write by 270,069 (185,320 inside E, 84,749 outside). Outside E, the write guard differs from vanilla by no more than a second vanilla run does.
- Why control differs from vanilla: **UNKNOWN**. Control is the module with all guards disabled and the sampler loaded; two vanilla runs agree to 4 cells, so the harness configuration changes the outcome. Hypothesis, untested: the relative timing of feature writes and structure placement. Control is a lab-only arm and is not shipped; the shipped configuration matches the template at all 24 sites.

### C. The natural spawner in the bbox gap

- Position (-284, -16, 248), seed 173, site (-19, 15) (chunk (-18, 15)). It is a vanilla monster-room spawner inside the structure's bounding box and outside every piece box.
- It appears in 20 of 20 earlier vanilla-jar runs (no module), in every observe-mode run of that site, and in all 16 production-matrix runs of that site. It is absent only in configurations that cancel monster rooms (fault injection, forced ZONE).
- One entry per run, so no duplicate. By the audit's definition (outside all piece boxes) there is no overlap with a piece.
- Not measured: its distance to the nearest piece box. The second site that reports one, (42, 4) at (48, -6, 246), was not compared with a vanilla-jar run.
- Assessment: normal vanilla generation. Verdict: **no defect found; adjacency unmeasured.**

### D. Outstanding evidence, recorded accurately

- **Drift state.** In all 64 matrix runs the monster-room and geode levels stayed PROVISIONAL, `verified_samples` was 0, and the report shows `effective_refine = ZONE`. The feature hooks made **0 attempts** in all 64 runs, so "0 verified samples" means the hooks never evaluated a placement, not that verification failed. The protection in those runs came from the write guard (blocked writes 284–3045 per run, `unavailable` 0). Feature cancellation only activates at level ZONE: forced fallback (FW) gave 1008 monster-room cancellations; the injected foreign monster-room transform (XM) put that feature at ZONE and the geode at VERIFIED.
- **B2 stays NOT EVALUATED.** Indicator only, not a verdict (24 sites, 2 vanilla replicates, not the 270-site data): ring feature counts in the write arm equal both vanilla runs for smooth_basalt (65,038), calcite (53,070), amethyst_block (41,263) and budding_amethyst (3,841); mossy_cobblestone is 2,739 vs 2,775 and spawners 86 vs 87 (`ring_totals_24sites.json`).
- **Stale jar (N7-E).** Disclosed on PR #36. The N7-E and N7-D artifact checks verified `sg-worldgen-protection-0.2.0-n7d.jar` because the script chose the first jar by sort order. `verify_artifacts.py` now reads the project version and the stale jars were removed. The recheck on `0.3.0-n7e` passed 12/12 (new).

## 2. N8-R acceptance record

| Item | Verdict | Evidence | Limitation |
|---|---|---|---|
| Artifact check, jar `0.3.0-n7e` | PASS | 12/12 (new) | production and lab jars only |
| Unit tests | PASS | 140 tests OK (new, before the queue) | not re-run after the recovery |
| Contract suite | PASS | 32/32, exit 0 (new) | |
| Production-jar matrix, 4 sites x 8 orders x 2 reps | PASS (completion) | 64/64 generated, no failed run, `unavailable` 0 (new) | no pass threshold beyond completion; hooks inert, so it exercises the write guard only. One run was interrupted by a container restart and rerun; the partial output is kept as `.interrupted` |
| Focus runs PJ, PE, FW, XM | PASS (against expectation) | levels and cancellations as in D | one site, one order |
| B1 strict zero | **FAIL** | 3 state-only `iron_bars` cells in 270 sites | see A |
| Piece count, trial-spawner parity, audit errors | PASS | 21 pieces per site, 0 trial-spawner mismatch, 0 errors, 270 sites | |
| Write-guard match to template at the 24 determinism sites | PASS | 0 template deviations (vanilla A 292, control 389) | 24 sites |
| C2 overhead | PASS on the stated rule, weak | median +7.1% of generation window, n=12, range -45% to +50% (new) | noise exceeds the effect |
| Control vs vanilla in-box differences | UNKNOWN (attribution) | B above | no defect in the shipped arm |
| Natural spawner in bbox gap | no defect found | C above | adjacency unmeasured |
| B2 neighbourhood | NOT EVALUATED | indicator only | |
| A1-A3 resource criteria on the write soak | NOT EVALUATED | the soak ran (270 sites, 3,480 s) but was not scored against the criteria | read-only step, not done |
| Cancellation-rate comparison vs N7-B/D/E | NOT EVALUATED | feature hooks made 0 attempts in the matrix | |
| N8-D: ancestry, byte-identical rebuild, SG-02 non-regression, CI check-run listing | NOT EVALUATED | | |
| 3x3 write boundary | PASS (inherited) | 18/18 inside writes applied, 18/18 outside refused | not re-run |

Queue interruption: container restarted around 16:05 (uptime 2 min at 16:07); no Java process survived; no log names a cause. Cause: **UNKNOWN**.

Accepted risks: the strict B1 failure at box boundaries; unattributed control-vs-vanilla differences in an unshipped arm; protection that rests on the write guard alone in normal operation; the remaining NOT EVALUATED items.

## 3. Technical debt

| Priority | Item |
|---|---|
| P1 (before any release statement) | Owner decision: the write guard reverses the earlier N7 decision not to intercept block writes; the owner has accepted it here for N9, release needs an explicit decision. |
| P1 | Real-client behaviour of the write guard is unobserved (N9). |
| P2 | Score the retained 270-site write soak against the A criteria; formal B2 on write-guard worlds (3+ vanilla replicates). |
| P2 | N8-D items: rebuild reproducibility, SG-02 non-regression, actual CI check-runs; repository CI does not exercise the guard. |
| P2 | Attribute control-vs-vanilla in-box differences (write-timing hypothesis). |
| P3 | Read iron_bars properties in a retained write world (keep the world next time). |
| P3 | Measure the spawner's distance to the nearest piece box; compare site (42, 4) with a vanilla-jar run. |
| P3 | Owner decision: keep or remove the feature-level hooks and drift code in the production jar; the hooks were inert in all 64 matrix runs. |
| P3 | Root-cause the container restart; the resume script `h2_resume.sh` is checkpointed (skips runs that have `lab.json`). |

## 4. N9 readiness

Assessment: ready to implement. Criteria are committed before any run (`docs/sg-03/n9-live-acceptance-criteria.md`, L1–L10).

Dependencies, checked just now: Xvfb, xdotool, xvfb-run, Mesa lavapipe (`lvp_icd.json`) are installed; Mojang endpoints reachable (HTTP 200); Loom caches exist (the Minecraft client download itself is not yet verified); the production jar `0.3.0-n7e` is built; `live_acceptance.py` exists as an **untested draft**.

Proposed scope: run the built production jar on a fresh seed-173 world with the real client under Xvfb; L1 join and render; L2 natural structure via `/locate`; L3–L4 approach and traversal with real xdotool input; L6 combat by real clicks; L7 trial spawner; L8–L9 screenshots and saved cells; L10 stability. L5 stays server-only and is reported as such. Anything that cannot be driven by real input is LIVE PENDING or BLOCKED, never PASS. Separate Draft PR. Expect the first run to debug `live_acceptance.py`.

Waiting for explicit authorization to implement N9.


## Erratum (N10 follow-up)
The C2 overhead recorded above (+7.1%, "PASS") compared two builds that both had the write guard enabled; it is withdrawn. The corrected pairs (baseline with the write guard off) give a median of +11.9%, a literal FAIL of the +10% rule, with a spread of -37.8% to +91.6%. See `docs/sg-03/n10-merge-readiness.md`, section 7. All other classifications in this record are unchanged.
