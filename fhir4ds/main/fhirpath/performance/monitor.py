"""
Core Performance Monitoring System

This module provides the foundational performance monitoring infrastructure for the
FHIRPath evaluation system. It captures performance metrics with minimal overhead
while providing comprehensive insights for system optimization.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import defaultdict, deque
from enum import Enum
import json

# Optional psutil import for memory monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

from ..exceptions import FHIRPathError

logger = logging.getLogger(__name__)


class MonitoringLevel(Enum):
    """Performance monitoring detail levels"""
    DISABLED = "disabled"
    BASIC = "basic"          # Basic timing and memory
    DETAILED = "detailed"    # Include component-level metrics
    PROFILING = "profiling"  # Full profiling with call traces


@dataclass
class MonitoringConfig:
    """Configuration for performance monitoring system"""
    enabled: bool = True
    level: MonitoringLevel = MonitoringLevel.BASIC
    max_overhead_ms: float = 2.0  # Maximum allowed monitoring overhead
    sample_rate: float = 0.1      # Default 10% sampling rate for production use
    max_history_size: int = 1000  # Maximum metrics history entries
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'evaluation_time_ms': 100.0,
        'memory_usage_mb': 100.0,
        'collection_operation_time_ms': 50.0
    })
    enable_memory_tracking: bool = True
    enable_database_metrics: bool = True
    # Adaptive sampling for high-frequency operations
    enable_adaptive_sampling: bool = True
    high_frequency_threshold: int = 100  # Operations per second to be considered high-frequency
    high_frequency_sample_rate: float = 0.01  # 1% sampling for high-frequency operations


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation"""
    operation_name: str
    start_time: float
    end_time: float
    duration_ms: float
    memory_start_mb: Optional[float] = None
    memory_end_mb: Optional[float] = None
    memory_peak_mb: Optional[float] = None
    component_metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def memory_delta_mb(self) -> Optional[float]:
        """Calculate memory usage delta"""
        if self.memory_start_mb is not None and self.memory_end_mb is not None:
            return self.memory_end_mb - self.memory_start_mb
        return None


class PerformanceMonitor:
    """
    Core performance monitoring system for FHIRPath evaluation

    Provides low-overhead performance monitoring with configurable detail levels
    and automatic bottleneck detection.
    """

    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self._metrics_history: deque = deque(maxlen=self.config.max_history_size)
        self._active_operations: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._component_metrics: Dict[str, List[float]] = defaultdict(list)
        self._alert_callbacks: List[Callable[[str, PerformanceMetrics], None]] = []

        # Operation frequency tracking for adaptive sampling
        self._operation_counts: Dict[str, int] = defaultdict(int)
        self._operation_window_start: float = time.time()
        self._frequency_window_seconds: float = 1.0  # 1-second window for frequency calculation

        # Initialize process for memory monitoring
        self._process = None
        if self.config.enable_memory_tracking and HAS_PSUTIL:
            try:
                self._process = psutil.Process()
            except Exception as e:
                logger.warning(f"Failed to initialize psutil process: {e}")
                self._process = None
        elif self.config.enable_memory_tracking and not HAS_PSUTIL:
            logger.warning("Memory tracking requested but psutil not available")

        logger.info(f"Performance monitor initialized with level: {self.config.level.value}")

    def add_alert_callback(self, callback: Callable[[str, PerformanceMetrics], None]) -> None:
        """Add callback for performance alerts"""
        self._alert_callbacks.append(callback)

    def _get_adaptive_sample_rate(self, operation_name: str) -> float:
        """
        Calculate adaptive sample rate based on operation frequency

        Args:
            operation_name: Name of the operation

        Returns:
            Sample rate (0.0-1.0) based on operation frequency
        """
        if not self.config.enable_adaptive_sampling:
            return self.config.sample_rate

        # Lightweight frequency tracking - minimal overhead
        current_time = time.time()
        elapsed = current_time - self._operation_window_start

        if elapsed >= self._frequency_window_seconds:
            # Reset window without lock (eventual consistency is fine)
            self._operation_counts.clear()
            self._operation_window_start = current_time
            elapsed = 0.001  # Reset elapsed

        # Increment count without full lock (atomic increment)
        self._operation_counts[operation_name] += 1
        count = self._operation_counts[operation_name]

        # Calculate frequency (operations per second)
        frequency = count / max(elapsed, 0.001)  # Avoid division by zero

        # Use high-frequency sample rate if threshold exceeded
        if frequency > self.config.high_frequency_threshold:
            return self.config.high_frequency_sample_rate

        return self.config.sample_rate

    @contextmanager
    def monitor_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for monitoring an operation

        Args:
            operation_name: Name of the operation being monitored
            metadata: Optional metadata about the operation

        Yields:
            Operation ID for additional metric collection
        """
        if not self.config.enabled or self.config.level == MonitoringLevel.DISABLED:
            yield None
            return

        # Use adaptive sampling based on operation frequency
        import random
        sample_rate = self._get_adaptive_sample_rate(operation_name)
        if random.random() > sample_rate:
            yield None
            return

        operation_id = f"{operation_name}_{time.time()}_{threading.get_ident()}"
        start_time = time.time()
        start_memory = self._get_memory_usage() if self.config.enable_memory_tracking else None

        with self._lock:
            self._active_operations[operation_id] = {
                'name': operation_name,
                'start_time': start_time,
                'start_memory': start_memory,
                'metadata': metadata or {},
                'components': {}
            }

        try:
            yield operation_id
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage() if self.config.enable_memory_tracking else None

            with self._lock:
                if operation_id in self._active_operations:
                    op_data = self._active_operations.pop(operation_id)

                    # Create metrics object
                    metrics = PerformanceMetrics(
                        operation_name=operation_name,
                        start_time=start_time,
                        end_time=end_time,
                        duration_ms=(end_time - start_time) * 1000,
                        memory_start_mb=start_memory,
                        memory_end_mb=end_memory,
                        component_metrics=op_data.get('components', {}),
                        metadata=op_data.get('metadata', {})
                    )

                    # Add to history
                    self._metrics_history.append(metrics)

                    # Update component metrics
                    self._component_metrics[operation_name].append(metrics.duration_ms)

                    # Check for alerts
                    self._check_alerts(metrics)

                    logger.debug(f"Operation {operation_name} completed in {metrics.duration_ms:.2f}ms")

    def record_component_metric(self, operation_id: Optional[str], component: str,
                              duration_ms: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record metrics for a component within an operation"""
        if not operation_id or not self.config.enabled:
            return

        with self._lock:
            if operation_id in self._active_operations:
                self._active_operations[operation_id]['components'][component] = {
                    'duration_ms': duration_ms,
                    'metadata': metadata or {}
                }

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics summary"""
        with self._lock:
            if not self._metrics_history:
                return {'status': 'no_data'}

            recent_metrics = list(self._metrics_history)[-100:]  # Last 100 operations

            total_ops = len(recent_metrics)
            avg_duration = sum(m.duration_ms for m in recent_metrics) / total_ops
            max_duration = max(m.duration_ms for m in recent_metrics)
            min_duration = min(m.duration_ms for m in recent_metrics)

            # Memory metrics if available
            memory_metrics = {}
            memory_deltas = [m.memory_delta_mb for m in recent_metrics if m.memory_delta_mb is not None]
            if memory_deltas:
                memory_metrics = {
                    'avg_memory_delta_mb': sum(memory_deltas) / len(memory_deltas),
                    'max_memory_delta_mb': max(memory_deltas),
                    'total_operations_with_memory': len(memory_deltas)
                }

            return {
                'total_operations': total_ops,
                'avg_duration_ms': avg_duration,
                'max_duration_ms': max_duration,
                'min_duration_ms': min_duration,
                'memory_metrics': memory_metrics,
                'active_operations': len(self._active_operations),
                'monitoring_level': self.config.level.value,
                'monitoring_overhead_estimate_ms': self._estimate_overhead()
            }

    def get_component_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics by component"""
        with self._lock:
            result = {}
            for component, durations in self._component_metrics.items():
                if durations:
                    result[component] = {
                        'count': len(durations),
                        'avg_duration_ms': sum(durations) / len(durations),
                        'max_duration_ms': max(durations),
                        'min_duration_ms': min(durations),
                        'total_duration_ms': sum(durations)
                    }
            return result

    def reset_metrics(self) -> None:
        """Reset all collected metrics"""
        with self._lock:
            self._metrics_history.clear()
            self._component_metrics.clear()
            logger.info("Performance metrics reset")

    def export_metrics(self, format: str = 'json') -> Union[str, Dict[str, Any]]:
        """Export metrics in specified format"""
        data = {
            'config': {
                'level': self.config.level.value,
                'enabled': self.config.enabled,
                'sample_rate': self.config.sample_rate
            },
            'current_metrics': self.get_current_metrics(),
            'component_metrics': self.get_component_metrics(),
            'recent_operations': [
                {
                    'operation': m.operation_name,
                    'duration_ms': m.duration_ms,
                    'memory_delta_mb': m.memory_delta_mb,
                    'timestamp': m.start_time
                }
                for m in list(self._metrics_history)[-50:]  # Last 50 operations
            ]
        }

        if format.lower() == 'json':
            return json.dumps(data, indent=2)
        return data

    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB"""
        if not self._process:
            return None

        try:
            return self._process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")
            return None

    def _check_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check if metrics trigger any alerts"""
        for threshold_name, threshold_value in self.config.alert_thresholds.items():
            triggered = False

            if threshold_name == 'evaluation_time_ms' and metrics.duration_ms > threshold_value:
                triggered = True
            elif threshold_name == 'memory_usage_mb' and metrics.memory_delta_mb:
                if metrics.memory_delta_mb > threshold_value:
                    triggered = True

            if triggered:
                alert_message = f"Performance threshold exceeded: {threshold_name} = {threshold_value}"
                logger.warning(f"{alert_message} for operation {metrics.operation_name}")

                # Call alert callbacks
                for callback in self._alert_callbacks:
                    try:
                        callback(alert_message, metrics)
                    except Exception as e:
                        logger.error(f"Alert callback failed: {e}")

    def _estimate_overhead(self) -> float:
        """Estimate monitoring overhead in milliseconds"""
        # Simple estimation based on monitoring level
        if self.config.level == MonitoringLevel.DISABLED:
            return 0.0
        elif self.config.level == MonitoringLevel.BASIC:
            return 0.1
        elif self.config.level == MonitoringLevel.DETAILED:
            return 0.5
        else:  # PROFILING
            return 1.0


def create_performance_monitor(config: Optional[MonitoringConfig] = None) -> PerformanceMonitor:
    """Create a performance monitor with default or custom configuration"""
    return PerformanceMonitor(config)


# Global monitor instance for convenient access
_global_monitor: Optional[PerformanceMonitor] = None


def get_global_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = create_performance_monitor()
    return _global_monitor


def configure_global_monitor(config: MonitoringConfig) -> None:
    """Configure the global performance monitor"""
    global _global_monitor
    _global_monitor = create_performance_monitor(config)


@contextmanager
def monitor(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Convenient context manager using global monitor"""
    with get_global_monitor().monitor_operation(operation_name, metadata) as op_id:
        yield op_id