# Redis Caching Patterns - Senior Developer Interview Guide

## 🎯 Core Interview Questions & Your Answers

### **Question 1: "Explain different caching patterns and when to use each"**

**Your Answer:**

```
1. Cache-Aside (Most Common - 90% of use cases)
   - App manages cache manually
   - Read: Check cache → if miss, get from DB → cache result
   - Write: Update DB → invalidate cache
   - Use when: User profiles, configuration data, read-heavy workloads

2. Write-Through
   - Cache and DB updated simultaneously
   - Higher latency but guaranteed consistency
   - Use when: Financial data, critical business data

3. Write-Behind (Write-Back)
   - Write to cache first, DB asynchronously
   - Highest performance but risk of data loss
   - Use when: High-write workloads, logs, analytics
```

### **Question 2: "How would you implement API rate limiting?"**

**Your Answer (Sliding Window Algorithm):**

```python
# Key insight: Use Redis sorted sets with timestamps
async def is_allowed(client_id, limit, window_seconds):
    current_time = time.now()
    window_start = current_time - window_seconds

    # Remove old entries
    redis.zremrangebyscore(key, 0, window_start)

    # Count current requests
    current_count = redis.zcard(key)

    if current_count >= limit:
        return False  # Rate limited

    # Add current request
    redis.zadd(key, {current_time: current_time})
    return True
```

**Why Sliding Window vs Fixed Window:**

- Fixed: Allows burst traffic at window boundaries
- Sliding: Precise time-based limiting, no bursts

### **Question 3: "What happens when Redis goes down in production?"**

**Your Answer (Circuit Breaker Pattern):**

```python
class CircuitBreaker:
    states = ["CLOSED", "OPEN", "HALF_OPEN"]

    # CLOSED: Normal operation
    # OPEN: Skip Redis, go direct to DB
    # HALF_OPEN: Test if Redis recovered

    def handle_request(self):
        if state == "OPEN":
            if recovery_time_passed():
                state = "HALF_OPEN"
            else:
                return fallback_to_database()

        try:
            result = call_redis()
            if state == "HALF_OPEN":
                state = "CLOSED"  # Recovery successful
            return result
        except RedisError:
            failure_count += 1
            if failure_count >= threshold:
                state = "OPEN"
            return fallback_to_database()
```

## 🚀 Advanced Topics (Senior+ Level)

### **Cache Invalidation Strategies**

```
1. TTL-based: Automatic expiration
2. Event-based: Invalidate on data changes
3. Tag-based: Group related cache entries
4. Pattern-based: Bulk invalidation with wildcards
```

### **Redis Data Structures & Use Cases**

```
- Strings: Simple key-value, counters
- Hashes: User sessions, object storage
- Lists: Queues, recent items, chat messages
- Sets: Unique items, tags, relationships
- Sorted Sets: Leaderboards, rate limiting, time series
- Streams: Event sourcing, real-time analytics
```

### **Performance Optimization**

```
1. Connection Pooling: Reuse connections
2. Pipelining: Batch multiple commands
3. Lua Scripts: Atomic operations
4. Memory Optimization: Use hashes for objects
5. Partitioning: Shard across multiple Redis instances
```

### **Monitoring & Alerting**

```
Key Metrics to Track:
- Hit Rate: Should be > 80% for effective caching
- Memory Usage: Monitor Redis memory consumption
- Connection Count: Avoid connection pool exhaustion
- Latency: P95 latency should be < 1ms
- Eviction Rate: Monitor cache evictions

Alerts:
- Hit rate drops below 70%
- Memory usage > 80%
- Connection errors increase
- Latency spikes above 5ms
```

## 💡 Interview Pro Tips

### **When they ask: "Design a caching strategy for [specific system]"**

1. **Ask clarifying questions:**
   - Read vs write ratio?
   - Data consistency requirements?
   - Scale (users, QPS)?
   - Acceptable staleness?

2. **Design approach:**
   - Start with cache-aside for simplicity
   - Add write-through for critical data
   - Consider read replicas for read-heavy
   - Plan for cache warming

3. **Address failure scenarios:**
   - Circuit breaker for Redis failures
   - Graceful degradation strategy
   - Monitoring and alerting plan

### **Common Gotchas to Mention:**

1. **Thundering Herd:** Multiple processes fetching same expired key

   ```python
   # Solution: Use lock or jittered TTL
   ttl = base_ttl + random(0, jitter_seconds)
   ```

2. **Cache Stampede:** Cache expires under high load

   ```python
   # Solution: Refresh cache before expiration
   if ttl < refresh_threshold:
       background_refresh()
   ```

3. **Hot Keys:** Few keys getting most traffic

   ```python
   # Solution: Local cache + Redis, or read replicas
   ```

## 🎤 Interview Dialogue Examples

**Interviewer:** "How would you cache user profiles?"

**You:** "I'd use cache-aside pattern with Redis strings or hashes. For each user request:

1. Check Redis with key 'user:{id}'
2. If hit, return cached data
3. If miss, query database, cache result with 1-hour TTL
4. On profile updates, invalidate the cache

I'd monitor hit rates and adjust TTL based on user activity patterns."

**Interviewer:** "What if Redis becomes a bottleneck?"

**You:** "Several strategies:

1. Read replicas for read-heavy workloads
2. Partitioning/sharding across multiple Redis instances
3. Local caching (L1) + Redis (L2) for hot data
4. Connection pooling to reduce overhead
5. Pipelining for batch operations"

## 📊 Production Patterns You Implemented

✅ **Cache-Aside Pattern** - User profiles, configuration data
✅ **Sliding Window Rate Limiting** - API throttling, abuse prevention
✅ **Circuit Breaker Pattern** - Graceful Redis failure handling

These 3 patterns handle 90% of production caching scenarios and are asked in every senior developer interview.

## 🔑 Key Takeaways

1. **Cache-aside is the most common pattern** - master this first
2. **Rate limiting with Redis is essential** - every API needs this
3. **Graceful degradation separates senior from junior** - apps must work when Redis fails
4. **Monitor hit rates religiously** - <80% means ineffective caching
5. **Plan for failures from day 1** - circuit breakers, fallbacks, monitoring

**Your implementations demonstrate production-ready thinking and senior-level system design skills.** 🚀
