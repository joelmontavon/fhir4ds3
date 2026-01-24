"""
Performance Monitoring and Profiling Infrastructure

This module provides comprehensive performance monitoring, profiling, and optimization
capabilities for the FHIRPath evaluation system. It includes monitoring infrastructure,
bottleneck detection, and performance reporting for population-scale healthcare analytics.
"""

from .monitor import (
    PerformanceMonitor,
    MonitoringConfig,
    PerformanceMetrics,
    create_performance_monitor,
    get_global_monitor,
    configure_global_monitor,
    monitor
)
from .profiler import (
    FHIRPathProfiler,
    ProfileResult,
    ProfilerConfig,
    create_profiler,
    get_global_profiler,
    configure_global_profiler,
    profile
)
from .metrics import (
    MetricsCollector,
    MetricsAnalyzer,
    PerformanceReport,
    BottleneckDetector,
    create_metrics_collector
)
from .dashboard import (
    PerformanceDashboard,
    create_dashboard,
    get_global_dashboard
)

__all__ = [
    'PerformanceMonitor',
    'MonitoringConfig',
    'PerformanceMetrics',
    'create_performance_monitor',
    'get_global_monitor',
    'configure_global_monitor',
    'monitor',
    'FHIRPathProfiler',
    'ProfileResult',
    'ProfilerConfig',
    'create_profiler',
    'get_global_profiler',
    'configure_global_profiler',
    'profile',
    'MetricsCollector',
    'MetricsAnalyzer',
    'PerformanceReport',
    'BottleneckDetector',
    'create_metrics_collector',
    'PerformanceDashboard',
    'create_dashboard',
    'get_global_dashboard'
]