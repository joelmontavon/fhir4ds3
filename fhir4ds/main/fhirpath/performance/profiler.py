"""
FHIRPath Evaluation Pipeline Profiler

This module provides detailed profiling capabilities for the FHIRPath evaluation pipeline,
including component-level timing, call stack analysis, and optimization recommendations.
"""

import time
import cProfile
import pstats
import io
import threading
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager
import logging

from ..exceptions import FHIRPathError

logger = logging.getLogger(__name__)


@dataclass
class ProfilerConfig:
    """Configuration for FHIRPath profiler"""
    enabled: bool = True
    profile_evaluation: bool = True
    profile_parsing: bool = True
    profile_collection_ops: bool = True
    profile_type_operations: bool = True
    profile_database_operations: bool = True
    max_call_depth: int = 10
    capture_call_stacks: bool = False
    save_detailed_profiles: bool = False
    profile_sample_rate: float = 0.1  # Profile 10% of operations


@dataclass
class ComponentProfile:
    """Profiling data for a specific component"""
    component_name: str
    total_time_ms: float
    call_count: int
    avg_time_ms: float
    max_time_ms: float
    min_time_ms: float
    call_stack: Optional[List[str]] = None
    sub_components: Dict[str, 'ComponentProfile'] = field(default_factory=dict)


@dataclass
class ProfileResult:
    """Complete profiling result for an operation"""
    operation_name: str
    total_time_ms: float
    components: Dict[str, ComponentProfile]
    call_graph: Optional[str] = None
    optimization_suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FHIRPathProfiler:
    """
    Detailed profiler for FHIRPath evaluation pipeline

    Provides component-level profiling with optimization recommendations
    for population-scale healthcare analytics performance.
    """

    def __init__(self, config: Optional[ProfilerConfig] = None):
        self.config = config or ProfilerConfig()
        self._active_profiles: Dict[str, Dict[str, Any]] = {}
        self._profile_results: deque = deque(maxlen=100)
        self._lock = threading.RLock()
        self._component_stats: Dict[str, List[float]] = defaultdict(list)

        logger.info(f"FHIRPath profiler initialized with config: {self.config}")

    @contextmanager
    def profile_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Profile a complete FHIRPath operation

        Args:
            operation_name: Name of the operation being profiled
            metadata: Optional metadata about the operation

        Yields:
            Profile session ID for component profiling
        """
        if not self.config.enabled:
            yield None
            return

        # Sample based on configured rate
        import random
        if random.random() > self.config.profile_sample_rate:
            yield None
            return

        session_id = f"profile_{operation_name}_{time.time()}_{threading.get_ident()}"
        start_time = time.time()

        # Initialize cProfile if detailed profiling is enabled
        profiler = None
        if self.config.save_detailed_profiles:
            profiler = cProfile.Profile()
            profiler.enable()

        with self._lock:
            self._active_profiles[session_id] = {
                'operation_name': operation_name,
                'start_time': start_time,
                'components': {},
                'call_stack': [],
                'metadata': metadata or {},
                'profiler': profiler
            }

        try:
            yield session_id
        finally:
            end_time = time.time()
            total_time_ms = (end_time - start_time) * 1000

            if profiler:
                profiler.disable()

            with self._lock:
                if session_id in self._active_profiles:
                    profile_data = self._active_profiles.pop(session_id)
                    result = self._create_profile_result(
                        operation_name, total_time_ms, profile_data, profiler
                    )
                    self._profile_results.append(result)

                    logger.debug(f"Profiled operation {operation_name}: {total_time_ms:.2f}ms")

    @contextmanager
    def profile_component(self, session_id: Optional[str], component_name: str,
                         metadata: Optional[Dict[str, Any]] = None):
        """Profile a component within an operation"""
        if not session_id or not self.config.enabled:
            yield
            return

        start_time = time.time()

        with self._lock:
            if session_id in self._active_profiles:
                self._active_profiles[session_id]['call_stack'].append(component_name)

        try:
            yield
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            with self._lock:
                if session_id in self._active_profiles:
                    profile_data = self._active_profiles[session_id]

                    # Remove from call stack
                    if profile_data['call_stack'] and profile_data['call_stack'][-1] == component_name:
                        profile_data['call_stack'].pop()

                    # Record component timing
                    if component_name not in profile_data['components']:
                        profile_data['components'][component_name] = {
                            'times': [],
                            'metadata': []
                        }

                    profile_data['components'][component_name]['times'].append(duration_ms)
                    profile_data['components'][component_name]['metadata'].append(metadata or {})

                    # Update global component stats
                    self._component_stats[component_name].append(duration_ms)

    def profile_evaluation_step(self, session_id: Optional[str], step_name: str,
                              expression: str, context_size: int = 0):
        """Profile a specific evaluation step"""
        return self.profile_component(
            session_id,
            f"evaluation.{step_name}",
            {
                'expression_length': len(expression),
                'context_size': context_size,
                'step_type': step_name
            }
        )

    def profile_collection_operation(self, session_id: Optional[str], operation: str,
                                   collection_size: int = 0):
        """Profile a collection operation"""
        return self.profile_component(
            session_id,
            f"collection.{operation}",
            {
                'collection_size': collection_size,
                'operation_type': operation
            }
        )

    def profile_type_operation(self, session_id: Optional[str], operation: str,
                              type_name: str = "unknown"):
        """Profile a type system operation"""
        return self.profile_component(
            session_id,
            f"type.{operation}",
            {
                'type_name': type_name,
                'operation_type': operation
            }
        )

    def profile_database_operation(self, session_id: Optional[str], operation: str,
                                  query_size: int = 0, result_size: int = 0):
        """Profile a database operation"""
        return self.profile_component(
            session_id,
            f"database.{operation}",
            {
                'query_size': query_size,
                'result_size': result_size,
                'operation_type': operation
            }
        )

    def get_profile_summary(self) -> Dict[str, Any]:
        """Get summary of all profiling data"""
        with self._lock:
            if not self._profile_results:
                return {'status': 'no_data'}

            total_profiles = len(self._profile_results)
            avg_time = sum(p.total_time_ms for p in self._profile_results) / total_profiles

            # Component analysis
            component_summary = {}
            for component, times in self._component_stats.items():
                if times:
                    component_summary[component] = {
                        'call_count': len(times),
                        'total_time_ms': sum(times),
                        'avg_time_ms': sum(times) / len(times),
                        'max_time_ms': max(times),
                        'percentage_of_total': (sum(times) / sum(sum(t) for t in self._component_stats.values())) * 100
                    }

            return {
                'total_profiles': total_profiles,
                'avg_operation_time_ms': avg_time,
                'component_summary': component_summary,
                'top_bottlenecks': self._identify_bottlenecks(),
                'optimization_opportunities': self._identify_optimizations()
            }

    def get_recent_profiles(self, count: int = 10) -> List[ProfileResult]:
        """Get most recent profile results"""
        with self._lock:
            return list(self._profile_results)[-count:]

    def _create_profile_result(self, operation_name: str, total_time_ms: float,
                              profile_data: Dict[str, Any], profiler: Optional[cProfile.Profile]) -> ProfileResult:
        """Create a ProfileResult from collected data"""
        components = {}

        # Process component timings
        for comp_name, comp_data in profile_data['components'].items():
            times = comp_data['times']
            if times:
                components[comp_name] = ComponentProfile(
                    component_name=comp_name,
                    total_time_ms=sum(times),
                    call_count=len(times),
                    avg_time_ms=sum(times) / len(times),
                    max_time_ms=max(times),
                    min_time_ms=min(times)
                )

        # Generate call graph if profiler was used
        call_graph = None
        if profiler:
            call_graph = self._generate_call_graph(profiler)

        # Generate optimization suggestions
        suggestions = self._generate_optimization_suggestions(components, total_time_ms)

        return ProfileResult(
            operation_name=operation_name,
            total_time_ms=total_time_ms,
            components=components,
            call_graph=call_graph,
            optimization_suggestions=suggestions,
            metadata=profile_data['metadata']
        )

    def _generate_call_graph(self, profiler: cProfile.Profile) -> str:
        """Generate call graph from cProfile data"""
        try:
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats(20)  # Top 20 functions
            return s.getvalue()
        except Exception as e:
            logger.warning(f"Failed to generate call graph: {e}")
            return "Call graph generation failed"

    def _generate_optimization_suggestions(self, components: Dict[str, ComponentProfile],
                                          total_time_ms: float) -> List[str]:
        """Generate optimization suggestions based on profiling data"""
        suggestions = []

        # Check for slow components
        for comp_name, comp_profile in components.items():
            if comp_profile.avg_time_ms > 10.0:  # > 10ms average
                suggestions.append(f"Component '{comp_name}' is slow (avg: {comp_profile.avg_time_ms:.1f}ms)")

            # Check for high variance
            if comp_profile.max_time_ms > comp_profile.avg_time_ms * 3:
                suggestions.append(f"Component '{comp_name}' has high variance - consider caching")

        # Check overall performance
        if total_time_ms > 100.0:
            suggestions.append("Overall operation is slow - consider expression optimization")

        # Check for collection operation patterns
        collection_components = [c for c in components.keys() if c.startswith('collection.')]
        if len(collection_components) > 5:
            suggestions.append("Many collection operations - consider batch processing")

        return suggestions

    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []

        for component, times in self._component_stats.items():
            if times:
                total_time = sum(times)
                avg_time = total_time / len(times)

                if avg_time > 5.0:  # Components averaging > 5ms
                    bottlenecks.append({
                        'component': component,
                        'avg_time_ms': avg_time,
                        'total_time_ms': total_time,
                        'call_count': len(times),
                        'severity': 'high' if avg_time > 20.0 else 'medium'
                    })

        return sorted(bottlenecks, key=lambda x: x['avg_time_ms'], reverse=True)[:10]

    def _identify_optimizations(self) -> List[str]:
        """Identify optimization opportunities"""
        optimizations = []

        # Analyze component patterns
        total_calls = sum(len(times) for times in self._component_stats.values())
        total_time = sum(sum(times) for times in self._component_stats.values())

        if total_calls > 100:
            optimizations.append("High call volume - consider expression caching")

        type_operations = sum(len(times) for comp, times in self._component_stats.items()
                             if comp.startswith('type.'))
        if type_operations > total_calls * 0.3:
            optimizations.append("Frequent type operations - consider type inference optimization")

        db_operations = sum(len(times) for comp, times in self._component_stats.items()
                           if comp.startswith('database.'))
        if db_operations > total_calls * 0.2:
            optimizations.append("Frequent database operations - consider query batching")

        return optimizations


def create_profiler(config: Optional[ProfilerConfig] = None) -> FHIRPathProfiler:
    """Create a FHIRPath profiler with default or custom configuration"""
    return FHIRPathProfiler(config)


# Global profiler instance
_global_profiler: Optional[FHIRPathProfiler] = None


def get_global_profiler() -> FHIRPathProfiler:
    """Get or create the global profiler"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = create_profiler()
    return _global_profiler


def configure_global_profiler(config: ProfilerConfig) -> None:
    """Configure the global profiler"""
    global _global_profiler
    _global_profiler = create_profiler(config)


@contextmanager
def profile(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Convenient context manager using global profiler"""
    with get_global_profiler().profile_operation(operation_name, metadata) as session_id:
        yield session_id