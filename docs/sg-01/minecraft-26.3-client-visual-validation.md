# SG-01 Minecraft 26.3 client and visual validation

**Target:** Structure Generator PR #5, current branch `feat/sg-01-central-cavern-portable-export`
**Status:** SG-01B runtime harness is being corrected from actual run #23 evidence. No design changes were made.

## Verdicts

| Check | Verdict | Evidence |
|---|---|---|
| Portable NBT/datapack generation and static NBT/Jigsaw checks | **PASS** | Structure Generator [GitHub Actions run #4](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39056031517); it rebuilds the datapack, compares committed resources byte-for-byte, regenerates the prior GLB/PNG package, and runs all 17 exporter/Jigsaw tests. |
| Gradle fixture configuration | **PASS** | Run #23 completed the Gradle 9.6 / Fabric Loom 1.17.21 configuration-only `help` step successfully using `implementation` for Fabric Loader and Fabric API. |
| Minecraft 26.3 server startup and datapack recognition | **PASS** | Run #23 started the server to `Done`; `datapack list enabled` included `[file/sg01 (world)]`. Exact runtime logs are in [artifact #12112524684](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39065733597/artifacts/12112524684). |
| `/place template` and `/place structure` actual placement | **FAIL (harness check)** | Commands were issued with the expected resource IDs, but all six returned `That position is not loaded`. The previous script failed to recognize this message and incorrectly wrote `runtime-place=PASS`; that verdict is invalid. The corrected runner force-loads the relevant chunks and requires explicit successful placement messages before reporting PASS. |
| Minecraft client startup | **PASS** | Run #23 selected Vulkan llvmpipe and created an X11 window at 1280×720. OpenGL's GLX initialization failed, then Minecraft successfully selected Vulkan. |
| Client joins a loaded world and screenshots | **FAIL (harness lifecycle)** | Quick play received `Connection refused` because the server was launched in an earlier GitHub Actions step and the runner cleaned up its background process at that step boundary. The new combined runner keeps server acceptance and client capture in one bounded step. No PNG was produced. |
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

Until that run exists, the game-side placement and visual-quality verdicts remain **NOT RUN**. The current design is unchanged pending the requested screenshot review.

## SG-01B automated acceptance harness

The workflow now defines a disposable Fabric Loom client/server fixture at `validation/minecraft-visual/` and a bounded `minecraft-26-3-visual` job. It targets Java 25 and Minecraft 26.3 (Fabric Loader 0.19.5 / Fabric API 0.161.0+26.3), follows the referenced Beta runner's Ubuntu + Xvfb + Mesa llvmpipe setup, and limits the overall job to 30 minutes. The server loads a generated pack only after its full directory has passed the repository's byte-for-byte comparison against the committed export. It uses an isolated flat world, fixed seed 173, noon, clear weather and RCON enabled only on loopback.

The job first runs a configuration-only Gradle `help` step with a five-minute timeout. It does not launch Minecraft. Only after that gate passes does the bounded server task run. The job gates placement on the live `/datapack list enabled` result for `file/sg01`, then records `/place template` attempts for the main chamber and four tunnel resource paths and `/place structure moreminecrafts:forgotten_kingdom/central_cavern`. A quick-play Minecraft client connects to that server at 1280×720 under Xvfb/llvmpipe; the client options set GUI scale 2. RCON moves the player to documented fixed positions and yaw/pitch; `F2` writes each actual Minecraft frame. Logs, camera commands and screenshots are uploaded as the workflow artifact. This is a test-only launch fixture; it adds no gameplay content and does not change the cavern design.

The harness source is documented in [`validation/minecraft-visual/README.md`](../../validation/minecraft-visual/README.md). Runtime outcomes must be filled in from the GitHub Actions run. Until that run produces the runtime log and PNG artifact, client startup, datapack/resource loading, live placements, assembly and screenshots remain **NOT RUN**. The previous GLB-derived previews are not runtime evidence.

### Run #23 evidence and resumed correction

- Workflow run [#23](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39065733597), at branch head `11491b65fb65e15e956b27a04fca1680aad92807`: portable-export and all 17 tests **PASS**; datapack reproducibility and committed resource checksums **PASS**; Gradle configuration **PASS**; server started and recognized the exact pack **PASS**.
- Run #23 client log showed Vulkan llvmpipe and a created X11 window, but failed to connect because the server process ended between Actions steps. The run's [artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39065733597/artifacts/12112524684) contains logs and command transcripts but **no PNGs**.
- Review of the RCON transcript found all five `/place template` calls and the `/place structure` call returned `That position is not loaded`. The old result check missed that error and wrote a false PASS. Do not use that marker as evidence.
- The current patch moves server acceptance and client capture into a single 22-minute Actions step, force-loads test chunks before placement, and requires explicit positive placement responses. Local `bash -n`, YAML parsing, and `git diff --check` passed before the latest placement-result correction; a new Actions run is needed to verify it.
- Current visual verdict: **NOT RUN**. No actual Minecraft PNGs exist yet, so architectural quality is **NOT RUN**. The cavern design is unchanged.
