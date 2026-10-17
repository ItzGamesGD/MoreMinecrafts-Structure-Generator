# SG-01 visual model

This is a block-derived view of the actual five exported structure NBT templates, assembled at the four checked Jigsaw connector coordinates. The standalone `sg-01-central-cavern.glb` includes the central room and all four connecting tunnels; it embeds the texture atlas and can be downloaded by itself.

## Open and inspect

- **Browser/mobile:** open [`index.html`](index.html) from a static web server. It uses Google's `<model-viewer>` from unpkg, so the viewer page needs internet access. Drag to rotate, scroll or pinch to zoom, and use two fingers to pan. The GLB itself is separate and self-contained.
- **Any GLB viewer:** download [`sg-01-central-cavern.glb`](sg-01-central-cavern.glb) and open it in a glTF 2.0 viewer, such as Blender, Windows 3D Viewer, or an online glTF viewer. The binary GLB embeds all textures.
- **Repository preview:** the PNG files below are 1200 × 900 renders of triangles read back from the GLB. They use representative block colors for clarity; the interactive model contains the embedded block texture atlas.

## Preview images

- [Exterior isometric overview](exterior-isometric.png)
- [Interior view from the central plaza](interior-central-plaza.png)
- [Elevated view of balconies and support columns](elevated-balconies-supports.png)
- [Top-down overview](top-down-overview.png)
- [Sectional cutaway](sectional-cutaway.png)
- [Jigsaw connection diagnostic with seam markers](jigsaw-connections-diagnostic.png) — markers are kept out of the clean GLB and architectural renders.

## Rebuild

From the repository root, install the export dependency and run:

```bash
python3 -m pip install -r requirements-export.txt
PYTHONPATH=vendor/mcbuild/src python3 examples/forgotten_kingdom/export_visual.py
```

The script reads the committed NBT files under `datapack/data/moreminecrafts/structure/...`, composes the four checked joins, writes the GLB, reads that GLB back to render the PNGs, and emits `validation-report.json`. Re-running it produces byte-identical files in this environment.

## Validation and limits

`validation-report.json` records source NBT SHA-256 hashes, each tunnel origin/rotation and shared boundary, block counts, coordinate bounds, and the GLB vertex count. The assembled solid bounds are x/z −14 through 54 and y 0 through 16 (69 × 17 × 69 coordinate span); room and tunnel templates share the connector plane, owned by the chamber in this assembled view. The clean model contains 8,443 unique solid block positions. All four tunnels are represented.

The GLB uses vendored vanilla block textures. SG-01's non-full blocks are `stone_brick_stairs` and `deepslate_brick_wall`: stair-facing direction and half-block shape are modeled, while stair inner/outer corner variants are rendered as straight stairs; wall post/arms are inferred from adjacent wall blocks because template palettes omit neighbor-derived wall connections. The wall texture uses `deepslate_bricks`, and stairs use `stone_bricks`, as the closest matching vanilla base textures. All other present blocks use their matching texture where available. No slabs, fences, entities, or mobs occur in these templates. The PNG renderer shades GLB triangles with representative colors rather than sampling textures; use the GLB for textured inspection.

Static source-coordinate and GLB-bounds checks pass. The GitHub Actions workflow also rebuilds the datapack and visuals and byte-compares both outputs with committed artifacts. Actual Minecraft 26.3 template loading and world generation remain a separate runtime check.
