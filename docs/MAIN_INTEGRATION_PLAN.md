# Main Integration Plan

## Scope of the first integration

Branch `integration/main-prep-20261018`, cut from `origin/main` (`5ca7d73`), merging with `--no-ff`:

| Source branch | Verified HEAD | Commits | Files |
|---|---|---|---|
| `recovery/phase-2-headless-validation` | `0828f49` | 5 | `artifacts/phase-2/*`, `tools/phase2_validate.py` |
| `phase-3/ruined-watchtower-2026-10-05` | `8fa0003` | 2 | `artifacts/phase-3/*` |

Both branch from `f15ab67`, touch disjoint files, and merge without conflicts.

This integration was reconstructed after the original local integration branch was lost with its container. Its merge commits are new and do not share SHAs or ancestry with the lost ones.

## Explicitly excluded

- `feat/sg-01-central-cavern-portable-export` (SG-01, unfinished)
- `probe/ancient-city-*`, `prototype/ancient-city-*` (unapproved Ancient City work)
- `inspection/ice-box-*`, `repair/ice-box-*` (not part of this integration)
- Any security-related changes unrelated to the above

## Acceptance blockers

- **Open P1 review finding (functional, not security)** on PR #2 (`artifacts/phase-3/final/blueprint.py` line 100): solid blocks at `(8, 8, 5)` and `(8, 9, 5)` leave no headroom at the stair landing `(8, 7, 5)`, so the staircase has no player-height exit. Reproduced on this branch from the generated voxel grid. The thread is unresolved and the Phase 3 report's "walkable upper deck" claim is not supported until it is fixed or waived.
- **Security P1 findings: evidence not found.** The earlier handoff referred to known security P1 findings, but no issue, PR comment, review thread, or file in this repository contains them. The merge blocker is retained until the owner supplies or links the original findings (or states there are none).
- Human review and the repository ruleset requirements for `main`.

## Verification

CI is defined in `.github/workflows/pr-checks.yml` (pytest, Ruff lint/format with the Ruff version pinned in `vendor/mcbuild/uv.lock`, Phase 2 validation, Phase 3 NBT-equivalence). Phase 3 schematics are compared on decoded NBT, not file bytes, because the exporter writes gzip and the Sponge Schematic v3 format does not require deterministic compressed bytes. See the PR description for newly run results versus historical results quoted in `artifacts/phase-2/report.md` and `artifacts/phase-3/report.md`.
