# Ancient City peak-era: approved modules only

**Status:** individual building BLUEPRINT CANDIDATES; not yet original-NBT aligned, visually approved, or merged. This is **not** a whole-city restoration.

Approved mappings:
- `chamber_1/2/3` → three variant single-family residences.
- `camp_1/2/3` → three variant residences, some retaining blue/cyan wool canopy and raised camp-platform vocabulary.
- `tall_ruin_1/3` → priest churches with tall deepslate towers and brewing stands.
- `tall_ruin_2/4` → two-story residences.

Each folder contains a **standalone sandbox Python mcbuild DSL blueprint** with the same module basename as the vanilla jigsaw piece. The authoring entrance faces +z conceptually; paths were intentionally kept independent.

All blueprints are **new interpretations** based on the user-approved role mapping, not geometric restoration verified against each vanilla Java 26.3 NBT. The actual vanilla footprints, junctions, jigsaw connectors, block palettes, and module-by-module transforms remain to be measured before any worldgen integration.

Approved palette emphasizes `deepslate_bricks`, `deepslate_tiles`, `polished_deepslate`, `polished_basalt`, blue/cyan accents, and `soul_lantern`. Bed, doors, ladder and brewing stand are illustrative functional blocks, not gameplay hooks.

## Hard scope fence

Do not add any other original Ancient City structure, city center, streets, arena, death/nether variants, jigsaw placement, Fabric world generation, mobs, gameplay or global restore. Do not merge until user visual review.

## Render/export

From repository root with vendored mcbuild installed:

```bash
vendor/mcbuild/.venv/bin/python tools/render_approved_ancient_modules.py
```

Output goes to `out/ancient-city-approved-modules/<piece>/` with `render.png`, `candidate.schem`, `report.json`, and combined `summary.json`. These are *candidates*, not final approvals. This batch covers **exactly 10** pieces.
