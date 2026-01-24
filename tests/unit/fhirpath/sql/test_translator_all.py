"""Unit tests for ASTToSQLTranslator all() function translation.

Tests the _translate_all() method implementation for universal quantification
SQL generation. Validates correctness across both DuckDB and PostgreSQL dialects.

Test Coverage:
- all() on various collection types with different criteria
- Dialect-specific SQL syntax generation (DuckDB vs PostgreSQL)
- Error handling for invalid arguments (all() requires 1 argument)
- Context preservation (no side effects on translation state)
- Population-friendly SQL patterns (bool_and aggregation)
- Vacuous truth handling (empty collections return true)

Module: tests.unit.fhirpath.sql.test_translator_all
Created: 2025-10-03
Task: SP-006-011
"""

import pytest
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import FunctionCallNode, LiteralNode, OperatorNode, IdentifierNode


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


class TestAllBasicTranslation:
    """Test basic all() function translation"""

    def test_all_with_simple_criteria_duckdb(self, duckdb_dialect):
        """Test all() on Patient.name collection with simple criteria with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.all(use = 'official')
        translator.context.push_path("name")

        # Create criteria: use = 'official'
        use_identifier = IdentifierNode(
            node_type="identifier",
            text="use",
            identifier="use"
        )
        use_identifier.children = []

        official_literal = LiteralNode(
            node_type="literal",
            text="'official'",
            literal_type="string",
            value="official"
        )
        official_literal.children = []

        criteria_operator = OperatorNode(
            node_type="operator",
            text="=",
            operator="="
        )
        criteria_operator.children = [use_identifier, official_literal]

        # Create all() function call
        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(use = 'official')",
            function_name="all",
            arguments=[criteria_operator]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "bool_and" in fragment.expression.lower()
        assert "COALESCE" in fragment.expression
        assert "$.name" in fragment.expression
        assert "true" in fragment.expression.lower()

    def test_all_with_simple_criteria_postgresql(self, postgresql_dialect):
        """Test all() on Patient.name collection with simple criteria with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.name.all(use = 'official')
        translator.context.push_path("name")

        # Create criteria: use = 'official'
        use_identifier = IdentifierNode(
            node_type="identifier",
            text="use",
            identifier="use"
        )
        use_identifier.children = []

        official_literal = LiteralNode(
            node_type="literal",
            text="'official'",
            literal_type="string",
            value="official"
        )
        official_literal.children = []

        criteria_operator = OperatorNode(
            node_type="operator",
            text="=",
            operator="="
        )
        criteria_operator.children = [use_identifier, official_literal]

        # Create all() function call
        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(use = 'official')",
            function_name="all",
            arguments=[criteria_operator]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "bool_and" in fragment.expression.lower()
        assert "COALESCE" in fragment.expression
        assert "name" in fragment.expression
        assert "jsonb_array_elements" in fragment.expression
        assert "true" in fragment.expression.lower()

    def test_all_on_telecom_collection_duckdb(self, duckdb_dialect):
        """Test all() on Patient.telecom collection with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.telecom.all(system = 'phone')
        translator.context.push_path("telecom")

        # Create criteria: system = 'phone'
        system_identifier = IdentifierNode(
            node_type="identifier",
            text="system",
            identifier="system"
        )
        system_identifier.children = []

        phone_literal = LiteralNode(
            node_type="literal",
            text="'phone'",
            literal_type="string",
            value="phone"
        )
        phone_literal.children = []

        criteria_operator = OperatorNode(
            node_type="operator",
            text="=",
            operator="="
        )
        criteria_operator.children = [system_identifier, phone_literal]

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(system = 'phone')",
            function_name="all",
            arguments=[criteria_operator]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        assert isinstance(fragment, SQLFragment)
        assert "bool_and" in fragment.expression.lower()
        assert "$.telecom" in fragment.expression
        assert "COALESCE" in fragment.expression


class TestAllErrorHandling:
    """Test error handling for all() function"""

    def test_all_with_no_arguments_raises_error(self, duckdb_dialect):
        """Test that all() with no arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        # Create all() with no arguments (invalid)
        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all()",
            function_name="all",
            arguments=[]
        )
        all_node.children = []

        with pytest.raises(ValueError, match="all\\(\\) function requires exactly 1 argument"):
            translator._translate_all(all_node)

    def test_all_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Test that all() with multiple arguments raises ValueError"""
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

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all()",
            function_name="all",
            arguments=[literal1, literal2]
        )
        all_node.children = []

        with pytest.raises(ValueError, match="all\\(\\) function requires exactly 1 argument"):
            translator._translate_all(all_node)


class TestAllContextPreservation:
    """Test that all() preserves translation context"""

    def test_all_preserves_current_table(self, duckdb_dialect):
        """Test that all() does not modify current_table"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        original_table = translator.context.current_table

        # Simple criteria
        literal = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal.children = []

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal]
        )
        all_node.children = []

        translator._translate_all(all_node)

        assert translator.context.current_table == original_table

    def test_all_preserves_parent_path(self, duckdb_dialect):
        """Test that all() does not modify parent_path"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("telecom")
        translator.context.push_path("system")

        original_path = translator.context.parent_path.copy()

        # Simple criteria
        literal = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal.children = []

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal]
        )
        all_node.children = []

        translator._translate_all(all_node)

        assert translator.context.parent_path == original_path


class TestAllDialectConsistency:
    """Test that all() generates consistent logic across dialects"""

    def test_all_logic_consistency_duckdb_vs_postgresql(self, duckdb_dialect, postgresql_dialect):
        """Test that DuckDB and PostgreSQL generate equivalent all() check logic"""
        # DuckDB translation
        duckdb_translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        duckdb_translator.context.push_path("name")

        # Create criteria
        literal_duckdb = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal_duckdb.children = []

        all_node_duckdb = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal_duckdb]
        )
        all_node_duckdb.children = []

        duckdb_fragment = duckdb_translator._translate_all(all_node_duckdb)

        # PostgreSQL translation
        postgresql_translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        postgresql_translator.context.push_path("name")

        literal_postgresql = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal_postgresql.children = []

        all_node_postgresql = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal_postgresql]
        )
        all_node_postgresql.children = []

        postgresql_fragment = postgresql_translator._translate_all(all_node_postgresql)

        # Both should use bool_and
        assert "bool_and" in duckdb_fragment.expression.lower()
        assert "bool_and" in postgresql_fragment.expression.lower()

        # Both should use COALESCE for empty array handling
        assert "COALESCE" in duckdb_fragment.expression
        assert "COALESCE" in postgresql_fragment.expression

        # Both should have consistent fragment properties
        assert duckdb_fragment.requires_unnest == postgresql_fragment.requires_unnest
        assert duckdb_fragment.is_aggregate == postgresql_fragment.is_aggregate


class TestAllPopulationScale:
    """Test that all() generates population-friendly SQL"""

    def test_all_avoids_limit_patterns(self, duckdb_dialect):
        """Test that all() does not use LIMIT (anti-pattern)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        literal = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal.children = []

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        # Should not contain LIMIT (anti-pattern for population queries)
        assert "LIMIT" not in fragment.expression.upper()

    def test_all_uses_bool_and_aggregation(self, duckdb_dialect):
        """Test that all() uses bool_and for population-scale checks"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        literal = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal.children = []

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        # Should use bool_and (population-friendly aggregation)
        assert "bool_and" in fragment.expression.lower()


class TestAllFragmentProperties:
    """Test SQLFragment properties for all() function"""

    def test_all_fragment_no_unnest_required(self, duckdb_dialect):
        """Test that all() fragment does not require unnesting (handled internally)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        literal = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal.children = []

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        assert fragment.requires_unnest is False

    def test_all_fragment_not_aggregate(self, duckdb_dialect):
        """Test that all() fragment is not marked as aggregate (returns boolean)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        literal = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal.children = []

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        assert fragment.is_aggregate is False

    def test_all_fragment_no_dependencies(self, duckdb_dialect):
        """Test that all() fragment has no dependencies"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        literal = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal.children = []

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        assert fragment.dependencies == []

    def test_all_fragment_source_table(self, duckdb_dialect):
        """Test that all() fragment preserves source table"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        literal = LiteralNode(
            node_type="literal",
            text="true",
            literal_type="boolean",
            value=True
        )
        literal.children = []

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(true)",
            function_name="all",
            arguments=[literal]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        assert fragment.source_table == translator.context.current_table


class TestAllVacuousTruth:
    """Test that all() handles empty collections correctly (vacuous truth)"""

    def test_all_coalesce_handles_empty_arrays(self, duckdb_dialect):
        """Test that all() uses COALESCE to return true for empty arrays"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        literal = LiteralNode(
            node_type="literal",
            text="false",
            literal_type="boolean",
            value=False
        )
        literal.children = []

        all_node = FunctionCallNode(
            node_type="functionCall",
            text="all(false)",
            function_name="all",
            arguments=[literal]
        )
        all_node.children = []

        fragment = translator._translate_all(all_node)

        # Should use COALESCE(..., true) pattern
        assert "COALESCE" in fragment.expression
        assert "true" in fragment.expression.lower()
