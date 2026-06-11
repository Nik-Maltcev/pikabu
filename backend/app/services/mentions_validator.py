"""Validates and corrects mentions_count in key_pains after LLM generation.

Ensures all KeyPain objects have mentions_count >= 1 by performing keyword-based
recount against source posts when the LLM returns 0, and sorting results descending.
"""

from __future__ import annotations

import re

from app.models.schemas import KeyPain

# Russian stop-words and short words to exclude from keyword extraction
_STOP_WORDS: set[str] = {
    "и", "в", "на", "с", "по", "к", "у", "о", "из", "за", "от", "до",
    "для", "не", "но", "что", "как", "это", "все", "так", "его", "она",
    "они", "мы", "вы", "он", "её", "их", "при", "бы", "же", "ли",
    "если", "или", "то", "да", "нет", "уже", "ещё", "тоже", "также",
    "очень", "только", "можно", "нужно", "когда", "где", "там", "тут",
    "быть", "который", "этот", "свой", "весь", "такой", "какой",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "and", "but", "or", "nor", "not", "so", "if", "then", "that", "this",
    "it", "its", "he", "she", "they", "we", "you", "my", "your", "his",
    "her", "our", "their", "what", "which", "who", "whom", "when", "where",
}

# Minimum keyword length to be considered significant
_MIN_KEYWORD_LENGTH = 3


class MentionsValidator:
    """Validates and corrects mentions_count in key_pains after LLM generation."""

    def validate_and_fix(
        self,
        key_pains: list[KeyPain],
        source_posts: list[dict],
    ) -> list[KeyPain]:
        """Validate and fix mentions_count for all key pains.

        Steps:
        1. For each pain with mentions_count == 0: keyword-recount from source_posts
        2. If still 0 after recount: assign 1
        3. Ensure all mentions_count >= 1
        4. Sort descending by mentions_count (stable sort preserves LLM order for ties)

        Args:
            key_pains: List of KeyPain objects from LLM output.
            source_posts: List of post dicts with optional keys: title, body, comments.

        Returns:
            List of KeyPain objects with corrected mentions_count, sorted descending.
        """
        result: list[KeyPain] = []

        for pain in key_pains:
            if pain.mentions_count == 0:
                # Attempt keyword-based recount
                recount = self._keyword_recount(pain, source_posts)
                if recount > 0:
                    pain = pain.model_copy(update={"mentions_count": recount})
                else:
                    # Still 0 after recount — assign minimum of 1
                    pain = pain.model_copy(update={"mentions_count": 1})
            elif pain.mentions_count < 1:
                # Handle any negative values — ensure >= 1
                pain = pain.model_copy(update={"mentions_count": 1})

            result.append(pain)

        # Stable sort descending by mentions_count
        result.sort(key=lambda p: p.mentions_count, reverse=True)

        return result

    def _keyword_recount(self, pain: KeyPain, posts: list[dict]) -> int:
        """Count posts containing at least one keyword from pain.description.

        Extracts significant keywords (non-stop-words with length >= 3) from the
        pain's description, then counts how many posts have at least one keyword
        match in their title, body, or comments text.

        Args:
            pain: A KeyPain object whose description provides keywords.
            posts: List of post dicts with optional keys: title, body, comments.

        Returns:
            Number of posts containing at least one keyword.
        """
        keywords = self._extract_keywords(pain.description)
        if not keywords:
            return 0

        count = 0
        for post in posts:
            post_text = self._get_post_text(post)
            if not post_text:
                continue
            post_text_lower = post_text.lower()
            # Check if at least one keyword is present in the post text
            if any(kw in post_text_lower for kw in keywords):
                count += 1

        return count

    def _extract_keywords(self, description: str) -> list[str]:
        """Extract significant keywords from a pain description.

        Tokenizes text, removes stop-words and short tokens, returns lowercase keywords.

        Args:
            description: The pain description text.

        Returns:
            List of lowercase keyword strings.
        """
        # Tokenize: split on non-word characters (supports Cyrillic via \w)
        tokens = re.findall(r"\w+", description.lower())
        # Filter: remove stop-words and short tokens
        keywords = [
            token
            for token in tokens
            if token not in _STOP_WORDS and len(token) >= _MIN_KEYWORD_LENGTH
        ]
        return keywords

    def _get_post_text(self, post: dict) -> str:
        """Combine all text fields of a post into a single searchable string.

        Args:
            post: A post dict with optional keys: title, body, comments.

        Returns:
            Combined text from title, body, and comments.
        """
        parts: list[str] = []

        if title := post.get("title"):
            parts.append(str(title))

        if body := post.get("body"):
            parts.append(str(body))

        comments = post.get("comments")
        if comments:
            if isinstance(comments, list):
                for comment in comments:
                    if isinstance(comment, str):
                        parts.append(comment)
                    elif isinstance(comment, dict):
                        # Support comment dicts with "text" or "body" fields
                        comment_text = comment.get("text") or comment.get("body") or ""
                        if comment_text:
                            parts.append(str(comment_text))
            elif isinstance(comments, str):
                parts.append(comments)

        return " ".join(parts)
