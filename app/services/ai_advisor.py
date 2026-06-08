"""Travel tips via Google Gemini or Groq (fallback)."""

from __future__ import annotations

import json
import logging
import re
from typing import Literal

import httpx

from app.core.config import Settings, get_settings
from app.schemas.trip import TripSearchCreate

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

AiProvider = Literal["gemini", "groq", "none"]


class GeminiGeoBlockedError(Exception):
    """Gemini API rejected the request due to regional restrictions."""


def _ai_provider(settings: Settings) -> AiProvider:
    if settings.gemini_api_key:
        return "gemini"
    if settings.groq_api_key:
        return "groq"
    return "none"


def _missing_key_message() -> str:
    return "Добавьте GEMINI_API_KEY или GROQ_API_KEY в .env, чтобы включить ИИ-подсказки."


def _geo_blocked_message() -> str:
    return (
        "Google Gemini недоступен в вашем регионе. "
        "Добавьте бесплатный ключ Groq (console.groq.com) в GROQ_API_KEY в .env и перезапустите сервер."
    )


def _gemini_failure_kind(exc: httpx.HTTPStatusError) -> str | None:
    try:
        payload = exc.response.json()
        message = str((payload.get("error") or {}).get("message") or "")
    except (ValueError, AttributeError):
        message = exc.response.text or ""
    lowered = message.lower()
    if "location is not supported" in lowered or "not available in your country" in lowered:
        return "geo"
    if exc.response.status_code == 429 or "quota" in lowered or "rate limit" in lowered:
        return "quota"
    return None


def build_offers_context(
    trip: TripSearchCreate,
    offers: list[dict],
) -> str:
    lines = [
        f"Вылет из: {trip.origin}",
        f"Направление: {trip.destination}",
        f"Даты: {trip.start_date} — {trip.end_date}",
        f"Люди: {trip.people_count}",
        f"Бюджет: {trip.budget} RUB",
        f"Тип отдыха: {trip.travel_type.value}",
        f"Комфорт: {(trip.comfort_level or 'standard').value}",
        "Варианты:",
    ]
    for offer in offers[:4]:
        b = offer.get("breakdown_json") or {}
        lines.append(
            f"- {offer.get('title')}: {offer.get('total_price')} RUB, "
            f"в бюджет={'да' if offer.get('fits_budget') else 'нет'}, "
            f"перелёт={b.get('flight')}, жильё={b.get('hotel')}, "
            f"источники={b.get('sources')}"
        )
    return "\n".join(lines)


def _extract_json_object(content: str) -> str:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def _parse_advice_json(content: str) -> dict[str, str | list[str]]:
    parsed = json.loads(_extract_json_object(content))
    tips = parsed.get("tips") or []
    if isinstance(tips, str):
        tips = [tips]
    return {
        "summary": str(parsed.get("summary") or ""),
        "best_pick": str(parsed.get("best_pick") or ""),
        "tips": [str(t) for t in tips][:6],
    }


def _gemini_generate(
    settings: Settings,
    *,
    system: str,
    user: str,
    temperature: float,
    json_mode: bool = False,
    max_output_tokens: int = 1024,
) -> str:
    url = f"{GEMINI_BASE}/{settings.gemini_model}:generateContent"
    generation_config: dict = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if json_mode:
        generation_config["responseMimeType"] = "application/json"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": generation_config,
    }
    response = httpx.post(
        url,
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": settings.gemini_api_key or "",
        },
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise ValueError("Gemini returned empty text")
    return text.strip()


def _groq_chat(
    settings: Settings,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    json_mode: bool = False,
    max_tokens: int = 600,
) -> str:
    body: dict = {
        "model": settings.groq_model,
        "temperature": temperature,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    response = httpx.post(
        GROQ_CHAT_URL,
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=30.0,
    )
    response.raise_for_status()
    return str(response.json()["choices"][0]["message"]["content"]).strip()


def _llm_json_advice(settings: Settings, system: str, user: str) -> dict[str, str | list[str]]:
    geo_blocked = False
    last_error: Exception | None = None

    if settings.gemini_api_key:
        try:
            content = _gemini_generate(
                settings,
                system=system,
                user=user,
                temperature=0.4,
                json_mode=True,
                max_output_tokens=2048,
            )
            return _parse_advice_json(content)
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if _gemini_failure_kind(exc) == "geo":
                geo_blocked = True
            logger.warning("Gemini advice failed: %s", exc)
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning("Gemini advice parse failed: %s", exc)

    if settings.groq_api_key:
        try:
            content = _groq_chat(
                settings,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.4,
                json_mode=True,
                max_tokens=1024,
            )
            return _parse_advice_json(content)
        except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning("Groq advice fallback failed: %s", exc)

    if geo_blocked:
        raise GeminiGeoBlockedError() from last_error
    if last_error is not None:
        raise last_error
    raise ValueError("No AI provider configured")


def _llm_chat_reply(
    settings: Settings,
    *,
    system: str,
    messages: list[dict[str, str]],
) -> str:
    geo_blocked = False
    last_error: Exception | None = None

    if settings.gemini_api_key:
        history_lines: list[str] = []
        for item in messages:
            role = item.get("role")
            if role == "system":
                continue
            label = "Пользователь" if role == "user" else "Ассистент"
            history_lines.append(f"{label}: {item['content']}")
        user_block = "\n\n".join(history_lines)
        try:
            return _gemini_generate(
                settings,
                system=system,
                user=user_block,
                temperature=0.55,
                json_mode=False,
                max_output_tokens=600,
            )
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if _gemini_failure_kind(exc) == "geo":
                geo_blocked = True
            logger.warning("Gemini chat failed: %s", exc)
        except ValueError as exc:
            last_error = exc
            logger.warning("Gemini chat failed: %s", exc)

    if settings.groq_api_key:
        try:
            return _groq_chat(
                settings,
                messages=[{"role": "system", "content": system}, *messages],
                temperature=0.55,
                json_mode=False,
                max_tokens=600,
            )
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            last_error = exc
            logger.warning("Groq chat fallback failed: %s", exc)

    if geo_blocked:
        raise GeminiGeoBlockedError() from last_error
    if last_error is not None:
        raise last_error
    raise ValueError("No AI provider configured")


def get_ai_travel_advice(trip: TripSearchCreate, offers: list[dict]) -> dict[str, str | list[str]]:
    settings = get_settings()
    if _ai_provider(settings) == "none":
        return {
            "summary": _missing_key_message(),
            "tips": [],
            "best_pick": "",
        }

    context = build_offers_context(trip, offers)
    system = (
        "Ты Voyago — умный помощник по бюджетным путешествиям. "
        "Отвечай по-русски, кратко и по делу. Формат ответа — JSON с ключами: "
        "summary (2 предложения), best_pick (лучший вариант и почему), "
        "tips (массив из 3–5 коротких советов: когда выгоднее лететь, как сэкономить, на что обратить внимание)."
    )
    user = (
        f"Подбери самые выгодные путёвки в ближайшее время по данным расчёта:\n\n{context}\n\n"
        "Учти сезон, даты и бюджет. Не выдумывай цены — опирайся только на цифры выше."
    )

    try:
        return _llm_json_advice(settings, system, user)
    except GeminiGeoBlockedError:
        return {
            "summary": _geo_blocked_message(),
            "tips": [],
            "best_pick": "",
        }
    except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("AI travel advice failed (%s): %s", _ai_provider(settings), exc)
        return {
            "summary": "ИИ временно недоступен. Используйте расчёт и кнопки бронирования ниже.",
            "tips": [],
            "best_pick": "",
        }


def chat_with_ai(
    message: str,
    history: list[dict[str, str]],
    trip_context: str | None = None,
) -> str:
    settings = get_settings()
    if _ai_provider(settings) == "none":
        return _missing_key_message()

    system = (
        "Ты Voyago AI — дружелюбный помощник по бюджетным путешествиям. "
        "Отвечай по-русски, коротко (2–5 предложений), без выдуманных точных цен. "
        "Помогай выбрать направление, даты, экономить на перелёте и жилье. "
        "Если есть контекст последнего расчёта — опирайся на него."
    )
    if trip_context:
        system += f"\n\nКонтекст последнего поиска пользователя:\n{trip_context}"

    messages: list[dict[str, str]] = []
    for item in history[-10:]:
        role = item.get("role", "user")
        if role in {"user", "assistant"} and item.get("content"):
            messages.append({"role": role, "content": str(item["content"])[:2000]})
    messages.append({"role": "user", "content": message[:2000]})

    try:
        return _llm_chat_reply(settings, system=system, messages=messages)
    except GeminiGeoBlockedError:
        return _geo_blocked_message()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("AI chat failed (%s): %s", _ai_provider(settings), exc)
        return "Сейчас не могу ответить. Попробуйте через минуту или сделайте новый поиск поездки."
