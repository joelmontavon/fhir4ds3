"""
Unit tests for DuckDB dialect implementation.

Tests DuckDB-specific SQL generation while validating thin dialect
architecture compliance: only syntax differences, no business logic.
"""

import pytest
from typing import Sequence
from unittest.mock import Mock, patch

from fhir4ds.dialects.duckdb import DuckDBDialect


class TestDuckDBDialect:
    @staticmethod
    def _assert_contains_all(text: str, substrings: Sequence[str]) -> None:
        for substring in substrings:
            assert substring in text, f"Expected '{substring}' in:\n{text}"

    @pytest.fixture
    def mock_connection(self):
        """Create mock DuckDB connection."""
        mock_conn = Mock()
        # Properly chain return values: execute() returns a result object with fetchall()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        return mock_conn

    @pytest.fixture
    def dialect(self, mock_connection):
        """Create DuckDB dialect with mocked connection."""
        with patch('fhir4ds.dialects.duckdb.duckdb') as mock_duckdb:
            mock_duckdb.connect.return_value = mock_connection
            dialect = DuckDBDialect(connection=mock_connection)
            return dialect

    def test_initialization(self, dialect):
        """Test DuckDB dialect initialization."""
        assert dialect.name == "DUCKDB"
        assert dialect.supports_jsonb is False
        assert dialect.supports_json_functions is True
        assert dialect.json_type == "JSON"
        assert dialect.cast_syntax == "::"
        assert dialect.quote_char == '"'

    def test_initialization_without_duckdb(self):
        """Test initialization fails without DuckDB available."""
        with patch('fhir4ds.dialects.duckdb.DUCKDB_AVAILABLE', False):
            with pytest.raises(ImportError, match="DuckDB is required"):
                DuckDBDialect()

    def test_get_connection(self, dialect, mock_connection):
        """Test connection retrieval."""
        assert dialect.get_connection() is mock_connection

    def test_execute_query_success(self, dialect, mock_connection):
        """Test successful query execution."""
        mock_connection.execute.return_value.fetchall.return_value = [('test',)]

        result = dialect.execute_query("SELECT 1")
        assert result == [('test',)]
        # Verify the query was called (note: dialect init calls execute once for JSON setup)
        assert mock_connection.execute.call_args_list[-1] == (("SELECT 1",),)

    def test_execute_query_failure(self, dialect, mock_connection):
        """Test query execution failure handling."""
        mock_connection.execute.side_effect = Exception("Query failed")

        with pytest.raises(Exception, match="Query failed"):
            dialect.execute_query("INVALID SQL")

    def test_extract_json_field(self, dialect):
        """Test JSON field extraction as text."""
        result = dialect.extract_json_field("resource", "$.name")
        assert result == "json_extract_string(resource, '$.name')"

    def test_extract_json_object(self, dialect):
        """Test JSON object extraction preserving structure."""
        result = dialect.extract_json_object("resource", "$.address")
        assert result == "json_extract(resource, '$.address')"

    def test_check_json_exists(self, dialect):
        """Test JSON path existence check."""
        result = dialect.check_json_exists("resource", "$.id")
        assert result == "(json_extract(resource, '$.id') IS NOT NULL)"

    def test_get_json_type(self, dialect):
        """Test JSON type detection."""
        result = dialect.get_json_type("resource")
        assert result == "json_type(resource)"

    def test_get_json_array_length(self, dialect):
        """Test JSON array length calculation."""
        # Without path
        result = dialect.get_json_array_length("array_col")
        assert result == "json_array_length(CAST(array_col AS JSON))"

        # With path
        result = dialect.get_json_array_length("resource", "$.name")
        assert result == "json_array_length(CAST(json_extract(resource, '$.name') AS JSON))"

    def test_unnest_json_array(self, dialect):
        """Test JSON array unnesting for DuckDB."""
        result = dialect.unnest_json_array("resource", "$.name", "name_item")
        assert result == "UNNEST(json_extract(resource, '$.name')) AS name_item"

        # Test with different path
        result = dialect.unnest_json_array("resource", "$.address", "addr_item")
        assert result == "UNNEST(json_extract(resource, '$.address')) AS addr_item"

    def test_generate_lateral_unnest(self, dialect):
        """Test LATERAL UNNEST generation."""
        result = dialect.generate_lateral_unnest(
            source_table="patient_resources",
            array_column="json_extract(resource, '$.name')",
            alias="name_item",
        )
        assert result == "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item"

        # Ensure source_table parameter presence does not alter syntax
        result = dialect.generate_lateral_unnest(
            source_table="ignored_cte",
            array_column="json_extract(resource, '$.telecom')",
            alias="telecom_item",
        )
        assert result == "LATERAL UNNEST(json_extract(resource, '$.telecom')) AS telecom_item"

    def test_iterate_json_array(self, dialect):
        """Test JSON array iteration."""
        result = dialect.iterate_json_array("resource", "$.telecom")
        assert result == "json_each(resource, '$.telecom')"

    def test_aggregate_to_json_array(self, dialect):
        """Test JSON array aggregation."""
        result = dialect.aggregate_to_json_array("name")
        assert result == "CAST(to_json(list(name)) AS JSON)"

    def test_create_json_array(self, dialect):
        """Test JSON array creation."""
        # Empty array
        result = dialect.create_json_array()
        assert result == "json_array()"

        # Array with elements
        result = dialect.create_json_array("'John'", "'Jane'")
        assert result == "json_array('John', 'Jane')"

    def test_create_json_object(self, dialect):
        """Test JSON object creation."""
        # Empty object
        result = dialect.create_json_object()
        assert result == "json_object()"

        # Object with key-value pairs
        result = dialect.create_json_object("'name'", "'John'", "'age'", "30")
        assert result == "json_object('name', 'John', 'age', 30)"

    def test_string_concat(self, dialect):
        """Test string concatenation."""
        result = dialect.string_concat("first_name", "last_name")
        assert result == "(first_name || last_name)"

    def test_substring(self, dialect):
        """Test substring extraction."""
        result = dialect.substring("name", "1", "5")
        assert result == "SUBSTRING(name, (1) + 1, 5)"

    def test_split_string(self, dialect):
        """Test string splitting."""
        result = dialect.split_string("full_name", "' '")
        assert result == "string_split(CAST(full_name AS VARCHAR), ' ')"

    def test_try_cast(self, dialect):
        """Test safe type conversion."""
        result = dialect.try_cast("value", "INTEGER")
        assert result == "TRY_CAST(value AS INTEGER)"

    def test_cast_to_timestamp(self, dialect):
        """Test timestamp casting."""
        result = dialect.cast_to_timestamp("date_string")
        assert result == "CAST(date_string AS TIMESTAMP)"

    def test_cast_to_time(self, dialect):
        """Test time casting."""
        result = dialect.cast_to_time("time_string")
        assert result == "CAST(time_string AS TIME)"

    def test_cast_to_double(self, dialect):
        """Test double precision casting."""
        result = dialect.cast_to_double("numeric_expr")
        assert result == "CAST(numeric_expr AS DOUBLE)"

    def test_is_finite(self, dialect):
        """Test finite number check."""
        result = dialect.is_finite("numeric_expr")
        assert result == "isfinite(numeric_expr)"

    def test_generate_math_function(self, dialect):
        """Test mathematical function generation."""
        # Test known functions
        assert dialect.generate_math_function("sqrt", "16") == "sqrt(16)"
        assert dialect.generate_math_function("ln", "x") == "ln(x)"
        assert dialect.generate_math_function("power", "2", "3") == "pow(2, 3)"
        assert dialect.generate_math_function("ceiling", "3.7") == "ceil(3.7)"

        # Test unknown function (should pass through)
        assert dialect.generate_math_function("unknown", "x") == "unknown(x)"

    def test_generate_power_operation(self, dialect):
        """Test power operation generation."""
        result = dialect.generate_power_operation("base", "exponent")
        assert result == "pow(base, exponent)"

    def test_generate_string_function_substring_with_length(self, dialect):
        """Test substring function with start and length."""
        result = dialect.generate_string_function("substring", "name", "1", "5")
        assert result == "substring(name, 1, 5)"

    def test_generate_string_function_substring_without_length(self, dialect):
        """Test substring function with only start position."""
        result = dialect.generate_string_function("substring", "text", "3")
        assert result == "substring(text, 3)"

    def test_generate_string_function_indexof(self, dialect):
        """Test indexOf function for finding substring position."""
        result = dialect.generate_string_function("indexOf", "full_text", "'search'")
        # DuckDB strpos returns 1-based index, we subtract 1 for 0-based FHIRPath
        assert result == "(strpos(full_text, 'search') - 1)"

    def test_generate_string_function_length(self, dialect):
        """Test length function for string length."""
        result = dialect.generate_string_function("length", "text")
        assert result == "length(text)"

    def test_generate_string_function_replace(self, dialect):
        """Test replace function for substring replacement."""
        result = dialect.generate_string_function("replace", "text", "'old'", "'new'")
        assert result == "replace(text, 'old', 'new')"

    def test_generate_string_function_invalid_args_substring(self, dialect):
        """Test substring function with invalid argument count."""
        with pytest.raises(ValueError, match="substring\\(\\) requires 2 or 3 arguments"):
            dialect.generate_string_function("substring", "text")

    def test_generate_string_function_invalid_args_indexof(self, dialect):
        """Test indexOf function with invalid argument count."""
        with pytest.raises(ValueError, match="indexOf\\(\\) requires 2 arguments"):
            dialect.generate_string_function("indexOf", "text")

    def test_generate_string_function_invalid_args_length(self, dialect):
        """Test length function with invalid argument count."""
        with pytest.raises(ValueError, match="length\\(\\) requires 1 argument"):
            dialect.generate_string_function("length")

    def test_generate_string_function_invalid_args_replace(self, dialect):
        """Test replace function with invalid argument count."""
        with pytest.raises(ValueError, match="replace\\(\\) requires 3 arguments"):
            dialect.generate_string_function("replace", "text", "'old'")

    def test_generate_string_function_unknown(self, dialect):
        """Test unknown string function raises error."""
        with pytest.raises(ValueError, match="Unknown string function: unknown_func"):
            dialect.generate_string_function("unknown_func", "arg")

    def test_generate_current_timestamp(self, dialect):
        """Test current timestamp generation."""
        result = dialect.generate_current_timestamp()
        assert result == "now()"

    def test_generate_current_date(self, dialect):
        """Test current date generation."""
        result = dialect.generate_current_date()
        assert result == "current_date"

    def test_generate_date_diff(self, dialect):
        """Test date difference generation."""
        result = dialect.generate_date_diff("day", "start_date", "end_date")
        assert result == "DATE_DIFF('day', start_date, end_date)"

    def test_generate_aggregate_function(self, dialect):
        """Test aggregate function generation."""
        # Basic function
        result = dialect.generate_aggregate_function("sum", "amount")
        assert result == "SUM(amount)"

        # Function with mapping
        result = dialect.generate_aggregate_function("variance", "value")
        assert result == "VAR_SAMP(value)"

        # With DISTINCT
        result = dialect.generate_aggregate_function("count", "id", distinct=True)
        assert result == "COUNT(DISTINCT id)"

        # With filter condition
        result = dialect.generate_aggregate_function("sum", "amount", filter_condition="amount > 0")
        assert result == "SUM(amount) FILTER (WHERE amount > 0)"

    def test_generate_where_clause_filter(self, dialect):
        """Test WHERE clause filtering for collections."""
        result = dialect.generate_where_clause_filter("names", "length > 3")
        expected = """(
            SELECT json_group_array(item.value)
            FROM json_each(names) AS item
            WHERE length > 3
        )"""
        assert result.strip().replace(" ", "").replace("\n", "") == expected.strip().replace(" ", "").replace("\n", "")

    def test_generate_select_transformation(self, dialect):
        """Test SELECT transformation for collections."""
        result = dialect.generate_select_transformation("persons", "name")
        expected = """(
            SELECT json_group_array(json_extract(value, '$.name'))
            FROM json_each(persons)
        )"""
        assert result.strip().replace(" ", "").replace("\n", "") == expected.strip().replace(" ", "").replace("\n", "")

    def test_generate_string_join(self, dialect):
        """Test string join generation."""
        result_json = dialect.generate_string_join("names_json", "','", True)
        assert "from_json" in result_json
        result_array = dialect.generate_string_join("list_expr", "','", False)
        assert "from_json" not in result_array

    def test_generate_collection_combine(self, dialect):
        """Test collection combination."""
        result = dialect.generate_collection_combine("list1", "list2")
        # Test that it contains the key parts we expect
        assert "json_group_array" in result
        assert "json_each" in result
        assert "UNION ALL" in result

    def test_generate_collection_exclude(self, dialect):
        """Test collection exclusion generation."""
        result = dialect.generate_collection_exclude("names_json", "'Jim'")
        assert "list_filter" in result
        assert "from_json" in result

    def test_wrap_json_array(self, dialect):
        """Test scalar wrapping helper."""
        result = dialect.wrap_json_array("value_expr")
        assert result == "json_array(value_expr)"

    def test_serialize_json_value(self, dialect):
        """Test JSON value serialization helper."""
        assert dialect.serialize_json_value("value_expr") == "CAST(value_expr AS VARCHAR)"

    def test_empty_json_array(self, dialect):
        """Test empty JSON array helper."""
        assert dialect.empty_json_array() == "json_array()"

    def test_is_json_array(self, dialect):
        """Test JSON array predicate helper."""
        predicate = dialect.is_json_array("candidate_expr")
        assert predicate == "(json_type(CAST(candidate_expr AS JSON)) = 'ARRAY')"

    def test_enumerate_json_array(self, dialect):
        """Test JSON array enumeration helper."""
        enumeration_sql = dialect.enumerate_json_array("array_expr", "val", "idx")
        assert "json_each(array_expr)" in enumeration_sql
        assert "AS val" in enumeration_sql
        assert "AS idx" in enumeration_sql

    def test_generate_exists_check(self, dialect):
        """Test exists/empty check generation."""
        # Collection check
        result = dialect.generate_exists_check("array_col", True)
        assert result == "(json_array_length(array_col) > 0)"

        # Non-collection check
        result = dialect.generate_exists_check("value", False)
        assert result == "(value IS NOT NULL)"

    def test_generate_logical_combine(self, dialect):
        """Test logical condition combination."""
        result = dialect.generate_logical_combine("condition1", "and", "condition2")
        assert result == "(condition1) AND (condition2)"

        result = dialect.generate_logical_combine("condition1", "or", "condition2")
        assert result == "(condition1) OR (condition2)"

    def test_generate_conditional_expression(self, dialect):
        """Test conditional expression generation."""
        result = dialect.generate_conditional_expression("x > 0", "positive", "non_positive")
        assert result == "CASE WHEN x > 0 THEN positive ELSE non_positive END"

    def test_generate_date_literal(self, dialect):
        """Test date literal generation for DuckDB."""
        result = dialect.generate_date_literal("2024-01-15")
        assert result == "DATE '2024-01-15'"

    def test_generate_datetime_literal(self, dialect):
        """Test datetime literal generation for DuckDB."""
        result = dialect.generate_datetime_literal("2024-01-15T14:30:00")
        assert result == "TIMESTAMP '2024-01-15 14:30:00'"

    def test_generate_comparison_equals(self, dialect):
        """Test comparison operator generation for equals."""
        result = dialect.generate_comparison("age", "=", "18")
        assert result == "(age = 18)"

    def test_generate_comparison_not_equals(self, dialect):
        """Test comparison operator generation for not equals."""
        result = dialect.generate_comparison("status", "!=", "'active'")
        assert result == "(status != 'active')"

    def test_generate_comparison_less_than(self, dialect):
        """Test comparison operator generation for less than."""
        result = dialect.generate_comparison("value", "<", "100")
        assert result == "(value < 100)"

    def test_generate_comparison_greater_than(self, dialect):
        """Test comparison operator generation for greater than."""
        result = dialect.generate_comparison("count", ">", "0")
        assert result == "(count > 0)"

    def test_generate_comparison_less_or_equal(self, dialect):
        """Test comparison operator generation for less than or equal."""
        result = dialect.generate_comparison("score", "<=", "50")
        assert result == "(score <= 50)"

    def test_generate_comparison_greater_or_equal(self, dialect):
        """Test comparison operator generation for greater than or equal."""
        result = dialect.generate_comparison("age", ">=", "21")
        assert result == "(age >= 21)"

    @pytest.mark.parametrize("left,op,right,expected", [
        ("x", "=", "y", "(x = y)"),
        ("a", "!=", "b", "(a != b)"),
        ("m", "<", "n", "(m < n)"),
        ("p", ">", "q", "(p > q)"),
        ("s", "<=", "t", "(s <= t)"),
        ("u", ">=", "v", "(u >= v)"),
    ])
    def test_generate_comparison_parametrized(self, dialect, left, op, right, expected):
        """Test comparison generation with various operators."""
        result = dialect.generate_comparison(left, op, right)
        assert result == expected

    # Type operation tests

    def test_generate_type_check_string(self, dialect):
        """Test type checking for String type."""
        result = dialect.generate_type_check("field_value", "String")
        self._assert_contains_all(result, [
            "WHEN field_value IS NULL THEN false",
            "json_type(field_value)",
            "typeof(field_value)",
            "'VARCHAR'",
        ])

    def test_generate_type_check_integer(self, dialect):
        """Test type checking for Integer type."""
        result = dialect.generate_type_check("age", "Integer")
        self._assert_contains_all(result, [
            "WHEN age IS NULL THEN false",
            "json_type(age)",
            "typeof(age)",
            "'INTEGER'",
        ])

    def test_generate_type_check_decimal(self, dialect):
        """Test type checking for Decimal type."""
        result = dialect.generate_type_check("amount", "Decimal")
        self._assert_contains_all(result, [
            "WHEN amount IS NULL THEN false",
            "json_type(amount)",
            "typeof(amount)",
            "'DOUBLE'",
        ])

    def test_generate_type_check_boolean(self, dialect):
        """Test type checking for Boolean type."""
        result = dialect.generate_type_check("flag", "Boolean")
        self._assert_contains_all(result, [
            "WHEN flag IS NULL THEN false",
            "json_type(flag)",
            "typeof(flag)",
            "'BOOLEAN'",
        ])

    def test_generate_type_check_datetime(self, dialect):
        """Test type checking for DateTime type."""
        result = dialect.generate_type_check("timestamp_value", "DateTime")
        self._assert_contains_all(result, [
            "WHEN timestamp_value IS NULL THEN false",
            "json_type(timestamp_value)",
            "typeof(timestamp_value)",
            "'TIMESTAMP'",
        ])

    def test_generate_type_check_date(self, dialect):
        """Test type checking for Date type."""
        result = dialect.generate_type_check("date_value", "Date")
        self._assert_contains_all(result, [
            "WHEN date_value IS NULL THEN false",
            "json_type(date_value)",
            "typeof(date_value)",
            "'DATE'",
        ])

    def test_generate_type_check_time(self, dialect):
        """Test type checking for Time type."""
        result = dialect.generate_type_check("time_value", "Time")
        self._assert_contains_all(result, [
            "WHEN time_value IS NULL THEN false",
            "json_type(time_value)",
            "typeof(time_value)",
            "'TIME'",
        ])

    def test_generate_type_check_unknown_type(self, dialect):
        """Test type checking for unknown type returns false."""
        result = dialect.generate_type_check("value", "UnknownType")
        assert result == "false"

    def test_generate_type_cast_string(self, dialect):
        """Test type casting to String."""
        result = dialect.generate_type_cast("value", "String")
        assert result == "TRY_CAST(value AS VARCHAR)"

    def test_generate_type_cast_integer(self, dialect):
        """Test type casting to Integer."""
        result = dialect.generate_type_cast("value", "Integer")
        assert result == "TRY_CAST(value AS INTEGER)"

    def test_generate_type_cast_decimal(self, dialect):
        """Test type casting to Decimal."""
        result = dialect.generate_type_cast("value", "Decimal")
        assert result == "TRY_CAST(value AS DOUBLE)"

    def test_generate_type_cast_boolean(self, dialect):
        """Test type casting to Boolean."""
        result = dialect.generate_type_cast("value", "Boolean")
        assert result == "TRY_CAST(value AS BOOLEAN)"

    def test_generate_type_cast_datetime(self, dialect):
        """Test type casting to DateTime."""
        result = dialect.generate_type_cast("value", "DateTime")
        assert result == "TRY_CAST(value AS TIMESTAMP)"

    def test_generate_type_cast_date(self, dialect):
        """Test type casting to Date."""
        result = dialect.generate_type_cast("value", "Date")
        assert result == "TRY_CAST(value AS DATE)"

    def test_generate_type_cast_time(self, dialect):
        """Test type casting to Time."""
        result = dialect.generate_type_cast("value", "Time")
        assert result == "TRY_CAST(value AS TIME)"

    def test_generate_type_cast_unknown_type(self, dialect):
        """Test type casting to unknown type returns NULL."""
        result = dialect.generate_type_cast("value", "UnknownType")
        assert result == "NULL"

    def test_generate_collection_type_filter_string(self, dialect):
        """Test collection filtering for String type."""
        result = dialect.generate_collection_type_filter("items", "String")
        self._assert_contains_all(result, [
            "json_group_array",
            "json_each",
            "elem.\"type\"",
            "'VARCHAR'",
        ])

    def test_generate_collection_type_filter_integer(self, dialect):
        """Test collection filtering for Integer type."""
        result = dialect.generate_collection_type_filter("numbers", "Integer")
        self._assert_contains_all(result, [
            "json_group_array",
            "json_each",
            "'INTEGER'",
        ])

    def test_generate_collection_type_filter_decimal(self, dialect):
        """Test collection filtering for Decimal type."""
        result = dialect.generate_collection_type_filter("amounts", "Decimal")
        self._assert_contains_all(result, [
            "json_group_array",
            "json_each",
            "'DOUBLE'",
        ])

    def test_generate_collection_type_filter_boolean(self, dialect):
        """Test collection filtering for Boolean type."""
        result = dialect.generate_collection_type_filter("flags", "Boolean")
        self._assert_contains_all(result, [
            "json_group_array",
            "json_each",
            "'BOOLEAN'",
        ])

    def test_generate_collection_type_filter_datetime(self, dialect):
        """Test collection filtering for DateTime type."""
        result = dialect.generate_collection_type_filter("timestamps", "DateTime")
        self._assert_contains_all(result, [
            "json_group_array",
            "json_each",
            "elem.\"type\" = 'VARCHAR'",
            "json_extract_string(elem.value, '$')",
            "REGEXP",
        ])

    def test_generate_collection_type_filter_date(self, dialect):
        """Test collection filtering for Date type."""
        result = dialect.generate_collection_type_filter("dates", "Date")
        self._assert_contains_all(result, [
            "json_group_array",
            "json_each",
            "elem.\"type\" = 'VARCHAR'",
            "json_extract_string(elem.value, '$')",
            "REGEXP",
        ])

    def test_generate_collection_type_filter_time(self, dialect):
        """Test collection filtering for Time type."""
        result = dialect.generate_collection_type_filter("times", "Time")
        self._assert_contains_all(result, [
            "json_group_array",
            "json_each",
            "elem.\"type\" = 'VARCHAR'",
            "json_extract_string(elem.value, '$')",
            "REGEXP",
        ])

    def test_generate_collection_type_filter_unknown_type(self, dialect):
        """Test collection filtering for unknown type returns empty array."""
        result = dialect.generate_collection_type_filter("items", "UnknownType")
        assert result == "[]"

    @pytest.mark.parametrize("fhirpath_type,duckdb_type", [
        ("String", "VARCHAR"),
        ("Integer", "INTEGER"),
        ("Decimal", "DOUBLE"),
        ("Boolean", "BOOLEAN"),
        ("DateTime", "TIMESTAMP"),
        ("Date", "DATE"),
        ("Time", "TIME"),
    ])
    def test_type_mapping_consistency(self, dialect, fhirpath_type, duckdb_type):
        """Test that type mapping is consistent across all type operations."""
        # Check that type_check uses the correct type
        type_check = dialect.generate_type_check("value", fhirpath_type)
        assert duckdb_type in type_check

        # Check that type_cast uses the correct type
        type_cast = dialect.generate_type_cast("value", fhirpath_type)
        assert f"TRY_CAST(value AS {duckdb_type})" == type_cast

        # Check that collection_type_filter uses the correct type
        collection_filter = dialect.generate_collection_type_filter("items", fhirpath_type)
        if duckdb_type in {"TIMESTAMP", "DATE", "TIME"}:
            assert "json_extract_string" in collection_filter
            assert "REGEXP" in collection_filter
        else:
            assert duckdb_type in collection_filter


class TestDuckDBDialectIntegration:
    """Integration tests for DuckDB dialect with actual DuckDB (if available)."""

    @pytest.fixture
    def real_dialect(self):
        """Create real DuckDB dialect if DuckDB is available."""
        try:
            import duckdb
            return DuckDBDialect()
        except ImportError:
            pytest.skip("DuckDB not available for integration tests")

    def test_real_json_operations(self, real_dialect):
        """Test actual JSON operations with DuckDB."""
        # Test with real DuckDB to ensure our SQL is valid
        test_sql = """
        SELECT
            json_extract_string('{"name": "John", "age": 30}', '$.name') as name,
            json_extract('{"items": [1, 2, 3]}', '$.items') as items,
            json_type('{"test": true}') as type_check
        """

        try:
            result = real_dialect.execute_query(test_sql)
            assert len(result) == 1
            assert result[0][0] == "John"  # name
            # Other assertions would depend on DuckDB JSON format
        except Exception as e:
            pytest.fail(f"Real DuckDB operation failed: {e}")

    def test_real_aggregation_operations(self, real_dialect):
        """Test actual aggregation operations with DuckDB."""
        test_sql = """
        WITH test_data AS (
            SELECT unnest(['a', 'b', 'c']) as value
        )
        SELECT json_group_array(value) as aggregated
        FROM test_data
        """

        try:
            result = real_dialect.execute_query(test_sql)
            assert len(result) == 1
            # Should return a JSON array
        except Exception as e:
            pytest.fail(f"Real DuckDB aggregation failed: {e}")
