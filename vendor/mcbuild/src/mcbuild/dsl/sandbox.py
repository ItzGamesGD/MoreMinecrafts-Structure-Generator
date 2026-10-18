"""AST-denylist sandbox + op-budget executor for blueprint code.

SECURITY NOTE (2026-10-18 audit): blueprint text is LLM output produced from a user prompt,
so it is treated as untrusted. Two layers apply:

1. `run_blueprint` (in-process): the AST denylist, import stripping, and the line/time budget.
   The denylist is defense in depth, not a security boundary. It can only enumerate escape
   shapes already known, and Python's reflection surface keeps producing new ones (the audit
   added `str.format()` dunder chains and frame/generator/code-introspection attributes).
   In-process execution is for trusted input only: the repository's own blueprints and tests.

2. `run_blueprint_isolated` (out-of-process): every LLM-authored blueprint in the agent loop
   runs here. The child is a fresh `python -I` process with an empty environment, a scratch
   working directory, CPU and address-space rlimits, a parent-side deadline, JSON-only
   exchange (no pickle), and a validated result. A sandbox escape therefore reaches a
   disposable process without the parent's secrets or memory. This is not a complete
   boundary: the child still runs as the same OS user with filesystem and network access, and
   there is no seccomp, namespace, or container layer. See docs/SECURITY.md for the full
   assessment and the open follow-ups.

Import statements are stripped rather than rejected (everything a blueprint needs is already
injected as globals; see dsl/REFERENCE.md), dunder/attribute escapes and a handful of dangerous
builtins are blocked outright, and execution runs under a line-count + wall-clock budget via
sys.settrace.
"""

from __future__ import annotations

import ast
import builtins as _builtins
import importlib.util
import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time

from mcbuild import palette
from mcbuild import voxel as _voxel
from mcbuild.dsl import errors, stdlib
from mcbuild.palette import PaletteError

BLUEPRINT_FILENAME = "<blueprint>"

MAX_LINES = 2_000_000
MAX_SECONDS = 10.0

BANNED_NAMES = {
    "eval",
    "exec",
    "open",
    "__import__",
    "getattr",
    "setattr",
    "delattr",
    "globals",
    "locals",
    "vars",
    "type",
    "compile",
    "input",
    "breakpoint",
    "__builtins__",
    "memoryview",
    "staticmethod",
    "classmethod",
    "super",
    "exit",
    "quit",
    "help",
    "__build_class__",
}

# Attribute names that don't start with "_" (so the dunder check below misses them) but
# still expose frame/generator/code-object internals an attacker can walk to reach the
# real __builtins__, other frames' locals (including the host process's), or arbitrary
# live objects via __subclasses__()-style traversal. None of mcbuild's DSL primitives or
# the allowed stdlib names use these, so blocking them has no legitimate-blueprint cost.
BANNED_ATTRS = {
    # generator / coroutine / async-generator frame and code objects
    "gi_frame",
    "gi_code",
    "gi_yieldfrom",
    "cr_frame",
    "cr_code",
    "cr_await",
    "ag_frame",
    "ag_code",
    "ag_await",
    # frame objects
    "f_back",
    "f_globals",
    "f_locals",
    "f_builtins",
    "f_code",
    "f_trace",
    # traceback / code objects
    "tb_frame",
    "tb_next",
    "co_consts",
    "co_code",
    "co_names",
    "co_varnames",
    "co_freevars",
    "co_cellvars",
    "cell_contents",
    # str.format()/format_map() interpret their template at runtime, so a dunder chain
    # inside the template string (e.g. "{0.__class__.__bases__}".format(x)) never appears
    # as an ast.Attribute node and bypasses the leading-underscore check entirely.
    "format",
    "format_map",
}

_SAFE_BUILTIN_NAMES = (
    "range",
    "len",
    "enumerate",
    "zip",
    "min",
    "max",
    "abs",
    "round",
    "int",
    "float",
    "str",
    "list",
    "dict",
    "set",
    "tuple",
    "sorted",
    "sum",
    "any",
    "all",
    "bool",
    "print",
)

SAFE_BUILTINS: dict[str, object] = {
    name: getattr(_builtins, name) for name in _SAFE_BUILTIN_NAMES if hasattr(_builtins, name)
}


class SandboxViolation(Exception):
    """Raised when a blueprint's AST contains disallowed constructs."""

    def __init__(self, message: str, lineno: int | None = None):
        self.lineno = lineno
        super().__init__(message)


class BudgetExceeded(Exception):
    """Raised when a blueprint exceeds its executed-line or wall-clock budget."""


def validate_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in BANNED_ATTRS):
            raise SandboxViolation(f"Access to attribute '{node.attr}' is not allowed.", node.lineno)
        if isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            raise SandboxViolation(f"Use of '{node.id}' is not allowed.", node.lineno)


class _ImportStripper(ast.NodeTransformer):
    """Removes import statements wholesale instead of rejecting the whole blueprint.

    Everything a blueprint needs is already injected as globals (see dsl/REFERENCE.md),
    so a stray `import` is harmless to drop; if the blueprint actually relied on the
    imported name, it fails naturally with a NameError at the point of use instead.
    """

    def visit_Import(self, node: ast.Import) -> None:
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        return None

    def generic_visit(self, node: ast.AST) -> ast.AST:
        node = super().generic_visit(node)
        body = getattr(node, "body", None)
        if isinstance(body, list) and not body:
            # A block can't be empty; fix_missing_locations (called by the caller) fills lineno.
            setattr(node, "body", [ast.Pass()])  # noqa: B010
        return node


def compile_blueprint(source: str, filename: str = BLUEPRINT_FILENAME) -> ast.Module:
    tree = ast.parse(source, filename=filename)
    tree = _ImportStripper().visit(tree)
    ast.fix_missing_locations(tree)
    validate_ast(tree)
    return tree


def run_blueprint(
    source: str,
    grid: _voxel.VoxelGrid,
    seed: int = 0,
    max_lines: int = MAX_LINES,
    max_seconds: float = MAX_SECONDS,
) -> None:
    """Validate, compile, and execute a blueprint against the given VoxelGrid.

    Raises BlueprintError (with line + excerpt) on any failure: syntax error,
    sandbox violation, budget overrun, or a runtime exception from user code.
    """
    filename = BLUEPRINT_FILENAME
    try:
        tree = compile_blueprint(source, filename)
    except SyntaxError as e:
        raise errors.from_syntax_error(e, source) from e
    except SandboxViolation as e:
        raise errors.from_sandbox_violation(e, source) from e

    code = compile(tree, filename, "exec")
    stdlib_ns = stdlib.make_stdlib(grid, seed=seed)
    global_ns: dict[str, object] = {"__builtins__": SAFE_BUILTINS, **stdlib_ns}

    counter = {"n": 0}
    start = time.monotonic()

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != filename:
            return None
        if event == "line":
            counter["n"] += 1
            if counter["n"] > max_lines:
                raise BudgetExceeded(f"Blueprint exceeded {max_lines:,} executed lines (possible infinite loop).")
            if counter["n"] % 2000 == 0 and time.monotonic() - start > max_seconds:
                raise BudgetExceeded(f"Blueprint exceeded {max_seconds}s execution budget.")
        return tracer

    old_trace = sys.gettrace()
    sys.settrace(tracer)
    palette.reset_warnings()
    try:
        exec(code, global_ns)
    except BudgetExceeded as e:
        raise errors.BlueprintError(str(e), source=source) from e
    except (_voxel.VoxelLimitError, PaletteError) as e:
        raise errors.from_exception(e, source, filename) from e
    except Exception as e:
        raise errors.from_exception(e, source, filename) from e
    finally:
        sys.settrace(old_trace)
    grid.palette_warnings = palette.pop_warnings()


# --- Process-isolated execution (for untrusted/LLM-authored blueprints) ---------------
#
# The child is a fresh `python -I -m mcbuild.dsl.isolated_child` process. Requests and results
# are JSON only (never pickle), and blocks cross the boundary as coordinates plus block-state
# strings, not palette indices: indices are process-local, and a blueprint can create dynamic
# indices (e.g. "oak_stairs[facing=north]") that the parent has never seen.

ISOLATION_MAX_SECONDS = 15.0  # parent-side wall-clock backstop, above the in-sandbox MAX_SECONDS
ISOLATION_CPU_SECONDS = 20  # hard CPU-time rlimit inside the child (SIGXCPU if exceeded)
ISOLATION_MEMORY_BYTES = 1_024 * 1_024 * 1_024  # 1 GiB address-space rlimit inside the child
MAX_ISOLATED_RESULT_BYTES = 256 * 1024 * 1024  # cap on what the parent will read back from a child
_STATE_NAME = re.compile(r"[a-z0-9_]+(\[[a-z0-9_=,]+\])?")
_MAX_STATE_NAME_CHARS = 256


class IsolatedExecutionError(errors.BlueprintError):
    """The isolated child timed out, crashed, was killed, returned a malformed result, or could
    not enforce its limits. Subclasses BlueprintError so the agent loop treats it as a
    recoverable failure instead of aborting the run."""

    def __init__(self, message: str):
        super().__init__(message)


def isolation_supported() -> bool:
    """True when this platform can apply the child's resource limits (POSIX `resource` module).

    Isolation without limits is not offered: where `resource` is missing (e.g. Windows),
    run_blueprint_isolated refuses to run rather than executing unconstrained (fail closed).
    """
    return importlib.util.find_spec("resource") is not None


def _apply_child_limits() -> None:
    """Apply CPU and address-space caps in the child. Failures raise; they are never ignored."""
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (ISOLATION_CPU_SECONDS, ISOLATION_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_AS, (ISOLATION_MEMORY_BYTES, ISOLATION_MEMORY_BYTES))


def _state_string(block: palette.Block) -> str:
    if not block.state:
        return block.name
    return f"{block.name}[" + ",".join(f"{k}={v}" for k, v in block.state) + "]"


def encode_grid(grid: _voxel.VoxelGrid) -> dict:
    """Serialize a grid to JSON-safe values: block coordinates plus block-state strings."""
    blocks = [[x, y, z, _state_string(palette.get_block_by_index(index))] for (x, y, z), index in grid.items()]
    return {"blocks": blocks, "warnings": list(getattr(grid, "palette_warnings", None) or [])}


def decode_grid(payload: object) -> _voxel.VoxelGrid:
    """Rebuild a grid from encode_grid output, validating every field.

    The result comes from a child that may be compromised, so nothing is trusted: types are
    checked (bool is rejected as an int), names must match the block-state grammar and length
    limit, and placement goes through VoxelGrid.set so the block-count and extent limits apply.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("blocks"), list):
        raise IsolatedExecutionError("isolated result has an unexpected shape.")
    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list) or not all(isinstance(w, str) for w in warnings):
        raise IsolatedExecutionError("isolated result has invalid warnings.")

    grid = _voxel.VoxelGrid()
    try:
        for entry in payload["blocks"]:
            if not isinstance(entry, list) or len(entry) != 4:
                raise IsolatedExecutionError("isolated result has a malformed block entry.")
            x, y, z, name = entry
            if any(type(c) is not int for c in (x, y, z)) or not isinstance(name, str):
                raise IsolatedExecutionError("isolated result has a block entry with invalid types.")
            if len(name) > _MAX_STATE_NAME_CHARS or _STATE_NAME.fullmatch(name) is None:
                raise IsolatedExecutionError("isolated result has a block name outside the allowed grammar.")
            try:
                index = palette.get_block(name).index
            except (PaletteError, ValueError, KeyError) as e:
                raise IsolatedExecutionError(f"isolated result names an unknown block: {e}") from e
            grid.set(x, y, z, index)
    except _voxel.VoxelLimitError as e:
        raise IsolatedExecutionError(f"isolated result exceeds grid limits: {e}") from e
    finally:
        # get_block may append alias/correction warnings in this process; discard them here.
        palette.pop_warnings()
    grid.palette_warnings = list(warnings)
    return grid


def _send_all(fd: int, data: bytes, deadline: float) -> None:
    view = memoryview(data)
    while view:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
            raise TimeoutError
        view = view[os.write(fd, view[:65536]) :]


def _recv_all(fd: int, deadline: float) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise TimeoutError
        chunk = os.read(fd, 65536)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAX_ISOLATED_RESULT_BYTES:
            raise IsolatedExecutionError("isolated result exceeds the size limit.")
        chunks.append(chunk)


def run_blueprint_isolated(
    source: str,
    grid: _voxel.VoxelGrid,
    seed: int = 0,
    max_lines: int = MAX_LINES,
    max_seconds: float = MAX_SECONDS,
    timeout: float = ISOLATION_MAX_SECONDS,
) -> _voxel.VoxelGrid:
    """Run a blueprint against a copy of `grid` inside a resource-limited child process.

    Returns a new VoxelGrid with the result; `grid` is not modified. Starting from `grid` keeps
    edit semantics: get_block() and edits see the existing build.

    Raises:
        BlueprintError: the blueprint itself failed (syntax, sandbox violation, runtime error,
            or its own line/time budget). Same message and line information as run_blueprint.
        IsolatedExecutionError: the child exceeded `timeout`, was killed (its CPU or memory
            limit, the OOM killer, a crash), returned a malformed result, could not apply its
            limits, or isolation is unsupported on this platform.

    The child is always reaped before this function returns or raises.
    """
    if not isolation_supported():
        raise IsolatedExecutionError(
            "Blueprint isolation is unavailable on this platform (no POSIX resource limits); "
            "refusing to run the blueprint unconstrained."
        )

    request = json.dumps(
        {
            "source": source,
            "seed": seed,
            "max_lines": max_lines,
            "max_seconds": max_seconds,
            "grid": encode_grid(grid),
        }
    ).encode("utf-8")

    # The child gets an empty environment (so it cannot read API keys such as OPENROUTER_API_KEY
    # from os.environ) and a fresh empty working directory (so it cannot read the repository by
    # relative path). Both are removed afterwards.
    scratch = tempfile.mkdtemp(prefix="mcbuild-isolated-")
    result_read, result_write = os.pipe()
    try:
        # -I: ignore PYTHON* env vars and drop the cwd from sys.path. start_new_session keeps the
        # child out of our process group, so a terminal Ctrl-C does not race the cleanup below.
        child = subprocess.Popen(
            [sys.executable, "-I", "-m", "mcbuild.dsl.isolated_child", str(result_write)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=(result_write,),
            start_new_session=True,
            env={},
            cwd=scratch,
        )
    except OSError as e:
        os.close(result_read)
        os.close(result_write)
        shutil.rmtree(scratch, ignore_errors=True)
        raise IsolatedExecutionError(f"could not start the isolated process: {e}") from e
    os.close(result_write)  # keep only the child's copy, so EOF means the child has exited

    deadline = time.monotonic() + timeout
    try:
        try:
            _send_all(child.stdin.fileno(), request, deadline)
        except (BrokenPipeError, TimeoutError):
            pass  # the child died or stalled before reading; reported below as no result
        finally:
            child.stdin.close()
        raw = _recv_all(result_read, deadline)
    except TimeoutError as e:
        child.kill()  # a child that blew its deadline is hung or spinning; do not grant it a grace period
        raise IsolatedExecutionError(
            f"Blueprint execution did not finish within {timeout}s (isolated process killed)."
        ) from e
    finally:
        os.close(result_read)
        _reap(child)
        shutil.rmtree(scratch, ignore_errors=True)

    if not raw:
        raise IsolatedExecutionError(
            f"Isolated blueprint process ended without a result (exit code {child.returncode}); "
            "likely its CPU or memory limit, the OS OOM killer, or a crash."
        )
    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise IsolatedExecutionError("isolated result is not valid JSON.") from e
    if not isinstance(envelope, dict):
        raise IsolatedExecutionError("isolated result has an unexpected shape.")

    status = envelope.get("status")
    if status == "ok":
        return decode_grid(envelope.get("grid"))
    message = envelope.get("message")
    if not isinstance(message, str):
        raise IsolatedExecutionError("isolated result has no message.")
    if status == "error":
        line = envelope.get("line")
        raise errors.BlueprintError(message, line=line if type(line) is int else None, source=source)
    if status == "isolation_failed":
        raise IsolatedExecutionError(message)
    raise IsolatedExecutionError("isolated result has an unknown status.")


def _reap(child: subprocess.Popen) -> None:
    """Make sure the child is gone: wait briefly for its own exit, then terminate, then kill."""
    try:
        child.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        child.terminate()
        try:
            child.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
