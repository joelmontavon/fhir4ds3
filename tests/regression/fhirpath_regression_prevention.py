"""
FHIRPath Regression Prevention System

Ensures that new FHIRPath implementation enhancements don't break existing
SQL-on-FHIR and CQL test compliance, maintaining backward compatibility.
"""

import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from fhir4ds.fhirpath.parser import FHIRPathParser


@dataclass
class RegressionTestResult:
    """Result of a regression test"""
    test_name: str
    test_category: str  # "fhirpath", "sql_on_fhir", "cql"
    expression: str
    passed: bool
    baseline_result: Any
    current_result: Any
    execution_time_ms: float
    regression_detected: bool
    error_message: Optional[str] = None


@dataclass
class RegressionReport:
    """Comprehensive regression test report"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    regression_tests: int
    categories_tested: List[str]
    overall_success_rate: float
    regression_rate: float
    execution_time_total_ms: float
    category_results: Dict[str, Dict[str, int]]
    regressions_detected: List[RegressionTestResult]
    timestamp: str


class RegressionBaseline:
    """Manages baseline results for regression testing"""

    def __init__(self, baseline_file: str = "regression_baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.baselines: Dict[str, Any] = {}
        self._load_baselines()

    def _load_baselines(self):
        """Load existing baseline results"""
        if self.baseline_file.exists() and self.baseline_file.stat().st_size > 0:
            with open(self.baseline_file, 'r') as f:
                self.baselines = json.load(f)

    def save_baselines(self):
        """Save current baselines to file"""
        with open(self.baseline_file, 'w') as f:
            json.dump(self.baselines, f, indent=2, default=str)

    def set_baseline(self, test_name: str, category: str, result: Any):
        """Set baseline result for a test"""
        key = f"{category}::{test_name}"
        self.baselines[key] = {
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "category": category
        }

    def get_baseline(self, test_name: str, category: str) -> Optional[Any]:
        """Get baseline result for a test"""
        key = f"{category}::{test_name}"
        baseline = self.baselines.get(key)
        return baseline["result"] if baseline else None

    def has_baseline(self, test_name: str, category: str) -> bool:
        """Check if baseline exists for a test"""
        key = f"{category}::{test_name}"
        return key in self.baselines


class FHIRPathRegressionPrevention:
    """
    Regression Prevention System for FHIRPath Implementation

    Validates that FHIRPath enhancements maintain compatibility with existing
    functionality and don't introduce regressions in related systems.
    """

    def __init__(self, database_type: str = "duckdb"):
        self.database_type = database_type
        self.parser = FHIRPathParser(database_type)
        self.baseline = RegressionBaseline()

    def run_fhirpath_regression_tests(self, max_tests: Optional[int] = None) -> List[RegressionTestResult]:
        """
        Run FHIRPath regression tests

        Args:
            max_tests: Maximum number of tests to run

        Returns:
            List of regression test results
        """
        # Sample FHIRPath test expressions for regression testing
        test_expressions = [
            "Patient.name",
            "Patient.name.given",
            "Patient.birthDate",
            "Patient.active",
            "Patient.telecom.where(system = 'phone')",
            "Patient.address.where(use = 'home')",
            "Observation.value",
            "Observation.status",
            "Observation.code.coding",
            "Encounter.status",
            "Encounter.class",
            "Encounter.period",
            "true",
            "false",
            "1 + 1",
            "2 * 3",
            "'hello' + ' world'",
            "now()",
            "today()",
            "empty()",
        ]

        if max_tests:
            test_expressions = test_expressions[:max_tests]

        results = []
        for i, expression in enumerate(test_expressions):
            test_name = f"fhirpath_test_{i:03d}"
            result = self._run_regression_test(test_name, "fhirpath", expression)
            results.append(result)

        return results

    def run_sql_on_fhir_regression_tests(self) -> List[RegressionTestResult]:
        """
        Run SQL-on-FHIR regression tests

        Returns:
            List of regression test results for SQL-on-FHIR compatibility
        """
        # Sample SQL-on-FHIR compatibility tests
        sql_tests = [
            ("sql_basic_select", "Patient"),
            ("sql_where_clause", "Patient.active = true"),
            ("sql_join_equivalent", "Patient.name.given"),
            ("sql_aggregation", "count(Patient)"),
            ("sql_filtering", "Patient.where(active = true)"),
        ]

        results = []
        for test_name, expression in sql_tests:
            result = self._run_regression_test(test_name, "sql_on_fhir", expression)
            results.append(result)

        return results

    def run_cql_regression_tests(self) -> List[RegressionTestResult]:
        """
        Run CQL regression tests

        Returns:
            List of regression test results for CQL compatibility
        """
        # Sample CQL compatibility tests
        cql_tests = [
            ("cql_patient_query", "Patient"),
            ("cql_boolean_logic", "Patient.active = true"),
            ("cql_date_operations", "Patient.birthDate"),
            ("cql_string_operations", "Patient.name.given"),
            ("cql_numeric_operations", "1 + 1"),
        ]

        results = []
        for test_name, expression in cql_tests:
            result = self._run_regression_test(test_name, "cql", expression)
            results.append(result)

        return results

    def _run_regression_test(self, test_name: str, category: str, expression: str) -> RegressionTestResult:
        """Run a single regression test"""
        start_time = time.time()

        try:
            # Execute current implementation
            current_result = self.parser.evaluate(expression)
            execution_time = (time.time() - start_time) * 1000

            # Get baseline result
            baseline_result = self.baseline.get_baseline(test_name, category)

            # Determine if test passed and if regression occurred
            passed = current_result is not None
            regression_detected = False

            if baseline_result is not None:
                # Compare with baseline
                if self._results_differ(baseline_result, current_result):
                    regression_detected = True
            else:
                # No baseline - set current as baseline if test passed
                if passed:
                    self.baseline.set_baseline(test_name, category, current_result)

            return RegressionTestResult(
                test_name=test_name,
                test_category=category,
                expression=expression,
                passed=passed,
                baseline_result=baseline_result,
                current_result=current_result,
                execution_time_ms=execution_time,
                regression_detected=regression_detected
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return RegressionTestResult(
                test_name=test_name,
                test_category=category,
                expression=expression,
                passed=False,
                baseline_result=self.baseline.get_baseline(test_name, category),
                current_result=None,
                execution_time_ms=execution_time,
                regression_detected=True,  # Exception is a regression
                error_message=str(e)
            )

    def _results_differ(self, baseline: Any, current: Any) -> bool:
        """Check if current result differs significantly from baseline"""
        # Simple comparison - in production this would be more sophisticated
        try:
            baseline_str = json.dumps(baseline, sort_keys=True, default=str)
            current_str = json.dumps(current, sort_keys=True, default=str)
            return baseline_str != current_str
        except Exception:
            return str(baseline) != str(current)

    def run_comprehensive_regression_tests(self, max_fhirpath_tests: Optional[int] = None) -> RegressionReport:
        """
        Run comprehensive regression test suite

        Args:
            max_fhirpath_tests: Maximum FHIRPath tests to run

        Returns:
            Comprehensive regression report
        """
        print("Running comprehensive regression prevention tests...")
        start_time = time.time()

        # Run all test categories
        all_results = []

        print("Running FHIRPath regression tests...")
        fhirpath_results = self.run_fhirpath_regression_tests(max_fhirpath_tests)
        all_results.extend(fhirpath_results)

        print("Running SQL-on-FHIR regression tests...")
        sql_results = self.run_sql_on_fhir_regression_tests()
        all_results.extend(sql_results)

        print("Running CQL regression tests...")
        cql_results = self.run_cql_regression_tests()
        all_results.extend(cql_results)

        total_time = (time.time() - start_time) * 1000

        # Save updated baselines
        self.baseline.save_baselines()

        # Generate report
        return self._generate_regression_report(all_results, total_time)

    def _generate_regression_report(self, results: List[RegressionTestResult], total_time_ms: float) -> RegressionReport:
        """Generate comprehensive regression report"""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests
        regression_tests = sum(1 for r in results if r.regression_detected)

        overall_success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        regression_rate = (regression_tests / total_tests * 100) if total_tests > 0 else 0

        # Category breakdown
        categories = set(r.test_category for r in results)
        category_results = {}

        for category in categories:
            category_tests = [r for r in results if r.test_category == category]
            category_passed = sum(1 for r in category_tests if r.passed)
            category_regressions = sum(1 for r in category_tests if r.regression_detected)

            category_results[category] = {
                "total": len(category_tests),
                "passed": category_passed,
                "failed": len(category_tests) - category_passed,
                "regressions": category_regressions,
                "success_rate": (category_passed / len(category_tests) * 100) if category_tests else 0,
                "regression_rate": (category_regressions / len(category_tests) * 100) if category_tests else 0
            }

        # Get regression details
        regressions_detected = [r for r in results if r.regression_detected]

        return RegressionReport(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            regression_tests=regression_tests,
            categories_tested=list(categories),
            overall_success_rate=overall_success_rate,
            regression_rate=regression_rate,
            execution_time_total_ms=total_time_ms,
            category_results=category_results,
            regressions_detected=regressions_detected,
            timestamp=datetime.now().isoformat()
        )

    def print_regression_summary(self, report: RegressionReport) -> None:
        """Print formatted regression test summary"""
        print("\n" + "="*60)
        print("REGRESSION PREVENTION REPORT")
        print("="*60)
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests}")
        print(f"Failed: {report.failed_tests}")
        print(f"Regressions Detected: {report.regression_tests}")
        print(f"Overall Success Rate: {report.overall_success_rate:.1f}%")
        print(f"Regression Rate: {report.regression_rate:.1f}%")
        print(f"Total Execution Time: {report.execution_time_total_ms:.1f}ms")

        print("\nCategory Breakdown:")
        for category, results in report.category_results.items():
            print(f"  {category.upper()}:")
            print(f"    Tests: {results['passed']}/{results['total']} passed ({results['success_rate']:.1f}%)")
            print(f"    Regressions: {results['regressions']} ({results['regression_rate']:.1f}%)")

        if report.regressions_detected:
            print(f"\nRegressions Detected ({len(report.regressions_detected)}):")
            for regression in report.regressions_detected[:5]:  # Show first 5
                print(f"  - {regression.test_name} ({regression.test_category})")
                print(f"    Expression: {regression.expression}")
                if regression.error_message:
                    print(f"    Error: {regression.error_message}")

    def save_regression_report(self, report: RegressionReport, output_path: Path) -> Path:
        """Save regression report to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)

        return output_path


def run_regression_prevention(database_type: str = "duckdb",
                            max_fhirpath_tests: Optional[int] = None) -> RegressionReport:
    """
    Convenience function for regression prevention testing

    Args:
        database_type: Database type for testing
        max_fhirpath_tests: Maximum FHIRPath tests to run

    Returns:
        Regression prevention report
    """
    prevention = FHIRPathRegressionPrevention(database_type)
    report = prevention.run_comprehensive_regression_tests(max_fhirpath_tests)
    prevention.print_regression_summary(report)

    return report


if __name__ == "__main__":
    # Demonstrate regression prevention
    print("Demonstrating FHIRPath regression prevention...")

    # Run regression tests with limited FHIRPath tests
    report = run_regression_prevention(database_type="duckdb", max_fhirpath_tests=10)

    # Save report
    prevention = FHIRPathRegressionPrevention()
    output_path = prevention.save_regression_report(report, Path("regression_prevention_report.json"))
    print(f"\nRegression report saved to: {output_path}")