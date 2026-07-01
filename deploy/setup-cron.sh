#!/bin/bash
# ===========================================
# BizMap — Настройка еженедельного парсинга
# ===========================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "  Настройка cron для еженедельного парсинга"
echo "=========================================="
echo ""

CRON_SECRET=$(grep CRON_SECRET .env | cut -d= -f2)

if [ -z "$CRON_SECRET" ]; then
    echo "ОШИБКА: CRON_SECRET не найден в .env"
    exit 1
fi

CRON_CMD="0 3 * * 0 curl -s -X POST http://localhost:8000/api/cron/parse-and-cleanup -H \"Authorization: Bearer $CRON_SECRET\" >> /var/log/bizmap-cron.log 2>&1"

if crontab -l 2>/dev/null | grep -q "parse-and-cleanup"; then
    echo "Cron job уже существует, обновляю..."
    crontab -l | grep -v "parse-and-cleanup" | crontab -
fi

(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "Cron job добавлен:"
echo "  Каждое воскресенье в 3:00 UTC — парсинг всех категорий"
echo ""
echo "  Логи: tail -f /var/log/bizmap-cron.log"
echo ""
