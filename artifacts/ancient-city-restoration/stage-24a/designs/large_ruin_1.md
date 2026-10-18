# `large_ruin_1` — Large residential house

**State:** ORIGINAL SOURCE VERIFIED · GEOMETRY VERIFIED · DESIGN PROPOSED · VISUAL PENDING · LIVE PENDING

## Existing geometry

17×5×17 box. Only 38 blocks are present: 34 cobbled deepslate, 3 deepslate bricks, 1 jigsaw. The source is a broken, mostly y=0 footing with a few y=1/2 remnants; it contains no floor slab, enclosure, roof, furniture, or functional block. The west-facing jigsaw is at (0,0,7), `orientation=west_up`, `name=connect_structure`, `target=empty`, `pool=empty`, `joint=rollable`, `final_state=cobbled_deepslate`.

## Restoration concept

- **Footprint / height:** 17×5×17, all additions inside x=0..16, y=0..4, z=0..16. One story with a walled courtyard lightwell.
- **Silhouette:** broad low house with a stepped deepslate-brick parapet, two restrained polished-basalt doorway piers, and a small blue-glass clerestory at the courtyard edge. Keep the roof low and horizontal; avoid a tall fantasy roof.
- **Levels / supports:** existing y=0 footing remains. Fill missing floor areas at y=0 with deepslate tile/brick patches. Perimeter walls y=1..3. Roof y=4 in tile slabs/blocks with a 5×5 open-to-sky court at x=6..10,z=6..10. Existing footing irregularities become interior buttress points; support long spans with low beams at y=3.
- **Entry / path:** west threshold x=0,z=7, aligned to the original west connector. Short deepslate path apron outside the box belongs to a later city-layout task. A small vestibule at x=1..3,z=6..8 separates the entry from the family room.
- **Room layout:** west/front vestibule and shared sitting room (x=2..6,z=5..11); kitchen/storage (x=2..5,z=1..4); two sleeping alcoves (x=11..15,z=2..6 and x=11..15,z=10..14); work/eating room (x=11..15,z=7..9); courtyard in the center with covered circulation around it. Bed, table, barrels, shelves, and a modest furnace/campfire substitute only where smoke safety and version support are confirmed.
- **Internal circulation:** one level; continuous 2-block-high paths loop the court and connect each room. No ladder is needed.
- **Lighting / palette:** soul lanterns at room corners, candles on recessed polished-deepslate shelves; deepslate tiles and bricks, cracked/cobbled repair patches, sparse cyan/blue glass.

```text
Plan at y=1..3 (not to scale; N is z=0)
N / z=0
#################
#K K#       #S S#
#K  #       #S S#
#   #       #   #
####+       #   #
#   +.......+   #
#   . COURT .   #
E>..V.......+   #
#   .       .   #
#   +.......+   #
####+       #   #
#   #       #   #
#   #       #   #
#   #       #   #
#   #       #   #
#   #       #   #
#################
E = west entrance; V = vestibule; K = kitchen/store; S = sleeping; dots = open court.
```

## Change plan

- **Keep unchanged:** all original cobbled-deepslate/deepslate-brick footing blocks except the jigsaw position; exact jigsaw block, orientation and complete NBT; original overall 17×5×17 size.
- **Remove:** no original blocks by default. Only if a later collision review proves necessary, remove a non-connector footing fragment at the doorway and replace it with a threshold; this needs explicit coordinate-level review.
- **Replace:** repair gaps in footing and build enclosure/roof using deepslate bricks, tiles, stairs/slabs, polished basalt, small blue-glass details.
- **Add:** missing floor, walls, courtyard-edge beams, partitions, door, beds, food/storage furniture, lanterns/candles.

## Conflicts / review

Original y=0 fragments make a full continuous floor an addition, not restoration of a source floor. Ensure no window, wall, bed, or door occupies (0,0,7) before the jigsaw placement resolution is understood. The connector's empty target/pool may resolve to its final block rather than form an exterior passage; preserve it unchanged and test in the eventual placement pipeline. No jigsaw neighbor is guaranteed. No footprint/height expansion is proposed.

**Geometry verified:** original source only. **Design geometry / schematic:** pending. **Live placement:** pending.
