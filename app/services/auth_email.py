"""Письма регистрации и сброса пароля."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.email_sender import send_email


def reset_link(token: str) -> str:
    settings = get_settings()
    base = settings.app_public_url.rstrip("/")
    return f"{base}/auth?reset={token}"


def _public_url(path: str) -> str:
    settings = get_settings()
    base = settings.app_public_url.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def send_welcome_email(*, to: str, full_name: str | None) -> bool:
    settings = get_settings()
    greeting = full_name.strip() if full_name and full_name.strip() else "путешественник"
    subject = f"Добро пожаловать в {settings.app_name}"
    body = (
        f"Здравствуйте, {greeting}!\n\n"
        f"Вы успешно зарегистрировались в {settings.app_name}.\n"
        f"Теперь можно сохранять поиски, избранное и получать уведомления о снижении цен.\n\n"
        f"Войти в аккаунт: {_public_url('/auth')}\n"
        f"Подобрать поездку: {_public_url('/')}\n\n"
        "Если это были не вы — просто проигнорируйте письмо.\n"
    )
    return send_email(to=to, subject=subject, body=body)


def send_password_reset_email(*, to: str, reset_token: str) -> bool:
    settings = get_settings()
    link = reset_link(reset_token)
    subject = f"{settings.app_name} — сброс пароля"
    body = (
        "Вы запросили сброс пароля.\n\n"
        f"Перейдите по ссылке (действует 2 часа):\n{link}\n\n"
        "Если вы не запрашивали сброс — проигнорируйте это письмо.\n"
        "Пароль не изменится, пока вы не откроете ссылку и не зададите новый.\n"
    )
    return send_email(to=to, subject=subject, body=body)
