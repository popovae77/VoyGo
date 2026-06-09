"""Отправка писем: SMTP или HTTPS API (RuSender, UniSender Go, Brevo)."""

from __future__ import annotations

import logging
import re
import smtplib
import ssl
import uuid
from email.message import EmailMessage

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

RUSENDER_API_URL = "https://api.rusender.ru/api/v1/external-mails/send"


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


def _send_via_rusender(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    sender_email, sender_name = _parse_sender(settings.smtp_from, settings.smtp_user)
    if not sender_email:
        logger.error("[email] RuSender: укажите SMTP_FROM или SMTP_USER")
        return False

    from_block: dict = {"email": sender_email}
    if sender_name:
        from_block["name"] = sender_name

    payload = {
        "idempotencyKey": str(uuid.uuid4()),
        "mail": {
            "to": {"email": to},
            "from": from_block,
            "subject": subject,
            "text": body,
        },
    }

    response = httpx.post(
        RUSENDER_API_URL,
        headers={
            "X-Api-Key": settings.rusender_api_key or "",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30.0,
    )
    if response.status_code >= 400:
        logger.error("[email] RuSender %s: %s", response.status_code, response.text[:500])
        return False
    return True


def _send_via_unisender(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    sender_email, sender_name = _parse_sender(settings.smtp_from, settings.smtp_user)
    if not sender_email:
        logger.error("[email] UniSender Go: укажите SMTP_FROM или SMTP_USER")
        return False

    message: dict = {
        "recipients": [{"email": to}],
        "subject": subject,
        "from_email": sender_email,
        "body": {"plaintext": body},
        "skip_unsubscribe": 1,
    }
    if sender_name:
        message["from_name"] = sender_name

    base_url = settings.unisender_api_url.rstrip("/")
    response = httpx.post(
        f"{base_url}/email/send.json",
        headers={
            "X-API-KEY": settings.unisender_api_key or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={"message": message},
        timeout=30.0,
    )
    if response.status_code >= 400:
        logger.error("[email] UniSender %s: %s", response.status_code, response.text[:500])
        return False

    data = response.json()
    if data.get("status") == "error":
        logger.error("[email] UniSender error: %s", str(data)[:500])
        return False
    return True


def _try_smtp(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.smtp_configured:
        return False
    try:
        _send_via_smtp(to=to, subject=subject, body=body)
        logger.info("[email] Отправлено (smtp): to=%s subject=%s", to, subject)
        return True
    except Exception:
        logger.exception("[email] SMTP не сработал для %s", to)
        return False


def _try_brevo(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.brevo_configured:
        return False
    if _send_via_brevo(to=to, subject=subject, body=body):
        logger.info("[email] Отправлено (brevo): to=%s subject=%s", to, subject)
        return True
    return False


def _try_rusender(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.rusender_configured:
        return False
    if _send_via_rusender(to=to, subject=subject, body=body):
        logger.info("[email] Отправлено (rusender): to=%s subject=%s", to, subject)
        return True
    return False


def _try_unisender(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.unisender_configured:
        return False
    if _send_via_unisender(to=to, subject=subject, body=body):
        logger.info("[email] Отправлено (unisender): to=%s subject=%s", to, subject)
        return True
    return False


_PROVIDER_HANDLERS = {
    "smtp": _try_smtp,
    "brevo": _try_brevo,
    "rusender": _try_rusender,
    "unisender": _try_unisender,
}


def send_email(*, to: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.email_configured:
        logger.info("[email] Почта не настроена — письмо не отправлено: to=%s subject=%s", to, subject)
        print(f"[email] Почта не настроена. Получатель: {to}\nТема: {subject}\n{body}\n")
        return False

    primary = _PROVIDER_HANDLERS.get(settings.email_provider, _try_smtp)
    if primary(to=to, subject=subject, body=body):
        return True

    for name, handler in _PROVIDER_HANDLERS.items():
        if name == settings.email_provider:
            continue
        if handler(to=to, subject=subject, body=body):
            return True
    return False
