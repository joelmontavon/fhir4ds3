"""Unit tests for ASTToSQLTranslator matches() function translation.

Tests the _translate_matches() method implementation for regex pattern matching.

Test Coverage:
- matches() for regex pattern matching on strings
- Multi-database consistency (DuckDB and PostgreSQL)
- Error handling for invalid arguments
- Proper SQL generation through dialect methods
- Edge cases (null handling, empty strings, etc.)

Module: tests.unit.fhirpath.sql.test_translator_matches
Created: 2025-10-05
Task: SP-007-001
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


class TestMatchesBasicTranslation:
    """Test basic matches() function translation"""

    def test_matches_simple_pattern_duckdb(self, duckdb_dialect):
        """Test 'hello'.matches('hello.*') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create 'hello.*' regex pattern (explicit argument)
        pattern_node = LiteralNode(
            node_type="literal",
            text="'hello.*'",
            literal_type="string",
            value="hello.*"
        )
        pattern_node.children = []

        # Method call: 'hello world'.matches('hello.*')
        # Context: The string 'hello world' is implicit (from context)
        # Argument: The regex pattern 'hello.*' to match
        matches_node = FunctionCallNode(
            node_type="functionCall",
            text="matches()",
            function_name="matches",
            arguments=[pattern_node]
        )
        matches_node.children = [pattern_node]

        fragment = translator._translate_matches(matches_node)

        assert isinstance(fragment, SQLFragment)
        # DuckDB uses regexp_matches() function
        assert "regexp_matches(" in fragment.expression
        assert "hello.*" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_matches_simple_pattern_postgresql(self, postgresql_dialect):
        """Test 'hello'.matches('hello.*') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create 'hello.*' regex pattern (explicit argument)
        pattern_node = LiteralNode(
            node_type="literal",
            text="'hello.*'",
            literal_type="string",
            value="hello.*"
        )
        pattern_node.children = []

        # Method call: 'hello world'.matches('hello.*')
        matches_node = FunctionCallNode(
            node_type="functionCall",
            text="matches()",
            function_name="matches",
            arguments=[pattern_node]
        )
        matches_node.children = [pattern_node]

        fragment = translator._translate_matches(matches_node)

        assert isinstance(fragment, SQLFragment)
        # PostgreSQL uses ~ operator
        assert " ~ " in fragment.expression
        assert "hello.*" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_matches_digit_pattern_duckdb(self, duckdb_dialect):
        """Test '123'.matches('\\d+') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create '\\d+' digit pattern (explicit argument)
        pattern_node = LiteralNode(
            node_type="literal",
            text="'\\d+'",
            literal_type="string",
            value="\\d+"
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
        assert "regexp_matches(" in fragment.expression
        assert fragment.requires_unnest is False

    def test_matches_character_class_pattern_postgresql(self, postgresql_dialect):
        """Test 'abc'.matches('[A-Z]+') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create '[A-Z]+' uppercase pattern (explicit argument)
        pattern_node = LiteralNode(
            node_type="literal",
            text="'[A-Z]+'",
            literal_type="string",
            value="[A-Z]+"
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
        assert "[A-Z]+" in fragment.expression


class TestMatchesWithIdentifiers:
    """Test matches() with identifiers from context"""

    def test_matches_with_identifier_duckdb(self, duckdb_dialect):
        """Test Patient.name.family.matches('[A-Z][a-z]+') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.name.family (implicit context for matches)
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Create '[A-Z][a-z]+' name pattern (explicit argument)
        pattern_node = LiteralNode(
            node_type="literal",
            text="'[A-Z][a-z]+'",
            literal_type="string",
            value="[A-Z][a-z]+"
        )
        pattern_node.children = []

        # Method call: family.matches('[A-Z][a-z]+')
        # Context: Patient.name.family is the implicit string
        # Argument: '[A-Z][a-z]+' is the regex pattern
        matches_node = FunctionCallNode(
            node_type="functionCall",
            text="matches()",
            function_name="matches",
            arguments=[pattern_node]
        )
        matches_node.children = [pattern_node]

        fragment = translator._translate_matches(matches_node)

        assert isinstance(fragment, SQLFragment)
        assert "regexp_matches(" in fragment.expression
        assert "json_extract" in fragment.expression
        assert "family" in fragment.expression
        assert "[A-Z][a-z]+" in fragment.expression

    def test_matches_with_identifier_postgresql(self, postgresql_dialect):
        """Test Patient.name.family.matches('[A-Z][a-z]+') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context for Patient.name.family
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Create '[A-Z][a-z]+' name pattern
        pattern_node = LiteralNode(
            node_type="literal",
            text="'[A-Z][a-z]+'",
            literal_type="string",
            value="[A-Z][a-z]+"
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
        # PostgreSQL uses different JSON extraction
        assert "family" in fragment.expression
        assert "[A-Z][a-z]+" in fragment.expression


class TestMatchesErrorHandling:
    """Test error handling for matches() function"""

    def test_matches_with_no_arguments_raises_error(self, duckdb_dialect):
        """Test that matches() with no arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        matches_node = FunctionCallNode(
            node_type="functionCall",
            text="matches()",
            function_name="matches",
            arguments=[]
        )
        matches_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_matches(matches_node)

        assert "exactly 1 argument" in str(exc_info.value)
        assert "regex pattern" in str(exc_info.value)

    def test_matches_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Test that matches() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        pattern1 = LiteralNode(
            node_type="literal",
            text="'pattern1'",
            literal_type="string",
            value="pattern1"
        )
        pattern1.children = []

        pattern2 = LiteralNode(
            node_type="literal",
            text="'pattern2'",
            literal_type="string",
            value="pattern2"
        )
        pattern2.children = []

        matches_node = FunctionCallNode(
            node_type="functionCall",
            text="matches()",
            function_name="matches",
            arguments=[pattern1, pattern2]
        )
        matches_node.children = [pattern1, pattern2]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_matches(matches_node)

        assert "exactly 1 argument" in str(exc_info.value)


class TestMatchesMultiDatabaseConsistency:
    """Test that matches() produces consistent results across databases"""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_matches_basic_consistency(self, request, dialect_fixture):
        """Test matches() consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        pattern_node = LiteralNode(
            node_type="literal",
            text="'hello.*'",
            literal_type="string",
            value="hello.*"
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
        assert "hello.*" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_matches_with_context_consistency(self, request, dialect_fixture):
        """Test matches() with context path consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Set up context path
        translator.context.push_path("name")
        translator.context.push_path("family")

        pattern_node = LiteralNode(
            node_type="literal",
            text="'^[A-Z]'",
            literal_type="string",
            value="^[A-Z]"
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
        assert "family" in fragment.expression
        assert "^[A-Z]" in fragment.expression


class TestMatchesEdgeCases:
    """Test matches() edge cases"""

    def test_matches_with_empty_pattern_duckdb(self, duckdb_dialect):
        """Test matches() with empty regex pattern on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        pattern_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
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
        assert "regexp_matches(" in fragment.expression

    def test_matches_with_complex_pattern_postgresql(self, postgresql_dialect):
        """Test matches() with complex regex pattern on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Email pattern
        pattern_node = LiteralNode(
            node_type="literal",
            text="'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'",
            literal_type="string",
            value="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
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

    def test_matches_with_anchor_patterns_duckdb(self, duckdb_dialect):
        """Test matches() with anchor patterns (^, $) on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Anchored pattern: starts with uppercase letter
        pattern_node = LiteralNode(
            node_type="literal",
            text="'^[A-Z]'",
            literal_type="string",
            value="^[A-Z]"
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
        assert "regexp_matches(" in fragment.expression
        assert "^[A-Z]" in fragment.expression

    def test_matches_with_quantifiers_postgresql(self, postgresql_dialect):
        """Test matches() with regex quantifiers (+, *, ?, {n,m}) on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Pattern with various quantifiers
        pattern_node = LiteralNode(
            node_type="literal",
            text="'[0-9]{3,5}'",
            literal_type="string",
            value="[0-9]{3,5}"
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
        assert "[0-9]{3,5}" in fragment.expression


class TestMatchesWithSpecialCharacters:
    """Test matches() with regex special characters"""

    def test_matches_with_escaped_characters_duckdb(self, duckdb_dialect):
        """Test matches() with escaped special characters on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Pattern to match a period (escaped)
        pattern_node = LiteralNode(
            node_type="literal",
            text="'\\.'",
            literal_type="string",
            value="\\."
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
        assert "regexp_matches(" in fragment.expression

    def test_matches_with_groups_postgresql(self, postgresql_dialect):
        """Test matches() with regex groups on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Pattern with capturing group
        pattern_node = LiteralNode(
            node_type="literal",
            text="'(\\d{3})-(\\d{4})'",
            literal_type="string",
            value="(\\d{3})-(\\d{4})"
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


class TestMatchesFragmentProperties:
    """Test that matches() returns correct SQLFragment properties"""

    def test_matches_fragment_structure_duckdb(self, duckdb_dialect):
        """Test matches() returns properly structured SQLFragment on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        pattern_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
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

        # Verify all fragment properties
        assert isinstance(fragment, SQLFragment)
        assert isinstance(fragment.expression, str)
        assert len(fragment.expression) > 0
        assert fragment.source_table == "resource"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert isinstance(fragment.dependencies, list)

    def test_matches_fragment_structure_postgresql(self, postgresql_dialect):
        """Test matches() returns properly structured SQLFragment on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        pattern_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
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

        # Verify all fragment properties
        assert isinstance(fragment, SQLFragment)
        assert isinstance(fragment.expression, str)
        assert len(fragment.expression) > 0
        assert fragment.source_table == "resource"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert isinstance(fragment.dependencies, list)
