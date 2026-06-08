"""Отправка писем: SMTP или Brevo API (HTTPS, если провайдер блокирует SMTP)."""

from __future__ import annotations

import logging
import re
import smtplib
import ssl
from email.message import EmailMessage

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _parse_sender(from_value: str | None, fallback_email: str | None) -> tuple[str, str | None]:
    if not from_value:
        return fallback_email or "", None
    match = re.match(r"^(.+?)\s*<([^>]+)>$", from_value.strip())
    if match:
        return match.group(2).strip(), match.group(1).strip().strip('"')
    return from_value.strip(), None


def _smtp_client(settings):
    context = ssl.create_default_context()
    if settings.smtp_use_ssl:
        return smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=30,
            context=context,
        )
    client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
    client.ehlo()
    if settings.smtp_use_tls:
        client.starttls(context=context)
        client.ehlo()
    return client


def _send_via_smtp(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    sender = settings.smtp_from or settings.smtp_user
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.set_content(body)

    with _smtp_client(settings) as client:
        client.login(settings.smtp_user, settings.smtp_password)
        client.send_message(message)
    return True


def _send_via_brevo(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    sender_email, sender_name = _parse_sender(settings.smtp_from, settings.smtp_user)
    if not sender_email:
        logger.error("[email] Brevo: укажите SMTP_FROM или SMTP_USER")
        return False

    payload: dict = {
        "sender": {"email": sender_email},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    if sender_name:
        payload["sender"]["name"] = sender_name

    response = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": settings.brevo_api_key or "",
            "accept": "application/json",
            "content-type": "application/json",
        },
        json=payload,
        timeout=30.0,
    )
    if response.status_code >= 400:
        logger.error("[email] Brevo %s: %s", response.status_code, response.text[:500])
        return False
    return True


def send_email(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.email_configured:
        logger.info("[email] Почта не настроена — письмо не отправлено: to=%s subject=%s", to, subject)
        print(f"[email] Почта не настроена. Получатель: {to}\nТема: {subject}\n{body}\n")
        return False

    try:
        if settings.email_provider == "brevo":
            ok = _send_via_brevo(to=to, subject=subject, body=body)
        else:
            ok = _send_via_smtp(to=to, subject=subject, body=body)
        if ok:
            logger.info("[email] Отправлено (%s): to=%s subject=%s", settings.email_provider, to, subject)
        return ok
    except Exception:
        logger.exception("[email] Ошибка отправки (%s) на %s", settings.email_provider, to)
        return False
