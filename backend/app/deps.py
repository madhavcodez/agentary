from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from .config import settings
from .database import get_session


def get_db() -> Generator[Session, None, None]:
    yield from get_session()


def get_gemini_api_key() -> str:
    return settings.gemini_api_key


def get_qdrant_url() -> str:
    return settings.qdrant_url


def get_redis_url() -> str:
    return settings.redis_url
