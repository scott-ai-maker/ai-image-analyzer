"""
🎯 AI Image Analyzer - Enterprise FastAPI Backend

Production-ready FastAPI application with rate limiting, Azure integration,
and comprehensive monitoring for enterprise deployment.
"""

import logging
import os
import time
from datetime import datetime

from fastapi import FastAPI, File, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Azure Application Insights (only import if connection string is available)
try:
    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        from opencensus.ext.azure import metrics_exporter
        from opencensus.ext.azure.log_exporter import AzureLogHandler
        from opencensus.ext.fastapi import FastAPIMiddleware
        from opencensus.stats import aggregation as aggregation_module
        from opencensus.stats import measure as measure_module
        from opencensus.stats import stats as stats_module
        from opencensus.stats import view as view_module
        from opencensus.tags import tag_map as tag_map_module

        # Configure logging
        logger = logging.getLogger(__name__)
        logger.addHandler(
            AzureLogHandler(
                connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
            )
        )
        logger.setLevel(logging.INFO)

        AZURE_MONITORING_ENABLED = True
    else:
        AZURE_MONITORING_ENABLED = False
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
except ImportError:
    AZURE_MONITORING_ENABLED = False
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


# Simple in-memory rate limiting
class SimpleRateLimiter:
    def __init__(self):
        self.requests = {}  # user_id -> [timestamps]

    def is_allowed(
        self, user_id: str, limit: int = 10, window: int = 60
    ) -> tuple[bool, int]:
        """Check if request is allowed within rate limit."""
        now = time.time()

        # Initialize user if not exists
        if user_id not in self.requests:
            self.requests[user_id] = []

        # Clean old requests outside window
        cutoff = now - window
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id] if req_time > cutoff
        ]

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
                    "retry_after": 60,
                },
                headers={
                    "X-RateLimit-Limit": "10",
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = "10"
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


# Configuration from environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Create FastAPI app
app = FastAPI(
    title="AI Image Analyzer API",
    description="Enterprise-grade AI Image Analyzer with rate limiting and Azure integration",
    version="2.0.0",
    docs_url="/docs" if ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if ENVIRONMENT == "development" else None,
)

# CORS Configuration
allowed_origins = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add Azure monitoring middleware if available
if AZURE_MONITORING_ENABLED:
    try:
        app.add_middleware(FastAPIMiddleware)
        logger.info("Azure Application Insights monitoring enabled")
    except Exception as e:
        logger.warning(f"Failed to enable Azure monitoring: {e}")

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)


@app.get("/health")
async def health_check():
    """Health check - no rate limits."""
    import psutil

    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AI Image Analyzer API",
        "version": "2.0.0",
        "environment": ENVIRONMENT,
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": (disk.used / disk.total) * 100,
            "uptime_seconds": time.time() - psutil.boot_time()
            if hasattr(psutil, "boot_time")
            else None,
        },
        "azure_monitoring": AZURE_MONITORING_ENABLED,
        "rate_limiting": {
            "active_users": len(rate_limiter.requests),
            "algorithm": "sliding_window",
        },
    }

    # Log health check if Azure monitoring is enabled
    if AZURE_MONITORING_ENABLED:
        logger.info(
            "Health check performed",
            extra={
                "custom_dimensions": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "active_users": len(rate_limiter.requests),
                }
            },
        )

    return health_data


@app.get("/api/test")
async def test_endpoint():
    """Test endpoint with rate limiting."""
    return {
        "message": "This endpoint is rate limited!",
        "timestamp": datetime.utcnow().isoformat(),
        "tip": "Call this endpoint rapidly to test rate limiting",
    }


@app.get("/api/status")
async def rate_limit_status(request: Request):
    """Get current rate limit status."""
    user_id = request.client.host if request.client else "unknown"

    # Check current status without consuming a request
    now = time.time()
    if user_id in rate_limiter.requests:
        recent_requests = [
            req for req in rate_limiter.requests[user_id] if req > now - 60
        ]
        remaining = max(0, 10 - len(recent_requests))
    else:
        remaining = 10

    return {
        "user_id": user_id,
        "rate_limit": {
            "limit": 10,
            "window_seconds": 60,
            "remaining": remaining,
            "reset_time": datetime.fromtimestamp(now + 60).isoformat(),
        },
    }


@app.post("/api/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    """Analyze uploaded image with rate limiting."""
    start_time = time.time()

    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            if AZURE_MONITORING_ENABLED:
                logger.warning(
                    "Invalid file type uploaded",
                    extra={
                        "custom_dimensions": {
                            "content_type": file.content_type,
                            "filename": file.filename,
                        }
                    },
                )
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid file type. Please upload an image."},
            )

        # Read file content (in production, this would go to Azure Storage)
        content = await file.read()
        file_size = len(content)

        # Mock AI analysis (in production, this would use Azure Computer Vision)
        processing_time = int((time.time() - start_time) * 1000)

        analysis_result = {
            "filename": file.filename,
            "file_size": file_size,
            "content_type": file.content_type,
            "analysis": {
                "objects_detected": ["person", "car", "building"],
                "confidence_scores": [0.95, 0.87, 0.92],
                "description": "This image contains a person standing next to a car in front of a building",
                "colors": ["blue", "red", "gray"],
                "text_detected": [],
                "faces_detected": 1,
                "adult_content": False,
                "racy_content": False,
            },
            "metadata": {
                "analyzed_at": datetime.utcnow().isoformat(),
                "processing_time_ms": processing_time,
                "model_version": "2.0.0",
                "environment": ENVIRONMENT,
            },
        }

        # Log successful analysis if Azure monitoring is enabled
        if AZURE_MONITORING_ENABLED:
            logger.info(
                "Image analysis completed",
                extra={
                    "custom_dimensions": {
                        "filename": file.filename,
                        "file_size": file_size,
                        "content_type": file.content_type,
                        "processing_time_ms": processing_time,
                        "objects_count": len(
                            analysis_result["analysis"]["objects_detected"]
                        ),
                    }
                },
            )

        return analysis_result

    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        if AZURE_MONITORING_ENABLED:
            logger.error(
                "Image analysis failed",
                extra={
                    "custom_dimensions": {
                        "error": str(e),
                        "processing_time_ms": processing_time,
                        "filename": file.filename if file else "unknown",
                    }
                },
            )
        raise


@app.get("/api/demo-info")
async def get_demo_info():
    """Get information about the demo capabilities."""
    return {
        "demo_features": [
            "Image upload and analysis",
            "Rate limiting (10 requests/minute)",
            "Mock AI analysis results",
            "Enterprise error handling",
            "Azure cloud deployment",
            "CORS configuration",
            "Health monitoring",
        ],
        "rate_limiting": {
            "limit": 10,
            "window_seconds": 60,
            "algorithm": "sliding_window",
        },
        "supported_formats": ["image/jpeg", "image/png", "image/gif", "image/bmp"],
        "max_file_size": "10MB",
        "environment": ENVIRONMENT,
        "version": "2.0.0",
    }


if __name__ == "__main__":
    print(
        """
🎯 AI Image Analyzer API Ready!
===============================

FEATURES:
✅ Image upload and analysis
✅ Rate limiting (10 requests/minute)
✅ Azure integration ready
✅ CORS configured
✅ Enterprise error handling
✅ Health monitoring

ENDPOINTS:
- GET  /health           - Health check
- GET  /api/test         - Rate limit test
- GET  /api/status       - Rate limit status
- POST /api/analyze-image - Image analysis
- GET  /api/demo-info    - Demo information

🚀 Ready for Azure deployment!
    """
    )
