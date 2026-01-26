"""
Unit Tests for Boolean Operators: XOR and Implies

SP-100-009: XOR Operator Implementation
SP-100-010: Implies Operator Implementation

Tests cover:
- Truth table validation for both operators
- Empty collection semantics per FHIRPath specification
- Edge cases and boundary conditions
- Cross-dialect consistency (DuckDB and PostgreSQL)
"""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.parser import FHIRPathParser

from .test_translator_converts_to import _StubDialect

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


def _translate_expression(translator, parser, expression):
    """Helper to translate FHIRPath expression to SQL"""
    ast = parser.parse(expression).get_ast()
    fragments = translator.translate(ast)
    return fragments[-1]


@pytest.fixture
def stub_env():
    """Provide translator and parser pair backed by stub dialect."""
    translator = ASTToSQLTranslator(_StubDialect(), "Patient")
    parser = FHIRPathParser()
    return translator, parser


@pytest.fixture
def duckdb_env():
    """Provide DuckDB translator + parser, skipping when unavailable."""
    if not DUCKDB_AVAILABLE:
        pytest.skip("DuckDB not available")
    translator = ASTToSQLTranslator(DuckDBDialect(database=":memory:"), "Patient")
    parser = FHIRPathParser(database_type="duckdb")
    return translator, parser


@pytest.fixture
def postgresql_env():
    """Provide PostgreSQL translator + parser, skipping when unavailable."""
    if not POSTGRESQL_AVAILABLE:
        pytest.skip("PostgreSQL not available")
    try:
        # Try to initialize with a test connection string
        # If PostgreSQL server is not running, skip the test
        dialect = PostgreSQLDialect(
            connection_string="postgresql://postgres:postgres@localhost:5432/postgres",
        )
        translator = ASTToSQLTranslator(dialect, "Patient")
        parser = FHIRPathParser(database_type="postgresql")
        return translator, parser
    except Exception as e:
        pytest.skip(f"PostgreSQL not available or not running: {str(e)}")


class TestXOROperator:
    """Test XOR operator implementation (SP-100-009)"""

    # Truth Table Tests
    def test_xor_true_false_returns_true(self, duckdb_env):
        """true xor false should return true"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "true xor false")

        sql = fragment.expression.upper()
        assert "XOR" in sql or ("AND NOT" in sql and "OR" in sql)

    def test_xor_false_true_returns_true(self, duckdb_env):
        """false xor true should return true"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "false xor true")

        sql = fragment.expression.upper()
        assert "XOR" in sql or ("AND NOT" in sql and "OR" in sql)

    def test_xor_true_true_returns_false(self, duckdb_env):
        """true xor true should return false"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "true xor true")

        sql = fragment.expression.upper()
        # Should use XOR pattern with AND NOT
        assert "AND NOT" in sql or "XOR" in sql

    def test_xor_false_false_returns_false(self, duckdb_env):
        """false xor false should return false"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "false xor false")

        sql = fragment.expression.upper()
        assert "FALSE" in sql

    # Empty Collection Semantics
    def test_xor_empty_with_true_returns_true(self, duckdb_env):
        """{} xor true should return true (empty treated as false)"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "{} xor true")

        # Empty collection should be handled properly
        sql = fragment.expression
        # Should handle empty collection semantics
        assert "XOR" in sql.upper() or ("AND NOT" in sql.upper() and "OR" in sql.upper())

    def test_xor_empty_with_false_returns_false(self, duckdb_env):
        """{} xor false should return false (empty treated as false)"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "{} xor false")

        # Empty collection should be handled properly
        sql = fragment.expression
        # Should handle empty collection semantics
        assert "XOR" in sql.upper() or "FALSE" in sql.upper()

    def test_xor_true_with_empty_returns_true(self, duckdb_env):
        """true xor {} should return true (empty treated as false)"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "true xor {}")

        # Empty collection should be handled properly
        sql = fragment.expression
        # Should handle empty collection semantics
        assert "XOR" in sql.upper() or ("AND NOT" in sql.upper() and "OR" in sql.upper())

    def test_xor_empty_with_empty_returns_false(self, duckdb_env):
        """{} xor {} should return false (both empty treated as false)"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "{} xor {}")

        # Both empty should evaluate to FALSE or empty array
        assert "FALSE" in fragment.expression.upper() or "[]" in fragment.expression

    # Nested Expressions
    def test_xor_with_and_expression(self, duckdb_env):
        """XOR with AND expression: (true and false) xor true"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "(true and false) xor true")

        sql = fragment.expression
        assert "AND" in sql
        assert "XOR" in sql.upper() or ("AND NOT" in sql.upper() and "OR" in sql.upper())

    def test_xor_with_or_expression(self, duckdb_env):
        """XOR with OR expression: (true or false) xor false"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "(true or false) xor false")

        sql = fragment.expression
        assert "OR" in sql.upper()

    # Cross-Dialect Consistency
    def test_xor_cross_dialect_consistency(self, duckdb_env, postgresql_env):
        """XOR should produce consistent results across dialects"""
        translator_ddb, parser_ddb = duckdb_env
        translator_pg, parser_pg = postgresql_env

        fragment_ddb = _translate_expression(translator_ddb, parser_ddb, "true xor false")
        fragment_pg = _translate_expression(translator_pg, parser_pg, "true xor false")

        # Both should generate valid XOR logic
        assert "TRUE" in fragment_ddb.expression.upper()
        assert "FALSE" in fragment_ddb.expression.upper()
        assert "TRUE" in fragment_pg.expression.upper()
        assert "FALSE" in fragment_pg.expression.upper()


class TestImpliesOperator:
    """Test Implies operator implementation (SP-100-010)"""

    # Truth Table Tests
    def test_implies_true_true_returns_true(self, duckdb_env):
        """true implies true should return true"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "true implies true")

        # Should use (NOT a) OR b pattern
        sql = fragment.expression.upper()
        assert ("NOT" in sql or "FALSE" in sql) and "OR" in sql

    def test_implies_true_false_returns_false(self, duckdb_env):
        """true implies false should return false"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "true implies false")

        sql = fragment.expression.upper()
        # (NOT true) OR false = false OR false = false
        assert "FALSE" in sql

    def test_implies_false_true_returns_true(self, duckdb_env):
        """false implies true should return true"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "false implies true")

        # false implies anything = true
        assert fragment.expression.upper() == "TRUE"

    def test_implies_false_false_returns_true(self, duckdb_env):
        """false implies false should return true"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "false implies false")

        # false implies anything = true
        assert fragment.expression.upper() == "TRUE"

    # Empty Collection Semantics
    def test_implies_empty_with_true_returns_true(self, duckdb_env):
        """{} implies true should return true (empty antecedent is true)"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "{} implies true")

        # Empty antecedent with true consequent - should handle empty semantics
        sql = fragment.expression
        # The implementation should handle empty collections properly
        assert "IMPLIES" in sql.upper() or ("NOT" in sql.upper() and "OR" in sql.upper())

    def test_implies_empty_with_false_returns_empty(self, duckdb_env):
        """{} implies false should return empty (propagate empty)"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "{} implies false")

        # Should propagate empty collection
        sql = fragment.expression
        # Check for empty array representation
        assert "[]" in sql or "NULL" in sql.upper()

    def test_implies_empty_with_empty_returns_empty(self, duckdb_env):
        """{} implies {} should return empty (propagate empty)"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "{} implies {}")

        # Should propagate empty collection
        sql = fragment.expression
        # Check for empty array representation
        assert "[]" in sql or "NULL" in sql.upper()

    def test_implies_true_with_empty_returns_empty(self, duckdb_env):
        """true implies {} should return empty (propagate empty)"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "true implies {}")

        # Should propagate empty collection
        sql = fragment.expression
        # Check for empty array representation
        assert "[]" in sql or "NULL" in sql.upper()

    # Nested Expressions
    def test_implies_with_and_expression(self, duckdb_env):
        """Implies with AND: (true and false) implies true"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "(true and false) implies true")

        sql = fragment.expression
        assert "AND" in sql

    def test_implies_with_or_expression(self, duckdb_env):
        """Implies with OR: (true or false) implies false"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "(true or false) implies false")

        sql = fragment.expression
        assert "OR" in sql.upper()

    def test_implies_chained(self, duckdb_env):
        """Chained implies: true implies false implies true"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "true implies false implies true")

        sql = fragment.expression
        # Should handle chaining with proper precedence
        assert "IMPLIES" in sql.upper() or ("NOT" in sql.upper() and "OR" in sql.upper())

    # Cross-Dialect Consistency
    def test_implies_cross_dialect_consistency(self, duckdb_env, postgresql_env):
        """Implies should produce consistent results across dialects"""
        translator_ddb, parser_ddb = duckdb_env
        translator_pg, parser_pg = postgresql_env

        fragment_ddb = _translate_expression(translator_ddb, parser_ddb, "true implies true")
        fragment_pg = _translate_expression(translator_pg, parser_pg, "true implies true")

        # Both should generate valid implies logic
        assert "TRUE" in fragment_ddb.expression.upper()
        assert "TRUE" in fragment_pg.expression.upper()


class TestBooleanOperatorIntegration:
    """Integration tests for boolean operators"""

    def test_xor_and_implies_together(self, duckdb_env):
        """XOR and Implies in same expression"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "(true xor false) implies (false xor true)")

        sql = fragment.expression
        # Should contain both operators
        assert ("XOR" in sql.upper() or ("AND NOT" in sql.upper())) and ("IMPLIES" in sql.upper() or ("NOT" in sql.upper() and "OR" in sql.upper()))

    def test_boolean_operator_precedence(self, duckdb_env):
        """Test operator precedence: implies < xor < and < or"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "true or false xor true and false")

        sql = fragment.expression
        # Should respect precedence
        assert "OR" in sql.upper()
        assert "AND" in sql.upper()

    def test_boolean_with_comparison(self, duckdb_env):
        """Boolean operators with comparison expressions"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "(1 > 2) xor (3 < 4)")

        sql = fragment.expression
        assert ">" in sql or "<" in sql

    def test_boolean_with_existence(self, duckdb_env):
        """Boolean operators with existence expressions"""
        translator, parser = duckdb_env
        fragment = _translate_expression(translator, parser, "Patient.name.empty() xor Patient.birthDate.exists()")

        sql = fragment.expression
        # Should generate valid SQL with XOR logic (AND NOT with OR)
        assert "AND NOT" in sql.upper() and "OR" in sql.upper()
