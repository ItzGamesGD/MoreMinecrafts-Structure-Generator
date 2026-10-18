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

- **Security P1 findings remain unresolved** and block acceptance into `main`. The finding details are not recorded in this repository; they must be linked here before the PR leaves Draft.
- Human review and the repository ruleset requirements for `main`.

## Verification

See the PR description for newly run results versus historical results quoted in `artifacts/phase-2/report.md` and `artifacts/phase-3/report.md`.
