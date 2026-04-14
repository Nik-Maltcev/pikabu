"""Chunker service for splitting posts into chunks for Gemini API analysis."""

import json

from app.config import settings
from app.models.schemas import Chunk


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a text string.

    Uses a heuristic of ~4 characters per token for Russian text,
    which accounts for Cyrillic characters being multi-byte in most tokenizers.

    Args:
        text: The text to estimate tokens for.

    Returns:
        Estimated token count (minimum 0).
    """
    if not text:
        return 0
    return max(0, len(text) // 4)


def _post_to_dict(post: dict) -> dict:
    """Normalize a post dict, keeping only relevant fields."""
    return post


def _estimate_post_tokens(post: dict) -> int:
    """Estimate token count for a single post serialized as JSON."""
    serialized = json.dumps(post, ensure_ascii=False)
    return estimate_tokens(serialized)


def chunk_data(
    posts: list[dict],
    max_tokens: int | None = None,
) -> list[Chunk]:
    """Split posts into chunks where each chunk's estimated tokens ≤ max_tokens.

    Each post (with its comments) goes into exactly one chunk — posts are never
    split across chunks. If a single post exceeds max_tokens, it goes into its
    own chunk (it cannot be split further).

    Args:
        posts: List of post dicts (each may contain nested comments).
        max_tokens: Maximum tokens per chunk. Defaults to 80% of
            settings.gemini_context_window.

    Returns:
        List of Chunk objects covering all input posts without loss or duplication.
    """
    if max_tokens is None:
        max_tokens = int(settings.gemini_context_window * 0.8)

    if not posts:
        return []

    chunks: list[Chunk] = []
    current_posts: list[dict] = []
    current_tokens: int = 0
    chunk_index: int = 0

    for post in posts:
        post_tokens = _estimate_post_tokens(post)

        # If adding this post would exceed the limit, finalize current chunk first
        if current_posts and (current_tokens + post_tokens) > max_tokens:
            chunks.append(Chunk(
                index=chunk_index,
                posts_data=current_posts,
                estimated_tokens=current_tokens,
            ))
            chunk_index += 1
            current_posts = []
            current_tokens = 0

        # Add post to current chunk (even if it alone exceeds max_tokens)
        current_posts.append(post)
        current_tokens += post_tokens

    # Don't forget the last chunk
    if current_posts:
        chunks.append(Chunk(
            index=chunk_index,
            posts_data=current_posts,
            estimated_tokens=current_tokens,
        ))

    return chunks
