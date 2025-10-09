"""
Hands-on Redis Caching - Core Interview Patterns

You'll implement the 3 most important patterns:
1. Cache-aside (get/set with fallback)
2. Rate limiting (sliding window)
3. Graceful degradation (handle Redis failures)

These patterns appear in 90% of senior developer interviews!
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# We'll start simple - no Redis connection yet
class SimpleCache:
    """
    PATTERN 1: Cache-Aside Implementation
    
    Interview Question: "Implement a cache-aside pattern"
    Your Answer: This implementation!
    """
    
    def __init__(self):
        # TODO: You'll implement the core caching logic here
        self.cache = {} # Simple dict for now
        self.cache_ttl = {} # Track expiration times

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        TODO: Implement cache-aside pattern
        
        Steps you'll code:
        1. Check cache first
        2. If miss, fetch from "database" (simulate)
        3. Store result in cache
        4. Return data
        """
        print(f"🔍 Getting user profile for {user_id}")
        
        # STEP 1: Check cache first
        # TODO: Add cache lookup logic here
        cached_data = self.cache.get(user_id)
        if cached_data and not self._is_expired(user_id):
            print(f"   ✅ Cache hit!")
            return cached_data
        
        # STEP 2: Cache miss - fetch from database
        print(f"   💾 Cache miss - fetching from database...")
        
        # Simulate database fetch
        await asyncio.sleep(0.1)  # Simulate DB latency
        user_data = {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "created_at": datetime.now().isoformat()
        }
        
        # STEP 3: Store in cache
        # TODO: Add cache storage logic here
        self.cache[user_id] = user_data
        self.cache_ttl[user_id] = datetime.now() + timedelta(seconds=300)
        print(f"   💾 Stored in cache")
        
        return user_data
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() > self.cache_ttl.get(key, datetime.min)
    
    # TEST THE PATTERN
    async def test_cache_aside(self):
        """Test your cache-aside implementation."""
        print("🧪 Testing Cache-Aside Pattern")
        print("=" * 40)
        
        # First call - should be cache miss
        print("First call (cache miss expected):")
        start = time.time()
        result1 = await self.get_user_profile("123")
        time1 = time.time() - start
        print(f"   Time: {time1:.3f}s")
        print()
        
        # Second call - should be cache hit
        print("Second call (cache hit expected):")
        start = time.time()
        result2 = await self.get_user_profile("123")
        time2 = time.time() - start
        print(f"   Time: {time2:.3f}s")
        print(f"   Speed improvement: {time1/time2:.1f}x faster")
        print()


class RateLimiter:
    """
    PATTERN 2: Rate Limiting with Sliding Window
    
    Interview Question: "How would you implement rate limiting for an API?"
    Your Answer: This sliding window implementation!
    
    Why sliding window vs fixed window?
    - Fixed: 100 requests at 00:59, 100 more at 01:01 = 200 in 2 seconds ❌
    - Sliding: Always respects the time window precisely ✅
    """
    
    def __init__(self):
        # TODO: You'll implement rate limiting storage
        self.request_history = {}  # client_id -> List of timestamps
    
    async def is_allowed(self, client_id: str, limit: int, window_seconds: int) -> Dict[str, Any]:
        """
        TODO: Implement sliding window rate limiting
        
        Algorithm you'll code:
        1. Remove old timestamps (outside window)
        2. Count current requests in window
        3. If under limit, allow and record timestamp
        4. Return result with remaining count
        
        Interview Tip: Explain the algorithm step by step!
        """
        current_time = datetime.now()
        
        print(f"🚦 Checking rate limit for {client_id}")
        print(f"   Limit: {limit} requests per {window_seconds} seconds")
        
        # TODO: Implement the sliding window logic here
        if client_id not in self.request_history:
            self.request_history[client_id] = []
        
        requests = self.request_history[client_id]

        # Step 1: Clean old entries
        window_start = current_time - timedelta(seconds=window_seconds)
        self.request_history[client_id] = [
            req_time for req_time in requests
            if req_time > window_start
        ]

        # Step 2: Count current requests  
        current_count = len(self.request_history[client_id])
        print(f"   Current count in window: {current_count}")

        # Step 3: Check if allowed
        if current_count >= limit:
            return {
                "allowed": False,
                "remaining": 0,
                "current_count": current_count,
                "reset_time": current_time + timedelta(seconds=window_seconds)
            }

        # Step 4: Record new request if allowed
        self.request_history[client_id].append(current_time)

        return {
            "allowed": True,
            "remaining": limit - current_count - 1,
            "current_count": current_count + 1,
            "reset_time": current_time + timedelta(seconds=window_seconds)
        }
        
    # TEST THE PATTERN   
    async def test_rate_limiting(self):
        """Test your rate limiting implementation."""
        print("🧪 Testing Rate Limiting Pattern")
        print("=" * 40)
        
        client_id = "api_client_123"
        limit = 3  # 3 requests per 5 seconds
        window = 5
        
        print(f"Testing {limit} requests per {window} seconds")
        print()
        
        # Make requests rapidly
        for i in range(1, 6):  # Try 5 requests (should block after 3)
            result = await self.is_allowed(client_id, limit, window)
            
            status = "✅ ALLOWED" if result['allowed'] else "❌ BLOCKED"
            print(f"Request {i}: {status}")
            print(f"   Remaining: {result['remaining']}")
            print(f"   Current count: {result['current_count']}")
            
            if not result['allowed']:
                print(f"   🚫 Rate limit hit! Reset at: {result['reset_time']}")
            
            print()
            await asyncio.sleep(0.5)  # Small delay between requests


class ResilientCache:
    """
    PATTERN 3: Graceful Degradation with Circuit Breaker
    
    Interview Question: "What happens when Redis goes down in production?"
    Your Answer: Graceful degradation with circuit breaker pattern!
    
    Circuit Breaker States:
    - CLOSED: Normal operation (Redis working)
    - OPEN: Redis is down, skip Redis calls  
    - HALF_OPEN: Test if Redis is back up
    """
    
    def __init__(self):
        # Cache storage
        self.cache = {}
        self.cache_ttl = {}
        
        # TODO: You'll implement circuit breaker logic
        # Circuit breaker state
        self.circuit_state = "CLOSED" # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.failure_threshold = 3 # Open circuit after 3 failures
        self.recovery_timeout = 10 # Try recovery after 10 seconds
        self.last_failure_time = None
    
    
    async def get_with_fallback(self, user_id: str) -> Dict[str, Any]:
        """
        TODO: Implement cache with graceful degradation
        
        Logic you'll code:
        1. Check circuit breaker state
        2. If OPEN, skip Redis and go to database
        3. If CLOSED/HALF_OPEN, try Redis
        4. Handle Redis failures and update circuit breaker
        5. Always return data (never fail completely)
        
        Interview Gold: "The app never goes down, even if Redis fails"
        """
        # Check circuit breaker state
        if self.circuit_state == "OPEN":
            # Check if we should try recovery
            if (self.last_failure_time and
                (datetime.now() - self.last_failure_time).seconds > self.recovery_timeout):
                self.circuit_state = "HALF_OPEN"
                print("   🟡 Circuit HALF_OPEN - testing recovery...")
            else:
                print("   🔴 Circuit OPEN - skipping Redis, going direct to DB")
                return await self._get_from_database(user_id)
        
        # Try Redis (CLOSED or HALF_OPEN state)
        print(f"    🟢 Circuit {self.circuit_state} - trying Redis...")
        try:
            # Simulate Redis failure for demo (every 4th call fails)
            import random
            if random.random() < 0.30: # 30% failure rate for demo
                raise Exception("Simulated Redis connection failure")

            result = await self._get_from_cache_or_db(user_id)

            # Success! Reset circuit breaker
            if self.circuit_state == "HALF_OPEN":
                print("   ✅ Recovery successful - circuit CLOSED")
                self.circuit_state = "CLOSED"
                self.failure_count = 0

            return result
        
        except Exception as e:
            print(f"   🔴 Redis failed: {e}")

            # Update circuit breaker
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.circuit_state = "OPEN"
                print(f"   ⚡ Circuit breaker OPENED after {self.failure_count} failures")

            # Fallback to database
            return await self._get_from_database(user_id)
    
    async def _get_from_cache_or_db(self, user_id: str) -> Dict[str, Any]:
        """Try cache first, then database."""
        # Check cache
        cached_data = self.cache.get(user_id)
        if cached_data and not self._is_expired(user_id):
            print("   ✅ Cache hit!")
            return cached_data
        
        print("   💾 Cache miss - fetching from database...")
        data = await self._get_from_database(user_id)
        
        # Cache the result
        self.cache[user_id] = data
        self.cache_ttl[user_id] = datetime.now() + timedelta(seconds=300)
        
        return data
    
    async def _get_from_database(self, user_id: str) -> Dict[str, Any]:
        """Direct database access (fallback)."""
        await asyncio.sleep(0.1)  # Simulate DB latency
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "created_at": datetime.now().isoformat(),
            "source": "database"  # Track where data came from
        }
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() > self.cache_ttl.get(key, datetime.min)
    
    async def test_graceful_degradation(self):
        """Test graceful degradation patterns."""
        print("🧪 Testing Graceful Degradation Pattern")
        print("=" * 40)
        
        print("Scenario 1: Normal operation (Redis working)")
        result1 = await self.get_with_fallback("user_100")
        print(f"   Got user: {result1['name']}")
        print()
        
        print("Scenario 2: Redis failure (circuit breaker opens)")
        # TODO: You'll implement Redis failure simulation
        result2 = await self.get_with_fallback("user_200") 
        print(f"   Got user: {result2['name']} from {result2['source']}")
        print()
        
        print("💡 Key Point: App never fails, even when Redis is down!")
        print()


# Update main to test all three patterns
if __name__ == "__main__":
    print("🎯 Redis Caching Patterns - Senior Developer Interview Prep")
    print("=" * 70)
    print()
    
    # Test cache-aside
    cache = SimpleCache()
    asyncio.run(cache.test_cache_aside())
    
    print("\n" + "="*70 + "\n")
    
    # Test rate limiting  
    limiter = RateLimiter()
    asyncio.run(limiter.test_rate_limiting())
    
    print("\n" + "="*70 + "\n")
    
    # Test graceful degradation
    resilient_cache = ResilientCache()
    asyncio.run(resilient_cache.test_graceful_degradation())