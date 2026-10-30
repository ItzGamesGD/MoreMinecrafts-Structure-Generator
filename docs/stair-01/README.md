# STAIR-01: explicit stair state contract (Minecraft 26.3)

Base: 61a09eebafa9beee0944eba266e7f05a9543eec5 (PR #47 and #48 integrated).

The converter and independent verifier require authors to supply `facing`, `half`, and `shape` on every stair state. Valid values are checked against the pinned 26.3 block reference: four horizontal facings, top/bottom, and straight/inner_left/inner_right/outer_left/outer_right. Invalid or omitted values fail. `waterlogged` remains eligible for the pinned default fill.

The pinned oak_stairs default is north/bottom/straight/waterlogged=false. That registry default is not proof of the correct shape in a layout. Vanilla neighbour-derived corner shape depends on nearby stairs' facing and matching half; strict template placement does not repair authored shapes. This change deliberately chooses explicit errors rather than implementing that solver. Explicit shapes are preserved even when an author intentionally chooses a shape different from normal neighbour updates. It validates state fidelity, not geometric plausibility or walkability.

Positions and facing rotate together. A pure horizontal rotation preserves half and shape, including left/right; it is not a mirror. Exported template states remain in the template frame; Minecraft performs placement rotation. Existing live.rotate_props already implements this and remains unchanged. Unit tests exercise all 40 facing/half/shape combinations at all four rotations, inverted corners and a rising spiral-shaped run. These are offline expectations; actual 26.3 server comparison is NOT RUN for this change. No mirror support is added.

`stair_boundary_review` is emitted only when a stair has a horizontal neighbour outside the template or omitted by air=omit. Each entry records template position, side and reason. It is a conservative SEAM-01 review candidate, not a proven shape defect. Explicit state is never overwritten; internal adjacent blocks are known but do not trigger inference either. Complete boundary context, combined-module shape validation, patch application and terrain neighbours belong to SEAM-01. Reports for exports without these stair candidates remain unchanged.

Design provenance: ST03_PHASE_B2_V2_AUDIT_20261029.zip SHA256 0b025a524fbbf8ffd3ad590babebe108327c79f90f603765a86d1e0d4b17ea5b; DESIGN_PACKAGE_V2.md sections 4.4, 17, 18, 19 identify explicit stair shapes and unproven tower spiral geometry. The package contains design data, not production NBT. ST-03 construction, actual traversal and full 34-placement assembly are outside this change.

Validation (offline): targeted stair tests plus exporter/connectivity/block-entity regression tests. Existing export reproduction tests compare committed bytes; no committed NBT or report was regenerated. The previous 369-test and game evidence on 7fdb8e8 is historical and is not evidence of new stair runtime validation. Broader vendor/phase tooling and real-server stair placement remain NOT RUN. CONDITIONAL GO pending real-server four-rotation state comparison and SEAM-01 review of reported candidates.

## Real-server result (Minecraft 26.3, vanilla server jar sha1 33680f5f, run on the final script)

`python -m tools.structure_export.stair_live` (committed result: `live-26.3-result.json`). Phase 1 lets the game decide every shape (non-strict `/setblock` runs `updateFromNeighbourShapes`; no solver in the converter). Phase 2 exports each fixture with explicit facing/half/shape, places it `strict` (as jigsaw worldgen does) at none/clockwise_90/180/counterclockwise_90 and compares every cell with the expected rotated state via `execute if block`; the same export is also placed without `strict`.

- Fixtures: 40-state matrix (5 shapes x 2 halves x 4 facings, isolated), 128 neighbour pairs, 128 run-end corner clusters, a rising 32-step spiral, an upside-down corbel row with returns, a hip roof with upside-down eave, and a stair run split in two templates (module seam).
- Result: strict placement matches the exported state in every cell at all four rotations (0 mismatches over all fixtures; facing rotates, half and shape are kept, left/right never swap). Server log clean.
- Strict vs normal: non-strict placement recomputes shapes. The isolated matrix therefore changes 32 of 40 cells (every non-straight shape reverts); fixtures whose authored shapes were game-derived do not change. Authored states are only guaranteed by strict placement.
- Module seam: 2 of 48 stairs have a different game shape when their module is placed alone (x=7 and x=8, z=10: inner_* alone, straight assembled). Both are listed by `stair_boundary_review` of their module. No stair outside the report depends on the other module. This supports SEAM-01 using that list as its candidate set.
- Not a result: no mismatch was found, so nothing was changed in the converter. Fixtures use a fixed set of block ids (oak, stone brick, dark oak); traversal of the spiral and walkability are not tested.
