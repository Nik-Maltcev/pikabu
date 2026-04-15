#!/bin/bash
# Pikabu Topic Analyzer — автоустановка на Ubuntu 24.04
# Запуск: bash setup_vps.sh YOUR_DOMAIN_OR_IP YOUR_DB_PASSWORD YOUR_DASHSCOPE_API_KEY
#
# Пример: bash setup_vps.sh 185.123.45.67 MyStr0ngPass sk-abc123def456

set -e

HOST="${1:?Укажи IP или домен: bash setup_vps.sh HOST DB_PASS LLM_KEY}"
DB_PASS="${2:?Укажи пароль БД: bash setup_vps.sh HOST DB_PASS LLM_KEY}"
LLM_KEY="${3:?Укажи DashScope API ключ: bash setup_vps.sh HOST DB_PASS LLM_KEY}"

echo "=== Pikabu Topic Analyzer — установка ==="
echo "Host: $HOST"

# 1. Системные пакеты
echo ">>> Установка пакетов..."
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git curl
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# 2. PostgreSQL
echo ">>> Настройка PostgreSQL..."
sudo -u postgres psql -c "CREATE USER pikabu WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE pikabu_analyzer OWNER pikabu;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pikabu_analyzer TO pikabu;" 2>/dev/null || true

# 3. Пользователь и код
echo ">>> Клонирование репозитория..."
id -u pikabu &>/dev/null || adduser --system --group --home /opt/pikabu pikabu
mkdir -p /opt/pikabu
cd /opt/pikabu
if [ -d app ]; then
  cd app && sudo -u pikabu git pull && cd ..
else
  sudo -u pikabu git clone https://github.com/Nik-Maltcev/pikabu.git app
fi

# 4. Бэкенд
echo ">>> Настройка бэкенда..."
cd /opt/pikabu/app/backend
sudo -u pikabu python3 -m venv venv
sudo -u pikabu venv/bin/pip install -r requirements.txt

cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://pikabu:${DB_PASS}@localhost:5432/pikabu_analyzer
LLM_API_KEY=${LLM_KEY}
LLM_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
CORS_ORIGINS=http://${HOST},https://${HOST}
PIKABU_PROXY_URL=
EOF
chown pikabu:pikabu .env

# 5. Фронтенд
echo ">>> Сборка фронтенда..."
cd /opt/pikabu/app/frontend
sudo -u pikabu npm ci
VITE_API_URL="http://${HOST}/api" sudo -u pikabu npx vite build

# 6. Systemd сервис
echo ">>> Создание systemd сервиса..."
cat > /etc/systemd/system/pikabu-backend.service << 'EOF'
[Unit]
Description=Pikabu Topic Analyzer Backend
After=network.target postgresql.service
[Service]
Type=simple
User=pikabu
Group=pikabu
WorkingDirectory=/opt/pikabu/app/backend
Environment=PATH=/opt/pikabu/app/backend/venv/bin:/usr/bin
ExecStart=/opt/pikabu/app/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pikabu-backend
systemctl restart pikabu-backend

# 7. Nginx
echo ">>> Настройка Nginx..."
cat > /etc/nginx/sites-available/pikabu << NGINXEOF
server {
    listen 80;
    server_name ${HOST};
    root /opt/pikabu/app/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 300s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/pikabu /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# 8. Файрвол
echo ">>> Настройка файрвола..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Проверка
echo ""
echo "=== ГОТОВО ==="
sleep 2
HEALTH=$(curl -s http://127.0.0.1:8000/health)
echo "Backend health: $HEALTH"
echo ""
echo "Открой в браузере: http://${HOST}"
echo ""
echo "Логи: journalctl -u pikabu-backend -f"
echo "Для HTTPS: apt install certbot python3-certbot-nginx && certbot --nginx -d ${HOST}"
