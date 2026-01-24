"""
Utilities for preparing population-scale FHIR datasets used in benchmarks.

The helpers in this module provide deterministic dataset generation so
that performance benchmarks remain reproducible across environments. We
start from the curated 100-patient fixture and expand it to larger
populations while preserving realistic data shapes required by the path
navigation expressions under test.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from fhir4ds.dialects.base import DatabaseDialect

BASE_FIXTURE_PATH = Path("tests/fixtures/fhir/patients.json")
_BASE_CACHE: List[Dict[str, Any]] | None = None


def load_base_patients() -> List[Dict[str, Any]]:
    """Load the canonical 100-patient fixture with basic caching."""
    global _BASE_CACHE
    if _BASE_CACHE is None:
        payload = json.loads(BASE_FIXTURE_PATH.read_text())
        if not isinstance(payload, list):
            raise ValueError("Expected patient fixture to contain a JSON array")
        _BASE_CACHE = payload
    return deepcopy(_BASE_CACHE)


def generate_population_dataset(
    target_size: int,
    *,
    base_records: Sequence[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Expand the base patient fixture to the requested population size."""
    if target_size <= 0:
        raise ValueError("target_size must be positive")

    source_records = base_records or load_base_patients()
    if not source_records:
        raise ValueError("base patient fixture must not be empty")

    population: List[Dict[str, object]] = []
    fixture_len = len(source_records)

    for index in range(target_size):
        template = deepcopy(source_records[index % fixture_len])
        _reseed_patient(template, index + 1)
        population.append(template)

    return population


def materialise_resource_table(
    dialect: DatabaseDialect,
    dataset: Iterable[Dict[str, Any]],
    *,
    table_name: str = "resource",
) -> None:
    """Populate the canonical resource table with the supplied dataset."""
    connection = dialect.get_connection()
    connection.execute(f"DROP TABLE IF EXISTS {table_name}")
    connection.execute(f"CREATE TABLE {table_name} (id INTEGER, resource JSON)")

    for record in dataset:
        identifier = int(str(record.get("id", "0")))
        connection.execute(
            f"INSERT INTO {table_name} VALUES (?, ?)",
            [identifier, json.dumps(record)],
        )


def _reseed_patient(record: Dict[str, Any], index: int) -> None:
    """Ensure derived patient data remains unique for benchmarking."""
    record["id"] = str(index)

    names = record.get("name")
    if isinstance(names, list):
        for entry in names:
            if not isinstance(entry, dict):
                continue
            family = entry.get("family")
            if isinstance(family, str):
                entry["family"] = f"{family}_{index}"
            given = entry.get("given")
            if isinstance(given, list):
                entry["given"] = [f"{value}_{index}" for value in given if isinstance(value, str)]

    telecom = record.get("telecom")
    if isinstance(telecom, list):
        for position, contact in enumerate(telecom):
            if isinstance(contact, dict):
                value = contact.get("value")
                if isinstance(value, str):
                    contact["value"] = f"{value}_{index}_{position}"

    identifier = record.get("identifier")
    if isinstance(identifier, list):
        for position, ident in enumerate(identifier):
            if isinstance(ident, dict):
                value = ident.get("value")
                if isinstance(value, str):
                    ident["value"] = f"{value}_{index}_{position}"

    address = record.get("address")
    if isinstance(address, list):
        for entry in address:
            if not isinstance(entry, dict):
                continue
            city = entry.get("city")
            if isinstance(city, str):
                entry["city"] = f"{city}_{index}"
            lines = entry.get("line")
            if isinstance(lines, list):
                entry["line"] = [f"{line}_{index}" for line in lines if isinstance(line, str)]
