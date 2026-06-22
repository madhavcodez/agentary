"""Sandboxed Python code execution connector.

Runs user-supplied Python code in a subprocess with limited access.
The code has ``pandas``, ``numpy``, ``json``, ``math``, ``datetime``,
``collections``, ``itertools``, ``re``, and ``statistics`` available.
It must assign its output to a variable named ``result``, which is
captured via JSON on stdout.

Security measures:
- Dangerous builtins (open, exec, eval, compile, __import__) are blocked
  for untrusted module imports.
- Only a curated allowlist of safe modules is importable.
- Output is truncated to MAX_OUTPUT_BYTES (1 MB) to prevent memory exhaustion.
- Execution is bounded by a configurable timeout (default 30s).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from ..base_connector import SourceResult

logger = logging.getLogger(__name__)

# Maximum output size in bytes (1 MB)
MAX_OUTPUT_BYTES: int = 1_048_576

# Modules that user code is allowed to import
_SAFE_MODULES = frozenset({
    "math", "json", "datetime", "re", "collections", "itertools",
    "statistics", "functools", "operator", "string", "textwrap",
    "decimal", "fractions", "random", "copy", "pprint",
    "pandas", "numpy", "pd", "np",
})

# Patterns that indicate potentially dangerous code
_DANGEROUS_PATTERNS = [
    r"\bopen\s*\(",
    r"\b__import__\s*\(",
    r"\bexec\s*\(",
    r"\beval\s*\(",
    r"\bcompile\s*\(",
    r"\bgetattr\s*\(",
    r"\bsetattr\s*\(",
    r"\bdelattr\s*\(",
    r"\bglobals\s*\(",
    r"\bos\b",
    r"\bsys\b",
    r"\bsubprocess\b",
    r"\bshutil\b",
    r"\bsocket\b",
    r"\bpickle\b",
    r"\bshelve\b",
    r"\bctypes\b",
    r"\bimportlib\b",
    r"\b__builtins__\b",
    r"\b__subclasses__\b",
]


def _validate_code(code: str) -> str | None:
    """Return an error message if the code contains dangerous patterns, else None."""
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            return f"Blocked: code contains disallowed pattern ({pattern})"
    return None


class PythonExecutorConnector:
    """Execute Python code in a sandboxed subprocess."""

    name: str = "Python Executor"
    provider: str = "python_executor"
    description: str = (
        "Execute Python code for data analysis. Has pandas, numpy, and "
        "statistics available. Code must assign output to 'result'."
    )

    def __init__(self) -> None:
        pass  # No API key needed

    # ------------------------------------------------------------------
    # main execution method
    # ------------------------------------------------------------------

    async def execute(
        self,
        code: str,
        input_data: dict[str, Any] | None = None,
        timeout: int = 30,  # noqa: ASYNC109 - public connector API contract; subprocess wall-clock limit
    ) -> SourceResult:
        """Run *code* in a subprocess and return the captured ``result``."""
        # Static code validation
        validation_error = _validate_code(code)
        if validation_error:
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": "SecurityError",
                    "message": validation_error,
                },
            )

        serialized_input = json.dumps(input_data or {})

        # Wrapper script that restricts builtins and available modules
        wrapper = (
            "import json, math, statistics, datetime, collections, itertools, re\n"
            "from collections import Counter, defaultdict\n"
            "try:\n"
            "    import pandas as pd\n"
            "    import numpy as np\n"
            "except ImportError:\n"
            "    pass\n"
            "\n"
            "# Remove dangerous builtins\n"
            "import builtins as _builtins\n"
            "_safe_builtins = {k: v for k, v in vars(_builtins).items()\n"
            "                  if k not in ('open', 'exec', 'eval', 'compile',\n"
            "                               '__import__', 'exit', 'quit',\n"
            "                               'breakpoint', 'input')}\n"
            "\n"
            "# Restricted __import__ that only allows safe modules\n"
            f"_SAFE = {set(_SAFE_MODULES)}\n"
            "def _restricted_import(name, *args, **kwargs):\n"
            "    if name.split('.')[0] not in _SAFE:\n"
            "        raise ImportError(f'Module {name!r} is not allowed')\n"
            "    return _builtins.__import__(name, *args, **kwargs)\n"
            "_safe_builtins['__import__'] = _restricted_import\n"
            "_safe_builtins['__builtins__'] = _safe_builtins\n"
            "\n"
            f"data = json.loads('''{serialized_input}''')\n"
            "result = None\n"
            "\n"
            "_code_ns = dict(_safe_builtins)\n"
            "_code_ns['data'] = data\n"
            "_code_ns['result'] = result\n"
            f"_user_code = {code!r}\n"
            "_builtins.exec(_user_code, _code_ns)\n"
            "result = _code_ns.get('result')\n"
            "\n"
            "print(json.dumps({'result': result}, default=str))\n"
        )

        proc = await asyncio.create_subprocess_exec(
            "python3",
            "-c",
            wrapper,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": "TimeoutError",
                    "message": f"Execution exceeded {timeout}s timeout",
                },
            )

        stderr_text = stderr.decode().strip()
        stdout_text = stdout.decode().strip()

        # Truncate output to MAX_OUTPUT_BYTES
        if len(stdout_text) > MAX_OUTPUT_BYTES:
            logger.warning(
                "Python executor output truncated from %d to %d bytes",
                len(stdout_text), MAX_OUTPUT_BYTES,
            )
            stdout_text = stdout_text[:MAX_OUTPUT_BYTES]

        if proc.returncode != 0:
            return SourceResult(
                data=[],
                raw_response={"stderr": stderr_text[:MAX_OUTPUT_BYTES], "stdout": stdout_text},
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": "ExecutionError",
                    "message": stderr_text[:500] or "Non-zero exit code",
                    "exit_code": proc.returncode,
                },
            )

        try:
            output = json.loads(stdout_text)
        except json.JSONDecodeError:
            return SourceResult(
                data=[],
                raw_response={"stdout": stdout_text[:1000], "stderr": stderr_text[:1000]},
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": "OutputParseError",
                    "message": (
                        "Could not parse output as JSON. Make sure code "
                        "assigns to 'result' and does not print extra output."
                    ),
                },
            )

        result_value = output.get("result")
        if isinstance(result_value, list):
            data = result_value
        elif isinstance(result_value, dict):
            data = [result_value]
        else:
            data = [{"result": result_value}]

        return SourceResult(
            data=data,
            raw_response=output,
            total_results=len(data),
            source_name=self.name,
            metadata={"stderr": stderr_text} if stderr_text else {},
        )

    # ------------------------------------------------------------------
    # core interface
    # ------------------------------------------------------------------

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        raise NotImplementedError(
            "PythonExecutorConnector does not support search. "
            "Use execute() or get() with a 'code' kwarg instead."
        )

    async def get(
        self,
        identifier: str,
        *,
        code: str | None = None,
        input_data: dict[str, Any] | None = None,
        timeout: int = 30,  # noqa: ASYNC109 - public connector API contract; forwarded to execute()
        **kwargs: Any,
    ) -> SourceResult:
        return await self.execute(
            code=code or identifier,
            input_data=input_data,
            timeout=timeout,
        )

    async def health_check(self) -> dict[str, Any]:
        start = time.monotonic()
        try:
            result = await self.execute("result = 1 + 1", timeout=10)
            latency_ms = round((time.monotonic() - start) * 1_000, 1)
            if result.data and result.data[0].get("result") == 2:
                return {"status": "healthy", "latency_ms": latency_ms, "message": "OK"}
            return {
                "status": "degraded",
                "latency_ms": latency_ms,
                "message": "Execution succeeded but unexpected result",
            }
        except Exception as exc:
            latency_ms = round((time.monotonic() - start) * 1_000, 1)
            return {"status": "down", "latency_ms": latency_ms, "message": str(exc)}

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "name": "python_executor",
            "description": (
                "Execute Python code for data analysis. Has pandas, numpy, "
                "statistics available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": (
                            "Python code to execute. Must assign result "
                            "to 'result' variable."
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": "What the code does",
                    },
                },
                "required": ["code"],
            },
        }
