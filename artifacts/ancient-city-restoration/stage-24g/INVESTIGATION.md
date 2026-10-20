# Stage 24-G — How restored functional blocks disappear during Ancient City generation (Minecraft 26.1.2)

Status keys: **VERIFIED** = read in the decompiled 26.1.2 server code *and* reproduced cell-for-cell in real generated
worlds; **VERIFIED (code)** = read in the code, consistent with every observation; **HYPOTHESIS** = consistent with the
evidence but the exact code path was not isolated.

Sources: `server-26.1.2.jar` (sha1 `83eb1106f12f24c9127ce22070d71853157af127`, unpacked from the bundler
`server.jar` sha1 `97ccd4c0ed3f81bbb7bfacddd1090b0c56f9bc51`), decompiled with Vineflower 1.11.1; data files read from
the same jar and committed as fixtures in `tests/fixtures/stage24g/`.

## 1. The pipeline the eight restored modules go through

All eight templates are entries of `minecraft:ancient_city/structures`
(`data/minecraft/worldgen/template_pool/ancient_city/structures.json`), each a `single_pool_element` with
`"processors": "minecraft:ancient_city_generic_degradation"`, `"projection": "rigid"`. No other pool references them.

`SinglePoolElement.getSettings()` builds the `StructurePlaceSettings` used at placement (VERIFIED (code)):

| order | processor | effect |
|---|---|---|
| 1 | `BlockIgnoreProcessor.STRUCTURE_BLOCK` | drops structure blocks |
| 2 | `JigsawReplacementProcessor` | jigsaw -> its `final_state`; **`structure_void` -> `null` (cell not written)** |
| 3 | `block_rot` (`integrity 0.95`, `#minecraft:ancient_city_replaceable`) | drops 5 % of tagged blocks |
| 4 | `rule` | deepslate_bricks/tiles -> cracked (30 %), soul_lantern -> air (5 %) |
| 5 | `protected_blocks` (`#minecraft:features_cannot_replace`) | never overwrites chests/spawners/... already in the world |
| — | `setKnownShape(true)`; `placeInWorld(..., flags 18)` | no shape updates, no neighbour updates at placement |

`#minecraft:ancient_city_replaceable` = deepslate, deepslate_bricks, deepslate_tiles, deepslate_brick_slab,
deepslate_tile_slab, deepslate_brick_stairs, deepslate_tile_wall, deepslate_brick_wall, cobbled_deepslate,
cracked_deepslate_bricks, cracked_deepslate_tiles, gray_wool. Doors, ladders, beds, chests, barrels, polished
deepslate (+ walls/slabs), chiseled deepslate, deepslate **tile stairs**, polished basalt, glass and soul lanterns are
not in it.

## 2. block_rot — VERIFIED

`BlockRotProcessor.processBlock`: `random = settings.getRandom(pos)`. `SinglePoolElement` never sets a random, so
`StructurePlaceSettings.getRandom(pos)` returns `RandomSource.create(Mth.getSeed(pos))` — a **fresh
`LegacyRandomSource` seeded only by the world position**. The block is dropped when the *original* template state is
tagged and `nextFloat() > 0.95`. `RuleProcessor` likewise seeds a fresh source from `Mth.getSeed(pos)`.

Consequences (all VERIFIED):
* Decay depends only on the world position, not on the world seed or the piece. The same cell of the same piece at the
  same position decays identically in every variant — which is what makes Stage 24-F vs 24-G comparisons exact.
* A dropped block is **not replaced by air**: nothing is written, so whatever noise generation, carvers or earlier
  features left in that cell stays (air, sculk, dripstone, terrain).
* The tag is checked on the *original* state, so a jigsaw is never rotted even when its `final_state` is a tagged block.
* Adding a block to a generic tag does not exempt anything: the only exemption is *not being in*
  `#ancient_city_replaceable`, and that tag is shared by every Ancient City piece — changing it would change the whole
  city (stop condition), and type-based exemption cannot tell a railing from decorative masonry of the same type.

Evidence:
* `tools/stage24g/processors.py` re-implements `Mth.getSeed`, `LegacyRandomSource` and the processor chain.
  `investigation/jvm-rng-crosscheck.txt` runs the real `net.minecraft.util.Mth`/`RandomSource` classes in jshell
  against the server jar: seeds and floats match bit-for-bit (unit-tested).
* `investigation/f24-processor-replay.json`: every block of every restored piece in the 24 Stage 24-F cities was run
  through the model and compared with the saved world — **91,118 cells: 72,285 placed as predicted, 15,211 placed and
  later turned to sculk by sculk-patch features, 3,410 predicted rotted and absent (+1 rotted cell whose terrain happened
  to be the same block), 0 predicted-placed blocks missing except the 211 cells in §6.**

## 3. Door survival — VERIFIED (mechanism) / HYPOTHESIS (last step)

`DoorBlock.canSurvive`: the lower half needs a face-sturdy block below; the upper half needs the lower half.
`DoorBlock.updateShape` turns a lower half into air when the block below changes and it can no longer survive, and an
upper half into air when its lower half is no longer a door.

`medium_ruin_1` and `small_ruin_1` stand their entrance door directly on the module's `connect_structure` jigsaw, and
that jigsaw (preserved unchanged from vanilla) has `final_state: minecraft:structure_void`. `JigsawReplacementProcessor`
returns `null` for it (VERIFIED (code)), so **the cell under the door is never written**: it holds whatever terrain the
cave had. In the 24 Stage 24-F cities the cell was unwritten in all **48** placements of these two modules
(`investigation/f24-functional-survival.json`): air in 30, a sculk vein in 16 — the door stands on nothing — and, by
chance, a sculk catalyst or dripstone block in 2.

Seed 24007, `medium_ruin_1` at (-264,-50,928): the support cell holds a sculk vein, the **lower door half is gone and the
upper half floats** — the same in the Stage 24-C and 24-F worlds. The lower half was removed after placement; which
update re-evaluated it (worldgen `WorldGenRegion.setBlock` does not propagate neighbour updates, post-processing only
touches marked positions) was not isolated: **HYPOTHESIS** — a later shape update on the lower half (canSurvive false).
Whatever the trigger, a sturdy block in that cell makes `canSurvive` true, which removes the failure.

The other door modules (large_ruin_1, medium_ruin_2, small_ruin_2) rest their doors on a jigsaw whose `final_state`
is `cobbled_deepslate`; jigsaws are never rotted, so those supports are always written.

## 4. Ladder attachment — VERIFIED (code + worlds)

`LadderBlock.canSurvive` needs a sturdy face at `pos.relative(facing.getOpposite())`; `updateShape` drops the ladder
when that neighbour changes. `medium_pillar_1` hangs 7 ladders on `deepslate_bricks` and 1 on `deepslate_tiles`,
`large_pillar_1` one on `deepslate_tiles` (12 on polished basalt, untagged). In Stage 24-F the backing block was rotted
under 12 ladders across the sweep (12 of 696 ladder placements); the ladder remains (known shape) but floats and breaks on the first neighbour update.

## 5. Railings, decks, upper floors — VERIFIED

Deck floors (`deepslate_tiles`), the large watchtower's 1-high deck parapet (plain `deepslate`) and the edge walls and
floor of `medium_ruin_2`'s upper storey (`deepslate_bricks`/`deepslate_tiles`) are tagged, so 5 % of them vanish. In
Stage 24-F block_rot removed 55 of 1,717 role-protected railing cells and 74 of 1,658 elevated walking-floor cells
across the 24 cities (holes and gaps over 2–13 block drops).
`medium_pillar_1`'s deck railing is `polished_deepslate_wall` (untagged) and was never affected.

## 6. Losses the processors do not explain (211 cells) — VERIFIED as later features

| cells | what | cause |
|---|---|---|
| 189 | plain `deepslate` of pillar/sauna foundations -> tuff / gravel / ores / dripstone | underground ore and blob features of a neighbouring chunk run after the piece was placed (deepslate is `#base_stone_overworld`) |
| 5 | white candles in the sauna, same block, other state | candle count/lit state changed after placement |
| 1 | `medium_ruin_1` door lower half, seed 24007 | §3 |

Interaction accessibility: beds, chests and barrels are not tagged and are never dropped by the processors; their
access cells can be affected only by terrain left in unwritten cells (§7).

## 7. NBT contents vs processors vs terrain

The restored templates (like the vanilla ruins they replace, which store 16–38 blocks and no air) do not store air in
their rooms. `StructureTemplate.placeInWorld` writes only stored blocks, so every unstored cell keeps natural terrain:
noise terrain is mostly carved by the city's `beard_box` adaptation, but features that ran before the city (dripstone
clusters, geodes) or after it (lava springs/flows, ores) remain. That is how `medium_ruin_1` (seed 24005) is filled with
dripstone, `large_ruin_1` (24009) gets a dripstone cluster in its hall and `small_ruin_1` (24008) gets lava in its room.
See `TERRAIN-CLASSIFICATION.md`; fixing it means clearing terrain in the template's interior cells (owner decision).
