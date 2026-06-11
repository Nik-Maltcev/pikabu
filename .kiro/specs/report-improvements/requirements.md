# Requirements Document

## Introduction

Комплексная доработка функциональности отчётов в BizMap (режим `niche_search`). Цель — повысить качество, достоверность и практическую ценность генерируемых отчётов: исправить баги в рейтинге упоминаний, визуально разделить секции, добавить реальные рыночные данные, обогатить бизнес-идеи примерами аналогов, переработать раздел рисков по известным фреймворкам и сделать рекомендации конкретными и actionable.

## Glossary

- **Report_System**: Подсистема BizMap, отвечающая за генерацию, хранение и отображение аналитических отчётов (backend analyzer + frontend ReportView)
- **Mention_Rating**: Визуальная секция отчёта, отображающая количество упоминаний каждой боли в виде горизонтальных bar-графиков с числовыми значениями
- **Key_Pains_Section**: Секция отчёта «ТОП Ключевых болей», содержащая описание болей, частоту, эмоциональный заряд и цитаты
- **Market_Data_Service**: Сервис обогащения отчётов реальными рыночными данными (объём рынка, динамика роста) из внешних источников (Google Trends и др.)
- **Competitor_Lookup_Service**: Сервис поиска информации об аналогичных бизнесах (выручка, инвест-раунды, наличие конкурентов в РФ) через внешние API (Linkup и др.)
- **Risk_Framework**: Структурированная модель оценки рисков, основанная на методологиях «Lean Startup» (Эрик Рис) и «Стартап. Настольная книга основателя» (Стив Бланк, Боб Дорф)
- **LLM_Analyzer**: Сервис `analyzer.py`, выполняющий анализ контента через LLM-провайдеры (DeepSeek, Gemini, GLM) и генерирующий структурированный JSON-отчёт
- **Aggregation_Prompt**: Промпт, отправляемый LLM для агрегации частичных результатов в финальный отчёт
- **NicheReport**: Pydantic-модель финального отчёта в режиме niche_search, содержащая key_pains, jtbd_analyses, business_ideas, market_trends

## Requirements

### Requirement 1: Fix Mention Rating Sorting and Values

**User Story:** As a report user, I want the mention ratings to display correct non-zero values and be sorted by count descending, so that I can accurately understand which pains are most prevalent.

#### Acceptance Criteria

1. WHEN the LLM_Analyzer generates key_pains data for a chunk, THE Report_System SHALL ensure each KeyPain object contains a mentions_count value of 1 or greater representing the number of posts and comments in that chunk where the pain is referenced
2. WHEN the Report_System aggregates key_pains from multiple chunks during hierarchical aggregation, THE Report_System SHALL sum the mentions_count values of merged similar pains so that the final count reflects all source chunks
3. WHEN the Mention_Rating section is rendered, THE Report_System SHALL sort the final aggregated key_pains entries in descending order by mentions_count so that rank 1 corresponds to the highest value
4. IF the LLM_Analyzer returns a KeyPain with mentions_count equal to zero, THEN THE Report_System SHALL recalculate the value by counting posts and comments in the source chunk whose text contains keywords from the KeyPain description, and assign the result as mentions_count
5. IF the recalculated mentions_count still equals zero after the keyword-based recount, THEN THE Report_System SHALL assign a mentions_count of 1 to that KeyPain entry
6. WHEN multiple key_pains have identical mentions_count values, THE Report_System SHALL preserve their relative order from the LLM response (stable sort)

### Requirement 2: Visual Separation of Key Pains and Mention Rating

**User Story:** As a report user, I want the "Top Key Pains" and "Mention Rating" sections to be clearly distinct visually, so that I understand they represent different facets of the data.

#### Acceptance Criteria

1. THE Report_System SHALL render the Key_Pains_Section and the Mention_Rating as two visually distinct blocks, each with its own heading, a different background color or gradient, and vertical spacing of at least 24px between them when stacked vertically
2. THE Report_System SHALL display a fixed subheading under each section title: "Формулировки проблем с цитатами" under Key_Pains_Section and "Количественная частота упоминаний" under Mention_Rating
3. WHEN the viewport width is 1024px or wider, THE Report_System SHALL render Key_Pains_Section and Mention_Rating in a two-column layout with a vertical divider of at least 1px width visible between the columns
4. WHEN the viewport width is less than 1024px, THE Report_System SHALL stack the Key_Pains_Section above the Mention_Rating in a single-column layout, preserving distinct background colors for each section
5. THE Report_System SHALL display a unique icon in the heading of each section (one icon for Key_Pains_Section, a different icon for Mention_Rating) so that a user can differentiate them without reading the heading text

### Requirement 3: Real Market Trend Data Enrichment

**User Story:** As a report user, I want to see real market volume numbers and growth dynamics adjusted for inflation, so that I can assess the actual market opportunity.

#### Acceptance Criteria

1. WHEN generating market_trends for a NicheReport, THE Market_Data_Service SHALL query external data sources (Google Trends API or equivalent) using up to 5 search keywords derived from each MarketTrend entry name and description, with a per-source request timeout of 10 seconds
2. IF external data sources return volume data for a MarketTrend entry, THEN THE Market_Data_Service SHALL include a numeric market_volume_estimate field expressed in rubles (₽) for Russian-market niches or USD ($) for international niches, representing annual market size
3. IF external data sources return volume data for a MarketTrend entry, THEN THE Market_Data_Service SHALL include a growth_rate_percent field representing year-over-year growth adjusted by subtracting the most recent official annual inflation rate published by the Central Bank of Russia (or equivalent national source for USD markets) from the nominal growth figure
4. IF the Market_Data_Service cannot retrieve real market data for a given trend within 30 seconds total enrichment time per report, THEN THE Report_System SHALL display the LLM-generated trend description with a label indicating "Оценка ИИ (реальные данные недоступны)"
5. IF market_volume_estimate and growth_rate_percent are available for a MarketTrend entry, THEN THE Report_System SHALL display them in the MarketTrend card in the format: "Объём рынка: ~{volume} {currency_symbol}, Рост: +{rate}% г/г с учётом инфляции"
6. WHILE the Market_Data_Service is querying external sources, THE Report_System SHALL complete all market trend enrichment queries within 30 seconds per report; any trends not enriched within this budget SHALL fall back to the LLM-generated label defined in criterion 4

### Requirement 4: Business Ideas Enrichment with Analogous Businesses

**User Story:** As a report user, I want to see examples of real analogous businesses with their revenue, investment rounds, and competitor presence in Russia, so that I can validate the viability of proposed ideas.

#### Acceptance Criteria

1. WHEN generating business_ideas for a NicheReport, THE Competitor_Lookup_Service SHALL search for 1-3 analogous businesses for each BusinessIdea using external APIs (Linkup or equivalent), with a timeout of 10 seconds per BusinessIdea
2. THE Report_System SHALL store and display for each analogue: company name, description (maximum 200 characters), estimated annual revenue formatted as currency with magnitude (e.g., "$2M/год" or "~150 млн ₽/год") when available, investment round information (stage and amount), and whether competitors exist in Russia (boolean yes/no indicator)
3. IF the Competitor_Lookup_Service cannot find analogous businesses for a given idea, THEN THE Report_System SHALL display "Аналоги не найдены — рынок может быть незанят" as a positive signal
4. IF the Competitor_Lookup_Service fails due to a network error, timeout, or API unavailability, THEN THE Report_System SHALL display "Данные об аналогах временно недоступны" and render the BusinessIdea card without the analogues sub-block
5. THE Report_System SHALL display analogue data in a structured sub-block within each BusinessIdea card, separated from the MVP plan and recommendations by a visible horizontal divider or distinct background with at least 16px vertical margin
6. WHEN analogue data includes investment round information, THE Report_System SHALL format it as "Раунд: [stage] — [amount]" (e.g., "Раунд: Series A — $5M")

### Requirement 5: Risks Section Based on Startup Frameworks

**User Story:** As a report user, I want the risks section to be structured using proven startup frameworks, so that I receive a systematic risk assessment rather than a generic list.

#### Acceptance Criteria

1. WHEN generating risks for each BusinessIdea, THE LLM_Analyzer SHALL categorize each risk into one of the following framework-based categories: "Market Risk" (рынок не существует или слишком мал), "Product Risk" (продукт не решает реальную проблему), "Customer Risk" (целевой сегмент неверно определён), "Execution Risk" (команда/ресурсы недостаточны для реализации), "Financial Risk" (unit-экономика не сходится)
2. THE LLM_Analyzer SHALL include for each identified risk: a category label matching one of the five defined categories, a specific description of 1 to 3 sentences relating the risk to the particular business idea, and a mitigation action stating one actionable step (1 to 2 sentences) to reduce the risk
3. THE Report_System SHALL display risks grouped by category, with each category section having a distinct heading that includes the category name and a category-specific icon
4. THE Aggregation_Prompt SHALL instruct the LLM to evaluate risks by requiring each risk description to reference either a problem-solution fit assumption that has not been validated or a build-measure-learn hypothesis that could disprove the idea's viability
5. WHEN the LLM_Analyzer returns fewer than 3 or more than 6 categorized risks for a BusinessIdea, THE Report_System SHALL re-prompt the LLM with explicit instruction to return between 3 and 6 risks inclusive
6. THE Report_System SHALL display no fewer than 3 and no more than 6 categorized risks per BusinessIdea, where risks from at least 2 distinct categories are represented

### Requirement 6: Actionable Recommendations

**User Story:** As a report user, I want the recommendations section to contain specific, time-bound, measurable action steps, so that I know exactly what to do next after reading the report.

#### Acceptance Criteria

1. WHEN generating launch_recommendations for each BusinessIdea, THE LLM_Analyzer SHALL produce recommendations where each item follows the structure: a relative timeframe prefix in the format "За N дней:" or "За N недель:" (where N is a positive integer), followed by an action verb, a named deliverable or outcome, and at least one named tool, platform, or method (e.g., "За 3 дня: провести 10 custdev-интервью с целевой аудиторией в чатах Telegram")
2. THE LLM_Analyzer SHALL order launch_recommendations by ascending timeframe so that earlier steps appear first, forming a sequential launch plan from validation through first revenue
3. THE LLM_Analyzer SHALL ensure each recommendation references at least one named tool, platform, or channel relevant to the Russian-speaking market (e.g., "Tilda", "Telegram-бот", "Яндекс.Директ", "Avito", "VK")
4. WHILE the user has paid access to the report AND a BusinessIdea contains at least one launch_recommendation, THE Report_System SHALL display launch_recommendations as an ordered list where each item is prefixed with a step number (1, 2, 3…) serving as a visual progress indicator
5. THE LLM_Analyzer SHALL generate between 5 and 7 launch_recommendations per BusinessIdea, covering all five stages: validation, MVP build, first users acquisition, monetization test, and scaling decision — with at least one recommendation per stage
6. IF the LLM_Analyzer produces fewer than 5 or more than 7 launch_recommendations for a BusinessIdea, THEN THE LLM_Analyzer SHALL retry generation once, and if the count still falls outside the 5–7 range, trim from the end or pad the underrepresented stage to achieve exactly 5 items
