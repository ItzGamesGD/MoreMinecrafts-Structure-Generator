# SG-03-N3: Selective lush-caves clay A/B (experimental)

Stacked Draft branch on PR #13. No changes to structure geometry, committed export, source builder, parent PRs or main.

## Verified Minecraft 26.3 candidate

The vanilla `CavePlacements` registry uses `minecraft:lush_caves_clay` with 62 placement attempts. Its `CountPlacement` codec accepts zero. The treatment adds **only** `data/minecraft/worldgen/placed_feature/lush_caves_clay.json` to a byte-identical copy of the SG-03 control datapack. It retains the original configured feature reference and sets `minecraft:count` to zero.

References:
- https://mc-packet-reference.netlify.app/26.x/source/net/minecraft/data/worldgen/placement/caveplacements/
- https://mc-packet-reference.netlify.app/26.x/source/net/minecraft/world/level/levelgen/placement/countplacement/

## Protocol

Run fresh official SHA-1-verified Minecraft 26.3 servers independently with seed 42, two natural candidate sites, identical candidate selection and chunk-loading order, and 200 ticks. Never use /place. Save the complete Jigsaw start signatures (template, rotation, bounding box and position) and reject comparisons if any start differs. Compare **all** expected moss-to-actual-clay coordinates at candidate chunk (4,13), before and after ticks. Do not hardcode a 47-cell count: 46 and 47 have both been observed. Preserve JSON and logs for both arms.

Positive evidence: same starts, positive control clay count, and zero treatment clay replacements. This supports a causal role for the placed feature **under this seed and loading order**. Negative evidence: clay persists. Invalid: changed starts, missing baseline, tick-unstable coordinates, or server/data errors. A green experimental CI does not mean SG-03 natural integrity PASS.

Important caveat: changing a placement modifier can alter downstream decoration RNG. Further replication may be required before a permanent design decision. Do not merge, whitelist mismatches or modify the production datapack automatically.
