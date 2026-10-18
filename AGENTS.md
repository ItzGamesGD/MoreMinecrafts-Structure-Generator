# Agent Guidelines

- Follow `docs/DEVELOPMENT_WORKFLOW.md` and `docs/MAIN_INTEGRATION_PLAN.md`.
- Never push to or merge into `main`; open Draft PRs from topic branches.
- Never force-push, rewrite existing history, delete source branches, or bypass GitHub Rulesets.
- Do not change repository security settings.
- Do not include unfinished SG-01 work or unapproved Ancient City changes/experiments in integration branches.
- `vendor/mcbuild` is an upstream snapshot; avoid editing it by hand (it is refreshed by `.github/workflows/vendor-mcbuild.yml`).
- Report verification honestly: distinguish newly run results from historical ones, and report failures with their output.
- Unresolved P1 review findings and any security findings block merge until explicitly resolved or waived by the owner; do not invent finding details, and record missing evidence instead (see `docs/MAIN_INTEGRATION_PLAN.md`).
