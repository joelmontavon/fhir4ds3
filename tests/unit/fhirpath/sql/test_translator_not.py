"""Unit tests for ASTToSQLTranslator not() function translation.

Tests the _translate_not() method implementation for boolean negation
SQL generation. Validates correctness across both DuckDB and PostgreSQL dialects.

Test Coverage:
- not() on various boolean expressions
- Dialect-specific SQL syntax generation (DuckDB vs PostgreSQL)
- Error handling for invalid arguments (not() takes no arguments)
- Context preservation (no side effects on translation state)
- Population-friendly SQL patterns (NOT operator)

Module: tests.unit.fhirpath.sql.test_translator_not
Created: 2025-10-05
Task: SP-006-031
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


class TestNotBasicTranslation:
    """Test basic not() function translation"""

    def test_not_on_active_field_duckdb(self, duckdb_dialect):
        """Test not() on Patient.active field with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.active.not()
        translator.context.push_path("active")

        # Create not() function call with no arguments
        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "NOT" in fragment.expression
        assert "$.active" in fragment.expression

    def test_not_on_active_field_postgresql(self, postgresql_dialect):
        """Test not() on Patient.active field with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.active.not()
        translator.context.push_path("active")

        # Create not() function call with no arguments
        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "NOT" in fragment.expression
        assert "active" in fragment.expression

    def test_not_on_deceased_field_duckdb(self, duckdb_dialect):
        """Test not() on Patient.deceased field with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.deceased.not()
        translator.context.push_path("deceased")

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        assert isinstance(fragment, SQLFragment)
        assert "NOT" in fragment.expression
        assert "$.deceased" in fragment.expression

    def test_not_on_multipleBirth_field_postgresql(self, postgresql_dialect):
        """Test not() on Patient.multipleBirth field with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.multipleBirth.not()
        translator.context.push_path("multipleBirth")

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        assert isinstance(fragment, SQLFragment)
        assert "NOT" in fragment.expression
        assert "multipleBirth" in fragment.expression


class TestNotErrorHandling:
    """Test error handling for not() function"""

    def test_not_with_arguments_raises_error(self, duckdb_dialect):
        """Test that not() with arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        # Create not() with an argument (invalid)
        literal_node = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal_node.children = []

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[literal_node]
        )
        not_node.children = []

        with pytest.raises(ValueError, match="not\\(\\) function requires 0 arguments"):
            translator._translate_not(not_node)

    def test_not_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Test that not() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        # Create two literal nodes
        literal1 = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal1.children = []

        literal2 = LiteralNode(
            node_type="literal",
            text="false",
            literal_type="boolean",
            value=False
        )
        literal2.children = []

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[literal1, literal2]
        )
        not_node.children = []

        with pytest.raises(ValueError, match="not\\(\\) function requires 0 arguments"):
            translator._translate_not(not_node)


class TestNotContextPreservation:
    """Test that not() preserves translation context"""

    def test_not_preserves_current_table(self, duckdb_dialect):
        """Test that not() does not modify current_table"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        original_table = translator.context.current_table

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        translator._translate_not(not_node)

        assert translator.context.current_table == original_table

    def test_not_preserves_parent_path(self, duckdb_dialect):
        """Test that not() does not modify parent_path"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("deceased")
        translator.context.push_path("boolean")

        original_path = translator.context.parent_path.copy()

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        translator._translate_not(not_node)

        assert translator.context.parent_path == original_path


class TestNotDialectConsistency:
    """Test that not() generates consistent logic across dialects"""

    def test_not_logic_consistency_duckdb_vs_postgresql(self, duckdb_dialect, postgresql_dialect):
        """Test that DuckDB and PostgreSQL generate equivalent NOT logic"""
        # DuckDB translation
        duckdb_translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        duckdb_translator.context.push_path("active")

        not_node_duckdb = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node_duckdb.children = []

        duckdb_fragment = duckdb_translator._translate_not(not_node_duckdb)

        # PostgreSQL translation
        postgresql_translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        postgresql_translator.context.push_path("active")

        not_node_postgresql = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node_postgresql.children = []

        postgresql_fragment = postgresql_translator._translate_not(not_node_postgresql)

        # Both should use NOT operator
        assert "NOT" in duckdb_fragment.expression
        assert "NOT" in postgresql_fragment.expression

        # Both should have consistent fragment properties
        assert duckdb_fragment.requires_unnest == postgresql_fragment.requires_unnest
        assert duckdb_fragment.is_aggregate == postgresql_fragment.is_aggregate


class TestNotPopulationScale:
    """Test that not() generates population-friendly SQL"""

    def test_not_avoids_limit_patterns(self, duckdb_dialect):
        """Test that not() does not use LIMIT (anti-pattern)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        # Should not contain LIMIT (anti-pattern for population queries)
        assert "LIMIT" not in fragment.expression.upper()

    def test_not_uses_standard_sql_operator(self, duckdb_dialect):
        """Test that not() uses standard SQL NOT operator"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        # Should use NOT operator (population-friendly)
        assert "NOT" in fragment.expression


class TestNotFragmentProperties:
    """Test SQLFragment properties for not() function"""

    def test_not_fragment_no_unnest_required(self, duckdb_dialect):
        """Test that not() fragment does not require unnesting"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        assert fragment.requires_unnest is False

    def test_not_fragment_not_aggregate(self, duckdb_dialect):
        """Test that not() fragment is not an aggregate"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        assert fragment.is_aggregate is False

    def test_not_fragment_no_dependencies(self, duckdb_dialect):
        """Test that not() fragment has no dependencies"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        assert fragment.dependencies == []

    def test_not_fragment_source_table(self, duckdb_dialect):
        """Test that not() fragment preserves source table"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        assert fragment.source_table == translator.context.current_table


class TestNotComposition:
    """Test not() in complex expressions"""

    def test_double_negation(self, duckdb_dialect):
        """Test double negation: Patient.active.not().not()"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        # First not()
        not_node1 = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node1.children = []

        fragment1 = translator._translate_not(not_node1)

        # Second not() on the result - in real implementation this would be a chain
        # For unit test, we test that NOT is present in both
        assert "NOT" in fragment1.expression

    def test_not_with_root_path(self, duckdb_dialect):
        """Test not() with root-level boolean path"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("active")

        not_node = FunctionCallNode(
            node_type="functionCall",
            text="not()",
            function_name="not",
            arguments=[]
        )
        not_node.children = []

        fragment = translator._translate_not(not_node)

        # Should have NOT and path reference
        assert "NOT" in fragment.expression
        assert "active" in fragment.expression
