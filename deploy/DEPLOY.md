# Деплой Voyago — vayago.ru

| | |
|---|---|
| VPS | Timeweb Cloud, `176.124.212.74` |
| Домен | `vayago.ru` |
| GitHub | https://github.com/popovae77/VoyGo |

После настройки: **каждый push в `main` → автопересборка Docker на сервере** (через 1–3 минуты).

> **SSH с Mac на сервер часто не работает** (таймаут на Timeweb) — это нормально.  
> Автодеплой идёт **с сервера наружу** в GitHub, входящий SSH не нужен.

---

## 1. DNS (Timeweb hosting → Домены → vayago.ru → Редактор DNS)

| Тип | Имя | Значение |
|-----|-----|----------|
| A | `@` | `176.124.212.74` |
| A | `www` | `176.124.212.74` |

---

## 2. Один раз на сервере (консоль Timeweb Cloud)

```bash
apt-get update && apt-get install -y git
git clone https://github.com/popovae77/VoyGo.git /opt/voyago
cd /opt/voyago
bash deploy/bootstrap-server.sh
```

### `.env` на сервере

```bash
cp deploy/.env.production.example .env
openssl rand -hex 32
nano .env
```

Вставьте `SECRET_KEY`, API-ключи (Travelpayouts, SerpApi, Gemini).  
Почта **без RuSender**: SMTP Mail.ru + `APP_DEBUG=true` (ссылка сброса пароля на экране).

---

## 3. Автодеплой (на сервере, один раз)

В консоли Timeweb:

```bash
cd /opt/voyago
bash deploy/install-auto-pull.sh
```

Сервер **каждые 3 минуты** проверяет GitHub. Если есть новый коммит в `main` → `git pull` + `docker compose up -d --build`.

Лог деплоя:

```bash
tail -f /var/log/voyago-deploy.log
```

### GitHub Actions (опционально)

Работает только если SSH с интернета на сервер доступен. Если `ssh root@176.124.212.74` с Mac даёт timeout — используйте **auto-pull** выше, Secrets в GitHub не обязательны.

---

## 4. Как обновлять сайт

```bash
git add .
git commit -m "..."
git push origin main
```

Через 1–3 минуты сервер сам подтянет код и пересоберёт контейнеры.

Ручной деплой (консоль Timeweb):

```bash
cd /opt/voyago && bash deploy/deploy.sh
```

---

## 5. Проверка

- http://vayago.ru
- http://vayago.ru/api/v1/health

Ручной деплой на сервере:

```bash
cd /opt/voyago && bash deploy/deploy.sh
```

---

## 6. HTTPS (когда HTTP работает)

```bash
cd /opt/voyago
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d vayago.ru -d www.vayago.ru \
  --email voyago_trip@mail.ru \
  --agree-tos --no-eff-email

cp deploy/nginx/prod.conf deploy/nginx/active.conf
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

В `.env`: `APP_PUBLIC_URL=https://vayago.ru`, затем push или `bash deploy/deploy.sh`.

---

## Два `.env` — не путать

| Файл | Где |
|------|-----|
| `.env` на Mac | локальная разработка, `127.0.0.1:8000` |
| `/opt/voyago/.env` на VPS | прод, `vayago.ru` |

Шаблоны: `.env.example` (Mac) и `deploy/.env.production.example` (сервер).
