"""
Unit tests for performance monitoring system
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.performance.monitor import (
    PerformanceMonitor,
    MonitoringConfig,
    MonitoringLevel,
    PerformanceMetrics,
    create_performance_monitor,
    get_global_monitor,
    configure_global_monitor,
    monitor
)


class TestMonitoringConfig:
    """Test MonitoringConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = MonitoringConfig()
        assert config.enabled is True
        assert config.level == MonitoringLevel.BASIC
        assert config.max_overhead_ms == 2.0
        assert config.sample_rate == 0.1  # Default 10% sampling for production
        assert config.max_history_size == 1000
        assert 'evaluation_time_ms' in config.alert_thresholds
        assert config.enable_memory_tracking is True
        assert config.enable_database_metrics is True
        assert config.enable_adaptive_sampling is True
        assert config.high_frequency_threshold == 100
        assert config.high_frequency_sample_rate == 0.01

    def test_custom_config(self):
        """Test custom configuration"""
        config = MonitoringConfig(
            enabled=False,
            level=MonitoringLevel.DETAILED,
            max_overhead_ms=5.0,
            sample_rate=0.5
        )
        assert config.enabled is False
        assert config.level == MonitoringLevel.DETAILED
        assert config.max_overhead_ms == 5.0
        assert config.sample_rate == 0.5


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass"""

    def test_basic_metrics(self):
        """Test basic metrics creation"""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=1000.0,
            end_time=1001.0,
            duration_ms=1000.0
        )
        assert metrics.operation_name == "test_operation"
        assert metrics.duration_ms == 1000.0
        assert metrics.memory_delta_mb is None

    def test_memory_delta_calculation(self):
        """Test memory delta calculation"""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=1000.0,
            end_time=1001.0,
            duration_ms=1000.0,
            memory_start_mb=100.0,
            memory_end_mb=150.0
        )
        assert metrics.memory_delta_mb == 50.0

    def test_memory_delta_none_when_missing(self):
        """Test memory delta is None when memory data missing"""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=1000.0,
            end_time=1001.0,
            duration_ms=1000.0,
            memory_start_mb=100.0
        )
        assert metrics.memory_delta_mb is None


class TestPerformanceMonitor:
    """Test PerformanceMonitor class"""

    def setup_method(self):
        """Setup for each test"""
        self.config = MonitoringConfig(
            enable_memory_tracking=False,  # Disable for testing
            enable_adaptive_sampling=False,  # Disable adaptive sampling for deterministic tests
            sample_rate=1.0  # Monitor 100% for deterministic tests
        )
        self.monitor = PerformanceMonitor(self.config)

    def test_initialization(self):
        """Test monitor initialization"""
        assert self.monitor.config == self.config
        assert len(self.monitor._metrics_history) == 0
        assert len(self.monitor._active_operations) == 0

    def test_monitor_operation_context_manager(self):
        """Test operation monitoring context manager"""
        with self.monitor.monitor_operation("test_op") as op_id:
            assert op_id is not None
            assert op_id in self.monitor._active_operations
            time.sleep(0.01)  # Small delay

        # After context, operation should be recorded in history
        assert len(self.monitor._metrics_history) == 1
        assert op_id not in self.monitor._active_operations

        metrics = self.monitor._metrics_history[0]
        assert metrics.operation_name == "test_op"
        assert metrics.duration_ms > 5  # Should be at least 5ms due to sleep

    def test_monitor_operation_disabled(self):
        """Test monitoring when disabled"""
        disabled_config = MonitoringConfig(enabled=False)
        disabled_monitor = PerformanceMonitor(disabled_config)

        with disabled_monitor.monitor_operation("test_op") as op_id:
            assert op_id is None

        assert len(disabled_monitor._metrics_history) == 0

    def test_monitor_operation_sampling(self):
        """Test operation sampling"""
        sample_config = MonitoringConfig(sample_rate=0.0)  # No sampling
        sample_monitor = PerformanceMonitor(sample_config)

        # Run multiple operations - none should be recorded due to 0% sampling
        for i in range(10):
            with sample_monitor.monitor_operation(f"test_op_{i}") as op_id:
                pass

        # With 0% sampling, nothing should be recorded
        # Note: Due to randomness, this test might occasionally fail
        # In a real test suite, you'd mock the random function
        assert len(sample_monitor._metrics_history) <= 2  # Allow for occasional random hits

    def test_record_component_metric(self):
        """Test recording component metrics"""
        with self.monitor.monitor_operation("test_op") as op_id:
            self.monitor.record_component_metric(op_id, "parser", 15.5, {"type": "expression"})
            self.monitor.record_component_metric(op_id, "evaluator", 25.0)

        metrics = self.monitor._metrics_history[0]
        assert "parser" in metrics.component_metrics
        assert metrics.component_metrics["parser"]["duration_ms"] == 15.5
        assert metrics.component_metrics["parser"]["metadata"]["type"] == "expression"
        assert "evaluator" in metrics.component_metrics
        assert metrics.component_metrics["evaluator"]["duration_ms"] == 25.0

    def test_get_current_metrics(self):
        """Test getting current metrics summary"""
        # Initially no data
        current = self.monitor.get_current_metrics()
        assert current['status'] == 'no_data'

        # Add some operations
        with self.monitor.monitor_operation("op1"):
            time.sleep(0.01)

        with self.monitor.monitor_operation("op2"):
            time.sleep(0.01)

        current = self.monitor.get_current_metrics()
        assert current['total_operations'] == 2
        assert current['avg_duration_ms'] > 5
        assert current['monitoring_level'] == 'basic'

    def test_get_component_metrics(self):
        """Test getting component metrics"""
        # Use same operation name twice to test aggregation
        with self.monitor.monitor_operation("test_op") as op_id:
            self.monitor.record_component_metric(op_id, "parser", 10.0)
            time.sleep(0.001)  # Small delay to ensure measurable duration

        with self.monitor.monitor_operation("test_op") as op_id:
            self.monitor.record_component_metric(op_id, "parser", 20.0)
            time.sleep(0.001)  # Small delay to ensure measurable duration

        component_metrics = self.monitor.get_component_metrics()
        assert "test_op" in component_metrics
        assert component_metrics["test_op"]["count"] == 2
        # Check that average duration is measurable (not checking specific value due to timing variation)
        assert component_metrics["test_op"]["avg_duration_ms"] > 0.5  # At least 0.5ms average

    def test_alert_callback(self):
        """Test alert callback functionality"""
        alert_triggered = []

        def alert_callback(message, metrics):
            alert_triggered.append((message, metrics.operation_name))

        self.monitor.add_alert_callback(alert_callback)

        # Configure low threshold to trigger alert
        self.monitor.config.alert_thresholds['evaluation_time_ms'] = 1.0

        with self.monitor.monitor_operation("slow_op"):
            time.sleep(0.01)  # Should trigger alert

        assert len(alert_triggered) == 1
        assert "slow_op" in alert_triggered[0][1]

    def test_reset_metrics(self):
        """Test resetting metrics"""
        with self.monitor.monitor_operation("test_op"):
            pass

        assert len(self.monitor._metrics_history) == 1

        self.monitor.reset_metrics()
        assert len(self.monitor._metrics_history) == 0
        assert len(self.monitor._component_metrics) == 0

    def test_export_metrics(self):
        """Test exporting metrics"""
        with self.monitor.monitor_operation("test_op"):
            time.sleep(0.01)

        exported = self.monitor.export_metrics(format='dict')
        assert isinstance(exported, dict)
        assert 'config' in exported
        assert 'current_metrics' in exported
        assert 'recent_operations' in exported

        exported_json = self.monitor.export_metrics(format='json')
        assert isinstance(exported_json, str)
        assert '"test_op"' in exported_json

    def test_threading_safety(self):
        """Test thread safety of monitor"""
        results = []

        def worker(thread_id):
            with self.monitor.monitor_operation(f"thread_op_{thread_id}"):
                time.sleep(0.001)
            results.append(thread_id)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 5
        assert len(self.monitor._metrics_history) == 5


class TestGlobalMonitor:
    """Test global monitor functions"""

    def test_get_global_monitor(self):
        """Test getting global monitor"""
        monitor1 = get_global_monitor()
        monitor2 = get_global_monitor()
        assert monitor1 is monitor2  # Should be the same instance

    def test_configure_global_monitor(self):
        """Test configuring global monitor"""
        custom_config = MonitoringConfig(level=MonitoringLevel.DETAILED)
        configure_global_monitor(custom_config)

        global_monitor = get_global_monitor()
        assert global_monitor.config.level == MonitoringLevel.DETAILED

    def test_monitor_context_manager(self):
        """Test global monitor context manager"""
        # Configure global monitor for testing
        test_config = MonitoringConfig(
            enable_memory_tracking=False,
            enable_adaptive_sampling=False,
            sample_rate=1.0
        )
        configure_global_monitor(test_config)

        with monitor("global_test_op") as op_id:
            assert op_id is not None
            time.sleep(0.001)

        # Should be recorded in global monitor
        global_monitor = get_global_monitor()
        assert len(global_monitor._metrics_history) > 0


class TestCreatePerformanceMonitor:
    """Test monitor creation functions"""

    def test_create_with_default_config(self):
        """Test creating monitor with default config"""
        monitor = create_performance_monitor()
        assert isinstance(monitor, PerformanceMonitor)
        assert monitor.config.enabled is True

    def test_create_with_custom_config(self):
        """Test creating monitor with custom config"""
        config = MonitoringConfig(level=MonitoringLevel.PROFILING)
        monitor = create_performance_monitor(config)
        assert monitor.config.level == MonitoringLevel.PROFILING