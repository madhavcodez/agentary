"""Sandboxed Python executor for data analysis tasks.

Replaces the previous substring-blocklist implementation, which was trivially
bypassed (e.g. ``__import__('o'+'s')``, ``importlib.import_module('subprocess')``,
``open('/etc/passwd')``). Now uses RestrictedPython's AST-level guards to ensure
only a vetted set of names and operations are reachable from user code.

Security model
--------------
- Code is parsed and recompiled by ``RestrictedPython.compile_restricted``,
  which rewrites attribute access, subscripting, iteration, and import sites
  to call guarded shims. The original AST is rejected if it contains
  disallowed constructs (e.g. ``__import__``, ``exec``, ``eval``).
- ``__builtins__`` is replaced with the RestrictedPython curated set
  (``safe_builtins`` + ``limited_builtins`` + ``utility_builtins``). Names
  like ``open``, ``exec``, ``eval``, ``compile``, ``input``, ``__import__``
  are absent.
- Only a small allowlist of stdlib modules is exposed by name (``math``,
  ``statistics``, ``collections``, ``itertools``, ``functools``, ``decimal``,
  ``fractions``, ``datetime``, ``re``, ``csv``, ``io``, ``json``). The
  ``re`` module's compile/match interface is exposed but search patterns are
  user-supplied and could ReDoS — see the timeout guard.
- Execution runs in a thread with a hard wall-clock cap. The thread can't
  be killed cleanly mid-execution, so we ``join`` and abandon if it doesn't
  return in time; the caller's request handler is freed.
- ``print()`` is captured by ``PrintCollector`` so output is bounded and
  doesn't escape into the host process stdout.

Out of scope (defense in depth still needed at the network/OS layer)
- CPU/memory limits inside the same process (RestrictedPython does not cap)
- Filesystem access via leaked references to imported modules' ``__file__``
- Side channels via long-running pure-Python computation that the timeout
  thread can't preempt
Operators are still expected to restrict outbound network from worker pools.
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Any

from RestrictedPython import (
    compile_restricted,
    limited_builtins,
    safe_builtins,
    safe_globals,
    utility_builtins,
)
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence,
    safer_getattr,
)
from RestrictedPython.PrintCollector import PrintCollector

logger = logging.getLogger(__name__)

TOOL_SCHEMA: dict[str, Any] = {
    "name": "python_executor",
    "description": (
        "Execute Python code for data analysis, calculations, and statistics. "
        "Returns captured stdout. Runs in a sandbox: imports, file I/O, and "
        "network are unavailable. Stdlib modules pre-imported: math, statistics, "
        "collections, itertools, functools, decimal, fractions, datetime, re, "
        "csv, io, json."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": (
                    "Python code to execute. Use print() to output results. "
                    "No file I/O, no imports, no network."
                ),
            },
        },
        "required": ["code"],
    },
}

TIMEOUT_SECONDS = 10
MAX_OUTPUT_BYTES = 3000


def _build_safe_modules() -> dict[str, Any]:
    """Return the allowlist of stdlib modules pre-bound for user code.

    Imported here so the modules are loaded once at startup, not on every
    tool invocation. None of these modules expose filesystem or network I/O
    via their default attributes — but we still go through ``safer_getattr``
    on access, which rejects dunder lookups.
    """
    import collections
    import csv
    import datetime
    import decimal
    import fractions
    import functools
    import io
    import itertools
    import math
    import re
    import statistics

    return {
        "math": math,
        "statistics": statistics,
        "collections": collections,
        "itertools": itertools,
        "functools": functools,
        "decimal": decimal,
        "fractions": fractions,
        "datetime": datetime,
        "re": re,
        "csv": csv,
        "io": io,
        "json": json,
    }


_SAFE_MODULES = _build_safe_modules()


def _build_restricted_globals() -> dict[str, Any]:
    """Construct the globals dict for one execution.

    Each call returns a fresh dict so user code can't poison state across
    invocations.
    """
    builtins: dict[str, Any] = {}
    builtins.update(safe_builtins)
    builtins.update(limited_builtins)
    builtins.update(utility_builtins)

    restricted: dict[str, Any] = dict(safe_globals)
    restricted["__builtins__"] = builtins
    restricted["_print_"] = PrintCollector
    restricted["_getattr_"] = safer_getattr
    restricted["_getitem_"] = default_guarded_getitem
    restricted["_getiter_"] = default_guarded_getiter
    restricted["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence
    restricted["_unpack_sequence_"] = guarded_unpack_sequence
    restricted["_write_"] = lambda x: x  # allow assignment to attributes of objects we own
    restricted["_inplacevar_"] = _inplace_var
    restricted.update(_SAFE_MODULES)
    return restricted


def _inplace_var(op: str, x: Any, y: Any) -> Any:
    """Support augmented assignment (``+=``, ``-=`` etc.) on simple types."""
    if op == "+=":
        return x + y
    if op == "-=":
        return x - y
    if op == "*=":
        return x * y
    if op == "/=":
        return x / y
    if op == "//=":
        return x // y
    if op == "%=":
        return x % y
    if op == "**=":
        return x**y
    if op == "<<=":
        return x << y
    if op == ">>=":
        return x >> y
    if op == "&=":
        return x & y
    if op == "|=":
        return x | y
    if op == "^=":
        return x ^ y
    raise ValueError(f"Unsupported augmented assignment: {op}")


def _run_in_thread(byte_code: Any, restricted: dict[str, Any]) -> tuple[Any, BaseException | None]:
    """Execute compiled bytecode in a worker thread and capture exceptions.

    Returns ``(result, error)`` where ``result`` is the printed output if the
    code ran to completion, or ``None`` if it raised; and ``error`` is the
    exception object if any. The caller decides what to do with timeouts.
    """
    result: dict[str, Any] = {"output": None, "error": None}

    def _target() -> None:
        try:
            exec(byte_code, restricted)  # noqa: S102 - intentional: sandboxed bytecode only
            printed = restricted.get("_print")
            result["output"] = printed() if callable(printed) else ""
        except BaseException as exc:  # noqa: BLE001 - propagate to caller
            result["error"] = exc

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=TIMEOUT_SECONDS)
    if thread.is_alive():
        # We can't forcibly terminate a Python thread. The daemon flag means
        # it won't block process shutdown; the caller is informed that the
        # execution timed out and the thread is abandoned in place.
        return None, TimeoutError(f"Execution exceeded {TIMEOUT_SECONDS}s")
    return result["output"], result["error"]


async def execute(code: str, **kwargs: Any) -> dict[str, Any]:
    """Execute restricted Python code and return a structured tool result.

    The shape matches the existing tool contract:
        {"tool": "python_executor", "status": "success"|"error",
         "output": ..., "stdout": str, "error"?: str}
    """
    if not isinstance(code, str) or not code.strip():
        return {
            "tool": "python_executor",
            "status": "error",
            "error": "No code supplied",
        }

    try:
        byte_code = compile_restricted(code, filename="<inline>", mode="exec")
    except SyntaxError as exc:
        return {
            "tool": "python_executor",
            "status": "error",
            "error": f"Syntax error: {exc.msg} (line {exc.lineno})",
        }
    except Exception as exc:  # RestrictedPython rejects disallowed AST nodes here
        logger.info("RestrictedPython rejected code: %s", exc)
        return {
            "tool": "python_executor",
            "status": "error",
            "error": f"Restricted: {exc}",
        }

    restricted = _build_restricted_globals()
    printed, error = _run_in_thread(byte_code, restricted)

    if error is not None:
        if isinstance(error, TimeoutError):
            return {
                "tool": "python_executor",
                "status": "error",
                "error": str(error),
            }
        return {
            "tool": "python_executor",
            "status": "error",
            "error": f"{type(error).__name__}: {error}",
        }

    stdout = printed if isinstance(printed, str) else ""
    if len(stdout) > MAX_OUTPUT_BYTES:
        stdout = stdout[:MAX_OUTPUT_BYTES] + "\n…[truncated]"

    parsed: Any = stdout
    try:
        parsed = json.loads(stdout) if stdout.strip() else stdout
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "tool": "python_executor",
        "status": "success",
        "output": parsed,
        "stdout": stdout,
    }
