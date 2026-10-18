"""AST-denylist sandbox + op-budget executor for blueprint code.

SECURITY NOTE (2026-10-18 audit): this module's docstring previously described
its threat model as "LLM accidents... not a malicious adversary." That is no
longer the operating assumption. `run_blueprint` executes text that ultimately
originates from an LLM response to a user-supplied prompt (see
`agent/loop.py`, reachable from the WebSocket server); a sufficiently
adversarial prompt or a compromised/confused model can produce blueprint text
designed to escape the sandbox. The denylist below (banned names, banned
attribute names, import stripping) is defense in depth, not a security
boundary: an AST denylist can only ever enumerate *known* escape shapes, and
Python's reflection surface is large enough that new ones keep turning up
(this audit added a `str.format()`/`format_map()` dunder-chain block and a
frame/generator/code-introspection attribute block; both were previously
unfiltered — see tests/test_dsl_sandbox.py's "audit" tests for the PoCs that
motivated them). Treat `run_blueprint` as suitable only for trusted or
low-stakes input. For untrusted/LLM-authored blueprints, prefer
`run_blueprint_isolated`, which runs the same validate+exec in a separate
process with CPU/memory rlimits, so a successful sandbox escape reaches a
disposable child process's address space rather than the host process
(API keys, other sessions' state, the filesystem) directly. Process isolation
is still not a hard boundary on its own (no seccomp/namespace/container layer
here) — see docs/SECURITY.md for the full assessment and open follow-ups.

Import statements are stripped rather than rejected (everything a blueprint
needs is already injected as globals; see dsl/REFERENCE.md), dunder/attribute
escapes and a handful of dangerous builtins are blocked outright, and
execution runs under a line-count + wall-clock budget via sys.settrace.
"""

from __future__ import annotations

import ast
import builtins as _builtins
import multiprocessing
import sys
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

ISOLATION_MAX_SECONDS = 15.0  # wall-clock backstop; a bit above the default in-sandbox budget
ISOLATION_CPU_SECONDS = 20  # hard CPU-time rlimit applied inside the child
ISOLATION_MEMORY_BYTES = 1_024 * 1_024 * 1_024  # 1 GiB address-space rlimit applied inside the child


class IsolatedExecutionError(Exception):
    """Raised by run_blueprint_isolated when the child process fails, times out, or is killed."""


def _isolated_worker(source: str, seed: int, max_lines: int, max_seconds: float, conn) -> None:
    """Child-process entry point: apply resource limits, run the blueprint, send back the result.

    Runs in a freshly spawned interpreter (multiprocessing "spawn" context, not "fork"), so it
    does not inherit the parent's open file descriptors, imported modules' live state, or memory
    contents -- a sandbox escape here reaches a disposable process, not the parent's.
    """
    try:
        import contextlib
        import resource

        # Best-effort hard caps; a successful escape past the AST/budget checks still can't
        # consume unbounded CPU or memory, and can't outlive this process's exit.
        resource.setrlimit(resource.RLIMIT_CPU, (ISOLATION_CPU_SECONDS, ISOLATION_CPU_SECONDS))
        with contextlib.suppress(ValueError, OSError):
            # RLIMIT_AS is unreliable under some allocators/platforms; CPU + join-timeout remain.
            resource.setrlimit(resource.RLIMIT_AS, (ISOLATION_MEMORY_BYTES, ISOLATION_MEMORY_BYTES))
    except ImportError:
        pass  # resource is POSIX-only; on platforms without it, the parent's join timeout is the backstop.

    grid = _voxel.VoxelGrid()
    try:
        run_blueprint(source, grid, seed=seed, max_lines=max_lines, max_seconds=max_seconds)
    except errors.BlueprintError as e:
        conn.send(("error", e.raw_message, e.line))
        return
    except BaseException as e:  # noqa: BLE001 - must not let an unexpected escape crash silently
        conn.send(("error", f"{type(e).__name__}: {e}", None))
        return
    conn.send(("ok", grid, None))


def run_blueprint_isolated(
    source: str,
    seed: int = 0,
    max_lines: int = MAX_LINES,
    max_seconds: float = MAX_SECONDS,
    timeout: float = ISOLATION_MAX_SECONDS,
) -> _voxel.VoxelGrid:
    """Like run_blueprint, but executes in a separate, resource-limited child process.

    Recommended entry point for untrusted/LLM-authored blueprint text (see the module
    docstring). Returns a populated VoxelGrid on success; raises BlueprintError for a
    blueprint-level failure (syntax/sandbox/runtime/budget) with the same semantics as
    run_blueprint, or IsolatedExecutionError if the child times out or is killed outright
    (e.g. by its own CPU/memory rlimit, OOM-killer, or a segfault) without reporting back.
    """
    ctx = multiprocessing.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(
        target=_isolated_worker,
        args=(source, seed, max_lines, max_seconds, child_conn),
        daemon=True,
    )
    process.start()
    child_conn.close()
    try:
        if parent_conn.poll(timeout):
            status, payload, line = parent_conn.recv()
        else:
            status, payload, line = "timeout", None, None
    except EOFError:
        status, payload, line = "crashed", None, None
    finally:
        if process.is_alive():
            process.terminate()
            process.join(2.0)
            if process.is_alive():
                process.kill()
                process.join()
        parent_conn.close()

    if status == "ok":
        return payload
    if status == "error":
        raise errors.BlueprintError(payload, line=line, source=source)
    if status == "timeout":
        raise IsolatedExecutionError(f"Blueprint execution did not complete within {timeout}s (isolated process).")
    raise IsolatedExecutionError(
        f"Isolated blueprint process exited without a result (exit code {process.exitcode}); "
        "likely killed by its own resource limit, the OS OOM-killer, or a crash."
    )
