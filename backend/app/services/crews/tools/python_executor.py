"""Sandboxed Python executor for data analysis tasks."""
from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
from typing import Any

TOOL_SCHEMA: dict[str, Any] = {
    "name": "python_executor",
    "description": "Execute Python code for data analysis, calculations, and statistics. Returns stdout output. Only standard library + json available.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute. Use print() to output results. Only stdlib is available.",
            },
        },
        "required": ["code"],
    },
}

# Blocked imports for security
BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "pathlib", "glob",
    "socket", "http", "urllib", "requests", "httpx",
    "importlib", "ctypes", "signal", "threading", "multiprocessing",
    "pickle", "shelve", "sqlite3", "builtins", "__builtins__",
}

TIMEOUT_SECONDS = 10


async def execute(code: str, **kwargs: Any) -> dict[str, Any]:
    """Execute Python code in a sandboxed subprocess."""
    # Basic static analysis for dangerous imports
    for blocked in BLOCKED_IMPORTS:
        if f"import {blocked}" in code or f"from {blocked}" in code:
            return {
                "tool": "python_executor",
                "error": f"Import of '{blocked}' is not allowed for security reasons",
                "status": "error",
            }

    # Wrap code to capture output
    wrapped = textwrap.dedent(f"""\
import json, math, statistics, collections, itertools, functools, decimal, fractions, datetime, re, csv, io
try:
{textwrap.indent(code, '    ')}
except Exception as e:
    print(f"ERROR: {{type(e).__name__}}: {{e}}")
""")

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=True
        ) as f:
            f.write(wrapped)
            f.flush()

            result = subprocess.run(
                ["python3", f.name],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                env={},  # Empty env for sandboxing
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode != 0:
                return {
                    "tool": "python_executor",
                    "error": stderr or "Non-zero exit code",
                    "stdout": stdout,
                    "status": "error",
                }

            # Try to parse as JSON if possible
            parsed = stdout
            try:
                parsed = json.loads(stdout)
            except (json.JSONDecodeError, ValueError):
                pass

            return {
                "tool": "python_executor",
                "output": parsed,
                "stdout": stdout[:3000],
                "status": "success",
            }
    except subprocess.TimeoutExpired:
        return {
            "tool": "python_executor",
            "error": f"Execution timed out after {TIMEOUT_SECONDS}s",
            "status": "error",
        }
    except Exception as e:
        return {
            "tool": "python_executor",
            "error": str(e),
            "status": "error",
        }
