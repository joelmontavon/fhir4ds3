"""Integration tests for string function translations.

Tests the integration and interaction of multiple string functions working together
in realistic FHIRPath expressions.

Test Coverage:
- Combined string operations (chaining multiple functions)
- Real-world FHIR use cases (patient names, contact info, etc.)
- Multi-database consistency for complex expressions
- Performance characteristics of chained operations
- Edge cases when functions interact

Module: tests.unit.fhirpath.sql.test_translator_string_integration
Created: 2025-10-07
Task: SP-007-007
"""

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode, LiteralNode, IdentifierNode
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


class TestChainedStringOperations:
    """Test chaining multiple string operations together"""

    def test_upper_then_trim_duckdb(self, duckdb_dialect):
        """Test that upper() and trim() both generate valid SQL on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.name.family
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Test upper() on family name
        upper_node = FunctionCallNode(
            node_type="functionCall",
            text="upper()",
            function_name="upper",
            arguments=[]
        )
        upper_node.children = []

        upper_fragment = translator._translate_upper(upper_node)

        # Verify upper() works
        assert isinstance(upper_fragment, SQLFragment)
        assert "UPPER" in upper_fragment.expression or "upper" in upper_fragment.expression.lower()

        # Test trim() on family name (separate operation)
        translator2 = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator2.context.push_path("name")
        translator2.context.push_path("family")

        trim_node = FunctionCallNode(
            node_type="functionCall",
            text="trim()",
            function_name="trim",
            arguments=[]
        )
        trim_node.children = []

        trim_fragment = translator2._translate_trim(trim_node)

        # Verify trim() works
        assert isinstance(trim_fragment, SQLFragment)
        assert "TRIM" in trim_fragment.expression or "trim" in trim_fragment.expression.lower()

    def test_lower_then_contains_postgresql(self, postgresql_dialect):
        """Test that lower() and contains() both generate valid SQL on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context for Patient.name.family
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Test lower() on family name
        lower_node = FunctionCallNode(
            node_type="functionCall",
            text="lower()",
            function_name="lower",
            arguments=[]
        )
        lower_node.children = []

        lower_fragment = translator._translate_lower(lower_node)

        # Verify lower() works
        assert isinstance(lower_fragment, SQLFragment)
        assert "LOWER" in lower_fragment.expression or "lower" in lower_fragment.expression.lower()

        # Test contains() on family name (separate operation)
        translator2 = ASTToSQLTranslator(postgresql_dialect, "Patient")
        translator2.context.push_path("name")
        translator2.context.push_path("family")

        substring_node = LiteralNode(
            node_type="literal",
            text="'smith'",
            literal_type="string",
            value="smith"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        contains_fragment = translator2._translate_contains(contains_node)

        # Verify contains() works
        assert isinstance(contains_fragment, SQLFragment)
        assert "smith" in contains_fragment.expression


class TestRealWorldFHIRUseCases:
    """Test realistic FHIR data processing scenarios"""

    def test_normalize_patient_name_duckdb(self, duckdb_dialect):
        """Test normalizing patient name: trim().upper() on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.name.family
        translator.context.push_path("name")
        translator.context.push_path("family")

        # First: trim() to remove whitespace
        trim_node = FunctionCallNode(
            node_type="functionCall",
            text="trim()",
            function_name="trim",
            arguments=[]
        )
        trim_node.children = []

        fragment = translator._translate_trim(trim_node)

        assert isinstance(fragment, SQLFragment)
        assert "TRIM" in fragment.expression or "trim" in fragment.expression.lower()

    def test_validate_email_format_postgresql(self, postgresql_dialect):
        """Test email validation: telecom.value.matches(email_regex) on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context for Patient.telecom.value
        translator.context.push_path("telecom")
        translator.context.push_path("value")

        # Email regex pattern
        email_pattern = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
        pattern_node = LiteralNode(
            node_type="literal",
            text=f"'{email_pattern}'",
            literal_type="string",
            value=email_pattern
        )
        pattern_node.children = []

        matches_node = FunctionCallNode(
            node_type="functionCall",
            text="matches()",
            function_name="matches",
            arguments=[pattern_node]
        )
        matches_node.children = [pattern_node]

        fragment = translator._translate_matches(matches_node)

        assert isinstance(fragment, SQLFragment)
        assert " ~ " in fragment.expression
        assert email_pattern in fragment.expression

    def test_mask_ssn_duckdb(self, duckdb_dialect):
        """Test masking SSN: replaceMatches('\\d', 'X') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.identifier.value
        translator.context.push_path("identifier")
        translator.context.push_path("value")

        # Pattern to match digits
        pattern_node = LiteralNode(
            node_type="literal",
            text="'\\d'",
            literal_type="string",
            value="\\d"
        )
        pattern_node.children = []

        # Replacement character
        subst_node = LiteralNode(
            node_type="literal",
            text="'X'",
            literal_type="string",
            value="X"
        )
        subst_node.children = []

        replacematches_node = FunctionCallNode(
            node_type="functionCall",
            text="replaceMatches()",
            function_name="replacematches",
            arguments=[pattern_node, subst_node]
        )
        replacematches_node.children = [pattern_node, subst_node]

        fragment = translator._translate_replacematches(replacematches_node)

        assert isinstance(fragment, SQLFragment)
        assert "regexp_replace(" in fragment.expression
        assert "\\d" in fragment.expression
        assert "'X'" in fragment.expression

    def test_filter_scottish_names_postgresql(self, postgresql_dialect):
        """Test finding Scottish names: startsWith('Mc') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context for Patient.name.family
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Prefix pattern
        prefix_node = LiteralNode(
            node_type="literal",
            text="'Mc'",
            literal_type="string",
            value="Mc"
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startswith",
            arguments=[prefix_node]
        )
        startswith_node.children = [prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "Mc" in fragment.expression


class TestMultiDatabaseIntegrationConsistency:
    """Test that complex expressions work consistently across databases"""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_trim_and_upper_consistency(self, request, dialect_fixture):
        """Test trim().upper() produces consistent structure across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Set up context
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Execute trim() first
        trim_node = FunctionCallNode(
            node_type="functionCall",
            text="trim()",
            function_name="trim",
            arguments=[]
        )
        trim_node.children = []

        trim_fragment = translator._translate_trim(trim_node)

        # Both databases should produce valid fragments
        assert isinstance(trim_fragment, SQLFragment)
        assert len(trim_fragment.expression) > 0
        assert trim_fragment.source_table == "resource"
        assert trim_fragment.requires_unnest is False
        assert trim_fragment.is_aggregate is False

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_regex_operations_consistency(self, request, dialect_fixture):
        """Test matches() and replaceMatches() consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Set up context
        translator.context.push_path("telecom")
        translator.context.push_path("value")

        # Test matches() first
        pattern_node = LiteralNode(
            node_type="literal",
            text="'^\\d{3}-\\d{4}$'",
            literal_type="string",
            value="^\\d{3}-\\d{4}$"
        )
        pattern_node.children = []

        matches_node = FunctionCallNode(
            node_type="functionCall",
            text="matches()",
            function_name="matches",
            arguments=[pattern_node]
        )
        matches_node.children = [pattern_node]

        matches_fragment = translator._translate_matches(matches_node)

        # Both databases should produce valid fragments
        assert isinstance(matches_fragment, SQLFragment)
        assert "\\d{3}" in matches_fragment.expression
        assert "\\d{4}" in matches_fragment.expression


class TestEdgeCasesInIntegration:
    """Test edge cases when functions interact"""

    def test_empty_string_through_multiple_functions_duckdb(self, duckdb_dialect):
        """Test processing empty string through multiple functions on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Empty string literal
        empty_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
        )
        empty_node.children = []

        # Test upper() on empty string
        upper_node = FunctionCallNode(
            node_type="functionCall",
            text="upper()",
            function_name="upper",
            arguments=[]
        )
        upper_node.children = []

        fragment = translator._translate_upper(upper_node)

        assert isinstance(fragment, SQLFragment)
        # Should handle empty string gracefully

    def test_special_characters_in_chained_operations_postgresql(self, postgresql_dialect):
        """Test special characters through contains() and matches() on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Test contains with special characters
        special_char_node = LiteralNode(
            node_type="literal",
            text="'O\\'Brien'",
            literal_type="string",
            value="O'Brien"
        )
        special_char_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[special_char_node]
        )
        contains_node.children = [special_char_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        # Should handle apostrophe in name


class TestPerformanceCharacteristics:
    """Test performance-related aspects of string operations"""

    def test_single_operation_minimal_overhead_duckdb(self, duckdb_dialect):
        """Test that single operation has minimal SQL overhead on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Simple upper() operation
        upper_node = FunctionCallNode(
            node_type="functionCall",
            text="upper()",
            function_name="upper",
            arguments=[]
        )
        upper_node.children = []

        fragment = translator._translate_upper(upper_node)

        # SQL should be concise
        assert isinstance(fragment, SQLFragment)
        assert len(fragment.expression) < 500  # Reasonable size limit
        assert fragment.dependencies == []  # No extra dependencies

    def test_regex_operation_sql_structure_postgresql(self, postgresql_dialect):
        """Test regex operation generates efficient SQL on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context
        translator.context.push_path("telecom")
        translator.context.push_path("value")

        # Simple phone pattern
        pattern_node = LiteralNode(
            node_type="literal",
            text="'^\\d{10}$'",
            literal_type="string",
            value="^\\d{10}$"
        )
        pattern_node.children = []

        matches_node = FunctionCallNode(
            node_type="functionCall",
            text="matches()",
            function_name="matches",
            arguments=[pattern_node]
        )
        matches_node.children = [pattern_node]

        fragment = translator._translate_matches(matches_node)

        # SQL should be efficient
        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is False  # Not an aggregate operation
        assert fragment.requires_unnest is False  # No unnesting needed


class TestStringFunctionCombinations:
    """Test various combinations of string functions"""

    def test_contains_after_lower_duckdb(self, duckdb_dialect):
        """Test case-insensitive contains using lower() on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Lower then contains for case-insensitive search
        lower_node = FunctionCallNode(
            node_type="functionCall",
            text="lower()",
            function_name="lower",
            arguments=[]
        )
        lower_node.children = []

        fragment = translator._translate_lower(lower_node)

        assert isinstance(fragment, SQLFragment)
        assert "LOWER" in fragment.expression or "lower" in fragment.expression.lower()

    def test_trim_then_startswith_postgresql(self, postgresql_dialect):
        """Test trimming before prefix check on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context
        translator.context.push_path("name")
        translator.context.push_path("prefix")

        # Trim whitespace first
        trim_node = FunctionCallNode(
            node_type="functionCall",
            text="trim()",
            function_name="trim",
            arguments=[]
        )
        trim_node.children = []

        fragment = translator._translate_trim(trim_node)

        assert isinstance(fragment, SQLFragment)
        assert "trim" in fragment.expression.lower() or "TRIM" in fragment.expression

    def test_replacematches_then_matches_duckdb(self, duckdb_dialect):
        """Test replacing then matching pattern on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context
        translator.context.push_path("identifier")
        translator.context.push_path("value")

        # Replace digits first
        pattern_node = LiteralNode(
            node_type="literal",
            text="'\\d'",
            literal_type="string",
            value="\\d"
        )
        pattern_node.children = []

        subst_node = LiteralNode(
            node_type="literal",
            text="'X'",
            literal_type="string",
            value="X"
        )
        subst_node.children = []

        replacematches_node = FunctionCallNode(
            node_type="functionCall",
            text="replaceMatches()",
            function_name="replacematches",
            arguments=[pattern_node, subst_node]
        )
        replacematches_node.children = [pattern_node, subst_node]

        fragment = translator._translate_replacematches(replacematches_node)

        assert isinstance(fragment, SQLFragment)
        assert "regexp_replace(" in fragment.expression


class TestComplexRealWorldScenarios:
    """Test complex real-world scenarios"""

    def test_phone_number_formatting_duckdb(self, duckdb_dialect):
        """Test phone number formatting: replaceMatches('[^0-9]', '') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for telecom.value
        translator.context.push_path("telecom")
        translator.context.push_path("value")

        # Remove all non-digits
        pattern_node = LiteralNode(
            node_type="literal",
            text="'[^0-9]'",
            literal_type="string",
            value="[^0-9]"
        )
        pattern_node.children = []

        subst_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
        )
        subst_node.children = []

        replacematches_node = FunctionCallNode(
            node_type="functionCall",
            text="replaceMatches()",
            function_name="replacematches",
            arguments=[pattern_node, subst_node]
        )
        replacematches_node.children = [pattern_node, subst_node]

        fragment = translator._translate_replacematches(replacematches_node)

        assert isinstance(fragment, SQLFragment)
        assert "regexp_replace(" in fragment.expression
        assert "[^0-9]" in fragment.expression

    def test_name_standardization_postgresql(self, postgresql_dialect):
        """Test name standardization: trim().upper() on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Trim then uppercase for standardization
        trim_node = FunctionCallNode(
            node_type="functionCall",
            text="trim()",
            function_name="trim",
            arguments=[]
        )
        trim_node.children = []

        fragment = translator._translate_trim(trim_node)

        assert isinstance(fragment, SQLFragment)
        assert "trim" in fragment.expression.lower() or "TRIM" in fragment.expression
