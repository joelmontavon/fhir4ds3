"""Focused unit tests for count() aggregation translation.

These tests validate the enhanced count() behaviour implemented for task
SP-007-009. They exercise the SQL generation logic across both DuckDB and
PostgreSQL dialect expectations, covering scalar values, collections, context
changes, and edge-case handling to ensure specification compliance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest
from unittest.mock import Mock, MagicMock, patch

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.ast.nodes import AggregationNode
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.dialects.base import DatabaseDialect


def _make_count_node() -> AggregationNode:
    """Create a reusable count() aggregation node."""
    node = AggregationNode(
        node_type="aggregation",
        text="count()",
        aggregation_function="count",
        aggregation_type="count"
    )
    node.children = []
    return node


@dataclass
class _DialectFactory:
    """Small helper to produce stub dialects with SQL-like functions."""

    name: str
    extractor: Callable[[str, str], str]
    type_of: Callable[[str], str]
    array_length: Callable[[str, str], str]

    def create(self):
        """Return a lightweight dialect object exposing the required methods."""

        class _StubDialect:
            def __init__(self, factory: _DialectFactory):
                self._factory = factory

            def extract_json_object(self, column: str, path: str) -> str:
                return self._factory.extractor(column, path)

            def get_json_type(self, expression: str) -> str:
                return self._factory.type_of(expression)

            def get_json_array_length(self, column: str, path: str = None) -> str:
                return self._factory.array_length(column, path)

        return _StubDialect(self)


def _duckdb_factory() -> _DialectFactory:
    """Create stubbed DuckDB dialect behaviour."""

    def extractor(column: str, path: str) -> str:
        return f"json_extract({column}, '{path}')"

    def type_of(expression: str) -> str:
        return f"json_type({expression})"

    def array_length(column: str, path: str = None) -> str:
        if path:
            return f"json_array_length(json_extract({column}, '{path}'))"
        return f"json_array_length({column})"

    return _DialectFactory("duckdb", extractor, type_of, array_length)


def _postgresql_factory() -> _DialectFactory:
    """Create stubbed PostgreSQL dialect behaviour."""

    def extractor(column: str, path: str) -> str:
        path_components = [part for part in path.strip("$").strip(".").split(".") if part]
        if not path_components:
            return column
        args = ", ".join(f"'{component}'" for component in path_components)
        return f"jsonb_extract_path({column}, {args})"

    def type_of(expression: str) -> str:
        return f"jsonb_typeof({expression})"

    def array_length(column: str, path: str = None) -> str:
        if path:
            extracted = extractor(column, path)
            return f"jsonb_array_length({extracted})"
        return f"jsonb_array_length({column})"

    return _DialectFactory("postgresql", extractor, type_of, array_length)


@pytest.fixture(params=[_duckdb_factory(), _postgresql_factory()], ids=lambda f: f.name)
def stub_dialect(request):
    """Provide stub dialect resembling DuckDB and PostgreSQL behaviour."""
    return request.param.create()


@pytest.fixture
def duckdb_dialect_real():
    """Return real DuckDB dialect instance for integration-style assertions."""
    from fhir4ds.dialects.duckdb import DuckDBDialect

    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect_real():
    """Return real PostgreSQL dialect instance, skipping if unavailable."""
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    import psycopg2  # noqa: F401

    dummy_conn = MagicMock()
    dummy_cursor = MagicMock()
    dummy_conn.cursor.return_value = dummy_cursor
    dummy_cursor.execute.return_value = None
    dummy_cursor.fetchall.return_value = []

    with patch("fhir4ds.dialects.postgresql.psycopg2.connect", return_value=dummy_conn):
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")


def test_count_returns_sqlfragment_with_flags(stub_dialect):
    """Ensure translation returns a SQLFragment with aggregate metadata."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")
    translator.context.push_path("name")

    fragment = translator.visit_aggregation(_make_count_node())

    assert isinstance(fragment, SQLFragment)
    assert fragment.is_aggregate is True
    assert fragment.requires_unnest is False


@pytest.mark.parametrize(
    "path_components",
    [
        ["name"],
        ["name", "given"],
        ["contact", "telecom", "value"]
    ]
)
def test_count_expression_contains_path(stub_dialect, path_components):
    """Count SQL should reference the full JSON path from context."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")
    for component in path_components:
        translator.context.push_path(component)

    fragment = translator.visit_aggregation(_make_count_node())
    expected_path = "$." + ".".join(path_components)
    expression = fragment.expression

    if "json_extract(" in expression:
        assert expected_path in expression
    else:
        for component in path_components:
            assert f"'{component}'" in expression


def test_count_expression_uses_current_table_alias(stub_dialect):
    """Verify count SQL respects context.current_table updates."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")
    translator.context.current_table = "cte_7"
    translator.context.push_path("name")

    fragment = translator.visit_aggregation(_make_count_node())

    assert "cte_7" in fragment.expression


def test_count_expression_includes_case_and_coalesce(stub_dialect):
    """Generated SQL must guard array detection with CASE/COALESCE."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")
    translator.context.push_path("birthDate")

    fragment = translator.visit_aggregation(_make_count_node())
    expression = fragment.expression

    assert expression.startswith("COALESCE(")
    assert "CASE" in expression
    assert "ELSE 1" in expression
    assert "IS NULL THEN 0" in expression
    assert "LOWER(" in expression


def test_count_expression_handles_scalar_then_array(stub_dialect):
    """Multiple invocations with different paths should generate distinct SQL."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")

    translator.context.push_path("birthDate")
    scalar_fragment = translator.visit_aggregation(_make_count_node())
    scalar_expr = scalar_fragment.expression
    translator.context.parent_path.clear()
    translator.context.push_path("name")
    array_fragment = translator.visit_aggregation(_make_count_node())
    array_expr = array_fragment.expression

    assert scalar_expr != array_expr
    assert "ELSE 1" in scalar_expr
    assert "LOWER(" in array_expr


def test_count_expression_resets_to_count_star_without_path(stub_dialect):
    """When no JSON path exists, count() should fall back to COUNT(*)."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")
    translator.context.parent_path.clear()

    fragment = translator.visit_aggregation(_make_count_node())

    assert fragment.expression == "COUNT(*)"


def test_count_preserves_context_path(stub_dialect):
    """visit_aggregation must not mutate the path stack."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")
    translator.context.push_path("name")
    original_path = list(translator.context.parent_path)

    translator.visit_aggregation(_make_count_node())

    assert translator.context.parent_path == original_path


def test_count_calls_dialect_methods_once():
    """Ensure translator interacts with dialect helpers exactly once."""
    dialect = Mock(spec=DatabaseDialect)
    dialect.extract_json_object.return_value = "json_extract(resource, '$.name')"
    dialect.get_json_type.return_value = (
        "json_type(json_extract(resource, '$.name'))"
    )
    dialect.get_json_array_length.return_value = (
        "json_array_length(json_extract(resource, '$.name'))"
    )

    translator = ASTToSQLTranslator(dialect, "Patient")
    translator.context.push_path("name")
    translator.visit_aggregation(_make_count_node())

    dialect.extract_json_object.assert_called_once_with(column="resource", path="$.name")
    dialect.get_json_type.assert_called_once()
    dialect.get_json_array_length.assert_called_once_with(column="resource", path="$.name")


def test_count_expression_handles_cte_named_table(stub_dialect):
    """Count should embed arbitrary table identifiers from context."""
    translator = ASTToSQLTranslator(stub_dialect, "Encounter")
    translator.context.current_table = "filtered_results"
    translator.context.push_path("identifier")

    fragment = translator.visit_aggregation(_make_count_node())

    assert "filtered_results" in fragment.expression
    assert "identifier" in fragment.expression


def test_count_expression_contains_array_length_function(stub_dialect):
    """Array length helper should still appear inside overall CASE expression."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")
    translator.context.push_path("name")

    fragment = translator.visit_aggregation(_make_count_node())

    assert "array_length" in fragment.expression


def test_count_expression_reuses_existing_context_after_call(stub_dialect):
    """Subsequent aggregations should continue to use updated context table."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")
    translator.context.current_table = "cte_20"
    translator.context.push_path("telecom")

    fragment_first = translator.visit_aggregation(_make_count_node())
    fragment_second = translator.visit_aggregation(_make_count_node())

    assert fragment_first.expression == fragment_second.expression
    assert fragment_first.source_table == "cte_20"
    assert fragment_second.source_table == "cte_20"


def test_count_expression_handles_deeply_nested_paths(stub_dialect):
    """Ensure deeply nested paths are preserved in SQL output."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")
    for component in ["link", "other", "reference"]:
        translator.context.push_path(component)

    fragment = translator.visit_aggregation(_make_count_node())
    expression = fragment.expression

    if "json_extract(" in expression:
        assert "$.link.other.reference" in expression
    else:
        for component in ["link", "other", "reference"]:
            assert f"'{component}'" in expression


def test_count_expression_supports_changing_resource_type(stub_dialect):
    """Resource type differences should not impact count generation."""
    translator = ASTToSQLTranslator(stub_dialect, "Observation")
    translator.context.push_path("component")

    fragment = translator.visit_aggregation(_make_count_node())

    assert "component" in fragment.expression
    assert translator.context.current_resource_type == "Observation"


def test_count_expression_handles_multiple_context_tables(stub_dialect):
    """Switching tables between calls should reflect in generated SQL."""
    translator = ASTToSQLTranslator(stub_dialect, "Patient")

    translator.context.current_table = "cte_before"
    translator.context.push_path("name")
    before_fragment = translator.visit_aggregation(_make_count_node())
    before_expr = before_fragment.expression

    translator.context.current_table = "cte_after"
    after_fragment = translator.visit_aggregation(_make_count_node())
    after_expr = after_fragment.expression

    assert before_expr != after_expr
    assert "cte_before" in before_expr
    assert "cte_after" in after_expr


class TestCountAggregationRealDialects:
    """Additional coverage using real dialect implementations."""

    def test_count_array_field_duckdb_real(self, duckdb_dialect_real):
        translator = ASTToSQLTranslator(duckdb_dialect_real, "Patient")
        translator.context.push_path("name")

        fragment = translator.visit_aggregation(_make_count_node())

        assert "json_array_length" in fragment.expression
        assert "COALESCE" in fragment.expression
        assert "$.name" in fragment.expression
        translator.context.parent_path.clear()

    def test_count_scalar_field_duckdb_real(self, duckdb_dialect_real):
        translator = ASTToSQLTranslator(duckdb_dialect_real, "Patient")
        translator.context.push_path("birthDate")

        fragment = translator.visit_aggregation(_make_count_node())

        assert fragment.expression.startswith("COALESCE(")
        assert "ELSE 1" in fragment.expression
        assert "$.birthDate" in fragment.expression
        translator.context.parent_path.clear()

    def test_count_without_path_duckdb_real(self, duckdb_dialect_real):
        translator = ASTToSQLTranslator(duckdb_dialect_real, "Patient")
        translator.context.parent_path.clear()

        fragment = translator.visit_aggregation(_make_count_node())

        assert fragment.expression == "COUNT(*)"

    def test_count_array_field_postgresql_real(self, postgresql_dialect_real):
        translator = ASTToSQLTranslator(postgresql_dialect_real, "Patient")
        translator.context.push_path("telecom")

        fragment = translator.visit_aggregation(_make_count_node())

        lowered = fragment.expression.lower()
        assert "jsonb_array_length" in lowered or "json_array_length" in lowered
        assert "coalesce" in lowered
        assert "telecom" in lowered
        translator.context.parent_path.clear()

    def test_count_scalar_field_postgresql_real(self, postgresql_dialect_real):
        translator = ASTToSQLTranslator(postgresql_dialect_real, "Patient")
        translator.context.push_path("birthDate")

        fragment = translator.visit_aggregation(_make_count_node())

        lowered = fragment.expression.lower()
        assert lowered.startswith("coalesce(")
        assert "else 1" in lowered
        translator.context.parent_path.clear()

    @pytest.mark.parametrize(
        "path_components",
        [
            ["component"],
            ["component", "value"],
            ["extension", "value", "Coding"],
        ],
    )
    def test_count_handles_varied_paths_real_duckdb(self, duckdb_dialect_real, path_components):
        translator = ASTToSQLTranslator(duckdb_dialect_real, "Observation")
        for component in path_components:
            translator.context.push_path(component)

        fragment = translator.visit_aggregation(_make_count_node())
        expected_path = "$." + ".".join(path_components)

        assert expected_path in fragment.expression
        translator.context.parent_path.clear()

    def test_count_fragment_metadata_real(self, duckdb_dialect_real):
        translator = ASTToSQLTranslator(duckdb_dialect_real, "Patient")
        translator.context.push_path("name")

        fragment = translator.visit_aggregation(_make_count_node())

        assert fragment.is_aggregate is True
        assert fragment.requires_unnest is False
        assert fragment.dependencies == []
        translator.context.parent_path.clear()

    def test_count_respects_current_table_override_real(self, duckdb_dialect_real):
        translator = ASTToSQLTranslator(duckdb_dialect_real, "Patient")
        translator.context.current_table = "cte_results"
        translator.context.push_path("name")

        fragment = translator.visit_aggregation(_make_count_node())

        assert "cte_results" in fragment.expression
        assert fragment.source_table == "cte_results"
        translator.context.parent_path.clear()

    def test_count_invalid_function_raises_valueerror_real(self, duckdb_dialect_real):
        translator = ASTToSQLTranslator(duckdb_dialect_real, "Patient")
        invalid_node = AggregationNode(
            node_type="aggregation",
            text="median()",
            aggregation_function="median",
            aggregation_type="median",
        )

        with pytest.raises(ValueError, match="Unsupported aggregation function"):
            translator.visit_aggregation(invalid_node)
