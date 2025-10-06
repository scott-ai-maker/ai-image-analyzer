#!/usr/bin/env python3
"""
Azure Computer Vision Connection Test Script

This script tests the connection to Azure Computer Vision service
and validates that your credentials are working properly.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Set PYTHONPATH to include src directory
os.environ['PYTHONPATH'] = str(project_root / "src")

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    # dotenv not available, try manual loading
    env_file = project_root / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

from src.core.config import Settings
from src.services.computer_vision import ComputerVisionService


async def test_azure_connection():
    """Test Azure Computer Vision connection and capabilities."""
    print("🔄 Testing Azure Computer Vision Connection...\n")
    
    # Load configuration
    try:
        settings = Settings()
        print(f"✅ Configuration loaded successfully")
        print(f"   Endpoint: {settings.azure_computer_vision_endpoint}")
        key_display = f"{'*' * 28}{settings.azure_computer_vision_key[-4:]}" if settings.azure_computer_vision_key else "Not set"
        print(f"   Key: {key_display}")
        print()
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        print("   Make sure you have a .env file with valid credentials")
        return False
    
    # Initialize service
    try:
        cv_service = ComputerVisionService(settings)
        print("✅ Computer Vision service initialized")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return False
    
    # Test with a sample image URL  
    test_image_url = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/landmark.jpg"
    
    try:
        print(f"🔄 Analyzing test image: {test_image_url}")
        detected_objects, image_metadata, processing_time = await cv_service.analyze_image_from_url(test_image_url)
        
        print("✅ Image analysis successful!")
        print(f"   Objects detected: {len(detected_objects)}")
        print(f"   Analysis time: {processing_time:.1f}ms")
        
        if image_metadata:
            print(f"   Image size: {image_metadata.width}x{image_metadata.height}")
            print(f"   Image format: {image_metadata.format}")
        print()
        
        # Display detected objects
        if detected_objects:
            print("🔍 Detected Objects:")
            for i, obj in enumerate(detected_objects, 1):
                print(f"   {i}. {obj.name} (confidence: {obj.confidence:.2%})")
                print(f"      Location: x={obj.bounding_box.x}, y={obj.bounding_box.y}, w={obj.bounding_box.width}, h={obj.bounding_box.height}")
        else:
            print("   No objects detected in the test image")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Image analysis failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Try to get more error details if available
        try:
            if hasattr(e, 'status_code'):
                print(f"   Status code: {getattr(e, 'status_code')}")
            elif hasattr(e, 'response'):
                response = getattr(e, 'response')
                if hasattr(response, 'status_code'):
                    print(f"   Status code: {getattr(response, 'status_code')}")
        except:
            pass  # Ignore errors when trying to extract error details
            
        return False


def check_environment():
    """Check if required environment variables are set."""
    required_vars = [
        "AZURE_COMPUTER_VISION_ENDPOINT",
        "AZURE_COMPUTER_VISION_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease create a .env file with these variables.")
        print("See docs/AZURE_SETUP.md for detailed instructions.")
        return False
    
    return True


async def main():
    """Main test function."""
    print("🚀 Azure Computer Vision Test Script")
    print("=" * 50)
    print()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test connection
    success = await test_azure_connection()
    
    if success:
        print("🎉 All tests passed! Your Azure Computer Vision is ready.")
        print("\nNext steps:")
        print("1. Update your application settings if needed")
        print("2. Test with your own images")
        print("3. Deploy to production")
    else:
        print("❌ Tests failed. Please check your configuration.")
        print("\nTroubleshooting:")
        print("1. Verify your Azure credentials in .env file")
        print("2. Check that your Computer Vision resource is active")
        print("3. Ensure you have sufficient quota remaining")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())