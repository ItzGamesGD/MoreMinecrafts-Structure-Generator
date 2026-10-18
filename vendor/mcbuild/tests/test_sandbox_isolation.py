"""Tests for run_blueprint_isolated (2026-10-18 security audit remediation).

The "real child" tests start `python -I -m mcbuild.dsl.isolated_child`, so they are slower than
the rest of the suite. The rest test the parent's validation and status mapping with stubs.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

import pytest

import mcbuild.dsl.sandbox as sandbox
from mcbuild import palette
from mcbuild.dsl.errors import BlueprintError
from mcbuild.dsl.sandbox import (
    IsolatedExecutionError,
    decode_grid,
    encode_grid,
    run_blueprint,
    run_blueprint_isolated,
)
from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid

_SRC_DIR = Path(sandbox.__file__).parent


class _RecordingPopen(subprocess.Popen):
    """Real Popen that remembers every child (and how it was launched) so tests can prove each
    was reaped and started with the expected isolation settings."""

    instances: list[subprocess.Popen] = []
    launch_kwargs: list[dict] = []

    def __init__(self, *args, **kwargs):
        _RecordingPopen.launch_kwargs.append(kwargs)
        super().__init__(*args, **kwargs)
        _RecordingPopen.instances.append(self)


@pytest.fixture
def recorded_children(monkeypatch):
    _RecordingPopen.instances = []
    _RecordingPopen.launch_kwargs = []
    monkeypatch.setattr(sandbox.subprocess, "Popen", _RecordingPopen)
    yield _RecordingPopen.instances
    for child in _RecordingPopen.instances:
        assert child.returncode is not None, "isolated child was left running"


# --- real child: behavior parity and edit semantics ----------------------------------------


def test_isolated_execution_matches_in_process_result(recorded_children):
    source = "fill(0, 0, 0, 2, 2, 2, 'stone')"
    in_process = VoxelGrid()
    run_blueprint(source, in_process, seed=0)

    isolated = run_blueprint_isolated(source, VoxelGrid(), seed=0)

    assert isolated.bounds == in_process.bounds
    assert dict(isolated.items()) == dict(in_process.items())
    assert len(recorded_children) == 1


def test_dynamic_block_states_survive_the_process_boundary(recorded_children):
    """Regression: a state like oak_stairs[facing=north] exists only in the child's palette.
    Sending raw palette indices would resolve to the wrong block (or fail) in the parent."""
    result = run_blueprint_isolated("fill(0, 0, 0, 1, 0, 0, 'oak_stairs[facing=north]')", VoxelGrid(), seed=0)

    names = {palette.get_block_by_index(index).mc_id for _, index in result.items()}
    assert names == {"minecraft:oak_stairs[facing=north]"}


def test_isolated_execution_preserves_existing_build_for_edits(recorded_children):
    """Edit semantics: the blueprint runs against the current build, so get_block() sees it."""
    stone = get_block("stone").index
    start = VoxelGrid()
    start.set(7, 0, 7, stone)

    result = run_blueprint_isolated(
        "assert get_block(7, 0, 7) is not None\nfill(0, 0, 0, 1, 0, 1, 'stone')", start, seed=0
    )

    assert result.get(7, 0, 7) == stone
    assert len(result) == 5


def test_input_grid_is_not_mutated(recorded_children):
    start = VoxelGrid()
    start.set(0, 0, 0, get_block("stone").index)
    before = dict(start.items())

    run_blueprint_isolated("fill(0, 0, 0, 3, 0, 3, 'dirt')", start, seed=0)

    assert dict(start.items()) == before


def test_isolated_execution_reports_blueprint_errors_as_blueprint_error(recorded_children):
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint_isolated("this_name_does_not_exist()", VoxelGrid(), seed=0)
    assert "this_name_does_not_exist" in str(exc_info.value)
    assert exc_info.value.line == 1
    assert not isinstance(exc_info.value, IsolatedExecutionError)


def test_isolated_execution_reports_sandbox_violations(recorded_children):
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint_isolated("x = (1).__class__\n", VoxelGrid(), seed=0)
    assert "not allowed" in str(exc_info.value)


def test_runaway_python_loop_stops_on_the_in_sandbox_budget(recorded_children):
    start = time.monotonic()
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint_isolated("while True:\n    pass\n", VoxelGrid(), seed=0, max_seconds=1.0, timeout=10.0)
    assert "budget" in str(exc_info.value).lower() or "lines" in str(exc_info.value).lower()
    assert time.monotonic() - start < 10.0


# --- real child: resource limits and cleanup -----------------------------------------------


def test_c_level_busy_work_is_killed_by_parent_timeout(recorded_children):
    """sum() over a huge range runs in C with no Python line events, so the in-sandbox budget
    never fires. The parent deadline must still kill the child promptly and report it."""
    start = time.monotonic()
    with pytest.raises(IsolatedExecutionError) as exc_info:
        run_blueprint_isolated("sum(range(10 ** 12))", VoxelGrid(), seed=0, timeout=3.0)
    elapsed = time.monotonic() - start
    assert "did not finish" in str(exc_info.value)
    assert elapsed < 6.0  # deadline + a short reap, not a grace period


def test_memory_hog_is_stopped_by_the_address_space_limit(recorded_children):
    """[0] * 10**10 needs ~80 GB; the 1 GiB address-space cap makes the child raise MemoryError,
    which is reported as an ordinary blueprint error while the parent keeps running."""
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint_isolated("x = [0] * (10 ** 10)\n", VoxelGrid(), seed=0, timeout=30.0)
    assert "memory limit" in exc_info.value.raw_message
    assert not isinstance(exc_info.value, IsolatedExecutionError)


def test_child_gets_no_inherited_secrets_and_no_repository_cwd(recorded_children, monkeypatch):
    """Regression: the child used to inherit os.environ, so an escaped blueprint could read
    OPENROUTER_API_KEY. It must start with an empty environment and a scratch working directory."""
    import os

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-should-not-leak")
    run_blueprint_isolated("pass", VoxelGrid(), seed=0)

    launch = _RecordingPopen.launch_kwargs[-1]
    assert launch["env"] == {}
    assert "OPENROUTER_API_KEY" not in launch["env"]
    assert launch["cwd"] != os.getcwd()
    assert not os.path.exists(launch["cwd"])  # scratch directory removed after the run


def test_child_runs_in_isolated_mode_with_no_pickle_on_the_boundary(recorded_children):
    run_blueprint_isolated("pass", VoxelGrid(), seed=0)
    assert "-I" in recorded_children[0].args
    banned_import = re.compile(r"^\s*(import|from)\s+(pickle|marshal|shelve|multiprocessing)\b", re.MULTILINE)
    for module in (sandbox, _load_child_module()):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert banned_import.search(source) is None, module.__name__


def _load_child_module():
    import mcbuild.dsl.isolated_child as child

    return child


# --- fail closed ----------------------------------------------------------------------------


def test_fails_closed_when_isolation_is_unsupported(monkeypatch):
    monkeypatch.setattr(sandbox, "isolation_supported", lambda: False)
    spawned = []
    monkeypatch.setattr(sandbox.subprocess, "Popen", lambda *a, **k: spawned.append((a, k)))

    with pytest.raises(IsolatedExecutionError) as exc_info:
        run_blueprint_isolated("fill(0, 0, 0, 1, 1, 1, 'stone')", VoxelGrid(), seed=0)

    assert "refusing to run" in str(exc_info.value)
    assert spawned == []


# --- parent-side validation and status mapping (stubbed child) -------------------------------


class _StubChild:
    def __init__(self):
        self.returncode = 0
        self.stdin = _StubStdin()

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass

    def terminate(self):
        pass


class _StubStdin:
    def fileno(self):
        return -1

    def close(self):
        pass


@pytest.fixture
def stub_child(monkeypatch):
    """Replace the child and its pipe reads, so tests choose exactly the bytes the parent sees."""
    result = {"raw": b""}
    monkeypatch.setattr(sandbox.subprocess, "Popen", lambda *a, **k: _StubChild())
    monkeypatch.setattr(sandbox, "_send_all", lambda fd, data, deadline: None)
    monkeypatch.setattr(sandbox, "_recv_all", lambda fd, deadline: result["raw"])
    return result


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"status": "isolation_failed", "message": "could not apply resource limits: boom"}, "boom"),
        ({"status": "error", "message": "NameError: x", "line": 3}, "NameError"),
    ],
)
def test_status_mapping(stub_child, payload, message):
    stub_child["raw"] = json.dumps(payload).encode()
    with pytest.raises(BlueprintError) as exc_info:
        run_blueprint_isolated("pass", VoxelGrid(), seed=0)
    assert message in str(exc_info.value)
    assert isinstance(exc_info.value, IsolatedExecutionError) == (payload["status"] == "isolation_failed")


@pytest.mark.parametrize(
    "raw, fragment",
    [
        (b"", "without a result"),
        (b"not json", "not valid JSON"),
        (b"[1, 2]", "unexpected shape"),
        (json.dumps({"status": "mystery"}).encode(), "no message"),
        (json.dumps({"status": "mystery", "message": "?"}).encode(), "unknown status"),
    ],
)
def test_malformed_results_are_isolated_execution_errors(stub_child, raw, fragment):
    stub_child["raw"] = raw
    with pytest.raises(IsolatedExecutionError) as exc_info:
        run_blueprint_isolated("pass", VoxelGrid(), seed=0)
    assert fragment in str(exc_info.value)


@pytest.mark.parametrize(
    "payload",
    [
        "x",
        {"blocks": "not-a-list"},
        {"blocks": [[0, 0, 0]]},
        {"blocks": [[True, 0, 0, "stone"]]},
        {"blocks": [[0, 0, 0, "__import__('os')"]]},
        {"blocks": [[0, 0, 0, "stone[" + "a" * 300 + "]"]]},
        {"blocks": [[0, 0, 0, "not_a_real_block"]]},
        {"blocks": [[0, 0, 0, "stone"]], "warnings": [1]},
    ],
)
def test_decoder_rejects_malicious_or_malformed_grids(payload):
    with pytest.raises(IsolatedExecutionError):
        decode_grid(payload)


def test_decoder_enforces_grid_extent_between_blocks():
    payload = {"blocks": [[0, 0, 0, "stone"], [10_000, 0, 0, "stone"]]}
    with pytest.raises(IsolatedExecutionError):
        decode_grid(payload)


def test_encode_decode_round_trip_keeps_blocks_and_warnings():
    grid = VoxelGrid()
    grid.set(1, 2, 3, get_block("oak_stairs[facing=east]").index)
    grid.palette_warnings = ["a warning"]

    decoded = decode_grid(json.loads(json.dumps(encode_grid(grid))))

    assert dict(decoded.items()) == dict(grid.items())
    assert decoded.palette_warnings == ["a warning"]
