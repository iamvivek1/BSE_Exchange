"""
Monitoring Service

Provides comprehensive monitoring, metrics collection, and health checks
for the BSE data optimization system.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Health check configuration and result."""
    name: str
    check_function: Callable[[], bool]
    description: str
    timeout: float = 5.0
    last_check: Optional[datetime] = None
    last_result: bool = True
    last_error: Optional[str] = None
    consecutive_failures: int = 0


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """System alert."""
    id: str
    level: AlertLevel
    message: str
    timestamp: datetime
    component: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
    
    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                self.logger.info("Circuit breaker entering half-open state")
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful function execution."""
        if self.state == "half-open":
            self.state = "closed"
            self.logger.info("Circuit breaker reset to closed state")
        
        self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed function execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "recovery_timeout": self.recovery_timeout
        }


class MetricsCollector:
    """
    Collects and stores system metrics.
    """
    
    def __init__(self, max_points_per_metric: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_points_per_metric: Maximum data points to store per metric
        """
        self.max_points_per_metric = max_points_per_metric
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        
        self.logger = logging.getLogger(f"{__name__}.MetricsCollector")
    
    def record_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """
        Record a counter metric.
        
        Args:
            name: Metric name
            value: Counter increment value
            tags: Optional tags for the metric
        """
        self.counters[name] += value
        
        metric_point = MetricPoint(
            timestamp=datetime.now(),
            value=self.counters[name],
            tags=tags or {}
        )
        
        self.metrics[name].append(metric_point)
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a gauge metric.
        
        Args:
            name: Metric name
            value: Gauge value
            tags: Optional tags for the metric
        """
        self.gauges[name] = value
        
        metric_point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            tags=tags or {}
        )
        
        self.metrics[name].append(metric_point)
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a timing metric.
        
        Args:
            name: Metric name
            duration: Duration in seconds
            tags: Optional tags for the metric
        """
        metric_point = MetricPoint(
            timestamp=datetime.now(),
            value=duration,
            tags=tags or {}
        )
        
        self.metrics[name].append(metric_point)
    
    def get_metric_summary(self, name: str, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get summary statistics for a metric.
        
        Args:
            name: Metric name
            time_window: Optional time window to filter data
            
        Returns:
            Dictionary with metric summary
        """
        if name not in self.metrics:
            return {"error": f"Metric {name} not found"}
        
        points = list(self.metrics[name])
        
        # Filter by time window if specified
        if time_window:
            cutoff_time = datetime.now() - time_window
            points = [p for p in points if p.timestamp >= cutoff_time]
        
        if not points:
            return {"error": "No data points in specified time window"}
        
        values = [p.value for p in points]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
            "first_timestamp": points[0].timestamp.isoformat(),
            "last_timestamp": points[-1].timestamp.isoformat()
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metric values."""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "metrics_count": {name: len(points) for name, points in self.metrics.items()}
        }


class MonitoringService:
    """
    Comprehensive monitoring service for the BSE data optimization system.
    """
    
    def __init__(self):
        """Initialize monitoring service."""
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.metrics = MetricsCollector()
        self.health_checks: Dict[str, HealthCheck] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.alerts: List[Alert] = []
        
        # Monitoring state
        self.is_running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Alert thresholds
        self.alert_thresholds = {
            "api_response_time": 5.0,  # seconds
            "cache_hit_rate": 0.8,     # 80%
            "websocket_connections": 1000,
            "error_rate": 0.1          # 10%
        }
        
        self.logger.info("MonitoringService initialized")
    
    def add_health_check(self, name: str, check_function: Callable[[], bool], 
                        description: str, timeout: float = 5.0):
        """
        Add a health check.
        
        Args:
            name: Unique name for the health check
            check_function: Function that returns True if healthy
            description: Description of what the check validates
            timeout: Timeout for the check in seconds
        """
        self.health_checks[name] = HealthCheck(
            name=name,
            check_function=check_function,
            description=description,
            timeout=timeout
        )
        
        self.logger.info(f"Added health check: {name}")
    
    def add_circuit_breaker(self, name: str, failure_threshold: int = 5, 
                           recovery_timeout: int = 60, expected_exception: type = Exception):
        """
        Add a circuit breaker.
        
        Args:
            name: Unique name for the circuit breaker
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers the breaker
        """
        self.circuit_breakers[name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )
        
        self.logger.info(f"Added circuit breaker: {name}")
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self.circuit_breakers.get(name)
    
    def run_health_checks(self) -> Dict[str, Any]:
        """
        Run all health checks and return results.
        
        Returns:
            Dictionary with health check results
        """
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, check in self.health_checks.items():
            try:
                start_time = time.time()
                
                # Run check with timeout
                result = self._run_check_with_timeout(check)
                
                duration = time.time() - start_time
                
                check.last_check = datetime.now()
                check.last_result = result
                
                if result:
                    check.consecutive_failures = 0
                    check.last_error = None
                    status = HealthStatus.HEALTHY
                else:
                    check.consecutive_failures += 1
                    status = HealthStatus.DEGRADED if check.consecutive_failures < 3 else HealthStatus.UNHEALTHY
                    
                    if status == HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.UNHEALTHY
                    elif status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                
                results[name] = {
                    "status": status.value,
                    "description": check.description,
                    "last_check": check.last_check.isoformat(),
                    "consecutive_failures": check.consecutive_failures,
                    "duration": duration,
                    "error": check.last_error
                }
                
            except Exception as e:
                check.last_error = str(e)
                check.consecutive_failures += 1
                check.last_check = datetime.now()
                check.last_result = False
                
                overall_status = HealthStatus.UNHEALTHY
                
                results[name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "description": check.description,
                    "last_check": check.last_check.isoformat(),
                    "consecutive_failures": check.consecutive_failures,
                    "error": str(e)
                }
                
                self.logger.error(f"Health check {name} failed: {e}")
        
        return {
            "overall_status": overall_status.value,
            "checks": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _run_check_with_timeout(self, check: HealthCheck) -> bool:
        """Run a health check with timeout."""
        import threading
        import queue
        
        result_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def run_check():
            try:
                result = check.check_function()
                result_queue.put(result)
            except Exception as e:
                exception_queue.put(e)
        
        # Start check in separate thread
        thread = threading.Thread(target=run_check)
        thread.daemon = True
        thread.start()
        
        # Wait for result with timeout
        thread.join(timeout=check.timeout)
        
        if thread.is_alive():
            # Timeout occurred
            check.last_error = f"Timeout after {check.timeout}s"
            return False
        
        # Check if exception occurred
        if not exception_queue.empty():
            exception = exception_queue.get()
            check.last_error = str(exception)
            return False
        
        # Check if result is available
        if not result_queue.empty():
            return result_queue.get()
        
        # No result available (shouldn't happen)
        check.last_error = "No result returned"
        return False
    
    def create_alert(self, level: AlertLevel, message: str, component: str) -> str:
        """
        Create a new alert.
        
        Args:
            level: Alert severity level
            message: Alert message
            component: Component that generated the alert
            
        Returns:
            Alert ID
        """
        alert_id = f"{component}_{int(time.time())}"
        
        alert = Alert(
            id=alert_id,
            level=level,
            message=message,
            timestamp=datetime.now(),
            component=component
        )
        
        self.alerts.append(alert)
        
        # Log alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }[level]
        
        self.logger.log(log_level, f"ALERT [{level.value.upper()}] {component}: {message}")
        
        return alert_id
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert by ID.
        
        Args:
            alert_id: Alert ID to resolve
            
        Returns:
            True if alert was found and resolved
        """
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                self.logger.info(f"Resolved alert {alert_id}")
                return True
        
        return False
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active (unresolved) alerts."""
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        
        return [
            {
                "id": alert.id,
                "level": alert.level.value,
                "message": alert.message,
                "component": alert.component,
                "timestamp": alert.timestamp.isoformat()
            }
            for alert in active_alerts
        ]
    
    def check_thresholds(self):
        """Check metrics against alert thresholds."""
        # Check API response time
        api_timing = self.metrics.get_metric_summary("api_response_time", timedelta(minutes=5))
        if "avg" in api_timing and api_timing["avg"] > self.alert_thresholds["api_response_time"]:
            self.create_alert(
                AlertLevel.WARNING,
                f"High API response time: {api_timing['avg']:.2f}s (threshold: {self.alert_thresholds['api_response_time']}s)",
                "api"
            )
        
        # Check cache hit rate
        cache_metrics = self.metrics.get_all_metrics()
        if "cache_hits" in cache_metrics["counters"] and "cache_misses" in cache_metrics["counters"]:
            total_requests = cache_metrics["counters"]["cache_hits"] + cache_metrics["counters"]["cache_misses"]
            if total_requests > 0:
                hit_rate = cache_metrics["counters"]["cache_hits"] / total_requests
                if hit_rate < self.alert_thresholds["cache_hit_rate"]:
                    self.create_alert(
                        AlertLevel.WARNING,
                        f"Low cache hit rate: {hit_rate:.2%} (threshold: {self.alert_thresholds['cache_hit_rate']:.2%})",
                        "cache"
                    )
    
    def start_monitoring(self, check_interval: int = 30):
        """
        Start continuous monitoring.
        
        Args:
            check_interval: Interval between checks in seconds
        """
        if self.is_running:
            self.logger.warning("Monitoring already running")
            return
        
        self.is_running = True
        
        def monitoring_loop():
            self.logger.info(f"Starting monitoring loop with {check_interval}s interval")
            
            while self.is_running:
                try:
                    # Run health checks
                    self.run_health_checks()
                    
                    # Check alert thresholds
                    self.check_thresholds()
                    
                    time.sleep(check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(check_interval)
        
        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("Monitoring service started")
    
    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.is_running = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("Monitoring service stopped")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        health_results = self.run_health_checks()
        
        return {
            "health": health_results,
            "metrics": self.metrics.get_all_metrics(),
            "circuit_breakers": {
                name: breaker.get_state() 
                for name, breaker in self.circuit_breakers.items()
            },
            "active_alerts": self.get_active_alerts(),
            "monitoring_active": self.is_running,
            "timestamp": datetime.now().isoformat()
        }