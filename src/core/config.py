"""Configuration management using Pydantic Settings."""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class AzureConfig(BaseSettings):
    """Azure Computer Vision configuration."""

    computer_vision_endpoint: str = Field(
        default="https://demo.cognitiveservices.azure.com/",
        description="Azure Computer Vision endpoint URL",
    )
    computer_vision_key: Optional[str] = Field(
        None, description="Azure Computer Vision subscription key"
    )
    client_id: Optional[str] = Field(
        None, description="Managed identity client ID (alternative to key)"
    )

    @validator("computer_vision_endpoint")
    def validate_endpoint(cls, v):
        """Ensure endpoint is properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must be a valid URL")
        return v.rstrip("/")

    class Config:
        """Pydantic settings configuration."""

        env_prefix = "AZURE_"
        case_sensitive = False


class ApiConfig(BaseSettings):
    """API server configuration."""

    host: str = Field(default="0.0.0.0", description="API host address")
    port: int = Field(default=8000, ge=1024, le=65535, description="API port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    log_level: str = Field(default="INFO", description="Logging level")

    # Security
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    api_keys: List[str] = Field(default_factory=list, description="Valid API keys")

    # Performance
    max_image_size_mb: int = Field(
        default=10, ge=1, le=100, description="Max image size"
    )
    concurrent_requests: int = Field(
        default=100, ge=1, description="Max concurrent requests"
    )
    request_timeout_seconds: int = Field(
        default=30, ge=1, description="Request timeout"
    )

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(
        default=9090, ge=1024, le=65535, description="Metrics port"
    )

    @validator("api_keys", pre=True)
    def parse_api_keys(cls, v):
        """Parse comma-separated API keys."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v or []

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    class Config:
        """Pydantic settings configuration."""

        env_prefix = "API_"
        case_sensitive = False


class Settings(BaseSettings):
    """Application settings combining all configuration sections."""

    # Environment
    environment: str = Field(
        default="development", description="Deployment environment"
    )
    debug: bool = Field(default=True, description="Enable debug mode")

    # Azure Configuration
    azure_computer_vision_endpoint: str = Field(
        default="https://demo.cognitiveservices.azure.com/",
        description="Azure Computer Vision endpoint URL",
    )
    azure_computer_vision_key: Optional[str] = Field(
        default=None, description="Azure Computer Vision subscription key"
    )
    azure_client_id: Optional[str] = Field(
        default=None, description="Managed identity client ID (alternative to key)"
    )
    azure_cv_api_version: str = Field(
        default="2023-10-01", description="Azure Computer Vision API version"
    )
    azure_max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts for Azure API calls"
    )
    azure_retry_delay: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Retry delay in seconds"
    )
    azure_request_timeout: int = Field(
        default=30, ge=5, le=300, description="Request timeout for Azure API calls"
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, ge=1024, le=65535, description="Server port")
    server_name: str = Field(default="AI Image Analyzer", description="Server name")
    api_version: str = Field(default="1.0.0", description="API version")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    log_level: str = Field(default="INFO", description="Logging level")

    # CORS Configuration
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed origins for CORS",
    )

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT tokens",
    )
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    api_keys: List[str] = Field(default_factory=list, description="Valid API keys")
    max_request_size: int = Field(
        default=10485760,
        ge=1048576,
        le=104857600,
        description="Maximum request size in bytes",
    )
    request_timeout: int = Field(
        default=30, ge=1, le=300, description="Request timeout"
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=60, ge=1, le=10000, description="Requests per minute per IP"
    )

    # Performance
    max_image_size_mb: int = Field(
        default=10, ge=1, le=100, description="Max image size"
    )
    concurrent_requests: int = Field(
        default=100, ge=1, description="Max concurrent requests"
    )

    # Monitoring and Health
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(
        default=9090, ge=1024, le=65535, description="Metrics port"
    )
    health_check_timeout: int = Field(
        default=30, ge=5, le=300, description="Health check timeout in seconds"
    )
    metrics_interval: int = Field(
        default=60, ge=10, le=3600, description="Metrics collection interval in seconds"
    )

    @property
    def azure(self):
        """Get Azure configuration."""
        return type(
            "AzureConfig",
            (),
            {
                "computer_vision_endpoint": self.azure_computer_vision_endpoint,
                "computer_vision_key": self.azure_computer_vision_key,
                "client_id": self.azure_client_id,
            },
        )()

    @property
    def api(self):
        """Get API configuration."""
        return type(
            "ApiConfig",
            (),
            {
                "host": self.host,
                "port": self.port,
                "reload": self.reload,
                "log_level": self.log_level,
                "api_key_header": self.api_key_header,
                "api_keys": self.api_keys,
                "max_image_size_mb": self.max_image_size_mb,
                "concurrent_requests": self.concurrent_requests,
                "request_timeout": self.request_timeout,
                "enable_metrics": self.enable_metrics,
                "metrics_port": self.metrics_port,
            },
        )()

    @validator("azure_computer_vision_endpoint")
    def validate_azure_endpoint(cls, v):
        """Ensure Azure endpoint is properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Azure endpoint must be a valid URL")
        return v.rstrip("/")

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or []

    @validator("api_keys", pre=True)
    def parse_api_keys(cls, v):
        """Parse comma-separated API keys."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v or []

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_envs = ["development", "testing", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v

    @validator("secret_key")
    def validate_secret_key(cls, v, values):
        """Validate secret key security in production."""
        environment = values.get("environment", "development")
        
        if (
            environment == "production"
            and v == "dev-secret-key-change-in-production"
        ):
            raise ValueError("Secret key must be changed for production deployment")
        
        # Relaxed requirements for testing environment
        if environment == "testing":
            return v
            
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
