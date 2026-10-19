# SG-03-N: natural-terrain integration verification

Separate Draft branch stacked on SG-03 PR #11; none of the SG-01/02/03 design geometry or exported resources are changed.

## Method

The workflow (.github/workflows/sg03-natural.yml) starts an official, SHA-1-verified Minecraft 26.3 vanilla server with normal-world terrain and structures enabled. It generates two deterministic unsuppressed random-spread candidate sites each for seeds 173 and 42, with no /place commands.

The probe reads structures.starts directly from saved vanilla chunks, then reconstructs the actual Jigsaw Children records. It checks all 21 pieces: one main chamber, four tunnels, and sixteen rooms. Each piece is checked against its template's rotated blocks and recorded bounding box, along with disjointness, known versus unexplained overwrites, natural exterior cave-air/water/lava contacts, interior fluid, and saved trial-spawner block entities. Minecraft advances 200 ticks and the probe repeats the inspection.

Each CI job uploads a per-seed JSON report and vanilla server log. Stage results must be read from an actual completed run; the presence of this workflow is not a runtime PASS.

Known SG-01-B issues include sculk/geode overlays, sealed tunnel mouths, occasional tunnel-fluid ingress, and trial-chamber exclusion. This stage reports known overwrites explicitly rather than pretending every original structure block survived. Unexplained mismatches, missing pieces, unloaded boundaries or chamber fluid fail the CI job.

## Not tested

- Live-player survival movement or input.
- Actual trial-spawner activation and combat, which need nearby non-spectator players.
- Natural client screenshots (the existing SG-03 native screenshots were produced in controlled flat-world placement).
- Targeted vanilla Trial Chambers or Ancient City collision cases.
- Owner/artistic approval.

All three upstream PRs stay Draft. Do not merge this validation branch until its CI is green and the results are reviewed.


## First CI observations (2026-10-18)

[Exact-head run 39116803781](https://github.com/ItzGamesGD/MoreMinecrafts-Structure-Generator/actions/runs/39116803781), source head bf5acc7: Minecraft 26.3 naturally generated **4/4** sites (2 sites for each seed 173 and 42), with **21 recorded Jigsaw pieces per site**. This run used no /place. All four preserved the expected 1 chamber, 4 tunnels, 16 room placements. Inspection after 200 ticks gave the same findings.

| Seed | Candidate chunk | Block matches | Verdict |
|---|---|---|---|
| 173 | (-19,15) | 55,305/55,305 | PASS; shell lava 1, west tunnel lava ingress 5, central chamber dry, trial spawners 3/3 with block entities |
| 173 | (-18,36) | 53,252/53,252 | PASS; shell water 9, lava 7, interior dry, spawners 3/3 |
| 42 | (4,13) | 52,396/52,443 | **FAIL**; 47 expected moss blocks in residence_ruin rooms became clay; interior dry, spawners 3/3 |
| 42 | (6,-19) | 48,556/48,556 | PASS; shell water 49, lava 16, interior dry, spawners 12/12 |

**Overall: 3/4 sites PASS, 1/4 FAIL.** CI remains red for the seed-42 job; do not present this stage as fully approved. The sample is small and does not establish a global success rate.

**N-1 (open):** The 47 moss-to-clay replacements are directly confirmed in saved-world chunks. A late vanilla clay/biome feature is a plausible explanation but **not proven**. Do not silently exempt clay or alter approved room geometry. A targeted feature-order investigation and owner choice (accept environmental variation vs. mitigate it) remain necessary.

**N-2 (open design choice):** In one seed-173 site, five lava blocks enter the west tunnel. No fluid enters the main chamber. The related SG-01-B open-mouth behaviour is already documented; leaving it is not a new technical PASS for fluid-tight tunnels.

**N-3 (partial):** Saved trial-spawner blocks and their block entities were present across the four sites. Actual mob activation, threat balance, and player combat remain NOT RUN.

This evidence includes no native natural-world client screenshots or player traversal test. No SG-01/02/03 building or export was changed.
