#!/usr/bin/env bash
# Одной командой: убрать Docker с 80 порта и поднять Voyago по IP.
set -euo pipefail

echo "=== 1. Останавливаем Docker (он часто вешает порт 80) ==="
systemctl stop docker 2>/dev/null || true
systemctl disable docker 2>/dev/null || true

echo "=== 2. Чистим iptables ==="
iptables -t nat -F 2>/dev/null || true
iptables -F 2>/dev/null || true

echo "=== 3. Освобождаем порт 80 ==="
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f docker-proxy 2>/dev/null || true
fuser -k 80/tcp 2>/dev/null || true
sleep 2

echo "=== 4. Запускаем Voyago на 0.0.0.0:80 ==="
cd /opt/voyago
if [ ! -f .venv/bin/uvicorn ]; then
  echo "Нет /opt/voyago/.venv — сначала: bash deploy/install-native.sh"
  exit 1
fi
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 80 --workers 1 > /tmp/voyago.log 2>&1 &
sleep 4

echo "=== 5. Проверка ==="
echo -n "localhost: "
curl -sf --max-time 5 http://127.0.0.1/api/v1/health && echo || { tail -15 /tmp/voyago.log; exit 1; }
echo -n "public IP:  "
curl -sf --max-time 5 http://176.124.212.74/api/v1/health && echo || echo "FAIL (с сервера)"

echo ""
ss -tlnp | grep ':80' || true
echo ""
echo "Откройте в браузере: http://176.124.212.74"
echo "Если с Mac всё ещё пусто — напишите в поддержку Timeweb: порт 80 принимает TCP, HTTP не отвечает снаружи."
