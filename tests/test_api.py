"""Integration tests for API endpoints."""

import pytest
from unittest.mock import patch, Mock
import json
from io import BytesIO

from fastapi import status


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        with patch('src.services.computer_vision.ComputerVisionService') as mock_service:
            # Mock healthy service
            mock_instance = Mock()
            mock_instance.health_check.return_value = {"status": "healthy"}
            mock_instance.close.return_value = None
            mock_service.return_value = mock_instance
            
            response = client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] in ["healthy", "unhealthy"]
            assert "version" in data
            assert "uptime_seconds" in data
            assert "dependencies" in data
    
    def test_health_check_unhealthy_dependency(self, client):
        """Test health check with unhealthy dependency."""
        with patch('src.services.computer_vision.ComputerVisionService') as mock_service:
            # Mock unhealthy service
            mock_instance = Mock()
            mock_instance.health_check.return_value = {
                "status": "unhealthy",
                "error": "Connection failed"
            }
            mock_instance.close.return_value = None
            mock_service.return_value = mock_instance
            
            response = client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "unhealthy"


class TestMetricsEndpoint:
    """Test metrics endpoint."""
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_requests" in data
        assert "successful_requests" in data
        assert "failed_requests" in data
        assert "average_processing_time_ms" in data
        assert "requests_per_minute" in data


class TestAnalyzeUrlEndpoint:
    """Test URL analysis endpoint."""
    
    @patch('src.services.computer_vision.ComputerVisionService')
    def test_analyze_url_success(self, mock_service, client, auth_headers):
        """Test successful URL analysis."""
        # Mock service response
        mock_instance = Mock()
        mock_instance.analyze_image_from_url.return_value = (
            [],  # detected_objects
            None,  # image_metadata
            150.5  # processing_time
        )
        mock_service.return_value = mock_instance
        
        request_data = {
            "image_url": "https://example.com/test.jpg",
            "confidence_threshold": "medium",
            "max_objects": 10,
            "include_metadata": True
        }
        
        response = client.post(
            "/api/v1/analyze/url",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "request_id" in data
        assert "timestamp" in data
        assert "detected_objects" in data
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] == 150.5
    
    def test_analyze_url_missing_url(self, client, auth_headers):
        """Test URL analysis without image URL."""
        request_data = {
            "confidence_threshold": "medium",
            "max_objects": 10
        }
        
        response = client.post(
            "/api/v1/analyze/url",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "image_url is required" in response.json()["detail"]
    
    def test_analyze_url_unauthorized(self, client):
        """Test URL analysis without authentication."""
        request_data = {
            "image_url": "https://example.com/test.jpg"
        }
        
        response = client.post(
            "/api/v1/analyze/url",
            json=request_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_analyze_url_invalid_key(self, client):
        """Test URL analysis with invalid API key."""
        request_data = {
            "image_url": "https://example.com/test.jpg"
        }
        
        headers = {"Authorization": "Bearer invalid-key"}
        response = client.post(
            "/api/v1/analyze/url",
            json=request_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch('src.services.computer_vision.ComputerVisionService')
    def test_analyze_url_service_error(self, mock_service, client, auth_headers):
        """Test URL analysis with service error."""
        from src.services.computer_vision import ComputerVisionServiceError
        
        # Mock service error
        mock_instance = Mock()
        mock_instance.analyze_image_from_url.side_effect = ComputerVisionServiceError(
            "Image not found", "INACCESSIBLE_URL"
        )
        mock_service.return_value = mock_instance
        
        request_data = {
            "image_url": "https://example.com/nonexistent.jpg"
        }
        
        response = client.post(
            "/api/v1/analyze/url",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()["detail"]
        assert data["error_code"] == "INACCESSIBLE_URL"


class TestAnalyzeUploadEndpoint:
    """Test upload analysis endpoint."""
    
    @patch('src.services.computer_vision.ComputerVisionService')
    def test_analyze_upload_success(self, mock_service, client, auth_headers):
        """Test successful upload analysis."""
        # Mock service response
        mock_instance = Mock()
        mock_instance.analyze_image_from_stream.return_value = (
            [],  # detected_objects
            None,  # image_metadata
            200.3  # processing_time
        )
        mock_service.return_value = mock_instance
        
        # Create fake image file
        image_data = b"fake_jpeg_data"
        
        response = client.post(
            "/api/v1/analyze/upload",
            files={"image": ("test.jpg", BytesIO(image_data), "image/jpeg")},
            data={
                "confidence_threshold": "high",
                "max_objects": 20,
                "include_metadata": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "request_id" in data
        assert "detected_objects" in data
        assert data["processing_time_ms"] == 200.3
    
    def test_analyze_upload_no_file(self, client, auth_headers):
        """Test upload analysis without file."""
        response = client.post(
            "/api/v1/analyze/upload",
            data={"confidence_threshold": "medium"},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_analyze_upload_invalid_content_type(self, client, auth_headers):
        """Test upload analysis with invalid content type."""
        file_data = b"not_an_image"
        
        response = client.post(
            "/api/v1/analyze/upload",
            files={"image": ("test.txt", BytesIO(file_data), "text/plain")},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        assert "Unsupported content type" in response.json()["detail"]
    
    @patch('src.services.computer_vision.ComputerVisionService')
    def test_analyze_upload_service_error(self, mock_service, client, auth_headers):
        """Test upload analysis with service error."""
        from src.services.computer_vision import ComputerVisionServiceError
        
        # Mock service error
        mock_instance = Mock()
        mock_instance.analyze_image_from_stream.side_effect = ComputerVisionServiceError(
            "Invalid image data", "INVALID_IMAGE_DATA"
        )
        mock_service.return_value = mock_instance
        
        image_data = b"invalid_image_data"
        
        response = client.post(
            "/api/v1/analyze/upload",
            files={"image": ("test.jpg", BytesIO(image_data), "image/jpeg")},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()["detail"]
        assert data["error_code"] == "INVALID_IMAGE_DATA"


class TestGetAnalysisResultEndpoint:
    """Test get analysis result endpoint."""
    
    def test_get_analysis_result_not_implemented(self, client, auth_headers):
        """Test get analysis result endpoint (not implemented)."""
        import uuid
        
        response = client.get(
            f"/api/v1/analysis/{uuid.uuid4()}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
        data = response.json()["detail"]
        assert data["error_code"] == "NOT_IMPLEMENTED"