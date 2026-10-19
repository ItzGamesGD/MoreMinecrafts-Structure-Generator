# SG-03-N7-A — Fabric worldgen protection technical spike

**Status: EXPERIMENTAL, not production. Verdict: PARTIAL. N7-B: CONDITIONAL GO (see end).**
Stacked on PR #21 (N6). Nothing in production datapacks, exports, geometry, the N4 step-10 fix or the N4/N5 checks was changed.
Prototype lives only in `validation/fabric-protection-spike/` (Loom project, server-only, Minecraft 26.3, Loader 0.19.5, Fabric API 0.161.0+26.3).

## What was built
* `GeodeFeatureMixin` / `MonsterRoomFeatureMixin`: one `@Inject(at=HEAD, cancellable, require=1)` each into `place`; mixin config `required: true`, `defaultRequire: 1`. No `setBlock` hooks, no `@Redirect/@Overwrite`, no vanilla data overrides.
* `Guard`: computes the feature's hard reach box (geode origin ±16; monster room x/z ±4, y −1..+4), reads `STRUCTURE_REFERENCES` of the overlapped chunks (clamped to centre ±1) from the `WorldGenRegion`, loads the referenced `STRUCTURE_STARTS` only if `hasChunk` (never generates), intersects each Jigsaw piece bounding box with the reach box, and returns `false` from `place` before any write on collision. OBSERVE mode only records. Unavailable data ⇒ explicit WARN `SG_SPIKE unavailable structure data` and safe cancellation.
* Protection set from structure tag `moreminecrafts:protected_from_overlays`, resolved at `SERVER_STARTING` and data-pack reload. Missing or empty tag, or a Mixin not applied, is a startup exception.
* Test-only switches: `SG01_GUARD_MODE`, `SG01_FAULT`, `SG01_FEATURES`.

## Evidence (all newly run in this session, local official 26.3 server, N5 lab, seed 173 only)
Raw per-run data: `evidence/n7a-spike-runs.json` (24 live runs), `evidence/n7a-failloud.json`.

| Check | Result |
|---|---|
| Both Mixins apply | PASS: startup self-check (`GuardMarker` assignable from both records) logs `applied=true` for both; handler executed in all runs (attempts: geode 10, monster room ~4578 per run) |
| Start + piece-box lookup in natural generation | PASS in the tested runs: references→starts→21 piece boxes resolved, `unavailable=0` in all natural runs |
| Baseline failure (observe) | Reproduced in 8 of 9 observe runs (one rowmajor run at (-18,36) was clean, so the failure is order/timing sensitive): geode site mismatch 139 / foreign 37; monster-room site mismatch 120–226 / foreign 338–473 |
| Guarded (enforce) | 10 of 10 final enforce runs and all 4 chunk orders: mismatch 0, foreign 0, 21 pieces, trial spawners 3/3, no orphaned natural spawner inside piece boxes |
| Cancelled counts | Geode: 2 per run (both genuine reach/piece collisions). Monster room: 62–70 per run |
| Fail-closed | Fault injection (3 runs): out-of-range / status-too-high / missing start ⇒ explicit diagnostics, all affected features cancelled, structure intact; the lookup throws instead of generating |
| Loud failure | Server start without the SG datapack (tag resolves to nothing) aborts with an exception: PASS |
| Config tests | `tests/test_n7a_spike_config.py` 6 passed |
| Per-hook independence (h1/h2, one site, one order) | h2 (monster-room hook only): the unguarded geode still corrupts (mismatch 120, foreign 473) while the monster-room hook cancelled 70. h1 (geode hook only): clean, but the monster room did not corrupt in the run either, so **h1 does not demonstrate that the monster-room hook is individually necessary** |

## Honest findings and limitations
* **Over-cancellation:** the guard compares the reach box with piece bounding boxes, not actual write volumes. 62–70 monster rooms were cancelled per run, but only a few are known to have caused damage; the cancelled count therefore overstates real collisions. No attempt was made to count rooms that would have actually written into a template or to measure vanilla loss outside the protected region beyond the counts above.
* "No neighbouring-chunk generation during lookup" is supported by the source (`WorldGenRegion.getChunk` throws outside the region), by `hasChunk` checks, by fault injection, and by zero unavailable events; it was **not** instrumented with a chunk-generation counter.
* Only seed 173 and two sites; seed 42, other structures, existing worlds, player modifications, concurrent worldgen, other mods and performance were **not** tested. No universal deadlock-safety or compatibility claim is made. Timing was not benchmarked.
* The monster-room hook's individual effect is demonstrated only indirectly (cancelled collisions with piece boxes plus the all-features enforce runs), not by an isolated unguarded-vs-guarded monster-room-only failure.
* Only non-spike file touched: `.gitignore` (build/run output of the spike). `collision_lab.py` is an N5 lab script extended with Fabric options.

## Verdict: PARTIAL
Mixins apply, start/piece lookup works in natural generation, both features are intercepted, real geode and monster-room collisions were prevented with strict integrity preserved in the tested cases. Missing: direct no-generation instrumentation, isolated monster-room hook proof, seed 42, existing-world and performance tests.

## N7-B recommendation: CONDITIONAL GO
Condition: first close the gaps above (generation counter, isolated monster-room failure, exact write-volume check to cut over-cancellation, seed 42, existing-world behaviour). N7-B was not started.
