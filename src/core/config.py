"""Configuration management using Pydantic Settings."""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class AzureConfig(BaseSettings):
    """Azure Computer Vision configuration."""
    
    computer_vision_endpoint: str = Field(
        default="https://demo.cognitiveservices.azure.com/", 
        description="Azure Computer Vision endpoint URL"
    )
    computer_vision_key: Optional[str] = Field(
        None, 
        description="Azure Computer Vision subscription key"
    )
    client_id: Optional[str] = Field(
        None, 
        description="Managed identity client ID (alternative to key)"
    )
    
    @validator('computer_vision_endpoint')
    def validate_endpoint(cls, v):
        """Ensure endpoint is properly formatted."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Endpoint must be a valid URL")
        return v.rstrip('/')

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
    max_image_size_mb: int = Field(default=10, ge=1, le=100, description="Max image size")
    concurrent_requests: int = Field(default=100, ge=1, description="Max concurrent requests")
    request_timeout_seconds: int = Field(default=30, ge=1, description="Request timeout")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, ge=1024, le=65535, description="Metrics port")

    @validator('api_keys', pre=True)
    def parse_api_keys(cls, v):
        """Parse comma-separated API keys."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(',') if key.strip()]
        return v or []

    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
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
    environment: str = Field(default="development", description="Deployment environment")
    debug: bool = Field(default=True, description="Enable debug mode")
    
    # Azure Configuration
    azure_computer_vision_endpoint: str = Field(
        default="https://demo.cognitiveservices.azure.com/", 
        description="Azure Computer Vision endpoint URL"
    )
    azure_computer_vision_key: Optional[str] = Field(
        default=None, 
        description="Azure Computer Vision subscription key"
    )
    azure_client_id: Optional[str] = Field(
        default=None, 
        description="Managed identity client ID (alternative to key)"
    )
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=8000, ge=1024, le=65535, description="API port")
    api_reload: bool = Field(default=False, description="Enable auto-reload in development")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Security
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    api_keys: List[str] = Field(default_factory=list, description="Valid API keys")
    
    # Performance
    max_image_size_mb: int = Field(default=10, ge=1, le=100, description="Max image size")
    concurrent_requests: int = Field(default=100, ge=1, description="Max concurrent requests")
    request_timeout_seconds: int = Field(default=30, ge=1, description="Request timeout")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, ge=1024, le=65535, description="Metrics port")
    
    @property
    def azure(self):
        """Get Azure configuration."""
        return type('AzureConfig', (), {
            'computer_vision_endpoint': self.azure_computer_vision_endpoint,
            'computer_vision_key': self.azure_computer_vision_key,
            'client_id': self.azure_client_id
        })()
    
    @property 
    def api(self):
        """Get API configuration."""
        return type('ApiConfig', (), {
            'host': self.api_host,
            'port': self.api_port,
            'reload': self.api_reload,
            'log_level': self.log_level,
            'api_key_header': self.api_key_header,
            'api_keys': self.api_keys,
            'max_image_size_mb': self.max_image_size_mb,
            'concurrent_requests': self.concurrent_requests,
            'request_timeout_seconds': self.request_timeout_seconds,
            'enable_metrics': self.enable_metrics,
            'metrics_port': self.metrics_port
        })()

    @validator('api_keys', pre=True)
    def parse_api_keys(cls, v):
        """Parse comma-separated API keys."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(',') if key.strip()]
        return v or []

    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_envs = ['development', 'staging', 'production']
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v

    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()