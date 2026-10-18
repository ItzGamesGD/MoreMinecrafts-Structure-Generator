# SG-01 Minecraft 26.3 visual and placement validation

**Repository:** `ItzGamesGD/MoreMinecrafts-Structure-Generator`
**Draft PR:** [#5](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/pull/5)
**Branch:** `feat/sg-01-central-cavern-portable-export`

## SG-01C diagnosis

The run #41 failure did **not** establish that /place omitted the chamber. Its RCON transcript shows the exact command `place template moreminecrafts:forgotten_kingdom/central_cavern/main_chamber 0 100 0` and Minecraft responded `Loaded template ... at 0, 100, 0`. The template file has NBT size `[41,17,41]`, with local minimum coordinate `[0,0,0]`. With this absolute placement origin, no rotation, and no mirror, the coordinate rule is:

```
world_x = local_x
world_y = 100 + local_y
world_z = local_z
```

For this template, local `[20,0,20]` is indeed `minecraft:polished_deepslate`, so its expected world position is `[20,100,20]`. The earlier expectation was correct.

Run #41 then used `data get block 20 100 20`, which only returns block-entity NBT and reports “The target block is not a block entity” for ordinary blocks. It followed with a valid `execute if block` command, but its result was incorrectly judged by searching `validation/minecraft-visual/run/server/logs/server.log`. The server output was actually redirected to `validation/minecraft-visual/run/logs/server.log`; the checked path could not exist. Therefore the reported “missing block” was a **harness false failure**, and run #41 did not actually determine the block state. Its placement command source was the dedicated-server console (Overworld context); the replacement probes explicitly use `execute in minecraft:overworld` to remove that ambiguity.

### NBT-derived sample states

These are the first local positions for ten distinct non-air palette states. Their expected world coordinates follow the mapping above.

| Local NBT position | Expected world position | Expected block state |
|---|---|---|
| `[0,0,0]` | `[0,100,0]` | `minecraft:deepslate_tiles` |
| `[12,0,12]` | `[12,100,12]` | `minecraft:chiseled_tuff_bricks` |
| `[13,0,12]` | `[13,100,12]` | `minecraft:tuff_bricks` |
| `[13,0,13]` | `[13,100,13]` | `minecraft:polished_deepslate` |
| `[0,1,0]` | `[0,101,0]` | `minecraft:deepslate_bricks` |
| `[20,1,0]` | `[20,101,0]` | `minecraft:jigsaw[orientation=north_up]` |
| `[19,1,13]` | `[19,101,13]` | `minecraft:stone_brick_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]` |
| `[13,1,19]` | `[13,101,19]` | `minecraft:stone_brick_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]` |
| `[27,1,19]` | `[27,101,19]` | `minecraft:stone_brick_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]` |
| `[19,1,27]` | `[19,101,27]` | `minecraft:stone_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]` |
| `[0,1,20]` | `[0,101,20]` | `minecraft:jigsaw[orientation=west_up]` |
| `[40,1,20]` | `[40,101,20]` | `minecraft:jigsaw[orientation=east_up]` |
| `[20,1,40]` | `[20,101,40]` | `minecraft:jigsaw[orientation=south_up]` |
| `[4,9,4]` | `[4,109,4]` | `minecraft:deepslate_brick_wall` |
| `[20,15,5]` | `[20,115,5]` | `minecraft:sea_lantern` |

The replacement run checks each of the 15 distinct non-air palette states with an explicit Overworld `execute if/unless block` query. After `save-all flush`, it independently reads the saved Anvil region data and compares the decoded chunk palette at those positions. It stops before Jigsaw or client startup if any template probe fails. This makes the command response, live block state, and persisted world state separate results.

## Jigsaw checks

Only after direct chamber placement and saved-chunk probes pass, the workflow places each tunnel template at a separate test origin and runs `/place structure moreminecrafts:forgotten_kingdom/central_cavern 0 100 0` in the Overworld. It flushes and decodes the saved chunk data again, checking sampled states for the chamber and four tunnel transforms as well as the floor immediately beyond the north, east, south, and west seams.

The exported transforms are:

| Piece | Origin offset from Jigsaw placement |
|---|---|
| Main chamber | `[0,0,0]` |
| East tunnel | `[40,0,18]` |
| North tunnel | `[18,0,-14]` |
| South tunnel | `[18,0,40]` |
| West tunnel | `[-14,0,18]` |

The assembled local bounds are expected at x/z `-14..54`, y `0..16`; with the placement origin `[0,100,0]`, the expected world bounds are x/z `-14..54`, y `100..116`. Jigsaw validation is reported separately from direct template placement.

## Screenshot acceptance

The capture method remains the existing test-only Fabric harness calling Minecraft's native `Screenshot.grab(...)` after the client world and renderer are ready. The first camera is the central plaza at `[20,102,20]`; further views start only after the plaza PNG is saved, is nonempty, and has the expected 1280×720 dimensions. Screenshots are accepted only after direct block verification succeeds.

This method was verified in MoreMinecrafts-Beta PR #83 and [Actions run #38345195208](https://github.com/MoreMinecrafts-Beta/actions/runs/38345195208), whose [artifact #11787944376](https://github.com/MoreMinecrafts-Beta/actions/runs/38345195208/artifacts/11787944376) contains Minecraft-rendered PNGs. The Beta repository remains read-only.

## Historical results

- [Run #37](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091006597): the native harness wrote ten PNGs, but inspected plaza/interior images show the flat-world scene rather than SG-01.
- [Run #39](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091506040): `/place structure` returned success; the subsequent test used the same invalid ordinary-block NBT query / log-path assumption and did not prove block placement.
- [Run #41](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091758916): exporter checks, deterministic export, 17 existing tests, and Gradle configuration passed. Its world-write verdict was invalid because of the path mismatch documented above. The [run #41 artifact](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091758916/artifacts/12122908412) contains its command and server logs.

Current SG-01C runtime and screenshot verdicts will be filled from the next workflow run. This document distinguishes command success, persisted block verification, Jigsaw assembly, and visual review; a successful `/place` response alone is never treated as placement acceptance.

The harness is test-only. No gameplay systems, mobs, bosses, loot, research features, or cavern redesign are included. PR #5 remains **Draft** and **unmerged**.
