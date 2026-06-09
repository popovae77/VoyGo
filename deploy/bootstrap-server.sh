#!/usr/bin/env bash
# Однократная настройка VPS под автодеплой из GitHub.
set -euo pipefail

REPO_URL="${1:-https://github.com/popovae77/VoyGo.git}"
APP_DIR=/opt/voyago

apt-get update
apt-get install -y git curl

bash "$(dirname "$0")/setup-server.sh"

mkdir -p /opt
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
chmod +x deploy/deploy.sh

if [ ! -f .env ]; then
  cp deploy/.env.production.example .env
  echo ""
  echo "Создан $APP_DIR/.env — заполните SECRET_KEY и API-ключи:"
  echo "  nano $APP_DIR/.env"
  echo ""
fi

cp deploy/nginx/init.conf deploy/nginx/active.conf

systemctl stop docker 2>/dev/null || true
iptables -t nat -F 2>/dev/null || true
iptables -F 2>/dev/null || true

docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "Bootstrap готов. Дальше:"
echo "  1. Заполните .env на сервере"
echo "  2. Добавьте GitHub Secrets (см. deploy/DEPLOY.md)"
echo "  3. Push в main → деплой автоматически"
