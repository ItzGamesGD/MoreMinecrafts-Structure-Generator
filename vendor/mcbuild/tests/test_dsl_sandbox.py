import pytest

from mcbuild.dsl.errors import BlueprintError
from mcbuild.dsl.sandbox import SandboxViolation, compile_blueprint, run_blueprint
from mcbuild.voxel import VoxelGrid


def test_simple_fill_executes():
    grid = VoxelGrid()
    run_blueprint("fill(0, 0, 0, 1, 1, 1, 'stone')", grid)
    assert len(grid) == 8


def test_import_is_stripped_not_blocked():
    grid = VoxelGrid()
    run_blueprint("import os\nfill(0,0,0,1,1,1,'stone')", grid)
    assert len(grid) == 8


def test_import_from_is_stripped():
    grid = VoxelGrid()
    run_blueprint("from os import path\nfill(0,0,0,1,1,1,'stone')", grid)
    assert len(grid) == 8


def test_relying_on_stripped_import_fails_with_name_error():
    grid = VoxelGrid()
    with pytest.raises(BlueprintError):
        run_blueprint("import os\nx = os.getcwd()\n", grid)


def test_import_as_only_statement_in_block_still_compiles():
    grid = VoxelGrid()
    run_blueprint("if True:\n    import os\nfill(0,0,0,1,1,1,'stone')", grid)
    assert len(grid) == 8


def test_dunder_attribute_access_blocked():
    grid = VoxelGrid()
    with pytest.raises(BlueprintError):
        run_blueprint("x = (1).__class__\n", grid)


def test_banned_name_blocked():
    grid = VoxelGrid()
    with pytest.raises(BlueprintError):
        run_blueprint("eval('1+1')\n", grid)


def test_open_blocked():
    grid = VoxelGrid()
    with pytest.raises(BlueprintError):
        run_blueprint("open('x.txt')\n", grid)


def test_syntax_error_reports_line():
    grid = VoxelGrid()
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint("fill(0,0,0,1,1,1,'stone'\n", grid)
    assert exc_info.value.line is not None


def test_unknown_block_reports_line_and_suggestion():
    grid = VoxelGrid()
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint("x = 1\nfill(0,0,0,1,1,1,'stoen')\n", grid)
    err = exc_info.value
    assert err.line == 2
    assert "stone" in str(err)


### Regression tests for the 2026-10-18 security audit (confirmed sandbox-escape gaps). ###
### These reproduce the exact PoCs used to validate the finding; each failed (was NOT    ###
### blocked) before BANNED_ATTRS was added to validate_ast.                              ###


def test_str_format_dunder_chain_blocked():
    """str.format()'s template string is interpreted at runtime, not parsed as an
    ast.Attribute node, so a dunder chain inside it (the classic Python sandbox-escape
    primitive: reach object -> __subclasses__() -> an exploitable class) used to bypass
    the leading-underscore attribute check entirely."""
    with pytest.raises(SandboxViolation):
        compile_blueprint('x = "{0.__class__.__bases__}".format(0)')


def test_str_format_map_dunder_chain_blocked():
    with pytest.raises(SandboxViolation):
        compile_blueprint('x = "{a.__class__}".format_map({"a": 0})')


@pytest.mark.parametrize(
    "attr",
    [
        "gi_frame",
        "cr_frame",
        "ag_frame",
        "f_back",
        "f_globals",
        "f_locals",
        "f_builtins",
        "tb_frame",
        "co_consts",
        "cell_contents",
    ],
)
def test_frame_and_code_introspection_attrs_blocked(attr):
    """None of these start with '_', so they were invisible to the old dunder-only check.
    A generator's .gi_frame.f_back.f_globals chain (when reached while a frame is live on
    the call stack, e.g. during a generator's own next()/send()) walks back through
    run_blueprint's own call stack and beyond -- toward the embedding process's frames,
    not just the blueprint's."""
    with pytest.raises(SandboxViolation):
        compile_blueprint(f"x = None\nf = x.{attr}\n")


def test_infinite_loop_hits_budget():
    grid = VoxelGrid()
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint("while True:\n    pass\n", grid, max_lines=1000, max_seconds=2.0)
    assert "budget" in str(exc_info.value).lower() or "lines" in str(exc_info.value).lower()


def test_transform_stack_translate_and_mirror():
    grid = VoxelGrid()
    run_blueprint(
        """
def wing():
    set_block(1, 0, 0, 'stone')

wing()
with mirror('x', at=0):
    wing()
""",
        grid,
    )
    assert grid.get(1, 0, 0) == grid.get(-1, 0, 0)
    assert len(grid) == 2


def test_rotate_y_quarter_turn():
    grid = VoxelGrid()
    run_blueprint("set_block(2, 0, 0, 'stone')\nwith rotate_y(1):\n    set_block(2, 0, 0, 'stone')\n", grid)
    # rotate_y(1): (x, z) -> (-z, x) => (2, 0) -> (0, 2)
    assert grid.get(2, 0, 0) is not None
    assert grid.get(0, 0, 2) is not None


def test_seeded_rng_is_deterministic():
    grid1 = VoxelGrid()
    grid2 = VoxelGrid()
    src = "for i in range(5):\n    set_block(rng.randint(0, 10), 0, 0, 'stone')\n"
    run_blueprint(src, grid1, seed=42)
    run_blueprint(src, grid2, seed=42)
    assert dict(grid1.items()) == dict(grid2.items())


def test_get_block_returns_none_for_untouched_cell():
    grid = VoxelGrid()
    run_blueprint("x = get_block(0, 0, 0)\nset_block(9, 9, 9, 'stone' if x is None else 'glass')\n", grid)
    assert grid.get(9, 9, 9) is not None
    from mcbuild.palette import get_block as resolve

    assert grid.get(9, 9, 9) == resolve("stone").index


def test_get_block_returns_name_of_earlier_placed_block():
    grid = VoxelGrid()
    run_blueprint(
        """
set_block(0, 0, 0, 'stone')
found = get_block(0, 0, 0)
set_block(1, 0, 0, found)
""",
        grid,
    )
    assert grid.get(0, 0, 0) == grid.get(1, 0, 0)


def test_get_block_round_trips_block_state():
    grid = VoxelGrid()
    run_blueprint(
        """
set_block(0, 0, 0, "oak_stairs[facing=north,half=top]")
again = get_block(0, 0, 0)
set_block(1, 0, 0, again)
""",
        grid,
    )
    assert grid.get(0, 0, 0) == grid.get(1, 0, 0)


def test_get_block_reads_through_active_transforms():
    grid = VoxelGrid()
    run_blueprint(
        """
set_block(1, 0, 0, 'stone')
with mirror('x', at=0):
    seen = get_block(1, 0, 0)  # world coord (-1, 0, 0): nothing placed there yet
    set_block(1, 0, 0, 'glass' if seen is None else 'stone')  # writes to (-1, 0, 0)
""",
        grid,
    )
    assert grid.get(-1, 0, 0) is not None
    from mcbuild.palette import get_block as resolve

    assert grid.get(-1, 0, 0) == resolve("glass").index


def test_get_block_sees_cleared_cell_as_none_but_explicit_air_as_air():
    grid = VoxelGrid()
    run_blueprint(
        """
set_block(0, 0, 0, 'stone')
set_block(1, 0, 0, 'stone')
clear(0, 0, 0, 0, 0, 0)         # removed entirely -> None
set_block(1, 0, 0, 'air')       # explicitly placed air -> still a block
after_clear = get_block(0, 0, 0)
after_air = get_block(1, 0, 0)
set_block(5, 5, 5, 'glass' if after_clear is None else 'stone')
set_block(6, 6, 6, 'diamond_block' if after_air == 'air' else 'stone')
""",
        grid,
    )
    from mcbuild.palette import get_block as resolve

    assert grid.get(5, 5, 5) == resolve("glass").index
    assert grid.get(6, 6, 6) == resolve("diamond_block").index
