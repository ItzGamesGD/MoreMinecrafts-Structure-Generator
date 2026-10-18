# PR #7 — Security second-pass review and NeoForge runtime evidence

Date: 2026-10-18  
Repository: `ItzGamesGD/MoreMinecrafts-Structure-Generator`  
PR: [#7](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/pull/7)  
Reviewed working source: `55b8e5c58109221c5bc0b074744a57b6d7d6b2b3`

## Review status and scope

**Second-pass technical review, not independent approval.** The same assistant helped
implement earlier isolation changes; this review does not constitute approval by an
independent security reviewer or a comprehensive external penetration test.

Scope: `sandbox.py`, `isolated_child.py`, `os_confinement.py`,
the IPC model, the token and Origin controls, the Java `/build` permission predicate,
and the vendor patch-reproduction process. CI was checked via GitHub Actions logs.

## Findings

| Item | Severity / status | Evidence and next action |
| --- | --- | --- |
| Peer-process signal/resource syscalls permitted by initial seccomp denylist | **P1 conditional on a sandbox escape — repaired** | Initial policy did not restrict `kill(2)`, `prlimit64(2)`, and related peer-process APIs. Patch `0003` now denies these. Harmless `kill(parent, 0)` and read-only `prlimit` checks verify kernel refusal. No harmful signal was sent. |
| AST denylist is not a standalone Python sandbox | **Residual, unresolved** | Known introspection shapes are blocked, but unrestricted reflection through undiscovered shapes has not been disproven. Keep the kernel layer mandatory and fail closed. |
| No separate filesystem/user/network namespace | **Residual, unresolved** | Bubblewrap namespace creation was denied on the GitHub runner. Seccomp restricts tested syscalls but does not change OS identity or unmount host paths. |
| Denylist is not an exhaustive file/host isolation policy | **Residual, review required** | The policy must be audited against other path-based metadata/syscall interfaces (e.g. xattr and newer `fchmodat2`), peer process APIs, and newly added kernel syscalls. Do not claim a general containment boundary merely from current tests. |
| Trusted parent deserializes child JSON | **Bounded, review required** | No pickle crosses IPC; a 256 MiB response cap and block/name validation exist. Performance/DoS review of maximum JSON payload and warning sizes remains appropriate. |
| Authenticated WebSocket server | **Verified for tested cases** | Missing/wrong tokens rejected; browser `Origin` rejected; real Python server and Java protocol interop were exercised previously. This is not an authentication-system penetration test. |
| Vendor patches | **PASS** | GitHub `vendor-drift` job verifies pinned upstream plus patches; the patch series must be regenerated when vendor files change. |
| Java permission predicate | **Live NeoForge dispatcher PASS; player-login test NOT RUN** | See runtime evidence below. |

## Actual NeoForge runtime permission test

GitHub Actions [run #39104185011](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39104185011)
started the actual NeoForge server from the PR's mod source. A **disposable CI-only**
event observer inspected the real server's registered Brigadier `build` command node:

- `node.canUse(source.withPermission(0))` was false.
- `node.canUse(source.withPermission(1))` was false.
- `node.canUse(source.withPermission(2))` was true.
- The server emitted the `MCBUILD_RUNTIME_PERMISSION_PASS` marker and the workflow **succeeded**.

The observer is injected during CI and is **not committed into the shipped Java code**.
The test does not log in a real nonoperator/operator player, execute an actual LLM-funded
`/build` request or verify generated world blocks. Those are separate acceptance tests.

## Python, vendor and Java CI evidence

GitHub Actions [run #39104184895](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39104184895)
on `55b8e5c5`:

- **PASS:** 217 Python tests.
- **PASS:** locked Ruff lint and formatting.
- **PASS:** deterministic vendor drift against the pinned upstream and all three patches.
- **PASS:** Java build using Gradle wrapper and JDK 21.

The kernel unit tests are **real subprocess tests**, not merely mocked syscall
predicates. They verify denial of file opening, socket creation, process creation,
peer signal-0 permission checks and read-only peer `prlimit` queries.

## Merge recommendation

**BLOCKED — keep Draft.** The real server command predicate and automated regression
checks have passed, and the peer-process interference finding has been repaired.
Before considering a production security claim, obtain review by a separate
security engineer/agent, and explicitly resolve or accept the residual filesystem
and syscall-boundary risks. A real operator/nonoperator player test and a
full authenticated build/world-placement test are still separate validation work.

Do not treat CI green as proof of general-purpose sandbox containment.
