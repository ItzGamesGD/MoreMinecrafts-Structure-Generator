# Security assessment: 2026-10-18 audit findings

A separate security audit dated 2026-10-18 reported two findings against the vendored
`mcbuild` tool. This PR independently validates each with non-destructive proofs-of-concept,
then applies the smallest fixes that address what was confirmed.

## Finding 1: potential mcbuild DSL sandbox escape

**Confirmed.** `vendor/mcbuild/src/mcbuild/dsl/sandbox.py`'s `validate_ast` blocked
`ast.Attribute` nodes whose name starts with `_`, plus a small name denylist (`eval`,
`exec`, `open`, ...). Two independent gaps let code reach real interpreter internals
without ever producing a banned `ast.Attribute` or `ast.Name` node:

1. **`str.format()`/`format_map()` dunder chains.** `"{0.__class__.__bases__}".format(0)`
   performs the attribute walk inside the format-mini-language at runtime, against the
   *string template*, not as AST nodes the validator ever sees. Verified:
   `compile_blueprint('x = "{0.__class__.__bases__}".format(0)')` was accepted (no
   `SandboxViolation`) before the fix.
2. **Frame/generator/code introspection via public-named attributes.** `gi_frame`,
   `f_back`, `f_globals`, `f_locals`, `tb_frame`, `co_consts`, etc. don't start with `_`,
   so the old check never considered them, even though they expose frame locals/globals
   and code objects. Verified: `compile_blueprint("x = None\nf = x.f_back\n")` (and the
   other names) was accepted before the fix.

Both are now blocked by an explicit `BANNED_ATTRS` set checked alongside the existing
leading-underscore rule. Regression tests: `tests/test_dsl_sandbox.py` (new
"2026-10-18 security audit" section, parametrized over every blocked attribute name, plus
both `str.format` variants).

**Not confirmed / not attempted:** full arbitrary code execution, filesystem access, or
process spawning from inside the sandbox. I stopped at proving attribute-level reachability
(non-destructive: reading type names and counts, never invoking anything dangerous through
the escaped reference) rather than building a weaponized exploit chain. Treat the sandbox
as **broken as a hard boundary** regardless — an AST denylist can only enumerate *known*
escape shapes, and the two found here were not the only theoretically possible ones, just
the ones checked. The code's own former docstring said as much ("threat model: LLM
accidents... not a malicious adversary"), which undersold the actual exposure: blueprint
text reaches `run_blueprint` via the LLM agent loop, which runs on a user-supplied prompt.

**Fix implemented:**
- Hardened `validate_ast` (`BANNED_ATTRS`), covering both confirmed gaps. This remains
  defense in depth, not a boundary — the module docstring now says so explicitly.
- Added `run_blueprint_isolated()`: runs `run_blueprint` in a `multiprocessing`
  "spawn"-context child process with `RLIMIT_CPU` and (best-effort) `RLIMIT_AS` applied,
  a wall-clock join timeout with terminate/kill fallback, and only the resulting
  `VoxelGrid` (or a structured error) sent back over a pipe. A sandbox escape inside the
  child reaches a disposable process, not the host process's address space, open file
  descriptors, or in-memory secrets (e.g. the OpenRouter API key living in
  `OpenRouterClient`). Regression tests: `tests/test_sandbox_isolation.py` (correctness
  parity with in-process execution, error propagation, and that a runaway blueprint can't
  hang the caller).

**Explicitly not done, and why:** `agent/loop.py`'s three `sandbox.run_blueprint(...)`
call sites (the actual LLM-facing path) were **not** switched to the isolated variant in
this PR. That loop shares a live `VoxelGrid` across iterations and streams render/design
events synchronously; moving it to a separate process needs the grid and event stream to
be marshaled across a process boundary without changing its live-build behavior, which is
a larger, higher-risk refactor than "smallest robust fix" and risks regressing the
streaming feature if done hastily. `run_blueprint_isolated` is ready and tested for that
migration as a tracked follow-up. Process isolation is also not a complete boundary by
itself here — there's no seccomp/namespace/container layer, so a child process that
escapes Python can still do anything the host OS user can do; it only removes the
*in-process* blast radius (shared memory, file descriptors, other live Python objects).

## Finding 2: unauthenticated WebSocket server / missing Origin validation

**Confirmed by inspection** (both halves, no PoC needed — the code had neither
check at all):
- `vendor/mcbuild/src/mcbuild/server/ws_server.py`'s `_handler` accepted any
  `{"cmd": "build", "prompt": ...}` message with no credential of any kind.
- `serve(handler, host, port)` was called with no `origins=` argument, so the
  `websockets` library applied no Origin restriction.

**Threats verified:**
- **Localhost, non-browser:** the server binds `127.0.0.1` by default, which stops other
  *machines*, but any other local process, user, or sandboxed/contained process able to
  reach the loopback interface could open a raw WebSocket connection and get a build —
  i.e. real LLM spend (`Config.cost_ceiling` caps one build's cost, not how many a
  non-owner can start) — for free. No credential was required to distinguish the
  legitimate Forge-mod client from anything else on the box.
- **Browser-origin:** browsers do not apply same-origin restrictions to outbound
  WebSocket connections — any page open in the operator's browser (a malicious site, or
  JS injected into an otherwise-trusted one) can run
  `new WebSocket("ws://127.0.0.1:8765")` directly. This is the realistic "a webpage
  attacks your local server" vector for a `ws://localhost` service; it needs no DNS
  rebinding, since `ws://127.0.0.1` is directly reachable from page JS.

**Fix implemented:**
- **Authentication:** every connection's first message must include a `token` field,
  compared against `Config.auth_token` with `hmac.compare_digest` (avoids a timing
  side-channel). `ws_server.py main()` takes `--token`, falls back to the
  `MCBUILD_SERVER_TOKEN` env var, and generates+prints a random one via
  `secrets.token_urlsafe(24)` if neither is given — never silently runs without one.
- **Origin policy:** `serve(..., origins=[None])` — accepts only connections with *no*
  `Origin` header. Every browser-initiated WebSocket handshake carries one (page JS cannot
  suppress or forge it); the Forge mod's `java_websocket`-based client does not send one.
  This rejects all browser-originated connections, from any site, while leaving the
  legitimate mod client connectable. Kept as a second layer on top of auth, since some
  non-browser HTTP/WS client libraries *can* set an arbitrary Origin header, so this alone
  would not be sufficient against every possible client.
- Regression tests: `tests/test_ws_server_security.py`, exercising `_handler` directly
  against a fake connection (no real socket) — missing token, wrong token, malformed JSON,
  the build-in-progress path, and the correct-token success path.

**Java `/build` permission model:** `BuildCommand.java` required
`source.hasPermission(0)` — any player, including one with no other elevated permission on
the server. Combined with the unauthenticated WS server, any player could trigger
LLM-funded builds. Raised to `hasPermission(2)` (the vanilla operator level). The mod also
had to start sending the new `token`: `WsClient.java` now reads
`System.getenv("MCBUILD_SERVER_TOKEN")` and includes it, so the operator sets one value
(the env var) on both the Python server's and the Minecraft server's environment.

**Limitation:** the two Java changes (`BuildCommand.java`, `WsClient.java`) were
**reviewed by inspection only — not compiled or run**. This sandbox has no network access
to `maven.neoforged.net`/the NeoForge Gradle toolchain (`gradle compileJava --offline`
fails immediately on an unresolvable plugin), so there was no way to build or test the
mod module here. Confirm these compile and the mod still builds locally or in CI with
Maven/NeoForge access before relying on them.

## A deployment gap this patch set does not close

`vendor/mcbuild` is treated elsewhere in this repo as an unmodified upstream snapshot: see
`vendor/mcbuild/SECURITY_PATCHES.md`, added alongside this PR, for which files were
hand-patched and why the next `.github/workflows/vendor-mcbuild.yml` run will silently
overwrite them back to upstream's original (vulnerable) code unless the fixes are
upstreamed, the workflow is changed to not clobber these files, or someone reapplies this
patch set after every resync. None of those follow-ups are done by this PR.

## Summary: confirmed vs. unconfirmed

| Finding | Status |
|---|---|
| AST denylist bypass via `str.format()`/`format_map()` dunder chains | **Confirmed**, fixed |
| AST denylist bypass via frame/generator/code-introspection attributes | **Confirmed**, fixed |
| Full RCE / filesystem / process-spawn escape beyond attribute reachability | Not attempted (would require a weaponized exploit; out of scope for a non-destructive PoC) |
| In-process execution as an inadequate boundary for untrusted blueprints | **Confirmed** in principle (denylists are inherently incomplete); process isolation added as the recommended mitigation, not yet wired into the LLM-facing call sites |
| Unauthenticated WebSocket server | **Confirmed** (no check existed), fixed |
| Missing Origin validation | **Confirmed** (no check existed), fixed |
| `/build` permission level too low | **Confirmed** (level 0 = any player), fixed, **not compiled/tested** |
| Vendored patches surviving the next upstream resync | **Open** — tracked in `vendor/mcbuild/SECURITY_PATCHES.md`, not fixed here |
