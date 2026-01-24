"""
SQL execution validation tests for both DuckDB and PostgreSQL dialects.

This module validates that generated SQL from dialect methods executes correctly
on actual databases, ensuring syntax correctness and result accuracy across both
database platforms.
"""

import pytest
from typing import Any, List, Tuple

from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect


# PostgreSQL connection string for testing
POSTGRESQL_CONN_STRING = "postgresql://postgres:postgres@localhost:5432/postgres"


class TestDuckDBSQLExecution:
    """Test SQL execution correctness for DuckDB dialect."""

    @pytest.fixture
    def dialect(self):
        """Create DuckDB dialect instance."""
        try:
            return DuckDBDialect()
        except ImportError:
            pytest.skip("DuckDB not available for testing")

    def test_json_extract_field_execution(self, dialect):
        """Test JSON field extraction executes correctly."""
        sql = f"""
        SELECT {dialect.extract_json_field("data", "$.name")} as result
        FROM (SELECT '{{"name": "John", "age": 30}}'::JSON as data)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == "John"

    def test_json_extract_object_execution(self, dialect):
        """Test JSON object extraction executes correctly."""
        sql = f"""
        SELECT {dialect.extract_json_object("data", "$.address")} as result
        FROM (SELECT '{{"address": {{"city": "Boston"}}}}'::JSON as data)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        # Result should be a JSON object

    def test_check_json_exists_execution(self, dialect):
        """Test JSON existence check executes correctly."""
        sql = f"""
        SELECT
            {dialect.check_json_exists("data", "$.name")} as exists_true,
            {dialect.check_json_exists("data", "$.missing")} as exists_false
        FROM (SELECT '{{"name": "John"}}'::JSON as data)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_get_json_type_execution(self, dialect):
        """Test JSON type detection executes correctly."""
        sql = f"""
        SELECT {dialect.get_json_type("data")} as type_result
        FROM (SELECT '{{"name": "John"}}'::JSON as data)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        # DuckDB returns 'OBJECT' for JSON objects

    def test_get_json_array_length_execution(self, dialect):
        """Test JSON array length calculation executes correctly."""
        sql = f"""
        SELECT {dialect.get_json_array_length("data")} as length_result
        FROM (SELECT '[1, 2, 3, 4, 5]'::JSON as data)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 5

    def test_unnest_json_array_execution(self, dialect):
        """Test JSON array unnesting executes correctly."""
        # Use json_each which works in DuckDB for iterating arrays
        sql = """
        WITH test AS (
            SELECT '{"items": [1, 2, 3]}'::JSON as data
        )
        SELECT value FROM test, json_each(json_extract(data, '$.items'))
        """
        result = dialect.execute_query(sql)
        assert len(result) == 3

    def test_aggregate_to_json_array_execution(self, dialect):
        """Test JSON array aggregation executes correctly."""
        sql = f"""
        SELECT {dialect.aggregate_to_json_array("value")} as aggregated
        FROM (SELECT unnest([1, 2, 3]) as value)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_create_json_array_execution(self, dialect):
        """Test JSON array creation executes correctly."""
        sql = f"SELECT {dialect.create_json_array('1', '2', '3')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_create_json_object_execution(self, dialect):
        """Test JSON object creation executes correctly."""
        json_obj = dialect.create_json_object("'name'", "'John'", "'age'", '30')
        sql = f"SELECT {json_obj} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_string_concat_execution(self, dialect):
        """Test string concatenation executes correctly."""
        sql = f"""
        SELECT {dialect.string_concat("first_name", "last_name")} as full_name
        FROM (SELECT 'John' as first_name, 'Doe' as last_name)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == "JohnDoe"

    def test_substring_execution(self, dialect):
        """Test substring extraction executes correctly."""
        sql = f"""
        SELECT {dialect.substring("text", "0", "5")} as result
        FROM (SELECT 'Hello World' as text)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == "Hello"

    def test_split_string_execution(self, dialect):
        """Test string splitting executes correctly."""
        sql = f"""
        SELECT {dialect.split_string("text", "' '")} as result
        FROM (SELECT 'Hello World' as text)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_try_cast_execution(self, dialect):
        """Test safe type conversion executes correctly."""
        sql = f"""
        SELECT
            {dialect.try_cast("'123'", "INTEGER")} as cast_success,
            {dialect.try_cast("'abc'", "INTEGER")} as cast_fail
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 123
        assert result[0][1] is None

    def test_cast_to_timestamp_execution(self, dialect):
        """Test timestamp casting executes correctly."""
        sql = f"""
        SELECT {dialect.cast_to_timestamp("'2024-01-15 10:30:00'")} as result
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_cast_to_time_execution(self, dialect):
        """Test time casting executes correctly."""
        sql = f"""
        SELECT {dialect.cast_to_time("'10:30:00'")} as result
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_generate_math_function_sqrt_execution(self, dialect):
        """Test square root function executes correctly."""
        sql = f"SELECT {dialect.generate_math_function('sqrt', '16')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 4.0

    def test_generate_math_function_abs_execution(self, dialect):
        """Test absolute value function executes correctly."""
        sql = f"SELECT {dialect.generate_math_function('abs', '-5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 5

    def test_generate_math_function_ceil_execution(self, dialect):
        """Test ceiling function executes correctly."""
        sql = f"SELECT {dialect.generate_math_function('ceiling', '3.2')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 4

    def test_generate_math_function_floor_execution(self, dialect):
        """Test floor function executes correctly."""
        sql = f"SELECT {dialect.generate_math_function('floor', '3.8')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 3

    def test_generate_power_operation_execution(self, dialect):
        """Test power operation executes correctly."""
        sql = f"SELECT {dialect.generate_power_operation('2', '3')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 8.0

    def test_generate_current_timestamp_execution(self, dialect):
        """Test current timestamp generation executes correctly."""
        sql = f"SELECT {dialect.generate_current_timestamp()} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        # Result should be a timestamp

    def test_generate_current_date_execution(self, dialect):
        """Test current date generation executes correctly."""
        sql = f"SELECT {dialect.generate_current_date()} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        # Result should be a date

    def test_generate_date_diff_execution(self, dialect):
        """Test date difference calculation executes correctly."""
        sql = f"""
        SELECT {dialect.generate_date_diff('day', "DATE '2024-01-01'", "DATE '2024-01-10'")} as result
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 9

    def test_generate_aggregate_sum_execution(self, dialect):
        """Test SUM aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('sum', 'value')} as total
        FROM (SELECT unnest([1, 2, 3, 4, 5]) as value)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 15

    def test_generate_aggregate_avg_execution(self, dialect):
        """Test AVG aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('avg', 'value')} as average
        FROM (SELECT unnest([2, 4, 6, 8]) as value)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 5.0

    def test_generate_aggregate_count_execution(self, dialect):
        """Test COUNT aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('count', '*')} as total
        FROM (SELECT unnest([1, 2, 3]) as value)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 3

    def test_generate_aggregate_max_execution(self, dialect):
        """Test MAX aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('max', 'value')} as maximum
        FROM (SELECT unnest([5, 2, 8, 1, 9]) as value)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 9

    def test_generate_aggregate_min_execution(self, dialect):
        """Test MIN aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('min', 'value')} as minimum
        FROM (SELECT unnest([5, 2, 8, 1, 9]) as value)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 1

    def test_generate_aggregate_distinct_execution(self, dialect):
        """Test DISTINCT aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('count', 'value', distinct=True)} as unique_count
        FROM (SELECT unnest([1, 2, 2, 3, 3, 3]) as value)
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 3

    def test_generate_exists_check_collection_execution(self, dialect):
        """Test exists check for collections executes correctly."""
        sql = f"""
        SELECT
            {dialect.generate_exists_check("'[1, 2, 3]'::JSON", True)} as has_items,
            {dialect.generate_exists_check("'[]'::JSON", True)} as empty
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_generate_exists_check_value_execution(self, dialect):
        """Test exists check for values executes correctly."""
        sql = f"""
        SELECT
            {dialect.generate_exists_check("'value'", False)} as has_value,
            {dialect.generate_exists_check("NULL", False)} as no_value
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_generate_logical_and_execution(self, dialect):
        """Test logical AND operation executes correctly."""
        sql = f"""
        SELECT {dialect.generate_logical_combine("TRUE", "and", "TRUE")} as both_true,
               {dialect.generate_logical_combine("TRUE", "and", "FALSE")} as one_false
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_generate_logical_or_execution(self, dialect):
        """Test logical OR operation executes correctly."""
        sql = f"""
        SELECT {dialect.generate_logical_combine("TRUE", "or", "FALSE")} as one_true,
               {dialect.generate_logical_combine("FALSE", "or", "FALSE")} as both_false
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_generate_date_literal_execution(self, dialect):
        """Test date literal generation executes correctly."""
        sql = f"SELECT {dialect.generate_date_literal('2024-01-15')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_generate_datetime_literal_execution(self, dialect):
        """Test datetime literal generation executes correctly."""
        sql = f"SELECT {dialect.generate_datetime_literal('2024-01-15T14:30:00')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_generate_comparison_equals_execution(self, dialect):
        """Test equals comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('5', '=', '5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_not_equals_execution(self, dialect):
        """Test not equals comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('5', '!=', '3')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_less_than_execution(self, dialect):
        """Test less than comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('3', '<', '5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_greater_than_execution(self, dialect):
        """Test greater than comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('7', '>', '5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_less_or_equal_execution(self, dialect):
        """Test less than or equal comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('5', '<=', '5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_greater_or_equal_execution(self, dialect):
        """Test greater than or equal comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('5', '>=', '3')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_conditional_expression_execution(self, dialect):
        """Test conditional expression executes correctly."""
        sql = f"""
        SELECT {dialect.generate_conditional_expression("5 > 3", "'yes'", "'no'")} as result
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == "yes"


class TestPostgreSQLSQLExecution:
    """Test SQL execution correctness for PostgreSQL dialect."""

    @pytest.fixture
    def dialect(self):
        """Create PostgreSQL dialect instance."""
        try:
            return PostgreSQLDialect(POSTGRESQL_CONN_STRING)
        except Exception as e:
            pytest.skip(f"PostgreSQL not available for testing: {e}")

    def test_json_extract_field_execution(self, dialect):
        """Test JSON field extraction executes correctly."""
        sql = f"""
        SELECT {dialect.extract_json_field("data", "$.name")} as result
        FROM (SELECT '{{"name": "John", "age": 30}}'::jsonb as data) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == "John"

    def test_json_extract_object_execution(self, dialect):
        """Test JSON object extraction executes correctly."""
        sql = f"""
        SELECT {dialect.extract_json_object("data", "$.address")} as result
        FROM (SELECT '{{"address": {{"city": "Boston"}}}}'::jsonb as data) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_check_json_exists_execution(self, dialect):
        """Test JSON existence check executes correctly."""
        sql = f"""
        SELECT
            {dialect.check_json_exists("data", "$.name")} as exists_true,
            {dialect.check_json_exists("data", "$.missing")} as exists_false
        FROM (SELECT '{{"name": "John"}}'::jsonb as data) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_get_json_type_execution(self, dialect):
        """Test JSON type detection executes correctly."""
        sql = f"""
        SELECT {dialect.get_json_type("data")} as type_result
        FROM (SELECT '{{"name": "John"}}'::jsonb as data) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == "object"

    def test_get_json_array_length_execution(self, dialect):
        """Test JSON array length calculation executes correctly."""
        sql = f"""
        SELECT {dialect.get_json_array_length("data")} as length_result
        FROM (SELECT '[1, 2, 3, 4, 5]'::jsonb as data) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 5

    def test_unnest_json_array_execution(self, dialect):
        """Test JSON array unnesting executes correctly."""
        sql = f"""
        SELECT item FROM (
            SELECT '{{"items": [1, 2, 3]}}'::jsonb as data
        ) t, {dialect.unnest_json_array("data", "$.items", "item")}
        """
        result = dialect.execute_query(sql)
        assert len(result) == 3

    def test_aggregate_to_json_array_execution(self, dialect):
        """Test JSON array aggregation executes correctly."""
        sql = f"""
        SELECT {dialect.aggregate_to_json_array("value")} as aggregated
        FROM (SELECT generate_series(1, 3) as value) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_create_json_array_execution(self, dialect):
        """Test JSON array creation executes correctly."""
        sql = f"SELECT {dialect.create_json_array('1', '2', '3')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_create_json_object_execution(self, dialect):
        """Test JSON object creation executes correctly."""
        json_obj = dialect.create_json_object("'name'", "'John'", "'age'", '30')
        sql = f"SELECT {json_obj} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_string_concat_execution(self, dialect):
        """Test string concatenation executes correctly."""
        sql = f"""
        SELECT {dialect.string_concat("first_name", "last_name")} as full_name
        FROM (SELECT 'John' as first_name, 'Doe' as last_name) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == "JohnDoe"

    def test_substring_execution(self, dialect):
        """Test substring extraction executes correctly."""
        sql = f"""
        SELECT {dialect.substring("text", "0", "5")} as result
        FROM (SELECT 'Hello World' as text) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == "Hello"

    def test_split_string_execution(self, dialect):
        """Test string splitting executes correctly."""
        sql = f"""
        SELECT {dialect.split_string("text", "' '")} as result
        FROM (SELECT 'Hello World' as text) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_cast_to_timestamp_execution(self, dialect):
        """Test timestamp casting executes correctly."""
        sql = f"""
        SELECT {dialect.cast_to_timestamp("'2024-01-15 10:30:00'")} as result
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_cast_to_time_execution(self, dialect):
        """Test time casting executes correctly."""
        sql = f"""
        SELECT {dialect.cast_to_time("'10:30:00'")} as result
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_generate_math_function_sqrt_execution(self, dialect):
        """Test square root function executes correctly."""
        sql = f"SELECT {dialect.generate_math_function('sqrt', '16')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 4.0

    def test_generate_math_function_abs_execution(self, dialect):
        """Test absolute value function executes correctly."""
        sql = f"SELECT {dialect.generate_math_function('abs', '-5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 5

    def test_generate_math_function_ceil_execution(self, dialect):
        """Test ceiling function executes correctly."""
        sql = f"SELECT {dialect.generate_math_function('ceiling', '3.2')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 4

    def test_generate_math_function_floor_execution(self, dialect):
        """Test floor function executes correctly."""
        sql = f"SELECT {dialect.generate_math_function('floor', '3.8')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 3

    def test_generate_power_operation_execution(self, dialect):
        """Test power operation executes correctly."""
        sql = f"SELECT {dialect.generate_power_operation('2', '3')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 8.0

    def test_generate_current_timestamp_execution(self, dialect):
        """Test current timestamp generation executes correctly."""
        sql = f"SELECT {dialect.generate_current_timestamp()} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_generate_current_date_execution(self, dialect):
        """Test current date generation executes correctly."""
        sql = f"SELECT {dialect.generate_current_date()} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_generate_date_diff_execution(self, dialect):
        """Test date difference calculation executes correctly."""
        sql = f"""
        SELECT {dialect.generate_date_diff('day', "DATE '2024-01-01'", "DATE '2024-01-10'")} as result
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 9

    def test_generate_aggregate_sum_execution(self, dialect):
        """Test SUM aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('sum', 'value')} as total
        FROM (SELECT generate_series(1, 5) as value) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 15

    def test_generate_aggregate_avg_execution(self, dialect):
        """Test AVG aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('avg', 'value')} as average
        FROM (SELECT unnest(ARRAY[2, 4, 6, 8]) as value) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 5.0

    def test_generate_aggregate_count_execution(self, dialect):
        """Test COUNT aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('count', '*')} as total
        FROM (SELECT generate_series(1, 3) as value) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 3

    def test_generate_aggregate_max_execution(self, dialect):
        """Test MAX aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('max', 'value')} as maximum
        FROM (SELECT unnest(ARRAY[5, 2, 8, 1, 9]) as value) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 9

    def test_generate_aggregate_min_execution(self, dialect):
        """Test MIN aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('min', 'value')} as minimum
        FROM (SELECT unnest(ARRAY[5, 2, 8, 1, 9]) as value) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 1

    def test_generate_aggregate_distinct_execution(self, dialect):
        """Test DISTINCT aggregate function executes correctly."""
        sql = f"""
        SELECT {dialect.generate_aggregate_function('count', 'value', distinct=True)} as unique_count
        FROM (SELECT unnest(ARRAY[1, 2, 2, 3, 3, 3]) as value) t
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == 3

    def test_generate_exists_check_collection_execution(self, dialect):
        """Test exists check for collections executes correctly."""
        sql = f"""
        SELECT
            {dialect.generate_exists_check("'[1, 2, 3]'::jsonb", True)} as has_items,
            {dialect.generate_exists_check("'[]'::jsonb", True)} as empty
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_generate_exists_check_value_execution(self, dialect):
        """Test exists check for values executes correctly."""
        sql = f"""
        SELECT
            {dialect.generate_exists_check("'value'", False)} as has_value,
            {dialect.generate_exists_check("NULL", False)} as no_value
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_generate_logical_and_execution(self, dialect):
        """Test logical AND operation executes correctly."""
        sql = f"""
        SELECT {dialect.generate_logical_combine("TRUE", "and", "TRUE")} as both_true,
               {dialect.generate_logical_combine("TRUE", "and", "FALSE")} as one_false
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_generate_logical_or_execution(self, dialect):
        """Test logical OR operation executes correctly."""
        sql = f"""
        SELECT {dialect.generate_logical_combine("TRUE", "or", "FALSE")} as one_true,
               {dialect.generate_logical_combine("FALSE", "or", "FALSE")} as both_false
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True
        assert result[0][1] is False

    def test_generate_date_literal_execution(self, dialect):
        """Test date literal generation executes correctly."""
        sql = f"SELECT {dialect.generate_date_literal('2024-01-15')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_generate_datetime_literal_execution(self, dialect):
        """Test datetime literal generation executes correctly."""
        sql = f"SELECT {dialect.generate_datetime_literal('2024-01-15T14:30:00')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1

    def test_generate_comparison_equals_execution(self, dialect):
        """Test equals comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('5', '=', '5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_not_equals_execution(self, dialect):
        """Test not equals comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('5', '!=', '3')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_less_than_execution(self, dialect):
        """Test less than comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('3', '<', '5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_greater_than_execution(self, dialect):
        """Test greater than comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('7', '>', '5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_less_or_equal_execution(self, dialect):
        """Test less than or equal comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('5', '<=', '5')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_comparison_greater_or_equal_execution(self, dialect):
        """Test greater than or equal comparison executes correctly."""
        sql = f"SELECT {dialect.generate_comparison('5', '>=', '3')} as result"
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] is True

    def test_generate_conditional_expression_execution(self, dialect):
        """Test conditional expression executes correctly."""
        sql = f"""
        SELECT {dialect.generate_conditional_expression("5 > 3", "'yes'", "'no'")} as result
        """
        result = dialect.execute_query(sql)
        assert len(result) == 1
        assert result[0][0] == "yes"
