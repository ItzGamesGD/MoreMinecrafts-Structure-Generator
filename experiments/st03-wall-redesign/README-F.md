# ST-03 perimeter wall F: a fresh design (final prototype, owner approval pending)

Branch `exp/st03-wall-final-20261106`, based on `exp/st03-wall-b2-20261106` @ `fc49d35`. The base was chosen only
for its tools (`checks.py --out`, extra capture views). The design does not continue A, B, C or B2.

Untouched:
- the approved NBTs;
- the batch-8 candidate wall;
- the A/B/C/B2 prototypes;
- the placement table.

F does not replace the wall until the owner approves it.

| file | |
|---|---|
| `design_f.py` | the design (`build.py f`) |
| `out/f/st03_wall_86.nbt`, `out/f/st03_wall_31.nbt` | final MW86 86×13×5 and MW31 31×13×5 |
| `out/f-draft/` | the draft NBTs, kept for comparison |
| `screenshots-f/{draft,rev1,final}/` | real 26.3 client shots; the same cameras at each stage |
| `approval-f/` | contact sheets: `f_evolution_*` (draft / revision 1 / final), `f_final_*` |
| `check-result-f.json`, `place-check-f.json` | verification of the final |

## Design

**One principle: a stone frame with timber set inside it.** Each bay of the outer face reads in three depths:

| plane | what |
|---|---|
| z0 | stone frame: 2-wide piers, a three-course plinth with a weathered sill, a corbel course, the crenellated parapet |
| z1 | dark-oak timber frame: posts, knee braces and a beam that carries the corbelled wall head |
| z2 | rough rubble infill (cobble, andesite, stone; mossy low down) with the arrow loop |

The timber is structural, not a colour accent. It also echoes the half-timbered dark-oak and spruce buildings of
the compound.

- **Rhythm (final).**
  - Bays are 7 wide and are paired. Each pair is one wide timber frame, divided by a dark-oak post that stands on the
    plinth under a continuous beam.
  - Between the pairs, the stone piers rise one course above the parapet.
  - The 6 to 8 wide solid end masses toward the towers and gate rise as well.
  - MW86: end + 4 double frames + 3 stone piers + end. MW31: end + 1 double frame + end (both ends alike).
- **Parapet.** Merlon pairs and single crenels on a period of 3, aligned so that a crenel sits over every bay end
  and bay centre.
  - Bay merlons top out at y11; piers and end masses at y12.
  - Deck y9, so the feet are at y10, with breastwork at y10.
- **Compound side.**
  - Stone pilasters answer the stone piers.
  - Dark-oak posts answer the timber posts.
  - A dark-oak beam on braces carries a spruce-plank widening of the wall-walk behind a fence rail.
- **Dressing.** Kept small:
  - lanterns under the beams of the end bays, outside and inside;
  - a banner on the central post of each end frame;
  - barrels and a log pile at the inner foot near the ends.
- **Defence.** The wall is solid from y1 to y9. Each arrow loop is 2 high in the infill face and 1 high through the
  core, so it is not a passage.

## Draft and the two revisions (the maximum allowed)

| stage | weakest point seen in the client | change |
|---|---|---|
| draft | Every bay was a tall dark opening reaching almost to the ground: from the front, 10 identical doorways. The timber read as thin lines. The white slab frames of the loops and the end niches with banners read as windows. | (none) |
| revision 1 | Doorway look fixed. From a distance it was still a flat slab with 8 identical small windows: the timber was invisible, the silhouette flat, and the chiseled band on the end masses was the most visible feature. | Plinth raised to 3 courses, so the timber panel became a horizontal 7×4 panel at mid height. Loop frames removed. End masses made solid with a capital band. Banners moved inside the frames. |
| final (revision 2) | Remaining weakness, see below. | Bays paired into wide timber frames under one beam. Every second stone pier became a dark-oak post (outside and inside). The remaining stone piers rise above the parapet, giving a two-level rhythm. End band removed. Lanterns reduced to the end bays, banners hung on the end frames' posts. |

Both revisions changed proportion and composition. Neither one added ornament.

## Verification (all newly run on the final; pinned 26.3 server sha1 33680f5f…, client sha1 e877b6a0…)

| item | result | evidence |
|---|---|---|
| NBT size and block states | PASS | `check-result-f.json`: verify.py, 0 mismatches. MW86: 3752 cells, palette 29. MW31: 1449 cells, palette 28. No extra cells, no air cells. Strict `place template`: 0 failures. |
| block support (lanterns, banners) | PASS | 0 unsupported |
| footing under every column, solid ends z0-3 y0-8, top ≤ y12 with the ends at y12 | PASS | `footing`, `ends`, `top` |
| unintended passage: no 1×2 opening, ground to compound, feet y1-8 | PASS | `barrier`: no passage in either module |
| placement table and rotations | PASS | `place-check-f.json` live A: turns 90, 180 and 270, 15 wall placements, every cell compared: 0 failures |
| tower and gate boundaries | PASS | `check-result-f.json` `boundaries`, q=0-3: no overlap; every end abuts the expected tower or gate; exterior face outside the box; top at y12 |
| clash with the facilities | PASS | offline: 0 footprint overlaps, q=0-3. Live B (q=0 with F01-F20 and House A): 0 failures in every wall and every facility in this run. |
| slope footing (Q89 fill, test terrain) | PASS | S1, S2, S3: 0 template failures, 0 hollow cells, 0 cells changed outside; fill up to 5 |
| real client rendering | done | `screenshots-f/final`, 21 views; NBT hashes in `capture-info-f-final.json` match `out/f` |
| F06 grass defect | not fixed (out of scope) | It did not trigger in this run. The same live-B check on B2 earlier today failed one F06 `grass_block` cell (x13 z60), so it is still an open, intermittent F06 issue. |
| natural worldgen, MM-Beta integration, tower and gate joints (not built), combat use, wall-walk gameplay | UNTESTED | |

## Remaining weaknesses

- **Loops read as small windows.** The knee braces round the top corners of each infill panel, so up close the loop
  with its rubble surround reads a little like an arched window.
- **The inside face below the beam is plain stone.** It has pilasters and timber posts, but nothing else.
- **The end masses are deliberately plain.** How they meet the future towers and gatehouse is untested, because
  those modules do not exist yet.
- **Banners render as the project's standard white wall banner.** Their pattern is as in the earlier batches.

## Reproduce

```
PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/build.py f
PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/checks.py --designs f \
    --out experiments/st03-wall-redesign/check-result-f.json --server-jar server.jar --java java25 --work <dir>
PYTHONPATH=. python experiments/st03-placement-check/place_check.py --only MW86,MW31 \
    --perimeter-dir experiments/st03-wall-redesign/out/f --out experiments/st03-wall-redesign/place-check-f.json \
    --server-jar server.jar --java java25 --work <dir>
ST03_TAG=f-final PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/capture.py \
    --design f --server-jar server.jar --java java25 --client-dir client --work <dir> \
    --out experiments/st03-wall-redesign/screenshots-f/final
python experiments/st03-wall-redesign/sheet_f.py experiments/st03-wall-redesign/screenshots-f \
    experiments/st03-wall-redesign/approval-f
```
