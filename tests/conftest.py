"""Test configuration and fixtures."""

import asyncio
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import Mock

from fastapi.testclient import TestClient
import httpx

from src.api.main import create_app
from src.core.config import Settings
from src.services.computer_vision import ComputerVisionService


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        environment="testing",
        debug=True,
        azure_computer_vision_endpoint="https://test.cognitiveservices.azure.com/",
        azure_computer_vision_key="test-key-123",
        host="127.0.0.1",
        port=8000,
        api_keys=["test-key-123"],
        max_image_size_mb=5,
        log_level="DEBUG",
        secret_key="test-secret-key-for-testing-only"
    )


@pytest.fixture
def app(mock_settings):
    """Create FastAPI test app."""
    # Monkey patch settings
    import src.core.config
    src.core.config.settings = mock_settings
    
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict:
    """Create authentication headers for testing."""
    return {"Authorization": "Bearer test-key-123"}


@pytest.fixture
def mock_cv_client():
    """Create mock Computer Vision client."""
    mock_client = Mock()
    
    # Mock successful object detection response
    mock_result = Mock()
    mock_result.objects = [
        Mock(
            object_property="person",
            confidence=0.85,
            rectangle=Mock(x=100, y=50, w=200, h=300),
            parent=None
        ),
        Mock(
            object_property="car",
            confidence=0.75,
            rectangle=Mock(x=300, y=200, w=150, h=100),
            parent=None
        )
    ]
    
    mock_client.detect_objects.return_value = mock_result
    mock_client.detect_objects_in_stream.return_value = mock_result
    mock_client.list_models.return_value = []
    
    return mock_client


@pytest.fixture
def mock_cv_service(mock_settings, mock_cv_client):
    """Create mock Computer Vision service."""
    service = ComputerVisionService(mock_settings)
    service.client = mock_cv_client
    return service


@pytest.fixture
async def async_client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async test client."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Sample test data
SAMPLE_IMAGE_URL = "https://example.com/test-image.jpg"

SAMPLE_JPEG_BYTES = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\x00\xff\xd9'