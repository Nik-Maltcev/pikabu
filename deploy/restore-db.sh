#!/bin/bash
# ===========================================
# BizMap — Скачивание и восстановление БД из Railway
# ===========================================
# Использование: ./restore-db.sh "postgresql://user:pass@host:port/db"
# ===========================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DUMP_FILE="bizmap.dump"
RAILWAY_DB_URL="${1:-}"

echo ""
echo "=========================================="
echo "  Скачивание и восстановление БД BizMap"
echo "=========================================="
echo ""

# --- Скачать дамп из Railway ---
if [ ! -f "$DUMP_FILE" ]; then
    if [ -z "$RAILWAY_DB_URL" ]; then
        echo "ИСПОЛЬЗОВАНИЕ: ./restore-db.sh \"postgresql://user:pass@host:port/db\""
        echo ""
        echo "Вставь DATABASE_PUBLIC_URL из Railway -> Postgres -> Variables"
        echo ""
        exit 1
    fi
    echo "[0/3] Скачиваю базу данных из Railway..."
    echo "(Это может занять 1-5 минут)"
    echo ""
    docker run --rm -v "$SCRIPT_DIR":/dump postgres:16-alpine \
        pg_dump "$RAILWAY_DB_URL" \
        --no-owner --no-acl -Fc \
        -f /dump/bizmap.dump
    echo ""
    echo "Дамп скачан!"
    echo ""
else
    echo "Файл $DUMP_FILE уже есть, пропускаю скачивание."
fi

echo "Размер дампа: $(du -h $DUMP_FILE | cut -f1)"
echo ""

# --- Убедимся что postgres запущен ---
echo "[1/3] Проверяю что postgres работает..."
if ! docker compose ps postgres 2>/dev/null | grep -q "running"; then
    echo "Запускаю postgres..."
    docker compose up -d postgres
    sleep 5
fi

# --- Восстановление ---
echo "[2/3] Восстанавливаю базу данных..."
echo "(Это может занять 1-5 минут)"
echo ""

docker compose exec -T postgres pg_restore \
    -U bizmap \
    -d bizmap \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    < "$DUMP_FILE" 2>&1 || true

echo ""
echo "[3/3] Проверяю..."

POSTS=$(docker compose exec -T postgres psql -U bizmap -d bizmap -t -c "SELECT COUNT(*) FROM posts;" 2>/dev/null | tr -d ' ')
COMMENTS=$(docker compose exec -T postgres psql -U bizmap -d bizmap -t -c "SELECT COUNT(*) FROM comments;" 2>/dev/null | tr -d ' ')
TOPICS=$(docker compose exec -T postgres psql -U bizmap -d bizmap -t -c "SELECT COUNT(*) FROM topics;" 2>/dev/null | tr -d ' ')

echo ""
echo "=========================================="
echo "  БД восстановлена!"
echo "=========================================="
echo ""
echo "  Темы:        $TOPICS"
echo "  Посты:       $POSTS"
echo "  Комментарии: $COMMENTS"
echo ""
