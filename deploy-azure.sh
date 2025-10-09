#!/bin/bash

# Azure Deployment Script for AI Image Analyzer
# Deploys full-stack application with infrastructure

set -euo pipefail

# Configuration
ENVIRONMENT="${1:-dev}"
LOCATION="${2:-eastus2}"
PROJECT_NAME="ai-image-analyzer"
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validation
validate_prerequisites() {
    log_info "Validating prerequisites..."

    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi

    # Check if logged in to Azure
    if ! az account show &> /dev/null; then
        log_error "Not logged in to Azure. Please run 'az login' first."
        exit 1
    fi

    # Check if subscription is set
    if [[ -z "$SUBSCRIPTION_ID" ]]; then
        SUBSCRIPTION_ID=$(az account show --query id -o tsv)
        log_warning "Using current subscription: $SUBSCRIPTION_ID"
    fi

    # Check if Bicep is available
    if ! az bicep version &> /dev/null; then
        log_info "Installing Bicep..."
        az bicep install
    fi

    log_success "Prerequisites validated"
}

# Deploy infrastructure
deploy_infrastructure() {
    log_info "Deploying infrastructure for environment: $ENVIRONMENT"

    local deployment_name="${PROJECT_NAME}-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
    local parameters_file="infrastructure/azure/main.${ENVIRONMENT}.bicepparam"

    if [[ ! -f "$parameters_file" ]]; then
        log_error "Parameters file not found: $parameters_file"
        exit 1
    fi

    log_info "Creating deployment: $deployment_name"

    # Deploy the Bicep template
    az deployment sub create \
        --name "$deployment_name" \
        --location "$LOCATION" \
        --template-file "infrastructure/azure/main.bicep" \
        --parameters "@$parameters_file" \
        --subscription "$SUBSCRIPTION_ID"

    if [[ $? -eq 0 ]]; then
        log_success "Infrastructure deployment completed"

        # Get deployment outputs
        local outputs
        outputs=$(az deployment sub show --name "$deployment_name" --query properties.outputs --subscription "$SUBSCRIPTION_ID")

        # Store outputs in environment file
        echo "# Azure Deployment Outputs - Generated $(date)" > ".env.azure.$ENVIRONMENT"
        echo "AZURE_RESOURCE_GROUP=$(echo "$outputs" | jq -r '.resourceGroupName.value')" >> ".env.azure.$ENVIRONMENT"
        echo "AZURE_BACKEND_URL=$(echo "$outputs" | jq -r '.backendUrl.value')" >> ".env.azure.$ENVIRONMENT"
        echo "AZURE_FRONTEND_URL=$(echo "$outputs" | jq -r '.frontendUrl.value')" >> ".env.azure.$ENVIRONMENT"
        echo "AZURE_APP_INSIGHTS_KEY=$(echo "$outputs" | jq -r '.applicationInsightsKey.value')" >> ".env.azure.$ENVIRONMENT"

        log_success "Outputs saved to .env.azure.$ENVIRONMENT"

        # Display key information
        echo ""
        log_info "Deployment Summary:"
        echo -e "  Resource Group: ${GREEN}$(echo "$outputs" | jq -r '.resourceGroupName.value')${NC}"
        echo -e "  Backend URL:    ${GREEN}$(echo "$outputs" | jq -r '.backendUrl.value')${NC}"
        echo -e "  Frontend URL:   ${GREEN}$(echo "$outputs" | jq -r '.frontendUrl.value')${NC}"
        echo ""

        return 0
    else
        log_error "Infrastructure deployment failed"
        return 1
    fi
}

# Deploy backend application
deploy_backend() {
    log_info "Deploying backend application..."

    if [[ ! -f ".env.azure.$ENVIRONMENT" ]]; then
        log_error "Environment file not found. Deploy infrastructure first."
        exit 1
    fi

    source ".env.azure.$ENVIRONMENT"

    local backend_app_name="${PROJECT_NAME}-${ENVIRONMENT}-backend"

    # Build and deploy backend
    log_info "Building backend application..."

    # Create deployment package
    zip -r backend-deploy.zip app/ requirements.txt startup.sh -x "**/__pycache__/*" "**/*.pyc"

    # Deploy to Azure App Service
    az webapp deployment source config-zip \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --name "$backend_app_name" \
        --src backend-deploy.zip

    # Clean up
    rm backend-deploy.zip

    log_success "Backend deployment completed"
}

# Deploy frontend application
deploy_frontend() {
    log_info "Deploying frontend application..."

    if [[ ! -f ".env.azure.$ENVIRONMENT" ]]; then
        log_error "Environment file not found. Deploy infrastructure first."
        exit 1
    fi

    source ".env.azure.$ENVIRONMENT"

    local frontend_app_name="${PROJECT_NAME}-${ENVIRONMENT}-frontend"

    # Build frontend
    log_info "Building frontend application..."
    cd frontend

    # Set environment variables for build
    export REACT_APP_BACKEND_URL="$AZURE_BACKEND_URL"
    export REACT_APP_ENVIRONMENT="$ENVIRONMENT"

    # Install dependencies and build
    npm install
    npm run build

    # Create deployment package
    cd build
    zip -r ../frontend-deploy.zip .
    cd ..

    # Deploy to Azure App Service
    az webapp deployment source config-zip \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --name "$frontend_app_name" \
        --src frontend-deploy.zip

    # Clean up
    rm frontend-deploy.zip
    cd ..

    log_success "Frontend deployment completed"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    if [[ ! -f ".env.azure.$ENVIRONMENT" ]]; then
        log_error "Environment file not found."
        exit 1
    fi

    source ".env.azure.$ENVIRONMENT"

    # Test backend health
    log_info "Testing backend health endpoint..."
    if curl -f -s "$AZURE_BACKEND_URL/health" > /dev/null; then
        log_success "Backend health check passed"
    else
        log_error "Backend health check failed"
        return 1
    fi

    # Test frontend
    log_info "Testing frontend availability..."
    if curl -f -s "$AZURE_FRONTEND_URL" > /dev/null; then
        log_success "Frontend availability check passed"
    else
        log_error "Frontend availability check failed"
        return 1
    fi

    log_success "All deployment verification checks passed"

    echo ""
    log_info "🚀 Deployment Complete! 🚀"
    echo -e "  Frontend: ${GREEN}$AZURE_FRONTEND_URL${NC}"
    echo -e "  Backend:  ${GREEN}$AZURE_BACKEND_URL${NC}"
    echo ""
}

# Main execution
main() {
    echo "=================================================="
    echo "  Azure Deployment - AI Image Analyzer"
    echo "  Environment: $ENVIRONMENT"
    echo "  Location: $LOCATION"
    echo "=================================================="
    echo ""

    validate_prerequisites

    if deploy_infrastructure; then
        deploy_backend
        deploy_frontend
        verify_deployment
    else
        log_error "Deployment failed at infrastructure stage"
        exit 1
    fi
}

# Help function
show_help() {
    echo "Usage: $0 [ENVIRONMENT] [LOCATION]"
    echo ""
    echo "Arguments:"
    echo "  ENVIRONMENT    Target environment (dev, staging, prod) [default: dev]"
    echo "  LOCATION       Azure region [default: eastus2]"
    echo ""
    echo "Environment Variables:"
    echo "  AZURE_SUBSCRIPTION_ID    Azure subscription ID (optional)"
    echo ""
    echo "Examples:"
    echo "  $0                      # Deploy to dev environment"
    echo "  $0 prod                 # Deploy to production"
    echo "  $0 dev westus2          # Deploy to dev in West US 2"
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
