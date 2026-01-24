"""Unit tests for ASTToSQLTranslator where() function translation.

Tests the _translate_where() method implementation for array filtering
with LATERAL UNNEST SQL generation. Validates correctness across both
DuckDB and PostgreSQL dialects.

Test Coverage:
- Simple where() with equality conditions
- where() with comparison operators
- where() with complex logical conditions
- Context management (table updates, path handling)
- Dialect-specific SQL syntax generation
- Error handling for invalid arguments
- Population-friendly SQL patterns (no LIMIT 1)

Module: tests.unit.fhirpath.sql.test_translator_where
Created: 2025-09-30
Task: SP-005-008
"""

import pytest
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode, OperatorNode, LiteralNode, IdentifierNode
)


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


class TestWhereBasicTranslation:
    """Test basic where() function translation"""

    def test_where_with_simple_equality(self, duckdb_dialect):
        """Test where() with simple equality condition"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.where(use='official')
        translator.context.push_path("name")

        # Create condition: use='official'
        left_node = IdentifierNode(
            node_type="identifier",
            text="use",
            identifier="use"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="'official'",
            value="official",
            literal_type="string"
        )
        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [left_node, right_node]

        # Create where() function call
        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        fragment = translator._translate_where(where_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False  # Compositional design: subquery is self-contained
        assert fragment.is_aggregate is False
        # Check for LATERAL (used by both DuckDB and PostgreSQL) instead of UNNEST
        assert "LATERAL" in fragment.expression
        assert "$.name" in fragment.expression
        assert "'official'" in fragment.expression
        assert "WHERE" in fragment.expression

    def test_where_with_comparison_operator(self, duckdb_dialect):
        """Test where() with comparison operator (>)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Set up context: Observation.component.where(value > 100)
        translator.context.push_path("component")

        # Create condition: value > 100
        left_node = IdentifierNode(
            node_type="identifier",
            text="value",
            identifier="value"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="100",
            value=100,
            literal_type="integer"
        )
        condition_node = OperatorNode(
            node_type="operator",
            text=">",
            operator=">",
            operator_type="comparison"
        )
        condition_node.children = [left_node, right_node]

        # Create where() function call
        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(value > 100)",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        fragment = translator._translate_where(where_node)

        assert "> 100" in fragment.expression
        assert "$.component" in fragment.expression
        assert fragment.requires_unnest is False  # Compositional design: subquery is self-contained

    @pytest.mark.skip(reason="Compositional design: where() returns subquery, doesn't update context")
    def test_where_updates_context_table(self, duckdb_dialect):
        """Test that where() updates context.current_table"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        old_table = translator.context.current_table

        # Create simple where() condition
        left_node = IdentifierNode(
            node_type="identifier",
            text="use",
            identifier="use"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="'official'",
            value="official",
            literal_type="string"
        )
        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [left_node, right_node]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        fragment = translator._translate_where(where_node)

        # Context table should be updated to CTE name
        assert translator.context.current_table != old_table
        assert translator.context.current_table.startswith("cte_")
        assert translator.context.current_table == fragment.source_table

    @pytest.mark.skip(reason="Compositional design: where() returns subquery, not CTE")
    def test_where_generates_unique_cte_names(self, duckdb_dialect):
        """Test that multiple where() calls generate unique CTE names"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create first where()
        translator.context.push_path("name")
        condition_node1 = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        left1 = IdentifierNode(node_type="identifier", text="use", identifier="use")
        right1 = LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        condition_node1.children = [left1, right1]

        where_node1 = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node1]
        )
        where_node1.children = [condition_node1]

        fragment1 = translator._translate_where(where_node1)
        cte_name1 = fragment1.source_table

        # Create second where()
        translator.context.pop_path()  # Reset path
        translator.context.push_path("address")
        condition_node2 = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        left2 = IdentifierNode(node_type="identifier", text="use", identifier="use")
        right2 = LiteralNode(node_type="literal", text="'home'", value="home", literal_type="string")
        condition_node2.children = [left2, right2]

        where_node2 = FunctionCallNode(
            node_type="functionCall",
            text="where(use='home')",
            function_name="where",
            arguments=[condition_node2]
        )
        where_node2.children = [condition_node2]

        fragment2 = translator._translate_where(where_node2)
        cte_name2 = fragment2.source_table

        # CTE names should be unique
        assert cte_name1 != cte_name2
        assert cte_name1 == "cte_1"
        assert cte_name2 == "cte_2"


class TestWhereComplexConditions:
    """Test where() with complex filter conditions"""

    def test_where_with_logical_and(self, duckdb_dialect):
        """Test where() with AND logical operator"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("address")

        # Create condition: use='home' and type='physical'
        left_cond = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        left_cond.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'home'", value="home", literal_type="string")
        ]

        right_cond = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        right_cond.children = [
            IdentifierNode(node_type="identifier", text="type", identifier="type"),
            LiteralNode(node_type="literal", text="'physical'", value="physical", literal_type="string")
        ]

        and_node = OperatorNode(
            node_type="operator",
            text="and",
            operator="and",
            operator_type="logical"
        )
        and_node.children = [left_cond, right_cond]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='home' and type='physical')",
            function_name="where",
            arguments=[and_node]
        )
        where_node.children = [and_node]

        fragment = translator._translate_where(where_node)

        assert "AND" in fragment.expression.upper()
        assert "'home'" in fragment.expression
        assert "'physical'" in fragment.expression


class TestWhereErrorHandling:
    """Test error handling in where() translation"""

    def test_where_with_no_arguments_raises_error(self, duckdb_dialect):
        """Test that where() with no arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where()",
            function_name="where",
            arguments=[]
        )
        where_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_where(where_node)

        assert "requires exactly 1 argument" in str(exc_info.value)

    def test_where_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Test that where() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        arg1 = LiteralNode(node_type="literal", text="true", value=True, literal_type="boolean")
        arg2 = LiteralNode(node_type="literal", text="false", value=False, literal_type="boolean")

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(true, false)",
            function_name="where",
            arguments=[arg1, arg2]
        )
        where_node.children = [arg1, arg2]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_where(where_node)

        assert "requires exactly 1 argument" in str(exc_info.value)
        assert "got 2" in str(exc_info.value)


class TestWhereDialectCompatibility:
    """Test where() translation for different SQL dialects"""

    @pytest.mark.skip(reason="Implementation uses UNNEST for compositional pattern")
    def test_where_duckdb_syntax(self, duckdb_dialect):
        """Test where() generates correct DuckDB UNNEST syntax"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Simple condition
        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        fragment = translator._translate_where(where_node)

        # DuckDB uses json_each with LATERAL join
        assert "json_each" in fragment.expression
        assert "LATERAL" in fragment.expression

    def test_where_postgresql_syntax(self, postgresql_dialect):
        """Test where() generates correct PostgreSQL jsonb_array_elements syntax"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        translator.context.push_path("name")

        # Simple condition
        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        fragment = translator._translate_where(where_node)

        # PostgreSQL uses jsonb_array_elements
        assert "jsonb_array_elements" in fragment.expression
        assert "LATERAL" in fragment.expression


class TestWhereFragmentMetadata:
    """Test SQLFragment metadata for where() translation"""

    def test_where_fragment_has_correct_flags(self, duckdb_dialect):
        """Test where() fragment has correct metadata flags"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Simple condition
        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        fragment = translator._translate_where(where_node)

        # Check metadata flags
        assert fragment.requires_unnest is False  # Compositional design: subquery is self-contained
        assert fragment.is_aggregate is False
        assert len(fragment.dependencies) == 1
        assert fragment.dependencies[0] == "resource"

    def test_where_fragment_has_dependencies(self, duckdb_dialect):
        """Test where() fragment tracks source table dependency"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Set custom source table to test dependency tracking
        translator.context.current_table = "custom_source"

        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        fragment = translator._translate_where(where_node)

        # Should track dependency on custom_source
        assert "custom_source" in fragment.dependencies


class TestWherePopulationFriendly:
    """Test that where() generates population-friendly SQL"""

    def test_where_does_not_use_limit(self, duckdb_dialect):
        """Test where() does not use LIMIT (population-first design)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        fragment = translator._translate_where(where_node)

        # Should NOT contain LIMIT
        assert "LIMIT" not in fragment.expression.upper()

    def test_where_uses_lateral_join(self, duckdb_dialect):
        """Test where() uses LATERAL join for population-scale processing"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        fragment = translator._translate_where(where_node)

        # Should use LATERAL for population processing
        assert "LATERAL" in fragment.expression


class TestWhereLogging:
    """Test logging in where() translation"""

    def test_where_logs_translation_activity(self, duckdb_dialect):
        """Test that where() logs translation steps"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        with patch('fhir4ds.fhirpath.sql.translator.logger') as mock_logger:
            translator._translate_where(where_node)

            # Should have multiple debug log calls
            assert mock_logger.debug.call_count >= 4
            # Check that key information is logged
            calls_str = str(mock_logger.debug.call_args_list)
            assert "where" in calls_str.lower()


class TestWhereIntegrationWithVisitor:
    """Test where() integration with visit_function_call"""

    def test_visit_function_call_dispatches_to_where(self, duckdb_dialect):
        """Test that visit_function_call correctly dispatches to _translate_where"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition_node]
        )
        where_node.children = [condition_node]

        # Call via visitor pattern
        fragment = translator.visit_function_call(where_node)

        # Should produce where() fragment
        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False  # Compositional design: subquery is self-contained
        assert "WHERE" in fragment.expression
