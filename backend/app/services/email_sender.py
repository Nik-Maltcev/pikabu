"""Email notification service via SMTP."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


def send_report_ready_email(to_email: str, report_url: str, topic_name: str = ""):
    """Send email notification that report is ready."""
    if not settings.smtp_host or not settings.smtp_user:
        logger.warning("SMTP not configured, skipping email to %s", to_email)
        return False

    subject = "BizMap: ваш отчёт готов!"
    
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
            Это автоматическое уведомление от BizMap. Не отвечайте на это письмо.
        </p>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"BizMap <{settings.smtp_user}>"
        msg["To"] = to_email

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, to_email, msg.as_string())

        logger.info("Email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False
