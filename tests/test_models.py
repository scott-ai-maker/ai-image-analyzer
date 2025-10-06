"""Unit tests for data models and schemas."""

import pytest
from datetime import datetime
from uuid import UUID
from pydantic import ValidationError

from src.models.schemas import (
    BoundingBox,
    DetectedObject,
    ImageMetadata,
    ImageFormat,
    AnalysisRequest,
    AnalysisResult,
    DetectionConfidence,
    HealthStatus,
    ApiUsageStats
)


class TestBoundingBox:
    """Test BoundingBox model."""
    
    def test_valid_bounding_box(self):
        """Test valid bounding box creation."""
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        assert bbox.x == 0.1
        assert bbox.y == 0.2
        assert bbox.width == 0.3
        assert bbox.height == 0.4
    
    def test_bounding_box_validation(self):
        """Test bounding box validation."""
        # Test valid edge case
        bbox = BoundingBox(x=0.0, y=0.0, width=1.0, height=1.0)
        assert bbox.x == 0.0
        
        # Test invalid - x + width > 1.0
        with pytest.raises(ValidationError):
            BoundingBox(x=0.8, y=0.1, width=0.3, height=0.2)
        
        # Test invalid - y + height > 1.0
        with pytest.raises(ValidationError):
            BoundingBox(x=0.1, y=0.8, width=0.2, height=0.3)
        
        # Test invalid negative values
        with pytest.raises(ValidationError):
            BoundingBox(x=-0.1, y=0.1, width=0.2, height=0.3)


class TestDetectedObject:
    """Test DetectedObject model."""
    
    def test_valid_detected_object(self):
        """Test valid detected object creation."""
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        obj = DetectedObject(
            object_id="test_1",
            name="person",
            confidence=0.85,
            bounding_box=bbox
        )
        
        assert obj.object_id == "test_1"
        assert obj.name == "person"
        assert obj.confidence == 0.85
        assert obj.bounding_box == bbox
        assert obj.parent is None
    
    def test_detected_object_with_parent(self):
        """Test detected object with parent."""
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        obj = DetectedObject(
            object_id="test_1",
            name="face",
            confidence=0.90,
            bounding_box=bbox,
            parent="person"
        )
        
        assert obj.parent == "person"


class TestImageMetadata:
    """Test ImageMetadata model."""
    
    def test_valid_image_metadata(self):
        """Test valid image metadata creation."""
        metadata = ImageMetadata(
            width=1920,
            height=1080,
            format=ImageFormat.JPEG,
            size_bytes=512000,
            color_space="RGB"
        )
        
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.format == ImageFormat.JPEG
        assert metadata.size_bytes == 512000
        assert metadata.color_space == "RGB"
    
    def test_invalid_dimensions(self):
        """Test invalid image dimensions."""
        with pytest.raises(ValidationError):
            ImageMetadata(
                width=0,  # Invalid
                height=1080,
                format=ImageFormat.JPEG,
                size_bytes=512000
            )


class TestAnalysisRequest:
    """Test AnalysisRequest model."""
    
    def test_valid_url_request(self):
        """Test valid URL analysis request."""
        request = AnalysisRequest(
            image_url="https://example.com/image.jpg",
            confidence_threshold=DetectionConfidence.HIGH,
            max_objects=25,
            include_metadata=False
        )
        
        assert str(request.image_url) == "https://example.com/image.jpg"
        assert request.confidence_threshold == DetectionConfidence.HIGH
        assert request.max_objects == 25
        assert request.include_metadata is False
    
    def test_request_defaults(self):
        """Test request with default values."""
        request = AnalysisRequest()
        
        assert request.image_url is None
        assert request.confidence_threshold == DetectionConfidence.MEDIUM
        assert request.max_objects == 50
        assert request.include_metadata is True
        assert request.callback_url is None
    
    def test_invalid_image_url(self):
        """Test invalid image URL validation."""
        with pytest.raises(ValidationError):
            AnalysisRequest(image_url="https://example.com/document.pdf")
    
    def test_max_objects_validation(self):
        """Test max_objects validation."""
        # Valid
        request = AnalysisRequest(max_objects=1)
        assert request.max_objects == 1
        
        request = AnalysisRequest(max_objects=100)
        assert request.max_objects == 100
        
        # Invalid - too low
        with pytest.raises(ValidationError):
            AnalysisRequest(max_objects=0)
        
        # Invalid - too high
        with pytest.raises(ValidationError):
            AnalysisRequest(max_objects=101)


class TestAnalysisResult:
    """Test AnalysisResult model."""
    
    def test_valid_analysis_result(self):
        """Test valid analysis result creation."""
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        obj = DetectedObject(
            object_id="test_1",
            name="person",
            confidence=0.85,
            bounding_box=bbox
        )
        
        result = AnalysisResult(
            detected_objects=[obj],
            processing_time_ms=150.5,
            confidence_threshold=0.7,
            total_objects_detected=1
        )
        
        assert len(result.detected_objects) == 1
        assert result.detected_objects[0] == obj
        assert result.processing_time_ms == 150.5
        assert result.confidence_threshold == 0.7
        assert result.total_objects_detected == 1
        assert isinstance(result.request_id, UUID)
        assert isinstance(result.timestamp, datetime)
    
    def test_empty_result(self):
        """Test empty analysis result."""
        result = AnalysisResult(
            detected_objects=[],
            processing_time_ms=50.0,
            confidence_threshold=0.5,
            total_objects_detected=0
        )
        
        assert len(result.detected_objects) == 0
        assert result.total_objects_detected == 0
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        result = AnalysisResult(
            detected_objects=[],
            processing_time_ms=50.0,
            confidence_threshold=0.5,
            total_objects_detected=0
        )
        
        json_data = result.dict()
        assert 'request_id' in json_data
        assert 'timestamp' in json_data
        assert isinstance(json_data['request_id'], str)


class TestHealthStatus:
    """Test HealthStatus model."""
    
    def test_valid_health_status(self):
        """Test valid health status creation."""
        status = HealthStatus(
            status="healthy",
            version="0.1.0",
            dependencies={"azure_cv": {"status": "healthy"}},
            uptime_seconds=3600.5
        )
        
        assert status.status == "healthy"
        assert status.version == "0.1.0"
        assert status.dependencies["azure_cv"]["status"] == "healthy"
        assert status.uptime_seconds == 3600.5
        assert isinstance(status.timestamp, datetime)


class TestApiUsageStats:
    """Test ApiUsageStats model."""
    
    def test_valid_usage_stats(self):
        """Test valid usage stats creation."""
        stats = ApiUsageStats(
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            average_processing_time_ms=125.5,
            requests_per_minute=16.7,
            last_request_timestamp=datetime.utcnow()
        )
        
        assert stats.total_requests == 1000
        assert stats.successful_requests == 950
        assert stats.failed_requests == 50
        assert stats.average_processing_time_ms == 125.5
        assert stats.requests_per_minute == 16.7
        assert isinstance(stats.last_request_timestamp, datetime)
    
    def test_no_last_request(self):
        """Test stats with no last request."""
        stats = ApiUsageStats(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            average_processing_time_ms=0.0,
            requests_per_minute=0.0
        )
        
        assert stats.last_request_timestamp is None