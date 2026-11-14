# ST-03 B3-02 — Design completion audit (2026-10-30)

## Verdict

**DESIGN DECISIONS COMPLETE (Q01-Q10); IMPLEMENTATION READINESS: CONDITIONAL / BLOCKED pending coordinate and manifest decisions.**

Audit is **document/contract review only**. No NBT, block-cell map, schematic, generator, placement manifest, tests or client assets were modified or run by this audit. This is not a Minecraft 26.3 runtime or visual validation.

## Verified documentary inputs

- Owner choices Q01-Q10: [OWNER_DECISIONS_B3_02.md](OWNER_DECISIONS_B3_02.md).
- B3-01 pilot [README.md](README.md): House A bounding box 9×7×10 (x,z,y), door at local (4,6) on south face, F11 (14,0,11) and F14 (89,0,11), two placements, current experimental NBT has **flush door and no porch**.
- B3-01 pilot server evidence is limited to isolated House A placement under four rotations, not a joined House A + porch module.
- PR #50 SEAM-01 and PR #49 STAIR-01 are stacked dependencies; preservation of authored stair facing/half/shape remains mandatory.

## Contract / geometry review

1. **Known geometric conflict:** existing House A z domain is 0..6 and the door is at z=6, facing south. An *external* 3-block-deep porch necessarily projects beyond the existing House A z boundary. Its 1-block forward eave projects farther. Therefore it cannot be represented wholly inside the existing House A NBT without breaking the original bounds. Q10's separate-module choice addresses representation, **but not** placement/manifest authorization.
2. **Nominal width:** centered 5-block porch spans local x=2..6; 1-block lateral eaves span x=1..7. This fits the original house width x=0..8 **in x only**; the forward z projection still exceeds its bounds. These are derived *horizontal* spans, not approved full voxel coordinates. A candidate front porch body z=7..9 and front eave through z=10 assumes the first exterior row begins at z=7; this is a **candidate**, not an approved absolute placement.
3. **Height and access unresolved:** the approved floor is 1 block above *surrounding ground*, but the experimental House A floor/door starts at y=0/y=1. Without the actual surrounding terrain elevation and stair clearance, it is not possible to assert a walkable door-to-porch transition. Ridge rise 2 above eaves fixes only relative roof geometry; roof underside clearance, lantern hanging height and junction to main roof require explicit voxel plan.
4. **New accessory module registration unresolved:** Q10 approves a separate porch module concept, not a silent 26th roster module, new placement(s), a changed order, or a change to air=include/omit. Need owner-approved representation and manifest impact (potentially two porch placements tied to F11/F14) before any production export.
5. **Neighbour/terrain overlap unresolved:** neither actual adjoining ground-module cell maps nor terrain/clearing policy is proven. Check F11 and F14 separately and all four rotations; verify approach walkway and stair footprint, roof collision, roof-join, and pane/door updates.
6. **State preservation:** authored stair facing, half and shape are authority. Need precise block states for porch stairs, gable roof and trapdoors; lantern hanging support; front posts. Recompute only allowed adjacent connection properties; never silently alter authored stairs.

## Decision classification

- **PASS — choice completeness:** all ten owner choices are recorded without reinterpreting their dimensions.
- **PASS — representation intent:** separate accessory module selected; original House A geometry/placement contracts are to remain unchanged.
- **BLOCKED — coordinate-ready:** no owner-approved complete voxel layout, roof-to-house join, floor/door elevation or collision-free adjacent footprint.
- **BLOCKED — manifest-ready:** 25-module / 34-placement authority has no approved addition or representation rule for the porch.
- **NOT RUN — joined validation:** no new House A + porch runtime, four-rotation, neighbour, pathing, or client visual validation.
- **NOT AUTHORIZED — build:** no production NBT, no main merge, no ST-03 complete approval.

## Required next action (design-only)

Create a **non-implementing coordinate proposal** for the porch origin, bounding box, placement relation to F11/F14, block state and rotation mapping, roof junction, door/stair access, and terrain collision matrix. Report exact required manifest/roster change separately for owner decision. Do not build or export NBT until approved.
