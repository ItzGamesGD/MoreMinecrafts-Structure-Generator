"""Regression: the final protocol message must reach the client before run_build_session returns.

Before the fix, enqueue() scheduled its put with call_soon_threadsafe and join() could return
before that put ran, so the closing message (finish/error) was silently dropped.
"""

from __future__ import annotations

import asyncio
import json

from mcbuild.config import Config
from mcbuild.llm.fake import FakeLLM
from mcbuild.server import session


def _collect(prompt: str, config: Config) -> list[dict]:
    sent: list[dict] = []

    async def send(message: str) -> None:
        sent.append(json.loads(message))

    asyncio.run(session.run_build_session(prompt, send, config=config))
    return sent


def test_missing_api_key_error_is_delivered(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def no_key():
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    monkeypatch.setattr(session, "OpenRouterClient", no_key)

    sent = _collect("hut", Config(max_iters=1))

    assert [m["type"] for m in sent] == ["hello", "error"]
    assert "OPENROUTER_API_KEY" in sent[-1]["reason"]


def test_finish_message_is_delivered_after_a_successful_build(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(session, "OpenRouterClient", FakeLLM)

    sent = _collect("a tiny stone hut", Config(max_iters=6, seed=1))

    assert sent[-1]["type"] in ("finish", "error")
    assert sent[-1]["type"] == "finish", sent[-1]
