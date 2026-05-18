"""SQLAlchemy engine, session factory, and connectivity verification.

``init_db`` no longer attempts to ``create_all``; Alembic is the only authority
for schema. Instead it confirms the database is reachable and raises early if
not — replacing the previous ``except Exception: pass`` that hid wrong DSN /
permission / network failures behind a successful boot.
"""
from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    pool_recycle=1800,
    pool_timeout=10,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


class Base(DeclarativeBase):
    pass


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Verify the database is reachable. Raise loudly on failure.

    Schema management belongs to Alembic; we deliberately do not call
    ``Base.metadata.create_all`` from runtime code anymore. Calling
    ``create_all`` masked migration drift — a model added without a
    corresponding migration would silently create the table on next boot,
    diverging dev/prod schemas.

    Any connectivity issue (wrong DSN, dead server, missing permissions) now
    surfaces as an exception at startup so the process exits and the
    orchestrator can restart with the correct config.
    """
    # Touch the model registry so all ORM classes are loaded before any
    # session begins issuing queries. Imported lazily to avoid circular deps.
    from . import models  # noqa: F401

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except (OperationalError, DBAPIError) as exc:
        logger.critical("Database connectivity check failed: %s", exc)
        raise RuntimeError(
            "Database is unreachable. Verify DATABASE_URL and that "
            "Postgres is accepting connections."
        ) from exc
