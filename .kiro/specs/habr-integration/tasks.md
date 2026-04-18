# План реализации: Интеграция Habr

## Обзор

Расширение сервиса «Pikabu Topic Analyzer» поддержкой habr.com. Порядок: миграция БД → ORM/схемы → парсер Habr → TopicManager → API → пайплайн → фронтенд → тесты.

## Задачи

- [x] 1. Миграция БД: добавить колонку source
  - [x] 1.1 Создать Alembic-миграцию для добавления колонки `source` в таблицы `topics`, `posts` и `reports`
    - Добавить `source VARCHAR(20) NOT NULL DEFAULT 'pikabu'` в таблицу `topics`
    - Добавить `source VARCHAR(20) NOT NULL DEFAULT 'pikabu'` в таблицу `posts`
    - Добавить `sources VARCHAR(50) NOT NULL DEFAULT 'pikabu'` в таблицу `reports`
    - Создать индексы `idx_topics_source` и `idx_posts_source`
    - Существующие записи автоматически получат значение `'pikabu'` через DEFAULT
    - _Требования: 5.2, 7.4_

- [ ] 2. Обновить ORM-модели и Pydantic-схемы
  - [x] 2.1 Добавить поле `source` в ORM-модели `Topic`, `Post` и `Report`
    - `Topic.source = Column(String(20), nullable=False, default="pikabu")`
    - `Post.source = Column(String(20), nullable=False, default="pikabu")`
    - `Report.sources = Column(String(50), nullable=False, default="pikabu")`
    - _Требования: 5.2, 7.4_
  - [ ] 2.2 Обновить Pydantic-схемы в `backend/app/models/schemas.py`
    - Добавить `source: str = "pikabu"` в `Topic`
    - Добавить `source: str = "pikabu"` и `habr_topic_id: int | None = None` в `AnalysisStartRequest`
    - Добавить `sources: str = "pikabu"` в `Report`
    - _Требования: 7.1, 8.3, 8.4_

- [x] 3. Контрольная точка
  - Убедиться, что миграция применяется без ошибок, существующие тесты проходят. Спросить пользователя при возникновении вопросов.

- [ ] 4. Создать HabrParserService
  - [x] 4.1 Создать файл `backend/app/services/habr_parser.py` с классом `HabrParserService`
    - Реализовать `__init__(self, session: AsyncSession)`
    - Реализовать `parse_topic(self, topic_id, callback, days)` — основной метод парсинга потока Habr
    - Реализовать `parse_posts(self, flow_url, since)` — извлечение статей из страницы потока с пагинацией
    - Реализовать `parse_comments(self, article_url)` — извлечение комментариев со страницы статьи
    - Реализовать `_fetch_page(self, url)` — HTTP-запрос с retry-логикой (429 → пауза 60 сек, 5xx → до 3 повторов через 10 сек), без прокси
    - Реализовать `_save_post`, `_save_comment`, `_update_parse_metadata` — аналогично `ParserService`
    - _Требования: 3.1, 3.2, 3.3, 3.5, 3.6, 3.7, 3.8, 4.1, 4.2, 4.3, 5.1, 5.4_
  - [x] 4.2 Реализовать статические методы парсинга HTML для Habr
    - `_extract_posts_from_html(html)` — CSS-селекторы: `article.tm-articles-list__item`, `a.tm-title__link`, `time[datetime]`, `.tm-votes-meter__value`, `.tm-article-comments-counter-link__value`
    - `_extract_comments_from_html(html)` — CSS-селекторы: `.tm-comment-thread__comment`, `.tm-comment__body-content`, `.tm-comment-datetime time[datetime]`, `.tm-votes-lever__score-count`
    - Реализовать early-exit при пагинации: прекращать загрузку, когда все статьи на странице старше `since`
    - URL пагинации: `https://habr.com/ru/flows/{name}/articles/page{N}/`
    - _Требования: 3.4, 9.1, 9.2, 9.3, 9.4_
  - [ ]* 4.3 Написать property-тест: полнота извлечения данных статей
    - **Свойство 3: Полнота извлечения данных статей**
    - Генерировать HTML с случайными статьями Habr, парсить, проверять наличие всех обязательных полей
    - **Проверяет: Требования 3.2, 9.1, 9.4**
  - [ ]* 4.4 Написать property-тест: ранний выход при устаревших статьях
    - **Свойство 4: Ранний выход при устаревших статьях**
    - Генерировать страницы с датами, проверять прекращение пагинации
    - **Проверяет: Требования 3.4**
  - [ ]* 4.5 Написать property-тест: полнота извлечения комментариев
    - **Свойство 5: Полнота извлечения комментариев**
    - Генерировать HTML с комментариями Habr, парсить, проверять наличие обязательных полей
    - **Проверяет: Требования 4.2, 9.2**
  - [ ]* 4.6 Написать property-тест: round-trip парсинга статей
    - **Свойство 9: Round-trip парсинга статей**
    - Генерировать данные статей → HTML → парсинг → сравнение (title, url, rating)
    - **Проверяет: Требования 9.5**

- [ ] 5. Обновить TopicManager
  - [x] 5.1 Добавить `HABR_FLOWS` и фильтрацию по `source` в `backend/app/services/topic_manager.py`
    - Добавить предопределённый список `HABR_FLOWS` с потоками: management, top_management, marketing
    - Каждый поток: `pikabu_id` с префиксом `habr_`, URL по шаблону `https://habr.com/ru/flows/{name}/articles/`, `source="habr"`
    - Расширить `fetch_topics(source="pikabu")` — при `"pikabu"` текущее поведение, при `"habr"` — только Habr-потоки, при `"both"` — всё
    - Обновить `_upsert_topics` для поддержки поля `source`
    - Обновить `_all_topics` и `_get_cached_topics` для фильтрации по `source`
    - _Требования: 2.1, 2.2, 2.3, 2.4, 1.3, 1.4, 1.5_
  - [ ]* 5.2 Написать property-тест: фильтрация тем по источнику
    - **Свойство 1: Фильтрация тем по источнику**
    - Генерировать случайные списки тем с разными `source`, проверять корректность фильтрации
    - **Проверяет: Требования 1.4, 1.5, 8.1**
  - [ ]* 5.3 Написать property-тест: валидность формата потоков Habr
    - **Свойство 2: Валидность формата потоков Habr**
    - Проверить предопределённый список: `pikabu_id` с префиксом `habr_`, URL по шаблону, все обязательные поля
    - **Проверяет: Требования 2.2, 2.3, 2.4**

- [ ] 6. Контрольная точка
  - Убедиться, что все тесты проходят, парсер и TopicManager работают корректно. Спросить пользователя при возникновении вопросов.

- [ ] 7. Обновить API endpoints
  - [x] 7.1 Обновить `GET /api/topics` в `backend/app/api/router.py`
    - Добавить query-параметр `source: str = "pikabu"` (значения: `"pikabu"`, `"habr"`, `"both"`)
    - Передать `source` в `TopicManager.fetch_topics(source=source)`
    - При отсутствии параметра — возвращать только Pikabu-темы (обратная совместимость)
    - Обновить `_topic_to_schema` для передачи поля `source`
    - _Требования: 8.1, 8.2_
  - [x] 7.2 Обновить `POST /api/analysis/start` в `backend/app/api/router.py`
    - Принимать поля `source` и `habr_topic_id` из расширенного `AnalysisStartRequest`
    - Валидация: при `source="habr"` или `"both"` без `habr_topic_id` → HTTP 400
    - Передать `source` и `habr_topic_id` в фоновую задачу `_run_analysis_background`
    - _Требования: 8.3, 8.4, 8.5_
  - [x] 7.3 Обновить `_report_to_schema` для передачи поля `sources` из отчёта
    - _Требования: 7.1_

- [ ] 8. Обновить пайплайн анализа
  - [x] 8.1 Расширить `_run_analysis_background` в `backend/app/api/router.py`
    - Добавить параметры `source` и `habr_topic_id`
    - При `source="pikabu"` — текущее поведение (ParserService)
    - При `source="habr"` — использовать `HabrParserService`
    - При `source="both"` — последовательно парсить оба источника, загрузить посты по обоим `topic_id`
    - Сохранять `sources` в отчёте (`"pikabu"`, `"habr"`, `"pikabu,habr"`)
    - Обновить сообщения прогресса для указания текущего источника
    - _Требования: 6.1, 6.2, 6.3, 6.4, 7.1, 7.4_
  - [ ]* 8.2 Написать property-тест: полнота объединённых данных
    - **Свойство 7: Полнота объединённых данных**
    - Генерировать два набора постов, объединять, проверять отсутствие потерь и дубликатов
    - **Проверяет: Требования 6.2**
  - [ ]* 8.3 Написать property-тест: валидность источников в отчёте
    - **Свойство 8: Валидность источников в отчёте**
    - Генерировать отчёты с разными `source`, проверять корректность поля `sources`
    - **Проверяет: Требования 7.1, 7.4**

- [ ] 9. Контрольная точка
  - Убедиться, что все backend-тесты проходят, API корректно обрабатывает параметр source. Спросить пользователя при возникновении вопросов.

- [ ] 10. Фронтенд: обновить TypeScript-типы и API-клиент
  - [x] 10.1 Обновить `frontend/src/types/api.ts`
    - Добавить `source?: string` в интерфейс `Topic`
    - Добавить `source?: string` и `habr_topic_id?: number` в `AnalysisStartRequest`
    - Добавить `sources?: string` в интерфейс `Report`
    - _Требования: 7.1, 8.3_
  - [x] 10.2 Обновить `frontend/src/api/client.ts`
    - `getTopics(search?, source?)` — добавить параметр `source` в запрос
    - `startAnalysis(topicId, days, source?, habrTopicId?)` — передавать `source` и `habr_topic_id`
    - _Требования: 8.1, 8.3_

- [ ] 11. Фронтенд: переключатель источника в TopicSelector
  - [x] 11.1 Добавить селектор режима источника в `frontend/src/pages/TopicSelector.vue`
    - Три кнопки: «Pikabu», «Habr», «Pikabu + Habr» (по умолчанию «Pikabu»)
    - При переключении — перезагрузка списка тем с параметром `source`
    - В режиме `"both"` — отображать два списка с бейджами «Pikabu» / «Habr», пользователь выбирает по одной теме из каждого
    - Передавать `source` и `habrTopicId` при запуске анализа
    - _Требования: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [ ] 12. Фронтенд: бейджи источника в ReportView
  - [x] 12.1 Обновить `frontend/src/pages/ReportView.vue`
    - Отображать бейдж источника в заголовке отчёта (Pikabu / Habr / Pikabu + Habr)
    - Ссылки на оригинальные посты — указывать платформу («Открыть на Pikabu ↗» / «Открыть на Habr ↗»)
    - _Требования: 7.2, 7.3_

- [ ] 13. Контрольная точка
  - Убедиться, что все тесты проходят, фронтенд корректно отображает переключатель и бейджи. Спросить пользователя при возникновении вопросов.

- [ ] 14. Написать unit-тесты и интеграционные тесты
  - [ ]* 14.1 Unit-тесты для HabrParserService
    - Тест парсинга реального HTML Habr (snapshot)
    - Тест retry-логики: мок HTTP 429, мок HTTP 5xx
    - Тест пропуска комментариев при ошибке парсинга отдельной статьи
    - Edge cases: пустой HTML, невалидный HTML, отсутствие комментариев
    - Команда запуска: `py -m pytest backend/tests/test_habr_parser.py -v`
    - _Требования: 3.7, 3.8, 4.3, 9.1, 9.2_
  - [ ]* 14.2 Unit-тесты для обновлённого API
    - Тест `GET /api/topics` с параметром `source` (pikabu, habr, both)
    - Тест `GET /api/topics` без параметра `source` — обратная совместимость
    - Тест `POST /api/analysis/start` с `source="habr"` без `habr_topic_id` → 400
    - Тест `POST /api/analysis/start` с `source="both"` и обоими topic_id
    - Команда запуска: `py -m pytest backend/tests/test_api_router.py -v`
    - _Требования: 8.1, 8.2, 8.3, 8.4, 8.5_
  - [ ]* 14.3 Написать property-тест: валидность кэша
    - **Свойство 6: Валидность кэша**
    - Генерировать случайные timestamps, проверять решение о кэшировании (< 24 часов → кэш валиден)
    - Команда запуска: `py -m pytest backend/tests/test_habr_cache.py -v`
    - **Проверяет: Требования 5.5**

- [ ] 15. Финальная контрольная точка
  - Запустить все тесты: `py -m pytest backend/tests/ -v`. Убедиться, что все проходят. Спросить пользователя при возникновении вопросов.

## Примечания

- Задачи с `*` — опциональные (тесты), могут быть пропущены для ускорения MVP
- Каждая задача ссылается на конкретные требования для трассируемости
- Контрольные точки обеспечивают инкрементальную валидацию
- Property-тесты проверяют универсальные свойства корректности (Hypothesis)
- Unit-тесты проверяют конкретные примеры и edge cases
