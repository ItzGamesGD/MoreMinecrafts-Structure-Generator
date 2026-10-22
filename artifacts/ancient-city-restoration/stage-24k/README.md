# Stage 24-K — approved watchtower designs in production

Baseline: Stage 24-J Draft PR #35, head `f7170895596ab3728517901324d98718313e8950` (CI green).

**Owner decision (final):** `large_pillar_1` Option A — open lookout; `medium_pillar_1` Option A — corbelled crown. Option B of
either tower is not substituted and neither tower is redesigned. The deferrals of the blocked entrances at seeds 24005, 24009
and 24015 are retained (`../DESIGN-DECISIONS.md`); no terrain-clearing feature, road or plaza was added.

## What changed

| | |
|---|---|
| production templates | `final-candidates/` — `large_pillar_1` and `medium_pillar_1` are **byte-identical** to the approved Stage 24-J Option A candidates; the other six are **byte-identical** to Stage 24-F (`SOURCES.json`, `SHA256SUMS`) |
| dimensions | unchanged: large 6×15×6, medium 7×11×8 → same piece boxes, jigsaws, block entities (incl. the medium-pillar skull and barrel) |
| production pack | `derived-24i/datapack` — differs from the Stage 24-I pack in exactly 4 files (the two tower templates and the two tower protection overlays); the pool file and all other files are byte-identical |
| derived data | Stage 24-G/24-H/24-I builders re-run unchanged on the new templates (`DERIVATION.md`): the six other modules' protection inventory, clearance mask and roof cells are **identical**; tower protection 39→53 (large) and 38→48 (medium) cells, clearance-mask cells identical, roof cells 0 |
| roof protection of the four houses | preserved: 64 / 78 / 29 / 11 cells, templates byte-identical |

## Results

| | Stage 24-I | Stage 24-K |
|---|---|---|
| large tower deck | no railing: 30 open drop edges, deck above the template | railed parapet on the corbelled cap, 15 deck cells, 0 open drops |
| medium tower top | loose fragments projecting, 11 deck cells | corbelled crown, 29 deck cells, 0 open drops |
| city layouts, 24 seeds (2,160 pieces) | – | **identical**, 0 overlaps, identical jigsaw records (263; 251 connected), identical bounding boxes |
| protected cell instances missing | 0 of 9,176 (5 replaced by ore features) | **0 of 9,974, 0 replaced** (roof 4,170/4,170 present) |
| decorative `block_rot` losses | 3,067 | 2,972 (large 238→165, medium 330→308; six other modules identical, 2,499) |
| decay at unchanged blocks | – | **identical** (every changed loss cell is a designed or newly protected cell) |
| live placement, 8 modules × 4 rotations (real processors) | – | 71 placements, 0 violations |
| exact tower placement, 4 rotations | – | 8/8, 0 mismatching cells |
| scripted player on the towers, 4 rotations | – | large 52/52, medium 78/78 steps, **every deck cell visited**, every deck edge walked |
| scripted player, buried placements, 8 modules × 4 rotations | 32/32 | 32/32 |

All player results are scripted mineflayer checks on a real 26.1.2 server — **not Minecraft-client gameplay**. Images are
headless renders — **client visual verification is PENDING**.

## Discrepancies and open items (reported, nothing altered)

1. **Sauna pool: 385 of 387 water cells (Stage 24-I: 387/387).** At seeds 24006 and 24007 one floor-level pool cell is a sculk
   catalyst. Reproducible (same cell in a repeat run; absent in both Stage 24-I runs). The sauna template and all its derived
   data are byte-identical. A bisect (`tools/stage24k/sauna_bisect.py`, `worldgen/sauna-bisect.json`) isolates it to the
   `medium_pillar_1` change — but seed 24007 contains **no** `medium_pillar_1` piece (nearest to the seed-24006 sauna: 42 blocks), so
   it is not a local geometry effect. **Cause unresolved**; leading hypothesis is a generation-order interplay of the vanilla sculk
   decoration. Impact: the pool keeps 385 cells of water, the buried swim test passes.
2. **Vanilla sculk on decks.** In 6 of 67 generated towers a vanilla sculk sensor/catalyst/shrieker sits on a deck cell (12 of
   2,990 deck-cell checks). Every clear deck cell is reachable from the ladder in every tower and no ladder exit is blocked. The
   same vanilla behaviour as sculk growing into cleared rooms (Stage 24-H).
3. **Medium Option A: headroom cell above deck cell (4,2) is not stored in the template** (`(4,10,2)`) — identical to the approved
   Stage 24-F tower, not changed here. It is air in all 67 generated towers; only the buried test fill would fill it, so
   `tools/stage24h/gameplay_buried.py` got an optional `open_top` parameter (default unchanged).
4. **Natural-feature differences next to the towers (cosmetic):** 20 glow-lichen cells (lichen that grew on the old top slab is
   gone with it; two runs of one pack differ by 1), 21 base/shaft cells that are a tuff blob (and one iron ore, one gravel cell)
   in Stage 24-K where a vanilla sculk patch had converted them in Stage 24-I, 3 natural-terrain cells, and natural deepslate in
   5 cells where the old loose fragments were. None involves a protected cell.
5. **Lantern losses** differ by ±1 cell in unchanged modules; two runs of the unchanged Stage 24-I pack differ the same way.
6. **Deferred entrances** (24005, 24009, 24015): the entrance survey is identical to Stage 24-I (113/116 open).
7. Seed 24012 sauna water flow and seed 24014 sauna lava column: unchanged, pre-existing.

## Evidence

| path | content |
|---|---|
| `final-candidates/`, `SOURCES.json` | the eight production templates |
| `derived-24g/`, `derived-24h/`, `derived-24i/` | rebuilt protection, clearance and roof data and packs; `DERIVATION.md`, `DERIVATION-DIFF.json` |
| `static-checks.json` | tower size, jigsaws, ladder, deck reachability, fall protection, block states |
| `live/` | pool placements (8 × 4), tower placement + traversal, buried gameplay |
| `worldgen/` | 24-seed sweep manifests, analysis, survival, processor replay, I-vs-K cell comparison, decay regression, terrain, entrances, reproducibility, sauna bisect |
| `worldgen-rep/` | repeat generations used as the noise floor |
| `gallery/` | before/after renders of both towers (templates and generated worlds) |
| `VALIDATION-MATRIX.md` | every requested check with status |

## Reproduce

```
vendor/mcbuild/.venv/bin/python tools/stage24k/build.py            # final-candidates + derived data + diff
vendor/mcbuild/.venv/bin/python tools/stage24k/check.py            # static tower checks (needs the vanilla block report)
tools/stage24k/live_pool.py; tools/stage24k/live_towers.py; tools/stage24k/buried.py
tools/stage24c/worldgen.py --seeds 24001..24024 --variants k24 --src stage-24k/final-candidates --pack stage-24k/derived-24i/datapack --out stage-24k/worldgen
tools/stage24k/compare.py; tools/stage24k/decay_regression.py; tools/stage24k/reproducibility.py; tools/stage24k/gallery.py
```
