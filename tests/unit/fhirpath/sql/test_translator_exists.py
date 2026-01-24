"""Unit tests for ASTToSQLTranslator exists() function translation.

Tests the _translate_exists() method implementation for existence checking
SQL generation. Validates correctness across both DuckDB and PostgreSQL dialects.

Test Coverage:
- exists() without criteria (simple non-empty check)
- exists() with equality conditions
- exists() with comparison operators
- exists() with complex logical conditions
- Context preservation (no side effects on translation state)
- Dialect-specific SQL syntax generation
- Error handling for invalid arguments
- Population-friendly SQL patterns

Module: tests.unit.fhirpath.sql.test_translator_exists
Created: 2025-09-30
Task: SP-005-010
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


class TestExistsBasicTranslation:
    """Test basic exists() function translation"""

    def test_exists_without_criteria_duckdb(self, duckdb_dialect):
        """Test exists() without criteria (simple non-empty check) on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.exists()
        translator.context.push_path("name")

        # Create exists() function call with no arguments
        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists()",
            function_name="exists",
            arguments=[]
        )
        exists_node.children = []

        fragment = translator._translate_exists(exists_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "CASE WHEN" in fragment.expression
        assert "IS NOT NULL" in fragment.expression
        assert "json_array_length" in fragment.expression
        assert "$.name" in fragment.expression
        assert "THEN TRUE" in fragment.expression
        assert "ELSE FALSE" in fragment.expression

    def test_exists_without_criteria_postgresql(self, postgresql_dialect):
        """Test exists() without criteria on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.telecom.exists()
        translator.context.push_path("telecom")

        # Create exists() function call with no arguments
        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists()",
            function_name="exists",
            arguments=[]
        )
        exists_node.children = []

        fragment = translator._translate_exists(exists_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "CASE WHEN" in fragment.expression
        assert "IS NOT NULL" in fragment.expression
        # Note: PostgreSQL also uses json_array_length for consistency
        assert "json_array_length" in fragment.expression
        assert "THEN TRUE" in fragment.expression
        assert "ELSE FALSE" in fragment.expression

    def test_exists_with_equality_condition_duckdb(self, duckdb_dialect):
        """Test exists() with simple equality condition on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.exists(use='official')
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

        # Create exists() function call with condition
        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists(use='official')",
            function_name="exists",
            arguments=[condition_node]
        )
        exists_node.children = [condition_node]

        fragment = translator._translate_exists(exists_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "CASE WHEN EXISTS" in fragment.expression
        assert "SELECT 1" in fragment.expression
        assert "UNNEST" in fragment.expression
        assert "$.name" in fragment.expression
        assert "'official'" in fragment.expression
        assert "WHERE" in fragment.expression
        assert "THEN TRUE" in fragment.expression
        assert "ELSE FALSE" in fragment.expression

    def test_exists_with_equality_condition_postgresql(self, postgresql_dialect):
        """Test exists() with equality condition on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.telecom.exists(system='phone')
        translator.context.push_path("telecom")

        # Create condition: system='phone'
        left_node = IdentifierNode(
            node_type="identifier",
            text="system",
            identifier="system"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="'phone'",
            value="phone",
            literal_type="string"
        )
        condition_node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node.children = [left_node, right_node]

        # Create exists() function call with condition
        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists(system='phone')",
            function_name="exists",
            arguments=[condition_node]
        )
        exists_node.children = [condition_node]

        fragment = translator._translate_exists(exists_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "CASE WHEN EXISTS" in fragment.expression
        assert "SELECT 1" in fragment.expression
        # PostgreSQL uses jsonb_array_elements
        assert "jsonb_array_elements" in fragment.expression
        assert "'phone'" in fragment.expression
        assert "WHERE" in fragment.expression
        assert "THEN TRUE" in fragment.expression
        assert "ELSE FALSE" in fragment.expression


class TestExistsComparisonOperators:
    """Test exists() with comparison operators"""

    def test_exists_with_greater_than(self, duckdb_dialect):
        """Test exists() with greater than comparison"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Set up context: Observation.component.exists(value > 100)
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

        # Create exists() function call
        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists(value > 100)",
            function_name="exists",
            arguments=[condition_node]
        )
        exists_node.children = [condition_node]

        fragment = translator._translate_exists(exists_node)

        assert isinstance(fragment, SQLFragment)
        assert "CASE WHEN EXISTS" in fragment.expression
        assert "SELECT 1" in fragment.expression
        assert ">" in fragment.expression or "CAST" in fragment.expression
        assert "100" in fragment.expression
        assert "WHERE" in fragment.expression

    def test_exists_with_less_than_or_equal(self, duckdb_dialect):
        """Test exists() with less than or equal comparison"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Set up context: Observation.component.exists(value <= 50)
        translator.context.push_path("component")

        # Create condition: value <= 50
        left_node = IdentifierNode(
            node_type="identifier",
            text="value",
            identifier="value"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="50",
            value=50,
            literal_type="integer"
        )
        condition_node = OperatorNode(
            node_type="operator",
            text="<=",
            operator="<=",
            operator_type="comparison"
        )
        condition_node.children = [left_node, right_node]

        # Create exists() function call
        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists(value <= 50)",
            function_name="exists",
            arguments=[condition_node]
        )
        exists_node.children = [condition_node]

        fragment = translator._translate_exists(exists_node)

        assert isinstance(fragment, SQLFragment)
        assert "CASE WHEN EXISTS" in fragment.expression
        assert "<=" in fragment.expression or "CAST" in fragment.expression
        assert "50" in fragment.expression


class TestExistsLogicalOperators:
    """Test exists() with logical operators"""

    def test_exists_with_and_condition(self, duckdb_dialect):
        """Test exists() with AND logical operator"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.exists(use='official' and family='Smith')
        translator.context.push_path("name")

        # Create left condition: use='official'
        left_left = IdentifierNode(
            node_type="identifier",
            text="use",
            identifier="use"
        )
        left_right = LiteralNode(
            node_type="literal",
            text="'official'",
            value="official",
            literal_type="string"
        )
        left_condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        left_condition.children = [left_left, left_right]

        # Create right condition: family='Smith'
        right_left = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )
        right_right = LiteralNode(
            node_type="literal",
            text="'Smith'",
            value="Smith",
            literal_type="string"
        )
        right_condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        right_condition.children = [right_left, right_right]

        # Create AND condition
        and_condition = OperatorNode(
            node_type="operator",
            text="and",
            operator="and",
            operator_type="logical"
        )
        and_condition.children = [left_condition, right_condition]

        # Create exists() function call
        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists(use='official' and family='Smith')",
            function_name="exists",
            arguments=[and_condition]
        )
        exists_node.children = [and_condition]

        fragment = translator._translate_exists(exists_node)

        assert isinstance(fragment, SQLFragment)
        assert "CASE WHEN EXISTS" in fragment.expression
        assert "AND" in fragment.expression
        assert "'official'" in fragment.expression
        assert "'Smith'" in fragment.expression


class TestExistsContextManagement:
    """Test exists() context preservation"""

    def test_exists_preserves_context(self, duckdb_dialect):
        """Test that exists() preserves translation context"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context
        translator.context.push_path("name")
        original_table = translator.context.current_table
        original_path = translator.context.parent_path.copy()

        # Create exists() with condition
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

        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists(use='official')",
            function_name="exists",
            arguments=[condition_node]
        )
        exists_node.children = [condition_node]

        # Translate exists()
        fragment = translator._translate_exists(exists_node)

        # Verify context is preserved (not modified by exists())
        assert translator.context.current_table == original_table
        assert translator.context.parent_path == original_path


class TestExistsErrorHandling:
    """Test exists() error handling"""

    def test_exists_with_too_many_arguments(self, duckdb_dialect):
        """Test exists() raises error with more than 1 argument"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        translator.context.push_path("name")

        # Create exists() with 2 arguments (invalid)
        arg1 = LiteralNode(
            node_type="literal",
            text="'official'",
            value="official",
            literal_type="string"
        )
        arg2 = LiteralNode(
            node_type="literal",
            text="'Smith'",
            value="Smith",
            literal_type="string"
        )

        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists('official', 'Smith')",
            function_name="exists",
            arguments=[arg1, arg2]
        )
        exists_node.children = [arg1, arg2]

        with pytest.raises(ValueError) as excinfo:
            translator._translate_exists(exists_node)

        assert "requires 0 or 1 arguments" in str(excinfo.value)


class TestExistsPopulationFriendly:
    """Test exists() generates population-friendly SQL"""

    def test_exists_no_limit_clause(self, duckdb_dialect):
        """Test exists() does not use LIMIT 1 (population-friendly)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        translator.context.push_path("name")

        # Test without criteria
        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists()",
            function_name="exists",
            arguments=[]
        )
        exists_node.children = []

        fragment = translator._translate_exists(exists_node)

        # Verify no LIMIT clause
        assert "LIMIT" not in fragment.expression.upper()

    def test_exists_with_criteria_no_limit_clause(self, duckdb_dialect):
        """Test exists() with criteria does not use LIMIT 1"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        translator.context.push_path("name")

        # Create condition
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

        exists_node = FunctionCallNode(
            node_type="functionCall",
            text="exists(use='official')",
            function_name="exists",
            arguments=[condition_node]
        )
        exists_node.children = [condition_node]

        fragment = translator._translate_exists(exists_node)

        # Verify no LIMIT clause
        assert "LIMIT" not in fragment.expression.upper()


class TestExistsDialectConsistency:
    """Test exists() produces consistent logic across dialects"""

    def test_exists_without_criteria_both_dialects(self, duckdb_dialect, postgresql_dialect):
        """Test exists() without criteria is consistent across dialects"""
        # DuckDB
        translator_duck = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator_duck.context.push_path("name")

        exists_node_duck = FunctionCallNode(
            node_type="functionCall",
            text="exists()",
            function_name="exists",
            arguments=[]
        )
        exists_node_duck.children = []

        fragment_duck = translator_duck._translate_exists(exists_node_duck)

        # PostgreSQL
        translator_pg = ASTToSQLTranslator(postgresql_dialect, "Patient")
        translator_pg.context.push_path("name")

        exists_node_pg = FunctionCallNode(
            node_type="functionCall",
            text="exists()",
            function_name="exists",
            arguments=[]
        )
        exists_node_pg.children = []

        fragment_pg = translator_pg._translate_exists(exists_node_pg)

        # Both should have same structure (CASE WHEN ... IS NOT NULL ...)
        assert "CASE WHEN" in fragment_duck.expression
        assert "CASE WHEN" in fragment_pg.expression
        assert "IS NOT NULL" in fragment_duck.expression
        assert "IS NOT NULL" in fragment_pg.expression
        assert "THEN TRUE" in fragment_duck.expression
        assert "THEN TRUE" in fragment_pg.expression
        assert "ELSE FALSE" in fragment_duck.expression
        assert "ELSE FALSE" in fragment_pg.expression

    def test_exists_with_criteria_both_dialects(self, duckdb_dialect, postgresql_dialect):
        """Test exists() with criteria is consistent across dialects"""
        # DuckDB
        translator_duck = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator_duck.context.push_path("name")

        # Create condition
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

        exists_node_duck = FunctionCallNode(
            node_type="functionCall",
            text="exists(use='official')",
            function_name="exists",
            arguments=[condition_node]
        )
        exists_node_duck.children = [condition_node]

        fragment_duck = translator_duck._translate_exists(exists_node_duck)

        # PostgreSQL
        translator_pg = ASTToSQLTranslator(postgresql_dialect, "Patient")
        translator_pg.context.push_path("name")

        # Create same condition
        left_node2 = IdentifierNode(
            node_type="identifier",
            text="use",
            identifier="use"
        )
        right_node2 = LiteralNode(
            node_type="literal",
            text="'official'",
            value="official",
            literal_type="string"
        )
        condition_node2 = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition_node2.children = [left_node2, right_node2]

        exists_node_pg = FunctionCallNode(
            node_type="functionCall",
            text="exists(use='official')",
            function_name="exists",
            arguments=[condition_node2]
        )
        exists_node_pg.children = [condition_node2]

        fragment_pg = translator_pg._translate_exists(exists_node_pg)

        # Both should have same structure (CASE WHEN EXISTS ... SELECT 1 ...)
        assert "CASE WHEN EXISTS" in fragment_duck.expression
        assert "CASE WHEN EXISTS" in fragment_pg.expression
        assert "SELECT 1" in fragment_duck.expression
        assert "SELECT 1" in fragment_pg.expression
        assert "WHERE" in fragment_duck.expression
        assert "WHERE" in fragment_pg.expression
        assert "'official'" in fragment_duck.expression
        assert "'official'" in fragment_pg.expression
        assert "THEN TRUE" in fragment_duck.expression
        assert "THEN TRUE" in fragment_pg.expression
