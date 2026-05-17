"""Auth API — email/password authentication + JWT tokens.

Two modes:
1. With registration: email + password → account → reports saved
2. Without registration: just provide contact (email/telegram) for notification
"""

import logging
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.database import User, Report as DBReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30


def _hash_password(password: str) -> str:
    """Hash password using SHA-256 + salt (simple but secure enough)."""
    salt = settings.jwt_secret[:16]
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return _hash_password(password) == password_hash


def _create_token(user_id: int, email: str) -> str:
    """Create JWT token for authenticated user."""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Extract user from Authorization header. Returns None if not authenticated."""
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    try:
        payload = _decode_token(token)
    except HTTPException:
        return None
    result = await session.execute(
        select(User).where(User.id == payload["user_id"])
    )
    return result.scalar_one_or_none()


# --- Request/Response Models ---


class RegisterRequest(BaseModel):
    """Register new account."""
    email: str
    password: str


class LoginRequest(BaseModel):
    """Login with email/password."""
    email: str
    password: str


class UserResponse(BaseModel):
    """User info response."""
    id: int
    email: str | None
    phone: str | None


# --- Endpoints ---


@router.post("/register")
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    """Register new account with email/password (no email verification)."""
    email = request.email.strip().lower()
    password = request.password.strip()

    # Validate
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check if email already exists
    result = await session.execute(
        select(User).where(User.email == email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    user = User(
        email=email,
        password_hash=_hash_password(password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = _create_token(user.id, user.email)
    logger.info(f"User registered: id={user.id}, email={email}")

    return {
        "success": True,
        "token": token,
        "user": {"id": user.id, "email": user.email},
    }


@router.post("/login")
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Login with email/password."""
    email = request.email.strip().lower()
    password = request.password.strip()

    # Find user
    result = await session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user is None or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not _verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    token = _create_token(user.id, user.email)
    logger.info(f"User logged in: id={user.id}, email={email}")

    return {
        "success": True,
        "token": token,
        "user": {"id": user.id, "email": user.email},
    }


@router.get("/me")
async def get_me(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_session),
):
    """Get current user info + their reports."""
    user = await get_current_user(authorization, session)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get user's reports
    result = await session.execute(
        select(DBReport)
        .where(DBReport.user_id == user.id)
        .order_by(DBReport.generated_at.desc())
    )
    reports = result.scalars().all()

    return {
        "user": {"id": user.id, "email": user.email, "phone": user.phone},
        "reports": [
            {
                "id": r.id,
                "topic_id": r.topic_id,
                "analysis_mode": r.analysis_mode,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "sources": r.sources,
            }
            for r in reports
        ],
    }


@router.post("/link-report")
async def link_report(
    report_id: int,
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_session),
):
    """Link a report to the current user's account."""
    user = await get_current_user(authorization, session)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.execute(
        select(DBReport).where(DBReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    report.user_id = user.id
    await session.commit()

    return {"success": True}


@router.get("/check")
async def check_auth(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_session),
):
    """Check if user is authenticated (for frontend)."""
    user = await get_current_user(authorization, session)
    if user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user": {"id": user.id, "email": user.email},
    }
