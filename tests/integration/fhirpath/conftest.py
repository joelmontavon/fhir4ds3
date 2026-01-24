import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor


@pytest.fixture(scope="session")
def patient_records() -> List[Dict[str, Any]]:
    """Load synthetic Patient resources used for end-to-end execution tests."""
    data_path = Path("tests/fixtures/fhir/patients.json")
    return json.loads(data_path.read_text())


@pytest.fixture
def duckdb_resource_table(duckdb_dialect, patient_records) -> str:
    """Populate DuckDB with Patient resources in the expected `resource` table."""
    connection = duckdb_dialect.get_connection()
    connection.execute("DROP TABLE IF EXISTS resource")
    connection.execute("CREATE TABLE resource (id INTEGER, resource JSON)")
    for record in patient_records:
        connection.execute(
            "INSERT INTO resource VALUES (?, ?)",
            [int(record["id"]), json.dumps(record)],
        )
    yield "resource"
    connection.execute("DROP TABLE IF EXISTS resource")


@pytest.fixture
def duckdb_executor(duckdb_resource_table, duckdb_dialect) -> FHIRPathExecutor:
    """Provide a FHIRPathExecutor backed by DuckDB."""
    return FHIRPathExecutor(duckdb_dialect, "Patient")


@pytest.fixture
def postgresql_executor(
    postgresql_dialect,
    duckdb_executor: FHIRPathExecutor,
) -> Tuple[FHIRPathExecutor, List[Tuple[str, str]]]:
    """Provide PostgreSQL executor with stubbed execution using DuckDB results."""
    executed_sql: List[Tuple[str, str]] = []
    expected_results: Dict[str, List[Any]] = {}

    original_execute_query = postgresql_dialect.execute_query

    def patched_execute_query(sql: str) -> List[Any]:
        expression = getattr(postgresql_dialect, "_current_expression", None)
        executed_sql.append((expression, sql))
        if expression is None or expression not in expected_results:
            raise RuntimeError(
                "PostgreSQL execution invoked without prepared expected results"
            )
        return expected_results[expression]

    postgresql_dialect.execute_query = patched_execute_query  # type: ignore[assignment]

    executor = FHIRPathExecutor(postgresql_dialect, "Patient")

    class ExecutorWrapper:
        def execute(self, expression: str) -> List[Any]:
            expected_results[expression] = duckdb_executor.execute(expression)
            postgresql_dialect._current_expression = expression  # type: ignore[attr-defined]
            try:
                return executor.execute(expression)
            finally:
                postgresql_dialect._current_expression = None  # type: ignore[attr-defined]

        def execute_with_details(self, expression: str) -> Dict[str, Any]:
            expected_results[expression] = duckdb_executor.execute(expression)
            postgresql_dialect._current_expression = expression  # type: ignore[attr-defined]
            try:
                return executor.execute_with_details(expression)
            finally:
                postgresql_dialect._current_expression = None  # type: ignore[attr-defined]

    wrapper = ExecutorWrapper()

    yield wrapper, executed_sql

    postgresql_dialect.execute_query = original_execute_query  # type: ignore[assignment]
