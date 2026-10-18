# Agent Guidelines

- Follow `docs/DEVELOPMENT_WORKFLOW.md` and `docs/MAIN_INTEGRATION_PLAN.md`.
- Never push to or merge into `main`; open Draft PRs from topic branches.
- Never force-push, rewrite existing history, delete source branches, or bypass GitHub Rulesets.
- Do not change repository security settings.
- Do not include unfinished SG-01 work or unapproved Ancient City changes/experiments in integration branches.
- `vendor/mcbuild` is an upstream snapshot; do not edit it by hand (it is refreshed by `.github/workflows/vendor-mcbuild.yml`).
- Report verification honestly: distinguish newly run results from historical ones, and report failures with their output.
- Known security P1 findings remain unresolved acceptance blockers until explicitly closed (see `docs/MAIN_INTEGRATION_PLAN.md`).
