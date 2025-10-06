"""Custom exception handlers and error utilities."""

import traceback
from typing import Optional, Dict, Any
from uuid import uuid4

from ..models.schemas import AnalysisError


class BaseServiceError(Exception):
    """Base exception for service-level errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        """Initialize service error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error context
            correlation_id: Request correlation ID
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid4())


class ValidationError(BaseServiceError):
    """Exception for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        """Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            **kwargs: Additional arguments
        """
        details = kwargs.get("details", {})
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"},
        )


class ExternalServiceError(BaseServiceError):
    """Exception for external service errors."""

    def __init__(self, service: str, message: str, **kwargs):
        """Initialize external service error.

        Args:
            service: Name of the external service
            message: Error message
            **kwargs: Additional arguments
        """
        details = kwargs.get("details", {})
        details["service"] = service

        super().__init__(
            message=f"{service} error: {message}",
            error_code=f"{service.upper()}_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"},
        )


class RateLimitError(BaseServiceError):
    """Exception for rate limiting."""

    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        """Initialize rate limit error.

        Args:
            message: Error message
            **kwargs: Additional arguments
        """
        super().__init__(message=message, error_code="RATE_LIMIT_EXCEEDED", **kwargs)


class ResourceNotFoundError(BaseServiceError):
    """Exception for resource not found errors."""

    def __init__(self, resource: str, identifier: str, **kwargs):
        """Initialize resource not found error.

        Args:
            resource: Type of resource
            identifier: Resource identifier
            **kwargs: Additional arguments
        """
        details = kwargs.get("details", {})
        details.update({"resource": resource, "identifier": identifier})

        super().__init__(
            message=f"{resource} not found: {identifier}",
            error_code="RESOURCE_NOT_FOUND",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"},
        )


def create_error_response(
    error: Exception, include_traceback: bool = False
) -> AnalysisError:
    """Create standardized error response from exception.

    Args:
        error: Exception to convert
        include_traceback: Whether to include stack trace

    Returns:
        AnalysisError response model
    """
    if isinstance(error, BaseServiceError):
        # Use structured error information
        details = error.details.copy()
        if include_traceback:
            details["traceback"] = traceback.format_exc()

        return AnalysisError(
            error_code=error.error_code, error_message=error.message, details=details
        )

    else:
        # Handle unexpected errors
        details = {
            "exception_type": type(error).__name__,
        }
        if include_traceback:
            details["traceback"] = traceback.format_exc()

        return AnalysisError(
            error_code="INTERNAL_ERROR",
            error_message="An unexpected error occurred",
            details=details,
        )


def log_error(logger, error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log error with appropriate level and context.

    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional context
    """
    context = context or {}

    if isinstance(error, BaseServiceError):
        # Log service errors as warnings (expected errors)
        logger.warning(
            f"Service error: {error.message}",
            error_code=error.error_code,
            correlation_id=error.correlation_id,
            details=error.details,
            **context,
        )
    else:
        # Log unexpected errors as errors
        logger.error(
            f"Unexpected error: {str(error)}",
            exception=str(error),
            exception_type=type(error).__name__,
            **context,
            exc_info=True,
        )
