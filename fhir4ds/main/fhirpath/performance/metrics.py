"""
Performance Metrics Collection and Analysis

This module provides comprehensive metrics collection, analysis, and bottleneck detection
for the FHIRPath evaluation system. It includes automated performance reporting and
optimization recommendations for population-scale healthcare analytics.
"""

import time
import statistics
import threading
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
import json

from .monitor import PerformanceMetrics, PerformanceMonitor
from .profiler import ProfileResult, FHIRPathProfiler

logger = logging.getLogger(__name__)


@dataclass
class MetricsSummary:
    """Summary of performance metrics over a time period"""
    period_start: datetime
    period_end: datetime
    total_operations: int
    avg_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    max_duration_ms: float
    min_duration_ms: float
    total_memory_delta_mb: float
    operation_types: Dict[str, int]
    error_rate: float = 0.0


@dataclass
class BottleneckInfo:
    """Information about a detected performance bottleneck"""
    component: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    avg_duration_ms: float
    impact_score: float  # 0-100 scale
    frequency: int
    description: str
    recommendations: List[str]
    first_seen: datetime
    last_seen: datetime


@dataclass
class PerformanceReport:
    """Comprehensive performance report"""
    report_id: str
    generated_at: datetime
    period_summary: MetricsSummary
    bottlenecks: List[BottleneckInfo]
    trends: Dict[str, Any]
    recommendations: List[str]
    compliance_status: Dict[str, bool]
    detailed_metrics: Dict[str, Any]


class MetricsCollector:
    """
    Comprehensive metrics collection and analysis system

    Collects performance data from monitors and profilers to provide
    unified metrics and insights.
    """

    def __init__(self, monitor: Optional[PerformanceMonitor] = None,
                 profiler: Optional[FHIRPathProfiler] = None):
        self.monitor = monitor
        self.profiler = profiler
        self._metrics_buffer: deque = deque(maxlen=10000)
        self._profile_buffer: deque = deque(maxlen=1000)
        self._lock = threading.RLock()
        self._collection_start = datetime.now()

        logger.info("Metrics collector initialized")

    def collect_metrics(self) -> None:
        """Collect current metrics from monitor and profiler"""
        if not self.monitor and not self.profiler:
            logger.warning("No monitor or profiler configured")
            return

        with self._lock:
            # Collect from monitor
            if self.monitor:
                current_metrics = self.monitor.get_current_metrics()
                if current_metrics.get('status') != 'no_data':
                    self._metrics_buffer.append({
                        'timestamp': datetime.now(),
                        'source': 'monitor',
                        'data': current_metrics
                    })

            # Collect from profiler
            if self.profiler:
                recent_profiles = self.profiler.get_recent_profiles(count=5)
                for profile in recent_profiles:
                    self._profile_buffer.append({
                        'timestamp': datetime.now(),
                        'source': 'profiler',
                        'data': profile
                    })

    def generate_summary(self, hours: int = 1) -> MetricsSummary:
        """Generate metrics summary for the specified time period"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        with self._lock:
            # Filter metrics within time period
            relevant_metrics = [
                m for m in self._metrics_buffer
                if start_time <= m['timestamp'] <= end_time
            ]

            if not relevant_metrics:
                return MetricsSummary(
                    period_start=start_time,
                    period_end=end_time,
                    total_operations=0,
                    avg_duration_ms=0.0,
                    median_duration_ms=0.0,
                    p95_duration_ms=0.0,
                    p99_duration_ms=0.0,
                    max_duration_ms=0.0,
                    min_duration_ms=0.0,
                    total_memory_delta_mb=0.0,
                    operation_types={}
                )

            # Extract durations and operation types
            durations = []
            operation_types = defaultdict(int)
            total_memory_delta = 0.0

            for metric in relevant_metrics:
                data = metric['data']
                if 'avg_duration_ms' in data:
                    durations.append(data['avg_duration_ms'])

                # Count operation types if available
                if 'component_metrics' in data:
                    for op_type in data['component_metrics'].keys():
                        operation_types[op_type] += 1

                # Sum memory deltas
                if 'memory_metrics' in data and data['memory_metrics']:
                    total_memory_delta += data['memory_metrics'].get('avg_memory_delta_mb', 0.0)

            # Calculate statistics
            if durations:
                return MetricsSummary(
                    period_start=start_time,
                    period_end=end_time,
                    total_operations=len(durations),
                    avg_duration_ms=statistics.mean(durations),
                    median_duration_ms=statistics.median(durations),
                    p95_duration_ms=self._percentile(durations, 95),
                    p99_duration_ms=self._percentile(durations, 99),
                    max_duration_ms=max(durations),
                    min_duration_ms=min(durations),
                    total_memory_delta_mb=total_memory_delta,
                    operation_types=dict(operation_types)
                )

            return MetricsSummary(
                period_start=start_time,
                period_end=end_time,
                total_operations=0,
                avg_duration_ms=0.0,
                median_duration_ms=0.0,
                p95_duration_ms=0.0,
                p99_duration_ms=0.0,
                max_duration_ms=0.0,
                min_duration_ms=0.0,
                total_memory_delta_mb=0.0,
                operation_types={}
            )

    def get_trend_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # Create hourly buckets
        hourly_data = defaultdict(list)

        with self._lock:
            for metric in self._metrics_buffer:
                if start_time <= metric['timestamp'] <= end_time:
                    hour_bucket = metric['timestamp'].replace(minute=0, second=0, microsecond=0)
                    data = metric['data']
                    if 'avg_duration_ms' in data:
                        hourly_data[hour_bucket].append(data['avg_duration_ms'])

        # Calculate trends
        trends = {
            'period_start': start_time.isoformat(),
            'period_end': end_time.isoformat()
        }

        if hourly_data:
            hours_sorted = sorted(hourly_data.keys())
            avg_by_hour = [statistics.mean(hourly_data[hour]) for hour in hours_sorted]

            if len(avg_by_hour) >= 2:
                # Simple linear trend
                x_values = list(range(len(avg_by_hour)))
                trend_slope = self._calculate_trend_slope(x_values, avg_by_hour)

                trends.update({
                    'trend_direction': 'improving' if trend_slope < 0 else 'degrading' if trend_slope > 0 else 'stable',
                    'trend_slope': trend_slope,
                    'hourly_averages': {str(hour): avg for hour, avg in zip(hours_sorted, avg_by_hour)}
                })
            else:
                trends['trend_direction'] = 'insufficient_data'
                trends['hourly_averages'] = {str(hour): statistics.mean(hourly_data[hour]) for hour in hours_sorted}
        else:
            trends['trend_direction'] = 'no_data'

        return trends

    def export_metrics(self, format: str = 'json') -> Union[str, Dict[str, Any]]:
        """Export collected metrics in specified format"""
        with self._lock:
            data = {
                'collection_period': {
                    'start': self._collection_start.isoformat(),
                    'current': datetime.now().isoformat()
                },
                'summary_1h': self.generate_summary(hours=1).__dict__,
                'summary_24h': self.generate_summary(hours=24).__dict__,
                'trends': self.get_trend_analysis(hours=24),
                'total_metrics_collected': len(self._metrics_buffer),
                'total_profiles_collected': len(self._profile_buffer)
            }

            # Convert datetime objects to strings for JSON serialization
            data = self._serialize_datetime_objects(data)

            if format.lower() == 'json':
                return json.dumps(data, indent=2)
            return data

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def _calculate_trend_slope(self, x_values: List[int], y_values: List[float]) -> float:
        """Calculate simple linear trend slope"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x_squared = sum(x * x for x in x_values)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x * sum_x)
        return slope

    def _serialize_datetime_objects(self, obj: Any) -> Any:
        """Recursively serialize datetime objects to strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_datetime_objects(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime_objects(item) for item in obj]
        else:
            return obj


class BottleneckDetector:
    """
    Automated bottleneck detection and analysis system

    Analyzes performance data to identify bottlenecks and provide
    optimization recommendations.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._detected_bottlenecks: Dict[str, BottleneckInfo] = {}
        self._lock = threading.RLock()

        # Thresholds for bottleneck detection
        self.thresholds = {
            'duration_ms': {
                'low': 10.0,
                'medium': 25.0,
                'high': 50.0,
                'critical': 100.0
            },
            'frequency': {
                'low': 5,
                'medium': 20,
                'high': 50,
                'critical': 100
            }
        }

    def detect_bottlenecks(self) -> List[BottleneckInfo]:
        """Detect performance bottlenecks in current metrics"""
        with self._lock:
            # Get recent performance data
            summary = self.metrics_collector.generate_summary(hours=1)

            # Analyze operation types
            current_bottlenecks = {}

            for operation_type, frequency in summary.operation_types.items():
                # Estimate average duration for this operation type
                avg_duration = self._estimate_operation_duration(operation_type)

                # Determine severity
                severity = self._classify_severity(avg_duration, frequency)

                if severity != 'none':
                    bottleneck_id = f"operation_{operation_type}"
                    current_bottlenecks[bottleneck_id] = BottleneckInfo(
                        component=operation_type,
                        severity=severity,
                        avg_duration_ms=avg_duration,
                        impact_score=self._calculate_impact_score(avg_duration, frequency),
                        frequency=frequency,
                        description=f"Operation type '{operation_type}' showing performance issues",
                        recommendations=self._generate_recommendations(operation_type, avg_duration, frequency),
                        first_seen=datetime.now(),
                        last_seen=datetime.now()
                    )

            # Update persistent bottleneck tracking
            for bottleneck_id, bottleneck in current_bottlenecks.items():
                if bottleneck_id in self._detected_bottlenecks:
                    # Update existing bottleneck
                    existing = self._detected_bottlenecks[bottleneck_id]
                    existing.last_seen = datetime.now()
                    existing.avg_duration_ms = (existing.avg_duration_ms + bottleneck.avg_duration_ms) / 2
                    existing.frequency += bottleneck.frequency
                else:
                    # New bottleneck
                    self._detected_bottlenecks[bottleneck_id] = bottleneck

            return list(self._detected_bottlenecks.values())

    def get_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on detected bottlenecks"""
        recommendations = []

        with self._lock:
            # General recommendations based on bottleneck patterns
            bottlenecks = list(self._detected_bottlenecks.values())

            if not bottlenecks:
                recommendations.append("No significant bottlenecks detected - system performance is good")
                return recommendations

            # Analyze bottleneck patterns
            high_severity_count = len([b for b in bottlenecks if b.severity in ['high', 'critical']])
            total_bottlenecks = len(bottlenecks)

            if high_severity_count > total_bottlenecks * 0.5:
                recommendations.append("Multiple critical bottlenecks detected - consider comprehensive optimization")

            # Component-specific recommendations
            component_types = defaultdict(list)
            for bottleneck in bottlenecks:
                component_type = bottleneck.component.split('.')[0] if '.' in bottleneck.component else 'general'
                component_types[component_type].append(bottleneck)

            for component_type, component_bottlenecks in component_types.items():
                if len(component_bottlenecks) > 1:
                    recommendations.append(f"Multiple bottlenecks in {component_type} components - consider {component_type}-specific optimization")

        return recommendations

    def _estimate_operation_duration(self, operation_type: str) -> float:
        """Estimate average duration for an operation type"""
        # This is a simplified estimation - in a real implementation,
        # you would analyze historical data for this specific operation type
        base_duration = 5.0  # Base 5ms

        # Adjust based on operation type
        if 'collection' in operation_type.lower():
            base_duration *= 2  # Collection operations typically slower
        elif 'database' in operation_type.lower():
            base_duration *= 3  # Database operations typically slowest
        elif 'type' in operation_type.lower():
            base_duration *= 1.5  # Type operations moderately slow

        return base_duration

    def _classify_severity(self, avg_duration_ms: float, frequency: int) -> str:
        """Classify bottleneck severity based on duration and frequency"""
        duration_severity = 'none'
        frequency_severity = 'none'

        # Check duration thresholds
        for severity in ['critical', 'high', 'medium', 'low']:
            if avg_duration_ms >= self.thresholds['duration_ms'][severity]:
                duration_severity = severity
                break

        # Check frequency thresholds
        for severity in ['critical', 'high', 'medium', 'low']:
            if frequency >= self.thresholds['frequency'][severity]:
                frequency_severity = severity
                break

        # Return the higher severity
        severity_order = ['none', 'low', 'medium', 'high', 'critical']
        duration_idx = severity_order.index(duration_severity)
        frequency_idx = severity_order.index(frequency_severity)

        return severity_order[max(duration_idx, frequency_idx)]

    def _calculate_impact_score(self, avg_duration_ms: float, frequency: int) -> float:
        """Calculate impact score (0-100) based on duration and frequency"""
        # Normalize to 0-100 scale
        duration_score = min(avg_duration_ms / 100.0 * 50, 50)  # Max 50 points for duration
        frequency_score = min(frequency / 100.0 * 50, 50)      # Max 50 points for frequency

        return duration_score + frequency_score

    def _generate_recommendations(self, operation_type: str, avg_duration_ms: float,
                                frequency: int) -> List[str]:
        """Generate specific recommendations for a bottleneck"""
        recommendations = []

        if avg_duration_ms > 50.0:
            recommendations.append(f"High duration detected - consider optimizing {operation_type} implementation")

        if frequency > 50:
            recommendations.append(f"High frequency detected - consider caching or batching for {operation_type}")

        if 'collection' in operation_type.lower():
            recommendations.append("Collection operation bottleneck - consider lazy evaluation or streaming")

        if 'database' in operation_type.lower():
            recommendations.append("Database operation bottleneck - consider query optimization or connection pooling")

        if 'type' in operation_type.lower():
            recommendations.append("Type operation bottleneck - consider type inference optimization")

        return recommendations


class MetricsAnalyzer:
    """
    Advanced metrics analysis and reporting system

    Provides comprehensive analysis of performance metrics with
    trends, predictions, and actionable insights.
    """

    def __init__(self, metrics_collector: MetricsCollector, bottleneck_detector: BottleneckDetector):
        self.metrics_collector = metrics_collector
        self.bottleneck_detector = bottleneck_detector

    def generate_performance_report(self, hours: int = 24) -> PerformanceReport:
        """Generate comprehensive performance report"""
        report_id = f"perf_report_{int(time.time())}"
        generated_at = datetime.now()

        # Generate summary
        period_summary = self.metrics_collector.generate_summary(hours=hours)

        # Detect bottlenecks
        bottlenecks = self.bottleneck_detector.detect_bottlenecks()

        # Get trends
        trends = self.metrics_collector.get_trend_analysis(hours=hours)

        # Generate recommendations
        recommendations = self.bottleneck_detector.get_optimization_recommendations()

        # Check compliance with performance targets
        compliance_status = self._check_performance_compliance(period_summary)

        # Get detailed metrics
        detailed_metrics = self.metrics_collector.export_metrics()

        return PerformanceReport(
            report_id=report_id,
            generated_at=generated_at,
            period_summary=period_summary,
            bottlenecks=bottlenecks,
            trends=trends,
            recommendations=recommendations,
            compliance_status=compliance_status,
            detailed_metrics=detailed_metrics if isinstance(detailed_metrics, dict) else {}
        )

    def _check_performance_compliance(self, summary: MetricsSummary) -> Dict[str, bool]:
        """Check compliance with performance targets"""
        return {
            'avg_duration_under_100ms': summary.avg_duration_ms < 100.0,
            'p95_duration_under_200ms': summary.p95_duration_ms < 200.0,
            'no_critical_performance_issues': summary.max_duration_ms < 1000.0,
            'acceptable_operation_count': summary.total_operations > 0
        }


def create_metrics_collector(monitor: Optional[PerformanceMonitor] = None,
                           profiler: Optional[FHIRPathProfiler] = None) -> MetricsCollector:
    """Create a metrics collector with monitor and profiler"""
    return MetricsCollector(monitor, profiler)