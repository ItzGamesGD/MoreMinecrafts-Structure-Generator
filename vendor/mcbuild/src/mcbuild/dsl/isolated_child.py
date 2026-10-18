"""Child-process entry point for run_blueprint_isolated. Not a public API.

Invoked as `python -I -m mcbuild.dsl.isolated_child <result_fd>`:

* stdin carries one JSON request: {"source", "seed", "max_lines", "max_seconds", "grid"}.
* the result is one JSON object written to file descriptor <result_fd>.

Both directions are JSON. Nothing is pickled, so the parent never deserializes bytes the
(possibly compromised) child chose to send beyond plain JSON values it validates itself.
`-I` ignores PYTHON* environment variables and drops the current directory from sys.path,
so a planted module in the working directory cannot shadow a stdlib import in the child.
"""

from __future__ import annotations

import json
import os
import sys

from mcbuild.dsl import os_confinement, sandbox
from mcbuild.dsl.errors import BlueprintError


def _respond(result_fd: int, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    view = memoryview(data)
    while view:
        written = os.write(result_fd, view)
        view = view[written:]


def main(argv: list[str]) -> int:
    result_fd = int(argv[1])
    try:
        sandbox._apply_child_limits()
    except OSError as e:
        _respond(result_fd, {"status": "isolation_failed", "message": f"could not apply resource limits: {e}"})
        return 0

    request = json.load(sys.stdin)
    try:
        grid = sandbox.decode_grid(request["grid"])
        # Eagerly construct trusted DSL helpers before file-open syscalls are blocked.
        sandbox.stdlib.make_stdlib(grid, seed=request["seed"])
        try:
            os_confinement.install()
        except OSError as e:
            _respond(result_fd, {"status": "isolation_failed", "message": f"OS syscall confinement unavailable: {e}"})
            return 0
        sandbox.run_blueprint(
            request["source"],
            grid,
            seed=request["seed"],
            max_lines=request["max_lines"],
            max_seconds=request["max_seconds"],
        )
    except BlueprintError as e:
        message = e.raw_message
        if isinstance(e.__cause__, MemoryError):
            message = "MemoryError: blueprint exceeded the isolated process memory limit"
        _respond(result_fd, {"status": "error", "message": message, "line": e.line})
    except MemoryError:
        _respond(
            result_fd,
            {"status": "error", "message": "MemoryError: blueprint exceeded the isolated process memory limit"},
        )
    except BaseException as e:  # noqa: BLE001 - every outcome must be reported, never lost
        _respond(result_fd, {"status": "error", "message": f"{type(e).__name__}: {e}"})
    else:
        _respond(result_fd, {"status": "ok", "grid": sandbox.encode_grid(grid)})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
