#!/bin/bash
# ===========================================
# BizMap — Получение SSL сертификата
# ===========================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "  Настройка SSL для BizMap"
echo "=========================================="
echo ""

read -p "Введи email для Let's Encrypt (для уведомлений об истечении): " SSL_EMAIL

if [ -z "$SSL_EMAIL" ]; then
    echo "ОШИБКА: email обязателен"
    exit 1
fi

echo ""
echo "[1/4] Ставлю временный nginx (без SSL)..."
cp nginx/nginx-initial.conf nginx/nginx.conf
docker compose up -d nginx
sleep 3

echo ""
echo "[2/4] Получаю SSL сертификат..."
docker compose run --rm certbot certonly \
    --webroot \
    -w /var/www/certbot \
    -d www.bizmap.space \
    -d bizmap.space \
    -d api.bizmap.space \
    --email "$SSL_EMAIL" \
    --agree-tos \
    --no-eff-email

echo ""
echo "[3/4] Переключаю на SSL конфиг..."
cp nginx/nginx-ssl.conf nginx/nginx.conf
docker compose restart nginx

echo ""
echo "[4/4] Проверяю..."
sleep 3

if curl -sf https://www.bizmap.space > /dev/null 2>&1; then
    echo "SSL работает! https://www.bizmap.space"
else
    echo "Подожди минуту и проверь: curl https://www.bizmap.space"
fi

echo ""
echo "=========================================="
echo "  SSL настроен! Сертификат обновляется автоматически."
echo "=========================================="
echo ""
