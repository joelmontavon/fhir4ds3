"""
PostgreSQL performance benchmarks (SP-012-002).

This module extends the existing CTE performance benchmarks (SP-011-015) to
support PostgreSQL execution, enabling direct performance comparison between
DuckDB and PostgreSQL for the 10 Path Navigation expressions.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, List

import psutil
import pytest

from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor

from .dataset_utils import generate_population_dataset, load_base_patients

PATH_NAV_EXPRESSIONS = [
    "Patient.birthDate",
    "Patient.gender",
    "Patient.active",
    "Patient.name",
    "Patient.telecom",
    "Patient.address",
    "Patient.identifier",
    "Patient.name.given",
    "Patient.name.family",
    "Patient.address.line",
]


@pytest.fixture(scope="session")
def _base_patients() -> List[Dict[str, object]]:
    """Provide the canonical 100-patient fixture."""
    return load_base_patients()


@pytest.fixture(scope="session")
def population_dataset_factory(
    _base_patients: List[Dict[str, object]],
) -> Callable[[int], List[Dict[str, object]]]:
    """Return a factory that materialises deterministic population datasets."""
    from copy import deepcopy
    cache: Dict[int, List[Dict[str, object]]] = {}

    def _factory(size: int) -> List[Dict[str, object]]:
        if size not in cache:
            cache[size] = generate_population_dataset(size, base_records=_base_patients)
        return deepcopy(cache[size])

    return _factory


def _materialise_resource_table_postgresql(
    dialect: PostgreSQLDialect,
    dataset: List[Dict[str, Any]],
    table_name: str = "resource"
) -> None:
    """Populate the resource table in PostgreSQL."""
    conn = None
    cursor = None
    try:
        conn = dialect.get_connection()
        cursor = conn.cursor()

        # Drop and create table
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute(f"CREATE TABLE {table_name} (id INTEGER, resource JSONB)")

        # Insert records
        for record in dataset:
            identifier = int(str(record.get("id", "0")))
            cursor.execute(
                f"INSERT INTO {table_name} VALUES (%s, %s)",
                (identifier, json.dumps(record)),
            )

        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn:
            dialect.release_connection(conn)


def _materialise_resource_table_duckdb(
    dialect: DuckDBDialect,
    dataset: List[Dict[str, Any]],
    table_name: str = "resource"
) -> None:
    """Populate the resource table in DuckDB."""
    connection = dialect.get_connection()
    connection.execute(f"DROP TABLE IF EXISTS {table_name}")
    connection.execute(f"CREATE TABLE {table_name} (id INTEGER, resource JSON)")

    for record in dataset:
        identifier = int(str(record.get("id", "0")))
        connection.execute(
            f"INSERT INTO {table_name} VALUES (?, ?)",
            [identifier, json.dumps(record)],
        )


def _cleanup_resource_table_postgresql(dialect: PostgreSQLDialect) -> None:
    """Drop the resource table in PostgreSQL."""
    conn = None
    cursor = None
    try:
        conn = dialect.get_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS resource")
        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn:
            dialect.release_connection(conn)


def _cleanup_resource_table_duckdb(dialect: DuckDBDialect) -> None:
    """Drop the resource table in DuckDB."""
    connection = dialect.get_connection()
    connection.execute("DROP TABLE IF EXISTS resource")


@pytest.fixture
def duckdb_executor(population_dataset_factory) -> FHIRPathExecutor:
    """Create DuckDB executor with 100-patient dataset."""
    dataset = population_dataset_factory(100)
    dialect = DuckDBDialect(database=":memory:")
    _materialise_resource_table_duckdb(dialect, dataset)
    executor = FHIRPathExecutor(dialect, "Patient")
    yield executor
    _cleanup_resource_table_duckdb(dialect)


@pytest.fixture
def postgresql_executor(population_dataset_factory) -> FHIRPathExecutor:
    """Create PostgreSQL executor with 100-patient dataset (reuses existing table)."""
    connection_string = "postgresql://postgres:postgres@localhost:5432/postgres"
    dialect = PostgreSQLDialect(connection_string, pool_size=5)
    executor = FHIRPathExecutor(dialect, "Patient")
    yield executor
    # Note: Don't drop the table - we reuse it across tests for efficiency
    dialect.close_all_connections()


@pytest.mark.parametrize("expression", PATH_NAV_EXPRESSIONS)
@pytest.mark.parametrize("dialect_name", ["duckdb", "postgresql"])
def test_comparative_execution_time(
    expression: str,
    dialect_name: str,
    duckdb_executor: FHIRPathExecutor,
    postgresql_executor: FHIRPathExecutor,
) -> None:
    """Measure and compare execution time for both databases."""
    executor = duckdb_executor if dialect_name == "duckdb" else postgresql_executor

    # Warm-up run to ensure caches are initialized
    executor.execute_with_details(expression)

    # Measure execution time over multiple runs
    timings: List[float] = []
    for _ in range(5):
        details = executor.execute_with_details(expression)
        timings.append(details["timings_ms"]["execute"])

    average_time_ms = sum(timings) / len(timings)
    print(f"\n[{dialect_name.upper()}] {expression}: {average_time_ms:.2f}ms (avg over 5 runs)")

    # Verify results are non-empty
    assert details["results"], f"Expected non-empty result set for {expression}"


@pytest.mark.parametrize("expression", PATH_NAV_EXPRESSIONS)
def test_postgresql_vs_duckdb_parity(
    expression: str,
    duckdb_executor: FHIRPathExecutor,
    postgresql_executor: FHIRPathExecutor,
) -> None:
    """Verify PostgreSQL and DuckDB return identical results."""
    # Execute on both databases
    duckdb_results = sorted(duckdb_executor.execute(expression))
    postgresql_results = sorted(postgresql_executor.execute(expression))

    # Results must be identical
    assert len(duckdb_results) == len(postgresql_results), (
        f"Result count mismatch for {expression}: "
        f"DuckDB={len(duckdb_results)}, PostgreSQL={len(postgresql_results)}"
    )

    # Compare results (allowing for minor floating-point differences)
    assert duckdb_results == postgresql_results, (
        f"Results differ for {expression}\n"
        f"DuckDB sample: {duckdb_results[:3]}\n"
        f"PostgreSQL sample: {postgresql_results[:3]}"
    )


@pytest.mark.parametrize("expression", ["Patient.birthDate", "Patient.name.given"])
@pytest.mark.parametrize("dialect_name", ["duckdb", "postgresql"])
def test_memory_usage_both_databases(
    expression: str,
    dialect_name: str,
    duckdb_executor: FHIRPathExecutor,
    postgresql_executor: FHIRPathExecutor,
    population_dataset_factory: Callable[[int], List[Dict[str, object]]],
) -> None:
    """Measure memory usage for both databases with 1000-patient dataset."""
    # Create fresh executor with larger dataset
    dataset = population_dataset_factory(1000)

    if dialect_name == "duckdb":
        dialect = DuckDBDialect(database=":memory:")
        _materialise_resource_table_duckdb(dialect, dataset)
        executor = FHIRPathExecutor(dialect, "Patient")
    else:
        connection_string = "postgresql://postgres:postgres@localhost:5432/postgres"
        dialect = PostgreSQLDialect(connection_string, pool_size=5)
        _materialise_resource_table_postgresql(dialect, dataset)
        executor = FHIRPathExecutor(dialect, "Patient")

    try:
        process = psutil.Process(os.getpid())
        rss_before = process.memory_info().rss
        executor.execute(expression)
        rss_after = process.memory_info().rss

        delta_mb = max(0, rss_after - rss_before) / (1024 * 1024)
        print(f"\n[{dialect_name.upper()}] {expression}: {delta_mb:.2f}MB memory increase")

        assert delta_mb < 100.0, f"Memory increase {delta_mb:.2f}MB exceeds 100MB target"
    finally:
        if dialect_name == "duckdb":
            _cleanup_resource_table_duckdb(dialect)
        else:
            _cleanup_resource_table_postgresql(dialect)
            dialect.close_all_connections()


def test_postgresql_connection_pool_overhead(postgresql_executor: FHIRPathExecutor) -> None:
    """Measure connection pool overhead for PostgreSQL."""
    expression = "Patient.birthDate"

    # Measure connection acquisition and query execution time
    total_timings: List[float] = []
    execute_timings: List[float] = []

    for _ in range(10):
        start = time.perf_counter()
        details = postgresql_executor.execute_with_details(expression)
        total_time_ms = (time.perf_counter() - start) * 1000.0

        total_timings.append(total_time_ms)
        execute_timings.append(details["timings_ms"]["execute"])

    avg_total = sum(total_timings) / len(total_timings)
    avg_execute = sum(execute_timings) / len(execute_timings)
    connection_overhead = avg_total - avg_execute

    print(f"\nPostgreSQL connection overhead: {connection_overhead:.2f}ms")
    print(f"  - Average total time: {avg_total:.2f}ms")
    print(f"  - Average execute time: {avg_execute:.2f}ms")

    # Connection overhead should be minimal (<10ms target)
    assert connection_overhead < 10.0, (
        f"Connection overhead {connection_overhead:.2f}ms exceeds 10ms target"
    )
