import pytest

from tests.compliance.fhirpath.test_runner import (
    PathNavigationComplianceRunner,
    run_path_navigation_suite,
)


@pytest.mark.unit
def test_duckdb_compliance_suite_passes():
    runner = PathNavigationComplianceRunner()
    summaries = runner.run(databases=("duckdb",))
    duckdb_summary = summaries["duckdb"]

    assert duckdb_summary.total_tests == 10
    assert duckdb_summary.passed_tests == 10
    assert duckdb_summary.failed_tests == 0
    assert duckdb_summary.compliance_percentage == pytest.approx(100.0)


@pytest.mark.unit
def test_postgresql_compliance_uses_reference_rows():
    summaries = run_path_navigation_suite()
    duckdb_summary = summaries["duckdb"]
    postgres_summary = summaries["postgresql"]

    assert postgres_summary.total_tests == duckdb_summary.total_tests == 10
    assert postgres_summary.passed_tests == duckdb_summary.passed_tests == 10
    assert postgres_summary.failed_tests == 0
    assert postgres_summary.compliance_percentage == pytest.approx(100.0)

    duckdb_row_counts = [result.actual_row_count for result in duckdb_summary.results]
    postgres_row_counts = [result.actual_row_count for result in postgres_summary.results]
    assert duckdb_row_counts == postgres_row_counts
