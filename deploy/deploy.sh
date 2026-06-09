#!/usr/bin/env bash
# Пересборка и перезапуск контейнеров (вызывается вручную или из GitHub Actions).
set -euo pipefail

cd /opt/voyago

git fetch origin
git checkout main
git pull --ff-only origin main

docker compose -f docker-compose.prod.yml up -d --build --remove-orphans
docker image prune -f

echo "Ждём healthcheck..."
for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1/api/v1/health >/dev/null 2>&1; then
    curl -s http://127.0.0.1/api/v1/health
    echo ""
    echo "Deploy OK"
    exit 0
  fi
  sleep 2
done

echo "Healthcheck failed. Логи API:"
docker compose -f docker-compose.prod.yml logs api --tail 40
exit 1
