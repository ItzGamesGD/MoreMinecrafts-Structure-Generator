"""Regression tests: every LLM-facing blueprint execution path goes through the isolated executor.

The three call sites in agent/loop.py are submit_blueprint, edit_region and str_replace. Each
test drives the real agent loop with a scripted LLM, and asserts two things:

* run_blueprint_isolated handled the blueprint, and
* the in-process run_blueprint was never reached from the loop (it is forbidden for this run).
"""

from __future__ import annotations

import json

import pytest

from mcbuild.agent.loop import run_agent
from mcbuild.config import Config
from mcbuild.dsl import sandbox
from mcbuild.dsl.sandbox import IsolatedExecutionError
from mcbuild.llm.fake import FakeLLM, _FakeMessage, _FnCall, _ToolCall
from mcbuild.rundir import RunDir


def _tool_msg(name, args, call_id="c"):
    return _FakeMessage(tool_calls=[_ToolCall(id=call_id, function=_FnCall(name=name, arguments=json.dumps(args)))])


@pytest.fixture
def isolation_spy(monkeypatch):
    """Count isolated executions, and make any in-process execution from the loop a failure."""
    calls: list[str] = []
    real_isolated = sandbox.run_blueprint_isolated

    def spy(source, grid, **kwargs):
        calls.append(source)
        return real_isolated(source, grid, **kwargs)

    def forbidden_in_process(*args, **kwargs):
        raise AssertionError("agent loop executed a blueprint in-process; it must use run_blueprint_isolated")

    monkeypatch.setattr(sandbox, "run_blueprint_isolated", spy)
    monkeypatch.setattr(sandbox, "run_blueprint", forbidden_in_process)
    return calls


class _ScriptedLLM(FakeLLM):
    def __init__(self, steps):
        super().__init__()
        self._script = steps


def test_every_llm_facing_build_path_runs_through_isolation(tmp_path, isolation_spy):
    steps = [
        lambda: _tool_msg(
            "submit_blueprint",
            {"code": "fill(0,0,0,4,0,4,'stone')", "design_notes": "slab", "views": [{"yaw": 0}]},
            call_id="s1",
        ),
        lambda: _tool_msg(
            "edit_region",
            {
                "region": [1, 0, 1, 3, 0, 3],
                "code": "fill(1,0,1,3,0,3,'glass')",
                "design_notes": "glass centre",
                "views": [{"yaw": 0}],
            },
            call_id="e1",
        ),
        lambda: _tool_msg(
            "str_replace",
            {
                "old_str": "fill(1,0,1,3,0,3,'glass')",
                "new_str": "fill(1,0,1,3,0,3,'glass')\nfill(0,1,0,0,1,0,'oak_planks')",
                "design_notes": "one extra block",
                "submit": True,
                "views": [{"yaw": 0}],
            },
            call_id="r1",
        ),
    ]
    llm = _ScriptedLLM(
        steps
        + [_scripted(FakeLLM, "_verify_query"), _scripted(FakeLLM, "_verify_inspect"), _scripted(FakeLLM, "_finish")]
    )
    events = []
    config = Config(max_iters=6, seed=1)
    rundir = RunDir.create("slab", base=str(tmp_path))

    result = run_agent("slab", llm, config, rundir, on_event=lambda t, d: events.append((t, d)))

    assert result.finished is True
    assert len(isolation_spy) == 3  # one isolated execution per LLM-facing build path
    event_types = {t for t, _ in events}
    assert {"submit_blueprint", "edit_region", "str_replace"} <= event_types
    grid = result.grid
    assert grid.get(2, 0, 2) is not None  # centre built by edit_region, preserved across later steps


def _scripted(cls, name):
    """Bind a FakeLLM step method so it can be placed in a plain script list."""
    return getattr(cls(), name)


def test_isolation_failure_is_a_recoverable_blueprint_failure_not_a_crash(tmp_path, monkeypatch):
    """A killed/timed-out child must not abort the agent run: the model sees the error as a failed
    tool call, the edit budget is untouched, and the next submission can still succeed."""
    real_isolated = sandbox.run_blueprint_isolated
    attempts = {"n": 0}

    def flaky(source, grid, **kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise IsolatedExecutionError("Blueprint execution did not finish within 15.0s (isolated process killed).")
        return real_isolated(source, grid, **kwargs)

    monkeypatch.setattr(sandbox, "run_blueprint_isolated", flaky)
    monkeypatch.setattr(sandbox, "run_blueprint", lambda *a, **k: (_ for _ in ()).throw(AssertionError("in-process")))

    llm = _ScriptedLLM(
        [
            lambda: _tool_msg(
                "submit_blueprint",
                {"code": "fill(0,0,0,1,1,1,'stone')", "design_notes": "a", "views": [{"yaw": 0}]},
                call_id="s1",
            ),
            lambda: _tool_msg(
                "submit_blueprint",
                {"code": "fill(0,0,0,1,1,1,'stone')", "design_notes": "b", "views": [{"yaw": 0}]},
                call_id="s2",
            ),
            _scripted(FakeLLM, "_verify_query"),
            _scripted(FakeLLM, "_verify_inspect"),
            _scripted(FakeLLM, "_finish"),
        ]
    )
    events = []
    config = Config(max_iters=6, seed=1)
    rundir = RunDir.create("hut", base=str(tmp_path))

    result = run_agent("hut", llm, config, rundir, on_event=lambda t, d: events.append((t, d)))

    assert result.finished is True
    assert attempts["n"] == 2
    assert any(t == "blueprint_error" and "isolated process killed" in d["error"] for t, d in events)
    assert result.grid is not None and len(result.grid) == 8
