# Security assessment: 2026-10-18 audit findings (remediation status)

A separate security audit dated 2026-10-18 reported two findings against the vendored
`mcbuild` tool. This document records what was independently validated, what was changed,
how each change was verified, and what remains open. The patch series lives in
`vendor/patches/mcbuild/` (see its README for the upstream-sync process).

Status key: **CONFIRMED** = reproduced here. **PASS / FAIL / NOT RUN / BLOCKED** describe
verification results and are kept separate from the finding status.

## Finding 1: mcbuild DSL sandbox escape

**CONFIRMED (attribute-level reachability).** `validate_ast` blocked only attributes beginning
with `_` plus a small name denylist. Two gaps let code reach interpreter internals without a
banned AST node:

1. `str.format()` and `format_map()` dunder chains, such as `"{0.__class__.__bases__}".format(0)`.
   The attribute walk happens inside the runtime format mini-language, so the validator never
   sees an `ast.Attribute`. Before the fix, `compile_blueprint` accepted this template.
2. Frame, generator, traceback and code introspection through public-named attributes
   (`gi_frame`, `f_back`, `f_globals`, `tb_frame`, `co_consts`, `cell_contents`, ...). None
   begins with `_`. Before the fix, `compile_blueprint` accepted each of these.

Both are blocked by `BANNED_ATTRS`. Regression tests: `tests/test_dsl_sandbox.py`
(parametrized over every blocked name, plus both `str.format` variants).

**Not attempted:** a full code-execution, filesystem or process-spawn exploit chain. The
validation stopped at attribute-level reachability, using PoCs that read type names and
counts and invoked nothing dangerous. The AST denylist remains defense in depth only, and
the module docstring says so.

### Remediation: process isolation for every LLM-authored blueprint

**Verified.** The three blueprint execution paths in `agent/loop.py` (`submit_blueprint`,
`edit_region`, `str_replace`) now call `run_blueprint_isolated`. Nothing in `src/` calls the
in-process `run_blueprint` except the isolated child itself. `run_blueprint` is kept for
trusted input: repository blueprints and tests.

How the isolated path works:

- The child is `python -I -m mcbuild.dsl.isolated_child`. `-I` ignores `PYTHON*` variables
  and drops the current directory from `sys.path`.
- The child starts with an **empty environment** (`OPENROUTER_API_KEY` is not visible to
  it) and a **fresh scratch working directory**, deleted afterwards.
- After decoding the trusted request, the worker installs a Linux x86-64 **seccomp** filter
  (kernel-enforced) before running any blueprint code. It rejects new file opens, socket
  operations, process creation and several alternative kernel interfaces. The worker fails
  closed if filter installation fails or the architecture is unsupported. This is a
  syscall-restriction layer, **not** a general-purpose container or VM.
- The worker uses a child-local uncolored palette while placing blocks; the parent later
  re-resolves block state names and textures. This prevents legitimate dynamic block states
  from requiring filesystem reads after syscall filtering.
- CPU and address-space rlimits are applied (20 s CPU, 1 GiB address space). The parent
  enforces a 15 s deadline, kills an overdue child immediately, and always reaps the child.
- Requests and results are **JSON only**. Nothing is unpickled from the child, because a
  compromised child could otherwise run code in the parent through a crafted pickle. Blocks
  cross the boundary as coordinates plus block-state strings, not palette indices, since
  indices are process-local. The parent re-resolves names against its own palette, enforces
  the name grammar and length limit, and places blocks through `VoxelGrid.set`, so the block
  count and extent limits still apply.
- `isolation_supported()` requires the POSIX `resource` module. Where it is missing (Windows),
  `run_blueprint_isolated` **refuses to run** rather than execute unconstrained (fail closed).
  A child that cannot apply its limits reports that and does not run the blueprint.

Failure handling: a blueprint error stays a `BlueprintError`. A timeout, kill, crash,
malformed result or limit failure raises `IsolatedExecutionError`, a `BlueprintError`
subclass, so the agent loop records it as a failed attempt and the model can retry. It does
not abort the run.

Verification (all run in this environment unless marked):

| Check | Result |
|---|---|
| Behavior parity with in-process execution, and a dynamic block state (`oak_stairs[facing=north]`) across the boundary | PASS |
| `edit_region` and `str_replace` operate on the existing build; the input grid is not mutated | PASS |
| Blueprint errors and sandbox violations propagate as `BlueprintError` with line numbers | PASS |
| Python runaway loop stops on the in-sandbox budget | PASS |
| C-level busy work (`sum(range(10**12))`) is killed by the parent deadline (about 3 s) | PASS |
| `[0] * 10**10` hits the address-space limit and reports `MemoryError` (about 0.1 s) | PASS |
| Environment is empty and the cwd is a fresh scratch directory, removed afterwards | PASS |
| No orphaned children after success, error, timeout and memory cases | PASS |
| Malformed or malicious child results are rejected by the parent (types, grammar, size, extent) | PASS |
| Limit-setup failure and unsupported platform fail closed | PASS |
| Loop regression: all three paths invoke the isolated executor; the in-process executor is forbidden in the same run | PASS |
| Loop regression mutation: reverting one call site to in-process fails the test; starting `edit_region` from an empty grid fails the existing edit test | PASS (mutation caught) |
| Child started on Windows | NOT RUN (no Windows environment; behavior is refusal by design) |
| Linux kernel denies opening an external fixture file, creating a socket and forking a child | **PASS** (`tests/test_os_confinement.py`, GitHub Actions run #39103118228) |
| Dynamic block state placement without opening texture files in the child; full agent loop regression | **PASS** (217 Python tests on GitHub Actions run #39103118228) |
| Filesystem namespace isolation using Bubblewrap on Ubuntu runner | **BLOCKED** (runner permissions; no fallback to unconfined execution) |

**Limitations that remain:**

- Seccomp now blocks new file opens, network sockets, and process creation in the child on
  Linux x86-64; real kernel denial tests pass. It does **not** unmount the host filesystem,
  change the OS user, create a complete filesystem namespace, or prove that every possible
  kernel escape route is closed. The trusted parent still has host access. This policy is
  intentionally more restrictive than scratch-only file access: the blueprint cannot open
  files even inside its scratch directory. Legitimate DSL execution does not require this.
- Only Linux x86-64 is verified for the syscall filter. Other architectures and platforms
  fail closed. New Linux syscall interfaces require security review when the policy changes.
- We tested Bubblewrap on GitHub's Ubuntu 24.04 runner. Its network namespace setup failed
  with `Failed RTM_NEWADDR: Operation not permitted`, and filesystem-only setup failed with
  `setting up uid map: Permission denied` (diagnostic runs #39102073092 and #39102213166).
  We did not bypass runner restrictions to force namespace isolation.
- This is defense in depth, not a claim of perfect containment of arbitrary native code;
  independent review is required before production exposure.
- Blueprint `print()` output is discarded (the child's stdout is `/dev/null`). Previously it
  went to the server's stdout.
- Each blueprint costs one interpreter start plus the `mcbuild` import (about 0.1 s measured).
- `isolation_supported()` is false on Windows, so the server cannot run blueprints there.
  That is deliberate, but it means the feature is unavailable on Windows until a Job Object
  implementation is written.

## Finding 2: unauthenticated WebSocket server and missing Origin validation

**CONFIRMED by inspection.** Before the fix, `_handler` accepted any `{"cmd": "build"}` message
without a credential, and `serve()` was called without an `origins` policy.

Threats, with the corresponding controls:

- **Other local processes or users** could open a raw connection to `127.0.0.1:8765` and
  trigger LLM-funded builds (`Config.cost_ceiling` caps one build's cost, not how many a
  non-owner can start). Control: a required shared token, compared with
  `hmac.compare_digest`.
- **Browser-origin pages**: browsers do not apply same-origin rules to outbound WebSockets,
  so any page open in the operator's browser can connect to `ws://127.0.0.1:8765`. Control:
  `origins=[None]`, which accepts only connections without an `Origin` header. Browsers
  always send one.

The token is **required** at startup: `--token` or `MCBUILD_SERVER_TOKEN`, at least 16
characters. There is no unauthenticated mode and no generated token. The token is never
printed or logged.

Verification (real server on port 8765, real Java client; see the Java section):

| Check | Result |
|---|---|
| Server refuses to start without a token, and with one shorter than 16 characters | PASS |
| No token, or a wrong token: the server returns `Unauthorized` and starts no build | PASS (python client and Java client) |
| Correct token reaches the build path (the server returns its missing-API-key error, which proves auth passed) | PASS (python and Java clients) |
| Browser-style `Origin: https://evil.example` with the correct token: HTTP 403 | PASS |
| The token value does not appear in the server log | PASS (0 occurrences) |
| The Java client's default handshake sends no `Origin`, so the policy does not lock out the mod | PASS |
| Unit tests for token comparison, handler rejection paths and the build-in-progress path | PASS (`tests/test_ws_server_security.py`) |

**Found and fixed during verification (pre-existing, not security):** `run_build_session` could
drop its final message. `enqueue()` hands each put to the loop with `call_soon_threadsafe`,
so `queue.join()` could return before the last put. The result was that the missing-API-key
error and the closing `finish`/`error` were never sent. Fixed by yielding once before the
join. Regression tests: `tests/test_server_session_flush.py`. The mutation check (removing the
yield) fails both tests.

**Remaining limitations of the WebSocket control:**

- The token travels as plaintext JSON on loopback. Anything that can capture loopback traffic
  (root or raw-socket access on the same host) can read it. Loopback-only binding is the
  boundary here.
- Anyone who can read the Minecraft server process environment (`/proc/<pid>/environ`, same
  user) can read `MCBUILD_SERVER_TOKEN`. Protect that environment like any other secret.
- No rotation, no rate limiting on failed attempts, and no check of token entropy beyond the
  length minimum. A 16+ character random token is adequate. A short human-chosen one is not.
- The origin policy rejects every browser client. Adding a browser UI later needs an explicit
  allowlist.

## Java: `/build` permission and the WebSocket client

| Check | Result |
|---|---|
| `./gradlew compileJava` from a fresh wrapper (Gradle 8.8, NeoForge 21.1.235, JDK 21), including the modified `BuildCommand.java` and `WsClient.java` | **PASS** (BUILD SUCCESSFUL) |
| `./gradlew assemble` (produces the `jarJar` shaded jar with Java-WebSocket) | **PASS** |
| `WsClient.java` and `ProtocolMessages.java` compiled unchanged and run against the real Python server (Java-WebSocket 1.5.7, Gson 2.10.1, `BuildSessionManager` stubbed to record callbacks) | **PASS**: correct token accepted; missing and wrong tokens refused |
| Protocol compatibility: the Python `protocol.py` shapes (`chat`, `blocks` with `null` air, `finish`, `error`, `hello`) decode into the Java POJOs with the right coordinates and block strings | **PASS** (fake server built from `protocol.py`, `origins=[None]`) |
| Authentication on reconnection | Each `WsClient` opens a new connection and sends the token in `onOpen`. There is no automatic reconnect, so each connection is authenticated. **PASS by inspection and harness** |
| Token does not reach logs (Java logs nothing; server log checked) | **PASS** |
| `/build` requires permission level 2, so only operators can run it | **Inspection only**: `hasPermission(2)`. **NOT RUN** at runtime, because this needs a Minecraft server with an operator and a non-operator player |
| Runtime behavior of a build inside a live Minecraft world | **NOT RUN** |

The Java changes are compile-verified and protocol-verified, not game-verified. Treat the
`/build` permission change as unverified until someone runs it on a live NeoForge server.

## Vendor patch preservation

`vendor/mcbuild` is an upstream snapshot whose local patches previously lived only in the tree,
and the old sync workflow wiped and recopied that tree, so the fixes would have been silently
overwritten. Now:

- `vendor/patches/mcbuild/0001-security-audit-2026-10-18.patch` is the source of truth for
  local changes. `vendor/patches/apply.sh` builds the tree from a pinned upstream checkout plus
  the series, and fails if any hunk does not apply.
- The `vendor-drift` job in `.github/workflows/mcbuild-ci.yml` fetches the pinned upstream
  commit (`vendor/mcbuild/UPSTREAM_COMMIT`), rebuilds, and fails on any difference from the
  committed tree.
- `.github/workflows/vendor-mcbuild.yml` no longer pushes to `main`. It is manual only. It
  takes a full commit SHA, builds from it, and opens a Draft PR from `vendor-sync/<sha12>`.
- Local round-trip check (this environment): `make-patch.sh` then `apply.sh` reproduces the
  committed tree exactly: 2,270 tracked files, zero content mismatches, executable bits kept.
  Applying twice gives identical output. A deliberately drifted upstream fails with
  `patch does not apply` and exit 1.

**Verified:** GitHub Actions run #39103118228 independently fetched pinned upstream
`34ce86372d4c23f4d83d4e24fc256cb399d6c3e3` and confirmed the committed vendor tree
matches that upstream plus the local patch series. GitHub Actions still cannot create PRs
under the current repository setting, so vendor-sync PR creation is a manual step.

## Summary

| Item | Status |
|---|---|
| AST denylist bypass via `str.format()` dunder chains | CONFIRMED; fixed; regression tests |
| AST denylist bypass via frame, generator and code introspection | CONFIRMED; fixed; regression tests |
| Full RCE, filesystem or process-spawn chain | NOT ATTEMPTED |
| In-process execution as a boundary for LLM-authored blueprints | CONFIRMED as inadequate; **every LLM-facing path now runs isolated** |
| OS-level file/network syscall restriction | **PASS for tested Linux x86-64 operations**: kernel seccomp denies new file opens, network sockets and forks; not a complete container boundary |
| Full OS isolation | **Not achieved**: same OS user and mounted host filesystem; namespace attempts blocked by runner privileges |
| Unauthenticated WebSocket server | CONFIRMED; fixed (required token, verified end to end) |
| Missing Origin validation | CONFIRMED; fixed (`origins=[None]`, verified with HTTP 403) |
| `/build` permission level 0 (any player) | CONFIRMED; raised to 2; Java **compile PASS**, runtime **NOT RUN** |
| Vendored fixes overwritten by the next upstream sync | Fixed by deterministic patch series and **GitHub vendor-drift PASS** |
| Pre-existing: final protocol message dropped | Fixed; regression tests |
