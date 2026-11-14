# ST-03 perimeter wall: batch 8 candidate vs wall F (2026-11-14)

Status: **DECIDED — owner decision D-1 (2026-11-14): wall F adopted.** The integration tools now load the F NBTs
(`experiments/st03-wall-redesign/out/f/`, copied byte-identically from `exp/st03-wall-final-20261106` @ `a57768c`).
The batch-8 candidate stays in `experiments/st03-batch8-perimeter-walls/` as history. Adoption evidence:
`experiments/st03-integration-d1-d9/README.md`. The comparison below is kept as it was written before the decision.

## Lineage (checked with `git merge-base`)

| branch | head | relation to the batch-8 tip `831e125` |
|---|---|---|
| `feat/st03-perimeter-walls-20261106` | `831e125` | the tip: batches 1-8, 18 facility NBTs + MW86/MW31 candidate |
| `exp/st03-wall-redesign-20261106` | `e4b9ff6` | child of the tip: prototypes A, B, C |
| `exp/st03-wall-b2-20261106` | `fc49d35` | child of the redesign branch: prototype B2 |
| `exp/st03-wall-final-20261106` | `a57768c` | child of B2: prototype **F** (final) |
| `exp/st03-wall-segment-20261106` | `511be3d` | child of wall-final: a single representative wall segment (v3), not a full MW86/MW31 |

So wall-final is **not an ancestor of the tip, but a descendant of it**. It is not an independent line. Its diff to
the tip touches no batch-8 file:
- It adds the folder `experiments/st03-wall-redesign/` (designs A, B, C, B2 and F, NBTs, checks, screenshots).
- It adds a backward-compatible `--perimeter-dir` option to `place_check.py`.

Adopting F would mean swapping in two NBT files with the same module ids, sizes and air mode. The placement table
does not change.

## Design

| | batch 8 (candidate) | F (final prototype) |
|---|---|---|
| idea | masonry curtain behind a battered plinth, a corbel table and a projecting parapet | stone frame with a recessed dark-oak timber frame and rubble infill in every bay |
| outer face rhythm | uniform; pilaster buttresses at fixed points (MW86 x12-13, 26-27, 42-43, 58-59, 72-73) | paired 7-wide bays under one beam; stone piers between pairs rise above the parapet |
| parapet | 2-wide merlons and 1-wide crenels (MW31: 3-wide end merlons); constant top at y12 | merlon pairs and single crenels on a period of 3; bay merlons to y11, piers and end masses to y12 |
| timber | only in the 9-block end zones (beam, brackets) | structural: posts, knee braces and beams in every bay; inside, a spruce-plank widening of the wall-walk with a fence rail |
| ends toward towers / gate | 1-wide solid end pier; decoration concentrated in 9-block end zones (Q90) | 6-8-wide solid end masses rising to y12 |
| decoration (MW86) | 6 lanterns, 7 banners, 5 barrels | lanterns only in the end bays; banners on the posts of the end frames; barrels and logs at the ends |
| size of the authored wall | MW86 3246 cells / palette 26; MW31 1198 / 26 | MW86 3752 / 29; MW31 1449 / 28 |
| weaknesses noted on the branches | no weakness is listed in its own README; the redesign README calls batch 8 "the old look (not kept)" and rates prototype C's risk as "outside closest to the old flat look", i.e. the redesign treats the batch-8 face as flat | its loops read a little like small arched windows up close; the inside face below the beam is plain; the end masses are deliberately plain |

## Verification evidence (as recorded on each branch; not re-run here unless stated)

| check | batch 8 | F |
|---|---|---|
| verify.py, strict placement, support | PASS (`check-result.json`) — **re-run 2026-11-14 in this session: PASS** | PASS (`check-result-f.json`) |
| rotations q=1-3, integrated q=0 (live B) | PASS (`place-check-result-walls.json`) | PASS (`place-check-f.json`) |
| slope sites S1-S3 (Q89 fill) | PASS | PASS |
| real 26.3 client screenshots | 41 views, 7 contact sheets | 21 final views (+ draft and revision 1), contact sheets |
| joint with the batch-9 towers and gatehouse | **PASS, newly run**: offline q=0 assembly and live (place_check q=0..3, batch-9 checks) | **offline only, newly run 2026-11-14:** all 10 wall ends backed by solid tower / gatehouse blocks (53/53 cells each). Not placed live with the towers. |

Q81 note: F's inner timber walkway is decoration. It is not connected to the towers or the gatehouse, which have no
wall-top access in either case, so no continuous patrol route exists with either wall (Q81 A).

## Decision needed (owner)

| option | effect | agent note |
|---|---|---|
| **A. keep batch 8** | nothing changes; batch 9 evidence stays valid as is | the default until decided |
| **B. adopt F** | copy `experiments/st03-wall-redesign/out/f/*.nbt` in place of the batch-8 NBTs (same module ids), re-run place_check live B and the batch-9 joint captures with F | recommended if the owner prefers F's stronger timber character. The towers and gatehouse need no change: the joints hold offline |
| C. adopt another prototype (A, B, C, B2, segment v3) | same swap procedure; the segment v3 would first have to be built as full MW86 / MW31 | |
