# ST-03 perimeter wall: representative segment (design study, owner approval pending)

This branch, `exp/st03-wall-segment-20261106`, is based on `exp/st03-wall-final-20261106` @ `a57768c`. It holds a
new design for one repeatable wall segment, not a full wall.

The following are untouched:
- MW86 / MW31;
- design F and its history;
- A, B, C and B2;
- the approved NBTs;
- the placement table and the ledger.

The design does not continue A, B, C, B2 or F.

| file | |
|---|---|
| `segment.py` | generator. `out/st03_wall_segment.nbt` is the segment; `out/st03_wall_segment_run5.nbt` is 5 repeats, for judging repetition only |
| `out/v1/`, `out/v2/` | earlier stages |
| `check.py` → `check-result.json` | minimal checks |
| `capture.py` | real 26.3 client capture (same cameras and noon light for every stage) |
| `screenshots/{v1,v2,v3}/` | raw F2 screenshots; v3 is the final candidate |
| `sheet.py` → `review/` | review sheets: `evolution_*` (v1 / v2 / v3) and `final_*` |

## Size

**15 × 13 × 5** (x × y × z): buttress (3) + bay (9) + buttress (3).
- Repeats share a buttress, so the **repeat period is 12**.
- The section is the MW86 / MW31 contract:
  - 13 high, y0 at grade, top at y12;
  - 5 deep;
  - local z0 is the outside;
  - air is omitted;
  - a full footing at y0.

## Design: a buttressed curtain with a timber-framed fighting gallery

From the ground up:
1. **Talus.** A rubble foot in two steps, at z0 and z1.
2. **Curtain.** A plain stone-brick curtain at z2, solid and heavy.
3. **Fighting gallery.** At y7-8 the gallery is cut two blocks deep into the wall head, between the buttresses and
   behind the stone line. Its dark-oak frame:
   - Y-posts on a corbelled stone sill;
   - a breastwork rail between the posts;
   - a beam whose ends rest on knee braces against the buttresses.

   This frame carries the wall-walk and the parapet. The timber is structural and sits in the stone's shadow, not
   on its face.
4. **Parapet.** Corbelled out to z0. The 3-wide merlons have crenels over the bay ends and centre.
5. **Buttresses.** Two depths. Each is set back by a sloped weathering at mid height, then carried on a corbel into
   a head with a pitched cap that stands one course above the battlement.

**Inside.** Stone pilasters answer the buttresses. The same Y-posts carry a beam and a plank widening of the
wall-walk behind a fence: the outer and inner timber frames line up. There is a lantern in the gallery and one
under the inner beam.

**Difference from F.**
- F put large brown timber panels into a stone frame on the face of the wall, at mid height, in every bay.
- Here the lower wall is solid stone. The timber is a load-bearing gallery recessed into the wall head under the
  parapet.
- The buttresses rise above the battlement, so the silhouette and the shadow band read from a distance.

## Stages (same cameras)

| stage | biggest weakness seen in the client | change |
|---|---|---|
| v1 | Corbelled parapet with machicolation brackets: strong stone mass, but from outside the timber was almost invisible (two joist ends), and a cross loop on a flat curtain looked decorative. | (none) |
| v2 | The timber frame read well. A rubble repair patch was a blotch on the curtain, and from far the gallery openings risked reading as a row of dark holes. | The machicolations and the cross loop were replaced by the recessed timber-framed fighting gallery. |
| v3 (final candidate) | See the remaining weaknesses below. | Curtain cleaned to dressed stone. A dark-oak breastwork rail was added to the gallery, so it reads as a manned gallery, not as openings. |

## Minimal verification (newly run on v3; pinned 26.3 server sha1 33680f5f…, client sha1 e877b6a0…)

| item | result |
|---|---|
| NBT valid, 26.3 block states, cell by cell (segment 678 cells, run5 2726 cells) | PASS: 0 mismatches, no extra or air cells |
| strict `place template` on the server, every cell compared | PASS: 0 failures (segment and run5) |
| section compatible with MW86 / MW31: 13 high, 5 deep, footing at y0, nothing above y12 | PASS |
| unintended passage: 1×2, ground to compound, feet y1-8 | PASS: none (segment and run5) |
| block support (lanterns, banner) | PASS |
| wall-walk and parapet continuity: floor y9 and headroom y10-11 at z2-3 in every column, parapet z0 y10, rail z4 y10 | PASS |
| repetition: run5 has the same structure as the segment in each 12-block period | PASS: 0 structural differences |
| real client rendering | done: 12 views per stage; v3 NBT hashes match `capture-info-v3.json` |
| rotations, terrain and slopes, facility clashes, tower and gate joints, worldgen, combat use | UNTESTED (deferred to the MW86 / MW31 expansion) |

## Remaining aesthetic weaknesses

- **Close views of a single segment.** Alone, buttress + bay + buttress reads a little like a box. Most of the
  quality comes from repetition.
- **The lower curtain is a plain field.** It is deliberately solid, but it is the least articulated part.
- **The gallery openings.** They are dark and regular; from very far they still lean toward a row of openings.

## Expected issues when expanding to MW86 / MW31

- **Length.** Neither length fits the period: 86 − 3 = 83 and 31 − 3 = 28 are not multiples of 12. Options: vary
  the bay widths, or use wider end masses.
  - MW86: 7 bays of 9 would be 87 long, so one bay must be 8 wide.
  - MW31: two bays of 9 give 27, so 4 blocks are left over. Use wider bays (11) or end masses.
- **Module ends.** Segment ends fall on a buttress centre, whose upper stage is set back (z0 open at y7-8). The
  module ends toward the towers and gate need a full-section abutment pier, as the existing wall contract requires.
  The open gallery must also be closed there.
- **Rotations, slopes, facilities, joints.** The q=1-3 rotations, the Q89 slope footing, facility clearances and the
  tower and gate joints must all be re-run on the expanded modules.
