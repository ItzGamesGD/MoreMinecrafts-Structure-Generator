# Local patches to vendored mcbuild

`vendor/mcbuild/` is a vendored copy of `harrynull/mcbuild`, pinned to the commit in
`vendor/mcbuild/UPSTREAM_COMMIT`. Local security fixes are kept as a patch series here, so a
future upstream sync cannot silently overwrite them.

## Files

| Path | Purpose |
|---|---|
| `0001-security-audit-2026-10-18.patch` | Fixes for the two 2026-10-18 audit findings (DSL sandbox, WebSocket server) and the Java `/build` permission level. |
| `0002-os-syscall-confinement.patch` | Linux x86-64 seccomp file/network/process denial, child-side palette identity separation, and security regression tests. |
| `../apply.sh` | Builds a tree from a pristine upstream checkout plus every patch here. Fails if any patch does not apply. |
| `../make-patch.sh` | Regenerates a patch from the pristine upstream tree and the current `vendor/mcbuild`. |

## Invariants

1. `vendor/mcbuild` equals pinned upstream plus these patches. CI enforces this in the
   `vendor-drift` job of `.github/workflows/mcbuild-ci.yml`, which rebuilds from the pin and
   diffs against the committed tree.
2. Edit `vendor/mcbuild` directly, then run `make-patch.sh` to regenerate the series. Never
   edit the patch file by hand. Never edit the vendor tree without regenerating the patch.
3. `UPSTREAM.md` and `UPSTREAM_COMMIT` are generated from the pin and are excluded from
   patches.
4. Patches are applied in lexical order. Add a new `NNNN-topic.patch` for each change rather
   than rewriting an existing one, so the history stays reviewable.

## Updating the upstream pin

1. Run the `vendor-mcbuild` workflow (manual dispatch) with the full upstream commit SHA.
2. It rebuilds the tree from that commit plus this series. If any patch no longer applies,
   the job fails. Resolve it by regenerating the patch against the new upstream, not by
   skipping it.
3. On success it opens a Draft PR from `vendor-sync/<sha12>`. Review the upstream diff, then
   confirm the `vendor-drift` and Python checks pass. Merge only after human review.

The workflow never pushes to `main`.

## Regenerating a patch after a local change

```bash
# pristine = a checkout of the pinned upstream commit
vendor/patches/make-patch.sh /path/to/pristine-upstream vendor/patches/mcbuild/0001-security-audit-2026-10-18.patch
vendor/patches/apply.sh /path/to/pristine-upstream /tmp/rebuilt   # must succeed
diff -r -x .git -x UPSTREAM.md -x UPSTREAM_COMMIT /tmp/rebuilt vendor/mcbuild   # must be empty
```

## Known limitations of this process

- The first patch was generated against `origin/main:vendor/mcbuild` as a stand-in for
  the pinned upstream snapshot. The `vendor-drift` job now **passes** against the actual
  pinned `harrynull/mcbuild@34ce863` in GitHub Actions (#39103118228).
- Patches cannot protect against an upstream change that touches the same lines. Those
  cases fail loudly (by design), so a human must reconcile them.
- Upstream fixes should be proposed upstream. Once upstream contains a fix, drop the
  matching hunk from the series so it is not applied twice.

## Security patch contents (0001)

- `src/mcbuild/dsl/sandbox.py`: AST denylist extended with frame, generator and code
  introspection attributes and `str.format` dunder chains. Adds `run_blueprint_isolated`,
  which runs blueprints in a separate `python -I` child with CPU and address-space limits.
  The child exchanges JSON only, never pickle.
- `src/mcbuild/dsl/isolated_child.py`: the child entry point.
- `src/mcbuild/agent/loop.py`: all three blueprint execution paths use the isolated executor.
- `src/mcbuild/server/ws_server.py`: requires a shared token (at least 16 characters, from
  `--token` or `MCBUILD_SERVER_TOKEN`), compares it in constant time, never prints it, and
  rejects any connection carrying an `Origin` header.
- `src/mcbuild/server/session.py`: fixes a pre-existing bug where the final message could be
  dropped before the socket closed.
- `mod/.../BuildCommand.java`: `/build` requires permission level 2 (operator), up from 0.
- `mod/.../WsClient.java`: sends `MCBUILD_SERVER_TOKEN` in the request.
- `mod/gradle/wrapper/gradle-wrapper.jar`: the missing wrapper bootstrap, plus regenerated
  scripts, so `./gradlew` works from a clean checkout.
- Regression tests under `tests/`.

## OS syscall restrictions (0002)

- Linux x86-64 blueprint workers must successfully install a seccomp filter before running
  untrusted code. File opens, sockets and process spawning are denied.
- Unknown architectures and failed seccomp setup are not silently downgraded to
  unconstrained execution.
- Child-side palette calculation preserves block identity without opening rendering assets;
  the trusted parent resolves texture and color metadata after JSON IPC.
- The GitHub CI security tests exercise actual denial and legitimate blueprint generation.
  Full process/filesystem namespace isolation is not claimed.
