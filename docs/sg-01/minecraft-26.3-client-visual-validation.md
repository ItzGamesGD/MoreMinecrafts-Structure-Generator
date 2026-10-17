# SG-01 Minecraft 26.3 client and visual validation

**Target:** Structure Generator PR #5, head `81c56bc23e6d266689d34ab445c934204dc83fad`
**Status:** Real client placement, Jigsaw assembly, and in-game visuals are **NOT RUN**. No design changes were made.

## Verdicts

| Check | Verdict | Evidence |
|---|---|---|
| Portable NBT/datapack generation and static NBT/Jigsaw checks | **PASS** | Structure Generator [GitHub Actions run #4](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39056031517); it rebuilds the datapack, compares committed resources byte-for-byte, regenerates the prior GLB/PNG package, and runs all 17 exporter/Jigsaw tests. |
| Minecraft 26.3 client available in this execution environment | **NOT RUN** | No Minecraft launcher, 26.3 client jar, or `~/.minecraft` installation was present. The available Java runtime is 21; this environment has no Xvfb/virtual display. |
| `/place template` for the chamber and four tunnels | **NOT RUN** | No in-game command tree or registered template IDs were observed. Exact command IDs therefore remain unverified. |
| `/place structure` and live Jigsaw assembly | **NOT RUN** | No Minecraft 26.3 world was loaded with this pack. Static connector-coordinate checks are not a runtime placement result. |
| Minecraft screenshots and architectural quality review | **NOT RUN** | No screenshots from the Minecraft renderer are available. The existing GLB-derived previews remain structural references only and are not presented as in-game evidence. |

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

### Latest SG-01B checkpoint

- Prior final-head workflow [run #19](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39064385344): portable-export **PASS**; Minecraft visual job **FAIL** during Gradle configuration.
- Exact prior failure: `Could not find method modImplementation() ...`. The fixture now uses the Beta project's `implementation` configuration for Fabric Loader and Fabric API.
- A configuration-only `gradlew help` step now gates the Minecraft server/client launch. It has not yet been observed on GitHub Actions in this checkpoint.
- Local configuration check: **NOT RUN** because the execution environment could not resolve `services.gradle.org` to download the wrapper distribution. Existing Python export/Jigsaw tests remain **PASS** locally.
- Minecraft server/client: **NOT RUN** after the dependency correction.
- Datapack recognized and loaded: **NOT RUN**.
- `/place template` chamber + four tunnels: **NOT RUN**.
- `/place structure` Jigsaw assembly: **NOT RUN**.
- Actual Minecraft screenshots: **NOT RUN**. No Minecraft frames exist in this checkpoint.
- Architectural visual-quality review: **NOT RUN**; no redesign made.
