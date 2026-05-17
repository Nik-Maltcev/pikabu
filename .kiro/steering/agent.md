# BizMap (Topic Analyzer) — Agent Context

## Описание проекта

**BizMap** — мультиплатформенный анализатор контента с трёх русскоязычных площадок: **Pikabu**, **Habr**, **VC.ru**. Собирает посты и комментарии, анализирует через LLM, генерирует структурированные отчёты для поиска бизнес-ниш и болей пользователей.

### Основные возможности
- Парсинг постов и комментариев с Pikabu, Habr, VC.ru
- Два режима анализа: `topic_analysis` (обзор темы) и `niche_search` (поиск бизнес-ниш)
- Автоматическое объединение одноимённых категорий с разных платформ
- Лимит бесплатных анализов (3 на устройство по fingerprint)
- Платный доступ через Robokassa
- SMS-авторизация через Twilio Verify
- Интеграция с MiroFish для экспорта данных

---

## Структура проекта

```
backend/
├── app/
│   ├── api/
│   │   ├── router.py          — REST API endpoints + background pipeline
│   │   ├── auth.py            — SMS авторизация (Twilio Verify + JWT)
│   │   ├── payment.py         — Robokassa интеграция (оплата отчётов)
│   │   ├── admin.py           — Админ API (просмотр задач, контактов)
│   │   └── cron.py            — Cron API (еженедельный парсинг, очистка)
│   ├── config.py              — Settings (env vars, pydantic-settings)
│   ├── database.py            — SQLAlchemy async engine + session
│   ├── main.py                — FastAPI app + startup (auto-migrate columns)
│   ├── models/
│   │   ├── database.py        — ORM models (Topic, Post, Comment, Report, AnalysisTask, User, Payment, DeviceLimit)
│   │   └── schemas.py         — Pydantic schemas (API + internal)
│   └── services/
│       ├── parser.py          — Pikabu parser (httpx + прокси, XML комментарии)
│       ├── habr_parser.py     — Habr parser (curl_cffi + Playwright для комментов)
│       ├── vcru_parser.py     — VC.ru parser (__INITIAL_STATE__ JSON + API пагинация)
│       ├── background_parser.py — Фоновый парсинг всех категорий + инкрементальный апдейт
│       ├── playwright_renderer.py — Headless Chromium для JS-рендеринга
│       ├── topic_manager.py   — Управление темами (Pikabu/Habr/VC.ru), поиск дубликатов
│       ├── task_queue.py      — Очередь задач с параллельным выполнением
│       ├── analyzer.py        — LLM анализ (DeepSeek, Gemini, GLM)
│       ├── chunker.py         — Разбиение данных на чанки (~4 chars/token)
│       ├── cache.py           — Кэширование результатов парсинга (TTL 24h)
│       ├── pipeline.py        — Утилиты пайплайна (_update_task, _load_posts_as_dicts)
│       └── mirofish_sender.py — Экспорт в MiroFish
├── alembic/                   — Миграции БД (PostgreSQL)
├── tests/                     — Тесты (pytest + hypothesis)
├── Dockerfile                 — Docker для Railway
└── requirements.txt           — Зависимости Python

frontend/
├── src/
│   ├── api/client.ts          — API клиент (axios)
│   ├── types/api.ts           — TypeScript интерфейсы
│   ├── pages/
│   │   ├── TopicSelector.vue  — Выбор источника и темы
│   │   ├── AnalysisProgress.vue — Прогресс анализа (polling)
│   │   ├── ReportView.vue     — Просмотр отчёта (free/paid sections)
│   │   ├── ReportHistory.vue  — История отчётов
│   │   ├── Account.vue        — Личный кабинет (SMS auth)
│   │   ├── Landing.vue        — Лендинг
│   │   ├── Pricing.vue        — Тарифы
│   │   ├── Privacy.vue        — Политика конфиденциальности
│   │   └── Terms.vue          — Условия использования
│   ├── utils/fingerprint.ts   — Browser fingerprint для rate limiting
│   └── router/index.ts        — Vue Router
├── public/
│   └── admin.html             — Админ-панель (статус очереди, контакты, БД)
├── Dockerfile                 — Docker для Railway
└── package.json               — Vue 3 + Vite + TailwindCSS 4
```

---

## Ключевые технические решения

### Парсеры

| Платформа | Библиотека | Особенности |
|-----------|------------|-------------|
| **Pikabu** | httpx + прокси | curl_cffi не работает с прокси в Docker. Комментарии через XML endpoint `generate_xml_comm.php` |
| **Habr** | curl_cffi | Listing через HTML, комментарии через Playwright (JS-рендеринг). Даты с `Z` → `+00:00` (Python 3.11) |
| **VC.ru** | curl_cffi | Данные в `__INITIAL_STATE__` JSON. Пагинация через `api.vc.ru/v2.8/timeline` с `lastId` |

### LLM провайдеры

```python
# Переключение через LLM_PROVIDER env var
"deepseek" → api.deepseek.com (deepseek-v4-flash)
"gemini"   → generativelanguage.googleapis.com (gemini-2.5-flash)
"glm"      → api.z.ai (glm-4.7-flash)
```

- OpenAI-совместимый API для всех провайдеров
- Иерархическая агрегация при превышении контекстного окна
- Автоматический repair truncated JSON

### База данных

- PostgreSQL + asyncpg + SQLAlchemy 2.0 async
- Единые таблицы для всех источников, различаются полем `source` (pikabu/habr/vcru)
- Auto-migrate missing columns в `main.py` startup

### Авторизация и платежи

- **Email/Password auth**: Простая регистрация без подтверждения email → JWT токен (30 дней)
- **Guest mode**: Можно запустить анализ без регистрации (указать контакт или подождать на странице)
- **Payments**: Robokassa с Shp_ параметрами для pre-analysis payments
- **Rate limiting**: 3 бесплатных анализа на fingerprint (DeviceLimit table)

---

## User Flow

```
1. Выбор категории (TopicSelector.vue)
   ↓
2. Выбор периода (14 или 30 дней)
   ↓
3. Модальное окно авторизации:
   - Войти (email + пароль)
   - Зарегистрироваться (без подтверждения email)
   - Продолжить без регистрации
   ↓
4. Выбор способа получения результата:
   - Подождать на странице
   - Отправить уведомление (email/telegram)
   ↓
5. Задача добавляется в очередь (status=queued)
   ↓
6. Пользователь видит прогресс на AnalysisProgress.vue
```

### Очередь задач (Parallel Queue)

Задачи выполняются **параллельно** с ограничением `MAX_CONCURRENT_ANALYSES` (по умолчанию 3):
- Первые 3 задачи стартуют сразу
- Остальные ждут освобождения слота
- Каждая задача занимает ~5-10 мин (с pre-parsed данными)

```python
# task_queue.py — Semaphore-based parallel execution
analysis_queue = AnalysisQueue()  # Singleton
await analysis_queue.enqueue(task_id, topic_id, coro_factory)
```

### Pre-Parsed Data Architecture

**Новая архитектура** для масштабирования на 1000+ пользователей:

```
ЕЖЕНЕДЕЛЬНО (cron job):
POST /api/cron/parse-and-cleanup → Парсит ВСЕ категории → Сохраняет в БД
                                                              ↓
ПО ЗАПРОСУ ПОЛЬЗОВАТЕЛЯ:
Берёт данные из БД → Инкрементальный апдейт комментов → LLM анализ → Отчёт
      ↓                        ↓
   мгновенно              ~1-2 мин (только новые комменты)
```

**Преимущества:**
- Время анализа: 10-20 мин → **5-10 мин**
- Нагрузка на Pikabu/Habr/VC.ru: при каждом запросе → **1 раз в неделю**
- Риск бана IP: высокий → **минимальный**
- Параллельность: ограничена парсингом → **только LLM лимиты**

---

## API Endpoints

### Topics & Analysis
```
GET  /api/topics?search=...              → TopicListResponse
POST /api/analysis/start                 → AnalysisStartResponse (requires contact_type + contact_value)
GET  /api/analysis/status/{task_id}      → AnalysisStatusResponse
GET  /api/reports/{topic_id}             → ReportListResponse
GET  /api/reports/{topic_id}/{report_id} → Report
GET  /api/posts/{topic_id}?days=N        → Posts with comments (for MiroFish)
POST /api/parse/start                    → Parse-only mode (no LLM)
POST /api/export/mirofish                → Export to MiroFish
```

### Auth
```
POST /api/auth/register                  → Register with email/password (no verification)
POST /api/auth/login                     → Login with email/password
GET  /api/auth/check                     → Check if token is valid
GET  /api/auth/me                        → Current user + reports
POST /api/auth/link-report               → Link report to user
```

### Payments
```
POST /api/payment/create                 → Create payment for report
POST /api/payment/create-for-analysis    → Create pre-analysis payment
POST /api/payment/result                 → Robokassa webhook
GET  /api/payment/success                → SuccessURL redirect
GET  /api/payment/check                  → Check payment status
GET  /api/payment/status/{inv_id}        → Poll payment status
```

### Utility
```
GET  /api/limit/check?fingerprint=...    → Check free analyses remaining
GET  /health                             → Health check
```

### Admin (просмотр контактов клиентов)
```
GET  /api/admin/tasks                    → Список задач с контактами
GET  /api/admin/contacts/export?format=csv → Экспорт контактов в CSV
GET  /api/admin/queue                    → Статус очереди анализа
GET  /api/admin/db-status                → Статус БД (посты, комменты)
```

### Cron (еженедельный парсинг)
```
POST /api/cron/parse-all                 → Запуск полного парсинга всех категорий
GET  /api/cron/parse-status              → Статус текущего парсинга
POST /api/cron/cleanup                   → Удаление постов старше N дней
POST /api/cron/parse-and-cleanup         → Парсинг + очистка (рекомендуемый cron job)
```

**Защита**: Все cron endpoints требуют `Authorization: Bearer <CRON_SECRET>`

**Админ-панель**: `/admin.html` — UI для просмотра задач, контактов, статуса БД

---

## Режимы анализа

### `topic_analysis` (обзор темы)
Выходные данные:
- `hot_topics` — популярные темы обсуждений
- `user_problems` — проблемы пользователей с примерами
- `trending_discussions` — активные дискуссии с ссылками

### `niche_search` (поиск ниш)
Выходные данные:
- `key_pains` — ключевые боли (frequency, emotional_charge)
- `jtbd_analyses` — JTBD разбор (situational, functional, emotional)
- `business_ideas` — бизнес-идеи с MVP планом, рисками, позиционированием
- `market_trends` — тренды с подсказками монетизации

---

## Переменные окружения

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# LLM
LLM_PROVIDER=deepseek|gemini|glm
LLM_API_KEY=...
LLM_MODEL=deepseek-v4-flash
GEMINI_API_KEY=...
GLM_API_KEY=...

# Pikabu proxy (РФ/BY IP required)
PIKABU_PROXY_URL=socks5://user:pass@host:port

# Robokassa
ROBOKASSA_LOGIN=...
ROBOKASSA_PASSWORD1=...
ROBOKASSA_PASSWORD2=...
ROBOKASSA_TEST_MODE=true|false
SITE_URL=https://your-frontend.com

# Auth
JWT_SECRET=your-jwt-secret-change-me

# Cron jobs
CRON_SECRET=your-secret-token  # Защита cron endpoints

# Concurrency
MAX_CONCURRENT_ANALYSES=3  # Макс. параллельных анализов

# CORS
CORS_ORIGINS=http://localhost:5173,https://your-frontend.com
```

---

## Частые проблемы и решения

| Проблема | Причина | Решение |
|----------|---------|---------|
| Pikabu 429 | IP забанен | Использовать прокси с РФ/BY IP |
| Habr комментарии пустые | Playwright timeout | Увеличить timeout, проверить статью |
| VC.ru 0 постов | CSS-селекторы не работают | Данные в `__INITIAL_STATE__` JSON |
| Railway `\n` в env var | Перенос строки в переменной | Перезаписать переменную |
| `column source does not exist` | Миграция не применена | Startup ALTER TABLE фиксит |
| LLM empty response | reasoning_content вместо content | Fallback на reasoning_content |
| Truncated JSON | max_tokens exceeded | `_repair_truncated_json()` |

---

## Команды разработки

```bash
# Backend тесты
cd backend && py -m pytest tests/ -v

# Локальный запуск backend
cd backend && uvicorn app.main:app --reload

# Локальный запуск frontend
cd frontend && npx vite

# Playwright browsers (для Habr/VC.ru комментариев)
playwright install chromium

# Alembic миграции
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "description"
```

---

## Архитектурные паттерны

### Background Analysis Pipeline (с pre-parsed данными)
```
1. POST /api/analysis/start
2. Create AnalysisTask (status=queued)
3. Добавить в analysis_queue (semaphore-based)
4. Проверить наличие данных в БД:
   - Если есть (≥10 постов) → Инкрементальный апдейт комментов (~1-2 мин)
   - Если нет → Полный парсинг (~5-10 мин)
5. Chunk data → Analyze chunks → Hierarchical aggregate
6. Save Report, update task status=completed
```

### Weekly Cron Job (pre-parsing)
```
# Railway/Render cron: раз в неделю (например, воскресенье 3:00 UTC)
curl -X POST https://your-backend.com/api/cron/parse-and-cleanup \
  -H "Authorization: Bearer YOUR_CRON_SECRET"

# Что делает:
1. Парсит ВСЕ категории (Pikabu + Habr + VC.ru) за 30 дней
2. Сохраняет посты и комментарии в БД
3. Удаляет посты старше 35 дней
```

### Incremental Comment Update
```python
# background_parser.py — BackgroundParser.update_comments_for_topic()
# Для каждого поста в БД:
1. Сравнить post.comments_count с количеством комментов в БД
2. Если есть новые → загрузить только новые комменты
3. Пропустить посты без изменений
# Результат: ~1-2 мин вместо 5-10 мин полного парсинга
```

### Cross-Platform Topic Matching
```python
# TopicManager.find_duplicates_by_name()
# Находит все темы с одинаковым названием на разных платформах
# Например: "Маркетинг" → pikabu + habr + vcru
```

### Chunking Strategy
```python
# ~4 chars per token (Cyrillic)
# max_tokens = settings.llm_chunk_size (default 20000)
# Posts never split across chunks
```

---

## Тестирование

- **pytest** + **hypothesis** для property-based тестов
- Моки для HTTP запросов и LLM API
- Тесты покрывают: parser, analyzer, chunker, cache, pipeline, API router, schemas

```bash
# Запуск всех тестов
cd backend && py -m pytest tests/ -v

# Конкретный тест
cd backend && py -m pytest tests/test_analyzer.py -v
```

---

## Frontend Stack

- **Vue 3** (Composition API)
- **Vue Router 5**
- **TailwindCSS 4** (Vite plugin)
- **Axios** для API
- **TypeScript**

### Ключевые страницы
- `TopicSelector.vue` — выбор платформы и категории
- `AnalysisProgress.vue` — polling статуса задачи
- `ReportView.vue` — отображение отчёта (free/paid секции)
- `Account.vue` — SMS авторизация и история отчётов
