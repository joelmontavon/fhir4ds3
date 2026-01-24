"""Regression tests for arithmetic operator translation edge cases.

Covers type coercion, division safety, integer division semantics, and modulo
handling to ensure alignment with FHIRPath specification across dialects.
"""

from __future__ import annotations

from fhir4ds.fhirpath.ast.nodes import LiteralNode, OperatorNode
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


def _literal(value, text=None):
    """Helper to create literal nodes with minimal boilerplate."""
    literal = LiteralNode(
        node_type="literal",
        text=text or str(value),
        value=value,
    )
    literal.children = []
    return literal


def _operator_node(symbol: str, left: LiteralNode, right: LiteralNode) -> OperatorNode:
    """Helper to create binary operator nodes."""
    expr_text = f"{left.text} {symbol} {right.text}"
    node = OperatorNode(
        node_type="operator",
        text=expr_text,
        operator=symbol,
        operator_type="binary",
    )
    node.add_child(left)
    node.add_child(right)
    return node


class TestDuckDBArithmeticTranslation:
    """Validate arithmetic expression SQL executed against DuckDB."""

    def test_decimal_division_promotes_integer_operands(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        node = _operator_node("/", _literal(5), _literal(2))

        fragment = translator.visit_operator(node)
        result = duckdb_dialect.execute_query(f"SELECT {fragment.expression} AS value")

        assert result == [(2.5,)]

    def test_integer_division_truncates_toward_zero(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        node = _operator_node("div", _literal(-5), _literal(2))

        fragment = translator.visit_operator(node)
        result = duckdb_dialect.execute_query(f"SELECT {fragment.expression} AS value")

        assert result == [(-2,)]

    def test_division_by_zero_returns_null(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        node = _operator_node("/", _literal(5), _literal(0))

        fragment = translator.visit_operator(node)
        result = duckdb_dialect.execute_query(f"SELECT {fragment.expression} AS value")

        assert result == [(None,)]

    def test_modulo_by_zero_returns_null(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        node = _operator_node("mod", _literal(10), _literal(0))

        fragment = translator.visit_operator(node)
        result = duckdb_dialect.execute_query(f"SELECT {fragment.expression} AS value")

        assert result == [(None,)]

    def test_mixed_type_addition_promotes_to_decimal(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        node = _operator_node("+", _literal(5), _literal(2.5, text="2.5"))

        fragment = translator.visit_operator(node)
        result = duckdb_dialect.execute_query(f"SELECT {fragment.expression} AS value")

        assert result == [(7.5,)]


class TestPostgreSQLArithmeticTranslation:
    """Ensure PostgreSQL dialect SQL contains safety guards."""

    def test_division_expression_contains_case_and_numeric_cast(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        node = _operator_node("/", _literal(5), _literal(2))

        fragment = translator.visit_operator(node)
        sql = fragment.expression.replace("\n", " ").upper()

        assert "CASE" in sql
        assert "/ (" in sql or "/(" in sql
        assert "NUMERIC" in sql

    def test_integer_division_uses_floor_and_ceiling(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        node = _operator_node("div", _literal(-5), _literal(2))

        fragment = translator.visit_operator(node)
        sql = fragment.expression.replace("\n", " ").lower()

        assert "floor(" in sql
        assert "ceil(" in sql
        assert "case" in sql

    def test_modulo_expression_handles_zero_guard(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        node = _operator_node("mod", _literal(10), _literal(0))

        fragment = translator.visit_operator(node)
        sql = fragment.expression.replace("\n", " ").lower()

        assert "case" in sql
        assert "%" in sql
