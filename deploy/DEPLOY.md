# Деплой Voyago — voyago.ru

## Что нужно

| | |
|---|---|
| VPS | Timeweb Cloud, IP `176.124.212.74` |
| Домен | `voyago.ru` |
| GitHub | https://github.com/popovae77/VoyGo |

---

## Шаг 1. DNS (Timeweb → Домены → voyago.ru → Редактор DNS)

Две A-записи на IP сервера:

| Тип | Имя | Значение |
|-----|-----|----------|
| A | `voyago.ru` | `176.124.212.74` |
| A | `www.voyago.ru` | `176.124.212.74` |

---

## Шаг 2. Push кода на GitHub (на Mac)

GitHub Desktop → Commit → Push origin.

---

## Шаг 3. SSH на сервер (на Mac, Терминал)

```bash
ssh root@176.124.212.74
```

Пароль — из Timeweb Cloud → ваш сервер → root.

---

## Шаг 4. Установка (на сервере, по одной команде)

```bash
apt-get update && apt-get install -y git
```

```bash
rm -rf /opt/voyago
git clone https://github.com/popovae77/VoyGo.git /opt/voyago
cd /opt/voyago
```

```bash
bash deploy/setup-server.sh
```

---

## Шаг 5. Файл .env (на сервере)

```bash
cp deploy/.env.production.example .env
openssl rand -hex 32
```

Скопируйте вывод `openssl` — это `SECRET_KEY`.

```bash
nano .env
```

Заполните:

```env
SECRET_KEY=вставьте-ключ-из-openssl
APP_PUBLIC_URL=http://voyago.ru
CORS_ORIGINS=http://voyago.ru,http://www.voyago.ru
APP_DEBUG=false
TRAVELPAYOUTS_TOKEN=...
SERPAPI_API_KEY=...
GEMINI_API_KEY=...
```

Сохранить: **Ctrl+O** → Enter → **Ctrl+X**

---

## Шаг 6. Запуск

```bash
cd /opt/voyago
docker compose -f docker-compose.prod.yml up -d --build
```

Подождите 3–5 минут.

---

## Шаг 7. Проверка

- http://voyago.ru
- http://www.voyago.ru
- http://voyago.ru/api/v1/health

---

## Шаг 8. HTTPS (когда HTTP работает)

```bash
cd /opt/voyago
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d voyago.ru -d www.voyago.ru \
  --email voyago_trip@mail.ru \
  --agree-tos --no-eff-email

cp deploy/nginx/prod.conf deploy/nginx/active.conf
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

В `.env` смените на `https://voyago.ru` и перезапустите:

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## Обновление после изменений в коде

```bash
cd /opt/voyago
git pull
docker compose -f docker-compose.prod.yml up -d --build
```
