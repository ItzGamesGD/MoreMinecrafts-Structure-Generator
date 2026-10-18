# SG-01 Minecraft 26.3 client and visual validation

**Target:** Structure Generator PR #5, current branch `feat/sg-01-central-cavern-portable-export`
**Status:** SG-01B is adapting the verified native Minecraft 26.3 `Screenshot.grab` client harness from MoreMinecrafts-Beta PR #83. SG-01 screenshots are still **NOT RUN**. No design changes were made.

## Verdicts

| Check | Verdict | Evidence |
|---|---|---|
| Portable NBT/datapack generation and static NBT/Jigsaw checks | **PASS** | Structure Generator [GitHub Actions run #4](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39056031517); it rebuilds the datapack, compares committed resources byte-for-byte, regenerates the prior GLB/PNG package, and runs all 17 exporter/Jigsaw tests. |
| Gradle fixture configuration | **PASS** | Run #23 completed the Gradle 9.6 / Fabric Loom 1.17.21 configuration-only `help` step successfully using `implementation` for Fabric Loader and Fabric API. |
| Minecraft 26.3 server startup and datapack recognition | **PASS** | Run #23 started the server to `Done`; `datapack list enabled` included `[file/sg01 (world)]`. Exact runtime logs are in [artifact #12112524684](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39065733597/artifacts/12112524684). |
| `/place template` chamber + four tunnels | **PASS** | Run #25's RCON transcript records five `Loaded template "moreminecrafts:forgotten_kingdom/central_cavern/<template>" at ...` results at the requested coordinates. |
| `/place structure` live Jigsaw generation | **PASS (command)** | Run #25's RCON transcript records `Generated structure "moreminecrafts:forgotten_kingdom/central_cavern" at 0, 100, 0`. |
| Minecraft client startup | **PASS** | Run #27 selected Vulkan llvmpipe, created an SDL X11 window and loaded Minecraft texture atlases. OpenGL's GLX initialization failed first; the client continued on Vulkan. |
| Minecraft client joins the loaded world | **PASS in earlier runs only** | Run #29 and #31 logs show `SG01Visual` joined and was teleported to the plaza. Run #35 did not verify world join; capture stopped at EWMH activation before its join check. |
| Minecraft screenshots | **NOT RUN** | Earlier SG-01 runs produced no PNGs. Run #35 failed at EWMH activation. The fixture is being adapted to Minecraft's native `Screenshot.grab` method based on verified PR #83 code and run evidence. |
| Architectural visual quality review | **NOT RUN** | There are no Minecraft-rendered screenshots. The cavern design remains unchanged. |

## Read-only CI environment investigation

The referenced [MoreMinecrafts-Beta PR #117](https://github.com/ItzGamesGD/MoreMinecrafts-Beta/pull/117) is a separate server-side world-generation feasibility probe. Its report identifies Minecraft 26.3 / world version 5023, and explicitly marks in-client visual and screenshot validation **NOT RUN**. Its final head's [Fabric CI run #885](https://github.com/ItzGamesGD/MoreMinecrafts-Beta/actions/runs/39043907357) included a successful `client-smoke` job.

The Beta repository's [Fabric CI workflow](https://github.com/ItzGamesGD/MoreMinecrafts-Beta/blob/integration/stage23-final-reconciliation-20261016/.github/workflows/build.yml) shows a useful temporary runner setup:

- Ubuntu with Temurin Java 25.
- `xvfb`, Mesa software rendering, and a virtual `1280x720x24` display.
- A bounded `./gradlew runClient` launch, then checks for client initialization, a graphics backend, resource reload, and loaded Minecraft texture atlases.
- The PR #117 run's `client-smoke` job completed successfully. Its log also shows Minecraft resource initialization under Mesa llvmpipe.

This is a **client startup/resource smoke**, not SG-01 validation. It does not install this repository's datapack into a world, query the live command registry, execute `/place template` or `/place structure`, establish GUI scale 2, save Minecraft screenshots, or attach image artifacts. PR #117's world-generation probe exercises a different minimal test structure and reports screenshots as NOT RUN. Neither source repository was modified during this investigation.

## What is needed for actual visual review

A follow-up temporary client harness must launch Minecraft 26.3 with this exact datapack, create or load a disposable world, verify the registered command/template IDs in game, and place the chamber and tunnel templates plus the assembled structure. It must set a fixed time/weather and GUI scale, capture at least 1280×720 screenshots of the plaza, upper walkway, supports/ceiling, four passages, and exterior, and upload those images to this PR. The current Beta smoke workflow supplies a virtual-display starting point but does not provide this world/command/screenshot harness.

The latest server-side placement verdicts are documented below. Visual-quality review remains **NOT RUN** until actual Minecraft-rendered screenshots are available. The current design is unchanged pending the requested screenshot review.

## SG-01B automated acceptance harness

The workflow now defines a disposable Fabric Loom client/server fixture at `validation/minecraft-visual/` and a bounded `minecraft-26-3-visual` job. It targets Java 25 and Minecraft 26.3 (Fabric Loader 0.19.5 / Fabric API 0.161.0+26.3), follows the referenced Beta runner's Ubuntu + Xvfb + Mesa llvmpipe setup, and limits the overall job to 30 minutes. The server loads a generated pack only after its full directory has passed the repository's byte-for-byte comparison against the committed export. It uses an isolated flat world, fixed seed 173, noon, clear weather and RCON enabled only on loopback.

The job first runs a configuration-only Gradle `help` step with a five-minute timeout. It does not launch Minecraft. Only after that gate passes does the bounded server task run. The job gates placement on the live `/datapack list enabled` result for `file/sg01`, then records `/place template` attempts for the main chamber and four tunnel resource paths and `/place structure moreminecrafts:forgotten_kingdom/central_cavern`. A quick-play Minecraft client connects to that server at 1280×720 under Xvfb/llvmpipe; the client options set GUI scale 2. RCON moves the player to documented fixed positions and yaw/pitch; `F2` writes each actual Minecraft frame. Logs, camera commands and screenshots are uploaded as the workflow artifact. This is a test-only launch fixture; it adds no gameplay content and does not change the cavern design.

The harness source is documented in [`validation/minecraft-visual/README.md`](../../validation/minecraft-visual/README.md). Runtime outcomes below are taken from uploaded GitHub Actions logs. The previous GLB-derived previews are not Minecraft runtime evidence.

### Runs #23–#35 evidence and verified capture-method investigation

- Workflow run [#23](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39065733597), at branch head `11491b65fb65e15e956b27a04fca1680aad92807`: portable-export and all 17 tests **PASS**; datapack reproducibility and committed resource checksums **PASS**; Gradle configuration **PASS**; server started and recognized the exact pack **PASS**.
- Run #23 client log showed Vulkan llvmpipe and a created X11 window, but failed to connect because the server process ended between Actions steps. The run's [artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39065733597/artifacts/12112524684) contains logs and command transcripts but **no PNGs**.
- Review of the RCON transcript found all five `/place template` calls and the `/place structure` call returned `That position is not loaded`. The old result check missed that error and wrote a false PASS. Do not use that marker as evidence.
- Run #25's [artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39087368914/artifacts/12121058947) shows all five `/place template` commands returned `Loaded template ...` and the `/place structure` command returned `Generated structure ...`. The server loaded the exact pack and generated the structure. The harness stopped because its success matcher expected `Placed ...` instead of the actual 26.3 response text; the client step did not run, and the artifact has no PNGs.
- Run #27 [artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39087556594/artifacts/12121622245) confirms all placements and includes client logs, but no PNG. The client selected Vulkan and loaded its texture atlases. The server rejected `SG01Visual` as not whitelisted; the script's title filter also failed to detect the created SDL window.
- Run #29 [artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39088129974/artifacts/12121278096) shows the whitelist fix worked: client startup, world join and RCON camera teleport passed. Xvfb's lack of a window manager caused `windowactivate` to fail.
- Run #31 [artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39088364176/artifacts/12121796937) passed the plaza join and teleport but the `F2` action produced no PNG. Its evidence records X window 543 with an empty title; no capture was saved.
- Run #33 [artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39088625611/artifacts/12121867071) again passed world join and camera teleport but produced no image. Its focus diagnostic reports root window `1`; the runner had no window manager and lacked `xwininfo`.
- Run #35 [artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39088898276/artifacts/12121149496) passed exporter checks, all 17 tests, Gradle configuration, server startup, pack recognition, and placement. It failed at EWMH activation. Its empty `window-manager.log` and shutdown-only `client.log` do not verify the X session/window relationship, client join, or screenshots. World joins in #29/#31 are separate earlier evidence; run #35 join is **NOT RUN**.
- Read-only inspection of PR #83's source found a client Fabric harness that calls `net.minecraft.client.Screenshot.grab(...)` in a post-render HUD callback after the world is ready and frames have settled. Its capture script launches Minecraft under Xvfb with the lavapipe Vulkan ICD, uses RCON to set the camera, then waits for the native capture completion marker. It uses no EWMH activation or synthetic key event.
- PR #83 Actions run [#38345195208](https://github.com/ItzGamesGD/MoreMinecrafts-Beta/actions/runs/38345195208) and artifact [#11787944376](https://github.com/ItzGamesGD/MoreMinecrafts-Beta/actions/runs/38345195208/artifacts/11787944376) were independently inspected. The `arena` job and upload passed; the archive contains two nonempty 1280×720 PNGs, and client logs record Vulkan/Mesa llvmpipe, resource reload, `ARENA_CLIENT_JOINED`, and `ARENA_CAPTURE_WRITTEN`.
- PR #68 includes five committed PNGs; its README identifies them as actual uncropped Minecraft 26.3 captures from a local single-player world with Mesa llvmpipe Vulkan. No reproducible capture script is included in that tree.
- The PR #72 branch and supplied commit `098b1f866923c08dbcccc437d3edf7d7bf5a5ecb` do not contain `control.py`, `derive_companions.py`, or `run/command_history.txt`; those files are also absent from the available workspace. PR #72's description refers to a 38-image archive under `/workspace`, but that archive is not available here. Its associated CI run #37733592847 has a failed `client-smoke` job; the workflow does not capture PNGs. Those files and the 38-image claim therefore do not establish a reusable capture method in this workspace.
- The current fixture adds only the proven native capture API path. It keeps the existing SG-01 server/datapack/placement flow and requests the plaza screenshot first; it validates that PNG before continuing to other camera positions. This implementation has not yet run in Minecraft. Screenshots and architectural review remain **NOT RUN** until a PNG appears in a new run artifact.
- CI run #35's portable export, deterministic resource comparison, visual export comparison, and all 17 tests passed. No design change was made.
