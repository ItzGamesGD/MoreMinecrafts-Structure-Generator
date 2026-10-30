# ST-03 B3-02 — House A porch owner decisions (2026-10-30)

Status: **OWNER-APPROVED Q01-Q10 DESIGN INTENT / NOT YET IMPLEMENTED**. These decisions supersede the unresolved porch *choice* in the B3-01 pilot, but do not approve the trial NBT or the remaining proposed architecture.

| Decision | Owner selection | Authoritative requirement |
|---|---|---|
| B3-02-Q01 | B | External projecting porch, not recessed |
| B3-02-Q02 | A | Small gabled porch roof |
| B3-02-Q03 | B | Porch projects 3 blocks from the existing house outer wall (roof overhang excluded) |
| B3-02-Q04 | B | Porch body width 5 blocks, centered on the entrance subject to geometry verification |
| B3-02-Q05 | B | Roof overhang 1 block to each side and 1 block forward |
| B3-02-Q06 | B | Small gable ridge rises 2 blocks above eaves (relative elevation; absolute Y unresolved) |
| B3-02-Q07 | B | Two symmetric front support posts; exact coordinates and height unresolved |
| B3-02-Q08 | B | Porch floor raised 1 block relative to surrounding ground, with central entrance stair; must reconcile with existing door threshold |
| B3-02-Q09 | B | Balanced decor: dark-oak posts and plank floor, stone-brick entrance stairs, trapdoor accents at post tops, centrally suspended lantern; final block states and mounting clearance unresolved |
| B3-02-Q10 | B | Porch as separate accessory NBT/module attached to House A, preserving the existing House A module contract; any new placement/roster change requires separate approval |

**Nominal horizontal roof projection:** 7 blocks wide × 4 blocks outward, excluding any rear junction with the existing roof. This is a design dimension, **not** a proven available footprint or an authorization to enlarge a module.

## Constraints and unresolved implementation questions

- The existing House A module is 9×7×10 (x,z,y), with placements F11 (14,0,11) and F14 (89,0,11), as recorded in the B3-01 README. The current experimental NBT has a flush entrance and **does not implement the approved porch**.
- Determine whether the projecting porch and its eaves can be represented within the existing module and placement contracts or require a separately approved adjacent-ground/structure representation. **Do not silently alter the 25-module roster, 34-placement manifest, module dimensions, placement coordinates, rotation rules, or air policy.**
- Check actual collision/clearance with the two House A placements, nearby buildings, walkways, terrain and roof/window geometry in all four whole-structure rotations. If incompatible, report the exact conflict and request a new owner decision; do not shrink, relocate, or omit the porch automatically.
- All authored stair facing, half and shape states remain authoritative. Whole-structure rotation is allowed; neighbor-induced redesign is not.
- Relative roof rise, post count, relative porch floor height, entrance stair and material/decor concept are **APPROVED** by Q06-Q09. Exact absolute elevations, porch module bounding box/origin, coordinates, orientation, roof geometry and rear roof junction, floor-to-door access, lantern suspension and trapdoor block states remain **UNRESOLVED**. Q10 approves the separate-module approach but **does not authorize** increasing the 25-module / 34-placement manifest without a further decision.
- B3-01 remains **BLOCKED / OWNER APPROVAL REQUIRED**; isolated 26.3 server cell checks do not establish actual-neighbor compatibility or client VISUAL PASS. No production NBT or MMB worldgen approval follows from this record.

Next: derive a coordinate-precise separate-porch-module proposal and collision report from the existing design and the two placements, then seek owner approval for any manifest/schema changes before implementing it as a production asset.
