"""SEAM-01: 34 placements x 4 rotations, patch generation, validation and determinism (synthetic module contents)."""

# ruff: noqa: E501
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.seam01 import assembly as A
from tools.seam01 import export, synthetic
from tools.seam01 import patches as P
from tools.seam01.stairs import stairs_shape

REFERENCE = json.loads((Path(__file__).parent / "fixtures" / "seam01_design_manifests.json").read_text())


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    sources = synthetic.sources()
    templates, results = export.export_all(tmp_path_factory.mktemp("seam") / "pack", sources)
    return sources, templates, results, P.generate(0, sources, templates)


def test_plan_has_25_modules_and_34_placements():
    assert len(A.plan()["modules"]) == 25 and len(A.plan()["placements"]) == 34
    assert len(A.manifest(0)) == 34


@pytest.mark.parametrize("q", range(4))
def test_manifest_equals_the_design_package_reference(q):
    assert A.manifest(q) == REFERENCE[str(q)]


@pytest.mark.parametrize("q", range(4))
def test_every_template_cell_of_every_placement_lands_inside_the_rotated_box(q):
    n = A.box_size()
    for e in A.manifest(q):
        w, h, d = e["size"]
        for u in (0, w - 1):
            for v in (0, d - 1):
                x, _, z = A.place_cell(e, (u, 0, v))
                assert 0 <= x < n and 0 <= z < n and e["footprint"][0] <= x <= e["footprint"][2]


def test_patches_exist_and_touch_only_connecting_blocks(world):
    _, _, _, base = world
    assert len(base) > 100
    assert len({p.pos for p in base}) == len(base)
    assert all(p.block.endswith(("_wall", "_fence", "iron_bars", "glass_pane", "_fence_gate")) for p in base)


@pytest.mark.parametrize("q", range(4))
def test_rotated_patches_equal_patches_generated_for_the_rotated_structure(world, q):
    sources, templates, _, base = world
    assert P.rotate(base, q) == P.generate(q, sources, templates)


@pytest.mark.parametrize("q", range(4))
def test_module_assembly_plus_patches_equals_the_whole_structure(world, q):
    sources, templates, _, base = world
    patches = P.rotate(base, q)
    whole, _, _ = P.whole_structure(q, sources)
    assert P.validate(patches, P.module_result(q, templates), whole) == []


def test_generation_is_deterministic_and_application_order_does_not_matter(world):
    sources, templates, _, base = world
    again = P.patchset(0, P.generate(0, sources, templates))
    assert again == P.patchset(0, base)
    placed = P.module_result(0, templates)
    shuffled = base[:]
    random.Random(1).shuffle(shuffled)
    assert P.apply(placed, shuffled) == P.apply(placed, base)


def test_patchset_roundtrips_through_json(world):
    _, _, _, base = world
    ps = P.patchset(0, base)
    assert P.from_json(json.loads(json.dumps(ps))) == base


def test_validator_detects_missing_duplicate_conflicting_outside_and_misordered(world):
    sources, templates, _, base = world
    placed = P.module_result(0, templates)
    whole, _, _ = P.whole_structure(0, sources)
    assert any("missing" in m for m in P.validate(base[1:], placed, whole))
    assert any("duplicate" in m for m in P.validate(base[:1] + base, placed, whole))
    other = P.Patch(base[0].pos, base[0].block, base[0].state[::-1][:1] + base[0].state[1:], base[0].was)
    assert any("conflict" in m for m in P.validate([base[0], other] + base[1:], placed, whole))
    outside = P.Patch((500, 1, 1), base[0].block, base[0].state, base[0].was)
    assert any("outside" in m for m in P.validate(base + [outside], placed, whole))
    assert any("order" in m for m in P.validate(base[::-1], placed, whole))
    wrong = P.Patch(base[0].pos, "minecraft:oak_fence", base[0].state, base[0].was)
    assert any("targets" in m or "holds" in m for m in P.validate([wrong] + base[1:], placed, whole))


def test_stairs_are_never_patched_and_seam_stairs_are_covered_by_the_pr49_review(world):
    sources, templates, results, _ = world
    for q in range(4):
        report = P.stair_report(q, sources, templates)
        assert report["stairs"] > 100 and report["seam_dependent"]
        assert P.reconcile_stairs(q, report, results)["not_in_stair_boundary_review"] == []

    # negative control: without the PR #49 review nothing would be covered
    class Empty:
        report: dict = {}

    report = P.stair_report(0, sources, templates)
    empty = {m: Empty() for m in results}
    assert len(P.reconcile_stairs(0, report, empty)["not_in_stair_boundary_review"]) == len(report["seam_dependent"])


def test_module_alone_stairs_have_their_vanilla_shape(world):
    _, templates, _, _ = world
    for module in A.plan()["modules"]:
        cells = templates[module["id"]]
        for pos, (bid, props) in cells.items():
            if bid.endswith("_stairs"):
                assert stairs_shape(cells, pos) == props["shape"], (module["id"], pos)


def test_a_state_the_author_stated_is_never_patched(world):
    sources, templates, _, _ = world
    src = {m: dict(c) for m, c in sources.items()}
    # the author states every connection of a bar at a module edge as false; the (unchanged) module export still carries the
    # computed `true`, so the only way to match the whole structure would be to overwrite a stated value: refuse instead
    module, pos = next(
        (m, pos)
        for m, cells in src.items()
        for pos, (b, _) in cells.items()
        if b == "minecraft:iron_bars" and pos[0] == A.modules()[m]["size"][0] - 1 and pos[1] == 1
    )
    src[module][pos] = ("minecraft:iron_bars", dict.fromkeys(("north", "east", "south", "west"), "false"))
    with pytest.raises(P.SeamError, match="author-stated|not computed"):
        P.generate(0, src, templates)

@pytest.mark.parametrize("q", range(4))
def test_owner_stair_policy_and_dependent_connections(world, q):
    from tools.structure_export.live import ROTATIONS, rotate_props

    sources, templates, results, base = world
    placed = P.module_result(q, templates)
    whole, _, _ = P.whole_structure(q, sources)
    vanilla, _, _ = P.whole_structure(q, sources, vanilla_stairs=True)
    patches = P.generate(q, sources, templates)
    after = P.apply(placed, patches)
    seam = P.stair_report(q, sources, templates)["seam_dependent"]
    affected = [p for p in whole if whole[p] != vanilla[p] and not whole[p][0].endswith("_stairs")]
    assert len(seam) == 18 and len(affected) == 15
    assert not P.reconcile_stairs(q, {"seam_dependent": seam}, results)["not_in_stair_boundary_review"]
    assert all(after[tuple(s["pos"])] == whole[tuple(s["pos"])] == placed[tuple(s["pos"])] for s in seam)
    assert all(after[p] == whole[p] for p in affected)
    for (x, y, z), (block, props) in P.module_result(0, templates).items():
        if block.endswith("_stairs"):
            rx, rz = A.rot_cell(x, z, q)
            assert placed[(rx, y, rz)] == (block, rotate_props(props, ROTATIONS[q]))
    assert patches == P.rotate(base, q)
    assert P.apply(placed, patches) == P.apply(placed, list(reversed(patches)))
    assert P.validate(patches, placed, whole) == []
