"""Tests for run_blueprint_isolated (2026-10-18 security audit remediation).

These spawn real child processes via multiprocessing, so they're slower than the rest of
the suite; kept in their own module so they're easy to skip/select separately if needed.
"""

from __future__ import annotations

import time

import pytest

from mcbuild.dsl.errors import BlueprintError
from mcbuild.dsl.sandbox import (
    IsolatedExecutionError,
    run_blueprint,
    run_blueprint_isolated,
)
from mcbuild.voxel import VoxelGrid


def test_isolated_execution_matches_in_process_result():
    source = "fill(0, 0, 0, 2, 2, 2, 'stone')"
    in_process = VoxelGrid()
    run_blueprint(source, in_process, seed=0)

    isolated = run_blueprint_isolated(source, seed=0)

    assert isolated.bounds == in_process.bounds
    assert len(isolated) == len(in_process)
    assert dict(isolated.items()) == dict(in_process.items())


def test_isolated_execution_reports_blueprint_errors():
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint_isolated("this_name_does_not_exist()", seed=0)
    assert "this_name_does_not_exist" in str(exc_info.value)


def test_isolated_execution_reports_sandbox_violations():
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint_isolated("x = (1).__class__\n", seed=0)
    assert "not allowed" in str(exc_info.value)


def test_isolated_execution_enforces_its_own_budget_without_hanging_the_caller():
    start = time.monotonic()
    with pytest.raises((BlueprintError, IsolatedExecutionError)):
        run_blueprint_isolated("while True:\n    pass\n", seed=0, max_seconds=1.0, timeout=10.0)
    # The point of isolation is that a runaway child can't hang the parent indefinitely;
    # it must come back well inside the outer `timeout` backstop.
    assert time.monotonic() - start < 10.0
