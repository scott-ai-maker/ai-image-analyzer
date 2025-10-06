"""Unit tests for Computer Vision service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from io import BytesIO

from src.services.computer_vision import ComputerVisionService, ComputerVisionServiceError
from src.models.schemas import DetectedObject, BoundingBox, ImageMetadata, ImageFormat


class TestComputerVisionService:
    """Test Computer Vision service."""
    
    def test_service_initialization(self, mock_settings):
        """Test service initialization."""
        with patch('src.services.computer_vision.ComputerVisionClient'):
            service = ComputerVisionService(mock_settings)
            assert service.settings == mock_settings
            assert service.client is not None
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_url_success(self, mock_cv_service):
        """Test successful URL image analysis."""
        # Mock HTTP client response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.content = b'fake_image_data'
        
        with patch.object(mock_cv_service.http_client, 'head', return_value=mock_response), \
             patch.object(mock_cv_service.http_client, 'get', return_value=mock_response):
            
            objects, metadata, processing_time = await mock_cv_service.analyze_image_from_url(
                "https://example.com/test.jpg",
                confidence_threshold=0.5,
                max_objects=10
            )
            
            assert isinstance(objects, list)
            assert len(objects) <= 10
            assert processing_time > 0
            
            # Verify client was called
            mock_cv_service.client.detect_objects.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_url_inaccessible(self, mock_cv_service):
        """Test URL analysis with inaccessible URL."""
        import httpx
        
        with patch.object(mock_cv_service.http_client, 'head', side_effect=httpx.HTTPError("Not found")):
            
            with pytest.raises(ComputerVisionServiceError) as exc_info:
                await mock_cv_service.analyze_image_from_url(
                    "https://example.com/nonexistent.jpg"
                )
            
            assert exc_info.value.error_code == "INACCESSIBLE_URL"
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_url_invalid_content_type(self, mock_cv_service):
        """Test URL analysis with invalid content type."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch.object(mock_cv_service.http_client, 'head', return_value=mock_response):
            
            with pytest.raises(ComputerVisionServiceError) as exc_info:
                await mock_cv_service.analyze_image_from_url(
                    "https://example.com/not-an-image.html"
                )
            
            assert exc_info.value.error_code == "INVALID_IMAGE_URL"
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_stream_success(self, mock_cv_service):
        """Test successful stream image analysis."""
        image_data = b'fake_jpeg_data'
        
        # Mock PIL Image
        with patch('src.services.computer_vision.Image') as mock_image:
            mock_img = Mock()
            mock_img.verify = Mock()
            mock_img.width = 800
            mock_img.height = 600
            mock_img.format = 'JPEG'
            mock_img.mode = 'RGB'
            mock_image.open.return_value.__enter__.return_value = mock_img
            
            objects, metadata, processing_time = await mock_cv_service.analyze_image_from_stream(
                image_data,
                confidence_threshold=0.7,
                max_objects=5
            )
            
            assert isinstance(objects, list)
            assert len(objects) <= 5
            assert processing_time > 0
            assert metadata is not None
            assert metadata.width == 800
            assert metadata.height == 600
            
            # Verify client was called
            mock_cv_service.client.detect_objects_in_stream.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_stream_empty_data(self, mock_cv_service):
        """Test stream analysis with empty data."""
        with pytest.raises(ComputerVisionServiceError) as exc_info:
            await mock_cv_service.analyze_image_from_stream(b'')
        
        assert exc_info.value.error_code == "EMPTY_IMAGE_DATA"
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_stream_too_large(self, mock_cv_service):
        """Test stream analysis with oversized image."""
        # Create data larger than limit (5MB in mock settings)
        large_data = b'x' * (6 * 1024 * 1024)
        
        with pytest.raises(ComputerVisionServiceError) as exc_info:
            await mock_cv_service.analyze_image_from_stream(large_data)
        
        assert exc_info.value.error_code == "IMAGE_TOO_LARGE"
    
    @pytest.mark.asyncio
    async def test_analyze_image_from_stream_invalid_image(self, mock_cv_service):
        """Test stream analysis with invalid image data."""
        invalid_data = b'not_an_image'
        
        with patch('src.services.computer_vision.Image') as mock_image:
            mock_image.open.side_effect = Exception("Invalid image")
            
            with pytest.raises(ComputerVisionServiceError) as exc_info:
                await mock_cv_service.analyze_image_from_stream(invalid_data)
            
            assert exc_info.value.error_code == "INVALID_IMAGE_DATA"
    
    def test_convert_azure_objects(self, mock_cv_service):
        """Test conversion of Azure detection objects."""
        # Mock Azure objects
        mock_azure_obj1 = Mock()
        mock_azure_obj1.object_property = "person"
        mock_azure_obj1.confidence = 0.85
        mock_azure_obj1.rectangle = Mock(x=100, y=50, w=200, h=300)
        mock_azure_obj1.parent = None
        
        mock_azure_obj2 = Mock()
        mock_azure_obj2.object_property = "face"
        mock_azure_obj2.confidence = 0.60  # Below threshold
        mock_azure_obj2.rectangle = Mock(x=150, y=75, w=50, h=75)
        mock_azure_obj2.parent = mock_azure_obj1
        
        mock_azure_obj3 = Mock()
        mock_azure_obj3.object_property = "car"
        mock_azure_obj3.confidence = 0.75
        mock_azure_obj3.rectangle = Mock(x=300, y=200, w=150, h=100)
        mock_azure_obj3.parent = None
        
        azure_objects = [mock_azure_obj1, mock_azure_obj2, mock_azure_obj3]
        
        # Convert objects
        detected_objects = mock_cv_service._convert_azure_objects(
            azure_objects,
            confidence_threshold=0.7,
            max_objects=10
        )
        
        # Should only include objects above threshold
        assert len(detected_objects) == 2
        
        # Check first object
        obj1 = detected_objects[0]
        assert obj1.name == "person"
        assert obj1.confidence == 0.85
        assert obj1.parent is None
        
        # Check second object
        obj2 = detected_objects[1]
        assert obj2.name == "car"
        assert obj2.confidence == 0.75
        assert obj2.parent is None
    
    def test_convert_azure_objects_max_limit(self, mock_cv_service):
        """Test max objects limit in conversion."""
        # Create more objects than limit
        azure_objects = []
        for i in range(10):
            mock_obj = Mock()
            mock_obj.object_property = f"object_{i}"
            mock_obj.confidence = 0.8
            mock_obj.rectangle = Mock(x=i*10, y=i*10, w=50, h=50)
            mock_obj.parent = None
            azure_objects.append(mock_obj)
        
        # Convert with low limit
        detected_objects = mock_cv_service._convert_azure_objects(
            azure_objects,
            confidence_threshold=0.5,
            max_objects=3
        )
        
        # Should respect max limit
        assert len(detected_objects) == 3
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_cv_service):
        """Test healthy service health check."""
        health = await mock_cv_service.health_check()
        
        assert health["status"] == "healthy"
        assert "endpoint" in health
        assert "authentication" in health
        
        # Verify client was called
        mock_cv_service.client.list_models.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_cv_service):
        """Test unhealthy service health check."""
        # Mock client error
        mock_cv_service.client.list_models.side_effect = Exception("Connection failed")
        
        health = await mock_cv_service.health_check()
        
        assert health["status"] == "unhealthy"
        assert "error" in health
        assert health["error"] == "Connection failed"
    
    @pytest.mark.asyncio
    async def test_close(self, mock_cv_service):
        """Test service cleanup."""
        mock_cv_service.http_client = Mock()
        mock_cv_service.http_client.aclose = AsyncMock()
        
        await mock_cv_service.close()
        
        mock_cv_service.http_client.aclose.assert_called_once()


class TestComputerVisionServiceError:
    """Test ComputerVisionServiceError exception."""
    
    def test_error_creation(self):
        """Test error creation with all parameters."""
        error = ComputerVisionServiceError(
            message="Test error",
            error_code="TEST_ERROR",
            details={"key": "value"}
        )
        
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.details == {"key": "value"}
        assert error.correlation_id is not None
    
    def test_error_creation_minimal(self):
        """Test error creation with minimal parameters."""
        error = ComputerVisionServiceError(
            message="Simple error",
            error_code="SIMPLE_ERROR"
        )
        
        assert str(error) == "Simple error"
        assert error.message == "Simple error"
        assert error.error_code == "SIMPLE_ERROR"
        assert error.details == {}
        assert error.correlation_id is not None