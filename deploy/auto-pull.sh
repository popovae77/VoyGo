#!/usr/bin/env bash
# Автодеплой: сервер проверяет GitHub и перезапускает Voyago (без Docker).
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
git reset --hard origin/main
bash deploy/restart-native.sh
echo "[$(date -Iseconds)] Deploy OK"
