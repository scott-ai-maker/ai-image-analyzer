# Azure Deployment Guide - AI Image Analyzer

## 🚀 Complete Full-Stack Azure Deployment

This guide covers deploying the AI Image Analyzer as a complete enterprise solution on Azure with infrastructure as code, monitoring, and CI/CD.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Azure Subscription                         │
├─────────────────────────────────────────────────────────────────┤
│  Resource Group: ai-image-analyzer-{env}-rg                    │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Frontend      │  │    Backend      │  │   Monitoring    │ │
│  │   App Service   │  │   App Service   │  │                 │ │
│  │   (React)       │  │   (FastAPI)     │  │ App Insights    │ │
│  │                 │  │                 │  │ Log Analytics   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  App Service    │  │    Storage      │                     │
│  │     Plan        │  │   Account       │                     │
│  │   (Shared)      │  │  (Images)       │                     │
│  └─────────────────┘  └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Azure Setup

1. **Azure CLI**: Install and login

   ```bash
   # Install Azure CLI (if not installed)
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

   # Login
   az login

   # Set subscription (if you have multiple)
   az account set --subscription "your-subscription-id"
   ```

2. **Required Permissions**:
   - Contributor role on the subscription
   - Ability to create resource groups
   - Ability to create App Services and storage accounts

### Local Development Setup

1. **Node.js 18+** for frontend
2. **Python 3.11+** for backend
3. **Git** for version control

## 🏗️ Infrastructure as Code (Bicep)

### Files Structure

```
infrastructure/azure/
├── main.bicep                 # Main template (subscription scope)
├── main.dev.bicepparam       # Development parameters
├── main.prod.bicepparam      # Production parameters
└── modules/
    └── infrastructure.bicep   # Core resources module
```

### Resources Created

- **Resource Group**: Container for all resources
- **App Service Plan**: Linux-based, shared between apps
- **Backend App Service**: Python 3.11 runtime
- **Frontend App Service**: Node.js 18 runtime
- **Application Insights**: Monitoring and analytics
- **Log Analytics Workspace**: Centralized logging
- **Storage Account**: File storage for images

## 🔧 Deployment Options

### Option 1: Automated Script Deployment

```bash
# Deploy to development
./deploy-azure.sh dev

# Deploy to production
./deploy-azure.sh prod eastus2
```

### Option 2: Manual Bicep Deployment

```bash
# Deploy infrastructure
az deployment sub create \
  --name "ai-image-analyzer-dev-$(date +%Y%m%d)" \
  --location "East US 2" \
  --template-file "infrastructure/azure/main.bicep" \
  --parameters "@infrastructure/azure/main.dev.bicepparam"

# Get deployment outputs
az deployment sub show \
  --name "ai-image-analyzer-dev-$(date +%Y%m%d)" \
  --query properties.outputs
```

### Option 3: GitHub Actions CI/CD

1. **Setup GitHub Secrets**:

   ```
   AZURE_CREDENTIALS: Service principal JSON
   AZURE_SUBSCRIPTION_ID: Your subscription ID
   ```

2. **Trigger Deployment**:
   - Push to `main` branch
   - Or use manual workflow dispatch

## 🔐 Security Configuration

### App Service Security

- HTTPS only enforced
- TLS 1.2 minimum
- FTPS disabled
- System-assigned managed identity

### CORS Configuration

```python
# Automatically configured origins:
- Production frontend URL
- Development localhost:3000
- Development localhost:5173
```

### Rate Limiting

- 10 requests per minute per IP
- Sliding window algorithm
- HTTP 429 responses for violations

## 📊 Monitoring & Observability

### Application Insights Features

- **Request telemetry**: All API calls tracked
- **Dependency tracking**: External service calls
- **Exception tracking**: Automatic error capture
- **Custom metrics**: Business-specific metrics
- **Live metrics**: Real-time performance

### Key Metrics Tracked

```python
# Custom dimensions logged:
- Image analysis: file_size, processing_time, objects_count
- Health checks: cpu_percent, memory_percent, active_users
- Rate limiting: violations, user patterns
- Errors: error types, processing failures
```

### Log Analytics Queries

```kusto
# Image analysis performance
requests
| where name == "POST /api/analyze-image"
| summarize avg(duration), count() by bin(timestamp, 1h)

# Rate limiting violations
requests
| where resultCode == 429
| summarize count() by bin(timestamp, 5m), client_IP

# System health trends
customMetrics
| where name in ("cpu_percent", "memory_percent")
| render timechart
```

## 🌐 Frontend Features

### React Application Capabilities

- **Image Upload**: Drag & drop + file picker
- **Real-time Analysis**: Instant API calls
- **Rate Limit Demo**: Interactive testing
- **Responsive Design**: Mobile-friendly
- **Error Handling**: User-friendly messages
- **Azure Integration**: Environment-aware

### Environment Configuration

```javascript
// Automatic backend URL detection:
- Production: Uses REACT_APP_BACKEND_URL
- Development: Proxies to localhost:8000
```

## 🔧 Backend API Endpoints

### Core Endpoints

```
GET  /health              # System health + metrics
GET  /api/test            # Rate limiting test
GET  /api/status          # Rate limit status
POST /api/analyze-image   # Image analysis (with rate limiting)
GET  /api/demo-info       # Demo capabilities info
GET  /docs                # Swagger UI (dev only)
```

### Example Responses

```json
// Image Analysis Response
{
  "filename": "example.jpg",
  "file_size": 245760,
  "content_type": "image/jpeg",
  "analysis": {
    "objects_detected": ["person", "car", "building"],
    "confidence_scores": [0.95, 0.87, 0.92],
    "description": "This image contains...",
    "faces_detected": 1
  },
  "metadata": {
    "processing_time_ms": 245,
    "model_version": "2.0.0"
  }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Deployment Fails**:

   ```bash
   # Check Bicep syntax
   az bicep build --file infrastructure/azure/main.bicep

   # Validate template
   az deployment sub validate \
     --location "East US 2" \
     --template-file "infrastructure/azure/main.bicep" \
     --parameters "@infrastructure/azure/main.dev.bicepparam"
   ```

2. **App Won't Start**:

   ```bash
   # Check app logs
   az webapp log tail --name ai-image-analyzer-dev-backend --resource-group ai-image-analyzer-dev-rg

   # Check app settings
   az webapp config appsettings list --name ai-image-analyzer-dev-backend --resource-group ai-image-analyzer-dev-rg
   ```

3. **CORS Issues**:
   - Verify frontend URL in backend environment variables
   - Check Azure App Service CORS settings
   - Ensure both apps are using HTTPS

4. **Rate Limiting Not Working**:
   - Check if middleware is properly configured
   - Verify IP addresses are being captured correctly
   - Test with curl commands

### Monitoring Health

```bash
# Backend health
curl https://ai-image-analyzer-dev-backend.azurewebsites.net/health

# Frontend availability
curl https://ai-image-analyzer-dev-frontend.azurewebsites.net

# Rate limiting test
for i in {1..15}; do curl https://ai-image-analyzer-dev-backend.azurewebsites.net/api/test; done
```

## 💰 Cost Optimization

### Development Environment

- **App Service Plan**: Basic B1 (~$13/month)
- **Storage Account**: Standard LRS (~$2/month)
- **Application Insights**: First 5GB free
- **Total**: ~$15/month

### Production Environment

- **App Service Plan**: Premium P1v3 (~$70/month)
- **Storage Account**: Standard LRS (~$5/month)
- **Application Insights**: Pay per GB ingested
- **Total**: ~$75-100/month

### Cost Saving Tips

1. Use **Basic tier** for development
2. Enable **auto-scaling** only when needed
3. Set **retention policies** for logs
4. Use **Azure Dev/Test pricing** if eligible

## 🚀 Demo Script

After deployment, use this script to demonstrate capabilities:

```bash
# Source the environment variables
source .env.azure.prod

# Test backend health
echo "Testing backend health..."
curl -s $AZURE_BACKEND_URL/health | jq .

# Test rate limiting
echo "Testing rate limiting..."
for i in {1..12}; do
  echo "Request $i:"
  curl -s $AZURE_BACKEND_URL/api/test | jq .message
done

# Open frontend in browser
echo "Opening frontend: $AZURE_FRONTEND_URL"
open $AZURE_FRONTEND_URL  # macOS
# xdg-open $AZURE_FRONTEND_URL  # Linux
```

## 📈 Scaling Considerations

### Horizontal Scaling

- App Service Plan supports auto-scaling
- Configure based on CPU/memory metrics
- Scale out during peak hours

### Performance Optimization

- Enable **Application Insights Profiler**
- Use **Azure CDN** for frontend assets
- Implement **Redis Cache** for rate limiting
- Add **Azure SQL Database** for persistence

## 🔄 CI/CD Pipeline Features

### GitHub Actions Workflow

- **Multi-stage deployment**: Infrastructure → Backend → Frontend
- **Environment promotion**: dev → staging → prod
- **Health checks**: Automated verification
- **Rollback capability**: Easy revert on failure

### Pipeline Stages

1. **Build & Test**: Unit tests, linting, security scans
2. **Infrastructure**: Bicep template deployment
3. **Backend Deployment**: Python app with dependencies
4. **Frontend Deployment**: React build artifacts
5. **Health Verification**: End-to-end testing
6. **Monitoring Setup**: Alerts and dashboards

This comprehensive setup provides an enterprise-grade, scalable, and monitored solution suitable for production workloads and impressive demo presentations.

## 🎯 Next Steps

1. **Deploy infrastructure**: Run `./deploy-azure.sh dev`
2. **Test locally**: Verify frontend connects to Azure backend
3. **Set up monitoring**: Configure alerts in Application Insights
4. **Demo preparation**: Test all features work end-to-end
5. **Production deployment**: Use production parameters for final deployment
