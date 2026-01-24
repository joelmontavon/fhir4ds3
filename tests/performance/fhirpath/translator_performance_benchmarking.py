"""
FHIRPath AST-to-SQL Translator Performance Benchmarking

Performance testing framework for the AST-to-SQL translator (PEP-003) to validate
the <10ms translation target for typical healthcare expressions.

Task: SP-005-025 - Performance Benchmarking
Phase: 6 - Integration and Documentation

Acceptance Criteria:
- [ ] <10ms translation for typical expressions validated
- [ ] Performance report generated
- [ ] Bottlenecks identified and documented
- [ ] Optimization opportunities noted

Module: tests.performance.fhirpath.translator_performance_benchmarking
Created: 2025-10-02
"""

import time
import statistics
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect


@dataclass
class TranslatorBenchmark:
    """Individual translator performance benchmark result"""
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
    fragment_count: int
    ast_node_count: int = 0


@dataclass
class TranslatorPerformanceReport:
    """Comprehensive translator performance testing report"""
    total_expressions: int
    expressions_meeting_target: int
    expressions_exceeding_target: int
    target_compliance_percentage: float
    overall_average_time_ms: float
    database_type: str
    benchmarks: List[TranslatorBenchmark]
    performance_categories: Dict[str, Dict[str, float]]
    bottlenecks: List[Dict[str, Any]]
    optimization_opportunities: List[str]
    timestamp: str
    target_ms: float


class TranslatorPerformanceTester:
    """
    Performance Testing Framework for AST-to-SQL Translator

    Tests translator performance against <10ms target for typical expressions
    and identifies bottlenecks and optimization opportunities.
    """

    def __init__(self, database_type: str = "duckdb", target_time_ms: float = 10.0):
        """
        Initialize translator performance tester

        Args:
            database_type: Database dialect to test ("duckdb" or "postgresql")
            target_time_ms: Performance target in milliseconds (default: 10ms)
        """
        self.database_type = database_type
        self.target_time_ms = target_time_ms

        # Initialize parser and dialect
        self.parser = FHIRPathParser(database_type)

        if database_type == "duckdb":
            self.dialect = DuckDBDialect(database=":memory:")
        elif database_type == "postgresql":
            self.dialect = PostgreSQLDialect(
                connection_string="postgresql://postgres:postgres@localhost:5432/postgres"
            )
        else:
            raise ValueError(f"Unsupported database type: {database_type}")

    def benchmark_translation(self,
                            expression: str,
                            category: str = "general",
                            iterations: int = 100) -> TranslatorBenchmark:
        """
        Benchmark translation performance for a single expression

        Args:
            expression: FHIRPath expression to benchmark
            category: Category for performance analysis
            iterations: Number of iterations for timing

        Returns:
            Performance benchmark results
        """
        execution_times = []
        fragment_count = 0
        ast_node_count = 0

        # Warm up - parse once
        try:
            expression_obj = self.parser.parse(expression)
            enhanced_ast = expression_obj.get_ast()
        except Exception as e:
            # If parsing fails, return failed benchmark
            return self._create_failed_benchmark(expression, category, iterations)

        # Benchmark iterations - translation only
        for _ in range(iterations):
            start_time = time.perf_counter()
            try:
                # Parse expression (we benchmark full workflow including parsing)
                expression_obj = self.parser.parse(expression)

                # Get enhanced AST from parser
                enhanced_ast = expression_obj.get_ast()

                # Convert to FHIRPath AST format
                fhirpath_ast = enhanced_ast

                # Create translator
                translator = ASTToSQLTranslator(self.dialect, "Patient")

                # Translate to SQL fragments
                fragments = translator.translate(fhirpath_ast)

                end_time = time.perf_counter()
                execution_times.append((end_time - start_time) * 1000)

                # Track fragment count from last iteration
                fragment_count = len(fragments)

            except Exception as e:
                # Include failed translations as very slow
                execution_times.append(1000.0)

        # Calculate statistics
        total_time = sum(execution_times)
        average_time = statistics.mean(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        median_time = statistics.median(execution_times)
        std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0

        meets_target = average_time <= self.target_time_ms

        return TranslatorBenchmark(
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
            target_ms=self.target_time_ms,
            fragment_count=fragment_count,
            ast_node_count=ast_node_count
        )

    def _create_failed_benchmark(self,
                                expression: str,
                                category: str,
                                iterations: int) -> TranslatorBenchmark:
        """Create a failed benchmark result"""
        return TranslatorBenchmark(
            expression=expression,
            category=category,
            iterations=iterations,
            total_time_ms=1000.0 * iterations,
            average_time_ms=1000.0,
            min_time_ms=1000.0,
            max_time_ms=1000.0,
            median_time_ms=1000.0,
            std_dev_ms=0.0,
            meets_target=False,
            target_ms=self.target_time_ms,
            fragment_count=0,
            ast_node_count=0
        )

    def benchmark_typical_expressions(self, iterations: int = 100) -> List[TranslatorBenchmark]:
        """
        Benchmark typical healthcare FHIRPath expressions

        Args:
            iterations: Number of iterations per expression

        Returns:
            List of performance benchmarks
        """
        # Typical healthcare expressions organized by category
        typical_expressions = [
            # Simple path navigation
            ("Patient.name", "path_simple"),
            ("Patient.birthDate", "path_simple"),
            ("Patient.gender", "path_simple"),
            ("Observation.status", "path_simple"),
            ("Observation.value", "path_simple"),

            # Nested path navigation
            ("Patient.name.family", "path_nested"),
            ("Patient.name.given", "path_nested"),
            ("Patient.address.city", "path_nested"),
            ("Observation.code.coding", "path_nested"),
            ("Observation.value.unit", "path_nested"),

            # Simple operators
            ("Patient.active = true", "operator_comparison"),
            ("Patient.gender = 'male'", "operator_comparison"),
            ("Observation.value > 100", "operator_comparison"),
            ("Patient.birthDate < @2000-01-01", "operator_comparison"),
            ("Observation.status = 'final'", "operator_comparison"),

            # Logical operators
            ("Patient.active = true and Patient.gender = 'male'", "operator_logical"),
            ("Observation.status = 'final' or Observation.status = 'amended'", "operator_logical"),

            # Array operations - where()
            ("Patient.name.where(use = 'official')", "array_where"),
            ("Patient.address.where(use = 'home')", "array_where"),
            ("Observation.code.coding.where(system = 'http://loinc.org')", "array_where"),

            # Array operations - first()
            ("Patient.name.first()", "array_first"),
            ("Patient.address.first()", "array_first"),
            ("Observation.value.first()", "array_first"),

            # Array operations - select()
            ("Patient.name.select(family)", "array_select"),
            ("Patient.address.select(city)", "array_select"),

            # Existence checking
            ("Patient.name.exists()", "exists"),
            ("Patient.address.exists()", "exists"),
            ("Observation.value.exists()", "exists"),
            ("Patient.name.exists(use = 'official')", "exists_criteria"),

            # Complex multi-step expressions
            ("Patient.name.where(use = 'official').first().family", "complex_chain"),
            ("Patient.address.where(use = 'home').select(city)", "complex_chain"),
            ("Observation.code.coding.where(system = 'http://loinc.org').first().code", "complex_chain"),

            # Literals
            ("'test string'", "literal"),
            ("123", "literal"),
            ("true", "literal"),
            ("@2024-01-01", "literal"),
        ]

        benchmarks = []

        print(f"\nBenchmarking {len(typical_expressions)} typical expressions...")
        print(f"Target: {self.target_time_ms}ms per expression")
        print(f"Iterations per expression: {iterations}")

        for i, (expression, category) in enumerate(typical_expressions):
            if i % 10 == 0 and i > 0:
                print(f"Progress: {i}/{len(typical_expressions)} expressions benchmarked")

            benchmark = self.benchmark_translation(expression, category, iterations)
            benchmarks.append(benchmark)

            # Print real-time feedback for slow expressions
            if not benchmark.meets_target:
                print(f"  ⚠️  {expression[:50]}: {benchmark.average_time_ms:.2f}ms (exceeds {self.target_time_ms}ms)")

        print(f"Completed: {len(typical_expressions)}/{len(typical_expressions)} expressions benchmarked\n")

        return benchmarks

    def identify_bottlenecks(self, benchmarks: List[TranslatorBenchmark]) -> List[Dict[str, Any]]:
        """
        Identify performance bottlenecks from benchmark results

        Args:
            benchmarks: List of performance benchmarks

        Returns:
            List of identified bottlenecks with details
        """
        bottlenecks = []

        # Sort by average time (slowest first)
        slow_benchmarks = sorted(benchmarks, key=lambda b: b.average_time_ms, reverse=True)

        # Identify top 10 slowest expressions
        for benchmark in slow_benchmarks[:10]:
            if not benchmark.meets_target:
                bottlenecks.append({
                    "expression": benchmark.expression,
                    "category": benchmark.category,
                    "average_time_ms": benchmark.average_time_ms,
                    "target_ms": benchmark.target_ms,
                    "slowdown_factor": benchmark.average_time_ms / benchmark.target_ms,
                    "fragment_count": benchmark.fragment_count,
                    "std_dev_ms": benchmark.std_dev_ms
                })

        return bottlenecks

    def identify_optimization_opportunities(self,
                                          benchmarks: List[TranslatorBenchmark],
                                          bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """
        Identify optimization opportunities based on benchmark analysis

        Args:
            benchmarks: List of performance benchmarks
            bottlenecks: List of identified bottlenecks

        Returns:
            List of optimization opportunities
        """
        opportunities = []

        # Analyze category performance
        category_performance = {}
        for benchmark in benchmarks:
            if benchmark.category not in category_performance:
                category_performance[benchmark.category] = []
            category_performance[benchmark.category].append(benchmark.average_time_ms)

        # Identify slow categories
        for category, times in category_performance.items():
            avg_time = statistics.mean(times)
            if avg_time > self.target_time_ms:
                opportunities.append(
                    f"Optimize {category} operations (avg: {avg_time:.2f}ms, "
                    f"target: {self.target_time_ms}ms)"
                )

        # Analyze fragment count correlation
        fragment_counts = [b.fragment_count for b in benchmarks]
        times = [b.average_time_ms for b in benchmarks]

        if fragment_counts and times:
            avg_fragments = statistics.mean(fragment_counts)
            max_fragments = max(fragment_counts)

            if max_fragments > avg_fragments * 2:
                opportunities.append(
                    f"High fragment count detected (max: {max_fragments}, avg: {avg_fragments:.1f}) "
                    f"- consider fragment consolidation"
                )

        # Analyze variance
        high_variance_benchmarks = [b for b in benchmarks if b.std_dev_ms > b.average_time_ms * 0.5]
        if len(high_variance_benchmarks) > len(benchmarks) * 0.1:
            opportunities.append(
                f"High performance variance detected in {len(high_variance_benchmarks)} expressions "
                f"- investigate caching or warm-up issues"
            )

        # Check if any expressions are extremely slow
        extremely_slow = [b for b in benchmarks if b.average_time_ms > self.target_time_ms * 10]
        if extremely_slow:
            opportunities.append(
                f"{len(extremely_slow)} expressions exceed 10x target time - "
                f"investigate parsing or AST conversion overhead"
            )

        return opportunities

    def generate_performance_report(self,
                                   benchmarks: List[TranslatorBenchmark]) -> TranslatorPerformanceReport:
        """
        Generate comprehensive translator performance report

        Args:
            benchmarks: List of performance benchmarks

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
                "median_time_ms": statistics.median(category_times),
                "target_compliance_percentage": (
                    sum(1 for b in category_benchmarks if b.meets_target) /
                    len(category_benchmarks) * 100
                )
            }

        # Identify bottlenecks and optimization opportunities
        bottlenecks = self.identify_bottlenecks(benchmarks)
        optimization_opportunities = self.identify_optimization_opportunities(benchmarks, bottlenecks)

        return TranslatorPerformanceReport(
            total_expressions=total_expressions,
            expressions_meeting_target=expressions_meeting_target,
            expressions_exceeding_target=expressions_exceeding_target,
            target_compliance_percentage=target_compliance_percentage,
            overall_average_time_ms=overall_average_time,
            database_type=self.database_type,
            benchmarks=benchmarks,
            performance_categories=performance_categories,
            bottlenecks=bottlenecks,
            optimization_opportunities=optimization_opportunities,
            timestamp=datetime.now().isoformat(),
            target_ms=self.target_time_ms
        )

    def print_performance_summary(self, report: TranslatorPerformanceReport) -> None:
        """Print formatted performance test summary"""
        print("\n" + "=" * 80)
        print("AST-TO-SQL TRANSLATOR PERFORMANCE REPORT")
        print("=" * 80)
        print(f"Database Type: {report.database_type}")
        print(f"Target Time: {report.target_ms}ms")
        print(f"Timestamp: {report.timestamp}")
        print()
        print(f"Total Expressions: {report.total_expressions}")
        print(f"Meeting Target: {report.expressions_meeting_target} "
              f"({report.target_compliance_percentage:.1f}%)")
        print(f"Exceeding Target: {report.expressions_exceeding_target}")
        print(f"Overall Average Time: {report.overall_average_time_ms:.2f}ms")

        # Pass/fail verdict
        print()
        if report.target_compliance_percentage >= 90:
            print("✅ PASS: 90%+ expressions meet <10ms target")
        elif report.target_compliance_percentage >= 70:
            print("⚠️  PARTIAL: 70-90% expressions meet target - some optimization needed")
        else:
            print("❌ FAIL: <70% expressions meet target - significant optimization required")

        print("\n" + "-" * 80)
        print("PERFORMANCE BY CATEGORY")
        print("-" * 80)

        # Sort categories by average time
        sorted_categories = sorted(
            report.performance_categories.items(),
            key=lambda x: x[1]['average_time_ms'],
            reverse=True
        )

        for category, metrics in sorted_categories:
            status = "✅" if metrics['target_compliance_percentage'] >= 90 else "⚠️ "
            print(f"\n{status} {category.upper().replace('_', ' ')}")
            print(f"  Count: {metrics['count']}")
            print(f"  Average: {metrics['average_time_ms']:.2f}ms")
            print(f"  Range: {metrics['min_time_ms']:.2f}ms - {metrics['max_time_ms']:.2f}ms")
            print(f"  Median: {metrics['median_time_ms']:.2f}ms")
            print(f"  Target Compliance: {metrics['target_compliance_percentage']:.1f}%")

        if report.bottlenecks:
            print("\n" + "-" * 80)
            print(f"BOTTLENECKS IDENTIFIED ({len(report.bottlenecks)})")
            print("-" * 80)

            for i, bottleneck in enumerate(report.bottlenecks[:5], 1):
                print(f"\n{i}. {bottleneck['expression'][:60]}...")
                print(f"   Category: {bottleneck['category']}")
                print(f"   Average Time: {bottleneck['average_time_ms']:.2f}ms")
                print(f"   Slowdown Factor: {bottleneck['slowdown_factor']:.1f}x")
                print(f"   Fragments: {bottleneck['fragment_count']}")

        if report.optimization_opportunities:
            print("\n" + "-" * 80)
            print(f"OPTIMIZATION OPPORTUNITIES ({len(report.optimization_opportunities)})")
            print("-" * 80)

            for i, opportunity in enumerate(report.optimization_opportunities, 1):
                print(f"\n{i}. {opportunity}")

        print("\n" + "=" * 80)

    def save_performance_report(self, report: TranslatorPerformanceReport, output_path: Path) -> Path:
        """
        Save performance report to JSON file

        Args:
            report: Performance report to save
            output_path: Path to save JSON report

        Returns:
            Path to saved report
        """
        with open(output_path, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)

        return output_path


def run_translator_performance_benchmarking(
    database_type: str = "duckdb",
    target_time_ms: float = 10.0
) -> TranslatorPerformanceReport:
    """
    Convenience function for translator performance benchmarking

    Args:
        database_type: Database type for testing ("duckdb" or "postgresql")
        target_time_ms: Performance target in milliseconds

    Returns:
        Translator performance benchmark report
    """
    print("\n" + "=" * 80)
    print("AST-TO-SQL TRANSLATOR PERFORMANCE BENCHMARKING")
    print("=" * 80)
    print(f"Database: {database_type}")
    print(f"Target: <{target_time_ms}ms per expression")
    print("=" * 80)

    tester = TranslatorPerformanceTester(database_type, target_time_ms)

    # Benchmark typical expressions
    benchmarks = tester.benchmark_typical_expressions(iterations=100)

    # Generate comprehensive report
    report = tester.generate_performance_report(benchmarks)

    # Print summary
    tester.print_performance_summary(report)

    return report


if __name__ == "__main__":
    """Run translator performance benchmarking demonstration"""

    # Benchmark DuckDB translator
    print("\n" + "#" * 80)
    print("# DUCKDB TRANSLATOR PERFORMANCE BENCHMARKING")
    print("#" * 80)

    duckdb_report = run_translator_performance_benchmarking(
        database_type="duckdb",
        target_time_ms=10.0
    )

    # Save DuckDB report
    tester = TranslatorPerformanceTester("duckdb")
    duckdb_output = Path("translator_performance_duckdb.json")
    tester.save_performance_report(duckdb_report, duckdb_output)
    print(f"\n📊 DuckDB report saved to: {duckdb_output}")

    # Optionally benchmark PostgreSQL (requires PostgreSQL running)
    try:
        print("\n\n" + "#" * 80)
        print("# POSTGRESQL TRANSLATOR PERFORMANCE BENCHMARKING")
        print("#" * 80)

        pg_report = run_translator_performance_benchmarking(
            database_type="postgresql",
            target_time_ms=10.0
        )

        # Save PostgreSQL report
        pg_tester = TranslatorPerformanceTester("postgresql")
        pg_output = Path("translator_performance_postgresql.json")
        pg_tester.save_performance_report(pg_report, pg_output)
        print(f"\n📊 PostgreSQL report saved to: {pg_output}")

    except Exception as e:
        print(f"\n⚠️  PostgreSQL benchmarking skipped: {e}")
        print("   (Ensure PostgreSQL is running at localhost:5432)")
