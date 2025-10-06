"""Core data models for the AI Image Analyzer."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, validator


class ImageFormat(str, Enum):
    """Supported image formats."""

    JPEG = "jpeg"
    PNG = "png"
    BMP = "bmp"
    GIF = "gif"
    WEBP = "webp"


class DetectionConfidence(str, Enum):
    """Confidence level thresholds."""

    LOW = "low"  # 0.3+
    MEDIUM = "medium"  # 0.5+
    HIGH = "high"  # 0.7+


class BoundingBox(BaseModel):
    """Bounding box coordinates for detected objects."""

    x: float = Field(..., ge=0, le=1, description="Left coordinate (normalized 0-1)")
    y: float = Field(..., ge=0, le=1, description="Top coordinate (normalized 0-1)")
    width: float = Field(..., ge=0, le=1, description="Width (normalized 0-1)")
    height: float = Field(..., ge=0, le=1, description="Height (normalized 0-1)")

    @validator("x", "width")
    def validate_x_bounds(cls, v, values):
        """Ensure x + width <= 1.0"""
        if "x" in values and v + values.get("x", 0) > 1.0:
            raise ValueError("x + width must not exceed 1.0")
        return v

    @validator("y", "height")
    def validate_y_bounds(cls, v, values):
        """Ensure y + height <= 1.0"""
        if "y" in values and v + values.get("y", 0) > 1.0:
            raise ValueError("y + height must not exceed 1.0")
        return v


class DetectedObject(BaseModel):
    """Individual object detection result."""

    object_id: str = Field(..., description="Unique identifier for this detection")
    name: str = Field(..., description="Object class name")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence (0-1)")
    bounding_box: BoundingBox = Field(..., description="Object location")
    parent: Optional[str] = Field(None, description="Parent object if hierarchical")


class ImageMetadata(BaseModel):
    """Image metadata and technical information."""

    width: int = Field(..., gt=0, description="Image width in pixels")
    height: int = Field(..., gt=0, description="Image height in pixels")
    format: ImageFormat = Field(..., description="Image format")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    color_space: Optional[str] = Field(
        None, description="Color space (RGB, RGBA, etc.)"
    )


class AnalysisRequest(BaseModel):
    """Request payload for image analysis."""

    image_url: Optional[HttpUrl] = Field(None, description="Public URL to image")
    confidence_threshold: DetectionConfidence = Field(
        DetectionConfidence.MEDIUM,
        description="Minimum confidence for returned detections",
    )
    max_objects: int = Field(
        50, ge=1, le=100, description="Maximum number of objects to return"
    )
    include_metadata: bool = Field(
        True, description="Include image metadata in response"
    )
    callback_url: Optional[HttpUrl] = Field(
        None, description="Webhook URL for async processing results"
    )

    @validator("image_url")
    def validate_image_url(cls, v):
        """Validate image URL if provided."""
        if v and not str(v).lower().endswith(
            (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")
        ):
            raise ValueError("URL must point to a supported image format")
        return v


class AnalysisResult(BaseModel):
    """Complete analysis result."""

    request_id: UUID = Field(
        default_factory=uuid4, description="Unique request identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis timestamp"
    )
    detected_objects: List[DetectedObject] = Field(
        default_factory=list, description="List of detected objects"
    )
    image_metadata: Optional[ImageMetadata] = Field(
        None, description="Image metadata if requested"
    )
    processing_time_ms: float = Field(
        ..., ge=0, description="Processing time in milliseconds"
    )
    confidence_threshold: float = Field(
        ..., ge=0, le=1, description="Applied confidence threshold"
    )
    total_objects_detected: int = Field(
        ..., ge=0, description="Total objects before filtering"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class AnalysisError(BaseModel):
    """Error response model."""

    request_id: UUID = Field(default_factory=uuid4, description="Request identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error context")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )
    version: str = Field(..., description="Service version")
    dependencies: dict = Field(default_factory=dict, description="Dependency status")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ApiUsageStats(BaseModel):
    """API usage statistics."""

    total_requests: int = Field(..., ge=0, description="Total requests processed")
    successful_requests: int = Field(..., ge=0, description="Successful requests")
    failed_requests: int = Field(..., ge=0, description="Failed requests")
    average_processing_time_ms: float = Field(
        ..., ge=0, description="Average processing time"
    )
    requests_per_minute: float = Field(
        ..., ge=0, description="Current requests per minute"
    )
    last_request_timestamp: Optional[datetime] = Field(
        None, description="Timestamp of last request"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
