#!/usr/bin/env bash
# Voyago на сервере без Docker (если docker build падает на pip).
set -euo pipefail

cd /opt/voyago

apt-get update
apt-get install -y python3 python3-venv python3-pip curl

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install --timeout 300 --retries 10 -r requirements.txt

mkdir -p data

cat > /etc/systemd/system/voyago.service << 'EOF'
[Unit]
Description=Voyago
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/voyago
EnvironmentFile=/opt/voyago/.env
ExecStart=/opt/voyago/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80 --workers 2 --proxy-headers --forwarded-allow-ips *
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable voyago
systemctl restart voyago

echo "Готово. Проверка:"
sleep 3
curl -s http://127.0.0.1/api/v1/health || true
echo ""
echo "Откройте http://voyago.ru"
