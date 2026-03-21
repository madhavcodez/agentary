"""Tests for the tool registry."""
import pytest

from app.services.crews.tool_registry import ToolRegistry, tool_registry


class TestToolRegistry:
    def test_registry_has_six_tools(self):
        tools = tool_registry.list_tools()
        assert len(tools) >= 6

    def test_expected_tools_registered(self):
        expected = {
            "gemini_search", "exa_search", "web_scraper",
            "python_executor", "voice_caller", "chart_generator",
        }
        tool_names = {t["name"] for t in tool_registry.list_tools()}
        assert expected.issubset(tool_names)

    def test_all_tools_have_schema(self):
        for tool in tool_registry.list_tools():
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool

    def test_get_tools_for_expert(self):
        tools = tool_registry.get_tools_for_expert(["gemini_search", "exa_search"])
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"gemini_search", "exa_search"}

    def test_get_gemini_tool_declarations(self):
        declarations = tool_registry.get_gemini_tool_declarations(["web_scraper"])
        assert len(declarations) == 1
        assert declarations[0]["name"] == "web_scraper"

    def test_unknown_tool_returns_empty(self):
        tools = tool_registry.get_tools_for_expert(["nonexistent_tool"])
        assert len(tools) == 0

    def test_has_tool(self):
        assert tool_registry.has_tool("gemini_search") is True
        assert tool_registry.has_tool("nonexistent") is False


@pytest.mark.asyncio
class TestToolExecution:
    async def test_chart_generator(self):
        result = await tool_registry.execute(
            "chart_generator",
            chart_type="bar",
            title="Test Chart",
            labels=["A", "B", "C"],
            datasets=[{"label": "Values", "data": [10, 20, 30]}],
        )
        assert result["status"] == "success"
        assert result["chart_config"]["type"] == "bar"

    async def test_voice_caller_stub(self):
        result = await tool_registry.execute(
            "voice_caller",
            phone_number="+15125551234",
            business_name="Test Business",
            questions=["What are your hours?"],
        )
        assert result["status"] == "stub"
        assert "simulated" in result["outcome"].lower()

    async def test_unknown_tool_error(self):
        result = await tool_registry.execute("nonexistent_tool")
        assert result["status"] == "error"
