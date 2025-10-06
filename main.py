"""Application entry point."""

import uvicorn
from src.api.main import app
from src.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.api.log_level.lower(),
        access_log=True,
        server_header=False,  # Security: don't expose server info
        date_header=False,    # Security: don't expose date
    )