"""
Cross-database dialect compatibility tests.

Tests that both DuckDB and PostgreSQL dialects generate consistent results
for identical operations, validating the thin dialect architecture principle:
business logic in evaluator, only syntax differences in dialects.
"""

import pytest
from unittest.mock import Mock, patch
import json

from fhir4ds.dialects.factory import DialectFactory


class TestCrossDatabaseDialectCompatibility:
    """
    Integration tests validating identical behavior across database dialects.

    These tests ensure that the thin dialect architecture is properly maintained:
    - Business logic belongs in the FHIRPath evaluator
    - Dialects contain only syntax differences
    - Results are 100% identical across database platforms
    """

    @pytest.fixture
    def duckdb_dialect(self):
        """Create DuckDB dialect with mocked connection."""
        with patch('fhir4ds.dialects.duckdb.duckdb') as mock_duckdb:
            mock_conn = Mock()
            mock_conn.execute.return_value = None
            mock_duckdb.connect.return_value = mock_conn

            return DialectFactory.create_dialect('duckdb', database=':memory:')

    @pytest.fixture
    def postgresql_dialect(self):
        """Create PostgreSQL dialect with mocked connection."""
        with patch('fhir4ds.dialects.postgresql.psycopg2') as mock_psycopg2:
            mock_conn = Mock()
            mock_conn.autocommit = True
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            mock_psycopg2.connect.return_value = mock_conn

            return DialectFactory.create_dialect('postgresql',
                                               connection_string='postgresql://test:test@localhost/test')

    def test_json_field_extraction_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that JSON field extraction produces equivalent SQL across dialects."""
        column = "resource"
        path = "$.name.family"

        duckdb_sql = duckdb_dialect.extract_json_field(column, path)
        postgresql_sql = postgresql_dialect.extract_json_field(column, path)

        # Should use different functions but same semantic meaning
        assert "resource" in duckdb_sql
        assert "resource" in postgresql_sql
        assert "name" in duckdb_sql or "family" in duckdb_sql
        assert "name" in postgresql_sql and "family" in postgresql_sql

        # DuckDB uses json_extract_string
        assert "json_extract_string" in duckdb_sql
        # PostgreSQL uses jsonb_extract_path_text
        assert "jsonb_extract_path_text" in postgresql_sql

    def test_json_object_extraction_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that JSON object extraction maintains structural consistency."""
        column = "resource"
        path = "$.address"

        duckdb_sql = duckdb_dialect.extract_json_object(column, path)
        postgresql_sql = postgresql_dialect.extract_json_object(column, path)

        # Both should reference the resource and address
        assert "resource" in duckdb_sql
        assert "resource" in postgresql_sql
        assert "address" in duckdb_sql
        assert "address" in postgresql_sql

        # DuckDB uses json_extract
        assert "json_extract" in duckdb_sql
        # PostgreSQL uses jsonb_extract_path
        assert "jsonb_extract_path" in postgresql_sql

    def test_existence_check_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that existence checks produce equivalent logic."""
        column = "resource"
        path = "$.id"

        duckdb_sql = duckdb_dialect.check_json_exists(column, path)
        postgresql_sql = postgresql_dialect.check_json_exists(column, path)

        # Both should check for NOT NULL
        assert "IS NOT NULL" in duckdb_sql
        assert "IS NOT NULL" in postgresql_sql
        assert "resource" in duckdb_sql
        assert "resource" in postgresql_sql

    def test_array_length_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that array length calculations are consistent."""
        column = "array_col"

        duckdb_sql = duckdb_dialect.get_json_array_length(column)
        postgresql_sql = postgresql_dialect.get_json_array_length(column)

        # Both should reference the column
        assert "array_col" in duckdb_sql
        assert "array_col" in postgresql_sql

        # DuckDB uses json_array_length
        assert "json_array_length" in duckdb_sql
        # PostgreSQL uses jsonb_array_length
        assert "jsonb_array_length" in postgresql_sql

    def test_type_checking_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that type checking produces equivalent logic."""
        column = "value"

        duckdb_sql = duckdb_dialect.get_json_type(column)
        postgresql_sql = postgresql_dialect.get_json_type(column)

        # Both should reference the value
        assert "value" in duckdb_sql
        assert "value" in postgresql_sql

        # DuckDB uses json_type
        assert "json_type" in duckdb_sql
        # PostgreSQL uses jsonb_typeof
        assert "jsonb_typeof" in postgresql_sql

    def test_array_creation_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that array creation maintains consistent semantics."""
        # Empty array
        duckdb_empty = duckdb_dialect.create_json_array()
        postgresql_empty = postgresql_dialect.create_json_array()

        assert "json_array()" in duckdb_empty
        assert "jsonb_build_array()" in postgresql_empty

        # Array with elements
        elements = ["'a'", "'b'", "'c'"]
        duckdb_filled = duckdb_dialect.create_json_array(*elements)
        postgresql_filled = postgresql_dialect.create_json_array(*elements)

        for element in elements:
            assert element in duckdb_filled
            assert element in postgresql_filled

    def test_string_operations_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that string operations produce equivalent results."""
        # String concatenation
        duckdb_concat = duckdb_dialect.string_concat("first", "second")
        postgresql_concat = postgresql_dialect.string_concat("first", "second")

        # Both should use || operator
        assert "||" in duckdb_concat
        assert "||" in postgresql_concat
        assert "first" in duckdb_concat
        assert "second" in duckdb_concat
        assert "first" in postgresql_concat
        assert "second" in postgresql_concat

        # Substring extraction
        duckdb_substr = duckdb_dialect.substring("text", "1", "3")
        postgresql_substr = postgresql_dialect.substring("text", "1", "3")

        # Both should reference text, start, and length
        assert "text" in duckdb_substr
        assert "text" in postgresql_substr
        assert "1" in duckdb_substr
        assert "1" in postgresql_substr
        assert "3" in duckdb_substr
        assert "3" in postgresql_substr

    def test_mathematical_operations_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that mathematical operations produce equivalent results."""
        # Power operation
        duckdb_power = duckdb_dialect.generate_power_operation("base", "exp")
        postgresql_power = postgresql_dialect.generate_power_operation("base", "exp")

        assert "base" in duckdb_power
        assert "exp" in duckdb_power
        assert "base" in postgresql_power
        assert "exp" in postgresql_power

        # Both should call some power function
        assert "pow" in duckdb_power.lower()
        assert "power" in postgresql_power.lower()

    def test_date_time_operations_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that date/time operations maintain semantic equivalence."""
        # Current timestamp
        duckdb_now = duckdb_dialect.generate_current_timestamp()
        postgresql_now = postgresql_dialect.generate_current_timestamp()

        # Both should provide current timestamp
        assert "now" in duckdb_now.lower() or "current" in duckdb_now.lower()
        assert "current" in postgresql_now.lower()

        # Current date
        duckdb_today = duckdb_dialect.generate_current_date()
        postgresql_today = postgresql_dialect.generate_current_date()

        assert "current" in duckdb_today.lower() or "date" in duckdb_today.lower()
        assert "current" in postgresql_today.lower()

    def test_conditional_expressions_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that conditional expressions maintain identical logic."""
        condition = "x > 0"
        true_expr = "positive"
        false_expr = "negative"

        duckdb_case = duckdb_dialect.generate_conditional_expression(condition, true_expr, false_expr)
        postgresql_case = postgresql_dialect.generate_conditional_expression(condition, true_expr, false_expr)

        # Both should use CASE WHEN structure
        assert "CASE" in duckdb_case
        assert "WHEN" in duckdb_case
        assert "THEN" in duckdb_case
        assert "ELSE" in duckdb_case
        assert "END" in duckdb_case

        assert "CASE" in postgresql_case
        assert "WHEN" in postgresql_case
        assert "THEN" in postgresql_case
        assert "ELSE" in postgresql_case
        assert "END" in postgresql_case

        # All expressions should be present
        for expr in [condition, true_expr, false_expr]:
            assert expr in duckdb_case
            assert expr in postgresql_case

    def test_logical_operations_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that logical operations maintain identical semantics."""
        left = "condition1"
        right = "condition2"

        # AND operation
        duckdb_and = duckdb_dialect.generate_logical_combine(left, "and", right)
        postgresql_and = postgresql_dialect.generate_logical_combine(left, "and", right)

        assert "condition1" in duckdb_and
        assert "condition2" in duckdb_and
        assert "AND" in duckdb_and

        assert "condition1" in postgresql_and
        assert "condition2" in postgresql_and
        assert "AND" in postgresql_and

        # OR operation
        duckdb_or = duckdb_dialect.generate_logical_combine(left, "or", right)
        postgresql_or = postgresql_dialect.generate_logical_combine(left, "or", right)

        assert "OR" in duckdb_or
        assert "OR" in postgresql_or

    def test_collection_operations_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that collection operations maintain behavioral equivalence."""
        collection = "items"

        # Exists check for collections
        duckdb_exists = duckdb_dialect.generate_exists_check(collection, True)
        postgresql_exists = postgresql_dialect.generate_exists_check(collection, True)

        # Both should check array length > 0
        assert "items" in duckdb_exists
        assert "items" in postgresql_exists
        assert "> 0" in duckdb_exists
        assert "> 0" in postgresql_exists

        # Both should use their respective array length functions
        assert "json_array_length" in duckdb_exists
        assert "jsonb_array_length" in postgresql_exists

    def test_aggregate_functions_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that aggregate functions produce equivalent semantics."""
        expression = "value"
        function_name = "sum"

        duckdb_agg = duckdb_dialect.generate_aggregate_function(function_name, expression)
        postgresql_agg = postgresql_dialect.generate_aggregate_function(function_name, expression)

        # Both should use SUM function with value
        assert "SUM" in duckdb_agg
        assert "value" in duckdb_agg
        assert "sum" in postgresql_agg.lower()
        assert "value" in postgresql_agg

        # Test with DISTINCT
        duckdb_distinct = duckdb_dialect.generate_aggregate_function(function_name, expression, distinct=True)
        postgresql_distinct = postgresql_dialect.generate_aggregate_function(function_name, expression, distinct=True)

        assert "DISTINCT" in duckdb_distinct
        assert "DISTINCT" in postgresql_distinct

    def test_type_casting_consistency(self, duckdb_dialect, postgresql_dialect):
        """Test that type casting maintains equivalent semantics."""
        expression = "text_value"

        # Timestamp casting
        duckdb_ts = duckdb_dialect.cast_to_timestamp(expression)
        postgresql_ts = postgresql_dialect.cast_to_timestamp(expression)

        assert "text_value" in duckdb_ts
        assert "text_value" in postgresql_ts
        assert "TIMESTAMP" in duckdb_ts
        assert "TIMESTAMP" in postgresql_ts

        # Time casting
        duckdb_time = duckdb_dialect.cast_to_time(expression)
        postgresql_time = postgresql_dialect.cast_to_time(expression)

        assert "text_value" in duckdb_time
        assert "text_value" in postgresql_time
        assert "TIME" in duckdb_time
        assert "TIME" in postgresql_time


class TestDialectArchitectureCompliance:
    """
    Tests to ensure thin dialect architecture compliance.

    Validates that dialects contain only syntax differences and no business logic.
    """

    @pytest.fixture
    def dialects(self):
        """Get both dialect instances for comparison."""
        with patch('fhir4ds.dialects.duckdb.duckdb'), \
             patch('fhir4ds.dialects.postgresql.psycopg2'), \
             patch('fhir4ds.dialects.postgresql.pool.SimpleConnectionPool'):

            duckdb_dialect = DialectFactory.create_dialect('duckdb', database=':memory:')
            postgresql_dialect = DialectFactory.create_dialect('postgresql',
                                                             connection_string='postgresql://test@localhost/test')

            return duckdb_dialect, postgresql_dialect

    def test_no_hardcoded_business_logic(self, dialects):
        """Test that dialects contain no hardcoded business logic."""
        duckdb_dialect, postgresql_dialect = dialects

        # Test a complex operation that should only differ in syntax
        # Collection filtering should have same logic structure
        collection = "patients"
        condition = "age > 18"

        duckdb_filter = duckdb_dialect.generate_where_clause_filter(collection, condition)
        postgresql_filter = postgresql_dialect.generate_where_clause_filter(collection, condition)

        # Both should contain the same logical elements
        assert "patients" in duckdb_filter
        assert "patients" in postgresql_filter
        assert "age > 18" in duckdb_filter
        assert "age > 18" in postgresql_filter

        # Both should use similar structure (SELECT ... FROM ... WHERE)
        assert "SELECT" in duckdb_filter
        assert "SELECT" in postgresql_filter
        assert "FROM" in duckdb_filter
        assert "FROM" in postgresql_filter
        assert "WHERE" in duckdb_filter
        assert "WHERE" in postgresql_filter

    def test_consistent_error_handling_approach(self, dialects):
        """Test that error handling is consistent across dialects."""
        duckdb_dialect, postgresql_dialect = dialects

        # Both dialects should handle safe casting similarly
        duckdb_cast = duckdb_dialect.try_cast("value", "INTEGER")
        postgresql_cast = postgresql_dialect.try_cast("value", "INTEGER")

        # Both should reference the value and target type
        assert "value" in duckdb_cast
        assert "value" in postgresql_cast
        assert "integer" in duckdb_cast.lower()
        assert "integer" in postgresql_cast.lower()

        # Both should handle failures gracefully (return NULL or similar)
        # DuckDB uses TRY_CAST, PostgreSQL uses CASE expression
        assert ("TRY_CAST" in duckdb_cast) or ("CASE" in duckdb_cast)
        assert "CASE" in postgresql_cast  # PostgreSQL implementation uses CASE

    def test_metadata_awareness_consistency(self, dialects):
        """Test that both dialects can leverage metadata consistently."""
        duckdb_dialect, postgresql_dialect = dialects

        # Both should support feature checking
        assert hasattr(duckdb_dialect, 'supports_feature')
        assert hasattr(postgresql_dialect, 'supports_feature')

        # Feature support should reflect database capabilities
        assert duckdb_dialect.supports_feature('json_functions') is True
        assert postgresql_dialect.supports_feature('json_functions') is True
        assert duckdb_dialect.supports_feature('jsonb') is False
        assert postgresql_dialect.supports_feature('jsonb') is True

    def test_no_business_logic_in_collection_operations(self, dialects):
        """Test that collection operations contain only syntax differences."""
        duckdb_dialect, postgresql_dialect = dialects

        # Scalar wrapping uses syntax-only helpers
        assert duckdb_dialect.wrap_json_array("value_expr") == "json_array(value_expr)"
        assert postgresql_dialect.wrap_json_array("value_expr") == "jsonb_build_array(value_expr)"

        # Empty array literals are database specific syntax
        assert duckdb_dialect.empty_json_array() == "json_array()"
        assert postgresql_dialect.empty_json_array() == "'[]'::jsonb"

        # Array predicates stay syntax-only
        assert duckdb_dialect.is_json_array("expr").startswith("(json_type")
        assert "jsonb_typeof" in postgresql_dialect.is_json_array("expr")

        # Enumeration relies on database-specific functions without business logic
        duckdb_enum = duckdb_dialect.enumerate_json_array("array_expr", "val", "idx")
        postgres_enum = postgresql_dialect.enumerate_json_array("array_expr", "val", "idx")
        assert "json_each(array_expr)" in duckdb_enum
        assert "jsonb_array_elements(array_expr)" in postgres_enum
