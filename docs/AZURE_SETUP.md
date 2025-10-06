# Azure Computer Vision Setup Guide

## Prerequisites
- Azure subscription (free tier available)
- Azure CLI installed locally
- Owner or Contributor permissions on the subscription

## Step 1: Create Azure Computer Vision Resource

### Option A: Using Azure Portal (Recommended for beginners)

1. **Sign in to Azure Portal**
   - Go to https://portal.azure.com
   - Sign in with your Azure account

2. **Create Computer Vision Resource**
   - Click "Create a resource"
   - Search for "Computer Vision"
   - Click "Computer Vision" by Microsoft
   - Click "Create"

3. **Configure the Resource**
   ```
   Subscription: [Your subscription]
   Resource Group: [Create new] ai-image-analyzer-rg
   Region: East US (or closest to you)
   Name: ai-image-analyzer-cv
   Pricing Tier: F0 (Free) or S1 (Standard)
   ```

4. **Review and Create**
   - Click "Review + create"
   - Click "Create"
   - Wait for deployment to complete

5. **Get Keys and Endpoint**
   - Go to your resource
   - Click "Keys and Endpoint" in the left menu
   - Copy Key 1 and Endpoint URL

### Option B: Using Azure CLI (Faster for experienced users)

```bash
# Login to Azure
az login

# Create resource group
az group create --name ai-image-analyzer-rg --location eastus

# Create Computer Vision resource
az cognitiveservices account create \
  --name ai-image-analyzer-cv \
  --resource-group ai-image-analyzer-rg \
  --kind ComputerVision \
  --sku F0 \
  --location eastus \
  --yes

# Get endpoint and keys
az cognitiveservices account show \
  --name ai-image-analyzer-cv \
  --resource-group ai-image-analyzer-rg \
  --query "properties.endpoint" --output tsv

az cognitiveservices account keys list \
  --name ai-image-analyzer-cv \
  --resource-group ai-image-analyzer-rg \
  --query "key1" --output tsv
```

## Step 2: Configure Environment Variables

Create a `.env` file in your project root:

```bash
# Azure Computer Vision
AZURE_COMPUTER_VISION_ENDPOINT=https://your-resource-name.cognitiveservices.azure.com/
AZURE_COMPUTER_VISION_KEY=your-32-character-key-here

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## Step 3: Test the Connection

Run the test script to verify everything works:

```bash
# From your project root
python scripts/test_azure_connection.py
```

## Pricing Information

### Free Tier (F0)
- 20 calls per minute
- 5,000 calls per month
- Perfect for development and testing

### Standard Tier (S1)
- 10 calls per second
- Pay per transaction
- Required for production workloads

## Security Best Practices

1. **Never commit credentials to version control**
2. **Use Azure Key Vault for production secrets**
3. **Rotate keys regularly (every 90 days)**
4. **Use managed identities when possible**
5. **Monitor usage and set up billing alerts**

## Troubleshooting

### Common Issues
- **Invalid key**: Ensure you copied the full 32-character key
- **Wrong endpoint**: Must include the full URL with protocol
- **Rate limiting**: Free tier has strict limits
- **Region mismatch**: Ensure endpoint matches resource region

### Test Commands
```bash
# Test endpoint connectivity
curl -H "Ocp-Apim-Subscription-Key: YOUR_KEY" \
     "YOUR_ENDPOINT/vision/v3.2/analyze?visualFeatures=Objects"

# Check Azure CLI connection
az account show
```