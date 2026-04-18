# Документ требований: Интеграция VC.ru + Playwright

## Введение

Расширение системы Topic Analyzer двумя связанными возможностями:
1. Добавление VC.ru как нового источника контента (наряду с Pikabu и Habr) с 39 категориями.
2. Интеграция headless-браузера Playwright для рендеринга комментариев на VC.ru и Habr — оба сайта загружают комментарии через JavaScript, что делает невозможным их парсинг через обычные HTTP-запросы.

## Глоссарий

- **VcruParserService**: Сервис парсинга статей и комментариев с сайта vc.ru.
- **PlaywrightRenderer**: Компонент, управляющий headless-браузером Chromium через Playwright для рендеринга JavaScript-контента на страницах статей.
- **TopicManager**: Существующий сервис управления списком тем/категорий из всех источников.
- **HabrParserService**: Существующий сервис парсинга статей и комментариев с habr.com.
- **ParserService**: Существующий сервис парсинга постов и комментариев с pikabu.ru.
- **AnalysisPipeline**: Существующий конвейер анализа: парсинг → чанкинг → LLM-анализ → агрегация.
- **Category_Page**: Страница списка статей VC.ru по категории (например, `https://vc.ru/dev`).
- **Article_Page**: Страница отдельной статьи VC.ru или Habr с комментариями, рендерируемыми через JavaScript.
- **Source_Selector**: UI-компонент выбора источника данных на странице TopicSelector.
- **curl_cffi**: HTTP-клиент с имперсонацией TLS-отпечатков браузера, используемый для загрузки статических HTML-страниц.

## Требования

### Требование 1: Список категорий VC.ru

**User Story:** Как пользователь, я хочу видеть список категорий VC.ru в интерфейсе, чтобы выбрать интересующую категорию для анализа.

#### Критерии приёмки

1. THE TopicManager SHALL хранить 39 предопределённых категорий VC.ru со значениями: ai, apple, apps, ask, books, chatgpt, crypto, design, dev, education, flood, food, future, growth, hr, invest, legal, life, marketing, marketplace, media, migration, money, office, offline, opinions, retail, seo, services, social, story, tech, telegram, transport, travel, tribuna, video, workdays.
2. THE TopicManager SHALL формировать URL каждой категории VC.ru по шаблону `https://vc.ru/{category}`.
3. THE TopicManager SHALL сохранять категории VC.ru в таблицу topics с полем source равным "vcru".
4. WHEN пользователь запрашивает список тем с параметром source="vcru", THE TopicManager SHALL возвращать только категории VC.ru.
5. WHEN пользователь запрашивает список тем с параметром source="all", THE TopicManager SHALL возвращать категории из всех источников: Pikabu, Habr и VC.ru.

### Требование 2: Парсинг статей VC.ru

**User Story:** Как система, я хочу загружать и парсить статьи с категорийных страниц VC.ru, чтобы собирать контент для анализа.

#### Критерии приёмки

1. THE VcruParserService SHALL загружать страницы списка статей категории VC.ru через curl_cffi без использования прокси.
2. THE VcruParserService SHALL извлекать из каждой статьи следующие поля: заголовок (title), текст (body), дату публикации (published_at), рейтинг (rating), количество комментариев (comments_count), URL статьи.
3. THE VcruParserService SHALL формировать уникальный идентификатор статьи в формате "vcru_{article_id}", где article_id извлекается из URL статьи.
4. THE VcruParserService SHALL сохранять статьи в таблицу posts с полем source равным "vcru".
5. WHEN Category_Page содержит несколько страниц, THE VcruParserService SHALL загружать последующие страницы через пагинацию.
6. WHEN статья на Category_Page опубликована раньше запрошенного периода (параметр days), THE VcruParserService SHALL прекращать пагинацию, если все статьи на текущей странице старше запрошенного периода.
7. IF загрузка Category_Page завершается HTTP-ошибкой 429, THEN THE VcruParserService SHALL повторить запрос после паузы в 60 секунд (до 5 попыток).
8. IF загрузка Category_Page завершается HTTP-ошибкой 5xx, THEN THE VcruParserService SHALL повторить запрос до 3 раз с паузой 10 секунд между попытками.
9. IF загрузка Category_Page завершается сетевой ошибкой, THEN THE VcruParserService SHALL повторить запрос до 3 раз с паузой 15 секунд между попытками.

### Требование 3: Парсинг комментариев VC.ru через Playwright

**User Story:** Как система, я хочу загружать комментарии со страниц статей VC.ru с помощью headless-браузера, чтобы получить контент, рендерируемый через JavaScript.

#### Критерии приёмки

1. THE PlaywrightRenderer SHALL запускать один экземпляр headless-браузера Chromium для обработки всех статей в рамках одного сеанса парсинга.
2. THE PlaywrightRenderer SHALL закрывать экземпляр браузера после завершения обработки всех статей.
3. WHEN VcruParserService запрашивает комментарии статьи, THE PlaywrightRenderer SHALL открыть страницу статьи, дождаться загрузки комментариев и вернуть отрендеренный HTML.
4. THE VcruParserService SHALL извлекать из каждого комментария следующие поля: текст (body), дату публикации (published_at), рейтинг (rating), уникальный идентификатор комментария.
5. THE VcruParserService SHALL формировать уникальный идентификатор комментария в формате "vcru_comment_{comment_id}".
6. IF PlaywrightRenderer не может загрузить страницу статьи в течение 30 секунд, THEN THE PlaywrightRenderer SHALL прервать загрузку и вернуть пустой список комментариев для данной статьи.
7. IF PlaywrightRenderer обнаруживает ошибку при рендеринге страницы, THEN THE VcruParserService SHALL записать предупреждение в лог и продолжить обработку следующих статей.
8. THE PlaywrightRenderer SHALL использовать асинхронный API Playwright (async_playwright).

### Требование 4: Обновление парсинга комментариев Habr через Playwright

**User Story:** Как система, я хочу загружать комментарии Habr через headless-браузер, чтобы получить комментарии, которые рендерятся через JavaScript и недоступны в статическом HTML.

#### Критерии приёмки

1. WHEN HabrParserService запрашивает комментарии статьи Habr, THE PlaywrightRenderer SHALL открыть страницу статьи, дождаться загрузки комментариев и вернуть отрендеренный HTML.
2. THE HabrParserService SHALL использовать PlaywrightRenderer вместо curl_cffi для загрузки страниц статей с комментариями.
3. THE HabrParserService SHALL продолжать использовать curl_cffi для загрузки страниц списка статей (flow pages).
4. THE PlaywrightRenderer SHALL переиспользовать один экземпляр браузера для всех статей Habr в рамках одного сеанса парсинга.
5. IF PlaywrightRenderer не может загрузить страницу статьи Habr в течение 30 секунд, THEN THE HabrParserService SHALL записать предупреждение в лог и продолжить обработку следующих статей.

### Требование 5: Выбор источника в UI

**User Story:** Как пользователь, я хочу выбирать VC.ru как источник данных в интерфейсе, чтобы анализировать контент с этого сайта.

#### Критерии приёмки

1. THE Source_Selector SHALL отображать четыре варианта выбора источника: "Pikabu", "Habr", "VC.ru", "Все".
2. WHEN пользователь выбирает "VC.ru", THE Source_Selector SHALL загружать и отображать список категорий VC.ru.
3. WHEN пользователь выбирает "Все", THE Source_Selector SHALL отображать три списка тем: Pikabu, Habr и VC.ru, позволяя выбрать по одной теме из каждого источника.
4. WHEN пользователь выбирает "VC.ru" и выбирает категорию, THE Source_Selector SHALL разрешить запуск анализа.
5. THE Source_Selector SHALL передавать значение source="vcru" в API при выборе источника VC.ru.

### Требование 6: Интеграция VC.ru в конвейер анализа

**User Story:** Как система, я хочу обрабатывать данные VC.ru через существующий конвейер анализа, чтобы генерировать отчёты на основе контента VC.ru.

#### Критерии приёмки

1. WHEN пользователь запускает анализ с source="vcru", THE AnalysisPipeline SHALL вызывать VcruParserService для парсинга статей и комментариев выбранной категории.
2. WHEN пользователь запускает анализ с source="all", THE AnalysisPipeline SHALL последовательно вызывать ParserService, HabrParserService и VcruParserService.
3. THE AnalysisPipeline SHALL передавать данные VC.ru через существующие этапы: чанкинг → LLM-анализ → агрегация.
4. THE AnalysisPipeline SHALL сохранять в отчёте информацию об использованных источниках (поле sources в таблице reports).
5. WHEN source="vcru", THE AnalysisPipeline SHALL устанавливать значение sources="vcru" в отчёте.
6. WHEN source="all", THE AnalysisPipeline SHALL устанавливать значение sources="pikabu,habr,vcru" в отчёте.

### Требование 7: API-эндпоинты для VC.ru

**User Story:** Как фронтенд, я хочу использовать существующие API-эндпоинты с поддержкой нового источника, чтобы работать с данными VC.ru.

#### Критерии приёмки

1. WHEN GET /api/topics вызывается с параметром source="vcru", THE API SHALL возвращать список категорий VC.ru.
2. WHEN GET /api/topics вызывается с параметром source="all", THE API SHALL возвращать темы из всех источников.
3. WHEN POST /api/analysis/start вызывается с source="vcru", THE API SHALL запускать анализ с использованием VcruParserService.
4. WHEN POST /api/analysis/start вызывается с source="all", THE API SHALL требовать указания topic_id (Pikabu), habr_topic_id (Habr) и vcru_topic_id (VC.ru).
5. THE API SHALL принимать параметр vcru_topic_id в запросе AnalysisStartRequest.

### Требование 8: Зависимость Playwright

**User Story:** Как разработчик, я хочу добавить Playwright в зависимости проекта, чтобы использовать headless-браузер для рендеринга JavaScript-контента.

#### Критерии приёмки

1. THE requirements.txt SHALL содержать зависимость playwright.
2. THE PlaywrightRenderer SHALL использовать браузер Chromium, устанавливаемый командой `playwright install chromium`.
3. THE PlaywrightRenderer SHALL корректно работать в асинхронном контексте FastAPI.

### Требование 9: Отображение источника в отчётах

**User Story:** Как пользователь, я хочу видеть в отчёте, какие источники были использованы для анализа, чтобы понимать охват данных.

#### Критерии приёмки

1. THE Report SHALL отображать список использованных источников на основе поля sources.
2. WHEN отчёт содержит sources="vcru", THE Report SHALL отображать "VC.ru" как источник.
3. WHEN отчёт содержит sources="pikabu,habr,vcru", THE Report SHALL отображать "Pikabu, Habr, VC.ru" как источники.

### Требование 10: Управление жизненным циклом PlaywrightRenderer

**User Story:** Как система, я хочу эффективно управлять экземпляром браузера Playwright, чтобы минимизировать потребление ресурсов и избежать утечек памяти.

#### Критерии приёмки

1. THE PlaywrightRenderer SHALL поддерживать использование в качестве асинхронного контекстного менеджера (async context manager).
2. WHEN PlaywrightRenderer используется как контекстный менеджер, THE PlaywrightRenderer SHALL запускать браузер при входе в контекст и закрывать при выходе.
3. THE PlaywrightRenderer SHALL переиспользовать один экземпляр браузера для всех запросов рендеринга в рамках одного контекста.
4. IF происходит необработанное исключение внутри контекста, THEN THE PlaywrightRenderer SHALL гарантировать закрытие браузера.
5. THE PlaywrightRenderer SHALL принимать HTML-содержимое страницы и возвращать его после рендеринга JavaScript, позволяя вызывающему коду выполнять парсинг с помощью BeautifulSoup.
