# Stage 24-F provenance: the pinned Stage 24-E objects

`tools/stage24f/assemble.py` and `tests/test_stage24f_final.py` verify the two Stage 24-E-derived production designs
(`large_ruin_1` option C, `medium_ruin_2` option A) against git objects at the pinned Stage 24-E head
`5a3a57186762a2e0fcb1489b60531e328c2457b2`. That commit is not an ancestor of `main`. `stage-24e-5a3a571/` holds the five
objects those tools read, **byte-for-byte** as `git show 5a3a571:<path>` returns them (`SHA256SUMS`):

| object | read by |
|---|---|
| `PROPOSALS.md` (reviewed proposal SHA-256 manifest) | `assemble.py` |
| `static-checks.json`, `live-summary.json` (reviewed static and live results) | `assemble.py` |
| `proposals/large_ruin_1/C/candidate.nbt`, `proposals/medium_ruin_2/A/candidate.nbt` | `assemble.py`, `test_each_module_is_exactly_its_selected_source` |

`git_show` still reads the git object first; the vendored copy is used only when the object is unavailable, and is verified
against `SHA256SUMS` before use. The production NBTs equal these proposals byte-for-byte, and
`stage-24f/FINAL-CANDIDATES-MANIFEST.json` records the reviewed SHA-256 independently.
