"""Shared helpers for the three perimeter-wall design prototypes (A, B, C).

Fixed for every prototype (functional contract, unchanged from batch 8 / the placement table):
  MW86 86x13x5 (W-N, W-E, W-W) and MW31 31x13x5 (W-SW, W-SE), air=omit, y=0 at grade, local z=0 is the exterior
  face in every placement, both ends of both modules abut a reserved tower square or the gatehouse (MW31 meets the
  gate with either end, so its two ends must work identically); a full footing course at y=0 under every column (the
  Q89 below-grade fill builds on it); the top stays within y=12.
"""

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

from tools.seam01 import assembly as A
from tools.seam01.export import export_module

ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B4 = _load("batch4_build", EXP / "st03-batch4-barracks" / "build.py")
Cells, noise = B4.Cells, B4.noise
H, D = 13, 5
LENGTHS = {"MW86": 86, "MW31": 31}


def stairs(c, x, y, z, mat, facing, half="bottom", shape="straight"):
    c.put(x, y, z, f"{mat}_stairs", facing=facing, half=half, shape=shape, waterlogged=False)


def slab(c, x, y, z, mat, half):
    c.put(x, y, z, f"{mat}_slab", type=half, waterlogged=False)


def trap(c, x, y, z, mat, facing, open_, half="bottom"):
    c.put(x, y, z, f"{mat}_trapdoor", facing=facing, half=half, open=open_, powered=False, waterlogged=False)


def lantern(c, x, y, z, hanging=True):
    c.put(x, y, z, "lantern", hanging=hanging, waterlogged=False)


def banner(c, x, y, z, facing):
    c.put(x, y, z, "white_wall_banner", facing=facing)


def log(c, x, y, z, axis, wood="dark_oak"):
    c.put(x, y, z, f"{wood}_log", axis=axis)


# ------------------------------------------------------------------------------------------------ stone (owner
# principle: stone / andesite / cobblestone / stone bricks / cracked and mossy variants mixed naturally, coherent edges,
# weathering in staggered patches rather than per-block speckle)

def ashlar(x, y, z, low=4):
    """Dressed stone-brick masonry with patch weathering (mossy only low on the wall)."""
    patch = noise((x + 2 * (y // 3)) // 4, y // 3, 9, 41 + z)
    hit = noise(x, y, 3, 17 + z) != 0
    if patch == 0 and hit:
        return "cracked_stone_bricks"
    if patch == 1 and hit and y <= low:
        return "mossy_stone_bricks"
    if patch == 2 and noise(x, y, 4, 9) == 0:
        return "andesite" if y <= low + 1 else "cracked_stone_bricks"
    return "stone_bricks"


def rubble(x, y, z):
    """Rough rubble masonry (scarps, talus, footing): cobble / andesite / stone with mossy patches low down."""
    patch = noise((x + 3 * (y // 2)) // 3, y // 2, 6, 77 + z)
    r = noise(x, y, 4, 13 + z) != 0
    pair = {0: ("cobblestone", "mossy_cobblestone"), 1: ("cobblestone", "andesite"), 2: ("andesite", "stone"),
            3: ("stone_bricks", "mossy_stone_bricks"), 4: ("cobblestone", "mossy_cobblestone"),
            5: ("stone", "cobblestone")}[patch]
    v = pair[0 if r else 1]
    if y >= 4 and v.startswith("mossy"):
        v = v.replace("mossy_", "")
    return v


def rubble_stair(x, y, z):
    return ("cobblestone", "andesite", "cobblestone", "mossy_cobblestone", "stone")[noise(x, y, 5, 7 + z)]


def ashlar_stair(x, y, z):
    return "mossy_stone_brick" if (y <= 3 and noise(x, y, 6, 3 + z) == 0) else "stone_brick"


def footing(c, L):
    for x in range(L):
        for z in range(D):
            c.put(x, 0, z, rubble(x, 0, z))


def crenels(L, end, period, merlon):
    """Symmetric crenel columns: from each end, `end` merlon columns, then (merlon, crenel) repeating with crenels
    1 wide every `period`; the right half mirrors the left, so the middle merlon absorbs the remainder."""
    out = set()
    for x in range((L + 1) // 2):
        if x >= end and (x - end) % period == merlon:
            out.add(x)
    out |= {L - 1 - x for x in out}
    return out


def export(design, cells_by_module, outdir):
    """Export each module's cells with the real converter to outdir/<file>.nbt (+ .schem, export report)."""
    outdir.mkdir(parents=True, exist_ok=True)
    mods = A.modules()
    rows = {}
    for mid, cells in cells_by_module.items():
        module = mods[mid]
        assert module["size"] == [cells.W, cells.H, cells.D] and module["air"] == "omit", (design, mid)
        with tempfile.TemporaryDirectory() as d:
            result = export_module(module, dict(cells), Path(d) / "pack")
            shutil.copyfile(result.config.nbt_path, outdir / f"{module['file']}.nbt")
            shutil.copyfile(result.config.source, outdir / f"{module['file']}.schem")
            (outdir / f"{module['file']}.export-report.json").write_text(
                json.dumps(result.report, indent=2, sort_keys=True) + "\n")
        rows[mid] = len(cells)
        print(f"design {design} {module['file']}.nbt: {len(cells)} authored cells, size {module['size']}")
    return rows
