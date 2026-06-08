# Voyago

Сервис для путешествий без наценок. MVP веб-сервиса для подбора путешествия по бюджету и типу отдыха. Стек: FastAPI, SQLite, SQLAlchemy 2.x, Pydantic v2, JWT.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

После запуска:

- HTML-демо: http://127.0.0.1:8000/
- Swagger: http://127.0.0.1:8000/docs
- Healthcheck: http://127.0.0.1:8000/api/v1/health

SQLite-файл создаётся автоматически в `data/voyago.db`.

## Основные возможности MVP

- регистрация и вход по JWT;
- создание запроса на подбор поездки;
- расчёт бюджета с детализацией расходов;
- альтернативы при превышении бюджета;
- история запросов;
- избранные варианты;
- in-app уведомления и подписки на снижение цены;
- mock-провайдер цен для демонстрации без внешних API;
- опциональный провайдер авиабилетов Travelpayouts / Aviasales cache.

## Реальные данные

Для реальных цен на перелёты укажи в `.env`:

```env
PRICING_PROVIDER=travelpayouts
TRAVELPAYOUTS_TOKEN=your-token
DEFAULT_ORIGIN_IATA=MOW
```

После этого поиск будет пытаться брать перелёт из Travelpayouts Data API.

**Отели (по приоритету):**
1. **[SerpApi Google Hotels](https://serpapi.com/google-hotels-api)** — `SERPAPI_API_KEY`, цены по вашим датам в RUB.
2. **[Makcorps Free Hotel API](https://docs.hotelapi.co/free-hotel-api)** — `MAKCORPS_USERNAME` / `MAKCORPS_PASSWORD` (или `MAKCORPS_JWT`); агрегатор Booking, Priceline и др. (в free tier без дат заезда).
3. **Hotellook** (токен Travelpayouts) — если включён доступ к Hotels API.
4. **Каталог** `app/data/hotel_rates_catalog.json` — fallback.

В карточке и в `breakdown_json.sources` видно: `flight` и `accommodation`. Статус интеграций: `/api/v1/refs/integrations`.

Booking.com / Airbnb — только партнёрские программы, не парсинг сайтов. Статус: `/api/v1/refs/integrations`.

## Тесты

```bash
pytest
```

## Docker (локально)

```bash
docker compose up --build
```

## Продакшен (voyago.bizml.ru)

Полная инструкция: **[deploy/DEPLOY.md](deploy/DEPLOY.md)**

Кратко на VPS:

```bash
git clone https://github.com/popovae77/VoyGo.git /opt/voyago
cd /opt/voyago
cp deploy/.env.production.example .env   # заполнить секреты
bash deploy/setup-server.sh
docker compose -f docker-compose.prod.yml up -d --build
```

После привязки DNS и получения SSL — `https://voyago.bizml.ru`.
