# Stage 24-B Ancient City Restoration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Implement, validate, and render eight actual Ancient City NBT candidates from the exact approved Stage 24-A baseline.

**Architecture:** A pinned-source loader checks raw Git blob hashes and baseline JSON before building. A small candidate model edits palette/block records in the original compressed NBT while snapshotting protected jigsaws, water, chests, and skull entities. A generator writes native NBT, Sponge v3 schematic, previews, plans, and reports; tests reload those artifacts and inspect actual block states and connectivity.

**Tech Stack:** Python 3.11, nbtlib, vendored mcbuild palette/renderer/schematic exporter, pytest, GitHub Actions artifacts.

**Spec:** User request Stage 24-B; approved design sheets and source-inspection JSON in `artifacts/ancient-city-restoration/stage-24a/`.

## Global Constraints

- Source must match the eight recorded SHA-1 hashes at Minecraft assets commit `bb6d6451fb5fff54d3930fd8bf19d81200f00e6d`; stop on any mismatch.
- Preserve X/Z source dimensions, every source jigsaw position/state/orientation/full NBT, all sauna water/stairs/chests/loot NBT, and the medium tower skull NBT.
- Only `medium_ruin_2` may grow vertically, from Y=5 to Y=8; stop it if an in-template height/boundary collision is found.
- Do not modify PR #8, PR #4, approved structures, roads, walls, or the Warden landmark.
- Do not claim fluid simulation, Minecraft-client placement, or visual approval without those checks.

## Review Focus

1. Source drift or malformed compact state maps: baseline tests verify fetched bytes and report consistency.
2. Jigsaw/BE loss while appending palette states: candidate tests compare full source NBT compounds after reload.
3. False accessibility from furniture occupancy: BFS uses reloaded actual candidate passability and counts doors/ladders.
4. Sauna leaks or chest blockage: tests prove same-level containment geometry and chest interaction clearance; fluid ticks remain live pending.
5. High-contrast geometry silently overwrites source supports: every removal/overwrite is reported and checked against module-specific protected blocks.

---

### Task 1: Baseline manifest and pinned source loader

**Files:** `tools/stage24b_source.py`, `artifacts/ancient-city-restoration/stage-24b/baseline.json`, `tests/test_stage24b_source.py`.

**Interfaces:** `load_original(module: str) -> SourceStructure`; `build_baseline(root: Path) -> dict`.

- [ ] Write tests for the eight expected module names, exact dimensions, and SHA mismatch rejection.
- [ ] Run the tests and confirm the expected missing-interface failures.
- [ ] Implement raw source fetch, Git blob SHA verification, design/report consistency checks, and manifest serialization.
- [ ] Run the tests and require eight `verified=true` entries with exact preserved coordinates/NBT snapshots.

### Task 2: Candidate editing and protected NBT invariants

**Files:** `tools/stage24b_candidate.py`, `tests/test_stage24b_candidate.py`.

**Interfaces:** `Candidate.set_block`, `Candidate.carve`, `Candidate.save_native`, `Candidate.to_grid`, `Candidate.verify_protected`.

- [ ] Test palette append/reuse, in-bounds edits, explicit recorded removals, and source jigsaw/BE equality after reload.
- [ ] Run red tests.
- [ ] Implement the NBT editor and round-trip writer.
- [ ] Run green tests with actual nbtlib structures.

### Task 3: Five residential candidates

**Files:** `tools/restore_stage24b_houses.py`, `tests/test_stage24b_houses.py`.

- [ ] Test dimensions, distinct actual floor-plan block states, doors, beds, light, storage, entrance path and connected interior space.
- [ ] Run red tests.
- [ ] Implement five module-specific shells, roofs, rooms and furnishings. Preserve jigsaws; `medium_ruin_2` uses Y=8 and a partial upper floor with stairs and headroom.
- [ ] Run green tests; fail the expanded module on any collision or connector drift.

### Task 4: Sauna and watchtower candidates

**Files:** `tools/restore_stage24b_public.py`, `tests/test_stage24b_public.py`.

- [ ] Test all 43 source water blocks, containment rim, source chest/loot NBT, stairs, five jigsaws, tower connectors, tower skull, ladder path, headroom, upper platforms, and no connector obstruction.
- [ ] Run red tests.
- [ ] Implement sauna dry/accessible circulation and two distinct towers, preserving all locked blocks and reporting every removed filler block.
- [ ] Run green tests; report fluid simulation and live placement as pending.

### Task 5: NBT, schematic, and structural validation

**Files:** `tools/validate_stage24b.py`, `tests/test_stage24b_artifacts.py`.

- [ ] Test round-trip NBT, Sponge v3 schematic reload/dimensions, real block-state route connectivity, ladder transitions, stair clearance, bed/chest/workstation use space, walls/roof, and connector boundary conflicts.
- [ ] Run red tests against generated candidates.
- [ ] Implement structured reports with per-requirement pass/fail/block status and source-versus-candidate comparisons.
- [ ] Run the full suite and do not suppress failures.

### Task 6: Visual evidence and CI draft PR

**Files:** `tools/render_stage24b.py`, `.github/workflows/stage24b-restoration.yml`, `artifacts/ancient-city-restoration/stage-24b/README.md`.

- [ ] Test render evidence manifest and expected file set for all eight modules.
- [ ] Generate four-direction, entrance, cutaway, floor-plan and before/after views from actual candidates.
- [ ] Add a workflow that installs vendored dependencies, verifies sources, runs tests, generates candidates, and uploads NBT/schematic/render/report artifacts.
- [ ] Run workflow on the implementation branch; create a new Draft PR based on the verified Stage 24-A commit and report all unverified live/visual work.
