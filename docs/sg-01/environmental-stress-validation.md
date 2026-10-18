# SG-01-B — Environmental stress and survival accessibility validation

**Repository:** `ItzGamesGD/MoreMinecrafts-Structure-Generator`
**Draft PR:** [#5](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/pull/5) (open, unmerged)
**Branch:** `feat/sg-01-central-cavern-portable-export`
**Design geometry:** unchanged. No exported resource was modified in this stage.

Verdict words: **PASS**, **FAIL**, **BLOCKED**, **NOT RUN**. Evidence classes are kept apart:

| Class | Meaning here |
|---|---|
| Natural runtime | Official Minecraft 26.3 server generated the chunks (no `/place`); results read back from saved region files |
| Synthetic runtime | Real server, but the environment was constructed with `/fill`; never counted as natural generation |
| Runtime probe | Real server, entity collision/pathfinding, but not a live player or client |
| Static | Geometry-only model, no Minecraft runtime |
| Human visual | Owner inspection of screenshots. **Not performed in this stage** |

Nothing here is owner design approval.

## Method and reproduction

Everything is in `validation/minecraft-visual/stress/` and runs in the `sg01-environment-stress` job of
`.github/workflows/validate-structures.yml` (official 26.3 `server.jar`, SHA-1 verified by `fetch-server.sh`).

* **Candidate sites (bounded, deterministic).** `spread.py` reimplements vanilla `random_spread` (verified: it reproduces the
  proven seed-173 site, chunk 324,309 = block 5184,4944). For each of 16 fixed seeds
  (`173 1 2 3 42 1337 2024 31415 271828 8675309 -7 -9999 123456789 20261017 555 9001`, chosen before looking at results)
  the 6 nearest candidates to the origin (within ±6 regions) whose trial-chambers exclusion is not predicted are force-loaded,
  plus the 2 nearest predicted-suppressed candidates, plus the original site 173:324:309. Minecraft decides whether a
  structure exists; results are read from the saved chunks' `structures.starts` (exact pieces, rotation, bounding boxes).
* **Analysis (`analysis.py`).** Rebuilds the expected blocks of each recorded piece with its recorded rotation and compares
  every block of the saved world, classifies the exterior shell and the 12-cell openings of the tunnel mouths, counts
  non-air blocks in the template's air cells (per piece), and reads biomes and surface height. The world is read again after
  `tick sprint 2400` (2 minutes of game time, all chunks force-loaded) to observe fluid spread.
* **Traversal probe (`TraversalProbe.java`, Fabric fixture).** A player-width mob (Zombie, 0.6 wide, same step height) with all
  goals removed is driven by Minecraft's own `PathNavigation` / `MoveControl` / `JumpControl` and entity collision. A leg PASSes
  only if the mob ends standing on the ground within 2 blocks horizontally and 0.3 blocks vertically of the goal.
  **This is a runtime collision/locomotion probe, not a live player or client-input test.**
* **Static probe (`static_probe.py`, `tests/test_sg01_static_accessibility.py`).** Half-block collision model (stairs 0.5/1.0,
  walls 1.5, terrain outside the structure solid), walk step ≤ 0.6, jump ≤ 1.0. Geometric reachability only.
* **Synthetic fluid scenarios (`run_synthetic.py`).** Water / lava `/fill` against terrain-sealed tunnel mouths of a natural site.

Local reproduction: see the workflow step commands; Java 25 and Python 3.12 + numpy are required.

## Results

Numbers below are from the CI run linked in the PR description; the same code run locally gave the same site-level facts.
SG-01-B sample: **16 seeds, 128 candidate sites loaded, 96 generated structures** (the other 32 were the intentionally loaded
suppressed candidates). This is a sample, not a reliability proof.

### Phase 1 — cave and fluid interaction

| Scenario | Verdict | Evidence |
|---|---|---|
| Structure shell stays intact when caves touch it (natural) | **PASS** | 85 of 96 sites touch cave air with part of their shell (largest: hundreds of blocks); no cave breached a wall or the interior. |
| Direct water contact with shell (natural) | **PASS** | 12 of 96 sites; shell intact. |
| Direct lava contact with shell (natural) | **PASS** | 10 of 96 sites; shell intact. |
| Tunnel mouth sealed by terrain (natural) | **PASS** (as generated) | 361 of 384 mouths (94 %). Entrance is rock; see accessibility. |
| Tunnel mouth open to cave air (natural) | **PASS** | 16 mouths at 12 sites. Interior unaffected. |
| Fluid enters through an open tunnel mouth (natural) | **FAIL** as a design property, see Finding F-1 | 7 mouths at 5 sites were adjacent to water/lava; 6–24 fluid cells entered the tunnel (never the plaza chamber), no growth after 2,400 ticks. |
| Fluid stays out of the main chamber (natural) | **PASS** | 0 of 96 sites. Enforced by CI. |
| Fluid spread stops short of the plaza (synthetic) | **PASS** | Water: 33 cells in one tunnel, lava: 21 cells in another, chamber dry, 8,575/8,575 blocks intact after 2,400 ticks. |

Recorded per site (`summary.json`/`summary.md` in the CI artifact): seed, chunk, plaza and surface biome, rotation, Y range,
exterior contact counts, mouth states, interior non-air blocks, block integrity. The per-site table is in the artifact summary.

### Phase 2 — survival accessibility

| Scenario | Verdict | Evidence |
|---|---|---|
| Walk each tunnel mouth → chamber door → plaza centre, and back (runtime probe) | **PASS** | Pinned natural sites (7 sites × 4 mouths × 4 legs). Legs ending in a fluid-filled mouth FAIL, as expected (pathfinder avoids lava/water). |
| Plaza → stair foot → ring landing → full ring lap → back down (runtime probe) | **PASS** | All stair-up legs reached the ring only via a jump (peak height above the landing). |
| Same, static model | **PASS** with jump | Mouths reach the plaza and each other on walk-only edges; the ring needs a jump edge. |
| Reach the structure from the surface / from outside | **BLOCKED** | 94 % of mouths are solid rock; the structure has no surface entrance by design. A player must dig or find a connecting cave. |
| Walk from cave air into an open mouth (runtime probe) | **NOT RUN** | The simple "goal 6 blocks outward" probe could not stand on irregular cave floors, so it is inconclusive (all outward probes ended FAIL, including at open mouths). Only sealed mouths are a meaningful negative control. |
| Doors, fences, slabs | **NOT RUN** | The current design contains none (only full blocks, bottom stairs, walls, lanterns). |
| Live player/client input traversal | **NOT RUN** | Not available; see limitations. |

### Phase 3 — terrain, seeds, Trial Chambers

| Scenario | Verdict | Evidence |
|---|---|---|
| All 8,575 expected blocks present, no wrong block (excluding Finding F-2 overlays) | **PASS** | 85 of 96 sites exactly 8,575/8,575; 11 sites carry later-feature overlays (F-2). No unexplained replacement (CI-enforced). |
| Height | **PASS** | Structure Y-min −41…−21, top ≤ −5; lowest surface clearance above the top: 67 blocks. |
| Rotation | **PASS** | All four rotations generated: 24 / 28 / 21 / 23 sites. |
| Biome and terrain variety | **PASS** | 33 plaza-level and 32 surface biome types incl. oceans, deserts, taiga, swamp, mushroom fields, lush/dripstone caves, deep dark. |
| Trial Chambers coexistence | **PASS** (sample) | 33 generated pairs, no overlap; smallest bounding-box gap 73 blocks. |
| Trial Chambers exclusion zone behaviour | see F-3 | Positional, 100 % predicted by offline model (0 mismatches over 128 sites). |
| Ancient City / mineshaft / other structure overlap | **NOT RUN** | No dedicated targeting; only incidental. |

### Phase 4 — defects and repairs

No structural-geometry defect (missing, misplaced or mis-rotated block, broken seam, wrong height) was confirmed, so **no
exported geometry or datapack was changed**. The following are confirmed environment/design findings that need an owner
decision; none was "fixed" by silently redesigning.

* **F-1 Fluid enters open tunnel mouths.** The four far-end openings are 3×4 air cells. Where terrain beside a mouth is water
  or lava (7 of 384 mouths, 5 sites), 6–24 fluid cells flow in and stop. Reproduce: seeds/chunks `3:-29:38` (water),
  `1337:-84:3` (lava). Chamber/plaza never reached. Options: leave (consistent with caves), or close mouths until the future
  district connectors exist (geometry change).
* **F-2 Later vanilla features overwrite the shell and decorate the interior.** Sculk growth in deep-dark biome (7 sites) turns
  up to 1,566 floor/wall blocks to sculk and puts sculk sensors and shriekers (`can_summon=true`) inside the template air
  (5 sites). Amethyst geodes (3 sites) and a monster room (1 site) overwrite a few blocks. Glow lichen, cave vines, vines and
  spore blossoms grow inside the interior at 74 sites. Reproduce: `31415:38:76`, `2024:69:0`. A biome-tag exclusion of
  `minecraft:deep_dark` would not remove the case where only part of the footprint is deep dark (`2024:69:0`), so no
  partial mitigation was applied. Decision needed: accept, restrict biomes/height, or change materials.
* **F-3 Trial Chambers exclusion is positional.** Vanilla evaluates `exclusion_zone` against trial-chamber *candidate
  positions*, not generated chambers. Because both sets use spacing 34, 1,811 of 2,704 scanned SG-01 candidates (67 %) are
  suppressed, so effective frequency is about one third of the nominal random-spread rate, and 12 loaded suppressed sites
  had no trial chamber at all. Decision needed on `chunk_count`/spacing/salt.
* **F-4 Ring landing needs a jump.** The last stair's back surface is at 8.0, the ring floor surface at 9.0, a 1.0 rise
  (runtime: the mob only reaches the ring with a jump, static model agrees). Walkable by a player who jumps; not by
  walk-only movement. A characterisation test (`test_ring_is_reachable_but_only_with_a_jump`) pins this; an eighth stair step
  at the ring edge would remove it (geometry change, left to the owner).
* **F-5 Terrain-sealed entrances.** See Phase 2.

Regression coverage added: static accessibility unit tests, determinism pins for the sites above
(`stress/pinned-sites.json`), CI invariants (full block integrity apart from known overlay kinds, no fluid in the chamber,
prediction/Minecraft agreement, interior traversal legs).

## Limitations

* Sample of 16 seeds / 96 generated sites; no frequency or reliability claim beyond it.
* Traversal evidence is mob locomotion with player width, not a live player (jump height, sneaking, sprint-jump,
  ladders, and client collision are not exercised); the mob is 1.95 high, 0.15 taller than a player.
* Feature-overlay results depend on generation order across chunk borders (the same site gave slightly different overlays in
  two runs); pins therefore use lower bounds.
* Cave-to-mouth walking, Ancient City overlap, performance, and human visual acceptance are NOT RUN.
* No owner design approval is claimed.
