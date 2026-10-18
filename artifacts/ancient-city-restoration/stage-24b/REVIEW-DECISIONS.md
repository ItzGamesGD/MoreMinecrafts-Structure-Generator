# Stage 24-B review decisions and outstanding checks

## Owner review requested

1. **`medium_ruin_2` placement clearance:** approve the eight-block height after reviewing a placement in the actual Ancient City jigsaw generation context. X/Z remain 16×11 and the connector remains unchanged. This repository does not include the selected neighboring piece placement data, so structure-to-structure collision checking is blocked.
2. **`sauna_1` reception connection:** the source has one cracked deepslate-brick head block at `(11,2,33)` between the south reception and the preserved bath circulation. The candidate removes that block; the source's stairs, all 43 waters, complete basin rims, chests, loot NBT and jigsaws remain unchanged. Static block-state path checks now reach the main pool, plunge pool and all three chests. Please confirm the small opening is acceptable as a bathhouse doorway.
3. **`medium_pillar_1` ladder side:** the ladder is on the east side of the preserved central spine. A west-side ladder would require a second breach through the room perimeter or would be blocked by the spine; the implemented route remains away from both east-edge jigsaws. Confirm this interior orientation during visual review.

## Pending validation

- All renders are generated from NBT block states. **VISUAL PENDING:** owner review is not implied by rendering.
- **LIVE PENDING:** no Minecraft client or server was launched. The sauna basin's static boundary is present; fluid ticks are not simulated.
- **BLOCKED:** world-generation boundary collision checks require neighboring selected jigsaw pieces and placement transforms that are absent from this repository/workflow input. This is especially relevant to the explicitly raised `medium_ruin_2` roof.
- Tower ladder/stair collision, player headroom, roof support and path-to-city adjacency require a Minecraft-client/world check.

## Per-module state

| Module | Source | Candidate geometry | Render | Live/world check |
| --- | --- | --- | --- | --- |
| `large_ruin_1` | ORIGINAL SOURCE VERIFIED | GEOMETRY VERIFIED by static block checks | VISUAL PENDING | LIVE PENDING |
| `medium_ruin_1` | ORIGINAL SOURCE VERIFIED | GEOMETRY VERIFIED by static block checks | VISUAL PENDING | LIVE PENDING |
| `medium_ruin_2` | ORIGINAL SOURCE VERIFIED | GEOMETRY VERIFIED; declared Y=8 | VISUAL PENDING | BLOCKED pending placement collision context |
| `small_ruin_1` | ORIGINAL SOURCE VERIFIED | GEOMETRY VERIFIED by static block checks | VISUAL PENDING | LIVE PENDING |
| `small_ruin_2` | ORIGINAL SOURCE VERIFIED | GEOMETRY VERIFIED by static block checks | VISUAL PENDING | LIVE PENDING |
| `sauna_1` | ORIGINAL SOURCE VERIFIED | GEOMETRY VERIFIED for static circulation and fixture invariants | VISUAL PENDING | LIVE PENDING for fluids; review opening above |
| `large_pillar_1` | ORIGINAL SOURCE VERIFIED | GEOMETRY VERIFIED for ladder support, headroom and deck route | VISUAL PENDING | LIVE PENDING for collision/stability |
| `medium_pillar_1` | ORIGINAL SOURCE VERIFIED | GEOMETRY VERIFIED for retained spine, ladder and observation route | VISUAL PENDING | LIVE PENDING |
