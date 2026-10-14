# Ancient City Whole-Variant Structure Generation Task — 2026-10-14

## Correction / repository boundary

This work belongs in **MoreMinecrafts-Structure-Generator**, not MoreMinecrafts-Beta.

The earlier Beta PR #85 was created in the wrong repository and has been closed as **DO NOT MERGE**. Do not copy its Java/Fabric city-variant resolver into this repository.

This repository owns the proven structure-production workflow:

reference/concept input
→ blueprint.py
→ mcbuild VoxelGrid
→ deterministic render
→ visual inspection
→ revision
→ Sponge v3 .schem export

The existing Phase 3 Ruined Watchtower is the verified production reference for this workflow.

## Goal

Produce visual structure prototypes for the three approved **whole Ancient City variants**:

1. DEATH / REMAINS
2. NETHER-CORRUPTED
3. LIVING / PEAK

This task is about **structure generation and visual design**, not Fabric worldgen selection logic.

The Arena is already accepted as a separate independent Ancient City structure and is out of scope here.

## Critical interpretation

A whole-city variant must read as a coherent city-wide state.

Do not produce one themed room/module and call it a city variant.

Do not mix Death, Nether, and Living themes in one output.

Each prototype must preserve enough Ancient City visual language to remain recognizably derived from vanilla Ancient City architecture while changing the city-wide state.

## Source/reference handling

Before production:

- inspect the available reference images/concept material supplied for the task;
- inspect the proven Phase 3 mcbuild pipeline and artifacts;
- use actual image/reference evidence where available;
- if a required visual reference is absent, do not invent that an image was supplied: use the approved written concept as the design source and record that limitation.

Do not use external inference APIs unless explicitly authorized.

## Variant A — DEATH / REMAINS

Core question:

“How much life had to die for this much sculk to exist?”

Visual direction:

- Ancient City after catastrophic mass death;
- substantially stronger sculk infestation;
- remains, debris and destruction distributed across the scene;
- ruined civic spaces and broken architecture;
- environmental storytelling should dominate;
- still recognizably an Ancient City, not a generic bone dungeon.

Prefer Minecraft-native block storytelling rather than new gameplay systems.

## Variant B — NETHER-CORRUPTED

Visual direction:

- central Ancient City Warden-shaped landmark remains the spatial anchor;
- a Nether portal occupies the rectangular/square interior of that central landmark;
- Nether corruption radiates outward from the center;
- corruption intensity should visibly decrease with distance;
- central areas may be heavily transformed while outer areas retain more Ancient City material;
- leave room for future Nether mob population, but entity gameplay is out of scope.

The prototype must make the center→outward gradient visually legible.

## Variant C — LIVING / PEAK

Visual direction:

- Ancient City before ruin / at its inhabited peak;
- restore broken architecture rather than merely removing sculk;
- infer plausible intact forms from existing Ancient City architectural language;
- streets, civic spaces and buildings should read as maintained and inhabited;
- allow future inhabitants and friendly/protective Wardens, but do not implement AI or gameplay here.

The output should look like the same civilization at its height, not an unrelated deepslate city.

## Production strategy

Do not attempt a full Minecraft-scale Ancient City in one monolithic blueprint if that exceeds the proven pipeline.

First inspect the generator's practical bounds and choose the smallest representative city-scale composition that can honestly validate each whole-city visual language.

A representative prototype may combine multiple architectural zones/modules into one composition, but it must show enough of the city to demonstrate that the theme is city-wide.

Document any scale reduction explicitly.

## Required iteration loop

For EACH variant:

1. create iteration 1 blueprint;
2. execute it with the real vendored mcbuild DSL;
3. render multiple yaw views;
4. open and visually inspect the render;
5. record concrete strengths/weaknesses;
6. revise the blueprint at least once based on the actual render;
7. render iteration 2;
8. select a final only after visual inspection;
9. export final Sponge v3 .schem;
10. validate schematic dimensions, palette, non-empty voxel data and representative voxel round-trip.

Do not mark visual review complete merely because a PNG exists.

## Artifacts

Use separate paths:

artifacts/ancient-city-variants/death/
artifacts/ancient-city-variants/nether/
artifacts/ancient-city-variants/living/

For each variant preserve:

iteration-1/blueprint.py
iteration-1/render.png
iteration-1/structure-report.txt

iteration-2/blueprint.py
iteration-2/render.png
iteration-2/structure-report.txt

final/blueprint.py
final/render.png
final/final.schem
final/structure-report.txt

visual-review.md

Also create:

artifacts/ancient-city-variants/report.md

## Validation

Reuse the real mcbuild APIs proven by Phase 3.

Run relevant existing tests and lint/format checks.

At minimum validate:

- blueprint executes;
- VoxelGrid is populated;
- bounds/dimensions are sane;
- all intended representative materials exist;
- deterministic renderer produces non-empty images;
- final schematic is Sponge v3;
- nbtlib can load it;
- palette and dimensions match;
- representative voxels round-trip;
- no obviously detached/floating accidental geometry;
- no catastrophic clipping in rendered views.

## Scope boundary with MoreMinecrafts-Beta

This repository produces and validates structure assets.

Do NOT implement here:

- Fabric Ancient City registration;
- random worldgen selection;
- StructureStart variant state;
- Mixins into Minecraft;
- Warden AI;
- Ancient Heart changes;
- Knowledge/Research;
- Arena integration.

After visual prototypes are approved, their final schematics/blueprints can be handed off to MoreMinecrafts-Beta for actual game integration in a separate task.

## Git rules

Work only on the isolated branch created for this task.

Do not modify main directly.
Do not modify the existing Phase 3 branch.
Do not merge.
Create a Draft PR only after coherent artifacts and validation evidence exist.

## Final report

Return:

- exact base branch and base SHA;
- exact task branch HEAD;
- files changed;
- generator/runtime used;
- dimensions and block counts for each variant;
- material summaries;
- iteration changes;
- render paths;
- schematic paths;
- tests/lint/validation results;
- limitations;
- Draft PR number if created.

Answer separately for DEATH, NETHER and LIVING:

“Does this prototype visually communicate a coherent whole-city Ancient City variant rather than a single themed module?”

Only answer YES after inspecting the final render.
