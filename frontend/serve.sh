#!/bin/bash

# Enterprise AI Image Analyzer - Frontend Server
# Serves the demo frontend on port 3000

echo "🚀 Starting Enterprise AI Image Analyzer Frontend..."
echo "Frontend will be available at: http://localhost:3000"
echo "Backend API should be running at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "----------------------------------------"

cd "$(dirname "$0")"

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    python3 -m http.server 3000
elif command -v python &> /dev/null; then
    python -m http.server 3000
else
    echo "❌ Python not found. Please install Python to run the frontend server."
    exit 1
fi
