"""Sandboxed Python code execution connector.

Runs user-supplied Python code in a subprocess with limited access.
The code has ``pandas``, ``numpy``, ``json``, ``math``, ``datetime``,
``collections``, and ``statistics`` available. It must assign its output
to a variable named ``result``, which is captured via JSON on stdout.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from ..base_connector import SourceResult


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
        timeout: int = 30,
    ) -> SourceResult:
        """Run *code* in a subprocess and return the captured ``result``."""
        serialized_input = json.dumps(input_data or {})

        wrapper = (
            "import json, math, statistics, datetime, collections\n"
            "from collections import Counter, defaultdict\n"
            "try:\n"
            "    import pandas as pd\n"
            "    import numpy as np\n"
            "except ImportError:\n"
            "    pass\n"
            "\n"
            f"data = json.loads('''{serialized_input}''')\n"
            "result = None\n"
            "\n"
            f"{code}\n"
            "\n"
            'print(json.dumps({"result": result}, default=str))\n'
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
        except asyncio.TimeoutError:
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

        if proc.returncode != 0:
            return SourceResult(
                data=[],
                raw_response={"stderr": stderr_text, "stdout": stdout_text},
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": "ExecutionError",
                    "message": stderr_text or "Non-zero exit code",
                    "exit_code": proc.returncode,
                },
            )

        try:
            output = json.loads(stdout_text)
        except json.JSONDecodeError:
            return SourceResult(
                data=[],
                raw_response={"stdout": stdout_text, "stderr": stderr_text},
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
        timeout: int = 30,
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
