#!/bin/bash
# ===========================================
# BizMap — Запуск всех сервисов
# ===========================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "  Запускаю BizMap..."
echo "=========================================="
echo ""

if [ ! -f ".env" ]; then
    echo "ОШИБКА: Нет файла .env"
    echo "Скопируй: cp .env.example .env && nano .env"
    exit 1
fi

if [ ! -d "../backend" ]; then
    echo "ОШИБКА: Нет папки backend/"
    exit 1
fi

if [ ! -d "../frontend" ]; then
    echo "ОШИБКА: Нет папки frontend/"
    exit 1
fi

echo "[1/3] Собираю и запускаю контейнеры..."
docker compose up -d --build

echo ""
echo "[2/3] Жду пока postgres поднимется..."
sleep 10

echo ""
echo "[3/3] Проверяю здоровье..."
sleep 5

if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend работает!"
else
    echo "Backend ещё стартует, подожди 30 сек и проверь:"
    echo "  curl http://localhost:8000/health"
fi

if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "Frontend работает!"
else
    echo "Frontend ещё стартует, подожди 30 секунд."
fi

echo ""
echo "=========================================="
echo "  BizMap запущен!"
echo "=========================================="
echo ""
echo "  Логи:     docker compose logs -f"
echo "  Стоп:     docker compose down"
echo "  Рестарт:  docker compose restart"
echo ""
