# MoreMinecrafts Structure Generator

This repository keeps the vendored `mcbuild` voxel authoring engine and adds a separate portable export layer for vanilla
Java structure templates and world-generation datapacks. The adapter reads `mcbuild.VoxelGrid` and the existing block
palette directly; it does not replace the generator or require its runtime when Minecraft consumes the exported pack.

## SG-01: Forgotten Underground Kingdom

The first prototype is a built central cavern (41 × 17 × 41 blocks) with a plaza, four support piers, a continuous upper
walkway, stairs, a sealed floor and roof, and four 3 × 4 tunnel mouths. The Jigsaw start room connects to four tunnel
templates that end in named district sockets for future content.

The reproducible datapack is under `exports/sg-01/forgotten-underground-kingdom/datapack/`. It uses the `moreminecrafts`
namespace, Minecraft 26.3 structure NBT (`DataVersion` 5023), data pack format 121, an independent structure set, and an
exclusion zone against vanilla Trial Chambers. Built-in `encapsulate` is supplementary terrain adaptation. The structure
uses the `strongholds` generation step as a candidate supported by the referenced 26.3 probe.

See `docs/sg-01/README.md` for the capability audit, design, integration handoff, validation verdicts, and reproducible
commands. `docs/sg-01/structural-evidence.md` contains layer and section previews generated from the exported templates.

## Build and verify

```bash
python3 examples/forgotten_kingdom/build_cavern.py
python3 examples/forgotten_kingdom/preview.py
PYTHONPATH=vendor/mcbuild/src python3 -m unittest discover -s tests -v
```

The export and tests use only the Python standard library plus the bundled mcbuild block registry. An actual Minecraft
26.3 client/server is still needed for in-game loading, world-generation, fluid, and visual validation.
