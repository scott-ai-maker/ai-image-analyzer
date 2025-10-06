"""FastAPI routes for image analysis endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.schemas import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisError,
    DetectionConfidence,
)
from ..services.computer_vision import ComputerVisionService, ComputerVisionServiceError
from ..core.config import Settings, settings

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)

# Router
router = APIRouter(prefix="/api/v1", tags=["image-analysis"])


def get_computer_vision_service() -> ComputerVisionService:
    """Dependency to get Computer Vision service instance."""
    return ComputerVisionService(settings)


def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_settings: Settings = Depends(lambda: settings),
) -> bool:
    """Verify API key if configured.

    Args:
        credentials: HTTP authorization credentials
        api_settings: API configuration

    Returns:
        True if authorized

    Raises:
        HTTPException: If unauthorized
    """
    # Skip auth if no API keys configured (development mode)
    if not api_settings.api.api_keys:
        return True

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials not in api_settings.api.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


@router.post(
    "/analyze/url",
    response_model=AnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze image from URL",
    description="Perform object detection on an image accessible via public URL",
    responses={
        200: {"description": "Analysis completed successfully"},
        400: {"description": "Invalid request parameters", "model": AnalysisError},
        401: {"description": "Authentication required"},
        404: {"description": "Image not found or inaccessible", "model": AnalysisError},
        429: {"description": "Rate limit exceeded", "model": AnalysisError},
        500: {"description": "Internal server error", "model": AnalysisError},
    },
)
async def analyze_image_url(
    request: AnalysisRequest,
    cv_service: ComputerVisionService = Depends(get_computer_vision_service),
    authorized: bool = Depends(verify_api_key),
) -> AnalysisResult:
    """Analyze an image from a public URL for object detection.

    This endpoint accepts a public image URL and returns detected objects
    with their bounding boxes and confidence scores.

    Args:
        request: Analysis request containing image URL and parameters
        cv_service: Computer Vision service dependency
        authorized: Authorization dependency

    Returns:
        AnalysisResult with detected objects and metadata

    Raises:
        HTTPException: On various error conditions
    """
    if not request.image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_url is required for URL analysis",
        )

    try:
        logger.info(
            f"Starting URL analysis: {request.image_url} "
            f"(confidence: {request.confidence_threshold}, max_objects: {request.max_objects})"
        )

        # Convert confidence enum to float
        confidence_map = {
            DetectionConfidence.LOW: 0.3,
            DetectionConfidence.MEDIUM: 0.5,
            DetectionConfidence.HIGH: 0.7,
        }
        confidence_threshold = confidence_map[request.confidence_threshold]

        # Perform analysis
        (
            detected_objects,
            image_metadata,
            processing_time,
        ) = await cv_service.analyze_image_from_url(
            str(request.image_url), confidence_threshold, request.max_objects
        )

        # Build result
        result = AnalysisResult(
            detected_objects=detected_objects,
            image_metadata=image_metadata if request.include_metadata else None,
            processing_time_ms=processing_time,
            confidence_threshold=confidence_threshold,
            total_objects_detected=len(detected_objects),
        )

        logger.info(
            f"URL analysis completed: {len(detected_objects)} objects detected "
            f"in {processing_time:.2f}ms"
        )

        return result

    except ComputerVisionServiceError as e:
        logger.error(f"Computer Vision service error: {e}")

        # Map service errors to HTTP status codes
        status_map = {
            "INACCESSIBLE_URL": status.HTTP_404_NOT_FOUND,
            "INVALID_IMAGE_URL": status.HTTP_400_BAD_REQUEST,
            "IMAGE_TOO_LARGE": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "AZURE_CV_ERROR": status.HTTP_502_BAD_GATEWAY,
        }

        http_status = status_map.get(
            e.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        raise HTTPException(
            status_code=http_status,
            detail={
                "error_code": e.error_code,
                "error_message": e.message,
                "details": e.details,
            },
        )

    except Exception as e:
        logger.error(f"Unexpected error in URL analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "An unexpected error occurred",
                "details": {"exception": str(e)},
            },
        )


@router.post(
    "/analyze/upload",
    response_model=AnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze uploaded image",
    description="Perform object detection on an uploaded image file",
    responses={
        200: {"description": "Analysis completed successfully"},
        400: {"description": "Invalid request parameters", "model": AnalysisError},
        401: {"description": "Authentication required"},
        413: {"description": "Image file too large", "model": AnalysisError},
        415: {"description": "Unsupported media type", "model": AnalysisError},
        429: {"description": "Rate limit exceeded", "model": AnalysisError},
        500: {"description": "Internal server error", "model": AnalysisError},
    },
)
async def analyze_uploaded_image(
    image: UploadFile = File(..., description="Image file to analyze"),
    confidence_threshold: DetectionConfidence = Form(
        DetectionConfidence.MEDIUM,
        description="Minimum confidence level for detections",
    ),
    max_objects: int = Form(50, ge=1, le=100, description="Maximum objects to return"),
    include_metadata: bool = Form(
        True, description="Include image metadata in response"
    ),
    cv_service: ComputerVisionService = Depends(get_computer_vision_service),
    authorized: bool = Depends(verify_api_key),
) -> AnalysisResult:
    """Analyze an uploaded image file for object detection.

    This endpoint accepts an uploaded image file and returns detected objects
    with their bounding boxes and confidence scores.

    Args:
        image: Uploaded image file
        confidence_threshold: Minimum confidence for detections
        max_objects: Maximum number of objects to return
        include_metadata: Whether to include image metadata
        cv_service: Computer Vision service dependency
        authorized: Authorization dependency

    Returns:
        AnalysisResult with detected objects and metadata

    Raises:
        HTTPException: On various error conditions
    """
    # Validate content type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {image.content_type}. Must be an image.",
        )

    try:
        logger.info(
            f"Starting upload analysis: {image.filename} "
            f"(confidence: {confidence_threshold}, max_objects: {max_objects})"
        )

        # Read image data
        image_data = await image.read()

        # Convert confidence enum to float
        confidence_map = {
            DetectionConfidence.LOW: 0.3,
            DetectionConfidence.MEDIUM: 0.5,
            DetectionConfidence.HIGH: 0.7,
        }
        confidence_float = confidence_map[confidence_threshold]

        # Perform analysis
        (
            detected_objects,
            image_metadata,
            processing_time,
        ) = await cv_service.analyze_image_from_stream(
            image_data, confidence_float, max_objects
        )

        # Build result
        result = AnalysisResult(
            detected_objects=detected_objects,
            image_metadata=image_metadata if include_metadata else None,
            processing_time_ms=processing_time,
            confidence_threshold=confidence_float,
            total_objects_detected=len(detected_objects),
        )

        logger.info(
            f"Upload analysis completed: {len(detected_objects)} objects detected "
            f"in {processing_time:.2f}ms"
        )

        return result

    except ComputerVisionServiceError as e:
        logger.error(f"Computer Vision service error: {e}")

        # Map service errors to HTTP status codes
        status_map = {
            "EMPTY_IMAGE_DATA": status.HTTP_400_BAD_REQUEST,
            "INVALID_IMAGE_DATA": status.HTTP_400_BAD_REQUEST,
            "IMAGE_TOO_LARGE": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "AZURE_CV_ERROR": status.HTTP_502_BAD_GATEWAY,
        }

        http_status = status_map.get(
            e.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        raise HTTPException(
            status_code=http_status,
            detail={
                "error_code": e.error_code,
                "error_message": e.message,
                "details": e.details,
            },
        )

    except Exception as e:
        logger.error(f"Unexpected error in upload analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "An unexpected error occurred",
                "details": {"exception": str(e)},
            },
        )


@router.get(
    "/analysis/{request_id}",
    response_model=AnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Get analysis result",
    description="Retrieve analysis result by request ID (for async processing)",
    responses={
        200: {"description": "Analysis result found"},
        404: {"description": "Analysis result not found", "model": AnalysisError},
        401: {"description": "Authentication required"},
    },
)
async def get_analysis_result(
    request_id: UUID, authorized: bool = Depends(verify_api_key)
) -> AnalysisResult:
    """Get analysis result by request ID.

    This endpoint is for future async processing support.
    Currently returns 501 Not Implemented.

    Args:
        request_id: UUID of the analysis request
        authorized: Authorization dependency

    Returns:
        AnalysisResult if found

    Raises:
        HTTPException: Always raises 501 for now
    """
    # TODO: Implement async result storage and retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "error_code": "NOT_IMPLEMENTED",
            "error_message": "Async result retrieval not yet implemented",
            "details": {"request_id": str(request_id)},
        },
    )
