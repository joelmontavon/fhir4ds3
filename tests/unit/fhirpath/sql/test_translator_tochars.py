"""Unit tests for ASTToSQLTranslator toChars() function translation.

Tests the _translate_tochars() method implementation for converting strings
into arrays of single-character strings.

Test Coverage:
- toChars() for character array conversion
- Multi-database consistency (DuckDB and PostgreSQL)
- Error handling for invalid arguments
- Proper SQL generation through dialect methods
- Edge cases (empty strings, NULL handling, etc.)

Module: tests.unit.fhirpath.sql.test_translator_tochars
Created: 2025-10-07
Task: SP-007-006
"""

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode, LiteralNode
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


class TestToCharsBasicTranslation:
    """Test basic toChars() function translation"""

    def test_tochars_simple_duckdb(self, duckdb_dialect):
        """Test 'hello'.toChars() on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Method call: string.toChars() - takes no arguments
        tochars_node = FunctionCallNode(
            node_type="functionCall",
            text="toChars()",
            function_name="toChars",
            arguments=[]
        )
        tochars_node.children = []

        fragment = translator._translate_tochars(tochars_node)

        assert isinstance(fragment, SQLFragment)
        assert "CASE WHEN length(" in fragment.expression
        assert "regexp_split_to_array(" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_tochars_simple_postgresql(self, postgresql_dialect):
        """Test 'hello'.toChars() on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        tochars_node = FunctionCallNode(
            node_type="functionCall",
            text="toChars()",
            function_name="toChars",
            arguments=[]
        )
        tochars_node.children = []

        fragment = translator._translate_tochars(tochars_node)

        assert isinstance(fragment, SQLFragment)
        assert "CASE WHEN length(" in fragment.expression
        assert "ARRAY[]::text[]" in fragment.expression
        assert "regexp_split_to_array(" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False


class TestToCharsEdgeCases:
    """Test toChars() edge cases"""

    def test_tochars_empty_string_handling(self, duckdb_dialect):
        """Test toChars() correctly handles empty strings"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        tochars_node = FunctionCallNode(
            node_type="functionCall",
            text="toChars()",
            function_name="toChars",
            arguments=[]
        )
        tochars_node.children = []

        fragment = translator._translate_tochars(tochars_node)

        # Should have CASE WHEN for empty string handling
        assert "CASE WHEN length(" in fragment.expression
        assert "THEN []" in fragment.expression or "THEN ARRAY[]" in fragment.expression

    def test_tochars_returns_array(self, duckdb_dialect):
        """Test toChars() returns array type"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        tochars_node = FunctionCallNode(
            node_type="functionCall",
            text="toChars()",
            function_name="toChars",
            arguments=[]
        )
        tochars_node.children = []

        fragment = translator._translate_tochars(tochars_node)

        # Should use regexp_split_to_array which returns array
        assert "regexp_split_to_array(" in fragment.expression


class TestMultiDatabaseConsistency:
    """Test that SQL generation is consistent across databases"""

    def test_tochars_sql_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test toChars() generates functionally equivalent SQL for both databases"""
        duckdb_translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        postgresql_translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        tochars_node = FunctionCallNode(
            node_type="functionCall",
            text="toChars()",
            function_name="toChars",
            arguments=[]
        )
        tochars_node.children = []

        duckdb_fragment = duckdb_translator._translate_tochars(tochars_node)
        postgresql_fragment = postgresql_translator._translate_tochars(tochars_node)

        # Both should use CASE WHEN for empty string handling
        assert "CASE WHEN length(" in duckdb_fragment.expression
        assert "CASE WHEN length(" in postgresql_fragment.expression

        # Both should use regexp_split_to_array
        assert "regexp_split_to_array(" in duckdb_fragment.expression
        assert "regexp_split_to_array(" in postgresql_fragment.expression

        # DuckDB uses [] for empty array
        assert "THEN []" in duckdb_fragment.expression

        # PostgreSQL uses ARRAY[]::text[] for empty array
        assert "ARRAY[]::text[]" in postgresql_fragment.expression


class TestErrorHandling:
    """Test error handling for invalid inputs"""

    def test_tochars_with_arguments_raises_error(self, duckdb_dialect):
        """Test toChars() with arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # toChars() should not accept arguments
        arg_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        arg_node.children = []

        tochars_node = FunctionCallNode(
            node_type="functionCall",
            text="toChars()",
            function_name="toChars",
            arguments=[arg_node]
        )
        tochars_node.children = [arg_node]

        with pytest.raises(ValueError) as excinfo:
            translator._translate_tochars(tochars_node)
        assert "takes no arguments" in str(excinfo.value)


class TestDialectMethodCalls:
    """Test that translator correctly calls dialect methods"""

    def test_tochars_calls_generate_char_array(self, duckdb_dialect):
        """Test toChars() calls dialect.generate_char_array"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        tochars_node = FunctionCallNode(
            node_type="functionCall",
            text="toChars()",
            function_name="toChars",
            arguments=[]
        )
        tochars_node.children = []

        fragment = translator._translate_tochars(tochars_node)

        # Should call generate_char_array
        # Result should contain CASE WHEN and regexp_split_to_array
        assert "CASE WHEN length(" in fragment.expression
        assert "regexp_split_to_array(" in fragment.expression


class TestSQLFragmentProperties:
    """Test that generated SQLFragments have correct properties"""

    def test_tochars_fragment_properties(self, duckdb_dialect):
        """Test toChars() SQLFragment has correct properties"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        tochars_node = FunctionCallNode(
            node_type="functionCall",
            text="toChars()",
            function_name="toChars",
            arguments=[]
        )
        tochars_node.children = []

        fragment = translator._translate_tochars(tochars_node)

        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert fragment.source_table == "resource"
        assert fragment.dependencies == []


class TestContextHandling:
    """Test that functions correctly handle translation context"""

    def test_tochars_uses_current_context_path(self, duckdb_dialect):
        """Test toChars() uses current context path for target expression"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set context path
        translator.context.parent_path = ["name", "0", "family"]

        tochars_node = FunctionCallNode(
            node_type="functionCall",
            text="toChars()",
            function_name="toChars",
            arguments=[]
        )
        tochars_node.children = []

        fragment = translator._translate_tochars(tochars_node)

        # Should extract from the path set in context
        assert "json_extract" in fragment.expression or "jsonb" in fragment.expression
        # Should have character array conversion
        assert "regexp_split_to_array(" in fragment.expression
