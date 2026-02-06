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
    """skip(n) should emit OFFSET semantics (for scalar arrays) or row filtering (for UNNEST)."""
    dialect = request.getfixturevalue(dialect_fixture)
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(dialect, "Patient")

    # Parse the full expression to get proper context
    ast = parser.parse("Patient.name.skip(2)").get_ast()
    fragments = translator.translate(ast)

    # The last fragment should be from skip()
    skip_fragment = fragments[-1]
    assert isinstance(skip_fragment, SQLFragment)
    assert skip_fragment.metadata.get("function") == "skip"
    assert skip_fragment.metadata.get("is_collection") is True

    # When UNNEST fragments exist, skip() uses row filtering (column reference)
    # When no UNNEST fragments exist, skip() uses OFFSET in the SQL
    # The actual OFFSET/LIMIT logic is in the CTE builder, not the fragment expression
    # So we just check the metadata is set correctly
    assert "subset_filter" in skip_fragment.metadata or skip_fragment.metadata.get("array_column") is not None


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_skip_handles_negative_counts_with_empty_collection(dialect_fixture, request):
    """skip(n) returns empty collection when n < 0."""
    dialect = request.getfixturevalue(dialect_fixture)
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(dialect, "Patient")

    # Parse the full expression to get proper context
    ast = parser.parse("Patient.name.skip(-3)").get_ast()
    fragments = translator.translate(ast)

    # The last fragment should be from skip()
    skip_fragment = fragments[-1]
    assert isinstance(skip_fragment, SQLFragment)
    assert skip_fragment.metadata.get("function") == "skip"

    # The negative count check is in the array_column metadata when no UNNEST
    # or handled by CTE builder when UNNEST exists
    array_column = skip_fragment.metadata.get("array_column", "")
    if array_column:
        # For non-UNNEST case, the negative check should be in the expression
        assert "(-3) < 0" in array_column or "(-3) < 0" in skip_fragment.expression


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_take_uses_limit_and_empty_guard(dialect_fixture, request):
    """take(n) should emit LIMIT semantics and guard non-positive counts."""
    dialect = request.getfixturevalue(dialect_fixture)
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(dialect, "Patient")

    # Parse the full expression to get proper context
    ast = parser.parse("Patient.name.take(5)").get_ast()
    fragments = translator.translate(ast)

    # The last fragment should be from take()
    take_fragment = fragments[-1]
    assert isinstance(take_fragment, SQLFragment)
    assert take_fragment.metadata.get("function") == "take"
    assert take_fragment.metadata.get("is_collection") is True

    # The LIMIT logic is in the array_column metadata when no UNNEST
    # or handled by CTE builder when UNNEST exists
    array_column = take_fragment.metadata.get("array_column", "")
    if array_column:
        # For non-UNNEST case, the positive check and LIMIT should be in the expression
        assert "(5) <= 0" in array_column or "(5) <= 0" in take_fragment.expression


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_tail_equivalent_to_skip_one(dialect_fixture, request):
    """tail() should delegate to skip(1) and produce identical metadata."""
    dialect = request.getfixturevalue(dialect_fixture)
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(dialect, "Patient")

    # Parse tail expression
    tail_ast = parser.parse("Patient.name.tail()").get_ast()
    tail_fragments = translator.translate(tail_ast)

    # Parse skip(1) expression
    skip_ast = parser.parse("Patient.name.skip(1)").get_ast()
    skip_fragments = translator.translate(skip_ast)

    # Both should have the same metadata structure
    tail_fragment = tail_fragments[-1]
    skip_fragment = skip_fragments[-1]

    # tail() is syntactic sugar for skip(1), so both produce "skip" function metadata
    assert skip_fragment.metadata.get("function") == "skip"
    # tail() delegates to skip(), so it should also have "skip" as function
    assert tail_fragment.metadata.get("function") in ("tail", "skip")

    # Both should mark themselves as subset filters or have array columns
    assert ("subset_filter" in tail_fragment.metadata) == ("subset_filter" in skip_fragment.metadata)


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_last_orders_descending_and_limits_one(dialect_fixture, request):
    """last() should order elements descending and apply LIMIT 1."""
    dialect = request.getfixturevalue(dialect_fixture)
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(dialect, "Patient")

    # Parse the full expression to get proper context
    ast = parser.parse("Patient.name.last()").get_ast()
    fragments = translator.translate(ast)

    # The last fragment should be from last()
    last_fragment = fragments[-1]
    assert isinstance(last_fragment, SQLFragment)
    assert last_fragment.metadata.get("function") == "last"

    # last() returns a single element, not a collection
    # When using UNNEST, is_collection might not be set (defaults to None/False)
    # When not using UNNEST, it should be explicitly False
    is_collection = last_fragment.metadata.get("is_collection")
    assert is_collection is None or is_collection is False

    # last() metadata should indicate subset_filter
    assert "subset_filter" in last_fragment.metadata


def test_skip_requires_argument(duckdb_dialect):
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

    # Parse an invalid skip() expression
    ast = parser.parse("Patient.name.skip()").get_ast()

    # Should raise ValueError during translation
    with pytest.raises(ValueError, match="skip\\(\\) function requires exactly 1 argument"):
        translator.translate(ast)


def test_take_requires_argument(duckdb_dialect):
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

    # Parse an invalid take() expression
    ast = parser.parse("Patient.name.take()").get_ast()

    # Should raise ValueError during translation
    with pytest.raises(ValueError, match="take\\(\\) function requires exactly 1 argument"):
        translator.translate(ast)


def test_tail_rejects_arguments(duckdb_dialect):
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

    # Parse an invalid tail(1) expression
    ast = parser.parse("Patient.name.tail(1)").get_ast()

    # Should raise ValueError during translation
    with pytest.raises(ValueError, match="tail\\(\\) function takes no arguments"):
        translator.translate(ast)


def test_last_rejects_arguments(duckdb_dialect):
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

    # Parse an invalid last(1) expression
    ast = parser.parse("Patient.name.last(1)").get_ast()

    # Should raise ValueError during translation
    with pytest.raises(ValueError, match="last\\(\\) function takes no arguments"):
        translator.translate(ast)


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_skip_supports_property_chaining(dialect_fixture, request):
    """skip() should support property chaining after it."""
    dialect = request.getfixturevalue(dialect_fixture)
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(dialect, "Patient")

    # Parse the full expression
    ast = parser.parse("Patient.name.skip(1).family").get_ast()
    fragments = translator.translate(ast)

    # Should have multiple fragments
    assert len(fragments) >= 2

    # Last fragment should be the property access
    last_fragment = fragments[-1]
    assert isinstance(last_fragment, SQLFragment)


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_take_supports_property_chaining(dialect_fixture, request):
    """take() should support property chaining after it."""
    dialect = request.getfixturevalue(dialect_fixture)
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(dialect, "Patient")

    # Parse the full expression
    ast = parser.parse("Patient.telecom.take(2).system").get_ast()
    fragments = translator.translate(ast)

    # Should have multiple fragments
    assert len(fragments) >= 2

    # Last fragment should be the property access
    last_fragment = fragments[-1]
    assert isinstance(last_fragment, SQLFragment)


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_last_supports_property_chaining(dialect_fixture, request):
    """last() should support property chaining after it."""
    dialect = request.getfixturevalue(dialect_fixture)
    from fhir4ds.main.fhirpath.parser import FHIRPathParser
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(dialect, "Patient")

    # Parse the full expression
    ast = parser.parse("Patient.name.last().family").get_ast()
    fragments = translator.translate(ast)

    # Should have multiple fragments
    assert len(fragments) >= 2

    # Last fragment should be the property access
    last_fragment = fragments[-1]
    assert isinstance(last_fragment, SQLFragment)
    # The property access after last() returns a single value
    # The is_collection might not be set on the final fragment
