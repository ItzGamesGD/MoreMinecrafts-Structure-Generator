# SG-01 — Forgotten Underground Kingdom central cavern

## Capability audit

The trusted local base was branch `work` at `5ca7d731d8b4111ba3c674876c355bd8b146dbdc`. At that base, the repository
contained a small project README and the vendored mcbuild engine. Its only exporter wrote Sponge Schematic v3 (`.schem`)
through `nbtlib`; no vanilla structure-template exporter or Jigsaw datapack builder existed. This task leaves the
mcbuild engine in place and adds `structure_export/` as a separate adapter and pack builder.

The adapter reads `VoxelGrid` and the existing palette indices directly. It writes gzip-compressed, big-endian Java NBT
using the Python standard library, including a deterministic palette, explicit air for sparse cells, block states,
block-entity compounds, Jigsaw blocks, and an empty entity list. The builder writes `pack.mcmeta`, structure pools,
structure definitions, structure-set placement, and a manifest with SHA-256 checksums and references. No processor list
is needed by this prototype. Authoring scripts and previews live outside the exported datapack.

Minecraft 26.3 constants and JSON forms were checked against MoreMinecrafts-Beta Draft PR #117 and its report. That PR
and repository were read only; no Beta files or branches were changed.

## Design

The main cavern is a fully constructed 41 × 17 × 41 room. Its deepslate and tuff floor, walls, and ceiling enclose a
plaza; four 5 × 5 footed support piers carry the roof; a ring balcony and four stair runs provide upper paths. Four
3-wide × 4-high openings lead into separately serialized tunnels. The north, east, south, and west tunnels are distinct
5 × 9 × 15 / 15 × 9 × 5 templates, each with a matching inward Jigsaw socket and a named far-end socket for future
districts. The template pool and structure identifiers remain under `moreminecrafts:forgotten_kingdom/central_cavern`.

The Jigsaw graph has one start pool and one tunnel pool per direction. The start structure size is 1, so each chamber
socket places its tunnel once; the tunnel's far-end socket uses `minecraft:empty` until a future district is designed.
An independent structure set uses random-spread placement and a 12-chunk exclusion zone against
`minecraft:trial_chambers`. The structure uses the `strongholds` step, `encapsulate`, and a uniform Y range of −40 to −20.
As established in PR #117, encapsulate is supplementary; built geometry provides the actual shell.

No mobs, bosses, rewards, research, puzzles, or custom gameplay are introduced. Future rare rewards remain
`특수아이템(미정)`.

## Reproducible generation

From the repository root:

```bash
python3 examples/forgotten_kingdom/build_cavern.py
python3 examples/forgotten_kingdom/preview.py
PYTHONPATH=vendor/mcbuild/src python3 -m unittest discover -s tests -v
```

The datapack is generated at `exports/sg-01/forgotten-underground-kingdom/datapack/`. To choose another directory, pass
it as the first argument to `build_cavern.py`. It can be copied as-is into a world's `datapacks/` directory; Minecraft
does not need Structure Generator or mcbuild installed to read it.

The `manifest.json` inside the pack lists every resource, file checksum, and resource/connector reference. NBT files,
worldgen JSON, and `pack.mcmeta` are the only vanilla runtime resources; the generator source and preview remain outside
the pack.

## MoreMinecrafts-Beta integration handoff

The export can be placed in a disposable Minecraft 26.3 world's `datapacks/` directory and enabled with vanilla data
pack loading. The public IDs are:

- Structure: `moreminecrafts:forgotten_kingdom/central_cavern`
- Structure set: `moreminecrafts:forgotten_kingdom/central_cavern`
- Start pool: `moreminecrafts:forgotten_kingdom/central_cavern/start`
- Tunnel sockets: `moreminecrafts:forgotten_kingdom/central_cavern/tunnels/{north,east,south,west}`
- Future tunnel target name: `moreminecrafts:forgotten_kingdom/district_entrance`

This does not replace or override vanilla Trial Chambers. Any future implementation in MoreMinecrafts-Beta can consume
the datapack resources directly, without bundling Structure Generator runtime code. This PR does not copy resources into
the Beta repository.

## Validation verdicts

| Check | Verdict | Evidence / limitation |
|---|---|---|
| Direct `VoxelGrid` conversion to structure template NBT | **PASS** | Test round-trip checks size, sorted palette, block-state properties, explicit air, block entities, and empty entities. |
| NBT type encoding and deterministic gzip output | **PASS** | NBT reader/writer round-trip and byte-equality tests. |
| Block-state and block-entity ID consistency | **PASS** | Chest and Jigsaw fixtures; mismatched known block-entity IDs are rejected. |
| Template and worldgen JSON reference validation | **PASS** | Missing templates, pools, and connector target names are rejected by the builder. |
| Four Jigsaw seams, socket directions, and doorway boundaries | **PASS** (static) | Four chamber/tunnel joins have opposing faces and the child connector in the cell in front of the parent connector (vanilla adjacency); 90° rotation math has a separate test. Confirmed against Minecraft 26.3 generation (see below). |
| Built wall, roof, and floor integrity | **PASS** (static) | Generated block-layer tests confirm the constructed shell; only the four 3 × 4 doors break the perimeter. |
| Export reproducibility | **PASS** | Two independently generated packs match byte-for-byte; manifest checksums match each file. |
| Vanilla Trial Chambers exclusion definition | **PASS** (static) | Independent structure set references `minecraft:trial_chambers` with `chunk_count: 12`. |
| Automated tests | **PASS** | `PYTHONPATH=vendor/mcbuild/src python3 -m unittest discover -s tests -v`: 19 tests passed. |
| Existing upstream mcbuild test suite | **NOT RUN** | This task does not modify mcbuild; pytest and its dependencies are not installed in this environment. |
| Minecraft 26.3 explicit placement | **PASS** (Fabric Loom runtime) | Separate controlled tests use `/place template` and `/place structure`: main-chamber live/saved probes 15/15; all tunnel templates load; forced Jigsaw assembly matches 8,575/8,575 blocks at 180°. This is not natural world generation. |
| Natural structure-set generation in normal terrain | **PASS** (seed 173; validated again at final head by Actions run 39109618020) | Minecraft `/locate structure` found candidate `[5184, ~, 4944]`; chunk generation wrote the structure without `/place`. Saved-region probe: 8,575/8,575 blocks, 0 extras, bounds 71×17×71 at `[5169,-37,4929]..[5239,-21,4999]`, rotation 0°. Eight surrounding surface samples had minimum top-solid y=31, above the structure. Artifact includes MCA region files, RCON/server logs, probes, and native entry/plaza screenshots. |
| Cave-air, water, and lava contact | **PASS** (natural, 97 generated sites, 16 seeds; shell intact) with findings | Stage SG-01-B, Actions run 39114506648: cave air touches 86 sites, water 12, lava 10; no wall or interior breach. Fluid enters open tunnel mouths at 5 sites (never the plaza). Later vanilla features overwrite shell blocks at 10 sites (deep-dark sculk incl. summon-capable shriekers at 5). Details and owner decisions: `environmental-stress-validation.md`. |
| Trial Chambers coexistence | **PASS** (sample of 33 pairs, min gap 73 blocks); frequency finding | Exclusion zone is positional and suppresses 67 % of candidates (predicted offline with 0 mismatches). |
| Survival accessibility | Runtime probe **PASS**; live player **NOT RUN**; surface entrance **BLOCKED** | Player-width mob pathfinding: 250/252 interior legs (the 2 failures end in fluid-filled mouths); ring landing needs a jump; 94 % of mouths are sealed by rock. |
| Native client screenshots | **PASS** (current-head run 39109240434) | Ten controlled-placement views plus two native 1280×720 screenshots of the naturally generated entrance and plaza were captured and visually inspected. Owner design acceptance remains pending. |
| Live player traversal and ordinary user-managed world acceptance | **NOT RUN** | Saved block data and teleport-to-camera screenshots do not prove traversal or normal-world pack behavior. See `minecraft-26.3-client-visual-validation.md`. |


## Risks and limitations

- Minecraft 26.3 loading and one natural seed placement are verified; worldgen frequency is lower than nominal (F-3 in the SG-01-B document).
- SG-01-B sampled 16 seeds / 97 sites (see `environmental-stress-validation.md`); no frequency or universal reliability claim. The template contains its walls, floor,
  and roof; `encapsulate` is only supplementary.
- The four district endpoints are intentionally capped with `minecraft:empty` until future district templates are approved.
- The static state parser preserves mcbuild's state strings but does not independently compare every block-state property
  against a live 26.3 registry.
- Native screenshots are available for controlled placement and the natural seed site; no performance measurement was made.
