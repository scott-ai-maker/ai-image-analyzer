"""
Simple script to test rate limiting server
"""
import requests
import time

def test_health():
    try:
        response = requests.get("http://127.0.0.1:8002/health")
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_rate_limit():
    """Test rate limiting by making multiple requests quickly"""
    print("\n🧪 Testing Rate Limiting...")
    
    for i in range(5):
        try:
            response = requests.get("http://127.0.0.1:8002/api/v1/rate-limit/test")
            print(f"Request {i+1}: Status {response.status_code}")
            
            # Print rate limit headers
            if "X-RateLimit-Remaining" in response.headers:
                print(f"  Remaining: {response.headers['X-RateLimit-Remaining']}")
            
            if response.status_code == 429:
                print("  🛡️ Rate limited!")
                break
                
        except Exception as e:
            print(f"Request {i+1} failed: {e}")
        
        time.sleep(0.1)

if __name__ == "__main__":
    print("🎯 Testing Rate Limiting Server")
    print("=" * 40)
    
    if test_health():
        test_rate_limit()
    else:
        print("❌ Server not responding")