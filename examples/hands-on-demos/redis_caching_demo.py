"""
Redis Caching Demo - Interactive Learning Session

This demo shows enterprise-grade caching patterns in action:
1. Connection management with circuit breaker
2. Cache-aside pattern (user profiles)
3. Write-through pattern (analysis results)
4. Rate limiting with sliding windows
5. Session management with Redis hashes
6. Cache warming and invalidation strategies
7. Performance monitoring

Run this to see caching concepts in action!
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import our caching services
from src.cache.cache_service import (
    analysis_cache,
    rate_limit_cache,
    session_cache,
    user_cache,
    warming_service,
)
from src.cache.redis_config import cache_manager, redis_config


class CachingDemo:
    """Interactive caching demonstration."""

    def __init__(self):
        self.demo_users = [f"user_{i}" for i in range(1, 6)]
        self.demo_images = [f"image_{i}" for i in range(1, 4)]

    async def initialize(self):
        """Initialize Redis connection."""
        print("🚀 Initializing Redis connection...")
        await redis_config.initialize()

        is_available = await redis_config.is_available()
        if is_available:
            print("✅ Redis connection established!")
        else:
            print("⚠️  Redis not available - using no-op cache (graceful degradation)")

        print()

    async def demo_cache_aside_pattern(self):
        """Demonstrate cache-aside pattern with user profiles."""
        print("=" * 60)
        print("📋 DEMO 1: Cache-Aside Pattern (User Profiles)")
        print("=" * 60)

        print("Cache-aside: App manages cache manually")
        print("- Read: Check cache → if miss, load from DB → cache result")
        print("- Write: Update DB → invalidate cache")
        print()

        user_id = "user_123"

        # First request - cache miss
        print(f"🔍 First request for user {user_id} (should be cache miss)...")
        start_time = time.time()
        user_data = await user_cache.get_user_profile(user_id)
        miss_time = time.time() - start_time
        print(f"   Response time: {miss_time:.3f}s")
        print(f"   Data: {json.dumps(user_data, indent=2)}")
        print()

        # Second request - cache hit
        print(f"🚀 Second request for user {user_id} (should be cache hit)...")
        start_time = time.time()
        cached_data = await user_cache.get_user_profile(user_id)
        hit_time = time.time() - start_time
        print(f"   Response time: {hit_time:.3f}s")
        print(f"   Speed improvement: {(miss_time/hit_time):.1f}x faster!")
        print()

        # Cache invalidation
        print("🗑️  Simulating user profile update (cache invalidation)...")
        await user_cache.invalidate_user_cache(user_id)
        print("   Cache invalidated - next request will be fresh")
        print()

    async def demo_write_through_pattern(self):
        """Demonstrate write-through pattern with analysis results."""
        print("=" * 60)
        print("🖼️  DEMO 2: Write-Through Pattern (Image Analysis)")
        print("=" * 60)

        print("Write-through: Cache and DB updated simultaneously")
        print("- Ensures consistency between cache and database")
        print("- Higher latency but better data integrity")
        print()

        # Simulate image data
        image_data = b"fake_image_data_for_demo"
        image_hash = hashlib.sha256(image_data).hexdigest()[:16]

        # Simulate analysis function
        async def fake_analyze_image(data: bytes) -> dict[str, Any]:
            await asyncio.sleep(0.1)  # Simulate processing time
            return {
                "objects": ["car", "person", "building"],
                "confidence_scores": [0.95, 0.87, 0.92],
                "processing_time": 0.1,
                "model_version": "v2.0",
            }

        print(f"🔬 Analyzing image {image_hash}...")
        start_time = time.time()
        result1 = await analysis_cache.get_or_analyze_image(
            image_data, fake_analyze_image
        )
        analysis_time = time.time() - start_time
        print(f"   Analysis time: {analysis_time:.3f}s")
        print(f"   Objects found: {result1['objects']}")
        print()

        print("🚀 Re-analyzing same image (should use cache)...")
        start_time = time.time()
        result2 = await analysis_cache.get_or_analyze_image(
            image_data, fake_analyze_image
        )
        cached_time = time.time() - start_time
        print(f"   Cache retrieval time: {cached_time:.3f}s")
        print(f"   Speed improvement: {(analysis_time/cached_time):.1f}x faster!")
        print(f"   Same result: {result1 == result2}")
        print()

    async def demo_rate_limiting(self):
        """Demonstrate Redis-based rate limiting."""
        print("=" * 60)
        print("🚦 DEMO 3: Rate Limiting (Sliding Window)")
        print("=" * 60)

        print("Sliding window rate limiting:")
        print("- More accurate than fixed windows")
        print("- Prevents burst traffic effectively")
        print()

        client_id = "api_client_demo"
        limit = 5  # 5 requests per 10 seconds
        window = 10

        print(f"Rate limit: {limit} requests per {window} seconds")
        print(f"Testing with client: {client_id}")
        print()

        # Make requests quickly
        for i in range(1, 8):  # Try 7 requests (should hit limit)
            result = await rate_limit_cache.check_rate_limit(client_id, limit, window)

            status = "✅ ALLOWED" if result["allowed"] else "❌ BLOCKED"
            print(
                f"Request {i}: {status} - Remaining: {result['remaining']}, Count: {result['current_count']}"
            )

            if not result["allowed"]:
                print(f"   Rate limit exceeded! Reset at: {result['reset_time']}")

            await asyncio.sleep(0.5)  # Small delay between requests

        print()
        print("💡 In production, you'd return HTTP 429 for blocked requests")
        print()

    async def demo_session_management(self):
        """Demonstrate Redis-based session management."""
        print("=" * 60)
        print("👤 DEMO 4: Session Management (Redis Hashes)")
        print("=" * 60)

        print("Redis hashes for session data:")
        print("- Fast field-level access")
        print("- Automatic TTL management")
        print("- Complex data structures")
        print()

        user_id = "user_456"
        session_data = {
            "username": "john_doe",
            "role": "premium_user",
            "preferences": {"theme": "dark", "language": "en"},
            "login_ip": "192.168.1.100",
        }

        # Create session
        print("🔐 Creating new session...")
        session_id = await session_cache.create_session(user_id, session_data)
        print(f"   Session ID: {session_id}")
        print(f"   Session data: {json.dumps(session_data, indent=2)}")
        print()

        # Retrieve session
        print("📖 Retrieving session...")
        retrieved_session = await session_cache.get_session(session_id)
        print(f"   Retrieved data: {json.dumps(retrieved_session, indent=2)}")
        print()

        # Extend session
        print("⏰ Extending session by 30 minutes...")
        extended = await session_cache.extend_session(session_id, 1800)  # 30 minutes
        print(f"   Session extended: {extended}")
        print()

        # Delete session (logout)
        print("🚪 Logging out (deleting session)...")
        deleted = await session_cache.delete_session(session_id)
        print(f"   Session deleted: {deleted}")

        # Try to retrieve deleted session
        print("🔍 Trying to retrieve deleted session...")
        deleted_session = await session_cache.get_session(session_id)
        print(f"   Result: {deleted_session}")
        print()

    async def demo_cache_warming(self):
        """Demonstrate cache warming strategies."""
        print("=" * 60)
        print("🔥 DEMO 5: Cache Warming Strategies")
        print("=" * 60)

        print("Cache warming improves performance by:")
        print("- Pre-loading frequently accessed data")
        print("- Reducing cache misses during peak hours")
        print("- Ensuring consistent response times")
        print()

        print("🌟 Warming user cache...")
        await warming_service.warm_user_cache(10)  # Warm top 10 users
        print()

        print("🌟 Warming analysis cache...")
        sample_images = [f"popular_image_{i}" for i in range(1, 6)]
        await warming_service.warm_analysis_cache(sample_images)
        print()

        print("✅ Cache warming completed!")
        print()

    async def demo_cache_statistics(self):
        """Show cache performance statistics."""
        print("=" * 60)
        print("📊 DEMO 6: Cache Performance Statistics")
        print("=" * 60)

        print("Cache statistics help you understand:")
        print("- Hit rate and performance")
        print("- Cache usage patterns")
        print("- Optimization opportunities")
        print()

        # Get current statistics
        stats = cache_manager.get_cache_stats()

        print("Current cache statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        print()

        # Show Redis availability
        is_available = await redis_config.is_available()
        print(f"Redis status: {'✅ Available' if is_available else '❌ Unavailable'}")
        print()

    async def demo_cache_invalidation(self):
        """Demonstrate cache invalidation patterns."""
        print("=" * 60)
        print("🗑️  DEMO 7: Cache Invalidation Strategies")
        print("=" * 60)

        print("Cache invalidation strategies:")
        print("1. Time-based (TTL) - automatic expiration")
        print("2. Event-based - invalidate on data changes")
        print("3. Pattern-based - bulk invalidation")
        print()

        # Cache some test data
        print("📝 Caching test data...")
        test_users = ["test_user_1", "test_user_2", "test_user_3"]

        for user_id in test_users:
            await user_cache.get_user_profile(user_id)  # This will cache the data

        print(f"   Cached profiles for {len(test_users)} users")
        print()

        # Pattern-based invalidation
        print("🔥 Performing pattern-based invalidation...")
        pattern = "user:test_user_*"
        deleted_count = await cache_manager.invalidate_pattern(pattern)
        print(f"   Invalidated {deleted_count} cache entries matching '{pattern}'")
        print()

        print("💡 In production, you'd invalidate cache when:")
        print("   - User profiles are updated")
        print("   - System configuration changes")
        print("   - Model versions are updated")
        print()

    async def run_all_demos(self):
        """Run all caching demonstrations."""
        print("🎯 Redis Caching Patterns - Interactive Demo")
        print("=" * 60)
        print()

        try:
            await self.initialize()

            # Run all demonstrations
            await self.demo_cache_aside_pattern()
            await self.demo_write_through_pattern()
            await self.demo_rate_limiting()
            await self.demo_session_management()
            await self.demo_cache_warming()
            await self.demo_cache_statistics()
            await self.demo_cache_invalidation()

            print("🎉 All caching demos completed!")
            print()
            print("🎓 Key Interview Takeaways:")
            print("=" * 30)
            print("1. Cache-aside: App manages cache manually (most common)")
            print("2. Write-through: Cache and DB updated together (consistency)")
            print("3. Rate limiting: Use Redis counters for API throttling")
            print("4. Session management: Redis hashes for complex data")
            print("5. Cache warming: Pre-load data for better performance")
            print("6. Graceful degradation: Handle Redis failures elegantly")
            print("7. Monitoring: Track hit rates and performance metrics")
            print()

        except Exception as e:
            logger.error(f"Demo failed: {e}")
            print(f"❌ Demo failed: {e}")

        finally:
            # Clean up
            await redis_config.close()
            print("🧹 Redis connections closed")


async def main():
    """Run the Redis caching demonstration."""
    demo = CachingDemo()
    await demo.run_all_demos()


if __name__ == "__main__":
    asyncio.run(main())
