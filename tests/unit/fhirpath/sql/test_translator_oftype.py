"""Unit tests for ASTToSQLTranslator ofType() translation.

These tests exercise both the type operation handler (`_translate_oftype_operation`)
and the function-call bridge (`_translate_oftype_from_function_call`). They validate
SQL generation across DuckDB and PostgreSQL dialects, ensure thin-dialect contracts
are honoured, and cover edge cases such as unknown types, missing arguments, and
dependency propagation so the translator maintains population-scale semantics.
"""

from __future__ import annotations

from typing import List
from unittest.mock import MagicMock, patch

import pytest

from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode,
    IdentifierNode,
    LiteralNode,
    TypeOperationNode,
)
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


@pytest.fixture
def duckdb_dialect():
    """Instantiate DuckDB dialect for testing."""
    from fhir4ds.dialects.duckdb import DuckDBDialect

    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Instantiate PostgreSQL dialect for testing (skips if unavailable)."""
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    import psycopg2  # noqa: F401 - ensure dependency present

    dummy_conn = MagicMock()
    dummy_cursor = MagicMock()
    dummy_conn.cursor.return_value = dummy_cursor
    dummy_cursor.execute.return_value = None
    dummy_cursor.fetchall.return_value = []

    with patch("fhir4ds.dialects.postgresql.psycopg2.connect", return_value=dummy_conn):
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")


def _make_type_operation(child, target_type: str, text: str) -> TypeOperationNode:
    """Helper to create TypeOperationNode wired to a supplied child."""
    node = TypeOperationNode(
        node_type="typeOperation",
        text=text,
        operation="ofType",
        target_type=target_type,
    )
    node.children = [child]
    return node


def _make_function_call(arguments: List, text: str) -> FunctionCallNode:
    """Helper to create FunctionCallNode for ofType()."""
    node = FunctionCallNode(
        node_type="functionCall",
        text=text,
        function_name="ofType",
        arguments=arguments,
    )
    node.children = arguments
    return node


def _assert_duckdb_oftype_structure(expression: str) -> None:
    """Validate DuckDB ofType() aggregation structure."""
    lowered = expression.lower()
    assert "json_group_array" in lowered
    assert "json_each" in lowered
    assert 'elem."type"' in expression


def _assert_postgresql_oftype_structure(expression: str) -> None:
    """Validate PostgreSQL ofType() aggregation structure."""
    lowered = expression.lower()
    assert "jsonb_array_elements" in lowered
    assert "jsonb_agg" in lowered
    assert "jsonb_typeof" in lowered


class TestOfTypeOperationCollections:
    """Collection-focused tests for type operation translation."""

    def test_oftype_filters_string_collection_duckdb(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        # Build context: Observation.component.value.ofType(String)
        component_node = IdentifierNode(node_type="identifier", text="component", identifier="component")
        translator.visit_identifier(component_node)
        value_node = IdentifierNode(node_type="identifier", text="value", identifier="value")
        type_node = _make_type_operation(value_node, "String", "value ofType String")

        fragment = translator._translate_oftype_operation(type_node)

        expr = fragment.expression
        _assert_duckdb_oftype_structure(expr)
        assert "$.component.value" in expr
        assert "VARCHAR" in expr
        assert fragment.is_aggregate is False
        assert fragment.requires_unnest is False
        translator.context.parent_path.clear()

    def test_oftype_filters_string_collection_postgresql(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")
        component_node = IdentifierNode(node_type="identifier", text="component", identifier="component")
        translator.visit_identifier(component_node)
        value_node = IdentifierNode(node_type="identifier", text="value", identifier="value")
        type_node = _make_type_operation(value_node, "String", "value ofType String")

        fragment = translator._translate_oftype_operation(type_node)
        expr = fragment.expression
        _assert_postgresql_oftype_structure(expr)
        lowered = expr.lower()
        assert "select coalesce" in lowered
        assert " = 'string'" in lowered
        assert fragment.is_aggregate is False
        assert fragment.requires_unnest is False
        translator.context.parent_path.clear()

    def test_oftype_filters_integer_collection_duckdb(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        telecom_node = IdentifierNode(node_type="identifier", text="telecom", identifier="telecom")
        translator.visit_identifier(telecom_node)
        value_node = IdentifierNode(node_type="identifier", text="value", identifier="value")
        type_node = _make_type_operation(value_node, "Integer", "value ofType Integer")

        fragment = translator._translate_oftype_operation(type_node)

        expr = fragment.expression
        _assert_duckdb_oftype_structure(expr)
        assert "$.telecom.value" in expr
        for token in ("UBIGINT", "BIGINT", "INTEGER", "SMALLINT"):
            assert token in expr
        translator.context.parent_path.clear()

    def test_oftype_filters_integer_collection_postgresql(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        telecom_node = IdentifierNode(node_type="identifier", text="telecom", identifier="telecom")
        translator.visit_identifier(telecom_node)
        value_node = IdentifierNode(node_type="identifier", text="value", identifier="value")
        type_node = _make_type_operation(value_node, "Integer", "value ofType Integer")

        fragment = translator._translate_oftype_operation(type_node)

        expr = fragment.expression
        _assert_postgresql_oftype_structure(expr)
        lowered = expr.lower()
        assert " = 'number'" in lowered
        assert "~ '^-?[0-9]+$'" in expr
        translator.context.parent_path.clear()


class TestOfTypeOperationLiterals:
    """Literal handling for ofType() type operations."""

    def test_oftype_single_literal_string(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        literal_node = LiteralNode(node_type="literal", text="'hello'", value="hello", literal_type="string")
        type_node = _make_type_operation(literal_node, "String", "'hello' ofType String")

        fragment = translator._translate_oftype_operation(type_node)

        expr = fragment.expression
        _assert_duckdb_oftype_structure(expr)
        assert "'hello'" in expr
        assert "VARCHAR" in expr

    def test_oftype_single_literal_integer(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        literal_node = LiteralNode(node_type="literal", text="5", value=5, literal_type="integer")
        type_node = _make_type_operation(literal_node, "Integer", "5 ofType Integer")

        fragment = translator._translate_oftype_operation(type_node)

        expr = fragment.expression
        _assert_duckdb_oftype_structure(expr)
        assert "5" in expr
        assert "INTEGER" in expr

    def test_oftype_single_literal_boolean(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        literal_node = LiteralNode(node_type="literal", text="true", value=True, literal_type="boolean")
        type_node = _make_type_operation(literal_node, "Boolean", "true ofType Boolean")

        fragment = translator._translate_oftype_operation(type_node)

        expr = fragment.expression
        _assert_duckdb_oftype_structure(expr)
        assert "TRUE" in expr
        assert "BOOLEAN" in expr


class TestOfTypeOperationEdgeCases:
    """Edge-case coverage for ofType() type operations."""

    def test_oftype_unknown_type_returns_empty_duckdb(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        value_node = IdentifierNode(node_type="identifier", text="value", identifier="value")
        # Quantity is a valid type that maps to valueQuantity via polymorphic resolution
        type_node = _make_type_operation(value_node, "Quantity", "value ofType Quantity")

        fragment = translator._translate_oftype_operation(type_node)

        expr = fragment.expression
        # With polymorphic resolution, value.ofType(Quantity) → $.valueQuantity
        assert "$.valueQuantity" in expr or "$valueQuantity" in expr
        assert "json_extract" in expr or "jsonb_extract" in expr

    def test_oftype_unknown_type_returns_empty_postgresql(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")
        value_node = IdentifierNode(node_type="identifier", text="value", identifier="value")
        # Quantity is a valid type that maps to valueQuantity via polymorphic resolution
        type_node = _make_type_operation(value_node, "Quantity", "value ofType Quantity")

        fragment = translator._translate_oftype_operation(type_node)

        expr = fragment.expression
        # With polymorphic resolution, value.ofType(Quantity) → $.valueQuantity
        assert "valueQuantity" in expr
        assert "jsonb_extract" in expr or "json_extract" in expr

    def test_oftype_operation_without_children_raises(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        node = TypeOperationNode(
            node_type="typeOperation",
            text="ofType Integer",
            operation="ofType",
            target_type="Integer",
        )

        with pytest.raises(ValueError, match="requires an expression to filter"):
            translator._translate_oftype_operation(node)

    def test_oftype_preserves_child_dependencies(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        child = MagicMock(name="child_node")
        fragment = SQLFragment(
            expression="json_extract(resource, '$.address')",
            source_table="resource",
            requires_unnest=False,
            is_aggregate=False,
            dependencies=["cte_addresses"],
        )

        with patch.object(translator, "visit", return_value=fragment) as visit_mock:
            node = _make_type_operation(child, "String", "address ofType String")
            result = translator._translate_oftype_operation(node)

        visit_mock.assert_called_once_with(child)
        assert result.dependencies == ["cte_addresses"]
        assert result.source_table == "resource"

    def test_oftype_respects_current_table_override(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.current_table = "cte_filtered"
        name_node = IdentifierNode(node_type="identifier", text="name", identifier="name")
        type_node = _make_type_operation(name_node, "String", "name ofType String")

        fragment = translator._translate_oftype_operation(type_node)

        assert "cte_filtered" in fragment.expression
        assert fragment.source_table == "cte_filtered"

    def test_oftype_fragment_flags_false(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        name_node = IdentifierNode(node_type="identifier", text="name", identifier="name")
        type_node = _make_type_operation(name_node, "String", "name ofType String")

        fragment = translator._translate_oftype_operation(type_node)

        assert fragment.is_aggregate is False
        assert fragment.requires_unnest is False


class TestOfTypeFunctionCall:
    """Tests for _translate_oftype_from_function_call bridge."""

    def test_oftype_function_call_filters_collection_duckdb(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        type_arg = IdentifierNode(node_type="identifier", text="String", identifier="String")
        node = _make_function_call([type_arg], "Observation.value.ofType(String)")

        fragment = translator._translate_oftype_from_function_call(node)

        expr = fragment.expression
        _assert_duckdb_oftype_structure(expr)
        assert "$.value" in expr or ".value" in expr
        assert "VARCHAR" in expr

    def test_oftype_function_call_filters_collection_postgresql(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")
        type_arg = IdentifierNode(node_type="identifier", text="Integer", identifier="Integer")
        node = _make_function_call([type_arg], "Observation.component.value.ofType(Integer)")

        fragment = translator._translate_oftype_from_function_call(node)

        expr = fragment.expression
        _assert_postgresql_oftype_structure(expr)
        lowered = expr.lower()
        assert "component_item" in lowered or "component" in lowered
        assert " = 'number'" in lowered
        assert "~ '^-?[0-9]+$'" in expr

    def test_oftype_function_call_without_arguments_raises(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        node = _make_function_call([], "Patient.name.ofType()")

        with pytest.raises(ValueError, match="requires exactly 1 argument"):
            translator._translate_oftype_from_function_call(node)

    def test_oftype_function_call_invalid_argument_type_raises(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        invalid_arg = TypeOperationNode(node_type="typeOperation", text="count()", operation="count", target_type="")
        node = _make_function_call([invalid_arg], "Patient.name.ofType(count())")

        with pytest.raises(ValueError, match="Unexpected type argument node"):
            translator._translate_oftype_from_function_call(node)

    def test_oftype_function_call_unknown_type_returns_empty(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Bundle")
        type_arg = IdentifierNode(node_type="identifier", text="Patient", identifier="Patient")
        node = _make_function_call([type_arg], "Bundle.entry.resource.ofType(Patient)")

        fragment = translator._translate_oftype_from_function_call(node)

        assert fragment.expression == "[]"

    def test_oftype_function_call_fragment_flags(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        type_arg = IdentifierNode(node_type="identifier", text="String", identifier="String")
        node = _make_function_call([type_arg], "Patient.name.ofType(String)")

        fragment = translator._translate_oftype_from_function_call(node)

        assert fragment.is_aggregate is False
        assert fragment.requires_unnest is False
        assert fragment.source_table == translator.context.current_table

    def test_oftype_function_call_reuses_context_when_no_path(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.parent_path.append("name")
        type_arg = IdentifierNode(node_type="identifier", text="String", identifier="String")
        node = _make_function_call([type_arg], "ofType(String)")

        fragment = translator._translate_oftype_from_function_call(node)

        assert "$.name" in fragment.expression
        translator.context.parent_path.clear()

    def test_oftype_function_call_preserves_current_table_override(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.current_table = "cte_names"
        type_arg = IdentifierNode(node_type="identifier", text="String", identifier="String")
        node = _make_function_call([type_arg], "Patient.name.ofType(String)")

        fragment = translator._translate_oftype_from_function_call(node)

        assert "cte_names" in fragment.expression
        assert fragment.source_table == "cte_names"

    def test_oftype_function_call_calls_parser_once(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        type_arg = IdentifierNode(node_type="identifier", text="String", identifier="String")
        node = _make_function_call([type_arg], "Patient.telecom.value.ofType(String)")

        with patch("fhir4ds.fhirpath.parser.FHIRPathParser") as parser_cls, patch(
            "fhir4ds.fhirpath.sql.ast_adapter.convert_enhanced_ast_to_fhirpath_ast"
        ) as converter:
            parser_instance = parser_cls.return_value
            parser_instance.parse.return_value.get_ast.return_value = IdentifierNode(
                node_type="identifier",
                text="telecom",
                identifier="telecom",
            )
            converter.return_value = IdentifierNode(
                node_type="identifier",
                text="telecom",
                identifier="telecom",
            )
            fragment = translator._translate_oftype_from_function_call(node)

        parser_cls.assert_called_once()
        parser_instance.parse.assert_called_once_with("Patient.telecom.value")
        converter.assert_called_once()
        assert isinstance(fragment, SQLFragment)
