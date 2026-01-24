"""Variable-reference regression tests for SP-008-009.

These tests cover $this/$total bindings, scope restoration, and error handling
for unbound variables across both SQL dialects. They focus on translator-level
behaviour because Phase 3 fixes centred on TranslationContext management.
"""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.ast.nodes import FunctionCallNode, IdentifierNode, LiteralNode, OperatorNode
from fhir4ds.fhirpath.sql.context import VariableBinding
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


def _build_where_node(condition: OperatorNode, text: str = "where(...)") -> FunctionCallNode:
    """Construct a FunctionCallNode representing where(condition)."""
    where_node = FunctionCallNode(
        node_type="functionCall",
        text=text,
        function_name="where",
        arguments=[condition],
    )
    where_node.children = [condition]
    return where_node


def _bind_path(translator: ASTToSQLTranslator, *components: str) -> None:
    """Utility to seed the translator context with a JSON path."""
    translator.context.parent_path.clear()
    for component in components:
        translator.context.push_path(component)


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_where_binds_this_and_restores_parent_scope(
    request: pytest.FixtureRequest,
    dialect_fixture: str,
) -> None:
    """$this should resolve to the array alias inside where() and disappear afterward."""
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")

    # Pre-bind an outer variable to ensure scope preservation.
    translator.context.bind_variable("$outer", VariableBinding(expression="outer_alias"))
    _bind_path(translator, "name", "given")

    # Condition: $this = 'Ann'
    left = IdentifierNode(node_type="identifier", text="$this", identifier="$this")
    right = LiteralNode(node_type="literal", text="'Ann'", value="Ann", literal_type="string")
    condition = OperatorNode(
        node_type="operator",
        text="$this = 'Ann'",
        operator="=",
        operator_type="comparison",
    )
    condition.add_child(left)
    condition.add_child(right)

    fragment = translator._translate_where(_build_where_node(condition))

    sql = fragment.expression
    assert "$this" not in sql
    assert "LATERAL" in sql
    assert fragment.source_table.startswith("cte_")
    assert translator.context.get_variable("$this") is None, "where scope should clean temporary binding"

    outer_binding = translator.context.get_variable("$outer")
    assert outer_binding is not None and outer_binding.expression == "outer_alias"


@pytest.mark.parametrize(
    ("dialect_fixture", "expected_snippet"),
    [
        ("duckdb_dialect", "json_array_length"),
        ("postgresql_dialect", "jsonb_array_length"),
    ],
)
def test_total_variable_translates_to_array_length(
    request: pytest.FixtureRequest,
    dialect_fixture: str,
    expected_snippet: str,
) -> None:
    """$total should expand to the dialect-specific JSON array length expression."""
    dialect = request.getfixturevalue(dialect_fixture)
    translator = ASTToSQLTranslator(dialect, "Patient")
    _bind_path(translator, "name", "given")

    left = IdentifierNode(node_type="identifier", text="$total", identifier="$total")
    right = LiteralNode(node_type="literal", text="0", value=0, literal_type="integer")
    condition = OperatorNode(
        node_type="operator",
        text="$total > 0",
        operator=">",
        operator_type="comparison",
    )
    condition.add_child(left)
    condition.add_child(right)

    fragment = translator._translate_where(_build_where_node(condition, text="where($total > 0)"))
    sql = fragment.expression

    assert expected_snippet in sql
    assert "$total" not in sql


def test_variable_scope_helper_allows_shadowing(monkeypatch, duckdb_dialect) -> None:
    """Nested variable scopes should shadow and then restore parent bindings."""
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    translator.context.bind_variable("$x", VariableBinding(expression="outer"))

    with translator._variable_scope({"$x": VariableBinding(expression="inner")}, preserve_parent=True):
        assert translator.context.get_variable("$x").expression == "inner"

    # Outer scope should be restored after exiting context manager
    assert translator.context.get_variable("$x").expression == "outer"


def test_unbound_variable_raises_value_error(duckdb_dialect) -> None:
    """Referencing an undefined FHIRPath variable should raise a ValueError."""
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    node = IdentifierNode(node_type="identifier", text="$missing", identifier="$missing")

    with pytest.raises(ValueError, match="Unbound FHIRPath variable referenced: \\$missing"):
        translator.visit_identifier(node)
