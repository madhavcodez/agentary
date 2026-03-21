"""User-configurable REST API connector.

Driven entirely by a JSON config dict that specifies the target API's
base URL, authentication, endpoints, and field mappings. Allows users to
plug in arbitrary REST data sources without writing code.
"""

from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from ..base_connector import SourceResult


def _traverse(obj: Any, path: str) -> Any:
    """Resolve a dot-notation path against a nested dict/list.

    Example: _traverse({"data": {"items": [1, 2]}}, "data.items") -> [1, 2]
    """
    current = obj
    for segment in path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, list) and segment.isdigit():
            idx = int(segment)
            current = current[idx] if idx < len(current) else None
        else:
            return None
    return current


class CustomApiConnector:
    """Config-driven connector for arbitrary REST APIs.

    Expected *config* keys:

    - ``name`` (str, optional): Human-readable name.
    - ``base_url`` (str): API root URL.
    - ``auth_type`` (str): One of ``bearer``, ``api_key_header``,
      ``api_key_param``, ``basic``, ``none``.
    - ``auth_config`` (dict): Auth-type-specific values.
      - *bearer*: ``{"token": "..."}``
      - *api_key_header*: ``{"header": "X-Api-Key", "key": "..."}``
      - *api_key_param*: ``{"param": "api_key", "key": "..."}``
      - *basic*: ``{"username": "...", "password": "..."}``
    - ``search_endpoint`` (str): Path appended to *base_url*.
    - ``search_method`` (str): HTTP method (GET or POST).
    - ``search_params_map`` (dict): Maps ``query``/``**kwargs`` keys to
      the API's expected parameter names.
    - ``detail_endpoint`` (str, optional): e.g. ``"/items/{id}"``.
    - ``result_path`` (str): Dot-notation path into the JSON response
      to reach the list of results (e.g. ``"data.items"``).
    - ``field_map`` (dict): Maps API field names to normalized output
      names.
    """

    provider: str = "custom_api"
    description: str = "User-configurable REST API data source."

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = dict(config)  # shallow copy — no mutation of caller's dict
        self.name: str = config.get("name", "Custom API")

        self._base_url = config["base_url"].rstrip("/")
        self._auth_type = config.get("auth_type", "none")
        self._auth_config = config.get("auth_config", {})
        self._search_endpoint = config.get("search_endpoint", "")
        self._search_method = config.get("search_method", "GET").upper()
        self._search_params_map = config.get("search_params_map", {})
        self._detail_endpoint = config.get("detail_endpoint")
        self._result_path = config.get("result_path", "")
        self._field_map = config.get("field_map", {})

        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._build_auth_headers(),
        )

    # ------------------------------------------------------------------
    # auth helpers
    # ------------------------------------------------------------------

    def _build_auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._auth_type == "bearer":
            token = self._auth_config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
        elif self._auth_type == "api_key_header":
            header_name = self._auth_config.get("header", "X-Api-Key")
            headers[header_name] = self._auth_config.get("key", "")
        elif self._auth_type == "basic":
            username = self._auth_config.get("username", "")
            password = self._auth_config.get("password", "")
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        return headers

    def _build_auth_params(self) -> dict[str, str]:
        if self._auth_type == "api_key_param":
            param_name = self._auth_config.get("param", "api_key")
            return {param_name: self._auth_config.get("key", "")}
        return {}

    # ------------------------------------------------------------------
    # field mapping
    # ------------------------------------------------------------------

    def _map_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        if not self._field_map:
            return dict(raw)
        mapped: dict[str, Any] = {}
        for api_field, output_field in self._field_map.items():
            value = _traverse(raw, api_field)
            if value is not None:
                mapped[output_field] = value
        return mapped

    # ------------------------------------------------------------------
    # core interface
    # ------------------------------------------------------------------

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        url = f"{self._base_url}{self._search_endpoint}"

        # Build request params/body from the params map
        mapped_params: dict[str, Any] = {}
        for source_key, api_key in self._search_params_map.items():
            if source_key == "query":
                mapped_params[api_key] = query
            elif source_key in kwargs:
                mapped_params[api_key] = kwargs[source_key]

        mapped_params.update(self._build_auth_params())

        if self._search_method == "POST":
            response = await self._client.post(url, json=mapped_params)
        else:
            response = await self._client.get(url, params=mapped_params)

        response.raise_for_status()
        body = response.json()

        # Extract results via dot-notation path
        raw_results = _traverse(body, self._result_path) if self._result_path else body
        if raw_results is None:
            raw_results = []
        if isinstance(raw_results, dict):
            raw_results = [raw_results]

        records = [self._map_record(r) for r in raw_results]

        return SourceResult(
            data=records,
            raw_response=body,
            total_results=len(records),
            source_name=self.name,
            source_url=url,
        )

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        if self._detail_endpoint is None:
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"message": "No detail endpoint configured"},
            )

        path = self._detail_endpoint.replace("{id}", identifier)
        url = f"{self._base_url}{path}"

        params = self._build_auth_params()
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        body = response.json()

        raw_result = _traverse(body, self._result_path) if self._result_path else body
        if isinstance(raw_result, list):
            records = [self._map_record(r) for r in raw_result]
        elif isinstance(raw_result, dict):
            records = [self._map_record(raw_result)]
        else:
            records = []

        return SourceResult(
            data=records,
            raw_response=body,
            total_results=len(records),
            source_name=self.name,
            source_url=url,
        )

    async def health_check(self) -> dict[str, Any]:
        start = time.monotonic()
        try:
            response = await self._client.head(self._base_url)
            latency_ms = round((time.monotonic() - start) * 1_000, 1)
            if response.status_code < 400:
                return {"status": "healthy", "latency_ms": latency_ms, "message": "OK"}
            return {
                "status": "degraded",
                "latency_ms": latency_ms,
                "message": f"HTTP {response.status_code}",
            }
        except Exception as exc:
            latency_ms = round((time.monotonic() - start) * 1_000, 1)
            return {"status": "down", "latency_ms": latency_ms, "message": str(exc)}

    def get_tool_definition(self) -> dict[str, Any]:
        """Dynamically generate a tool definition from the config."""
        properties: dict[str, Any] = {
            "query": {
                "type": "string",
                "description": f"Search query for {self.name}",
            },
        }
        # Expose any extra params from the search_params_map as tool params
        for source_key in self._search_params_map:
            if source_key != "query":
                properties[source_key] = {
                    "type": "string",
                    "description": f"Filter by {source_key}",
                }

        return {
            "name": f"custom_api_{self.name.lower().replace(' ', '_')}",
            "description": f"Search {self.name} via custom API connector.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": ["query"],
            },
        }
