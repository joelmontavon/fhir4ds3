"""
Unit tests for comparison operator translation (SP-008-008).

Validates precision-aware handling of temporal literals that require
NULL outcomes when operand precision differs, following FHIRPath rules.
"""

import pytest

from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


class _SimpleDialect:
    """Minimal dialect implementation for translation testing."""

    name = "TEST"

    def generate_datetime_literal(self, datetime_value: str) -> str:
        return f"TIMESTAMP '{datetime_value.replace('T', ' ')}'"

    def generate_date_literal(self, date_value: str) -> str:
        return f"DATE '{date_value}'"

    def generate_time_literal(self, time_value: str) -> str:
        return f"TIME '{time_value}'"

    def generate_comparison(self, left_expr: str, operator: str, right_expr: str) -> str:
        return f"({left_expr} {operator} {right_expr})"

    def generate_logical_combine(self, left_condition: str, operator: str, right_condition: str) -> str:
        return f"({left_condition}) {operator} ({right_condition})"


@pytest.fixture
def translator():
    """Create translator with simple stub dialect."""
    dialect = _SimpleDialect()
    return ASTToSQLTranslator(dialect, "Patient")


def _translate_expression(translator: ASTToSQLTranslator, expression: str) -> str:
    parser = FHIRPathParser()
    enhanced_ast = parser.parse(expression).get_ast()
    fhirpath_ast = enhanced_ast
    fragments = translator.translate(fhirpath_ast)
    assert fragments, "Translator should produce at least one fragment"
    return fragments[-1].expression


class TestTemporalComparisonTranslation:
    """Precision-aware comparison translation tests."""

    def test_month_vs_day_comparison_uses_case(self, translator):
        sql = _translate_expression(translator, "@2018-03 < @2018-03-01")
        assert "CASE" in sql
        assert "NULL" in sql.upper()
        assert "<=" in sql
        assert "TIMESTAMP '2018-03-01 00:00:00'" in sql

    def test_minute_vs_second_datetime_comparison_uses_case(self, translator):
        sql = _translate_expression(translator, "@2018-03-01T10:30 < @2018-03-01T10:30:00")
        assert "CASE" in sql
        assert "TIMESTAMP '2018-03-01 10:30:00'" in sql
        assert "NULL" in sql.upper()

    def test_time_minute_vs_second_comparison_uses_case(self, translator):
        sql = _translate_expression(translator, "@T10:30 < @T10:30:00")
        assert "CASE" in sql
        assert "TIME '10:30:00'" in sql
        assert "NULL" in sql.upper()

    def test_full_precision_dates_use_direct_comparison(self, translator):
        sql = _translate_expression(translator, "@2018-03-01 < @2018-03-02")
        assert "CASE" not in sql  # full precision should fall back to direct comparison
        assert "(" in sql and "<" in sql

    def test_greater_or_equal_handles_partial_precision(self, translator):
        sql = _translate_expression(translator, "@2018-03 >= @2018-03-01")
        assert "CASE" in sql
        assert ">=" in sql or ">" in sql  # ensuring operator logic present
        assert "NULL" in sql.upper()
