"""Built-in workflow templates — 6 system templates seeded on first load."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ...models.workflow_template import WorkflowTemplate

logger = logging.getLogger(__name__)

SYSTEM_TEMPLATES = [
    # ── 1. Real Estate Market Analysis ────────────────────────────────
    {
        "name": "Real Estate Market Analysis",
        "description": "Research local real estate market: search listings, analyze trends, call agents for missing info, generate comprehensive report.",
        "category": "real_estate",
        "tags": ["real_estate", "market_analysis", "research"],
        "variables_schema": [
            {
                "name": "location",
                "type": "string",
                "label": "Location",
                "required": True,
                "description": "City or neighborhood to analyze",
            },
            {
                "name": "price_range",
                "type": "string",
                "label": "Price Range",
                "required": False,
                "default": "$200k-$500k",
                "description": "Target price range",
            },
            {
                "name": "property_type",
                "type": "string",
                "label": "Property Type",
                "required": False,
                "default": "single_family",
                "description": "Type of property",
            },
        ],
        "nodes_template": [
            {
                "id": "t1",
                "type": "manual_trigger",
                "label": "Start",
                "config": {},
                "position": {"x": 250, "y": 0},
            },
            {
                "id": "n1",
                "type": "web_search",
                "label": "Search Listings",
                "config": {
                    "query_template": "{{location}} real estate listings {{price_range}} {{property_type}}",
                    "num_results": 20,
                },
                "position": {"x": 250, "y": 150},
            },
            {
                "id": "n2",
                "type": "web_scrape",
                "label": "Scrape Details",
                "config": {
                    "url_template": "{{url}}",
                    "extract_fields": ["price", "sqft", "beds", "baths", "address"],
                },
                "position": {"x": 250, "y": 300},
            },
            {
                "id": "n3",
                "type": "ai_analyze",
                "label": "Market Analysis",
                "config": {
                    "prompt_template": "Analyze real estate market data for {{location}}. Include price trends, inventory, and recommendations.",
                    "output_format": "json",
                },
                "position": {"x": 250, "y": 450},
            },
            {
                "id": "n4",
                "type": "voice_call",
                "label": "Call Agents",
                "config": {
                    "target_source": "input",
                    "questions": ["What's the current market like?", "Any upcoming listings?"],
                },
                "position": {"x": 500, "y": 450},
            },
            {
                "id": "n5",
                "type": "merge",
                "label": "Combine Data",
                "config": {"strategy": "concat"},
                "position": {"x": 375, "y": 600},
            },
            {
                "id": "n6",
                "type": "generate_report",
                "label": "Final Report",
                "config": {
                    "report_type": "detailed",
                    "sections": [
                        "Market Overview",
                        "Listings",
                        "Price Trends",
                        "Agent Insights",
                        "Recommendations",
                    ],
                },
                "position": {"x": 375, "y": 750},
            },
        ],
        "edges_template": [
            {"source_node_id": "t1", "target_node_id": "n1"},
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
            {"source_node_id": "n2", "target_node_id": "n4"},
            {"source_node_id": "n3", "target_node_id": "n5", "target_port": "input_a"},
            {"source_node_id": "n4", "target_node_id": "n5", "target_port": "input_b"},
            {"source_node_id": "n5", "target_node_id": "n6"},
        ],
    },
    # ── 2. Competitive Intelligence ──────────────────────────────────
    {
        "name": "Competitive Intelligence",
        "description": "Monitor competitors: scrape pricing, features, and reviews, then compare against your product.",
        "category": "competitive_intel",
        "tags": ["competitive", "market_research", "pricing"],
        "variables_schema": [
            {
                "name": "competitor_names",
                "type": "string",
                "label": "Competitor Names",
                "required": True,
                "description": "Comma-separated competitor names",
            },
            {
                "name": "your_product",
                "type": "string",
                "label": "Your Product",
                "required": True,
                "description": "Your product/company name",
            },
        ],
        "nodes_template": [
            {
                "id": "t1",
                "type": "manual_trigger",
                "label": "Start",
                "config": {},
                "position": {"x": 250, "y": 0},
            },
            {
                "id": "n1",
                "type": "web_search",
                "label": "Search Competitors",
                "config": {
                    "query_template": "{{competitor_names}} product pricing features",
                    "num_results": 15,
                },
                "position": {"x": 250, "y": 150},
            },
            {
                "id": "n2",
                "type": "web_scrape",
                "label": "Scrape Pricing",
                "config": {
                    "url_template": "{{url}}",
                    "extract_fields": ["pricing", "plans", "features"],
                },
                "position": {"x": 100, "y": 300},
            },
            {
                "id": "n3",
                "type": "web_search",
                "label": "Search Reviews",
                "config": {
                    "query_template": "{{competitor_names}} reviews ratings",
                    "num_results": 10,
                },
                "position": {"x": 400, "y": 300},
            },
            {
                "id": "n4",
                "type": "merge",
                "label": "Combine Intel",
                "config": {"strategy": "concat"},
                "position": {"x": 250, "y": 450},
            },
            {
                "id": "n5",
                "type": "compare",
                "label": "Compare vs You",
                "config": {
                    "comparison_type": "side_by_side",
                    "metrics": ["pricing", "features", "reviews"],
                },
                "position": {"x": 250, "y": 600},
            },
            {
                "id": "n6",
                "type": "generate_report",
                "label": "Intel Report",
                "config": {
                    "report_type": "comparison",
                    "sections": [
                        "Pricing Comparison",
                        "Feature Matrix",
                        "Review Sentiment",
                        "Strategic Recommendations",
                    ],
                },
                "position": {"x": 250, "y": 750},
            },
        ],
        "edges_template": [
            {"source_node_id": "t1", "target_node_id": "n1"},
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n1", "target_node_id": "n3"},
            {"source_node_id": "n2", "target_node_id": "n4", "target_port": "input_a"},
            {"source_node_id": "n3", "target_node_id": "n4", "target_port": "input_b"},
            {"source_node_id": "n4", "target_node_id": "n5"},
            {"source_node_id": "n5", "target_node_id": "n6"},
        ],
    },
    # ── 3. Local Business Survey ─────────────────────────────────────
    {
        "name": "Local Business Survey",
        "description": "Find local businesses, scrape their info, call for missing details, and compile a comparison report.",
        "category": "local_business",
        "tags": ["local", "business", "survey", "phone_research"],
        "variables_schema": [
            {
                "name": "business_type",
                "type": "string",
                "label": "Business Type",
                "required": True,
                "description": "e.g. 'plumber', 'dentist', 'auto repair'",
            },
            {
                "name": "area",
                "type": "string",
                "label": "Area",
                "required": True,
                "description": "City or neighborhood",
            },
            {
                "name": "questions",
                "type": "string",
                "label": "Questions",
                "required": False,
                "default": "What are your rates? Do you offer free estimates?",
            },
        ],
        "nodes_template": [
            {
                "id": "t1",
                "type": "manual_trigger",
                "label": "Start",
                "config": {},
                "position": {"x": 250, "y": 0},
            },
            {
                "id": "n1",
                "type": "web_search",
                "label": "Find Businesses",
                "config": {
                    "query_template": "{{business_type}} in {{area}}",
                    "num_results": 20,
                    "search_engine": "gemini",
                },
                "position": {"x": 250, "y": 150},
            },
            {
                "id": "n2",
                "type": "web_scrape",
                "label": "Scrape Info",
                "config": {
                    "url_template": "{{url}}",
                    "extract_fields": ["phone", "address", "hours", "reviews"],
                },
                "position": {"x": 250, "y": 300},
            },
            {
                "id": "n3",
                "type": "voice_call",
                "label": "Call for Details",
                "config": {"target_source": "input", "questions": ["{{questions}}"]},
                "position": {"x": 250, "y": 450},
            },
            {
                "id": "n4",
                "type": "ai_analyze",
                "label": "Analyze & Rank",
                "config": {
                    "prompt_template": "Rank these {{business_type}} businesses by value. Consider pricing, reviews, and availability.",
                    "output_format": "json",
                },
                "position": {"x": 250, "y": 600},
            },
            {
                "id": "n5",
                "type": "generate_report",
                "label": "Survey Report",
                "config": {
                    "report_type": "ranking",
                    "sections": [
                        "Top Picks",
                        "Price Comparison",
                        "Review Summary",
                        "Recommendations",
                    ],
                },
                "position": {"x": 250, "y": 750},
            },
        ],
        "edges_template": [
            {"source_node_id": "t1", "target_node_id": "n1"},
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
            {"source_node_id": "n3", "target_node_id": "n4"},
            {"source_node_id": "n4", "target_node_id": "n5"},
        ],
    },
    # ── 4. Due Diligence ─────────────────────────────────────────────
    {
        "name": "Due Diligence",
        "description": "Comprehensive company research: leadership, financials, lawsuits, reviews — synthesized into a diligence report.",
        "category": "due_diligence",
        "tags": ["due_diligence", "company_research", "background_check"],
        "variables_schema": [
            {
                "name": "company_name",
                "type": "string",
                "label": "Company Name",
                "required": True,
                "description": "Company to investigate",
            },
        ],
        "nodes_template": [
            {
                "id": "t1",
                "type": "manual_trigger",
                "label": "Start",
                "config": {},
                "position": {"x": 350, "y": 0},
            },
            {
                "id": "n1",
                "type": "web_search",
                "label": "Company Overview",
                "config": {
                    "query_template": "{{company_name}} company overview about",
                    "num_results": 10,
                },
                "position": {"x": 100, "y": 150},
            },
            {
                "id": "n2",
                "type": "web_search",
                "label": "Leadership",
                "config": {
                    "query_template": "{{company_name}} CEO founders leadership team",
                    "num_results": 10,
                },
                "position": {"x": 300, "y": 150},
            },
            {
                "id": "n3",
                "type": "web_search",
                "label": "Financials",
                "config": {
                    "query_template": "{{company_name}} revenue funding financials",
                    "num_results": 10,
                },
                "position": {"x": 500, "y": 150},
            },
            {
                "id": "n4",
                "type": "web_search",
                "label": "Legal/Lawsuits",
                "config": {
                    "query_template": "{{company_name}} lawsuit legal issues complaints",
                    "num_results": 10,
                },
                "position": {"x": 100, "y": 300},
            },
            {
                "id": "n5",
                "type": "web_search",
                "label": "Reviews",
                "config": {
                    "query_template": "{{company_name}} employee reviews glassdoor",
                    "num_results": 10,
                },
                "position": {"x": 500, "y": 300},
            },
            {
                "id": "n6",
                "type": "ai_analyze",
                "label": "Synthesize",
                "config": {
                    "prompt_template": "Synthesize all research on {{company_name}} into a comprehensive due diligence assessment. Highlight red flags and strengths.",
                    "output_format": "json",
                },
                "position": {"x": 350, "y": 450},
            },
            {
                "id": "n7",
                "type": "generate_report",
                "label": "DD Report",
                "config": {
                    "report_type": "due_diligence",
                    "sections": [
                        "Executive Summary",
                        "Company Overview",
                        "Leadership",
                        "Financial Health",
                        "Legal Issues",
                        "Employee Sentiment",
                        "Risk Assessment",
                        "Recommendation",
                    ],
                },
                "position": {"x": 350, "y": 600},
            },
        ],
        "edges_template": [
            {"source_node_id": "t1", "target_node_id": "n1"},
            {"source_node_id": "t1", "target_node_id": "n2"},
            {"source_node_id": "t1", "target_node_id": "n3"},
            {"source_node_id": "n1", "target_node_id": "n4"},
            {"source_node_id": "n3", "target_node_id": "n5"},
            {"source_node_id": "n1", "target_node_id": "n6"},
            {"source_node_id": "n2", "target_node_id": "n6"},
            {"source_node_id": "n3", "target_node_id": "n6"},
            {"source_node_id": "n4", "target_node_id": "n6"},
            {"source_node_id": "n5", "target_node_id": "n6"},
            {"source_node_id": "n6", "target_node_id": "n7"},
        ],
    },
    # ── 5. Price Monitor ─────────────────────────────────────────────
    {
        "name": "Price Monitor",
        "description": "Daily price monitoring: scrape URLs, compare with previous data, alert on changes.",
        "category": "price_monitoring",
        "tags": ["price_monitoring", "alerts", "scheduled"],
        "variables_schema": [
            {
                "name": "urls",
                "type": "string",
                "label": "URLs to Monitor",
                "required": True,
                "description": "Comma-separated URLs to scrape prices from",
            },
            {
                "name": "frequency",
                "type": "string",
                "label": "Frequency",
                "required": False,
                "default": "daily",
                "description": "How often to check",
            },
        ],
        "nodes_template": [
            {
                "id": "t1",
                "type": "schedule_trigger",
                "label": "Daily Check",
                "config": {"cron": "0 9 * * *", "timezone": "America/Los_Angeles"},
                "position": {"x": 250, "y": 0},
            },
            {
                "id": "n1",
                "type": "web_scrape",
                "label": "Scrape Prices",
                "config": {
                    "url_template": "{{urls}}",
                    "extract_fields": ["price", "name", "availability"],
                },
                "position": {"x": 250, "y": 150},
            },
            {
                "id": "n2",
                "type": "compare",
                "label": "Compare Previous",
                "config": {"comparison_type": "diff"},
                "position": {"x": 250, "y": 300},
            },
            {
                "id": "n3",
                "type": "condition",
                "label": "Price Changed?",
                "config": {"expression": "len(data.get('changes', [])) > 0"},
                "position": {"x": 250, "y": 450},
            },
            {
                "id": "n4",
                "type": "send_alert",
                "label": "Alert",
                "config": {
                    "channel": "email",
                    "message_template": "Price change detected: {{changes}}",
                },
                "position": {"x": 100, "y": 600},
            },
            {
                "id": "n5",
                "type": "save_findings",
                "label": "Save Data",
                "config": {"category": "price_monitoring"},
                "position": {"x": 400, "y": 600},
            },
        ],
        "edges_template": [
            {"source_node_id": "t1", "target_node_id": "n1"},
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
            {"source_node_id": "n3", "target_node_id": "n4", "source_port": "true"},
            {"source_node_id": "n3", "target_node_id": "n5", "source_port": "false"},
        ],
    },
    # ── 6. People Research ───────────────────────────────────────────
    {
        "name": "People Research",
        "description": "Research a person: search across web, social media, and professional profiles, then synthesize a report.",
        "category": "people_research",
        "tags": ["people", "research", "background"],
        "variables_schema": [
            {
                "name": "person_name",
                "type": "string",
                "label": "Person Name",
                "required": True,
                "description": "Full name of person to research",
            },
            {
                "name": "context",
                "type": "string",
                "label": "Context",
                "required": False,
                "default": "",
                "description": "Additional context (company, role, etc.)",
            },
        ],
        "nodes_template": [
            {
                "id": "t1",
                "type": "manual_trigger",
                "label": "Start",
                "config": {},
                "position": {"x": 250, "y": 0},
            },
            {
                "id": "n1",
                "type": "web_search",
                "label": "General Search",
                "config": {"query_template": "{{person_name}} {{context}}", "num_results": 15},
                "position": {"x": 100, "y": 150},
            },
            {
                "id": "n2",
                "type": "web_search",
                "label": "Social Media",
                "config": {
                    "query_template": "{{person_name}} linkedin twitter site:linkedin.com OR site:twitter.com",
                    "num_results": 10,
                },
                "position": {"x": 300, "y": 150},
            },
            {
                "id": "n3",
                "type": "web_search",
                "label": "Professional",
                "config": {
                    "query_template": "{{person_name}} publications research conference speaker",
                    "num_results": 10,
                },
                "position": {"x": 500, "y": 150},
            },
            {
                "id": "n4",
                "type": "merge",
                "label": "Combine",
                "config": {"strategy": "concat"},
                "position": {"x": 250, "y": 300},
            },
            {
                "id": "n5",
                "type": "deduplicate",
                "label": "Dedup",
                "config": {"match_fields": ["url"], "strategy": "exact"},
                "position": {"x": 250, "y": 450},
            },
            {
                "id": "n6",
                "type": "ai_analyze",
                "label": "Synthesize",
                "config": {
                    "prompt_template": "Create a comprehensive profile of {{person_name}}. Include: background, current role, achievements, online presence, and connections.",
                    "output_format": "json",
                },
                "position": {"x": 250, "y": 600},
            },
            {
                "id": "n7",
                "type": "generate_report",
                "label": "Person Report",
                "config": {
                    "report_type": "person_profile",
                    "sections": [
                        "Summary",
                        "Professional Background",
                        "Online Presence",
                        "Publications & Media",
                        "Key Connections",
                    ],
                },
                "position": {"x": 250, "y": 750},
            },
        ],
        "edges_template": [
            {"source_node_id": "t1", "target_node_id": "n1"},
            {"source_node_id": "t1", "target_node_id": "n2"},
            {"source_node_id": "t1", "target_node_id": "n3"},
            {"source_node_id": "n1", "target_node_id": "n4"},
            {"source_node_id": "n2", "target_node_id": "n4"},
            {"source_node_id": "n3", "target_node_id": "n4"},
            {"source_node_id": "n4", "target_node_id": "n5"},
            {"source_node_id": "n5", "target_node_id": "n6"},
            {"source_node_id": "n6", "target_node_id": "n7"},
        ],
    },
]


def seed_templates(db: Session) -> int:
    """Seed system templates if they don't exist. Returns count of templates created."""
    created = 0
    for tmpl_data in SYSTEM_TEMPLATES:
        existing = (
            db.query(WorkflowTemplate)
            .filter(
                WorkflowTemplate.name == tmpl_data["name"], WorkflowTemplate.is_system.is_(True)
            )
            .first()
        )
        if existing:
            continue

        template = WorkflowTemplate(
            name=tmpl_data["name"],
            description=tmpl_data["description"],
            category=tmpl_data["category"],
            tags=tmpl_data["tags"],
            nodes_template=tmpl_data["nodes_template"],
            edges_template=tmpl_data["edges_template"],
            variables_schema=tmpl_data["variables_schema"],
            is_system=True,
            is_public=True,
        )
        db.add(template)
        created += 1

    if created:
        db.commit()
        logger.info("Seeded %d workflow templates", created)
    return created
