#!/usr/bin/env bash
# Ручной деплой: git pull + перезапуск Voyago.
set -euo pipefail

cd /opt/voyago

git fetch origin main
git checkout main
git reset --hard origin/main

bash deploy/restart-native.sh
