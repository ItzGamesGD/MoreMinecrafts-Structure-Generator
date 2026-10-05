# Vendored mcbuild source audit

## Completeness and installation

The snapshot identifies upstream commit
`34ce86372d4c23f4d83d4e24fc256cb399d6c3e3`. It contains the package source,
tests, lockfile, project metadata, bundled blockstate definitions and textures, and the
NeoForge integration. The inventory contains 2,238 files under `src/mcbuild` and occupies
approximately 177 MiB; no evidence of an incomplete snapshot was found. The supported
installation is `uv sync --extra dev`, with `uv.lock`; `pyproject.toml` requires Python
3.11 or newer.

## Narrow deterministic pipeline

1. **Blueprint representation:** a Python-like DSL source string/file. The sandbox parses
   its AST, strips imports, rejects unsafe access, injects only its standard primitives,
   and executes within line/time budgets.
2. **Execution:** `mcbuild.dsl.sandbox.run_blueprint(source, VoxelGrid(), seed=0)`.
   Primitives such as `floor`, `walls`, `fill`, `clear`, and `set_block` populate the real
   sparse, palette-indexed `VoxelGrid`.
3. **Rendering:** `mcbuild.render.views.build_contact_sheet` calls mcbuild's camera and
   raster pipeline. The implementation uses NumPy and Pillow for pure-software mesh
   rasterization and bundled block textures. It imports no windowing or GPU framework.
   Image-file output does not require a terminal display mode, GPU, `DISPLAY`, X11, or
   Xvfb.
4. **Export:** `mcbuild.export.schem.export_schem` converts the same grid into an NBT,
   gzip-compressed Sponge Schematic v3 file with DataVersion 3953 via `nbtlib`.
5. **Minecraft/Java:** neither is part of this narrow path. Java/NeoForge is solely an
   optional live-world integration under `mod/`; Minecraft was not launched.

## LLM boundary and bypass

The normal CLI imports `OpenRouterClient`; that wrapper uses the OpenAI SDK with an
OpenRouter base URL and reads `OPENROUTER_API_KEY`. The agent loop asks that client for
blueprint/tool calls and visual critique. The deterministic validation bypasses the CLI,
agent loop, and `mcbuild.llm` package entirely: it calls the sandbox, renderer, and
exporter interfaces directly. No API key is required, and no external inference request
was made.

## Audit conclusion

The narrowest source-supported headless route is:

`blueprint.py -> run_blueprint -> VoxelGrid -> build_contact_sheet -> render.png`

and, from the same grid:

`VoxelGrid -> export_schem -> final.schem`.

No vendored source file was modified.
