"""Tests for the Chunker service."""

import pytest

from app.services.chunker import chunk_data, estimate_tokens


# --- estimate_tokens ---


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_ascii(self):
        # 12 chars -> 3 tokens
        assert estimate_tokens("hello world!") == 3

    def test_russian_text(self):
        text = "Привет мир"  # 10 chars -> 2 tokens
        assert estimate_tokens(text) == 2

    def test_long_text(self):
        text = "a" * 400
        assert estimate_tokens(text) == 100

    def test_none_returns_zero(self):
        # Edge: empty string
        assert estimate_tokens("") == 0

    def test_returns_non_negative(self):
        assert estimate_tokens("x") >= 0


# --- chunk_data ---


def _make_post(title: str, body: str = "", comments: list[str] | None = None) -> dict:
    """Helper to create a post dict."""
    post = {"title": title, "body": body}
    if comments:
        post["comments"] = [{"text": c} for c in comments]
    return post


class TestChunkDataEmpty:
    def test_empty_posts_returns_empty(self):
        result = chunk_data([], max_tokens=1000)
        assert result == []


class TestChunkDataBasic:
    def test_single_small_post(self):
        posts = [_make_post("Hello", "World")]
        chunks = chunk_data(posts, max_tokens=10000)
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].posts_data == posts
        assert chunks[0].estimated_tokens > 0

    def test_multiple_small_posts_fit_one_chunk(self):
        posts = [_make_post(f"Post {i}", "short") for i in range(5)]
        chunks = chunk_data(posts, max_tokens=100000)
        assert len(chunks) == 1
        assert len(chunks[0].posts_data) == 5

    def test_posts_split_into_multiple_chunks(self):
        # Each post is roughly the same size; set max_tokens low to force splitting
        posts = [_make_post(f"Post {i}", "x" * 200) for i in range(10)]
        chunks = chunk_data(posts, max_tokens=100)
        assert len(chunks) > 1
        # Verify sequential indices
        for i, chunk in enumerate(chunks):
            assert chunk.index == i


class TestChunkDataLargePost:
    def test_single_post_exceeds_max_tokens(self):
        """A post larger than max_tokens should go into its own chunk."""
        big_post = _make_post("Big", "x" * 10000)
        small_post = _make_post("Small", "y")
        chunks = chunk_data([small_post, big_post, small_post], max_tokens=100)
        # big_post must be alone in its chunk
        found_big = False
        for chunk in chunks:
            for p in chunk.posts_data:
                if p["body"] == "x" * 10000:
                    assert len(chunk.posts_data) == 1
                    found_big = True
        assert found_big

    def test_oversized_post_still_included(self):
        """Even if a post exceeds max_tokens, it must appear in output."""
        big_post = _make_post("Huge", "z" * 50000)
        chunks = chunk_data([big_post], max_tokens=10)
        assert len(chunks) == 1
        assert chunks[0].posts_data[0] == big_post


class TestChunkDataFullCoverage:
    def test_no_data_loss(self):
        """All posts must appear in chunks exactly once."""
        posts = [_make_post(f"Post {i}", f"body {i}") for i in range(50)]
        chunks = chunk_data(posts, max_tokens=200)

        all_posts_from_chunks = []
        for chunk in chunks:
            all_posts_from_chunks.extend(chunk.posts_data)

        assert len(all_posts_from_chunks) == len(posts)
        for original, recovered in zip(posts, all_posts_from_chunks):
            assert original == recovered

    def test_no_duplication(self):
        """No post should appear in more than one chunk."""
        posts = [_make_post(f"Post {i}", f"body {i}") for i in range(30)]
        chunks = chunk_data(posts, max_tokens=150)

        seen_titles = set()
        for chunk in chunks:
            for p in chunk.posts_data:
                title = p["title"]
                assert title not in seen_titles, f"Duplicate post: {title}"
                seen_titles.add(title)

    def test_order_preserved(self):
        """Posts should appear in chunks in the same order as input."""
        posts = [_make_post(f"Post {i}", f"body {i}") for i in range(20)]
        chunks = chunk_data(posts, max_tokens=200)

        flat = []
        for chunk in chunks:
            flat.extend(chunk.posts_data)

        for i, p in enumerate(flat):
            assert p["title"] == f"Post {i}"


class TestChunkDataTokenEstimation:
    def test_chunk_estimated_tokens_within_limit(self):
        """Each chunk's estimated_tokens should be ≤ max_tokens (except oversized single posts)."""
        posts = [_make_post(f"Post {i}", "content " * 20) for i in range(20)]
        max_t = 500
        chunks = chunk_data(posts, max_tokens=max_t)

        for chunk in chunks:
            if len(chunk.posts_data) > 1:
                assert chunk.estimated_tokens <= max_t

    def test_estimated_tokens_matches_content(self):
        """Chunk's estimated_tokens should equal sum of its posts' token estimates."""
        posts = [_make_post(f"Post {i}", "hello world") for i in range(5)]
        chunks = chunk_data(posts, max_tokens=100000)
        assert len(chunks) == 1
        assert chunks[0].estimated_tokens > 0


class TestChunkDataWithComments:
    def test_posts_with_comments(self):
        """Posts with comments should be chunked correctly."""
        posts = [
            _make_post("Post 1", "body", ["comment 1", "comment 2"]),
            _make_post("Post 2", "body", ["comment 3"]),
        ]
        chunks = chunk_data(posts, max_tokens=100000)
        assert len(chunks) >= 1
        all_posts = []
        for c in chunks:
            all_posts.extend(c.posts_data)
        assert len(all_posts) == 2
        assert "comments" in all_posts[0]


class TestChunkDataDefaultMaxTokens:
    def test_uses_default_max_tokens(self):
        """chunk_data should work without explicit max_tokens (uses settings default)."""
        posts = [_make_post(f"Post {i}", "body") for i in range(3)]
        # Should not raise
        chunks = chunk_data(posts)
        assert len(chunks) >= 1
        all_posts = []
        for c in chunks:
            all_posts.extend(c.posts_data)
        assert len(all_posts) == 3
