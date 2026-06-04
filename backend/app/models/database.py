"""SQLAlchemy ORM models for all database tables."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    pikabu_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    subscribers_count = Column(Integer, nullable=True)
    url = Column(String(1000), nullable=False)
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    posts = relationship("Post", back_populates="topic", cascade="all, delete-orphan")
    analysis_tasks = relationship(
        "AnalysisTask", back_populates="topic", cascade="all, delete-orphan"
    )
    reports = relationship(
        "Report", back_populates="topic", cascade="all, delete-orphan"
    )
    parse_metadata = relationship(
        "ParseMetadata", back_populates="topic", uselist=False, cascade="all, delete-orphan"
    )
    source = Column(String(20), nullable=False, default="pikabu")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    topic_id = Column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=True
    )
    pikabu_post_id = Column(String(255), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    rating = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    url = Column(String(1000), nullable=False)
    parsed_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    source = Column(String(20), nullable=False, default="pikabu")

    topic = relationship("Topic", back_populates="posts")
    comments = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_posts_topic_id", "topic_id"),
        Index("idx_posts_published_at", "published_at"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True
    )
    pikabu_comment_id = Column(String(255), unique=True, nullable=False)
    body = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False)
    rating = Column(Integer, default=0)
    parsed_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    post = relationship("Post", back_populates="comments")

    __table_args__ = (Index("idx_comments_post_id", "post_id"),)


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_id = Column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=True
    )
    status = Column(String(50), nullable=False, default="pending")
    progress_percent = Column(Integer, default=0)
    current_stage = Column(String(100), nullable=True)
    total_chunks = Column(Integer, nullable=True)
    processed_chunks = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Contact info for notification
    contact_type = Column(String(20), nullable=True)  # email or telegram
    contact_value = Column(String(255), nullable=True)  # email address or telegram username
    
    # User who created the task (optional, for registered users)
    user_id = Column(Integer, nullable=True)

    topic = relationship("Topic", back_populates="analysis_tasks")
    partial_results = relationship(
        "PartialResult", back_populates="task", cascade="all, delete-orphan"
    )
    reports = relationship("Report", back_populates="task")
    analysis_mode = Column(String(30), nullable=False, default="topic_analysis")

    __table_args__ = (
        Index("idx_analysis_tasks_topic_id", "topic_id"),
        Index("idx_analysis_tasks_status", "status"),
    )


class PartialResult(Base):
    __tablename__ = "partial_results"

    id = Column(Integer, primary_key=True)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_tasks.id", ondelete="CASCADE"),
        nullable=True,
    )
    chunk_index = Column(Integer, nullable=False)
    topics_found = Column(JSONB, nullable=False, default=list)
    user_problems = Column(JSONB, nullable=False, default=list)
    active_discussions = Column(JSONB, nullable=False, default=list)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    task = relationship("AnalysisTask", back_populates="partial_results")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    topic_id = Column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=True
    )
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_tasks.id"),
        nullable=True,
    )
    hot_topics = Column(JSONB, nullable=False, default=list)
    user_problems = Column(JSONB, nullable=False, default=list)
    trending_discussions = Column(JSONB, nullable=False, default=list)
    generated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    sources = Column(String(50), nullable=False, default="pikabu")
    analysis_mode = Column(String(30), nullable=False, default="topic_analysis")
    niche_data = Column(JSONB, nullable=True)
    user_id = Column(Integer, nullable=True)  # linked user (optional)

    topic = relationship("Topic", back_populates="reports")
    task = relationship("AnalysisTask", back_populates="reports")

    __table_args__ = (
        Index("idx_reports_topic_id", "topic_id"),
        Index("idx_reports_generated_at", "generated_at"),
    )


class ParseMetadata(Base):
    __tablename__ = "parse_metadata"

    id = Column(Integer, primary_key=True)
    topic_id = Column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )
    last_parsed_at = Column(DateTime(timezone=True), nullable=False)
    posts_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)

    topic = relationship("Topic", back_populates="parse_metadata")

    __table_args__ = (Index("idx_parse_metadata_topic_id", "topic_id"),)


class DeviceLimit(Base):
    """Track free analysis usage per browser fingerprint."""

    __tablename__ = "device_limits"

    id = Column(Integer, primary_key=True)
    fingerprint = Column(String(64), unique=True, nullable=False, index=True)
    analyses_count = Column(Integer, nullable=False, default=0)
    first_seen_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_analysis_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("idx_device_limits_fingerprint", "fingerprint"),)


class User(Base):
    """User account for personal cabinet (email/password auth)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)  # Legacy, optional
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)  # bcrypt hash
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_users_phone", "phone"),
        Index("idx_users_email", "email"),
    )


class Payment(Base):
    """Track payments for report access via Robokassa."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    report_id = Column(
        Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=True
    )
    topic_id = Column(Integer, nullable=True)  # which topic was paid for
    amount = Column(Integer, nullable=False)  # in rubles
    status = Column(String(20), nullable=False, default="pending")  # pending, paid, failed
    access_token = Column(String(64), unique=True, nullable=False, index=True)
    robokassa_inv_id = Column(Integer, unique=True, nullable=True)
    task_id = Column(String(64), nullable=True)  # analysis task UUID after paid launch
    promo_code = Column(String(50), nullable=True)  # promo code used
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    paid_at = Column(DateTime(timezone=True), nullable=True)

    report = relationship("Report")

    __table_args__ = (
        Index("idx_payments_report_id", "report_id"),
        Index("idx_payments_access_token", "access_token"),
    )
