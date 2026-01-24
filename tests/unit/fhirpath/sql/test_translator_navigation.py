"""Unit tests for navigation function translation (last, tail, skip, take).

Validates that the translator emits population-scale SQL using LIMIT/OFFSET
patterns while maintaining thin dialect principles.
"""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import FunctionCallNode, LiteralNode


def _literal(value: int) -> LiteralNode:
    node = LiteralNode(
        node_type="literal",
        text=str(value),
        literal_type="integer",
        value=value,
    )
    node.children = []
    return node


def _function_node(text: str, name: str, arguments: list[LiteralNode] | None = None) -> FunctionCallNode:
    node = FunctionCallNode(
        node_type="functionCall",
        text=text,
        function_name=name,
        arguments=arguments or [],
    )
    node.children = []
    return node


@pytest.fixture
def duckdb_dialect():
    from fhir4ds.dialects.duckdb import DuckDBDialect

    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    from fhir4ds.dialects.postgresql import PostgreSQLDialect

    try:
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not available")


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_skip_uses_offset_and_preserves_metadata(dialect_fixture, request):
    """skip(n) should emit OFFSET semantics and expose metadata."""
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    node = _function_node("Patient.name.skip(2)", "skip", [_literal(2)])
    fragment = translator._translate_skip(node)

    assert isinstance(fragment, SQLFragment)
    assert "OFFSET" in fragment.expression
    assert "ORDER BY" in fragment.expression
    assert fragment.metadata.get("function") == "skip"
    assert fragment.metadata.get("is_collection") is True


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_skip_handles_negative_counts_with_empty_collection(dialect_fixture, request):
    """skip(n) returns empty collection when n < 0."""
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    node = _function_node("Patient.name.skip(-3)", "skip", [_literal(-3)])
    fragment = translator._translate_skip(node)

    assert f"({-3}) < 0" in fragment.expression
    assert dialect.empty_json_array() in fragment.expression


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_take_uses_limit_and_empty_guard(dialect_fixture, request):
    """take(n) should emit LIMIT semantics and guard non-positive counts."""
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    node = _function_node("Patient.name.take(5)", "take", [_literal(5)])
    fragment = translator._translate_take(node)

    assert "LIMIT" in fragment.expression
    assert "(5) <= 0" in fragment.expression
    assert fragment.metadata.get("function") == "take"
    assert fragment.metadata.get("is_collection") is True


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_tail_equivalent_to_skip_one(dialect_fixture, request):
    """tail() should delegate to skip(1) and produce identical SQL."""
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    tail_fragment = translator._translate_tail(_function_node("Patient.name.tail()", "tail"))
    skip_fragment = translator._translate_skip(_function_node("Patient.name.skip(1)", "skip", [_literal(1)]))

    assert tail_fragment.expression == skip_fragment.expression
    assert tail_fragment.metadata.get("function") == "tail"


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_last_orders_descending_and_limits_one(dialect_fixture, request):
    """last() should order elements descending and apply LIMIT 1."""
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    fragment = translator._translate_last(_function_node("Patient.name.last()", "last"))

    assert "ORDER BY" in fragment.expression
    assert "DESC" in fragment.expression
    assert "LIMIT 1" in fragment.expression
    assert fragment.metadata.get("function") == "last"
    assert fragment.metadata.get("is_collection") is False


def test_skip_requires_argument(duckdb_dialect):
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    with pytest.raises(ValueError, match="skip\\(\\) function requires exactly 1 argument"):
        translator._translate_skip(_function_node("Patient.name.skip()", "skip"))


def test_take_requires_argument(duckdb_dialect):
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    with pytest.raises(ValueError, match="take\\(\\) function requires exactly 1 argument"):
        translator._translate_take(_function_node("Patient.name.take()", "take"))


def test_tail_rejects_arguments(duckdb_dialect):
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    with pytest.raises(ValueError, match="tail\\(\\) function takes no arguments"):
        translator._translate_tail(_function_node("Patient.name.tail(1)", "tail", [_literal(1)]))


def test_last_rejects_arguments(duckdb_dialect):
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    with pytest.raises(ValueError, match="last\\(\\) function takes no arguments"):
        translator._translate_last(_function_node("Patient.name.last(1)", "last", [_literal(1)]))


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_skip_supports_property_chaining(dialect_fixture, request):
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    fragment = translator._translate_skip(_function_node("Patient.name.skip(1).family", "skip", [_literal(1)]))

    assert fragment.requires_unnest is True
    projection = fragment.metadata.get("projection_expression", "")
    assert "unnest" in projection
    assert "TRIM" in projection


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_take_supports_property_chaining(dialect_fixture, request):
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    fragment = translator._translate_take(_function_node("Patient.telecom.take(2).system", "take", [_literal(2)]))

    assert fragment.requires_unnest is True
    projection = fragment.metadata.get("projection_expression", "")
    assert "unnest" in projection
    assert "TRIM" in projection


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_last_supports_property_chaining(dialect_fixture, request):
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    fragment = translator._translate_last(_function_node("Patient.name.last().family", "last"))

    assert fragment.metadata.get("is_collection") is False
    assert "json_extract" in fragment.expression or "jsonb_extract_path" in fragment.expression
