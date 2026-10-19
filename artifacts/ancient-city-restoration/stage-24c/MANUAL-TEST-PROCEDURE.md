# Manual Minecraft-client procedure (for everything that stays LIVE PENDING / VISUAL PENDING)

No Minecraft client with rendering was run in this stage, so screenshots and physical pointer/keyboard interaction are
**not** claimed. The server-side and simulated-player evidence is in `gameplay/`, `placement/` and `worldgen/`.
To complete the client-side review on Minecraft Java 26.1.2:

1. Create a creative **Superflat** world (cheats on). Install this branch's structures as a data pack:
   copy each `artifacts/ancient-city-restoration/stage-24b/<module>/restored.nbt` to
   `world/datapacks/s24c/data/s24c/structure/<module>.nbt` plus a `pack.mcmeta`
   (`"min_format": 101, "max_format": 101`), then `/reload`.
2. Stand on flat ground and run `/place template s24c:<module> ~ ~ ~` (append `clockwise_90`, `180`, `counterclockwise_90`
   to test rotations). Press **F3+G** to see chunk borders.
3. For every module take the screenshots listed in `VERIFICATION-MATRIX.md` ("client screenshots needed").
4. Houses: open the door, walk to every room, sleep in each bed (set `/time set night`), open every barrel, and for
   `medium_ruin_2` walk the east-rising stair run to the upper floor and back down.
5. Towers: climb the ladder from the ground entrance to the deck, then try to walk off every deck edge (it should be impossible).
6. Sauna: enter at the south reception, open all three chests (loot must roll), swim in both basins, wait 60 s and confirm no
   water has left the 43 original cells.
7. Real generation: use the datapack in `tools/stage24c/worldgen.py` (`make_pack`) which overrides
   `data/minecraft/structure/ancient_city/structures/<module>.nbt`, create a world with seed `24002`, run
   `/execute in minecraft:overworld run tp @s 960 -40 -768`, then explore the city; `medium_ruin_2` is at about (874..884, -51..-44, -793..-778).
