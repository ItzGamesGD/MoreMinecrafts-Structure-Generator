# ST-03 perimeter walls: three design prototypes (A, B, C)

Experiment branch `exp/st03-wall-redesign-20261106`, base `feat/st03-perimeter-walls-20261106` @ `831e125`.
These are prototypes for the owner's design choice. The batch-8 candidate NBTs
(`experiments/st03-batch8-perimeter-walls/out/`), the approved buildings and the placement table are untouched. No
NBT is swapped in until the owner approves a design.

```
PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/build.py          # out/{a,b,c}/
PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/checks.py --server-jar ... --java ... --work <dir>
PYTHONPATH=. python experiments/st03-placement-check/place_check.py ... --only MW86,MW31 \
    --perimeter-dir experiments/st03-wall-redesign/out/<d> --out experiments/st03-wall-redesign/place-check-<d>.json
PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/capture.py --design <d> ...
python experiments/st03-wall-redesign/sheet.py experiments/st03-wall-redesign/screenshots experiments/st03-wall-redesign/approval
```

## Functional contract (kept by all three) vs. the old look (not kept)

Kept: MW86 86×13×5 and MW31 31×13×5, air=omit, y=0 at grade. Placements W-N, W-E and W-W (MW86) and W-SW and W-SE
(MW31) with their rotations; local z=0 is always the outside. Both ends abut a tower square or the gate; MW31 meets the
gate with either end, so its ends are built alike. Other requirements kept:
- Q81: no continuous patrol route is required.
- Q82: stone crenellations, arrow openings, lanterns, banners and timber; no mechanics.
- Owner stone principle: natural stone mix, coherent edges, weathering in patches.
- Q89: a full footing course at y0 under every column, the below-grade fill, no flattening.
- Q90: decoration concentrated at the tower and gate ends.

Not treated as requirements: the batch-8 section (recessed face, single corbel table, 2/1 merlons), its decoration
positions and its materials layout.

## The three designs

**A: counterfort arcade.** A vertical, structural rhythm (`design_a.py`).
- Two-stage counterforts stand on the front line. Between them the curtain sits back two blocks, and each bay is
  closed by a segmental stone arch springing from chiseled capitals.
- The parapet is carried forward over the arches on a corbel table, with machicolation slots under the crenels.
- Merlons are graded: full 4-wide merlons over the counterforts, half-capped narrow ones over the bays.
- The end piers are solid masses with a pointed banner niche.
- Inside, counterforts answer the outside ones and carry a timber wall-walk widening: a dark-oak wall plate on knee
  braces, with a fence rail.
- Arrow slits are 2 high outside and 1 high in the core, so they are not a passage.

**B: hoarded wall.** Stone below, a roofed timber fighting gallery above (`design_b.py`).
- A two-step rubble talus runs along the foot.
- Projecting stone piers carry blind cross loops and their own crenellation.
- Between the piers, a covered hoarding is cantilevered on dark-oak joists and brackets. It has a plank floor with
  murder-hole hatches, a boarded front with posts and loopholes, and a low dark-oak gable roof.
- The galleries are open to the compound behind a rail; the pier tops are open platforms between galleries.

**C: scarp and casemates.** A horizontal, layered wall with a hollowed inner face (`design_c.py`).
- The section is an hourglass: a two-step rubble scarp at the foot, a recessed waist with a band of small loops, and a
  two-stage machicolation (a continuous corbel, then alternating corbels and slots).
- Pointed (gable-capped) merlons have timber shutters hinged in the crenels.
- Inside is a continuous arcade of casemate niches under dark-oak lintels with knee braces. The niches hold barrels,
  timber and hay, as decoration only; the barrels are empty. A stone wall-rail runs along the wall-walk.

## Verification

### Offline (`check-result.json`, designs → MW86/MW31)
All PASS for all 6 NBTs. Each was checked as follows:
- verify.py for air=omit: 0 mismatches, no extra cells, no air cells.
- Support for every lantern and banner: 0 unsupported.
- Footing: all L×5 columns present at y0.
- Both end columns solid over z0-3, y0-8.
- Column tops at y9 or above and at most y12, with the ends at y12.
- **Barrier:** no 1×2 player passage through the wall with feet at y1-8.
- Boundaries for q=0-3 against T-NW, T-NE, T-SE, T-SW and GATE: no overlap; both ends of every wall abut the
  expected tower or gate; the outside face is outside the box; the top is at y12.

The barrier check is new; it was confirmed to detect a passage. It finds one in the **batch-8 candidate**: the
through slit at x21, y4-5 (1×2), four blocks above ground. All three prototypes are closed.

### Server live (pinned 26.3 server, sha1 33680f5f…)
- **`check-result.json`, `server`:** strict `place template`: 0 failures in all 6 NBTs. The batch-8 slope sites with the
  Q89 fill pass for every design. Each site compares every template cell (0 failures), checks every cell between the
  ground and the template (0 hollow) and checks the terrain outside the footprint (0 changed).

  | site | wall | fill depth up to |
  |---|---|---|
  | S1 valley | MW86 | 5 |
  | S2 cross slope | MW31 | 4 |
  | S3 undulating | MW31 | 4 |

- **`place-check-<d>.json`** (`place_check.py --perimeter-dir`, conditions unchanged):
  - 0 footprint overlaps for q=0-3.
  - Live A: turns 90/180/270, 15 wall placements per design, every cell including rotated states: 0 failures for A,
    B and C.
  - Live C (test terrain): 0 hollow cells and 0 template failures for all five walls.
  - Live B (integrated q=0, all 20 facilities and House A plus 5 walls): **0 failures in every wall** for A, B and C.
  - The tool's exit status is FAIL 1 in each run, from one F06 `grass_block` cell (x33 z72, x22 z60, x13 z60): a
    different cell each run. That is the pre-existing F06 random-tick issue (grass under solid blocks turns to dirt).
    It is not caused by the walls, and F06 is unchanged.

### Real client (unmodified 26.3 client, Mesa lavapipe, in-game F2)
- 17 views per design, 51 PNGs in `screenshots/`; NBT hashes in `capture-info-<d>.json` match `out/<d>/`. Views:
  - MW86: front, oblique outside, raking outside, side/end, top aerial, oblique inside, and details of the outside,
    the inside and the wall top.
  - MW31: front, oblique outside, oblique inside.
  - The q=0 layout: whole-HQ aerial, gate from the south, NW corner, W-E from inside.
  - The S1 footing close-up.
- `approval/`: one sheet per design (`<d>_mw86`, `<d>_mw31_context`) and comparison sheets with the same camera across
  A, B and C (`compare_exterior`, `compare_interior_top`, `compare_context`).

### UNTESTED
- Natural worldgen hook-up and real seeds.
- The joints to the towers and gatehouse, which are not built.
- Any combat use of the openings.
- Gameplay of the wall-walks or galleries (Q81 does not require a route).

## Comparison (MW86 figures; MW31 is in proportion)

| | A counterfort arcade | B hoarded wall | C scarp and casemates |
|---|---|---|---|
| main idea | vertical bays: counterforts and arched recesses | timber fighting galleries over a stone talus | horizontal layers outside, casemate arcade inside |
| depth planes used outside | 3 (z0 / z1 / z2) over the whole height | 3 (talus, piers, hoarding over a z2 face) | 3 (scarp, waist, machicolation) |
| relief seen head-on | strong: arches cast deep shadow | strong: hoarding shadows, broken roof line | weak: reads mostly flat from the front |
| relief seen obliquely / raking | strong | strong | good (machicolation rhythm) |
| inside face | counterforts and timber walk edge | open gallery, rail, brackets | best: casemate niches with lintels and stores |
| silhouette | crenellated, graded merlons | roofs alternating with stone piers | pointed merlons, regular |
| timber share of blocks | 6.2 % (structural walkway) | 18.5 % (galleries, joists, roofs) | 3.0 % (lintels, braces, shutters) |
| stairs + slabs / fences, walls, trapdoors | 370 / 86 | 530 / 70 | 334 / 106 |
| distinct block states | 34 | 37 | 27 |
| lanterns / banners / barrels | 4 / 5 / 4 | 7 / 4 / 6 | 4 / 3 / 12 (+6 hay) |
| fit to Q82 (stone crenellations) | full | **partial:** only piers and ends (26 of 86 columns) carry stone crenels, the bays are timber hoardings | full |
| fit to Q90 (lanterns concentrated at ends) | yes | weaker: a lantern in every gallery | yes |
| vanilla look / fit with the approved buildings | high (stone-brick family) | high; matches the dark-oak tower roofs of Q84 | high |
| risk | longest repeated rhythm on MW86 (10 equal bays) | busiest; the timber reads as large wood surfaces from afar | outside closest to the old flat look |

### Self-evaluation

- **A: strengths.**
  - The depth is structural: every bay is a real recess under a real arch, so the wall reads in three dimensions from
    the front, the diagonal and the side.
  - A clear hierarchy: end piers, counterforts, bays, merlons.
  - The timber has a real job (the walk widening).
  - Fully within Q82 and Q90.
- **A: weaknesses.**
  - The inside face between the counterforts is plain.
  - Ten identical bays on MW86 are rhythmic but uniform.
  - The share of timber is modest.
- **B: strengths.**
  - The most characterful and the most "fortress in use".
  - Stone and timber are truly integrated: the timber is the fighting position.
  - Strong silhouette, which will echo the dark-oak tower roofs.
- **B: weaknesses.**
  - Most of the parapet length is timber, so the stone-crenellation reading of Q82 is only partly met. It needs an
    explicit owner decision.
  - The gallery fronts look busy.
  - Lanterns are not concentrated at the ends.
- **C: strengths.**
  - The best inside face (casemates with stores make the wall useful to the compound).
  - A severe, coherent layered section and an attractive machicolation rhythm in raking light.
- **C: weaknesses.**
  - Head-on the outside is the flattest of the three; the waist band is too shallow to carry the design.
  - The crenel shutters read as small wood stubs from a distance.

### Recommendation

**A, counterfort arcade.** It answers the brief's main criterion, architectural completeness and depth, most
convincingly from every viewpoint. It stays entirely within Q81, Q82, Q89 and Q90, and it keeps a clean stone-brick
language next to the approved buildings.

**B is the alternative** if the owner wants a stronger timber, garrison-in-use character and accepts timber hoardings
in place of stone crenels along most of the length (Q82 interpretation).

Nothing replaces the batch-8 candidate until the owner chooses.
