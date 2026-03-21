"""API routes for data sources — CRUD, health check, query."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.data_source import DataSource
from ..models.user import User
from ..schemas.data_source import (
    DataSourceCreate,
    DataSourceHealthResponse,
    DataSourceQueryRequest,
    DataSourceQueryResponse,
    DataSourceResponse,
    DataSourceUpdate,
)

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


def _get_registry(request: Request):
    registry = getattr(request.app.state, "source_registry", None)
    if not registry:
        raise HTTPException(status_code=503, detail="Source registry not initialized")
    return registry


@router.get("", response_model=list[DataSourceResponse])
def list_data_sources(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """List available sources (system + user-created) with health status."""
    sources = (
        db.query(DataSource)
        .filter((DataSource.user_id == user.id) | (DataSource.is_system == True))
        .filter(DataSource.is_active == True)
        .order_by(DataSource.name)
        .all()
    )

    # Also include registered connectors that may not have DB records
    registry = getattr(request.app.state, "source_registry", None)
    if registry:
        registered = registry.list_available()
        existing_providers = {s.provider for s in sources}
        for r in registered:
            if r["provider"] not in existing_providers:
                sources.append(
                    DataSource(
                        name=r["name"],
                        slug=r["provider"],
                        source_type="api",
                        provider=r["provider"],
                        description=r["description"],
                        is_system=True,
                        is_active=True,
                        health_status="unknown",
                    )
                )
    return sources


@router.get("/{source_id}", response_model=DataSourceResponse)
def get_data_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get data source detail with usage stats."""
    source = (
        db.query(DataSource)
        .filter(
            DataSource.id == source_id,
            (DataSource.user_id == user.id) | (DataSource.is_system == True),
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    return source


@router.post("", response_model=DataSourceResponse, status_code=201)
def create_data_source(
    body: DataSourceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a custom API data source."""
    source = DataSource(
        user_id=user.id,
        is_system=False,
        **body.model_dump(),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.put("/{source_id}", response_model=DataSourceResponse)
def update_data_source(
    source_id: UUID,
    body: DataSourceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a data source config."""
    source = (
        db.query(DataSource)
        .filter(DataSource.id == source_id, DataSource.user_id == user.id)
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
def delete_data_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove a data source."""
    source = (
        db.query(DataSource)
        .filter(DataSource.id == source_id, DataSource.user_id == user.id)
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    db.delete(source)
    db.commit()


@router.post("/{source_id}/test", response_model=DataSourceQueryResponse)
async def test_data_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Test connection — return sample result."""
    source = (
        db.query(DataSource)
        .filter(
            DataSource.id == source_id,
            (DataSource.user_id == user.id) | (DataSource.is_system == True),
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    registry = _get_registry(request)
    connector = registry.get(source.provider)
    if not connector:
        raise HTTPException(status_code=400, detail=f"No connector for provider: {source.provider}")

    try:
        result = await connector.search(query="test", num_results=1)
        return DataSourceQueryResponse(
            data=result.data,
            total_results=result.total_results,
            source_name=result.source_name,
            cost_usd=result.cost_usd,
            cached=result.cached,
            metadata=result.metadata,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Test failed: {e}")


@router.get("/{source_id}/health", response_model=DataSourceHealthResponse)
async def health_check_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Health check a data source."""
    source = (
        db.query(DataSource)
        .filter(
            DataSource.id == source_id,
            (DataSource.user_id == user.id) | (DataSource.is_system == True),
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    registry = _get_registry(request)
    connector = registry.get(source.provider)
    if not connector:
        return DataSourceHealthResponse(status="down", message="No connector registered")

    try:
        health = await connector.health_check()
        from datetime import datetime

        source.health_status = health.get("status", "unknown")
        source.last_health_check = datetime.utcnow()
        db.commit()
        return DataSourceHealthResponse(**health)
    except Exception as e:
        return DataSourceHealthResponse(status="down", message=str(e))


@router.post("/{source_id}/query", response_model=DataSourceQueryResponse)
async def query_data_source(
    source_id: UUID,
    body: DataSourceQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Manually query a data source (for testing/debugging)."""
    source = (
        db.query(DataSource)
        .filter(
            DataSource.id == source_id,
            (DataSource.user_id == user.id) | (DataSource.is_system == True),
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    registry = _get_registry(request)

    kwargs = dict(body.params)
    if body.query:
        kwargs["query"] = body.query
    if body.identifier:
        kwargs["identifier"] = body.identifier

    try:
        result = await registry.query(source.provider, method=body.method, **kwargs)
        source.total_requests = (source.total_requests or 0) + 1
        source.total_cost_usd = (source.total_cost_usd or 0.0) + result.cost_usd
        db.commit()
        return DataSourceQueryResponse(
            data=result.data,
            total_results=result.total_results,
            source_name=result.source_name,
            cost_usd=result.cost_usd,
            cached=result.cached,
            metadata=result.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Query failed: {e}")
