# 🚀 Production Readiness Setup Guide

## Overview
This guide will walk you through setting up your AI Image Analyzer for production deployment, starting with real Azure Computer Vision credentials.

## Step 1: Azure Computer Vision Setup

### Quick Setup (Automated)
```bash
# Run our automated setup script
./scripts/setup_azure.sh
```

### Manual Setup
If you prefer manual setup or the script doesn't work:

1. **Follow the detailed guide:**
   ```bash
   cat docs/AZURE_SETUP.md
   ```

2. **Create your .env file:**
   ```bash
   cp .env.template .env
   # Edit .env with your actual values
   ```

### What You'll Get
- ✅ Azure Computer Vision resource (Free tier: 5,000 calls/month)
- ✅ Properly configured .env file
- ✅ Connection testing script

## Step 2: Test Your Setup

### Basic Connection Test
```bash
# Test Azure connection
python scripts/test_azure_connection.py
```

### Full Application Test
```bash
# Start the application
python -m uvicorn src.api.main:app --reload

# In another terminal, test the API
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ThreeTimeCorgi.jpg/256px-ThreeTimeCorgi.jpg"}'
```

## Expected Results

### Successful Setup ✅
```json
{
  "objects": [
    {
      "name": "dog",
      "confidence": 0.95,
      "bounding_box": {
        "x": 10,
        "y": 20,
        "width": 100,
        "height": 150
      }
    }
  ],
  "image_metadata": {
    "width": 256,
    "height": 192,
    "format": "JPEG"
  },
  "processing_time_ms": 1250
}
```

### Common Issues ❌

#### Issue: Invalid Credentials
```
❌ Image analysis failed: Unauthorized (401)
```
**Solution:** Double-check your Azure Computer Vision key and endpoint

#### Issue: Rate Limiting
```
❌ Too Many Requests (429)
```
**Solution:** You've exceeded the free tier limits. Wait or upgrade to paid tier.

#### Issue: Import Errors
```
❌ Import "services.computer_vision" could not be resolved
```
**Solution:** Make sure you're running from the project root with virtual environment activated

## Next Steps After Successful Setup

Once your Azure connection is working, you're ready for the next production readiness tasks:

1. **Enhanced Error Handling** - Add retry logic and graceful degradation
2. **CI/CD Pipeline** - Automated testing and deployment
3. **Container Deployment** - Azure Container Instances setup
4. **Monitoring & Logging** - Production observability
5. **Security Hardening** - Production security measures

## Need Help?

### Common Commands
```bash
# Check your configuration
python -c "from src.core.config import Settings; s=Settings(); print(f'Endpoint: {s.azure_computer_vision_endpoint}')"

# View application logs
tail -f server.log

# Test health endpoint
curl http://localhost:8000/health
```

### Troubleshooting Resources
- [Azure Computer Vision Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/computer-vision/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Settings](https://pydantic-docs.helpmanual.io/usage/settings/)

---

**Ready to proceed?** Run the Azure setup and let me know how it goes! 🎉