# Техническое задание (ТЗ)
## Веб-сервис «Voyago» — планирование путешествия по бюджету и типу отдыха

**Версия:** 1.1  
**Стек:** Python 3.11+, FastAPI, **SQLite**, **SQLAlchemy 2.x**, Alembic, Pydantic, JWT  
**Формат:** MVP (минимально рабочая версия для курсовой и демонстрации)

---

## 1. Назначение и цель проекта

### 1.1. Назначение
Разработать единый веб-сервис, который помогает пользователю:
- подобрать путешествие под **бюджет**;
- учесть **тип отдыха** и личные параметры;
- получить **уведомления** о выгодных и «горящих» предложениях;
- не переключаться между множеством сайтов и Telegram-каналов.

### 1.2. Цель MVP
Сделать рабочий прототип «для людей»: простой интерфейс, понятный результат («укладывается / не укладывается в бюджет»), базовые уведомления.

### 1.3. Целевая аудитория
- пользователи 18–45 лет, самостоятельно планирующие поездки;
- люди с ограниченным бюджетом, ищущие выгодные варианты;
- пользователи, уставшие от разрозненных сервисов и каналов.

---

## 2. Проблема, которую решает сервис

| Сейчас | В Voyago |
|--------|----------|
| Много сайтов бронирования | Один сервис |
| Ручной расчёт бюджета | Автоматический расчёт |
| Десятки Telegram-каналов | Встроенные уведомления |
| Не учитывается тип отдыха | Фильтр по типу отдыха |
| Сложно понять итоговую цену | Понятный итог и альтернативы |

---

## 3. Типы отдыха (обязательный справочник)

В системе фиксируется enum `TravelType`:

| Код | Название |
|-----|----------|
| `beach` | Пляжный |
| `active` | Активный |
| `excursion` | Экскурсионный |
| `city` | Городской |
| `family` | Семейный |
| `cruise` | Круиз (опционально в MVP) |
| `other` | Другой |

Пользователь выбирает тип при создании запроса на подбор поездки.

---

## 4. Функциональные требования

### 4.1. Модуль пользователей
- Регистрация (email + пароль).
- Авторизация (JWT access token, опционально refresh).
- Профиль: имя, email, предпочитаемая валюта (RUB по умолчанию).
- Личный кабинет: сохранённые поездки, история поиска, настройки уведомлений.

### 4.2. Модуль подбора путешествия
Пользователь создаёт **запрос на подбор** (`TripRequest`) с полями:
- страна / город (строка или id из справочника);
- дата начала, дата окончания;
- количество человек;
- бюджет (число);
- тип отдыха (`TravelType`);
- уровень комфорта: `economy` | `standard` | `comfort` (опционально).

**Результат подбора:**
- список вариантов (туры / самостоятельная поездка);
- расчёт итоговой стоимости;
- флаг: `fits_budget: true/false`;
- при превышении бюджета — 2–3 альтернативы (сдвиг дат, другой отель, меньше дней).

### 4.3. Модуль расчёта бюджета
Алгоритм считает:
1. Перелёт (из mock/API).
2. Проживание (ночей × цена за ночь).
3. Питание (средняя суточная ставка × дни × люди).
4. Транспорт на месте (фикс. коэффициент по типу отдыха).
5. Экскурсии/активности (коэффициент по `TravelType`).
6. Страховка (процент от базы, опционально).
7. Резерв 10% (настраиваемо).

**Формула (MVP, упрощённо):**
```
total = flight + hotel + food + local_transport + activities + insurance + reserve
fits_budget = total <= user_budget
```

Коэффициенты по типу отдыха хранить в конфиге/БД (таблица `travel_type_coefficients`).

### 4.4. Модуль уведомлений
- Пользователь подписывается на уведомления по сохранённому запросу/поездке.
- Фоновая задача (cron / APScheduler) периодически проверяет цены (mock или API).
- Если цена снизилась ≥ X% или появилось «горящее» предложение — создать `Notification`.
- Каналы MVP: **in-app** (список в ЛК) + **email** (опционально) + заглушка Telegram.

### 4.5. Избранное и история
- Сохранить вариант в избранное.
- История последних N поисков (например, 20).

### 4.6. Админ (минимум, опционально)
- Просмотр пользователей и логов уведомлений (через простую admin-страницу или Swagger tags).

---

## 5. Нефункциональные требования

| Параметр | Требование MVP |
|----------|----------------|
| Время ответа API | ≤ 2 с для расчёта (без внешнего API), ≤ 5 с с API |
| Доступность | 95% (локально/хостинг) |
| Безопасность | HTTPS, хеш паролей (bcrypt), JWT |
| Масштабируемость | Разделение frontend/backend, Docker |
| Локализация | RU (интерфейс и сообщения) |

---

## 6. Технологический стек

### Backend
- **FastAPI** — REST API
- **Uvicorn** — ASGI-сервер
- **SQLAlchemy 2.x** — ORM
- **Alembic** — миграции
- **Pydantic v2** — схемы запросов/ответов
- **python-jose** или **PyJWT** — JWT
- **passlib[bcrypt]** — пароли
- **APScheduler** или **Celery+Redis** (для MVP достаточно APScheduler)
- **httpx** — запросы к внешним API

### База данных
- **SQLite 3** — один файл `data/voyago.db` (удобно для курсовой, не нужен отдельный сервер БД)
- **SQLAlchemy 2.x** — ORM (модели, сессии, запросы)
- **Alembic** — миграции схемы

### Frontend (на выбор)
- Простой **HTML + Jinja2** (быстрее для курсовой), или
- **React/Vue** (если есть время)

### Инфраструктура
- **Docker** (опционально, только API) или запуск локально через `uvicorn`
- `.env` для секретов
- папка `data/` для файла SQLite (добавить в `.gitignore`)

---

## 6.1. SQLite + SQLAlchemy (как подключить)

### Рекомендация для MVP: синхронный режим
Проще для старта и курсовой. FastAPI-роуты могут быть `def` (не `async`) или обёртка через `run_in_threadpool`.

**URL подключения:**
```env
DATABASE_URL=sqlite:///./data/voyago.db
```

### Файл `app/core/database.py` (базовый шаблон)
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./data/voyago.db"

# check_same_thread=False обязателен для SQLite + FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Файл `app/main.py` (создание таблиц при старте, MVP)
```python
from app.core.database import Base, engine
# импортировать все модели, чтобы они зарегистрировались в Base.metadata
import app.models  # noqa: F401

Base.metadata.create_all(bind=engine)
```

### Alembic с SQLite
- Инициализация: `alembic init alembic`
- В `alembic/env.py` указать тот же `DATABASE_URL`
- Для изменений схемы в SQLite иногда нужен `render_as_batch=True` в `alembic.ini` / `context.configure`

### Типы полей в моделях (важно для SQLite)
| Поле | SQLAlchemy |
|------|------------|
| PK | `Integer, primary_key=True, autoincrement=True` |
| деньги | `Numeric(12, 2)` |
| enum | `String` или `Enum(...)` |
| JSON | `JSON` (SQLite поддерживает) |
| даты | `Date`, `DateTime` |

### Запуск без Docker
```bash
mkdir -p data
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Опционально: async-режим (если захочешь позже)
```env
DATABASE_URL=sqlite+aiosqlite:///./data/voyago.db
```
Тогда добавить `aiosqlite` в `requirements.txt` и использовать `AsyncSession`.

---

## 7. Структура проекта (рекомендуемая)

```
voyago/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/
│   │   ├── user.py
│   │   ├── trip.py
│   │   ├── notification.py
│   │   └── favorite.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── trip.py
│   │   └── notification.py
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── trips.py
│   │       ├── budget.py
│   │       ├── favorites.py
│   │       └── notifications.py
│   ├── services/
│   │   ├── budget_calculator.py
│   │   ├── trip_matcher.py
│   │   ├── price_monitor.py
│   │   └── notifier.py
│   └── tasks/
│       └── scheduler.py
├── data/
│   └── voyago.db          # создаётся автоматически (в .gitignore)
├── alembic/
├── tests/
├── .gitignore             # data/*.db, .venv, .env
├── docker-compose.yml     # опционально
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 8. Модель данных (ER, MVP)

### `users`
| Поле | Тип |
|------|-----|
| id | Integer PK, autoincrement |
| email | unique |
| password_hash | string |
| full_name | string, nullable |
| currency | string, default RUB |
| created_at | datetime |

### `trip_requests`
| Поле | Тип |
|------|-----|
| id | PK |
| user_id | FK → users |
| destination | string |
| start_date | date |
| end_date | date |
| people_count | int |
| budget | decimal |
| travel_type | enum |
| comfort_level | enum, nullable |
| created_at | datetime |

### `trip_offers` (результаты подбора / кэш)
| Поле | Тип |
|------|-----|
| id | PK |
| trip_request_id | FK |
| title | string |
| total_price | decimal |
| fits_budget | bool |
| breakdown_json | JSON (детализация расходов) |
| source | string (mock/api) |

### `favorites`
| user_id, offer_id | unique together |

### `notifications`
| id | PK |
| user_id | FK |
| trip_request_id | FK, nullable |
| message | text |
| is_read | bool |
| sent_at | datetime |

### `price_alerts` (подписки)
| user_id | FK |
| trip_request_id | FK |
| threshold_percent | int (например 5) |
| is_active | bool |

---

## 9. API (основные эндпоинты)

### Auth
| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/v1/auth/register` | Регистрация |
| POST | `/api/v1/auth/login` | Логин → JWT |
| GET | `/api/v1/auth/me` | Текущий пользователь |

### Trips & Budget
| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/v1/trips/search` | Создать запрос + расчёт + варианты |
| GET | `/api/v1/trips/requests` | История запросов |
| GET | `/api/v1/trips/requests/{id}` | Детали запроса |
| POST | `/api/v1/trips/requests/{id}/recalculate` | Пересчёт с новыми параметрами |

### Favorites
| POST | `/api/v1/favorites/{offer_id}` | В избранное |
| GET | `/api/v1/favorites` | Список избранного |
| DELETE | `/api/v1/favorites/{offer_id}` | Удалить |

### Notifications
| GET | `/api/v1/notifications` | Список уведомлений |
| PATCH | `/api/v1/notifications/{id}/read` | Прочитано |
| POST | `/api/v1/alerts` | Подписка на уведомления по запросу |

### Справочники
| GET | `/api/v1/refs/travel-types` | Типы отдыха |
| GET | `/api/v1/health` | Healthcheck |

Документация: **Swagger** `/docs`, **ReDoc** `/redoc`.

---

## 10. Бизнес-логика расчёта (детально для разработки)

### Вход (`TripSearchCreate`)
```python
destination: str
start_date: date
end_date: date
people_count: int = Field(ge=1, le=10)
budget: Decimal
travel_type: TravelType
comfort_level: ComfortLevel | None = "standard"
```

### Шаги `BudgetCalculatorService`
1. `days = (end_date - start_date).days`
2. Получить базовые цены: `flight_price`, `hotel_per_night` (из `PricingProvider`).
3. `hotel = hotel_per_night * days`
4. `food = daily_food_rate(destination) * days * people_count`
5. `transport = base_transport * coeff[travel_type]`
6. `activities = base_activities * coeff[travel_type]`
7. `insurance = (flight + hotel) * 0.03`
8. `subtotal = sum(...)`
9. `reserve = subtotal * 0.10`
10. `total = subtotal + reserve`
11. Сформировать `BudgetBreakdown` и `fits_budget`.

### Альтернативы если не влезает в бюджет
- сдвиг дат ±3/7 дней;
- понижение `comfort_level`;
- уменьшение `days` на 1–2;
- вернуть top-3 варианта с наименьшим `total`.

---

## 11. Интеграции (этапами)

### Этап 1 — MVP без внешних API
- `MockPricingProvider` — фиксированные/рандомные цены по стране.
- Достаточно для курсовой и демо.

### Этап 2 — реальные API (по желанию)
- Авиа: Aviasales / Skyscanner API (или заглушка).
- Отели: Booking/другой агрегатор.
- Важно: вынести в интерфейс `PricingProvider`, чтобы менять источник без переписывания логики.

---

## 12. Фоновые задачи

**Задача `check_price_alerts`** (каждые 30–60 мин):
1. Выбрать активные `price_alerts`.
2. Для каждого пересчитать `total` через `PricingProvider`.
3. Если `new_total <= old_total * (1 - threshold/100)` → создать уведомление.
4. Отправить через `NotifierService` (in-app + email stub).

---

## 13. Требования к интерфейсу (MVP)

### Главная
- форма: куда, даты, люди, бюджет, тип отдыха;
- кнопка «Подобрать».

### Результаты
- карточки вариантов;
- итоговая сумма;
- бейдж «В бюджете» / «Выше бюджета»;
- раскрывающаяся детализация расходов.

### Личный кабинет
- сохранённые поездки;
- избранное;
- уведомления (список + «прочитано»);
- переключатель подписки на алерты.

### UX-принципы
- минимум полей на первом экране;
- понятные подписи на русском;
- без перегруза «как старые сайты бронирования».

---

## 14. Безопасность

- Пароли: bcrypt, не хранить в открытом виде.
- JWT: `SECRET_KEY` в `.env`, срок access token 24ч (MVP).
- CORS: только разрешённые origin фронта.
- Валидация входных данных через Pydantic.
- Rate limit на `/auth/login` (опционально).

---

## 15. Тестирование

### Минимум для сдачи
- `pytest` + `httpx.AsyncClient`
- тесты:
  - регистрация/логин;
  - расчёт бюджета (в бюджете / не в бюджете);
  - создание уведомления при снижении цены (mock);
  - CRUD избранного.

---

## 16. Этапы разработки (по неделям)

| Неделя | Задачи | Результат |
|--------|--------|-----------|
| 1 | Репозиторий, SQLite + SQLAlchemy, модели, миграции | Проект поднимается, `voyago.db` создаётся |
| 2 | Auth (register/login/JWT), профиль | Пользователи работают |
| 3 | `BudgetCalculatorService`, `/trips/search` | Расчёт и подбор |
| 4 | Favorites, history, travel types | ЛК базовый |
| 5 | Notifications + scheduler | Алерты работают |
| 6 | Frontend (форма + результаты + ЛК) | Демо в браузере |
| 7 | Тесты, README, деплой локально | Готово к защите |

---

## 17. Критерии приёмки MVP

Сервис считается готовым (MVP), если:
1. Пользователь регистрируется и входит.
2. Создаёт запрос с бюджетом и типом отдыха.
3. Получает расчёт и список вариантов с `fits_budget`.
4. Видит детализацию расходов.
5. Сохраняет вариант в избранное.
6. Получает хотя бы одно in-app уведомление о снижении цены (через mock/тест).
7. API документировано в Swagger.
8. Проект запускается локально (`uvicorn`) или через Docker; БД — файл SQLite.

---

## 18. Переменные окружения (.env.example)

```env
DATABASE_URL=sqlite:///./data/voyago.db
SECRET_KEY=change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
TELEGRAM_BOT_TOKEN=
PRICING_PROVIDER=mock
```

---

## 19. Пример `requirements.txt` (старт)

```txt
fastapi>=0.110
uvicorn[standard]>=0.27
sqlalchemy>=2.0
alembic>=1.13
pydantic>=2.6
pydantic-settings>=2.2
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
httpx>=0.27
apscheduler>=3.10
pytest>=8.0
pytest-asyncio>=0.23
```

---

## 20. Что сказать на защите курсовой + проекта

«Voyago — единый сервис на FastAPI: пользователь вводит бюджет и тип отдыха, получает расчёт и варианты в одном месте, а система сама присылает уведомления о выгодных предложениях. Это замена неудобной схеме с десятками сайтов и Telegram-каналов.»

---

## 21. Следующий шаг (если начинаешь код сейчас)

1. Создать репозиторий `voyago-backend`.
2. Настроить `database.py` + папку `data/` (SQLite).
3. Реализовать модели SQLAlchemy + `users` + `auth`.
4. Реализовать `BudgetCalculatorService` + `/trips/search`.
5. Подключить простую HTML-страницу для демо.

Могу следующим сообщением сгенерировать **скелет проекта FastAPI + SQLite + SQLAlchemy** (`main.py`, `database.py`, модели, роуты).
