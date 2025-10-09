"""
🎯 Simplified FastAPI Rate Limiting - Working Implementation

This is a working version of rate limiting with FastAPI that you can actually test.
Focus on the core patterns without complex imports.
"""

import time
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Simple in-memory rate limiting
class SimpleRateLimiter:
    def __init__(self):
        self.requests = {}  # user_id -> [timestamps]
        
    def is_allowed(self, user_id: str, limit: int = 10, window: int = 60) -> tuple[bool, int]:
        """Check if request is allowed within rate limit."""
        now = time.time()
        
        # Initialize user if not exists
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Clean old requests outside window
        cutoff = now - window
        self.requests[user_id] = [req_time for req_time in self.requests[user_id] if req_time > cutoff]
        
        # Check limit
        current_count = len(self.requests[user_id])
        if current_count >= limit:
            return False, 0
        
        # Record this request
        self.requests[user_id].append(now)
        remaining = limit - current_count - 1
        
        return True, remaining

# Global rate limiter
rate_limiter = SimpleRateLimiter()

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)
        
        # Get user ID (from IP for simplicity)
        user_id = request.client.host if request.client else "unknown"
        
        # Check rate limit (10 requests per minute)
        allowed, remaining = rate_limiter.is_allowed(user_id, limit=10, window=60)
        
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Try again later.",
                    "retry_after": 60
                },
                headers={
                    "X-RateLimit-Limit": "10",
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = "10"
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response

# Create FastAPI app
app = FastAPI(
    title="Simple Rate Limiting Demo",
    description="Working rate limiting with FastAPI",
    version="1.0.0"
)

# Add middleware
app.add_middleware(RateLimitMiddleware)

@app.get("/health")
async def health_check():
    """Health check - no rate limits."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Simple Rate Limiting Demo",
        "version": "1.0.0"
    }

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint with rate limiting."""
    return {
        "message": "This endpoint is rate limited!",
        "timestamp": datetime.utcnow().isoformat(),
        "tip": "Call this endpoint rapidly to test rate limiting"
    }

@app.get("/api/status")
async def rate_limit_status(request: Request):
    """Get current rate limit status."""
    user_id = request.client.host if request.client else "unknown"
    
    # Check current status without consuming a request
    now = time.time()
    if user_id in rate_limiter.requests:
        recent_requests = [req for req in rate_limiter.requests[user_id] if req > now - 60]
        remaining = max(0, 10 - len(recent_requests))
    else:
        remaining = 10
    
    return {
        "user_id": user_id,
        "rate_limit": {
            "limit": 10,
            "window_seconds": 60,
            "remaining": remaining,
            "reset_time": datetime.fromtimestamp(now + 60).isoformat()
        }
    }

if __name__ == "__main__":
    print("""
🎯 Simple Rate Limiting Server Ready!
====================================

FEATURES:
✅ Rate limiting middleware
✅ 10 requests per minute per IP
✅ HTTP 429 responses for violations
✅ Rate limit headers (X-RateLimit-*)
✅ Status endpoint to check limits

TESTING:
1. Start server: uvicorn simple_rate_limiting:app --reload --port 8003
2. Test: curl http://localhost:8003/health
3. Rapid test: for i in {1..15}; do curl http://localhost:8003/api/test; done
4. Check status: curl http://localhost:8003/api/status

🚀 This shows core rate limiting patterns in action!
    """)