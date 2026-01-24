"""Unit tests for ASTToSQLTranslator empty() function translation.

Tests the _translate_empty() method implementation for empty collection checking
SQL generation. Validates correctness across both DuckDB and PostgreSQL dialects.

Test Coverage:
- empty() on various collection types (name, telecom, address, etc.)
- Dialect-specific SQL syntax generation (DuckDB vs PostgreSQL)
- Error handling for invalid arguments (empty() takes no arguments)
- Context preservation (no side effects on translation state)
- Population-friendly SQL patterns (json_array_length checks)

Module: tests.unit.fhirpath.sql.test_translator_empty
Created: 2025-10-03
Task: SP-006-010
"""

import pytest
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import FunctionCallNode, LiteralNode


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


class TestEmptyBasicTranslation:
    """Test basic empty() function translation"""

    def test_empty_on_name_collection_duckdb(self, duckdb_dialect):
        """Test empty() on Patient.name collection with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.empty()
        translator.context.push_path("name")

        # Create empty() function call with no arguments
        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "json_array_length" in fragment.expression
        assert "$.name" in fragment.expression
        assert "= 0" in fragment.expression

    def test_empty_on_name_collection_postgresql(self, postgresql_dialect):
        """Test empty() on Patient.name collection with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.name.empty()
        translator.context.push_path("name")

        # Create empty() function call with no arguments
        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "jsonb_array_length" in fragment.expression
        assert "name" in fragment.expression
        assert "= 0" in fragment.expression

    def test_empty_on_telecom_collection_duckdb(self, duckdb_dialect):
        """Test empty() on Patient.telecom collection with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.telecom.empty()
        translator.context.push_path("telecom")

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        assert isinstance(fragment, SQLFragment)
        assert "json_array_length" in fragment.expression
        assert "$.telecom" in fragment.expression
        assert "= 0" in fragment.expression

    def test_empty_on_address_collection_postgresql(self, postgresql_dialect):
        """Test empty() on Patient.address collection with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.address.empty()
        translator.context.push_path("address")

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        assert isinstance(fragment, SQLFragment)
        assert "jsonb_array_length" in fragment.expression
        assert "address" in fragment.expression
        assert "= 0" in fragment.expression


class TestEmptyErrorHandling:
    """Test error handling for empty() function"""

    def test_empty_with_arguments_raises_error(self, duckdb_dialect):
        """Test that empty() with arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create empty() with an argument (invalid)
        literal_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        literal_node.children = []

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[literal_node]
        )
        empty_node.children = []

        with pytest.raises(ValueError, match="empty\\(\\) function requires 0 arguments"):
            translator._translate_empty(empty_node)

    def test_empty_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Test that empty() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create two literal nodes
        literal1 = LiteralNode(
            node_type="literal",
            text="'test1'",
            literal_type="string",
            value="test1"
        )
        literal1.children = []

        literal2 = LiteralNode(
            node_type="literal",
            text="'test2'",
            literal_type="string",
            value="test2"
        )
        literal2.children = []

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[literal1, literal2]
        )
        empty_node.children = []

        with pytest.raises(ValueError, match="empty\\(\\) function requires 0 arguments"):
            translator._translate_empty(empty_node)


class TestEmptyContextPreservation:
    """Test that empty() preserves translation context"""

    def test_empty_preserves_current_table(self, duckdb_dialect):
        """Test that empty() does not modify current_table"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        original_table = translator.context.current_table

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        translator._translate_empty(empty_node)

        assert translator.context.current_table == original_table

    def test_empty_preserves_parent_path(self, duckdb_dialect):
        """Test that empty() does not modify parent_path"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("telecom")
        translator.context.push_path("system")

        original_path = translator.context.parent_path.copy()

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        translator._translate_empty(empty_node)

        assert translator.context.parent_path == original_path


class TestEmptyDialectConsistency:
    """Test that empty() generates consistent logic across dialects"""

    def test_empty_logic_consistency_duckdb_vs_postgresql(self, duckdb_dialect, postgresql_dialect):
        """Test that DuckDB and PostgreSQL generate equivalent empty check logic"""
        # DuckDB translation
        duckdb_translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        duckdb_translator.context.push_path("name")

        empty_node_duckdb = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node_duckdb.children = []

        duckdb_fragment = duckdb_translator._translate_empty(empty_node_duckdb)

        # PostgreSQL translation
        postgresql_translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        postgresql_translator.context.push_path("name")

        empty_node_postgresql = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node_postgresql.children = []

        postgresql_fragment = postgresql_translator._translate_empty(empty_node_postgresql)

        # Both should check array length = 0
        assert "= 0" in duckdb_fragment.expression
        assert "= 0" in postgresql_fragment.expression

        # Both should have consistent fragment properties
        assert duckdb_fragment.requires_unnest == postgresql_fragment.requires_unnest
        assert duckdb_fragment.is_aggregate == postgresql_fragment.is_aggregate


class TestEmptyPopulationScale:
    """Test that empty() generates population-friendly SQL"""

    def test_empty_avoids_limit_patterns(self, duckdb_dialect):
        """Test that empty() does not use LIMIT (anti-pattern)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        # Should not contain LIMIT (anti-pattern for population queries)
        assert "LIMIT" not in fragment.expression.upper()

    def test_empty_uses_json_array_length(self, duckdb_dialect):
        """Test that empty() uses json_array_length for population-scale checks"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        # Should use json_array_length (population-friendly)
        assert "json_array_length" in fragment.expression


class TestEmptyFragmentProperties:
    """Test SQLFragment properties for empty() function"""

    def test_empty_fragment_no_unnest_required(self, duckdb_dialect):
        """Test that empty() fragment does not require unnesting"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        assert fragment.requires_unnest is False

    def test_empty_fragment_not_aggregate(self, duckdb_dialect):
        """Test that empty() fragment is not an aggregate"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        assert fragment.is_aggregate is False

    def test_empty_fragment_no_dependencies(self, duckdb_dialect):
        """Test that empty() fragment has no dependencies"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        assert fragment.dependencies == []

    def test_empty_fragment_source_table(self, duckdb_dialect):
        """Test that empty() fragment preserves source table"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        empty_node = FunctionCallNode(
            node_type="functionCall",
            text="empty()",
            function_name="empty",
            arguments=[]
        )
        empty_node.children = []

        fragment = translator._translate_empty(empty_node)

        assert fragment.source_table == translator.context.current_table
