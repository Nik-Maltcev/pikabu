"""Payment API endpoints for Robokassa integration.

Flow:
1. POST /api/payment/create — creates payment, returns Robokassa URL
2. Robokassa redirects user to pay
3. POST /api/payment/result — Robokassa webhook (ResultURL), marks payment as paid
4. GET /api/payment/success — SuccessURL redirect back to frontend
5. GET /api/reports/{topic_id}/{report_id}/full?token=xxx — full report if token valid
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.database import Payment, Report as DBReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment")

REPORT_PRICE = 5  # rubles (TEST — change to 490 for production)


class PaymentCreateRequest(BaseModel):
    report_id: int


class PaymentCreateResponse(BaseModel):
    payment_url: str
    access_token: str


def _generate_robokassa_url(inv_id: int, amount: int, description: str) -> str:
    """Generate Robokassa payment URL with signature."""
    login = settings.robokassa_login
    password1 = settings.robokassa_password1

    # Signature: MerchantLogin:OutSum:InvId:Password#1
    out_sum = f"{amount:.2f}"
    signature_str = f"{login}:{out_sum}:{inv_id}:{password1}"
    signature = hashlib.md5(signature_str.encode()).hexdigest()

    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"

    params = (
        f"MerchantLogin={login}"
        f"&OutSum={out_sum}"
        f"&InvId={inv_id}"
        f"&Description={quote(description)}"
        f"&SignatureValue={signature}"
    )
    if settings.robokassa_test_mode:
        params += "&IsTest=1"

    return f"{base_url}?{params}"


def _verify_result_signature(out_sum: str, inv_id: str, signature: str) -> bool:
    """Verify Robokassa ResultURL signature using Password#2."""
    password2 = settings.robokassa_password2
    expected_str = f"{out_sum}:{inv_id}:{password2}"
    expected = hashlib.md5(expected_str.encode()).hexdigest().upper()
    return signature.upper() == expected


@router.post("/create", response_model=PaymentCreateResponse)
async def create_payment(
    request: PaymentCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> PaymentCreateResponse:
    """Create a payment for a report and return Robokassa URL."""
    # Validate report exists
    result = await session.execute(
        select(DBReport).where(DBReport.id == request.report_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    # Check if already paid
    existing = await session.execute(
        select(Payment).where(
            Payment.report_id == request.report_id,
            Payment.status == "paid",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Report already paid")

    # Create payment record
    access_token = secrets.token_hex(32)
    payment = Payment(
        report_id=request.report_id,
        amount=REPORT_PRICE,
        status="pending",
        access_token=access_token,
    )
    session.add(payment)
    await session.flush()

    # Use payment.id as InvId for Robokassa
    payment.robokassa_inv_id = payment.id
    await session.commit()

    # Generate Robokassa URL
    description = f"BizMap: полный отчёт #{request.report_id}"
    payment_url = _generate_robokassa_url(
        inv_id=payment.id,
        amount=REPORT_PRICE,
        description=description,
    )

    logger.info(f"Payment created: id={payment.id}, report={request.report_id}, token={access_token[:8]}...")

    return PaymentCreateResponse(
        payment_url=payment_url,
        access_token=access_token,
    )


@router.post("/result")
async def payment_result(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Robokassa ResultURL webhook. Called by Robokassa server after successful payment."""
    # Parse form data or query params
    if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        data = await request.form()
    else:
        data = request.query_params

    out_sum = data.get("OutSum", "")
    inv_id = data.get("InvId", "")
    signature = data.get("SignatureValue", "")

    logger.info(f"Robokassa ResultURL: InvId={inv_id}, OutSum={out_sum}")

    # Verify signature
    if not _verify_result_signature(out_sum, inv_id, signature):
        logger.warning(f"Invalid signature for InvId={inv_id}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Find and update payment
    result = await session.execute(
        select(Payment).where(Payment.robokassa_inv_id == int(inv_id))
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        logger.warning(f"Payment not found for InvId={inv_id}")
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    await session.commit()

    logger.info(f"Payment confirmed: id={payment.id}, report={payment.report_id}")

    # Robokassa expects "OK{InvId}" response
    return f"OK{inv_id}"


@router.get("/success")
async def payment_success(
    InvId: int = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """SuccessURL — redirect user back to frontend with access token."""
    result = await session.execute(
        select(Payment).where(Payment.robokassa_inv_id == InvId)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        return RedirectResponse(url=settings.site_url)

    # Redirect to report page with token
    report_result = await session.execute(
        select(DBReport).where(DBReport.id == payment.report_id)
    )
    report = report_result.scalar_one_or_none()
    if report is None:
        return RedirectResponse(url=settings.site_url)

    redirect_url = (
        f"{settings.site_url}/reports/{report.topic_id}/{report.id}"
        f"?token={payment.access_token}"
    )
    return RedirectResponse(url=redirect_url)


@router.get("/check")
async def check_payment(
    report_id: int = Query(...),
    token: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
):
    """Check if a report has been paid for (by token or report_id)."""
    if token:
        result = await session.execute(
            select(Payment).where(
                Payment.access_token == token,
                Payment.status == "paid",
            )
        )
        payment = result.scalar_one_or_none()
        if payment and payment.report_id == report_id:
            return {"paid": True, "access_token": token}

    # Check by report_id (any paid payment)
    result = await session.execute(
        select(Payment).where(
            Payment.report_id == report_id,
            Payment.status == "paid",
        )
    )
    payment = result.scalar_one_or_none()
    if payment:
        return {"paid": True, "access_token": payment.access_token}

    return {"paid": False}


@router.get("/test")
async def test_payment():
    """Generate a test Robokassa payment URL (5 RUB) to verify integration works.
    No database record — just returns a URL to test the flow.
    """
    description = "BizMap: тест оплаты"
    inv_id = 99999  # fixed test invoice
    amount = 5

    login = settings.robokassa_login
    password1 = settings.robokassa_password1
    out_sum = f"{amount:.2f}"
    signature_str = f"{login}:{out_sum}:{inv_id}:{password1}"
    signature = hashlib.md5(signature_str.encode()).hexdigest()

    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
    payment_url = (
        f"{base_url}"
        f"?MerchantLogin={login}"
        f"&OutSum={out_sum}"
        f"&InvId={inv_id}"
        f"&Description={quote(description)}"
        f"&SignatureValue={signature}"
    )
    if settings.robokassa_test_mode:
        payment_url += "&IsTest=1"

    return {"payment_url": payment_url, "amount": amount, "inv_id": inv_id}
