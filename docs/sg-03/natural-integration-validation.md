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
