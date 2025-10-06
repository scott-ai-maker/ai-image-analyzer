"""Azure Computer Vision service integration."""

import asyncio
import logging
from typing import List, Optional, Tuple
from io import BytesIO
import time

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import (
    DetectedObject as AzureDetectedObject
)
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from msrest.authentication import CognitiveServicesCredentials
from PIL import Image
import httpx

from ..models.schemas import (
    DetectedObject, 
    BoundingBox, 
    ImageMetadata, 
    ImageFormat,
    AnalysisError
)
from ..core.config import Settings


logger = logging.getLogger(__name__)


class ComputerVisionService:
    """Enterprise-grade Azure Computer Vision service wrapper."""

    def __init__(self, settings: Settings):
        """Initialize the Computer Vision service.
        
        Args:
            settings: Application settings containing Azure configuration
        """
        self.settings = settings
        self.client: Optional[ComputerVisionClient] = None
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.api.request_timeout_seconds)
        )
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Azure Computer Vision client with proper authentication."""
        try:
            endpoint = self.settings.azure.computer_vision_endpoint
            
            # Use managed identity if no key is provided
            if self.settings.azure.computer_vision_key:
                credentials = CognitiveServicesCredentials(
                    self.settings.azure.computer_vision_key
                )
                logger.info("Using subscription key authentication")
            else:
                # Use managed identity or Azure CLI credentials
                credential = DefaultAzureCredential()
                credentials = credential
                logger.info("Using managed identity authentication")
            
            self.client = ComputerVisionClient(endpoint, credentials)
            logger.info(f"Computer Vision client initialized for endpoint: {endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Computer Vision client: {e}")
            raise

    async def analyze_image_from_url(
        self, 
        image_url: str, 
        confidence_threshold: float = 0.5,
        max_objects: int = 50
    ) -> Tuple[List[DetectedObject], Optional[ImageMetadata], float]:
        """Analyze image from URL for object detection.
        
        Args:
            image_url: Public URL to the image
            confidence_threshold: Minimum confidence for detections
            max_objects: Maximum number of objects to return
            
        Returns:
            Tuple of (detected_objects, image_metadata, processing_time_ms)
            
        Raises:
            ComputerVisionServiceError: On service errors
        """
        start_time = time.time()
        
        try:
            # Validate image URL accessibility
            await self._validate_image_url(image_url)
            
            # Perform object detection
            logger.info(f"Analyzing image from URL: {image_url}")
            
            # Run synchronous Azure SDK call in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.detect_objects(image_url)
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Convert Azure results to our models
            detected_objects = self._convert_azure_objects(
                result.objects, 
                confidence_threshold, 
                max_objects
            )
            
            # Get image metadata
            image_metadata = await self._get_image_metadata(image_url)
            
            logger.info(
                f"Analysis completed: {len(detected_objects)} objects detected "
                f"in {processing_time:.2f}ms"
            )
            
            return detected_objects, image_metadata, processing_time
            
        except ComputerVisionErrorException as e:
            error_msg = f"Azure Computer Vision error: {e.message}"
            logger.error(error_msg)
            raise ComputerVisionServiceError(error_msg, "AZURE_CV_ERROR") from e
            
        except Exception as e:
            error_msg = f"Unexpected error during image analysis: {str(e)}"
            logger.error(error_msg)
            raise ComputerVisionServiceError(error_msg, "ANALYSIS_ERROR") from e

    async def analyze_image_from_stream(
        self, 
        image_data: bytes, 
        confidence_threshold: float = 0.5,
        max_objects: int = 50
    ) -> Tuple[List[DetectedObject], Optional[ImageMetadata], float]:
        """Analyze image from binary data for object detection.
        
        Args:
            image_data: Binary image data
            confidence_threshold: Minimum confidence for detections
            max_objects: Maximum number of objects to return
            
        Returns:
            Tuple of (detected_objects, image_metadata, processing_time_ms)
            
        Raises:
            ComputerVisionServiceError: On service errors
        """
        start_time = time.time()
        
        try:
            # Validate image data
            self._validate_image_data(image_data)
            
            logger.info("Analyzing uploaded image data")
            
            # Create BytesIO stream for Azure SDK
            image_stream = BytesIO(image_data)
            
            # Run synchronous Azure SDK call in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.detect_objects_in_stream(image_stream)
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Convert Azure results to our models
            detected_objects = self._convert_azure_objects(
                result.objects, 
                confidence_threshold, 
                max_objects
            )
            
            # Get image metadata from binary data
            image_metadata = self._get_image_metadata_from_bytes(image_data)
            
            logger.info(
                f"Analysis completed: {len(detected_objects)} objects detected "
                f"in {processing_time:.2f}ms"
            )
            
            return detected_objects, image_metadata, processing_time
            
        except ComputerVisionErrorException as e:
            error_msg = f"Azure Computer Vision error: {e.message}"
            logger.error(error_msg)
            raise ComputerVisionServiceError(error_msg, "AZURE_CV_ERROR") from e
            
        except Exception as e:
            error_msg = f"Unexpected error during image analysis: {str(e)}"
            logger.error(error_msg)
            raise ComputerVisionServiceError(error_msg, "ANALYSIS_ERROR") from e

    async def _validate_image_url(self, image_url: str) -> None:
        """Validate that image URL is accessible.
        
        Args:
            image_url: URL to validate
            
        Raises:
            ComputerVisionServiceError: If URL is not accessible
        """
        try:
            response = await self.http_client.head(image_url)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                raise ComputerVisionServiceError(
                    f"URL does not point to an image: {content_type}",
                    "INVALID_IMAGE_URL"
                )
                
        except httpx.HTTPError as e:
            raise ComputerVisionServiceError(
                f"Cannot access image URL: {str(e)}",
                "INACCESSIBLE_URL"
            ) from e

    def _validate_image_data(self, image_data: bytes) -> None:
        """Validate binary image data.
        
        Args:
            image_data: Binary data to validate
            
        Raises:
            ComputerVisionServiceError: If data is invalid
        """
        if not image_data:
            raise ComputerVisionServiceError(
                "Image data is empty", 
                "EMPTY_IMAGE_DATA"
            )
        
        # Check size limit
        max_size = self.settings.api.max_image_size_mb * 1024 * 1024
        if len(image_data) > max_size:
            raise ComputerVisionServiceError(
                f"Image size ({len(image_data)} bytes) exceeds limit ({max_size} bytes)",
                "IMAGE_TOO_LARGE"
            )
        
        # Validate it's actually an image
        try:
            with Image.open(BytesIO(image_data)) as img:
                img.verify()
        except Exception as e:
            raise ComputerVisionServiceError(
                f"Invalid image data: {str(e)}",
                "INVALID_IMAGE_DATA"
            ) from e

    def _convert_azure_objects(
        self, 
        azure_objects: List[AzureDetectedObject], 
        confidence_threshold: float,
        max_objects: int
    ) -> List[DetectedObject]:
        """Convert Azure detection results to our models.
        
        Args:
            azure_objects: Azure Computer Vision detection results
            confidence_threshold: Minimum confidence to include
            max_objects: Maximum objects to return
            
        Returns:
            List of DetectedObject instances
        """
        detected_objects = []
        
        for i, obj in enumerate(azure_objects):
            if obj.confidence < confidence_threshold:
                continue
                
            if len(detected_objects) >= max_objects:
                break
            
            # Convert bounding box (Azure uses pixel coordinates)
            bbox = BoundingBox(
                x=obj.rectangle.x / 1.0,  # Will be normalized by image dimensions
                y=obj.rectangle.y / 1.0,
                width=obj.rectangle.w / 1.0,
                height=obj.rectangle.h / 1.0
            )
            
            detected_obj = DetectedObject(
                object_id=f"obj_{i}_{int(time.time() * 1000)}",
                name=obj.object_property,
                confidence=obj.confidence,
                bounding_box=bbox,
                parent=obj.parent.object_property if obj.parent else None
            )
            
            detected_objects.append(detected_obj)
        
        return detected_objects

    async def _get_image_metadata(self, image_url: str) -> Optional[ImageMetadata]:
        """Get image metadata from URL.
        
        Args:
            image_url: Image URL
            
        Returns:
            ImageMetadata instance or None if unavailable
        """
        try:
            response = await self.http_client.get(image_url)
            response.raise_for_status()
            return self._get_image_metadata_from_bytes(response.content)
        except Exception as e:
            logger.warning(f"Could not get image metadata: {e}")
            return None

    def _get_image_metadata_from_bytes(self, image_data: bytes) -> Optional[ImageMetadata]:
        """Extract image metadata from binary data.
        
        Args:
            image_data: Binary image data
            
        Returns:
            ImageMetadata instance or None if unavailable
        """
        try:
            with Image.open(BytesIO(image_data)) as img:
                format_map = {
                    'JPEG': ImageFormat.JPEG,
                    'PNG': ImageFormat.PNG,
                    'BMP': ImageFormat.BMP,
                                        'GIF': ImageFormat.GIF,
                    'WEBP': ImageFormat.WEBP,
                }
                
                return ImageMetadata(
                    width=img.width,
                    height=img.height,
                    format=format_map.get(img.format, ImageFormat.JPEG),
                    size_bytes=len(image_data),
                    color_space=img.mode
                )
        except Exception as e:
            logger.warning(f"Could not extract image metadata: {e}")
            return None

    async def health_check(self) -> dict:
        """Check service health and connectivity.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Simple connectivity test - list available models
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.list_models()
            )
            
            return {
                "status": "healthy",
                "endpoint": self.settings.azure.computer_vision_endpoint,
                "authentication": "key" if self.settings.azure.computer_vision_key else "managed_identity"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "endpoint": self.settings.azure.computer_vision_endpoint
            }

    async def close(self) -> None:
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()


class ComputerVisionServiceError(Exception):
    """Custom exception for Computer Vision service errors."""
    
    def __init__(self, message: str, error_code: str, details: Optional[dict] = None):
        """Initialize error.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}