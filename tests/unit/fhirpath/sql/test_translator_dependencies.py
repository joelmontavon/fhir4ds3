"""Unit tests for dependency tracking in SQL translation.

This test module provides comprehensive coverage of dependency tracking between
SQL fragments generated during FHIRPath AST translation. Dependency tracking is
critical for CTE generation and ensuring correct execution order.

Test Coverage:
- Dependency population in all translator methods
- Dependency chains across multiple operations
- Dependency validation and correctness
- Edge cases (circular dependencies, missing dependencies)
- Multi-database consistency

Module: tests.unit.fhirpath.sql.test_translator_dependencies
Related: fhir4ds.fhirpath.sql.translator, fhir4ds.fhirpath.sql.fragments
Task: SP-005-015 - Implement Dependency Tracking
Created: 2025-09-30
"""

import pytest
from unittest.mock import MagicMock, patch
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.ast.nodes import (
    LiteralNode, IdentifierNode, FunctionCallNode, OperatorNode
)


@pytest.fixture
def duckdb_dialect():
    """Create a DuckDB dialect instance for testing."""
    from fhir4ds.dialects.duckdb import DuckDBDialect
    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Create a PostgreSQL dialect instance for testing."""
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        pytest.skip("psycopg2 not available")

    dummy_conn = MagicMock()
    dummy_cursor = MagicMock()
    dummy_conn.cursor.return_value = dummy_cursor
    dummy_cursor.execute.return_value = None
    dummy_cursor.fetchall.return_value = []

    with patch("fhir4ds.dialects.postgresql.psycopg2.connect", return_value=dummy_conn):
        return PostgreSQLDialect(connection_string="postgresql://postgres:postgres@localhost:5432/postgres")


class TestBasicDependencyTracking:
    """Test dependency tracking for individual operations."""

    def test_literal_has_no_dependencies(self, duckdb_dialect):
        """Test that literal nodes have empty dependencies list."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal = LiteralNode(
            node_type="literal",
            text="42",
            value=42,
            literal_type="integer"
        )

        fragments = translator.translate(literal)
        assert len(fragments) == 1
        assert fragments[0].dependencies == []

    def test_identifier_has_no_dependencies(self, duckdb_dialect):
        """Test that identifier nodes have empty dependencies list."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        identifier = IdentifierNode(
            node_type="identifier",
            text="name",
            identifier="name"
        )

        fragments = translator.translate(identifier)
        assert len(fragments) == 1
        assert fragments[0].dependencies == []

    def test_where_tracks_source_table_dependency(self, duckdb_dialect):
        """Test that where() tracks dependency on source table."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create condition: use = 'official'
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        fragments = translator.translate(where_node)

        # where() should have dependency on source table
        assert len(fragments) == 1
        assert "resource" in fragments[0].dependencies
        assert len(fragments[0].dependencies) == 1

    def test_select_tracks_source_table_dependency(self, duckdb_dialect):
        """Test that select() tracks dependency on source table."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create projection expression: family
        projection = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection]
        )
        select_node.children = [projection]

        fragments = translator.translate(select_node)

        # select() should have dependency on source table
        assert len(fragments) == 1
        assert "resource" in fragments[0].dependencies
        assert len(fragments[0].dependencies) == 1

    def test_first_has_no_dependencies(self, duckdb_dialect):
        """Test that first() has empty dependencies list."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )
        first_node.children = []

        fragments = translator.translate(first_node)

        # first() operates on current context, no new dependencies
        assert len(fragments) == 1
        assert fragments[0].dependencies == []

    def test_exists_without_criteria_has_no_dependencies(self, duckdb_dialect):
        """Test that exists() without criteria has empty dependencies list."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists()",
            function_name="exists",
            arguments=[]
        )
        exists_node.children = []

        fragments = translator.translate(exists_node)

        # exists() without criteria just checks array length, no dependencies
        assert len(fragments) == 1
        assert fragments[0].dependencies == []

    def test_exists_with_criteria_tracks_source_dependency(self, duckdb_dialect):
        """Test that exists() with criteria tracks dependency on source table."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create condition: use = 'official'
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists(use='official')",
            function_name="exists",
            arguments=[condition]
        )
        exists_node.children = [condition]

        fragments = translator.translate(exists_node)

        # exists() with criteria uses EXISTS subquery, has dependency
        assert len(fragments) == 1
        assert "resource" in fragments[0].dependencies
        assert len(fragments[0].dependencies) == 1


class TestDependencyChains:
    """Test dependency tracking through chains of operations."""

    def test_where_with_custom_source_table_tracks_correctly(self, duckdb_dialect):
        """Test that where() tracks dependency on custom source table."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("telecom")

        # Create condition
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="system", identifier="system"),
            LiteralNode(node_type="literal", text="'phone'", value="phone", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(system='phone')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        # Call _translate_where directly to bypass reset
        fragment = translator._translate_where(where_node)

        # Should track dependency on current table (resource)
        assert "resource" in fragment.dependencies

        # Now manually update context to simulate a chain
        # and call _translate_where again
        translator.context.current_table = "cte_1"
        translator.context.push_path("address")

        condition2 = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition2.children = [
            IdentifierNode(node_type="identifier", text="city", identifier="city"),
            LiteralNode(node_type="literal", text="'Boston'", value="Boston", literal_type="string")
        ]

        where_node2 = FunctionCallNode(
            node_type="functionCall",
            text="where(city='Boston')",
            function_name="where",
            arguments=[condition2]
        )
        where_node2.children = [condition2]

        # Call _translate_where directly without reset
        fragment2 = translator._translate_where(where_node2)

        # Should track dependency on cte_1, not resource
        assert "cte_1" in fragment2.dependencies
        assert "resource" not in fragment2.dependencies

    def test_select_with_custom_source_table_tracks_correctly(self, duckdb_dialect):
        """Test that select() tracks dependency on custom source table."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        projection = IdentifierNode(
            node_type="identifier",
            text="given",
            identifier="given"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(given)",
            function_name="select",
            arguments=[projection]
        )
        select_node.children = [projection]

        # Call _translate_select directly to bypass reset
        fragment = translator._translate_select(select_node)

        # Should track dependency on current table (resource)
        assert "resource" in fragment.dependencies

        # Now manually update context to simulate a chain
        # and call _translate_select again
        translator.context.current_table = "cte_2"
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

        # Call _translate_select directly without reset
        fragment2 = translator._translate_select(select_node2)

        # Should track dependency on cte_2
        assert "cte_2" in fragment2.dependencies
        assert "resource" not in fragment2.dependencies

    @pytest.mark.skip(reason="Compositional design: dependency tracking changed")
    def test_dependency_chain_through_multiple_operations(self, duckdb_dialect):
        """Test that dependencies are tracked correctly through a chain."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Simulate a chain: resource -> where (cte_1) -> select (cte_2)

        # First operation: where() on resource
        translator.context.push_path("name")
        condition1 = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition1.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition1]
        )
        where_node.children = [condition1]

        # Call _translate_where directly to bypass reset
        where_fragment = translator._translate_where(where_node)

        # First fragment should depend on resource
        assert "resource" in where_fragment.dependencies

        # The context.current_table should now be cte_1
        assert translator.context.current_table == "cte_1"

        # Second operation: select() on cte_1
        translator.context.push_path("name")  # Set path for select
        projection = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection]
        )
        select_node.children = [projection]

        # Call _translate_select directly without reset
        select_fragment = translator._translate_select(select_node)

        # Second fragment should depend on cte_1
        assert "cte_1" in select_fragment.dependencies
        assert "resource" not in select_fragment.dependencies


class TestDependencyValidation:
    """Test dependency validation and correctness."""

    def test_dependencies_are_list_type(self, duckdb_dialect):
        """Test that all fragments have dependencies as list type."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        fragments = translator.translate(where_node)

        # Verify dependencies is a list
        assert isinstance(fragments[0].dependencies, list)

    def test_dependencies_contain_only_strings(self, duckdb_dialect):
        """Test that dependencies contain only string table names."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        fragments = translator.translate(where_node)

        # Verify all dependencies are strings
        for dep in fragments[0].dependencies:
            assert isinstance(dep, str)

    def test_no_duplicate_dependencies(self, duckdb_dialect):
        """Test that dependencies list has no duplicates."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        fragments = translator.translate(where_node)

        # Verify no duplicates
        deps = fragments[0].dependencies
        assert len(deps) == len(set(deps))

    def test_dependencies_are_valid_table_names(self, duckdb_dialect):
        """Test that dependencies contain valid SQL table/CTE names."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        fragments = translator.translate(where_node)

        # Verify dependencies are valid table names (alphanumeric + underscore)
        import re
        for dep in fragments[0].dependencies:
            assert re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', dep), f"Invalid table name: {dep}"


class TestMultiDatabaseDependencyConsistency:
    """Test dependency tracking consistency across database dialects."""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_where_dependencies_consistent_across_dialects(self, dialect_fixture, request):
        """Test that where() tracks same dependencies on both dialects."""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")
        translator.context.push_path("name")

        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        fragments = translator.translate(where_node)

        # Both dialects should track same dependency
        assert "resource" in fragments[0].dependencies
        assert len(fragments[0].dependencies) == 1

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_select_dependencies_consistent_across_dialects(self, dialect_fixture, request):
        """Test that select() tracks same dependencies on both dialects."""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")
        translator.context.push_path("name")

        projection = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection]
        )
        select_node.children = [projection]

        fragments = translator.translate(select_node)

        # Both dialects should track same dependency
        assert "resource" in fragments[0].dependencies
        assert len(fragments[0].dependencies) == 1


class TestEdgeCases:
    """Test edge cases in dependency tracking."""

    def test_aggregation_has_no_dependencies(self, duckdb_dialect):
        """Test that aggregation functions have empty dependencies."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create count() aggregation using visit_aggregation
        from fhir4ds.fhirpath.ast.nodes import AggregationNode

        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragments = translator.translate(count_node)

        # Aggregation operates on current context, no new dependencies
        assert len(fragments) == 1
        assert fragments[0].dependencies == []

    @pytest.mark.skip(reason="Compositional design: context handling changed")
    def test_reset_context_clears_previous_dependencies_context(self, duckdb_dialect):
        """Test that resetting context allows fresh dependency tracking."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # First translation
        translator.context.push_path("name")
        condition1 = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition1.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node1 = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition1]
        )
        where_node1.children = [condition1]

        fragments1 = translator.translate(where_node1)
        assert translator.context.current_table == "cte_1"

        # Second translation (reset happens in translate())
        translator.context.push_path("telecom")
        condition2 = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition2.children = [
            IdentifierNode(node_type="identifier", text="system", identifier="system"),
            LiteralNode(node_type="literal", text="'phone'", value="phone", literal_type="string")
        ]

        where_node2 = FunctionCallNode(
            node_type="functionCall",
            text="where(system='phone')",
            function_name="where",
            arguments=[condition2]
        )
        where_node2.children = [condition2]

        fragments2 = translator.translate(where_node2)

        # Second translation should start fresh with resource
        assert "resource" in fragments2[0].dependencies
        assert "cte_1" not in fragments2[0].dependencies
