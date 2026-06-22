from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password, verify_password
from ..core.rate_limiter import limiter
from ..deps import get_current_user, get_db
from ..models.user import User
from ..schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("3/minute")
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Register a new user account.

    Validates email uniqueness, hashes password, creates user, and returns a JWT.
    Logs rate-limit info (5 registrations per IP per hour) without enforcing.
    """
    # Rate-limit logging (not enforced yet)
    client_ip = request.client.host if request.client else "unknown"
    logger.info("Registration attempt from IP: %s", client_ip)

    # Normalize email to lowercase
    normalized_email = body.email.lower()

    # Check email uniqueness
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create user
    user = User(
        email=normalized_email,
        password_hash=hash_password(body.password),
        name=body.name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT.

    Uses generic error messages to avoid leaking whether an email exists.
    """
    # Normalize email to lowercase
    normalized_email = body.email.lower()

    user = db.query(User).filter(User.email == normalized_email, User.is_active.is_(True)).first()

    # Always run bcrypt to prevent timing-based user enumeration
    _DUMMY_HASH = "$2b$12$KIXq3oH9Y8eZnmC.qJsMleOlCPWP5P9hBzfFMD8r8Hq3fY9dqMWGu"
    password_hash = user.password_hash if user else _DUMMY_HASH
    is_valid = verify_password(body.password, password_hash)

    if not user or not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user
