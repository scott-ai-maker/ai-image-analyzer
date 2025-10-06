"""Main FastAPI application for AI Image Analyzer."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from .routes import router as api_router
from ..core.config import settings
from ..models.schemas import AnalysisError, HealthStatus, ApiUsageStats


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.api.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Application state for metrics
app_state = {
    "start_time": time.time(),
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_processing_time": 0.0,
    "last_request_time": None
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI Image Analyzer service")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API host: {settings.api.host}:{settings.api.port}")
    
    # Validate Azure configuration
    if not settings.azure.computer_vision_endpoint:
        logger.error("Azure Computer Vision endpoint not configured!")
    else:
        logger.info(f"Azure Computer Vision endpoint: {settings.azure.computer_vision_endpoint}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Image Analyzer service")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="AI Image Analyzer",
        description="Enterprise-grade AI image analyzer with real-time object detection using Azure Computer Vision",
        version="0.1.0",
        contact={
            "name": "AI Engineering Team",
            "email": "engineering@company.com"
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        },
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Security middleware
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*.company.com"]
        )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["https://*.company.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    # Request middleware for metrics and logging
    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        """Middleware for request logging and metrics."""
        start_time = time.time()
        app_state["total_requests"] += 1
        app_state["last_request_time"] = start_time
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # Update success metrics
            if response.status_code < 400:
                app_state["successful_requests"] += 1
            else:
                app_state["failed_requests"] += 1
            
            processing_time = time.time() - start_time
            app_state["total_processing_time"] += processing_time
            
            # Log response
            logger.info(
                f"Response: {response.status_code} "
                f"({processing_time*1000:.2f}ms)"
            )
            
            # Add response headers
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
            response.headers["X-Request-ID"] = str(getattr(request.state, "request_id", "unknown"))
            
            return response
            
        except Exception as e:
            app_state["failed_requests"] += 1
            logger.error(f"Request failed: {str(e)}")
            
            # Return structured error response
            error_response = AnalysisError(
                error_code="INTERNAL_ERROR",
                error_message="An unexpected error occurred",
                details={"exception": str(e)}
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response.dict()
            )
    
    # Include API routes
    app.include_router(api_router)
    
    # Health check endpoint
    @app.get(
        "/health",
        response_model=HealthStatus,
        tags=["health"],
        summary="Health check",
        description="Check service health and dependencies"
    )
    async def health_check() -> HealthStatus:
        """Health check endpoint."""
        from ..services.computer_vision import ComputerVisionService
        
        # Check Computer Vision service
        cv_service = ComputerVisionService(settings)
        cv_health = await cv_service.health_check()
        await cv_service.close()
        
        dependencies = {
            "azure_computer_vision": cv_health
        }
        
        # Determine overall status
        overall_status = "healthy" if all(
            dep.get("status") == "healthy" for dep in dependencies.values()
        ) else "unhealthy"
        
        return HealthStatus(
            status=overall_status,
            version="0.1.0",
            dependencies=dependencies,
            uptime_seconds=time.time() - app_state["start_time"]
        )
    
    # Metrics endpoint
    @app.get(
        "/metrics",
        response_model=ApiUsageStats,
        tags=["monitoring"],
        summary="Usage metrics",
        description="Get API usage statistics"
    )
    async def get_metrics() -> ApiUsageStats:
        """Get API usage metrics."""
        total_requests = app_state["total_requests"]
        uptime = time.time() - app_state["start_time"]
        
        return ApiUsageStats(
            total_requests=total_requests,
            successful_requests=app_state["successful_requests"],
            failed_requests=app_state["failed_requests"],
            average_processing_time_ms=(
                (app_state["total_processing_time"] / max(total_requests, 1)) * 1000
            ),
            requests_per_minute=(total_requests / max(uptime / 60, 1)),
            last_request_timestamp=app_state["last_request_time"]
        )
    
    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="AI Image Analyzer API",
            version="0.1.0",
            description="""
# AI Image Analyzer API

Enterprise-grade AI image analyzer with real-time object detection using Azure Computer Vision.

## Features

- **Real-time object detection** on photos
- **Multiple input methods**: URL or file upload
- **Configurable confidence thresholds**
- **Comprehensive metadata** extraction
- **Enterprise security** with API key authentication
- **Monitoring and metrics** built-in

## Authentication

API key authentication is required for production environments.
Include your API key in the `Authorization` header:

```
Authorization: Bearer your-api-key-here
```

## Rate Limits

- Maximum image size: 10MB
- Maximum objects per request: 100
- Request timeout: 30 seconds

## Support

Contact the AI Engineering Team at engineering@company.com
            """,
            routes=app.routes,
        )
        
        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "description": "API key authentication"
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    return app


# Create application instance
app = create_app()