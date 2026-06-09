#!/usr/bin/env bash
# Включить автодеплой: каждые 3 минуты сервер проверяет GitHub и пересобирает.
set -euo pipefail

chmod +x /opt/voyago/deploy/auto-pull.sh /opt/voyago/deploy/deploy.sh /opt/voyago/deploy/restart-native.sh

CRON_LINE='*/3 * * * * root /opt/voyago/deploy/auto-pull.sh >> /var/log/voyago-deploy.log 2>&1'

echo "$CRON_LINE" > /etc/cron.d/voyago-deploy
chmod 644 /etc/cron.d/voyago-deploy

touch /var/log/voyago-deploy.log

echo "Готово. Каждые 3 минуты после push в main — автопересборка."
echo "Лог: tail -f /var/log/voyago-deploy.log"
