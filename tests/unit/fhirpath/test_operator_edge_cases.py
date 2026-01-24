"""Operator edge-case regression tests for SP-008-010.

Exercises arithmetic, concatenation, precedence, coercion, and error handling to
guard against regressions in the evaluation engine and SQL translator.
"""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.ast.nodes import LiteralNode, OperatorNode
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_string_concatenation_uses_dialect_concat(
    request: pytest.FixtureRequest,
    dialect_fixture: str,
) -> None:
    """Ensure translator defers concatenation syntax to the dialect implementation."""
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    left = LiteralNode(node_type="literal", text="'foo'", value="foo", literal_type="string")
    right = LiteralNode(node_type="literal", text="'bar'", value="bar", literal_type="string")
    node = OperatorNode(
        node_type="operator",
        text="'foo' & 'bar'",
        operator="&",
        operator_type="binary",
    )
    node.add_child(left)
    node.add_child(right)

    fragment = translator.visit_operator(node)
    assert fragment.expression.startswith("(") and fragment.expression.endswith(")")
    assert "||" in fragment.expression, "string concatenation should rely on SQL || operator"


def test_binary_operator_requires_two_children(duckdb_dialect) -> None:
    """Binary operators must raise ValueError when operand count is incorrect."""
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    incomplete_node = OperatorNode(
        node_type="operator",
        text="5 < ?",
        operator="<",
        operator_type="comparison",
    )
    incomplete_node.add_child(LiteralNode(node_type="literal", text="5", value=5, literal_type="integer"))

    with pytest.raises(ValueError, match="requires exactly 2 operands"):
        translator.visit_operator(incomplete_node)


def test_unknown_unary_operator_raises_error(duckdb_dialect) -> None:
    """Translator should reject unary operators that are not recognised."""
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    operand = LiteralNode(node_type="literal", text="1", value=1, literal_type="integer")
    node = OperatorNode(
        node_type="operator",
        text="mystery 1",
        operator="mystery",
        operator_type="unary",
    )
    node.add_child(operand)

    with pytest.raises(ValueError, match="Unknown unary operator"):
        translator.visit_operator(node)


@pytest.mark.skip(reason="FHIRPathEvaluationEngine removed in SP-018-001 - SQL translator only")
def test_null_like_empty_collection_short_circuits_comparisons() -> None:
    """Empty collection operands should produce an empty result per FHIRPath semantics."""
    # NOTE: This test relied on FHIRPathEvaluationEngine which was removed in SP-018-001
    # in favor of SQL-only execution path. Edge case behavior is now tested via SQL translator tests.
    pass


@pytest.mark.skip(reason="FHIRPathEvaluationEngine removed in SP-018-001 - SQL translator only")
def test_type_coercion_for_string_numeric_comparisons() -> None:
    """String numeric values should coerce to numbers during comparison."""
    # NOTE: This test relied on FHIRPathEvaluationEngine which was removed in SP-018-001
    # in favor of SQL-only execution path. Type coercion is now handled by SQL translator.
    pass


@pytest.mark.skip(reason="FHIRPathEvaluationEngine removed in SP-018-001 - SQL translator only")
def test_operator_precedence_in_evaluator() -> None:
    """Multiplication should take precedence over addition."""
    # NOTE: This test relied on FHIRPathEvaluationEngine which was removed in SP-018-001
    # in favor of SQL-only execution path. Operator precedence is now handled by SQL database.
    pass
