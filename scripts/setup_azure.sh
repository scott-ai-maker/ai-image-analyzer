#!/bin/bash

# Azure Computer Vision Resource Setup Script
# This script automates the creation of Azure Computer Vision resources

set -e  # Exit on any error

# Configuration
RESOURCE_GROUP="ai-image-analyzer-rg"
COMPUTER_VISION_NAME="ai-image-analyzer-cv"
LOCATION="eastus"
PRICING_TIER="F0"  # Free tier, change to S1 for production

echo "🚀 Setting up Azure Computer Vision Resource"
echo "============================================="
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed."
    echo "Please install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

echo "✅ Azure CLI found"

# Login check
echo "🔄 Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
echo "✅ Logged in to Azure subscription: $SUBSCRIPTION_NAME"
echo ""

# Create resource group
echo "🔄 Creating resource group: $RESOURCE_GROUP"
if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    echo "✅ Resource group already exists"
else
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
    echo "✅ Resource group created successfully"
fi
echo ""

# Create Computer Vision resource
echo "🔄 Creating Computer Vision resource: $COMPUTER_VISION_NAME"
if az cognitiveservices account show --name "$COMPUTER_VISION_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "✅ Computer Vision resource already exists"
else
    az cognitiveservices account create \
        --name "$COMPUTER_VISION_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --kind ComputerVision \
        --sku "$PRICING_TIER" \
        --location "$LOCATION" \
        --yes
    echo "✅ Computer Vision resource created successfully"
fi
echo ""

# Get endpoint and key
echo "🔄 Retrieving connection details..."
ENDPOINT=$(az cognitiveservices account show \
    --name "$COMPUTER_VISION_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.endpoint" --output tsv)

KEY=$(az cognitiveservices account keys list \
    --name "$COMPUTER_VISION_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "key1" --output tsv)

echo "✅ Connection details retrieved"
echo ""

# Create .env file
echo "🔄 Creating .env file..."
cat > .env << EOF
# Azure Computer Vision Configuration
AZURE_COMPUTER_VISION_ENDPOINT=$ENDPOINT
AZURE_COMPUTER_VISION_KEY=$KEY

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development

# Server Configuration  
HOST=0.0.0.0
PORT=8000
EOF

echo "✅ .env file created successfully"
echo ""

# Display summary
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Resource Details:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Computer Vision: $COMPUTER_VISION_NAME"
echo "  Location: $LOCATION"
echo "  Pricing Tier: $PRICING_TIER"
echo ""
echo "Connection Details:"
echo "  Endpoint: $ENDPOINT"
echo "  Key: ${KEY:0:8}...${KEY: -4}"
echo ""
echo "Next Steps:"
echo "1. Test your connection: python scripts/test_azure_connection.py"
echo "2. Start your application: python -m uvicorn src.api.main:app --reload"
echo "3. View API docs at: http://localhost:8000/docs"
echo ""
echo "⚠️  Important Security Notes:"
echo "- Never commit the .env file to version control"
echo "- Consider using Azure Key Vault for production"
echo "- Monitor your usage to avoid unexpected charges"