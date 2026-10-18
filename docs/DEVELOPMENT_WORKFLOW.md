# Development Workflow

## Branches

- `main` is protected by a GitHub Ruleset. Never push to it directly and never bypass the ruleset.
- Work on a topic branch (`feat/`, `recovery/`, `phase-N/`, `integration/`, `probe/`, `prototype/`, `repair/`) cut from the current `origin/main`.
- Never force-push, rewrite published history, or delete source branches that are still referenced by an integration.
- Integrate source branches with `git merge --no-ff` so each source stays identifiable in history.

## Before opening a PR

Run from `vendor/mcbuild` with the dev extras installed (`uv sync --frozen --extra dev`):

```bash
pytest -q
ruff check .
ruff format --check .
```

Then from the repository root:

```bash
python tools/phase2_validate.py          # writes untracked outputs under artifacts/phase-2/control/
git diff --check origin/main
git merge-tree --write-tree origin/main HEAD   # must report no conflicts
```

Do not commit generated Phase 2 outputs unless a PR explicitly calls for them.

## Pull requests

- Open as Draft; mark ready only after verification and review.
- Use `.github/PULL_REQUEST_TEMPLATE.md`.
- Record verification results as newly run or historical, and never claim a rebuilt commit has the SHA or ancestry of an earlier one.
- Keep unfinished or unapproved work (e.g. SG-01, Ancient City variants) out of integration PRs.
