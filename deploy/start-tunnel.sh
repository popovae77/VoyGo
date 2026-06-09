#!/usr/bin/env bash
# Публичная ссылка на Voyago (Cloudflare Tunnel). Работает, если порт 80 снаружи закрыт.
set -euo pipefail

cd /opt/voyago

# Voyago на localhost:80
if ! curl -sf http://127.0.0.1/api/v1/health >/dev/null; then
  bash deploy/restart-native.sh
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  curl -fsSL -o /tmp/cloudflared.deb \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  dpkg -i /tmp/cloudflared.deb || apt-get install -f -y
fi

pkill cloudflared 2>/dev/null || true
sleep 1
nohup cloudflared tunnel --url http://127.0.0.1:80 > /tmp/cloudflared.log 2>&1 &

echo "Ждём ссылку (до 40 сек)..."
for _ in $(seq 1 40); do
  url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cloudflared.log | head -1 || true)
  if [ -n "$url" ]; then
    echo ""
    echo "============================================"
    echo "ОТКРОЙТЕ В БРАУЗЕРЕ:"
    echo "$url"
    echo "============================================"
    echo ""
    echo "В .env на сервере:"
    echo "  APP_PUBLIC_URL=$url"
    echo "  CORS_ORIGINS=$url"
    echo ""
    echo "Потом: bash deploy/restart-native.sh"
    exit 0
  fi
  sleep 1
done

echo "Ссылка не появилась. Лог:"
tail -30 /tmp/cloudflared.log
exit 1
