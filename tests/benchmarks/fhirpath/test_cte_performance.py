"""
Performance benchmarks for the CTE infrastructure (SP-011-015).

These tests provide a regression harness that validates the population-scale
execution characteristics promised by PEP-004. They intentionally focus on
measuring stage-specific timings, memory usage, and comparative performance
against a naive row-by-row baseline.
"""

from __future__ import annotations

import os
from copy import deepcopy
import time
from typing import Callable, Dict, List

import psutil
import pytest

from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor

from .dataset_utils import (
    generate_population_dataset,
    load_base_patients,
    materialise_resource_table,
)
from .row_by_row_processor import RowByRowProcessor

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
    cache: Dict[int, List[Dict[str, object]]] = {}

    def _factory(size: int) -> List[Dict[str, object]]:
        if size not in cache:
            cache[size] = generate_population_dataset(size, base_records=_base_patients)
        # Return a copy so tests can mutate if needed without polluting cache.
        return deepcopy(cache[size])

    return _factory


def _prepare_executor(dataset: List[Dict[str, object]]) -> tuple[DuckDBDialect, FHIRPathExecutor]:
    dialect = DuckDBDialect(database=":memory:")
    materialise_resource_table(dialect, dataset)
    executor = FHIRPathExecutor(dialect, "Patient")
    return dialect, executor


@pytest.mark.parametrize("expression", PATH_NAV_EXPRESSIONS)
def test_cte_generation_under_10ms(
    expression: str,
    population_dataset_factory: Callable[[int], List[Dict[str, object]]],
) -> None:
    """CTE building must remain below the 10ms target for all navigation expressions."""
    dataset = population_dataset_factory(100)
    dialect, executor = _prepare_executor(dataset)

    # Warm-up to ensure caches are initialised.
    executor.execute_with_details(expression)

    timings: List[float] = []
    for _ in range(3):
        details = executor.execute_with_details(expression)
        timings.append(details["timings_ms"]["build"])

    average_build_ms = sum(timings) / len(timings)
    assert average_build_ms < 10.0, f"CTE build exceeded 10ms for {expression}"

    # Cleanup resource table to keep the in-memory database tidy.
    dialect.get_connection().execute("DROP TABLE IF EXISTS resource")


@pytest.mark.parametrize("expression", PATH_NAV_EXPRESSIONS)
def test_sql_execution_population_scale(
    expression: str,
    population_dataset_factory: Callable[[int], List[Dict[str, object]]],
) -> None:
    """Verify SQL execution stays within population-scale performance targets."""
    dataset = population_dataset_factory(1000)
    dialect, executor = _prepare_executor(dataset)

    details = executor.execute_with_details(expression)
    execution_ms = details["timings_ms"]["execute"]

    assert execution_ms < 150.0, f"Execution time {execution_ms:.2f}ms exceeds 150ms budget"
    assert details["results"], "Expected non-empty result set for population dataset"

    dialect.get_connection().execute("DROP TABLE IF EXISTS resource")


@pytest.mark.parametrize("expression", PATH_NAV_EXPRESSIONS)
def test_memory_usage_within_limits(
    expression: str,
    population_dataset_factory: Callable[[int], List[Dict[str, object]]],
) -> None:
    """Ensure peak RSS growth stays under the 100MB ceiling for complex expressions."""
    dataset = population_dataset_factory(1000)
    dialect, executor = _prepare_executor(dataset)

    process = psutil.Process(os.getpid())
    rss_before = process.memory_info().rss
    executor.execute(expression)
    rss_after = process.memory_info().rss

    delta_mb = max(0, rss_after - rss_before) / (1024 * 1024)
    assert delta_mb < 100.0, f"Memory increase {delta_mb:.2f}MB exceeds 100MB target"

    dialect.get_connection().execute("DROP TABLE IF EXISTS resource")


@pytest.mark.parametrize("expression", PATH_NAV_EXPRESSIONS)
def test_cte_outperforms_row_by_row(
    expression: str,
    population_dataset_factory: Callable[[int], List[Dict[str, object]]],
) -> None:
    """CTE execution must deliver 10x+ improvement over naive row-by-row processing."""
    dataset = population_dataset_factory(100)
    dialect, executor = _prepare_executor(dataset)

    details = executor.execute_with_details(expression)
    cte_results = sorted(details["results"])
    cte_time_ms = max(details["timings_ms"]["execute"], 0.001)

    row_processor = RowByRowProcessor(dialect, "Patient")
    patient_ids = [int(record["id"]) for record in dataset]

    start = time.perf_counter()
    row_results = row_processor.execute(expression, patient_ids)
    row_time_ms = (time.perf_counter() - start) * 1000.0

    assert sorted(row_results) == cte_results, "Row-by-row baseline disagrees with CTE output"

    improvement = row_time_ms / cte_time_ms
    assert improvement >= 10.0, f"Expected >=10x improvement, observed {improvement:.2f}x for {expression}"

    dialect.get_connection().execute("DROP TABLE IF EXISTS resource")


@pytest.mark.parametrize("expression", ["Patient.birthDate", "Patient.name.given"])
def test_execution_scalability_linear(
    expression: str,
    population_dataset_factory: Callable[[int], List[Dict[str, object]]],
) -> None:
    """Execution time must scale linearly (or better) as population size grows."""
    dataset_sizes = [100, 1000, 10000]
    timings: List[float] = []

    for size in dataset_sizes:
        dataset = population_dataset_factory(size)
        dialect, executor = _prepare_executor(dataset)
        details = executor.execute_with_details(expression)
        timings.append(details["timings_ms"]["execute"])
        dialect.get_connection().execute("DROP TABLE IF EXISTS resource")

    baseline_size = dataset_sizes[0]
    baseline_time = timings[0]

    for observed_size, observed_time in zip(dataset_sizes[1:], timings[1:]):
        expected_linear = baseline_time * (observed_size / baseline_size)
        assert (
            observed_time <= expected_linear * 1.2
        ), f"{expression} scaling exceeded linear bound: {observed_time:.2f}ms vs {expected_linear:.2f}ms"
