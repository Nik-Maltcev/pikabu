#!/bin/bash
# ===========================================
# BizMap — Автоматическая настройка VPS
# ===========================================
# Запускай от root на чистом Ubuntu/Debian:
#   chmod +x setup-vps.sh
#   ./setup-vps.sh
# ===========================================

set -e

echo ""
echo "=========================================="
echo "  BizMap VPS Setup"
echo "=========================================="
echo ""

echo "[1/3] Обновляю систему..."
apt-get update && apt-get upgrade -y

echo "[2/3] Устанавливаю Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    echo "Docker установлен!"
else
    echo "Docker уже есть, пропускаю."
fi

echo "[3/3] Готово!"
echo ""
echo "=========================================="
echo "  Следующие шаги:"
echo "=========================================="
echo ""
echo "  1. cd /opt/bizmap/deploy"
echo "  2. cp .env.example .env && nano .env"
echo "  3. ./start.sh"
echo ""
