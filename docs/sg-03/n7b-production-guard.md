# SG-03-N7-B — Production guard implementation and verification

Branch `experiment/sg03-n7b-production-guard`, stacked on PR #29 (`experiment/sg03-n7a4-readiness` @ `6b64233`). Draft; nothing was merged or marked Ready.

**Scope of this report.** What was implemented, what was verified (and how), what remains risky, and what is explicitly deferred to the final integration stage. Long-duration soak, the full world-preservation audit and live gameplay acceptance were **not** run and are **not** claimed.

## 1. Phase 0 — R1 cleanup of PR #25 (done, owner-approved)

| Step | Result |
|---|---|
| PR #25 description | Edited: a disclosure block now names the five unintended N7-A3 commits (`d78820c`, `477993b`, `c04573e`, `479f175`, `ee3cff2`), the reviewed head `cb5ec04` (anchor branch `anchor/sg03-n7a2-reviewed-head-cb5ec04`), and the fix commit. Original text kept below the block. |
| Test fix | Only the `test_n72_spike_guard.py` hunk of `a7d1e65` was applied (the commit also contains unrelated files, so it was **not** cherry-picked whole). Compatibility confirmed first: the test fails on `ee3cff2` (1 error) and passes with the hunk (7/7). Pushed as a fast-forward: PR #25 branch `ee3cff2 → 51a48b9`. No force-push, no history rewrite. |
| #27 / #29 compatibility | `git merge --no-commit` of `51a48b9` into PR #27's head (`5660b44`) and PR #29's head (`6b64233`): both merge cleanly (the hunk is identical to #29's). #27's and #29's heads unchanged. |
| Not done | No PR was merged or marked Ready. |

Note: PR #27's base branch now has one commit it does not contain; it merges cleanly, so no action is needed unless the owner wants #27 refreshed.

## 2. Implemented functionality

All changes are in the validation module `validation/fabric-protection-spike` (mod id unchanged), the SG-03 builder/pack, the lab scripts and tests. SG-02 and other SG-03 content are untouched (the SG-02 pack is asserted unchanged by a test, and the SG-03 pack differs from the previous commit only by the manifest file and its entry in the resource manifest).

### Phase 1 — manifest ownership
* **Real manifest in the real pack.** `DatapackBuilder.add_protection_manifest()` (validates: non-empty, no duplicates, only structures this pack defines, positive integer revision, one manifest) and `build_sg03` (opt-in parameter, SG-02 not affected) write `data/moreminecrafts/sg_protection/manifest.json` into **`exports/sg-03/forgotten-underground-kingdom/datapack`**: `{"format":1,"minecraft":"26.3","revision":1,"structures":["moreminecrafts:forgotten_kingdom/central_cavern"]}`. The pack's own `manifest.json` lists it (role `protection_manifest`, sha256). The committed pack is reproducible from the builder (test).
* **Legacy tag mode removed.** The merged-tag path, `SG01_PROTECTION`, the bundled `protected_from_overlays.json` and `tag_variants.py` are gone. The manifest contract is the only protection source; there is no opt-in or fallback to a tag.
* **Validation at startup and on every reload** (`ProtectionContract`), each failure a `ContractViolation` with a stable code, a description and a **remedy**: `MANIFEST_MISSING`, `MANIFEST_CONFLICT`, `MANIFEST_INVALID` (parse, missing/invalid fields, non-string or duplicate entries), `FORMAT_UNSUPPORTED`, `MANIFEST_STALE`, `GAME_VERSION_MISMATCH` (new, manifest `minecraft` field), `OWNER_PACK_INCOMPATIBLE` (owner pack only, unrelated packs never inspected), `MANIFEST_EMPTY`, `REQUIRED_UNRESOLVED`, and the new **ownership check** `OWNERSHIP_MISMATCH` (the manifest's owner pack must itself define every structure it requires; a later override of the definition is a warning `STRUCTURE_OVERRIDDEN`).
* Startup violations abort the server start. A reload that violates the contract is rejected loudly and the last validated set stays in force.

### Phase 2 — additive extensions
`data/moreminecrafts/tags/worldgen/structure/protected_extensions.json` in any pack, read **per pack file** (never from the merged tag). Policy:
* adds protected structures; cannot remove or override the owner's entries (there is no code path that removes from the effective set);
* `"replace": true` → rejected, `EXTENSION_REPLACE_FORBIDDEN`;
* unparseable file, missing `values`, entry that is not an id string / `{"id":…}` object, non-boolean `required`, tag reference (`#…`) → `EXTENSION_MALFORMED`;
* required entry (default) for an uninstalled structure → `EXTENSION_UNRESOLVED` (in practice vanilla's own loader refuses the pack first, see below); `{"id":…,"required":false}` for an uninstalled structure → warning `EXTENSION_OPTIONAL_UNRESOLVED`;
* duplicates (within a file, across packs, or repeating a manifest entry) → warning `EXTENSION_DUPLICATE`, no effect.

Design note (trade-off): rejecting `replace` and malformed files makes a third-party pack able to stop the server from starting (and to be rejected on reload). That is the same effect vanilla has for broken tags and is deliberate: the alternative is silently ignoring a pack's protection request.

### Phase 3 — monster-room guard and self-check
* The hybrid decision is the **production default** (`Guard.REFINE` default `HYBRID`, mode `ENFORCE`).
* **Runtime compatibility self-check** (`MonsterRoomSelfCheck`), two independent checks:
  1. *Startup fingerprint*: SHA-256 of the vanilla `MonsterRoomFeature.class` (read through the class loader) must be in the validated set. The embedded value for 26.3 (`006a3287…f742`) was cross-checked against the class extracted directly from `server-26.3.jar`. Unreadable class or unknown fingerprint → fallback.
  2. *Runtime near-miss watch*: whenever the hybrid decision lets vanilla run although a protected piece lies in the widest footprint, the overlap cells are snapshotted and compared after vanilla returns; any change is a direct violation of the hybrid invariant → fallback.
* **Fallback** = the conservative box guard (the N7-A reach, union of all variant footprints) for the rest of the process, logged at ERROR, reported in the shutdown report (`monster_room_guard`). It never means "unguarded".
* **Production vs lab separation.** Every behaviour-changing switch (mode, fault injection, fixture, refine, oracle, shadow, per-hook selection, fingerprint override) and the timing instrumentation exist only with `SG01_LAB=1`; setting one without it makes the server refuse to start with an explanatory message. Production needs no configuration at all.

## 3. Verified functionality (all newly run in this stage)

### 3.1 Real-server contract suite on the real SG-03 pack — 30/30 as designed
`contract_variants.py` starts the module in its **production configuration** (no `SG01_*` behaviour variables) against disposable copies of the committed pack with one defect injected per case (`evidence/n7b/contract_variants.json`; every failing case also shows that the log carries a `Remedy:`):

| Group | Cases (all as expected) |
|---|---|
| Production data | `production_valid` (committed manifest accepted: required 1, extensions 0, format 1) |
| Manifest | missing → `MANIFEST_MISSING`; format 2 → `FORMAT_UNSUPPORTED`; revision 0 → `MANIFEST_STALE`; `minecraft` 26.2 → `GAME_VERSION_MISMATCH`; unresolvable required id → `REQUIRED_UNRESOLVED`; empty list → `MANIFEST_EMPTY`; invalid JSON / duplicate entry / non-string entry / no `structures` → `MANIFEST_INVALID` ×4; owner pack declaring format 999 → `OWNER_PACK_INCOMPATIBLE`; second provider → `MANIFEST_CONFLICT`; owner that does not define the structure → `OWNERSHIP_MISMATCH` |
| Extensions | valid (`minecraft:stronghold`, extensions 1); optional unresolved (warning, extensions 0); required unresolved (**refused by vanilla's loader**, "Unbound values in registry", before the module runs); `replace:true` → `EXTENSION_REPLACE_FORBIDDEN`; malformed JSON / bad entry / tag reference → `EXTENSION_MALFORMED` ×3; duplicates (warning, extensions 1); the old N7-A tag replaced by another pack → no effect (required 1, extensions 0) |
| Unrelated packs | unrelated pack declaring format 999 → starts (not globally rejected) |
| Datapack reload | `reload_conflict`, `reload_stale`, `reload_manifest_removed`, `reload_extension_replace`: each rejected loudly (`reload_rejections ≥ 1`) and the last validated set stays in force; `reload_extension_added`: accepted, extensions 0 → 1; `reload_extension_removed`: accepted, extensions 1 → 0 |

### 3.2 Placement and protection regression, production configuration, real pack — 64/64 pass
4 N5 sites (seed 173 (-19,15), (-18,36); seed 42 (4,13), (6,-19)) × 8 chunk orders × 2 repeats, config `P`: no lab variables, `SG_PACK` = the committed `exports/sg-03/.../datapack` (`evidence/n7b/regression_verify.json`, `regression_runs.json`). Per run, `regression_verify.py` asserts: 0 protected mismatches; 0 foreign blocks in template air; 21 Jigsaw pieces; trial spawner blocks = entities = site reference; identical start signature within a site; 0 chunk scheduling / blocking / future requests and 0 unavailable reads; every cancellation a `collision` decision whose reach intersects the protected piece it names. Result: **64/64 on every assertion**. Aggregate: geode 832 attempts / 144 cancelled, monster room 280,224 attempts / 8 cancelled (all collisions), 0 unavailable, 0 fallbacks, 4,072 near-miss watches with 0 violations; every run reported mode ENFORCE, refine HYBRID, contract owner `file/sg01`, format 1, revision 1, required 1. (Monster-room collisions were 5 in the N7-A4 run and 8 here: world generation is not reproducible in this harness, see the N7-A4 report; the count is not a regression signal.)

### 3.3 Fallback paths
* **Startup fallback** (config `F`, simulated vanilla drift by a lab fingerprint override), 4 sites × 2 orders = 8 runs: all report `FINGERPRINT_MISMATCH`, effective guard `OFF` (= box), and **8/8 pass every strict assertion**; monster-room cancellations rise from 0–8 per run (hybrid) to 56–70 (box) while protected damage stays 0 (`fallback_runs.json`, `fallback_verify.json`). That is the cost of the conservative guard.
* **Runtime fallback** (config `R`: lab fault that makes the replicated precheck wrongly report "vanilla writes nothing", which the startup fingerprint cannot see), seed 173 (-19,15), 3 orders: in one order vanilla actually wrote into a protected piece in an attempt the broken precheck had allowed; the watch detected it (`RUNTIME_VIOLATION`, 198 cells changed in the watched overlap), switched to the box guard, and 39 further monster-room instances were cancelled with no second violation. The other two orders had 75 near-misses but vanilla wrote nothing into a piece, so there was nothing to detect and nothing damaged. **Honest reading:** the watch detects after the fact. In the run that triggered it, 14 protected-block mismatches against the template remained (`drift_verify.json` reports `mismatch 14` for that run, by design a FAIL). The injected fault is a test of the detection path, not evidence that real drift would be harmless.

### 3.4 Repository tests, newly run
| Check | Result |
|---|---|
| 13 unit-test files: `test_block_states`, `test_datapack_builder`, `test_forgotten_kingdom_cavern`, `test_jigsaw`, `test_sg01_static_accessibility`, `test_sg02_cavern`, `test_sg03_rooms`, `test_structure_export`, `test_sg03_clay_resolution`, `test_n7a_spike_config`, `test_n72_spike_guard`, `test_n74_contract`, `test_n7b_production` | PASS (`evidence/n7b/ci/unit_tests.txt`) |
| `test_n7b_production` (new, 13 tests) | production manifest present in the committed pack, consistent with the module's accepted format/revision, checksum in the pack manifest, reproducible from the builder, SG-02 untouched, builder rejections, self-check fallback is the box guard and not "off", fingerprint set is real, lab-only gating |
| vendored mcbuild `pytest` / `ruff check` / `ruff format --check` | PASS (162) / PASS / PASS (52 files) |
| `tools/phase2_validate.py`, `tools/phase3_validate.py`, `tests/test_phase3_watchtower.py` | PASS, PASS, PASS (5) |
| Module build | Gradle compile and every server start above used the freshly built module |
| JVM unit tests | **NOT RUN / do not exist**: the module has no JUnit setup; behaviour of the Java code is covered by the real-server suites above and by source-level Python tests. |

## 4. Remaining risks
1. **The module is still in `validation/fabric-protection-spike`** (mod id `sg01_worldgen_protection_spike`, package `sg01spike`); moving or renaming it for release packaging was not done and would touch the lab harness.
2. **Fingerprint scope**: it covers `MonsterRoomFeature.class` only, not helper classes it calls (for example `BlockState.isSolid` semantics). Any such change is only caught by the runtime watch, which detects after the first damaging placement (section 3.3).
3. **Geode hook** has no equivalent self-check; its reach comes from the feature's own configured offsets.
4. **Structure definitions are not reloaded** by `/reload` in vanilla (worldgen registries load at start); the guard's reload validation covers manifest and extensions, and a changed structure definition needs a restart. Not tested separately.
5. **Strict extension policy** lets a malformed third-party extension block server start (section 2).
6. **Hybrid decision depends on replicated vanilla logic**; the safety net is the two checks above, not proof.
7. **World-diff neutrality outside protected regions** remains inconclusive (N7-A4); the argument stays mechanism-based.
8. **PR #25 is still contaminated** (disclosed, not removed); PR #27's base lags by one commit.

## 5. Deferred to the final integration stage (not run, not claimed)
* Long-duration soak (hours, real chunk churn, guarded vs control). Only the N7-A4 9-minute soak exists, and it ran the previous module build.
* Full world-preservation audit (existing worlds, chunk-by-chunk preservation against vanilla).
* Live gameplay acceptance (real clients, other mods, a production server).
* Re-measurement of CPU/allocation overhead of the production build (timing instrumentation is now disabled in production, so no production timing exists).
* Compatibility with other worldgen mods beyond the N7-A3 single-mod check.

## 6. Reproduction
```
export SERVER_JAR=… JAVA_HOME=…(JDK 25) SG_PACK=$PWD/exports/sg-03/forgotten-underground-kingdom/datapack
python3 validation/minecraft-visual/sg03-natural/contract_variants.py --out OUT                  # 30 cases
n73_run.sh OUT P SEED CX CZ ORDER REP 0     # production configuration regression (4 sites x 8 orders x 2)
n73_run.sh OUT F SEED CX CZ ORDER REP 0     # simulated drift at startup -> box fallback
n73_run.sh OUT R 173 -19 15 ORDER 1 0       # injected precheck drift -> runtime watch
python3 validation/minecraft-visual/sg03-natural/regression_verify.py OUT.json RESULTS_DIR
PYTHONPATH=vendor/mcbuild/src python3 -m unittest discover -s tests -p 'test_*.py'
```
