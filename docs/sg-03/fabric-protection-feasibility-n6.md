# SG-03-N6 — Fabric worldgen protection hook: feasibility study (design and research only)

**Status: DESIGN ONLY. No Java, no Mixin, no datapack, export, geometry, CI threshold or existing-PR change is part of this study.**
Stacked on PR #20 (SG-03-N5). Related: #18 (integration baseline), #19 (N4 clay fix, structure step 10).
Nothing in the validation plan (section 8) has been run; every test named there is **NOT RUN**.

**Recommendation: CONDITIONAL GO** (section 9). A small server-side Mixin module is technically feasible and, on the evidence of the
26.3 sources, can be made independent of chunk-generation order, non-blocking and deadlock-free. It leaves the approved datapack architecture,
so it needs an explicit owner decision, a short prototype spike and the conditions listed in section 9 before any implementation.

Labels: **[VERIFIED]** read directly in the Mojang-named Minecraft 26.3 sources or the Fabric artefacts named below;
**[ASSUMED]** reasoned but not executed or not directly visible in the source; **[N5-DATA]** measured earlier in this repository.

## 0. Sources and versions

* Minecraft 26.3 (`net.minecraft.*`, Mojang names; 26.x is not obfuscated, so there is no intermediary or Yarn mapping layer). Sources:
  Loom `genSources` output `minecraft-merged-7e9a32a5b8-26.3-sources.jar` from `validation/minecraft-visual` (project fixture; not committed).
  [VERIFIED] `validation/minecraft-visual/build.gradle` uses `minecraft "com.mojang:minecraft:26.3"` with no mappings dependency.
* Fabric Loader `0.19.5`, Fabric API `0.161.0+26.3` (gradle cache), Fabric Loom `1.17.21` (`gradle.properties`), Sponge Mixin fork
  `net.fabricmc:sponge-mixin:0.17.4+mixin.0.8.7`. [VERIFIED] present in the Gradle cache of the existing fixture.
* Paths below are relative to `net/minecraft/` in the 26.3 sources; line numbers are those of that source jar.
* Older names do **not** carry over. Examples verified in 26.3: `Feature` is an interface whose `place` takes four arguments (no `FeaturePlaceContext`, no
  `ConfiguredFeature` wrapper); features are records; `ChunkStatus` lives in `world.level.chunk.status`; `ResourceLocation` is `Identifier`;
  Fabric's `ServerWorldEvents` is `ServerLevelEvents`.

## 1. Confirmed Minecraft 26.3 implementation details

### 1.1 Entry points of geode and monster-room generation [VERIFIED]

| Item | Class / member | Notes |
|---|---|---|
| Geode | `world.level.levelgen.feature.GeodeFeature` — `public record GeodeFeature(... int minGenOffset, int maxGenOffset, ... int invalidBlocksThreshold) implements Feature`; `public boolean place(WorldGenLevel level, ChunkGenerator chunkGenerator, RandomSource random, BlockPos origin)` (L78) | Writes inside `BlockPos.betweenClosed(origin+minGenOffset, origin+maxGenOffset)` (L133); vanilla config: -16..16, i.e. a hard 33-block cube. Writes via `Feature.safeSetBlock` (L145-200 of GeodeFeature). Aborts when more than `invalidBlocksThreshold` of its 4-6 sample points are air or `#geode_invalid_blocks` (L98). |
| Monster room | `world.level.levelgen.feature.MonsterRoomFeature` — `public record MonsterRoomFeature() implements Feature`; `place(...)` (L35) | Write box `origin + [-(xr+1)..xr+1] x [-1..4] x [-(zr+1)..zr+1]`, `xr,zr` in 2..3. Uses both `level.setBlock(wallBlock, AIR, 2)` (L76, **bypasses `safeSetBlock`**) and `safeSetBlock`; also sets a spawner (L115) and chests with loot (L107-108). |
| Common write helper | `Feature.safeSetBlock(WorldGenLevel, BlockPos, BlockState, Predicate<BlockState>)` (`Feature.java` L37), a `default` interface method | Does `level.setBlock(pos, state, 2)`. |
| Dispatcher | `world.level.levelgen.placement.FeaturePlacer.place(...)` (private, L38 ff.); the call `feature.place(this.level, this.generator, random, nextPos)` | Positions come from placement modifiers (`count`, `in_square`, `height_range`, ...), so the origin is always inside the chunk being decorated. |
| Per-step driver | `world.level.chunk.ChunkGenerator.applyBiomeDecoration(WorldGenLevel, ChunkAccess, StructureManager)` (L338). Only caller: `ChunkStatusTasks.generateFeatures` (L133-144). Overridden only by `DebugLevelSource`. | For each decoration step: first `structureManager.startsForStructure(sectionPos.x(), sectionPos.z(), structure).forEach(start -> start.placeInChunk(...))` for the structures of that step, then the biome features of that step. |
| Where the level is a `WorldGenRegion` | `server.level.WorldGenRegion implements WorldGenLevel` (L67); created in `ChunkStatusTasks.generateFeatures` (L137) | `/place feature` instead calls `feature.place(ServerLevel, ...)` (`server.commands.PlaceCommand` L233). |

Consequence for the N5 failures: within one chunk the step order is deterministic (geode step 2, monster room 3, structure `top_layer_modification` 10),
which is what N4 exploited; the remaining damage is cross-chunk.

### 1.2 How features write across chunk boundaries [VERIFIED]

* `ChunkPyramid.GENERATION_PYRAMID`, `FEATURES` step (`world.level.chunk.status.ChunkPyramid` L24-29): requires `STRUCTURE_STARTS` within radius 8,
  `TERRAIN` within radius 1, and `blockStateWriteRadius(1)`.
* `WorldGenRegion.ensureCanWrite(BlockPos)` (L297) allows a write only if the target chunk is within `blockStateWriteRadius` (1) of the centre
  chunk; otherwise it returns `false` (and logs in IDE). `WorldGenRegion.setBlock(BlockPos, BlockState, int, int)` (L322) is the single choke point:
  it calls `ensureCanWrite`, then `ChunkAccess.setBlockState`, creates block entities (or writes a `DUMMY` tag for proto chunks, L343-355) and
  marks post-processing. So a feature whose origin is in chunk C may write into the 3x3 chunks around C.
* A neighbour chunk only has to reach `TERRAIN` before C decorates (direct dependency list). It does **not** have to be undecorated or decorated:
  no mutual exclusion on "who decorates first". Structure pieces are clipped to the chunk being decorated (`ChunkGenerator.getWritableArea`, L434, passed
  to `StructureStart.placeInChunk`, `StructureStart.java` L79-100: `next.getBoundingBox().intersects(chunkBB)` then `postProcess(...)`). Hence a chunk's structure
  blocks exist only after that chunk was decorated. [N5-DATA] matches: damage appears exactly when a neighbour is decorated later.

### 1.3 Scheduling and threading [VERIFIED]

* `server.level.ChunkMap` constructs `ConsecutiveExecutor worldgen = new ConsecutiveExecutor(executor, "worldgen")` (L189) and
  `worldgenTaskDispatcher = new ChunkTaskDispatcher(worldgen, executor)` (L192). `util.thread.AbstractConsecutiveExecutor` runs **one task at a time** (an atomic
  `Status` SLEEPING/RUNNING, `pollTask`, `run`). `ChunkMap.runGenerationTask` (L652-657) submits `task.runUntilWait()` to that dispatcher.
  `ChunkGenerationTask.runUntilWait` -> `scheduleLayer` -> `GenerationChunkHolder.applyStep` -> `ChunkMap.applyStep` (L617) -> `ChunkStep.apply` ->
  `ChunkStatusTasks.generateFeatures`, all synchronous inside that task. So **feature decoration of different chunks in one dimension never runs
  concurrently**; the order is decided by the dispatcher's priority queue (ticket levels) and by when dependency futures complete.
  This is why N5's order matrix and the `-Dmax.bg.threads=1` runs were order-dependent but not fully deterministic: the pool size is irrelevant to that serialisation; timing of
  asynchronous steps (light, other tasks) changes the order. Per dimension there is one such executor. [ASSUMED] that no other mod re-parallelises it.
* `WorldGenRegion.getChunk(x, z, status, loadOrGenerate)` (L131-157) never generates or waits: it returns a chunk from the pre-acquired `StaticCache2D` if
  the requested status is not after the maximum allowed by the step's `directDependencies()` for that distance, otherwise it **throws** a `ReportedException`
  ("Requested chunk unavailable during world generation"). `WorldGenRegion.hasChunk(x, z)` (L160) is the safe pre-check. So querying neighbour data cannot start
  chunk generation, block, or create a circular wait; the only failure mode is that exception.

### 1.4 Structure starts, Jigsaw pieces, bounding boxes [VERIFIED]

* Starts are created in `ChunkStatus.STRUCTURE_STARTS` (`ChunkStatusTasks.generateStructureStarts` L44, `ChunkGenerator.createStructures`) — **before** biomes, terrain
  and features, and for Jigsaw structures the complete assembly (all 21 SG-03 pieces, rotations, bounding boxes) is already computed there.
  Starts of loaded chunks come from `loadStructureStarts` (L59) / chunk NBT.
* `STRUCTURE_REFERENCES` (`ChunkGenerator.createReferences`, L616): for every chunk, looks at the starts in chunks within +-8 and records in that chunk a
  reference (`structure -> LongSet` of start chunk keys) when `start.getBoundingBox()` intersects the chunk column (L629-633).
  Read with `ChunkAccess.getAllReferences()` (L232) / `getReferencesForStructure`; starts via `ChunkAccess.getStartForStructure(Structure)` (L200).
* `world.level.StructureManager` (L31): `forWorldGenRegion(WorldGenRegion)` (L42); `startsForStructure(int sectionX, int sectionZ, Predicate<Structure>)` (L50),
  `startsForStructure(sectionX, sectionZ, Structure)` (L64), `fillStartsForStructure(...)` (L71, silently skips a null/invalid start),
  `structureHasPieceAt(...)` (L162-174, tests each piece's bounding box), `getAllStructuresAt(...)` (L176).
* `levelgen.structure.StructureStart` (L22): `getBoundingBox()` (union, L69), `getPieces()` (L146), `isValid()` (L118), `getStructure()` (L142), `getChunkPos()` (L122).
  `StructurePiece.getBoundingBox()` (L110) is public; `PoolElementStructurePiece` (L27) exposes `getElement()`, `getPosition()`, `getRotation()` (L135-148);
  `SinglePoolElement.getTemplateLocation()` (L195) and `getBoundingBox(StructureTemplateManager, BlockPos, Rotation)` (L130). Templates:
  `MinecraftServer.getStructureTemplateManager()` (L~1957), whose repository is a `ConcurrentHashMap` (`StructureTemplateManager` L48).
* SG templates fill their whole cuboid (explicit air for empty cells; `docs/sg-01/README.md`) and are placed without an air-ignoring processor
  (`SinglePoolElement.getSettings` L164 uses only `BlockIgnoreProcessor.STRUCTURE_BLOCK` and `JigsawReplacementProcessor`), so each piece's bounding box is
  exactly the set of cells the structure writes. [N5-DATA]/SG-01-B consistent: template-air cells are rewritten to air and geode cores/dungeon interiors showed up as air replacements of structure blocks (62-207 cells per run). [ASSUMED] for any future template that is sparse.

### 1.5 When is structure information available relative to features? [VERIFIED]

From the pyramid dependencies (1.2) and 1.4: whenever `generateFeatures` runs for chunk C, all chunks within 8 have at least `STRUCTURE_STARTS`, and C and its 8
neighbours have `STRUCTURE_REFERENCES` (they are at least `TERRAIN`, which comes after it). The starts, and thus every piece's exact box, of any structure that can
touch C's 3x3 write zone are therefore **always present, independent of generation order**, even when the structure blocks themselves have not been written yet.

Subtle limit: a reference in neighbour chunk R (distance 1 from C) may name a start chunk S up to 8 from R, i.e. 9 from C, and `getChunk(S, STRUCTURE_STARTS)` is only permitted
up to distance 8 (`ChunkStatus.MAX_STRUCTURE_DISTANCE = 8`, `ChunkStatus.java` L16). For SG-01/02/03, `max_distance_from_center` is 64/112 blocks and the measured start
BB is about 107 blocks wide [N5-DATA], so S is within 7-8 chunks of any chunk it touches. The guard must check `hasChunk`/distance before reading and treat a start it cannot
read as "unknown" (section 7).

### 1.6 Fabric hook availability [VERIFIED for the names listed]

* Fabric API 0.161.0+26.3 (all module jars in the cache searched for class names containing `PlacedFeature`, `WorldGenRegion`, `ChunkGenerator`, `Decoration`,
  `BiomeModifications`, `ServerChunkEvents`, `ServerLifecycleEvents`, `ServerWorldEvents`): there is **no event around feature placement or block writes during worldgen**.
  `BiomeModifications` (fabric-biome-api-v1; class present, semantics from the public API and [ASSUMED] not re-read) works per biome, not per position, and so cannot implement a guard without disabling or replacing the
  feature. `ServerChunkEvents.Generate`/`Load` fire per chunk, not per feature, and are not usable to prevent an overwrite. [ASSUMED] their exact timing; irrelevant as they are
  post-hoc.
* Usable Fabric API pieces: `ServerLifecycleEvents.EndDataPackReload` / `StartDataPackReload` (cache invalidation), `ServerLifecycleEvents.ServerStarted` (self-check),
  `ServerLevelEvents.Load/Unload` (per-dimension state), `CommonLifecycleEvents.TagsLoaded` (read a structure tag).
* Therefore protection requires **Mixin** (Sponge Mixin 0.17.4 in the Fabric toolchain). Injection points, with exact 26.3 signatures:
  1. `GeodeFeature#place(WorldGenLevel, ChunkGenerator, RandomSource, BlockPos)` — `@Inject(at = @At("HEAD"), cancellable = true)` returning `false`.
  2. `MonsterRoomFeature#place(WorldGenLevel, ChunkGenerator, RandomSource, BlockPos)` — same.
  3. (backstop only) `WorldGenRegion#setBlock(BlockPos, BlockState, int, int)` — `@Inject(at = @At("HEAD"), cancellable = true)` returning `false`.
  Both feature classes are `record`s and `WorldGenRegion` is a normal class; none is a Fabric-API-owned type. [ASSUMED] Mixin applies cleanly to the two records on this Loader/Mixin
  combination (records are final; HEAD injection into an instance method should work) — to be proven in the spike (section 9, condition 2). `Feature` is an interface with a default
  `safeSetBlock`; mixing into default methods is possible but unnecessary and should be avoided.

## 2. Candidate comparison

A: feature-level collision guard. B: protected block-write interception. C: precomputed protection index (derived from starts/references). The recommended design is **C feeding A
(primary) with B as an optional backstop**.

| Criterion | A. Guard at `Feature.place` HEAD | B. Filter in `WorldGenRegion.setBlock` | C. Index (data source for A/B) |
|---|---|---|---|
| Reliability under any chunk order | **High**: decision is made from starts/references, which exist regardless of whether the structure blocks do (1.5). Works for both "structure first" and "feature first" orders. | Medium: works only when the structure region is known at write time; identical inputs; but outcome is partial features. | Required by A and B; no effect alone. |
| Atomicity (multi-block features, block entities) | **Whole instance cancelled before any write**: no half geodes, no orphaned spawner/chest/loot tables. | Poor: a geode clipped by the structure; a dungeon whose spawner write is rejected but whose `getBlockEntity(origin)` / chest loot lookup then run on a non-spawner block (L107-117), logging errors or touching an unrelated block entity. Partial dungeon walls remain. | n/a |
| Exactness of the protected volume | Coarse: cancel if the feature's hard write box (geode +-16; dungeon +-5) intersects any protected piece box. Over-cancels vanilla features that would not have touched the structure but lie within that reach. | **Exact** (per cell, `piece.getBoundingBox().isInside`). | Piece boxes are exact for SG (1.4). |
| Thread safety / deadlock | Runs inside the serialised worldgen task (1.3); read-only access to immutable starts; no waits; `getChunk` cannot generate. No deadlock path. | Same, but runs on every `setBlock` in every generation step: must be an O(1) rejection when not in a feature scope. | Immutable data; cache needs a concurrent map only if other threads read it. |
| CPU and memory | Per attempt: <= 9 reference-map lookups, 0-N start dedupe, <= 21 box tests. Monster room: 10 + deep attempts per chunk in step 3. Fast path when the 3x3 has no protected reference. No persistent memory. | Hot path (millions of writes per chunk); needs a scope flag (ThreadLocal or a field on the region) to stay cheap. | Optional cache of per-start box lists; ~21 boxes per structure. |
| Compatibility with other worldgen mods | Medium-high: `@Inject` + `cancellable` on two final records; no `@Overwrite`/`@Redirect`; other Mixins on the same method coexist. Other geode/dungeon-class features from other mods are covered automatically (class-level). | Lower: `WorldGenRegion.setBlock` is a popular target; many mods and Fabric API itself may touch it; a scope guard is required to avoid affecting their writes. | High (no Mixin). |
| Implementation complexity | Low-medium (two injections, one shared helper). | Medium-high (scope tracking, block-entity consistency). | Low (a helper using only `StructureManager`). |
| Maintenance across MC updates | Medium: depends on 4 stable-looking signatures and on the names `startsForStructure`/`getChunk`; 26.x already changed the Feature API once. Mixin `require = 1` makes breakage loud. | Higher: `setBlock` internals change often. | Low. |
| RNG parity | Cancelled instances do not consume the feature's random numbers, so later *attempts of the same placed feature in the same chunk* diverge from vanilla. Everything outside chunks that have a protection hit is bit-identical. | Preserves consumption inside the feature, changes only block reads afterwards. | n/a |
| Residual damage if the index is wrong | Fail-closed possible (cancel when unknown). | Fail-open only. | n/a |

Rejected variants: **dry-run/buffering proxy** (run the feature against an overlay level and discard if it touches protected cells) — exact and RNG-preserving but needs
a full `WorldGenLevel` delegate (about 60 methods plus block-entity reads) and is fragile across versions; keep as a possible refinement if over-cancellation proves unacceptable.
**Custom replacement feature types** registered by the mod and substituted into biomes via `BiomeModifications`: global replacement of vanilla geodes and rooms, excluded by the brief.

## 3. Preferred protection algorithm (design)

Server-side, stateless, no persisted data.

1. **Configuration.** A structure tag `moreminecrafts:protected_from_overlays` (JSON under `data/moreminecrafts/tags/worldgen/structure/`) lists protected structures
   (initially `moreminecrafts:forgotten_kingdom/central_cavern`). A data-driven tag keeps the Java free of identifiers and lets future structures opt in. Missing or empty tag => module inactive (log once).
2. **Hook.** `GeodeFeature.place` and `MonsterRoomFeature.place` HEAD: `if (!(level instanceof WorldGenRegion region)) return;` (commands, other mods' levels are untouched).
3. **Reach box** `R` (hard upper bounds taken from the feature itself, so config changes follow automatically):
   geode `[ox+minGenOffset, ox+maxGenOffset]^3` from the record accessors (vanilla +-16, horizontal and vertical); monster room `x,z in [ox-4, ox+4]`, `y in [oy-1, oy+4]` (xr, zr <= 3, +1 wall).
4. **Candidate chunks.** Chunks overlapped by `R` horizontally, clamped to the write zone (`|dx|,|dz| <= 1` from the centre chunk) — the centre's 3x3.
5. **Lookup** (per chunk, only if `region.hasChunk(x, z)`): `chunk.getAllReferences()` -> for each `(Structure, LongSet)` whose `Structure` is in the protected tag (resolve once per server start / tag reload into an
   `IdentityHashMap`/`Set<Structure>`) -> each start chunk key; skip duplicates; skip keys whose Chebyshev distance to the centre chunk exceeds `ChunkStatus.MAX_STRUCTURE_DISTANCE`
   and record "unknown" (see 7); fetch the start with `region.getChunk(sx, sz, ChunkStatus.STRUCTURE_STARTS).getStartForStructure(structure)`; a null or `!isValid()` start for a listed reference is "unknown".
6. **Test.** For each valid start: for each `StructurePiece`, `piece.getBoundingBox().intersects(R)` (use the piece box, **not** the start's union box: the union is far larger than the written volume).
   If any piece intersects, or the result is "unknown" (fail-closed), return `false` from `place` (this is exactly vanilla's "feature did not place").
7. **Backstop (optional, phase 2 of implementation).** While a guarded feature runs, set a scope marker (field on the region or a ThreadLocal set in the HEAD hook and cleared at every RETURN/exception path);
   a HEAD hook on `WorldGenRegion.setBlock` rejects writes whose position lies inside a protected piece box only while that scope is set. With step 6 correct this never fires; its purpose is to
   contain mistakes (for example a feature type other than geode/dungeon added later) and to give a loud metric when it does.
8. **Metrics/logging.** Counters per feature: attempts, fast-path skips, cancellations, "unknown" decisions, backstop hits; log at INFO on server stop and at WARN on any unknown/backstop event.

Properties: the decision depends only on structure starts (always present), so it is the same for both orders of a pair of adjacent chunks; the structure's own placement is unchanged
(N4 step 10 stays); features outside the reach box are unaffected, and chunks with no protected reference are bit-identical to vanilla.

## 4. Protection policy

| Element | Policy | Basis |
|---|---|---|
| Walls, floors, ceilings, pillars, balconies | Protected: all cells of the piece box (the box is exactly the written cuboid, 1.4) | SG templates cover their box |
| Jigsaw corridors and passages (tunnel pieces, door cells) | Protected as pieces (including the jigsaw cells that become air) | pieces are in `getPieces()` |
| Template air (rooms, halls, stairwells) | Protected (a geode core or dungeon floor placed in air is also a corruption: 62-207 air cells in [N5-DATA]) | box covers air |
| Trial spawners, chests, barrels, lecterns, other block entities | Protected as part of the box; the whole-instance cancellation means no block entity of a vanilla feature is ever created next to them | A before any write |
| Natural terrain between pieces, outside piece boxes, the structure union box, the surrounding rock | **Not protected**; vanilla geodes/rooms generate there | pieces only |
| Halo / margin | None for protection; the margin exists only in the *reach test* (a feature whose possible volume reaches a piece is cancelled) | keeps rock outside the shell vanilla where the feature's volume cannot reach |
| Which features | Class-level: `GeodeFeature`, `MonsterRoomFeature` (also covers other mods' placed features of these types). Other features (ores, vegetation, sculk, lakes) are out of scope; N4/F-2 already handled clay and sculk via the step | brief |

Cost of the policy (expected, to be measured): vanilla geodes whose +-16 cube reaches a piece and monster rooms within 5 blocks of a piece are not generated. [ASSUMED] with vanilla rarity (1/24 per chunk for
geodes) about two to three geodes per structure footprint (about 60-70 chunks within 16 blocks) — a rounding error of vanilla geode density, but not zero.

## 5. Thread safety, performance, deadlock analysis

* **Concurrency** [VERIFIED 1.3]: the hook executes inside the dimension's single worldgen task; no two decorations of the same dimension overlap. The guard only reads immutable data
  (`StructureStart`, `PiecesContainer`, `BoundingBox` are not mutated after creation; `StructureStart.cachedBoundingBox` is `volatile`). Any cache the module adds should be a
  `ConcurrentHashMap` keyed by `(structure, start chunk)` with weak/size-bounded values, or no cache at all (the per-attempt cost is small enough, to be measured).
* **Deadlock / blocking** [VERIFIED 1.3]: the guard never waits on a future and never calls an API that can schedule generation; `WorldGenRegion.getChunk` throws instead of generating.
  There is no circular dependency, because queries are restricted to chunks already inside the step's pre-acquired cache.
* **Exception safety**: wrap lookups so that `ReportedException`/`IllegalStateException` become "unknown" -> cancel the instance (never propagate into chunk generation). Do not catch broadly around vanilla code.
* **CPU** [ASSUMED, to benchmark]: monster rooms are the hot case (`count: 10` plus the deep variant, every chunk). With no protected reference in the 3x3 the cost is 9 map reads. Near a structure, add <= 21 `intersects` tests per
  distinct start. Expected well under 1% of chunk decoration time. Memory: none persistent.
* **Server stalls**: none expected; no IO. Template parsing is not needed (boxes only).

## 6. Existing-world compatibility

| Scenario | Behaviour | Status |
|---|---|---|
| New world with module | All decisions made from fresh starts; full protection. | design |
| Existing world, module added | The module stores nothing and changes no format. Chunks already at `FEATURES` are never revisited, so existing damage stays; damage in them is **not** repaired automatically (by requirement). New chunks adjacent to old structure chunks are protected, because the references/starts of old chunks are loaded from NBT (`loadStructureStarts`) and are visible to new chunks' reference lookups. | design; [ASSUMED] for starts of structures generated by earlier datapack versions |
| Partially generated structure | Starts exist from `STRUCTURE_STARTS` onward and are persisted with the proto-chunk NBT; the guard uses them for the not-yet-decorated chunks. Already-decorated chunks keep what they have. | design |
| Existing chunk next to a newly generated chunk | New chunk's geode volume may reach into an old structure chunk: protected via reference lookup (the new chunk's references include the old start). | design |
| Server restart mid-generation | Stateless guard: after restart, `LOADING_PYRAMID` reloads starts, generation resumes; no module state to recover. A restart can change the generation order (that is already true in vanilla); the guard makes the result independent of it. | design |
| Mod installed later / removed | Removal returns to current N5 behaviour for new chunks; nothing stored needs cleanup. Players who rely on the protection need the mod on the server for every future chunk. Clients need nothing (server-only, no registry entries, no network) [ASSUMED: the module registers nothing]. | design |
| Datapack changed or `/reload` | Structure tag is re-read on `EndDataPackReload`; if a future template is no longer a full cuboid the exactness argument must be revisited. Existing starts keep their recorded pieces. | design |
| Player-modified structures | The module never writes blocks or repairs; it only declines vanilla features. Player edits are untouched. No retroactive reconstruction. | design |
| Other dimensions | Works wherever a protected structure is generated; the module must not assume the overworld. | design |

## 7. Failure modes and safe fallbacks

| # | Failure | Detection | Safe behaviour |
|---|---|---|---|
| 1 | Missing structure-start information (reference without a readable start) | start null / invalid / chunk not available | **Fail-closed** for the instance: cancel the feature, count + log once per chunk. A structure start that is simply absent gives no reference and no protection (cannot be detected; equals today's behaviour). |
| 2 | Incomplete Jigsaw placement data (empty or partial piece list) | `getPieces().isEmpty()` | Fall back to `start.getBoundingBox()` for the reach test (coarser, over-cancels); log. |
| 3 | Concurrent chunk generation | none expected in one dimension [VERIFIED serial] | If a future version parallelises decoration, the read-only design remains safe; the optional scope marker must then be per-region, not global. Add a startup assertion that the executor is still consecutive (spike). |
| 4 | Circular chunk dependencies | impossible by construction (no blocking calls) | none needed; `ReportedException` from an out-of-range read is converted to "unknown" -> cancel. |
| 5 | Feature partially completed before cancellation | cancellation is at HEAD, before any write | not applicable to tier 1. For tier 2 (backstop) a rejected write inside a started feature can leave a partial feature: log WARN, and treat as a bug to fix in tier 1 rather than a normal path. |
| 6 | Block-entity consistency | tier 1 creates none; tier 2 may reject a spawner/chest write whose follow-up code runs on a non-matching block | prefer tier 1; do not ship tier 2 until its dungeon behaviour is tested; never edit block entities in the module. |
| 7 | Conflicts with other Mixins | startup failure of an `@Inject` (target not found) or incompatible `@Overwrite`/`@Redirect` by another mod | use only `@Inject` with `require = 1` in a mixin config that is `required: true`, so an unsupported combination **crashes at startup with a clear message** instead of silently running unprotected; document mod-compat list; do not use `@Redirect`/`@Overwrite`. |
| 8 | Mod absent on the server | cannot be detected by the datapack | accepted limitation; document that the SG datapack is only "overlay-safe" with the module. Optionally the module logs at start that protected structures are active. Without it, behaviour equals the current N5 state. |
| 9 | Unsupported worldgen version (26.4+, other MC) | `fabric.mod.json` `depends: minecraft = 26.3` exact; Mixin `require=1` | refuse to start rather than run unprotected; add a CI job that compiles and runs the lab against each new MC version before bumping. |
| 10 | Unexpected structure/feature registry changes (renamed structure id, tag removed, new Feature type for geodes) | tag empty / structure not found | module inactive with a WARN (never crashes worldgen); the lab test (section 8) fails loudly because overlays reappear. |
| 11 | Protected structure's template becomes sparse (cells not written) | static test on templates (reuse `tests/`), run in CI | switch the reach test to exact cells via the template cell mask (design option) or document over-protection. |
| 12 | `/place feature`, command or other-mod levels | `level instanceof WorldGenRegion` false | unchanged vanilla behaviour (intentional). |

## 8. Proposed future validation plan (all items NOT RUN)

Reuse the N5 laboratory (`validation/minecraft-visual/sg03-natural/collision_lab.py`, `run_natural.py`) with a Fabric server (the fixture already starts the Loom
`runServer` for the traversal probe) loading a build of the module. Retain all strict failure conditions of `assert_n4.py`.

1. **Order matrix.** Seeds 173 and 42; sites (-19,15), (-18,36), (4,13), (6,-19); the eight orders `rowmajor`, `rowmajor_rev`, `colmajor`, `colmajor_rev`, `spiral_out`, `spiral_in`, `random:1`, `random:2`.
   Acceptance: zero mismatched structure blocks and zero foreign blocks in template air in every run. Baseline (unmodified) result to compare: 17 of 32 runs corrupted [N5-DATA].
2. **Repetition under concurrent load.** Each site/order repeated at least 5 times, with 3 parallel servers and with `taskset` limited to 2 cores, since timing changed N5 outcomes.
3. **Integrity set.** Per run: all 21 pieces, rotations and bounding boxes equal to the unmodified control for the same seed (start signatures), exact block and air-volume integrity, trial spawner block/entity
   consistency, persistence after 200 ticks, no clay-family overwrite (N4), no sculk shrieker.
4. **Vanilla preservation.** Count geodes (amethyst/calcite/budding blocks) and monster rooms (spawners) in the same loaded area **outside** the reach boxes with and without the module, for the same orders; require parity
   outside chunks that have a protection hit and report the number of cancelled attempts near the structure (cost of the policy).
5. **RNG parity.** Hash chunk NBT of chunks with no protected reference, module vs unmodified: expect identical.
6. **Negative controls.** (a) Module present but tag empty -> overlays reappear (proves the lab detects them). (b) Backstop disabled/enabled. (c) A synthetic structure without the tag is not protected.
7. **Existing-world tests.** World generated without the module (damage present) opened with the module: new chunks adjacent to old structure chunks protected, old chunks unchanged byte-for-byte; module removed again; server killed
   mid-generation (kill -9 during forceload of the region) then restarted; datapack `/reload` with a modified tag; `/place structure` followed by neighbours generating.
8. **Failure injection.** Remove the start of one chunk (corrupt NBT copy) to exercise "unknown"; run with an out-of-range reference; load alongside a second Mixin mod that also injects at HEAD of `GeodeFeature.place`.
9. **Performance.** Worldgen throughput (chunks/s, p95 per-chunk decoration time) for a 200x200-chunk pregeneration, module vs unmodified, with and without protected structures in range; target < 1% overhead (hypothesis, not a result).
10. **Multi-structure and dimension cases.** Two SG structures within 16 chunks; structure in a dimension other than the overworld if reachable.
11. **Compatibility.** Matrix of Fabric API 0.161.0+26.3 only, plus the next MC snapshot as an early warning (expected to fail loudly).

## 9. Recommendation

**CONDITIONAL GO** — implement only after the following are satisfied; otherwise treat as NO-GO and keep N5 option 1/2.

What supports GO [VERIFIED]: structure starts/pieces/boxes exist for every neighbour before any feature runs; decoration is serial per dimension; neighbour reads cannot generate or block; `Feature.place` HEAD injection cancels a
feature atomically with no block-entity or loot side effects; piece boxes equal the written cuboid; no datapack or Fabric API alternative exists.

Conditions:
1. **Owner decision** to leave the pure-datapack architecture (a server-side Fabric module, shipped separately from the datapack; server operators must install it). Without that decision this stays a study.
2. **Prototype spike** (one day, in a throw-away branch): prove that `@Inject` into the two records applies on Loader 0.19.5/Mixin 0.17.4, that cancelling at HEAD yields the expected N5 matrix results, and measure RNG parity and overhead. Stop and re-evaluate if Mixin cannot target the records.
3. **Accept the documented costs**: vanilla geodes and rooms within the reach box of a protected piece are cancelled; sequences of random numbers diverge from vanilla in chunks with a protection hit; protection exists only where the module is installed.
4. **Fail-loud packaging**: exact Minecraft version dependency, `require = 1`, and a CI job that runs the section-8 order matrix against the modded server (no relaxation of `assert_n4.py`).
5. **Scope discipline**: tier 1 only at first; tier 2 (write filter) only after its dungeon block-entity behaviour is tested.

Not covered / remaining unknowns: effect on other vanilla structures (unmeasured); behaviour with other worldgen mods; real overhead; whether the chosen reach boxes over-cancel too much (alternative: dry-run proxy); whether the owner accepts server-side modding.

## Appendix — source index (26.3, Mojang names)

| Topic | File : lines |
|---|---|
| Decoration driver, per-step structures then features | `world/level/chunk/ChunkGenerator.java` 338-432; `getWritableArea` 434 |
| References (radius 8) | `ChunkGenerator.java` 616-646 |
| FEATURES / STRUCTURE_* steps and dependencies | `world/level/chunk/status/ChunkPyramid.java` 11-33; `ChunkStatusTasks.java` 44, 59, 66, 133-144; `ChunkStatus.java` 16-27 |
| Write zone, `getChunk`, `hasChunk`, `ensureCanWrite`, `setBlock` | `server/level/WorldGenRegion.java` 89-111, 131-163, 297-361 |
| Serial worldgen executor | `server/level/ChunkMap.java` 189-192, 617-665; `util/thread/AbstractConsecutiveExecutor.java` 16-95; `server/level/ChunkTaskDispatcher.java` 86-92; `server/level/ChunkGenerationTask.java` |
| Feature API | `world/level/levelgen/feature/Feature.java` 20-60; `placement/FeaturePlacer.java` 28-85 |
| Geode / monster room | `feature/GeodeFeature.java` 33-210; `feature/MonsterRoomFeature.java` 23-120 |
| Structures | `world/level/StructureManager.java` 31-185; `levelgen/structure/StructureStart.java` 22-150; `StructurePiece.java` 110; `PoolElementStructurePiece.java` 27-160; `pools/SinglePoolElement.java` 130-200 |
| Template manager | `levelgen/structure/templatesystem/StructureTemplateManager.java` 39-95; `server/MinecraftServer.java` ~1957 |
| Fabric | Loader 0.19.5; API 0.161.0+26.3 (`fabric-lifecycle-events-v1 4.1.9`, `fabric-biome-api-v1 20.0.9`); Sponge Mixin 0.17.4+mixin.0.8.7 |
