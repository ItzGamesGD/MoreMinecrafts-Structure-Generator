# SG-03-N7-A4 — Production readiness and branch recovery

**Status: EXPERIMENTAL validation, not production. N7-B was not started. No production datapack or structure geometry was changed. PRs #18–#27 were not modified by this stage.**

Branch: `experiment/sg03-n7a4-readiness`, stacked on PR #27 (`experiment/sg03-n7a3-performance-validation` @ `5660b44`).

__RESULT_SUMMARY__

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

17 cases (the 16 first-pass cases, with the extension case split in two after a fixture error; the rerun is recorded separately). All behave as designed:

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

Not tested: a tampering pack that replaces the manifest *and* the owner pack in the same load order (the conflict check covers two providers, not a pack that deletes the owner); and the legacy-mode demonstration of the silent `replace` hole is stated from tag semantics and checked in section 7.

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

__REMAINING_SECTIONS__
