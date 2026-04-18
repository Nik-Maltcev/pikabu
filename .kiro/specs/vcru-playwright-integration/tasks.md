# План реализации: Интеграция VC.ru + Playwright

## Обзор

Поэтапная реализация интеграции VC.ru и Playwright в существующую систему Topic Analyzer. Порядок задач обеспечивает инкрементальную сборку: зависимости → рендерер → парсер → категории → обновление Habr → API → pipeline → схемы → фронтенд → тесты.

## Задачи

- [ ] 1. Добавить playwright в зависимости и создать PlaywrightRenderer
  - [x] 1.1 Добавить `playwright` в `backend/requirements.txt`
    - Добавить строку `playwright>=1.40.0` в файл зависимостей
    - _Требования: 8.1_

  - [x] 1.2 Создать модуль `backend/app/services/playwright_renderer.py`
    - Реализовать класс `PlaywrightRenderer` как async context manager (`__aenter__`, `__aexit__`)
    - В `__aenter__`: запуск `async_playwright()` и `chromium.launch(headless=True)`
    - В `__aexit__`: закрытие браузера и остановка playwright (даже при исключении)
    - Метод `render_page(url, wait_selector, timeout=30000)` — открывает страницу, ждёт селектор, возвращает HTML
    - При timeout или ошибке — возвращать пустую строку, логировать warning
    - _Требования: 3.1, 3.2, 3.3, 3.6, 3.7, 3.8, 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 1.3 Написать property-тест для жизненного цикла PlaywrightRenderer
    - **Свойство 9: Жизненный цикл контекстного менеджера PlaywrightRenderer**
    - **Проверяет: Требования 10.1, 10.2, 10.4**
    - Example-based тест с моком Playwright: проверить что браузер запускается при входе и закрывается при выходе (включая выход по исключению)

- [ ] 2. Создать VcruParserService
  - [x] 2.1 Создать модуль `backend/app/services/vcru_parser.py`
    - Реализовать класс `VcruParserService` по аналогии с `HabrParserService`
    - Конструктор принимает `AsyncSession`
    - Метод `parse_topic(topic_id, callback, days)` — основной метод парсинга категории
    - Внутри `parse_topic`: создать один `PlaywrightRenderer` контекст для всех статей
    - Метод `parse_posts(category_url, since)` — загрузка статей через curl_cffi с пагинацией `?page=N`
    - Метод `parse_comments(article_url, renderer)` — загрузка комментариев через PlaywrightRenderer
    - Статический метод `_extract_posts_from_html(html)` — извлечение статей из HTML
    - Статический метод `_extract_comments_from_html(html)` — извлечение комментариев из HTML
    - ID статей: `vcru_{article_id}`, ID комментариев: `vcru_comment_{comment_id}`
    - Все посты сохраняются с `source="vcru"`
    - Retry-логика: HTTP 429 (60 сек, 5 попыток), 5xx (10 сек, 3 попытки), сетевые ошибки (15 сек, 3 попытки)
    - CSS-селекторы для listing: `div.feed__item, article.l-entry`, `a.content-link`, `h2.content-title` и т.д.
    - CSS-селекторы для комментариев: `.comment, .comments__item`, `.comment__text`, `.comment__date time[datetime]`
    - DB-хелперы: `_save_post`, `_save_comment`, `_update_parse_metadata` (аналогично HabrParserService)
    - _Требования: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 2.2 Написать property-тест для формирования идентификаторов
    - **Свойство 4: Форматирование идентификаторов сущностей**
    - **Проверяет: Требования 2.3, 3.5**
    - Генерация случайных числовых ID → проверка формата `vcru_{id}` и `vcru_comment_{id}`

  - [ ]* 2.3 Написать property-тест для извлечения данных статьи из HTML
    - **Свойство 3: Извлечение данных статьи из HTML**
    - **Проверяет: Требования 2.2**
    - Генерация HTML-фрагментов с известными значениями полей → проверка корректного извлечения

  - [ ]* 2.4 Написать property-тест для извлечения данных комментария из HTML
    - **Свойство 6: Извлечение данных комментария из HTML**
    - **Проверяет: Требования 3.4**
    - Генерация HTML-фрагментов комментариев с известными значениями → проверка извлечения

  - [ ]* 2.5 Написать property-тест для остановки пагинации по дате
    - **Свойство 5: Остановка пагинации по дате**
    - **Проверяет: Требования 2.6**
    - Генерация случайных дат и cutoff → проверка решения о прекращении пагинации

- [ ] 3. Добавить VCRU_CATEGORIES в TopicManager
  - [x] 3.1 Обновить `backend/app/services/topic_manager.py`
    - Добавить константу `VCRU_CATEGORIES` — список из 39 категорий VC.ru: ai, apple, apps, ask, books, chatgpt, crypto, design, dev, education, flood, food, future, growth, hr, invest, legal, life, marketing, marketplace, media, migration, money, office, offline, opinions, retail, seo, services, social, story, tech, telegram, transport, travel, tribuna, video, workdays
    - Каждая категория: `{"pikabu_id": "vcru_{slug}", "name": "...", "url": "https://vc.ru/{slug}", "subscribers_count": None, "source": "vcru"}`
    - Обновить метод `fetch_topics`: добавить поддержку `source="vcru"` и `source="all"`
    - `source="all"` возвращает темы из всех источников (pikabu + habr + vcru)
    - Обратная совместимость: `source="both"` продолжает работать (pikabu + habr)
    - Обновить метод `_all_topics`: добавить фильтрацию по `source="vcru"` и `source="all"`
    - _Требования: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 3.2 Написать property-тест для формирования URL категории
    - **Свойство 1: Формирование URL категории**
    - **Проверяет: Требования 1.2**
    - Генерация случайных slug → проверка формата `https://vc.ru/{slug}`

  - [ ]* 3.3 Написать property-тест для фильтрации тем по источнику
    - **Свойство 2: Фильтрация тем по источнику**
    - **Проверяет: Требования 1.4, 1.5**
    - Генерация наборов Topic с разными source → проверка корректности фильтрации

- [ ] 4. Checkpoint — Проверка базовых компонентов
  - Убедиться, что все тесты проходят: `py -m pytest backend/tests/ -x -q`
  - Спросить пользователя, если возникнут вопросы.

- [ ] 5. Обновить HabrParserService для использования PlaywrightRenderer
  - [x] 5.1 Обновить `backend/app/services/habr_parser.py`
    - Изменить метод `parse_comments`: добавить опциональный параметр `renderer: PlaywrightRenderer | None = None`
    - Если renderer передан — использовать `renderer.render_page(url, ".tm-comment-thread__comment", timeout=30000)` вместо `_fetch_page`
    - Если renderer не передан — использовать `_fetch_page` как раньше (обратная совместимость)
    - Изменить метод `parse_topic`: создать `PlaywrightRenderer` контекст и передавать renderer в `parse_comments`
    - `parse_posts` остаётся без изменений (curl_cffi для listing pages)
    - При timeout PlaywrightRenderer — логировать warning, продолжить обработку
    - _Требования: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 5.2 Написать unit-тесты для обновлённого HabrParserService
    - Проверить что `parse_comments` использует renderer когда он передан
    - Проверить что `parse_comments` использует `_fetch_page` когда renderer=None
    - Проверить обработку timeout от PlaywrightRenderer

- [ ] 6. Обновить Pydantic-схемы
  - [x] 6.1 Обновить `backend/app/models/schemas.py`
    - Добавить поле `vcru_topic_id: int | None = None` в `AnalysisStartRequest`
    - _Требования: 7.5_

  - [ ]* 6.2 Написать property-тест для валидации запроса source="all"
    - **Свойство 7: Валидация запроса source="all"**
    - **Проверяет: Требования 7.4**
    - Генерация случайных комбинаций None/int для topic_id, habr_topic_id, vcru_topic_id → проверка валидации

- [ ] 7. Обновить API (router.py)
  - [x] 7.1 Обновить `backend/app/api/router.py`
    - `GET /api/topics`: добавить поддержку `source="vcru"` и `source="all"` в параметре source
    - `POST /api/analysis/start`: добавить валидацию `vcru_topic_id`
    - При `source="all"`: требовать `habr_topic_id` и `vcru_topic_id` (HTTP 400 если отсутствуют)
    - При `source="vcru"`: использовать `topic_id` как ID категории VC.ru
    - Передать `vcru_topic_id` в `_run_analysis_background`
    - _Требования: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 7.2 Написать unit-тесты для обновлённых API-эндпоинтов
    - Тест GET /api/topics?source=vcru
    - Тест POST /api/analysis/start с source="vcru"
    - Тест POST /api/analysis/start с source="all" без vcru_topic_id → 400
    - _Требования: 7.1, 7.2, 7.3, 7.4_

- [ ] 8. Обновить pipeline (_run_analysis_background)
  - [x] 8.1 Обновить функцию `_run_analysis_background` в `backend/app/api/router.py`
    - Добавить параметр `vcru_topic_id: int | None = None`
    - Добавить ветку `source="vcru"`: вызов `VcruParserService.parse_topic`
    - Обновить ветку `source="all"`: последовательный вызов ParserService, HabrParserService, VcruParserService
    - Обновить `sources_label`: "vcru" для source="vcru", "pikabu,habr,vcru" для source="all"
    - Загрузка постов VC.ru через `_load_posts_as_dicts(session, vcru_topic_id)` и добавление к общему списку
    - Прогресс для source="all": Pikabu 0-17%, Habr 17-34%, VC.ru 34-50%, анализ 50-85%, агрегация 85-100%
    - _Требования: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 9. Checkpoint — Проверка бэкенда
  - Убедиться, что все тесты проходят: `py -m pytest backend/tests/ -x -q`
  - Спросить пользователя, если возникнут вопросы.

- [ ] 10. Обновить фронтенд
  - [x] 10.1 Обновить `frontend/src/types/api.ts`
    - Добавить `vcru_topic_id?: number` в `AnalysisStartRequest`
    - _Требования: 7.5_

  - [x] 10.2 Обновить `frontend/src/api/client.ts`
    - Добавить параметр `vcruTopicId?: number` в функцию `startAnalysis`
    - Передавать `vcru_topic_id` в теле запроса если указан
    - _Требования: 7.5_

  - [x] 10.3 Обновить `frontend/src/pages/TopicSelector.vue`
    - Расширить `SourceMode`: `'pikabu' | 'habr' | 'vcru' | 'all'`
    - Добавить кнопку "VC.ru" и "Все" в source selector (4 кнопки вместо 3)
    - Добавить ref `vcruTopics` и `selectedVcruTopic`
    - Режим "vcru": загрузка и отображение категорий VC.ru (source="vcru")
    - Режим "all": три колонки (Pikabu, Habr, VC.ru), grid `1fr 1fr 1fr 320px`
    - Обновить `canStartAnalysis`: для "all" требовать выбор из всех трёх источников
    - Обновить `onStartAnalysis`: передавать `vcruTopicId` в `startAnalysis`
    - Добавить CSS-стили для badge `ts-source-badge--vcru` (оранжевый/тёплый цвет)
    - _Требования: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 10.4 Обновить `frontend/src/pages/ReportView.vue`
    - Обновить `sourcesLabel`: добавить маппинг "vcru" → "VC.ru", "pikabu,habr,vcru" → "Pikabu + Habr + VC.ru"
    - Обновить `sourcesBadgeClass`: добавить класс `rv-src-badge--vcru`
    - Обновить `postPlatformLabel`: добавить проверку `vc.ru` → "Открыть на VC.ru ↗"
    - Добавить CSS-стили для `rv-src-badge--vcru`
    - _Требования: 9.1, 9.2, 9.3_

  - [ ]* 10.5 Написать property-тест для маппинга sources в метку
    - **Свойство 8: Маппинг sources в отображаемую метку**
    - **Проверяет: Требования 9.2, 9.3**
    - Перебор всех валидных значений sources → проверка корректной человекочитаемой строки

- [ ] 11. Финальный checkpoint — Полная проверка
  - Убедиться, что все тесты проходят: `py -m pytest backend/tests/ -x -q`
  - Спросить пользователя, если возникнут вопросы.

## Примечания

- Задачи с `*` — опциональные (тесты), могут быть пропущены для ускорения MVP
- Каждая задача ссылается на конкретные требования для трассируемости
- Checkpoints обеспечивают инкрементальную валидацию
- Property-тесты проверяют универсальные свойства корректности из дизайн-документа
- Миграция БД не требуется — существующее поле `source` поддерживает значение "vcru"
- Для запуска тестов используется `py -m pytest`
