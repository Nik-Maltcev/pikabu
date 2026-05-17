# Topic Analyzer

Мультиплатформенный анализатор контента — собирает посты и комментарии с Pikabu, Habr и VC.ru, анализирует через LLM и генерирует отчёты с горячими темами, проблемами пользователей и трендовыми дискуссиями.

## Возможности

- **3 источника данных**: Pikabu (22 темы), Habr (3 потока), VC.ru (38 категорий)
- **4 режима анализа**: Pikabu / Habr / VC.ru / Все (комбинированный)
- **Парсинг постов и комментариев**: Pikabu (XML API), Habr (Playwright), VC.ru (Playwright + JSON API)
- **LLM-анализ**: поддержка GPT-4o-mini, DeepSeek, Gemini, GLM (Z.AI)
- **Чанкинг**: автоматическое разбиение данных на чанки по ~50K токенов
- **Иерархическая агрегация**: анализ чанков → объединение в итоговый отчёт
- **Отчёты**: горячие темы, проблемы пользователей, трендовые дискуссии с ссылками
- **Кэширование**: повторный анализ не требует перепарсинга (TTL 24 часа)
- **Retry-логика**: 429, 5xx, сетевые ошибки — автоматические повторы с backoff

## Стек

### Backend
- **Python 3.12** + **FastAPI** — REST API
- **SQLAlchemy 2.0** (async) + **asyncpg** — ORM и PostgreSQL
- **Alembic** — миграции БД
- **BeautifulSoup4** — парсинг HTML
- **curl_cffi** — HTTP-клиент с Chrome TLS fingerprint (для Habr, VC.ru)
- **httpx** — HTTP-клиент с поддержкой прокси (для Pikabu)
- **Playwright** — headless Chromium для JS-рендеринга комментариев
- **Hypothesis** — property-based тестирование

### Frontend
- **Vue 3** + **TypeScript** — SPA
- **Vue Router** — маршрутизация
- **Axios** — HTTP-клиент
- **Vite** — сборка

### Инфраструктура
- **PostgreSQL** — база данных
- **Nginx** — reverse proxy (VPS) или Railway (Docker)
- **Docker** — контейнеризация для Railway
- **Railway** — хостинг (backend + frontend + PostgreSQL)

## Архитектура

```
Frontend (Vue 3)
    ↓ REST API
Backend (FastAPI)
    ├── ParserService (Pikabu) → httpx + прокси
    ├── HabrParserService (Habr) → curl_cffi + Playwright (комменты)
    ├── VcruParserService (VC.ru) → curl_cffi + JSON API + Playwright (комменты)
    ├── Chunker → разбиение на чанки ~50K токенов
    ├── AnalyzerService → LLM (GPT-4o-mini / DeepSeek / Gemini / GLM)
    └── PostgreSQL → посты, комментарии, отчёты
```

## API Endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/topics?source=pikabu\|habr\|vcru\|all` | Список тем |
| POST | `/api/analysis/start` | Запуск анализа |
| GET | `/api/analysis/status/{task_id}` | Статус анализа |
| GET | `/api/reports/{topic_id}` | Список отчётов |
| GET | `/api/reports/{topic_id}/{report_id}` | Конкретный отчёт |
| GET | `/health` | Проверка здоровья |

## Переменные окружения

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host/db` |
| `LLM_PROVIDER` | Провайдер LLM: deepseek, gemini, glm | `deepseek` |
| `LLM_API_KEY` | API ключ LLM (DeepSeek/OpenAI) | `sk-...` |
| `LLM_BASE_URL` | Base URL LLM API | `https://api.openai.com/v1` |
| `LLM_MODEL` | Модель LLM | `gpt-4o-mini` |
| `GEMINI_API_KEY` | API ключ Google Gemini | `AIza...` |
| `GLM_API_KEY` | API ключ Z.AI (GLM) | `...` |
| `PIKABU_PROXY_URL` | Прокси для Pikabu (РФ) | `http://user:pass@host:port` |
| `CORS_ORIGINS` | Разрешённые origins | `https://frontend.railway.app` |

## Локальный запуск

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # настроить переменные
uvicorn app.main:app --reload

# Frontend
cd frontend
npm ci
VITE_API_URL=http://localhost:8000/api npx vite
```

## Деплой на Railway

1. Создать проект с двумя сервисами (backend, frontend) + PostgreSQL addon
2. Backend: root directory = `backend`, Dockerfile
3. Frontend: root directory = `frontend`, Dockerfile
4. Настроить переменные окружения
5. `VITE_API_URL` для frontend = URL backend сервиса + `/api`

## Деплой на VPS

```bash
wget -O setup.sh https://raw.githubusercontent.com/Nik-Maltcev/pikabu/main/setup_vps.sh
bash setup.sh IP ПАРОЛЬ_БД LLM_КЛЮЧ
```

## Тесты

```bash
cd backend
py -m pytest tests/ -v
```
