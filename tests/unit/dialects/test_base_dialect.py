"""
Unit tests for base database dialect interface.

Tests the abstract interface and common functionality shared across
all database dialect implementations.
"""

import pytest
from abc import ABC

from fhir4ds.dialects.base import DatabaseDialect


class TestDatabaseDialect:
    """Test cases for DatabaseDialect abstract base class."""

    def test_is_abstract_base_class(self):
        """Test that DatabaseDialect is an abstract base class."""
        assert issubclass(DatabaseDialect, ABC)

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            DatabaseDialect()

    def test_abstract_methods_defined(self):
        """Test that all required abstract methods are defined."""
        abstract_methods = DatabaseDialect.__abstractmethods__

        expected_methods = {
            'get_connection',
            'execute_query',
            'extract_json_field',
            'extract_json_object',
            'check_json_exists',
            'get_json_type',
            'get_json_array_length',
            'unnest_json_array',
            'iterate_json_array',
            'aggregate_to_json_array',
            'create_json_array',
            'create_json_object',
            'json_array_contains',
            'string_concat',
            'substring',
            'split_string',
            'generate_string_join',
            'try_cast',
            'cast_to_timestamp',
            'cast_to_time',
            'cast_to_double',
            'is_finite',
            'generate_math_function',
            'generate_power_operation',
            'generate_current_timestamp',
            'generate_current_date',
            'generate_date_diff',
            'generate_date_literal',
            'generate_datetime_literal',
            'generate_comparison',
            'generate_aggregate_function',
            'generate_where_clause_filter',
            'generate_select_transformation',
            'generate_collection_combine',
            'generate_collection_exclude',
            'wrap_json_array',
            'serialize_json_value',
            'empty_json_array',
            'is_json_array',
            'enumerate_json_array',
            'generate_exists_check',
            'generate_logical_combine',
            'generate_conditional_expression',
            'generate_type_check',
            'generate_all_true',
            'generate_any_true',
            'generate_all_false',
            'generate_any_false',
        }

        # All expected methods should be abstract
        for method in expected_methods:
            assert method in abstract_methods, f"Method {method} should be abstract"

    def test_concrete_methods_available(self):
        """Test that concrete utility methods are available."""
        # These should be accessible even though the class is abstract
        assert hasattr(DatabaseDialect, 'quote_identifier')
        assert hasattr(DatabaseDialect, 'cast_to_type')
        assert hasattr(DatabaseDialect, 'supports_feature')


class MockDialect(DatabaseDialect):
    """Mock dialect implementation for testing concrete methods."""

    def __init__(self):
        super().__init__()
        self.name = "MOCK"

    # Implement all abstract methods with simple implementations
    def get_connection(self): return None
    def execute_query(self, sql): return []
    def extract_json_field(self, column, path): return f"extract_field({column}, {path})"
    def extract_json_object(self, column, path): return f"extract_object({column}, {path})"
    def check_json_exists(self, column, path): return f"exists({column}, {path})"
    def get_json_type(self, column): return f"type({column})"
    def get_json_array_length(self, column, path=None): return f"length({column})"
    def unnest_json_array(self, column, path, alias): return f"unnest({column}, {path}) AS {alias}"
    def iterate_json_array(self, column, path): return f"iterate({column}, {path})"
    def aggregate_to_json_array(self, expression): return f"agg_array({expression})"
    def create_json_array(self, *args): return f"array({', '.join(map(str, args))})"
    def create_json_object(self, *args): return f"object({', '.join(map(str, args))})"
    def json_array_contains(self, array_expr, scalar_expr): return f"json_array_contains({array_expr}, {scalar_expr})"
    def string_concat(self, left, right): return f"concat({left}, {right})"
    def substring(self, expression, start, length): return f"substr({expression}, {start}, {length})"
    def split_string(self, expression, delimiter): return f"split({expression}, {delimiter})"
    def generate_string_join(self, collection_expr, delimiter_expr, is_json_collection):
        return f"join({collection_expr}, {delimiter_expr}, json={is_json_collection})"
    def try_cast(self, expression, target_type): return f"try_cast({expression}, {target_type})"
    def cast_to_timestamp(self, expression): return f"timestamp({expression})"
    def cast_to_time(self, expression): return f"time({expression})"
    def cast_to_double(self, expression): return f"double({expression})"
    def is_finite(self, expression): return f"isfinite({expression})"
    def generate_math_function(self, function_name, *args): return f"{function_name}({', '.join(args)})"
    def generate_power_operation(self, base_expr, exponent_expr): return f"power({base_expr}, {exponent_expr})"
    def generate_current_timestamp(self): return "now()"
    def generate_current_date(self): return "today()"
    def generate_date_diff(self, unit, start_date, end_date): return f"diff({unit}, {start_date}, {end_date})"
    def generate_aggregate_function(self, function_name, expression, filter_condition=None, distinct=False):
        return f"{function_name}({expression})"
    def generate_where_clause_filter(self, collection_expr, condition_sql):
        return f"filter({collection_expr}, {condition_sql})"
    def generate_select_transformation(self, collection_expr, transform_path):
        return f"select({collection_expr}, {transform_path})"
    def generate_collection_combine(self, first_collection, second_collection):
        return f"combine({first_collection}, {second_collection})"
    def generate_collection_exclude(self, collection_expr, exclusion_expr):
        return f"exclude({collection_expr}, {exclusion_expr})"
    def wrap_json_array(self, expression):
        return f"wrap_array({expression})"
    def serialize_json_value(self, expression):
        return f"serialize({expression})"
    def empty_json_array(self):
        return "empty_array()"
    def is_json_array(self, expression):
        return f"is_array({expression})"
    def enumerate_json_array(self, array_expr, value_alias, index_alias):
        return f"SELECT 0 AS {index_alias}, {array_expr} AS {value_alias}"
    def generate_exists_check(self, fragment, is_collection):
        return f"exists({fragment}, {is_collection})"
    def generate_logical_combine(self, left_condition, operator, right_condition):
        return f"({left_condition} {operator} {right_condition})"
    def generate_conditional_expression(self, condition, true_expr, false_expr):
        return f"if({condition}, {true_expr}, {false_expr})"
    def generate_date_literal(self, date_value): return f"DATE '{date_value}'"
    def generate_datetime_literal(self, datetime_value): return f"TIMESTAMP '{datetime_value}'"
    def generate_comparison(self, left_expr, operator, right_expr): return f"({left_expr} {operator} {right_expr})"
    def generate_type_check(self, expression, fhirpath_type): return f"is_type({expression}, {fhirpath_type})"
    def generate_type_cast(self, expression, target_type): return f"cast({expression}, {target_type})"
    def generate_boolean_not(self, expression): return f"NOT({expression})"
    def generate_regex_match(self, string_expr, regex_pattern): return f"regex_match({string_expr}, {regex_pattern})"
    def generate_regex_replace(self, string_expr, regex_pattern, substitution): return f"regex_replace({string_expr}, {regex_pattern}, {substitution})"
    def generate_substring_check(self, string_expr, substring): return f"substring_check({string_expr}, {substring})"
    def generate_collection_type_filter(self, collection_expr, fhirpath_type): return f"oftype({collection_expr}, {fhirpath_type})"
    def generate_empty_check(self, collection_expr): return f"empty({collection_expr})"
    def generate_all_true(self, collection_expr): return f"all_true({collection_expr})"
    def generate_any_true(self, collection_expr): return f"any_true({collection_expr})"
    def generate_all_false(self, collection_expr): return f"all_false({collection_expr})"
    def generate_any_false(self, collection_expr): return f"any_false({collection_expr})"
    def generate_all_check(self, collection_expr, criteria_expr, element_alias): return f"all({collection_expr}, {criteria_expr})"
    def generate_array_skip(self, array_expr, skip_count): return f"skip({array_expr}, {skip_count})"
    def generate_array_take(self, array_expr, take_count): return f"take({array_expr}, {take_count})"
    def generate_array_last(self, array_expr): return f"last({array_expr})"
    def generate_string_function(self, function_name, *args): return f"{function_name}({', '.join(args)})"
    def generate_case_conversion(self, expression, conversion_type): return f"{conversion_type}({expression})"
    def generate_char_array(self, string_expr): return f"chars({string_expr})"
    def generate_prefix_check(self, string_expr, prefix): return f"starts_with({string_expr}, {prefix})"
    def generate_suffix_check(self, string_expr, suffix): return f"ends_with({string_expr}, {suffix})"
    def generate_trim(self, string_expr): return f"trim({string_expr})"
    def extract_extension_values(self, *args, **kwargs): return "extension_values"
    def filter_extension_by_url(self, *args, **kwargs): return "extension_filter"
    def generate_decimal_boundary(self, *args, **kwargs): return "decimal_boundary"
    def generate_decimal_division(self, *args, **kwargs): return "decimal_division"
    def generate_integer_division(self, *args, **kwargs): return "integer_division"
    def generate_modulo(self, *args, **kwargs): return "modulo"
    def generate_quantity_boundary(self, *args, **kwargs): return "quantity_boundary"
    def generate_temporal_boundary(self, *args, **kwargs): return "temporal_boundary"
    def generate_time_literal(self, *args, **kwargs): return "TIME '00:00'"
    def project_json_array(self, *args, **kwargs): return "project_json_array"
    def extract_primitive_value(self, column, path): return f"extract_primitive({column}, {path})"
    def extract_json_string(self, column, path): return f"extract_string({column}, {path})"
    def extract_json_boolean(self, column, path): return f"extract_boolean({column}, {path})"
    def extract_json_integer(self, column, path): return f"extract_integer({column}, {path})"
    def extract_json_decimal(self, column, path): return f"extract_decimal({column}, {path})"
    def generate_current_time(self): return "current_time()"
    def safe_cast_to_decimal(self, expression): return f"TRY_CAST({expression} AS DECIMAL)"
    def safe_cast_to_integer(self, expression): return f"TRY_CAST({expression} AS BIGINT)"
    def safe_cast_to_date(self, expression): return f"TRY_CAST({expression} AS DATE)"
    def safe_cast_to_timestamp(self, expression): return f"TRY_CAST({expression} AS TIMESTAMP)"
    def safe_cast_to_boolean(self, expression): return f"TRY_CAST({expression} AS BOOLEAN)"


class TestDatabaseDialectConcreteMethods:
    """Test cases for concrete methods in DatabaseDialect."""

    @pytest.fixture
    def dialect(self):
        """Create mock dialect for testing."""
        return MockDialect()

    def test_initialization(self, dialect):
        """Test dialect initialization sets correct defaults."""
        assert dialect.name == "MOCK"
        assert dialect.supports_jsonb is False
        assert dialect.supports_json_functions is True
        assert dialect.json_type == "JSON"
        assert dialect.cast_syntax == "::"
        assert dialect.quote_char == '"'

    def test_quote_identifier(self, dialect):
        """Test identifier quoting."""
        assert dialect.quote_identifier("table_name") == '"table_name"'
        assert dialect.quote_identifier("column") == '"column"'

    def test_cast_to_type(self, dialect):
        """Test type casting syntax."""
        assert dialect.cast_to_type("expression", "INTEGER") == "expression::INTEGER"
        assert dialect.cast_to_type("value", "VARCHAR") == "value::VARCHAR"

    def test_supports_feature(self, dialect):
        """Test feature support checking."""
        assert dialect.supports_feature('jsonb') is False
        assert dialect.supports_feature('json_functions') is True
        assert dialect.supports_feature('unknown_feature') is False

    def test_supports_feature_custom_dialect(self):
        """Test feature support with custom dialect settings."""
        dialect = MockDialect()
        dialect.supports_jsonb = True

        assert dialect.supports_feature('jsonb') is True
        assert dialect.supports_feature('json_functions') is True
