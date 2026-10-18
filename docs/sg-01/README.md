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
| Minecraft 26.3 datapack load and world generation | **PASS** (vanilla 26.3 server) | Server-side only; see `minecraft-26.3-client-visual-validation.md`. Pack enabled, all five templates place, 15/15 live and 15/15 saved-chunk block probes match, and `/place structure` produces 8,575/8,575 expected blocks (180° rotation). |
| Mountain/cave placement, fluids, natural-cave intersections, and in-world Trial Chambers coexistence | **NOT RUN** | Requires actual Minecraft world generation; PR #117 informs placement choices but does not validate this export. |
| In-client visual inspection/screenshots | **NOT RUN** | A text layer and vertical-section preview is provided in `structural-evidence.md`; this is structural evidence, not client rendering. |

## Risks and limitations

- Actual 26.3 codec loading, Jigsaw runtime placement, worldgen frequency, and chunk/biome behavior remain unverified.
- Natural cave and fluid intersections cannot be concluded from static shell checks. The template contains its walls, floor,
  and roof; `encapsulate` is only supplementary.
- The four district endpoints are intentionally capped with `minecraft:empty` until future district templates are approved.
- The static state parser preserves mcbuild's state strings but does not independently compare every block-state property
  against a live 26.3 registry.
- No game screenshots or performance measurements were available in this environment.
