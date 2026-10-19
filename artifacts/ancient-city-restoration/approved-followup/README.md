# Ancient City: three NBT-backed approved follow-up structures

Scope: ONLY barracks, ice_box_1, small_statue. Pillar and ruin families remain deferred for later city-layout decisions. Previously approved ten modules and the Warden landmark remain unchanged.

## Locked mappings

| Vanilla structure | Peak-era use | Hard requirement |
| --- | --- | --- |
| barracks | Armoury | Original exterior and shrine remain; the space *below the new surface hatch* is a true underground room, not a ground-floor extension. Stocked weapons/armour, ladders, workstations, basement supports. |
| ice_box_1 | Refrigerated food and grain store | Original ice, iron trapdoor and ladder stay; simple tiled shelter roof and wall repairs complete the cold store. Wheat, seeds, raw meat and fish are stocked in food barrels inside. |
| small_statue | Conservatively restored small shrine | Keep original statue silhouette, candles and structural layout; only tiny corner-edge repairs. |

## Source and evidence

- Exact original Minecraft Java 26.1.2 NBTs via [pinned mirror commit](https://github.com/InventivetalentDev/minecraft-assets/tree/bb6d6451fb5fff54d3930fd8bf19d81200f00e6d/data/minecraft/structure/ancient_city/structures). The three original Git blob SHA-1 hashes are verified at download time. No original binaries committed.
- The restoration modifies original NBT block positions directly, and freezes **all original jigsaw positions, block states and NBT**. The selected source sizes stay identical.
- barracks original y=0..3 is mostly solid deepslate; the approved basement is a **new intentional excavation**, not an original room.
- ice_box_1 original ladder: (11,1..3,4) and original iron trapdoor: (11,4,4).
- Raw Structure candidate.nbt is the main deliverable and carries containers / block entities. Sponge v3 candidate.schem and render.png are visual review outputs and do not promise inventory preservation.

## Regeneration

    vendor/mcbuild/.venv/bin/python tools/render_approved_ancient_followup.py

Output folder: out/ancient-city-followup/<module>/{candidate.nbt,candidate.schem,render.png,report.json}, plus interior_cutaway.png for barracks and ice_box_1; aggregate summary.json.

## Validation and limits

Verified by executable tests: pinned original source blobs; in-bounds writes; original jigsaws, chests, lantern shrine fixtures, food-cellar iron trapdoor/ladder unchanged; native NBT reload; material export; 4-angle image rendering. Architecture still requires real Minecraft placement checks, particularly barrel ItemStack NBT semantics and worldgen processors. This is a prototype, NOT merged production world generation. No city streets, monuments, extra buildings, PR or merge.


## ice_box_1 entrance and access repair

Root cause in the prior candidate: its excavation carved away the original ladder backing at `(11,1..3,5)`, leaving the north-facing ladder at `(11,1..3,4)` unsupported. The repair preserves those original polished-basalt blocks and cuts a two-block-high west turn through `x=10`, joining the existing pantry at `z=6`.

The original iron trapdoor at `(11,4,4)`, ceiling lever at `(11,3,3)`, and stone pressure plate at `(11,5,5)` remain in place. The pressure plate powers its original support block at `(11,4,5)`, adjacent to the hatch. The lever powers its ceiling support at `(11,4,3)`, also adjacent to the hatch. Validation models these vanilla neighbor-power paths and the closed/open signal states; it does not run a Minecraft redstone tick or survival interaction.

A compact threshold frames the existing hatch at `x=11,z=4`: deepslate brick shoulders at `(10,5,4)` and `(12,5,4)`, blue-ice accents directly above, and soul lanterns at `(10,5,5)` and `(12,5,5)`. These stay inside the 19×10×15 template and clear the central player route. Original ice states, containers, dimensions, ladder, hatch, redstone fixtures and all jigsaw block entities/states are asserted unchanged.

The repair validator reconstructs the exact base-branch `ice_box` candidate as the before case, requires its ladder/access checks to fail, then requires the repaired route and fixtures to pass. It exports and reloads native NBT and Sponge v3 schematic and creates four-direction, entrance, top-down, cutaway and before/after previews.

All checks are static geometry, block-state preservation, or a simple redstone adjacency model. Actual Minecraft client gameplay and survival-mode interaction remain NOT TESTED.
