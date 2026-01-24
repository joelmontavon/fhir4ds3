"""Unit tests for ASTToSQLTranslator contains() function translation.

Tests the _translate_contains() method implementation for substring detection.

Test Coverage:
- contains() for substring detection in strings
- Multi-database consistency (DuckDB and PostgreSQL)
- Error handling for invalid arguments
- Proper SQL generation through dialect methods
- Edge cases (null handling, empty strings, etc.)

Module: tests.unit.fhirpath.sql.test_translator_contains
Created: 2025-10-06
Task: SP-007-003
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


class TestContainsBasicTranslation:
    """Test basic contains() function translation"""

    def test_contains_simple_substring_duckdb(self, duckdb_dialect):
        """Test 'hello'.contains('ell') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create 'ell' substring (explicit argument)
        substring_node = LiteralNode(
            node_type="literal",
            text="'ell'",
            literal_type="string",
            value="ell"
        )
        substring_node.children = []

        # Method call: 'hello world'.contains('ell')
        # Context: The string 'hello world' is implicit (from context)
        # Argument: The substring 'ell' to find
        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        # Both databases use LIKE with wildcards
        assert "LIKE" in fragment.expression
        assert "ell" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_contains_simple_substring_postgresql(self, postgresql_dialect):
        """Test 'hello'.contains('ell') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create 'ell' substring (explicit argument)
        substring_node = LiteralNode(
            node_type="literal",
            text="'ell'",
            literal_type="string",
            value="ell"
        )
        substring_node.children = []

        # Method call: 'hello world'.contains('ell')
        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        # PostgreSQL also uses LIKE with wildcards
        assert "LIKE" in fragment.expression
        assert "ell" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_contains_literal_target_uses_literal(self, duckdb_dialect):
        """Ensure literal targets are preserved in SQL."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'hello world'",
            literal_type="string",
            value="hello world"
        )
        target_node.children = []

        substring_node = LiteralNode(
            node_type="literal",
            text="'world'",
            literal_type="string",
            value="world"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="'hello world'.contains('world')",
            function_name="contains",
            arguments=[substring_node],
            target=target_node
        )
        contains_node.children = [target_node, substring_node]

        fragment = translator._translate_contains(contains_node)

        assert "'hello world'" in fragment.expression
        assert "LIKE" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_contains_explicit_string_argument(self, duckdb_dialect):
        """Support contains(string, substring) invocation."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = IdentifierNode(
            node_type="identifier",
            text="name.family",
            identifier="name.family"
        )
        string_node.children = []

        substring_node = LiteralNode(
            node_type="literal",
            text="'Smith'",
            literal_type="string",
            value="Smith"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains(name.family, 'Smith')",
            function_name="contains",
            arguments=[string_node, substring_node]
        )
        contains_node.children = [string_node, substring_node]

        fragment = translator._translate_contains(contains_node)

        assert "json_extract" in fragment.expression
        assert "Smith" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_contains_word_substring_duckdb(self, duckdb_dialect):
        """Test 'hello world'.contains('world') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create 'world' substring (explicit argument)
        substring_node = LiteralNode(
            node_type="literal",
            text="'world'",
            literal_type="string",
            value="world"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "world" in fragment.expression
        assert fragment.requires_unnest is False

    def test_contains_case_sensitive_postgresql(self, postgresql_dialect):
        """Test 'Hello'.contains('hello') on PostgreSQL - case sensitive"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create 'hello' substring (lowercase)
        substring_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        # The implementation is case-sensitive by default
        assert "hello" in fragment.expression

    def test_contains_unicode_literal_duckdb(self, duckdb_dialect):
        """Ensure contains() retains Unicode characters in SQL literal."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'Señor'",
            literal_type="string",
            value="Señor"
        )
        target_node.children = []

        substring_node = LiteralNode(
            node_type="literal",
            text="'ñ'",
            literal_type="string",
            value="ñ"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="'Señor'.contains('ñ')",
            function_name="contains",
            arguments=[substring_node],
            target=target_node
        )
        contains_node.children = [target_node, substring_node]

        fragment = translator._translate_contains(contains_node)

        assert "Señor" in fragment.expression
        assert "ñ" in fragment.expression
        assert "LIKE" in fragment.expression


class TestContainsWithIdentifiers:
    """Test contains() with identifiers from context"""

    def test_contains_with_identifier_duckdb(self, duckdb_dialect):
        """Test Patient.name.family.contains('Smith') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.name.family (implicit context for contains)
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Create 'Smith' substring (explicit argument)
        substring_node = LiteralNode(
            node_type="literal",
            text="'Smith'",
            literal_type="string",
            value="Smith"
        )
        substring_node.children = []

        # Method call: family.contains('Smith')
        # Context: Patient.name.family is the implicit string
        # Argument: 'Smith' is the substring to find
        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "json_extract" in fragment.expression
        assert "family" in fragment.expression
        assert "Smith" in fragment.expression

    def test_contains_with_identifier_postgresql(self, postgresql_dialect):
        """Test Patient.name.family.contains('Smith') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context for Patient.name.family
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Create 'Smith' substring
        substring_node = LiteralNode(
            node_type="literal",
            text="'Smith'",
            literal_type="string",
            value="Smith"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        # PostgreSQL uses different JSON extraction
        assert "family" in fragment.expression
        assert "Smith" in fragment.expression


class TestContainsErrorHandling:
    """Test error handling for contains() function"""

    def test_contains_with_no_arguments_raises_error(self, duckdb_dialect):
        """Test that contains() with no arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[]
        )
        contains_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_contains(contains_node)

        assert "exactly 1 argument" in str(exc_info.value)
        assert "substring" in str(exc_info.value)

    def test_contains_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Test that contains() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        substring1 = LiteralNode(
            node_type="literal",
            text="'substring1'",
            literal_type="string",
            value="substring1"
        )
        substring1.children = []

        substring2 = LiteralNode(
            node_type="literal",
            text="'substring2'",
            literal_type="string",
            value="substring2"
        )
        substring2.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring1, substring2]
        )
        contains_node.children = [substring1, substring2]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_contains(contains_node)

        assert "exactly 1 argument" in str(exc_info.value)


class TestContainsMultiDatabaseConsistency:
    """Test that contains() produces consistent results across databases"""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_contains_basic_consistency(self, request, dialect_fixture):
        """Test contains() consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        substring_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "test" in fragment.expression
        assert "LIKE" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_contains_with_context_consistency(self, request, dialect_fixture):
        """Test contains() with context path consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Set up context path
        translator.context.push_path("name")
        translator.context.push_path("family")

        substring_node = LiteralNode(
            node_type="literal",
            text="'Doe'",
            literal_type="string",
            value="Doe"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "family" in fragment.expression
        assert "Doe" in fragment.expression


class TestContainsEdgeCases:
    """Test contains() edge cases"""

    def test_contains_with_empty_substring_duckdb(self, duckdb_dialect):
        """Test contains() with empty substring on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        substring_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        # Empty substring should return true (per FHIRPath spec)

    def test_contains_with_special_characters_postgresql(self, postgresql_dialect):
        """Test contains() with special characters on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Substring with special characters
        substring_node = LiteralNode(
            node_type="literal",
            text="'test@example.com'",
            literal_type="string",
            value="test@example.com"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression

    def test_contains_with_numeric_substring_duckdb(self, duckdb_dialect):
        """Test contains() with numeric substring on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        substring_node = LiteralNode(
            node_type="literal",
            text="'123'",
            literal_type="string",
            value="123"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "123" in fragment.expression

    def test_contains_with_whitespace_postgresql(self, postgresql_dialect):
        """Test contains() with whitespace in substring on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Substring with spaces
        substring_node = LiteralNode(
            node_type="literal",
            text="'hello world'",
            literal_type="string",
            value="hello world"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "hello world" in fragment.expression


class TestContainsWithSpecialStrings:
    """Test contains() with various special strings"""

    def test_contains_with_single_character_duckdb(self, duckdb_dialect):
        """Test contains() with single character substring on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        substring_node = LiteralNode(
            node_type="literal",
            text="'a'",
            literal_type="string",
            value="a"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression

    def test_contains_with_punctuation_postgresql(self, postgresql_dialect):
        """Test contains() with punctuation characters on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Substring with punctuation
        substring_node = LiteralNode(
            node_type="literal",
            text="'Dr.'",
            literal_type="string",
            value="Dr."
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression


class TestContainsFragmentProperties:
    """Test that contains() returns correct SQLFragment properties"""

    def test_contains_fragment_structure_duckdb(self, duckdb_dialect):
        """Test contains() returns properly structured SQLFragment on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        substring_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        # Verify all fragment properties
        assert isinstance(fragment, SQLFragment)
        assert isinstance(fragment.expression, str)
        assert len(fragment.expression) > 0
        assert fragment.source_table == "resource"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert isinstance(fragment.dependencies, list)

    def test_contains_fragment_structure_postgresql(self, postgresql_dialect):
        """Test contains() returns properly structured SQLFragment on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        substring_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        substring_node.children = []

        contains_node = FunctionCallNode(
            node_type="functionCall",
            text="contains()",
            function_name="contains",
            arguments=[substring_node]
        )
        contains_node.children = [substring_node]

        fragment = translator._translate_contains(contains_node)

        # Verify all fragment properties
        assert isinstance(fragment, SQLFragment)
        assert isinstance(fragment.expression, str)
        assert len(fragment.expression) > 0
        assert fragment.source_table == "resource"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert isinstance(fragment.dependencies, list)
