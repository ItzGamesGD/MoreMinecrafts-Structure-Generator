# Stage 24-B — Eight Ancient City restoration candidates

Implementation baseline: `049c791ad8e7255d15c30f66774f427a343522e5` (Stage 24-A design package, Draft PR #8 head). Source modules are pinned to `InventivetalentDev/minecraft-assets@bb6d6451fb5fff54d3930fd8bf19d81200f00e6d`. `baseline.json` records each Git blob SHA-1, original dimensions, palette counts, foundation blocks, jigsaws and block entities. The baseline checker verifies the approved commit is an ancestor and re-hashes all eight remote source NBTs.

Each module directory contains `restored.nbt`, a block-only `.schem` preview, exact coordinate-level `block-changes.json`, machine-readable `validation.json`, four-direction source/restored renders, cutaway, entrance close-up, and floor plans for each accessible level. The sauna includes basin and preserved loot-chest close-ups. Use native NBT as the candidate: the schematic does not carry jigsaw or block-entity metadata.

## Module status

| Module | Result | Geometry evidence | Pending |
| --- | --- | --- | --- |
| `large_ruin_1` | Broad one-story courtyard home | Entry-to-bed route, room clearance and open courtyard checks | Visual and Minecraft-client review |
| `medium_ruin_1` | Compact one-story longhouse | Entry-to-bed route, usable workstation/storage and shell checks | Visual and Minecraft-client review |
| `medium_ruin_2` | Partial two-story home; declared Y=8 | Real stair route, upper floor, bed and two-block headroom checks | Neighbor-placement collision review is blocked until jigsaw placement context is available |
| `small_ruin_1` | Small complete cottage | Entry-to-bed route, screened sleeping alcove and shell checks | Visual and Minecraft-client review |
| `small_ruin_2` | Micro home with one bed and clear entry lane | Entry-to-bed route and accessible storage checks | Visual and Minecraft-client review |
| `sauna_1` | Public bathing, plunge, changing and resting areas | 43 water cells, all basin rims, 86 stairs, 3 exact loot NBTs, 5 jigsaws, paths to both pools and all chests | Water tick behavior and owner review of one circulation opening |
| `large_pillar_1` | 6×6, 15-high multi-level watchtower | Supported continuous ladder, three landings, deck/headroom route | Visual and player-collision/stability review |
| `medium_pillar_1` | 7×8, 11-high guard/watchtower | Retained central spine and skull, supported ladder, lower-to-upper route | Visual and Minecraft-client review |

Only `medium_ruin_2` changes dimensions: X/Z stay 16×11 and Y becomes 8 as explicitly approved. Every other module keeps its original declared bounds. Original connectors and complete jigsaw NBT are preserved in every candidate.

## Review limitations

- Static renders are generated from the NBT palette; **VISUAL PENDING** means owner review has not happened.
- No Minecraft client or server was launched. **LIVE PENDING**: player collision, ladder/stair handling, city-path adjacency and the sauna's fluid tick behavior.
- **BLOCKED:** the repository does not include the neighboring jigsaw selections and placement transforms needed to certify world-generation overlap. This is particularly relevant to the increased `medium_ruin_2` height.
- The bathhouse candidate removes cracked deepslate brick at `(11,2,33)` to open the existing reception-to-bath route. The full water rims, source stairs, loot chests and jigsaws remain unchanged. See [REVIEW-DECISIONS.md](REVIEW-DECISIONS.md).
- The medium tower ladder uses the east side of its preserved spine so the lower entrance connects to the upper deck without crossing either east-edge connector. See [REVIEW-DECISIONS.md](REVIEW-DECISIONS.md).
- This branch does not depend on or copy changes from Draft PR #4. It does not alter PR #4, the Warden landmark, roads, city walls or previously approved prototypes.

Stage 24-A design sheets and original layer maps remain in `../stage-24a/`. Implementation scripts and tests live under `tools/` and `tests/`.
