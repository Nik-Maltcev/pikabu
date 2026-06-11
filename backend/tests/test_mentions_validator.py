"""Unit tests for MentionsValidator service."""

import pytest

from app.models.schemas import KeyPain
from app.services.mentions_validator import MentionsValidator


@pytest.fixture
def validator():
    return MentionsValidator()


@pytest.fixture
def sample_posts():
    return [
        {
            "title": "Проблема с доставкой еды",
            "body": "Постоянно опаздывают курьеры, еда приходит холодной",
            "comments": [
                {"text": "У меня тоже проблема с доставкой, ждал час"},
                {"text": "Перешёл на самовывоз из-за этого"},
            ],
        },
        {
            "title": "Качество обслуживания в ресторанах",
            "body": "Сервис ухудшился, официанты грубят",
            "comments": ["Согласен, сервис стал хуже"],
        },
        {
            "title": "Цены на продукты растут",
            "body": "Инфляция бьёт по кошельку, продукты дорожают каждый месяц",
            "comments": [],
        },
    ]


class TestValidateAndFix:
    """Tests for MentionsValidator.validate_and_fix method."""

    def test_zero_mentions_get_recounted(self, validator, sample_posts):
        """Pains with mentions_count=0 should be recounted using keywords."""
        pains = [
            KeyPain(
                description="Проблема с доставкой еды — курьеры опаздывают",
                frequency="Часто",
                emotional_charge="Высокий",
                mentions_count=0,
            ),
        ]
        result = validator.validate_and_fix(pains, sample_posts)
        # Should find at least 1 post mentioning "доставкой" or "курьеры"
        assert result[0].mentions_count >= 1

    def test_zero_mentions_no_match_gets_one(self, validator, sample_posts):
        """Pains with mentions_count=0 and no keyword matches should get 1."""
        pains = [
            KeyPain(
                description="xyz абракадабра невозможныйтермин",
                frequency="Редко, но метко",
                emotional_charge="Средний",
                mentions_count=0,
            ),
        ]
        result = validator.validate_and_fix(pains, sample_posts)
        assert result[0].mentions_count == 1

    def test_nonzero_mentions_preserved(self, validator, sample_posts):
        """Pains with mentions_count > 0 should keep their original value."""
        pains = [
            KeyPain(
                description="Качество сервиса",
                frequency="Часто",
                emotional_charge="Высокий",
                mentions_count=5,
            ),
        ]
        result = validator.validate_and_fix(pains, sample_posts)
        assert result[0].mentions_count == 5

    def test_all_output_pains_have_minimum_one(self, validator, sample_posts):
        """All output pains must have mentions_count >= 1."""
        pains = [
            KeyPain(description="A", frequency="f", emotional_charge="e", mentions_count=0),
            KeyPain(description="B", frequency="f", emotional_charge="e", mentions_count=3),
            KeyPain(description="C", frequency="f", emotional_charge="e", mentions_count=0),
        ]
        result = validator.validate_and_fix(pains, sample_posts)
        assert all(p.mentions_count >= 1 for p in result)

    def test_sorted_descending(self, validator, sample_posts):
        """Output should be sorted descending by mentions_count."""
        pains = [
            KeyPain(description="Low", frequency="f", emotional_charge="e", mentions_count=1),
            KeyPain(description="High", frequency="f", emotional_charge="e", mentions_count=10),
            KeyPain(description="Mid", frequency="f", emotional_charge="e", mentions_count=5),
        ]
        result = validator.validate_and_fix(pains, sample_posts)
        counts = [p.mentions_count for p in result]
        assert counts == sorted(counts, reverse=True)

    def test_stable_sort_preserves_order_for_ties(self, validator):
        """For equal mentions_count, original LLM order should be preserved."""
        pains = [
            KeyPain(description="First", frequency="f", emotional_charge="e", mentions_count=3),
            KeyPain(description="Second", frequency="f", emotional_charge="e", mentions_count=3),
            KeyPain(description="Third", frequency="f", emotional_charge="e", mentions_count=3),
        ]
        result = validator.validate_and_fix(pains, [])
        descriptions = [p.description for p in result]
        assert descriptions == ["First", "Second", "Third"]

    def test_empty_input(self, validator):
        """Empty input should return empty output."""
        result = validator.validate_and_fix([], [])
        assert result == []

    def test_empty_posts_with_zero_mentions(self, validator):
        """Zero mentions with empty posts list should assign 1."""
        pains = [
            KeyPain(description="Something", frequency="f", emotional_charge="e", mentions_count=0),
        ]
        result = validator.validate_and_fix(pains, [])
        assert result[0].mentions_count == 1

    def test_negative_mentions_get_fixed(self, validator):
        """Negative mentions_count should be corrected to 1."""
        pains = [
            KeyPain(description="Negative", frequency="f", emotional_charge="e", mentions_count=-5),
        ]
        result = validator.validate_and_fix(pains, [])
        assert result[0].mentions_count == 1


class TestKeywordRecount:
    """Tests for MentionsValidator._keyword_recount method."""

    def test_finds_keyword_in_title(self, validator):
        """Should count posts where keywords appear in title."""
        pain = KeyPain(
            description="Проблема с доставкой",
            frequency="Часто",
            emotional_charge="Высокий",
        )
        posts = [
            {"title": "Доставкой занимаются роботы", "body": "", "comments": []},
            {"title": "Погода сегодня хорошая", "body": "", "comments": []},
        ]
        count = validator._keyword_recount(pain, posts)
        assert count == 1

    def test_finds_keyword_in_body(self, validator):
        """Should count posts where keywords appear in body."""
        pain = KeyPain(
            description="Плохое качество продуктов",
            frequency="Часто",
            emotional_charge="Высокий",
        )
        posts = [
            {"title": "Обзор", "body": "Качество продуктов оставляет желать лучшего"},
        ]
        count = validator._keyword_recount(pain, posts)
        assert count == 1

    def test_finds_keyword_in_comments(self, validator):
        """Should count posts where keywords appear in comments."""
        pain = KeyPain(
            description="Долгое ожидание ответа поддержки",
            frequency="Часто",
            emotional_charge="Средний",
        )
        posts = [
            {
                "title": "Сервис",
                "body": "Написал в поддержку",
                "comments": [{"text": "Ожидание ответа заняло неделю"}],
            },
        ]
        count = validator._keyword_recount(pain, posts)
        assert count == 1

    def test_returns_zero_for_no_matches(self, validator):
        """Should return 0 when no posts match any keywords."""
        pain = KeyPain(
            description="Уникальная специфическая проблематика",
            frequency="Редко, но метко",
            emotional_charge="Средний",
        )
        posts = [
            {"title": "Погода", "body": "Сегодня солнечно"},
        ]
        count = validator._keyword_recount(pain, posts)
        assert count == 0

    def test_case_insensitive_matching(self, validator):
        """Keyword matching should be case-insensitive."""
        pain = KeyPain(
            description="ДОСТАВКА товаров",
            frequency="Часто",
            emotional_charge="Высокий",
        )
        posts = [
            {"title": "проблемы с доставка", "body": ""},
        ]
        count = validator._keyword_recount(pain, posts)
        assert count == 1

    def test_empty_description_returns_zero(self, validator):
        """Empty description should yield no keywords and return 0."""
        pain = KeyPain(
            description="",
            frequency="Часто",
            emotional_charge="Средний",
        )
        posts = [{"title": "Anything", "body": "Something"}]
        count = validator._keyword_recount(pain, posts)
        assert count == 0

    def test_stop_words_only_description_returns_zero(self, validator):
        """Description with only stop-words should return 0."""
        pain = KeyPain(
            description="и в на с по к у о",
            frequency="Часто",
            emotional_charge="Средний",
        )
        posts = [{"title": "и в на с по", "body": "к у о"}]
        count = validator._keyword_recount(pain, posts)
        assert count == 0

    def test_comments_as_string_list(self, validator):
        """Should handle comments as a plain list of strings."""
        pain = KeyPain(
            description="проблема сервиса",
            frequency="Часто",
            emotional_charge="Высокий",
        )
        posts = [
            {"title": "Тест", "body": "", "comments": ["Плохой сервиса качество"]},
        ]
        count = validator._keyword_recount(pain, posts)
        assert count == 1
