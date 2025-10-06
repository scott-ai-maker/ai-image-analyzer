"""
Production error handling configuration.

This module contains error handling configurations for different
production environments and service tiers.
"""

from ..core.error_handling import (
    RetryConfig,
    CircuitBreakerConfig,
    RateLimitConfig,
    RetryStrategy,
)
from azure.core.exceptions import HttpResponseError


# Azure Computer Vision Error Handling Configurations

# Production configuration for Azure Computer Vision (Standard tier)
AZURE_CV_PRODUCTION_CONFIG = {
    "retry": RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    ),
    "circuit_breaker": CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=120.0,
        expected_exception=HttpResponseError,
        half_open_max_calls=5,
    ),
    "rate_limiter": RateLimitConfig(
        max_requests=100,  # Standard tier: 10 calls/second
        time_window=60.0,
        burst_allowance=20,
    ),
}

# Development configuration (Free tier)
AZURE_CV_DEVELOPMENT_CONFIG = {
    "retry": RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    ),
    "circuit_breaker": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exception=HttpResponseError,
        half_open_max_calls=3,
    ),
    "rate_limiter": RateLimitConfig(
        max_requests=15,  # Free tier: 20 calls/minute (conservative)
        time_window=60.0,
        burst_allowance=5,
    ),
}

# Staging configuration
AZURE_CV_STAGING_CONFIG = {
    "retry": RetryConfig(
        max_attempts=4,
        base_delay=1.0,
        max_delay=45.0,
        exponential_base=2.0,
        jitter=True,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    ),
    "circuit_breaker": CircuitBreakerConfig(
        failure_threshold=7,
        recovery_timeout=90.0,
        expected_exception=HttpResponseError,
        half_open_max_calls=4,
    ),
    "rate_limiter": RateLimitConfig(
        max_requests=50,  # Intermediate rate limiting
        time_window=60.0,
        burst_allowance=10,
    ),
}

# Configuration mapping by environment
ERROR_HANDLING_CONFIGS = {
    "development": AZURE_CV_DEVELOPMENT_CONFIG,
    "staging": AZURE_CV_STAGING_CONFIG,
    "production": AZURE_CV_PRODUCTION_CONFIG,
}


def get_error_handling_config(environment: str) -> dict:
    """
    Get error handling configuration for environment.

    Args:
        environment: Environment name (development, staging, production)

    Returns:
        Error handling configuration dictionary
    """
    return ERROR_HANDLING_CONFIGS.get(environment.lower(), AZURE_CV_DEVELOPMENT_CONFIG)
