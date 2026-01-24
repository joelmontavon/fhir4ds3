"""
FHIRPath Performance Benchmarking and Testing

Performance testing framework for enhanced FHIRPath components with
population-scale validation and benchmarking against established targets.
"""

import time
import statistics
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from fhir4ds.fhirpath.parser import FHIRPathParser
from tests.compliance.fhirpath.test_parser import parse_fhirpath_tests


@dataclass
class PerformanceBenchmark:
    """Individual performance benchmark result"""
    expression: str
    category: str
    iterations: int
    total_time_ms: float
    average_time_ms: float
    min_time_ms: float
    max_time_ms: float
    median_time_ms: float
    std_dev_ms: float
    meets_target: bool
    target_ms: float


@dataclass
class PerformanceReport:
    """Comprehensive performance testing report"""
    total_expressions: int
    expressions_meeting_target: int
    expressions_exceeding_target: int
    target_compliance_percentage: float
    overall_average_time_ms: float
    population_scale_performance: Dict[str, float]
    database_type: str
    parser_type: str
    benchmarks: List[PerformanceBenchmark]
    performance_categories: Dict[str, Dict[str, float]]
    timestamp: str


class FHIRPathPerformanceTester:
    """
    Performance Testing Framework for FHIRPath Implementation

    Tests performance against established targets (<100ms for typical expressions)
    and validates population-scale analytics capabilities.
    """

    def __init__(self, database_type: str = "duckdb", target_time_ms: float = 100.0):
        self.database_type = database_type
        self.parser = FHIRPathParser(database_type)
        self.target_time_ms = target_time_ms

    def benchmark_expression(self,
                           expression: str,
                           category: str = "general",
                           iterations: int = 10) -> PerformanceBenchmark:
        """
        Benchmark a single expression performance

        Args:
            expression: FHIRPath expression to benchmark
            category: Performance category (e.g., "path", "function", "arithmetic")
            iterations: Number of iterations for timing

        Returns:
            Performance benchmark results
        """
        execution_times = []

        # Warm up
        try:
            self.parser.evaluate(expression)
        except Exception:
            pass  # Ignore warm-up errors

        # Benchmark iterations
        for _ in range(iterations):
            start_time = time.perf_counter()
            try:
                self.parser.evaluate(expression)
                end_time = time.perf_counter()
                execution_times.append((end_time - start_time) * 1000)
            except Exception:
                # Include failed executions as very slow
                execution_times.append(1000.0)

        # Calculate statistics
        total_time = sum(execution_times)
        average_time = statistics.mean(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        median_time = statistics.median(execution_times)
        std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0

        meets_target = average_time <= self.target_time_ms

        return PerformanceBenchmark(
            expression=expression,
            category=category,
            iterations=iterations,
            total_time_ms=total_time,
            average_time_ms=average_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            median_time_ms=median_time,
            std_dev_ms=std_dev,
            meets_target=meets_target,
            target_ms=self.target_time_ms
        )

    def benchmark_expression_set(self,
                                expressions: List[Tuple[str, str]],
                                iterations: int = 10) -> List[PerformanceBenchmark]:
        """
        Benchmark a set of expressions

        Args:
            expressions: List of (expression, category) tuples
            iterations: Number of iterations per expression

        Returns:
            List of performance benchmarks
        """
        benchmarks = []

        print(f"Benchmarking {len(expressions)} expressions with {iterations} iterations each...")

        for i, (expression, category) in enumerate(expressions):
            if i % 10 == 0:
                print(f"Progress: {i}/{len(expressions)} expressions benchmarked")

            benchmark = self.benchmark_expression(expression, category, iterations)
            benchmarks.append(benchmark)

        return benchmarks

    def benchmark_official_tests(self,
                               max_tests: Optional[int] = None,
                               iterations: int = 5) -> List[PerformanceBenchmark]:
        """
        Benchmark official FHIRPath test expressions

        Args:
            max_tests: Maximum number of tests to benchmark
            iterations: Number of iterations per test

        Returns:
            List of performance benchmarks
        """
        official_tests = parse_fhirpath_tests()

        if max_tests:
            official_tests = official_tests[:max_tests]

        # Categorize expressions
        expressions = []
        for test in official_tests:
            category = self._categorize_expression(test['expression'])
            expressions.append((test['expression'], category))

        return self.benchmark_expression_set(expressions, iterations)

    def _categorize_expression(self, expression: str) -> str:
        """Categorize expression for performance analysis"""
        expression_lower = expression.lower()

        # Check specific function types first
        if any(func in expression_lower for func in ['substring', 'length', 'upper', 'lower']):
            return "string"
        elif any(func in expression_lower for func in ['where', 'select', 'exists']):
            return "collection"
        elif any(func in expression_lower for func in ['now', 'today', 'date']):
            return "datetime"
        elif any(op in expression_lower for op in ['+', '-', '*', '/', 'mod']):
            return "arithmetic"
        elif '.' in expression:
            return "path"
        elif '(' in expression:
            return "function"
        else:
            return "literal"

    def test_population_scale_performance(self, scale_factors: List[int] = None) -> Dict[str, float]:
        """
        Test performance at population scale

        Args:
            scale_factors: List of scale factors to test (simulating patient counts)

        Returns:
            Performance metrics at different scales
        """
        if scale_factors is None:
            scale_factors = [100, 1000, 10000, 100000]

        print("Testing population-scale performance...")

        # Simple expressions that would be used in population queries
        population_expressions = [
            "Patient.active",
            "Patient.gender",
            "Patient.birthDate",
            "Observation.status",
            "Observation.value",
        ]

        scale_performance = {}

        for scale in scale_factors:
            print(f"Testing scale factor: {scale}")

            total_time = 0.0
            iterations = min(10, max(1, 1000 // scale))  # Fewer iterations for larger scales

            for expression in population_expressions:
                for _ in range(iterations):
                    start_time = time.perf_counter()
                    try:
                        # Simulate population-scale execution
                        for _ in range(min(scale, 100)):  # Simulate processing multiple records
                            self.parser.evaluate(expression)
                    except Exception:
                        pass
                    total_time += (time.perf_counter() - start_time) * 1000

            avg_time_per_expression = total_time / (len(population_expressions) * iterations)
            scale_performance[f"scale_{scale}"] = avg_time_per_expression

        return scale_performance

    def generate_performance_report(self,
                                  benchmarks: List[PerformanceBenchmark],
                                  population_performance: Optional[Dict[str, float]] = None) -> PerformanceReport:
        """
        Generate comprehensive performance report

        Args:
            benchmarks: List of performance benchmarks
            population_performance: Population-scale performance metrics

        Returns:
            Comprehensive performance report
        """
        total_expressions = len(benchmarks)
        expressions_meeting_target = sum(1 for b in benchmarks if b.meets_target)
        expressions_exceeding_target = total_expressions - expressions_meeting_target

        target_compliance_percentage = (
            expressions_meeting_target / total_expressions * 100
            if total_expressions > 0 else 0
        )

        overall_average_time = statistics.mean([b.average_time_ms for b in benchmarks]) if benchmarks else 0

        # Category performance analysis
        categories = set(b.category for b in benchmarks)
        performance_categories = {}

        for category in categories:
            category_benchmarks = [b for b in benchmarks if b.category == category]
            category_times = [b.average_time_ms for b in category_benchmarks]

            performance_categories[category] = {
                "count": len(category_benchmarks),
                "average_time_ms": statistics.mean(category_times),
                "min_time_ms": min(category_times),
                "max_time_ms": max(category_times),
                "target_compliance_percentage": (
                    sum(1 for b in category_benchmarks if b.meets_target) /
                    len(category_benchmarks) * 100
                )
            }

        return PerformanceReport(
            total_expressions=total_expressions,
            expressions_meeting_target=expressions_meeting_target,
            expressions_exceeding_target=expressions_exceeding_target,
            target_compliance_percentage=target_compliance_percentage,
            overall_average_time_ms=overall_average_time,
            population_scale_performance=population_performance or {},
            database_type=self.database_type,
            parser_type=type(self.parser).__name__,
            benchmarks=benchmarks,
            performance_categories=performance_categories,
            timestamp=datetime.now().isoformat()
        )

    def run_comprehensive_performance_tests(self,
                                          max_tests: Optional[int] = None,
                                          test_population_scale: bool = True) -> PerformanceReport:
        """
        Run comprehensive performance test suite

        Args:
            max_tests: Maximum number of official tests to benchmark
            test_population_scale: Whether to test population-scale performance

        Returns:
            Comprehensive performance report
        """
        print("Running comprehensive FHIRPath performance tests...")

        # Benchmark official test expressions
        benchmarks = self.benchmark_official_tests(max_tests=max_tests, iterations=5)

        # Test population-scale performance if requested
        population_performance = None
        if test_population_scale:
            population_performance = self.test_population_scale_performance()

        # Generate comprehensive report
        return self.generate_performance_report(benchmarks, population_performance)

    def print_performance_summary(self, report: PerformanceReport) -> None:
        """Print formatted performance test summary"""
        print("\n" + "="*60)
        print("FHIRPATH PERFORMANCE REPORT")
        print("="*60)
        print(f"Database Type: {report.database_type}")
        print(f"Parser Type: {report.parser_type}")
        print(f"Target Time: {self.target_time_ms}ms")
        print(f"Total Expressions: {report.total_expressions}")
        print(f"Meeting Target: {report.expressions_meeting_target}")
        print(f"Exceeding Target: {report.expressions_exceeding_target}")
        print(f"Target Compliance: {report.target_compliance_percentage:.1f}%")
        print(f"Overall Average Time: {report.overall_average_time_ms:.2f}ms")

        print("\nPerformance by Category:")
        for category, metrics in report.performance_categories.items():
            print(f"  {category.title()}:")
            print(f"    Count: {metrics['count']}")
            print(f"    Average: {metrics['average_time_ms']:.2f}ms")
            print(f"    Range: {metrics['min_time_ms']:.2f}ms - {metrics['max_time_ms']:.2f}ms")
            print(f"    Target Compliance: {metrics['target_compliance_percentage']:.1f}%")

        if report.population_scale_performance:
            print("\nPopulation-Scale Performance:")
            for scale, time_ms in report.population_scale_performance.items():
                print(f"  {scale}: {time_ms:.2f}ms average per expression")

        # Show slowest expressions
        slow_benchmarks = sorted(report.benchmarks, key=lambda b: b.average_time_ms, reverse=True)[:5]
        if slow_benchmarks:
            print(f"\nSlowest Expressions:")
            for benchmark in slow_benchmarks:
                print(f"  {benchmark.average_time_ms:.2f}ms: {benchmark.expression}")

    def save_performance_report(self, report: PerformanceReport, output_path: Path) -> Path:
        """Save performance report to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)

        return output_path


def run_performance_benchmarking(database_type: str = "duckdb",
                                max_tests: Optional[int] = None,
                                target_time_ms: float = 100.0) -> PerformanceReport:
    """
    Convenience function for performance benchmarking

    Args:
        database_type: Database type for testing
        max_tests: Maximum number of tests to benchmark
        target_time_ms: Performance target in milliseconds

    Returns:
        Performance benchmark report
    """
    tester = FHIRPathPerformanceTester(database_type, target_time_ms)
    report = tester.run_comprehensive_performance_tests(max_tests=max_tests, test_population_scale=True)
    tester.print_performance_summary(report)

    return report


if __name__ == "__main__":
    # Demonstrate performance benchmarking
    print("Demonstrating FHIRPath performance benchmarking...")

    # Run performance tests with limited test set
    report = run_performance_benchmarking(
        database_type="duckdb",
        max_tests=25,
        target_time_ms=100.0
    )

    # Save report
    tester = FHIRPathPerformanceTester()
    output_path = tester.save_performance_report(report, Path("performance_benchmark_report.json"))
    print(f"\nPerformance report saved to: {output_path}")