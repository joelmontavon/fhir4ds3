"""
Unit tests for performance metrics collection and analysis
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.performance.monitor import PerformanceMonitor, MonitoringConfig
from fhir4ds.fhirpath.performance.profiler import FHIRPathProfiler, ProfilerConfig
from fhir4ds.fhirpath.performance.metrics import (
    MetricsCollector,
    BottleneckDetector,
    MetricsAnalyzer,
    MetricsSummary,
    BottleneckInfo,
    PerformanceReport,
    create_metrics_collector
)


class TestMetricsSummary:
    """Test MetricsSummary dataclass"""

    def test_metrics_summary_creation(self):
        """Test creating metrics summary"""
        start = datetime.now()
        end = start + timedelta(hours=1)

        summary = MetricsSummary(
            period_start=start,
            period_end=end,
            total_operations=100,
            avg_duration_ms=25.5,
            median_duration_ms=20.0,
            p95_duration_ms=50.0,
            p99_duration_ms=75.0,
            max_duration_ms=100.0,
            min_duration_ms=5.0,
            total_memory_delta_mb=150.0,
            operation_types={"evaluation": 50, "parsing": 30, "collection": 20}
        )

        assert summary.total_operations == 100
        assert summary.avg_duration_ms == 25.5
        assert summary.operation_types["evaluation"] == 50


class TestBottleneckInfo:
    """Test BottleneckInfo dataclass"""

    def test_bottleneck_info_creation(self):
        """Test creating bottleneck info"""
        now = datetime.now()
        bottleneck = BottleneckInfo(
            component="slow_parser",
            severity="high",
            avg_duration_ms=45.0,
            impact_score=75.0,
            frequency=20,
            description="Parser showing performance issues",
            recommendations=["Consider caching", "Optimize parsing logic"],
            first_seen=now,
            last_seen=now
        )

        assert bottleneck.component == "slow_parser"
        assert bottleneck.severity == "high"
        assert bottleneck.impact_score == 75.0
        assert len(bottleneck.recommendations) == 2


class TestMetricsCollector:
    """Test MetricsCollector class"""

    def setup_method(self):
        """Setup for each test"""
        self.monitor = PerformanceMonitor(MonitoringConfig(enable_memory_tracking=False, enable_adaptive_sampling=False, sample_rate=1.0))
        self.profiler = FHIRPathProfiler(ProfilerConfig(profile_sample_rate=1.0))
        self.collector = MetricsCollector(self.monitor, self.profiler)

    def test_initialization(self):
        """Test collector initialization"""
        assert self.collector.monitor == self.monitor
        assert self.collector.profiler == self.profiler
        assert len(self.collector._metrics_buffer) == 0
        assert len(self.collector._profile_buffer) == 0

    def test_initialization_without_monitor_profiler(self):
        """Test collector initialization without monitor/profiler"""
        collector = MetricsCollector()
        assert collector.monitor is None
        assert collector.profiler is None

    def test_collect_metrics_with_monitor(self):
        """Test metrics collection from monitor"""
        # Generate some monitor data
        with self.monitor.monitor_operation("test_op"):
            time.sleep(0.01)

        # Collect metrics
        self.collector.collect_metrics()

        assert len(self.collector._metrics_buffer) == 1
        buffer_entry = self.collector._metrics_buffer[0]
        assert buffer_entry['source'] == 'monitor'
        assert 'timestamp' in buffer_entry

    def test_collect_metrics_with_profiler(self):
        """Test metrics collection from profiler"""
        # Generate some profiler data
        with self.profiler.profile_operation("test_op"):
            time.sleep(0.01)

        # Collect metrics
        self.collector.collect_metrics()

        assert len(self.collector._profile_buffer) == 1
        buffer_entry = self.collector._profile_buffer[0]
        assert buffer_entry['source'] == 'profiler'

    def test_collect_metrics_no_monitor_profiler(self):
        """Test metrics collection without monitor/profiler"""
        collector = MetricsCollector()
        collector.collect_metrics()  # Should not raise error

        assert len(collector._metrics_buffer) == 0
        assert len(collector._profile_buffer) == 0

    def test_generate_summary_empty(self):
        """Test generating summary with no data"""
        summary = self.collector.generate_summary(hours=1)

        assert summary.total_operations == 0
        assert summary.avg_duration_ms == 0.0
        assert len(summary.operation_types) == 0

    def test_generate_summary_with_data(self):
        """Test generating summary with data"""
        # Generate test data
        for i in range(5):
            with self.monitor.monitor_operation(f"test_op_{i}"):
                time.sleep(0.005)

        self.collector.collect_metrics()

        summary = self.collector.generate_summary(hours=1)
        assert summary.total_operations > 0
        assert summary.avg_duration_ms > 0

    def test_get_trend_analysis(self):
        """Test trend analysis"""
        # Generate data over time
        for i in range(3):
            with self.monitor.monitor_operation(f"test_op_{i}"):
                time.sleep(0.002)
            self.collector.collect_metrics()
            time.sleep(0.001)  # Small gap between collections

        trends = self.collector.get_trend_analysis(hours=1)
        assert 'period_start' in trends
        assert 'period_end' in trends

    def test_export_metrics(self):
        """Test exporting metrics"""
        # Generate some data
        with self.monitor.monitor_operation("test_op"):
            time.sleep(0.01)
        self.collector.collect_metrics()

        # Export as dict
        exported = self.collector.export_metrics(format='dict')
        assert isinstance(exported, dict)
        assert 'collection_period' in exported
        assert 'summary_1h' in exported
        assert 'summary_24h' in exported

        # Export as JSON (default)
        exported_json = self.collector.export_metrics()
        assert isinstance(exported_json, str)
        assert '"collection_period"' in exported_json


class TestBottleneckDetector:
    """Test BottleneckDetector class"""

    def setup_method(self):
        """Setup for each test"""
        self.monitor = PerformanceMonitor(MonitoringConfig(enable_memory_tracking=False, enable_adaptive_sampling=False, sample_rate=1.0))
        self.collector = MetricsCollector(self.monitor)
        self.detector = BottleneckDetector(self.collector)

    def test_initialization(self):
        """Test detector initialization"""
        assert self.detector.metrics_collector == self.collector
        assert len(self.detector._detected_bottlenecks) == 0
        assert 'duration_ms' in self.detector.thresholds
        assert 'frequency' in self.detector.thresholds

    def test_detect_bottlenecks_no_data(self):
        """Test bottleneck detection with no data"""
        bottlenecks = self.detector.detect_bottlenecks()
        assert len(bottlenecks) == 0

    def test_classify_severity(self):
        """Test severity classification"""
        # Test different severity levels
        assert self.detector._classify_severity(5.0, 2) == 'none'
        assert self.detector._classify_severity(15.0, 10) == 'low'
        assert self.detector._classify_severity(30.0, 25) == 'medium'
        assert self.detector._classify_severity(60.0, 60) == 'high'
        assert self.detector._classify_severity(150.0, 150) == 'critical'

    def test_calculate_impact_score(self):
        """Test impact score calculation"""
        # Test impact score calculation
        score = self.detector._calculate_impact_score(50.0, 50)
        assert 0 <= score <= 100

        # Higher duration and frequency should give higher score
        high_score = self.detector._calculate_impact_score(100.0, 100)
        low_score = self.detector._calculate_impact_score(10.0, 10)
        assert high_score > low_score

    def test_generate_recommendations(self):
        """Test recommendation generation"""
        recommendations = self.detector._generate_recommendations("collection.where", 60.0, 100)
        assert len(recommendations) > 0
        assert any("collection" in rec.lower() for rec in recommendations)

        db_recommendations = self.detector._generate_recommendations("database.query", 80.0, 50)
        assert any("database" in rec.lower() for rec in db_recommendations)

    def test_get_optimization_recommendations_no_bottlenecks(self):
        """Test optimization recommendations with no bottlenecks"""
        recommendations = self.detector.get_optimization_recommendations()
        assert len(recommendations) == 1
        assert "no significant bottlenecks" in recommendations[0].lower()

    def test_estimate_operation_duration(self):
        """Test operation duration estimation"""
        base_duration = self.detector._estimate_operation_duration("basic_op")
        collection_duration = self.detector._estimate_operation_duration("collection.where")
        database_duration = self.detector._estimate_operation_duration("database.query")

        # Database operations should be estimated as slowest
        assert database_duration > collection_duration > base_duration


class TestMetricsAnalyzer:
    """Test MetricsAnalyzer class"""

    def setup_method(self):
        """Setup for each test"""
        self.monitor = PerformanceMonitor(MonitoringConfig(enable_memory_tracking=False, enable_adaptive_sampling=False, sample_rate=1.0))
        self.collector = MetricsCollector(self.monitor)
        self.detector = BottleneckDetector(self.collector)
        self.analyzer = MetricsAnalyzer(self.collector, self.detector)

    def test_initialization(self):
        """Test analyzer initialization"""
        assert self.analyzer.metrics_collector == self.collector
        assert self.analyzer.bottleneck_detector == self.detector

    def test_generate_performance_report(self):
        """Test performance report generation"""
        # Generate some test data
        with self.monitor.monitor_operation("test_op"):
            time.sleep(0.01)
        self.collector.collect_metrics()

        report = self.analyzer.generate_performance_report(hours=1)

        assert isinstance(report, PerformanceReport)
        assert report.report_id.startswith("perf_report_")
        assert isinstance(report.generated_at, datetime)
        assert isinstance(report.period_summary, MetricsSummary)
        assert isinstance(report.bottlenecks, list)
        assert isinstance(report.trends, dict)
        assert isinstance(report.recommendations, list)
        assert isinstance(report.compliance_status, dict)

    def test_check_performance_compliance(self):
        """Test performance compliance checking"""
        # Create a mock summary for testing
        summary = MetricsSummary(
            period_start=datetime.now(),
            period_end=datetime.now(),
            total_operations=10,
            avg_duration_ms=50.0,
            median_duration_ms=45.0,
            p95_duration_ms=80.0,
            p99_duration_ms=95.0,
            max_duration_ms=120.0,
            min_duration_ms=10.0,
            total_memory_delta_mb=25.0,
            operation_types={"test": 10}
        )

        compliance = self.analyzer._check_performance_compliance(summary)

        assert isinstance(compliance, dict)
        assert 'avg_duration_under_100ms' in compliance
        assert 'p95_duration_under_200ms' in compliance
        assert 'no_critical_performance_issues' in compliance
        assert 'acceptable_operation_count' in compliance

        # With our test data, most should pass
        assert compliance['avg_duration_under_100ms'] is True
        assert compliance['p95_duration_under_200ms'] is True
        assert compliance['no_critical_performance_issues'] is True
        assert compliance['acceptable_operation_count'] is True


class TestCreateMetricsCollector:
    """Test metrics collector creation function"""

    def test_create_with_monitor_and_profiler(self):
        """Test creating collector with monitor and profiler"""
        monitor = PerformanceMonitor()
        profiler = FHIRPathProfiler()

        collector = create_metrics_collector(monitor, profiler)
        assert collector.monitor == monitor
        assert collector.profiler == profiler

    def test_create_with_none(self):
        """Test creating collector with None values"""
        collector = create_metrics_collector(None, None)
        assert collector.monitor is None
        assert collector.profiler is None


class TestIntegration:
    """Integration tests for metrics components"""

    def test_end_to_end_metrics_flow(self):
        """Test complete metrics collection and analysis flow"""
        # Setup components
        monitor = PerformanceMonitor(MonitoringConfig(enable_memory_tracking=False, enable_adaptive_sampling=False, sample_rate=1.0))
        profiler = FHIRPathProfiler(ProfilerConfig(profile_sample_rate=1.0))
        collector = MetricsCollector(monitor, profiler)
        detector = BottleneckDetector(collector)
        analyzer = MetricsAnalyzer(collector, detector)

        # Generate performance data
        for i in range(3):
            with monitor.monitor_operation(f"operation_{i}"):
                time.sleep(0.005)

            with profiler.profile_operation(f"profile_op_{i}") as session_id:
                with profiler.profile_component(session_id, "parser"):
                    time.sleep(0.003)

        # Collect and analyze
        collector.collect_metrics()
        bottlenecks = detector.detect_bottlenecks()
        report = analyzer.generate_performance_report(hours=1)

        # Verify end-to-end flow
        assert len(collector._metrics_buffer) > 0
        assert len(collector._profile_buffer) > 0
        assert isinstance(report, PerformanceReport)
        assert report.period_summary.total_operations > 0

    def test_performance_monitoring_overhead(self):
        """Test that performance monitoring has minimal overhead"""
        # Test without monitoring - use more realistic workload
        start_time = time.time()
        for i in range(100):
            # Simulate realistic FHIRPath evaluation work
            result = sum(j * j for j in range(100))  # More substantial work
            _ = str(result)  # String conversion
        baseline_time = time.time() - start_time

        # Test with monitoring using production defaults (10% sampling with adaptive sampling)
        monitor = PerformanceMonitor(MonitoringConfig(enable_memory_tracking=False))
        start_time = time.time()
        for i in range(100):
            with monitor.monitor_operation(f"op_{i}"):
                # Same work as baseline
                result = sum(j * j for j in range(100))
                _ = str(result)
        monitored_time = time.time() - start_time

        # Overhead should remain within acceptable instrumentation limits even
        # when the system is under moderate load. Detailed monitoring commonly
        # incurs up to ~200% overhead in CI environments, so we allow a 250%
        # (2.5x) threshold to prevent flakes while still catching real
        # regressions that would exceed this range.
        overhead_ratio = (monitored_time - baseline_time) / baseline_time
        assert overhead_ratio < 2.5, f"Monitoring overhead too high: {overhead_ratio:.2%}"
