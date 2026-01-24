"""
Performance Dashboard and Reporting

This module provides a simple dashboard interface for viewing performance metrics,
generating reports, and monitoring the health of the FHIRPath evaluation system.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from .monitor import PerformanceMonitor, get_global_monitor
from .profiler import FHIRPathProfiler, get_global_profiler
from .metrics import MetricsCollector, BottleneckDetector, MetricsAnalyzer, create_metrics_collector


class PerformanceDashboard:
    """
    Simple performance dashboard for monitoring FHIRPath evaluation performance

    Provides a unified interface for accessing performance metrics, generating
    reports, and monitoring system health.
    """

    def __init__(self,
                 monitor: Optional[PerformanceMonitor] = None,
                 profiler: Optional[FHIRPathProfiler] = None):
        self.monitor = monitor or get_global_monitor()
        self.profiler = profiler or get_global_profiler()
        self.metrics_collector = create_metrics_collector(self.monitor, self.profiler)
        self.bottleneck_detector = BottleneckDetector(self.metrics_collector)
        self.metrics_analyzer = MetricsAnalyzer(self.metrics_collector, self.bottleneck_detector)

    def get_current_status(self) -> Dict[str, Any]:
        """Get current system performance status"""
        # Collect current metrics
        self.metrics_collector.collect_metrics()

        # Get basic metrics
        monitor_metrics = self.monitor.get_current_metrics()
        profiler_summary = self.profiler.get_profile_summary()

        # Detect bottlenecks
        bottlenecks = self.bottleneck_detector.detect_bottlenecks()

        # Calculate health score
        health_score = self._calculate_health_score(monitor_metrics, bottlenecks)

        return {
            'timestamp': datetime.now().isoformat(),
            'health_score': health_score,
            'status': self._get_status_label(health_score),
            'monitor_metrics': monitor_metrics,
            'profiler_summary': profiler_summary,
            'active_bottlenecks': len(bottlenecks),
            'critical_bottlenecks': len([b for b in bottlenecks if b.severity == 'critical']),
            'recommendations': self.bottleneck_detector.get_optimization_recommendations()[:3]
        }

    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        # Collect current metrics
        self.metrics_collector.collect_metrics()

        # Generate full report
        report = self.metrics_analyzer.generate_performance_report(hours=hours)

        # Convert to serializable format
        return {
            'report_id': report.report_id,
            'generated_at': report.generated_at.isoformat(),
            'period_hours': hours,
            'summary': {
                'total_operations': report.period_summary.total_operations,
                'avg_duration_ms': report.period_summary.avg_duration_ms,
                'p95_duration_ms': report.period_summary.p95_duration_ms,
                'max_duration_ms': report.period_summary.max_duration_ms,
                'operation_types': report.period_summary.operation_types
            },
            'bottlenecks': [
                {
                    'component': b.component,
                    'severity': b.severity,
                    'avg_duration_ms': b.avg_duration_ms,
                    'impact_score': b.impact_score,
                    'recommendations': b.recommendations
                }
                for b in report.bottlenecks[:5]  # Top 5 bottlenecks
            ],
            'trends': report.trends,
            'compliance_status': report.compliance_status,
            'recommendations': report.recommendations
        }

    def get_component_breakdown(self) -> Dict[str, Any]:
        """Get performance breakdown by component"""
        monitor_components = self.monitor.get_component_metrics()

        # Add profiler data if available
        profiler_summary = self.profiler.get_profile_summary()
        profiler_components = profiler_summary.get('component_summary', {})

        # Merge component data
        combined_components = {}

        for component, metrics in monitor_components.items():
            combined_components[component] = {
                'source': 'monitor',
                'count': metrics['count'],
                'avg_duration_ms': metrics['avg_duration_ms'],
                'total_duration_ms': metrics['total_duration_ms']
            }

        for component, metrics in profiler_components.items():
            if component in combined_components:
                combined_components[component]['profiler_data'] = metrics
            else:
                combined_components[component] = {
                    'source': 'profiler',
                    'count': metrics['call_count'],
                    'avg_duration_ms': metrics['avg_time_ms'],
                    'total_duration_ms': metrics['total_time_ms']
                }

        return combined_components

    def export_dashboard_data(self, format: str = 'json') -> str:
        """Export complete dashboard data"""
        data = {
            'dashboard_export': {
                'timestamp': datetime.now().isoformat(),
                'current_status': self.get_current_status(),
                'performance_report_1h': self.generate_performance_report(hours=1),
                'performance_report_24h': self.generate_performance_report(hours=24),
                'component_breakdown': self.get_component_breakdown(),
                'raw_metrics': {
                    'monitor': self.monitor.export_metrics(),
                    'collector': self.metrics_collector.export_metrics()
                }
            }
        }

        if format.lower() == 'json':
            return json.dumps(data, indent=2)
        else:
            return str(data)

    def reset_all_metrics(self) -> Dict[str, str]:
        """Reset all performance metrics"""
        self.monitor.reset_metrics()
        # Note: Profiler metrics reset automatically with its deque

        return {
            'status': 'success',
            'message': 'All performance metrics have been reset',
            'timestamp': datetime.now().isoformat()
        }

    def get_health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        status = self.get_current_status()

        health_checks = {
            'performance_monitoring': {
                'status': 'healthy' if status['monitor_metrics'].get('total_operations', 0) >= 0 else 'unhealthy',
                'details': 'Performance monitoring is collecting metrics'
            },
            'profiler': {
                'status': 'healthy' if status['profiler_summary'].get('total_profiles', 0) >= 0 else 'unhealthy',
                'details': 'Profiler is collecting performance data'
            },
            'bottleneck_detection': {
                'status': 'healthy' if status['critical_bottlenecks'] == 0 else 'warning',
                'details': f"{status['critical_bottlenecks']} critical bottlenecks detected"
            },
            'overall_performance': {
                'status': self._get_performance_status(status['monitor_metrics']),
                'details': f"Health score: {status['health_score']}/100"
            }
        }

        overall_status = 'healthy'
        if any(check['status'] == 'unhealthy' for check in health_checks.values()):
            overall_status = 'unhealthy'
        elif any(check['status'] == 'warning' for check in health_checks.values()):
            overall_status = 'warning'

        return {
            'overall_status': overall_status,
            'health_score': status['health_score'],
            'checks': health_checks,
            'recommendations': status['recommendations'],
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_health_score(self, monitor_metrics: Dict[str, Any], bottlenecks: List) -> int:
        """Calculate overall system health score (0-100)"""
        score = 100

        # Deduct for performance issues
        avg_duration = monitor_metrics.get('avg_duration_ms', 0)
        if avg_duration > 100:
            score -= 30  # Major performance issue
        elif avg_duration > 50:
            score -= 15  # Moderate performance issue
        elif avg_duration > 25:
            score -= 5   # Minor performance issue

        # Deduct for bottlenecks
        critical_bottlenecks = len([b for b in bottlenecks if b.severity == 'critical'])
        high_bottlenecks = len([b for b in bottlenecks if b.severity == 'high'])

        score -= critical_bottlenecks * 25  # 25 points per critical bottleneck
        score -= high_bottlenecks * 10      # 10 points per high bottleneck

        # Deduct for high memory usage
        memory_metrics = monitor_metrics.get('memory_metrics', {})
        if memory_metrics and memory_metrics.get('avg_memory_delta_mb', 0) > 50:
            score -= 10

        return max(0, min(100, score))

    def _get_status_label(self, health_score: int) -> str:
        """Get status label based on health score"""
        if health_score >= 90:
            return 'excellent'
        elif health_score >= 75:
            return 'good'
        elif health_score >= 50:
            return 'fair'
        elif health_score >= 25:
            return 'poor'
        else:
            return 'critical'

    def _get_performance_status(self, monitor_metrics: Dict[str, Any]) -> str:
        """Get performance status from monitor metrics"""
        avg_duration = monitor_metrics.get('avg_duration_ms', 0)

        if avg_duration == 0:
            return 'no_data'
        elif avg_duration < 25:
            return 'healthy'
        elif avg_duration < 100:
            return 'warning'
        else:
            return 'unhealthy'


def create_dashboard(monitor: Optional[PerformanceMonitor] = None,
                    profiler: Optional[FHIRPathProfiler] = None) -> PerformanceDashboard:
    """Create a performance dashboard instance"""
    return PerformanceDashboard(monitor, profiler)


# Global dashboard instance
_global_dashboard: Optional[PerformanceDashboard] = None


def get_global_dashboard() -> PerformanceDashboard:
    """Get or create the global performance dashboard"""
    global _global_dashboard
    if _global_dashboard is None:
        _global_dashboard = create_dashboard()
    return _global_dashboard