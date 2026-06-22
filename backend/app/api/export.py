"""Data export API routes — CSV, JSON, Excel for findings and entities."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


def _check_mission_access(mission_id: str, user: User, db: Session):
    """Verify user owns the mission."""
    from ..models.mission import Mission

    mission = (
        db.query(Mission)
        .filter(
            Mission.id == UUID(mission_id),
            Mission.user_id == user.id,
        )
        .first()
    )
    if not mission:
        raise HTTPException(404, "Mission not found")
    return mission


# ── Findings export ──────────────────────────────────────────────────


@router.get("/missions/{mission_id}/findings/csv")
def export_findings_csv(
    mission_id: str,
    category: str | None = None,
    confidence_min: float | None = None,
    source_type: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_mission_access(mission_id, user, db)

    from ..services.reports.data_exporter import DataExporter

    filters = {}
    if category:
        filters["category"] = category
    if confidence_min is not None:
        filters["confidence_min"] = confidence_min
    if source_type:
        filters["source_type"] = source_type

    exporter = DataExporter()
    csv_bytes = exporter.export_findings_csv(UUID(mission_id), filters or None, db)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="findings_{mission_id[:8]}.csv"'},
    )


@router.get("/missions/{mission_id}/findings/json")
def export_findings_json(
    mission_id: str,
    category: str | None = None,
    confidence_min: float | None = None,
    source_type: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_mission_access(mission_id, user, db)

    from ..services.reports.data_exporter import DataExporter

    filters = {}
    if category:
        filters["category"] = category
    if confidence_min is not None:
        filters["confidence_min"] = confidence_min
    if source_type:
        filters["source_type"] = source_type

    exporter = DataExporter()
    json_str = exporter.export_findings_json(UUID(mission_id), filters or None, db)
    return Response(content=json_str, media_type="application/json")


@router.get("/missions/{mission_id}/findings/excel")
def export_findings_excel(
    mission_id: str,
    category: str | None = None,
    confidence_min: float | None = None,
    source_type: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_mission_access(mission_id, user, db)

    from ..services.reports.data_exporter import DataExporter

    filters = {}
    if category:
        filters["category"] = category
    if confidence_min is not None:
        filters["confidence_min"] = confidence_min
    if source_type:
        filters["source_type"] = source_type

    exporter = DataExporter()
    xlsx_bytes = exporter.export_findings_excel(UUID(mission_id), filters or None, db)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="findings_{mission_id[:8]}.xlsx"'},
    )


@router.get("/missions/{mission_id}/structured-data/{format}")
def export_structured_data(
    mission_id: str,
    format: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if format not in ("csv", "json", "excel"):
        raise HTTPException(400, "Format must be csv, json, or excel")

    _check_mission_access(mission_id, user, db)

    from ..services.reports.data_exporter import DataExporter

    exporter = DataExporter()
    data = exporter.export_structured_data(UUID(mission_id), format, db)

    media_types = {
        "csv": "text/csv",
        "json": "application/json",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    extensions = {"csv": "csv", "json": "json", "excel": "xlsx"}

    return Response(
        content=data,
        media_type=media_types[format],
        headers={
            "Content-Disposition": f'attachment; filename="structured_data_{mission_id[:8]}.{extensions[format]}"'
        },
    )


# ── Entity collection export ────────────────────────────────────────


@router.get("/entity-collections/{collection_id}/csv")
def export_entity_collection_csv(
    collection_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..models.entity_collection import EntityCollection

    collection = (
        db.query(EntityCollection)
        .filter(
            EntityCollection.id == UUID(collection_id),
            EntityCollection.user_id == user.id,
        )
        .first()
    )
    if not collection:
        raise HTTPException(404, "Entity collection not found")

    from ..services.reports.data_exporter import DataExporter

    exporter = DataExporter()
    csv_bytes = exporter.export_entity_collection_csv(UUID(collection_id), db)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="entities_{collection_id[:8]}.csv"'},
    )
