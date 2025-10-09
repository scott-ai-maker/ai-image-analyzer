#!/bin/bash

# Startup script for Azure App Service - AI Image Analyzer Backend

echo "Starting AI Image Analyzer Backend..."

# Set default port for Azure App Service
export PORT=${PORT:-8000}

# Start the application with Gunicorn for production
echo "Starting Gunicorn server on port $PORT..."
exec gunicorn app.main:app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 60 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile -
