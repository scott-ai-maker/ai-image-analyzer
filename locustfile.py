"""
Performance testing configuration for AI Image Analyzer
Run with: locust -f locustfile.py --host=http://localhost:8000
"""

import base64
import io
import random
from locust import HttpUser, task, between
from PIL import Image


class ImageAnalyzerUser(HttpUser):
    """Simulates users interacting with the image analyzer API"""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Setup tasks executed when a user starts"""
        # Create sample image data for testing
        self.sample_images = self._create_sample_images()
    
    def _create_sample_images(self):
        """Create sample base64 encoded images for testing"""
        images = []
        
        # Create different sized test images
        sizes = [(100, 100), (300, 300), (800, 600), (1920, 1080)]
        colors = ['red', 'blue', 'green', 'yellow', 'purple']
        
        for size in sizes:
            for color in colors[:2]:  # Limit combinations
                # Create a simple colored image
                img = Image.new('RGB', size, color)
                
                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG')
                img_data = buffer.getvalue()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                images.append({
                    'size': size,
                    'color': color,
                    'data': img_base64
                })
        
        return images
    
    @task(3)
    def analyze_image(self):
        """Test the main image analysis endpoint (weighted higher)"""
        image_data = random.choice(self.sample_images)
        
        payload = {
            "image_data": image_data['data'],
            "format": "base64",
            "features": ["description", "objects", "text", "faces"]
        }
        
        with self.client.post(
            "/analyze", 
            json=payload,
            name="analyze_image",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "description" in result:
                    response.success()
                else:
                    response.failure("Missing expected fields in response")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(2)
    def analyze_with_url(self):
        """Test image analysis with URL"""
        # Use a test image URL (placeholder)
        test_urls = [
            "https://via.placeholder.com/300x200/FF0000/FFFFFF?text=Test+Image+1",
            "https://via.placeholder.com/600x400/00FF00/000000?text=Test+Image+2",
            "https://via.placeholder.com/800x600/0000FF/FFFFFF?text=Test+Image+3"
        ]
        
        payload = {
            "image_url": random.choice(test_urls),
            "features": ["description", "objects"]
        }
        
        with self.client.post(
            "/analyze-url",
            json=payload,
            name="analyze_url",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Expected for placeholder URLs
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Test health endpoint"""
        with self.client.get("/health", name="health_check") as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure("Health check returned unhealthy status")
    
    @task(1)
    def get_supported_formats(self):
        """Test supported formats endpoint"""
        with self.client.get("/formats", name="supported_formats") as response:
            if response.status_code == 200:
                data = response.json()
                if "formats" in data:
                    response.success()
                else:
                    response.failure("Missing formats in response")


class BurstUser(ImageAnalyzerUser):
    """User that sends requests in bursts"""
    wait_time = between(0.1, 1)  # Much faster requests
    weight = 1  # Lower weight (fewer of these users)


class HeavyUser(ImageAnalyzerUser):
    """User that only sends large images"""
    wait_time = between(2, 8)  # Slower between requests
    weight = 1  # Lower weight
    
    def on_start(self):
        """Create only large images for testing"""
        super().on_start()
        # Filter for only large images
        self.sample_images = [
            img for img in self.sample_images 
            if img['size'][0] >= 800 or img['size'][1] >= 600
        ]


# Custom test scenarios
class WebsiteUser(HttpUser):
    """Simulates a typical website user pattern"""
    weight = 3  # Most common user type
    wait_time = between(2, 10)
    
    tasks = {
        ImageAnalyzerUser.health_check: 1,
        ImageAnalyzerUser.analyze_image: 10,
        ImageAnalyzerUser.get_supported_formats: 1,
    }


if __name__ == "__main__":
    # Can be run directly for testing
    import os
    os.system("locust -f locustfile.py --host=http://localhost:8000 --headless -u 10 -r 2 -t 30s")