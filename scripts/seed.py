"""
Seed script: populates default ExpertAgents, WorkflowTemplates, and Sources.

Usage:
    cd backend && python -m scripts.seed
    # -- or --
    python scripts/seed.py          (from the repo root)

Idempotent: checks by slug / adapter_slug before inserting.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path setup — make sure `app` package is importable regardless of cwd
# ---------------------------------------------------------------------------
_backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

EXPERT_AGENTS = [
    {
        "slug": "web-researcher",
        "name": "Web Researcher",
        "description": "Searches the web for information using multiple search engines and scraping tools",
        "specialty": "web_researcher",
        "system_prompt": (
            "You are a web research specialist. Search thoroughly using multiple sources. "
            "Verify facts across sources. Extract structured data from web pages. "
            "Summarize findings clearly with source citations."
        ),
        "tools": ["exa_search", "web_scrape", "google_search"],
        "icon": "globe",
        "color": "#3B82F6",
        "is_system": True,
    },
    {
        "slug": "data-extractor",
        "name": "Data Extractor",
        "description": "Extracts and structures data from various sources into clean datasets",
        "specialty": "data_extractor",
        "system_prompt": (
            "You are a data extraction specialist. Parse unstructured data into clean, "
            "structured formats. Handle tables, lists, and nested data. Validate data "
            "types and handle missing values."
        ),
        "tools": ["web_scrape", "pdf_parse", "table_extract"],
        "icon": "database",
        "color": "#10B981",
        "is_system": True,
    },
    {
        "slug": "voice-caller",
        "name": "Voice Caller",
        "description": "Makes phone calls to gather information through natural conversation",
        "specialty": "voice_caller",
        "system_prompt": (
            "You are a professional phone researcher. Be polite, professional, and "
            "efficient. Ask clear questions. Handle objections gracefully. Extract the "
            "target information naturally."
        ),
        "tools": ["twilio_call", "speech_to_text", "call_record"],
        "icon": "phone",
        "color": "#8B5CF6",
        "is_system": True,
    },
    {
        "slug": "market-analyst",
        "name": "Market Analyst",
        "description": "Analyzes market conditions, trends, and opportunities",
        "specialty": "market_analyst",
        "system_prompt": (
            "You are a market analysis expert. Identify trends, opportunities, and risks. "
            "Analyze competitive landscapes. Provide data-driven insights with clear "
            "visualizations and recommendations."
        ),
        "tools": ["exa_search", "data_analysis", "chart_gen"],
        "icon": "trending-up",
        "color": "#F59E0B",
        "is_system": True,
    },
    {
        "slug": "financial-analyst",
        "name": "Financial Analyst",
        "description": "Analyzes financial data, valuations, and economic indicators",
        "specialty": "financial_analyst",
        "system_prompt": (
            "You are a financial analysis specialist. Analyze financial statements, "
            "valuations, and economic data. Calculate key metrics and ratios. Provide "
            "clear financial summaries."
        ),
        "tools": ["data_analysis", "financial_calc", "sec_filings"],
        "icon": "dollar-sign",
        "color": "#059669",
        "is_system": True,
    },
    {
        "slug": "real-estate-expert",
        "name": "Real Estate Expert",
        "description": (
            "Specializes in real estate market analysis, property data, and local market intelligence"
        ),
        "specialty": "real_estate_expert",
        "system_prompt": (
            "You are a real estate intelligence expert. Analyze property data, market trends, "
            "permits, and zoning. Pull MLS data, county records, and comparable sales. "
            "Generate property and market reports."
        ),
        "tools": ["mls_search", "county_records", "zillow_api", "web_scrape"],
        "icon": "home",
        "color": "#DC2626",
        "is_system": True,
    },
    {
        "slug": "competitive-intel",
        "name": "Competitive Intelligence",
        "description": "Tracks and analyzes competitor activities, products, and strategies",
        "specialty": "competitive_intel",
        "system_prompt": (
            "You are a competitive intelligence specialist. Monitor competitor websites, "
            "social media, press releases, and job postings. Track pricing changes, feature "
            "launches, and strategic moves. Compile weekly intelligence briefs."
        ),
        "tools": ["exa_search", "web_scrape", "social_monitor", "rss_track"],
        "icon": "eye",
        "color": "#7C3AED",
        "is_system": True,
    },
    {
        "slug": "due-diligence",
        "name": "Due Diligence Analyst",
        "description": "Performs deep research on companies, individuals, and deals",
        "specialty": "due_diligence",
        "system_prompt": (
            "You are a due diligence specialist. Research company backgrounds, financials, "
            "legal history, and reputation. Check regulatory filings, court records, and "
            "news coverage. Flag risks and red flags."
        ),
        "tools": ["exa_search", "sec_filings", "court_records", "news_search"],
        "icon": "shield",
        "color": "#0891B2",
        "is_system": True,
    },
    {
        "slug": "synthesizer",
        "name": "Synthesizer",
        "description": "Combines findings from multiple agents into coherent reports and insights",
        "specialty": "synthesizer",
        "system_prompt": (
            "You are an intelligence synthesizer. Combine findings from multiple research "
            "agents into coherent narratives. Identify patterns, contradictions, and key "
            "insights. Generate executive summaries and detailed reports."
        ),
        "tools": ["report_gen", "chart_gen", "data_merge"],
        "icon": "layers",
        "color": "#EC4899",
        "is_system": True,
    },
    {
        "slug": "local-business-intel",
        "name": "Local Business Intelligence",
        "description": "Gathers data on local businesses through calls, web research, and public records",
        "specialty": "local_business_intel",
        "system_prompt": (
            "You are a local business intelligence specialist. Research local businesses "
            "through web searches, phone calls, and public records. Gather pricing, hours, "
            "services, and contact info. Compile structured datasets."
        ),
        "tools": ["twilio_call", "google_maps", "web_scrape", "yelp_api"],
        "icon": "map-pin",
        "color": "#F97316",
        "is_system": True,
    },
]


def _slugify(name: str) -> str:
    """Convert a display name to a URL-safe slug."""
    return name.lower().replace(" ", "-").replace("&", "and")


WORKFLOW_TEMPLATES = [
    {
        "slug": "real-estate-market-analysis",
        "name": "Real Estate Market Analysis",
        "description": "Comprehensive analysis of a real estate market including comps, permits, and trends",
        "category": "real_estate",
        "is_system": True,
        "nodes": [
            {"id": "1", "type": "source", "label": "Define Market Area", "config": {"input": "area_params"}, "position": {"x": 0, "y": 0}},
            {"id": "2", "type": "research", "label": "Pull MLS Data", "config": {"agent": "real-estate-expert"}, "position": {"x": 200, "y": 0}},
            {"id": "3", "type": "research", "label": "County Records", "config": {"agent": "data-extractor"}, "position": {"x": 200, "y": 100}},
            {"id": "4", "type": "analyze", "label": "Comp Analysis", "config": {"agent": "market-analyst"}, "position": {"x": 400, "y": 50}},
            {"id": "5", "type": "report", "label": "Market Report", "config": {"agent": "synthesizer"}, "position": {"x": 600, "y": 50}},
        ],
        "edges": [
            {"id": "e1", "source_node_id": "1", "target_node_id": "2"},
            {"id": "e2", "source_node_id": "1", "target_node_id": "3"},
            {"id": "e3", "source_node_id": "2", "target_node_id": "4"},
            {"id": "e4", "source_node_id": "3", "target_node_id": "4"},
            {"id": "e5", "source_node_id": "4", "target_node_id": "5"},
        ],
        "variables": {
            "area": {"type": "string", "default": "", "description": "Target area or zip code"},
            "property_type": {"type": "string", "default": "residential", "description": "Property type filter"},
        },
    },
    {
        "slug": "competitive-intel-brief",
        "name": "Competitive Intel Brief",
        "description": "Weekly competitive intelligence briefing on target companies",
        "category": "competitive_intel",
        "is_system": True,
        "nodes": [
            {"id": "1", "type": "source", "label": "Target Companies", "config": {"input": "company_list"}, "position": {"x": 0, "y": 0}},
            {"id": "2", "type": "research", "label": "Web Research", "config": {"agent": "competitive-intel"}, "position": {"x": 200, "y": 0}},
            {"id": "3", "type": "research", "label": "News & Social", "config": {"agent": "web-researcher"}, "position": {"x": 200, "y": 100}},
            {"id": "4", "type": "analyze", "label": "Analysis", "config": {"agent": "market-analyst"}, "position": {"x": 400, "y": 50}},
            {"id": "5", "type": "report", "label": "Intel Brief", "config": {"agent": "synthesizer"}, "position": {"x": 600, "y": 50}},
        ],
        "edges": [
            {"id": "e1", "source_node_id": "1", "target_node_id": "2"},
            {"id": "e2", "source_node_id": "1", "target_node_id": "3"},
            {"id": "e3", "source_node_id": "2", "target_node_id": "4"},
            {"id": "e4", "source_node_id": "3", "target_node_id": "4"},
            {"id": "e5", "source_node_id": "4", "target_node_id": "5"},
        ],
        "variables": {
            "companies": {"type": "list", "default": [], "description": "List of competitor names"},
        },
    },
    {
        "slug": "company-due-diligence",
        "name": "Company Due Diligence",
        "description": "Deep research on a company before a deal -- financials, legal, reputation",
        "category": "due_diligence",
        "is_system": True,
        "nodes": [
            {"id": "1", "type": "source", "label": "Company Input", "config": {"input": "company_name"}, "position": {"x": 0, "y": 50}},
            {"id": "2", "type": "research", "label": "Background Check", "config": {"agent": "due-diligence"}, "position": {"x": 200, "y": 0}},
            {"id": "3", "type": "research", "label": "Financial Analysis", "config": {"agent": "financial-analyst"}, "position": {"x": 200, "y": 100}},
            {"id": "4", "type": "research", "label": "Web Presence", "config": {"agent": "web-researcher"}, "position": {"x": 200, "y": 200}},
            {"id": "5", "type": "analyze", "label": "Risk Assessment", "config": {"agent": "due-diligence"}, "position": {"x": 400, "y": 100}},
            {"id": "6", "type": "report", "label": "DD Report", "config": {"agent": "synthesizer"}, "position": {"x": 600, "y": 100}},
        ],
        "edges": [
            {"id": "e1", "source_node_id": "1", "target_node_id": "2"},
            {"id": "e2", "source_node_id": "1", "target_node_id": "3"},
            {"id": "e3", "source_node_id": "1", "target_node_id": "4"},
            {"id": "e4", "source_node_id": "2", "target_node_id": "5"},
            {"id": "e5", "source_node_id": "3", "target_node_id": "5"},
            {"id": "e6", "source_node_id": "4", "target_node_id": "5"},
            {"id": "e7", "source_node_id": "5", "target_node_id": "6"},
        ],
        "variables": {
            "company": {"type": "string", "default": "", "description": "Company name or domain"},
        },
    },
    {
        "slug": "local-business-data-collection",
        "name": "Local Business Data Collection",
        "description": "Call local businesses to gather specific data points (pricing, hours, availability)",
        "category": "data_extraction",
        "is_system": True,
        "nodes": [
            {"id": "1", "type": "source", "label": "Business List", "config": {"input": "business_targets"}, "position": {"x": 0, "y": 0}},
            {"id": "2", "type": "research", "label": "Web Lookup", "config": {"agent": "local-business-intel"}, "position": {"x": 200, "y": 0}},
            {"id": "3", "type": "voice_call", "label": "Phone Calls", "config": {"agent": "voice-caller"}, "position": {"x": 200, "y": 100}},
            {"id": "4", "type": "transform", "label": "Structure Data", "config": {"agent": "data-extractor"}, "position": {"x": 400, "y": 50}},
            {"id": "5", "type": "report", "label": "Data Report", "config": {"agent": "synthesizer"}, "position": {"x": 600, "y": 50}},
        ],
        "edges": [
            {"id": "e1", "source_node_id": "1", "target_node_id": "2"},
            {"id": "e2", "source_node_id": "1", "target_node_id": "3"},
            {"id": "e3", "source_node_id": "2", "target_node_id": "4"},
            {"id": "e4", "source_node_id": "3", "target_node_id": "4"},
            {"id": "e5", "source_node_id": "4", "target_node_id": "5"},
        ],
        "variables": {
            "business_type": {"type": "string", "default": "", "description": "Type of business to research"},
            "data_fields": {"type": "list", "default": [], "description": "Data points to collect"},
        },
    },
    {
        "slug": "market-gap-analysis",
        "name": "Market Gap Analysis",
        "description": "Analyze market demand signals vs existing supply to find gaps and opportunities",
        "category": "market_research",
        "is_system": True,
        "nodes": [
            {"id": "1", "type": "source", "label": "Market Definition", "config": {"input": "market_params"}, "position": {"x": 0, "y": 50}},
            {"id": "2", "type": "research", "label": "Demand Signals", "config": {"agent": "market-analyst"}, "position": {"x": 200, "y": 0}},
            {"id": "3", "type": "research", "label": "Existing Players", "config": {"agent": "competitive-intel"}, "position": {"x": 200, "y": 100}},
            {"id": "4", "type": "analyze", "label": "Gap Analysis", "config": {"agent": "market-analyst"}, "position": {"x": 400, "y": 50}},
            {"id": "5", "type": "report", "label": "Opportunity Report", "config": {"agent": "synthesizer"}, "position": {"x": 600, "y": 50}},
        ],
        "edges": [
            {"id": "e1", "source_node_id": "1", "target_node_id": "2"},
            {"id": "e2", "source_node_id": "1", "target_node_id": "3"},
            {"id": "e3", "source_node_id": "2", "target_node_id": "4"},
            {"id": "e4", "source_node_id": "3", "target_node_id": "4"},
            {"id": "e5", "source_node_id": "4", "target_node_id": "5"},
        ],
        "variables": {
            "market": {"type": "string", "default": "", "description": "Market or industry to analyze"},
            "geography": {"type": "string", "default": "", "description": "Geographic focus"},
        },
    },
]


DEFAULT_SOURCES = [
    {
        "name": "Gemini Search",
        "source_type": "web_search",
        "adapter_slug": "gemini_search",
        "config": {"model": "gemini-2.5-flash", "grounding": True},
        "is_system": True,
        "is_active": True,
    },
    {
        "name": "Exa Search",
        "source_type": "web_search",
        "adapter_slug": "exa_search",
        "config": {"type": "neural", "num_results": 10},
        "is_system": True,
        "is_active": True,
    },
    {
        "name": "Web Scraper",
        "source_type": "web_scrape",
        "adapter_slug": "web_scraper",
        "config": {"timeout": 30, "js_render": False},
        "is_system": True,
        "is_active": True,
    },
    {
        "name": "Twilio Voice",
        "source_type": "voice",
        "adapter_slug": "twilio_voice",
        "config": {"provider": "twilio", "voice_model": "gemini-live"},
        "is_system": True,
        "is_active": True,
    },
]


# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------


def seed_expert_agents(session) -> int:
    """Insert default ExpertAgents, skipping any that already exist by slug."""
    from app.models.expert_agent import AgentSpecialty, ExpertAgent

    created = 0
    for agent_data in EXPERT_AGENTS:
        existing = session.query(ExpertAgent).filter_by(slug=agent_data["slug"]).first()
        if existing:
            print(f"  [skip] ExpertAgent '{agent_data['slug']}' already exists")
            continue

        agent = ExpertAgent(
            slug=agent_data["slug"],
            name=agent_data["name"],
            description=agent_data["description"],
            specialty=AgentSpecialty(agent_data["specialty"]),
            system_prompt=agent_data["system_prompt"],
            tools=agent_data["tools"],
            icon=agent_data["icon"],
            color=agent_data["color"],
            is_system=agent_data["is_system"],
            is_active=True,
        )
        session.add(agent)
        created += 1
        print(f"  [add]  ExpertAgent '{agent_data['slug']}'")

    return created


def seed_workflow_templates(session) -> int:
    """Insert default WorkflowTemplates, skipping any that already exist by slug."""
    from app.models.workflow_template import WorkflowTemplate

    created = 0
    for tpl_data in WORKFLOW_TEMPLATES:
        existing = session.query(WorkflowTemplate).filter_by(slug=tpl_data["slug"]).first()
        if existing:
            print(f"  [skip] WorkflowTemplate '{tpl_data['slug']}' already exists")
            continue

        tpl = WorkflowTemplate(
            slug=tpl_data["slug"],
            name=tpl_data["name"],
            description=tpl_data["description"],
            category=tpl_data["category"],
            nodes=tpl_data["nodes"],
            edges=tpl_data["edges"],
            variables=tpl_data["variables"],
            is_system=tpl_data["is_system"],
            is_active=True,
        )
        session.add(tpl)
        created += 1
        print(f"  [add]  WorkflowTemplate '{tpl_data['slug']}'")

    return created


def seed_sources(session) -> int:
    """Insert default Sources, skipping any that already exist by adapter_slug."""
    from app.models.source import Source, SourceKind

    created = 0
    for src_data in DEFAULT_SOURCES:
        existing = session.query(Source).filter_by(adapter_slug=src_data["adapter_slug"]).first()
        if existing:
            print(f"  [skip] Source '{src_data['adapter_slug']}' already exists")
            continue

        source = Source(
            name=src_data["name"],
            source_type=SourceKind(src_data["source_type"]),
            adapter_slug=src_data["adapter_slug"],
            config=src_data["config"],
            is_system=src_data["is_system"],
            is_active=src_data["is_active"],
        )
        session.add(source)
        created += 1
        print(f"  [add]  Source '{src_data['adapter_slug']}'")

    return created


def main() -> None:
    from app.database import SessionLocal, init_db

    print("=== Initializing database ===")
    init_db()

    session = SessionLocal()
    try:
        print("\n--- Seeding ExpertAgents (10) ---")
        agents_created = seed_expert_agents(session)

        print("\n--- Seeding WorkflowTemplates (5) ---")
        templates_created = seed_workflow_templates(session)

        print("\n--- Seeding Sources (4) ---")
        sources_created = seed_sources(session)

        session.commit()

        print("\n=== Seed complete ===")
        print(f"  ExpertAgents:      {agents_created} created")
        print(f"  WorkflowTemplates: {templates_created} created")
        print(f"  Sources:           {sources_created} created")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
