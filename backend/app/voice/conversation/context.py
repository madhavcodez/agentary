from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CallMetadata:
    call_id: str = ""
    caller_number: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    direction: str = "inbound"
