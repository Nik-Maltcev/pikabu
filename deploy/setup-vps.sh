#!/bin/bash
# ===========================================
# BizMap — Автоматическая настройка VPS
# ===========================================
# Запускай от root на чистом Ubuntu 22.04/24.04:
#   chmod +x setup-vps.sh
#   ./setup-vps.sh
# ===========================================

set -e

echo ""
echo "=========================================="
echo "  BizMap VPS Setup"
echo "=========================================="
echo ""

# --- 1. Обновление системы ---
echo "[1/6] Обновляю систему..."
apt update && apt upgrade -y

# --- 2. Установка Docker ---
echo "[2/6] Устанавливаю Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    apt install -y docker-compose-plugin
    echo "Docker установлен!"
else
    echo "Docker уже есть, пропускаю."
fi

# --- 3. Создание директории проекта ---
echo "[3/6] Создаю директорию /opt/bizmap..."
mkdir -p /opt/bizmap
cd /opt/bizmap

# --- 4. Проверка наличия файлов ---
echo "[4/6] Проверяю файлы..."
if [ ! -f "docker-compose.yml" ]; then
    echo ""
    echo "ОШИБКА: Не найден docker-compose.yml в /opt/bizmap/"
    echo ""
    echo "Скопируй содержимое папки deploy/ на VPS:"
    echo "  scp -r deploy/* root@ТВОЙ_IP:/opt/bizmap/"
    echo ""
    exit 1
fi

if [ ! -f ".env" ]; then
    echo ""
    echo "ОШИБКА: Не найден .env в /opt/bizmap/"
    echo ""
    echo "Скопируй .env.example в .env и заполни:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    echo ""
    exit 1
fi

# --- 5. Создание nginx директорий ---
echo "[5/6] Подготавливаю nginx..."
mkdir -p nginx

# --- 6. Информация ---
echo "[6/6] Готово!"
echo ""
echo "=========================================="
echo "  Система готова! Следующие шаги:"
echo "=========================================="
echo ""
echo "  1. Убедись что .env заполнен (nano .env)"
echo ""
echo "  2. Скопируй код backend и frontend:"
echo "     scp -r path/to/backend root@IP:/opt/bizmap/backend"
echo "     scp -r path/to/frontend root@IP:/opt/bizmap/frontend"
echo ""
echo "  3. Запусти: ./start.sh"
echo ""
echo "=========================================="
