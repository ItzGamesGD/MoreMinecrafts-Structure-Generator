# Mob Model Generation Research

Status: research / capability-probe candidate
Recorded: 2026-10-06

This note records the proposed MoreMinecrafts mob-model production pipeline alongside the existing structure-generator experiments. It does not change the structure-generation pipeline.

## Goal

Reduce manual Blockbench modeling and custom animation work while preserving editable Minecraft-native models.

Preferred architecture:

AI / Work
-> concept sheet
-> constrained cuboid specification
-> deterministic compiler
-> editable .bbmodel
-> render / visual inspection
-> revise
-> Fabric integration

This intentionally mirrors the successful structure workflow:

Work
-> mcbuild blueprint
-> deterministic renderer
-> visual inspection
-> revision
-> schematic export

## Model classes

### M0 - Vanilla Reskin
- Reuse vanilla geometry, skeleton, and animations.
- Replace texture only.

### M1 - Vanilla Morph
- Reuse vanilla skeleton and animations.
- Change ModelPart scale, position, and/or proportions.
- Replace texture.

### M2 - Vanilla Skeleton + New Geometry
Primary target for original MoreMinecrafts mobs.

- Select the closest vanilla animation skeleton (Humanoid, Warden, Ravager/Hoglin, Wolf, Spider, Phantom/Allay, fish, etc.).
- Preserve the required bone hierarchy/pivots used by the vanilla animation.
- Generate or rebuild the visible cuboid geometry around those bones.
- Child decorations such as horns, armor plates, spikes, masks, jaws, mushrooms, etc. inherit parent motion and therefore do not require independent animation.
- Generate a new texture atlas.
- Result should look like an original mob while continuing to use vanilla motion.

Important constraint:
The model generator should not freely invent a skeleton for M2. The target vanilla skeleton is an input constraint. AI generates geometry under that hierarchy.

### M3 - Full Custom
- New skeleton.
- New geometry.
- Custom animation only where required.
- Reserve for mobs whose silhouette or locomotion cannot reasonably map to a vanilla skeleton.

## Candidate: img2blockbench

Repository:
https://github.com/orca-gamedev/img2blockbench

Why it is interesting:
- Designed around Minecraft/Blockbench-style cuboid reconstruction rather than treating triangle mesh as the final Minecraft entity model.
- Can produce editable .bbmodel output.
- Supports image-driven/direct cuboid workflows as well as mesh-assisted reconstruction.
- Uses a structured/intermediate representation plus deterministic generation, which fits the existing Work -> compiler -> render -> review approach.

Proposed MoreMinecrafts adaptation:

concept image
-> AI visual analysis
-> TARGET_VANILLA_SKELETON constraint
-> cuboid specification
-> validation/compiler
-> .bbmodel
-> render
-> Work visual review
-> revise cuboid spec
-> final .bbmodel
-> Fabric model implementation

The most valuable capability to test is therefore not unrestricted text-to-3D generation. It is constrained M2 generation: create original geometry while preserving a specified vanilla skeleton and animation compatibility.

## Secondary candidates

### minecraft-ai-generate-bbmodel
Repository:
https://github.com/Logeaddd/minecraft-ai-generate-bbmodel

Potentially useful because it also follows the structured cuboid-spec -> deterministic .bbmodel pattern. Needs capability validation before adoption.

### Meshy / Tripo
Treat as optional shape-reference generators, not the preferred final model source.

Their general-purpose output is triangle-mesh oriented. If used, the likely route is:

concept
-> generic 3D mesh
-> cuboid reconstruction
-> constrained skeleton assignment
-> .bbmodel

This is less desirable than direct Minecraft-native cuboid generation when the reference image already has clear block/cuboid anatomy.

## Proposed capability probe

Use one original mob and one fixed vanilla skeleton, preferably Warden or Humanoid.

Acceptance target:

1. Start from a Minecraft-style concept/reference image.
2. Fix the target vanilla bone hierarchy before generation.
3. Generate new cuboid geometry without replacing that hierarchy.
4. Produce an editable .bbmodel.
5. Render the result headlessly or through a deterministic preview path.
6. Let Work visually inspect the render.
7. Revise at least once from visual feedback.
8. Preserve vanilla-animation-compatible pivots/bones.
9. Record whether texture generation/UV requires manual cleanup.
10. Only after this probe passes, consider integration into the main MoreMinecrafts repository.

## Current decision

Default new-mob production priority:

M0 -> M1 -> M2 -> M3

Escalate only when the lower class cannot express the required silhouette or movement.

The intended outcome is that most ordinary mobs remain M0-M2, with M3 reserved for genuinely novel body plans or animation-dependent elite/boss designs.
