"""
Database models with cross-database compatibility.

Learning Point: Different databases have different capabilities.
- PostgreSQL: JSONB, UUID, Arrays
- SQLite: JSON, TEXT, Limited types
- MySQL: JSON, CHAR(36) for UUID

This version shows how to handle database differences in production systems.
"""

import json
import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON, TypeDecorator

# Create the base class for all models
Base = declarative_base()


class AnalysisStatus(str, Enum):
    """Analysis status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Custom types for cross-database compatibility
class UUID(TypeDecorator):
    """
    Cross-database UUID type.

    Interview Question: How do you handle database-specific types?
    Answer: Use TypeDecorator to abstract database differences.
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value
        else:
            return uuid.UUID(value)


class JSONType(TypeDecorator):
    """
    Cross-database JSON type.

    Uses JSONB for PostgreSQL (better performance) and JSON for others.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())


class ArrayType(TypeDecorator):
    """
    Cross-database array type.

    PostgreSQL has native arrays, other databases store as JSON.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value
        else:
            return json.loads(value)


class BaseModel(Base):
    """
    Abstract base model with common fields.

    Cross-database compatible version.
    """

    __abstract__ = True

    # UUID primary key for distributed systems
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)

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

    # Soft delete pattern
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class User(BaseModel):
    """User model with cross-database compatibility."""

    __tablename__ = "users"

    # User identification
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=True, index=True)

    # Authentication
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Authorization
    role = Column(String(20), default="user", nullable=False)

    # Rate limiting fields
    requests_count = Column(Integer, default=0, nullable=False)
    requests_reset_at = Column(DateTime(timezone=True), nullable=True)

    # User preferences stored as JSON (cross-database compatible)
    preferences = Column(JSONType, default=dict)

    # Relationships
    analyses: Mapped[list["ImageAnalysis"]] = relationship(
        "ImageAnalysis", back_populates="user"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="user")

    # Indexes for performance
    __table_args__ = (
        Index("idx_users_email_active", "email", "is_active"),
        Index("idx_users_role", "role"),
    )


class ApiKey(BaseModel):
    """API key management."""

    __tablename__ = "api_keys"

    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)

    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Scopes as JSON array (cross-database compatible)
    scopes = Column(ArrayType, default=list, nullable=False)

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    __table_args__ = (Index("idx_api_keys_user_active", "user_id", "is_active"),)


class ImageAnalysis(BaseModel):
    """Core model for image analysis."""

    __tablename__ = "image_analyses"

    # Request information
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)
    api_key_id = Column(UUID(), ForeignKey("api_keys.id"), nullable=True)

    # Image information
    image_url = Column(String(2048), nullable=True)
    image_hash = Column(String(64), nullable=True, index=True)
    image_size_bytes = Column(Integer, nullable=True)
    image_format = Column(String(10), nullable=True)
    image_dimensions = Column(JSONType, nullable=True)

    # Analysis configuration
    requested_features = Column(ArrayType, nullable=False)
    analysis_model = Column(String(50), default="azure-cv-4.0", nullable=False)

    # Processing information
    status = Column(String(20), default=AnalysisStatus.PENDING, nullable=False)
    processing_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Results stored as structured JSON
    analysis_results = Column(JSONType, nullable=True)
    confidence_scores = Column(JSONType, nullable=True)

    # Cost tracking
    cost_cents = Column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="analyses")
    api_key: Mapped[Optional["ApiKey"]] = relationship("ApiKey")

    __table_args__ = (
        Index("idx_analyses_user_status", "user_id", "status"),
        Index("idx_analyses_hash", "image_hash"),
        CheckConstraint("cost_cents >= 0", name="check_cost_non_negative"),
    )
