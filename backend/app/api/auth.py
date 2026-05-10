"""Auth API — phone verification via Twilio Verify + JWT tokens."""

import logging
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client as TwilioClient

from app.config import settings
from app.database import get_session
from app.models.database import User, Report as DBReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30


def _get_twilio_client():
    return TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)


def _create_token(user_id: int, phone: str) -> str:
    payload = {
        "user_id": user_id,
        "phone": phone,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
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


# --- Endpoints ---


class SendCodeRequest(BaseModel):
    phone: str  # e.g. "+79001234567"


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str


@router.post("/send-code")
async def send_code(request: SendCodeRequest):
    """Send SMS verification code via Twilio Verify."""
    phone = request.phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    try:
        client = _get_twilio_client()
        verification = client.verify.v2.services(
            settings.twilio_verify_service_sid
        ).verifications.create(to=phone, channel="sms")
        logger.info(f"Verification sent to {phone}: status={verification.status}")
        return {"success": True, "status": verification.status}
    except Exception as e:
        logger.error(f"Twilio send-code error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify")
async def verify_code(
    request: VerifyCodeRequest,
    session: AsyncSession = Depends(get_session),
):
    """Verify SMS code and return JWT token."""
    phone = request.phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    try:
        client = _get_twilio_client()
        check = client.verify.v2.services(
            settings.twilio_verify_service_sid
        ).verification_checks.create(to=phone, code=request.code)

        if check.status != "approved":
            raise HTTPException(status_code=400, detail="Invalid code")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Twilio verify error: {e}")
        raise HTTPException(status_code=400, detail="Verification failed")

    # Find or create user
    result = await session.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(phone=phone)
        session.add(user)
        await session.flush()

    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    token = _create_token(user.id, user.phone)
    logger.info(f"User authenticated: id={user.id}, phone={phone}")

    return {
        "success": True,
        "token": token,
        "user": {"id": user.id, "phone": user.phone},
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
        "user": {"id": user.id, "phone": user.phone},
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
