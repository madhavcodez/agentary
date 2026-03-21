"""Registry of tools available to expert agents."""
from __future__ import annotations

import importlib
from typing import Any

# Tool modules are loaded dynamically from the tools/ directory
_TOOL_MODULES = {
    "gemini_search": "app.services.crews.tools.gemini_search",
    "exa_search": "app.services.crews.tools.exa_search",
    "web_scraper": "app.services.crews.tools.web_scraper",
    "python_executor": "app.services.crews.tools.python_executor",
    "voice_caller": "app.services.crews.tools.voice_caller",
    "chart_generator": "app.services.crews.tools.chart_generator",
}

_loaded: dict[str, Any] = {}


def _load_tool(name: str) -> Any:
    """Lazily load a tool module."""
    if name not in _loaded:
        if name not in _TOOL_MODULES:
            raise ValueError(f"Unknown tool: {name}")
        _loaded[name] = importlib.import_module(_TOOL_MODULES[name])
    return _loaded[name]


class ToolRegistry:
    """Central registry for all tools available to expert agents."""

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}
        self._register_builtin()

    def _register_builtin(self) -> None:
        """Register all built-in tools."""
        for name in _TOOL_MODULES:
            mod = _load_tool(name)
            self._tools[name] = {
                "module": mod,
                "schema": getattr(mod, "TOOL_SCHEMA", {}),
                "execute": getattr(mod, "execute"),
            }

    def list_tools(self) -> list[dict[str, Any]]:
        """Return schemas for all registered tools."""
        return [tool["schema"] for tool in self._tools.values()]

    def get_tools_for_expert(self, tool_names: list[str]) -> list[dict[str, Any]]:
        """Return tool schemas for a specific expert's allowed tools."""
        return [
            self._tools[name]["schema"]
            for name in tool_names
            if name in self._tools
        ]

    def get_gemini_tool_declarations(self, tool_names: list[str]) -> list[dict[str, Any]]:
        """Return tool declarations in Gemini function-calling format."""
        declarations = []
        for name in tool_names:
            if name not in self._tools:
                continue
            schema = self._tools[name]["schema"]
            declarations.append({
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema.get("parameters", {}),
            })
        return declarations

    async def execute(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a tool by name with given arguments."""
        if tool_name not in self._tools:
            return {
                "tool": tool_name,
                "error": f"Unknown tool: {tool_name}",
                "status": "error",
            }

        try:
            result = await self._tools[tool_name]["execute"](**kwargs)
            return result
        except Exception as e:
            return {
                "tool": tool_name,
                "error": str(e),
                "status": "error",
            }

    def has_tool(self, name: str) -> bool:
        return name in self._tools


# Singleton instance
tool_registry = ToolRegistry()
