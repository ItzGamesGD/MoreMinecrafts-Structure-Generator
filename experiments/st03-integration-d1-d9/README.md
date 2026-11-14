# ST-03 owner decisions D-1 and D-9 applied, integrated re-check (2026-11-14)

Owner decisions, after the owner reviewed and passed the structure screenshots (2026-11-14):
- **D-1, wall F adopted:** the perimeter walls MW86 / MW31 are the F design.
- **D-9, F06 minimal fix:** the 33 grass cells in F06 that have a block standing on them become dirt.

No merge. Base: batch 10 `f32c66c` on `claude/clever-carson-w1fu8c`.

## What changed

| item | change | evidence |
|---|---|---|
| D-1 wall F | `experiments/st03-wall-redesign/{build,common,design_f,checks,sheet_f}.py`, `README-F.md`, `out/f/`, `check-result-f.json`, `place-check-f.json`, `approval-f/`, `screenshots-f/final/` copied **byte-identically** from `exp/st03-wall-final-20261106` @ `a57768c`. The A/B/C/B2 prototypes are not brought over. | `out/f` NBT sha256 `dcad38a6…` (MW86) and `6d4172a1…` (MW31): equal to wall-final's final screenshot record. Rebuilt on this branch: byte-identical NBTs. |
| switch to F | `place_check.WALLS` (one constant) points at `experiments/st03-wall-redesign/out/f`. `built_modules(perimeter=True)` and every check and capture that uses it now load F. The batch-9 joint test reads the same constant. | |
| batch-8 walls | unchanged; kept in `experiments/st03-batch8-perimeter-walls/` as history | |
| D-9 F06 | `experiments/st03-batch3-military/build.py`: at the end of `yard()`, every ground `grass_block` with a block standing on it (plants, fences, walls, lanterns, carpets, doors, trapdoors, banners and similar not counted) becomes `dirt`. The build asserts the count is 33. | `out/st03_yard.nbt` vs the previous NBT: exactly 33 cells differ, all y0, all `grass_block` → `dirt`. Covering blocks: stone bricks 13, spruce planks 12, dark-oak logs 6, barrel 1, chest 1. F05 (`st03_armory.nbt`) rebuilt byte-identically. |
| docs | `docs/st03/wall-lines-comparison-20261114.md` status set to DECIDED (D-1) | |

The placement table, towers, gatehouse, ground modules and every other facility are unchanged.

## Verification (all newly run 2026-11-14, pinned 26.3 server sha1 33680f5f…, client sha1 e877b6a0…)

| check | result | file |
|---|---|---|
| wall F own checks (`st03-wall-redesign/checks.py --designs f`): verify, support, footing, ends, top, no passage, boundaries q=0-3, strict placement, slope sites S1-S3 | **PASS** | `check-result-wall-f.json` |
| batch 3 checks (F05 / F06 after D-9): verify, states, access from every entrance, strict placement, F05↔F06 adjacency, premium chest access | **PASS** | `check-result-batch3-f05-f06.json` |
| batch 9 checks with F walls: joints, all 10 wall ends, every solid end cell backed by a solid tower / gatehouse block (**53/53 per end**); also boundaries q=0-3, traversal, strict placement, slope sites | **PASS** | `check-result-batch9-towers-gate.json` (`walls: experiments/st03-wall-redesign/out/f`) |
| batch 10 checks with F walls and fixed F06: network, all 27 entrances, walk test from outside the gate into every building, widths, decoration, steps, strict placement, slope site | **PASS** | `check-result-batch10-ground.json` |
| place_check, all 34 placements: rotations q=1-3 (32 placements each, every cell) | **PASS, 0 failures** | `place-check-result-adopted.json` |
| place_check live B, q=0, all 34 placements together, each cell against its final owner | **PASS, 0 failures** (F06 included: the intermittent grass failure is gone) | same |
| place_check live C, 0-2 drop terrain | **PASS, 0 hollow, 0 failures** | same |
| real 26.3 client, F walls with towers and gate | done | `screenshots-perimeter/` (18: four towers outside, four tower doors, gate outside and inside, 5 joints, 3 aerials), `screenshots-compound/` (12: whole compound q=0 and q=1-3, avenue, south road, three entrances); contact sheets in `approval/` and `approval-compound/` |

Notes:
- **Run count:** live B is a single run. The F06 failure used to be intermittent (random ticks). It is now removed at
  the source: no covered grass remains in F06, and the batch-10 modules have none either.
- **Corrected metadata:** `screenshots-compound/capture-info-adopted.json` field `walls` was corrected after the run.
  The batch-10 capture script still carried a fixed "batch-8" text. The walls it placed come from
  `place_check.built_modules`, which pointed at F for this run. The script now writes that field from
  `place_check.WALLS`.
- **Unchanged evidence:** the earlier batch READMEs and check results (batches 3, 8, 9 and 10) record the state at
  their time and were left unchanged. The current state is recorded here.

## Still UNTESTED

- Natural worldgen on real seeds and biomes, and the generator hook for the below-grade footing fill: no ST-03
  worldgen exists.
- Gameplay (garrison, loot, combat): out of architectural scope (Q95 follow-up).

## Reproduce

```
PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/checks.py --designs f \
    --out experiments/st03-integration-d1-d9/check-result-wall-f.json --server-jar server.jar --java java25 --work <dir>
PYTHONPATH=. python experiments/st03-batch3-military/build.py
PYTHONPATH=. python experiments/st03-batch3-military/checks.py --server-jar server.jar --java java25 --work <dir>
PYTHONPATH=. python experiments/st03-batch9-towers-gate/checks.py --server-jar server.jar --java java25 --work <dir>
PYTHONPATH=. python experiments/st03-batch10-ground-roads/checks.py --server-jar server.jar --java java25 --work <dir>
PYTHONPATH=. python experiments/st03-placement-check/place_check.py --server-jar server.jar --java java25 --work <dir> \
    --out experiments/st03-integration-d1-d9/place-check-result-adopted.json
ST03_ONLY=pl_,jt_,ov_ ST03_TAG=adopted PYTHONPATH=. python experiments/st03-batch9-towers-gate/capture.py ... \
    --out experiments/st03-integration-d1-d9/screenshots-perimeter
ST03_ONLY=ov_,rot_,rd_01,rd_06,en_02,en_07,en_08 ST03_TAG=adopted PYTHONPATH=. \
    python experiments/st03-batch10-ground-roads/capture.py ... --out experiments/st03-integration-d1-d9/screenshots-compound
```
(The batch 3, 9 and 10 checks write `check-result.json` into their own folders; those outputs were copied here and the
batch folders restored to their recorded state.)
