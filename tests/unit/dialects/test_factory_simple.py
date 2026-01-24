"""
Simplified unit tests for dialect factory.

Tests the core factory functionality without complex mocking.
"""

import pytest
from unittest.mock import Mock, patch

from fhir4ds.dialects.factory import DialectFactory
from fhir4ds.dialects.base import DatabaseDialect


class TestDialectFactoryCore:
    """Core factory functionality tests."""

    def test_get_available_dialects(self):
        """Test getting available dialect classes."""
        dialects = DialectFactory.get_available_dialects()

        assert 'duckdb' in dialects
        assert 'postgresql' in dialects
        assert 'postgres' in dialects  # Alias

    def test_detect_database_type_duckdb(self):
        """Test database type detection for DuckDB."""
        # Memory database
        assert DialectFactory._detect_database_type(':memory:') == 'duckdb'

        # File paths
        assert DialectFactory._detect_database_type('test.db') == 'duckdb'
        assert DialectFactory._detect_database_type('data.duckdb') == 'duckdb'

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

    def test_create_dialect_no_type_no_connection(self):
        """Test error when no type or connection string provided."""
        with pytest.raises(ValueError, match="Database type must be specified"):
            DialectFactory.create_dialect()

    def test_create_dialect_unsupported_type(self):
        """Test error for unsupported database type."""
        with pytest.raises(ValueError, match="Unsupported database type 'mysql'"):
            DialectFactory.create_dialect(database_type='mysql')

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


class TestDialectFactoryIntegration:
    """Integration tests that test actual dialect creation when available."""

    def test_create_duckdb_dialect_if_available(self):
        """Test creating DuckDB dialect if DuckDB is available."""
        try:
            import duckdb
            # If DuckDB is available, test creating a real dialect
            dialect = DialectFactory.create_dialect('duckdb', database=':memory:')
            assert dialect.name == "DUCKDB"
            assert dialect.supports_feature('json_functions') is True
            assert dialect.supports_feature('jsonb') is False
        except ImportError:
            pytest.skip("DuckDB not available for integration test")

    def test_auto_detect_and_create_duckdb(self):
        """Test auto-detection and creation of DuckDB dialect."""
        try:
            import duckdb
            # Test auto-detection
            dialect = DialectFactory.create_dialect(connection_string=':memory:')
            assert dialect.name == "DUCKDB"
        except ImportError:
            pytest.skip("DuckDB not available for auto-detection test")

    def test_create_from_config_duckdb(self):
        """Test creating dialect from configuration."""
        try:
            import duckdb
            config = {
                'type': 'duckdb',
                'database': ':memory:'
            }
            dialect = DialectFactory.create_from_config(config)
            assert dialect.name == "DUCKDB"
        except ImportError:
            pytest.skip("DuckDB not available for config test")
