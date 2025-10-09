#!/bin/bash

# Cleanup script for Azure resources
# Use this to clean up all resources when done with testing

set -e

# Configuration
RESOURCE_GROUP="rg-ai-image-analyzer-prod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}❌ ERROR:${NC} $1"
}

# Confirm deletion
echo "🗑️  Azure Resource Cleanup"
echo "=========================="
echo ""
log_warning "This will DELETE the entire resource group: $RESOURCE_GROUP"
log_warning "This action cannot be undone!"
echo ""
echo "Resources that will be deleted:"
echo "  - Resource Group: $RESOURCE_GROUP"
echo "  - All Container Apps"
echo "  - Container Registry and images"
echo "  - Key Vault and all secrets"
echo "  - Log Analytics workspace"
echo "  - All networking resources"
echo ""

read -p "Are you sure you want to continue? Type 'DELETE' to confirm: " confirm

if [ "$confirm" != "DELETE" ]; then
    log_info "Cleanup cancelled"
    exit 0
fi

echo ""
log_info "Starting cleanup process..."

# Check if resource group exists
if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    log_info "Deleting resource group: $RESOURCE_GROUP"

    # Delete the entire resource group (this deletes all resources in it)
    az group delete \
        --name "$RESOURCE_GROUP" \
        --yes \
        --no-wait

    log_success "Deletion initiated for resource group: $RESOURCE_GROUP"
    log_info "Deletion is running in the background. It may take several minutes to complete."
    log_info "You can check the status in the Azure portal or run: az group show --name $RESOURCE_GROUP"
else
    log_warning "Resource group $RESOURCE_GROUP does not exist or has already been deleted"
fi

echo ""
log_success "Cleanup script completed!"
echo ""
echo "💰 Cost Savings:"
echo "  - All Azure resources have been deleted"
echo "  - No further charges will be incurred"
echo "  - You can redeploy anytime using ./deployment/azure/deploy.sh"
