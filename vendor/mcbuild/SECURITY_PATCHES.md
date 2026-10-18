# Hand-applied security patches (2026-10-18 audit)

`vendor/mcbuild` is normally an unmodified upstream snapshot, refreshed wholesale by
`.github/workflows/vendor-mcbuild.yml` (which deletes this directory and `rsync`s a fresh
copy from `harrynull/mcbuild` on every run). The files below were hand-patched directly in
this vendored copy, at the explicit direction of a 2026-10-18 security remediation task,
to fix two findings reported by a separate security audit.

**This means the next `vendor-mcbuild.yml` run will silently delete these patches and
restore the original, vulnerable upstream code**, unless one of the following happens
first:
- the fixes are upstreamed to `harrynull/mcbuild` and the next vendor sync picks them up, or
- `vendor-mcbuild.yml` is changed to not clobber these specific files, or
- someone re-applies this patch set after every resync.

None of those are done by this change; it only patches the local snapshot, as directed.
See the PR that introduced this file for the full writeup (confirmed/unconfirmed findings,
test results, and limitations).

## Patched files

- `src/mcbuild/dsl/sandbox.py` — hardened `validate_ast`'s attribute denylist (closes a
  `str.format()`-dunder-chain bypass and a frame/generator/code-introspection bypass, both
  confirmed via non-destructive PoC); added `run_blueprint_isolated` (process-isolated
  execution with CPU/memory rlimits) as the recommended entry point for untrusted/LLM-
  authored blueprint text.
- `src/mcbuild/server/ws_server.py` — added a required shared-secret `token` on the first
  WebSocket message, and an `origins=[None]` policy that rejects any browser-originated
  connection (Origin header set).
- `src/mcbuild/server/protocol.py` — documented the new inbound `token` field.
- `src/mcbuild/config.py` — added `Config.auth_token`.
- `mod/src/main/java/com/mcbuild/mod/command/BuildCommand.java` — raised `/build`'s
  required permission level from 0 (any player) to 2 (operator).
- `mod/src/main/java/com/mcbuild/mod/net/WsClient.java` — sends the new `token` field,
  read from the `MCBUILD_SERVER_TOKEN` environment variable.
- `tests/test_dsl_sandbox.py`, `tests/test_sandbox_isolation.py` (new),
  `tests/test_ws_server_security.py` (new) — regression tests for the above.

The two Java files were **not compiled or run** in this environment (no network access to
`maven.neoforged.net`/the Forge toolchain from this sandbox); they were reviewed by
inspection only. See the PR for the full limitations list.
