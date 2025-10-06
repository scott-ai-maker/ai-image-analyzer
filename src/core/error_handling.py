"""
Enhanced error handling utilities for production resilience.

This module provides enterprise-grade error handling patterns including:
- Exponential backoff retry logic
- Circuit breaker pattern
- Rate limiting protection
- Graceful degradation strategies
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from functools import wraps
import random

from azure.core.exceptions import HttpResponseError
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """Retry strategy options."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"  # Temporary issues, safe to retry
    MEDIUM = "medium"  # Service issues, limited retries
    HIGH = "high"  # Critical issues, minimal retries
    CRITICAL = "critical"  # System failures, no retries


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: Type[Exception] = Exception
    half_open_max_calls: int = 3


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""

    max_requests: int = 100
    time_window: float = 60.0  # seconds
    burst_allowance: int = 10


class ErrorContext(BaseModel):
    """Context information for error handling."""

    operation: str
    attempt: int
    max_attempts: int
    total_elapsed: float
    last_error: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.MEDIUM


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str, service_name: str):
        super().__init__(message)
        self.service_name = service_name


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: float):
        super().__init__(message)
        self.retry_after = retry_after


class CircuitBreaker:
    """
    Circuit breaker implementation for service protection.

    Prevents cascading failures by temporarily blocking requests
    to failing services and allowing them time to recover.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info(
                        f"Circuit breaker {self.name} transitioning to HALF_OPEN"
                    )
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker {self.name} is OPEN", self.name
                    )

            if self.state == CircuitBreakerState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerError(
                        f"Circuit breaker {self.name} max half-open calls exceeded",
                        self.name,
                    )

        try:
            result = (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )
            await self._on_success()
            return result
        except self.config.expected_exception as e:
            await self._on_failure()
            raise

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED
                logger.info(
                    f"Circuit breaker {self.name} recovered, transitioning to CLOSED"
                )

            self.failure_count = 0
            self.half_open_calls += 1

    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    f"Circuit breaker {self.name} opened after {self.failure_count} failures"
                )

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if not self.last_failure_time:
            return False

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout

    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed (normal operation)."""
        return self.state == CircuitBreakerState.CLOSED


class RateLimiter:
    """
    Token bucket rate limiter for API protection.

    Prevents overwhelming external services by limiting
    the rate of outgoing requests.
    """

    def __init__(self, name: str, config: RateLimitConfig):
        self.name = name
        self.config = config
        self.tokens = config.max_requests
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens for request."""
        async with self._lock:
            now = time.time()
            self._refill_tokens(now)

            if self.tokens < tokens:
                wait_time = self._calculate_wait_time(tokens)
                raise RateLimitExceededError(
                    f"Rate limit exceeded for {self.name}. Try again in {wait_time:.2f}s",
                    wait_time,
                )

            self.tokens -= tokens

    def _refill_tokens(self, now: float) -> None:
        """Refill token bucket based on elapsed time."""
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * (self.config.max_requests / self.config.time_window)

        self.tokens = min(
            self.config.max_requests + self.config.burst_allowance,
            self.tokens + tokens_to_add,
        )
        self.last_refill = now

    def _calculate_wait_time(self, tokens_needed: int) -> float:
        """Calculate time to wait for required tokens."""
        tokens_deficit = tokens_needed - self.tokens
        return tokens_deficit * (self.config.time_window / self.config.max_requests)


def classify_error_severity(error: Exception) -> ErrorSeverity:
    """
    Classify error severity for retry decisions.

    Args:
        error: Exception to classify

    Returns:
        ErrorSeverity level
    """
    if isinstance(error, HttpResponseError):
        status_code = getattr(error, "status_code", None)

        if status_code is not None:
            # Client errors (4xx) - usually not worth retrying
            if 400 <= status_code < 500:
                if status_code == 429:  # Rate limited
                    return ErrorSeverity.MEDIUM
                elif status_code in [401, 403]:  # Auth issues
                    return ErrorSeverity.HIGH
                else:  # Other client errors
                    return ErrorSeverity.CRITICAL

            # Server errors (5xx) - worth retrying
            elif 500 <= status_code < 600:
                if status_code in [502, 503, 504]:  # Temporary server issues
                    return ErrorSeverity.LOW
                else:  # Other server errors
                    return ErrorSeverity.MEDIUM

    # Network/connection errors
    elif isinstance(error, (ConnectionError, TimeoutError)):
        return ErrorSeverity.LOW

    # Unknown errors
    return ErrorSeverity.MEDIUM


def calculate_backoff_delay(
    attempt: int, config: RetryConfig, severity: ErrorSeverity
) -> float:
    """
    Calculate backoff delay based on strategy and severity.

    Args:
        attempt: Current attempt number (1-based)
        config: Retry configuration
        severity: Error severity level

    Returns:
        Delay in seconds before next retry
    """
    # Adjust base delay based on severity
    severity_multipliers = {
        ErrorSeverity.LOW: 0.5,
        ErrorSeverity.MEDIUM: 1.0,
        ErrorSeverity.HIGH: 2.0,
        ErrorSeverity.CRITICAL: 5.0,
    }

    base_delay = config.base_delay * severity_multipliers[severity]

    if config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
        delay = base_delay * (config.exponential_base ** (attempt - 1))
    elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
        delay = base_delay * attempt
    else:  # FIXED_DELAY
        delay = base_delay

    # Apply jitter to prevent thundering herd
    if config.jitter:
        jitter_factor = random.uniform(0.8, 1.2)
        delay *= jitter_factor

    # Cap at max delay
    delay = min(delay, config.max_delay)

    return delay


async def retry_with_backoff(
    func: Callable, config: RetryConfig, operation_name: str, *args, **kwargs
) -> Any:
    """
    Execute function with retry logic and exponential backoff.

    Args:
        func: Function to execute
        config: Retry configuration
        operation_name: Name of operation for logging
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries exhausted
    """
    start_time = time.time()
    last_exception = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            logger.debug(
                f"Attempting {operation_name} (attempt {attempt}/{config.max_attempts})"
            )

            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            if attempt > 1:
                elapsed = time.time() - start_time
                logger.info(
                    f"{operation_name} succeeded on attempt {attempt} "
                    f"after {elapsed:.2f}s"
                )

            return result

        except Exception as e:
            last_exception = e
            severity = classify_error_severity(e)
            elapsed = time.time() - start_time

            context = ErrorContext(
                operation=operation_name,
                attempt=attempt,
                max_attempts=config.max_attempts,
                total_elapsed=elapsed,
                last_error=str(e),
                severity=severity,
            )

            # Don't retry critical errors
            if severity == ErrorSeverity.CRITICAL:
                logger.error(f"{operation_name} failed with critical error: {e}")
                raise

            # Last attempt - don't calculate delay
            if attempt == config.max_attempts:
                logger.error(
                    f"{operation_name} failed after {attempt} attempts "
                    f"in {elapsed:.2f}s: {e}"
                )
                break

            # Calculate delay and wait
            delay = calculate_backoff_delay(attempt, config, severity)

            logger.warning(
                f"{operation_name} attempt {attempt} failed ({severity.value}): {e}. "
                f"Retrying in {delay:.2f}s"
            )

            await asyncio.sleep(delay)

    # All retries exhausted
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError(
            f"{operation_name} failed after {config.max_attempts} attempts"
        )


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to functions.

    Args:
        config: Retry configuration (uses defaults if None)

    Returns:
        Decorated function
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            return await retry_with_backoff(
                func, config, operation_name, *args, **kwargs
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            return asyncio.run(
                retry_with_backoff(func, config, operation_name, *args, **kwargs)
            )

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
