# SG-03-N2: clay overwrite investigation

Stacked Draft validation branch on PR #12. **No datapack, geometry, room or worldgen design changes.**

Reproduce seed 42 candidate chunk (4,13) in an official Minecraft 26.3 normal world. Preserve all moss-to-clay replacement coordinates, saved biome IDs, room IDs, Y-level counts, bounding boxes and state transitions before and after 200 ticks. Assert 47 affected cells and 21 naturally generated pieces. The dedicated workflow may pass **reproduction** while the original natural-world integrity result remains **FAIL**.

This is not causal proof. A subsequent controlled A/B test that selectively disables suspected vanilla clay-generation features, holding seed and structure placement fixed, is needed before attributing the overwrite. Do not whitelist clay or change the architecture without an owner decision. The five lava cells in seed 173's west tunnel remain a separate open design finding.

Parent evidence: https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/pull/12
