# Implementation Plan: Категории бизнеса по ОКВЭД

## Overview

Реализация подбора категорий по ОКВЭД-коду через LLM и мульти-выбора категорий для объединённого анализа. Backend: новый сервис `CategorySuggester`, эндпоинт `/api/categories/suggest`, расширение `/api/analysis/start` для `topic_ids`. Frontend: компоненты `OkvedInput`, `SuggestionPanel`, `MultiSelectChips` + интеграция в `TopicSelector.vue`.

## Tasks

- [x] 1. Backend: Pydantic-схемы и валидация
  - [x] 1.1 Добавить Pydantic-схемы для category suggest в `backend/app/models/schemas.py`
    - Добавить `CategorySuggestion` (topic_id, name, reason)
    - Добавить `CategorySuggestRequest` с валидатором длины query (2-200 символов, strip)
    - Добавить `CategorySuggestResponse` (suggestions list + message)
    - _Requirements: 1.3, 1.4, 2.3_

  - [x] 1.2 Расширить `AnalysisStartRequest` для поддержки `topic_ids` в `backend/app/models/schemas.py`
    - Добавить поле `topic_ids: list[int] | None = None`
    - Добавить `model_validator` — ровно одно из `topic_id` / `topic_ids` задано
    - Валидация: `topic_ids` максимум 5 элементов
    - Обратная совместимость: `topic_id` продолжает работать
    - _Requirements: 7.3, 4.1, 6.1_

  - [ ]* 1.3 Написать property-тесты для валидации схем
    - **Property 1: Валидация длины запроса** — генерация строк 0-500 символов, проверка accept/reject по длине после strip
    - **Validates: Requirements 1.3, 1.4**
    - **Property 7: Обратная совместимость — topic_id XOR topic_ids** — генерация комбинаций topic_id/topic_ids, проверка валидации
    - **Validates: Requirements 7.3**

- [x] 2. Backend: Сервис CategorySuggester
  - [x] 2.1 Создать `backend/app/services/category_suggester.py`
    - Класс `CategorySuggesterService` с зависимостью на `AsyncSession`
    - Метод `suggest(query: str) -> list[CategorySuggestion]`
    - Метод `_build_prompt(query, topics)` — формирование промпта с полным списком категорий
    - Метод `_parse_response(text, valid_ids)` — парсинг JSON, фильтрация невалидных topic_id, обрезка до 5, обрезка reason до 100 символов
    - Использование `AnalyzerService._call_llm` для вызова LLM
    - Timeout 10 секунд, обработка ошибок (503 при timeout/HTTP error)
    - Retry 1 раз при невалидном JSON от LLM
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 2.2 Написать property-тест для парсинга ответа LLM
    - **Property 2: Парсинг ответа LLM — корректность структуры и количества**
    - Генерация JSON-структур с рандомными topic_id/name/reason, проверка что результат 0-5 элементов, все topic_id из допустимого множества, reason ≤ 100 символов
    - **Validates: Requirements 2.2, 2.3**

  - [ ]* 2.3 Написать unit-тесты для CategorySuggester
    - Тест `_build_prompt` — корректное форматирование
    - Тест `suggest` с мокнутым LLM — happy path (2-5 рекомендаций)
    - Тест `suggest` при timeout LLM → CategorySuggesterError
    - Тест `suggest` при пустом ответе LLM → пустой список + message
    - _Requirements: 2.1, 2.4, 2.5, 2.6_

- [x] 3. Backend: API эндпоинт `/api/categories/suggest`
  - [x] 3.1 Добавить эндпоинт `POST /api/categories/suggest` в `backend/app/api/router.py`
    - Принимает `CategorySuggestRequest`, возвращает `CategorySuggestResponse`
    - Инжектирует `AsyncSession`, создаёт `CategorySuggesterService`
    - Обработка `ValueError` → 422, `CategorySuggesterError` → 503
    - _Requirements: 1.2, 2.1, 2.6_

  - [ ]* 3.2 Написать integration-тест для эндпоинта suggest
    - Тест full cycle с мокнутым LLM — запрос → ответ с рекомендациями
    - Тест с невалидным query (<2 символов) → 422
    - Тест при ошибке LLM → 503 с fallback-сообщением
    - _Requirements: 1.2, 1.4, 2.6_

- [~] 4. Checkpoint — Backend suggest готов
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Backend: Расширение pipeline для multi-topic
  - [x] 5.1 Расширить обработку `POST /api/analysis/start` в `router.py` для `topic_ids`
    - Если `topic_id` задан — обернуть в `[topic_id]`
    - Если `topic_ids` задан — использовать напрямую
    - Проверка существования всех topic_id в БД (404 если не найден)
    - Передать список topic_ids в pipeline
    - _Requirements: 6.1, 7.2, 7.3_

  - [x] 5.2 Расширить `run_full_analysis` в `backend/app/services/pipeline.py` для multi-topic
    - Загрузка постов из всех topic_ids (объединение)
    - Вызов `find_duplicates_by_name` для каждого topic_id
    - Объединение данных → chunking → LLM analysis как единый набор
    - Пропуск категорий без данных, указание в отчёте
    - Привязка отчёта к первому topic_id (primary) для обратной совместимости
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 7.2_

  - [ ]* 5.3 Написать property-тест для загрузки постов из нескольких категорий
    - **Property 6: Pipeline загружает посты из всех запрошенных категорий**
    - Генерация topic_ids с постами в mock-БД, проверка что объединение содержит посты из КАЖДОГО topic_id
    - **Validates: Requirements 6.2**

  - [ ]* 5.4 Написать unit-тесты для multi-topic pipeline
    - Тест загрузки из 3 категорий — объединение постов
    - Тест с категорией без данных — продолжение по остальным
    - Тест backward compat: одиночный topic_id работает как прежде
    - _Requirements: 6.2, 6.5, 7.2_

- [~] 6. Checkpoint — Backend полностью готов
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Frontend: TypeScript интерфейсы и API клиент
  - [x] 7.1 Расширить TypeScript интерфейсы в `frontend/src/types/api.ts`
    - Добавить `CategorySuggestion` (topic_id, name, reason)
    - Добавить `CategorySuggestResponse` (suggestions, message)
    - Расширить `AnalysisStartRequest` — добавить `topic_ids?: number[]`
    - _Requirements: 2.3, 6.1, 7.3_

  - [x] 7.2 Добавить API-функции в `frontend/src/api/client.ts`
    - Функция `suggestCategories(query: string): Promise<CategorySuggestResponse>`
    - Расширить `startAnalysis` для поддержки `topic_ids` (массив) вместо одиночного `topicId`
    - _Requirements: 1.2, 6.1_

- [x] 8п. Frontend: Компоненты UI
  - [x] 8.1 Создать компонент `frontend/src/components/OkvedInput.vue`
    - Текстовое поле с placeholder «Введите ОКВЭД-код или описание деятельности»
    - Кнопка «Подобрать категории» — активна при ≥ 2 символах ввода
    - Состояния: idle, loading (spinner на кнопке), error
    - Emit событие `suggest` с query при нажатии кнопки
    - _Requirements: 1.1, 1.2_

  - [x] 8.2 Создать компонент `frontend/src/components/SuggestionPanel.vue`
    - Props: `suggestions: CategorySuggestion[]`, `message: string`
    - Отображение карточек: название + обоснование для каждой рекомендации
    - Кнопка «Принять все» — emit `acceptAll`
    - Клик по карточке — emit `select(suggestion)`
    - Fallback-сообщение при пустом списке: «Не удалось подобрать категории»
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 8.3 Создать компонент `frontend/src/components/MultiSelectChips.vue`
    - Props: `selectedTopics: Topic[]`, `maxCount: 5`
    - Отображение чипсов с кнопкой × для удаления
    - Счётчик «Выбрано: N / 5»
    - Emit `remove(topicId)` при нажатии ×
    - _Requirements: 4.2, 4.5, 5.3_

- [x] 9. Frontend: Интеграция в TopicSelector.vue
  - [x] 9.1 Интегрировать новые компоненты в `frontend/src/pages/TopicSelector.vue`
    - Заменить `selectedTopic: Topic | null` на `selectedTopics: Topic[]`
    - Добавить `OkvedInput` над текущим поиском категорий
    - Добавить `SuggestionPanel` для отображения рекомендаций LLM
    - Добавить `MultiSelectChips` для отображения выбранных категорий
    - Логика toggle: повторный клик по выбранной категории удаляет её
    - Лимит 5 категорий с предупреждением при превышении (toast «Максимум 5 категорий»)
    - Доступ к полному списку категорий сохраняется при отображённых рекомендациях
    - Кнопка «Далее» передаёт `topic_ids` массив в `startAnalysis`
    - Обратная совместимость: выбор одной категории без ОКВЭД работает как прежде
    - _Requirements: 1.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 6.1, 7.1, 7.2_

  - [ ]* 9.2 Написать frontend-тесты для компонентов (vitest + vue-test-utils)
    - `OkvedInput.vue`: кнопка скрыта при <2 символах, видна при ≥2
    - `SuggestionPanel.vue`: рендеринг карточек, клик добавляет, Accept All
    - `MultiSelectChips.vue`: отображение, удаление через ×, лимит 5
    - `TopicSelector.vue`: полный flow от ввода до «Далее» с topic_ids
    - _Requirements: 1.1, 3.1, 3.2, 3.3, 4.1, 4.4_

- [x] 10. Final checkpoint — Полная интеграция
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend использует Python (FastAPI + Pydantic + hypothesis)
- Frontend использует TypeScript (Vue 3 + vitest + vue-test-utils)
- Новых миграций БД не требуется — фича работает с существующими таблицами Topic и AnalysisTask

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "7.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "7.2"] },
    { "id": 2, "tasks": ["1.3", "2.2", "2.3", "3.1", "8.1", "8.2", "8.3"] },
    { "id": 3, "tasks": ["3.2", "5.1"] },
    { "id": 4, "tasks": ["5.2", "9.1"] },
    { "id": 5, "tasks": ["5.3", "5.4", "9.2"] }
  ]
}
```
