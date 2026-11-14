"""STAIR-01 live check on a real vanilla Minecraft 26.3 server.

    python -m tools.structure_export.stair_live --server-jar server.jar --java java --out result.json

Phase 1 (oracle server, no datapack): stair fixtures are built from bare `facing`/`half` stairs; the game itself decides
every `shape` (non-strict /setblock runs Block.updateFromNeighbourShapes). Those game states become the authored states.
Phase 2 (server with the exported datapack): each fixture is exported by the converter (explicit facing/half/shape), placed
`strict` (jigsaw-like, no neighbour update) at all four rotations and compared cell by cell with the expected rotated state;
also placed non-strict to record where normal placement would recompute a shape (strict and normal are different things).
Fixtures: matrix (5 shapes x 2 halves x 4 facings, isolated), neighbour pairs, inner/outer corner clusters, spiral, inverted
corbel row, gable roof with eave and hip, and a module seam (a stair run split in two templates).
"""

# ruff: noqa: E501, SIM113
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
import tempfile
import time
from pathlib import Path

import nbtlib
from nbtlib.tag import ByteArray, Compound, Int, IntArray, List, Short
from tools.stage24c.mcserver import Server

from . import convert as C
from .live import FLAT, ROTATIONS, Layout, _at, _free_port, _text, rotate_props

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "exports/structures/ruined_watchtower.toml"
FACING = ("north", "east", "south", "west")
HALVES = ("bottom", "top")
SHAPES = ("straight", "inner_left", "inner_right", "outer_left", "outer_right")
STEP = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0)}
RIGHT = {"north": "east", "east": "south", "south": "west", "west": "north"}
LEFT = {v: k for k, v in RIGHT.items()}
OAK, BRICK, DARK = "minecraft:oak_stairs", "minecraft:stone_brick_stairs", "minecraft:dark_oak_stairs"

Cell = tuple[str, str, str]  # block id, facing, half


def add(p, d, n=1):
    return (p[0] + d[0] * n, p[1] + d[1] * n, p[2] + d[2] * n)


# ----------------------------------------------------------------------------------------------- fixtures
def fx_matrix_slots():
    """Isolated stairs, one air cell apart; shape is chosen by the test (all five)."""
    slots = {}
    for i, (shape, half, facing) in enumerate(itertools.product(SHAPES, HALVES, FACING)):
        slots[(2 * (i % 10), 0, 2 * (i // 10))] = (OAK, facing, half, shape)
    return slots


def fx_pairs() -> dict[tuple[int, int, int], Cell]:
    """A centre stair and one neighbour on each side with every facing, both halves: 128 clusters on a grid."""
    cells, n = {}, 0
    for half, cf, side, nf in itertools.product(HALVES, FACING, FACING, FACING):
        ox, oz = 4 * (n % 16), 4 * (n // 16)
        c = (ox + 1, 0, oz + 1)
        cells[c] = (BRICK, cf, half)
        cells[add(c, STEP[side])] = (BRICK, nf, half)
        n += 1
    return cells


def fx_corners() -> dict[tuple[int, int, int], Cell]:
    """Runs of three stairs whose end cell meets a perpendicular front or back neighbour: corners at the end of a run."""
    cells, n = {}, 0
    for half, f, end, where in itertools.product(HALVES, FACING, ("left", "right"), ("front", "back")):
        ox, oz = 8 * (n % 8), 8 * (n // 8)
        n += 1
        c = (ox + 3, 0, oz + 3)
        side = STEP[LEFT[f]] if end == "left" else STEP[RIGHT[f]]
        cells[c] = (OAK, f, half)
        cells[add(c, side)] = (OAK, f, half)
        cells[add(c, side, 2)] = (OAK, f, half)
        turn = RIGHT[f] if end == "left" else LEFT[f]
        front = STEP[f] if where == "front" else tuple(-v for v in STEP[f])
        cells[add(add(c, side, 2), front)] = (OAK, turn, half)
    return cells


def fx_spiral() -> dict[tuple[int, int, int], Cell]:
    """A rising helical run of stairs around a 3x3 core (ring of 16 cells per turn, two turns; the level rises by one every four cells so corners sit at one level)."""
    ring = [(x, 0) for x in range(0, 5)] + [(4, z) for z in range(1, 5)] + [(x, 4) for x in range(3, -1, -1)]
    ring += [(0, z) for z in range(3, 0, -1)]  # 16 cells, clockwise from (0,0)
    cells = {}
    for k in range(32):
        x, z = ring[k % 16]
        nx, nz = ring[(k + 1) % 16]
        d = (nx - x, nz - z)
        facing = {(1, 0): "east", (0, 1): "south", (-1, 0): "west", (0, -1): "north"}[d]
        cells[(x, (k + 1) // 4, z)] = (BRICK, facing, "bottom")
    return cells


def fx_corbel() -> dict[tuple[int, int, int], Cell]:
    """Upside-down corbel row under a wall course with a return at each end (half=top), plus a stepped corner."""
    cells = {}
    for x in range(1, 9):
        cells[(x, 0, 1)] = (BRICK, "south", "top")
    cells[(0, 0, 1)] = (BRICK, "east", "top")
    cells[(9, 0, 1)] = (BRICK, "west", "top")
    for z in range(2, 6):
        cells[(0, 0, z)] = (BRICK, "east", "top")
    for z in range(2, 6):
        cells[(9, 0, z)] = (BRICK, "west", "top")
    cells[(0, 0, 6)] = (BRICK, "north", "top")
    cells[(9, 0, 6)] = (BRICK, "north", "top")
    return cells


def fx_roof() -> dict[tuple[int, int, int], Cell]:
    """Hip/gable roof of dark_oak_stairs: three courses with eave overhang, a ridge of back-to-back stairs, hip ends."""
    cells, w, d = {}, 9, 7
    for layer in range(3):
        x0, x1, z0, z1 = layer, w - 1 - layer, layer, d - 1 - layer
        for x in range(x0, x1 + 1):
            cells[(x, layer, z0)] = (DARK, "south", "bottom")
            cells[(x, layer, z1)] = (DARK, "north", "bottom")
        for z in range(z0 + 1, z1):
            cells[(x0, layer, z)] = (DARK, "east", "bottom")
            cells[(x1, layer, z)] = (DARK, "west", "bottom")
    for x in range(-1, w + 1):  # eave: upside-down edge, one row outside the roof footprint
        cells[(x, 0, -1)] = (DARK, "south", "top")
        cells[(x, 0, d)] = (DARK, "north", "top")
    return {(x + 1, y, z + 1): v for (x, y, z), v in cells.items()}  # keep every position non-negative


def fx_seam_whole() -> dict[tuple[int, int, int], Cell]:
    """A stepped, turning stair run that crosses x = SEAM_X; module A is x < SEAM_X, module B is x >= SEAM_X."""
    cells = {}
    for x in range(0, 16):
        cells[(x, 0, 2)] = (BRICK, "south", "bottom")
    for z in range(3, 8):
        cells[(7, 0, z)] = (BRICK, "east", "bottom")  # turn right at the seam: x=7 | x=8
        cells[(8, 0, z)] = (BRICK, "west", "bottom")
    cells[(8, 0, 2)] = (BRICK, "south", "bottom")
    for x in range(0, 16):
        cells[(x, 0, 10)] = (BRICK, "north", "top")
    for z in range(11, 14):
        cells[(8, 0, z)] = (BRICK, "west", "top")
        cells[(7, 0, z)] = (BRICK, "east", "top")
    return cells


SEAM_X = 8


# ----------------------------------------------------------------------------------------------- source files
def _varints(values):
    out = []
    for v in values:
        while True:
            b, v = v & 0x7F, v >> 7
            out.append(b | 0x80 if v else b)
            if not v:
                break
    return [b - 256 if b > 127 else b for b in out]


def write_schem(path: Path, states: dict[tuple[int, int, int], str], size) -> Path:
    palette = {"minecraft:air": 0}
    data = []
    for y, z, x in itertools.product(range(size[1]), range(size[2]), range(size[0])):
        text = states.get((x, y, z), "minecraft:air")
        data.append(palette.setdefault(text, len(palette)))
    schematic = Compound(
        {
            "Version": Int(3),
            "DataVersion": Int(3953),
            "Width": Short(size[0]),
            "Height": Short(size[1]),
            "Length": Short(size[2]),
            "Offset": IntArray([0, 0, 0]),
            "Blocks": Compound(
                {
                    "Palette": Compound({s: Int(i) for s, i in palette.items()}),
                    "Data": ByteArray(_varints(data)),
                    "BlockEntities": List[Compound]([]),
                }
            ),
            "Entities": List[Compound]([]),
        }
    )
    nbtlib.File(Compound({"Schematic": schematic}), gzipped=True, root_name="").save(path)
    return path


def box_size(cells) -> tuple[int, int, int]:
    return tuple(max(p[i] for p in cells) + 1 for i in range(3))


def state_text(block_id, facing, half, shape) -> str:
    return f"{block_id}[facing={facing},half={half},shape={shape}]"


def export(name: str, states: dict, size, pack: Path, air: str = "include") -> C.Result:
    src = write_schem(pack.parent / f"{name}.schem", states, size)
    config = C.Config(
        path=SAMPLE,
        source=src,
        source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
        source_data_version=3953,
        target="26.3",
        structure_id=f"moreminecrafts:stair_live/{name}",
        datapack=pack,
        reports=pack.parent / "reports",
        size=size,
        offset=(0, 0, 0),
        air=air,
    )
    result = C.convert(config)
    C.write(result)
    return result


# ----------------------------------------------------------------------------------------------- server plumbing
def make_server(work: Path, jar: Path, java: str, pack: Path | None):
    return Server(
        work,
        jar,
        java,
        {
            "level-type": "minecraft:flat",
            "generator-settings": json.dumps(FLAT, separators=(",", ":")),
            "generate-structures": "false",
            "rcon.port": str(_free_port()),
            "server-port": str(_free_port()),
            "level-seed": "1",
        },
        datapack=pack,
    )


def forceload(server, x0, z0, x1, z1):
    """/forceload accepts at most 256 chunks per call: add the area in 128-block tiles."""
    for x in range(x0, x1 + 1, 128):
        for z in range(z0, z1 + 1, 128):
            reply = server.cmd(f"forceload add {x} {z} {min(x + 127, x1)} {min(z + 127, z1)}")
            if not reply.startswith("Marked"):
                raise RuntimeError(f"forceload: {reply}")


def wait_loaded(server, x, y, z, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if "not loaded" not in server.cmd(f"execute if block {x} {y} {z} minecraft:air"):
            return
        time.sleep(2)
    raise TimeoutError(f"chunk at {x},{z} never loaded")


def shape_in_game(server, at, block_id, facing, half) -> str | None:
    found = [
        s
        for s in SHAPES
        if "passed"
        in server.cmd(f"execute if block {at[0]} {at[1]} {at[2]} {block_id}[facing={facing},half={half},shape={s}]")
    ]
    return found[0] if len(found) == 1 else None


def game_shapes(server, cells: dict, origin) -> dict:
    """Place bare stairs (facing + half only), let the game settle every shape, return {pos: shape}."""

    def put(pos, bid, facing, half):
        at = add(origin, pos)
        return server.cmd(f"setblock {at[0]} {at[1]} {at[2]} {bid}[facing={facing},half={half}]")

    for pos, (bid, facing, half) in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0])):
        put(pos, bid, facing, half)
    for _ in range(4):  # recompute until the game changes nothing
        changed = 0
        for pos, (bid, facing, half) in sorted(cells.items()):
            if put(pos, bid, facing, half).startswith("Changed the block"):
                changed += 1
        if not changed:
            break
    else:
        raise RuntimeError("game stair shapes did not settle")
    out = {}
    for pos, (bid, facing, half) in cells.items():
        s = shape_in_game(server, add(origin, pos), bid, facing, half)
        if s is None:
            raise RuntimeError(f"cannot read shape at {pos}")
        out[pos] = s
    return out


def run(server_jar: Path, java: str, work: Path) -> dict:
    work = Path(work)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    result: dict = {"fixtures": {}}

    # ---- fixtures: {name: (cells {pos: (bid,f,h)}, shapes {pos: shape}|None for authored matrix)}
    matrix = fx_matrix_slots()
    fixtures = {
        "pairs": fx_pairs(),
        "corners": fx_corners(),
        "spiral": fx_spiral(),
        "corbel": fx_corbel(),
        "roof": fx_roof(),
        "seam_whole": fx_seam_whole(),
    }
    seam_a = {p: v for p, v in fixtures["seam_whole"].items() if p[0] < SEAM_X}
    seam_b = {(p[0] - SEAM_X, p[1], p[2]): v for p, v in fixtures["seam_whole"].items() if p[0] >= SEAM_X}

    # ---- phase 1: the game decides shapes
    oracle = make_server(work / "oracle", server_jar, java, None)
    shapes: dict[str, dict] = {}
    try:
        oracle.start()
        forceload(oracle, 0, 0, 255, 255)
        wait_loaded(oracle, 250, 10, 250)
        oy = 10
        for i, (name, cells) in enumerate(list(fixtures.items()) + [("seam_a", seam_a), ("seam_b", seam_b)]):
            origin = (10 + 80 * (i % 3), oy, 10 + 80 * (i // 3))
            shapes[name] = game_shapes(oracle, cells, origin)
    finally:
        oracle.stop()
    cells_all = {**fixtures, "seam_a": seam_a, "seam_b": seam_b}
    for name, cells in cells_all.items():
        counts = {s: sum(1 for v in shapes[name].values() if v == s) for s in SHAPES}
        result["fixtures"][name] = {"stairs": len(cells), "game_shapes": counts}
        if name in ("pairs", "corners", "spiral", "roof") and counts["straight"] == len(cells):
            raise RuntimeError(f"fixture {name} has no corner shape; it would prove nothing")

    # ---- phase 2: export + strict/normal placement at four rotations
    pack = work / "pack" / "mmst_stair_live"
    (pack / "data").mkdir(parents=True)
    import zipfile

    with zipfile.ZipFile(server_jar) as z:
        version = json.loads(z.read("version.json"))
    pf = [version["pack_version"]["data_major"], version["pack_version"]["data_minor"]]
    (pack / "pack.mcmeta").write_text(
        json.dumps({"pack": {"description": "STAIR-01 live", "min_format": pf, "max_format": pf}})
    )

    expected: dict[str, dict] = {}
    exports: dict[str, C.Result] = {}
    mat_states = {p: state_text(b, f, h, s) for p, (b, f, h, s) in matrix.items()}
    expected["matrix"] = {p: (b, {"facing": f, "half": h, "shape": s}) for p, (b, f, h, s) in matrix.items()}
    exports["matrix"] = export("matrix", mat_states, box_size(matrix), pack)
    for name, cells in cells_all.items():
        st = {p: state_text(b, f, h, shapes[name][p]) for p, (b, f, h) in cells.items()}
        expected[name] = {p: (b, {"facing": f, "half": h, "shape": shapes[name][p]}) for p, (b, f, h) in cells.items()}
        exports[name] = export(name, st, box_size(cells), pack)

    server = make_server(work / "server", server_jar, java, pack)
    sizes = {n: tuple(exports[n].report["size"]) for n in exports}
    try:
        server.start()
        result["datapacks"] = server.cmd("datapack list enabled")
        layouts = {n: Layout(sizes[n]) for n in sizes}
        # one block of plots per fixture, stacked along z
        z_base, plots = 0, {}
        for n, lay in layouts.items():
            plots[n] = z_base
            z_base += 4 * lay.gap + 8
        forceload(server, 0, 0, 5 * max(lay.gap for lay in layouts.values()) + 40, z_base + 40)
        wait_loaded(server, 1, 10, z_base + 39)
        for n, lay in layouts.items():
            shift = plots[n]
            fail_all, rot_report = [], {}
            for r, rotation in enumerate(ROTATIONS):
                o_strict = tuple(a + b for a, b in zip(lay.origin(0, r), (0, 0, shift), strict=True))
                o_norm = tuple(a + b for a, b in zip(lay.origin(1, r), (0, 0, shift), strict=True))
                for origin, strict in ((o_strict, True), (o_norm, False)):
                    reply = server.cmd(
                        f"place template {exports[n].config.structure_id} {origin[0]} {origin[1] + 10} {origin[2]} "
                        f"{rotation} none 1 0{' strict' if strict else ''}"
                    )
                    if not reply.startswith("Loaded template"):
                        raise RuntimeError(f"{n} {rotation}: {reply}")
                strict_bad, normal_changed = [], []
                for pos, (bid, props) in sorted(expected[n].items()):
                    want = _text(bid, rotate_props(props, rotation))
                    for _tag, origin, bucket in (("strict", o_strict, strict_bad), ("normal", o_norm, normal_changed)):
                        at = _at((origin[0], origin[1] + 10, origin[2]), pos, rotation)
                        ok = "passed" in server.cmd(f"execute if block {at[0]} {at[1]} {at[2]} {want}")
                        if not ok:
                            bucket.append({"pos": list(pos), "expected": want})
                rot_report[rotation] = {
                    "cells": len(expected[n]),
                    "strict_mismatches": strict_bad[:10],
                    "strict_mismatch_count": len(strict_bad),
                    "normal_placement_changed_count": len(normal_changed),
                    "normal_placement_changed_examples": normal_changed[:5],
                }
                fail_all += strict_bad
            fx = result["fixtures"].setdefault(n, {"stairs": len(expected[n])})
            fx["rotations"] = rot_report
            fx["pass"] = not fail_all
    finally:
        server.stop()

    # ---- seam: boundary-dependent stairs vs. the converter's stair_boundary_review
    whole, a, b = shapes["seam_whole"], shapes["seam_a"], shapes["seam_b"]
    dependent = []
    for p, shape in whole.items():
        alone = a.get(p) if p[0] < SEAM_X else b.get((p[0] - SEAM_X, p[1], p[2]))
        if alone != shape:
            dependent.append({"pos": list(p), "alone": alone, "assembled": shape})
    reviewed = set()
    for name, off in (("seam_a", 0), ("seam_b", SEAM_X)):
        for e in exports[name].report.get("stair_boundary_review", []):
            reviewed.add(((e["pos"][0] + off, e["pos"][1], e["pos"][2]), e["side"]))
    uncovered = [d for d in dependent if not any((tuple(d["pos"]), s) in reviewed for s in FACING)]
    result["seam"] = {
        "stairs_whole": len(whole),
        "boundary_dependent_stairs": dependent,
        "not_covered_by_stair_boundary_review": uncovered,
    }
    log = (work / "server" / "server.log").read_text(errors="replace")
    result["log_problems"] = [
        line for line in log.splitlines() if ("/ERROR]" in line or "Failed to load" in line or "Exception" in line)
    ][:20]
    result["result"] = (
        "PASS"
        if all(f.get("pass") for f in result["fixtures"].values()) and not uncovered and not result["log_problems"]
        else "FAIL"
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-jar", type=Path, required=True)
    ap.add_argument("--java", default="java")
    ap.add_argument("--work", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    ref = C.load_reference("26.3")
    if hashlib.sha1(a.server_jar.read_bytes()).hexdigest() != ref["server_jar_sha1"]:
        raise SystemExit("server jar is not the pinned 26.3 jar")
    res = run(a.server_jar, a.java, a.work or Path(tempfile.mkdtemp(prefix="stair-live-")))
    text = json.dumps(res, indent=2, sort_keys=True, default=str) + "\n"
    if a.out:
        a.out.write_text(text)
    print(text if not a.out else f"{res['result']}: wrote {a.out}")
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
