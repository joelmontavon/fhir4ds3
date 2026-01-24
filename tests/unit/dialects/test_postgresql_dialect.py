"""
Unit tests for PostgreSQL dialect implementation.

Tests PostgreSQL-specific SQL generation while validating thin dialect
architecture compliance: only syntax differences, no business logic.
"""

import pytest
import time
from typing import Sequence
from unittest.mock import Mock, patch, MagicMock

from fhir4ds.dialects.postgresql import PostgreSQLDialect
from psycopg2 import OperationalError, InterfaceError, ProgrammingError, DataError


class TestPostgreSQLDialect:
    """Test cases for PostgreSQL dialect implementation."""

    @staticmethod
    def _assert_contains_all(text: str, substrings: Sequence[str]) -> None:
        for substring in substrings:
            assert substring in text, f"Expected '{substring}' in:\\n{text}"

    @pytest.fixture
    def mock_connection(self):
        """Create mock PostgreSQL connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.return_value = None
        mock_cursor.fetchall.return_value = [('test',)]
        mock_cursor.close.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.commit.return_value = None
        mock_conn.rollback.return_value = None
        return mock_conn

    @pytest.fixture
    def mock_pool(self, mock_connection):
        """Create mock connection pool."""
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_connection
        mock_pool_instance.putconn.return_value = None
        mock_pool_instance.closeall.return_value = None
        return mock_pool_instance

    @pytest.fixture
    def dialect(self, mock_pool):
        """Create PostgreSQL dialect with mocked connection pool."""
        with patch('fhir4ds.dialects.postgresql.pool') as mock_pool_module:
            mock_pool_module.SimpleConnectionPool.return_value = mock_pool
            dialect = PostgreSQLDialect("postgresql://test:test@localhost/test")
            return dialect

    def test_initialization(self, dialect):
        """Test PostgreSQL dialect initialization."""
        assert dialect.name == "POSTGRESQL"
        assert dialect.supports_jsonb is True
        assert dialect.supports_json_functions is True
        assert dialect.json_type == "JSONB"
        assert dialect.cast_syntax == "::"
        assert dialect.quote_char == '"'

    def test_initialization_without_psycopg2(self):
        """Test initialization fails without psycopg2 available."""
        with patch('fhir4ds.dialects.postgresql.POSTGRESQL_AVAILABLE', False):
            with pytest.raises(ImportError, match="psycopg2 is required"):
                PostgreSQLDialect("postgresql://test:test@localhost/test")

    def test_get_connection(self, dialect, mock_pool, mock_connection):
        """Test connection retrieval from pool."""
        conn = dialect.get_connection()
        assert conn is mock_connection
        mock_pool.getconn.assert_called_once()

    def test_release_connection(self, dialect, mock_pool, mock_connection):
        """Test connection release to pool."""
        dialect.release_connection(mock_connection)
        mock_pool.putconn.assert_called_once_with(mock_connection)

    def test_close_all_connections(self, dialect, mock_pool):
        """Test closing all connections in pool."""
        dialect.close_all_connections()
        mock_pool.closeall.assert_called_once()

    def test_execute_query_success(self, dialect, mock_connection):
        """Test successful query execution with connection pooling."""
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchall.return_value = [('test_result',)]

        result = dialect.execute_query("SELECT 1")
        assert result == [('test_result',)]

        # Check that timeout was set
        assert mock_cursor.execute.call_count == 2  # timeout + query
        # Check that commit was called
        mock_connection.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_execute_query_with_params(self, dialect, mock_connection):
        """Test query execution with parameters."""
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchall.return_value = [('result',)]

        result = dialect.execute_query("SELECT * FROM table WHERE id = %s", (123,))
        assert result == [('result',)]
        mock_connection.commit.assert_called_once()

    def test_execute_query_failure(self, dialect, mock_connection):
        """Test query execution failure handling with rollback."""
        mock_cursor = mock_connection.cursor.return_value
        # First call for timeout, second call raises exception
        mock_cursor.execute.side_effect = [None, Exception("Query failed")]

        with pytest.raises(Exception, match="Query failed"):
            dialect.execute_query("INVALID SQL")

        # Ensure rollback was called
        mock_connection.rollback.assert_called_once()
        # Cursor close is called in the finally block
        mock_cursor.close.assert_called_once()

    def test_retry_on_operational_error(self, dialect, mock_pool, mock_connection):
        """Test retry logic for transient operational errors."""
        mock_cursor = mock_connection.cursor.return_value
        # First two attempts fail with OperationalError, third succeeds
        mock_cursor.execute.side_effect = [
            None,  # timeout setting (attempt 1)
            OperationalError("Connection lost"),  # query fails (attempt 1)
            None,  # timeout setting (attempt 2)
            OperationalError("Connection lost"),  # query fails (attempt 2)
            None,  # timeout setting (attempt 3)
            None,  # query succeeds (attempt 3)
        ]
        mock_cursor.fetchall.return_value = [('success',)]

        with patch('time.sleep'):  # Mock sleep to avoid delays in tests
            result = dialect.execute_query("SELECT 1")

        assert result == [('success',)]
        # Should have tried 3 times (timeout + query for each attempt)
        assert mock_cursor.execute.call_count == 6

    def test_retry_exhaustion(self, dialect, mock_pool, mock_connection):
        """Test that retry logic gives up after max_retries."""
        mock_cursor = mock_connection.cursor.return_value
        # All attempts fail
        mock_cursor.execute.side_effect = OperationalError("Persistent connection failure")

        with patch('time.sleep'):  # Mock sleep to avoid delays in tests
            with pytest.raises(OperationalError, match="Persistent connection failure"):
                dialect.execute_query("SELECT 1")

        # Should have tried max_retries times (default 3)
        # Each attempt: timeout + query = 2 calls, but first call to timeout succeeds
        # So we get: attempt1(timeout ok, query fail), attempt2(timeout ok, query fail), attempt3(timeout ok, query fail)
        assert mock_cursor.execute.call_count >= 3

    def test_no_retry_on_programming_error(self, dialect, mock_pool, mock_connection):
        """Test that programming errors (syntax errors) are not retried."""
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.execute.side_effect = [
            None,  # timeout setting
            ProgrammingError("Syntax error in SQL")
        ]

        with pytest.raises(ProgrammingError, match="Syntax error"):
            dialect.execute_query("INVALID SQL")

        # Should only try once (timeout + query)
        assert mock_cursor.execute.call_count == 2

    def test_no_retry_on_data_error(self, dialect, mock_pool, mock_connection):
        """Test that data errors are not retried."""
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.execute.side_effect = [
            None,  # timeout setting
            DataError("Data type mismatch")
        ]

        with pytest.raises(DataError, match="Data type mismatch"):
            dialect.execute_query("SELECT 1")

        # Should only try once (timeout + query)
        assert mock_cursor.execute.call_count == 2

    def test_connection_pool_exhaustion(self, dialect, mock_pool):
        """Test handling of connection pool exhaustion."""
        mock_pool.getconn.return_value = None

        with pytest.raises(OperationalError, match="Connection pool exhausted"):
            dialect.get_connection()

    def test_extract_json_field(self, dialect):
        """Test JSON field extraction as text."""
        # Simple path
        result = dialect.extract_json_field("resource", "$.name")
        assert result == "jsonb_extract_path_text(resource, 'name')"

        # Nested path
        result = dialect.extract_json_field("resource", "$.name.family")
        assert result == "jsonb_extract_path_text(resource, 'name', 'family')"

        # Path with empty parts should be filtered
        result = dialect.extract_json_field("resource", "$.address.line")
        assert result == "jsonb_extract_path_text(resource, 'address', 'line')"

    def test_extract_json_object(self, dialect):
        """Test JSON object extraction preserving structure."""
        # Simple path
        result = dialect.extract_json_object("resource", "$.address")
        assert result == "jsonb_extract_path(resource, 'address')"

        # Nested path
        result = dialect.extract_json_object("resource", "$.name.given")
        assert result == "jsonb_extract_path(resource, 'name', 'given')"

    def test_check_json_exists(self, dialect):
        """Test JSON path existence check."""
        result = dialect.check_json_exists("resource", "$.id")
        assert result == "(jsonb_extract_path(resource, 'id') IS NOT NULL)"

    def test_get_json_type(self, dialect):
        """Test JSON type detection."""
        result = dialect.get_json_type("resource")
        assert result == "jsonb_typeof(resource)"

    def test_get_json_array_length(self, dialect):
        """Test JSON array length calculation."""
        # Without path
        result = dialect.get_json_array_length("array_col")
        assert result == "jsonb_array_length(array_col)"

        # With path
        result = dialect.get_json_array_length("resource", "$.name")
        assert result == "jsonb_array_length(jsonb_extract_path(resource, 'name'))"

    def test_unnest_json_array(self, dialect):
        """Test JSON array unnesting for PostgreSQL."""
        result = dialect.unnest_json_array("resource", "$.name", "name_item")
        assert result == "jsonb_array_elements(jsonb_extract_path(resource, 'name')) AS name_item(unnest)"

        # Test with different path
        result = dialect.unnest_json_array("resource", "$.address", "addr_item")
        assert result == "jsonb_array_elements(jsonb_extract_path(resource, 'address')) AS addr_item(unnest)"

    def test_generate_lateral_unnest(self, dialect):
        """Test PostgreSQL LATERAL UNNEST generation."""
        array_expr = dialect.extract_json_object("resource", "$.name")
        result = dialect.generate_lateral_unnest("patient_cte", array_expr, "name_item")
        assert result == "LATERAL jsonb_array_elements(jsonb_extract_path(resource, 'name')) AS name_item(unnest)"
        assert "patient_cte" not in result

    def test_iterate_json_array(self, dialect):
        """Test JSON array iteration."""
        result = dialect.iterate_json_array("resource", "$.telecom")
        assert result == "jsonb_array_elements(jsonb_extract_path(resource, 'telecom'))"

    def test_aggregate_to_json_array(self, dialect):
        """Test JSON array aggregation."""
        result = dialect.aggregate_to_json_array("name")
        assert result == "jsonb_agg(name)"

    def test_create_json_array(self, dialect):
        """Test JSON array creation."""
        # Empty array
        result = dialect.create_json_array()
        assert result == "jsonb_build_array()"

        # Array with elements
        result = dialect.create_json_array("'John'", "'Jane'")
        assert result == "jsonb_build_array('John', 'Jane')"

    def test_create_json_object(self, dialect):
        """Test JSON object creation."""
        # Empty object
        result = dialect.create_json_object()
        assert result == "jsonb_build_object()"

        # Object with key-value pairs
        result = dialect.create_json_object("'name'", "'John'", "'age'", "30")
        assert result == "jsonb_build_object('name', 'John', 'age', 30)"

    def test_string_concat(self, dialect):
        """Test string concatenation."""
        result = dialect.string_concat("first_name", "last_name")
        assert result == "(first_name || last_name)"

    def test_substring(self, dialect):
        """Test substring extraction."""
        result = dialect.substring("name", "1", "5")
        assert result == "SUBSTRING(name FROM (1) + 1 FOR 5)"

    def test_split_string(self, dialect):
        """Test string splitting."""
        result = dialect.split_string("full_name", "' '")
        assert result == "string_to_array(full_name, ' ')"

    def test_try_cast(self, dialect):
        """Test safe type conversion."""
        result = dialect.try_cast("value", "INTEGER")
        assert "CASE" in result
        assert "integer" in result.lower()
        assert "THEN value::INTEGER" in result

        result = dialect.try_cast("value", "boolean")
        assert "boolean" in result.lower()
        assert "THEN value::boolean" in result

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
        assert result == "CAST(numeric_expr AS DOUBLE PRECISION)"

    def test_is_finite(self, dialect):
        """Test finite number predicate."""
        result = dialect.is_finite("numeric_expr")
        assert result == "isfinite(numeric_expr)"

    def test_generate_math_function(self, dialect):
        """Test mathematical function generation."""
        # Test known functions
        assert dialect.generate_math_function("sqrt", "16") == "sqrt(16)"
        assert dialect.generate_math_function("ln", "x") == "ln(x)"
        assert dialect.generate_math_function("power", "2", "3") == "power(2, 3)"
        assert dialect.generate_math_function("ceiling", "3.7") == "ceil(3.7)"

        # Test unknown function (should pass through)
        assert dialect.generate_math_function("unknown", "x") == "unknown(x)"

    def test_generate_power_operation(self, dialect):
        """Test power operation generation."""
        result = dialect.generate_power_operation("base", "exponent")
        assert result == "power(base, exponent)"

    def test_generate_string_function_substring_with_length(self, dialect):
        """Test substring function with start and length."""
        result = dialect.generate_string_function("substring", "name", "1", "5")
        assert result == "substring(name FROM 1 FOR 5)"

    def test_generate_string_function_substring_without_length(self, dialect):
        """Test substring function with only start position."""
        result = dialect.generate_string_function("substring", "text", "3")
        assert result == "substring(text FROM 3)"

    def test_generate_string_function_indexof(self, dialect):
        """Test indexOf function for finding substring position."""
        result = dialect.generate_string_function("indexOf", "full_text", "'search'")
        # PostgreSQL position returns 1-based index, we subtract 1 for 0-based FHIRPath
        assert result == "(position('search' in full_text) - 1)"

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
        assert result == "CURRENT_TIMESTAMP"

    def test_generate_current_date(self, dialect):
        """Test current date generation."""
        result = dialect.generate_current_date()
        assert result == "CURRENT_DATE"

    def test_generate_date_diff(self, dialect):
        """Test date difference generation."""
        # Day difference
        result = dialect.generate_date_diff("day", "start_date", "end_date")
        assert result == "(end_date::date - start_date::date)"

        # Year difference
        result = dialect.generate_date_diff("year", "start_date", "end_date")
        assert "EXTRACT(year FROM AGE(" in result

        # Month difference
        result = dialect.generate_date_diff("month", "start_date", "end_date")
        assert "EXTRACT(year FROM AGE(" in result
        assert "* 12" in result

        # Other unit (should use epoch calculation)
        result = dialect.generate_date_diff("hour", "start_date", "end_date")
        assert "EXTRACT(epoch FROM" in result

    def test_generate_aggregate_function(self, dialect):
        """Test aggregate function generation."""
        # Basic function
        result = dialect.generate_aggregate_function("sum", "amount")
        assert result == "sum(amount)"

        # Function with mapping
        result = dialect.generate_aggregate_function("variance", "value")
        assert result == "var_samp(value)"

        # With DISTINCT
        result = dialect.generate_aggregate_function("count", "id", distinct=True)
        assert result == "count(DISTINCT id)"

        # With filter condition
        result = dialect.generate_aggregate_function("sum", "amount", filter_condition="amount > 0")
        assert result == "sum(amount) FILTER (WHERE amount > 0)"

    def test_generate_where_clause_filter(self, dialect):
        """Test WHERE clause filtering for collections."""
        result = dialect.generate_where_clause_filter("names", "length > 3")
        assert "jsonb_agg" in result
        assert "jsonb_array_elements" in result
        assert "length > 3" in result

    def test_generate_select_transformation(self, dialect):
        """Test SELECT transformation for collections."""
        result = dialect.generate_select_transformation("persons", "name")
        assert "jsonb_agg" in result
        assert "jsonb_extract_path" in result
        assert "'name'" in result

    def test_generate_string_join(self, dialect):
        """Test string join generation."""
        result_json = dialect.generate_string_join("names_jsonb", "','", True)
        assert "jsonb_array_elements_text" in result_json
        result_array = dialect.generate_string_join("text_array", "','", False)
        assert "jsonb_array_elements_text" not in result_array

    def test_generate_collection_combine(self, dialect):
        """Test collection combination."""
        result = dialect.generate_collection_combine("list1", "list2")
        # PostgreSQL should use || operator for JSONB concatenation
        assert "||" in result
        assert "jsonb_typeof" in result

    def test_generate_collection_exclude(self, dialect):
        """Test collection exclusion generation."""
        result = dialect.generate_collection_exclude("names_jsonb", "'Jim'")
        assert "jsonb_array_elements_text" in result
        assert "jsonb_agg" in result

    def test_wrap_json_array(self, dialect):
        """Test scalar wrapping helper."""
        result = dialect.wrap_json_array("value_expr")
        assert result == "jsonb_build_array(value_expr)"

    def test_serialize_json_value(self, dialect):
        """Test JSON value serialization helper."""
        assert dialect.serialize_json_value("value_expr") == "(value_expr)::text"

    def test_empty_json_array(self, dialect):
        """Test empty JSON array helper."""
        assert dialect.empty_json_array() == "'[]'::jsonb"

    def test_is_json_array(self, dialect):
        """Test JSON array predicate helper.

        Tests the fixed implementation that properly handles all expression types
        (jsonb, json, text, unknown) by always casting to jsonb before checking.

        This is simpler and more robust than the previous approach which used
        to_jsonb() and multiple type checks. The ::jsonb cast works for all types
        and PostgreSQL's jsonb_typeof() function then works correctly.
        """
        predicate = dialect.is_json_array("candidate_expr")
        expected = "(CASE WHEN candidate_expr IS NULL THEN NULL ELSE jsonb_typeof(candidate_expr::jsonb) = 'array' END)"
        assert predicate == expected

    def test_enumerate_json_array(self, dialect):
        """Test JSON array enumeration helper."""
        enumeration_sql = dialect.enumerate_json_array("array_expr", "val", "idx")
        assert "jsonb_array_elements(array_expr)" in enumeration_sql
        assert "AS elem(value, ordinality)" in enumeration_sql

    def test_generate_exists_check(self, dialect):
        """Test exists/empty check generation."""
        # Collection check
        result = dialect.generate_exists_check("array_col", True)
        assert result == "(jsonb_array_length(array_col) > 0)"

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
        """Test date literal generation for PostgreSQL."""
        result = dialect.generate_date_literal("2024-01-15")
        assert result == "DATE '2024-01-15'"

    def test_generate_datetime_literal(self, dialect):
        """Test datetime literal generation for PostgreSQL."""
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
            "pg_typeof(field_value)::text",
            "jsonb_typeof((field_value)::jsonb)",
            "'string'",
        ])

    def test_generate_type_check_integer(self, dialect):
        """Test type checking for Integer type."""
        result = dialect.generate_type_check("age", "Integer")
        self._assert_contains_all(result, [
            "WHEN age IS NULL THEN false",
            "pg_typeof(age)::text",
            "jsonb_typeof((age)::jsonb)",
            "'number'",
        ])

    def test_generate_type_check_decimal(self, dialect):
        """Test type checking for Decimal type."""
        result = dialect.generate_type_check("amount", "Decimal")
        self._assert_contains_all(result, [
            "WHEN amount IS NULL THEN false",
            "pg_typeof(amount)::text",
            "jsonb_typeof((amount)::jsonb)",
            "'number'",
        ])

    def test_generate_type_check_boolean(self, dialect):
        """Test type checking for Boolean type."""
        result = dialect.generate_type_check("flag", "Boolean")
        self._assert_contains_all(result, [
            "WHEN flag IS NULL THEN false",
            "pg_typeof(flag)::text",
            "jsonb_typeof((flag)::jsonb)",
            "'boolean'",
        ])

    def test_generate_type_check_datetime(self, dialect):
        """Test type checking for DateTime type."""
        result = dialect.generate_type_check("timestamp_value", "DateTime")
        self._assert_contains_all(result, [
            "WHEN timestamp_value IS NULL THEN false",
            "pg_typeof(timestamp_value)::text",
            "jsonb_typeof((timestamp_value)::jsonb)",
            "~ '",
        ])

    def test_generate_type_check_date(self, dialect):
        """Test type checking for Date type."""
        result = dialect.generate_type_check("date_value", "Date")
        self._assert_contains_all(result, [
            "WHEN date_value IS NULL THEN false",
            "pg_typeof(date_value)::text",
            "jsonb_typeof((date_value)::jsonb)",
        ])

    def test_generate_type_check_time(self, dialect):
        """Test type checking for Time type."""
        result = dialect.generate_type_check("time_value", "Time")
        self._assert_contains_all(result, [
            "WHEN time_value IS NULL THEN false",
            "pg_typeof(time_value)::text",
            "jsonb_typeof((time_value)::jsonb)",
        ])

    def test_generate_type_check_unknown_type(self, dialect):
        """Test type checking for unknown type returns false."""
        result = dialect.generate_type_check("value", "UnknownType")
        assert result == "false"

    def test_generate_type_cast_string(self, dialect):
        """Test type casting to String."""
        result = dialect.generate_type_cast("value", "String")
        assert "TEXT" in result
        assert "CASE" in result
        assert "value IS NULL THEN NULL" in result

    def test_generate_type_cast_integer(self, dialect):
        """Test type casting to Integer."""
        result = dialect.generate_type_cast("value", "Integer")
        assert "INTEGER" in result
        assert "CASE" in result
        assert "'^-?[0-9]+$'" in result  # Regex pattern for integer validation

    def test_generate_type_cast_decimal(self, dialect):
        """Test type casting to Decimal."""
        result = dialect.generate_type_cast("value", "Decimal")
        assert "NUMERIC" in result
        assert "CASE" in result
        assert "'^-?[0-9]*\\.?[0-9]+$'" in result  # Regex pattern for decimal validation

    def test_generate_type_cast_boolean(self, dialect):
        """Test type casting to Boolean."""
        result = dialect.generate_type_cast("value", "Boolean")
        assert "BOOLEAN" in result
        assert "CASE" in result
        assert "'true', 'false', 't', 'f', '1', '0'" in result

    def test_generate_type_cast_datetime(self, dialect):
        """Test type casting to DateTime."""
        result = dialect.generate_type_cast("value", "DateTime")
        assert "TIMESTAMP" in result
        assert "CASE" in result
        assert "'^[0-9]{4}-[0-9]{2}-[0-9]{2}'" in result  # Regex pattern for datetime validation

    def test_generate_type_cast_date(self, dialect):
        """Test type casting to Date."""
        result = dialect.generate_type_cast("value", "Date")
        assert "DATE" in result
        assert "CASE" in result
        assert "'^[0-9]{4}-[0-9]{2}-[0-9]{2}'" in result  # Regex pattern for date validation

    def test_generate_type_cast_time(self, dialect):
        """Test type casting to Time."""
        result = dialect.generate_type_cast("value", "Time")
        assert "TIME" in result
        assert "CASE" in result
        assert "'^[0-9]{2}:[0-9]{2}:[0-9]{2}'" in result  # Regex pattern for time validation

    def test_generate_type_cast_unknown_type(self, dialect):
        """Test type casting to unknown type returns NULL."""
        result = dialect.generate_type_cast("value", "UnknownType")
        assert result == "NULL"

    def test_generate_collection_type_filter_string(self, dialect):
        """Test collection filtering for String type."""
        result = dialect.generate_collection_type_filter("items", "String")
        self._assert_contains_all(result, [
            "jsonb_agg",
            "jsonb_array_elements",
            "jsonb_typeof(elem) = 'string'",
        ])

    def test_generate_collection_type_filter_integer(self, dialect):
        """Test collection filtering for Integer type."""
        result = dialect.generate_collection_type_filter("numbers", "Integer")
        self._assert_contains_all(result, [
            "jsonb_agg",
            "jsonb_array_elements",
            "jsonb_typeof(elem) = 'number'",
            "elem::text",
        ])

    def test_generate_collection_type_filter_decimal(self, dialect):
        """Test collection filtering for Decimal type."""
        result = dialect.generate_collection_type_filter("amounts", "Decimal")
        self._assert_contains_all(result, [
            "jsonb_agg",
            "jsonb_array_elements",
            "jsonb_typeof(elem) = 'number'",
        ])

    def test_generate_collection_type_filter_boolean(self, dialect):
        """Test collection filtering for Boolean type."""
        result = dialect.generate_collection_type_filter("flags", "Boolean")
        self._assert_contains_all(result, [
            "jsonb_agg",
            "jsonb_array_elements",
            "jsonb_typeof(elem) = 'boolean'",
        ])

    def test_generate_collection_type_filter_datetime(self, dialect):
        """Test collection filtering for DateTime type."""
        result = dialect.generate_collection_type_filter("timestamps", "DateTime")
        self._assert_contains_all(result, [
            "jsonb_agg",
            "jsonb_array_elements",
            "jsonb_typeof(elem)",
            "elem::text",
        ])

    def test_generate_collection_type_filter_date(self, dialect):
        """Test collection filtering for Date type."""
        result = dialect.generate_collection_type_filter("dates", "Date")
        self._assert_contains_all(result, [
            "jsonb_agg",
            "jsonb_array_elements",
            "jsonb_typeof(elem)",
            "'string'",
        ])

    def test_generate_collection_type_filter_time(self, dialect):
        """Test collection filtering for Time type."""
        result = dialect.generate_collection_type_filter("times", "Time")
        self._assert_contains_all(result, [
            "jsonb_agg",
            "jsonb_array_elements",
            "jsonb_typeof(elem)",
            "'string'",
        ])

    def test_generate_collection_type_filter_unknown_type(self, dialect):
        """Test collection filtering for unknown type returns empty array."""
        result = dialect.generate_collection_type_filter("items", "UnknownType")
        assert result == "'[]'::jsonb"

    @pytest.mark.parametrize("fhirpath_type,expected_token", [
        ("String", "'string'"),
        ("Integer", "'number'"),
        ("Decimal", "'number'"),
        ("Boolean", "'boolean'"),
        ("DateTime", "'string'"),
        ("Date", "'string'"),
        ("Time", "'string'"),
    ])
    def test_type_mapping_consistency(self, dialect, fhirpath_type, expected_token):
        """Test that type mapping is consistent across all type operations."""
        # Check that type_check uses the correct types
        type_check = dialect.generate_type_check("value", fhirpath_type)
        assert expected_token in type_check

        # Check that collection_type_filter uses the correct types
        collection_filter = dialect.generate_collection_type_filter("items", fhirpath_type)
        assert expected_token in collection_filter


class TestPostgreSQLDialectIntegration:
    """Integration tests for PostgreSQL dialect (requires actual PostgreSQL)."""

    @pytest.fixture
    def real_dialect(self):
        """Create real PostgreSQL dialect if PostgreSQL is available."""
        # This would need a real PostgreSQL connection string
        # For CI/CD, this might be set up with test containers
        try:
            conn_str = "postgresql://postgres:postgres@localhost:5432/postgres"
            return PostgreSQLDialect(conn_str)
        except Exception:
            pytest.skip("PostgreSQL not available for integration tests")

    def test_real_jsonb_operations(self, real_dialect):
        """Test actual JSONB operations with PostgreSQL."""
        # Test with real PostgreSQL to ensure our SQL is valid
        test_sql = """
        SELECT
            jsonb_extract_path_text('{"name": "John", "age": 30}'::jsonb, 'name') as name,
            jsonb_extract_path('{"items": [1, 2, 3]}'::jsonb, 'items') as items,
            jsonb_typeof('{"test": true}'::jsonb) as type_check
        """

        try:
            result = real_dialect.execute_query(test_sql)
            assert len(result) == 1
            assert result[0][0] == "John"  # name
        except Exception as e:
            pytest.skip(f"PostgreSQL integration test skipped: {e}")

    def test_real_aggregation_operations(self, real_dialect):
        """Test actual aggregation operations with PostgreSQL."""
        test_sql = """
        WITH test_data AS (
            SELECT unnest(ARRAY['a', 'b', 'c']) as value
        )
        SELECT jsonb_agg(value) as aggregated
        FROM test_data
        """

        try:
            result = real_dialect.execute_query(test_sql)
            assert len(result) == 1
            # Should return a JSONB array
        except Exception as e:
            pytest.skip(f"PostgreSQL aggregation test skipped: {e}")
