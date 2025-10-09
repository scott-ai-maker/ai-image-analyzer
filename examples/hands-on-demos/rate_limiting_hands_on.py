"""
🎯 API Rate Limiting & Throttling - Hands-on Implementation

This file implements production-grade rate limiting patterns used by major APIs.
YOU'LL learn and implement the core algorithms that power rate limiting at scale.

Key concepts you'll implement:
1. Token Bucket Algorithm (used by AWS, GitHub)
2. Sliding Window Counter (used by Twitter, Stripe)
3. User Tier-based Rate Limits (USER, PREMIUM, ADMIN)
4. Burst Handling and Grace Periods
5. Redis Integration for Distributed Rate Limiting

This shows how real APIs handle millions of requests without going down!
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

# Import user roles from your auth system
from auth_hands_on import UserRole

# ============================================================================
# 🎯 RATE LIMITING ALGORITHMS
# ============================================================================


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithm types."""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimit:
    """Rate limit configuration."""

    requests: int  # Number of requests allowed
    window: int  # Time window in seconds
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW


@dataclass
class RateLimitResult:
    """Result of rate limit check."""

    allowed: bool
    requests_remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None  # Seconds until next request allowed


# ============================================================================
# 🪣 TOKEN BUCKET ALGORITHM
# ============================================================================


class TokenBucket:
    """
    YOUR TASK: Implement Token Bucket Algorithm

    Used by: AWS API Gateway, GitHub API, Cloudflare

    Concept:
    - Bucket holds tokens, each request consumes 1 token
    - Tokens refill at a constant rate
    - Allows burst traffic up to bucket capacity
    - Smooth rate limiting over time
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum tokens in bucket (burst capacity)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)  # Start with full bucket
        self.last_refill = time.time()

        print(f"🪣 Token Bucket created: capacity={capacity}, rate={refill_rate}/sec")

    def consume(self, tokens: int = 1) -> bool:
        """
        YOUR TASK: Implement token consumption

        Steps:
        1. Calculate how many tokens to add based on time elapsed
        2. Add tokens to bucket (up to capacity)
        3. Check if enough tokens available
        4. Consume tokens if available
        """
        now = time.time()

        # TODO: YOU implement token refill logic
        time_elapsed = now - self.last_refill
        tokens_to_add = time_elapsed * self.refill_rate

        # Add tokens to bucket (don't exceed capacity)
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

        print(f"🪣 Bucket state: {self.tokens:.2f} tokens available")

        # TODO: YOU implement consumption logic
        if self.tokens >= tokens:
            self.tokens -= tokens
            print(f"   ✅ Consumed {tokens} tokens ({self.tokens:.2f} remaining)")
            return True
        else:
            print(f"   ❌ Not enough tokens (need {tokens}, have {self.tokens:.2f})")
            return False

    def get_wait_time(self) -> float:
        """Calculate seconds to wait until next token available."""
        if self.tokens >= 1:
            return 0.0
        return (1 - self.tokens) / self.refill_rate


# ============================================================================
# 📊 SLIDING WINDOW COUNTER
# ============================================================================


class SlidingWindowCounter:
    """
    YOUR TASK: Implement Sliding Window Counter

    Used by: Twitter API, Stripe API, Reddit API

    Concept:
    - Track requests in time buckets (e.g., per minute)
    - Calculate rate over sliding time window
    - More accurate than fixed windows
    - Prevents burst at window boundaries
    """

    def __init__(self, limit: int, window_seconds: int, bucket_size: int = 60):
        """
        Initialize sliding window counter.

        Args:
            limit: Max requests per window
            window_seconds: Time window (e.g., 3600 for 1 hour)
            bucket_size: Size of time buckets in seconds
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.bucket_size = bucket_size
        self.buckets: dict[int, int] = {}  # timestamp -> count

        print(f"📊 Sliding Window created: {limit} req/{window_seconds}sec")

    def is_allowed(self, user_id: str) -> tuple[bool, int]:
        """
        YOUR TASK: Check if request is allowed

        Steps:
        1. Get current time bucket
        2. Clean old buckets outside window
        3. Count requests in current window
        4. Allow or deny request
        """
        now = int(time.time())
        bucket_key = now // self.bucket_size

        # TODO: YOU implement window cleaning
        cutoff_time = now - self.window_seconds
        cutoff_bucket = cutoff_time // self.bucket_size

        # Remove old buckets
        old_buckets = [b for b in self.buckets.keys() if b <= cutoff_bucket]
        for old_bucket in old_buckets:
            del self.buckets[old_bucket]

        # TODO: YOU implement request counting
        total_requests = sum(self.buckets.values())

        print(f"📊 Window analysis: {total_requests}/{self.limit} requests used")

        if total_requests < self.limit:
            # Record this request
            self.buckets[bucket_key] = self.buckets.get(bucket_key, 0) + 1
            remaining = self.limit - total_requests - 1
            print(f"   ✅ Request allowed ({remaining} remaining)")
            return True, remaining
        else:
            print("   ❌ Rate limit exceeded")
            return False, 0

    def get_reset_time(self) -> datetime:
        """Get when the rate limit resets."""
        return datetime.fromtimestamp(time.time() + self.window_seconds)


# ============================================================================
# 🎚️ USER TIER-BASED RATE LIMITING
# ============================================================================


class UserTierRateLimiter:
    """
    YOUR TASK: Implement tier-based rate limiting

    Real-world pattern used by:
    - GitHub (different limits for free vs paid)
    - Twitter (different API tiers)
    - AWS (service limits based on account type)
    """

    def __init__(self):
        # Define rate limits per user tier
        self.tier_limits = {
            UserRole.USER: RateLimit(requests=100, window=3600),  # 100/hour
            UserRole.PREMIUM: RateLimit(requests=1000, window=3600),  # 1000/hour
            UserRole.ADMIN: RateLimit(requests=10000, window=3600),  # 10000/hour
        }

        # Store rate limiters per user
        self.user_limiters: dict[str, SlidingWindowCounter] = {}

        print("🎚️ Tier-based Rate Limiter initialized")
        for tier, limit in self.tier_limits.items():
            print(f"   {tier.value}: {limit.requests} requests/{limit.window}s")

    def check_rate_limit(self, user_id: str, user_role: UserRole) -> RateLimitResult:
        """
        YOUR TASK: Check rate limit for user based on their tier

        Steps:
        1. Get rate limit config for user tier
        2. Get or create rate limiter for user
        3. Check if request is allowed
        4. Return detailed result
        """
        # TODO: YOU implement tier-based checking
        rate_limit = self.tier_limits.get(user_role)
        if not rate_limit:
            # Default to most restrictive
            rate_limit = self.tier_limits[UserRole.USER]

        # Get or create rate limiter for this user
        if user_id not in self.user_limiters:
            self.user_limiters[user_id] = SlidingWindowCounter(
                limit=rate_limit.requests, window_seconds=rate_limit.window
            )

        limiter = self.user_limiters[user_id]
        allowed, remaining = limiter.is_allowed(user_id)

        print(f"🎚️ Rate limit check for {user_role.value} user {user_id}")

        return RateLimitResult(
            allowed=allowed,
            requests_remaining=remaining,
            reset_time=limiter.get_reset_time(),
            retry_after=60 if not allowed else None,  # Wait 1 minute if denied
        )


# ============================================================================
# 🚀 REDIS DISTRIBUTED RATE LIMITER
# ============================================================================


class RedisRateLimiter:
    """
    YOUR TASK: Implement Redis-based distributed rate limiting

    Why Redis?
    - Shared state across multiple servers
    - Atomic operations for accuracy
    - High performance (sub-millisecond)
    - Built-in expiration

    Used by: Netflix, Uber, Airbnb for distributed systems
    """

    def __init__(self):
        # For this demo, we'll simulate Redis with in-memory store
        # In production, use actual Redis client
        self.redis_store: dict[str, dict] = {}
        print("🚀 Redis Rate Limiter initialized (simulated)")

    def sliding_window_rate_limit(
        self, key: str, limit: int, window_seconds: int
    ) -> RateLimitResult:
        """
        YOUR TASK: Implement Redis sliding window using Lua script pattern

        Production pattern:
        - Use Redis sorted sets to store request timestamps
        - Atomic operations to prevent race conditions
        - Clean old entries and count current window
        """
        now = time.time()

        # TODO: YOU implement Redis sliding window

        # Get current window data
        if key not in self.redis_store:
            self.redis_store[key] = {"requests": []}

        requests = self.redis_store[key]["requests"]

        # Remove old requests outside window
        cutoff_time = now - window_seconds
        requests = [req_time for req_time in requests if req_time > cutoff_time]

        print(f"🚀 Redis check: {len(requests)}/{limit} requests in window")

        if len(requests) < limit:
            # Add current request
            requests.append(now)
            self.redis_store[key]["requests"] = requests

            remaining = limit - len(requests)
            print(f"   ✅ Request allowed ({remaining} remaining)")

            return RateLimitResult(
                allowed=True,
                requests_remaining=remaining,
                reset_time=datetime.fromtimestamp(now + window_seconds),
            )
        else:
            print("   ❌ Rate limit exceeded")
            return RateLimitResult(
                allowed=False,
                requests_remaining=0,
                reset_time=datetime.fromtimestamp(now + window_seconds),
                retry_after=int(window_seconds),
            )


# ============================================================================
# 🧪 TESTING YOUR RATE LIMITING IMPLEMENTATIONS
# ============================================================================


async def test_token_bucket_algorithm():
    """Test YOUR token bucket implementation."""
    print("\n🧪 Testing YOUR Token Bucket Algorithm")
    print("=" * 50)

    # Create bucket: 5 tokens, refill 2 per second
    bucket = TokenBucket(capacity=5, refill_rate=2.0)

    print("\n1. Testing burst capacity...")
    for i in range(7):  # Try to consume 7 tokens (more than capacity)
        success = bucket.consume()
        if not success:
            print(f"   Request {i+1}: Rate limited!")
            break

    print("\n2. Testing refill rate...")
    print("   Waiting 2 seconds for token refill...")
    await asyncio.sleep(2)

    print("   Trying requests after refill:")
    for i in range(3):
        success = bucket.consume()
        print(f"   Request {i+1}: {'✅ Success' if success else '❌ Limited'}")


async def test_sliding_window_counter():
    """Test YOUR sliding window implementation."""
    print("\n🧪 Testing YOUR Sliding Window Counter")
    print("=" * 50)

    # Create window: 5 requests per 10 seconds
    window = SlidingWindowCounter(limit=5, window_seconds=10)

    print("\n1. Testing request allowance...")
    for i in range(7):  # Try 7 requests (more than limit)
        allowed, remaining = window.is_allowed("user123")
        if not allowed:
            print(f"   Request {i+1}: Rate limited!")

        # Small delay between requests
        await asyncio.sleep(0.1)


async def test_user_tier_rate_limiting():
    """Test YOUR tier-based rate limiting."""
    print("\n🧪 Testing YOUR User Tier Rate Limiting")
    print("=" * 50)

    tier_limiter = UserTierRateLimiter()

    # Test different user tiers
    test_users = [
        ("user1", UserRole.USER),
        ("premium1", UserRole.PREMIUM),
        ("admin1", UserRole.ADMIN),
    ]

    for user_id, role in test_users:
        print(f"\n🎚️ Testing {role.value} user:")
        result = tier_limiter.check_rate_limit(user_id, role)
        print(f"   Allowed: {result.allowed}")
        print(f"   Remaining: {result.requests_remaining}")
        print(f"   Reset time: {result.reset_time}")


async def test_redis_distributed_limiting():
    """Test YOUR Redis distributed rate limiting."""
    print("\n🧪 Testing YOUR Redis Distributed Rate Limiting")
    print("=" * 50)

    redis_limiter = RedisRateLimiter()

    print("\n🚀 Testing distributed rate limiting...")
    for i in range(7):  # Test 7 requests with limit of 5
        result = redis_limiter.sliding_window_rate_limit(
            key="api:user123", limit=5, window_seconds=60
        )

        if not result.allowed:
            print(f"   Request {i+1}: Rate limited!")
            print(f"   Retry after: {result.retry_after} seconds")

        await asyncio.sleep(0.1)


# ============================================================================
# 🏃 MAIN TESTING FUNCTION
# ============================================================================


async def main():
    """Run all rate limiting tests."""
    print("🎯 API Rate Limiting & Throttling - YOUR Implementation")
    print("=" * 70)

    # Test all algorithms
    await test_token_bucket_algorithm()
    await test_sliding_window_counter()
    await test_user_tier_rate_limiting()
    await test_redis_distributed_limiting()

    print("\n" + "=" * 70)
    print("🎉 Rate Limiting Implementation Complete!")
    print(
        """
YOUR TASKS COMPLETED:
✅ Token Bucket Algorithm - Burst handling with smooth refill
✅ Sliding Window Counter - Accurate rate limiting over time
✅ User Tier Rate Limits - Different limits per user role
✅ Redis Distribution - Shared state for multiple servers

PRODUCTION PATTERNS LEARNED:
🎯 AWS/GitHub-style token buckets for burst traffic
🎯 Twitter/Stripe-style sliding windows for accuracy
🎯 Tier-based limits for different user types
🎯 Redis-based distribution for scale

NEXT STEPS:
- Integrate with FastAPI endpoints
- Add rate limit headers (X-RateLimit-*)
- Implement rate limit bypass for admin users
- Add monitoring and alerting for rate limit violations

This is how real APIs handle MILLIONS of requests! 🚀
    """
    )


if __name__ == "__main__":
    asyncio.run(main())
