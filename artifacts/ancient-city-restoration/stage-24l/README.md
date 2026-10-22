# Stage 24-L - Ancient City connectivity: DESIGN ONLY (Phase 0 measurement)

**This stage is design-only.** It contains a design report, a read-only measurement tool, its tests and the generated audit evidence.
It contains **no NBT, no datapack, no processor, no worldgen change and no gameplay change**; the approved Stage 24-F residential
architecture and the Stage 24-K Option A watchtowers are untouched, and Stage 24-K stays CODE VERIFIED / conditional PASS and VISUAL PENDING.
Implementation needs separate owner approval.

| file | content |
|---|---|
| `DESIGN.md` | problem classes, Phase 0 findings, alternatives, recommendation, owner decisions |
| `phase0/PHASE0-RESULTS.md` | generated per-seed / per-door results, obstruction coordinates, maps (from the JSON below) |
| `phase0/results-summary.json`, `seed-<seed>.json`, `focus-<seed>.json`, `survey-reproduction.json` | machine-readable evidence |
| `phase0/phase0-run.log` | log of the evidence run |
| `tools/stage24l/phase0.py`, `summarize.py` | the measurement (read-only) and the report generator |
| `tests/test_stage24l_phase0.py` | graph-rule unit tests + checks on the committed evidence + read-only / design-only guards |

## Reproduce

Needs the pinned 26.1.2 server jar (`MC_JAR`, `MC_JAVA`) as for the other stage workflows. Worlds are generated in `stage-24c/_work/` (git-ignored).

```
K=artifacts/ancient-city-restoration/stage-24k
python -I tools/stage24c/worldgen.py --seeds $(seq 24001 24024) --variants k24 \
    --src $K/final-candidates --pack $K/derived-24i/datapack --out /tmp/p0-manifests
python -I tools/stage24l/phase0.py --manifests /tmp/p0-manifests --out artifacts/ancient-city-restoration/stage-24l/phase0
python -I tools/stage24l/summarize.py artifacts/ancient-city-restoration/stage-24l/phase0
```

The evidence is byte-identical on a repeated run. The regenerated layouts equal the committed Stage 24-K manifests (kept on branch
`stage-24k-watchtower-implementation`) in 24/24 seeds.

## Limits

A static geometric model of saved worlds (see the docstring of `phase0.py`): not Minecraft-client gameplay, not a physics or mob
simulation, ladders / vines / elevators are not modelled. The Stage 24-I mineflayer navigation tests remain the only scripted-navigation
evidence; no new bot run was made in Phase 0.
