"""Tests for SQLAlchemy models and database session setup."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import inspect

from app.models.database import (
    AnalysisTask,
    Base,
    Comment,
    ParseMetadata,
    PartialResult,
    Post,
    Report,
    Topic,
)


def test_all_seven_tables_registered():
    """All 7 tables from the design doc are present in metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "topics",
        "posts",
        "comments",
        "analysis_tasks",
        "partial_results",
        "reports",
        "parse_metadata",
    }
    assert expected == table_names


def test_topic_columns():
    mapper = inspect(Topic)
    col_names = {c.key for c in mapper.columns}
    assert col_names == {
        "id", "pikabu_id", "name", "subscribers_count",
        "url", "last_fetched_at", "created_at", "source",
    }


def test_post_columns():
    mapper = inspect(Post)
    col_names = {c.key for c in mapper.columns}
    assert col_names == {
        "id", "topic_id", "pikabu_post_id", "title", "body",
        "published_at", "rating", "comments_count", "url", "parsed_at", "source",
    }


def test_comment_columns():
    mapper = inspect(Comment)
    col_names = {c.key for c in mapper.columns}
    assert col_names == {
        "id", "post_id", "pikabu_comment_id", "body",
        "published_at", "rating", "parsed_at",
    }


def test_analysis_task_columns():
    mapper = inspect(AnalysisTask)
    col_names = {c.key for c in mapper.columns}
    assert col_names == {
        "id", "topic_id", "status", "progress_percent",
        "current_stage", "total_chunks", "processed_chunks",
        "error_message", "created_at", "updated_at",
    }


def test_partial_result_columns():
    mapper = inspect(PartialResult)
    col_names = {c.key for c in mapper.columns}
    assert col_names == {
        "id", "task_id", "chunk_index",
        "topics_found", "user_problems", "active_discussions", "created_at",
    }


def test_report_columns():
    mapper = inspect(Report)
    col_names = {c.key for c in mapper.columns}
    assert col_names == {
        "id", "topic_id", "task_id",
        "hot_topics", "user_problems", "trending_discussions", "generated_at", "sources",
    }


def test_parse_metadata_columns():
    mapper = inspect(ParseMetadata)
    col_names = {c.key for c in mapper.columns}
    assert col_names == {
        "id", "topic_id", "last_parsed_at", "posts_count", "comments_count",
    }


def test_indexes_exist():
    """Verify all required indexes from the design doc are defined."""
    expected_indexes = {
        "idx_posts_topic_id",
        "idx_posts_published_at",
        "idx_comments_post_id",
        "idx_analysis_tasks_topic_id",
        "idx_analysis_tasks_status",
        "idx_reports_topic_id",
        "idx_reports_generated_at",
        "idx_parse_metadata_topic_id",
    }
    actual_indexes = set()
    for table in Base.metadata.tables.values():
        for idx in table.indexes:
            actual_indexes.add(idx.name)
    assert expected_indexes.issubset(actual_indexes)


def test_topic_pikabu_id_unique():
    table = Base.metadata.tables["topics"]
    pikabu_id_col = table.c.pikabu_id
    assert pikabu_id_col.unique is True


def test_analysis_task_id_is_uuid():
    task = AnalysisTask()
    # Default should generate a UUID
    assert task.id is None or isinstance(task.id, uuid.UUID)


def test_analysis_task_default_status():
    task = AnalysisTask()
    # Column default is "pending"
    col = inspect(AnalysisTask).columns["status"]
    assert col.default.arg == "pending"


def test_post_foreign_key_to_topics():
    table = Base.metadata.tables["posts"]
    fks = {fk.target_fullname for fk in table.foreign_keys}
    assert "topics.id" in fks


def test_comment_foreign_key_to_posts():
    table = Base.metadata.tables["comments"]
    fks = {fk.target_fullname for fk in table.foreign_keys}
    assert "posts.id" in fks


def test_partial_result_foreign_key_to_analysis_tasks():
    table = Base.metadata.tables["partial_results"]
    fks = {fk.target_fullname for fk in table.foreign_keys}
    assert "analysis_tasks.id" in fks


def test_report_foreign_keys():
    table = Base.metadata.tables["reports"]
    fks = {fk.target_fullname for fk in table.foreign_keys}
    assert "topics.id" in fks
    assert "analysis_tasks.id" in fks


def test_parse_metadata_topic_id_unique():
    table = Base.metadata.tables["parse_metadata"]
    topic_id_col = table.c.topic_id
    assert topic_id_col.unique is True


def test_cascade_delete_on_foreign_keys():
    """Foreign keys with ON DELETE CASCADE are set correctly."""
    tables_with_cascade = ["posts", "comments", "analysis_tasks", "partial_results", "reports", "parse_metadata"]
    for tname in tables_with_cascade:
        table = Base.metadata.tables[tname]
        for fk in table.foreign_keys:
            if fk.target_fullname == "topics.id" or fk.target_fullname == "posts.id" or (
                fk.target_fullname == "analysis_tasks.id" and tname == "partial_results"
            ):
                assert fk.ondelete == "CASCADE", f"{tname}.{fk.parent.name} should CASCADE"


def test_database_session_module_imports():
    """Verify the database module provides the expected exports."""
    from app.database import async_session, engine, get_session
    assert async_session is not None
    assert engine is not None
    assert callable(get_session)
