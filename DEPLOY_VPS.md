# Деплой на РФ VPS (Ubuntu 24.04) — без Docker

## 1. Подключаемся к серверу

```bash
ssh root@YOUR_SERVER_IP
```

## 2. Обновляем систему

```bash
apt update && apt upgrade -y
```

## 3. Устанавливаем зависимости

```bash
# Python 3.12+, pip, venv
apt install -y python3 python3-pip python3-venv

# PostgreSQL
apt install -y postgresql postgresql-contrib

# Node.js 20 (для сборки фронтенда)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Nginx (для проксирования)
apt install -y nginx

# Git
apt install -y git

# Утилиты
apt install -y curl wget htop
```

## 4. Настраиваем PostgreSQL

```bash
# Переключаемся на пользователя postgres
sudo -u postgres psql

# В psql выполняем:
CREATE USER pikabu WITH PASSWORD 'your_strong_password_here';
CREATE DATABASE pikabu_analyzer OWNER pikabu;
GRANT ALL PRIVILEGES ON DATABASE pikabu_analyzer TO pikabu;
\q
```

## 5. Создаём пользователя для приложения

```bash
adduser --system --group --home /opt/pikabu pikabu
```

## 6. Клонируем репозиторий

```bash
cd /opt/pikabu
sudo -u pikabu git clone https://github.com/Nik-Maltcev/pikabu.git app
cd app
```

## 7. Настраиваем бэкенд

```bash
cd /opt/pikabu/app/backend

# Создаём виртуальное окружение
sudo -u pikabu python3 -m venv venv

# Активируем
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Создаём .env файл
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://pikabu:your_strong_password_here@localhost:5432/pikabu_analyzer
LLM_API_KEY=your_dashscope_api_key_here
LLM_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
CORS_ORIGINS=http://YOUR_SERVER_IP,https://YOUR_DOMAIN
PIKABU_PROXY_URL=
EOF

# Редактируем .env — вставляем реальные значения
nano .env

deactivate
```

## 8. Собираем фронтенд

```bash
cd /opt/pikabu/app/frontend

# Устанавливаем зависимости
sudo -u pikabu npm ci

# Задаём URL бэкенда (замени YOUR_SERVER_IP или YOUR_DOMAIN)
export VITE_API_URL=http://YOUR_SERVER_IP/api

# Собираем
sudo -u pikabu npx vite build

# Результат в /opt/pikabu/app/frontend/dist/
```

## 9. Создаём systemd-сервис для бэкенда

```bash
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

# Включаем и запускаем
systemctl daemon-reload
systemctl enable pikabu-backend
systemctl start pikabu-backend

# Проверяем что работает
systemctl status pikabu-backend
curl http://127.0.0.1:8000/health
```

## 10. Настраиваем Nginx

```bash
cat > /etc/nginx/sites-available/pikabu << 'EOF'
server {
    listen 80;
    server_name YOUR_SERVER_IP;  # или YOUR_DOMAIN

    # Фронтенд (статика)
    root /opt/pikabu/app/frontend/dist;
    index index.html;

    # API проксирование к бэкенду
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    # SPA fallback — все остальные пути отдают index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

# Включаем сайт
ln -sf /etc/nginx/sites-available/pikabu /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверяем конфиг
nginx -t

# Перезапускаем
systemctl restart nginx
```

## 11. Открываем порты (если есть файрвол)

```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

## 12. Проверяем

Открой в браузере: `http://YOUR_SERVER_IP`

Должна открыться страница Pikabu Topic Analyzer.

---

## Обновление кода

```bash
cd /opt/pikabu/app
sudo -u pikabu git pull

# Бэкенд
cd backend
source venv/bin/activate
pip install -r requirements.txt
deactivate
systemctl restart pikabu-backend

# Фронтенд (если менялся)
cd ../frontend
sudo -u pikabu npm ci
export VITE_API_URL=http://YOUR_SERVER_IP/api
sudo -u pikabu npx vite build
# Nginx подхватит автоматически
```

## Логи

```bash
# Бэкенд
journalctl -u pikabu-backend -f

# Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

## HTTPS (опционально, если есть домен)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d YOUR_DOMAIN
# Certbot автоматически настроит SSL и обновит nginx конфиг
```
