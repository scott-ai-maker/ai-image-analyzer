#!/bin/bash

# Build script for frontend deployment

set -euo pipefail

echo "Building AI Image Analyzer Frontend..."

# Check if we're in the frontend directory
if [[ ! -f "package.json" ]]; then
    echo "Error: package.json not found. Make sure you're in the frontend directory."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Build the application
echo "Building React application..."
npm run build

echo "Frontend build completed successfully!"
echo "Build files are in the 'build' directory"
