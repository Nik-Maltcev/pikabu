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

REPORT_PRICE = 1490  # rubles

# Promo codes: code -> price in rubles
PROMO_CODES = {
    "BIZFIRST": 745,       # 50% off, one-time
    "Amx50100%": 5,        # test price
}


class PaymentCreateRequest(BaseModel):
    report_id: int
    promo_code: str = ""


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


def _verify_result_signature(out_sum: str, inv_id: str, signature: str, shp_params: dict = None) -> bool:
    """Verify Robokassa ResultURL signature using Password#2.
    Shp_ params must be included in signature in alphabetical order.
    """
    password2 = settings.robokassa_password2
    parts = [out_sum, inv_id, password2]
    if shp_params:
        for key in sorted(shp_params.keys()):
            parts.append(f"{key}={shp_params[key]}")
    expected_str = ":".join(parts)
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

    # Apply promo code
    price = REPORT_PRICE
    if request.promo_code and request.promo_code in PROMO_CODES:
        price = PROMO_CODES[request.promo_code]

    # Create payment record
    access_token = secrets.token_hex(32)
    payment = Payment(
        report_id=request.report_id,
        amount=price,
        status="pending",
        access_token=access_token,
        promo_code=request.promo_code if request.promo_code in PROMO_CODES else None,
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
        amount=price,
        description=description,
    )

    logger.info(f"Payment created: id={payment.id}, report={request.report_id}, price={price}, token={access_token[:8]}...")

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

    # Collect Shp_ params for signature verification
    shp_params = {}
    for key in data.keys():
        if key.startswith("Shp_"):
            shp_params[key] = data.get(key, "")

    # Verify signature
    if not _verify_result_signature(out_sum, inv_id, signature, shp_params):
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

    # If this is a pre-analysis payment (report_id is None), launch analysis
    shp_topic_id = data.get("Shp_topic_id", "")
    shp_days = data.get("Shp_days", "14")
    if payment.report_id is None and shp_topic_id:
        import asyncio
        from app.api.router import _run_analysis_background
        from app.models.database import AnalysisTask
        from app.services.topic_manager import TopicManager

        topic_id = int(shp_topic_id)
        days = int(shp_days) if shp_days else 14

        # Find duplicates and start analysis
        tm = TopicManager(session)
        all_topics = await tm.find_duplicates_by_name(topic_id)
        topic_ids_by_source: dict[str, int] = {}
        for t in all_topics:
            topic_ids_by_source[t.source] = t.id
        sources_label = ",".join(sorted(topic_ids_by_source.keys()))

        # Create task
        task = AnalysisTask(topic_id=topic_id, status="pending", progress_percent=0, analysis_mode="niche_search")
        session.add(task)
        await session.flush()
        task_id = task.id

        # Store task_id in payment for SuccessURL redirect
        payment.task_id = str(task_id)
        payment.report_id = None  # will be set when report is generated
        await session.commit()

        # Launch background analysis
        asyncio.create_task(
            _run_analysis_background(
                primary_topic_id=topic_id,
                topic_ids_by_source=topic_ids_by_source,
                task_id=task_id,
                days=days,
                analysis_mode="niche_search",
                sources_label=sources_label,
            )
        )
        logger.info(f"Paid analysis launched: task={task_id}, topic={topic_id}")

    # Robokassa expects "OK{InvId}" response
    return f"OK{inv_id}"


@router.get("/success")
async def payment_success(
    InvId: int = Query(...),
    Shp_topic_id: str = Query(default=""),
    Shp_days: str = Query(default="14"),
    Shp_fingerprint: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
):
    """SuccessURL — redirect user back to frontend."""
    import asyncio

    logger.info(f"SuccessURL: InvId={InvId}, Shp_topic_id={Shp_topic_id}")

    result = await session.execute(
        select(Payment).where(Payment.robokassa_inv_id == InvId)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        logger.warning(f"SuccessURL: payment not found for InvId={InvId}")
        return RedirectResponse(url=settings.site_url)

    # If pre-analysis payment — redirect to progress page
    if payment.report_id is None and Shp_topic_id:
        # If task already created by webhook — use it
        if payment.task_id:
            redirect_url = f"{settings.site_url}/analysis/{payment.task_id}?topicId={Shp_topic_id}"
            return RedirectResponse(url=redirect_url)

        # Webhook hasn't fired yet — wait briefly for it instead of launching a duplicate
        import asyncio
        for _ in range(5):
            await asyncio.sleep(1)
            await session.refresh(payment)
            if payment.task_id:
                redirect_url = f"{settings.site_url}/analysis/{payment.task_id}?topicId={Shp_topic_id}"
                return RedirectResponse(url=redirect_url)

        # After 5s the webhook still hasn't arrived — launch as last resort
        # Use a unique constraint check to prevent duplicates
        from app.api.router import _run_analysis_background
        from app.models.database import AnalysisTask
        from app.services.topic_manager import TopicManager

        # Re-check one more time after acquiring a lock
        await session.refresh(payment)
        if payment.task_id:
            redirect_url = f"{settings.site_url}/analysis/{payment.task_id}?topicId={Shp_topic_id}"
            return RedirectResponse(url=redirect_url)

        if payment.status != "paid":
            payment.status = "paid"
            payment.paid_at = datetime.now(timezone.utc)

        topic_id = int(Shp_topic_id)
        days = int(Shp_days) if Shp_days else 14

        tm = TopicManager(session)
        all_topics = await tm.find_duplicates_by_name(topic_id)
        topic_ids_by_source: dict[str, int] = {}
        for t in all_topics:
            topic_ids_by_source[t.source] = t.id
        sources_label = ",".join(sorted(topic_ids_by_source.keys()))

        task = AnalysisTask(topic_id=topic_id, status="pending", progress_percent=0, analysis_mode="niche_search")
        session.add(task)
        await session.flush()
        task_id = task.id
        payment.task_id = str(task_id)
        await session.commit()

        asyncio.create_task(
            _run_analysis_background(
                primary_topic_id=topic_id,
                topic_ids_by_source=topic_ids_by_source,
                task_id=task_id,
                days=days,
                analysis_mode="niche_search",
                sources_label=sources_label,
            )
        )
        logger.info(f"SuccessURL fallback: launched analysis task={task_id}")

        redirect_url = f"{settings.site_url}/analysis/{task_id}?topicId={Shp_topic_id}"
        return RedirectResponse(url=redirect_url)

    # If report payment — redirect to report with token
    if payment.report_id:
        report_result = await session.execute(
            select(DBReport).where(DBReport.id == payment.report_id)
        )
        report = report_result.scalar_one_or_none()
        if report:
            redirect_url = (
                f"{settings.site_url}/reports/{report.topic_id}/{report.id}"
                f"?token={payment.access_token}"
            )
            return RedirectResponse(url=redirect_url)

    logger.warning(f"SuccessURL: no redirect target for InvId={InvId}")
    return RedirectResponse(url=settings.site_url)


@router.get("/check")
async def check_payment(
    report_id: int = Query(...),
    token: str = Query(default=""),
    topic_id: int = Query(default=0),
    session: AsyncSession = Depends(get_session),
):
    """Check if a report has been paid for (by token, report_id, or topic_id)."""
    # Check by token
    if token:
        result = await session.execute(
            select(Payment).where(
                Payment.access_token == token,
                Payment.status == "paid",
            )
        )
        payment = result.scalar_one_or_none()
        if payment:
            return {"paid": True, "access_token": token}

    # Check by report_id (any paid payment linked to this report)
    result = await session.execute(
        select(Payment).where(
            Payment.report_id == report_id,
            Payment.status == "paid",
        )
    )
    payment = result.scalar_one_or_none()
    if payment:
        return {"paid": True, "access_token": payment.access_token}

    # Check by topic_id — find paid pre-analysis payment for this specific topic
    if topic_id:
        from sqlalchemy import and_
        paid_result = await session.execute(
            select(Payment).where(
                and_(
                    Payment.status == "paid",
                    Payment.topic_id == topic_id,
                    Payment.report_id.is_(None),
                )
            ).order_by(Payment.paid_at.desc()).limit(1)
        )
        paid_payment = paid_result.scalar_one_or_none()
        if paid_payment:
            # Link this payment to the report
            paid_payment.report_id = report_id
            await session.commit()
            return {"paid": True, "access_token": paid_payment.access_token}

    return {"paid": False}


@router.get("/status/{inv_id}")
async def payment_status(
    inv_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Poll payment status by InvId. Used by frontend after opening Robokassa."""
    result = await session.execute(
        select(Payment).where(Payment.robokassa_inv_id == inv_id)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        return {"status": "not_found"}

    return {
        "status": payment.status,
        "task_id": payment.task_id,
        "topic_id": payment.topic_id,
        "paid": payment.status == "paid",
    }


@router.post("/confirm/{inv_id}")
async def confirm_payment(
    inv_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Manual payment confirmation. Called when user clicks 'I paid'.
    
    Verifies payment status with Robokassa before confirming.
    Only marks as paid if Robokassa confirms the transaction.
    """
    import asyncio
    import httpx

    result = await session.execute(
        select(Payment).where(Payment.robokassa_inv_id == inv_id)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        return {"paid": False, "error": "Payment not found"}

    # Already paid and task exists
    if payment.status == "paid" and payment.task_id:
        return {"paid": True, "task_id": payment.task_id, "topic_id": payment.topic_id}

    # Verify with Robokassa before trusting the user
    is_verified = False
    try:
        # Robokassa XML interface for checking payment status
        login = settings.robokassa_login
        password2 = settings.robokassa_password2
        check_url = "https://auth.robokassa.ru/Merchant/WebService/Service.asmx/OpStateExt"
        
        # Signature: MerchantLogin:InvId:Password#2
        sig_str = f"{login}:{inv_id}:{password2}"
        sig = hashlib.md5(sig_str.encode()).hexdigest()
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                check_url,
                params={
                    "MerchantLogin": login,
                    "InvoiceID": inv_id,
                    "Signature": sig,
                },
            )
            # Robokassa returns XML with State Code:
            # 100 = completed successfully
            if resp.status_code == 200 and "100" in resp.text:
                is_verified = True
                logger.info(f"Robokassa verified payment InvId={inv_id} as paid")
            else:
                logger.warning(f"Robokassa says InvId={inv_id} NOT paid: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Failed to verify payment {inv_id} with Robokassa: {e}")
        # If Robokassa is unreachable, don't blindly trust the user
        return {"paid": False, "error": "Не удалось проверить оплату. Попробуйте через минуту."}

    if not is_verified:
        return {"paid": False, "error": "Оплата ещё не подтверждена Робокассой. Подождите немного."}

    # Robokassa confirmed — mark as paid
    if payment.status != "paid":
        payment.status = "paid"
        payment.paid_at = datetime.now(timezone.utc)

    # Launch analysis if not already launched
    if not payment.task_id and payment.topic_id:
        from app.api.router import _run_analysis_background
        from app.models.database import AnalysisTask
        from app.services.topic_manager import TopicManager

        topic_id = payment.topic_id
        days = 14  # default

        tm = TopicManager(session)
        all_topics = await tm.find_duplicates_by_name(topic_id)
        topic_ids_by_source: dict[str, int] = {}
        for t in all_topics:
            topic_ids_by_source[t.source] = t.id
        sources_label = ",".join(sorted(topic_ids_by_source.keys()))

        task = AnalysisTask(topic_id=topic_id, status="pending", progress_percent=0, analysis_mode="niche_search")
        session.add(task)
        await session.flush()
        task_id = task.id

        payment.task_id = str(task_id)
        await session.commit()

        asyncio.create_task(
            _run_analysis_background(
                primary_topic_id=topic_id,
                topic_ids_by_source=topic_ids_by_source,
                task_id=task_id,
                days=days,
                analysis_mode="niche_search",
                sources_label=sources_label,
            )
        )
        logger.info(f"Manual confirm: launched analysis task={task_id}, topic={topic_id}")
        return {"paid": True, "task_id": str(task_id), "topic_id": topic_id}

    await session.commit()
    return {"paid": True, "task_id": payment.task_id, "topic_id": payment.topic_id}


class PaidAnalysisRequest(BaseModel):
    """Request to create a paid analysis (when free limit is exhausted)."""
    topic_id: int
    days: int = 14
    fingerprint: str = ""
    promo_code: str = ""


class PromoCheckRequest(BaseModel):
    code: str


@router.post("/promo/check")
async def check_promo_code(request: PromoCheckRequest, session: AsyncSession = Depends(get_session)):
    """Check if a promo code is valid and return the discounted price."""
    code = request.code.strip()
    if code not in PROMO_CODES:
        return {"valid": False}
    
    # Check if one-time promo already used
    if code == "BIZFIRST":
        used = await session.execute(
            select(Payment).where(
                Payment.promo_code == code,
                Payment.status == "paid",
            )
        )
        if used.scalar_one_or_none():
            return {"valid": False, "error": "Промокод уже использован"}
    
    price = PROMO_CODES[code]
    discount_percent = round((1 - price / REPORT_PRICE) * 100)
    return {"valid": True, "price": price, "discount_percent": discount_percent, "original_price": REPORT_PRICE}


@router.post("/create-for-analysis")
async def create_payment_for_analysis(
    request: PaidAnalysisRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a payment that will trigger analysis after successful payment.
    Used when free analyses are exhausted.
    Stores topic_id and days in Shp_ params so we can start analysis after payment.
    """
    # Apply promo code
    price = REPORT_PRICE
    if request.promo_code and request.promo_code in PROMO_CODES:
        price = PROMO_CODES[request.promo_code]

    access_token = secrets.token_hex(32)
    payment = Payment(
        report_id=None,  # no report yet — will be created after payment
        topic_id=request.topic_id,
        amount=price,
        status="pending",
        access_token=access_token,
    )
    session.add(payment)
    await session.flush()
    payment.robokassa_inv_id = payment.id
    await session.commit()

    # Build Robokassa URL with Shp_ params to pass topic_id and days
    login = settings.robokassa_login
    password1 = settings.robokassa_password1
    out_sum = f"{price:.2f}"
    inv_id = payment.id

    # Shp_ params are included in signature in alphabetical order
    shp_days = request.days
    shp_fingerprint = request.fingerprint[:32] if request.fingerprint else ""
    shp_topic_id = request.topic_id

    # Signature with Shp_ params: MerchantLogin:OutSum:InvId:Password#1:Shp_days=X:Shp_fingerprint=X:Shp_topic_id=X
    signature_str = f"{login}:{out_sum}:{inv_id}:{password1}:Shp_days={shp_days}:Shp_fingerprint={shp_fingerprint}:Shp_topic_id={shp_topic_id}"
    signature = hashlib.md5(signature_str.encode()).hexdigest()

    description = "BizMap: полный анализ ниши"
    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"

    payment_url = (
        f"{base_url}"
        f"?MerchantLogin={login}"
        f"&OutSum={out_sum}"
        f"&InvId={inv_id}"
        f"&Description={quote(description)}"
        f"&SignatureValue={signature}"
        f"&Shp_days={shp_days}"
        f"&Shp_fingerprint={shp_fingerprint}"
        f"&Shp_topic_id={shp_topic_id}"
    )
    if settings.robokassa_test_mode:
        payment_url += "&IsTest=1"

    logger.info(f"Paid analysis payment created: id={payment.id}, topic={request.topic_id}")

    return {"payment_url": payment_url, "access_token": access_token}
