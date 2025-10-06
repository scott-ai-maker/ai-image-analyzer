# CI/CD Development Guide

This guide explains how to use the comprehensive CI/CD pipeline and development tools configured for the AI Image Analyzer project.

## Table of Contents
- [Quick Start](#quick-start)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Security](#security)
- [Performance](#performance)
- [CI/CD Pipeline](#cicd-pipeline)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Initial Setup
```bash
# Install development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run initial checks
pre-commit run --all-files
```

### Development Environment
```bash
# Activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Install project in development mode
pip install -e .[dev]
```

## Development Workflow

### 1. Pre-commit Hooks
Automated code quality checks run on every commit:
- **Ruff**: Fast Python linting and formatting
- **MyPy**: Type checking
- **Bandit**: Security scanning
- **YAML/JSON validation**
- **Markdown linting**
- **Docker file linting**

```bash
# Run manually
pre-commit run --all-files

# Skip hooks (use sparingly)
git commit -m "message" --no-verify
```

### 2. Code Formatting
Using Ruff (replaces Black, isort, and flake8):
```bash
# Format code
ruff format .

# Lint and auto-fix
ruff check . --fix

# Check without fixing
ruff check .
```

### 3. Type Checking
```bash
# Run MyPy type checking
mypy src/

# Check specific file
mypy src/services/computer_vision.py
```

## Testing

### Test Execution
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests

# Parallel execution
pytest -n auto          # Auto-detect CPU cores
pytest -n 4             # Use 4 processes
```

### Test Structure
```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Tests requiring external services
├── performance/    # Load and performance tests
└── security/       # Security-focused tests
```

### Test Markers
```python
import pytest

@pytest.mark.unit
def test_fast_function():
    pass

@pytest.mark.integration
def test_api_endpoint():
    pass

@pytest.mark.slow
def test_large_dataset():
    pass

@pytest.mark.security
def test_input_validation():
    pass
```

## Code Quality

### Coverage Reporting
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Generate XML for CI
pytest --cov=src --cov-report=xml

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=80
```

### Code Metrics
```bash
# Line count and complexity
ruff check . --statistics

# Security issues
bandit -r src/

# Dependency vulnerabilities
safety check

# Full security scan
semgrep --config=auto src/
```

## Security

### Dependency Scanning
```bash
# Check for known vulnerabilities
safety check

# Use policy file
safety check --policy-file .safety-policy.yml

# Include development dependencies
safety check --full-report
```

### Code Security
```bash
# Bandit security linting
bandit -r src/

# Use configuration file
bandit -r src/ -c .bandit

# Specific test IDs
bandit -r src/ -t B201,B301
```

### Container Security
```bash
# Scan Docker image
trivy image ai-image-analyzer:latest

# Scan filesystem
trivy fs .

# Use config file
trivy image --config .trivyignore ai-image-analyzer:latest
```

## Performance

### Load Testing with Locust
```bash
# Start web UI
locust -f locustfile.py --host=http://localhost:8000

# Headless mode
locust -f locustfile.py --host=http://localhost:8000 \
  --headless -u 50 -r 10 -t 300s

# Generate report
locust -f locustfile.py --host=http://localhost:8000 \
  --headless -u 100 -r 20 -t 600s --html=report.html
```

### Performance Testing
```bash
# Run performance tests
pytest -m performance

# With profiling
pytest -m performance --profile-svg

# Memory profiling
pytest -m performance --memray
```

## CI/CD Pipeline

### Pipeline Overview
The GitHub Actions workflow includes 6 main jobs:

1. **Test**: Multi-Python version testing (3.9-3.12)
2. **Security**: Bandit, Safety, and Semgrep scanning
3. **Docker**: Multi-architecture builds with Trivy scanning
4. **Integration**: End-to-end API testing
5. **Performance**: Load testing with Locust
6. **Deploy Validation**: Deployment readiness checks

### Pipeline Triggers
- **Push to main/develop**: Full pipeline
- **Pull requests**: Full pipeline
- **Tags (v*)**: Full pipeline + release creation
- **Manual**: Via workflow_dispatch

### Pipeline Secrets
Required GitHub secrets:
```
AZURE_COMPUTER_VISION_ENDPOINT
AZURE_COMPUTER_VISION_KEY
CODECOV_TOKEN
```

### Environment Variables
```bash
# Development
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG

# Testing  
export ENVIRONMENT=testing
export AZURE_COMPUTER_VISION_ENDPOINT=mock

# Production
export ENVIRONMENT=production
export LOG_LEVEL=INFO
```

### Deployment
```bash
# Build Docker image
docker build -t ai-image-analyzer:latest .

# Run locally
docker run -p 8000:8000 \
  -e AZURE_COMPUTER_VISION_ENDPOINT=$ENDPOINT \
  -e AZURE_COMPUTER_VISION_KEY=$KEY \
  ai-image-analyzer:latest

# Deploy to staging
docker tag ai-image-analyzer:latest \
  ghcr.io/username/ai-image-analyzer:staging
docker push ghcr.io/username/ai-image-analyzer:staging
```

## Troubleshooting

### Common Issues

#### Pre-commit Failures
```bash
# Update hooks
pre-commit autoupdate

# Clear cache
pre-commit clean

# Reinstall hooks
pre-commit uninstall
pre-commit install
```

#### Test Failures
```bash
# Verbose output
pytest -v --tb=long

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Debug mode
pytest --pdb
```

#### Docker Issues
```bash
# Build without cache
docker build --no-cache -t ai-image-analyzer:latest .

# Check image security
trivy image ai-image-analyzer:latest

# Debug container
docker run -it --entrypoint=/bin/bash ai-image-analyzer:latest
```

#### CI/CD Pipeline Issues
1. Check GitHub Actions logs
2. Verify secrets are set
3. Check branch protection rules
4. Validate workflow syntax

### Performance Issues
```bash
# Profile slow tests
pytest --durations=10

# Memory usage
pytest --memray

# CPU profiling
pytest --profile
```

### Security Issues
```bash
# Ignore specific vulnerability
echo "CVE-2021-12345" >> .trivyignore

# Update dependencies
pip-compile --upgrade requirements.in

# Security audit
pip-audit
```

## Configuration Files Reference

- `.pre-commit-config.yaml`: Pre-commit hooks configuration
- `.bandit`: Security scanning configuration  
- `.safety-policy.yml`: Dependency vulnerability policy
- `.trivyignore`: Container security scan configuration
- `pyproject.toml`: Project configuration, dependencies, and tool settings
- `locustfile.py`: Performance testing scenarios
- `.github/workflows/ci-cd.yml`: CI/CD pipeline definition

## Best Practices

1. **Always run tests locally** before pushing
2. **Use type hints** for better code quality
3. **Write descriptive commit messages**
4. **Keep dependencies updated**
5. **Monitor security vulnerabilities**
6. **Review coverage reports**
7. **Run performance tests** for critical changes
8. **Use feature branches** for development
9. **Squash commits** before merging
10. **Tag releases** with semantic versioning