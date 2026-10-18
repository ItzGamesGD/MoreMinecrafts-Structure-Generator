"""Regression tests for the 2026-10-18 security audit's WebSocket server fixes.

No real network socket is opened: `_handler` is exercised directly against a minimal fake
connection, so these stay fast and don't depend on a free port.
"""

from __future__ import annotations

import asyncio
import json

from mcbuild.config import Config
from mcbuild.server.ws_server import _handler, _token_matches


class _FakeConnection:
    """Just enough of websockets' ServerConnection for _handler: one inbound message,
    and a list capturing everything sent back."""

    def __init__(self, inbound: dict):
        self._inbound = json.dumps(inbound)
        self.sent: list[dict] = []

    async def recv(self) -> str:
        return self._inbound

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))


def _run(coro):
    return asyncio.run(coro)


def test_token_matches_rejects_wrong_token():
    config = Config(auth_token="correct-horse-battery-staple")
    assert _token_matches(config, "correct-horse-battery-staple") is True
    assert _token_matches(config, "wrong") is False
    assert _token_matches(config, None) is False
    assert _token_matches(config, 12345) is False  # non-string candidate must not crash


def test_token_matches_rejects_everything_when_server_has_no_token_configured():
    config = Config(auth_token=None)
    assert _token_matches(config, None) is False
    assert _token_matches(config, "") is False
    assert _token_matches(config, "anything") is False


def test_handler_rejects_missing_token_without_starting_a_build():
    config = Config(auth_token="s3cr3t")
    conn = _FakeConnection({"cmd": "build", "prompt": "a castle"})

    _run(_handler(conn, config))

    assert len(conn.sent) == 1
    assert conn.sent[0]["type"] == "error"
    assert "token" in conn.sent[0]["reason"].lower()


def test_handler_rejects_wrong_token_without_starting_a_build():
    config = Config(auth_token="s3cr3t")
    conn = _FakeConnection({"cmd": "build", "prompt": "a castle", "token": "nope"})

    _run(_handler(conn, config))

    assert len(conn.sent) == 1
    assert conn.sent[0]["type"] == "error"


def test_handler_rejects_malformed_json_before_checking_token():
    config = Config(auth_token="s3cr3t")

    class _RawConnection(_FakeConnection):
        async def recv(self) -> str:
            return "not json"

    conn = _RawConnection({})
    _run(_handler(conn, config))

    assert len(conn.sent) == 1
    assert conn.sent[0]["type"] == "error"
    assert "json" in conn.sent[0]["reason"].lower()


def test_handler_with_correct_token_gets_past_auth(monkeypatch):
    """Doesn't exercise a real build (that needs an LLM client); just confirms a
    correctly authenticated request reaches run_build_session instead of being rejected."""
    import mcbuild.server.ws_server as ws_server_module

    called_with = {}

    async def fake_run_build_session(prompt, send, config=None):
        called_with["prompt"] = prompt
        called_with["config"] = config

    monkeypatch.setattr(ws_server_module, "run_build_session", fake_run_build_session)

    config = Config(auth_token="s3cr3t")
    conn = _FakeConnection({"cmd": "build", "prompt": "a castle", "token": "s3cr3t"})

    _run(_handler(conn, config))

    assert called_with.get("prompt") == "a castle"
    assert conn.sent == []  # no error was sent; auth passed through to the real session


def test_handler_rejects_second_build_while_one_in_progress(monkeypatch):
    import mcbuild.server.ws_server as ws_server_module

    async def hanging_run_build_session(prompt, send, config=None):
        await asyncio.sleep(3600)

    monkeypatch.setattr(ws_server_module, "run_build_session", hanging_run_build_session)
    monkeypatch.setattr(ws_server_module, "_build_in_progress", True)

    config = Config(auth_token="s3cr3t")
    conn = _FakeConnection({"cmd": "build", "prompt": "a castle", "token": "s3cr3t"})

    _run(_handler(conn, config))

    assert len(conn.sent) == 1
    assert "already in progress" in conn.sent[0]["reason"]
