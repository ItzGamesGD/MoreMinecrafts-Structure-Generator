# SG-03 N9 — live Minecraft acceptance

**Stage verdict: PARTIAL.** Not PASS: L10 fails its literal rule, and L3, L8 and L9 are demonstrated only to a partial level (see the table). No production code was changed in this stage (`git diff experiment/sg03-n8r-write-guard -- mod` is empty).

Criteria: `docs/sg-03/n9-live-acceptance-criteria.md` (committed before any N9 run, not edited). Evidence: `docs/sg-03/evidence/n9/`. Owner decisions in force: the production write guard stays; the inert feature-level code stays; the strict B1 FAIL is preserved.

## What was run

- Server: the built production jar `sg-worldgen-protection-0.3.0-n7e.jar` through `runJarServer` (no lab mod), fresh seed-173 world, SG-03 datapack, normal difficulty, monster spawning on, offline mode.
- Client: real Minecraft 26.3 (Fabric Loom client project) on Xvfb 1280x720 with Mesa lavapipe Vulkan (software). The OpenGL backend could not start, so the client used its Vulkan backend. No audio device, so sound was off. Screenshots are the game's own `Screenshot.grab`; the repository copies are JPEG q85 conversions, and `screenshots.sha256` lists the native PNG hashes.
- Input counted as live: keyboard (`xdotool keydown/key`), mouse buttons and relative mouse movement, delivered by the X server. Setup uses RCON commands (teleport, summon, give, forceload) and is labelled SERVER-ONLY. No `/place` is used.
- Final driver `live_acceptance.py` was run twice without changes between the runs (`run8`, `run9`). Runs 1–7 were development runs, listed below.

## Result per scenario (identical in run 8 and run 9 unless noted)

| ID | Verdict | Evidence level | Evidence | Limitation |
|---|---|---|---|---|
| L1 | PASS | LIVE | client joined, server lists the player, renderer started, native screenshot with 35,371 (run 8) / 20,591 (run 9) colours | software renderer |
| L2 | PASS | SAVED-DATA | `/locate` reported (-304, 240); after loading the area the structure start is in the saved region with 21 pieces; nothing was placed with a command | `/locate` is only a candidate, so the area is force-loaded one chunk row at a time |
| L3 | PARTIAL | LIVE approach; entry SERVER-ONLY | from a surface point about 90 blocks away the player walked 29.5 / 29.9 blocks toward the structure (28.7 / 29.7 closer) with W and real mouse aiming on the first attempt | the structure lies about 100+ blocks below the surface with no vertical shaft (longest open run above the pieces is 12 blocks), so entry into the piece boxes is a teleport; the criterion's "ends inside a piece box" is therefore not met live |
| L4 | PASS | LIVE | two routes, each three successive connected pieces: tunnel_east to main_chamber to tunnel_west, and tunnel_south to main_chamber to tunnel_north. The first piece of a route is a teleport setup; the next two were entered by live W-key walking, confirmed by the server-side player position inside the next piece box (legs 4.7 s and 17.7–22.7 s) | development runs 6 and 7 each completed only one of the two routes; the final two runs completed both |
| L5 | PASS | SERVER-ONLY (saved data) | 40 junction entries, 0 blocked: doorway cells at the connector height are passable (flat junctions at the ground height, upper-room junctions at ground + 9) | rule derived from this structure's data; not a general proof |
| L6 | PASS | LIVE (zombie placed by command) | the player's real mouse aim and clicks killed a no-AI zombie summoned 2.5 blocks ahead: 4 clicks (run 8), 8 clicks with a re-aim (run 9) | weapon given by command; natural zombies shoved the player in earlier runs |
| L7 | PASS | SERVER-ONLY observation with the live player present | spawner (-345,-24,167): the player stood in line of sight; the block state was `active` at the first poll (about 2 s after arrival), the block entity listed the registered player and 3 spawned mobs (spider config) | the inactive-to-active transition itself was not observed |
| L8 | PARTIAL | LIVE screenshot + SAVED-DATA | native surface screenshot above the structure shows intact terrain; 3,025 sampled columns above the footprint, 0 open-air columns of 30+ blocks, longest open run 12 | no screenshot of a cave opening near the structure |
| L9 | PARTIAL | LIVE screenshots + SAVED-DATA | a natural geode at (-423,-18,93), 102.5 blocks from the nearest piece box, and a natural monster room at (-464,2,376), 155.5 blocks away, were screenshotted (amethyst crystals in a cave; cobblestone room with spawner and chest). The live world's pieces match their templates: 55,305 of 55,305 cells, 3 of 3 trial-spawner blocks have entities, 0 errors | the feature hooks made 0 attempts, so the guard recorded no cancelled feature; the write guard refused 1,102 writes (unavailable 0). No screenshots were taken at refused locations |
| L10 | FAIL (literal) | LIVE | no crash, client alive, server tick average 3.7 / 4.1 ms, P99 10.1 / 12.6 ms. One `Can't keep up` warning per run (3,500 ms in run 8, 2,742 ms in run 9) | see below |

### L10 in detail

- The warning occurs at the first forceload row, right after the `/locate` in the L2 setup, in every run that reached L10 (runs 3, 4, 6, 7, 8, 9; run 5 stopped earlier on a parser error). Run 8 and run 9 each have 0 warnings after the L2 setup.
- Control (`n9_stall_control.py`, same `/locate` and forceload sequence, no client): vanilla server jar 2,942 ms and 3,248 ms; production jar 3,208 ms and 3,304 ms (two runs each). So the stall is reproduced without the module; two samples per variant cannot show a small difference.
- The criterion says no such message during the scenarios, so L10 stays FAIL. It is a candidate for an explicit owner exception, not a PASS. The client-stall half of the rule (no stall over 5 s) was **not measured**: the client log has no per-frame markers.

## Development runs and defects found in the harness (not in the product)

| Run | Finding | Fix |
|---|---|---|
| 1 | L2 failed: `/locate` does not generate the structure | force-load the located area before reading the saved region |
| 2 | no X window found by title | window lookup by title, class or any visible window, with a dump |
| 3 | spawner check passed on identical NBT (false positive); L4 teleported to each tunnel separately; L10 stall at a 121-chunk forceload | state read from the block property; successive-piece routes; forceload one chunk row at a time |
| 4 | `xdotool mousemove` rotated the camera while the cursor was grabbed (L4 drift, L6 offset); trial spawner needs line of sight | no cursor warp; real relative mouse aiming; line-of-sight standing cell |
| 5 | rotation parser rejected `E-6` floats | parser fix |
| 6 | L6: `tp ... facing` aims from the feet, tilting the view 18 degrees; route 1 climbed to an upper level | explicit yaw and pitch; jump only when blocked |
| 7 | L6: natural zombies shoved the player off line | re-aim at the zombie with the mouse before each click batch |

## Regressions and checks

- `python3 -m unittest discover -s tests`: 147 tests OK (new `tests/test_n9_driver.py`: no `/place`, production jar only, every criterion has a step, no cursor warp).
- Production code: unchanged against PR #39 (empty `mod/` diff).
- Repository CI (`pr-checks.yml`) lints and tests only `vendor/mcbuild`; it does not run the guard, the driver or the live scenarios, so these results are not backed by CI.

## Unresolved risks and follow-up

1. L10 literal FAIL; client stall unmeasured. Owner decision: exception for the setup-command stall, or require a gentler setup.
2. L3 entry into the structure is not live. A live entry would need a natural cave route or digging.
3. L8 has no cave-opening screenshot; L9 has no per-refusal screenshots and no cancelled features to inspect (the feature hooks are inert in normal operation).
4. One seed, one structure site, one software-rendered client; timing is not representative of real hardware.
5. The previous N8-R items remain open as recorded in `docs/sg-03/n8r-acceptance.md` (B1 FAIL, B2 NOT EVALUATED, resource criteria on the write soak NOT EVALUATED, N8-D NOT EVALUATED, three iron_bars cells UNKNOWN in the write world).

Next recommended stage: N10 (final release audit) after the owner decides on item 1; it needs explicit authorization and has not been started.
