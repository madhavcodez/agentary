from collections.abc import Generator

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator[Session, None, None]:
    yield from get_session()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Extract and validate the current user from the JWT bearer token."""
    from .auth import verify_token
    from .models.user import User

    user_id = verify_token(token)
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_gemini_api_key() -> str:
    return settings.gemini_api_key


def get_qdrant_url() -> str:
    return settings.qdrant_url


def get_redis_url() -> str:
    return settings.redis_url
