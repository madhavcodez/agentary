"""Comprehensive tests for the Agentary data source connector system.

Covers: SourceResult, SourceConnector protocol, SourceRegistry,
all 10 connectors' get_tool_definition(), PythonExecutorConnector,
CustomAPIConnector, WebScraperConnector, EntityService, and SourceCache.

All external APIs are mocked -- no database or network access required.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from app.services.data_sources.base_connector import SourceConnector, SourceResult
from app.services.data_sources.cache import SourceCache
from app.services.data_sources.connectors.custom_api import CustomApiConnector, _traverse
from app.services.data_sources.connectors.python_executor import PythonExecutorConnector
from app.services.data_sources.connectors.web_scraper import (
    WebScraperConnector,
    _clean_text,
    _extract_tables,
)
from app.services.data_sources.source_registry import SourceRegistry
from app.services.entities.entity_service import (
    EntityService,
    _merge_dicts,
    _normalize_address,
)

# =====================================================================
# Helpers
# =====================================================================


def _make_mock_connector(
    name: str = "mock",
    provider: str = "mock_provider",
    description: str = "A mock connector",
) -> MagicMock:
    """Create a MagicMock that satisfies the SourceConnector protocol."""
    connector = MagicMock()
    connector.name = name
    connector.provider = provider
    connector.description = description
    connector.search = AsyncMock(
        return_value=SourceResult(
            data=[{"result": "test"}],
            raw_response=None,
            total_results=1,
            source_name=name,
        ),
    )
    connector.get = AsyncMock(
        return_value=SourceResult(
            data=[],
            raw_response=None,
            total_results=0,
            source_name=name,
        ),
    )
    connector.health_check = AsyncMock(
        return_value={"status": "healthy", "latency_ms": 1.0, "message": "OK"},
    )
    connector.get_tool_definition = MagicMock(
        return_value={
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    )
    return connector


def _make_entity(
    *,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    entity_type: str = "person",
    name: str = "Test Entity",
    description: str | None = None,
    canonical_data: dict | None = None,
    aliases: list | None = None,
    source_urls: list | None = None,
    tags: list | None = None,
) -> MagicMock:
    """Build a MagicMock that looks like an Entity ORM instance."""
    entity = MagicMock()
    entity.id = entity_id or uuid4()
    entity.user_id = user_id or uuid4()
    entity.entity_type = entity_type
    entity.name = name
    entity.description = description
    entity.canonical_data = canonical_data if canonical_data is not None else {}
    entity.aliases = aliases if aliases is not None else []
    entity.source_urls = source_urls if source_urls is not None else []
    entity.tags = tags if tags is not None else []
    entity.created_at = MagicMock()
    return entity


# =====================================================================
# 1. SourceResult and SourceConnector protocol
# =====================================================================


class TestSourceResult:
    def test_creation_with_defaults(self):
        result = SourceResult(
            data=[{"key": "value"}],
            raw_response={"raw": True},
            total_results=1,
            source_name="test_source",
        )
        assert result.data == [{"key": "value"}]
        assert result.raw_response == {"raw": True}
        assert result.total_results == 1
        assert result.source_name == "test_source"
        assert result.source_url is None
        assert result.cost_usd == 0.0
        assert result.cached is False
        assert result.metadata == {}

    def test_creation_with_all_fields(self):
        result = SourceResult(
            data=[{"a": 1}],
            raw_response="raw",
            total_results=5,
            source_name="full",
            source_url="https://example.com",
            cost_usd=0.05,
            cached=True,
            metadata={"page": 1},
        )
        assert result.source_url == "https://example.com"
        assert result.cost_usd == 0.05
        assert result.cached is True
        assert result.metadata == {"page": 1}

    def test_to_dict_includes_correct_keys(self):
        result = SourceResult(
            data=[{"x": 1}],
            raw_response=None,
            total_results=1,
            source_name="src",
            source_url="http://test.com",
            cost_usd=0.01,
            cached=True,
            metadata={"m": 2},
        )
        d = result.to_dict()
        assert d["data"] == [{"x": 1}]
        assert d["total_results"] == 1
        assert d["source_name"] == "src"
        assert d["source_url"] == "http://test.com"
        assert d["cost_usd"] == 0.01
        assert d["cached"] is True
        assert d["metadata"] == {"m": 2}
        # raw_response is intentionally excluded from to_dict
        assert "raw_response" not in d

    def test_to_dict_empty_data(self):
        result = SourceResult(data=[], raw_response=None, total_results=0, source_name="empty")
        d = result.to_dict()
        assert d["data"] == []
        assert d["total_results"] == 0

    def test_frozen_immutability(self):
        result = SourceResult(data=[], raw_response=None, total_results=0, source_name="frozen")
        with pytest.raises(AttributeError):
            result.source_name = "changed"


class TestSourceConnectorProtocol:
    def test_mock_connector_satisfies_protocol(self):
        connector = _make_mock_connector()
        assert isinstance(connector, SourceConnector)

    def test_python_executor_satisfies_protocol(self):
        connector = PythonExecutorConnector()
        assert isinstance(connector, SourceConnector)

    def test_web_scraper_satisfies_protocol(self):
        connector = WebScraperConnector()
        assert isinstance(connector, SourceConnector)

    def test_custom_api_satisfies_protocol(self):
        connector = CustomApiConnector({"base_url": "https://api.example.com"})
        assert isinstance(connector, SourceConnector)


# =====================================================================
# 2. SourceRegistry
# =====================================================================


class TestSourceRegistry:
    def test_register_and_get(self):
        registry = SourceRegistry()
        connector = _make_mock_connector(provider="alpha")
        registry.register(connector)
        assert registry.get("alpha") is connector

    def test_get_returns_none_for_missing(self):
        registry = SourceRegistry()
        assert registry.get("nonexistent") is None

    def test_register_overwrites_same_provider(self):
        registry = SourceRegistry()
        first = _make_mock_connector(provider="dup", name="first")
        second = _make_mock_connector(provider="dup", name="second")
        registry.register(first)
        registry.register(second)
        assert registry.get("dup").name == "second"

    def test_list_available_returns_correct_format(self):
        registry = SourceRegistry()
        registry.register(_make_mock_connector(provider="a", name="Alpha", description="desc A"))
        registry.register(_make_mock_connector(provider="b", name="Beta", description="desc B"))
        available = registry.list_available()
        assert len(available) == 2
        assert all(set(entry.keys()) == {"provider", "name", "description"} for entry in available)
        providers = {e["provider"] for e in available}
        assert providers == {"a", "b"}

    def test_list_available_empty_registry(self):
        registry = SourceRegistry()
        assert registry.list_available() == []

    def test_get_tool_definitions_all(self):
        registry = SourceRegistry()
        registry.register(_make_mock_connector(provider="x"))
        registry.register(_make_mock_connector(provider="y"))
        defs = registry.get_tool_definitions()
        assert len(defs) == 2
        for d in defs:
            assert "name" in d
            assert "description" in d
            assert "parameters" in d

    def test_get_tool_definitions_filtered(self):
        registry = SourceRegistry()
        registry.register(_make_mock_connector(provider="x"))
        registry.register(_make_mock_connector(provider="y"))
        registry.register(_make_mock_connector(provider="z"))
        defs = registry.get_tool_definitions(providers=["x", "z"])
        assert len(defs) == 2

    def test_get_tool_definitions_ignores_unknown_providers(self):
        registry = SourceRegistry()
        registry.register(_make_mock_connector(provider="x"))
        defs = registry.get_tool_definitions(providers=["x", "unknown"])
        assert len(defs) == 1

    @pytest.mark.asyncio
    async def test_query_dispatches_to_correct_connector(self):
        registry = SourceRegistry()
        connector = _make_mock_connector(provider="test_prov")
        registry.register(connector)
        result = await registry.query("test_prov", method="search", query="hello")
        connector.search.assert_awaited_once_with(query="hello")
        assert result.source_name == "mock"

    @pytest.mark.asyncio
    async def test_query_raises_for_unknown_provider(self):
        registry = SourceRegistry()
        with pytest.raises(ValueError, match="Unknown provider"):
            await registry.query("ghost")

    @pytest.mark.asyncio
    async def test_query_calls_get_method(self):
        registry = SourceRegistry()
        connector = _make_mock_connector(provider="prov")
        registry.register(connector)
        await registry.query("prov", method="get", identifier="abc")
        connector.get.assert_awaited_once_with(identifier="abc")

    @pytest.mark.asyncio
    async def test_health_check_all_runs_all_connectors(self):
        registry = SourceRegistry()
        c1 = _make_mock_connector(provider="a")
        c2 = _make_mock_connector(provider="b")
        c2.health_check = AsyncMock(
            return_value={"status": "down", "latency_ms": 5.0, "message": "fail"}
        )
        registry.register(c1)
        registry.register(c2)
        results = await registry.health_check_all()
        assert "a" in results
        assert "b" in results
        assert results["a"]["status"] == "healthy"
        assert results["b"]["status"] == "down"

    @pytest.mark.asyncio
    async def test_health_check_all_handles_exceptions(self):
        registry = SourceRegistry()
        c = _make_mock_connector(provider="broken")
        c.health_check = AsyncMock(side_effect=RuntimeError("boom"))
        registry.register(c)
        results = await registry.health_check_all()
        assert results["broken"]["status"] == "down"
        assert "boom" in results["broken"]["message"]


# =====================================================================
# 3. All connectors' get_tool_definition()
# =====================================================================


class TestAllConnectorToolDefinitions:
    """Verify every connector returns a valid tool definition dict."""

    @staticmethod
    def _assert_valid_tool_def(tool_def: dict[str, Any]):
        assert isinstance(tool_def, dict)
        assert "name" in tool_def
        assert isinstance(tool_def["name"], str)
        assert "description" in tool_def
        assert isinstance(tool_def["description"], str)
        assert "parameters" in tool_def
        params = tool_def["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert isinstance(params["properties"], dict)
        assert "required" in params
        assert isinstance(params["required"], list)

    def test_python_executor_tool_def(self):
        connector = PythonExecutorConnector()
        self._assert_valid_tool_def(connector.get_tool_definition())

    def test_web_scraper_tool_def(self):
        connector = WebScraperConnector()
        self._assert_valid_tool_def(connector.get_tool_definition())

    def test_custom_api_tool_def(self):
        connector = CustomApiConnector(
            {
                "base_url": "https://api.example.com",
                "name": "Example",
                "search_params_map": {"query": "q", "category": "cat"},
            }
        )
        td = connector.get_tool_definition()
        self._assert_valid_tool_def(td)
        # Extra params from search_params_map should appear
        assert "category" in td["parameters"]["properties"]

    @patch("app.services.data_sources.connectors.gemini_search.settings")
    def test_gemini_search_tool_def(self, mock_settings):
        mock_settings.gemini_api_key = "fake-key"
        from app.services.data_sources.connectors.gemini_search import (
            GeminiSearchConnector,
        )

        connector = GeminiSearchConnector()
        self._assert_valid_tool_def(connector.get_tool_definition())

    @patch("app.services.data_sources.connectors.exa.settings")
    def test_exa_tool_def(self, mock_settings):
        mock_settings.exa_api_key = "fake-key"
        from app.services.data_sources.connectors.exa import ExaConnector

        connector = ExaConnector()
        self._assert_valid_tool_def(connector.get_tool_definition())

    @patch("app.services.data_sources.connectors.google_places.settings")
    def test_google_places_tool_def(self, mock_settings):
        mock_settings.google_places_api_key = "fake-key"
        from app.services.data_sources.connectors.google_places import (
            GooglePlacesConnector,
        )

        connector = GooglePlacesConnector()
        self._assert_valid_tool_def(connector.get_tool_definition())

    def test_zillow_tool_def(self):
        from app.services.data_sources.connectors.zillow import ZillowConnector

        connector = ZillowConnector(api_key="fake")
        self._assert_valid_tool_def(connector.get_tool_definition())

    def test_county_records_tool_def(self):
        from app.services.data_sources.connectors.county_records import (
            CountyRecordsConnector,
        )

        connector = CountyRecordsConnector()
        self._assert_valid_tool_def(connector.get_tool_definition())

    def test_yelp_tool_def(self):
        from app.services.data_sources.connectors.yelp import YelpConnector

        connector = YelpConnector(api_key="fake")
        self._assert_valid_tool_def(connector.get_tool_definition())

    def test_crunchbase_tool_def(self):
        from app.services.data_sources.connectors.crunchbase import (
            CrunchbaseConnector,
        )

        connector = CrunchbaseConnector(api_key="fake")
        self._assert_valid_tool_def(connector.get_tool_definition())


# =====================================================================
# 4. PythonExecutorConnector
# =====================================================================


class TestPythonExecutorConnector:
    @pytest.mark.asyncio
    async def test_execute_simple_addition(self):
        connector = PythonExecutorConnector()
        result = await connector.execute("result = 1 + 1")
        assert result.total_results == 1
        assert result.data[0]["result"] == 2
        assert result.source_name == "Python Executor"

    @pytest.mark.asyncio
    async def test_execute_with_input_data(self):
        connector = PythonExecutorConnector()
        result = await connector.execute(
            "result = data['x'] * data['y']",
            input_data={"x": 3, "y": 7},
        )
        assert result.data[0]["result"] == 21

    @pytest.mark.asyncio
    async def test_execute_returns_list(self):
        connector = PythonExecutorConnector()
        result = await connector.execute("result = [1, 2, 3]")
        assert result.data == [1, 2, 3]
        assert result.total_results == 3

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self):
        connector = PythonExecutorConnector()
        result = await connector.execute('result = {"a": 1, "b": 2}')
        assert result.data == [{"a": 1, "b": 2}]
        assert result.total_results == 1

    @pytest.mark.asyncio
    async def test_execute_timeout_returns_error_result(self):
        connector = PythonExecutorConnector()
        result = await connector.execute(
            "import time; time.sleep(10); result = 'done'",
            timeout=1,
        )
        assert result.total_results == 0
        assert result.data == []
        assert result.metadata.get("error") == "TimeoutError"

    @pytest.mark.asyncio
    async def test_execute_syntax_error(self):
        connector = PythonExecutorConnector()
        result = await connector.execute("result = ???invalid")
        assert result.total_results == 0
        assert result.metadata.get("error") == "ExecutionError"

    @pytest.mark.asyncio
    async def test_execute_runtime_error(self):
        connector = PythonExecutorConnector()
        result = await connector.execute("result = 1 / 0")
        assert result.total_results == 0
        assert result.metadata.get("error") == "ExecutionError"

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self):
        connector = PythonExecutorConnector()
        health = await connector.health_check()
        assert health["status"] == "healthy"
        assert "latency_ms" in health
        assert health["message"] == "OK"

    @pytest.mark.asyncio
    async def test_search_raises_not_implemented(self):
        connector = PythonExecutorConnector()
        with pytest.raises(NotImplementedError, match="does not support search"):
            await connector.search("test")

    @pytest.mark.asyncio
    async def test_get_delegates_to_execute(self):
        connector = PythonExecutorConnector()
        result = await connector.get("ignored", code="result = 42")
        assert result.data[0]["result"] == 42

    @pytest.mark.asyncio
    async def test_get_uses_identifier_as_code(self):
        connector = PythonExecutorConnector()
        result = await connector.get("result = 99")
        assert result.data[0]["result"] == 99

    def test_attributes(self):
        connector = PythonExecutorConnector()
        assert connector.name == "Python Executor"
        assert connector.provider == "python_executor"
        assert "Python code" in connector.description


# =====================================================================
# 5. CustomAPIConnector
# =====================================================================


class TestCustomApiConnector:
    def test_init_stores_config(self):
        config = {
            "base_url": "https://api.example.com",
            "name": "Test API",
            "auth_type": "bearer",
            "auth_config": {"token": "secret"},
            "search_endpoint": "/search",
            "search_method": "GET",
            "result_path": "data.items",
        }
        connector = CustomApiConnector(config)
        assert connector.name == "Test API"
        assert connector.provider == "custom_api"

    def test_get_tool_definition_dynamic_schema(self):
        config = {
            "base_url": "https://api.example.com",
            "name": "My Source",
            "search_params_map": {
                "query": "q",
                "location": "loc",
                "limit": "count",
            },
        }
        connector = CustomApiConnector(config)
        td = connector.get_tool_definition()
        props = td["parameters"]["properties"]
        assert "query" in props
        assert "location" in props
        assert "limit" in props
        assert td["parameters"]["required"] == ["query"]

    def test_traverse_simple_path(self):
        obj = {"data": {"items": [1, 2, 3]}}
        assert _traverse(obj, "data.items") == [1, 2, 3]

    def test_traverse_nested_dict(self):
        obj = {"a": {"b": {"c": "deep"}}}
        assert _traverse(obj, "a.b.c") == "deep"

    def test_traverse_list_index(self):
        obj = {"data": [10, 20, 30]}
        assert _traverse(obj, "data.1") == 20

    def test_traverse_list_index_out_of_bounds(self):
        obj = {"data": [10]}
        assert _traverse(obj, "data.5") is None

    def test_traverse_missing_key(self):
        obj = {"a": 1}
        assert _traverse(obj, "b.c") is None

    def test_traverse_none_in_path(self):
        obj = {"a": None}
        assert _traverse(obj, "a.b") is None

    def test_traverse_non_dict_non_list(self):
        obj = {"a": 42}
        assert _traverse(obj, "a.b") is None

    def test_bearer_auth_headers(self):
        config = {
            "base_url": "https://api.test.com",
            "auth_type": "bearer",
            "auth_config": {"token": "my-token"},
        }
        connector = CustomApiConnector(config)
        headers = connector._build_auth_headers()
        assert headers["Authorization"] == "Bearer my-token"

    def test_api_key_header_auth(self):
        config = {
            "base_url": "https://api.test.com",
            "auth_type": "api_key_header",
            "auth_config": {"header": "X-Api-Key", "key": "abc123"},
        }
        connector = CustomApiConnector(config)
        headers = connector._build_auth_headers()
        assert headers["X-Api-Key"] == "abc123"

    def test_basic_auth_headers(self):
        import base64

        config = {
            "base_url": "https://api.test.com",
            "auth_type": "basic",
            "auth_config": {"username": "user", "password": "pass"},
        }
        connector = CustomApiConnector(config)
        headers = connector._build_auth_headers()
        expected = base64.b64encode(b"user:pass").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_api_key_param_auth(self):
        config = {
            "base_url": "https://api.test.com",
            "auth_type": "api_key_param",
            "auth_config": {"param": "apikey", "key": "xyz"},
        }
        connector = CustomApiConnector(config)
        params = connector._build_auth_params()
        assert params == {"apikey": "xyz"}

    def test_no_auth_returns_empty(self):
        config = {
            "base_url": "https://api.test.com",
            "auth_type": "none",
        }
        connector = CustomApiConnector(config)
        assert connector._build_auth_headers() == {}
        assert connector._build_auth_params() == {}

    def test_field_mapping(self):
        config = {
            "base_url": "https://api.test.com",
            "field_map": {"full_name": "name", "contact.email": "email"},
        }
        connector = CustomApiConnector(config)
        raw = {"full_name": "Alice", "contact": {"email": "a@b.com"}}
        mapped = connector._map_record(raw)
        assert mapped == {"name": "Alice", "email": "a@b.com"}

    def test_field_mapping_empty_returns_copy(self):
        config = {"base_url": "https://api.test.com"}
        connector = CustomApiConnector(config)
        raw = {"x": 1, "y": 2}
        mapped = connector._map_record(raw)
        assert mapped == {"x": 1, "y": 2}

    @pytest.mark.asyncio
    async def test_get_no_detail_endpoint(self):
        config = {"base_url": "https://api.test.com"}
        connector = CustomApiConnector(config)
        result = await connector.get("some-id")
        assert result.total_results == 0
        assert "No detail endpoint" in result.metadata.get("message", "")


# =====================================================================
# 6. WebScraperConnector
# =====================================================================


class TestWebScraperConnector:
    @pytest.mark.asyncio
    async def test_text_extraction(self):
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is test content.</p>
        </body>
        </html>
        """
        connector = WebScraperConnector()

        with patch.object(connector, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (html, 200)
            result = await connector.get("https://example.com", extract_type="text")

        assert result.total_results == 1
        assert result.data[0]["title"] == "Test Page"
        assert "Hello World" in result.data[0]["text"]
        assert result.data[0]["extract_type"] == "text"

    @pytest.mark.asyncio
    async def test_table_extraction(self):
        html = """
        <html>
        <head><title>Tables</title></head>
        <body>
            <table>
                <tr><th>Name</th><th>Age</th></tr>
                <tr><td>Alice</td><td>30</td></tr>
                <tr><td>Bob</td><td>25</td></tr>
            </table>
        </body>
        </html>
        """
        connector = WebScraperConnector()

        with patch.object(connector, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (html, 200)
            result = await connector.get("https://example.com/data", extract_type="tables")

        assert result.data[0]["extract_type"] == "tables"
        tables = result.data[0]["tables"]
        assert len(tables) == 1
        assert tables[0]["headers"] == ["Name", "Age"]
        assert tables[0]["row_count"] == 2
        assert tables[0]["rows"][0] == {"Name": "Alice", "Age": "30"}

    @pytest.mark.asyncio
    async def test_http_403_returns_error(self):
        connector = WebScraperConnector()
        with patch.object(connector, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ("", 403)
            result = await connector.get("https://blocked.com")

        assert result.total_results == 0
        assert result.metadata["status_code"] == 403

    @pytest.mark.asyncio
    async def test_http_429_rate_limited(self):
        connector = WebScraperConnector()
        with patch.object(connector, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ("", 429)
            result = await connector.get("https://ratelimited.com")

        assert result.total_results == 0
        assert "429" in result.metadata["error"]

    @pytest.mark.asyncio
    async def test_http_500_server_error(self):
        connector = WebScraperConnector()
        with patch.object(connector, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ("", 500)
            result = await connector.get("https://broken.com")

        assert result.total_results == 0
        assert "500" in result.metadata["error"]

    @pytest.mark.asyncio
    async def test_empty_response_body(self):
        connector = WebScraperConnector()
        with patch.object(connector, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ("", 200)
            result = await connector.get("https://empty.com")

        assert result.total_results == 0
        assert "Empty" in result.metadata["error"]

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self):
        connector = WebScraperConnector()
        with patch.object(connector, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = httpx.TimeoutException("timed out")
            result = await connector.get("https://slow.com")

        assert result.total_results == 0
        assert "timed out" in result.metadata["error"]

    @pytest.mark.asyncio
    async def test_connection_error(self):
        connector = WebScraperConnector()
        with patch.object(connector, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = httpx.ConnectError("connection refused")
            result = await connector.get("https://unreachable.com")

        assert result.total_results == 0
        assert "Connection failed" in result.metadata["error"]

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        connector = WebScraperConnector()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            health = await connector.health_check()

        assert health["status"] == "healthy"
        assert "latency_ms" in health

    @pytest.mark.asyncio
    async def test_health_check_down(self):
        connector = WebScraperConnector()
        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ConnectError("no route"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            health = await connector.health_check()

        assert health["status"] == "down"

    @pytest.mark.asyncio
    async def test_search_requires_urls(self):
        connector = WebScraperConnector()
        result = await connector.search("test query")
        assert result.total_results == 0
        assert "requires 'urls' parameter" in result.metadata["error"]

    def test_attributes(self):
        connector = WebScraperConnector()
        assert connector.name == "Web Scraper"
        assert connector.provider == "web_scraper"


class TestWebScraperHelpers:
    def test_clean_text_strips_scripts_and_styles(self):
        from bs4 import BeautifulSoup

        html = "<html><body><script>alert(1)</script><style>.x{}</style><p>Hello</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = _clean_text(soup)
        assert "alert" not in text
        assert "Hello" in text

    def test_clean_text_truncates_long_content(self):
        from bs4 import BeautifulSoup

        html = f"<html><body><p>{'x' * 20000}</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = _clean_text(soup)
        assert len(text) <= 10_000

    def test_extract_tables_empty(self):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><body><p>no tables</p></body></html>", "html.parser")
        tables = _extract_tables(soup)
        assert tables == []

    def test_extract_tables_mismatched_columns(self):
        from bs4 import BeautifulSoup

        html = """
        <table>
            <tr><th>A</th><th>B</th><th>C</th></tr>
            <tr><td>1</td><td>2</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        tables = _extract_tables(soup)
        assert len(tables) == 1
        # Mismatched row gets padded
        assert tables[0]["rows"][0] == {"A": "1", "B": "2", "C": ""}


# =====================================================================
# 7. EntityService
# =====================================================================


class TestEntityServiceHelpers:
    def test_normalize_address_street(self):
        assert "st" in _normalize_address("123 Main Street")

    def test_normalize_address_avenue(self):
        assert "ave" in _normalize_address("456 Park Avenue")

    def test_normalize_address_removes_punctuation(self):
        normalized = _normalize_address("Apt #5, 789 Oak Blvd.")
        assert "#" not in normalized
        assert "," not in normalized

    def test_normalize_address_case_insensitive(self):
        a = _normalize_address("123 MAIN STREET")
        b = _normalize_address("123 main street")
        assert a == b

    def test_merge_dicts_fills_gaps(self):
        existing = {"a": 1, "b": None}
        new = {"b": 2, "c": 3}
        merged = _merge_dicts(existing, new)
        assert merged == {"a": 1, "b": 2, "c": 3}

    def test_merge_dicts_no_overwrite(self):
        existing = {"a": 1, "b": 2}
        new = {"a": 99, "c": 3}
        merged = _merge_dicts(existing, new)
        # existing 'a' should be preserved
        assert merged["a"] == 1
        assert merged["c"] == 3

    def test_merge_dicts_skips_none_values(self):
        existing = {"a": 1}
        new = {"b": None}
        merged = _merge_dicts(existing, new)
        assert "b" not in merged


class TestEntityServiceCreateEntity:
    @pytest.mark.asyncio
    async def test_create_entity(self):
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()
        data = {
            "entity_type": "person",
            "name": "Jane Doe",
            "description": "Test person",
            "canonical_data": {"email": "jane@test.com"},
            "aliases": ["JD"],
            "source_urls": ["https://linkedin.com/jane"],
            "tags": ["lead"],
        }
        with patch("app.services.entities.entity_service.Entity") as MockEntity:
            mock_instance = _make_entity(user_id=user_id, name="Jane Doe", entity_type="person")
            MockEntity.return_value = mock_instance
            result = await service.create_entity(user_id, data, db)

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
        assert result.name == "Jane Doe"


class TestEntityServiceFindOrCreate:
    @pytest.mark.asyncio
    async def test_find_or_create_person_by_email(self):
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()

        existing_entity = _make_entity(
            user_id=user_id,
            entity_type="person",
            name="Jane Doe",
            canonical_data={"email": "jane@test.com"},
        )

        # Simulate: db.query(Entity).filter(...).all() returns the existing entity
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [existing_entity]
        db.query.return_value = mock_query

        identifiers = {
            "email": "jane@test.com",
            "name": "Jane Doe",
        }

        result = await service.find_or_create(user_id, "person", identifiers, db)
        assert result is existing_entity

    @pytest.mark.asyncio
    async def test_find_or_create_company_by_name_fuzzy(self):
        """A name close enough to exceed the 85 threshold should match."""
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()

        existing_entity = _make_entity(
            user_id=user_id,
            entity_type="company",
            name="Acme Corporation",
            canonical_data={"domain": "acme.com"},
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [existing_entity]
        db.query.return_value = mock_query

        # "Acme Corporaton" (one letter off) passes the 85 threshold
        identifiers = {"name": "Acme Corporaton"}

        result = await service.find_or_create(user_id, "company", identifiers, db)
        assert result is existing_entity

    @pytest.mark.asyncio
    async def test_find_or_create_company_below_threshold_creates_new(self):
        """A name too different should trigger creation of a new entity."""
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()

        existing_entity = _make_entity(
            user_id=user_id,
            entity_type="company",
            name="Acme Corporation",
            canonical_data={},
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [existing_entity]
        db.query.return_value = mock_query

        identifiers = {"name": "Totally Different Co"}

        with patch("app.services.entities.entity_service.Entity") as MockEntity:
            new_entity = _make_entity(
                user_id=user_id,
                entity_type="company",
                name="Totally Different Co",
            )
            MockEntity.return_value = new_entity
            result = await service.find_or_create(user_id, "company", identifiers, db)

        # Should have created a new entity since names are too different
        db.add.assert_called_once()
        assert result.name == "Totally Different Co"

    @pytest.mark.asyncio
    async def test_find_or_create_company_exact_name_match(self):
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()

        existing_entity = _make_entity(
            user_id=user_id,
            entity_type="company",
            name="Acme Inc",
            canonical_data={},
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [existing_entity]
        db.query.return_value = mock_query

        identifiers = {"name": "Acme Inc"}

        result = await service.find_or_create(user_id, "company", identifiers, db)
        # Exact match should always return the existing entity
        assert result is existing_entity

    @pytest.mark.asyncio
    async def test_find_or_create_creates_new_when_no_match(self):
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []  # No existing entities
        mock_query.first.return_value = None
        db.query.return_value = mock_query

        identifiers = {
            "name": "Brand New Company",
            "email": "new@company.com",
        }

        with patch("app.services.entities.entity_service.Entity") as MockEntity:
            new_entity = _make_entity(
                user_id=user_id,
                entity_type="company",
                name="Brand New Company",
            )
            MockEntity.return_value = new_entity
            result = await service.find_or_create(user_id, "company", identifiers, db)

        db.add.assert_called_once()
        assert result.name == "Brand New Company"

    @pytest.mark.asyncio
    async def test_find_or_create_merges_canonical_data(self):
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()

        existing_entity = _make_entity(
            user_id=user_id,
            entity_type="person",
            name="Jane Doe",
            canonical_data={"email": "jane@test.com", "phone": None},
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [existing_entity]
        db.query.return_value = mock_query

        identifiers = {
            "email": "jane@test.com",
            "canonical_data": {"phone": "555-1234", "title": "CEO"},
        }

        result = await service.find_or_create(user_id, "person", identifiers, db)
        assert result is existing_entity
        # After merge, phone should be filled in
        db.commit.assert_called()


class TestEntityServiceUpdateEntity:
    @pytest.mark.asyncio
    async def test_update_entity_merges_canonical_data(self):
        service = EntityService()
        db = MagicMock()
        entity_id = uuid4()

        existing = _make_entity(
            entity_id=entity_id,
            canonical_data={"email": "old@test.com", "phone": None},
            aliases=["alias1"],
            source_urls=["url1"],
            tags=["tag1"],
        )
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing
        db.query.return_value = mock_query

        await service.update_entity(
            entity_id,
            {
                "canonical_data": {"phone": "555-0000", "role": "CEO"},
                "aliases": ["alias2"],
                "source_urls": ["url2"],
                "tags": ["tag2"],
            },
            db,
        )

        db.commit.assert_called_once()
        # canonical_data should merge (no overwrite of existing 'email')
        assert existing.canonical_data["email"] == "old@test.com"
        assert existing.canonical_data["phone"] == "555-0000"
        assert existing.canonical_data["role"] == "CEO"

    @pytest.mark.asyncio
    async def test_update_entity_not_found_raises(self):
        service = EntityService()
        db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        db.query.return_value = mock_query

        with pytest.raises(ValueError, match="not found"):
            await service.update_entity(uuid4(), {"name": "x"}, db)


class TestEntityServiceMergeEntities:
    @pytest.mark.asyncio
    async def test_merge_entities_combines_data(self):
        service = EntityService()
        db = MagicMock()

        primary_id = uuid4()
        other_id = uuid4()

        primary = _make_entity(
            entity_id=primary_id,
            name="Primary",
            canonical_data={"email": "primary@test.com"},
            aliases=["P"],
            source_urls=["url1"],
            tags=["t1"],
        )
        other = _make_entity(
            entity_id=other_id,
            name="Other",
            canonical_data={"phone": "555-0000", "email": "other@test.com"},
            aliases=["O"],
            source_urls=["url2"],
            tags=["t2"],
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        # first() returns primary, all() returns [other]
        mock_query.first.return_value = primary
        mock_query.all.return_value = [other]
        db.query.return_value = mock_query

        result = await service.merge_entities([primary_id, other_id], primary_id, db)

        assert result is primary
        # The other's name should appear in aliases
        assert "Other" in primary.aliases
        # phone should be merged in
        assert primary.canonical_data["phone"] == "555-0000"
        # primary's email should not be overwritten
        assert primary.canonical_data["email"] == "primary@test.com"
        db.delete.assert_called_once_with(other)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_merge_entities_primary_not_found_raises(self):
        service = EntityService()
        db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        db.query.return_value = mock_query

        with pytest.raises(ValueError, match="not found"):
            await service.merge_entities([uuid4()], uuid4(), db)


class TestEntityServiceSearchEntities:
    @pytest.mark.asyncio
    async def test_search_with_query_filter(self):
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()

        entity_a = _make_entity(name="Alice Smith")

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [entity_a]
        db.query.return_value = mock_query

        results = await service.search_entities(user_id, query="Alice", db=db)
        assert len(results) == 1
        assert results[0].name == "Alice Smith"

    @pytest.mark.asyncio
    async def test_search_with_entity_type_filter(self):
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        db.query.return_value = mock_query

        await service.search_entities(user_id, entity_type="company", db=db)
        # filter() should have been called at least twice (user_id + entity_type)
        assert mock_query.filter.call_count >= 2

    @pytest.mark.asyncio
    async def test_search_with_pagination(self):
        service = EntityService()
        db = MagicMock()
        user_id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        db.query.return_value = mock_query

        await service.search_entities(user_id, limit=10, offset=20, db=db)
        mock_query.offset.assert_called_once_with(20)
        mock_query.limit.assert_called_once_with(10)


# =====================================================================
# 8. SourceCache
# =====================================================================


class TestSourceCache:
    def test_make_key_produces_consistent_hash(self):
        cache = SourceCache()
        key1 = cache.make_key("google", "search", {"query": "test"})
        key2 = cache.make_key("google", "search", {"query": "test"})
        assert key1 == key2
        assert key1.startswith("source_cache:")

    def test_make_key_different_params_produce_different_keys(self):
        cache = SourceCache()
        key1 = cache.make_key("google", "search", {"query": "test"})
        key2 = cache.make_key("google", "search", {"query": "other"})
        assert key1 != key2

    def test_make_key_different_providers_produce_different_keys(self):
        cache = SourceCache()
        key1 = cache.make_key("google", "search", {"query": "test"})
        key2 = cache.make_key("exa", "search", {"query": "test"})
        assert key1 != key2

    def test_make_key_format(self):
        cache = SourceCache()
        key = cache.make_key("p", "m", {"k": "v"})
        # Should be "source_cache:" + 16 hex chars
        prefix, hash_part = key.split(":", 1)
        assert prefix == "source_cache"
        assert len(hash_part) == 16

    def test_make_key_sorted_params(self):
        cache = SourceCache()
        key1 = cache.make_key("p", "m", {"a": 1, "b": 2})
        key2 = cache.make_key("p", "m", {"b": 2, "a": 1})
        assert key1 == key2

    @pytest.mark.asyncio
    async def test_get_returns_none_when_unavailable(self):
        cache = SourceCache()
        cache._available = False
        result = await cache.get("some_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_when_no_redis(self):
        cache = SourceCache()
        cache._available = True
        cache._redis = None
        result = await cache.get("some_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_on_cache_miss(self):
        cache = SourceCache()
        cache._available = True
        cache._redis = AsyncMock()
        cache._redis.get = AsyncMock(return_value=None)
        result = await cache.get("missing_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_source_result_on_hit(self):
        cache = SourceCache()
        cache._available = True
        cache._redis = AsyncMock()

        cached_data = {
            "data": [{"name": "cached"}],
            "total_results": 1,
            "source_name": "test_source",
            "source_url": "https://cached.com",
            "metadata": {"from": "cache"},
        }
        cache._redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await cache.get("hit_key")
        assert result is not None
        assert result.cached is True
        assert result.data == [{"name": "cached"}]
        assert result.source_name == "test_source"
        assert result.cost_usd == 0.0

    @pytest.mark.asyncio
    async def test_get_handles_redis_error(self):
        cache = SourceCache()
        cache._available = True
        cache._redis = AsyncMock()
        cache._redis.get = AsyncMock(side_effect=Exception("Redis error"))
        result = await cache.get("error_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_skipped_when_unavailable(self):
        cache = SourceCache()
        cache._available = False
        cache._redis = AsyncMock()
        sr = SourceResult(data=[], raw_response=None, total_results=0, source_name="x")
        await cache.set("key", sr, 60)
        cache._redis.setex.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_set_calls_redis_setex(self):
        cache = SourceCache()
        cache._available = True
        cache._redis = AsyncMock()
        cache._redis.setex = AsyncMock()

        sr = SourceResult(data=[{"v": 1}], raw_response=None, total_results=1, source_name="src")
        await cache.set("the_key", sr, 300)
        cache._redis.setex.assert_awaited_once()
        call_args = cache._redis.setex.call_args
        assert call_args[0][0] == "the_key"
        assert call_args[0][1] == 300

    @pytest.mark.asyncio
    async def test_cached_query_calls_fetch_fn_on_miss(self):
        cache = SourceCache()
        cache._available = True
        cache._redis = AsyncMock()
        cache._redis.get = AsyncMock(return_value=None)
        cache._redis.setex = AsyncMock()

        expected = SourceResult(
            data=[{"fetched": True}],
            raw_response=None,
            total_results=1,
            source_name="fresh",
        )
        fetch_fn = AsyncMock(return_value=expected)

        result = await cache.cached_query("miss_key", 120, fetch_fn)
        fetch_fn.assert_awaited_once()
        assert result is expected
        # Should also set in cache
        cache._redis.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cached_query_returns_cached_on_hit(self):
        cache = SourceCache()
        cache._available = True
        cache._redis = AsyncMock()

        cached_data = {
            "data": [{"cached": True}],
            "total_results": 1,
            "source_name": "cached_source",
        }
        cache._redis.get = AsyncMock(return_value=json.dumps(cached_data))

        fetch_fn = AsyncMock()

        result = await cache.cached_query("hit_key", 120, fetch_fn)
        fetch_fn.assert_not_awaited()  # Should not call fetch_fn
        assert result.cached is True
        assert result.data == [{"cached": True}]

    @pytest.mark.asyncio
    async def test_connect_sets_available_on_success(self):
        cache = SourceCache()
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with (
            patch("app.services.data_sources.cache.settings") as mock_settings,
            patch("app.services.data_sources.cache.aioredis") as mock_aioredis,
        ):
            mock_settings.redis_url = "redis://localhost:6379"
            mock_aioredis.from_url.return_value = mock_redis
            await cache.connect()

        assert cache._available is True
        assert cache._redis is mock_redis

    @pytest.mark.asyncio
    async def test_connect_sets_unavailable_on_failure(self):
        cache = SourceCache()

        with (
            patch("app.services.data_sources.cache.settings") as mock_settings,
            patch("app.services.data_sources.cache.aioredis") as mock_aioredis,
        ):
            mock_settings.redis_url = "redis://localhost:6379"
            mock_aioredis.from_url.side_effect = Exception("connection refused")
            await cache.connect()

        assert cache._available is False
