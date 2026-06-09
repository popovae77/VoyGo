#!/usr/bin/env bash
# Почта: SMTP на VPS обычно блокируется. Включаем ссылку сброса на экране + правильный URL.
set -euo pipefail

ENV_FILE=/opt/voyago/.env
PUBLIC_URL="${1:-http://176.124.212.74}"

set_var() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

set_var APP_PUBLIC_URL "$PUBLIC_URL"
set_var APP_DEBUG true

echo "=== .env (почта) ==="
grep -E '^(APP_PUBLIC_URL|APP_DEBUG|EMAIL_PROVIDER|BREVO_API_KEY|SMTP_)' "$ENV_FILE" || true

echo ""
echo "=== Перезапуск Voyago ==="
pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 1
cd /opt/voyago && source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 80 --workers 1 > /tmp/voyago.log 2>&1 &
sleep 3

echo ""
echo "Готово. Снова нажмите «Забыли пароль?» — ссылка появится на экране."
echo ""
echo "Для реальных писем (российский сервис, без ссылки на экране):"
echo "  RuSender (рекомендуется):"
echo "    1. https://beta.rusender.ru/api → API-ключ"
echo "    2. Подтвердите домен vayago.ru в RuSender"
echo "    3. В .env: EMAIL_PROVIDER=rusender, RUSENDER_API_KEY=..., SMTP_FROM=Voyago <noreply@vayago.ru>"
echo "  UniSender Go:"
echo "    1. https://go.unisender.ru → API-ключ"
echo "    2. В .env: EMAIL_PROVIDER=unisender, UNISENDER_API_KEY=..."
echo "  4. APP_DEBUG=false и перезапуск"
