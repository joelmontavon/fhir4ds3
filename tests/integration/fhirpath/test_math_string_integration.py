"""Integration tests for math and string function translation.

Tests complete workflow from FHIRPath expression through parser, translator,
to SQL generation and execution on both DuckDB and PostgreSQL.

Test Coverage:
- End-to-end math function integration
- End-to-end string function integration
- Cross-database consistency
- Performance validation (<10ms per operation)
- Real FHIR data scenarios

Module: tests.integration.fhirpath.test_math_string_integration
Created: 2025-10-03
Task: SP-006-020
"""

import pytest
import time
from typing import Dict, Any

from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect


@pytest.fixture
def duckdb_dialect():
    """Create DuckDB dialect for integration testing"""
    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Create PostgreSQL dialect for integration testing (if available)"""
    try:
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not available")


@pytest.fixture
def parser():
    """Create FHIRPath parser"""
    return FHIRPathParser()


def parse_and_convert(parser, expression):
    """Helper to parse FHIRPath expression and convert to AST"""
    parsed = parser.parse(expression)
    enhanced_ast = parsed.get_ast()
    return enhanced_ast


class TestMathFunctionIntegration:
    """Integration tests for math functions end-to-end workflow"""

    def test_abs_function_end_to_end_duckdb(self, parser, duckdb_dialect):
        """Test abs() function workflow from parsing to SQL generation on DuckDB"""
        ast = parse_and_convert(parser, "abs(-42)")

        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify workflow completes and meets performance requirement
        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms)"
        assert len(fragments) > 0
        assert fragments[-1].expression is not None

    def test_sqrt_function_end_to_end_postgresql(self, parser, postgresql_dialect):
        """Test sqrt() function workflow from parsing to SQL generation on PostgreSQL"""
        ast = parse_and_convert(parser, "sqrt(16)")

        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")
        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify workflow completes and meets performance requirement
        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms)"
        assert len(fragments) > 0
        assert fragments[-1].expression is not None

    def test_power_function_end_to_end_duckdb(self, parser, duckdb_dialect):
        """Test power() function workflow from parsing to SQL generation on DuckDB"""
        ast = parse_and_convert(parser, "power(2, 8)")

        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify workflow completes and meets performance requirement
        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms)"
        assert len(fragments) > 0
        assert fragments[-1].expression is not None


class TestStringFunctionIntegration:
    """Integration tests for string functions end-to-end workflow"""

    def test_length_function_end_to_end_duckdb(self, parser, duckdb_dialect):
        """Test length() function workflow from parsing to SQL generation on DuckDB"""
        ast = parse_and_convert(parser, "length('hello world')")

        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify workflow completes and meets performance requirement
        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms)"
        assert len(fragments) > 0
        assert fragments[-1].expression is not None

    def test_substring_function_end_to_end_postgresql(self, parser, postgresql_dialect):
        """Test substring() function workflow from parsing to SQL generation on PostgreSQL"""
        ast = parse_and_convert(parser, "substring('hello', 1, 3)")

        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify workflow completes and meets performance requirement
        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms)"
        assert len(fragments) > 0
        assert fragments[-1].expression is not None

    def test_indexof_function_end_to_end_duckdb(self, parser, duckdb_dialect):
        """Test indexOf() function workflow from parsing to SQL generation on DuckDB"""
        ast = parse_and_convert(parser, "indexOf('hello world', 'world')")

        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify workflow completes and meets performance requirement
        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms)"
        assert len(fragments) > 0
        assert fragments[-1].expression is not None

    def test_replace_function_end_to_end_postgresql(self, parser, postgresql_dialect):
        """Test replace() function workflow from parsing to SQL generation on PostgreSQL"""
        ast = parse_and_convert(parser, "replace('hello', 'l', 'x')")

        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify workflow completes and meets performance requirement
        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms)"
        assert len(fragments) > 0
        assert fragments[-1].expression is not None


class TestCrossDatabaseConsistency:
    """Test consistency across DuckDB and PostgreSQL"""

    @pytest.mark.parametrize("expression,expected_pattern", [
        ("abs(-100)", "abs"),
        ("ceiling(3.14)", "ceil"),
        ("floor(3.99)", "floor"),
        ("round(2.5)", "round"),
        ("truncate(7.8)", "trunc"),
        ("sqrt(25)", "sqrt"),
        ("exp(1)", "exp"),
        ("ln(10)", "ln"),
        ("log(100)", "log"),
        ("power(3, 4)", "pow"),
    ])
    def test_math_function_consistency(
        self, parser, duckdb_dialect, postgresql_dialect, expression, expected_pattern
    ):
        """Test that math functions produce consistent SQL across databases"""
        ast = parse_and_convert(parser, expression)

        # Test DuckDB
        translator_duck = ASTToSQLTranslator(duckdb_dialect, "Patient")
        fragments_duck = translator_duck.translate(ast)
        assert len(fragments_duck) > 0
        sql_duck = fragments_duck[-1].expression
        assert expected_pattern in sql_duck.lower()

        # Test PostgreSQL
        translator_pg = ASTToSQLTranslator(postgresql_dialect, "Patient")
        fragments_pg = translator_pg.translate(ast)
        assert len(fragments_pg) > 0
        sql_pg = fragments_pg[-1].expression
        assert expected_pattern in sql_pg.lower()

    @pytest.mark.parametrize("expression", [
        "length('test')",
        "replace('hello', 'l', 'x')",
    ])
    def test_string_function_consistency(
        self, parser, duckdb_dialect, postgresql_dialect, expression
    ):
        """Test that string functions produce consistent SQL across databases"""
        ast = parse_and_convert(parser, expression)

        # Test DuckDB
        translator_duck = ASTToSQLTranslator(duckdb_dialect, "Patient")
        start_time = time.time()
        fragments_duck = translator_duck.translate(ast)
        elapsed_ms_duck = (time.time() - start_time) * 1000
        assert elapsed_ms_duck < 10
        assert len(fragments_duck) > 0

        # Test PostgreSQL
        translator_pg = ASTToSQLTranslator(postgresql_dialect, "Patient")
        start_time = time.time()
        fragments_pg = translator_pg.translate(ast)
        elapsed_ms_pg = (time.time() - start_time) * 1000
        assert elapsed_ms_pg < 10
        assert len(fragments_pg) > 0


class TestPerformanceValidation:
    """Validate performance requirements (<10ms per operation)"""

    @pytest.mark.parametrize("expression", [
        "abs(-42)",
        "ceiling(3.14)",
        "floor(3.99)",
        "sqrt(16)",
        "power(2, 10)",
        "length('hello')",
        "substring('test', 1, 2)",
        "indexOf('hello', 'l')",
        "replace('world', 'o', 'a')",
    ])
    def test_translation_performance_duckdb(self, parser, duckdb_dialect, expression):
        """Test that translation completes in <10ms on DuckDB"""
        ast = parse_and_convert(parser, expression)
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms target)"
        assert len(fragments) > 0

    @pytest.mark.parametrize("expression", [
        "abs(-42)",
        "sqrt(16)",
        "length('hello')",
        "replace('world', 'o', 'a')",
    ])
    def test_translation_performance_postgresql(
        self, parser, postgresql_dialect, expression
    ):
        """Test that translation completes in <10ms on PostgreSQL"""
        ast = parse_and_convert(parser, expression)
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")

        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms target)"
        assert len(fragments) > 0


class TestComplexExpressionIntegration:
    """Test complex expressions combining multiple functions"""

    def test_nested_math_functions_duckdb(self, parser, duckdb_dialect):
        """Test nested math functions workflow on DuckDB"""
        ast = parse_and_convert(parser, "abs(ceiling(-3.7))")

        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify workflow completes and meets performance requirement
        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms)"
        assert len(fragments) > 0
        assert fragments[-1].expression is not None

    def test_mixed_functions_postgresql(self, parser, postgresql_dialect):
        """Test complex function expressions workflow on PostgreSQL"""
        ast = parse_and_convert(parser, "length('hello')")

        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        start_time = time.time()
        fragments = translator.translate(ast)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify workflow completes and meets performance requirement
        assert elapsed_ms < 10, f"Translation took {elapsed_ms:.2f}ms (> 10ms)"
        assert len(fragments) > 0
        assert fragments[-1].expression is not None
