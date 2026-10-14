# Ancient City variant prototype progress — 2026-10-14

Repository: `ItzGamesGD/MoreMinecrafts-Structure-Generator`.

Base: `phase-3/ruined-watchtower-2026-10-05` (the proven mcbuild structure-production experiment), not the unrelated MoreMinecrafts-Beta implementation branch.

## Current stage

- Three city-scale thematic compositions authored: death, nether, living.
- Two **preliminary candidate drafts** for each theme written in mcbuild blueprint DSL.
- These are staged before render review; the second draft is a planned visual alternative, **not yet a render-informed revision**.
- A reusable real-mcbuild renderer/validator and GitHub Actions workflow are committed.
- Real render execution, visual inspection, and final schematic approval are **PENDING** until Actions evidence is retrieved and inspected.
- No `final/` assets are declared.
- No draft PR and no merge yet.

## Intended architecture

This is a structure-asset generator, not a Fabric worldgen integration project.
The composition shows linked districts and a central landmark. Outputs are **representative-scale compositions**, not full 1:1 recreations of Minecraft's vanilla Ancient City template layout.

- Death: sculk expansion, collapse, remains distributed through separate districts.
- Nether: central portal mockup, corruption gradient with distance, multiple affected districts.
- Living: restored roofs, maintained streets, lighting, civic market details.

**Caution:** Nether's purple-glass interior is a **visual portal mockup**, not a functioning Nether portal; mob/AI behavior is out of scope.

## Validation gate

Workflow: `.github/workflows/ancient-city-variant-renders.yml`.

Renderer: `tools/render_ancient_city_variants.py`.

It attempts actual DSL execution and multi-angle views for every candidate and exports/validates intermediate Sponge schematic candidates. Success must be confirmed from CI artifacts; no execution outcome is currently claimed.

After first renders:

1. Inspect images (including multiple yaw angles and top view).
2. Revise geometry from concrete observations.
3. Render the revisions again.
4. Export/promote accepted final artifacts.
5. Open a Draft PR, retaining main untouched.

## Known constraints

- No new visual reference images were supplied with this task. The user-approved written concepts and vanilla Ancient City design language are the references.
- This generator branch does not register variants into Minecraft worldgen.
- Four-way city-level random selection belongs to a separate future integration task, not this generator task.
