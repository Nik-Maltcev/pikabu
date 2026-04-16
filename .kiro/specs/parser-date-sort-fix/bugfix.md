# Bugfix Requirements Document

## Introduction

The Pikabu topic parser fetches community pages using the default URL (e.g., `https://pikabu.ru/community/medicina`), which returns posts sorted by popularity ("hot"). When a user requests analysis for a short period (e.g., 7 days), the first page of "hot" results may contain only old popular posts. The parser's early-exit logic (`found_old and fresh_on_page == 0`) then stops pagination immediately, returning 0 posts — even though fresh posts exist on the date-sorted pages.

The fix must ensure the parser always fetches posts sorted by date (newest first) so that the early-exit optimization works correctly and fresh posts are reliably collected.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a topic URL uses the default sort order (e.g., `https://pikabu.ru/community/medicina`) THEN the system fetches posts sorted by popularity ("hot"), causing the first page to contain old popular posts instead of recent ones

1.2 WHEN the parser encounters a page where all posts are older than the requested period (due to "hot" sorting) THEN the system stops pagination immediately with 0 results, even though fresh posts exist on the site under date-sorted pages

1.3 WHEN a user requests analysis for a short time period (e.g., 7 days) on a community with many popular old posts THEN the system returns 0 posts and 0 chunks because the early-exit condition triggers on the first page

### Expected Behavior (Correct)

2.1 WHEN a topic URL uses the default sort order THEN the system SHALL modify the URL to request date-sorted (newest first) results before fetching pages

2.2 WHEN the parser fetches pages with date sorting applied THEN the system SHALL encounter fresh posts on the first pages, allowing the early-exit logic to work correctly (stopping only when genuinely reaching posts older than the requested period)

2.3 WHEN a user requests analysis for a short time period (e.g., 7 days) on any community THEN the system SHALL return all posts published within that period by paginating through date-sorted pages

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the parser paginates through multiple pages THEN the system SHALL CONTINUE TO append `?page=N` for pages beyond the first

3.2 WHEN a post's `published_at` is older than the `since` threshold THEN the system SHALL CONTINUE TO skip that post and not include it in results

3.3 WHEN all posts on a page are older than the `since` threshold (with date sorting) THEN the system SHALL CONTINUE TO stop pagination early, as this correctly indicates no more fresh posts exist

3.4 WHEN the parser encounters HTTP errors (429, 5xx) or network errors THEN the system SHALL CONTINUE TO apply the existing retry logic unchanged

3.5 WHEN parsing post HTML elements THEN the system SHALL CONTINUE TO extract title, body, published_at, rating, comments_count, and URL using the same selectors and logic
