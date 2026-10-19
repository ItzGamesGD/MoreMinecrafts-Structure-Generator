# Stage 24-D — visual review gallery (read-only)

Open `gallery/index.html` (offline, no server, no external requests) or unzip `stage-24d-offline-gallery.zip`. Decisions: `OWNER-REVIEW.md`.
Inputs: the **final Stage 24-C** NBTs (`artifacts/ancient-city-restoration/stage-24b/*/restored.nbt` at Stage 24-C head `b92a4be…`, verified byte-identical) —
see `INPUT-MANIFEST.json` (source blob SHA-1s, candidate SHA-256, dimensions, jigsaw and block-entity preservation, Stage 24-C repair diff vs PR #10).
No structure NBT, generator, gameplay behaviour or prototype was modified; the CI workflow fails if `stage-24b/` changes.

## Rendering method and fidelity (read this before judging materials)
* **Not Minecraft-client screenshots.** No rendering client was run.
* Renderer (`tools/stage24d/viewer.js`, three.js in headless Chromium/SwiftShader): vanilla 26.1.2 **blockstates, block models (including parents, element rotation, multipart) and textures read from the official client jar**
  (sha1 `4e618f09…`). Stairs, slabs, walls, doors, ladders, candles, lanterns (hanging/standing), glass (translucent) and water (tinted, 14/16 height) use the real models; orientation is exact.
* Approximations: **flat studio lighting** with vanilla per-face factors (no block/sky light, no ambient occlusion, no emissive glow), orthographic camera, jigsaws replaced by their `final_state`
  (as in generation), beds/chests/skulls (entity-rendered in the game) rebuilt from the entity textures with the standard box UV unwrap (close but not identical), water not animated, sculk shown with its first texture frame.
* The blocky figure beside entrances is a flat-colour 1.8-block scale reference, not a skin.
* Cutaways are made by removing blocks (roof layer / half-space), not by clipping planes; floor-by-floor views remove everything above the stated Y.
* V1 reference homes (chamber_1–3, tall_ruin_2/4) are the approved *blueprint* prototypes executed through the vendored sandbox (`reference-inputs/`, unchanged copies), not NBT.
* V5 "generated" pieces come from the Stage 24-C real 26.1.2 worldgen worlds (stored in `generated-pieces/`). For each building I picked the sampled piece with the **most** lost critical blocks, so it is a worst-case-leaning sample, not an average (averages are in Stage 24-C `EVIDENCE-TABLES.md`).

## Counts
132 JPEG images: per building 7 exterior + 2 interior cutaways + 2–4 floor views + 2 original-vs-restored + 2 V5 = 111 in total, plus 21 priority sheets (V1 two sheets, V2, V3, V4).
Missing / blocked: real client screenshots and in-game lighting (blocked: no rendering client); nothing else was skipped.

## Reproduce
`tools/stage24d/{manifest,render_gallery,priority,v5,build_gallery}.py` with `MC_ASSETS` pointing at the extracted client `assets/` folder; or run `.github/workflows/stage24d-gallery.yml`.
