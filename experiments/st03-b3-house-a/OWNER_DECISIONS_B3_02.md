# ST-03 B3-02 — House A porch owner decisions (2026-10-30)

Status: **OWNER-APPROVED DESIGN INTENT / NOT YET IMPLEMENTED**. These decisions supersede the unresolved porch *choice* in the B3-01 pilot, but do not approve the trial NBT or the remaining proposed architecture.

| Decision | Owner selection | Authoritative requirement |
|---|---|---|
| B3-02-Q01 | B | External projecting porch, not recessed |
| B3-02-Q02 | A | Small gabled porch roof |
| B3-02-Q03 | B | Porch projects 3 blocks from the existing house outer wall (roof overhang excluded) |
| B3-02-Q04 | B | Porch body width 5 blocks, centered on the entrance subject to geometry verification |
| B3-02-Q05 | B | Roof overhang 1 block to each side and 1 block forward |

**Nominal horizontal roof projection:** 7 blocks wide × 4 blocks outward, excluding any rear junction with the existing roof. This is a design dimension, **not** a proven available footprint or an authorization to enlarge a module.

## Constraints and unresolved implementation questions

- The existing House A module is 9×7×10 (x,z,y), with placements F11 (14,0,11) and F14 (89,0,11), as recorded in the B3-01 README. The current experimental NBT has a flush entrance and **does not implement the approved porch**.
- Determine whether the projecting porch and its eaves can be represented within the existing module and placement contracts or require a separately approved adjacent-ground/structure representation. **Do not silently alter the 25-module roster, 34-placement manifest, module dimensions, placement coordinates, rotation rules, or air policy.**
- Check actual collision/clearance with the two House A placements, nearby buildings, walkways, terrain and roof/window geometry in all four whole-structure rotations. If incompatible, report the exact conflict and request a new owner decision; do not shrink, relocate, or omit the porch automatically.
- All authored stair facing, half and shape states remain authoritative. Whole-structure rotation is allowed; neighbor-induced redesign is not.
- Roof pitch, ridge elevation, support posts, porch floor elevation, connection to the existing doorway, materials and rear roof junction remain **PROPOSED / UNAPPROVED** unless independently established by earlier authority.
- B3-01 remains **BLOCKED / OWNER APPROVAL REQUIRED**; isolated 26.3 server cell checks do not establish actual-neighbor compatibility or client VISUAL PASS. No production NBT or MMB worldgen approval follows from this record.

Next: derive a coordinate-precise porch proposal and collision report from the existing design and the two placements, then seek owner approval before implementing it as a production asset.
