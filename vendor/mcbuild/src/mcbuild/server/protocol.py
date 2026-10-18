"""JSON message shapes sent to a connected mod client over the WebSocket.

This is the wire contract with the Forge mod's Gson POJOs (`net/ProtocolMessages.java`) —
keep the two in sync when changing shapes here.

    {"type": "hello", "run_dir": str}
    {"type": "chat", "text": str}
    {"type": "blocks", "iteration": int, "changes": [{"x": int, "y": int, "z": int, "block": str|None}]}
    {"type": "finish", "summary": str}
    {"type": "error", "reason": str}

Inbound (client -> server), since the 2026-10-18 security audit:

    {"cmd": "build", "prompt": str, "token": str}

`token` must match the server's configured `Config.auth_token` (see server/ws_server.py);
a connection that omits it or sends the wrong value is rejected with an `error` message
and closed before any build starts. This exists because `serve()`'s Origin check (also
added in that audit) only stops *browser* clients; it does nothing against another local
process, user, or container on the same host opening a raw TCP/WebSocket connection to
127.0.0.1, which previously got a build (and whatever LLM spend it incurs) for free.
"""

from __future__ import annotations

import json


def hello(run_dir: str) -> str:
    return json.dumps({"type": "hello", "run_dir": run_dir})


def chat(text: str) -> str:
    return json.dumps({"type": "chat", "text": text})


def blocks(iteration: int, changes: list[dict]) -> str:
    return json.dumps({"type": "blocks", "iteration": iteration, "changes": changes})


def finish(summary: str) -> str:
    return json.dumps({"type": "finish", "summary": summary})


def error(reason: str) -> str:
    return json.dumps({"type": "error", "reason": reason})
