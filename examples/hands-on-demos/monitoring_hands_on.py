"""
🎯 Monitoring & Observability - Hands-on Implementation

This implements production-grade monitoring patterns used by major tech companies.
YOU'LL learn the 3 pillars of observability: Metrics, Logs, and Traces.

Key concepts you'll implement:
1. Prometheus Metrics (RED method: Rate, Errors, Duration)
2. Structured Logging with Correlation IDs
3. Distributed Tracing (OpenTelemetry pattern)
4. Health Checks and Service Discovery
5. Custom Dashboards and Alerting

This shows how Netflix, Google, and Uber monitor production systems!
"""

import asyncio
import json
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

# ============================================================================
# 📊 PROMETHEUS METRICS SYSTEM
# ============================================================================


class MetricType(str, Enum):
    """Types of metrics we can collect."""

    COUNTER = "counter"  # Always increasing (requests, errors)
    GAUGE = "gauge"  # Can go up/down (CPU, memory)
    HISTOGRAM = "histogram"  # Distribution of values (response times)
    SUMMARY = "summary"  # Similar to histogram but with percentiles


@dataclass
class Metric:
    """Individual metric data point."""

    name: str
    value: float
    labels: dict[str, str]
    timestamp: float
    metric_type: MetricType


class PrometheusMetrics:
    """
    YOUR TASK: Implement Prometheus-style metrics collection

    Used by: Google, Netflix, Kubernetes, Docker

    Key patterns:
    - RED Method: Rate, Errors, Duration
    - USE Method: Utilization, Saturation, Errors
    - Labels for multi-dimensional data
    """

    def __init__(self):
        self.counters: dict[str, float] = defaultdict(float)
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list[float]] = defaultdict(list)
        self.metrics_history: list[Metric] = []

        print("📊 Prometheus Metrics System initialized")

    def counter_inc(self, name: str, labels: dict[str, str] = None, value: float = 1.0):
        """
        YOUR TASK: Increment counter metric

        Counters always go up (requests, errors, bytes sent)
        """
        labels = labels or {}
        key = f"{name}_{self._labels_to_string(labels)}"

        # TODO: YOU implement counter increment
        self.counters[key] += value

        # Record metric
        self.metrics_history.append(
            Metric(
                name=name,
                value=self.counters[key],
                labels=labels,
                timestamp=time.time(),
                metric_type=MetricType.COUNTER,
            )
        )

        print(f"📊 Counter {name}{labels}: {self.counters[key]}")

    def gauge_set(self, name: str, value: float, labels: dict[str, str] = None):
        """
        YOUR TASK: Set gauge metric

        Gauges can go up/down (CPU usage, memory, queue size)
        """
        labels = labels or {}
        key = f"{name}_{self._labels_to_string(labels)}"

        # TODO: YOU implement gauge setting
        self.gauges[key] = value

        # Record metric
        self.metrics_history.append(
            Metric(
                name=name,
                value=value,
                labels=labels,
                timestamp=time.time(),
                metric_type=MetricType.GAUGE,
            )
        )

        print(f"📊 Gauge {name}{labels}: {value}")

    def histogram_observe(self, name: str, value: float, labels: dict[str, str] = None):
        """
        YOUR TASK: Record histogram observation

        Histograms track distribution (response times, request sizes)
        """
        labels = labels or {}
        key = f"{name}_{self._labels_to_string(labels)}"

        # TODO: YOU implement histogram observation
        self.histograms[key].append(value)

        # Keep only recent observations (sliding window)
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]

        # Record metric
        self.metrics_history.append(
            Metric(
                name=name,
                value=value,
                labels=labels,
                timestamp=time.time(),
                metric_type=MetricType.HISTOGRAM,
            )
        )

        print(f"📊 Histogram {name}{labels}: {value}")

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Get current metrics snapshot for Prometheus scraping."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                name: {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values) if values else 0,
                    "p50": self._percentile(values, 0.5),
                    "p95": self._percentile(values, 0.95),
                    "p99": self._percentile(values, 0.99),
                }
                for name, values in self.histograms.items()
                if values
            },
        }
        return snapshot

    def _labels_to_string(self, labels: dict[str, str]) -> str:
        """Convert labels dict to string for key generation."""
        if not labels:
            return ""
        return "_".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _percentile(self, values: list[float], p: float) -> float:
        """Calculate percentile from list of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(p * (len(sorted_values) - 1))
        return sorted_values[index]


# ============================================================================
# 📝 STRUCTURED LOGGING SYSTEM
# ============================================================================


class LogLevel(str, Enum):
    """Log levels following standard hierarchy."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: str
    level: LogLevel
    message: str
    correlation_id: str
    service: str
    module: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    extra_fields: dict[str, Any] = None


class StructuredLogger:
    """
    YOUR TASK: Implement structured logging with correlation IDs

    Used by: Uber, Airbnb, Netflix for debugging distributed systems

    Key features:
    - JSON format for machine parsing
    - Correlation IDs to trace requests across services
    - Contextual information for debugging
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.log_entries: list[LogEntry] = []
        self.current_correlation_id: Optional[str] = None

        print(f"📝 Structured Logger initialized for service: {service_name}")

    @contextmanager
    def correlation_context(self, correlation_id: str = None):
        """
        YOUR TASK: Context manager for correlation ID

        This ensures all logs within a context share the same correlation ID
        """
        old_correlation_id = self.current_correlation_id
        self.current_correlation_id = correlation_id or str(uuid.uuid4())

        print(f"📝 Starting correlation context: {self.current_correlation_id}")

        try:
            yield self.current_correlation_id
        finally:
            self.current_correlation_id = old_correlation_id

    def log(
        self,
        level: LogLevel,
        message: str,
        module: str = "main",
        user_id: str = None,
        request_id: str = None,
        **extra_fields,
    ):
        """
        YOUR TASK: Create structured log entry

        All logs should be JSON for easy parsing by log aggregators
        """
        # TODO: YOU implement structured logging
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level,
            message=message,
            correlation_id=self.current_correlation_id or "no-correlation",
            service=self.service_name,
            module=module,
            user_id=user_id,
            request_id=request_id,
            extra_fields=extra_fields or {},
        )

        # Store for analysis
        self.log_entries.append(log_entry)

        # Print as JSON (in production, send to log aggregator)
        log_dict = asdict(log_entry)
        print(f"📝 {json.dumps(log_dict)}")

    def info(self, message: str, **kwargs):
        """Log info level message."""
        self.log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        self.log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error level message."""
        self.log(LogLevel.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        self.log(LogLevel.DEBUG, message, **kwargs)

    def get_logs_by_correlation_id(self, correlation_id: str) -> list[LogEntry]:
        """Get all logs for a specific correlation ID (trace reconstruction)."""
        return [log for log in self.log_entries if log.correlation_id == correlation_id]


# ============================================================================
# 🔍 DISTRIBUTED TRACING SYSTEM
# ============================================================================


@dataclass
class Span:
    """Distributed tracing span."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    tags: dict[str, str] = None
    logs: list[dict[str, Any]] = None

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000


class DistributedTracer:
    """
    YOUR TASK: Implement distributed tracing (OpenTelemetry pattern)

    Used by: Google (Dapper), Uber (Jaeger), Twitter (Zipkin)

    Concept:
    - Trace = end-to-end request journey
    - Span = individual operation within trace
    - Parent-child relationship shows call hierarchy
    """

    def __init__(self):
        self.active_spans: dict[str, Span] = {}
        self.completed_traces: dict[str, list[Span]] = defaultdict(list)

        print("🔍 Distributed Tracer initialized")

    def start_span(
        self,
        operation_name: str,
        trace_id: str = None,
        parent_span_id: str = None,
        tags: dict[str, str] = None,
    ) -> Span:
        """
        YOUR TASK: Start a new span

        Each operation (DB query, HTTP call, etc.) gets its own span
        """
        # TODO: YOU implement span creation
        trace_id = trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            tags=tags or {},
            logs=[],
        )

        self.active_spans[span_id] = span
        print(f"🔍 Started span: {operation_name} (trace: {trace_id[:8]}...)")

        return span

    def finish_span(self, span: Span, tags: dict[str, str] = None):
        """
        YOUR TASK: Finish span and record duration
        """
        # TODO: YOU implement span finishing
        span.end_time = time.time()

        if tags:
            span.tags.update(tags)

        # Move to completed traces
        if span.span_id in self.active_spans:
            del self.active_spans[span.span_id]

        self.completed_traces[span.trace_id].append(span)

        print(f"🔍 Finished span: {span.operation_name} ({span.duration_ms:.2f}ms)")

    def add_span_log(self, span: Span, event: str, fields: dict[str, Any] = None):
        """Add log entry to span."""
        log_entry = {"timestamp": time.time(), "event": event, "fields": fields or {}}
        span.logs.append(log_entry)

    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        trace_id: str = None,
        parent_span_id: str = None,
        tags: dict[str, str] = None,
    ):
        """Context manager for automatic span lifecycle."""
        span = self.start_span(operation_name, trace_id, parent_span_id, tags)
        try:
            yield span
        except Exception as e:
            span.tags["error"] = "true"
            span.tags["error.message"] = str(e)
            raise
        finally:
            self.finish_span(span)

    def get_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace (for debugging)."""
        return self.completed_traces.get(trace_id, [])


# ============================================================================
# 🏥 HEALTH CHECK SYSTEM
# ============================================================================


class HealthStatus(str, Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Individual health check result."""

    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    metadata: dict[str, Any] = None


class HealthChecker:
    """
    YOUR TASK: Implement comprehensive health checks

    Used by: Kubernetes probes, load balancers, service discovery

    Types:
    - Liveness: Is the service running?
    - Readiness: Can the service handle requests?
    - Startup: Has the service finished initializing?
    """

    def __init__(self):
        self.checks: dict[str, callable] = {}
        print("🏥 Health Checker initialized")

    def register_check(self, name: str, check_func: callable):
        """
        YOUR TASK: Register health check function

        Each dependency (DB, Redis, external API) should have a health check
        """
        self.checks[name] = check_func
        print(f"🏥 Registered health check: {name}")

    async def run_check(self, name: str) -> HealthCheck:
        """
        YOUR TASK: Run individual health check
        """
        if name not in self.checks:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Health check not found",
                response_time_ms=0,
            )

        start_time = time.time()

        try:
            # TODO: YOU implement health check execution
            check_func = self.checks[name]
            result = (
                await check_func()
                if asyncio.iscoroutinefunction(check_func)
                else check_func()
            )

            response_time = (time.time() - start_time) * 1000

            if result is True:
                return HealthCheck(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message="OK",
                    response_time_ms=response_time,
                )
            elif isinstance(result, dict):
                return HealthCheck(
                    name=name,
                    status=HealthStatus(result.get("status", "healthy")),
                    message=result.get("message", "OK"),
                    response_time_ms=response_time,
                    metadata=result.get("metadata"),
                )
            else:
                return HealthCheck(
                    name=name,
                    status=HealthStatus.DEGRADED,
                    message=str(result),
                    response_time_ms=response_time,
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e!s}",
                response_time_ms=response_time,
            )

    async def run_all_checks(self) -> dict[str, HealthCheck]:
        """Run all registered health checks."""
        results = {}

        for name in self.checks:
            results[name] = await self.run_check(name)
            print(
                f"🏥 {name}: {results[name].status.value} ({results[name].response_time_ms:.2f}ms)"
            )

        return results


# ============================================================================
# 📈 MONITORING DASHBOARD
# ============================================================================


class MonitoringDashboard:
    """
    YOUR TASK: Create monitoring dashboard with key metrics

    This aggregates all monitoring data for easy visualization
    """

    def __init__(
        self,
        metrics: PrometheusMetrics,
        logger: StructuredLogger,
        tracer: DistributedTracer,
        health_checker: HealthChecker,
    ):
        self.metrics = metrics
        self.logger = logger
        self.tracer = tracer
        self.health_checker = health_checker

        print("📈 Monitoring Dashboard initialized")

    async def get_dashboard_data(self) -> dict[str, Any]:
        """
        YOUR TASK: Generate dashboard data

        Real dashboards show: error rates, response times, throughput, health
        """
        # Get current metrics
        metrics_snapshot = self.metrics.get_metrics_snapshot()

        # Get health status
        health_results = await self.health_checker.run_all_checks()
        overall_health = HealthStatus.HEALTHY
        for check in health_results.values():
            if check.status == HealthStatus.UNHEALTHY:
                overall_health = HealthStatus.UNHEALTHY
                break
            elif check.status == HealthStatus.DEGRADED:
                overall_health = HealthStatus.DEGRADED

        # Calculate key SLIs (Service Level Indicators)
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service_health": {
                "overall_status": overall_health.value,
                "checks": {
                    name: asdict(check) for name, check in health_results.items()
                },
            },
            "metrics": metrics_snapshot,
            "sli_summary": {
                "availability": self._calculate_availability(),
                "error_rate": self._calculate_error_rate(),
                "response_time_p95": self._calculate_response_time_p95(),
                "throughput_rpm": self._calculate_throughput(),
            },
            "active_traces": len(self.tracer.active_spans),
            "completed_traces": len(self.tracer.completed_traces),
            "log_entries_last_hour": len(
                [
                    log
                    for log in self.logger.log_entries
                    if datetime.fromisoformat(log.timestamp.replace("Z", "+00:00"))
                    > datetime.utcnow().replace(tzinfo=None) - timedelta(hours=1)
                ]
            ),
        }

        return dashboard_data

    def _calculate_availability(self) -> float:
        """Calculate service availability percentage."""
        # Simplified calculation - in production, use actual uptime data
        return 99.9

    def _calculate_error_rate(self) -> float:
        """Calculate error rate percentage."""
        error_logs = [
            log
            for log in self.logger.log_entries
            if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]
        total_logs = len(self.logger.log_entries)
        return (len(error_logs) / max(total_logs, 1)) * 100

    def _calculate_response_time_p95(self) -> float:
        """Calculate 95th percentile response time."""
        # Look for response time histogram
        for name, values in self.metrics.histograms.items():
            if "response_time" in name and values:
                return self.metrics._percentile(values, 0.95)
        return 0.0

    def _calculate_throughput(self) -> float:
        """Calculate requests per minute."""
        # Simplified - count recent requests
        recent_logs = [
            log
            for log in self.logger.log_entries
            if datetime.fromisoformat(log.timestamp.replace("Z", "+00:00"))
            > datetime.utcnow().replace(tzinfo=None) - timedelta(minutes=1)
        ]
        return len(recent_logs)


# ============================================================================
# 🧪 TESTING YOUR MONITORING IMPLEMENTATION
# ============================================================================


async def test_prometheus_metrics():
    """Test YOUR Prometheus metrics implementation."""
    print("\n🧪 Testing YOUR Prometheus Metrics")
    print("=" * 50)

    metrics = PrometheusMetrics()

    # Test different metric types
    print("\n1. Testing Counter metrics...")
    metrics.counter_inc("http_requests_total", {"method": "GET", "status": "200"})
    metrics.counter_inc("http_requests_total", {"method": "GET", "status": "200"})
    metrics.counter_inc("http_requests_total", {"method": "POST", "status": "201"})

    print("\n2. Testing Gauge metrics...")
    metrics.gauge_set("memory_usage_bytes", 1024 * 1024 * 500)  # 500MB
    metrics.gauge_set("cpu_usage_percent", 75.5)

    print("\n3. Testing Histogram metrics...")
    for response_time in [0.1, 0.2, 0.15, 0.3, 0.8, 1.2, 0.05]:
        metrics.histogram_observe("http_request_duration_seconds", response_time)

    print("\n4. Metrics snapshot:")
    snapshot = metrics.get_metrics_snapshot()
    print(json.dumps(snapshot, indent=2))


async def test_structured_logging():
    """Test YOUR structured logging implementation."""
    print("\n🧪 Testing YOUR Structured Logging")
    print("=" * 50)

    logger = StructuredLogger("image-analyzer")

    # Test logging with correlation context
    with logger.correlation_context() as correlation_id:
        logger.info(
            "Processing image analysis request",
            module="api",
            user_id="user123",
            request_id="req456",
        )
        logger.debug("Connecting to database", module="db")
        logger.warning("High memory usage detected", module="monitoring", memory_mb=800)
        logger.info("Image analysis completed", module="api", processing_time_ms=1250)

    print(
        f"\n📝 Found {len(logger.get_logs_by_correlation_id(correlation_id))} logs with correlation ID"
    )


async def test_distributed_tracing():
    """Test YOUR distributed tracing implementation."""
    print("\n🧪 Testing YOUR Distributed Tracing")
    print("=" * 50)

    tracer = DistributedTracer()

    # Simulate distributed request
    with tracer.trace_operation(
        "http_request", tags={"method": "POST", "endpoint": "/analyze"}
    ) as root_span:
        with tracer.trace_operation(
            "db_query", trace_id=root_span.trace_id, parent_span_id=root_span.span_id
        ) as db_span:
            await asyncio.sleep(0.05)  # Simulate DB query
            tracer.add_span_log(db_span, "query_executed", {"rows": 1})

        with tracer.trace_operation(
            "ai_processing",
            trace_id=root_span.trace_id,
            parent_span_id=root_span.span_id,
        ) as ai_span:
            await asyncio.sleep(0.1)  # Simulate AI processing
            tracer.add_span_log(ai_span, "model_inference", {"confidence": 0.95})

    # Show trace
    trace = tracer.get_trace(root_span.trace_id)
    print(f"\n🔍 Trace contains {len(trace)} spans:")
    for span in trace:
        print(f"  - {span.operation_name}: {span.duration_ms:.2f}ms")


async def test_health_checks():
    """Test YOUR health check implementation."""
    print("\n🧪 Testing YOUR Health Checks")
    print("=" * 50)

    health_checker = HealthChecker()

    # Register mock health checks
    async def database_check():
        await asyncio.sleep(0.01)  # Simulate DB ping
        return {
            "status": "healthy",
            "message": "Database responding",
            "metadata": {"connections": 5},
        }

    def memory_check():
        import psutil

        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 90:
            return {
                "status": "unhealthy",
                "message": f"High memory usage: {memory_percent}%",
            }
        elif memory_percent > 80:
            return {
                "status": "degraded",
                "message": f"Elevated memory usage: {memory_percent}%",
            }
        return {
            "status": "healthy",
            "message": f"Memory usage normal: {memory_percent}%",
        }

    def disk_check():
        return True  # Simple healthy check

    health_checker.register_check("database", database_check)
    health_checker.register_check("memory", memory_check)
    health_checker.register_check("disk", disk_check)

    # Run all checks
    results = await health_checker.run_all_checks()
    print(f"\n🏥 Health check results: {len(results)} checks completed")


async def test_monitoring_dashboard():
    """Test YOUR monitoring dashboard."""
    print("\n🧪 Testing YOUR Monitoring Dashboard")
    print("=" * 50)

    # Create full monitoring stack
    metrics = PrometheusMetrics()
    logger = StructuredLogger("test-service")
    tracer = DistributedTracer()
    health_checker = HealthChecker()

    # Add some test data
    metrics.counter_inc("requests_total", {"status": "200"}, 100)
    metrics.gauge_set("memory_usage", 75.0)
    metrics.histogram_observe("response_time", 0.250)

    logger.info("Test log entry", module="test")

    # Simple health check
    health_checker.register_check("test", lambda: True)

    # Create dashboard
    dashboard = MonitoringDashboard(metrics, logger, tracer, health_checker)
    dashboard_data = await dashboard.get_dashboard_data()

    print("📈 Dashboard data generated:")
    print(json.dumps(dashboard_data, indent=2))


# ============================================================================
# 🏃 MAIN TESTING FUNCTION
# ============================================================================


async def main():
    """Run all monitoring tests."""
    print("🎯 Monitoring & Observability - YOUR Implementation")
    print("=" * 70)

    # Test all monitoring components
    await test_prometheus_metrics()
    await test_structured_logging()
    await test_distributed_tracing()
    await test_health_checks()
    await test_monitoring_dashboard()

    print("\n" + "=" * 70)
    print("🎉 Monitoring & Observability Implementation Complete!")
    print(
        """
YOUR TASKS COMPLETED:
✅ Prometheus Metrics - RED method (Rate, Errors, Duration)
✅ Structured Logging - JSON logs with correlation IDs
✅ Distributed Tracing - Request journey across services
✅ Health Checks - Liveness, readiness, and dependency monitoring
✅ Monitoring Dashboard - Unified view of system health

PRODUCTION PATTERNS LEARNED:
🎯 Netflix-style metrics collection and aggregation
🎯 Uber-style structured logging for debugging
🎯 Google-style distributed tracing (Dapper pattern)
🎯 Kubernetes-style health checks for reliability
🎯 SRE-style SLI/SLO monitoring and alerting

NEXT STEPS:
- Integrate with Grafana for visualization
- Set up alerting rules (Prometheus AlertManager)
- Add log aggregation (ELK/EFK stack)
- Implement SLI/SLO tracking
- Set up on-call runbooks

This is how real production systems monitor MILLIONS of requests! 🚀
    """
    )


if __name__ == "__main__":
    # Install required package for health checks
    try:
        import psutil
    except ImportError:
        print("Installing psutil for system monitoring...")
        import subprocess

        subprocess.check_call(["pip", "install", "psutil"])

    asyncio.run(main())
