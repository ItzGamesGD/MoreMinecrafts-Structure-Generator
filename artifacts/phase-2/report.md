# mcbuild + Codex Cloud — Phase 2 report

## Overall verdict: **PASS**

All mandatory stages completed using the current vendored snapshot, with no external LLM
service. The control artifact is reproducible using the included harness.

## Results

1. **Starting repository SHA:** `f15ab6764baabf01936a22714479e9fc6e6b7305`.
2. **Vendored upstream SHA:** `34ce86372d4c23f4d83d4e24fc256cb399d6c3e3`.
3. **Runtime:** Python 3.12.13; uv 0.7.22; Ubuntu 24.04.4 LTS, Linux 6.18.44,
   x86_64.
4. **Dependencies:** PASS. `uv sync --frozen --extra dev` completed from the vendored
   lockfile, and imports of mcbuild, Pillow, NumPy, and nbtlib passed.
5. **Blueprint execution:** PASS. The sandbox executed
   `control/blueprint.py` with fixed seed 0 into a real `VoxelGrid`.
6. **Structure:** 334 populated cells; bounds `(0,0,0)..(6,11,6)`; dimensions
   7 wide × 12 high × 7 long. Materials are 171 cobblestone, 74 red wool, 49 stone,
   and 40 stone bricks. Programmatic probes confirmed the centered south doorway is empty
   at `x=2..4, y=1..3, z=0`, corresponding locations in the opposite wall are populated,
   and the interior probe `(3,5,3)` is empty.
7. **Renderer:** PASS. mcbuild's actual `build_contact_sheet` generated four isometric
   yaw views at 0°, 90°, 180°, and 270°. The PNG is 1100 × 275 pixels.
8. **Headless status:** pure software (NumPy/Pillow rasterizer); no GPU, `DISPLAY`, X11,
   or Xvfb was used or required.
9. **Render:** `artifacts/phase-2/control/render.png` (SHA-256
   `42443a3c277c79d2e3f7025cbf5d3354c9b259892143d371ed417896384b2f37`).
10. **Actual Codex visual inspection:** PASS. Codex opened the produced PNG through its
    image-view capability rather than inferring from logs. It visibly shows a tall square,
    tower-like cobblestone structure in four rotations. A centered three-block-wide,
    three-block-tall doorway is apparent in two views. Stone-brick vertical corner pillars
    are clearly distinct on all visible corners. The red two-tier cap is strongly
    contrasting and has gray corner finials. No obvious missing geometry, texture
    corruption, transparency artifact, or framing/clipping defect is present. The doorway
    reads somewhat light because the far interior wall is visible through it, but its
    rectangular opening remains recognizable. The clean multi-view image is useful for a
    future AI visual-review loop.
11. **Schematic export:** PASS. The real `mcbuild.export.schem.export_schem` wrote Sponge
    Schematic v3. `nbtlib` loaded it back; version, DataVersion, 7 × 12 × 7 dimensions,
    and expected palette entries passed round-trip validation.
12. **Schematic:** `artifacts/phase-2/control/final.schem`, 258 bytes. (The exporter
    uses gzip metadata, so compressed-file bytes are not asserted deterministic across
    runs; decoded dimensions, palette, and voxel data are.)
13. **External LLM/API:** none contacted. No LLM client was instantiated and no key was
    requested.
14. **Added files:** deterministic harness under `tools/phase2_validate.py`; environment,
    audit, report, blueprint, render, schematic, and machine-readable structure report
    under `artifacts/phase-2/`. No file under `vendor/mcbuild` was changed.

## Exact reproduction commands

From repository root:

```bash
cd vendor/mcbuild
uv sync --frozen --extra dev
uv run python -c "import mcbuild, PIL, numpy, nbtlib; print('mcbuild import smoke: OK')"
cd ../..
uv run --project vendor/mcbuild python tools/phase2_validate.py
uv run --project vendor/mcbuild pytest -q vendor/mcbuild/tests
```

The harness assertions validate block count/bounds/materials/interior/doorway, render
non-emptiness, schematic existence and size, and the nbtlib round-trip metadata and
palette. Visual inspection remains a deliberate human/Codex vision step after opening
`artifacts/phase-2/control/render.png`.
