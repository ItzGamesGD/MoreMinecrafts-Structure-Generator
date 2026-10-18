# SG-02 — Central cavern expansion and multi-level room interfaces

SG-02 grows the SG-01 central cavern (draft PR #5) without redesigning it, replaces the stone-brick
stairs, widens the first elevated platforms to four usable lanes, adds plaza-edge rails, and defines
the connection interfaces SG-03 fills with rooms. The SG-01 export under `exports/sg-01/` is untouched
and remains the comparison baseline.

Generator: `examples/forgotten_kingdom/build_sg02.py` (`sg02_cavern.py`, `sg02_stubs.py`,
`kingdom_common.py`). Output: `exports/sg-02/forgotten-underground-kingdom/datapack/`
(same `moreminecrafts:forgotten_kingdom/central_cavern/*` resource ids as SG-01, so it is a drop-in
replacement — load **one** of the two packs, not both).

## What changed relative to SG-01

| Aspect | SG-01 | SG-02 |
|---|---|---|
| Envelope | 41×17×41 | **47×17×47** (+3 on every side; the exporter's 48-block template limit makes 47 the largest symmetric envelope) |
| Plaza, stairs, pillars, roof pattern, lights | — | identical geometry, translated by (+3, 0, +3); a regression test compares every SG-01 cell in the plaza box |
| Stairs | `stone_brick_stairs` | `deepslate_brick_stairs`, same routes/orientation/`shape=straight`/`half=bottom` |
| Platform | 3-wide ring, rail on the outer edge → 2 usable lanes | 5-wide deck (d=5..9), rail on the plaza-facing edge → **4 clear lanes** (d=5..8) |
| Rails | outer-edge `deepslate_brick_wall` | `deepslate_brick_wall` on the exposed plaza edge, open at all four stair mouths, with vanilla-consistent connection states |
| Outer envelope | thin shell, 3-wide empty bay behind the ring | 5-thick gallery-back masonry (d=0..4) at deck level and above, open undercroft (piers, fascia beam) below, extended roof |
| Room interfaces | none | 8 lower + 8 upper Jigsaw connectors (below) |

Side-local coordinates: `u` runs along a side (0..46), `d` is the depth inward from the outer shell
plane (`d=0`). All four sides are rotations of one design.

## Platform and stairs

* Stairs are unchanged relative to the plaza: step *i* (0..6) is at `d = 16 − i`, `y = i + 1`, `u = 22..24`.
  Their inner edge did not move; the plaza interior (SG-01 x/z 7..33, translated 10..36) is unchanged.
* The deck is at `y = 8`, `d = 5..9`. The rail stands on `d = 9`, leaving **`d = 5..8` (four lanes)** with two
  blocks of headroom. Pillars, rails and the vestibule stairs are not counted as lane width.
* Under the deck the undercroft stays open (`y = 1..7`), carried by a continuous fascia beam at `d = 9` and
  piers at `u = 17, 29`. Lower doors and the tunnel doors remain walkable at plaza level.

## Connection interfaces (chamber-local coordinates, rotation `none`)

Jigsaw blocks sit on the shell plane (`d = 0`), orientation `<side>_up`, joint `aligned`, `final_state = minecraft:air`.

| Kind | Position (north / east / south / west sides) | Door | Child pool | Child entry name |
|---|---|---|---|---|
| Tunnel (SG-01) | (23,1,0) / (46,1,23) / (23,1,46) / (0,1,23) | 3×4 | `…/tunnels/<side>` | `tunnel_in_<side>` |
| Lower rooms | (8,1,0),(38,1,0) / (46,1,8),(46,1,38) / (8,1,46),(38,1,46) / (0,1,8),(0,1,38) | 3×4 at plaza level | `…/central_cavern/lower_rooms` | `forgotten_kingdom/lower_room_entry` |
| Upper rooms | (11,10,0),(35,10,0) / (46,10,11),(46,10,35) / (11,10,46),(35,10,46) / (0,10,11),(0,10,35) | 5×5, floor at y=9 | `…/central_cavern/upper_rooms` | `forgotten_kingdom/upper_room_entry` |

* **Lower slots (`u = 8, 38`)** open from the undercroft beneath/behind the first platform. They were moved
  from the first draft (`u = 11, 35`) after native screenshots showed the SG-01 pillar footing (x/z 11..15)
  standing in the line of sight between the plaza and the door; a regression test now checks every lower-door
  column is free of pillar footings.
* **Upper slots (`u = 11, 35`)** open from the elevated lanes through a 5-block-deep vestibule cut through the
  gallery-back masonry. The vestibule floor is `y = 9`; a one-block `deepslate_brick_stairs` sill at `d = 4`
  joins it to the `y = 8` lane, so the sill is a step, not a jump. Rails never cross a vestibule mouth.
* The child's connector is placed in the cell directly in front of the parent's connector (vanilla rule), so
  child floors are `y = 0` (lower) and `y = 9` (upper) in chamber coordinates.

### Reserved volumes (why vanilla Jigsaw collision never has to be relaxed)

Children are authored with their entry centred on their south edge, extending away from the chamber.
Maximum footprints (lateral × height × depth): lower `17 × 9 × 24`, upper `23 × 17 × 32`.

* Lateral extents stay inside the chamber's own 0..46 span, so rooms on adjacent sides can never meet at a corner,
  and the two slots on one side (`u` 8/38 or 11/35) are separated by more than the room width.
* Lower rooms occupy `y = 0..8`; upper rooms start at `y = 9`, directly above the lower band and above the
  tunnels' top layer (tunnels are 9 tall). Upper interiors have 15 blocks of clearance (two to three levels),
  lower interiors 7; the lower roof slab sits directly under the upper floor slab.
* The tests place a maximum-size stub at all 16 slots and check every pair of bounding boxes is disjoint.
  `max_distance_from_center` was raised to 112 so the whole assembly fits Jigsaw's placement box.

SG-02 deliberately fills the pools with two **reserved-volume stubs** (empty deepslate shells at the maximum
footprint, entry connector only) instead of final rooms. SG-03 replaces them.

## Verification

* `python3 -m unittest discover -s tests` — exporter, Jigsaw seam, SG-01 baseline and the 27 SG-02 regression tests
  (geometry from NBT: envelope, SG-01 plaza regression, stair states, 4-lane width, rails, connector table,
  reserved-volume disjointness, sightlines, walkability, determinism).
* `validation/minecraft-visual/run_runtime.py` — real Minecraft 26.3 server: every template placed with
  `/place template` and compared cell-for-cell (air included) with saved region data; the Jigsaw structure placed
  with `/place structure`, each assembly recovered from the world, and every non-air block explained by exactly one
  piece with no overlaps, all connectors filled, and a conservative walk model proving the plaza reaches every
  deck lane cell and every connector.
* `validation/minecraft-visual/capture_client.py` — native `Screenshot.grab` frames from the real client.
  Committed copies of a local run are in `exports/sg-02/forgotten-underground-kingdom/evidence/local-runtime/`.

## Known limitations

* `/place structure` does not persist structure starts, so piece placement is recovered from block data; natural
  world generation in varied terrain and cave intersections is not exercised.
* The walk model is conservative (stairs and walls are treated as full blocks) and is not a substitute for play-testing.
* Screenshots are from a flat void-above-ground test world; terrain intersection and fog are not represented.
