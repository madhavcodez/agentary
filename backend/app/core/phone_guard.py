"""E.164 phone-number validation and abuse-prevention guard.

Prompt-injected research objectives can convince an LLM to invoke
``voice_caller`` against arbitrary numbers — international premium-rate
lines, emergency services, or do-not-call recipients. Validating at the
tool boundary keeps the LLM's outputs from triggering TCPA violations or
unexpected costs.

What this guards
- Numbers must parse as valid E.164 via ``phonenumbers``
- Country must be in ``ALLOWED_COUNTRY_CODES`` (US/CA by default)
- Number type must be in ``ALLOWED_NUMBER_TYPES`` — premium-rate, shared-
  cost, voicemail, pager, and "service" lines are rejected
- US-specific premium prefixes (1-900, 1-976, 1-809) are denied explicitly
  in case ``phonenumbers`` mis-classifies them in some build
- Emergency numbers (911 family) are denied

Operators can override the lists by setting environment variables (parsed
in ``config.py``) before this module is used — none of these defaults are
load-bearing for tests.
"""
from __future__ import annotations

from typing import Final

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType

ALLOWED_COUNTRY_CODES: Final[frozenset[str]] = frozenset({"US", "CA"})

ALLOWED_NUMBER_TYPES: Final[frozenset[int]] = frozenset(
    {
        PhoneNumberType.FIXED_LINE,
        PhoneNumberType.MOBILE,
        PhoneNumberType.FIXED_LINE_OR_MOBILE,
        PhoneNumberType.TOLL_FREE,
        PhoneNumberType.VOIP,
    }
)

# US premium-rate prefixes (matched against the national significant number)
_BLOCKED_US_PREFIXES: Final[tuple[str, ...]] = (
    "900",  # premium rate
    "976",  # premium rate (some carriers)
    "809",  # often used for premium-rate scams from Caribbean
)

# Emergency / service short codes
_BLOCKED_SHORT_NUMBERS: Final[frozenset[str]] = frozenset(
    {"911", "112", "211", "311", "411", "511", "611", "711", "811"}
)


class PhoneNumberRejected(ValueError):
    """The supplied number is not allowed for outbound calling."""


def validate_outbound_number(raw: str) -> str:
    """Validate a phone number and return its canonical E.164 form.

    Raises ``PhoneNumberRejected`` with an operator-meaningful reason on
    failure. The reason is safe to surface to the LLM tool result so it
    can self-correct.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise PhoneNumberRejected("Phone number is required")

    stripped = raw.strip()
    if stripped in _BLOCKED_SHORT_NUMBERS:
        raise PhoneNumberRejected(f"Short number {stripped} is reserved")

    try:
        parsed = phonenumbers.parse(stripped, None)
    except NumberParseException as exc:
        raise PhoneNumberRejected(
            f"Could not parse as E.164: {exc.error_type.name if hasattr(exc.error_type, 'name') else exc}"
        ) from exc

    if not phonenumbers.is_valid_number(parsed):
        raise PhoneNumberRejected("Number is not a valid E.164 number")

    region = phonenumbers.region_code_for_number(parsed) or ""
    if region not in ALLOWED_COUNTRY_CODES:
        raise PhoneNumberRejected(
            f"Calls to region {region!r} are not allowed (allowed: "
            f"{sorted(ALLOWED_COUNTRY_CODES)})"
        )

    number_type = phonenumbers.number_type(parsed)
    if number_type not in ALLOWED_NUMBER_TYPES:
        raise PhoneNumberRejected(
            f"Number type {number_type} is not permitted for outbound calls"
        )

    national = phonenumbers.national_significant_number(parsed)
    if region == "US" and any(national.startswith(p) for p in _BLOCKED_US_PREFIXES):
        raise PhoneNumberRejected(
            f"Premium-rate prefix +1-{national[:3]} is denied"
        )

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
