"""Generation step of the Forgotten Kingdom jigsaw structure, shared by the SG-01/02/03 builders.

Minecraft places a step's structures *before* that step's biome features, and features of later steps afterwards, so a
structure can only avoid being overwritten by a feature that targets blocks it contains if it generates in a later step.
Verified against the vanilla 26.3 biome data (feature step index in parentheses):

* ``amethyst_geode`` (2), ``monster_room`` (3), ``sculk_patch_deep_dark`` / ``sculk_vein`` (7),
* ``lush_caves_clay`` (9, in ``vegetal_decoration``; it replaces moss blocks with clay, water and big dripleaf).

``top_layer_modification`` (10) is the last step, so it follows every one of them within a chunk. It does not stop a
neighbouring chunk's feature from writing into this chunk after it was decorated (cross-chunk order is not guaranteed).
"""

STRUCTURE_STEP = "top_layer_modification"

# N10-R: PR #19 moved all three packs to STRUCTURE_STEP, but the lush-cave clay overwrite it fixes was demonstrated for SG-03 only (docs/sg-03/clay-resolution-n4.md).
# SG-01 and SG-02 are restored to the generation steps they had before PR #19 (values read from the integration baseline 282b74d); SG-03 keeps STRUCTURE_STEP.
SG01_STEP = "vegetal_decoration"
SG02_STEP = "strongholds"
