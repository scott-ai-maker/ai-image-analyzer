"""
Database models for the AI Image Analyzer.

This module demonstrates enterprise-grade database design patterns:
- Async SQLAlchemy models with proper relationships
- UUID primary keys for distributed systems
- Proper indexing strategy for performance
- Audit fields for compliance and debugging
- Soft delete pattern for data retention
"""

import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

# Create the base class for all models
Base = declarative_base()


class AnalysisStatus(str, Enum):
    """Analysis status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseModel(Base):
    """
    Abstract base model with common fields.

    Interview Tip: This pattern is used by companies like Stripe and GitHub
    to ensure consistency across all database tables.
    """

    __abstract__ = True

    # UUID primary key for distributed systems
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Audit fields - critical for production systems
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Soft delete pattern - never actually delete data in production
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class User(BaseModel):
    """
    User model with proper authentication and authorization fields.

    Interview Discussion: How would you handle user authentication
    in a distributed system? UUID vs incremental IDs?
    """

    __tablename__ = "users"

    # User identification
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=True, index=True)

    # Authentication
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Authorization
    role = Column(String(20), default="user", nullable=False)  # user, premium, admin

    # Rate limiting fields
    requests_count = Column(Integer, default=0, nullable=False)
    requests_reset_at = Column(DateTime(timezone=True), nullable=True)

    # User preferences stored as JSON
    preferences = Column(JSONB, default=dict)

    # Relationships
    analyses: Mapped[list["ImageAnalysis"]] = relationship(
        "ImageAnalysis", back_populates="user"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="user")

    # Indexes for performance
    __table_args__ = (
        Index("idx_users_email_active", "email", "is_active"),
        Index("idx_users_role", "role"),
        Index("idx_users_requests_reset", "requests_reset_at"),
    )


class ApiKey(BaseModel):
    """
    API key management for programmatic access.

    Interview Question: How would you implement API key rotation
    and scope-based permissions?
    """

    __tablename__ = "api_keys"

    # API key identification
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)  # Human-readable name

    # Key properties
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Scopes and permissions (stored as array)
    scopes = Column(ARRAY(String), default=list, nullable=False)

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_user_active", "user_id", "is_active"),
        Index("idx_api_keys_expires", "expires_at"),
    )


class ImageAnalysis(BaseModel):
    """
    Core model for image analysis requests and results.

    Design Decision: Should we store the image data or just metadata?
    In production, images are typically stored in object storage (S3, Azure Blob)
    while metadata goes in the database.
    """

    __tablename__ = "image_analyses"

    # Request information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    # Image information
    image_url = Column(String(2048), nullable=True)  # URL if image is stored externally
    image_hash = Column(
        String(64), nullable=True, index=True
    )  # SHA-256 for deduplication
    image_size_bytes = Column(Integer, nullable=True)
    image_format = Column(String(10), nullable=True)  # JPEG, PNG, etc.
    image_dimensions = Column(JSONB, nullable=True)  # {"width": 1920, "height": 1080}

    # Analysis configuration
    requested_features = Column(
        ARRAY(String), nullable=False
    )  # ["description", "objects", "text"]
    analysis_model = Column(String(50), default="azure-cv-4.0", nullable=False)

    # Processing information
    status = Column(String(20), default=AnalysisStatus.PENDING, nullable=False)
    processing_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Results stored as structured JSON
    analysis_results = Column(JSONB, nullable=True)
    confidence_scores = Column(JSONB, nullable=True)

    # Cost tracking (important for business metrics)
    cost_cents = Column(
        Integer, default=0, nullable=False
    )  # Store in cents to avoid float precision issues

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="analyses")
    api_key: Mapped[Optional["ApiKey"]] = relationship("ApiKey")

    # Advanced indexes for complex queries
    __table_args__ = (
        Index("idx_analyses_user_status", "user_id", "status"),
        Index("idx_analyses_created_status", "created_at", "status"),
        Index("idx_analyses_hash", "image_hash"),  # For deduplication
        Index("idx_analyses_model_status", "analysis_model", "status"),
        CheckConstraint("cost_cents >= 0", name="check_cost_non_negative"),
        CheckConstraint(
            "processing_time_ms >= 0", name="check_processing_time_non_negative"
        ),
    )


class AnalysisCache(BaseModel):
    """
    Cache table for expensive analysis results.

    Pattern: Database-level caching for complex computations.
    Alternative: Redis cache (we'll implement both approaches)
    """

    __tablename__ = "analysis_cache"

    # Cache key components
    image_hash = Column(String(64), nullable=False, index=True)
    features_hash = Column(String(64), nullable=False)  # Hash of requested features
    model_version = Column(String(50), nullable=False)

    # Cached data
    analysis_results = Column(JSONB, nullable=False)
    confidence_scores = Column(JSONB, nullable=True)

    # Cache metadata
    hit_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now())

    # TTL for cache expiration
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "image_hash", "features_hash", "model_version", name="uq_cache_key"
        ),
        Index("idx_cache_expires", "expires_at"),
        Index("idx_cache_last_accessed", "last_accessed_at"),
    )


class SystemMetrics(BaseModel):
    """
    System performance and usage metrics.

    Production Pattern: Store time-series data for monitoring and analytics.
    In large systems, this might be moved to InfluxDB or TimescaleDB.
    """

    __tablename__ = "system_metrics"

    # Metric identification
    metric_name = Column(String(100), nullable=False, index=True)
    metric_type = Column(String(20), nullable=False)  # counter, gauge, histogram

    # Metric data
    value = Column(Float, nullable=False)
    labels = Column(JSONB, default=dict)  # Additional metric dimensions

    # Time-series data
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_metrics_name_timestamp", "metric_name", "timestamp"),
        Index("idx_metrics_timestamp", "timestamp"),
    )
