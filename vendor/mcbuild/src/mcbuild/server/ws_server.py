"""WebSocket server entry point: accepts a mod client, runs one build per connection.

SECURITY NOTE (2026-10-18 audit): this server binds to 127.0.0.1 by default, which stops
other machines on the network, but not every local threat. Two were unaddressed before
this audit and are both fixed below:

1. Any other local process/user/container could open a raw connection to 127.0.0.1:8765
   and get a build for free (no auth at all) -- a resource-exhaustion / LLM-spend-abuse
   vector (`Config.cost_ceiling` limits one build's spend, not how many builds a
   non-owner can trigger). Fixed with a shared-secret `token` the client must send on its
   first message (see protocol.py); compared with `hmac.compare_digest` to avoid a timing
   oracle.
2. A page open in the operator's browser can have its JavaScript open a plain
   `ws://127.0.0.1:8765` connection -- browsers do not apply same-origin restrictions to
   WebSocket connections, so this works from *any* site the operator has open, not just a
   malicious one (e.g. via a compromised ad, XSS on an unrelated site, or a supply-chain
   issue in a browser extension). That request carries a real `Origin` header the browser
   sets and cannot be overridden by page JS; a non-browser client like the Forge mod's
   `java_websocket`-based `WsClient` does not send one at all. `serve(..., origins=[None])`
   below accepts only connections with no Origin header, so it rejects every
   browser-originated connection outright, regardless of which page it came from. The auth
   token is still required on top of this -- Origin filtering is a header the client
   controls on some code paths (e.g. non-browser HTTP libraries can set an arbitrary
   Origin), so it narrows the field, it does not replace authentication.

Neither of these is a reason to bind to a non-loopback host; that remains the operator's
explicit choice via --host and is unrelated to this fix. The token is required at startup
(no generated or default value) and is never printed, so it cannot leak through the server log.
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import hmac
import json
import os

from dotenv import load_dotenv
from websockets.asyncio.server import ServerConnection, serve

from mcbuild.config import Config
from mcbuild.server import protocol
from mcbuild.server.session import run_build_session

MIN_TOKEN_CHARS = 16

# Only one build runs at a time in this version; a second connection while a build is in
# flight is rejected outright rather than queued.
_build_in_progress = False


def _token_matches(config: Config, candidate: object) -> bool:
    if not isinstance(candidate, str) or config.auth_token is None:
        return False
    # Constant-time comparison: a naive `==` leaks the token one byte at a time to an
    # attacker measuring response latency across many attempts.
    return hmac.compare_digest(candidate, config.auth_token)


async def _handler(connection: ServerConnection, config: Config) -> None:
    global _build_in_progress

    raw = await connection.recv()
    try:
        request = json.loads(raw)
    except json.JSONDecodeError:
        await connection.send(protocol.error("Malformed request: expected JSON."))
        return

    if not _token_matches(config, request.get("token")):
        # Deliberately generic: don't confirm/deny whether a token was configured, or
        # distinguish "missing" from "wrong", beyond what's needed to self-diagnose.
        await connection.send(protocol.error("Unauthorized: missing or invalid 'token'."))
        return

    if request.get("cmd") != "build" or not request.get("prompt"):
        await connection.send(protocol.error('Expected {"cmd": "build", "prompt": "...", "token": "..."}.'))
        return

    if _build_in_progress:
        await connection.send(protocol.error("A build is already in progress; try again shortly."))
        return

    _build_in_progress = True
    try:
        await run_build_session(request["prompt"], connection.send, config=config)
    finally:
        _build_in_progress = False


async def _serve(host: str, port: int, config: Config) -> None:
    handler = functools.partial(_handler, config=config)
    # origins=[None]: accept only connections with no Origin header. Browsers always set
    # one on a WebSocket handshake (same-origin or not) and page JS cannot suppress or
    # forge it; a non-browser client (our Forge mod's java_websocket) sends none. This
    # rejects every browser-originated connection regardless of which site it came from.
    async with serve(handler, host, port, origins=[None]) as server:
        # The token is deliberately never printed or logged: it is a credential.
        print(f"mcbuild server listening on ws://{host}:{port} (model={config.model}, token required)")
        await server.serve_forever()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="mcbuild live-build WebSocket server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default=Config.model, help="Vision-capable OpenRouter model id.")
    parser.add_argument("--max-iters", type=int, default=Config.max_iters)
    parser.add_argument("--reasoning", default=Config.reasoning, help="off|low|medium|high")
    parser.add_argument(
        "--cost-ceiling",
        type=float,
        default=None,
        help="Abort a build (keeping its best build so far) once usage cost reaches this many USD.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Shared secret clients must send to connect. Prefer the MCBUILD_SERVER_TOKEN env var, "
        "which keeps the value out of shell history and process listings.",
    )
    args = parser.parse_args()

    token = args.token or os.environ.get("MCBUILD_SERVER_TOKEN")
    if not token or len(token) < MIN_TOKEN_CHARS:
        # Fail closed: there is no unauthenticated mode, and no generated token is printed.
        parser.error(
            f"a shared token of at least {MIN_TOKEN_CHARS} characters is required (--token or MCBUILD_SERVER_TOKEN)"
        )

    config = Config(
        model=args.model,
        max_iters=args.max_iters,
        reasoning=args.reasoning,
        cost_ceiling=args.cost_ceiling,
        auth_token=token,
    )
    asyncio.run(_serve(args.host, args.port, config))


if __name__ == "__main__":
    main()
