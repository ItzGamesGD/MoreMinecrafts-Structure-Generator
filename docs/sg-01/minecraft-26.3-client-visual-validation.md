# SG-01 Minecraft 26.3 visual and placement validation

**Repository:** `ItzGamesGD/MoreMinecrafts-Structure-Generator`
**Draft PR:** [#5](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/pull/5)
**Branch:** `feat/sg-01-central-cavern-portable-export`

## Root cause: `/place template` succeeded but placed nothing

The exported templates wrote block-state palette entries as `{Name, Properties}`. Minecraft 26.3 reads
structure-template palette entries as `{id, properties}` (compare the game's own `igloo/top.nbt`, `DataVersion` 5023).
With the old keys the game still finds and loads the template, and `/place template` still prints
`Loaded template ... at 0, 100, 0`, but every palette entry decodes to air, so no block is written.

Evidence, all from the real Minecraft 26.3 server (`server.jar` SHA-1 `33680f5f…`, `world_version` 5023,
`pack_version.data_major` 121, Java 25) with the exact same data pack:

| Observation | Result |
|---|---|
| `datapack list enabled` | `file/sg01 (world)` enabled; namespace `moreminecrafts`, template ids resolve (not a loading problem) |
| Live probes after `/place template` with `Name`/`Properties` | 15/15 `SG01_TEMPLATE_PROBE_nn_MISS` in the server log (run 45 artifact) |
| `fill 0 100 0 40 116 40 air` after placing | `No blocks were filled`, so nothing was written (not a probe problem) |
| Same NBT with only `Name`→`id`, `Properties`→`properties` | All probes pass, jigsaw block entity data (`pool`, `target`, `name`, `joint`) intact |
| Minecraft's version, `DataVersion`, `pack_format`, origin, chunk loading, world height | All correct, ruled out |

Fix: `structure_export/structure.py` now writes `id`/`properties` and rejects the old keys. Tests pin the schema
(`test_palette_uses_minecraft_26_3_keys_not_legacy_name_properties`, `test_legacy_name_palette_is_rejected`).

## Other defects found and repaired

1. **Wrong Jigsaw seam model (exporter).** `connect_templates` and the visual assembler assumed the chamber and tunnel
   connectors share one cell. Vanilla places the child connector in the cell *in front of* the parent connector. The
   corrected tunnel origins are north `[18,0,-15]`, east `[41,0,18]`, south `[18,0,41]`, west `[-15,0,18]` (relative to the
   chamber), giving a 71 × 17 × 71 assembly of 8,575 solid blocks. Minecraft generated exactly 8,575 blocks; the old model
   predicted 8,443 and 69-wide bounds. The preview GLB/PNGs and `validation-report.json` were regenerated.
2. **Saved-world path (harness).** Minecraft 26.x stores the Overworld at `world/dimensions/minecraft/overworld/region`, not
   `world/region`. The `cp` in run #45 failed on that path, so saved-chunk probes had never run.
3. **Saved-chunk decoding (harness).** Chunk palettes use `{id, properties}` or, for a block without properties, a bare string
   (a `{"": value}` wrapper in mixed lists). Default-valued properties (`facing=north`, `orientation=north_up`, …) are omitted
   when saving, and walls get game-derived connection properties. `probe-world.py` now compares block id and every
   expected property, accepting an omitted property only when it equals the known default.
4. **Jigsaw probe assumptions (harness).** `/place structure` ignores the y of the command: the structure's `start_height`
   (absolute −40…−20) decides the height, and the game picks the rotation. `probe-jigsaw.py` reconstructs the expected assembly
   from the templates and finds the rotation/offset in the saved chunks; all blocks must match and no extra structure block may
   exist. Rotation rotates stair `facing` too.
5. **Connector forceload (harness).** Connector test origins at x=100…190 were not force-loaded (`That position is not loaded`).

## Probes versus placement: how they are separated

* **Controls** run first (`control-placement`): vanilla `minecraft:igloo/top` (shipped in the game jar) and a 3 × 3 × 3
  `sg01_control:cube` built by this repo's exporter in a *separate* control pack. A probe or harness fault shows up here, not as
  an SG-01 failure. An earlier control miss was a real probe error (the igloo's first snow block is at local `[0,0,3]`, not `[0,0,0]`).
* **Live probes:** one `execute in minecraft:overworld if/unless block … run say` pair per non-air palette state; the marker is
  read from the server log.
* **Saved chunks:** after `save-all flush` the Anvil region files are decoded independently.
* A successful `/place` response, exported NBT or a synthetic render is never treated as proof of placement.

## Current verdicts

| Stage | Vanilla 26.3 server, local run | GitHub Actions (Fabric Loom fixture) |
|---|---|---|
| Server start, data pack `file/sg01` enabled | PASS | PASS ([run #53](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39097876094), head `5af87be`) |
| Control placement (vanilla igloo + exporter cube) | PASS | PASS ([run #53](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39097876094), head `5af87be`) |
| `/place template` main chamber, 15 live probes | PASS 15/15 | PASS ([run #53](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39097876094), head `5af87be`) |
| Saved-chunk probes (15 states) | PASS 15/15 | PASS ([run #53](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39097876094), head `5af87be`) |
| Connector templates place | PASS | PASS ([run #53](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39097876094), head `5af87be`) |
| `/place structure` Jigsaw assembly | PASS: 8,575/8,575 blocks, 0 extra, rotation 180°, bounds 71 × 17 × 71 | PASS ([run #53](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39097876094), head `5af87be`) |
| Native client screenshots | Needs the graphical CI fixture | PASS ([run #53](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39097876094), head `5af87be`) |

Screenshots: ten native Minecraft 1280×720 PNGs per run, in the `sg-01-minecraft-26.3-visual-<run id>` artifact (30 days). Viewed:
plaza, north entrance, interior overview, balconies/columns and the exterior from outside. The exterior shows the chamber placed
directly at `0,100,0`, so it floats above the flat test world; the Jigsaw assembly itself is verified by block data, not by
screenshot. Two earlier camera bugs (a view facing away from the chamber, and a player falling to the terrain during the capture
delay) were harness errors, fixed in `capture-session.sh`. Full passes: run #49 (`7de32d3`), #51 (`b172d04`), #53 (`5af87be`).

The local run drove the same `run-acceptance.sh` against the unmodified vanilla server jar via `SG01_SERVER_CMD`. The
Fabric/client screenshot path remains the existing native `Screenshot.grab` harness.

## Screenshot acceptance

The capture method is unchanged: a test-only Fabric client entrypoint calls Minecraft's native `Screenshot.grab(...)` after
the client world and renderer are ready. The first camera is the central plaza at `[20,102,20]`; further views start only
after the plaza PNG is saved, is nonempty and is 1280×720. Screenshots are accepted only after direct block verification
succeeds.

## Historical results

- [Run #37](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091006597): ten PNGs, but they show the empty flat world (consistent with the palette bug).
- [Run #39](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091506040): `/place structure` returned success; the check was invalid.
- [Run #41](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39091758916): verdict invalid (log-path mismatch).
- [Run #45](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39092916208): live probes ran for the first time and reported 15/15 `MISS`, which exposed the palette bug; saved-chunk copy failed on the 26.x region path.

The harness is test-only. No gameplay systems, mobs, bosses, loot, research features, or cavern redesign are included.
PR #5 remains **Draft** and **unmerged**.
