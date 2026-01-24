"""
Multi-Database Validation for FHIRPath Implementation

Validates consistent behavior across DuckDB and PostgreSQL platforms,
ensuring identical results and maintaining thin dialect architecture.
"""

import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime

from fhir4ds.fhirpath.parser import FHIRPathParser
from tests.compliance.fhirpath.test_parser import parse_fhirpath_tests


@dataclass
class DatabaseResult:
    """Result from a single database execution"""
    database_type: str
    expression: str
    result: Any
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None
    result_hash: Optional[str] = None


@dataclass
class ConsistencyCheck:
    """Consistency check between database results"""
    expression: str
    databases: List[str]
    consistent: bool
    results: List[DatabaseResult]
    consistency_issues: List[str]
    execution_time_variance_ms: float


@dataclass
class MultiDatabaseReport:
    """Comprehensive multi-database validation report"""
    total_expressions: int
    consistent_expressions: int
    inconsistent_expressions: int
    consistency_percentage: float
    databases_tested: List[str]
    execution_time_total_ms: float
    consistency_checks: List[ConsistencyCheck]
    database_performance: Dict[str, Dict[str, float]]
    architectural_compliance: Dict[str, Any]
    timestamp: str


class MultiDatabaseValidator:
    """
    Multi-Database Validation System

    Validates that FHIRPath expressions produce identical results across
    different database platforms, ensuring thin dialect architecture compliance.
    """

    def __init__(self, database_types: List[str] = None):
        """Initialize multi-database validator"""
        if database_types is None:
            database_types = ["duckdb", "postgresql"]

        self.database_types = database_types
        self.parsers = {
            db_type: FHIRPathParser(database_type=db_type)
            for db_type in database_types
        }

    def validate_expression(self, expression: str) -> ConsistencyCheck:
        """
        Validate a single expression across all databases

        Args:
            expression: FHIRPath expression to validate

        Returns:
            Consistency check results
        """
        results = []

        for db_type in self.database_types:
            try:
                start_time = time.time()
                result = self.parsers[db_type].evaluate(expression)
                execution_time = (time.time() - start_time) * 1000

                # Create hash of result for comparison
                result_hash = self._hash_result(result)

                results.append(DatabaseResult(
                    database_type=db_type,
                    expression=expression,
                    result=result,
                    execution_time_ms=execution_time,
                    success=True,
                    result_hash=result_hash
                ))

            except Exception as e:
                results.append(DatabaseResult(
                    database_type=db_type,
                    expression=expression,
                    result=None,
                    execution_time_ms=0.0,
                    success=False,
                    error_message=str(e)
                ))

        # Check consistency
        consistent, issues = self._check_consistency(results)

        # Calculate execution time variance
        execution_times = [r.execution_time_ms for r in results if r.success]
        variance = max(execution_times) - min(execution_times) if len(execution_times) > 1 else 0.0

        return ConsistencyCheck(
            expression=expression,
            databases=self.database_types,
            consistent=consistent,
            results=results,
            consistency_issues=issues,
            execution_time_variance_ms=variance
        )

    def validate_expression_set(self,
                               expressions: List[str],
                               max_expressions: Optional[int] = None) -> MultiDatabaseReport:
        """
        Validate a set of expressions across all databases

        Args:
            expressions: List of FHIRPath expressions to validate
            max_expressions: Maximum number of expressions to validate

        Returns:
            Comprehensive multi-database validation report
        """
        if max_expressions:
            expressions = expressions[:max_expressions]

        print(f"Validating {len(expressions)} expressions across {len(self.database_types)} databases...")

        start_time = time.time()
        consistency_checks = []

        for i, expression in enumerate(expressions):
            if i % 50 == 0:
                print(f"Progress: {i}/{len(expressions)} expressions validated")

            check = self.validate_expression(expression)
            consistency_checks.append(check)

        total_time = (time.time() - start_time) * 1000

        # Generate report
        return self._generate_report(consistency_checks, total_time)

    def validate_official_tests(self, max_tests: Optional[int] = None) -> MultiDatabaseReport:
        """
        Validate official FHIRPath test suite across databases

        Args:
            max_tests: Maximum number of tests to validate

        Returns:
            Multi-database validation report for official tests
        """
        official_tests = parse_fhirpath_tests()

        if max_tests:
            official_tests = official_tests[:max_tests]

        expressions = [test['expression'] for test in official_tests]

        print(f"Validating {len(expressions)} official FHIRPath expressions...")
        return self.validate_expression_set(expressions)

    def _hash_result(self, result: Any) -> str:
        """Create hash of result for comparison"""
        if result is None:
            return "none"

        try:
            # Convert result to a normalized JSON string for hashing
            result_str = json.dumps(result, sort_keys=True, default=str)
            return hashlib.md5(result_str.encode()).hexdigest()
        except Exception:
            return str(hash(str(result)))

    def _check_consistency(self, results: List[DatabaseResult]) -> Tuple[bool, List[str]]:
        """Check consistency between database results"""
        issues = []

        # Check if all databases succeeded
        success_count = sum(1 for r in results if r.success)
        if success_count == 0:
            issues.append("All databases failed to execute expression")
            return False, issues

        if success_count < len(results):
            failed_dbs = [r.database_type for r in results if not r.success]
            issues.append(f"Execution failed on databases: {failed_dbs}")

        # Check result consistency among successful executions
        successful_results = [r for r in results if r.success]
        if len(successful_results) <= 1:
            return len(issues) == 0, issues

        # Compare result hashes
        result_hashes = set(r.result_hash for r in successful_results)
        if len(result_hashes) > 1:
            issues.append("Results differ between databases")
            for r in successful_results:
                issues.append(f"  {r.database_type}: hash {r.result_hash[:8]}...")

        # Check for significant performance differences (>100x)
        execution_times = [r.execution_time_ms for r in successful_results]
        if max(execution_times) > min(execution_times) * 100:
            issues.append("Significant performance difference between databases")

        return len(issues) == 0, issues

    def _generate_report(self, consistency_checks: List[ConsistencyCheck], total_time_ms: float) -> MultiDatabaseReport:
        """Generate comprehensive multi-database validation report"""
        total_expressions = len(consistency_checks)
        consistent_expressions = sum(1 for check in consistency_checks if check.consistent)
        inconsistent_expressions = total_expressions - consistent_expressions

        consistency_percentage = (consistent_expressions / total_expressions * 100) if total_expressions > 0 else 0

        # Calculate database performance metrics
        database_performance = {}
        for db_type in self.database_types:
            db_results = []
            for check in consistency_checks:
                db_result = next((r for r in check.results if r.database_type == db_type), None)
                if db_result and db_result.success:
                    db_results.append(db_result.execution_time_ms)

            if db_results:
                database_performance[db_type] = {
                    "average_execution_time_ms": sum(db_results) / len(db_results),
                    "min_execution_time_ms": min(db_results),
                    "max_execution_time_ms": max(db_results),
                    "successful_executions": len(db_results),
                    "total_executions": total_expressions
                }

        # Architectural compliance assessment
        architectural_compliance = self._assess_architectural_compliance(consistency_checks)

        return MultiDatabaseReport(
            total_expressions=total_expressions,
            consistent_expressions=consistent_expressions,
            inconsistent_expressions=inconsistent_expressions,
            consistency_percentage=consistency_percentage,
            databases_tested=self.database_types,
            execution_time_total_ms=total_time_ms,
            consistency_checks=consistency_checks,
            database_performance=database_performance,
            architectural_compliance=architectural_compliance,
            timestamp=datetime.now().isoformat()
        )

    def _assess_architectural_compliance(self, consistency_checks: List[ConsistencyCheck]) -> Dict[str, Any]:
        """Assess compliance with thin dialect architecture principles"""
        total_checks = len(consistency_checks)
        business_logic_violations = 0
        performance_outliers = 0
        error_inconsistencies = 0

        for check in consistency_checks:
            # Check for business logic violations (different results for same expression)
            if not check.consistent:
                successful_results = [r for r in check.results if r.success]
                if len(successful_results) > 1:
                    unique_hashes = set(r.result_hash for r in successful_results)
                    if len(unique_hashes) > 1:
                        business_logic_violations += 1

            # Check for performance outliers (>10x difference)
            execution_times = [r.execution_time_ms for r in check.results if r.success]
            if len(execution_times) > 1:
                if max(execution_times) > min(execution_times) * 10:
                    performance_outliers += 1

            # Check for error inconsistencies (one DB fails, others succeed)
            success_count = sum(1 for r in check.results if r.success)
            if 0 < success_count < len(check.results):
                error_inconsistencies += 1

        return {
            "total_expressions_tested": total_checks,
            "business_logic_violations": business_logic_violations,
            "business_logic_compliance_percentage": (
                (total_checks - business_logic_violations) / total_checks * 100
                if total_checks > 0 else 0
            ),
            "performance_outliers": performance_outliers,
            "performance_consistency_percentage": (
                (total_checks - performance_outliers) / total_checks * 100
                if total_checks > 0 else 0
            ),
            "error_inconsistencies": error_inconsistencies,
            "error_handling_consistency_percentage": (
                (total_checks - error_inconsistencies) / total_checks * 100
                if total_checks > 0 else 0
            ),
            "overall_architectural_compliance": (
                consistency_checks[0].consistent if consistency_checks else 0
            )
        }

    def print_validation_summary(self, report: MultiDatabaseReport) -> None:
        """Print formatted multi-database validation summary"""
        print("\n" + "="*70)
        print("MULTI-DATABASE VALIDATION REPORT")
        print("="*70)
        print(f"Databases Tested: {', '.join(report.databases_tested)}")
        print(f"Total Expressions: {report.total_expressions}")
        print(f"Consistent: {report.consistent_expressions}")
        print(f"Inconsistent: {report.inconsistent_expressions}")
        print(f"Consistency Rate: {report.consistency_percentage:.1f}%")
        print(f"Total Validation Time: {report.execution_time_total_ms:.1f}ms")

        print("\nDatabase Performance:")
        for db_type, metrics in report.database_performance.items():
            print(f"  {db_type.upper()}:")
            print(f"    Average execution time: {metrics['average_execution_time_ms']:.1f}ms")
            print(f"    Success rate: {metrics['successful_executions']}/{metrics['total_executions']}")

        arch_compliance = report.architectural_compliance
        print("\nArchitectural Compliance:")
        print(f"  Business Logic Compliance: {arch_compliance['business_logic_compliance_percentage']:.1f}%")
        print(f"  Performance Consistency: {arch_compliance['performance_consistency_percentage']:.1f}%")
        print(f"  Error Handling Consistency: {arch_compliance['error_handling_consistency_percentage']:.1f}%")

        # Show first few inconsistencies
        inconsistent_checks = [c for c in report.consistency_checks if not c.consistent]
        if inconsistent_checks:
            print(f"\nFirst {min(5, len(inconsistent_checks))} Inconsistencies:")
            for check in inconsistent_checks[:5]:
                print(f"  Expression: {check.expression}")
                for issue in check.consistency_issues:
                    print(f"    - {issue}")

    def save_validation_report(self, report: MultiDatabaseReport, output_path: Path) -> Path:
        """Save validation report to JSON file"""
        # Convert consistency checks to serializable format
        serializable_report = asdict(report)

        with open(output_path, 'w') as f:
            json.dump(serializable_report, f, indent=2, default=str)

        return output_path


def validate_multi_database_consistency(database_types: List[str] = None,
                                      max_tests: Optional[int] = None) -> MultiDatabaseReport:
    """
    Convenience function for multi-database validation

    Args:
        database_types: List of database types to validate (defaults to duckdb, postgresql)
        max_tests: Maximum number of tests to validate

    Returns:
        Multi-database validation report
    """
    if database_types is None:
        database_types = ["duckdb", "postgresql"]

    validator = MultiDatabaseValidator(database_types)
    report = validator.validate_official_tests(max_tests=max_tests)
    validator.print_validation_summary(report)

    return report


if __name__ == "__main__":
    # Demonstrate multi-database validation
    print("Demonstrating multi-database validation...")

    # Note: PostgreSQL validation would require actual PostgreSQL connection
    # For demonstration, we'll validate DuckDB only
    print("Running validation for DuckDB (PostgreSQL would require connection)...")

    report = validate_multi_database_consistency(
        database_types=["duckdb"],  # Only DuckDB for demo
        max_tests=50
    )

    # Save report
    validator = MultiDatabaseValidator(["duckdb"])
    output_path = validator.save_validation_report(report, Path("multi_database_validation.json"))
    print(f"\nValidation report saved to: {output_path}")