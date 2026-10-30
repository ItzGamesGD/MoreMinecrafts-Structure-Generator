# SEAM-01: seam patch generator for the ST-03 modular assembly

Scope: 25 module templates, 34 placements, 112 x 112 box (ST03_PHASE_B2_V2_AUDIT_20261029.zip, SHA256 `0b025a52...ea5b`, DESIGN_PACKAGE_V2.md D6/D8). No ST-03 NBT exists, so the module contents are **synthetic** (`tools/seam01/synthetic.py`): a ring of walls, fences, bars, panes, gates, sturdy blocks and stairs along every template perimeter, so every footprint contact exercises the seam rules. Nothing here is ST-03 content, biome policy, terrain adaptation or a base-building approval.

## Method

1. `assembly.py` re-derives origin / rotation / footprint of the 34 placements for whole-structure rotation q (0..3) from the q=0 table `data/st03_placements.json`; `tests/fixtures/seam01_design_manifests.json` (the design package's own `assembly.manifest(q)` output) is the independent reference.
2. Whole: the SOURCE states of all placements are assembled in one structure frame and the connection states are computed once (PR #47 `connect`, unchanged).
3. Modules: each module is exported alone with the real converter (PR #47 connect + PR #49 stairs) and the exports are assembled in manifest order (what `place template ... strict` writes).
4. Patches = cells where (3) differs from (2). Only connecting blocks, only computed (not author-stated) properties; anything else raises `SeamError`. Order: y, z, x ascending; patches are independent strict state writes, so order cannot change the result.
5. `rotate()` turns the q=0 patches with the structure; tests require equality with patches generated directly for the rotated structure.
6. `validate()` finds missing, duplicate, conflicting, outside-the-box, wrong-block and mis-ordered patches independently of generation.
7. Application: `apply()` (pure) and `live.py` (strict `/setblock` after `place template ... strict`, i.e. after assembly). **Not implemented:** the Fabric/MoreMinecrafts-Beta worldgen hook that calls it; the patch JSON (`python -m tools.seam01 generate`) is the contract it would consume.

Stairs are never patched (STAIR-01: authored shapes win). `stair_report` lists stairs whose vanilla shape differs once the neighbouring module exists, and `reconcile_stairs` checks each is named by the `stair_boundary_review` of PR #49.

## Real Minecraft 26.3 result (vanilla server, jar sha1 33680f5f..., `live-26.3-result.json`)

Per rotation (none, clockwise_90, 180, counterclockwise_90): 34 placements placed strict in manifest order, 338 patches, 2928 non-air cells, 2129 connecting blocks, 593 stairs.

- Assembly + patches equals the whole-structure reference over the full box (112 x 24 x 112, layer by layer) and cell by cell; the game's own recompute on the patched structure changes 0 blocks.
- Patches applied in reverse order give the identical structure.
- Negative control: without patches 2 layers differ from the reference, all 338 patch cells are wrong, and the game's recompute changes ~190 blocks.
- Normal-placement oracle: the game's fixpoint (connecting blocks + stairs updating each other) equals the whole structure computed with the stair shapes the game derives, on all 2129 connecting blocks (0 mismatches).
- Python stair rule vs game: 0 mismatches over 593 stairs per rotation; 18 stairs per rotation take a different shape in the game than authored, all 18 are named by the PR #49 review.
- Patch sets are deterministic (sha256 identical across runs and between q computed directly and q rotated from q=0).

## Open boundary cases (need a design decision, not made here)

- 18 stairs per rotation would be reshaped by a normal (non-strict) neighbour update because of a stair in the next module. SEAM-01 keeps the authored shape.
- 15 connecting blocks per rotation have a connection that depends on that choice (a wall/bar/pane touching a seam stair: a corner-shaped stair is sturdier on the side face). Their patch states assume the authored stair shape (`connections_that_depend_on_a_seam_stair_shape` in the result). If the design later prefers vanilla seam stair shapes, those stairs and cells must be patched together.
- Cells next to the 112 x 112 box edge or to air=omit modules (walls) border unknown terrain; the generator treats it as air, as the converter does (`boundary_unresolved` of the whole structure: ~1900 blocks). Terrain adaptation is out of scope.
- Real module content will have stair/wall layouts this synthetic fixture does not; the generator is content-agnostic but its coverage on real NBT is not yet shown.
