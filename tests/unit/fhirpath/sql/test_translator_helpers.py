"""Additional translator helper coverage for SP-008-011."""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode,
    LiteralNode,
    OperatorNode,
    TypeOperationNode,
)


@pytest.fixture
def translator(duckdb_dialect):
    return ASTToSQLTranslator(duckdb_dialect, "Patient")


def test_traverse_expression_chain_accumulates(translator):
    """Ensure the expression chain traversal visits significant operations."""
    parser = FHIRPathParser()
    enhanced = parser.parse("Patient.name.where(use='official').first()").get_ast()
    ast = enhanced

    translator.fragments.clear()
    translator._traverse_expression_chain(ast)

    # At least one fragment should be accumulated for the chained operations.
    assert len(translator.fragments) >= 1


def test_resolve_function_target_uses_context_path(translator):
    """When no explicit path exists, the current context path should be used."""
    translator.context.push_path("name")
    node = FunctionCallNode(
        node_type="functionCall",
        text="where($this = 'official')",
        function_name="where",
        arguments=[],
    )

    target_expr, _, literal_value, snapshot, _, _ = translator._resolve_function_target(node)
    assert "$.name" in target_expr
    assert literal_value is None
    translator._restore_context(snapshot)


def test_resolve_function_target_literal_branch(translator):
    """Literal targets should return SQL literal expressions."""
    node = FunctionCallNode(
        node_type="functionCall",
        text="'hello'.toString()",
        function_name="toString",
        arguments=[],
    )

    target_expr, _, literal_value, snapshot, _, _ = translator._resolve_function_target(node)
    assert literal_value == "hello"
    assert target_expr == "'hello'"
    translator._restore_context(snapshot)


def test_should_accumulate_as_separate_fragment(translator):
    """Helper should treat function/type operations as significant."""
    func_node = FunctionCallNode(node_type="functionCall", text="where(...)", function_name="where")
    type_node = TypeOperationNode(node_type="typeOperation", text="is Integer", operation="is")
    literal_node = LiteralNode(node_type="literal", text="'value'", value="value")

    assert translator._should_accumulate_as_separate_fragment(func_node) is True
    assert translator._should_accumulate_as_separate_fragment(type_node) is True
    assert translator._should_accumulate_as_separate_fragment(literal_node) is False


def test_to_sql_literal_unsupported_type(translator):
    """Unsupported literal types should raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported literal type"):
        translator._to_sql_literal({"complex": "object"}, "complex")


def test_visit_function_call_unknown(translator):
    """Unknown functions should surface a ValueError."""
    node = FunctionCallNode(node_type="functionCall", text="foo()", function_name="foo", arguments=[])
    with pytest.raises(ValueError, match="Unknown or unsupported function"):
        translator.visit_function_call(node)


def test_visit_operator_unary_missing_operand(translator):
    """Unary operators with missing operand should raise."""
    node = OperatorNode(node_type="operator", text="not", operator="not", operator_type="unary")
    with pytest.raises(ValueError, match="requires exactly 1 operand"):
        translator.visit_operator(node)


@pytest.mark.parametrize("operator", ["<", "<=", ">", ">="])
def test_build_temporal_conditions_handles_all_operators(translator, operator):
    """Temporal condition builder should output clauses for each comparison operator."""
    parser = FHIRPathParser()
    ast = parser.parse("@2018-03 < @2018-03-01").get_ast()
    # SP-023-006: EnhancedASTNode.accept() handles visitor dispatch directly

    # Get the operator node's children for temporal info extraction
    # The AST structure has the comparison operator at root with left/right children
    left_info = translator._extract_temporal_info(ast.children[0])
    right_info = translator._extract_temporal_info(ast.children[1])
    conditions = translator._build_temporal_conditions(left_info, right_info, operator)

    assert conditions is not None
    true_clause, false_clause = conditions
    assert "TIMESTAMP" in true_clause
    assert "TIMESTAMP" in false_clause


def test_translate_is_from_function_call_argument_validation(translator):
    """is() helper should validate argument count."""
    node = FunctionCallNode(node_type="functionCall", text="value.is()", function_name="is", arguments=[])
    with pytest.raises(ValueError, match="requires exactly 1 argument"):
        translator._translate_is_from_function_call(node)


def test_translate_as_from_function_call_argument_validation(translator):
    """as() helper should validate argument count."""
    node = FunctionCallNode(node_type="functionCall", text="value.as()", function_name="as", arguments=[])
    with pytest.raises(ValueError, match="requires exactly 1 argument"):
        translator._translate_as_from_function_call(node)


def test_translate_oftype_from_function_call_argument_validation(translator):
    """ofType() helper should validate argument count."""
    node = FunctionCallNode(node_type="functionCall", text="value.ofType()", function_name="ofType", arguments=[])
    with pytest.raises(ValueError, match="requires exactly 1 argument"):
        translator._translate_oftype_from_function_call(node)


def test_translate_math_function_uses_context_path(translator):
    """Math helper should fallback to current path when no arguments supplied."""
    translator.context.push_path("valueQuantity")
    node = FunctionCallNode(node_type="functionCall", text="abs()", function_name="abs", arguments=[])
    fragment = translator._translate_math_function(node)
    assert "json_extract" in fragment.expression
    translator.context.parent_path.clear()


def test_translate_string_function_split_argument_validation(translator):
    """split() helper should enforce argument count."""
    node = FunctionCallNode(node_type="functionCall", text="split()", function_name="split", arguments=[])
    with pytest.raises(ValueError, match="split\\(\\) requires exactly 1 argument"):
        translator._translate_string_function(node)


def test_translate_string_function_unknown(translator):
    """Unknown string function names should raise."""
    arg = LiteralNode(node_type="literal", text="'test'", value="test", literal_type="string")
    node = FunctionCallNode(
        node_type="functionCall",
        text="mystery()",
        function_name="mystery",
        arguments=[arg],
    )
    with pytest.raises(ValueError, match="Unknown string function"):
        translator._translate_string_function(node)
