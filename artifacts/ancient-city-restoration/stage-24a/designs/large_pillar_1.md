# `large_pillar_1` — Large multi-level watchtower

**State:** ORIGINAL SOURCE VERIFIED · GEOMETRY VERIFIED · DESIGN PROPOSED · VISUAL PENDING · LIVE PENDING

## Existing geometry

6×15×6, 320 records; 135 deepslate, 84 polished deepslate, 64 deepslate tile stairs, 20 tiles, 16 chiseled deepslate, one jigsaw. Original outer stair courses at y=1 and y=13, inner stair frame y=3 and y=11, mostly solid 4×4 center y=2..10, solid 6×6 top cap y=14. One east-edge connector at (5,0,2), `east_up`, target/pool empty, rollable, final state structure_void. No original ladder, interior door, or functional room.

## Restoration concept

- **Footprint / height:** retain 6×15×6. Keep it a narrow, vertical watchtower, not a broad fantasy keep.
- **Access:** ground entry on west face x=0,z=2..3, selected away from the east connector. Cut a 1-wide ground opening through the existing wall/fill only after coordinate collision review. Internal ladder against west inner face (x=1) connects compact landings around y=2,7,11. Do not rely on the east connector as an entrance.
- **Interior / floors:** hollow a 2×2 vertical shaft x=2..3,z=2..3 through the central fill y=2..10. Add small supported platforms at y=2,7,11, with a ladder opening at each level. Each interior occupies only a 2×2 shaft; this is tight but navigable. An alternate 3×3 carve yields more usable platforms but weakens remaining 1-block support ring and requires structural review.
- **Observation deck:** open a 2×2 aperture in the center of the y=14 cap and preserve the outer 1-block parapet ring at y=14; use the existing y=13 stair course as the edge walk and add a single-height safety rail only in safe gaps. Deck access from y=11 via ladder.
- **Roof / silhouette:** keep original tiered stair courses; the parapet opens to the sky rather than becoming a roof. Add only one small soul lantern below the observation lip.
- **Materials / lighting:** retain polished deepslate and chiseled accents. New ladder and trapdoors in dark wood/iron, with no ornament beyond existing stair and tile trim. Use soul lanterns at y=2 and y=7 landings.

```text
Top-down schematic (y=2,7,11; N=z=0; 6x6)
######
#....#
#.LL.#
#.LL.#
#....#
######
Outer ring = original support; LL=2x2 ladder/landing shaft. Connector lies at east edge (x=5,z=2).
```

## Change plan / conflict

Keep original perimeter and stair courses, polished/chiseled material accents, connector block and full NBT, and original 6×15×6 bounds. Remove only the central 2×2 fill in y=2..10 and center cap cells y=14 (exact coordinates to be locked in later implementation); retain a continuous 1-block support ring. Add ladders, compact landings, trapdoors, rails and soul lanterns. The single-block entry breach needs a coordinate-level support check. The shaft is intentionally cramped; test player collision and ladder transitions in a live client. No expansion proposed.
