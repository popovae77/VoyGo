#!/usr/bin/env bash
# Автодеплой без входящего SSH: сервер сам проверяет GitHub и пересобирает.
set -euo pipefail

cd /opt/voyago

git fetch origin main 2>/dev/null || exit 0

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0
fi

echo "[$(date -Iseconds)] Новый коммит $REMOTE — деплой..."
git checkout main
git pull --ff-only origin main
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans
docker image prune -f
echo "[$(date -Iseconds)] Deploy OK"
