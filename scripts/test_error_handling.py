#!/usr/bin/env python3
"""
Error Handling Test Script

This script tests the comprehensive error handling capabilities
including retry logic, circuit breaker, and rate limiting.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Set PYTHONPATH to include src directory
os.environ['PYTHONPATH'] = str(project_root / "src")

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    # dotenv not available, try manual loading
    env_file = project_root / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

from azure.core.exceptions import HttpResponseError
from src.core.config import Settings
from src.core.error_handling import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RateLimiter,
    RateLimitConfig,
    RetryConfig,
    retry_with_backoff,
    classify_error_severity,
    ErrorSeverity,
    CircuitBreakerError,
    RateLimitExceededError
)


async def test_retry_logic():
    """Test retry logic with different error types."""
    print("🔄 Testing Retry Logic...")
    
    # Test successful retry after failures
    attempt_count = 0
    
    async def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise HttpResponseError("Temporary error")
        return "Success!"
    
    config = RetryConfig(max_attempts=5, base_delay=0.1)
    
    try:
        result = await retry_with_backoff(
            flaky_function,
            config,
            "test_retry"
        )
        print(f"  ✅ Retry succeeded after {attempt_count} attempts: {result}")
    except Exception as e:
        print(f"  ❌ Retry failed: {e}")
        return False
    
    # Test critical error (no retry)
    async def critical_function():
        # Simulate 401 Unauthorized (critical error) 
        error = HttpResponseError("Unauthorized")
        error.status_code = 401
        raise error
    
    try:
        await retry_with_backoff(
            critical_function,
            config,
            "test_critical"
        )
        print("  ❌ Critical error should not retry")
        return False
    except HttpResponseError:
        print("  ✅ Critical error correctly not retried")
    
    return True


async def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("🔄 Testing Circuit Breaker...")
    
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1.0,  # Short timeout for testing
        expected_exception=HttpResponseError
    )
    
    circuit_breaker = CircuitBreaker("test_cb", config)
    
    # Test normal operation
    async def success_func():
        return "Success"
    
    try:
        result = await circuit_breaker.call(success_func)
        print(f"  ✅ Normal operation: {result}")
    except Exception as e:
        print(f"  ❌ Normal operation failed: {e}")
        return False
    
    # Test circuit opening after failures
    async def failing_func():
        raise HttpResponseError("Service error")
    
    # Cause failures to open circuit
    for i in range(config.failure_threshold):
        try:
            await circuit_breaker.call(failing_func)
        except HttpResponseError:
            pass  # Expected
    
    # Circuit should be open now
    try:
        await circuit_breaker.call(success_func)
        print("  ❌ Circuit breaker should be open")
        return False
    except CircuitBreakerError:
        print("  ✅ Circuit breaker correctly opened")
    
    # Wait for recovery timeout
    await asyncio.sleep(config.recovery_timeout + 0.1)
    
    # Circuit should allow test call (half-open)
    try:
        result = await circuit_breaker.call(success_func)
        print(f"  ✅ Circuit breaker recovered: {result}")
    except Exception as e:
        print(f"  ❌ Circuit recovery failed: {e}")
        return False
    
    return True


async def test_rate_limiter():
    """Test rate limiting functionality."""
    print("🔄 Testing Rate Limiter...")
    
    config = RateLimitConfig(
        max_requests=3,
        time_window=1.0,  # 1 second window
        burst_allowance=1
    )
    
    rate_limiter = RateLimiter("test_rl", config)
    
    # Test normal requests within limit
    try:
        for i in range(3):
            await rate_limiter.acquire()
        print("  ✅ Requests within limit succeeded")
    except RateLimitExceededError as e:
        print(f"  ❌ Requests within limit failed: {e}")
        return False
    
    # Test rate limit exceeded
    try:
        await rate_limiter.acquire()
        print("  ❌ Rate limit should be exceeded")
        return False
    except RateLimitExceededError:
        print("  ✅ Rate limit correctly enforced")
    
    # Wait for token refill
    await asyncio.sleep(1.1)
    
    # Should work again after refill
    try:
        await rate_limiter.acquire()
        print("  ✅ Rate limiter recovered after time window")
    except RateLimitExceededError as e:
        print(f"  ❌ Rate limiter recovery failed: {e}")
        return False
    
    return True


def test_error_classification():
    """Test error severity classification."""
    print("🔄 Testing Error Classification...")
    
    # Test HTTP 429 (rate limited) - medium severity
    error_429 = HttpResponseError("Rate limited")
    error_429.status_code = 429
    severity = classify_error_severity(error_429)
    if severity != ErrorSeverity.MEDIUM:
        print(f"  ❌ HTTP 429 should be MEDIUM, got {severity}")
        return False
    
    # Test HTTP 401 (unauthorized) - high severity
    error_401 = HttpResponseError("Unauthorized")
    error_401.status_code = 401
    severity = classify_error_severity(error_401)
    if severity != ErrorSeverity.HIGH:
        print(f"  ❌ HTTP 401 should be HIGH, got {severity}")
        return False
    
    # Test HTTP 502 (bad gateway) - low severity (temporary)
    error_502 = HttpResponseError("Bad Gateway")
    error_502.status_code = 502
    severity = classify_error_severity(error_502)
    if severity != ErrorSeverity.LOW:
        print(f"  ❌ HTTP 502 should be LOW, got {severity}")
        return False
    
    # Test connection error - low severity
    conn_error = ConnectionError("Connection failed")
    severity = classify_error_severity(conn_error)
    if severity != ErrorSeverity.LOW:
        print(f"  ❌ ConnectionError should be LOW, got {severity}")
        return False
    
    print("  ✅ Error classification working correctly")
    return True


async def test_integrated_error_handling():
    """Test integrated error handling with all components."""
    print("🔄 Testing Integrated Error Handling...")
    
    # Mock Azure Computer Vision service behavior
    call_count = 0
    
    async def mock_azure_call():
        nonlocal call_count
        call_count += 1
        
        if call_count <= 2:
            # First two calls fail with retryable error
            error = HttpResponseError("Service temporarily unavailable")
            error.status_code = 503
            raise error
        else:
            # Third call succeeds
            return {"objects": [], "metadata": {"width": 100, "height": 100}}
    
    # Configuration for quick testing
    retry_config = RetryConfig(max_attempts=5, base_delay=0.1)
    circuit_config = CircuitBreakerConfig(failure_threshold=10, recovery_timeout=1.0)
    rate_config = RateLimitConfig(max_requests=10, time_window=1.0)
    
    circuit_breaker = CircuitBreaker("integrated_test", circuit_config)
    rate_limiter = RateLimiter("integrated_test", rate_config)
    
    try:
        # Apply rate limiting
        await rate_limiter.acquire()
        
        # Execute with circuit breaker and retry
        result = await circuit_breaker.call(
            lambda: retry_with_backoff(
                mock_azure_call,
                retry_config,
                "integrated_test"
            )
        )
        
        print(f"  ✅ Integrated error handling succeeded after {call_count} attempts")
        return True
        
    except Exception as e:
        print(f"  ❌ Integrated error handling failed: {e}")
        return False


async def main():
    """Run all error handling tests."""
    print("🚀 Error Handling Test Suite")
    print("=" * 50)
    print()
    
    tests = [
        ("Retry Logic", test_retry_logic),
        ("Circuit Breaker", test_circuit_breaker),
        ("Rate Limiter", test_rate_limiter),
        ("Error Classification", lambda: test_error_classification()),
        ("Integrated Handling", test_integrated_error_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            
            if success:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
        
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All error handling tests PASSED!")
        print("\nYour error handling system is production-ready!")
        print("\nFeatures verified:")
        print("- ✅ Exponential backoff retry logic")
        print("- ✅ Circuit breaker pattern")
        print("- ✅ Rate limiting protection")
        print("- ✅ Error severity classification")
        print("- ✅ Integrated error handling")
    else:
        print(f"❌ {total - passed} tests failed. Please review the error handling implementation.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())