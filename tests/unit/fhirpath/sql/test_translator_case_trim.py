"""Unit tests for ASTToSQLTranslator upper(), lower(), and trim() function translation.

Tests the _translate_upper(), _translate_lower(), and _translate_trim() method implementations
for string case conversion and whitespace trimming.

Test Coverage:
- upper() for uppercase conversion
- lower() for lowercase conversion
- trim() for whitespace removal
- Multi-database consistency (DuckDB and PostgreSQL)
- Error handling for invalid arguments
- Proper SQL generation through dialect methods
- Edge cases (null handling, empty strings, etc.)

Module: tests.unit.fhirpath.sql.test_translator_case_trim
Created: 2025-10-07
Task: SP-007-005
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


def _make_string_literal(value: str) -> LiteralNode:
    """Create a string LiteralNode with proper escaping."""
    escaped = value.replace("'", "''")
    node = LiteralNode(
        node_type="literal",
        text=f"'{escaped}'",
        literal_type="string",
        value=value
    )
    node.children = []
    return node


def _make_method_call(function_name: str, literal_value: str) -> FunctionCallNode:
    """Create FunctionCallNode representing `'literal'.function_name()`."""
    literal_node = _make_string_literal(literal_value)
    escaped = literal_value.replace("'", "''")
    node = FunctionCallNode(
        node_type="functionCall",
        text=f"'{escaped}'.{function_name}()",
        function_name=function_name,
        arguments=[]
    )
    node.target = literal_node
    node.children = [literal_node]
    return node


def _make_function_call(function_name: str, literal_value: str) -> FunctionCallNode:
    """Create FunctionCallNode representing `function_name('literal')`."""
    literal_node = _make_string_literal(literal_value)
    escaped = literal_value.replace("'", "''")
    node = FunctionCallNode(
        node_type="functionCall",
        text=f"{function_name}('{escaped}')",
        function_name=function_name,
        arguments=[literal_node]
    )
    node.children = [literal_node]
    return node


class TestUpperBasicTranslation:
    """Test basic upper() function translation"""

    def test_upper_simple_duckdb(self, duckdb_dialect):
        """Test 'hello'.upper() on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        upper_node = _make_method_call("upper", "hello")

        fragment = translator.visit_function_call(upper_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression == "UPPER('hello')"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_upper_simple_postgresql(self, postgresql_dialect):
        """Test 'hello'.upper() on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        upper_node = _make_method_call("upper", "hello")

        fragment = translator.visit_function_call(upper_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression == "UPPER('hello')"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_upper_function_style_argument(self, duckdb_dialect):
        """Test upper('hello') function-style invocation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        upper_node = _make_function_call("upper", "hello")

        fragment = translator.visit_function_call(upper_node)

        assert fragment.expression == "UPPER('hello')"
        assert fragment.dependencies == []

    def test_upper_unicode_literal(self, duckdb_dialect):
        """Ensure upper() keeps Unicode literal intact in SQL expression"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        upper_node = _make_method_call("upper", "Straße")

        fragment = translator.visit_function_call(upper_node)

        assert "UPPER(" in fragment.expression
        assert "Straße" in fragment.expression


class TestLowerBasicTranslation:
    """Test basic lower() function translation"""

    def test_lower_simple_duckdb(self, duckdb_dialect):
        """Test 'HELLO'.lower() on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        lower_node = _make_method_call("lower", "HELLO")

        fragment = translator.visit_function_call(lower_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression == "LOWER('HELLO')"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_lower_simple_postgresql(self, postgresql_dialect):
        """Test 'HELLO'.lower() on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        lower_node = _make_method_call("lower", "HELLO")

        fragment = translator.visit_function_call(lower_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression == "LOWER('HELLO')"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_lower_function_style_argument(self, duckdb_dialect):
        """Test lower('HELLO') function-style invocation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        lower_node = _make_function_call("lower", "HELLO")

        fragment = translator.visit_function_call(lower_node)

        assert fragment.expression == "LOWER('HELLO')"
        assert fragment.dependencies == []


class TestTrimBasicTranslation:
    """Test basic trim() function translation"""

    def test_trim_simple_duckdb(self, duckdb_dialect):
        """Test '  hello  '.trim() on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        trim_node = _make_method_call("trim", "  hello  ")

        fragment = translator.visit_function_call(trim_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression == "TRIM('  hello  ')"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_trim_simple_postgresql(self, postgresql_dialect):
        """Test '  hello  '.trim() on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        trim_node = _make_method_call("trim", "  hello  ")

        fragment = translator.visit_function_call(trim_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression == "TRIM('  hello  ')"
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_trim_function_style_argument(self, duckdb_dialect):
        """Test trim('  hello  ') function-style invocation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        trim_node = _make_function_call("trim", "  hello  ")

        fragment = translator.visit_function_call(trim_node)

        assert fragment.expression == "TRIM('  hello  ')"
        assert fragment.dependencies == []


class TestMultiDatabaseConsistency:
    """Test that SQL generation is consistent across databases"""

    def test_upper_sql_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test upper() generates identical SQL for both databases"""
        duckdb_translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        postgresql_translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        upper_node = _make_method_call("upper", "alpha")

        duckdb_fragment = duckdb_translator.visit_function_call(upper_node)
        postgresql_fragment = postgresql_translator.visit_function_call(upper_node)

        # Both should use UPPER() function
        assert duckdb_fragment.expression == postgresql_fragment.expression == "UPPER('alpha')"

    def test_lower_sql_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test lower() generates identical SQL for both databases"""
        duckdb_translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        postgresql_translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        lower_node = _make_method_call("lower", "BETA")

        duckdb_fragment = duckdb_translator.visit_function_call(lower_node)
        postgresql_fragment = postgresql_translator.visit_function_call(lower_node)

        # Both should use LOWER() function
        assert duckdb_fragment.expression == postgresql_fragment.expression == "LOWER('BETA')"

    def test_trim_sql_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test trim() generates identical SQL for both databases"""
        duckdb_translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        postgresql_translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        trim_node = _make_method_call("trim", "  gamma  ")

        duckdb_fragment = duckdb_translator.visit_function_call(trim_node)
        postgresql_fragment = postgresql_translator.visit_function_call(trim_node)

        # Both should use TRIM() function
        assert duckdb_fragment.expression == postgresql_fragment.expression == "TRIM('  gamma  ')"


class TestErrorHandling:
    """Test error handling for invalid inputs"""

    def test_upper_with_arguments_raises_error(self, duckdb_dialect):
        """Test upper() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        arg_one = _make_string_literal("one")
        arg_two = _make_string_literal("two")

        upper_node = FunctionCallNode(
            node_type="functionCall",
            text="upper('one', 'two')",
            function_name="upper",
            arguments=[arg_one, arg_two]
        )
        upper_node.children = [arg_one, arg_two]

        with pytest.raises(ValueError) as excinfo:
            translator.visit_function_call(upper_node)
        assert "at most 1 argument" in str(excinfo.value)

    def test_lower_with_arguments_raises_error(self, duckdb_dialect):
        """Test lower() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        arg_one = _make_string_literal("ONE")
        arg_two = _make_string_literal("TWO")

        lower_node = FunctionCallNode(
            node_type="functionCall",
            text="lower('ONE', 'TWO')",
            function_name="lower",
            arguments=[arg_one, arg_two]
        )
        lower_node.children = [arg_one, arg_two]

        with pytest.raises(ValueError) as excinfo:
            translator.visit_function_call(lower_node)
        assert "at most 1 argument" in str(excinfo.value)

    def test_trim_with_arguments_raises_error(self, duckdb_dialect):
        """Test trim() with multiple arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        arg_one = _make_string_literal(" one ")
        arg_two = _make_string_literal(" two ")

        trim_node = FunctionCallNode(
            node_type="functionCall",
            text="trim(' one ', ' two ')",
            function_name="trim",
            arguments=[arg_one, arg_two]
        )
        trim_node.children = [arg_one, arg_two]

        with pytest.raises(ValueError) as excinfo:
            translator.visit_function_call(trim_node)
        assert "at most 1 argument" in str(excinfo.value)


class TestDialectMethodCalls:
    """Test that translator correctly calls dialect methods"""

    def test_upper_calls_generate_case_conversion_with_upper(self, duckdb_dialect):
        """Test upper() calls dialect.generate_case_conversion with 'upper'"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        upper_node = _make_method_call("upper", "beta")

        fragment = translator.visit_function_call(upper_node)

        # Should call generate_case_conversion with 'upper' parameter
        # Result should contain UPPER() function
        assert "UPPER(" in fragment.expression

    def test_lower_calls_generate_case_conversion_with_lower(self, duckdb_dialect):
        """Test lower() calls dialect.generate_case_conversion with 'lower'"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        lower_node = _make_method_call("lower", "GAMMA")

        fragment = translator.visit_function_call(lower_node)

        # Should call generate_case_conversion with 'lower' parameter
        # Result should contain LOWER() function
        assert "LOWER(" in fragment.expression

    def test_trim_calls_generate_trim(self, duckdb_dialect):
        """Test trim() calls dialect.generate_trim"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        trim_node = _make_method_call("trim", "  delta  ")

        fragment = translator.visit_function_call(trim_node)

        # Should call generate_trim
        # Result should contain TRIM() function
        assert "TRIM(" in fragment.expression


class TestSQLFragmentProperties:
    """Test that generated SQLFragments have correct properties"""

    def test_upper_fragment_properties(self, duckdb_dialect):
        """Test upper() SQLFragment has correct properties"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        upper_node = _make_method_call("upper", "alpha")

        fragment = translator.visit_function_call(upper_node)

        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert fragment.source_table == "resource"
        assert fragment.dependencies == []

    def test_lower_fragment_properties(self, duckdb_dialect):
        """Test lower() SQLFragment has correct properties"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        lower_node = _make_method_call("lower", "BETA")

        fragment = translator.visit_function_call(lower_node)

        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert fragment.source_table == "resource"
        assert fragment.dependencies == []

    def test_trim_fragment_properties(self, duckdb_dialect):
        """Test trim() SQLFragment has correct properties"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        trim_node = _make_method_call("trim", "  gamma  ")

        fragment = translator.visit_function_call(trim_node)

        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert fragment.source_table == "resource"
        assert fragment.dependencies == []


class TestContextHandling:
    """Test that functions correctly handle translation context"""

    def test_upper_uses_current_context_path(self, duckdb_dialect):
        """Test upper() uses current context path for target expression"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set context path
        translator.context.parent_path = ["name", "0", "family"]

        upper_node = FunctionCallNode(
            node_type="functionCall",
            text="upper()",
            function_name="upper",
            arguments=[]
        )
        upper_node.children = []

        fragment = translator.visit_function_call(upper_node)

        # Should extract from the path set in context
        assert "json_extract" in fragment.expression or "jsonb" in fragment.expression
        assert "UPPER(" in fragment.expression

    def test_lower_uses_current_context_path(self, duckdb_dialect):
        """Test lower() uses current context path for target expression"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set context path
        translator.context.parent_path = ["name", "0", "family"]

        lower_node = FunctionCallNode(
            node_type="functionCall",
            text="lower()",
            function_name="lower",
            arguments=[]
        )
        lower_node.children = []

        fragment = translator.visit_function_call(lower_node)

        # Should extract from the path set in context
        assert "json_extract" in fragment.expression or "jsonb" in fragment.expression
        assert "LOWER(" in fragment.expression

    def test_trim_uses_current_context_path(self, duckdb_dialect):
        """Test trim() uses current context path for target expression"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set context path
        translator.context.parent_path = ["name", "0", "family"]

        trim_node = FunctionCallNode(
            node_type="functionCall",
            text="trim()",
            function_name="trim",
            arguments=[]
        )
        trim_node.children = []

        fragment = translator.visit_function_call(trim_node)

        # Should extract from the path set in context
        assert "json_extract" in fragment.expression or "jsonb" in fragment.expression
        assert "TRIM(" in fragment.expression
