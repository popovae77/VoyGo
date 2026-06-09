#!/usr/bin/env bash
# Быстрый systemd-сервис Voyago без Docker (после fix-ip-access.sh можно не использовать).
set -euo pipefail

cat > /etc/systemd/system/voyago.service << 'EOF'
[Unit]
Description=Voyago
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/voyago
EnvironmentFile=/opt/voyago/.env
ExecStart=/opt/voyago/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80 --workers 1 --proxy-headers --forwarded-allow-ips=*
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable voyago
systemctl restart voyago
sleep 3
systemctl status voyago --no-pager || true
curl -sf http://127.0.0.1/api/v1/health && echo
