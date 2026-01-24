"""
Unit tests for dialect factory.

Tests the factory pattern for creating database dialect instances
based on runtime configuration and connection strings.
"""

import pytest
from unittest.mock import Mock, patch

from fhir4ds.dialects.factory import (
    DialectFactory,
    create_duckdb_dialect,
    create_postgresql_dialect,
    detect_and_create_dialect
)
from fhir4ds.dialects.base import DatabaseDialect
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect


class TestDialectFactory:
    """Test cases for DialectFactory."""

    def test_get_available_dialects(self):
        """Test getting available dialect classes."""
        dialects = DialectFactory.get_available_dialects()

        assert 'duckdb' in dialects
        assert 'postgresql' in dialects
        assert 'postgres' in dialects  # Alias

        assert dialects['duckdb'] == DuckDBDialect
        assert dialects['postgresql'] == PostgreSQLDialect
        assert dialects['postgres'] == PostgreSQLDialect

    def test_detect_database_type_duckdb(self):
        """Test database type detection for DuckDB."""
        # Memory database
        assert DialectFactory._detect_database_type(':memory:') == 'duckdb'

        # File paths
        assert DialectFactory._detect_database_type('test.db') == 'duckdb'
        assert DialectFactory._detect_database_type('data.duckdb') == 'duckdb'
        assert DialectFactory._detect_database_type('/path/to/file.db') == 'duckdb'

        # URL scheme
        assert DialectFactory._detect_database_type('duckdb:///path/to/file.db') == 'duckdb'

    def test_detect_database_type_postgresql(self):
        """Test database type detection for PostgreSQL."""
        # PostgreSQL connection strings
        assert DialectFactory._detect_database_type('postgresql://user:pass@localhost/db') == 'postgresql'
        assert DialectFactory._detect_database_type('postgres://user:pass@localhost/db') == 'postgresql'

    def test_detect_database_type_unknown(self):
        """Test database type detection for unknown formats."""
        with patch('fhir4ds.dialects.factory.logger'):  # Suppress warning logs
            assert DialectFactory._detect_database_type('unknown://test') is None
            assert DialectFactory._detect_database_type('') is None
            assert DialectFactory._detect_database_type(None) is None

    @patch('fhir4ds.dialects.duckdb.duckdb')  # Mock the duckdb module
    def test_create_dialect_duckdb_explicit(self, mock_duckdb):
        """Test creating DuckDB dialect with explicit type."""
        mock_conn = Mock()
        mock_duckdb.connect.return_value = mock_conn

        result = DialectFactory.create_dialect(database_type='duckdb')

        assert result is not None
        assert result.name == "DUCKDB"
        mock_duckdb.connect.assert_called_once_with(':memory:')

    @patch('fhir4ds.dialects.postgresql.pool.SimpleConnectionPool')
    @patch('fhir4ds.dialects.postgresql.psycopg2')
    def test_create_dialect_postgresql_explicit(self, mock_psycopg2, mock_pool):
        """Test creating PostgreSQL dialect with explicit type."""
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = Mock()
        mock_pool_instance.putconn.return_value = None
        mock_pool.return_value = mock_pool_instance

        conn_str = 'postgresql://user:pass@localhost/db'
        result = DialectFactory.create_dialect(database_type='postgresql', connection_string=conn_str)

        assert result is not None
        assert result.name == "POSTGRESQL"
        mock_pool.assert_called_once_with(1, 5, conn_str)

    @patch('fhir4ds.dialects.duckdb.duckdb')
    def test_create_dialect_auto_detect_duckdb(self, mock_duckdb):
        """Test creating dialect with auto-detection for DuckDB."""
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_duckdb.connect.return_value = mock_conn

        result = DialectFactory.create_dialect(connection_string=':memory:')

        assert result is not None
        assert result.name == "DUCKDB"
        mock_duckdb.connect.assert_called_once_with(':memory:')

    @patch('fhir4ds.dialects.postgresql.pool.SimpleConnectionPool')
    @patch('fhir4ds.dialects.postgresql.psycopg2')
    def test_create_dialect_auto_detect_postgresql(self, mock_psycopg2, mock_pool):
        """Test creating dialect with auto-detection for PostgreSQL."""
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = Mock()
        mock_pool_instance.putconn.return_value = None
        mock_pool.return_value = mock_pool_instance

        conn_str = 'postgresql://user:pass@localhost/db'
        result = DialectFactory.create_dialect(connection_string=conn_str)

        assert result is not None
        assert result.name == "POSTGRESQL"
        mock_pool.assert_called_once_with(1, 5, conn_str)

    def test_create_dialect_no_type_no_connection(self):
        """Test error when no type or connection string provided."""
        with pytest.raises(ValueError, match="Database type must be specified"):
            DialectFactory.create_dialect()

    def test_create_dialect_unsupported_type(self):
        """Test error for unsupported database type."""
        with pytest.raises(ValueError, match="Unsupported database type 'mysql'"):
            DialectFactory.create_dialect(database_type='mysql')

    def test_create_postgresql_dialect_no_connection_string(self):
        """Test error when PostgreSQL dialect requires connection string."""
        with pytest.raises(ValueError, match="PostgreSQL dialect requires a connection string"):
            DialectFactory.create_dialect(database_type='postgresql')

    def test_register_dialect(self):
        """Test registering a new dialect."""
        class CustomDialect(DatabaseDialect):
            def get_connection(self): pass
            def execute_query(self, sql): pass
            def extract_json_field(self, column, path): pass
            def extract_json_object(self, column, path): pass
            def check_json_exists(self, column, path): pass
            def get_json_type(self, column): pass
            def get_json_array_length(self, column, path=None): pass
            def iterate_json_array(self, column, path): pass
            def aggregate_to_json_array(self, expression): pass
            def create_json_array(self, *args): pass
            def create_json_object(self, *args): pass
            def string_concat(self, left, right): pass
            def substring(self, expression, start, length): pass
            def split_string(self, expression, delimiter): pass
            def try_cast(self, expression, target_type): pass
            def cast_to_timestamp(self, expression): pass
            def cast_to_time(self, expression): pass
            def generate_math_function(self, function_name, *args): pass
            def generate_power_operation(self, base_expr, exponent_expr): pass
            def generate_current_timestamp(self): pass
            def generate_current_date(self): pass
            def generate_date_diff(self, unit, start_date, end_date): pass
            def generate_aggregate_function(self, function_name, expression, filter_condition=None, distinct=False): pass
            def generate_where_clause_filter(self, collection_expr, condition_sql): pass
            def generate_select_transformation(self, collection_expr, transform_path): pass
            def generate_collection_combine(self, first_collection, second_collection): pass
            def generate_collection_exclude(self, collection_expr, exclusion_expr): pass
            def wrap_json_array(self, expression): pass
            def serialize_json_value(self, expression): pass
            def empty_json_array(self): pass
            def is_json_array(self, expression): pass
            def enumerate_json_array(self, array_expr, value_alias, index_alias): pass
            def generate_exists_check(self, fragment, is_collection): pass
            def generate_logical_combine(self, left_condition, operator, right_condition): pass
            def generate_conditional_expression(self, condition, true_expr, false_expr): pass

        # Register new dialect
        DialectFactory.register_dialect('custom', CustomDialect)

        # Verify it's registered
        dialects = DialectFactory.get_available_dialects()
        assert 'custom' in dialects
        assert dialects['custom'] == CustomDialect

        # Clean up
        del DialectFactory._dialects['custom']

    def test_register_dialect_invalid_class(self):
        """Test error when registering invalid dialect class."""
        class NotADialect:
            pass

        with pytest.raises(ValueError, match="must inherit from DatabaseDialect"):
            DialectFactory.register_dialect('invalid', NotADialect)

    @patch('fhir4ds.dialects.duckdb.duckdb')
    def test_create_from_config(self, mock_duckdb):
        """Test creating dialect from configuration dictionary."""
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_duckdb.connect.return_value = mock_conn

        config = {
            'type': 'duckdb',
            'database': 'test.db'
        }

        result = DialectFactory.create_from_config(config)

        assert result is not None
        assert result.name == "DUCKDB"
        mock_duckdb.connect.assert_called_once_with('test.db')


class TestConvenienceFunctions:
    """Test convenience functions for dialect creation."""

    @patch('fhir4ds.dialects.factory.DialectFactory.create_dialect')
    def test_create_duckdb_dialect(self, mock_create):
        """Test DuckDB convenience function."""
        mock_instance = Mock()
        mock_create.return_value = mock_instance

        result = create_duckdb_dialect('test.db')

        assert result is mock_instance
        mock_create.assert_called_once_with('duckdb', database='test.db', connection=None)

    @patch('fhir4ds.dialects.factory.DialectFactory.create_dialect')
    def test_create_postgresql_dialect(self, mock_create):
        """Test PostgreSQL convenience function."""
        mock_instance = Mock()
        mock_create.return_value = mock_instance

        conn_str = 'postgresql://user:pass@localhost/db'
        result = create_postgresql_dialect(conn_str)

        assert result is mock_instance
        mock_create.assert_called_once_with('postgresql', connection_string=conn_str)

    @patch('fhir4ds.dialects.factory.DialectFactory.create_dialect')
    def test_detect_and_create_dialect(self, mock_create):
        """Test auto-detect convenience function."""
        mock_instance = Mock()
        mock_create.return_value = mock_instance

        conn_str = ':memory:'
        result = detect_and_create_dialect(conn_str, extra_param='test')

        assert result is mock_instance
        mock_create.assert_called_once_with(connection_string=conn_str, extra_param='test')


class TestDialectFactoryEdgeCases:
    """Test edge cases and error conditions for DialectFactory."""

    @patch('fhir4ds.dialects.duckdb.duckdb')
    def test_create_dialect_with_creation_failure(self, mock_duckdb):
        """Test handling of dialect creation failure."""
        mock_duckdb.connect.side_effect = Exception("Creation failed")

        with pytest.raises(Exception, match="Creation failed"):
            DialectFactory.create_dialect(database_type='duckdb')

    @patch('fhir4ds.dialects.duckdb.duckdb')
    def test_case_insensitive_database_type(self, mock_duckdb):
        """Test that database type is case insensitive."""
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_duckdb.connect.return_value = mock_conn

        # Test various cases
        result1 = DialectFactory.create_dialect(database_type='DUCKDB', database=':memory:')
        result2 = DialectFactory.create_dialect(database_type='DuckDB', database=':memory:')
        result3 = DialectFactory.create_dialect(database_type='duckdb', database=':memory:')

        assert all(result.name == "DUCKDB" for result in [result1, result2, result3])
        assert mock_duckdb.connect.call_count == 3

    @patch('fhir4ds.dialects.postgresql.pool.SimpleConnectionPool')
    @patch('fhir4ds.dialects.postgresql.psycopg2')
    def test_postgresql_alias_handling(self, mock_psycopg2, mock_pool):
        """Test that postgres alias works correctly."""
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = Mock()
        mock_pool.return_value = mock_pool_instance
        mock_psycopg2.connect.return_value = Mock()

        conn_str = 'postgresql://test@localhost/db'

        # Both 'postgresql' and 'postgres' should work
        result1 = DialectFactory.create_dialect(database_type='postgresql', connection_string=conn_str)
        result2 = DialectFactory.create_dialect(database_type='postgres', connection_string=conn_str)

        assert result1.name == "POSTGRESQL"
        assert result2.name == "POSTGRESQL"
        assert mock_pool.call_count == 2
        for call in mock_pool.call_args_list:
            assert call.args[0] == 1
            assert call.args[1] == 5
            assert call.args[2] == conn_str
