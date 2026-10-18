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

- **Phase 3 stair headroom (Codex P1 on PR #2): corrected on this branch, pending CI.** Reproduced from the generated voxel grid: the six stairs end at feet y=7, one block under the deck surface, and solid blocks at `(8, 8, 5)`/`(8, 9, 5)` plus the stairwell rails left no exit. This is an **integration-time correction** applied only to `artifacts/phase-3/final/` (`(7, 7, 4)` becomes a north-facing half-height stair; rail `(7, 8, 4)` removed); the Phase 3 source branch and `iteration-1/`, `iteration-2/` are unchanged. The PR #2 review thread is still open and should be resolved by its owner. Guarded by `tests/test_phase3_watchtower.py`.
- **Externally reported security findings (audit dated 2026-10-18), not independently reproduced.** (1) Potential mcbuild DSL sandbox escape; (2) unauthenticated WebSocket server and missing Origin validation. They were not recorded in GitHub issues or PR discussions, and no details beyond these two titles are in this repository. They are retained as open, unreproduced findings and tracked as **separate remediation dependencies**; no security fix is made in this PR, and `vendor/mcbuild` is unchanged. Acceptance into `main` stays blocked until the owner decides how they are resolved or waived.
- Human review and the repository ruleset requirements for `main`.

## Verification

CI is defined in `.github/workflows/pr-checks.yml` (pytest, Ruff lint/format with the Ruff version pinned in `vendor/mcbuild/uv.lock`, Phase 2 validation, Phase 3 NBT-equivalence). Phase 3 schematics are compared on decoded NBT, not file bytes, because the exporter writes gzip and the Sponge Schematic v3 format does not require deterministic compressed bytes. See the PR description for newly run results versus historical results quoted in `artifacts/phase-2/report.md` and `artifacts/phase-3/report.md`.
