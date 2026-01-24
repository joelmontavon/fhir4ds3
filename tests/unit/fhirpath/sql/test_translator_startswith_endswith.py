"""Unit tests for ASTToSQLTranslator startsWith() and endsWith() function translation.

Tests the _translate_startswith() and _translate_endswith() method implementations
for prefix and suffix string matching.

Test Coverage:
- startsWith() for prefix detection in strings
- endsWith() for suffix detection in strings
- Multi-database consistency (DuckDB and PostgreSQL)
- Error handling for invalid arguments
- Proper SQL generation through dialect methods
- Edge cases (null handling, empty strings, etc.)

Module: tests.unit.fhirpath.sql.test_translator_startswith_endswith
Created: 2025-10-06
Task: SP-007-004
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


class TestStartsWithBasicTranslation:
    """Test basic startsWith() function translation"""

    def test_startswith_simple_prefix_duckdb(self, duckdb_dialect):
        """Test 'hello'.startsWith('hel') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create 'hel' prefix (explicit argument)
        prefix_node = LiteralNode(
            node_type="literal",
            text="'hel'",
            literal_type="string",
            value="hel"
        )
        prefix_node.children = []

        # Method call: 'hello'.startsWith('hel')
        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startsWith",
            arguments=[prefix_node]
        )
        startswith_node.children = [prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "hel" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_startswith_simple_prefix_postgresql(self, postgresql_dialect):
        """Test 'hello'.startsWith('hel') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        prefix_node = LiteralNode(
            node_type="literal",
            text="'hel'",
            literal_type="string",
            value="hel"
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startsWith",
            arguments=[prefix_node]
        )
        startswith_node.children = [prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "hel" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_startswith_literal_target_uses_literal(self, duckdb_dialect):
        """Ensure literal targets remain in generated SQL."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        target_node.children = []

        prefix_node = LiteralNode(
            node_type="literal",
            text="'he'",
            literal_type="string",
            value="he"
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="'hello'.startsWith('he')",
            function_name="startsWith",
            arguments=[prefix_node],
            target=target_node
        )
        startswith_node.children = [target_node, prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert "'hello'" in fragment.expression
        assert "LIKE" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_startswith_explicit_string_argument(self, duckdb_dialect):
        """Support startsWith(string, prefix) invocation."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = IdentifierNode(
            node_type="identifier",
            text="name.family",
            identifier="name.family"
        )
        string_node.children = []

        prefix_node = LiteralNode(
            node_type="literal",
            text="'Mc'",
            literal_type="string",
            value="Mc"
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith(name.family, 'Mc')",
            function_name="startsWith",
            arguments=[string_node, prefix_node]
        )
        startswith_node.children = [string_node, prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert "json_extract" in fragment.expression
        assert "Mc" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_startswith_unicode_literal(self, duckdb_dialect):
        """Ensure Unicode prefixes remain intact."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'Ångström'",
            literal_type="string",
            value="Ångström"
        )
        target_node.children = []

        prefix_node = LiteralNode(
            node_type="literal",
            text="'Å'",
            literal_type="string",
            value="Å"
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="'Ångström'.startsWith('Å')",
            function_name="startsWith",
            arguments=[prefix_node],
            target=target_node
        )
        startswith_node.children = [target_node, prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert "Ångström" in fragment.expression
        assert "Å" in fragment.expression
        assert "LIKE" in fragment.expression

    def test_startswith_scottish_name_duckdb(self, duckdb_dialect):
        """Test name.family.startsWith('Mc') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.name.family
        translator.context.push_path("name")
        translator.context.push_path("family")

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
            function_name="startsWith",
            arguments=[prefix_node]
        )
        startswith_node.children = [prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "json_extract" in fragment.expression
        assert "family" in fragment.expression
        assert "Mc" in fragment.expression


class TestEndsWithBasicTranslation:
    """Test basic endsWith() function translation"""

    def test_endswith_simple_suffix_duckdb(self, duckdb_dialect):
        """Test 'hello'.endsWith('llo') on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        suffix_node = LiteralNode(
            node_type="literal",
            text="'llo'",
            literal_type="string",
            value="llo"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[suffix_node]
        )
        endswith_node.children = [suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "llo" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_endswith_simple_suffix_postgresql(self, postgresql_dialect):
        """Test 'hello'.endsWith('llo') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        suffix_node = LiteralNode(
            node_type="literal",
            text="'llo'",
            literal_type="string",
            value="llo"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[suffix_node]
        )
        endswith_node.children = [suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "llo" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_endswith_literal_target_uses_literal(self, duckdb_dialect):
        """Ensure literal targets remain intact for endsWith."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        target_node.children = []

        suffix_node = LiteralNode(
            node_type="literal",
            text="'lo'",
            literal_type="string",
            value="lo"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="'hello'.endsWith('lo')",
            function_name="endsWith",
            arguments=[suffix_node],
            target=target_node
        )
        endswith_node.children = [target_node, suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert "'hello'" in fragment.expression
        assert "LIKE" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_endswith_explicit_string_argument(self, duckdb_dialect):
        """Support endsWith(string, suffix) invocation."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = IdentifierNode(
            node_type="identifier",
            text="name.family",
            identifier="name.family"
        )
        string_node.children = []

        suffix_node = LiteralNode(
            node_type="literal",
            text="'son'",
            literal_type="string",
            value="son"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith(name.family, 'son')",
            function_name="endsWith",
            arguments=[string_node, suffix_node]
        )
        endswith_node.children = [string_node, suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert "json_extract" in fragment.expression
        assert "son" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_endswith_unicode_literal(self, duckdb_dialect):
        """Ensure Unicode suffixes remain intact."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'naïve'",
            literal_type="string",
            value="naïve"
        )
        target_node.children = []

        suffix_node = LiteralNode(
            node_type="literal",
            text="'ïve'",
            literal_type="string",
            value="ïve"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="'naïve'.endsWith('ïve')",
            function_name="endsWith",
            arguments=[suffix_node],
            target=target_node
        )
        endswith_node.children = [target_node, suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert "naïve" in fragment.expression
        assert "ïve" in fragment.expression
        assert "LIKE" in fragment.expression

    def test_endswith_patronymic_name_postgresql(self, postgresql_dialect):
        """Test name.family.endsWith('son') on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context for Patient.name.family
        translator.context.push_path("name")
        translator.context.push_path("family")

        suffix_node = LiteralNode(
            node_type="literal",
            text="'son'",
            literal_type="string",
            value="son"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[suffix_node]
        )
        endswith_node.children = [suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "family" in fragment.expression
        assert "son" in fragment.expression


class TestStartsWithErrorHandling:
    """Test error handling for startsWith() function"""

    def test_startswith_with_no_arguments_raises_error(self, duckdb_dialect):
        """Test that startsWith() with no arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startsWith",
            arguments=[]
        )
        startswith_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_startswith(startswith_node)

        assert "exactly 1 argument" in str(exc_info.value)
        assert "prefix" in str(exc_info.value)

    def test_startswith_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Test that startsWith() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        prefix1 = LiteralNode(
            node_type="literal",
            text="'prefix1'",
            literal_type="string",
            value="prefix1"
        )
        prefix1.children = []

        prefix2 = LiteralNode(
            node_type="literal",
            text="'prefix2'",
            literal_type="string",
            value="prefix2"
        )
        prefix2.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startsWith",
            arguments=[prefix1, prefix2]
        )
        startswith_node.children = [prefix1, prefix2]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_startswith(startswith_node)

        assert "exactly 1 argument" in str(exc_info.value)


class TestEndsWithErrorHandling:
    """Test error handling for endsWith() function"""

    def test_endswith_with_no_arguments_raises_error(self, duckdb_dialect):
        """Test that endsWith() with no arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[]
        )
        endswith_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_endswith(endswith_node)

        assert "exactly 1 argument" in str(exc_info.value)
        assert "suffix" in str(exc_info.value)

    def test_endswith_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Test that endsWith() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        suffix1 = LiteralNode(
            node_type="literal",
            text="'suffix1'",
            literal_type="string",
            value="suffix1"
        )
        suffix1.children = []

        suffix2 = LiteralNode(
            node_type="literal",
            text="'suffix2'",
            literal_type="string",
            value="suffix2"
        )
        suffix2.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[suffix1, suffix2]
        )
        endswith_node.children = [suffix1, suffix2]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_endswith(endswith_node)

        assert "exactly 1 argument" in str(exc_info.value)


class TestMultiDatabaseConsistency:
    """Test that functions produce consistent results across databases"""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_startswith_consistency(self, request, dialect_fixture):
        """Test startsWith() consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        prefix_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startsWith",
            arguments=[prefix_node]
        )
        startswith_node.children = [prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "test" in fragment.expression
        assert "LIKE" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_endswith_consistency(self, request, dialect_fixture):
        """Test endsWith() consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        suffix_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[suffix_node]
        )
        endswith_node.children = [suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "test" in fragment.expression
        assert "LIKE" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False


class TestEdgeCases:
    """Test edge cases for both functions"""

    def test_startswith_with_empty_prefix_duckdb(self, duckdb_dialect):
        """Test startsWith() with empty prefix on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        prefix_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startsWith",
            arguments=[prefix_node]
        )
        startswith_node.children = [prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        # Empty prefix should return true (per FHIRPath spec)

    def test_endswith_with_empty_suffix_postgresql(self, postgresql_dialect):
        """Test endsWith() with empty suffix on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        suffix_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[suffix_node]
        )
        endswith_node.children = [suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        # Empty suffix should return true (per FHIRPath spec)

    def test_startswith_with_single_character_postgresql(self, postgresql_dialect):
        """Test startsWith() with single character prefix on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        prefix_node = LiteralNode(
            node_type="literal",
            text="'A'",
            literal_type="string",
            value="A"
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startsWith",
            arguments=[prefix_node]
        )
        startswith_node.children = [prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        assert "'A'" in fragment.expression

    def test_endswith_with_special_characters_duckdb(self, duckdb_dialect):
        """Test endsWith() with special characters on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        suffix_node = LiteralNode(
            node_type="literal",
            text="'.com'",
            literal_type="string",
            value=".com"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[suffix_node]
        )
        endswith_node.children = [suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression


class TestFragmentProperties:
    """Test that functions return correct SQLFragment properties"""

    def test_startswith_fragment_structure_duckdb(self, duckdb_dialect):
        """Test startsWith() returns properly structured SQLFragment on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        prefix_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startsWith",
            arguments=[prefix_node]
        )
        startswith_node.children = [prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        # Verify all fragment properties
        assert isinstance(fragment, SQLFragment)
        assert isinstance(fragment.expression, str)
        assert len(fragment.expression) > 0
        assert fragment.source_table == "resource"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert isinstance(fragment.dependencies, list)

    def test_endswith_fragment_structure_postgresql(self, postgresql_dialect):
        """Test endsWith() returns properly structured SQLFragment on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        suffix_node = LiteralNode(
            node_type="literal",
            text="'test'",
            literal_type="string",
            value="test"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[suffix_node]
        )
        endswith_node.children = [suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        # Verify all fragment properties
        assert isinstance(fragment, SQLFragment)
        assert isinstance(fragment.expression, str)
        assert len(fragment.expression) > 0
        assert fragment.source_table == "resource"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert isinstance(fragment.dependencies, list)


class TestCaseSensitivity:
    """Test case-sensitive behavior of both functions"""

    def test_startswith_case_sensitive_duckdb(self, duckdb_dialect):
        """Test startsWith() is case-sensitive on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        prefix_node = LiteralNode(
            node_type="literal",
            text="'HELLO'",
            literal_type="string",
            value="HELLO"
        )
        prefix_node.children = []

        startswith_node = FunctionCallNode(
            node_type="functionCall",
            text="startsWith()",
            function_name="startsWith",
            arguments=[prefix_node]
        )
        startswith_node.children = [prefix_node]

        fragment = translator._translate_startswith(startswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        # Should be case-sensitive by default
        assert "HELLO" in fragment.expression

    def test_endswith_case_sensitive_postgresql(self, postgresql_dialect):
        """Test endsWith() is case-sensitive on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        suffix_node = LiteralNode(
            node_type="literal",
            text="'WORLD'",
            literal_type="string",
            value="WORLD"
        )
        suffix_node.children = []

        endswith_node = FunctionCallNode(
            node_type="functionCall",
            text="endsWith()",
            function_name="endsWith",
            arguments=[suffix_node]
        )
        endswith_node.children = [suffix_node]

        fragment = translator._translate_endswith(endswith_node)

        assert isinstance(fragment, SQLFragment)
        assert "LIKE" in fragment.expression
        # Should be case-sensitive by default
        assert "WORLD" in fragment.expression
