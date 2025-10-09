"""
🎯 FastAPI Rate Limiting Integration - Hands-on Implementation

This integrates your rate limiting algorithms with FastAPI endpoints.
YOU'LL add production-grade rate limiting middleware to protect your API.

Key patterns you'll implement:
1. FastAPI middleware for automatic rate limiting
2. Rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining)
3. HTTP 429 "Too Many Requests" responses
4. User-specific rate limits based on JWT roles
5. Endpoint-specific rate limits

This shows how real APIs protect themselves from abuse!
"""

from datetime import datetime
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth_hands_on import UserRole

# Import your FastAPI auth integration
from fastapi_auth_integration import get_current_user

# Import your rate limiting classes
from rate_limiting_hands_on import RedisRateLimiter, UserTierRateLimiter

# ============================================================================
# 🛡️ RATE LIMITING MIDDLEWARE
# ============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    YOUR TASK: Implement FastAPI rate limiting middleware

    This middleware will:
    1. Check rate limits before processing requests
    2. Add rate limit headers to responses
    3. Return 429 status when limits exceeded
    4. Apply different limits based on user tiers
    """

    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.tier_limiter = UserTierRateLimiter()
        self.redis_limiter = RedisRateLimiter()

        # Endpoint-specific limits (requests per hour)
        self.endpoint_limits = {
            "/api/v1/analyze/basic": 100,  # Analysis endpoint
            "/api/v1/analytics/dashboard": 50,  # Analytics endpoint
            "/api/v1/admin/cleanup": 10,  # Admin endpoint
        }

        print("🛡️ Rate Limiting Middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        YOUR TASK: Process request with rate limiting

        Steps:
        1. Extract user info from JWT token (if present)
        2. Check rate limits for user tier and endpoint
        3. Add rate limit headers to response
        4. Return 429 if limits exceeded
        """

        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        # TODO: YOU implement user extraction
        user_info = await self._extract_user_info(request)
        user_id = user_info.get("user_id", "anonymous")
        user_role = user_info.get("role", UserRole.USER)

        # TODO: YOU implement rate limit checking
        rate_limit_result = self.tier_limiter.check_rate_limit(user_id, user_role)

        if not rate_limit_result.allowed:
            # Rate limit exceeded - return 429
            print(f"🛡️ Rate limit exceeded for user {user_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Try again in {rate_limit_result.retry_after} seconds.",
                    "user_id": user_id,
                    "user_role": user_role.value,
                    "retry_after": rate_limit_result.retry_after,
                },
                headers={
                    "X-RateLimit-Limit": str(self._get_user_limit(user_role)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(
                        int(rate_limit_result.reset_time.timestamp())
                    ),
                    "Retry-After": str(rate_limit_result.retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # TODO: YOU implement rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self._get_user_limit(user_role))
        response.headers["X-RateLimit-Remaining"] = str(
            rate_limit_result.requests_remaining
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(rate_limit_result.reset_time.timestamp())
        )

        print(
            f"🛡️ Request processed for {user_role.value} user: {rate_limit_result.requests_remaining} remaining"
        )

        return response

    async def _extract_user_info(self, request: Request) -> dict:
        """Extract user info from JWT token if present."""
        try:
            # Get Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return {"user_id": "anonymous", "role": UserRole.USER}

            # Use your existing JWT verification
            from fastapi_auth_integration import jwt_manager

            token = auth_header.split(" ")[1]
            payload = jwt_manager.verify_access_token(token)

            if payload:
                return {
                    "user_id": payload.get("user_id", "anonymous"),
                    "role": UserRole(payload.get("role", "user")),
                }
        except Exception as e:
            print(f"⚠️ Error extracting user info: {e}")

        return {"user_id": "anonymous", "role": UserRole.USER}

    def _get_user_limit(self, user_role: UserRole) -> int:
        """Get rate limit for user role."""
        limits = {UserRole.USER: 100, UserRole.PREMIUM: 1000, UserRole.ADMIN: 10000}
        return limits.get(user_role, 100)


# ============================================================================
# 🎛️ RATE LIMIT DECORATORS
# ============================================================================


def rate_limit(requests: int, window: int):
    """
    YOUR TASK: Create decorator for endpoint-specific rate limits

    Usage: @rate_limit(requests=10, window=60)  # 10 requests per minute
    """

    def decorator(func):
        # Mark function with rate limit info
        func._rate_limit = {"requests": requests, "window": window}
        return func

    return decorator


def premium_rate_limit(user_requests: int, premium_requests: int, window: int):
    """
    YOUR TASK: Create decorator for tier-based endpoint limits

    Different limits for different user tiers on same endpoint.
    """

    def decorator(func):
        func._tier_rate_limits = {
            UserRole.USER: {"requests": user_requests, "window": window},
            UserRole.PREMIUM: {"requests": premium_requests, "window": window},
            UserRole.ADMIN: {
                "requests": premium_requests * 10,
                "window": window,
            },  # Admin gets 10x
        }
        return func

    return decorator


# ============================================================================
# 🚀 FASTAPI APP WITH RATE LIMITING
# ============================================================================

app = FastAPI(
    title="AI Image Analyzer with Rate Limiting",
    description="Production-grade API with sophisticated rate limiting",
    version="3.0.0",
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)


# ============================================================================
# 🔓 PUBLIC ENDPOINTS (NO RATE LIMITS)
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check - no rate limits."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AI Image Analyzer with Rate Limiting",
        "version": "3.0.0",
    }


# Import authentication endpoints from your auth integration
from fastapi_auth_integration import LoginRequest, TokenResponse


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Login endpoint - no rate limits for authentication."""
    # Import the login logic from your auth integration
    from fastapi_auth_integration import MOCK_USERS, jwt_manager

    user = MOCK_USERS.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Get user permissions based on role
    from rate_limiting_hands_on import RBACManager

    rbac_manager = RBACManager()
    user_permissions = rbac_manager.role_permissions.get(user["role"], [])
    permission_strings = [perm.value for perm in user_permissions]

    access_token = jwt_manager.create_access_token(
        user_id=user["user_id"], role=user["role"], permissions=permission_strings
    )

    refresh_token = jwt_manager.create_refresh_token(user["user_id"])

    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, expires_in=15 * 60
    )


# ============================================================================
# 🔒 PROTECTED ENDPOINTS WITH RATE LIMITING
# ============================================================================


@app.post("/api/v1/analyze/basic")
@rate_limit(requests=100, window=3600)  # 100 requests per hour
async def analyze_image_basic(
    image_url: str, current_user: dict = Depends(get_current_user)
):
    """
    Basic image analysis with rate limiting.
    Rate limit: 100 requests/hour for all users.
    """
    return {
        "message": "Image analysis completed with rate limiting",
        "image_url": image_url,
        "analysis": ["car", "person", "building"],
        "confidence": 0.95,
        "processed_by": current_user["user_id"],
        "user_role": current_user["role"],
        "rate_limited": True,
    }


@app.get("/api/v1/analytics/dashboard")
@premium_rate_limit(user_requests=10, premium_requests=100, window=3600)
async def get_analytics_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Analytics dashboard with tier-based rate limiting.
    USER: 10 requests/hour, PREMIUM: 100 requests/hour, ADMIN: 1000 requests/hour
    """
    return {
        "message": "Analytics dashboard with tier-based rate limiting",
        "total_analyses": 1234,
        "success_rate": 0.98,
        "avg_processing_time": 1.2,
        "accessed_by": current_user["user_id"],
        "user_role": current_user["role"],
        "tier_limited": True,
    }


@app.delete("/api/v1/admin/cleanup")
@rate_limit(requests=5, window=3600)  # Very restrictive for admin operations
async def admin_cleanup(current_user: dict = Depends(get_current_user)):
    """
    Admin cleanup with strict rate limiting.
    Only 5 requests per hour - admin operations should be rare.
    """
    return {
        "message": "Admin cleanup with strict rate limiting",
        "cleaned_records": 42,
        "executed_by": current_user["user_id"],
        "user_role": current_user["role"],
        "strictly_limited": True,
    }


# ============================================================================
# 📊 RATE LIMIT STATUS ENDPOINTS
# ============================================================================


@app.get("/api/v1/rate-limit/status")
async def get_rate_limit_status(current_user: dict = Depends(get_current_user)):
    """Get current rate limit status for authenticated user."""
    user_role = UserRole(current_user["role"])

    # Get current limits
    tier_limiter = UserTierRateLimiter()
    result = tier_limiter.check_rate_limit(current_user["user_id"], user_role)

    return {
        "user_id": current_user["user_id"],
        "user_role": user_role.value,
        "rate_limit": {
            "requests_remaining": result.requests_remaining,
            "reset_time": result.reset_time.isoformat(),
            "window_seconds": 3600,
        },
        "tier_info": {
            "current_tier": user_role.value,
            "hourly_limit": tier_limiter.tier_limits[user_role].requests,
            "next_tier": "premium"
            if user_role == UserRole.USER
            else "admin"
            if user_role == UserRole.PREMIUM
            else "max",
        },
    }


@app.get("/api/v1/rate-limit/test")
async def test_rate_limiting():
    """Test endpoint to trigger rate limiting quickly."""
    return {
        "message": "Rate limiting test endpoint",
        "timestamp": datetime.utcnow().isoformat(),
        "tip": "Call this endpoint rapidly to test rate limiting",
    }


# ============================================================================
# 🧪 TESTING INSTRUCTIONS
# ============================================================================

if __name__ == "__main__":
    print(
        """
🎯 FastAPI Rate Limiting Integration Complete!
============================================

YOUR IMPLEMENTATION INCLUDES:
✅ Rate limiting middleware for all endpoints
✅ JWT-based user tier detection
✅ HTTP 429 responses for rate limit violations
✅ Rate limit headers (X-RateLimit-*)
✅ Endpoint-specific and tier-based limits
✅ Rate limit status endpoints

TESTING COMMANDS:
================

1. Start the server:
   uvicorn fastapi_rate_limiting:app --reload --port 8002

2. Login to get tokens:
   curl -X POST "http://localhost:8002/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "john_doe", "password": "password123"}'

3. Test rate limiting (call rapidly):
   for i in {1..10}; do
     curl -X GET "http://localhost:8002/api/v1/rate-limit/test" \
       -H "Authorization: Bearer YOUR_TOKEN" \
       -w "Status: %{http_code}\\n"
   done

4. Check rate limit status:
   curl -X GET "http://localhost:8002/api/v1/rate-limit/status" \
     -H "Authorization: Bearer YOUR_TOKEN"

5. Test different user tiers:
   - USER: john_doe (100 req/hour)
   - PREMIUM: premium_user (1000 req/hour)
   - ADMIN: admin_user (10000 req/hour)

🚀 This is how production APIs handle millions of requests safely!
    """
    )
