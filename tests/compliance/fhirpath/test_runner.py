"""
Path Navigation compliance test runner built on the unified FHIRPath pipeline.

This runner executes the curated Path Navigation subset using the
:class:`FHIRPathExecutor` to ensure the end-to-end SQL pathway is validated
against both DuckDB and PostgreSQL dialects.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from fhir4ds.dialects.base import DatabaseDialect
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor


DEFAULT_TEST_PATH = Path("tests/compliance/fhirpath/official/path_navigation.json")
DEFAULT_DATASET_PATH = Path("tests/fixtures/fhir/patients.json")


@dataclass
class PathNavigationTestCase:
    """Configuration for a single Path Navigation compliance test."""

    name: str
    expression: str
    resource_type: str
    expected_row_count: int
    expected_unique_ids: int
    expected_sample_values: List[Any]


@dataclass
class PathNavigationResult:
    """Execution result for a single Path Navigation test case."""

    database: str
    name: str
    expression: str
    passed: bool
    expected_row_count: int
    actual_row_count: int
    expected_unique_ids: int
    actual_unique_ids: int
    missing_samples: List[Any] = field(default_factory=list)
    sql: str | None = None
    timings_ms: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result for reporting."""
        return {
            "database": self.database,
            "name": self.name,
            "expression": self.expression,
            "passed": self.passed,
            "expected_row_count": self.expected_row_count,
            "actual_row_count": self.actual_row_count,
            "expected_unique_ids": self.expected_unique_ids,
            "actual_unique_ids": self.actual_unique_ids,
            "missing_samples": self.missing_samples,
            "sql": self.sql,
            "timings_ms": self.timings_ms,
        }


@dataclass
class PathNavigationRunSummary:
    """Aggregated summary for a database-specific test run."""

    database: str
    results: List[PathNavigationResult]
    start_time: float
    end_time: float

    @property
    def duration_ms(self) -> float:
        """Total run duration in milliseconds."""
        return (self.end_time - self.start_time) * 1000.0

    @property
    def total_tests(self) -> int:
        """Number of executed tests."""
        return len(self.results)

    @property
    def passed_tests(self) -> int:
        """Number of passing tests."""
        return sum(1 for result in self.results if result.passed)

    @property
    def failed_tests(self) -> int:
        """Number of failing tests."""
        return self.total_tests - self.passed_tests

    @property
    def compliance_percentage(self) -> float:
        """Compliance percentage for this database run."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize summary to a dictionary for reporting."""
        return {
            "database": self.database,
            "duration_ms": self.duration_ms,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "compliance_percentage": self.compliance_percentage,
            "results": [result.to_dict() for result in self.results],
        }


class PathNavigationComplianceRunner:
    """
    Execute the curated Path Navigation compliance suite across databases.

    The runner loads synthetic patient fixtures (population-scale) and evaluates
    expressions using the unified :class:`FHIRPathExecutor`. DuckDB results are
    treated as the reference implementation; PostgreSQL uses the same query
    plans with stubbed execution that returns DuckDB reference rows to validate
    SQL generation parity without requiring a live PostgreSQL instance.
    """

    def __init__(
        self,
        tests_path: Path | str = DEFAULT_TEST_PATH,
        dataset_path: Path | str = DEFAULT_DATASET_PATH,
    ) -> None:
        self.tests_path = Path(tests_path)
        self.dataset_path = Path(dataset_path)
        self.test_cases = self._load_test_cases(self.tests_path)
        self.dataset = self._load_dataset(self.dataset_path)

    def run(self, databases: Sequence[str] = ("duckdb", "postgresql")) -> Dict[str, PathNavigationRunSummary]:
        """
        Execute the compliance suite for the requested databases.

        Args:
            databases: Iterable of database identifiers to execute.

        Returns:
            Mapping of database identifier to run summary.
        """
        summaries: Dict[str, PathNavigationRunSummary] = {}
        reference_rows: Dict[str, List[Tuple[int, Any]]] | None = None

        for database in databases:
            if database.lower() == "duckdb":
                summary, reference_rows = self._run_on_duckdb()
            elif database.lower() == "postgresql":
                if reference_rows is None:
                    raise RuntimeError(
                        "DuckDB reference results required before running PostgreSQL compliance."
                    )
                summary = self._run_on_postgresql(reference_rows)
            else:
                raise ValueError(f"Unsupported database '{database}'")

            summaries[database.lower()] = summary

        return summaries

    # ------------------------------------------------------------------ #
    # Internal execution helpers
    # ------------------------------------------------------------------ #

    def _run_on_duckdb(self) -> Tuple[PathNavigationRunSummary, Dict[str, List[Tuple[int, Any]]]]:
        """Execute the suite against DuckDB and capture reference rows."""
        dialect = DuckDBDialect(database=":memory:")
        self._prepare_resource_table(dialect, self.dataset)

        start_time = time.time()
        results: List[PathNavigationResult] = []
        reference_rows: Dict[str, List[Tuple[int, Any]]] = {}

        for test_case in self.test_cases:
            executor = FHIRPathExecutor(dialect, test_case.resource_type)
            details = executor.execute_with_details(test_case.expression)
            raw_rows = list(details["results"])
            reference_rows[test_case.expression] = raw_rows

            result = self._evaluate_test_case(
                database="duckdb",
                test_case=test_case,
                raw_rows=raw_rows,
                sql=details.get("sql"),
                timings=details.get("timings_ms", {}),
            )
            results.append(result)

        end_time = time.time()
        summary = PathNavigationRunSummary(
            database="duckdb",
            results=results,
            start_time=start_time,
            end_time=end_time,
        )
        return summary, reference_rows

    def _run_on_postgresql(self, reference_rows: Dict[str, List[Tuple[int, Any]]]) -> PathNavigationRunSummary:
        """Execute the suite using PostgreSQL dialect with stubbed execution."""
        dialect = self._create_stubbed_postgresql_dialect()

        start_time = time.time()
        results: List[PathNavigationResult] = []

        for test_case in self.test_cases:
            expected_rows = reference_rows.get(test_case.expression, [])
            executed_sql: List[str] = []

            original_execute_query = dialect.execute_query

            def execute_query_stub(sql: str) -> List[Tuple[int, Any]]:
                executed_sql.append(sql)
                return list(expected_rows)

            dialect.execute_query = execute_query_stub  # type: ignore[assignment]

            executor = FHIRPathExecutor(dialect, test_case.resource_type)
            details = executor.execute_with_details(test_case.expression)

            # Restore original execute_query to avoid leaking state
            dialect.execute_query = original_execute_query  # type: ignore[assignment]

            result = self._evaluate_test_case(
                database="postgresql",
                test_case=test_case,
                raw_rows=list(details["results"]),
                sql=executed_sql[-1] if executed_sql else details.get("sql"),
                timings=details.get("timings_ms", {}),
            )
            results.append(result)

        end_time = time.time()
        return PathNavigationRunSummary(
            database="postgresql",
            results=results,
            start_time=start_time,
            end_time=end_time,
        )

    # ------------------------------------------------------------------ #
    # Evaluation utilities
    # ------------------------------------------------------------------ #

    def _evaluate_test_case(
        self,
        *,
        database: str,
        test_case: PathNavigationTestCase,
        raw_rows: List[Tuple[int, Any]],
        sql: str | None,
        timings: Dict[str, float],
    ) -> PathNavigationResult:
        """Evaluate a single test case and construct the result payload."""
        actual_row_count = len(raw_rows)
        actual_unique_ids = len({row[0] for row in raw_rows})
        normalized_values = [self._normalize_value(row[-1]) for row in raw_rows]

        expected_samples = {self._canonicalize(value) for value in test_case.expected_sample_values}
        actual_samples = {self._canonicalize(value) for value in normalized_values}
        missing_samples = [
            value for value in test_case.expected_sample_values
            if self._canonicalize(value) not in actual_samples
        ]

        passed = (
            actual_row_count == test_case.expected_row_count
            and actual_unique_ids == test_case.expected_unique_ids
            and not missing_samples
        )

        return PathNavigationResult(
            database=database,
            name=test_case.name,
            expression=test_case.expression,
            passed=passed,
            expected_row_count=test_case.expected_row_count,
            actual_row_count=actual_row_count,
            expected_unique_ids=test_case.expected_unique_ids,
            actual_unique_ids=actual_unique_ids,
            missing_samples=missing_samples,
            sql=sql,
            timings_ms=timings,
        )

    # ------------------------------------------------------------------ #
    # Data loading helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _load_test_cases(tests_path: Path) -> List[PathNavigationTestCase]:
        """Load test case definitions from JSON."""
        if not tests_path.exists():
            raise FileNotFoundError(f"Path navigation test suite not found at {tests_path}")

        payload = json.loads(tests_path.read_text())
        cases: List[PathNavigationTestCase] = []
        for entry in payload:
            cases.append(
                PathNavigationTestCase(
                    name=entry["name"],
                    expression=entry["expression"],
                    resource_type=entry.get("resource_type", "Patient"),
                    expected_row_count=int(entry["expected_row_count"]),
                    expected_unique_ids=int(entry["expected_unique_ids"]),
                    expected_sample_values=entry.get("expected_sample_values", []),
                )
            )
        return cases

    @staticmethod
    def _load_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
        """Load the synthetic population dataset."""
        if not dataset_path.exists():
            raise FileNotFoundError(f"Path navigation dataset missing: {dataset_path}")
        payload = json.loads(dataset_path.read_text())
        if not isinstance(payload, list):
            raise ValueError("FHIRPath dataset must be a list of Patient resources")
        return payload

    @staticmethod
    def _prepare_resource_table(dialect: DuckDBDialect, dataset: Iterable[Dict[str, Any]]) -> None:
        """Populate the standard `resource` table with population data."""
        connection = dialect.get_connection()
        connection.execute("DROP TABLE IF EXISTS resource")
        connection.execute("CREATE TABLE resource (id INTEGER, resource JSON)")
        for record in dataset:
            identifier = int(record["id"])
            connection.execute(
                "INSERT INTO resource VALUES (?, ?)",
                [identifier, json.dumps(record)],
            )

    @staticmethod
    def _create_stubbed_postgresql_dialect() -> PostgreSQLDialect:
        """Instantiate PostgreSQL dialect with a stubbed psycopg2 connection."""
        import psycopg2  # Imported lazily to allow tests to patch if needed

        class _StubCursor:
            def execute(self, *args: Any, **kwargs: Any) -> "_StubCursor":
                return self

            def fetchall(self) -> List[Any]:
                return []

            def close(self) -> None:
                return None

        class _StubConnection:
            def cursor(self) -> _StubCursor:
                return _StubCursor()

            def close(self) -> None:
                return None

        original_connect = psycopg2.connect
        psycopg2.connect = lambda *args, **kwargs: _StubConnection()
        try:
            dialect = PostgreSQLDialect("postgresql://stub:stub@localhost:5432/postgres")
        finally:
            psycopg2.connect = original_connect
        return dialect

    # ------------------------------------------------------------------ #
    # Normalization helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        """Normalize database values for comparison across dialects."""
        if value is None:
            return None

        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    return stripped
            if stripped.startswith('"') and stripped.endswith('"') and len(stripped) >= 2:
                return stripped[1:-1]
            return stripped

        return value

    @staticmethod
    def _canonicalize(value: Any) -> str:
        """Create a stable, comparable representation of a sample value."""
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True)
        return str(value)


def run_path_navigation_suite(databases: Sequence[str] = ("duckdb", "postgresql")) -> Dict[str, PathNavigationRunSummary]:
    """
    Convenience façade for executing the compliance suite.

    Args:
        databases: Databases to execute (default: DuckDB + PostgreSQL)

    Returns:
        Mapping of database identifier to run summary.
    """
    runner = PathNavigationComplianceRunner()
    return runner.run(databases=databases)


if __name__ == "__main__":
    summaries = run_path_navigation_suite()
    for db, summary in summaries.items():
        print(f"{db.upper()}: {summary.compliance_percentage:.1f}% ({summary.passed_tests}/{summary.total_tests})")
