# AGENT 5 — Data Sources & External Connectors

## YOUR MISSION

You are a coding agent. Build the **pluggable data source connector system** — the adapter layer connecting Agentary to external APIs, web scrapers, databases, and services. Every expert agent and workflow node depends on these connectors to fetch real-world data.

**Start:** `/plan Read this entire file, explore existing connectors (Exa, Gemini Search), then build everything.`

---

## WHAT YOU'RE BUILDING

A standardized connector system where each data source has the same interface. Expert agents and workflow nodes call the SourceRegistry, which routes to the appropriate connector, which calls the external service, normalizes the response, and returns structured data.

```
ExpertAgent / WorkflowNode
    → SourceRegistry.query("google_places", {query: "gas stations Austin"})
        → GooglePlacesConnector.search(query="gas stations Austin")
            → Google Places API HTTP call
            → Parse response
            → Normalize to SourceResult format
        ← SourceResult {data: [...], source_name, cost_usd, cached}
```

---

## MODELS

### data_source.py
Fields: id (UUID PK), user_id (FK users nullable — null=system), name (str 255), slug (str 100 unique), source_type (str: api|scraper|database|file|voice|manual), provider (str: gemini_search|exa|google_places|zillow|redfin|county_records|yelp|crunchbase|builtwith|custom_api|custom_scraper), description (Text), config (JSONB — provider-specific: base_url, endpoints, params), auth_config (JSONB — encrypted API keys/tokens), rate_limit (JSONB: {requests_per_minute, requests_per_day, concurrent_max}), cost_per_request (Float nullable), is_system (Bool), is_active (Bool), health_status (str: healthy|degraded|down|unknown), last_health_check (DateTime), total_requests (Int default 0), total_cost_usd (Float default 0.0), created_at, updated_at.

### source_request_log.py
Fields: id (UUID PK), data_source_id (FK data_sources), mission_id (FK missions nullable), crew_task_id (FK crew_tasks nullable), request_type (str), request_params (JSONB), response_status (Int), response_preview (Text — first 500 chars), duration_ms (Int), cost_usd (Float nullable), error (Text nullable), created_at. Index on (data_source_id, created_at).

### entity.py
Fields: id (UUID PK), user_id (FK users), entity_type (str: person|company|property|location|business|product|other), name (str 500), description (Text nullable), canonical_data (JSONB — type-specific structured data, e.g. for property: {address, city, state, zip, beds, baths, sqft, price, year_built}; for business: {name, address, phone, hours, website, rating, category}; for person: {full_name, email, phone, linkedin, title, company}; for company: {name, domain, industry, size, location, founded, funding}), aliases (ARRAY String), source_urls (ARRAY Text), tags (ARRAY String), created_at, updated_at. Index on (entity_type, name).

### entity_collection.py
Fields: id (UUID PK), project_id (FK projects), user_id (FK users), name (str 255), description (Text), entity_type (str), entity_ids (ARRAY UUID), filters (JSONB nullable — dynamic filter criteria), count (Int default 0), created_at, updated_at.

---

## CONNECTOR INTERFACE

```python
# backend/app/services/data_sources/base_connector.py
from dataclasses import dataclass, field
from typing import Any, Protocol

@dataclass
class SourceResult:
    data: list[dict]          # Normalized results
    raw_response: Any         # Raw API response (for debugging)
    total_results: int
    source_name: str
    source_url: str | None = None
    cost_usd: float = 0.0
    cached: bool = False
    metadata: dict = field(default_factory=dict)

class SourceConnector(Protocol):
    name: str
    provider: str
    description: str

    async def search(self, query: str, **kwargs) -> SourceResult:
        """Search/query the source."""
        ...

    async def get(self, identifier: str, **kwargs) -> SourceResult:
        """Get a specific record by ID/URL."""
        ...

    async def health_check(self) -> dict:
        """Returns {status: healthy|degraded|down, latency_ms, message}"""
        ...

    def get_tool_definition(self) -> dict:
        """Return Gemini function-calling compatible tool definition."""
        ...
```

---

## 10 CONNECTORS TO BUILD

### 1. gemini_search_connector.py (EXISTING — wrap)
Wrap existing Gemini search grounding code. Tool def: `gemini_search(query, num_results)`. Returns web pages with snippets.

### 2. exa_connector.py (EXISTING — wrap)
Wrap existing Exa API code. Tool def: `exa_search(query, num_results, type: keyword|neural|auto)`. Returns semantically relevant pages.

### 3. google_places_connector.py (NEW — high priority)
Google Places API (or Google Maps scraping fallback). 

**search(query, location, radius_meters, type)** → Returns: name, address, phone, rating, review_count, hours (JSONB), website, lat, lng, place_id, price_level, categories.

**get(place_id)** → Full details including reviews.

**get_reviews(place_id, max_reviews)** → Review text + rating for sentiment analysis.

Tool definition:
```json
{
    "name": "google_places",
    "description": "Search for local businesses and places. Returns names, addresses, phone numbers, hours, ratings, reviews.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query, e.g. 'gas stations near Austin TX'"},
            "location": {"type": "string", "description": "Center point 'lat,lng' or address"},
            "radius_meters": {"type": "integer", "default": 5000},
            "type": {"type": "string", "description": "Place type: gas_station, restaurant, real_estate_agency, etc."}
        },
        "required": ["query"]
    }
}
```

If GOOGLE_PLACES_API_KEY is not set, fall back to scraping Google Maps or return mock data with a warning.

### 4. web_scraper_connector.py (NEW — high priority)
Fetch any URL, extract structured data. Uses httpx + BeautifulSoup + optionally Gemini for AI extraction.

**get(url, extract_type, extract_fields)** — extract_type options:
- `"auto"` — AI determines what to extract
- `"text"` — all text content
- `"tables"` — HTML tables as structured data
- `"selectors"` — CSS selectors for specific elements
- `"ai_extract"` — pass extract_fields=[{name, description}], Gemini extracts those specific fields from page content

**search(query, urls)** — scrape multiple URLs, search within content.

Tool definition: `web_scraper(url, extract_fields?)`. This is heavily used by WebResearcher and PropertyResearcher experts.

Implementation notes:
- Use httpx with reasonable timeout (30s)
- Respect robots.txt (check before scraping)
- Parse with BeautifulSoup4
- For AI extraction: send page text to Gemini with extraction instructions
- Cache results for 1 hour in Redis
- Handle common errors: 403, 429, timeout, SSL, encoding

### 5. zillow_connector.py (NEW)
Real estate data. Use Zillow's API if available, or scrape search pages, or use RapidAPI Zillow endpoint.

**search(location, price_min, price_max, beds_min, property_type, status)** → Returns: address, price, beds, baths, sqft, lot_size, year_built, status (for_sale|sold|pending), days_on_market, price_per_sqft, url, images_count, listing_agent.

**get(zpid_or_url)** → Full detail: price history, tax history, zestimate, nearby schools, walkability.

**get_comps(address_or_zpid, radius_miles)** → Comparable sales/listings nearby.

Tool definition: `zillow_search(location, price_min?, price_max?, beds_min?, property_type?)`.

### 6. county_records_connector.py (NEW)
Property records from county assessor websites. This is scraping-heavy.

**search(address, county, state)** → Returns: owner_name, assessed_value, tax_amount, parcel_number, deed_date, last_sale_price, legal_description, zoning, lot_size_acres.

**get_permits(address, county, state)** → Building permits: permit_type, date, description, status, contractor, value.

For MVP: support 10 major metro counties (Travis/TX, Maricopa/AZ, Los Angeles/CA, Cook/IL, Harris/TX, Miami-Dade/FL, King/WA, Clark/NV, Fulton/GA, Denver/CO). Each county has a different website format, so create per-county scrapers.

Tool definition: `county_records(address, county?, state?)`.

### 7. yelp_connector.py (NEW)
Yelp Fusion API (or scraping fallback).

**search(term, location, radius, categories, price, sort_by)** → Returns: name, rating, review_count, price_level ($$), phone, address, categories, url, distance, is_open.

**get(business_id)** → Full detail with hours, photos count, specialties.

**get_reviews(business_id, limit)** → Reviews with text, rating, date for sentiment analysis.

Tool definition: `yelp_search(term, location, radius?, categories?)`.

### 8. crunchbase_connector.py (NEW)
Company data. Use Crunchbase API if key available, or scrape, or use RapidAPI.

**search(query, industry, location, funding_min)** → Returns: name, description, funding_total, last_funding_date, funding_rounds, employee_count, industry, hq_location, website, founded_year.

**get(company_slug)** → Full profile: leadership team, funding rounds, acquisitions, competitors, recent news.

Tool definition: `crunchbase_search(query, industry?, location?)`.

### 9. custom_api_connector.py (NEW — user-configurable)
Lets users connect any REST API without code. Config-driven:
```json
{
    "base_url": "https://api.example.com",
    "auth_type": "bearer|api_key_header|api_key_param|basic|none",
    "auth_config": {"header": "Authorization", "prefix": "Bearer", "key": "..."},
    "search_endpoint": "/search",
    "search_method": "GET",
    "search_params_map": {"query": "q", "limit": "per_page"},
    "result_path": "data.items",
    "field_map": {"name": "title", "description": "body", "url": "link"}
}
```

**search(query, **kwargs)** → Calls configured endpoint, extracts results via result_path, maps fields.

**get(identifier)** → Calls detail endpoint if configured.

Tool definition: dynamically generated from config.

### 10. python_executor_connector.py (NEW — sandboxed code execution)
Execute Python code for data analysis. Used by DataAnalyst expert.

**execute(code, input_data, timeout=30)** → Run code in subprocess with:
- Available: pandas, numpy, statistics, json, math, datetime, collections
- `input_data` available as variable `data`
- Code must assign result to variable `result`
- Timeout: 30 seconds
- Memory limit: 256MB
- NO network access, NO filesystem (except /tmp)
- Capture stdout/stderr

Tool definition: `python_executor(code, description)`.

Implementation:
```python
async def execute(self, code: str, input_data: dict = None, timeout: int = 30):
    wrapper = f"""
import json, math, statistics, datetime, collections
from collections import Counter, defaultdict
try:
    import pandas as pd
    import numpy as np
except ImportError:
    pass

data = json.loads('''{json.dumps(input_data or {})}''')
result = None

{code}

print(json.dumps({{"result": result}}, default=str))
"""
    proc = await asyncio.create_subprocess_exec(
        "python3", "-c", wrapper,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = json.loads(stdout.decode())
        return SourceResult(data=[output["result"]], raw_response={"stdout": stdout.decode(), "stderr": stderr.decode()}, ...)
    except asyncio.TimeoutError:
        proc.kill()
        raise
```

---

## SOURCE REGISTRY

```python
# backend/app/services/data_sources/source_registry.py

class SourceRegistry:
    def __init__(self):
        self._connectors: dict[str, SourceConnector] = {}

    def register(self, connector: SourceConnector):
        self._connectors[connector.provider] = connector

    def get(self, provider: str) -> SourceConnector | None:
        return self._connectors.get(provider)

    def list_available(self) -> list[dict]:
        return [{"provider": c.provider, "name": c.name, "description": c.description} for c in self._connectors.values()]

    def get_tool_definitions(self, providers: list[str] = None) -> list[dict]:
        """Get Gemini function-calling tool definitions. If providers=None, return all."""
        targets = providers or list(self._connectors.keys())
        return [self._connectors[p].get_tool_definition() for p in targets if p in self._connectors]

    async def query(self, provider: str, method: str = "search", **kwargs) -> SourceResult:
        """Convenience: query a source by provider name."""
        connector = self.get(provider)
        if not connector:
            raise ValueError(f"Unknown provider: {provider}")
        fn = getattr(connector, method)
        return await fn(**kwargs)

    async def health_check_all(self) -> dict[str, dict]:
        results = {}
        for provider, connector in self._connectors.items():
            try:
                results[provider] = await connector.health_check()
            except Exception as e:
                results[provider] = {"status": "down", "message": str(e)}
        return results

def create_source_registry(settings) -> SourceRegistry:
    """Factory function called on app startup."""
    registry = SourceRegistry()
    # Always available (no API key needed)
    registry.register(WebScraperConnector())
    registry.register(PythonExecutorConnector())
    # Require API keys
    if getattr(settings, "GEMINI_API_KEY", None):
        registry.register(GeminiSearchConnector(settings.GEMINI_API_KEY))
    if getattr(settings, "EXA_API_KEY", None):
        registry.register(ExaConnector(settings.EXA_API_KEY))
    if getattr(settings, "GOOGLE_PLACES_API_KEY", None):
        registry.register(GooglePlacesConnector(settings.GOOGLE_PLACES_API_KEY))
    if getattr(settings, "ZILLOW_API_KEY", None):
        registry.register(ZillowConnector(settings.ZILLOW_API_KEY))
    if getattr(settings, "YELP_API_KEY", None):
        registry.register(YelpConnector(settings.YELP_API_KEY))
    if getattr(settings, "CRUNCHBASE_API_KEY", None):
        registry.register(CrunchbaseConnector(settings.CRUNCHBASE_API_KEY))
    return registry
```

Make the registry available as a FastAPI dependency and pass it to CrewRunner / WorkflowExecutor.

---

## ENTITY SERVICE

```python
# backend/app/services/entities/entity_service.py

class EntityService:
    async def create_entity(self, data: EntityCreate, db) -> Entity:
        """Create a new entity."""

    async def find_or_create(self, entity_type: str, identifiers: dict, db) -> Entity:
        """
        Dedup: find existing entity by matching identifiers, or create new.
        Match logic:
        - person: email OR (name + company)
        - company: domain OR name
        - property: address (normalized)
        - business: phone OR (name + address)
        - location: (lat, lng) within 100m OR name
        """

    async def update_entity(self, entity_id: UUID, data: dict, db) -> Entity:
        """Merge new data into canonical_data (don't overwrite, merge)."""

    async def merge_entities(self, entity_ids: list[UUID], primary_id: UUID, db) -> Entity:
        """Merge duplicates into one. Combine canonical_data, aliases, source_urls."""

    async def search_entities(self, query: str, entity_type: str = None, project_id: UUID = None, db=None) -> list[Entity]:
        """Full-text search + optional Qdrant vector search on entity descriptions."""

    async def create_collection(self, project_id: UUID, user_id: UUID, data: dict, db) -> EntityCollection:
        """Create an entity collection (group of entities for a project)."""

    async def add_to_collection(self, collection_id: UUID, entity_ids: list[UUID], db):
        """Add entities to a collection."""
```

---

## API ROUTES

### `/api/data-sources`
- GET / — list available sources (system + user-created) with health status
- GET /{id} — detail with usage stats
- POST / — create custom API source (uses custom_api_connector config)
- PUT /{id} — update config
- DELETE /{id} — remove
- POST /{id}/test — test connection, return sample result
- GET /{id}/health — health check
- POST /{id}/query — manually query (for testing/debugging)

### `/api/entities`
- POST / — create entity
- GET / — list entities (filter by type, project, search query)
- GET /{id} — entity detail with canonical_data
- PUT /{id} — update entity data
- POST /merge — merge duplicates {entity_ids, primary_id}
- GET /search?q=...&type=... — search

### `/api/entity-collections`
- POST / — create collection
- GET / — list for project
- GET /{id} — collection detail with entities
- POST /{id}/add — add entities
- POST /{id}/remove — remove entities
- GET /{id}/export/csv — export collection

---

## ENVIRONMENT VARIABLES

Add to .env.example:
```bash
# Data Source API Keys (all optional — connectors gracefully skip if missing)
GOOGLE_PLACES_API_KEY=
ZILLOW_API_KEY=          # or RAPIDAPI_KEY for Zillow via RapidAPI
YELP_API_KEY=
CRUNCHBASE_API_KEY=
# Already existing:
# EXA_API_KEY=
# GEMINI_API_KEY=
```

---

## CACHING

Implement Redis caching for expensive queries:
- Google Places results: cache 24h (keyed on query + location + radius)
- Web scraper results: cache 1h (keyed on URL)
- Zillow search: cache 4h
- Yelp search: cache 12h
- County records: cache 24h

```python
async def cached_query(self, cache_key: str, ttl: int, fetch_fn):
    cached = await redis.get(f"source_cache:{cache_key}")
    if cached:
        return SourceResult(**json.loads(cached), cached=True)
    result = await fetch_fn()
    await redis.setex(f"source_cache:{cache_key}", ttl, result.to_json())
    return result
```

---

## SUCCESS CRITERIA (Agent 7 Checks)

- [ ] DataSource and SourceRequestLog models with migrations
- [ ] Entity and EntityCollection models with migrations
- [ ] SourceConnector protocol defined in base_connector.py
- [ ] SourceRegistry with register, get, list, get_tool_definitions, query, health_check_all
- [ ] 10 connectors: gemini_search, exa, google_places, web_scraper, zillow, county_records, yelp, crunchbase, custom_api, python_executor
- [ ] Each connector has get_tool_definition() returning valid Gemini function-calling schema
- [ ] Each connector normalizes to SourceResult
- [ ] Web scraper handles: text, tables, CSS selectors, AI extraction
- [ ] Python executor is sandboxed with timeout
- [ ] Custom API connector is user-configurable via JSON config
- [ ] Health check system
- [ ] Redis caching for expensive queries
- [ ] Source request logging for cost/usage tracking
- [ ] EntityService with create, find_or_create, merge, search
- [ ] API routes for data-sources, entities, entity-collections
- [ ] Graceful degradation when API keys missing (log warning, skip connector)
- [ ] docs/PHASE_5_PROGRESS.md updated
