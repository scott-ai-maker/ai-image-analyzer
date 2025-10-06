#!/bin/bash

# Development helper script for AI Image Analyzer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}==== $1 ====${NC}"
}

# Check if virtual environment exists
check_venv() {
    if [ ! -d "venv" ]; then
        print_warning "Virtual environment not found. Creating one..."
        python3 -m venv venv
        print_status "Virtual environment created"
    fi
}

# Activate virtual environment
activate_venv() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_status "Virtual environment activated"
    else
        print_error "Virtual environment not found"
        exit 1
    fi
}

# Install dependencies
install_deps() {
    print_header "Installing Dependencies"
    pip install --upgrade pip
    pip install -e ".[dev]"
    print_status "Dependencies installed"
}

# Run tests
run_tests() {
    print_header "Running Tests"
    pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing
    print_status "Tests completed"
}

# Run linting
run_lint() {
    print_header "Running Code Quality Checks"
    
    print_status "Running Black (formatter)..."
    black src/ tests/ --check || {
        print_warning "Code formatting issues found. Run 'black src/ tests/' to fix"
    }
    
    print_status "Running isort (import sorting)..."
    isort src/ tests/ --check-only || {
        print_warning "Import sorting issues found. Run 'isort src/ tests/' to fix"
    }
    
    print_status "Running flake8 (linting)..."
    flake8 src/ tests/
    
    print_status "Running mypy (type checking)..."
    mypy src/
    
    print_status "Running bandit (security)..."
    bandit -r src/ -ll
    
    print_status "Code quality checks completed"
}

# Fix code formatting
fix_format() {
    print_header "Fixing Code Formatting"
    black src/ tests/
    isort src/ tests/
    print_status "Code formatting fixed"
}

# Start development server
start_dev() {
    print_header "Starting Development Server"
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Copying from .env.example..."
        cp .env.example .env
        print_warning "Please update .env with your Azure credentials"
    fi
    
    # Start server
    python main.py
}

# Build Docker image
build_docker() {
    print_header "Building Docker Image"
    docker build -t ai-image-analyzer:latest .
    print_status "Docker image built successfully"
}

# Run Docker container
run_docker() {
    print_header "Running Docker Container"
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        print_error ".env file required for Docker. Copy from .env.example and configure"
        exit 1
    fi
    
    docker run --rm -p 8000:8000 --env-file .env ai-image-analyzer:latest
}

# Show help
show_help() {
    echo "AI Image Analyzer Development Helper"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup       - Set up development environment"
    echo "  install     - Install dependencies"
    echo "  test        - Run tests with coverage"
    echo "  lint        - Run code quality checks"
    echo "  format      - Fix code formatting"
    echo "  dev         - Start development server"
    echo "  docker-build - Build Docker image"
    echo "  docker-run  - Run Docker container"
    echo "  help        - Show this help"
    echo ""
}

# Main script logic
case "${1:-}" in
    setup)
        check_venv
        activate_venv
        install_deps
        print_status "Setup completed! Run './dev.sh dev' to start development server"
        ;;
    install)
        activate_venv
        install_deps
        ;;
    test)
        activate_venv
        run_tests
        ;;
    lint)
        activate_venv
        run_lint
        ;;
    format)
        activate_venv
        fix_format
        ;;
    dev)
        activate_venv
        start_dev
        ;;
    docker-build)
        build_docker
        ;;
    docker-run)
        run_docker
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        print_error "No command specified"
        show_help
        exit 1
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac