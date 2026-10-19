# `sauna_1` — Public bathhouse

**State:** ORIGINAL SOURCE VERIFIED · GEOMETRY VERIFIED · DESIGN PROPOSED · VISUAL PENDING · LIVE PENDING

## Existing geometry

29×10×37; 1847 blocks; palette 42. The original has deepslate-brick/tile walls and walkways, candles, 86 stair blocks, 43 still-water blocks, three chests with `minecraft:chests/ancient_city` loot-table NBT, and no entity records. Existing bath water: basin A x=13..20,z=24..28 at y=0 (8×5=40 source water blocks); basin B x=13..15,z=6,y=4 (3 water blocks). Four bottom jigsaws use pool `minecraft:ancient_city/sculk`; one edge connector at (28,0,21) faces east_up and uses the empty pool. Preserve all five exact jigsaws and original chest NBT by default.

## Restoration concept

- **Footprint / height:** keep 29×10×37 exactly. Complete the existing public bathhouse inside the source shell; no new wings.
- **Entrance / path connection:** proposed main entry is the existing two-block-high south-edge opening around x=12..14,z=36, with a short external approach centered at x=13. Keep the approach clear of the nearby y=0 jigsaw at (18,0,33). This is a design candidate inferred from the source's open boundary cells; confirm the adjoining city path before fixing its exact width.
- **Zones:** the 8×5 lower pool at x=13..20,z=24..28 is the main immersion bath; keep its existing stairs at the west edge, add two safe steps/handholds only if floor map review finds clearance. The 3-block pool at x=13..15,z=6,y=4 is a small warm/cold plunge basin; preserve its y=4 level and give it a separate stair approach. Use the already partitioned dry rooms for entrance/changing benches, towel/locker barrels, quiet rest alcoves, and a central warm resting hall.
- **Water feasibility:** 40 source blocks form one compact 8×5 rectangle inside the existing bounds. At y=0, the full immediate perimeter around those water cells is occupied by deepslate tiles/stairs; the NBT contains no basin floor beneath y=0 and no raised edge course above y=0. This is a flush, one-block-deep bath outline whose water containment depends on the same-level ring remaining intact. The small y=4 plunge contains three water cells bounded at that layer by existing stair blocks, also without a raised lip. Keep every water and rim block unchanged. Verify after placement that fluid ticks do not escape and that the bathing entrance is usable; this remains **LIVE PENDING**.
- **Access / circulation:** use the existing dry floor corridors between the bath zones. Keep at least one 2-wide path connecting public entry, changing bench, lower bath steps, rest benches, and upper small plunge. Do not create a dead-end room or obstruct stairs/chests. Mark wet/dry floor transition with a one-block deepslate-slab strip.
- **Roof / walls:** repair missing roof panels with deepslate tile slab/block, keep low stepped roof profile below y=9. Retain existing wall partitions and openings; use polished basalt as sparse structural jambs and cyan glass only in high narrow openings.
- **Furniture / lighting:** changing benches in paired rows, 2-3 locker barrels (not replacing source chests absent approval), low resting couches/stone benches, water-side handrails, soul lanterns at corridor intersections, candles on dry ledges. Avoid placing candles above water or on flammable materials.
- **Vertical movement:** source stairs already support level changes; keep their original state/orientation. Add a short handrail where safe, after testing collisions with source stairs.

```text
Proposed circulation (plan orientation; N=z=0)
city path
   ↓ south approach x≈13
south opening z=36 → dry reception / changing → main bath steps at x=12,z=24..28
                                            ↘ dry perimeter route → small plunge (x=13..15,z=6)
Main bath exit → dry rest benches → return to reception
```

```text
Plan zoning overview (not to scale; exact source state maps are linked in README)
N
+---------------------------+
| small plunge / dry rooms  |  z=0..12
| changing + rest benches  |
|-----------+---------------|
| corridor / original rooms | z=13..23
|     access to lower bath  |
| dry steps | 8x5 MAIN POOL | z=24..28
| rest hall + dry perimeter | z=29..36
+---------------------------+
```

## Change plan / conflict

- **Keep unchanged:** all source water and same-level containment ring blocks, existing stairs and slabs, all jigsaws with complete NBT, all 3 chest blocks and loot-table NBT, existing candle states unless a safety/collision review requires relocation, full 29×10×37 bounds.
- **Remove:** no original blocks by default.
- **Replace/add:** only roof/wall gap infill and new dry-room furniture/handrails/lamps in proven empty coordinates. Do not add water until a live fluid containment test is passed.

The data proves complete same-level rims but not whether post-placement fluid ticks remain contained; the main bath has no raised lip. Layer maps in the source JSON and eventual Minecraft simulation must confirm that. The south entrance is proposed from an existing opening but its path adjacency is not established. Preserve y=0 sculk-pool connectors at their positions; new dry paths and walls must not cap or cover connector blocks. Keep the east boundary connector clear of the exterior approach.
