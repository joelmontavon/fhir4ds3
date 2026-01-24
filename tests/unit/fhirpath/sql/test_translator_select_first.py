"""Unit tests for ASTToSQLTranslator select() and first() function translation.

Tests the _translate_select() and _translate_first() method implementations for
array transformation and access. Validates correctness across both DuckDB and
PostgreSQL dialects.

Test Coverage:
- select() with simple field projection
- select() with complex expressions
- select() context management (table updates, path handling)
- first() with array indexing (population-friendly, NOT LIMIT 1)
- first() context management
- Dialect-specific SQL syntax generation
- Error handling for invalid arguments
- Multi-database consistency validation

Module: tests.unit.fhirpath.sql.test_translator_select_first
Created: 2025-09-30
Task: SP-005-009
"""

import pytest
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode, OperatorNode, LiteralNode, IdentifierNode
)

def _assert_has_lateral_alias(expression: str) -> None:
    """Verify generated SQL includes aliased LATERAL UNNEST clause."""
    assert "LATERAL" in expression
    assert " AS cte_" in expression


@pytest.fixture
def duckdb_dialect():
    """Create DuckDB dialect for testing"""
    from fhir4ds.dialects.duckdb import DuckDBDialect
    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Create PostgreSQL dialect for testing (if available)"""
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    try:
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not available")


class TestSelectBasicTranslation:
    """Test basic select() function translation"""

    def test_select_with_simple_field_projection(self, duckdb_dialect):
        """Test select() with simple field projection"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.select(family)
        translator.context.push_path("name")

        # Create projection expression: family
        projection_node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        # Create select() function call
        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection_node]
        )
        select_node.children = [projection_node]

        fragment = translator._translate_select(select_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is True
        assert fragment.is_aggregate is True
        # Check for LATERAL (used by both DuckDB and PostgreSQL) instead of UNNEST
        assert "LATERAL" in fragment.expression
        assert "$.name" in fragment.expression
        assert "GROUP BY" in fragment.expression
        assert fragment.source_table == "cte_1"
        _assert_has_lateral_alias(fragment.expression)

    def test_select_with_nested_field_projection(self, duckdb_dialect):
        """Test select() with nested field access"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.select(given)
        translator.context.push_path("name")

        # Create projection expression: given
        projection_node = IdentifierNode(
            node_type="identifier",
            text="given",
            identifier="given"
        )

        # Create select() function call
        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(given)",
            function_name="select",
            arguments=[projection_node]
        )
        select_node.children = [projection_node]

        fragment = translator._translate_select(select_node)

        assert "$.name" in fragment.expression
        assert "given" in fragment.expression
        assert fragment.requires_unnest is True
        assert fragment.is_aggregate is True
        _assert_has_lateral_alias(fragment.expression)

    def test_select_updates_context_table(self, duckdb_dialect):
        """Test that select() updates context.current_table"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("telecom")

        old_table = translator.context.current_table

        # Create simple select() expression
        projection_node = IdentifierNode(
            node_type="identifier",
            text="value",
            identifier="value"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(value)",
            function_name="select",
            arguments=[projection_node]
        )
        select_node.children = [projection_node]

        fragment = translator._translate_select(select_node)

        # Context table should be updated to new CTE name
        assert translator.context.current_table == "cte_1"
        assert translator.context.current_table != old_table
        assert fragment.source_table == "cte_1"

    def test_select_with_no_arguments_raises_error(self, duckdb_dialect):
        """Test that select() with no arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create select() with no arguments (invalid)
        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select()",
            function_name="select",
            arguments=[]
        )
        select_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_select(select_node)

        assert "requires exactly 1 argument" in str(exc_info.value)

    def test_select_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Test that select() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create two projection nodes
        projection1 = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )
        projection2 = IdentifierNode(
            node_type="identifier",
            text="given",
            identifier="given"
        )

        # Create select() with multiple arguments (invalid)
        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family, given)",
            function_name="select",
            arguments=[projection1, projection2]
        )
        select_node.children = [projection1, projection2]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_select(select_node)

        assert "requires exactly 1 argument" in str(exc_info.value)

    def test_select_includes_dependencies(self, duckdb_dialect):
        """Test that select() tracks source table dependency"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        translator.context.push_path("component")

        old_table = translator.context.current_table

        projection_node = IdentifierNode(
            node_type="identifier",
            text="code",
            identifier="code"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(code)",
            function_name="select",
            arguments=[projection_node]
        )
        select_node.children = [projection_node]

        fragment = translator._translate_select(select_node)

        # Should have dependency on old table
        assert old_table in fragment.dependencies
        assert len(fragment.dependencies) == 1
        _assert_has_lateral_alias(fragment.expression)

    def test_select_generates_unique_cte_names(self, duckdb_dialect):
        """Test that multiple select() calls generate unique CTE names"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # First select()
        translator.context.push_path("name")
        projection1 = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )
        select_node1 = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection1]
        )
        select_node1.children = [projection1]

        fragment1 = translator._translate_select(select_node1)

        # Second select()
        translator.context.pop_path()
        translator.context.push_path("telecom")
        projection2 = IdentifierNode(
            node_type="identifier",
            text="value",
            identifier="value"
        )
        select_node2 = FunctionCallNode(
            node_type="functionCall",
            text="select(value)",
            function_name="select",
            arguments=[projection2]
        )
        select_node2.children = [projection2]

        fragment2 = translator._translate_select(select_node2)

        # CTE names should be different
        assert fragment1.source_table != fragment2.source_table
        assert fragment1.source_table == "cte_1"
        assert fragment2.source_table == "cte_2"
        _assert_has_lateral_alias(fragment1.expression)
        _assert_has_lateral_alias(fragment2.expression)

    def test_select_clears_path_during_projection_translation(self, duckdb_dialect):
        """Test that select() clears path during projection translation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up nested path
        translator.context.push_path("name")
        translator.context.push_path("given")

        # Create projection that references field at element level
        projection_node = IdentifierNode(
            node_type="identifier",
            text="use",
            identifier="use"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(use)",
            function_name="select",
            arguments=[projection_node]
        )
        select_node.children = [projection_node]

        # Before select(), path should be ["name", "given"]
        assert translator.context.parent_path == ["name", "given"]

        fragment = translator._translate_select(select_node)

        # After select(), path should be restored to ["name", "given"]
        assert translator.context.parent_path == ["name", "given"]
        _assert_has_lateral_alias(fragment.expression)


class TestSelectDialectConsistency:
    """Test select() generates consistent SQL across dialects"""

    def test_select_duckdb_syntax(self, duckdb_dialect):
        """Test select() generates correct DuckDB syntax"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        projection_node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection_node]
        )
        select_node.children = [projection_node]

        fragment = translator._translate_select(select_node)

        # DuckDB should aggregate via to_json(list(...)) for list semantics
        lowered = fragment.expression.lower()
        assert "to_json(list(" in lowered
        _assert_has_lateral_alias(fragment.expression)

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_select_consistent_metadata_across_dialects(self, dialect_fixture, request):
        """Test select() produces consistent metadata across dialects"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")
        translator.context.push_path("name")

        projection_node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection_node]
        )
        select_node.children = [projection_node]

        fragment = translator._translate_select(select_node)

        # All dialects should have consistent metadata
        assert fragment.requires_unnest is True
        assert fragment.is_aggregate is True
        assert fragment.source_table == "cte_1"
        assert len(fragment.dependencies) == 1
        _assert_has_lateral_alias(fragment.expression)


class TestFirstBasicTranslation:
    """Test basic first() function translation"""

    def test_first_with_simple_array_access(self, duckdb_dialect):
        """Test first() with simple array field access"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.first()
        translator.context.push_path("name")

        # Create first() function call
        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False  # No unnest needed
        assert fragment.is_aggregate is False
        assert "$.name[0]" in fragment.expression
        assert "LIMIT" not in fragment.expression.upper()  # No LIMIT 1 anti-pattern

    def test_first_uses_array_indexing_not_limit(self, duckdb_dialect):
        """Test first() uses [0] indexing, NOT LIMIT 1 (population-friendly)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        translator.context.push_path("component")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # Must use [0] indexing
        assert "[0]" in fragment.expression

        # Must NOT use LIMIT 1 (violates population-first principle)
        assert "LIMIT" not in fragment.expression.upper()
        assert "LIMIT 1" not in fragment.expression

    def test_first_updates_context_path(self, duckdb_dialect):
        """Test that first() updates context path with [0]"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        original_path_length = len(translator.context.parent_path)

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # Path should have [0] appended
        assert len(translator.context.parent_path) == original_path_length + 1
        assert translator.context.parent_path[-1] == "[0]"

    def test_first_with_arguments_raises_error(self, duckdb_dialect):
        """Test that first() with arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create first() with argument (invalid)
        arg_node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first(family)",
            function_name="first",
            arguments=[arg_node]
        )
        first_node.children = [arg_node]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_first(first_node)

        assert "requires 0 arguments" in str(exc_info.value)

    def test_first_does_not_require_unnest(self, duckdb_dialect):
        """Test that first() does not set requires_unnest flag"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("telecom")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # first() operates at JSON path level, no unnest needed
        assert fragment.requires_unnest is False

    def test_first_is_not_aggregate(self, duckdb_dialect):
        """Test that first() does not set is_aggregate flag"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # first() is not an aggregate operation
        assert fragment.is_aggregate is False

    def test_first_has_no_dependencies(self, duckdb_dialect):
        """Test that first() has empty dependencies list"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        translator.context.push_path("component")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # first() operates on current context, no dependencies
        assert fragment.dependencies == []

    def test_first_maintains_current_table(self, duckdb_dialect):
        """Test that first() maintains current_table reference"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        old_table = translator.context.current_table

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # current_table should remain unchanged (unlike where/select which create CTEs)
        assert translator.context.current_table == old_table
        assert fragment.source_table == old_table

    def test_first_with_nested_path(self, duckdb_dialect):
        """Test first() with nested path context"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Build nested path: Patient.contact.name
        translator.context.push_path("contact")
        translator.context.push_path("name")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # Should build path correctly
        assert "$.contact.name[0]" in fragment.expression


class TestFirstDialectConsistency:
    """Test first() generates consistent SQL across dialects"""

    def test_first_duckdb_syntax(self, duckdb_dialect):
        """Test first() generates correct DuckDB syntax"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # DuckDB should use json_extract with [0] indexing
        assert "json_extract" in fragment.expression.lower()
        assert "[0]" in fragment.expression

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_first_consistent_metadata_across_dialects(self, dialect_fixture, request):
        """Test first() produces consistent metadata across dialects"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")
        translator.context.push_path("name")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # All dialects should have consistent metadata
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert fragment.source_table == "resource"
        assert fragment.dependencies == []

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_first_no_limit_clause_any_dialect(self, dialect_fixture, request):
        """Test first() never uses LIMIT clause in any dialect (population-first)"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Observation")
        translator.context.push_path("component")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # CRITICAL: No dialect should use LIMIT (violates population-first principle)
        assert "LIMIT" not in fragment.expression.upper()


class TestSelectFirstChaining:
    """Test chaining select() and first() functions"""

    def test_first_after_path_navigation(self, duckdb_dialect):
        """Test first() can be used after path navigation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Build path: Patient.contact.telecom
        translator.context.push_path("contact")
        translator.context.push_path("telecom")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        assert "$.contact.telecom[0]" in fragment.expression

    def test_select_on_simple_array(self, duckdb_dialect):
        """Test select() on simple array field"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("address")

        projection_node = IdentifierNode(
            node_type="identifier",
            text="city",
            identifier="city"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(city)",
            function_name="select",
            arguments=[projection_node]
        )
        select_node.children = [projection_node]

        fragment = translator._translate_select(select_node)

        assert "$.address" in fragment.expression
        assert "city" in fragment.expression
        _assert_has_lateral_alias(fragment.expression)


class TestPopulationScaleValidation:
    """Validate population-scale patterns for select() and first()"""

    def test_first_population_friendly_design(self, duckdb_dialect):
        """Validate first() uses population-friendly array indexing"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragment = translator._translate_first(first_node)

        # Population-friendly: Uses json path [0] indexing
        # This operates on each patient's name array independently
        assert "[0]" in fragment.expression

        # Anti-pattern check: No LIMIT which would restrict entire query
        assert "LIMIT" not in fragment.expression.upper()

    def test_select_population_friendly_design(self, duckdb_dialect):
        """Validate select() uses population-friendly aggregation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        projection_node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection_node]
        )
        select_node.children = [projection_node]

        fragment = translator._translate_select(select_node)

        # Population-friendly: Uses GROUP BY with patient ID
        assert "GROUP BY" in fragment.expression
        assert ".id" in fragment.expression

        # Should aggregate per patient, not globally
        lowered = fragment.expression.lower()
        assert "to_json(list(" in lowered or "json_agg" in lowered or "array_agg" in lowered
        _assert_has_lateral_alias(fragment.expression)
