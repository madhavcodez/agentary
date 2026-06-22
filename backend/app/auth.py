from __future__ import annotations

import uuid as uuid_mod
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt with 12 rounds."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash (constant-time)."""
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: UUID, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token for the given user ID."""
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(days=settings.jwt_expire_days))
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "nbf": now,
        "jti": str(uuid_mod.uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> UUID:
    """Verify a JWT token and return the user ID. Raises HTTPException 401 on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        sub: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if sub is None or token_type != "access":
            raise credentials_exception
        return UUID(sub)
    except (JWTError, ValueError) as exc:
        raise credentials_exception from exc
