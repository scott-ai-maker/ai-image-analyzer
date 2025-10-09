# Azure Deployment Guide - Enterprise AI Image Analyzer

## 🎯 Overview

This guide provides a complete Azure deployment solution for the Enterprise AI Image Analyzer, implementing production-ready patterns with enterprise security and scalability.

## 🏗️ Architecture

```
┌─────────────────────┐    ┌─────────────────────┐
│   Azure Front Door  │────│  Container Apps     │
│   (CDN + WAF)      │    │  Environment        │
└─────────────────────┘    └─────────────────────┘
                                      │
                           ┌──────────┼──────────┐
                           │          │          │
                    ┌──────▼────┐ ┌──▼────┐ ┌──▼────┐
                    │ Frontend  │ │Backend│ │ ...   │
                    │Container  │ │ API   │ │       │
                    │   App     │ │ App   │ │       │
                    └───────────┘ └───┬───┘ └───────┘
                                      │
                           ┌──────────┼──────────┐
                           │          │          │
                    ┌──────▼────┐ ┌──▼────┐ ┌──▼────┐
                    │Azure Key  │ │  ACR  │ │ Log   │
                    │  Vault    │ │       │ │Analytics│
                    └───────────┘ └───────┘ └───────┘
```

## 🔐 Security Features

### Secrets Management

- **Azure Key Vault**: All secrets stored securely
- **Managed Identity**: No hardcoded credentials
- **RBAC**: Role-based access control
- **Key rotation**: Automated secret rotation support

### Container Security

- **Non-root users**: All containers run as non-root
- **Multi-stage builds**: Minimal attack surface
- **Image scanning**: Azure Defender integration
- **Network isolation**: Private networking

### Application Security

- **HTTPS only**: Managed SSL certificates
- **CORS protection**: Configured for production
- **Rate limiting**: API abuse prevention
- **Security headers**: OWASP recommendations

## 🚀 Deployment Instructions

### Prerequisites

1. **Azure CLI** installed and logged in:

   ```bash
   az login
   az account set --subscription "your-subscription-id"
   ```

2. **Docker** installed and running

3. **Permissions**: Contributor role on the subscription

### Quick Deployment

```bash
# Make the script executable
chmod +x deployment/azure/deploy.sh

# Run the deployment
./deployment/azure/deploy.sh
```

### Manual Step-by-Step Deployment

1. **Set up infrastructure**:

   ```bash
   # Create resource group
   az group create --name rg-ai-image-analyzer-prod --location eastus2

   # Create Key Vault
   az keyvault create --name kv-image-analyzer-prod --resource-group rg-ai-image-analyzer-prod
   ```

2. **Build and push images**:

   ```bash
   # Login to ACR
   az acr login --name acrimageanalyzerprod

   # Build and push backend
   docker build -t acrimageanalyzerprod.azurecr.io/backend:latest -f deployment/docker/Dockerfile.backend .
   docker push acrimageanalyzerprod.azurecr.io/backend:latest

   # Build and push frontend
   docker build -t acrimageanalyzerprod.azurecr.io/frontend:latest -f deployment/docker/Dockerfile.frontend .
   docker push acrimageanalyzerprod.azurecr.io/frontend:latest
   ```

3. **Deploy applications**:

   ```bash
   # Deploy backend
   az containerapp create --name api-image-analyzer --resource-group rg-ai-image-analyzer-prod --environment cae-image-analyzer-prod --image acrimageanalyzerprod.azurecr.io/backend:latest

   # Deploy frontend
   az containerapp create --name web-image-analyzer --resource-group rg-ai-image-analyzer-prod --environment cae-image-analyzer-prod --image acrimageanalyzerprod.azurecr.io/frontend:latest
   ```

## 📊 Production Configuration

### Auto-scaling Settings

- **Backend**: 1-10 replicas based on CPU/memory
- **Frontend**: 1-5 replicas based on HTTP requests
- **Scale triggers**: CPU > 70%, Memory > 80%

### Resource Limits

```yaml
Backend:
  CPU: 0.5 vCPU
  Memory: 1 GB
  Storage: 2 GB

Frontend:
  CPU: 0.25 vCPU
  Memory: 0.5 GB
  Storage: 1 GB
```

### Monitoring & Logging

- **Application Insights**: Performance monitoring
- **Log Analytics**: Centralized logging
- **Azure Monitor**: Alerts and dashboards
- **Health checks**: Kubernetes-style probes

## 🔧 Configuration Management

### Environment Variables

```bash
# Backend Configuration
ENVIRONMENT=production
JWT_SECRET_KEY=<from-key-vault>
API_KEY=<from-key-vault>
RATE_LIMIT_PER_MINUTE=100
AZURE_KEY_VAULT_URL=https://kv-image-analyzer-prod.vault.azure.net/

# Frontend Configuration
BACKEND_URL=https://api-image-analyzer.azurecontainerapps.io
```

### Key Vault Secrets

```
jwt-secret-key: <auto-generated-32-byte-key>
api-key: <auto-generated-hex-key>
environment: production
rate-limit-per-minute: 100
acr-server: acrimageanalyzerprod.azurecr.io
acr-username: <acr-username>
acr-password: <acr-password>
backend-url: https://api-image-analyzer.azurecontainerapps.io
```

## 🧪 Testing Your Deployment

### Health Checks

```bash
# Backend health
curl https://api-image-analyzer-[random].azurecontainerapps.io/health

# Frontend health
curl https://web-image-analyzer-[random].azurecontainerapps.io/health
```

### API Testing

```bash
# Test rate limiting
for i in {1..15}; do
  curl -X GET "https://api-image-analyzer-[random].azurecontainerapps.io/api/test"
  echo "Request $i completed"
done
```

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Run load test
ab -n 1000 -c 10 https://api-image-analyzer-[random].azurecontainerapps.io/health
```

## 💰 Cost Management

### Estimated Monthly Costs (East US 2)

- **Container Apps**: $50-200/month (based on usage)
- **Container Registry**: $5-20/month
- **Key Vault**: $1-5/month
- **Log Analytics**: $10-50/month
- **Total**: ~$66-275/month

### Cost Optimization Tips

1. **Scale to zero**: Configure minimum replicas = 0 for dev environments
2. **Resource sizing**: Monitor and adjust CPU/memory limits
3. **Image optimization**: Use minimal base images
4. **Log retention**: Configure appropriate retention periods

## 🔄 CI/CD Integration

### GitHub Actions

The deployment includes a GitHub Actions workflow for automated deployment:

```yaml
# .github/workflows/azure-deploy.yml
name: Deploy to Azure
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Azure
        run: ./deployment/azure/deploy.sh
```

### Azure DevOps

For Azure DevOps integration, use the provided ARM templates and deployment scripts.

## 🛡️ Security Checklist

- [ ] **Secrets**: All secrets in Key Vault
- [ ] **Identity**: Managed Identity configured
- [ ] **Network**: Private endpoints enabled
- [ ] **SSL/TLS**: HTTPS enforced
- [ ] **CORS**: Properly configured
- [ ] **Headers**: Security headers set
- [ ] **Scanning**: Container image scanning enabled
- [ ] **Monitoring**: Security alerts configured

## 🗑️ Cleanup

When you're done testing, clean up resources to avoid charges:

```bash
# Run the cleanup script
./deployment/azure/cleanup.sh

# Or manually delete the resource group
az group delete --name rg-ai-image-analyzer-prod --yes
```

## 📞 Support

### Troubleshooting

1. **Check logs**: Use Azure portal or CLI to view application logs
2. **Health status**: Monitor Container Apps health in Azure portal
3. **Key Vault access**: Verify managed identity permissions
4. **Network connectivity**: Test internal service communication

### Useful Commands

```bash
# View application logs
az containerapp logs show --name api-image-analyzer --resource-group rg-ai-image-analyzer-prod

# Check app status
az containerapp show --name api-image-analyzer --resource-group rg-ai-image-analyzer-prod --query properties.runningStatus

# Update app configuration
az containerapp update --name api-image-analyzer --resource-group rg-ai-image-analyzer-prod --set-env-vars NEW_VAR=value
```

## 🎉 Success

Your Enterprise AI Image Analyzer is now running on Azure with production-grade security, scalability, and monitoring. The deployment demonstrates enterprise-level cloud architecture skills perfect for senior developer interviews.

**Live URLs will be displayed after deployment completes.**
