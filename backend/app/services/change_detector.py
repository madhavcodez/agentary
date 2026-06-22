"""Change detection utilities for monitor snapshots."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChangeResult:
    changed: bool
    change_type: str
    summary: str
    details: dict[str, Any]


def detect_text_change(old_text: str | None, new_text: str | None) -> ChangeResult:
    """Compare two text snapshots and return a unified diff."""
    old = (old_text or "").splitlines(keepends=True)
    new = (new_text or "").splitlines(keepends=True)

    diff = list(difflib.unified_diff(old, new, lineterm=""))
    if not diff:
        return ChangeResult(changed=False, change_type="text", summary="No change", details={})

    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

    return ChangeResult(
        changed=True,
        change_type="text",
        summary=f"{added} lines added, {removed} lines removed",
        details={
            "diff": "".join(diff[:100]),
            "added_lines": added,
            "removed_lines": removed,
        },
    )


def detect_value_change(
    old_val: float | int | None,
    new_val: float | int | None,
    threshold: float = 0.0,
) -> ChangeResult:
    """Compare two numeric values, optionally with a threshold."""
    if old_val is None and new_val is None:
        return ChangeResult(changed=False, change_type="value", summary="No change", details={})

    if old_val is None or new_val is None:
        return ChangeResult(
            changed=True,
            change_type="value",
            summary=f"Value changed from {old_val} to {new_val}",
            details={"old_value": old_val, "new_value": new_val},
        )

    diff = new_val - old_val
    pct = (diff / old_val * 100) if old_val != 0 else float("inf")

    if abs(diff) <= threshold:
        return ChangeResult(
            changed=False, change_type="value", summary="Within threshold", details={}
        )

    direction = "increased" if diff > 0 else "decreased"
    return ChangeResult(
        changed=True,
        change_type="value",
        summary=f"Value {direction} from {old_val} to {new_val} ({pct:+.1f}%)",
        details={
            "old_value": old_val,
            "new_value": new_val,
            "difference": diff,
            "percentage_change": round(pct, 2),
        },
    )


def detect_new_items(
    old_list: list[dict] | None,
    new_list: list[dict] | None,
    key: str = "id",
) -> ChangeResult:
    """Find items in new_list that are not in old_list."""
    old_items = old_list or []
    new_items = new_list or []

    old_keys = {item.get(key) for item in old_items if item.get(key) is not None}
    new_entries = [item for item in new_items if item.get(key) not in old_keys]

    if not new_entries:
        return ChangeResult(
            changed=False, change_type="new_items", summary="No new items", details={}
        )

    return ChangeResult(
        changed=True,
        change_type="new_items",
        summary=f"{len(new_entries)} new item(s) found",
        details={
            "new_items": new_entries[:20],
            "count": len(new_entries),
        },
    )


def detect_removed_items(
    old_list: list[dict] | None,
    new_list: list[dict] | None,
    key: str = "id",
) -> ChangeResult:
    """Find items in old_list that are no longer in new_list."""
    old_items = old_list or []
    new_items = new_list or []

    new_keys = {item.get(key) for item in new_items if item.get(key) is not None}
    removed = [item for item in old_items if item.get(key) not in new_keys]

    if not removed:
        return ChangeResult(
            changed=False, change_type="removed_items", summary="No removed items", details={}
        )

    return ChangeResult(
        changed=True,
        change_type="removed_items",
        summary=f"{len(removed)} item(s) removed",
        details={
            "removed_items": removed[:20],
            "count": len(removed),
        },
    )
