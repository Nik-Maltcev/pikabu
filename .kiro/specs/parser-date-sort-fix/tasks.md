# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** — URL Missing `sort=date` Parameter
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Use Hypothesis to generate random Pikabu community URL paths and `since` datetimes; scope the property to verify that every URL passed to `_fetch_page` contains `sort=date`
  - Mock `_fetch_page` to capture the URLs it receives, then call `parse_posts(topic_url, since)` on the UNFIXED code
  - Assert that ALL captured URLs contain the query parameter `sort=date` (from Bug Condition `isBugCondition`: `"sort=date" NOT IN page_url`)
  - Assert that page 1 URL contains `sort=date` and page 2+ URLs contain both `sort=date` and `page=N`
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists because `sort=date` is never in the URL)
  - Document counterexamples found (e.g., `parse_posts("https://pikabu.ru/community/medicina", since)` passes URL without `sort=date` to `_fetch_page`)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 2.1, 2.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** — Pagination, Filtering, and Early-Exit Behavior Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe on UNFIXED code: `parse_posts` with a page of mixed fresh/old posts correctly filters by `since` and collects only fresh posts
  - Observe on UNFIXED code: `parse_posts` stops pagination when all posts on a page are older than `since` (early-exit)
  - Observe on UNFIXED code: `parse_posts` appends `?page=N` for pages beyond the first
  - Observe on UNFIXED code: `_extract_posts_from_html` returns the same parsed fields (title, body, published_at, rating, comments_count, url)
  - Observe on UNFIXED code: `_fetch_page` retry logic for 429/5xx is unchanged (no modifications to that method)
  - Write property-based tests using Hypothesis:
    - Generate random sets of posts with various `published_at` dates and verify filtering by `since` produces the correct subset
    - Generate random page counts and verify early-exit triggers when a page has only old posts
  - Write example-based preservation tests:
    - Verify pagination URL pattern (`?page=2`, `?page=3`, etc.) is appended correctly
    - Verify `_extract_posts_from_html` and `_extract_comments_from_html` output is identical to current behavior
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix for URL missing `sort=date` parameter in `parse_posts`

  - [x] 3.1 Implement the fix
    - Add `_ensure_date_sort(url: str) -> str` helper function using `urllib.parse` (urlparse, parse_qs, urlencode, urlunparse) that injects `sort=date` into any URL
    - Handle edge cases: URL with no existing query params (`?sort=date`), URL with existing params (`&sort=date`), URL that already has `sort=date` (no-op)
    - Call `topic_url = _ensure_date_sort(topic_url)` as the first line of `parse_posts`, before the pagination loop
    - Update page URL construction: change `f"{topic_url}?page={page}"` to `f"{topic_url}&page={page}"` for page > 1 (since base URL now always has query params from `sort=date`)
    - _Bug\_Condition: isBugCondition(input) where `"sort=date" NOT IN constructPageUrl(input.topic_url, page=1)`_
    - _Expected\_Behavior: ALL URLs passed to `_fetch_page` contain `sort=date` query parameter_
    - _Preservation: Pagination `page=N`, post filtering by `since`, early-exit on all-old pages, retry logic, HTML parsing — all unchanged_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** — URL Contains `sort=date` Parameter
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior (all URLs must contain `sort=date`)
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** — Pagination, Filtering, and Early-Exit Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint — Ensure all tests pass
  - Run the full test suite: `pytest backend/tests/test_parser.py -v`
  - Ensure all existing tests plus new exploration and preservation tests pass
  - Ensure no regressions in HTML parsing, comment parsing, retry logic, or pagination
  - Ask the user if questions arise
