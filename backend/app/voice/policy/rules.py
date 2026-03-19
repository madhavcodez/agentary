BUSINESS_HOURS = {
    "start": 9,
    "end": 18,
    "timezone": "America/Los_Angeles",
}

FORBIDDEN_TOPICS = [
    "salary negotiation",
    "competitor information",
    "legal matters",
    "medical information",
    "political opinions",
]

PII_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
}

OUTBOUND_LIMITS = {
    "max_daily_calls": 20,
    "min_company_cooldown_hours": 48,
    "max_attempts_per_contact": 3,
}
