# Stage 24-A — remaining eight Ancient City structures

**Purpose:** pinned-source inspection and restoration design review only. This package does not implement or replace structure NBTs, alter city roads/walls or the Warden landmark, or modify the thirteen previously approved building prototypes. PR #4 remains untouched.

## Status key

- **ORIGINAL SOURCE VERIFIED** — the downloaded 26.1.2 source bytes match the Git blob SHA-1 recorded below.
- **GEOMETRY VERIFIED** — dimensions, block coordinates/states, jigsaws, and original occupancy maps were parsed from those bytes.
- **DESIGN PROPOSED** — a human-readable restoration concept is documented; this is not a generated structure.
- **VISUAL PENDING** — proposed geometry has no rendered restoration preview yet.
- **LIVE PENDING** — no Minecraft-client placement or gameplay inspection has occurred.
- **BLOCKED** — the requested function conflicts with the original declared box or preserved connector constraints until an owner decision is made.

## Source provenance

Source: `InventivetalentDev/minecraft-assets`, commit [`bb6d6451fb5fff54d3930fd8bf19d81200f00e6d`](https://github.com/InventivetalentDev/minecraft-assets/tree/bb6d6451fb5fff54d3930fd8bf19d81200f00e6d/data/minecraft/structure/ancient_city/structures), directory `data/minecraft/structure/ancient_city/structures/`. SHA values are Git blob SHA-1 over the exact fetched compressed NBT bytes (`blob <length>\0<data>`), verified by `tools/inspect_remaining_ancient_nbt.py` on every run.

| Module | Role | Size X×Y×Z | Block records | Palette size | Source blob SHA-1 | Status |
|---|---|---:|---:|---:|---|---|
| `large_ruin_1` | Large residential house | 17×5×17 | 38 | 3 | `3ce04aa7cd68ab706ed7e7910cbf8453f090fb39` | ORIGINAL SOURCE VERIFIED; GEOMETRY VERIFIED; DESIGN PROPOSED |
| `medium_ruin_1` | Medium residential house A, single story | 8×5×13 | 20 | 2 | `c476ea76624d25ac483f723c55ef39695ac86aee` | ORIGINAL SOURCE VERIFIED; GEOMETRY VERIFIED; DESIGN PROPOSED |
| `medium_ruin_2` | Medium residential house B, partial second floor | 16×5×11 | 29 | 2 | `0f8b01b7aff4bd43c8e5ecc18292940ca648bf03` | ORIGINAL SOURCE VERIFIED; GEOMETRY VERIFIED; DESIGN PROPOSED; BLOCKED (vertical fit) |
| `small_ruin_1` | Small residential house A | 7×5×8 | 17 | 2 | `b1b9c2ac7c4b06a1a80e53adf4dd4fd706f2a799` | ORIGINAL SOURCE VERIFIED; GEOMETRY VERIFIED; DESIGN PROPOSED |
| `small_ruin_2` | Small residential house B | 8×5×4 | 16 | 2 | `34d14f95c92675e6d97d212baf88e84c4f506fbd` | ORIGINAL SOURCE VERIFIED; GEOMETRY VERIFIED; DESIGN PROPOSED |
| `sauna_1` | Public bathhouse | 29×10×37 | 1847 | 42 | `ef56d35f13f3acb8d62095ccc2f7e85d58d253b1` | ORIGINAL SOURCE VERIFIED; GEOMETRY VERIFIED; DESIGN PROPOSED |
| `large_pillar_1` | Large multi-level watchtower | 6×15×6 | 320 | 23 | `4d619829f48909054996945d01a77d949946e678` | ORIGINAL SOURCE VERIFIED; GEOMETRY VERIFIED; DESIGN PROPOSED |
| `medium_pillar_1` | Medium guard tower | 7×11×8 | 130 | 21 | `38ece3d8a57c9fed3f2a050ffd21b5b636121bbe` | ORIGINAL SOURCE VERIFIED; GEOMETRY VERIFIED; DESIGN PROPOSED |

Full exact material counts, all layer occupancy maps, block states, functional block coordinates, block-entity NBT, and jigsaw records are in [`source-inspection/`](source-inspection/). `occupancy_maps_x_by_z_per_y` shows empty cells as spaces and occupied cells by family; `palette_index_maps_x_by_z_per_y` uses `.` for empty and one character per palette index, as mapped by `palette_index_symbol_legend`. Together with `palette`, the compact index maps preserve every source block coordinate and exact state. Each JSON source report has a matching original-source four-direction preview. These previews render each block as a color cube: block states remain in the report, but stairs, slabs, water, and other non-cube shapes are visually approximated.

## Source findings

- All five ruins are sparse cobbled-deepslate foundation fragments with one jigsaw each, not finished shells. Their declared vertical size is only five blocks. They have no vanilla interior floors, functional blocks, entities, or bed/furniture contents.
- Ruin jigsaws all face `west_up`, lie on x=0 at y=0, use `name=minecraft:connect_structure`, `target=minecraft:empty`, `pool=minecraft:empty`, and have `joint=rollable`. Their `final_state` alternates between cobbled deepslate and structure void; see exact JSON per module.
- `sauna_1` already contains a large 8×5 water bath at y=0 (x=13..20, z=24..28), a second 3-block water basin at y=4 (x=13..15,z=6), perimeter and stair features, three ancient-city-loot chests, and five jigsaws. The large bath has a complete one-block-wide rim at y=0 on all four sides, but no raised rim above y=0 and no floor below the water layer inside the NBT box. The small basin is bounded at its water layer by existing stair blocks. Four connectors use `ancient_city/sculk`; one east-edge connector uses the empty pool. No water addition, basin enlargement, or basin wall removal is proposed.
- `large_pillar_1` is a 6×6×15 narrow tower shell with full central fill through much of its shaft, stair courses around y=1/3/11/13, a full top cap at y=14, and one east-edge connector. Access and occupied floors require interior carving.
- `medium_pillar_1` is a 7×11×8 narrow shell/spine, with a lower stair/plinth course, a mid-height central support, a high crown, a skull, and two adjacent east-edge connectors. The room, safe access, and upper deck need selective infill/carving.
- Every source NBT has zero entity records. Block-entity NBT appears only on original jigsaw/chest/skull blocks; exact details are listed in source JSON.

## Geometry and render evidence

| Module | Original source render | Exact per-layer maps and counts |
|---|---|---|
| `large_ruin_1` | [four views](source-inspection/large_ruin_1/original-four-view.png) | [source JSON](source-inspection/large_ruin_1/source.json) |
| `medium_ruin_1` | [four views](source-inspection/medium_ruin_1/original-four-view.png) | [source JSON](source-inspection/medium_ruin_1/source.json) |
| `medium_ruin_2` | [four views](source-inspection/medium_ruin_2/original-four-view.png) | [source JSON](source-inspection/medium_ruin_2/source.json) |
| `small_ruin_1` | [four views](source-inspection/small_ruin_1/original-four-view.png) | [source JSON](source-inspection/small_ruin_1/source.json) |
| `small_ruin_2` | [four views](source-inspection/small_ruin_2/original-four-view.png) | [source JSON](source-inspection/small_ruin_2/source.json) |
| `sauna_1` | [four views](source-inspection/sauna_1/original-four-view.png) | [source JSON](source-inspection/sauna_1/source.json) |
| `large_pillar_1` | [four views](source-inspection/large_pillar_1/original-four-view.png) | [source JSON](source-inspection/large_pillar_1/source.json) |
| `medium_pillar_1` | [four views](source-inspection/medium_pillar_1/original-four-view.png) | [source JSON](source-inspection/medium_pillar_1/source.json) |

## Proposed versus original

| Structure | Original situation | Restoration concept | Size / conflict result |
|---|---|---|---|
| Large ruin | Broad incomplete foundation; no usable room | Enclosed single-story courtyard home with lightwell and separated domestic rooms | Fits 17×5×17; roof and walls remain in original box |
| Medium ruin A | Long, narrow partial foundation | Linear single-story household with living room, sleep alcove, storage niche | Fits 8×5×13 |
| Medium ruin B | Broad but shallow incomplete foundation | Split-level home with a partial second floor as requested | **BLOCKED:** 5-block Y box cannot fit safe floor, two usable clearances, stair, and roof. Owner must choose expanded height (suggested 8) or revised one-story role |
| Small ruin A | Irregular 7×8 broken footing | One-room cottage with offset sleeping alcove and hearth | Fits 7×5×8 |
| Small ruin B | Very narrow 8×4 footing | Compact linear bunkhouse with built-in bunks, table, and storage | Fits 8×5×4 but has very limited occupancy; one-room plan only |
| Sauna | Built bathing complex with two water features and rest rooms | Repair/complete public bath with bathing, changing, and resting zones | Fits 29×10×37; static containment is plausible at the same-level rims, fluid tick test pending |
| Large pillar | 6×6 tall solid-centered shell | Three compact interior levels, ladder spine, accessible observation deck | Fits 6×15×6 after selective shaft/core removal and top-cap opening |
| Medium pillar | Small shell with center support and exposed connectors | Two-level guard post with internal ladder and parapet platform | Fits 7×11×8 after infill and core adjustments |

### Boundary, jigsaw, and connectivity report

- Ruin entrance concept is on the west face (x=0) centered on the original west-facing connector. Keep the jigsaw block and its NBT byte-for-byte; design a doorway around its resolved final-state opening only if the structure placement engine behavior is confirmed. Current connector `target=empty` and `pool=empty` mean no adjoining room is promised by the connector itself. Connect the threshold to the existing path with a short approach outside this module, subject to world-layout review; that path connection is not included in this structure package.
- `sauna_1` jigsaw connectors at (5,0,26), (8,0,12), (18,0,33), and (21,0,9) are y=0 connectors using the sculk pool; preserve their position, state, and metadata and keep new routes clear. Preserve the fifth connector at (28,0,21), orientation east_up. Exact metadata is in the JSON source report.
- `large_pillar_1` connector at (5,0,2) and `medium_pillar_1` connectors at (6,0,3) and (6,0,4) are on the east boundary. Keep a full connector-width clear on the east side and do not use those positions for a new entrance or fixed furniture.
- Module-local plans do not prove world-level path adjacency or neighbor separation. Actual placed coordinates, rotations, terrain cuts, and path links remain **LIVE PENDING**.

## Owner decisions required

1. **Medium ruin B:** authorize a vertical-only height increase from Y=5 to Y=8 for a true partial upper story, while keeping X/Z 16×11 and the west jigsaw fixed; or revise it to a one-story split-level house. No NBT has been enlarged.
2. **Ruin connectors:** confirm the existing `target=empty` / `pool=empty` connectors should stay byte-for-byte and that the intended path entrance is resolved in the worldgen/paste pipeline as expected.
3. **Tower cores:** approve selective removal of interior deepslate infill and part of the large tower cap to form passable stairs/ladders and a walkable observation deck. Retain perimeter supports and jigsaw metadata.
4. **Sauna loot:** preserve the three existing ancient-city chest positions and loot-table NBT, or approve converting them to ordinary public-bathhouse storage during a later implementation review.

## Validation and limits

The read-only extractor verifies all eight source Git blob SHA-1 hashes and parses exact size, block palette, coordinates, states, all y-layer occupancy maps, jigsaws and block-entity data. It also renders four yaw views from the source occupancy. The proposed plans are human-readable spatial concepts, not geometry-verified restoration schematics: proposals are **VISUAL PENDING**. No Minecraft client was launched and no live placement was tested (**LIVE PENDING**). No structures or world generation were changed.
