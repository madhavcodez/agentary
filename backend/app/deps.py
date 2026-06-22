from collections.abc import Generator

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_db() -> Generator[Session]:
    yield from get_session()


def _get_or_create_dev_user(db: Session):
    """Get or create a default dev user when running without auth."""
    import uuid

    from .models.user import User

    dev_email = "dev@agentary.local"
    user = db.query(User).filter(User.email == dev_email).first()
    if user:
        return user

    user = User(
        id=uuid.uuid4(),
        email=dev_email,
        name="Dev User",
        password_hash="dev-no-login",  # noqa: S106 - sentinel for local dev user, not a real credential
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Extract user from JWT token. In dev mode, auto-creates a dev user if no token."""
    if not token:
        if settings.app_env == "dev":
            return _get_or_create_dev_user(db)
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from .auth import verify_token
    from .models.user import User

    user_id = verify_token(token)
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_gemini_api_key() -> str:
    return settings.gemini_api_key


def get_qdrant_url() -> str:
    return settings.qdrant_url


def get_redis_url() -> str:
    return settings.redis_url
