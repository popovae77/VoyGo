#!/usr/bin/env bash
# Публичная ссылка на Voyago без открытия порта 80 (Cloudflare Tunnel).
set -euo pipefail

cd /opt/voyago
source .venv/bin/activate

pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 1

nohup uvicorn app.main:app --host 127.0.0.1 --port 8080 --workers 1 > /tmp/voyago.log 2>&1 &
sleep 3

if ! curl -sf http://127.0.0.1:8080/api/v1/health >/dev/null; then
  echo "Voyago не запустился. Лог:"
  tail -20 /tmp/voyago.log
  exit 1
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  curl -fsSL -o /tmp/cloudflared.deb \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  dpkg -i /tmp/cloudflared.deb || apt-get install -f -y
fi

pkill cloudflared 2>/dev/null || true
sleep 1
nohup cloudflared tunnel --url http://127.0.0.1:8080 > /tmp/cloudflared.log 2>&1 &

echo "Ждём публичную ссылку (до 30 сек)..."
for _ in $(seq 1 30); do
  url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cloudflared.log | head -1 || true)
  if [ -n "$url" ]; then
    echo ""
    echo "============================================"
    echo "ОТКРОЙТЕ В БРАУЗЕРЕ:"
    echo "$url"
    echo "============================================"
    echo ""
    echo "В .env на сервере поставьте:"
    echo "APP_PUBLIC_URL=$url"
    exit 0
  fi
  sleep 1
done

echo "Ссылка не появилась. Лог:"
tail -30 /tmp/cloudflared.log
exit 1
