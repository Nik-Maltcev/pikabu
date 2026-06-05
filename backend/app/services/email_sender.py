"""Email notification service via Resend API."""

import logging
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_report_ready_email(to_email: str, report_url: str, topic_name: str = ""):
    """Send email notification that report is ready via Resend."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured, skipping email to %s", to_email)
        return False

    html_body = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 32px 24px;">
        <h1 style="color: #006a62; font-size: 24px; margin: 0 0 16px;">BizMap</h1>
        <p style="font-size: 16px; color: #1b1b1d; margin: 0 0 12px;">Ваш анализ завершён!</p>
        <p style="font-size: 14px; color: #6b7280; margin: 0 0 24px;">
            {f'Категория: {topic_name}' if topic_name else 'Отчёт готов к просмотру.'}
        </p>
        <a href="{report_url}" style="display: inline-block; background: #006a62; color: #fff; padding: 14px 28px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 16px;">
            Посмотреть отчёт
        </a>
        <p style="font-size: 12px; color: #9ca3af; margin: 24px 0 0;">
            Это автоматическое уведомление от BizMap.
        </p>
    </div>
    """

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.resend_from_email,
                    "to": [to_email],
                    "subject": "BizMap: ваш отчёт готов!",
                    "html": html_body,
                },
            )
            if resp.status_code in (200, 201):
                logger.info("Email sent to %s via Resend", to_email)
                return True
            else:
                logger.error("Resend error %d: %s", resp.status_code, resp.text)
                return False
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False
