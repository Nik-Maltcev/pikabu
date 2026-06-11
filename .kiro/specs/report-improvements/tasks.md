# Implementation Plan: Report Improvements

## Overview

Комплексная доработка отчётов BizMap в режиме `niche_search`: валидация mentions_count, визуальное разделение секций, обогащение рыночными данными и аналогами, структурированные риски и actionable-рекомендации. Реализация затрагивает backend (Python/FastAPI), frontend (Vue 3 + TypeScript) и LLM-промпты.

## Tasks

- [x] 1. Data models and configuration updates
  - [x] 1.1 Add new Pydantic models (Risk, Analogue) and update existing models (MarketTrend, BusinessIdea, KeyPain) in `backend/app/models/schemas.py`
    - Add `Risk` model with fields: category (str), description (str), mitigation (str)
    - Add `Analogue` model with fields: company_name (str), description (str), annual_revenue (str | None), investment_round (str | None), has_ru_competitor (bool | None)
    - Update `MarketTrend` to add: market_volume_estimate (str | None), growth_rate_percent (float | None), data_source_label (str | None)
    - Update `BusinessIdea`: change `risks: list[str]` to `risks: list[Risk]`, add `analogues: list[Analogue] = []`
    - Ensure backward compatibility: all new fields have defaults (None or [])
    - _Requirements: 3.2, 3.3, 4.2, 5.1, 5.2_

  - [x] 1.2 Update TypeScript interfaces in `frontend/src/types/api.ts`
    - Add `Risk` interface with category, description, mitigation
    - Add `Analogue` interface with company_name, description, annual_revenue?, investment_round?, has_ru_competitor?
    - Update `MarketTrend` interface to add market_volume_estimate?, growth_rate_percent?, data_source_label?
    - Update `BusinessIdea` interface: risks from `string[]` to `Risk[]`, add `analogues?: Analogue[]`
    - _Requirements: 3.5, 4.2, 5.1_

  - [x] 1.3 Update `backend/app/config.py` with new settings
    - Add `serpapi_key: str = ""`
    - Add `inflation_rate_percent: float = 9.5`
    - Add `linkup_api_key: str = ""`
    - Add `enrichment_total_timeout: float = 30.0`
    - Add `enrichment_per_source_timeout: float = 10.0`
    - Update `.env.example` with new environment variable placeholders
    - _Requirements: 3.1, 3.6, 4.1_

- [x] 2. Implement MentionsValidator service
  - [x] 2.1 Create `backend/app/services/mentions_validator.py`
    - Implement `MentionsValidator` class with `validate_and_fix(key_pains, source_posts)` method
    - Implement `_keyword_recount(pain, posts)` method: extract significant keywords from pain.description, count posts containing at least one keyword in title/body/comments
    - For each pain with mentions_count == 0: run keyword recount; if still 0, assign 1
    - Ensure all output pains have mentions_count >= 1
    - Sort descending by mentions_count using stable sort (preserving LLM order for ties)
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6_

  - [ ]* 2.2 Write property test: Mentions count minimum invariant
    - **Property 1: Mentions count minimum invariant**
    - **Validates: Requirements 1.1, 1.5**

  - [ ]* 2.3 Write property test: Keyword recount correctness
    - **Property 2: Keyword recount correctness**
    - **Validates: Requirements 1.4**

  - [ ]* 2.4 Write property test: Key pains descending stable sort
    - **Property 3: Key pains descending stable sort**
    - **Validates: Requirements 1.3, 1.6**

  - [ ]* 2.5 Write property test: Mentions count sum on merge
    - **Property 4: Mentions count sum on merge**
    - **Validates: Requirements 1.2**

- [x] 3. Implement MarketDataService
  - [x] 3.1 Create `backend/app/services/market_data.py`
    - Implement `MarketDataService` class with `__init__(api_key, timeout)` reading from settings
    - Implement `enrich_trends(trends, total_timeout=30.0)`: query external sources for each trend, populate market_volume_estimate and growth_rate_percent
    - Implement `_query_trend_data(keywords)`: call SerpAPI/Google Trends with up to 5 keywords, per-source timeout 10s
    - Implement `_adjust_for_inflation(nominal_rate, inflation_rate)`: subtract inflation from nominal growth
    - On timeout/error: set `data_source_label = "Оценка ИИ (реальные данные недоступны)"` and leave volume/rate as None
    - Handle API rate limits with single exponential backoff retry
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

  - [ ]* 3.2 Write property test: Inflation adjustment arithmetic
    - **Property 5: Inflation adjustment arithmetic**
    - **Validates: Requirements 3.3**

  - [ ]* 3.3 Write unit tests for MarketDataService
    - Test successful enrichment with mocked SerpAPI response
    - Test timeout fallback produces correct data_source_label
    - Test network error fallback behavior
    - _Requirements: 3.4, 3.6_

- [x] 4. Implement CompetitorLookupService
  - [x] 4.1 Create `backend/app/services/competitor_lookup.py`
    - Implement `CompetitorLookupService` class with `__init__(api_key, timeout)` reading from settings
    - Implement `find_analogues(ideas, total_timeout=30.0)`: search 1-3 analogues per idea via Linkup API
    - Implement `_search_competitors(idea_name, description)`: call Linkup API, parse response into Analogue objects
    - Enforce Analogue.description max 200 chars (truncate if longer)
    - On timeout/network error: leave `analogues = []` (frontend shows fallback message)
    - On no results found: leave `analogues = []` (frontend shows positive signal)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 4.2 Write property test: Analogue description length constraint
    - **Property 7: Analogue description length constraint**
    - **Validates: Requirements 4.2**

  - [ ]* 4.3 Write property test: Investment round format
    - **Property 8: Investment round format**
    - **Validates: Requirements 4.6**

  - [ ]* 4.4 Write unit tests for CompetitorLookupService
    - Test successful lookup with mocked Linkup API response
    - Test timeout fallback: analogues list is empty
    - Test no-results case: analogues list is empty
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Update LLM prompts and analyzer integration
  - [x] 6.1 Update `NICHE_AGGREGATION_PROMPT` in `backend/app/services/analyzer.py`
    - Restructure risks instruction: require 3-6 risks per idea with category/description/mitigation format
    - Add 5 allowed risk categories: "Market Risk", "Product Risk", "Customer Risk", "Execution Risk", "Financial Risk"
    - Add instruction for mitigation to reference problem-solution fit or build-measure-learn hypothesis
    - Restructure launch_recommendations instruction: require 5-7 items per idea with timeframe prefix "За N дней:" or "За N недель:"
    - Add instruction for ascending timeframe order
    - Add instruction for each recommendation to include named Russian-market tool/platform
    - Add instruction to cover 5 stages: validation, MVP build, first users, monetization test, scaling
    - Update JSON schema in prompt to include `risks` as list of objects with category/description/mitigation
    - _Requirements: 5.1, 5.2, 5.4, 6.1, 6.2, 6.3, 6.5_

  - [x] 6.2 Add post-aggregation pipeline in `backend/app/services/analyzer.py`
    - Add `aggregate_and_enrich` method or modify `aggregate_results` for niche_search mode
    - After LLM aggregation: call `MentionsValidator.validate_and_fix()` on key_pains
    - After validation: run `MarketDataService.enrich_trends()` and `CompetitorLookupService.find_analogues()` in parallel using `asyncio.gather`
    - Validate risks count (3-6) per idea: re-prompt LLM once if out of range, then trim/pad as fallback
    - Validate recommendations count (5-7) per idea: re-prompt LLM once if out of range, then trim/pad
    - Validate risk categories are from allowed set: map to closest or default to "Execution Risk"
    - Validate recommendation timeframe prefix: prepend "За 7 дней:" if missing
    - _Requirements: 1.1, 1.2, 1.3, 3.1, 4.1, 5.5, 6.6_

  - [ ]* 6.3 Write property test: Risk object structural validity
    - **Property 9: Risk object structural validity**
    - **Validates: Requirements 5.1, 5.2**

  - [ ]* 6.4 Write property test: Risks count and category diversity invariant
    - **Property 10: Risks count and category diversity invariant**
    - **Validates: Requirements 5.5, 5.6**

  - [ ]* 6.5 Write property test: Recommendation structure validity
    - **Property 11: Recommendation structure validity**
    - **Validates: Requirements 6.1, 6.3**

  - [ ]* 6.6 Write property test: Recommendations ascending timeframe order
    - **Property 12: Recommendations ascending timeframe order**
    - **Validates: Requirements 6.2**

  - [ ]* 6.7 Write property test: Recommendations count and stage coverage
    - **Property 13: Recommendations count and stage coverage**
    - **Validates: Requirements 6.5**

- [x] 7. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Frontend: Visual separation of Key Pains and Mention Rating
  - [x] 8.1 Refactor `ReportView.vue` to split Key Pains and Mention Rating into visually distinct blocks
    - Give Key_Pains_Section a background of `bg-emerald-50` and its own heading with 🔥 icon
    - Add subheading "Формулировки проблем с цитатами" under Key Pains title
    - Give Mention_Rating a background of `bg-slate-50` and its own heading with 📊 icon
    - Add subheading "Количественная частота упоминаний" under Mention Rating title
    - Add vertical divider (1px) between columns at >=1024px viewport
    - Maintain two-column layout at >=1024px, single-column stacked at <1024px
    - Ensure at least 24px vertical spacing between sections when stacked
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 9. Frontend: Business Idea card enrichments
  - [x] 9.1 Add Analogues sub-block to BusinessIdea card in `ReportView.vue`
    - Display analogue data: company_name, description, annual_revenue, investment_round formatted as "Раунд: [stage] — [amount]"
    - Show "Аналоги не найдены — рынок может быть незанят" when analogues array is empty
    - Show "Данные об аналогах временно недоступны" on error (analogues undefined/null)
    - Add visible horizontal divider separating analogues from MVP plan section with 16px margin
    - Display has_ru_competitor as a badge (🇷🇺 indicator)
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 9.2 Add structured Risks section to BusinessIdea card
    - Group risks by category with distinct headings and category-specific icons
    - Display each risk: description text + mitigation action
    - Use category icons: 📈 Market, 🛠️ Product, 👥 Customer, ⚡ Execution, 💰 Financial
    - _Requirements: 5.1, 5.2, 5.3, 5.6_

  - [x] 9.3 Update Recommendations display in BusinessIdea card
    - Display launch_recommendations as an ordered numbered list (1, 2, 3...)
    - Each item shows timeframe prefix highlighted/bolded and action text
    - Only display when user has paid access
    - _Requirements: 6.1, 6.4_

- [x] 10. Frontend: Market Trend card enrichments
  - [x] 10.1 Update MarketTrend card to display enriched data
    - Show market_volume_estimate and growth_rate_percent when available in format: "Объём рынка: ~{volume}, Рост: +{rate}% г/г с учётом инфляции"
    - Show data_source_label badge ("ИИ-оценка") when data_source_label is not null
    - Graceful fallback: display existing trend data when enrichment fields are null
    - _Requirements: 3.4, 3.5_

  - [ ]* 10.2 Write property test: Market data display format
    - **Property 6: Market data display format**
    - **Validates: Requirements 3.5**

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Integration wiring and backward compatibility
  - [x] 12.1 Wire enrichment services into the analysis pipeline in `backend/app/api/router.py`
    - Import MentionsValidator, MarketDataService, CompetitorLookupService
    - Call `aggregate_and_enrich` (or modified flow) after hierarchical_aggregate in the niche_search path
    - Pass source_posts to MentionsValidator for keyword recount
    - Ensure old reports (risks as strings, no analogues) still deserialize without errors
    - _Requirements: 1.1, 1.2, 3.1, 4.1_

  - [ ]* 12.2 Write integration tests for the full enrichment pipeline
    - Mock SerpAPI and Linkup API responses
    - Verify end-to-end: chunk → analyze → aggregate → validate → enrich → serialize
    - Test timeout scenario: verify fallback labels are applied
    - Test backward compatibility: load old report JSON with string risks, verify no crash
    - _Requirements: 1.1, 3.4, 4.4_

- [x] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Hypothesis library, already in project)
- Unit tests validate specific examples and edge cases
- The enrichment services (MarketDataService, CompetitorLookupService) require API keys; without them the system gracefully falls back to LLM-only data
- Backward compatibility is critical: old reports stored in JSONB must deserialize without errors after schema changes

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "3.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "2.5", "3.2", "3.3", "4.2", "4.3", "4.4"] },
    { "id": 3, "tasks": ["6.1"] },
    { "id": 4, "tasks": ["6.2"] },
    { "id": 5, "tasks": ["6.3", "6.4", "6.5", "6.6", "6.7"] },
    { "id": 6, "tasks": ["8.1", "9.1", "9.2", "9.3", "10.1"] },
    { "id": 7, "tasks": ["10.2"] },
    { "id": 8, "tasks": ["12.1"] },
    { "id": 9, "tasks": ["12.2"] }
  ]
}
```
