#!/usr/bin/env bash
# Запуск без Docker (pip внутри контейнера на Timeweb часто таймаутит).
set -euo pipefail

cd /opt/voyago

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

systemctl stop docker 2>/dev/null || true
pkill -f docker-proxy 2>/dev/null || true
pkill -f "uvicorn app.main:app" 2>/dev/null || true
fuser -k 80/tcp 2>/dev/null || true
sleep 2

nohup uvicorn app.main:app \
  --host 0.0.0.0 --port 80 --workers 1 \
  --proxy-headers --forwarded-allow-ips='*' \
  > /tmp/voyago.log 2>&1 &

sleep 3
curl -sf http://127.0.0.1/api/v1/health
echo ""
echo "Native deploy OK"
