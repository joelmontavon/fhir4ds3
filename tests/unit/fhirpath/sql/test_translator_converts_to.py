"""Unit tests for convertsTo*() and count() function call translations.

This test file provides comprehensive coverage for path navigation quick wins
implemented in SP-007-012, including:
- Type conversion functions (convertsToBoolean, convertsToInteger, convertsToString)
- Primitive conversion functions (toBoolean, toInteger, toString)
- Collection helper functions (join, exclude, combine, repeat)
- count() function call variant

Tests validate:
- Basic functionality
- Multi-database consistency (DuckDB and PostgreSQL)
- Edge cases (null, empty, nested paths)
- Error handling
- Regression prevention
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import FunctionCallNode, LiteralNode
from fhir4ds.fhirpath.parser import FHIRPathParser

# Import actual dialects for multi-database testing
try:
    from fhir4ds.dialects.duckdb import DuckDBDialect
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

try:
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False


class _StubDialect:
    """Lightweight dialect stub implementing methods used in tests."""

    def __init__(self):
        self.name = "STUB"

    def extract_json_field(self, column: str, path: str) -> str:
        return f"EXTRACT({column}, '{path}')"

    def extract_json_object(self, column: str, path: str) -> str:
        return f"EXTRACT_OBJ({column}, '{path}')"

    def extract_primitive_value(self, column: str, path: str) -> str:
        return f"EXTRACT_PRIM({column}, '{path}')"

    def get_json_type(self, expression: str) -> str:
        return f"TYPEOF({expression})"

    def get_json_array_length(self, column: str, path: str = None) -> str:
        if path:
            return f"ARRAY_LENGTH({column}, '{path}')"
        return f"ARRAY_LENGTH({column})"

    def generate_string_join(self, collection_expr: str, delimiter_expr: str, is_json_collection: bool) -> str:
        return f"join({collection_expr}, {delimiter_expr}, json={is_json_collection})"

    def generate_trim(self, string_expr: str) -> str:
        return f"TRIM({string_expr})"

    def generate_type_cast(self, expression: str, target_type: str) -> str:
        return f"CAST({expression} AS {target_type.upper()})"

    def generate_collection_combine(self, first_collection: str, second_collection: str) -> str:
        return f"combine({first_collection}, {second_collection})"

    def split_string(self, expression: str, delimiter: str) -> str:
        return f"split({expression}, {delimiter}, json=False)"

    def wrap_json_array(self, expression: str) -> str:
        return f"WRAP({expression})"

    def serialize_json_value(self, expression: str) -> str:
        return f"SERIALIZE({expression})"

    def generate_empty_check(self, collection_expr: str) -> str:
        return f"(ARRAY_LENGTH({collection_expr}) = 0)"

    def empty_json_array(self) -> str:
        return "[]"

    def is_json_array(self, expression: str) -> str:
        return f"IS_ARRAY({expression})"

    def enumerate_json_array(self, array_expr: str, value_alias: str, index_alias: str) -> str:
        return f"SELECT {array_expr} AS {value_alias}, 0 AS {index_alias}"

    def aggregate_to_json_array(self, expression: str) -> str:
        return f"AGG({expression})"

    def generate_boolean_not(self, expr: str) -> str:
        return f"NOT({expr})"

    def cast_to_double(self, expression: str) -> str:
        """Cast expression to double for stub dialect."""
        return f"TRY_CAST({expression} AS DOUBLE)"

    def generate_regex_match(self, string_expr: str, regex_pattern: str) -> str:
        """Generate regex matching SQL for stub dialect."""
        return f"REGEXP_MATCHES({string_expr}, {regex_pattern})"


@pytest.fixture()
def translator():
    return ASTToSQLTranslator(_StubDialect(), "Patient")


@pytest.fixture()
def duckdb_translator():
    """Translator with real DuckDB dialect for multi-database testing."""
    if not DUCKDB_AVAILABLE:
        pytest.skip("DuckDB not available")
    dialect = DuckDBDialect(database=":memory:")
    return ASTToSQLTranslator(dialect, "Patient")


@pytest.fixture()
def postgresql_translator():
    """Translator with real PostgreSQL dialect for multi-database testing."""
    if not POSTGRESQL_AVAILABLE:
        pytest.skip("PostgreSQL not available")
    try:
        dialect = PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
        return ASTToSQLTranslator(dialect, "Patient")
    except Exception:
        pytest.skip("PostgreSQL not accessible")


def _make_function(text: str, name: str) -> FunctionCallNode:
    node = FunctionCallNode(
        node_type="functionCall",
        text=text,
        function_name=name,
        arguments=[]
    )
    node.children = []
    return node


class TestLiteralConvertsTo:
    """Literal evaluation for convertsTo* functions."""

    def test_integer_literal_converts_to_boolean_true(self, translator):
        node = _make_function("1.convertsToBoolean()", "convertsToBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_integer_literal_converts_to_boolean_false(self, translator):
        node = _make_function("2.convertsToBoolean()", "convertsToBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "FALSE"

    def test_string_literal_converts_to_integer_true(self, translator):
        node = _make_function("'123'.convertsToInteger()", "convertsToInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_decimal_literal_converts_to_integer_false(self, translator):
        node = _make_function("1.5.convertsToInteger()", "convertsToInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "FALSE"

    def test_boolean_literal_converts_to_integer_true(self, translator):
        node = _make_function("true.convertsToInteger()", "convertsToInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_literal_converts_to_string_true(self, translator):
        node = _make_function("1.convertsToString()", "convertsToString")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"


class TestContextualConvertsTo:
    """Context-based convertsTo* should build CASE expressions."""

    def test_context_boolean_conversion_includes_case(self, translator):
        translator.context.push_path("active")
        node = _make_function("Patient.active.convertsToBoolean()", "convertsToBoolean")

        fragment = translator.visit_function_call(node)

        assert "CASE" in fragment.expression
        assert "extract" in fragment.expression.lower()
        # Ensure dialect-specific trim/lower usage present
        assert "LOWER" in fragment.expression


class TestToFunctions:
    """Tests for primitive toX() conversions."""

    def test_literal_to_boolean_true(self, translator):
        node = _make_function("1.toBoolean()", "toBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_literal_to_boolean_empty(self, translator):
        node = _make_function("2.toBoolean()", "toBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "NULL"

    def test_literal_to_integer_true(self, translator):
        node = _make_function("'5'.toInteger()", "toInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "5"

    def test_literal_to_string(self, translator):
        node = _make_function("true.toString()", "toString")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "'true'"

    def test_context_to_integer_generates_case(self, translator):
        translator.context.push_path("count")
        node = _make_function("Observation.count.toInteger()", "toInteger")
        fragment = translator.visit_function_call(node)
        assert "CASE" in fragment.expression


class TestCollectionHelpers:
    """Tests for join(), exclude(), repeat() helpers."""

    parser = FHIRPathParser()

    @classmethod
    def _translate_expression(cls, translator: ASTToSQLTranslator, expression: str) -> SQLFragment:
        ast = cls.parser.parse(expression).get_ast()
        fragments = translator.translate(ast)
        return fragments[-1]

    def test_join_uses_json_object_path(self, translator):
        fragment = self._translate_expression(translator, "name.given.join(',')")

        assert "join(" in fragment.expression
        assert "EXTRACT_OBJ(resource, '$.name.given')" in fragment.expression
        assert "json=True" in fragment.expression

    def test_join_after_split_uses_native_array(self, translator):
        fragment = self._translate_expression(translator, "name.given.split(',').join(',')")

        assert fragment.expression.startswith("join(")
        assert "json=True" in fragment.expression

    def test_exclude_uses_json_object_path(self, translator):
        fragment = self._translate_expression(translator, "name.given.exclude('Jim')")

        sql = fragment.expression
        assert "EXTRACT_OBJ(resource, '$.name.given')" in sql
        assert "ROW_NUMBER" in sql
        assert "SERIALIZE" in sql

    def test_combine_merges_collections(self, translator):
        fragment = self._translate_expression(translator, "name.given.combine(name.family)")
        assert "select" in fragment.expression.lower()
        assert "order by" in fragment.expression.lower()
        assert fragment.metadata == {"function": "combine", "is_collection": True}

    def test_repeat_literal_returns_expression(self, translator):
        fragment = self._translate_expression(translator, "Patient.name.repeat('test')")
        assert fragment.expression == "'test'"


class TestCountFunctionCall:
    """count() function call should reuse aggregation logic."""

    def test_count_function_generates_sql(self, translator):
        node = _make_function("Patient.name.count()", "count")
        fragment = translator.visit_function_call(node)

        assert isinstance(fragment.expression, str)
        assert fragment.is_aggregate is False
        assert fragment.metadata == {"function": "count", "result_type": "integer"}
        assert "case" in fragment.expression.lower()
        assert "array_length" in fragment.expression.lower()


# ============================================================================
# Multi-Database Consistency Tests
# ============================================================================


class TestMultiDatabaseConvertsTo:
    """Validate convertsTo* functions produce consistent behavior across databases."""

    parser = FHIRPathParser()

    @classmethod
    def _translate_expression(cls, translator: ASTToSQLTranslator, expression: str) -> SQLFragment:
        ast = cls.parser.parse(expression).get_ast()
        fragments = translator.translate(ast)
        return fragments[-1]

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_converts_to_boolean_consistency(self, request, dialect_fixture):
        """Test convertsToBoolean() generates consistent SQL across databases."""
        translator = request.getfixturevalue(dialect_fixture)
        fragment = self._translate_expression(translator, "active.convertsToBoolean()")

        # Both databases should generate CASE expressions with type checking
        assert "CASE" in fragment.expression.upper()
        # Result should be boolean
        assert "TRUE" in fragment.expression or "FALSE" in fragment.expression

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_converts_to_integer_consistency(self, request, dialect_fixture):
        """Test convertsToInteger() generates consistent SQL across databases."""
        translator = request.getfixturevalue(dialect_fixture)
        fragment = self._translate_expression(translator, "count.convertsToInteger()")

        assert "CASE" in fragment.expression.upper()

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_converts_to_string_consistency(self, request, dialect_fixture):
        """Test convertsToString() generates consistent SQL across databases."""
        translator = request.getfixturevalue(dialect_fixture)
        fragment = self._translate_expression(translator, "id.convertsToString()")

        # All types can convert to string
        assert "TRUE" in fragment.expression or "CASE" in fragment.expression.upper()


class TestMultiDatabaseToFunctions:
    """Validate toX() functions produce consistent behavior across databases."""

    parser = FHIRPathParser()

    @classmethod
    def _translate_expression(cls, translator: ASTToSQLTranslator, expression: str) -> SQLFragment:
        ast = cls.parser.parse(expression).get_ast()
        fragments = translator.translate(ast)
        return fragments[-1]

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_to_boolean_consistency(self, request, dialect_fixture):
        """Test toBoolean() generates consistent SQL across databases."""
        translator = request.getfixturevalue(dialect_fixture)
        fragment = self._translate_expression(translator, "active.toBoolean()")

        # Should generate CASE expression with conversion logic
        assert "CASE" in fragment.expression.upper()

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_to_integer_consistency(self, request, dialect_fixture):
        """Test toInteger() generates consistent SQL across databases."""
        translator = request.getfixturevalue(dialect_fixture)
        fragment = self._translate_expression(translator, "count.toInteger()")

        assert "CASE" in fragment.expression.upper()

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_to_string_consistency(self, request, dialect_fixture):
        """Test toString() generates consistent SQL across databases."""
        translator = request.getfixturevalue(dialect_fixture)
        fragment = self._translate_expression(translator, "id.toString()")

        # Should cast value to string
        assert "CAST" in fragment.expression.upper() or "::" in fragment.expression


class TestMultiDatabaseCollectionHelpers:
    """Validate collection helper functions work consistently across databases."""

    parser = FHIRPathParser()

    @classmethod
    def _translate_expression(cls, translator: ASTToSQLTranslator, expression: str) -> SQLFragment:
        ast = cls.parser.parse(expression).get_ast()
        fragments = translator.translate(ast)
        return fragments[-1]

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_join_consistency(self, request, dialect_fixture):
        """Test join() generates database-specific but semantically equivalent SQL."""
        translator = request.getfixturevalue(dialect_fixture)
        fragment = self._translate_expression(translator, "name.given.join(',')")

        # Both should extract JSON and join with delimiter
        # DuckDB and PostgreSQL both use array_to_string
        sql = fragment.expression
        dialect_name = translator.dialect.name

        # Should contain array_to_string or list operation
        assert "array_to_string" in sql or "list" in sql or "json" in sql

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_exclude_consistency(self, request, dialect_fixture):
        """Test exclude() generates database-specific but semantically equivalent SQL."""
        translator = request.getfixturevalue(dialect_fixture)
        fragment = self._translate_expression(translator, "name.given.exclude('Jim')")

        sql = fragment.expression
        dialect_name = translator.dialect.name

        assert "ROW_NUMBER" in sql
        if dialect_name == "DUCKDB":
            assert "json_each" in sql.lower()
        elif dialect_name == "POSTGRESQL":
            assert "jsonb_array_elements" in sql.lower()
        assert "NOT IN" in sql.upper()

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_combine_consistency(self, request, dialect_fixture):
        """Test combine() generates database-specific but semantically equivalent SQL."""
        translator = request.getfixturevalue(dialect_fixture)
        fragment = self._translate_expression(translator, "name.given.combine(name.family)")

        sql = fragment.expression
        dialect_name = translator.dialect.name

        # Both databases implement combine logic (may use UNION ALL or || operator)
        # Should contain merging/concatenation logic
        assert "select" in sql.lower()
        assert "order by" in sql.lower()


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCasesConvertsTo:
    """Test edge cases for convertsTo* functions."""

    def test_converts_to_boolean_with_decimal_literal(self, translator):
        """Test convertsToBoolean() with decimal literal (not 0 or 1)."""
        node = _make_function("2.5.convertsToBoolean()", "convertsToBoolean")
        fragment = translator.visit_function_call(node)
        # Decimal 2.5 is not 0 or 1, so cannot convert to boolean
        assert fragment.expression == "FALSE"

    def test_converts_to_integer_with_string_literal(self, translator):
        """Test convertsToInteger() with non-numeric string."""
        node = _make_function("'abc'.convertsToInteger()", "convertsToInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "FALSE"

    def test_converts_to_integer_with_decimal_string(self, translator):
        """Test convertsToInteger() with decimal string."""
        node = _make_function("'1.5'.convertsToInteger()", "convertsToInteger")
        fragment = translator.visit_function_call(node)
        # Decimal string cannot convert to integer
        assert fragment.expression == "FALSE"

    def test_converts_to_string_always_true_for_literals(self, translator):
        """Test convertsToString() always returns true for literals."""
        for literal in ["1", "true", "'test'", "1.5"]:
            node = _make_function(f"{literal}.convertsToString()", "convertsToString")
            fragment = translator.visit_function_call(node)
            assert fragment.expression == "TRUE"


class TestEdgeCasesToFunctions:
    """Test edge cases for toX() functions."""

    def test_to_boolean_invalid_returns_null(self, translator):
        """Test toBoolean() with invalid value returns NULL."""
        node = _make_function("2.toBoolean()", "toBoolean")
        fragment = translator.visit_function_call(node)
        # 2 is not 0, 1, true, or false, so returns empty (NULL)
        assert fragment.expression == "NULL"

    def test_to_integer_with_non_numeric_string_returns_null(self, translator):
        """Test toInteger() with non-numeric string returns NULL."""
        node = _make_function("'abc'.toInteger()", "toInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "NULL"

    def test_to_integer_with_decimal_string_returns_null(self, translator):
        """Test toInteger() with decimal string returns NULL."""
        node = _make_function("'1.5'.toInteger()", "toInteger")
        fragment = translator.visit_function_call(node)
        # Cannot convert decimal to integer
        assert fragment.expression == "NULL"

    def test_to_string_with_all_types(self, translator):
        """Test toString() works with all literal types."""
        test_cases = [
            ("1", "'1'"),
            ("true", "'true'"),
            ("'test'", "'test'"),
            ("1.5", "'1.5'"),
        ]
        for input_val, expected in test_cases:
            node = _make_function(f"{input_val}.toString()", "toString")
            fragment = translator.visit_function_call(node)
            assert fragment.expression == expected


class TestEdgeCasesCollectionHelpers:
    """Test edge cases for collection helper functions."""

    parser = FHIRPathParser()

    @classmethod
    def _translate_expression(cls, translator: ASTToSQLTranslator, expression: str) -> SQLFragment:
        ast = cls.parser.parse(expression).get_ast()
        fragments = translator.translate(ast)
        return fragments[-1]

    def test_join_with_empty_delimiter(self, translator):
        """Test join() with empty string delimiter."""
        fragment = self._translate_expression(translator, "name.given.join('')")
        assert "join(" in fragment.expression
        assert "''" in fragment.expression or '""' in fragment.expression

    def test_exclude_with_multiple_values(self, translator):
        """Test exclude() removes specified values from collection."""
        fragment = self._translate_expression(translator, "name.given.exclude('John')")
        sql = fragment.expression
        assert "SERIALIZE" in sql
        assert "NOT IN" in sql.upper()
        assert "'John'" in fragment.expression

    def test_combine_with_same_collection(self, translator):
        """Test combine() can merge same collection with itself."""
        fragment = self._translate_expression(translator, "name.given.combine(name.given)")
        assert "select" in fragment.expression.lower()
        assert "order by" in fragment.expression.lower()
        assert fragment.metadata == {"function": "combine", "is_collection": True}

    def test_repeat_with_literal_string(self, translator):
        """Test repeat() with literal string (base case)."""
        fragment = self._translate_expression(translator, "Patient.name.repeat('test')")
        # Literal case: returns the literal expression directly
        assert fragment.expression == "'test'"


# ============================================================================
# Regression Prevention Tests
# ============================================================================


class TestRegressionPrevention:
    """Tests that would have failed before SP-007-012 fixes."""

    parser = FHIRPathParser()

    @classmethod
    def _translate_expression(cls, translator: ASTToSQLTranslator, expression: str) -> SQLFragment:
        ast = cls.parser.parse(expression).get_ast()
        fragments = translator.translate(ast)
        return fragments[-1]

    def test_converts_to_boolean_was_not_implemented(self, translator):
        """Before SP-007-012, convertsToBoolean() raised NotImplementedError."""
        # This should now work without raising
        fragment = self._translate_expression(translator, "true.convertsToBoolean()")
        assert fragment.expression == "TRUE"

    def test_join_was_not_implemented(self, translator):
        """Before SP-007-012, join() raised NotImplementedError."""
        # This should now generate SQL without raising
        fragment = self._translate_expression(translator, "name.given.join(',')")
        assert "join(" in fragment.expression

    def test_exclude_was_not_implemented(self, translator):
        """Before SP-007-012, exclude() raised NotImplementedError."""
        fragment = self._translate_expression(translator, "name.given.exclude('test')")
        sql = fragment.expression
        assert "ROW_NUMBER" in sql
        assert "SERIALIZE" in sql

    def test_combine_was_not_implemented(self, translator):
        """Before SP-007-012, combine() raised NotImplementedError."""
        fragment = self._translate_expression(translator, "name.given.combine(name.family)")
        assert "select" in fragment.expression.lower()
        assert "order by" in fragment.expression.lower()
        assert fragment.metadata == {"function": "combine", "is_collection": True}

    def test_repeat_literal_case_works(self, translator):
        """Before SP-007-012, repeat() raised NotImplementedError."""
        fragment = self._translate_expression(translator, "Patient.name.repeat('literal')")
        assert fragment.expression == "'literal'"

    def test_count_function_call_works(self, translator):
        """Before SP-007-012, count() function call may not have worked correctly."""
        node = _make_function("Patient.name.count()", "count")
        fragment = translator.visit_function_call(node)
        assert fragment.is_aggregate is False
        assert fragment.metadata == {"function": "count", "result_type": "integer"}
        assert "array_length" in fragment.expression.lower()


# ============================================================================
# Additional Coverage Tests
# ============================================================================


class TestConvertsToBoolean:
    """Additional tests for convertsToBoolean() to increase coverage."""

    def test_zero_literal_converts_to_boolean(self, translator):
        """Test 0 literal can convert to boolean (false)."""
        node = _make_function("0.convertsToBoolean()", "convertsToBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_true_literal_converts_to_boolean(self, translator):
        """Test true literal can convert to boolean."""
        node = _make_function("true.convertsToBoolean()", "convertsToBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_false_literal_converts_to_boolean(self, translator):
        """Test false literal can convert to boolean."""
        node = _make_function("false.convertsToBoolean()", "convertsToBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_string_literal_cannot_convert_to_boolean(self, translator):
        """Test string literal cannot convert to boolean."""
        node = _make_function("'test'.convertsToBoolean()", "convertsToBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "FALSE"


class TestConvertsToInteger:
    """Additional tests for convertsToInteger() to increase coverage."""

    def test_zero_literal_converts_to_integer(self, translator):
        """Test 0 literal can convert to integer."""
        node = _make_function("0.convertsToInteger()", "convertsToInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_negative_integer_converts_to_integer(self, translator):
        """Test negative integer can convert to integer."""
        node = _make_function("'-5'.convertsToInteger()", "convertsToInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_false_literal_converts_to_integer(self, translator):
        """Test false literal can convert to integer (0)."""
        node = _make_function("false.convertsToInteger()", "convertsToInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"


class TestToBoolean:
    """Additional tests for toBoolean() to increase coverage."""

    def test_zero_to_boolean(self, translator):
        """Test 0 converts to false."""
        node = _make_function("0.toBoolean()", "toBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "FALSE"

    def test_false_to_boolean(self, translator):
        """Test false stays false."""
        node = _make_function("false.toBoolean()", "toBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "FALSE"

    def test_string_true_to_boolean(self, translator):
        """Test string 'true' converts to true."""
        node = _make_function("'true'.toBoolean()", "toBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "TRUE"

    def test_string_false_to_boolean(self, translator):
        """Test string 'false' converts to false."""
        node = _make_function("'false'.toBoolean()", "toBoolean")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "FALSE"


class TestToInteger:
    """Additional tests for toInteger() to increase coverage."""

    def test_zero_string_to_integer(self, translator):
        """Test '0' string converts to 0."""
        node = _make_function("'0'.toInteger()", "toInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "0"

    def test_negative_string_to_integer(self, translator):
        """Test negative number string converts to integer."""
        node = _make_function("'-10'.toInteger()", "toInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "-10"

    def test_true_to_integer(self, translator):
        """Test true converts to 1."""
        node = _make_function("true.toInteger()", "toInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "1"

    def test_false_to_integer(self, translator):
        """Test false converts to 0."""
        node = _make_function("false.toInteger()", "toInteger")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "0"


class TestToString:
    """Additional tests for toString() to increase coverage."""

    def test_zero_to_string(self, translator):
        """Test 0 converts to '0'."""
        node = _make_function("0.toString()", "toString")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "'0'"

    def test_negative_to_string(self, translator):
        """Test negative number converts to string."""
        node = _make_function("-5.toString()", "toString")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "'-5'"

    def test_false_to_string(self, translator):
        """Test false converts to 'false'."""
        node = _make_function("false.toString()", "toString")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "'false'"

    def test_decimal_to_string(self, translator):
        """Test decimal converts to string."""
        node = _make_function("3.14.toString()", "toString")
        fragment = translator.visit_function_call(node)
        assert fragment.expression == "'3.14'"


# ============================================================================
# SP-101-003: convertsToDateTime and convertsToTime Tests
# ============================================================================


class TestConvertsToDateTime:
    """Tests for convertsToDateTime() function - SP-101-003.

    Tests partial date format support:
    - Year only: '2015'
    - Year-month: '2015-02'
    - Year-month-day: '2015-02-04'
    - With time: '2015-02-04T10:00:00'
    """

    parser = FHIRPathParser()

    @classmethod
    def _translate_expression(cls, translator: ASTToSQLTranslator, expression: str) -> SQLFragment:
        ast = cls.parser.parse(expression).get_ast()
        fragments = translator.translate(ast)
        return fragments[-1]

    def test_string_year_converts_to_datetime(self, translator):
        """Test year-only string '2015'.convertsToDateTime() returns TRUE."""
        node = _make_function("'2015'.convertsToDateTime()", "convertsToDateTime")
        fragment = translator.visit_function_call(node)
        # Valid year literal should evaluate to TRUE
        assert fragment.expression == "TRUE"

    def test_string_month_converts_to_datetime(self, translator):
        """Test year-month string '2015-02'.convertsToDateTime() returns TRUE."""
        node = _make_function("'2015-02'.convertsToDateTime()", "convertsToDateTime")
        fragment = translator.visit_function_call(node)
        # Valid year-month literal should evaluate to TRUE
        assert fragment.expression == "TRUE"

    def test_string_day_converts_to_datetime(self, translator):
        """Test full date string '2015-02-04'.convertsToDateTime() returns TRUE."""
        node = _make_function("'2015-02-04'.convertsToDateTime()", "convertsToDateTime")
        fragment = translator.visit_function_call(node)
        # Valid full date literal should evaluate to TRUE
        assert fragment.expression == "TRUE"

    def test_string_datetime_with_time_converts_to_datetime(self, translator):
        """Test datetime with time '2015-02-04T10:00:00'.convertsToDateTime() returns TRUE."""
        node = _make_function("'2015-02-04T10:00:00'.convertsToDateTime()", "convertsToDateTime")
        fragment = translator.visit_function_call(node)
        # Valid datetime literal should evaluate to TRUE
        assert fragment.expression == "TRUE"

    def test_string_invalid_datetime_format(self, translator):
        """Test invalid format 'not-a-date'.convertsToDateTime() returns FALSE."""
        node = _make_function("'not-a-date'.convertsToDateTime()", "convertsToDateTime")
        fragment = translator.visit_function_call(node)
        # Invalid format should evaluate to FALSE
        assert fragment.expression == "FALSE"

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_converts_to_datetime_uses_dialect_regex_for_context(self, request, dialect_fixture):
        """Test convertsToDateTime() uses dialect.generate_regex_match() for context references."""
        translator = request.getfixturevalue(dialect_fixture)
        # Use a context reference (not a literal) to trigger SQL generation
        fragment = self._translate_expression(translator, "id.convertsToDateTime()")

        # Should contain dialect-specific regex matching
        dialect_name = translator.dialect.name
        assert "CASE" in fragment.expression
        if dialect_name == "DUCKDB":
            assert "regexp_matches" in fragment.expression
        elif dialect_name == "POSTGRESQL":
            assert " ~ " in fragment.expression  # PostgreSQL uses ~ operator

    def test_converts_to_datetime_context_reference_generates_sql(self, translator):
        """Test convertsToDateTime() on context reference generates CASE expression."""
        # Use stub dialect's extract method for context reference
        fragment = self._translate_expression(translator, "id.convertsToDateTime()")
        # Context reference should generate SQL with CASE
        assert "CASE" in fragment.expression
        # Verify dialect method was used (should see regex matching - uppercase for stub)
        assert ("REGEXP_MATCHES" in fragment.expression or "regexp_matches" in fragment.expression or " ~ " in fragment.expression)


class TestConvertsToTime:
    """Tests for convertsToTime() function - SP-101-003.

    Tests partial time format support:
    - Hour only: '14'
    - Hour-minute: '14:34'
    - Hour-minute-second: '14:34:28'
    - With milliseconds: '14:34:28.123'
    """

    parser = FHIRPathParser()

    @classmethod
    def _translate_expression(cls, translator: ASTToSQLTranslator, expression: str) -> SQLFragment:
        ast = cls.parser.parse(expression).get_ast()
        fragments = translator.translate(ast)
        return fragments[-1]

    def test_string_hour_converts_to_time(self, translator):
        """Test hour-only string '14'.convertsToTime() returns TRUE."""
        node = _make_function("'14'.convertsToTime()", "convertsToTime")
        fragment = translator.visit_function_call(node)
        # Valid hour literal should evaluate to TRUE
        assert fragment.expression == "TRUE"

    def test_string_minute_converts_to_time(self, translator):
        """Test hour-minute string '14:34'.convertsToTime() returns TRUE."""
        node = _make_function("'14:34'.convertsToTime()", "convertsToTime")
        fragment = translator.visit_function_call(node)
        # Valid hour-minute literal should evaluate to TRUE
        assert fragment.expression == "TRUE"

    def test_string_second_converts_to_time(self, translator):
        """Test full time string '14:34:28'.convertsToTime() returns TRUE."""
        node = _make_function("'14:34:28'.convertsToTime()", "convertsToTime")
        fragment = translator.visit_function_call(node)
        # Valid full time literal should evaluate to TRUE
        assert fragment.expression == "TRUE"

    def test_string_millisecond_converts_to_time(self, translator):
        """Test time with milliseconds '14:34:28.123'.convertsToTime() returns TRUE."""
        node = _make_function("'14:34:28.123'.convertsToTime()", "convertsToTime")
        fragment = translator.visit_function_call(node)
        # Valid time with milliseconds literal should evaluate to TRUE
        assert fragment.expression == "TRUE"

    def test_string_invalid_time_format(self, translator):
        """Test invalid format 'not-a-time'.convertsToTime() returns FALSE."""
        node = _make_function("'not-a-time'.convertsToTime()", "convertsToTime")
        fragment = translator.visit_function_call(node)
        # Invalid format should evaluate to FALSE
        assert fragment.expression == "FALSE"

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_converts_to_time_uses_dialect_regex_for_context(self, request, dialect_fixture):
        """Test convertsToTime() uses dialect.generate_regex_match() for context references."""
        translator = request.getfixturevalue(dialect_fixture)
        # Use a context reference (not a literal) to trigger SQL generation
        fragment = self._translate_expression(translator, "id.convertsToTime()")

        # Should contain dialect-specific regex matching
        dialect_name = translator.dialect.name
        assert "CASE" in fragment.expression
        if dialect_name == "DUCKDB":
            assert "regexp_matches" in fragment.expression
        elif dialect_name == "POSTGRESQL":
            assert " ~ " in fragment.expression  # PostgreSQL uses ~ operator

    def test_converts_to_time_context_reference_generates_sql(self, translator):
        """Test convertsToTime() on context reference generates CASE expression."""
        # Use stub dialect's extract method for context reference
        fragment = self._translate_expression(translator, "id.convertsToTime()")
        # Context reference should generate SQL with CASE
        assert "CASE" in fragment.expression
        # Verify dialect method was used (should see regex matching - uppercase for stub)
        assert ("REGEXP_MATCHES" in fragment.expression or "regexp_matches" in fragment.expression or " ~ " in fragment.expression)


class TestConvertsToDateTimeTimeEdgeCases:
    """Edge case tests for convertsToDateTime() and convertsToTime()."""

    parser = FHIRPathParser()

    @classmethod
    def _translate_expression(cls, translator: ASTToSQLTranslator, expression: str) -> SQLFragment:
        ast = cls.parser.parse(expression).get_ast()
        fragments = translator.translate(ast)
        return fragments[-1]

    def test_empty_string_converts_to_datetime(self, translator):
        """Test empty string ''.convertsToDateTime() returns FALSE."""
        node = _make_function("''.convertsToDateTime()", "convertsToDateTime")
        fragment = translator.visit_function_call(node)
        # Empty string should evaluate to FALSE
        assert fragment.expression == "FALSE"

    def test_empty_string_converts_to_time(self, translator):
        """Test empty string ''.convertsToTime() returns FALSE."""
        node = _make_function("''.convertsToTime()", "convertsToTime")
        fragment = translator.visit_function_call(node)
        # Empty string should evaluate to FALSE
        assert fragment.expression == "FALSE"

    def test_partial_datetime_with_t_only(self, translator):
        """Test year with T '2015T'.convertsToDateTime() returns TRUE."""
        node = _make_function("'2015T'.convertsToDateTime()", "convertsToDateTime")
        fragment = translator.visit_function_call(node)
        # Pattern allows T with no time components
        assert fragment.expression == "TRUE"

    def test_time_with_single_digit_components(self, translator):
        """Test time with single digit hour '9'.convertsToTime() should return FALSE."""
        node = _make_function("'9'.convertsToTime()", "convertsToTime")
        fragment = translator.visit_function_call(node)
        # Pattern requires 2-digit hour, so single digit should fail
        assert fragment.expression == "FALSE"
