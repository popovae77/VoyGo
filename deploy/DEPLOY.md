# Деплой Voyago в прод (voyago.bizml.ru)

## Что нужно заранее

| Что | Пример |
|-----|--------|
| VPS (Ubuntu 22.04+) | Timeweb, Selectel, Reg.ru, Hetzner |
| Домен | `voyago.bizml.ru` |
| Доступ по SSH | `root@IP_СЕРВЕРА` |
| Репозиторий | https://github.com/popovae77/VoyGo |

Минимум сервера: **1 CPU, 1 GB RAM, 10 GB SSD**.

---

## 1. DNS

В панели домена `bizml.ru` (Mail.ru / biz.mail.ru):

- Тип: **A**
- Имя: **voyago** (или `@` если нужен корень)
- Значение: **IP вашего VPS**

Подождите 5–30 минут. Проверка:

```bash
ping voyago.bizml.ru
```

---

## 2. Подключение к серверу

```bash
ssh root@ВАШ_IP
```

---

## 3. Docker

```bash
apt-get update && apt-get install -y git
git clone https://github.com/popovae77/VoyGo.git /opt/voyago
cd /opt/voyago
bash deploy/setup-server.sh
```

---

## 4. Файл `.env` на сервере

```bash
cd /opt/voyago
cp deploy/.env.production.example .env
nano .env
```

Обязательно заполните:

```env
SECRET_KEY=...          # openssl rand -hex 32
APP_PUBLIC_URL=https://voyago.bizml.ru
CORS_ORIGINS=https://voyago.bizml.ru
APP_DEBUG=false
TRAVELPAYOUTS_TOKEN=...
SERPAPI_API_KEY=...
GEMINI_API_KEY=...      # или GROQ_API_KEY
EMAIL_PROVIDER=brevo    # или smtp на VPS
BREVO_API_KEY=...
```

Сгенерировать `SECRET_KEY`:

```bash
openssl rand -hex 32
```

---

## 5. Первый запуск (HTTP)

```bash
cd /opt/voyago
docker compose -f docker-compose.prod.yml up -d --build
```

Проверка: откройте `http://voyago.bizml.ru` — должен открыться Voyago.

Healthcheck: `http://voyago.bizml.ru/api/v1/health`

---

## 6. SSL (HTTPS)

```bash
cd /opt/voyago

docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d voyago.bizml.ru \
  --email voyago_trip@mail.ru \
  --agree-tos \
  --no-eff-email

cp deploy/nginx/prod.conf deploy/nginx/active.conf
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

Проверка: `https://voyago.bizml.ru`

---

## 7. Обновление после изменений в GitHub

```bash
cd /opt/voyago
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Полезные команды

```bash
# Логи приложения
docker compose -f docker-compose.prod.yml logs -f api

# Статус
docker compose -f docker-compose.prod.yml ps

# Остановить
docker compose -f docker-compose.prod.yml down

# Бэкап базы SQLite
docker compose -f docker-compose.prod.yml exec api cat /app/data/voyago.db > voyago-backup.db
```

---

## Почта на проде

1. **Brevo (рекомендуется)** — `EMAIL_PROVIDER=brevo`, ключ в `BREVO_API_KEY`
2. **Mail.ru SMTP** — на VPS часто работает, если домашний провайдер блокировал порты

---

## Если другой домен

Замените `voyago.bizml.ru` в:

- `deploy/nginx/init.conf`
- `deploy/nginx/prod.conf`
- `deploy/nginx/active.conf`
- `.env` → `APP_PUBLIC_URL`, `CORS_ORIGINS`
