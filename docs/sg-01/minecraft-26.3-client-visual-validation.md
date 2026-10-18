# SG-01 Minecraft 26.3 visual validation

**Repository:** `ItzGamesGD/MoreMinecrafts-Structure-Generator`  
**Draft PR:** [#5](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/pull/5)  
**Branch:** `feat/sg-01-central-cavern-portable-export`  
**Current head:** `21a76fa4f84015d8225f6e2cb8c0eeaab58ba9f1`

## Current verdict

| Check | Verdict | Evidence |
|---|---|---|
| Portable exporter, byte reproducibility, visual asset reproducibility, 17 existing tests | **PASS** | [Actions run #41](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091758916), `portable-export` job. |
| Gradle/Loom configuration | **PASS** | Run #41 configuration-only Gradle `help` step. |
| Minecraft 26.3 server startup and exact datapack recognition | **PASS** | Run #41 starts the 26.3 server and reports `file/sg01` enabled. |
| Template resource lookup | **PASS (lookup only)** | `/place template` returned `Loaded template ...` for the five exact NBT resource IDs. |
| Template blocks written to the test world | **FAIL** | Run #41 checked the chamber's known polished deepslate floor at `(20, 100, 20)` immediately after template commands. `execute if block` did not match, and the stage stopped before client startup. |
| Jigsaw structure command | **PASS (command only, run #39)** | Minecraft returned `Generated structure ...`, but the expected chamber floor did not exist afterward. |
| Native screenshot API file creation | **PASS, scene invalid (run #37)** | The Fabric harness wrote ten nonempty 1280×720 PNGs. Manual inspection of `plaza-eye.png` and `interior-overview.png` shows sky/flat grass rather than the cavern. These are not accepted as SG-01 visual evidence. |
| Valid Minecraft-rendered cavern screenshot | **NOT RUN / FAIL** | No accessible PNG currently depicts SG-01. [Run #41 artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091758916/artifacts/12122908412) contains logs only; [run #37 artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091006597/artifacts/12123146028) contains the invalid-scene PNGs. |
| Architectural visual quality review | **NOT RUN** | No valid Minecraft view of the cavern exists. The cavern design has not been changed. |

## Capture-method investigation

The capture method was based on directly inspected MoreMinecrafts-Beta PR #83 source and [Actions run #38345195208](https://github.com/ItzGamesGD/MoreMinecrafts-Beta/actions/runs/38345195208). The test-only Fabric client calls `net.minecraft.client.Screenshot.grab(...)` in a post-render HUD callback after world join and rendered frames. Its workflow runs Minecraft 26.3 under Xvfb with Mesa lavapipe Vulkan, sets camera positions through RCON, and waits for the API completion marker. Its [artifact #11787944376](https://github.com/ItzGamesGD/MoreMinecrafts-Beta/actions/runs/38345195208/artifacts/11787944376) contains two nonempty 1280×720 PNGs and logs showing actual Minecraft renderer startup and capture completion. SG-01 now uses this native capture method; it does not rely on X11 focus or synthetic F2 input.

PR #68 contains five Minecraft 26.3 screenshots described as uncropped local captures, but no reproducible automation source was present in the inspected tree. PR #72's referenced `control.py`, `derive_companions.py`, and `run/command_history.txt` were absent from the branch, supplied commit `098b1f866923c08dbcccc437d3edf7d7bf5a5ecb`, and available workspace. Its claimed 38-image archive was also unavailable; its associated `client-smoke` run did not provide image evidence. Those files were not assumed to exist or treated as verified capture instructions. MoreMinecrafts-Beta remains read-only and unchanged.

## SG-01 runtime evidence

- Run #37 [workflow](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091006597) passed exporter checks, Gradle configuration, server startup, datapack recognition, template commands, and the Jigsaw command. The native screenshot harness saved ten PNGs. Inspecting the plaza and interior images showed an empty flat-world scene, so the capture API worked but the images do not show the requested build.
- Run #39 [workflow](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091506040) retained passing exporter checks and server/command responses. The added block-presence check failed after the Jigsaw call; no client or screenshots were run.
- Run #41 [workflow](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091758916) again passed exporter checks, all 17 tests, and Gradle configuration. It logged all five successful template resource responses, then failed the immediate world-block check at the chamber floor. The failure artifact includes the command transcript and server log; no client launch was attempted.

The exact blocker is therefore the discrepancy between successful `/place template` command responses and the missing expected block at the NBT-derived world coordinate. In run #39, the `/place structure` success response also did not establish that the expected floor block was present. The current evidence does not prove that the generated NBT blocks reached the world. Screenshot/visual acceptance is withheld until that is resolved.

The validation harness is test-only. No gameplay systems, creatures, rewards, research systems, or cavern redesign were introduced. PR #5 remains **Draft** and **unmerged**.
