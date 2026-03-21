"""Built-in extraction templates for common voice extraction use cases.

These are seeded as VoiceExtraction presets — each template provides a
pre-configured extraction_schema, persona, and objective that users can
clone when creating new voice extractions.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

BUILT_IN_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "Business Info",
        "description": "Extract basic business information: hours, address, services, contact person, website.",
        "category": "business_info",
        "objective": "Gather basic business information through a brief, friendly phone call.",
        "persona": {
            "name": "Alex",
            "role": "Local Business Researcher",
            "tone": "friendly and curious",
            "style": "conversational",
        },
        "extraction_schema": {
            "fields": [
                {"name": "business_hours", "type": "text", "question": "What are your hours of operation?", "required": True},
                {"name": "address", "type": "text", "question": "Can you confirm your address?", "required": True},
                {"name": "services", "type": "list", "question": "What services do you offer?", "required": True},
                {"name": "contact_person", "type": "string", "question": "Who would be the best person to follow up with?", "required": False},
                {"name": "website", "type": "url", "question": "Do you have a website I can check out?", "required": False},
                {"name": "phone_alternative", "type": "phone", "question": "Is there a direct line or cell I could use?", "required": False},
            ]
        },
    },
    {
        "name": "Pricing",
        "description": "Extract pricing information for specific products or services, including bulk discounts.",
        "category": "pricing",
        "objective": "Research current pricing for products or services through a natural inquiry call.",
        "persona": {
            "name": "Jordan",
            "role": "Market Researcher",
            "tone": "professional and straightforward",
            "style": "efficient",
        },
        "extraction_schema": {
            "fields": [
                {"name": "regular_price", "type": "currency", "question": "What's the current price for your standard option?", "required": True},
                {"name": "premium_price", "type": "currency", "question": "Do you have a premium tier? What does that run?", "required": False},
                {"name": "bulk_discount", "type": "text", "question": "Do you offer any volume or bulk discounts?", "required": False},
                {"name": "price_valid_until", "type": "date", "question": "How long are these prices good for?", "required": False},
                {"name": "payment_methods", "type": "list", "question": "What payment methods do you accept?", "required": False},
                {"name": "minimum_order", "type": "text", "question": "Is there a minimum order or purchase amount?", "required": False},
            ]
        },
    },
    {
        "name": "Availability",
        "description": "Check appointment slots, inventory levels, or wait times.",
        "category": "availability",
        "objective": "Determine availability of appointments, products, or services.",
        "persona": {
            "name": "Sam",
            "role": "Scheduling Coordinator",
            "tone": "warm and organized",
            "style": "direct",
        },
        "extraction_schema": {
            "fields": [
                {"name": "next_available", "type": "date", "question": "When is your next available opening?", "required": True},
                {"name": "wait_time", "type": "text", "question": "How long is the typical wait?", "required": True},
                {"name": "slots_open", "type": "integer", "question": "How many openings do you have this week?", "required": False},
                {"name": "booking_required", "type": "boolean", "question": "Do I need to book in advance or can I walk in?", "required": True},
                {"name": "cancellation_policy", "type": "text", "question": "What's your cancellation policy?", "required": False},
            ]
        },
    },
    {
        "name": "Screening",
        "description": "Qualify a person or business against specific criteria (tenant, vendor, candidate).",
        "category": "screening",
        "objective": "Conduct a preliminary screening to qualify against defined criteria.",
        "persona": {
            "name": "Morgan",
            "role": "Screening Coordinator",
            "tone": "professional and empathetic",
            "style": "structured but conversational",
        },
        "extraction_schema": {
            "fields": [
                {"name": "meets_primary_criteria", "type": "boolean", "question": "Can you tell me about your experience/qualifications in this area?", "required": True},
                {"name": "qualifications", "type": "list", "question": "What relevant qualifications or certifications do you have?", "required": True},
                {"name": "deal_breakers", "type": "list", "question": "Are there any constraints or limitations I should know about?", "required": True},
                {"name": "timeline", "type": "text", "question": "What's your availability or timeline?", "required": False},
                {"name": "references", "type": "boolean", "question": "Could you provide references if needed?", "required": False},
                {"name": "follow_up_needed", "type": "boolean", "question": "Would you be open to a more detailed follow-up conversation?", "required": False},
            ]
        },
    },
    {
        "name": "Survey",
        "description": "Conduct opinion surveys with structured responses and sentiment capture.",
        "category": "survey",
        "objective": "Gather opinions and feedback through a brief, respectful survey call.",
        "persona": {
            "name": "Riley",
            "role": "Survey Researcher",
            "tone": "neutral and respectful",
            "style": "structured but friendly",
        },
        "extraction_schema": {
            "fields": [
                {"name": "response_1", "type": "text", "question": "On a scale of 1-10, how would you rate your overall experience?", "required": True},
                {"name": "response_2", "type": "text", "question": "What's the one thing you'd most like to see improved?", "required": True},
                {"name": "response_3", "type": "text", "question": "Would you recommend this to others? Why or why not?", "required": True},
                {"name": "sentiment", "type": "enum", "question": "Overall, how are you feeling about the topic?", "required": False, "options": ["positive", "neutral", "negative", "mixed"]},
                {"name": "additional_comments", "type": "text", "question": "Is there anything else you'd like to share?", "required": False},
                {"name": "willingness_to_follow_up", "type": "boolean", "question": "Would you be willing to participate in a more detailed follow-up?", "required": False},
            ]
        },
    },
    {
        "name": "Custom",
        "description": "Blank template — define your own extraction fields and persona.",
        "category": "custom",
        "objective": "",
        "persona": {
            "name": "Alex",
            "role": "Research Associate",
            "tone": "friendly and professional",
            "style": "conversational",
        },
        "extraction_schema": {
            "fields": []
        },
    },
]


def get_template_by_name(name: str) -> dict[str, Any] | None:
    """Look up a built-in template by name (case-insensitive)."""
    lower = name.lower()
    for template in BUILT_IN_TEMPLATES:
        if template["name"].lower() == lower:
            return dict(template)
    return None


def get_template_by_category(category: str) -> dict[str, Any] | None:
    """Look up a built-in template by category."""
    for template in BUILT_IN_TEMPLATES:
        if template["category"] == category:
            return dict(template)
    return None


def list_templates() -> list[dict[str, Any]]:
    """Return all built-in templates."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "field_count": len(t["extraction_schema"].get("fields", [])),
        }
        for t in BUILT_IN_TEMPLATES
    ]
