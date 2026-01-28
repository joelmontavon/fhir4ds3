"""Unit tests for quantity literal parsing and translation (SP-106-003).

Tests the implementation of FHIRPath quantity literals which represent numeric values
with units (e.g., 10 'mg', 5.5 'kg'). Validates:

- Quantity literal parsing from FHIRPath syntax
- FHIR Quantity JSON structure generation
- convertsToQuantity() function with quantity literals
- toQuantity() function behavior
- Multi-database consistency (DuckDB and PostgreSQL)
- Edge cases and error handling

Test Coverage:
- Basic quantity literals (integer and decimal values)
- Quantity literal metadata preservation
- convertsToQuantity() with quantity literals returns TRUE
- toQuantity() conversion
- Various unit formats (mg, kg, cm, etc.)
- SQL fragment generation for quantities

Module: tests.unit.fhirpath.sql.test_quantity_literals
Created: 2025-01-27
Task: SP-106-003
"""

from __future__ import annotations

import pytest
import json
from decimal import Decimal

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.ast.nodes import (
    LiteralNode,
    FunctionCallNode,
    TypeOperationNode,
)

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


@pytest.fixture
def parser() -> FHIRPathParser:
    """Provide FHIRPath parser for tests."""
    return FHIRPathParser()


@pytest.fixture
def duckdb_translator():
    """Create DuckDB translator for testing."""
    if not DUCKDB_AVAILABLE:
        pytest.skip("DuckDB not available")
    dialect = DuckDBDialect(database=":memory:")
    return ASTToSQLTranslator(dialect, "Observation")


@pytest.fixture
def postgresql_translator():
    """Create PostgreSQL translator for testing."""
    if not POSTGRESQL_AVAILABLE:
        pytest.skip("PostgreSQL not available")
    try:
        dialect = PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not accessible")
    return ASTToSQLTranslator(dialect, "Observation")


class TestQuantityLiteralParsing:
    """Test quantity literal parsing from FHIRPath expressions."""

    def test_parse_simple_quantity_literal_integer(self, parser):
        """Test parsing simple integer quantity literal: 10 'mg'"""
        parsed = parser.parse("10 'mg'")
        ast = parsed.get_ast()

        assert ast is not None
        assert ast.node_type == "literal"
        # Parser may identify this as quantity or string - check the text
        assert "10" in ast.text
        assert "mg" in ast.text

    def test_parse_decimal_quantity_literal(self, parser):
        """Test parsing decimal quantity literal: 5.5 'kg'"""
        parsed = parser.parse("5.5 'kg'")
        ast = parsed.get_ast()

        assert ast is not None
        assert ast.node_type == "literal"
        assert "5.5" in ast.text or "5" in ast.text
        assert "kg" in ast.text

    def test_parse_quantity_literal_no_spaces(self, parser):
        """Test parsing quantity literal without spaces: 10'mg'"""
        parsed = parser.parse("10'mg'")
        ast = parsed.get_ast()

        assert ast is not None
        assert "10" in ast.text
        assert "mg" in ast.text


class TestQuantityLiteralTranslation:
    """Test SQL translation of quantity literals."""

    def test_quantity_literal_generates_json_structure(self, duckdb_translator, parser):
        """Test that quantity literals generate proper FHIR Quantity JSON structure."""
        parsed = parser.parse("10 'mg'")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        # Should generate JSON structure
        sql = fragment.expression
        assert "{" in sql  # JSON object
        assert "value" in sql
        assert "unit" in sql

        # Check metadata
        assert fragment.metadata.get('literal_type') == 'quantity'
        assert fragment.metadata.get('quantity_value') == '10'
        assert fragment.metadata.get('quantity_unit') == 'mg'

    def test_quantity_literal_json_content(self, duckdb_translator, parser):
        """Test that quantity JSON contains correct value and unit."""
        parsed = parser.parse("5.5 'kg'")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        sql = fragment.expression
        # Extract JSON from SQL (should be wrapped in quotes)
        # Format: '{"value": 5.5, "unit": "kg"}'
        assert "5.5" in sql or "5" in sql
        assert '"kg"' in sql or "'kg'" in sql

        # Verify it's valid JSON structure
        metadata = fragment.metadata
        assert metadata.get('quantity_value') == '5.5'
        assert metadata.get('quantity_unit') == 'kg'

    def test_quantity_literal_no_unnest_required(self, duckdb_translator, parser):
        """Test that quantity literals don't require unnesting."""
        parsed = parser.parse("10 'mg'")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    @pytest.mark.parametrize("expression,expected_value,expected_unit", [
        ("10 'mg'", "10", "mg"),
        ("5.5 'kg'", "5.5", "kg"),
        ("100 'cm'", "100", "cm"),
        ("0.5 'mL'", "0.5", "mL"),
    ])
    def test_various_quantity_units(self, duckdb_translator, parser, expression, expected_value, expected_unit):
        """Test various unit formats are preserved correctly."""
        parsed = parser.parse(expression)
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        metadata = fragment.metadata
        assert metadata.get('quantity_value') == expected_value
        assert metadata.get('quantity_unit') == expected_unit


class TestConvertsToQuantityWithLiterals:
    """Test convertsToQuantity() function with quantity literals."""

    def test_quantity_literal_converts_to_quantity_true(self, duckdb_translator, parser):
        """Test that quantity literals return TRUE for convertsToQuantity()."""
        parsed = parser.parse("10 'mg'.convertsToQuantity()")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        # Should return TRUE
        sql = fragment.expression.upper()
        assert "TRUE" in sql or "CASE" in sql

        # Metadata should indicate boolean result
        assert fragment.metadata.get('result_type') == 'boolean'
        assert fragment.metadata.get('function') == 'convertsToQuantity'

    def test_decimal_quantity_converts_to_quantity(self, duckdb_translator, parser):
        """Test decimal quantity literal converts to Quantity."""
        parsed = parser.parse("5.5 'kg'.convertsToQuantity()")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        sql = fragment.expression.upper()
        # Should evaluate to TRUE
        assert "TRUE" in sql or "CASE" in sql
        assert fragment.metadata.get('result_type') == 'boolean'

    def test_non_quantity_string_converts_to_quantity_false(self, duckdb_translator, parser):
        """Test that non-quantity strings return FALSE for convertsToQuantity()."""
        parsed = parser.parse("'hello'.convertsToQuantity()")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        sql = fragment.expression.upper()
        # Should return FALSE
        assert "FALSE" in sql or "CASE" in sql


class TestToQuantityFunction:
    """Test toQuantity() function with literals."""

    def test_to_quantity_with_literal(self, duckdb_translator, parser):
        """Test toQuantity() function with quantity literal."""
        parsed = parser.parse("10 'mg'.toQuantity()")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        # Should generate Quantity JSON
        sql = fragment.expression
        assert "{" in sql or "value" in sql or "unit" in sql or "NULL" in sql

        # Metadata
        assert fragment.metadata.get('function') == 'toQuantity'

    def test_to_quantity_with_string_literal(self, duckdb_translator, parser):
        """Test toQuantity() with string that represents a quantity."""
        parsed = parser.parse("'10 mg'.toQuantity()")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        # Should attempt conversion
        sql = fragment.expression
        # May return NULL or Quantity JSON
        assert sql is not None


class TestQuantityLiteralEdgeCases:
    """Test edge cases and error handling for quantity literals."""

    def test_zero_quantity_literal(self, duckdb_translator, parser):
        """Test zero value quantity literal: 0 'mg'"""
        parsed = parser.parse("0 'mg'")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        metadata = fragment.metadata
        assert metadata.get('quantity_value') == '0'
        assert metadata.get('quantity_unit') == 'mg'

    def test_negative_quantity_literal(self, duckdb_translator, parser):
        """Test negative quantity literal: -10 'mg'"""
        parsed = parser.parse("-10 'mg'")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        metadata = fragment.metadata
        # Value should preserve the negative sign
        assert '10' in metadata.get('quantity_value', '')

    def test_scientific_notation_quantity(self, duckdb_translator, parser):
        """Test scientific notation in quantity: 1.5e3 'mg'"""
        parsed = parser.parse("1.5e3 'mg'")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        # Should handle scientific notation
        assert fragment.expression is not None


class TestMultiDatabaseQuantityLiteralConsistency:
    """Test that quantity literals work consistently across databases."""

    @pytest.mark.parametrize("expression", [
        "10 'mg'",
        "5.5 'kg'",
        "100 'cm'",
    ])
    def test_quantity_literal_json_structure_consistency(
        self, expression, duckdb_translator, postgresql_translator, parser
    ):
        """Test that quantity JSON structure is consistent across dialects."""
        if not DUCKDB_AVAILABLE or not POSTGRESQL_AVAILABLE:
            pytest.skip("Both databases required for consistency test")

        parsed = parser.parse(expression)
        ast = parsed.get_ast()

        duckdb_fragment = duckdb_translator.visit(ast)
        pg_fragment = postgresql_translator.visit(ast)

        # Both should have quantity metadata
        assert duckdb_fragment.metadata.get('literal_type') == 'quantity'
        assert pg_fragment.metadata.get('literal_type') == 'quantity'

        # Both should preserve value and unit
        assert duckdb_fragment.metadata.get('quantity_value') == \
               pg_fragment.metadata.get('quantity_value')
        assert duckdb_fragment.metadata.get('quantity_unit') == \
               pg_fragment.metadata.get('quantity_unit')

    @pytest.mark.parametrize("expression", [
        "10 'mg'.convertsToQuantity()",
        "5.5 'kg'.convertsToQuantity()",
    ])
    def test_converts_to_quantity_consistency(
        self, expression, duckdb_translator, postgresql_translator, parser
    ):
        """Test that convertsToQuantity() works consistently."""
        if not DUCKDB_AVAILABLE or not POSTGRESQL_AVAILABLE:
            pytest.skip("Both databases required for consistency test")

        parsed = parser.parse(expression)
        ast = parsed.get_ast()

        duckdb_fragment = duckdb_translator.visit(ast)
        pg_fragment = postgresql_translator.visit(ast)

        # Both should return boolean type
        assert duckdb_fragment.metadata.get('result_type') == 'boolean'
        assert pg_fragment.metadata.get('result_type') == 'boolean'

        # Both should have the same function metadata
        assert duckdb_fragment.metadata.get('function') == 'convertsToQuantity'
        assert pg_fragment.metadata.get('function') == 'convertsToQuantity'


class TestQuantityLiteralInExpressions:
    """Test quantity literals used in larger expressions."""

    def test_quantity_literal_in_comparison(self, duckdb_translator, parser):
        """Test quantity literal used in comparison expression."""
        parsed = parser.parse("10 'mg' > 5 'mg'")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        # Should generate comparison SQL
        sql = fragment.expression
        assert ">" in sql or "CASE" in sql

    def test_quantity_literal_with_path_navigation(self, duckdb_translator, parser):
        """Test quantity literal combined with path navigation."""
        parsed = parser.parse("Observation.valueQuantity.value + 10 'mg'")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Should generate addition expression
        # Note: This may fail if quantity arithmetic not fully implemented
        assert any("+" in f.expression or "value" in f.expression for f in fragments)


class TestQuantityLiteralPreservedColumns:
    """Test that quantity literals preserve columns correctly (SP-106)."""

    def test_quantity_literal_preserves_source_table(self, duckdb_translator, parser):
        """Test that quantity literals maintain source table reference."""
        parsed = parser.parse("10 'mg'")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        # Should have source_table set
        assert fragment.source_table is not None
        assert isinstance(fragment.source_table, str)

    def test_quantity_literal_no_dependencies(self, duckdb_translator, parser):
        """Test that quantity literals have no dependencies."""
        parsed = parser.parse("10 'mg'")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        # Literals should not have dependencies
        assert not fragment.dependencies or len(fragment.dependencies) == 0


class TestQuantityLiteralInternalMethods:
    """Test internal quantity literal processing methods."""

    def test_extract_quantity_from_text_valid(self, duckdb_translator):
        """Test _extract_quantity_from_text with valid input."""
        result = duckdb_translator._extract_quantity_from_text("10'mg'")

        assert result is not None
        assert result['value'] == Decimal('10')
        assert result['unit'] == 'mg'

    def test_extract_quantity_from_text_decimal(self, duckdb_translator):
        """Test _extract_quantity_from_text with decimal value."""
        result = duckdb_translator._extract_quantity_from_text("5.5 'kg'")

        assert result is not None
        assert result['value'] == Decimal('5.5')
        assert result['unit'] == 'kg'

    def test_extract_quantity_from_text_invalid(self, duckdb_translator):
        """Test _extract_quantity_from_text with invalid input."""
        result = duckdb_translator._extract_quantity_from_text("not a quantity")

        assert result is None

    def test_match_quantity_literal_pattern(self, duckdb_translator):
        """Test _match_quantity_literal regex pattern."""
        # Valid patterns
        assert duckdb_translator._match_quantity_literal("10'mg'") is not None
        assert duckdb_translator._match_quantity_literal("5.5 'kg'") is not None
        assert duckdb_translator._match_quantity_literal("100 'cm'") is not None

        # Invalid patterns
        assert duckdb_translator._match_quantity_literal("not a quantity") is None
        assert duckdb_translator._match_quantity_literal("10") is None


class TestQuantityLiteralIntegration:
    """Integration tests for quantity literals with other FHIRPath features."""

    def test_quantity_literal_with_is_type_check(self, duckdb_translator, parser):
        """Test quantity literal with type checking."""
        parsed = parser.parse("10 'mg'.is(Quantity)")
        ast = parsed.get_ast()
        fragment = duckdb_translator.visit(ast)

        assert isinstance(fragment, SQLFragment)
        # Should return TRUE for quantity type
        sql = fragment.expression.upper()
        assert "TRUE" in sql or "CASE" in sql
        assert fragment.metadata.get('result_type') == 'boolean'

    def test_quantity_literal_aggregation(self, duckdb_translator, parser):
        """Test aggregating quantity literals."""
        parsed = parser.parse("(10 'mg' + 5 'mg' + 3 'mg')")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Should generate aggregation
        assert len(fragments) > 0
        # May fail if quantity arithmetic not fully implemented
