# Parser Date Sort Fix — Bugfix Design

## Overview

The Pikabu topic parser (`ParserService.parse_posts`) fetches community pages using the topic URL as-is (e.g., `https://pikabu.ru/community/medicina`), which defaults to popularity-based ("hot") sorting. For short analysis periods (e.g., 7 days), the first page of hot results often contains only old popular posts. The early-exit logic (`found_old and fresh_on_page == 0`) then terminates pagination immediately, returning 0 posts — even though fresh posts exist on date-sorted pages.

The fix appends `?sort=date` (or `&sort=date` when other query params exist) to the topic URL before fetching, ensuring posts are returned newest-first. This makes the early-exit optimization work correctly: fresh posts appear on the first pages, and pagination stops only when genuinely reaching posts older than the requested period.

## Glossary

- **Bug_Condition (C)**: The parser fetches a topic URL without a date-sort parameter, causing the server to return popularity-sorted results
- **Property (P)**: The parser always requests date-sorted pages, so fresh posts appear first and the early-exit logic works correctly
- **Preservation**: Pagination (`?page=N`), post filtering by `since`, early-exit on all-old pages, retry logic, and HTML parsing must remain unchanged
- **`parse_posts`**: The method in `backend/app/services/parser.py` that fetches and paginates through topic pages, filtering posts by date
- **`_fetch_page`**: The method that performs the actual HTTP request with retry logic
- **`since`**: The datetime threshold — posts older than this are skipped
- **Hot sorting**: Pikabu's default sort order, ranking posts by popularity rather than recency

## Bug Details

### Bug Condition

The bug manifests when `parse_posts` constructs the page URL without appending a date-sort query parameter. The Pikabu server defaults to "hot" sorting, which returns popular posts regardless of age. For communities with many popular old posts, the first page may contain zero posts within the requested time period, causing the early-exit condition to fire immediately.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type { topic_url: string, since: datetime }
  OUTPUT: boolean

  page_url := constructPageUrl(input.topic_url, page=1)
  RETURN "sort=date" NOT IN page_url
         AND serverReturnsHotSortedPosts(page_url)
         AND freshPostsExistOnDateSortedPages(input.topic_url, input.since)
         AND allPostsOnFirstHotPageAreOlderThan(input.since)
END FUNCTION
```

### Examples

- **Community "medicina", 7-day window**: URL `https://pikabu.ru/community/medicina` returns hot posts from months ago on page 1. Parser finds 0 fresh posts, exits immediately. Date-sorted URL would return today's posts first.
- **Community "science", 3-day window**: Same pattern — hot page 1 has viral posts from weeks ago. Early-exit triggers with 0 results.
- **Community "pikabu", 30-day window**: With a longer window, some hot posts may fall within range, so the bug is intermittent — sometimes returns partial results, sometimes 0.
- **Edge case — URL already has query params**: If the topic URL were `https://pikabu.ru/community/test?tag=foo`, the fix must append `&sort=date` rather than `?sort=date`.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Pagination must continue to append `?page=N` (or `&page=N`) for pages beyond the first
- Posts with `published_at` older than `since` must still be skipped
- When all posts on a page are older than `since` (with date sorting), early-exit must still stop pagination
- HTTP error retry logic (429, 5xx) in `_fetch_page` must remain unchanged
- HTML parsing in `_extract_posts_from_html` and `_extract_comments_from_html` must remain unchanged
- Comment parsing flow must remain unchanged

**Scope:**
All behavior unrelated to the URL construction in `parse_posts` should be completely unaffected. This includes:
- The `_fetch_page` method internals (retry, headers, proxy)
- All static HTML parsing methods
- The `parse_topic` orchestration logic
- The `parse_comments` method
- Database save operations

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is:

1. **Missing sort parameter in URL construction**: In `parse_posts` (line ~107 of parser.py), the `page_url` is constructed as:
   ```python
   page_url = f"{topic_url}?page={page}" if page > 1 else topic_url
   ```
   For page 1, the raw `topic_url` is used with no sort parameter. For subsequent pages, only `?page=N` is appended. Neither case includes `sort=date`.

2. **Pikabu defaults to "hot" sorting**: Without an explicit `sort=date` parameter, Pikabu returns posts sorted by popularity. This is a server-side default, not a parser bug per se, but the parser must account for it.

3. **Early-exit logic is correct but depends on date ordering**: The condition `found_old and fresh_on_page == 0` is a valid optimization for date-sorted pages (if all posts are old, no newer posts exist on later pages). But with hot sorting, old posts on page 1 don't imply absence of fresh posts on later pages.

## Correctness Properties

Property 1: Bug Condition — Date-sorted URL is always used

_For any_ topic URL passed to `parse_posts`, the actual HTTP request URL SHALL contain the `sort=date` query parameter, ensuring the server returns posts sorted by date (newest first) rather than by popularity.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation — Pagination, filtering, and early-exit behavior unchanged

_For any_ input where the topic URL already includes `sort=date` (i.e., the bug condition does NOT hold), the fixed `parse_posts` SHALL produce the same pagination URLs (with `page=N`), apply the same `since`-based filtering, and trigger the same early-exit logic as the original function, preserving all existing post-collection behavior.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `backend/app/services/parser.py`

**Function**: `parse_posts`

**Specific Changes**:

1. **Add a URL helper to ensure `sort=date`**: Before the pagination loop, modify `topic_url` to include `sort=date`. Use `urllib.parse` to properly handle URLs that may already have query parameters:
   ```python
   from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

   def _ensure_date_sort(url: str) -> str:
       parsed = urlparse(url)
       params = parse_qs(parsed.query)
       params["sort"] = ["date"]
       new_query = urlencode(params, doseq=True)
       return urlunparse(parsed._replace(query=new_query))
   ```

2. **Apply the helper at the start of `parse_posts`**: Add `topic_url = _ensure_date_sort(topic_url)` as the first line of the method, before the pagination loop.

3. **Adjust page URL construction**: The current logic uses `?page=N` for page > 1. With `sort=date` already in the base URL, page 2+ must use `&page=N`. The `_ensure_date_sort` helper ensures the base URL has `sort=date`, so pagination should use proper URL joining:
   ```python
   page_url = f"{topic_url}&page={page}" if page > 1 else topic_url
   ```
   Or better, use `urllib.parse` to add the page parameter cleanly.

4. **No changes to `_fetch_page`**: The HTTP fetching and retry logic remains untouched.

5. **No changes to HTML parsing**: `_extract_posts_from_html` and related static methods remain untouched.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Plan**: Write tests that inspect the URLs passed to `_fetch_page` by `parse_posts` and verify whether `sort=date` is present. Run on UNFIXED code to observe failures.

**Test Cases**:
1. **Basic URL test**: Call `parse_posts("https://pikabu.ru/community/test", since)` and capture the URL passed to `_fetch_page` — expect it to lack `sort=date` (will fail on unfixed code)
2. **Pagination URL test**: Trigger pagination and check page 2+ URLs — expect them to lack `sort=date` (will fail on unfixed code)
3. **Short period with hot-sorted mock**: Provide a mock page with only old posts (simulating hot sort) and verify 0 posts returned (demonstrates the user-visible bug)

**Expected Counterexamples**:
- URLs passed to `_fetch_page` do not contain `sort=date`
- Parser returns 0 posts when fresh posts would exist on date-sorted pages

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := parse_posts_fixed(input.topic_url, input.since)
  urls_fetched := capture_urls_from_fetch_page_calls()
  ASSERT ALL url IN urls_fetched: "sort=date" IN url
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT parse_posts_original(input) = parse_posts_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many URL variations automatically to verify `sort=date` is always present
- It catches edge cases in URL construction (existing query params, fragments, etc.)
- It provides strong guarantees that pagination, filtering, and early-exit are unchanged

**Test Plan**: Observe behavior on UNFIXED code first for pagination and filtering, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Pagination preservation**: Verify that `?page=N` is still appended correctly for pages beyond the first, coexisting with `sort=date`
2. **Post filtering preservation**: Verify that posts older than `since` are still excluded from results
3. **Early-exit preservation**: Verify that when all posts on a date-sorted page are old, pagination stops
4. **Retry logic preservation**: Verify that `_fetch_page` retry behavior is unchanged (no modifications to that method)

### Unit Tests

- Test `_ensure_date_sort` helper with various URL formats (no params, existing params, already has `sort=date`)
- Test that `parse_posts` passes date-sorted URLs to `_fetch_page`
- Test pagination URL construction with `sort=date` base URL
- Test early-exit still works correctly with date-sorted pages

### Property-Based Tests

- Generate random Pikabu community URLs and verify `_ensure_date_sort` always produces a URL with `sort=date`
- Generate random page numbers and verify pagination URLs contain both `sort=date` and correct `page=N`
- Generate random sets of posts with various dates and verify filtering/early-exit behavior is preserved

### Integration Tests

- Test `parse_topic` end-to-end with mocked HTTP returning date-sorted pages
- Test that a short analysis period (7 days) returns fresh posts when date-sorted pages are provided
- Test that the full pipeline (parse → save → metadata) works with the URL fix
