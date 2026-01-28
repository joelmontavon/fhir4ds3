"""Unit tests for ASTToSQLTranslator string function translation.

Tests the _translate_string_function() method implementation for string
operations: substring(), indexOf(), length(), replace().

Test Coverage:
- substring() for extracting substrings with 0-based indexing
- indexOf() for finding substring position (0-based, returns -1 if not found)
- length() for getting string length
- replace() for replacing substring occurrences
- Multi-database consistency (DuckDB and PostgreSQL)
- Index conversion (FHIRPath 0-based to SQL 1-based)
- Error handling for invalid arguments
- Proper SQL generation through dialect methods

Module: tests.unit.fhirpath.sql.test_translator_string_functions
Created: 2025-10-03
Task: SP-006-018
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


class TestSubstringFunction:
    """Test substring() function translation"""

    def test_substring_with_start_duckdb(self, duckdb_dialect):
        """Test substring(string, start) on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create substring('hello', 1) expression (0-based index 1 = 'e')
        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        start_node = LiteralNode(
            node_type="literal",
            text="1",
            literal_type="integer",
            value=1
        )
        start_node.children = []

        substring_node = FunctionCallNode(
            node_type="functionCall",
            text="substring()",
            function_name="substring",
            arguments=[string_node, start_node]
        )
        substring_node.children = [string_node, start_node]

        fragment = translator._translate_string_function(substring_node)

        assert isinstance(fragment, SQLFragment)
        assert "substring(" in fragment.expression
        # Check that index was converted: 1 (0-based) + 1 = 2 (1-based)
        assert "+ 1" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_substring_with_start_and_length_duckdb(self, duckdb_dialect):
        """Test substring(string, start, length) on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create substring('hello', 1, 3) expression
        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        start_node = LiteralNode(
            node_type="literal",
            text="1",
            literal_type="integer",
            value=1
        )
        start_node.children = []

        length_node = LiteralNode(
            node_type="literal",
            text="3",
            literal_type="integer",
            value=3
        )
        length_node.children = []

        substring_node = FunctionCallNode(
            node_type="functionCall",
            text="substring()",
            function_name="substring",
            arguments=[string_node, start_node, length_node]
        )
        substring_node.children = [string_node, start_node, length_node]

        fragment = translator._translate_string_function(substring_node)

        assert isinstance(fragment, SQLFragment)
        assert "substring(" in fragment.expression
        # Check that index was converted
        assert "+ 1" in fragment.expression
        assert "3" in fragment.expression

    def test_substring_with_start_and_length_postgresql(self, postgresql_dialect):
        """Test substring(string, start, length) on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create substring('hello', 1, 3) expression
        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        start_node = LiteralNode(
            node_type="literal",
            text="1",
            literal_type="integer",
            value=1
        )
        start_node.children = []

        length_node = LiteralNode(
            node_type="literal",
            text="3",
            literal_type="integer",
            value=3
        )
        length_node.children = []

        substring_node = FunctionCallNode(
            node_type="functionCall",
            text="substring()",
            function_name="substring",
            arguments=[string_node, start_node, length_node]
        )
        substring_node.children = [string_node, start_node, length_node]

        fragment = translator._translate_string_function(substring_node)

        assert isinstance(fragment, SQLFragment)
        assert "substring(" in fragment.expression
        # PostgreSQL uses FROM ... FOR syntax
        assert "FROM" in fragment.expression
        assert "FOR" in fragment.expression

    def test_substring_method_literal_uses_literal(self, duckdb_dialect):
        """Ensure method call on literal keeps literal target."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        target_node.children = []

        start_node = LiteralNode(
            node_type="literal",
            text="1",
            literal_type="integer",
            value=1
        )
        start_node.children = []

        method_node = FunctionCallNode(
            node_type="functionCall",
            text="'hello'.substring(1)",
            function_name="substring",
            arguments=[start_node],
            target=target_node
        )

        fragment = translator._translate_string_function(method_node)

        assert isinstance(fragment, SQLFragment)
        assert "'hello'" in fragment.expression
        assert "+ 1" in fragment.expression

    def test_substring_negative_start_returns_empty(self, duckdb_dialect):
        """Verify negative start index produces empty string case branch."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'12345'",
            literal_type="string",
            value="12345"
        )
        target_node.children = []

        start_node = LiteralNode(
            node_type="literal",
            text="-1",
            literal_type="integer",
            value=-1
        )
        start_node.children = []

        method_node = FunctionCallNode(
            node_type="functionCall",
            text="'12345'.substring(-1)",
            function_name="substring",
            arguments=[start_node],
            target=target_node
        )

        fragment = translator._translate_string_function(method_node)

        assert "CASE" in fragment.expression
        # SP-106-003: Type casting wraps the expression, so check for the key pattern
        assert "< 0 THEN ''" in fragment.expression

    def test_substring_context_without_string_argument(self, duckdb_dialect):
        """Ensure substring(0,1) uses current context path when no string argument provided."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")

        start_node = LiteralNode(
            node_type="literal",
            text="0",
            literal_type="integer",
            value=0
        )
        start_node.children = []

        length_node = LiteralNode(
            node_type="literal",
            text="1",
            literal_type="integer",
            value=1
        )
        length_node.children = []

        function_node = FunctionCallNode(
            node_type="functionCall",
            text="substring(0,1)",
            function_name="substring",
            arguments=[start_node, length_node]
        )

        fragment = translator._translate_string_function(function_node)

        assert "json_extract" in fragment.expression
        assert "$.name" in fragment.expression
        assert "+ 1" in fragment.expression


class TestIndexOfFunction:
    """Test indexOf() function translation (method call with 1 argument)"""

    def test_indexof_basic_duckdb(self, duckdb_dialect):
        """Test 'string'.indexOf(substring) on DuckDB - method call pattern"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create 'l' search substring (explicit argument)
        search_node = LiteralNode(
            node_type="literal",
            text="'l'",
            literal_type="string",
            value="l"
        )
        search_node.children = []

        # Method call: 'hello'.indexOf('l')
        # Context: The string 'hello' is implicit (from context)
        # Argument: The substring 'l' to search for
        indexof_node = FunctionCallNode(
            node_type="functionCall",
            text="indexOf()",
            function_name="indexOf",
            arguments=[search_node]  # Only 1 argument: substring to find
        )
        indexof_node.children = [search_node]

        fragment = translator._translate_string_function(indexof_node)

        assert isinstance(fragment, SQLFragment)
        # DuckDB uses strpos() and should subtract 1 for 0-based indexing
        assert "strpos(" in fragment.expression
        assert "- 1" in fragment.expression

    def test_indexof_basic_postgresql(self, postgresql_dialect):
        """Test 'string'.indexOf(substring) on PostgreSQL - method call pattern"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create 'l' search substring (explicit argument)
        search_node = LiteralNode(
            node_type="literal",
            text="'l'",
            literal_type="string",
            value="l"
        )
        search_node.children = []

        # Method call: 'hello'.indexOf('l')
        indexof_node = FunctionCallNode(
            node_type="functionCall",
            text="indexOf()",
            function_name="indexOf",
            arguments=[search_node]  # Only 1 argument: substring to find
        )
        indexof_node.children = [search_node]

        fragment = translator._translate_string_function(indexof_node)

        assert isinstance(fragment, SQLFragment)
        # PostgreSQL uses position() and should subtract 1 for 0-based indexing
        assert "position(" in fragment.expression
        assert "- 1" in fragment.expression

    def test_indexof_with_identifier_duckdb(self, duckdb_dialect):
        """Test name.family.indexOf('Smith') on DuckDB - method call with context"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create 'Smith' search string (explicit argument)
        search_node = LiteralNode(
            node_type="literal",
            text="'Smith'",
            literal_type="string",
            value="Smith"
        )
        search_node.children = []

        # Set up context for Patient.name.family (implicit context for indexOf)
        translator.context.push_path("name")
        translator.context.push_path("family")

        # Method call: family.indexOf('Smith')
        # Context: Patient.name.family is the implicit string
        # Argument: 'Smith' is the substring to find
        indexof_node = FunctionCallNode(
            node_type="functionCall",
            text="indexOf()",
            function_name="indexOf",
            arguments=[search_node]  # Only 1 argument: substring to find
        )
        indexof_node.children = [search_node]

        fragment = translator._translate_string_function(indexof_node)

        assert isinstance(fragment, SQLFragment)
        assert "strpos(" in fragment.expression
        assert "json_extract" in fragment.expression
        assert "family" in fragment.expression

    def test_indexof_literal_target_uses_literal(self, duckdb_dialect):
        """Ensure literal method target is preserved in generated SQL."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'LogicalModel-Person'",
            literal_type="string",
            value="LogicalModel-Person"
        )
        target_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="'-'",
            literal_type="string",
            value="-"
        )
        search_node.children = []

        method_node = FunctionCallNode(
            node_type="functionCall",
            text="'LogicalModel-Person'.indexOf('-')",
            function_name="indexOf",
            arguments=[search_node],
            target=target_node
        )

        fragment = translator._translate_string_function(method_node)

        assert "'LogicalModel-Person'" in fragment.expression
        assert "strpos(" in fragment.expression
        assert "- 1" in fragment.expression

    def test_indexof_function_style_literal_argument(self, duckdb_dialect):
        """Support indexOf(string, substring) invocation with literal string."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="'l'",
            literal_type="string",
            value="l"
        )
        search_node.children = []

        function_node = FunctionCallNode(
            node_type="functionCall",
            text="indexOf('hello', 'l')",
            function_name="indexOf",
            arguments=[string_node, search_node]
        )
        function_node.children = [string_node, search_node]

        fragment = translator._translate_string_function(function_node)

        assert "strpos('hello'" in fragment.expression
        assert "- 1" in fragment.expression

    def test_indexof_function_style_identifier_argument(self, duckdb_dialect):
        """Support indexOf(identifier, substring) invocation."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = IdentifierNode(
            node_type="identifier",
            text="name.family",
            identifier="name.family"
        )
        string_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="'Sm'",
            literal_type="string",
            value="Sm"
        )
        search_node.children = []

        function_node = FunctionCallNode(
            node_type="functionCall",
            text="indexOf(name.family, 'Sm')",
            function_name="indexOf",
            arguments=[string_node, search_node]
        )
        function_node.children = [string_node, search_node]

        fragment = translator._translate_string_function(function_node)

        assert "json_extract" in fragment.expression
        assert "Sm" in fragment.expression
        assert "- 1" in fragment.expression


class TestLengthFunction:
    """Test length() function translation"""

    def test_length_with_string_literal_duckdb(self, duckdb_dialect):
        """Test length(string) on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create length('hello') expression
        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        length_node = FunctionCallNode(
            node_type="functionCall",
            text="length()",
            function_name="length",
            arguments=[string_node]
        )
        length_node.children = [string_node]

        fragment = translator._translate_string_function(length_node)

        assert isinstance(fragment, SQLFragment)
        assert "length(" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_length_with_string_literal_postgresql(self, postgresql_dialect):
        """Test length(string) on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create length('hello') expression
        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        length_node = FunctionCallNode(
            node_type="functionCall",
            text="length()",
            function_name="length",
            arguments=[string_node]
        )
        length_node.children = [string_node]

        fragment = translator._translate_string_function(length_node)

        assert isinstance(fragment, SQLFragment)
        assert "length(" in fragment.expression

    def test_length_function_form_uses_argument(self, duckdb_dialect):
        """Ensure length(string) explicitly uses provided argument."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'FHIR4DS'",
            literal_type="string",
            value="FHIR4DS"
        )
        string_node.children = []

        length_node = FunctionCallNode(
            node_type="functionCall",
            text="length('FHIR4DS')",
            function_name="length",
            arguments=[string_node]
        )

        fragment = translator._translate_string_function(length_node)

        assert "length(" in fragment.expression
        assert "'FHIR4DS'" in fragment.expression


class TestReplaceFunction:
    """Test replace() function translation (method call with 2 arguments)"""

    def test_replace_basic_duckdb(self, duckdb_dialect):
        """Test 'string'.replace(pattern, substitution) on DuckDB - method call pattern"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create 'world' pattern (explicit argument 1)
        search_node = LiteralNode(
            node_type="literal",
            text="'world'",
            literal_type="string",
            value="world"
        )
        search_node.children = []

        # Create 'there' substitution (explicit argument 2)
        replace_node = LiteralNode(
            node_type="literal",
            text="'there'",
            literal_type="string",
            value="there"
        )
        replace_node.children = []

        # Method call: 'hello world'.replace('world', 'there')
        # Context: The string 'hello world' is implicit (from context)
        # Arguments: pattern='world', substitution='there'
        replace_func_node = FunctionCallNode(
            node_type="functionCall",
            text="replace()",
            function_name="replace",
            arguments=[search_node, replace_node]  # Only 2 arguments: pattern, substitution
        )
        replace_func_node.children = [search_node, replace_node]

        fragment = translator._translate_string_function(replace_func_node)

        assert isinstance(fragment, SQLFragment)
        assert "replace(" in fragment.expression
        assert fragment.requires_unnest is False

    def test_replace_basic_postgresql(self, postgresql_dialect):
        """Test 'string'.replace(pattern, substitution) on PostgreSQL - method call pattern"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create 'world' pattern (explicit argument 1)
        search_node = LiteralNode(
            node_type="literal",
            text="'world'",
            literal_type="string",
            value="world"
        )
        search_node.children = []

        # Create 'there' substitution (explicit argument 2)
        replace_node = LiteralNode(
            node_type="literal",
            text="'there'",
            literal_type="string",
            value="there"
        )
        replace_node.children = []

        # Method call: 'hello world'.replace('world', 'there')
        replace_func_node = FunctionCallNode(
            node_type="functionCall",
            text="replace()",
            function_name="replace",
            arguments=[search_node, replace_node]  # Only 2 arguments: pattern, substitution
        )
        replace_func_node.children = [search_node, replace_node]

        fragment = translator._translate_string_function(replace_func_node)

        assert isinstance(fragment, SQLFragment)
        assert "replace(" in fragment.expression

    def test_replace_function_form_uses_string_argument(self, duckdb_dialect):
        """Ensure replace(string, pattern, substitution) keeps explicit string argument."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello world'",
            literal_type="string",
            value="hello world"
        )
        string_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="'world'",
            literal_type="string",
            value="world"
        )
        search_node.children = []

        replace_node = LiteralNode(
            node_type="literal",
            text="'there'",
            literal_type="string",
            value="there"
        )
        replace_node.children = []

        replace_func_node = FunctionCallNode(
            node_type="functionCall",
            text="replace('hello world','world','there')",
            function_name="replace",
            arguments=[string_node, search_node, replace_node]
        )

        fragment = translator._translate_string_function(replace_func_node)

        assert "replace(" in fragment.expression
        assert "'hello world'" in fragment.expression


class TestStringFunctionErrorHandling:
    """Test error handling for string functions"""

    def test_substring_with_no_arguments_raises_error(self, duckdb_dialect):
        """Test that substring() with no arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        substring_node = FunctionCallNode(
            node_type="functionCall",
            text="substring()",
            function_name="substring",
            arguments=[]
        )
        substring_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_string_function(substring_node)

        assert "requires 1-3 arguments" in str(exc_info.value)

    def test_indexof_with_wrong_argument_count_raises_error(self, duckdb_dialect):
        """Test that indexOf() with wrong number of arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Test with 0 arguments (should fail - needs 1 argument: substring)
        indexof_node_zero = FunctionCallNode(
            node_type="functionCall",
            text="indexOf()",
            function_name="indexOf",
            arguments=[]
        )
        indexof_node_zero.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_string_function(indexof_node_zero)

        assert "exactly 1 argument" in str(exc_info.value)

    def test_length_with_too_many_arguments_raises_error(self, duckdb_dialect):
        """Test that length() with too many arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node1 = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node2 = LiteralNode(
            node_type="literal",
            text="'world'",
            literal_type="string",
            value="world"
        )

        length_node = FunctionCallNode(
            node_type="functionCall",
            text="length()",
            function_name="length",
            arguments=[string_node1, string_node2]
        )
        length_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_string_function(length_node)

        assert "at most 1 argument" in str(exc_info.value)

    def test_replace_with_wrong_argument_count_raises_error(self, duckdb_dialect):
        """Test that replace() with wrong number of arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Test with 1 argument (should fail - needs 2 arguments: pattern, substitution)
        search_node = LiteralNode(
            node_type="literal",
            text="'l'",
            literal_type="string",
            value="l"
        )
        search_node.children = []

        replace_node_one_arg = FunctionCallNode(
            node_type="functionCall",
            text="replace()",
            function_name="replace",
            arguments=[search_node]  # Missing substitution argument
        )
        replace_node_one_arg.children = [search_node]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_string_function(replace_node_one_arg)

        assert "exactly 2 arguments" in str(exc_info.value)


class TestMultiDatabaseConsistency:
    """Test that string functions produce consistent results across databases"""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_length_consistency(self, request, dialect_fixture):
        """Test length() consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        length_node = FunctionCallNode(
            node_type="functionCall",
            text="length()",
            function_name="length",
            arguments=[string_node]
        )
        length_node.children = [string_node]

        fragment = translator._translate_string_function(length_node)

        assert isinstance(fragment, SQLFragment)
        assert "length(" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_replace_consistency(self, request, dialect_fixture):
        """Test replace() consistency across databases (method call with 2 arguments)"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Create pattern (explicit argument 1)
        search_node = LiteralNode(
            node_type="literal",
            text="'l'",
            literal_type="string",
            value="l"
        )
        search_node.children = []

        # Create substitution (explicit argument 2)
        replace_node = LiteralNode(
            node_type="literal",
            text="'x'",
            literal_type="string",
            value="x"
        )
        replace_node.children = []

        # Method call: 'hello'.replace('l', 'x')
        replace_func_node = FunctionCallNode(
            node_type="functionCall",
            text="replace()",
            function_name="replace",
            arguments=[search_node, replace_node]  # Only 2 arguments
        )
        replace_func_node.children = [search_node, replace_node]

        fragment = translator._translate_string_function(replace_func_node)

        assert isinstance(fragment, SQLFragment)
        assert "replace(" in fragment.expression
        assert fragment.requires_unnest is False


class TestSubstringEdgeCases:
    """Test substring() edge cases"""

    def test_substring_with_zero_start_duckdb(self, duckdb_dialect):
        """Test substring() with start index 0 (first character) on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        start_node = LiteralNode(
            node_type="literal",
            text="0",
            literal_type="integer",
            value=0
        )
        start_node.children = []

        substring_node = FunctionCallNode(
            node_type="functionCall",
            text="substring()",
            function_name="substring",
            arguments=[string_node, start_node]
        )
        substring_node.children = [string_node, start_node]

        fragment = translator._translate_string_function(substring_node)

        assert isinstance(fragment, SQLFragment)
        assert "substring(" in fragment.expression
        # 0-based index 0 + 1 = 1 for 1-based SQL
        assert "+ 1" in fragment.expression

    def test_substring_with_length_zero_postgresql(self, postgresql_dialect):
        """Test substring() with length 0 on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        start_node = LiteralNode(
            node_type="literal",
            text="1",
            literal_type="integer",
            value=1
        )
        start_node.children = []

        length_node = LiteralNode(
            node_type="literal",
            text="0",
            literal_type="integer",
            value=0
        )
        length_node.children = []

        substring_node = FunctionCallNode(
            node_type="functionCall",
            text="substring()",
            function_name="substring",
            arguments=[string_node, start_node, length_node]
        )
        substring_node.children = [string_node, start_node, length_node]

        fragment = translator._translate_string_function(substring_node)

        assert isinstance(fragment, SQLFragment)
        assert "substring(" in fragment.expression
        assert "0" in fragment.expression
        assert "WHEN (0) <= 0 THEN ''" in fragment.expression

    def test_substring_start_beyond_length_returns_case(self, duckdb_dialect):
        """Ensure start index beyond string length still flows through CASE guard."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        target_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        target_node.children = []

        start_node = LiteralNode(
            node_type="literal",
            text="10",
            literal_type="integer",
            value=10
        )
        start_node.children = []

        method_node = FunctionCallNode(
            node_type="functionCall",
            text="'hello'.substring(10)",
            function_name="substring",
            arguments=[start_node],
            target=target_node
        )
        method_node.children = [target_node, start_node]

        fragment = translator._translate_string_function(method_node)

        assert "CASE" in fragment.expression
        # SP-106-003: Type casting wraps the expression, so check for the key pattern
        assert "+ 1)" in fragment.expression
        assert "substring('hello'" in fragment.expression


class TestIndexOfEdgeCases:
    """Test indexOf() edge cases"""

    def test_indexof_with_empty_search_string_duckdb(self, duckdb_dialect):
        """Test indexOf() with empty search string on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
        )
        search_node.children = []

        indexof_node = FunctionCallNode(
            node_type="functionCall",
            text="indexOf()",
            function_name="indexOf",
            arguments=[search_node]  # Only 1 argument: substring
        )
        indexof_node.children = [search_node]

        fragment = translator._translate_string_function(indexof_node)

        assert isinstance(fragment, SQLFragment)
        assert "strpos(" in fragment.expression

    def test_indexof_substring_not_found_postgresql(self, postgresql_dialect):
        """Test indexOf() when substring is not found on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="'xyz'",
            literal_type="string",
            value="xyz"
        )
        search_node.children = []

        indexof_node = FunctionCallNode(
            node_type="functionCall",
            text="indexOf()",
            function_name="indexOf",
            arguments=[search_node]  # Only 1 argument: substring
        )
        indexof_node.children = [search_node]

        fragment = translator._translate_string_function(indexof_node)

        assert isinstance(fragment, SQLFragment)
        assert "position(" in fragment.expression
        # Should convert to 0-based (subtract 1)
        assert "- 1" in fragment.expression


class TestLengthWithIdentifiers:
    """Test length() with different identifier types"""

    def test_length_with_identifier_postgresql(self, postgresql_dialect):
        """Test length() with identifier on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        identifier_node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )
        identifier_node.children = []

        translator.context.push_path("name")

        length_node = FunctionCallNode(
            node_type="functionCall",
            text="length()",
            function_name="length",
            arguments=[identifier_node]
        )
        length_node.children = [identifier_node]

        fragment = translator._translate_string_function(length_node)

        assert isinstance(fragment, SQLFragment)
        assert "length(" in fragment.expression
        assert "family" in fragment.expression


class TestReplaceEdgeCases:
    """Test replace() edge cases"""

    def test_replace_with_empty_search_duckdb(self, duckdb_dialect):
        """Test replace() with empty search string on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
        )
        search_node.children = []

        replace_node = LiteralNode(
            node_type="literal",
            text="'x'",
            literal_type="string",
            value="x"
        )
        replace_node.children = []

        replace_func_node = FunctionCallNode(
            node_type="functionCall",
            text="replace()",
            function_name="replace",
            arguments=[search_node, replace_node]  # Only 2 arguments: pattern, substitution
        )
        replace_func_node.children = [search_node, replace_node]

        fragment = translator._translate_string_function(replace_func_node)

        assert isinstance(fragment, SQLFragment)
        assert "replace(" in fragment.expression

    def test_replace_with_empty_replacement_postgresql(self, postgresql_dialect):
        """Test replace() with empty replacement string on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello world'",
            literal_type="string",
            value="hello world"
        )
        string_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="' '",
            literal_type="string",
            value=" "
        )
        search_node.children = []

        replace_node = LiteralNode(
            node_type="literal",
            text="''",
            literal_type="string",
            value=""
        )
        replace_node.children = []

        replace_func_node = FunctionCallNode(
            node_type="functionCall",
            text="replace()",
            function_name="replace",
            arguments=[search_node, replace_node]  # Only 2 arguments: pattern, substitution
        )
        replace_func_node.children = [search_node, replace_node]

        fragment = translator._translate_string_function(replace_func_node)

        assert isinstance(fragment, SQLFragment)
        assert "replace(" in fragment.expression

    def test_replace_no_match_duckdb(self, duckdb_dialect):
        """Test replace() when search string is not found on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            literal_type="string",
            value="hello"
        )
        string_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="'xyz'",
            literal_type="string",
            value="xyz"
        )
        search_node.children = []

        replace_node = LiteralNode(
            node_type="literal",
            text="'abc'",
            literal_type="string",
            value="abc"
        )
        replace_node.children = []

        replace_func_node = FunctionCallNode(
            node_type="functionCall",
            text="replace()",
            function_name="replace",
            arguments=[search_node, replace_node]  # Only 2 arguments: pattern, substitution
        )
        replace_func_node.children = [search_node, replace_node]

        fragment = translator._translate_string_function(replace_func_node)

        assert isinstance(fragment, SQLFragment)
        assert "replace(" in fragment.expression


class TestStringFunctionWithComplexExpressions:
    """Test string functions with more complex expressions"""

    def test_substring_with_identifier_and_literal_length_duckdb(self, duckdb_dialect):
        """Test substring() with identifier source and literal length on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        identifier_node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )
        identifier_node.children = []

        translator.context.push_path("name")

        start_node = LiteralNode(
            node_type="literal",
            text="0",
            literal_type="integer",
            value=0
        )
        start_node.children = []

        length_node = LiteralNode(
            node_type="literal",
            text="5",
            literal_type="integer",
            value=5
        )
        length_node.children = []

        substring_node = FunctionCallNode(
            node_type="functionCall",
            text="substring()",
            function_name="substring",
            arguments=[identifier_node, start_node, length_node]
        )
        substring_node.children = [identifier_node, start_node, length_node]

        fragment = translator._translate_string_function(substring_node)

        assert isinstance(fragment, SQLFragment)
        assert "substring(" in fragment.expression
        assert "family" in fragment.expression
        assert "5" in fragment.expression

    def test_indexof_with_special_characters_postgresql(self, postgresql_dialect):
        """Test indexOf() with special characters on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        string_node = LiteralNode(
            node_type="literal",
            text="'hello@world.com'",
            literal_type="string",
            value="hello@world.com"
        )
        string_node.children = []

        search_node = LiteralNode(
            node_type="literal",
            text="'@'",
            literal_type="string",
            value="@"
        )
        search_node.children = []

        indexof_node = FunctionCallNode(
            node_type="functionCall",
            text="indexOf()",
            function_name="indexOf",
            arguments=[search_node]  # Only 1 argument: substring
        )
        indexof_node.children = [search_node]

        fragment = translator._translate_string_function(indexof_node)

        assert isinstance(fragment, SQLFragment)
        assert "position(" in fragment.expression
        assert "@" in fragment.expression
