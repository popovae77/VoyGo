"""Отправка писем через SMTP (настройки в .env)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.smtp_configured:
        logger.info("[email] SMTP не настроен — письмо не отправлено: to=%s subject=%s", to, subject)
        print(f"[email] SMTP не настроен. Получатель: {to}\nТема: {subject}\n{body}\n")
        return False

    sender = settings.smtp_from or settings.smtp_user
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as client:
            if settings.smtp_use_tls:
                client.starttls()
            client.login(settings.smtp_user, settings.smtp_password)
            client.send_message(message)
        logger.info("[email] Отправлено: to=%s subject=%s", to, subject)
        return True
    except Exception:
        logger.exception("[email] Ошибка отправки на %s", to)
        return False
