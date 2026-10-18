"""Stage 24-C regression tests: every assertion here encodes a defect that a real 26.1.2 server exposed."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.stage24c.common import MODULES, S24B, blocks_of, load_nbt  # noqa: E402

FACING = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
PARTIAL = ("_stairs", "_slab", "_wall", "_door", "_trapdoor", "_bed", "_fence", "ladder", "lantern", "air", "water", "jigsaw",
           "button", "skull", "carpet", "torch")


def bid(state):
    return state.split("[", 1)[0].replace("minecraft:", "")


def prop(state, key):
    for piece in state.split("[", 1)[-1].rstrip("]").split(","):
        if piece.startswith(key + "="):
            return piece.split("=", 1)[1]
    return None


def full_cube(state):
    n = bid(state)
    return not any(n.endswith(s) or n == s for s in PARTIAL)


@pytest.fixture(scope="module")
def structures():
    return {m: {p: s for p, (s, _) in blocks_of(load_nbt(S24B / m / "restored.nbt")).items()} for m in MODULES}


def at(b, p):
    return b.get(p, "minecraft:air")


@pytest.mark.parametrize("module", MODULES)
def test_lanterns_have_a_floor_or_ceiling(structures, module):
    """Live defect: 15 soul lanterns with hanging=false and nothing below popped off on placement."""
    b = structures[module]
    for (x, y, z), s in b.items():
        if bid(s) != "soul_lantern":
            continue
        if prop(s, "hanging") == "true":
            assert bid(at(b, (x, y + 1, z))) != "air", (module, (x, y, z), "hanging lantern without ceiling")
        else:
            below = at(b, (x, y - 1, z))
            assert bid(below) not in ("air", "water"), (module, (x, y, z), "standing lantern without floor")


@pytest.mark.parametrize("module", MODULES)
def test_ladders_are_mounted_on_a_full_block(structures, module):
    """Live defect: large_pillar_1 ladders faced east into the open entrance tunnel and popped off."""
    b = structures[module]
    for (x, y, z), s in b.items():
        if bid(s) != "ladder":
            continue
        dx, dz = FACING[prop(s, "facing")]
        support = at(b, (x - dx, y, z - dz))
        assert full_cube(support), (module, (x, y, z), s, "support", support)


@pytest.mark.parametrize("module", MODULES[:5])
def test_beds_are_not_obstructed(structures, module):
    """Live defect: small_ruin_2 beds sat under wall blocks ("This bed is obstructed")."""
    b = structures[module]
    for (x, y, z), s in b.items():
        if bid(s).endswith("_bed"):
            assert not full_cube(at(b, (x, y + 1, z))) and bid(at(b, (x, y + 1, z))) == "air", (module, (x, y, z))


def test_medium_ruin_2_stair_run_has_two_cells_of_headroom(structures):
    """Live defect: the 2nd and 4th steps had roof/wall blocks within 1.8 blocks of the player's head."""
    b = structures["medium_ruin_2"]
    run = [(4, 1, 5), (5, 2, 5), (6, 3, 5), (7, 4, 5)]
    for x, y, z in run:
        assert bid(at(b, (x, y, z))) == "deepslate_tile_stairs"
        assert prop(at(b, (x, y, z)), "facing") == "east"
        for dy in (1, 2) + ((3,) if (x, y, z) != run[-1] else ()):
            assert bid(at(b, (x, y + dy, z))) == "air", ((x, y, z), dy, at(b, (x, y + dy, z)))
    # the landing keeps a 2-high clear opening in the upper west wall
    for dy in (1, 2):
        assert bid(at(b, (7, 4 + dy, 5))) == "air"
    assert bid(at(b, (8, 5, 5))) == "air" and bid(at(b, (8, 6, 5))) == "air"


def test_medium_pillar_1_deck_has_a_complete_parapet(structures):
    """Live defect: a player walked off 12 of 22 probed deck edges and fell 8 blocks."""
    b = structures["medium_pillar_1"]
    deck = {(x, z) for x in range(1, 6) for z in range(1, 7) if bid(at(b, (x, 8, z))) not in ("air", "ladder")}
    assert deck
    perimeter = {(x, z) for x, z in deck if x in (1, 5) or z in (1, 6)}
    for x, z in perimeter:
        assert bid(at(b, (x, 9, z))) == "polished_deepslate_wall", ((x, z), at(b, (x, 9, z)))
    # the ladder, east of the retained spine, is untouched (owner constraint)
    assert [bid(at(b, (4, y, 3))) for y in range(1, 9)] == ["ladder"] * 8
    assert prop(at(b, (4, 1, 3)), "facing") == "west"


def test_medium_pillar_1_parapet_survives_vanilla_degradation(structures):
    """Real generation (24 seeds): 27/630 parapet walls were rotted away when made of deepslate_tile_wall."""
    rottable = {"deepslate", "deepslate_bricks", "deepslate_tiles", "deepslate_brick_slab", "deepslate_tile_slab",
                "deepslate_brick_stairs", "deepslate_tile_wall", "deepslate_brick_wall", "cobbled_deepslate",
                "cracked_deepslate_bricks", "cracked_deepslate_tiles", "gray_wool"}
    b = structures["medium_pillar_1"]
    ring = [bid(s) for (x, y, z), s in b.items() if y == 9 and bid(s).endswith("_wall")]
    assert len(ring) == 18 and not (set(ring) & rottable)


def test_large_pillar_1_deck_edges_are_closed(structures):
    b = structures["large_pillar_1"]
    ring = [(x, z) for x in range(6) for z in range(6) if x in (0, 1, 4, 5) or z in (0, 1, 4, 5)]
    for x, z in ring:
        assert bid(at(b, (x, 14, z))) != "air", ((x, z), "gap in deck parapet ring")


def test_large_pillar_1_ladder_reaches_deck_surface(structures):
    """Live defect: ladder ended at y=12 and the climber hung 1 block under the y=13 deck (feet need y=14)."""
    b = structures["large_pillar_1"]
    assert [bid(at(b, (2, y, 2))) for y in range(1, 14)] == ["ladder"] * 13
    assert bid(at(b, (2, 14, 2))) == "air"
