"""SEAM-01 on a real vanilla Minecraft 26.3 server: assemble the 34 placements, apply the patches, compare with the whole structure.

Per whole-structure rotation q (none, clockwise_90, 180, counterclockwise_90) three plots of the same structure:
  A  every placement placed `strict` in manifest order (as jigsaw worldgen places pool elements), then the seam patches
     (strict /setblock, y-z-x order);
  U  the same without patches, then the game's own recompute (non-strict /setblock of each connecting block's stated
     properties = Block.updateFromNeighbourShapes) - the oracle for the connection states;
  R  the reference: every cell of the whole-structure result written one by one.
Checks: A equals R over the whole box (`execute if blocks`, layer by layer); the game's recompute changes nothing in A; the
recompute changes cells in U and U then equals R on every connecting block (negative control); patches applied in reverse
order give the same A; the python stair rule matches the game on every stair of the assembly (seam-dependent ones differ from
their authored shape, all others keep it).
SYNTHETIC module contents (tools/seam01/synthetic.py): this is not ST-03 content.
"""

# ruff: noqa: E501
from __future__ import annotations

import json
import shutil
import time
import zipfile
from pathlib import Path

from tools.stage24c.mcserver import Server  # noqa: F401  (documented dependency of make_server)
from tools.structure_export.connectivity import Rules, load_connectivity
from tools.structure_export.live import ROTATIONS, _text
from tools.structure_export.stair_live import forceload, make_server, wait_loaded

from . import assembly as A
from . import export, synthetic
from . import patches as P
from .stairs import stairs_shape

Y0 = 10  # world y of structure y = 0
GAP = 130


def run(server_jar: Path, java: str, work: Path) -> dict:
    work = Path(work)
    if work.exists():
        shutil.rmtree(work)
    pack = work / "pack" / "mmst_seam01"
    (pack / "data").mkdir(parents=True)
    with zipfile.ZipFile(server_jar) as z:
        version = json.loads(z.read("version.json"))
    pf = [version["pack_version"]["data_major"], version["pack_version"]["data_minor"]]
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "SEAM-01 live", "min_format": pf, "max_format": pf}})
    )
    sources = synthetic.sources()
    templates, results = export.export_all(pack, sources)
    rules = Rules(load_connectivity("26.3"))
    out: dict = {"minecraft_version": version["id"], "synthetic_modules": True, "rotations": {}}
    base = P.generate(0, sources, templates)

    server = make_server(work / "server", server_jar, java, pack)
    try:
        server.start()
        raw_cmd = server.cmd

        def cmd(c):  # chunks of a force-loaded area come in over several ticks: retry while the game says "not loaded"
            for _ in range(120):
                reply = raw_cmd(c)
                if "not loaded" not in reply:
                    return reply
                time.sleep(1)
            return reply

        server.cmd = cmd
        out["datapacks"] = server.cmd("datapack list enabled")
        forceload(server, 0, 0, 3 * GAP + 230, 3 * GAP + 230)  # /place checks the unrotated template box too
        wait_loaded(server, 3 * GAP + 220, Y0, 3 * GAP + 220)

        def put(pos, state, strict=True):
            return server.cmd(f"setblock {pos[0]} {pos[1]} {pos[2]} {state}" + (" strict" if strict else ""))

        def world(anchor, p):
            return (anchor[0] + p[0], Y0 + p[1], anchor[1] + p[2])

        def assemble_in_game(anchor, q):
            for e in A.manifest(q):
                o = (anchor[0] + e["origin"][0], Y0 + e["origin"][1], anchor[1] + e["origin"][2])
                reply = server.cmd(
                    f"place template moreminecrafts:seam01/{e['file'][:-4]} {o[0]} {o[1]} {o[2]} {e['rotation']} none 1 0 strict"
                )
                if not reply.startswith("Loaded template"):
                    raise RuntimeError(f"{e['placement']} q={q}: {reply}")

        def cell_failures(anchor, expected: dict) -> list:
            bad = []
            for pos, (bid, props) in expected.items():
                at = world(anchor, pos)
                if "passed" not in server.cmd(f"execute if block {at[0]} {at[1]} {at[2]} {_text(bid, props)}"):
                    bad.append(list(pos))
            return bad

        def layers_different(a, b) -> int:
            n = 0
            size = A.box_size()
            for y in range(A.height()):
                lo_a, lo_b = world(a, (0, y, 0)), world(b, (0, y, 0))
                hi_a = world(a, (size - 1, y, size - 1))
                reply = server.cmd("execute if blocks {} {} {} {} {} {} {} {} {} all".format(*lo_a, *hi_a, *lo_b))
                if "passed" not in reply:
                    n += 1
            return n

        import itertools

        from tools.structure_export.connectivity import COMPUTED
        from tools.structure_export.convert import load_reference

        ref_blocks = load_reference("26.3")["blocks"]

        def actual_state(anchor, pos, bid, props) -> str | None:
            """The state the game holds, found by probing every combination of the computed properties."""
            keys = COMPUTED[rules.kind(bid)]
            at = world(anchor, pos)
            for combo in itertools.product(*(ref_blocks[bid]["properties"][k] for k in keys)):
                trial = {**props, **dict(zip(keys, combo, strict=True))}
                if "passed" in server.cmd(f"execute if block {at[0]} {at[1]} {at[2]} {_text(bid, trial)}"):
                    return _text(bid, trial)
            return None

        def recompute(anchor, cells) -> int:
            changed = 0
            for pos in sorted(cells, key=lambda p: (-p[1], p[2], p[0])):  # top layer first, as the converter resolves
                bid, props = cells[pos]
                if rules.kind(bid):
                    stated = {k: v for k, v in props.items() if k in sources_stated.get(pos, ())}
                    at = world(anchor, pos)
                    if put(at, _text(bid, stated), strict=False).startswith("Changed the block"):
                        changed += 1
            return changed

        for q in range(4):
            t0 = time.time()
            patches = P.rotate(base, q)
            direct = P.generate(q, sources, templates)
            whole, explicit, _ = P.whole_structure(q, sources)
            placed = P.module_result(q, templates)
            sources_stated = {pos: set(s) for pos, s in explicit.items()}
            problems = P.validate(patches, placed, whole)
            for k in range(4):  # every plot of this rotation must be fully loaded before anything is placed
                wait_loaded(server, 10 + q * GAP, Y0, 10 + k * GAP)
                wait_loaded(server, 10 + q * GAP + A.box_size() + 1, Y0, 10 + k * GAP + A.box_size() + 1)
            anchor_a, anchor_u, anchor_r, anchor_s = (
                (10 + q * GAP, 10),
                (10 + q * GAP, 10 + GAP),
                (10 + q * GAP, 10 + 2 * GAP),
                (10 + q * GAP, 10 + 3 * GAP),
            )
            # R: the whole-structure reference, cell by cell
            for pos in sorted(whole, key=P.order_key):
                put(world(anchor_r, pos), _text(*whole[pos]))
            # A: placements + patches
            assemble_in_game(anchor_a, q)
            for p in patches:
                put(world(anchor_a, p.pos), _text(p.block, dict(p.state)))
            # S: reverse application order
            assemble_in_game(anchor_s, q)
            for p in reversed(patches):
                put(world(anchor_s, p.pos), _text(p.block, dict(p.state)))
            # U: unpatched, then the game's recompute
            assemble_in_game(anchor_u, q)
            unpatched_layers = layers_different(anchor_u, anchor_r)
            bad_patch_targets_before = cell_failures(anchor_u, {p.pos: (p.block, dict(p.state)) for p in patches})
            stairs = {p: v for p, v in placed.items() if v[0].endswith("_stairs")}

            def stair_pass(anchor_u=anchor_u, stairs=stairs) -> int:
                return sum(
                    put(
                        world(anchor_u, p), _text(b, {"facing": pr["facing"], "half": pr["half"]}), strict=False
                    ).startswith("Changed")
                    for p, (b, pr) in sorted(stairs.items(), key=lambda kv: P.order_key(kv[0]))
                )

            # The game's normal-placement fixpoint: connecting blocks and stairs update each other (a reshaped stair changes
            # which side of it is sturdy), so repeat both until neither changes anything.
            changed_u, passes_u = recompute(anchor_u, whole), 1
            stairs_reshaped = stair_pass()
            while recompute(anchor_u, whole) + stair_pass():
                passes_u += 1
                if passes_u > 12:
                    break
            connecting = {p: v for p, v in whole.items() if rules.kind(v[0])}
            whole_v, _, _ = P.whole_structure(q, sources, vanilla_stairs=True)
            connecting_v = {p: v for p, v in whole_v.items() if rules.kind(v[0])}
            stair_induced = sorted(p for p in connecting if connecting[p] != connecting_v[p])
            u_after = cell_failures(anchor_u, connecting_v)

            a_vs_r = layers_different(anchor_a, anchor_r)
            s_vs_r = layers_different(anchor_s, anchor_r)
            changed_a = recompute(anchor_a, whole)
            a_cells_bad = cell_failures(anchor_a, whole)
            # stairs: the game's shape against the python rule on the module assembly (plot U, at the joint fixpoint)
            stair_bad, stair_seam_game = [], 0
            for p, (b, pr) in stairs.items():
                at = world(anchor_u, p)
                game = [
                    s
                    for s in ("straight", "inner_left", "inner_right", "outer_left", "outer_right")
                    if "passed"
                    in server.cmd(
                        f"execute if block {at[0]} {at[1]} {at[2]} {b}[facing={pr['facing']},half={pr['half']},shape={s}]"
                    )
                ]
                want = stairs_shape(placed, p)
                if game != [want]:
                    stair_bad.append({"pos": list(p), "game": game, "rule": want})
                if want != pr["shape"] and game == [want]:
                    stair_seam_game += 1
            rep = P.stair_report(q, sources, templates)
            rec = P.reconcile_stairs(q, rep, results)
            out["rotations"][ROTATIONS[q]] = {
                "q": q,
                "whole_cells": len(whole),
                "connecting_blocks": len(connecting),
                "patches": len(patches),
                "patches_equal_direct_generation": direct == patches,
                "patchset_sha256": P.patchset(q, patches)["sha256"],
                "validate_problems": problems,
                "unpatched_layers_differing_from_reference": unpatched_layers,
                "patch_cells_wrong_before_patching": len(bad_patch_targets_before),
                "game_recompute_changed_unpatched_first_pass": changed_u,
                "game_recompute_changing_passes_unpatched": passes_u,
                "stairs_reshaped_by_game_first_pass": stairs_reshaped,
                "unpatched_after_recompute_connecting_wrong_vs_vanilla_stairs": len(u_after),
                "connections_that_depend_on_a_seam_stair_shape": [list(p) for p in stair_induced],
                "unpatched_after_recompute_examples": [
                    {
                        "pos": p,
                        "expected": _text(*whole_v[tuple(p)]),
                        "game": actual_state(anchor_u, tuple(p), *whole_v[tuple(p)]),
                    }
                    for p in u_after[:20]
                ],
                "patched_layers_differing_from_reference": a_vs_r,
                "patched_reverse_order_layers_differing": s_vs_r,
                "game_recompute_changed_patched": changed_a,
                "patched_cells_wrong": len(a_cells_bad),
                "stairs": len(stairs),
                "stair_rule_vs_game_mismatches": stair_bad[:10],
                "stair_rule_vs_game_mismatch_count": len(stair_bad),
                "stairs_whose_game_shape_differs_from_authored": stair_seam_game,
                "stair_seam_dependent_in_report": len(rep["seam_dependent"]),
                "stair_seam_not_in_pr49_review": rec["not_in_stair_boundary_review"][:10],
                "seconds": round(time.time() - t0, 1),
            }
            r = out["rotations"][ROTATIONS[q]]
            r["pass"] = (
                not problems
                and r["patches_equal_direct_generation"]
                and r["patches"] > 0
                and a_vs_r == 0
                and s_vs_r == 0
                and changed_a == 0
                and not a_cells_bad
                and unpatched_layers > 0
                and changed_u > 0
                and not u_after
                and not stair_bad
                and stair_seam_game == len(rep["seam_dependent"]) > 0
                and not rec["not_in_stair_boundary_review"]
            )
    finally:
        server.stop()
    log = (work / "server" / "server.log").read_text(errors="replace")
    out["log_problems"] = [x for x in log.splitlines() if "/ERROR]" in x or "Failed to load" in x or "Exception" in x][
        :20
    ]
    out["result"] = "PASS" if all(r["pass"] for r in out["rotations"].values()) and not out["log_problems"] else "FAIL"
    return out
