"""Runtime configuration for an mcbuild agent run."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    model: str = "anthropic/claude-sonnet-5"
    ref_model: str = "openai/gpt-image-2"
    ref_model_fallback: str = "google/gemini-2.5-flash-image"
    max_iters: int = 6
    seed: int = 0
    display: str = "auto"  # auto|sixel|ansi|off
    out_dir: str = "runs"
    reference: bool = False
    reasoning: str = "medium"  # off|low|medium|high
    cost_ceiling: float | None = None
    max_consecutive_failures: int = 10
    stream: bool = True
    # Shared secret the WebSocket server requires on the first message of every
    # connection (see server/ws_server.py). None only when the server itself hasn't
    # been given one, which main() treats as "generate a random one for this run" --
    # it is never silently optional.
    auth_token: str | None = None
