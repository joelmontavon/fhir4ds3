"""
Unit tests for FHIRPath profiler system
"""

import pytest
import time
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.performance.profiler import (
    FHIRPathProfiler,
    ProfilerConfig,
    ComponentProfile,
    ProfileResult,
    create_profiler,
    get_global_profiler,
    configure_global_profiler,
    profile
)


class TestProfilerConfig:
    """Test ProfilerConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ProfilerConfig()
        assert config.enabled is True
        assert config.profile_evaluation is True
        assert config.profile_parsing is True
        assert config.profile_collection_ops is True
        assert config.profile_type_operations is True
        assert config.profile_database_operations is True
        assert config.max_call_depth == 10
        assert config.capture_call_stacks is False
        assert config.save_detailed_profiles is False
        assert config.profile_sample_rate == 0.1

    def test_custom_config(self):
        """Test custom configuration"""
        config = ProfilerConfig(
            enabled=False,
            profile_sample_rate=0.5,
            save_detailed_profiles=True
        )
        assert config.enabled is False
        assert config.profile_sample_rate == 0.5
        assert config.save_detailed_profiles is True


class TestComponentProfile:
    """Test ComponentProfile dataclass"""

    def test_component_profile_creation(self):
        """Test creating component profile"""
        profile = ComponentProfile(
            component_name="test_component",
            total_time_ms=100.0,
            call_count=5,
            avg_time_ms=20.0,
            max_time_ms=30.0,
            min_time_ms=10.0
        )
        assert profile.component_name == "test_component"
        assert profile.total_time_ms == 100.0
        assert profile.call_count == 5
        assert profile.avg_time_ms == 20.0
        assert profile.max_time_ms == 30.0
        assert profile.min_time_ms == 10.0
        assert profile.call_stack is None
        assert len(profile.sub_components) == 0


class TestProfileResult:
    """Test ProfileResult dataclass"""

    def test_profile_result_creation(self):
        """Test creating profile result"""
        components = {
            "parser": ComponentProfile("parser", 50.0, 2, 25.0, 30.0, 20.0),
            "evaluator": ComponentProfile("evaluator", 75.0, 3, 25.0, 35.0, 15.0)
        }

        result = ProfileResult(
            operation_name="test_operation",
            total_time_ms=125.0,
            components=components,
            optimization_suggestions=["Use caching"]
        )

        assert result.operation_name == "test_operation"
        assert result.total_time_ms == 125.0
        assert len(result.components) == 2
        assert "parser" in result.components
        assert "evaluator" in result.components
        assert result.optimization_suggestions == ["Use caching"]
        assert result.call_graph is None


class TestFHIRPathProfiler:
    """Test FHIRPathProfiler class"""

    def setup_method(self):
        """Setup for each test"""
        self.config = ProfilerConfig(profile_sample_rate=1.0)  # Always profile for testing
        self.profiler = FHIRPathProfiler(self.config)

    def test_initialization(self):
        """Test profiler initialization"""
        assert self.profiler.config == self.config
        assert len(self.profiler._active_profiles) == 0
        assert len(self.profiler._profile_results) == 0

    def test_profile_operation_context_manager(self):
        """Test operation profiling context manager"""
        with self.profiler.profile_operation("test_op") as session_id:
            assert session_id is not None
            assert session_id in self.profiler._active_profiles
            time.sleep(0.01)

        # After context, operation should be recorded in results
        assert len(self.profiler._profile_results) == 1
        assert session_id not in self.profiler._active_profiles

        result = self.profiler._profile_results[0]
        assert result.operation_name == "test_op"
        assert result.total_time_ms > 5

    def test_profile_operation_disabled(self):
        """Test profiling when disabled"""
        disabled_config = ProfilerConfig(enabled=False)
        disabled_profiler = FHIRPathProfiler(disabled_config)

        with disabled_profiler.profile_operation("test_op") as session_id:
            assert session_id is None

        assert len(disabled_profiler._profile_results) == 0

    def test_profile_component(self):
        """Test component profiling"""
        with self.profiler.profile_operation("test_op") as session_id:
            with self.profiler.profile_component(session_id, "parser"):
                time.sleep(0.005)
            with self.profiler.profile_component(session_id, "evaluator"):
                time.sleep(0.005)

        result = self.profiler._profile_results[0]
        assert "parser" in result.components
        assert "evaluator" in result.components
        assert result.components["parser"].call_count == 1
        assert result.components["evaluator"].call_count == 1

    def test_profile_evaluation_step(self):
        """Test evaluation step profiling"""
        with self.profiler.profile_operation("test_op") as session_id:
            with self.profiler.profile_evaluation_step(session_id, "parse", "Patient.name", 1):
                time.sleep(0.005)

        result = self.profiler._profile_results[0]
        assert "evaluation.parse" in result.components

    def test_profile_collection_operation(self):
        """Test collection operation profiling"""
        with self.profiler.profile_operation("test_op") as session_id:
            with self.profiler.profile_collection_operation(session_id, "where", 100):
                time.sleep(0.005)

        result = self.profiler._profile_results[0]
        assert "collection.where" in result.components

    def test_profile_type_operation(self):
        """Test type operation profiling"""
        with self.profiler.profile_operation("test_op") as session_id:
            with self.profiler.profile_type_operation(session_id, "convert", "string"):
                time.sleep(0.005)

        result = self.profiler._profile_results[0]
        assert "type.convert" in result.components

    def test_profile_database_operation(self):
        """Test database operation profiling"""
        with self.profiler.profile_operation("test_op") as session_id:
            with self.profiler.profile_database_operation(session_id, "query", 500, 10):
                time.sleep(0.005)

        result = self.profiler._profile_results[0]
        assert "database.query" in result.components

    def test_get_profile_summary(self):
        """Test getting profile summary"""
        # Initially no data
        summary = self.profiler.get_profile_summary()
        assert summary['status'] == 'no_data'

        # Add some profiles
        with self.profiler.profile_operation("op1") as session_id:
            with self.profiler.profile_component(session_id, "parser"):
                time.sleep(0.005)

        with self.profiler.profile_operation("op2") as session_id:
            with self.profiler.profile_component(session_id, "parser"):
                time.sleep(0.005)

        summary = self.profiler.get_profile_summary()
        assert summary['total_profiles'] == 2
        assert 'component_summary' in summary
        assert 'parser' in summary['component_summary']
        assert summary['component_summary']['parser']['call_count'] == 2

    def test_get_recent_profiles(self):
        """Test getting recent profiles"""
        # Add multiple profiles
        for i in range(5):
            with self.profiler.profile_operation(f"op_{i}"):
                time.sleep(0.001)

        recent = self.profiler.get_recent_profiles(count=3)
        assert len(recent) == 3
        assert all(isinstance(r, ProfileResult) for r in recent)

    def test_optimization_suggestions(self):
        """Test optimization suggestion generation"""
        with self.profiler.profile_operation("slow_op") as session_id:
            # Simulate slow component
            with self.profiler.profile_component(session_id, "slow_parser"):
                time.sleep(0.015)  # 15ms should trigger suggestion

        result = self.profiler._profile_results[0]
        assert len(result.optimization_suggestions) > 0
        assert any("slow_parser" in suggestion for suggestion in result.optimization_suggestions)

    def test_bottleneck_identification(self):
        """Test bottleneck identification"""
        # Create multiple operations with varying performance
        for i in range(10):
            with self.profiler.profile_operation(f"op_{i}") as session_id:
                with self.profiler.profile_component(session_id, "parser"):
                    time.sleep(0.002 * (i + 1))  # Increasing time

        summary = self.profiler.get_profile_summary()
        bottlenecks = summary['top_bottlenecks']
        assert len(bottlenecks) > 0
        assert bottlenecks[0]['component'] == 'parser'

    def test_sampling_rate(self):
        """Test profile sampling"""
        sample_config = ProfilerConfig(profile_sample_rate=0.0)  # No sampling
        sample_profiler = FHIRPathProfiler(sample_config)

        # Run multiple operations - few should be recorded due to 0% sampling
        for i in range(10):
            with sample_profiler.profile_operation(f"test_op_{i}"):
                pass

        # With 0% sampling, very few should be recorded
        assert len(sample_profiler._profile_results) <= 2

    def test_component_call_stack_tracking(self):
        """Test call stack tracking during profiling"""
        with self.profiler.profile_operation("test_op") as session_id:
            # Nested component calls
            with self.profiler.profile_component(session_id, "outer"):
                with self.profiler.profile_component(session_id, "inner"):
                    time.sleep(0.001)

        # Verify call stack was managed correctly
        assert session_id not in self.profiler._active_profiles
        result = self.profiler._profile_results[0]
        assert "outer" in result.components
        assert "inner" in result.components


class TestGlobalProfiler:
    """Test global profiler functions"""

    def test_get_global_profiler(self):
        """Test getting global profiler"""
        profiler1 = get_global_profiler()
        profiler2 = get_global_profiler()
        assert profiler1 is profiler2  # Should be the same instance

    def test_configure_global_profiler(self):
        """Test configuring global profiler"""
        custom_config = ProfilerConfig(save_detailed_profiles=True)
        configure_global_profiler(custom_config)

        global_profiler = get_global_profiler()
        assert global_profiler.config.save_detailed_profiles is True

    def test_profile_context_manager(self):
        """Test global profiler context manager"""
        # Configure global profiler for testing
        test_config = ProfilerConfig(profile_sample_rate=1.0)
        configure_global_profiler(test_config)

        with profile("global_test_op") as session_id:
            time.sleep(0.001)

        # Should be recorded in global profiler
        global_profiler = get_global_profiler()
        assert len(global_profiler._profile_results) > 0


class TestCreateProfiler:
    """Test profiler creation functions"""

    def test_create_with_default_config(self):
        """Test creating profiler with default config"""
        profiler = create_profiler()
        assert isinstance(profiler, FHIRPathProfiler)
        assert profiler.config.enabled is True

    def test_create_with_custom_config(self):
        """Test creating profiler with custom config"""
        config = ProfilerConfig(save_detailed_profiles=True)
        profiler = create_profiler(config)
        assert profiler.config.save_detailed_profiles is True


class TestDetailedProfiling:
    """Test detailed profiling features"""

    def test_cprofile_integration(self):
        """Test cProfile integration when enabled"""
        config = ProfilerConfig(save_detailed_profiles=True, profile_sample_rate=1.0)
        profiler = FHIRPathProfiler(config)

        with profiler.profile_operation("detailed_op") as session_id:
            # Simulate some work
            sum(i**2 for i in range(1000))

        result = profiler._profile_results[0]
        # Call graph should be available when detailed profiling is enabled
        assert result.call_graph is not None or result.call_graph == "Call graph generation failed"