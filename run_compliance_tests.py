#!/usr/bin/env python3
"""
Quick script to run FHIRPath compliance tests and generate report.
"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, '/mnt/d/fhir4ds3')

from tests.compliance.fhirpath.test_parser import parse_fhirpath_tests
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner

def main():
    print("Running FHIRPath Compliance Tests...")
    print("=" * 60)

    # Parse tests
    print("Parsing tests from XML...")
    start_time = time.time()
    official_tests = parse_fhirpath_tests()
    parse_time = time.time() - start_time

    print(f"Parsed {len(official_tests)} tests in {parse_time:.2f}s")

    # Run tests with DuckDB
    print("\n" + "=" * 60)
    print("Running tests with DuckDB...")
    print("=" * 60)

    runner = EnhancedOfficialTestRunner(database_type="duckdb")

    start_time = time.time()
    results = runner.run_official_tests()
    run_time = time.time() - start_time

    print(f"\nCompleted in {run_time:.2f}s")
    print(f"Total: {results.total_tests}")
    print(f"Passed: {results.passed_tests}")
    print(f"Failed: {results.failed_tests}")
    print(f"Compliance: {results.compliance_percentage:.1f}%")

    print("\nCategory Breakdown:")
    for cat, stats in sorted(results.test_categories.items()):
        if stats['total'] > 0:
            pass_rate = (stats['passed'] / stats['total']) * 100
            status = "PASS" if pass_rate == 100 else "FAIL" if pass_rate < 50 else "PARTIAL"
            print(f"  [{status}] {cat}: {pass_rate:.1f}% ({stats['passed']}/{stats['total']})")

    # Save results
    output = {
        "total_tests": results.total_tests,
        "passed_tests": results.passed_tests,
        "failed_tests": results.failed_tests,
        "compliance_percentage": results.compliance_percentage,
        "test_categories": results.test_categories,
        "timestamp": results.timestamp,
        "execution_time_total_ms": results.execution_time_total_ms,
        "execution_time_average_ms": results.execution_time_average_ms,
        "parser_type": results.parser_type,
        "database_type": results.database_type
    }

    with open('compliance_report_current.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nReport saved to: compliance_report_current.json")

    return results

if __name__ == "__main__":
    main()
