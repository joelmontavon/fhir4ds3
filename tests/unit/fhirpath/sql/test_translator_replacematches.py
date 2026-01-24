"""Unit tests for ASTToSQLTranslator replaceMatches() function translation.

Tests the _translate_replacematches() method implementation for regex pattern replacement.

Test Coverage:
- replaceMatches() for regex pattern replacement on strings
- Multi-database consistency (DuckDB and PostgreSQL)
- Error handling for invalid arguments
- Proper SQL generation through dialect methods
- Edge cases (null handling, empty strings, capture groups, etc.)

Module: tests.unit.fhirpath.sql.test_translator_replacematches
Created: 2025-10-05
Task: SP-007-002
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


class TestReplaceMatchesBasicTranslation:
    """Test basic replaceMatches() function translation"""

    def test_replacematches_simple_pattern_duckdb(self, duckdb_dialect):
        """Test 'hello world'.replaceMatches('world', 'universe') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create 'world' regex pattern (first argument)
        pattern_node = LiteralNode(
            node_type="literal",
            text="'world'",
            literal_type="string",
            value="world"
        )
        pattern_node.children = []

        # Create 'universe' substitution (second argument)
        subst_node = LiteralNode(
            node_type="literal",
            text="'universe'",
            literal_type="string",
            value="universe"
        )
        subst_node.children = []

        # Method call: 'hello world'.replaceMatches('world', 'universe')
        # Context: The string 'hello world' is implicit (from context)
        # Argument 1: The regex pattern 'world' to match
        # Argument 2: The replacement 'universe'
        replacematches_node = FunctionCallNode(
            node_type="functionCall",
            text="replaceMatches()",
            function_name="replacematches",
            arguments=[pattern_node, subst_node]
        )
        replacematches_node.children = [pattern_node, subst_node]

        fragment = translator._translate_replacematches(replacematches_node)

        assert isinstance(fragment, SQLFragment)
        # DuckDB uses regexp_replace() function
        assert "regexp_replace(" in fragment.expression
        assert "world" in fragment.expression
        assert "universe" in fragment.expression
        assert "'g'" in fragment.expression  # Global flag
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_replacematches_simple_pattern_postgresql(self, postgresql_dialect):
        """Test 'hello world'.replaceMatches('world', 'universe') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create 'world' regex pattern
        pattern_node = LiteralNode(
            node_type="literal",
            text="'world'",
            literal_type="string",
            value="world"
        )
        pattern_node.children = []

        # Create 'universe' substitution
        subst_node = LiteralNode(
            node_type="literal",
            text="'universe'",
            literal_type="string",
            value="universe"
        )
        subst_node.children = []

        # Method call: 'hello world'.replaceMatches('world', 'universe')
        replacematches_node = FunctionCallNode(
            node_type="functionCall",
            text="replaceMatches()",
            function_name="replacematches",
            arguments=[pattern_node, subst_node]
        )
        replacematches_node.children = [pattern_node, subst_node]

        fragment = translator._translate_replacematches(replacematches_node)

        assert isinstance(fragment, SQLFragment)
        # PostgreSQL also uses regexp_replace() function
        assert "regexp_replace(" in fragment.expression
        assert "world" in fragment.expression
        assert "universe" in fragment.expression
        assert "'g'" in fragment.expression  # Global flag
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_replacematches_digit_pattern_duckdb(self, duckdb_dialect):
        """Test 'abc123def'.replaceMatches('\\d+', 'XXX') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create '\\d+' digit pattern
        pattern_node = LiteralNode(
            node_type="literal",
            text="'\\d+'",
            literal_type="string",
            value="\\d+"
        )
        pattern_node.children = []

        # Create 'XXX' substitution
        subst_node = LiteralNode(
            node_type="literal",
            text="'XXX'",
            literal_type="string",
            value="XXX"
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
        assert "XXX" in fragment.expression
        assert fragment.requires_unnest is False

    def test_replacematches_character_class_pattern_postgresql(self, postgresql_dialect):
        """Test 'abc123'.replaceMatches('[0-9]+', '') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create '[0-9]+' digit pattern
        pattern_node = LiteralNode(
            node_type="literal",
            text="'[0-9]+'",
            literal_type="string",
            value="[0-9]+"
        )
        pattern_node.children = []

        # Create empty string substitution
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
        assert "[0-9]+" in fragment.expression


class TestReplaceMatchesWithIdentifiers:
    """Test replaceMatches() with identifiers from context"""

    def test_replacematches_with_identifier_duckdb(self, duckdb_dialect):
        """Test Patient.name.family.replaceMatches('[0-9]', 'X') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.name.family (implicit context for replaceMatches)
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Create '[0-9]' digit pattern
        pattern_node = LiteralNode(
            node_type="literal",
            text="'[0-9]'",
            literal_type="string",
            value="[0-9]"
        )
        pattern_node.children = []

        # Create 'X' substitution
        subst_node = LiteralNode(
            node_type="literal",
            text="'X'",
            literal_type="string",
            value="X"
        )
        subst_node.children = []

        # Method call: family.replaceMatches('[0-9]', 'X')
        # Context: Patient.name.family is the implicit string
        # Argument 1: '[0-9]' is the regex pattern
        # Argument 2: 'X' is the replacement
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
        assert "json_extract" in fragment.expression
        assert "family" in fragment.expression
        assert "[0-9]" in fragment.expression
        assert "'X'" in fragment.expression

    def test_replacematches_with_identifier_postgresql(self, postgresql_dialect):
        """Test Patient.name.family.replaceMatches('[^A-Za-z]', '') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context for Patient.name.family
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Create '[^A-Za-z]' non-letter pattern
        pattern_node = LiteralNode(
            node_type="literal",
            text="'[^A-Za-z]'",
            literal_type="string",
            value="[^A-Za-z]"
        )
        pattern_node.children = []

        # Create empty string substitution (removes all non-letters)
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
        assert "family" in fragment.expression
        assert "[^A-Za-z]" in fragment.expression


class TestReplaceMatchesCaptureGroups:
    """Test replaceMatches() with capture groups"""

    def test_replacematches_with_capture_groups_duckdb(self, duckdb_dialect):
        """Test 'John Doe'.replaceMatches('(\\w+) (\\w+)', '$2, $1') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create '(\\w+) (\\w+)' pattern with two capture groups
        pattern_node = LiteralNode(
            node_type="literal",
            text="'(\\w+) (\\w+)'",
            literal_type="string",
            value="(\\w+) (\\w+)"
        )
        pattern_node.children = []

        # Create '$2, $1' substitution (swap the groups)
        subst_node = LiteralNode(
            node_type="literal",
            text="'$2, $1'",
            literal_type="string",
            value="$2, $1"
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
        assert "$2, $1" in fragment.expression or "\\2, \\1" in fragment.expression

    def test_replacematches_with_numbered_groups_postgresql(self, postgresql_dialect):
        """Test replaceMatches() with numbered capture groups on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create pattern with capture group
        pattern_node = LiteralNode(
            node_type="literal",
            text="'(\\d{3})-(\\d{4})'",
            literal_type="string",
            value="(\\d{3})-(\\d{4})"
        )
        pattern_node.children = []

        # Create substitution using groups
        subst_node = LiteralNode(
            node_type="literal",
            text="'$1 ext $2'",
            literal_type="string",
            value="$1 ext $2"
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


class TestReplaceMatchesErrorHandling:
    """Test error handling for replaceMatches() function"""

    def test_replacematches_with_no_arguments_raises_error(self, duckdb_dialect):
        """Test that replaceMatches() with no arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        replacematches_node = FunctionCallNode(
            node_type="functionCall",
            text="replaceMatches()",
            function_name="replacematches",
            arguments=[]
        )
        replacematches_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_replacematches(replacematches_node)

        assert "exactly 2 arguments" in str(exc_info.value)
        assert "regex pattern, substitution" in str(exc_info.value)

    def test_replacematches_with_one_argument_raises_error(self, duckdb_dialect):
        """Test that replaceMatches() with one argument raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        pattern = LiteralNode(
            node_type="literal",
            text="'pattern'",
            literal_type="string",
            value="pattern"
        )
        pattern.children = []

        replacematches_node = FunctionCallNode(
            node_type="functionCall",
            text="replaceMatches()",
            function_name="replacematches",
            arguments=[pattern]
        )
        replacematches_node.children = [pattern]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_replacematches(replacematches_node)

        assert "exactly 2 arguments" in str(exc_info.value)

    def test_replacematches_with_three_arguments_raises_error(self, duckdb_dialect):
        """Test that replaceMatches() with three arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        pattern = LiteralNode(
            node_type="literal",
            text="'pattern'",
            literal_type="string",
            value="pattern"
        )
        pattern.children = []

        subst1 = LiteralNode(
            node_type="literal",
            text="'subst1'",
            literal_type="string",
            value="subst1"
        )
        subst1.children = []

        subst2 = LiteralNode(
            node_type="literal",
            text="'subst2'",
            literal_type="string",
            value="subst2"
        )
        subst2.children = []

        replacematches_node = FunctionCallNode(
            node_type="functionCall",
            text="replaceMatches()",
            function_name="replacematches",
            arguments=[pattern, subst1, subst2]
        )
        replacematches_node.children = [pattern, subst1, subst2]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_replacematches(replacematches_node)

        assert "exactly 2 arguments" in str(exc_info.value)


class TestReplaceMatchesMultiDatabaseConsistency:
    """Test that replaceMatches() produces consistent results across databases"""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_replacematches_basic_consistency(self, request, dialect_fixture):
        """Test replaceMatches() consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        pattern_node = LiteralNode(
            node_type="literal",
            text="'world'",
            literal_type="string",
            value="world"
        )
        pattern_node.children = []

        subst_node = LiteralNode(
            node_type="literal",
            text="'universe'",
            literal_type="string",
            value="universe"
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
        assert "world" in fragment.expression
        assert "universe" in fragment.expression
        assert "'g'" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_replacematches_with_context_consistency(self, request, dialect_fixture):
        """Test replaceMatches() with context path consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Set up context path
        translator.context.push_path("name")
        translator.context.push_path("family")

        pattern_node = LiteralNode(
            node_type="literal",
            text="'[0-9]'",
            literal_type="string",
            value="[0-9]"
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
        assert "family" in fragment.expression
        assert "[0-9]" in fragment.expression
        assert "'X'" in fragment.expression


class TestReplaceMatchesEdgeCases:
    """Test replaceMatches() edge cases"""

    def test_replacematches_with_empty_pattern_duckdb(self, duckdb_dialect):
        """Test replaceMatches() with empty regex pattern on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        pattern_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
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

    def test_replacematches_with_empty_substitution_postgresql(self, postgresql_dialect):
        """Test replaceMatches() with empty substitution (removal) on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        pattern_node = LiteralNode(
            node_type="literal",
            text="'[0-9]+'",
            literal_type="string",
            value="[0-9]+"
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
        assert "[0-9]+" in fragment.expression


class TestReplaceMatchesFragmentProperties:
    """Test that replaceMatches() returns correct SQLFragment properties"""

    def test_replacematches_fragment_structure_duckdb(self, duckdb_dialect):
        """Test replaceMatches() returns properly structured SQLFragment on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        pattern_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        pattern_node.children = []

        subst_node = LiteralNode(
            node_type="literal",
            text="'replacement'",
            literal_type="string",
            value="replacement"
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

        # Verify all fragment properties
        assert isinstance(fragment, SQLFragment)
        assert isinstance(fragment.expression, str)
        assert len(fragment.expression) > 0
        assert fragment.source_table == "resource"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert isinstance(fragment.dependencies, list)

    def test_replacematches_fragment_structure_postgresql(self, postgresql_dialect):
        """Test replaceMatches() returns properly structured SQLFragment on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        pattern_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        pattern_node.children = []

        subst_node = LiteralNode(
            node_type="literal",
            text="'replacement'",
            literal_type="string",
            value="replacement"
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

        # Verify all fragment properties
        assert isinstance(fragment, SQLFragment)
        assert isinstance(fragment.expression, str)
        assert len(fragment.expression) > 0
        assert fragment.source_table == "resource"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert isinstance(fragment.dependencies, list)
