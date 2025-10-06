"""Structured logging configuration."""

import logging
import sys
from typing import Any, Dict
import structlog
from structlog.typing import FilteringBoundLogger

from ..core.config import settings


def setup_logging() -> FilteringBoundLogger:
    """Configure structured logging for the application.

    Returns:
        Configured structured logger
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.api.log_level.upper()),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add log level
            structlog.stdlib.add_log_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Process stack info if present
            structlog.processors.StackInfoRenderer(),
            # Format exceptions
            structlog.dev.set_exc_info,
            # Add correlation IDs, user info, etc.
            add_context_processor,
            # Final processor: JSON in production, pretty in development
            structlog.dev.ConsoleRenderer(colors=settings.debug)
            if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


def add_context_processor(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add contextual information to log records.

    Args:
        logger: Logger instance
        method_name: Logging method name
        event_dict: Event dictionary

    Returns:
        Enhanced event dictionary
    """
    # Add service information
    event_dict["service"] = "ai-image-analyzer"
    event_dict["version"] = "0.1.0"
    event_dict["environment"] = settings.environment

    # Add correlation ID if available (would be set by middleware)
    # This is a placeholder for request correlation
    correlation_id = getattr(logger, "_correlation_id", None)
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    return event_dict


class LoggerMixin:
    """Mixin to add structured logging to classes."""

    @property
    def logger(self) -> FilteringBoundLogger:
        """Get a bound logger for this class."""
        if not hasattr(self, "_logger"):
            self._logger = structlog.get_logger(self.__class__.__name__)
        return self._logger


# Global logger instance
logger = setup_logging()
