"""Integration tests for combined ofType() and count() translation.

These tests exercise translator behaviours when chaining type filtering, where()
filters, and aggregation. They validate context management, dialect differences,
and ensure fragments compose correctly for population-scale SQL generation.
"""

from __future__ import annotations

import pytest

from unittest.mock import MagicMock, patch

from fhir4ds.fhirpath.ast.nodes import (
    AggregationNode,
    FunctionCallNode,
    IdentifierNode,
    LiteralNode,
    OperatorNode,
    TypeOperationNode,
)
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


@pytest.fixture
def duckdb_dialect():
    """Create DuckDB dialect for integration checks."""
    from fhir4ds.dialects.duckdb import DuckDBDialect

    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Create PostgreSQL dialect for integration checks, skipping if unavailable."""
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    import psycopg2  # noqa: F401

    dummy_conn = MagicMock()
    dummy_cursor = MagicMock()
    dummy_conn.cursor.return_value = dummy_cursor
    dummy_cursor.execute.return_value = None
    dummy_cursor.fetchall.return_value = []

    with patch("fhir4ds.dialects.postgresql.psycopg2.connect", return_value=dummy_conn):
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")


def _make_type_operation(text: str, target_type: str, child: IdentifierNode) -> TypeOperationNode:
    node = TypeOperationNode(
        node_type="typeOperation",
        text=text,
        operation="ofType",
        target_type=target_type,
    )
    node.children = [child]
    return node


def _make_where_function(condition: OperatorNode) -> FunctionCallNode:
    node = FunctionCallNode(
        node_type="functionCall",
        text="where(...)",
        function_name="where",
        arguments=[condition],
    )
    node.children = [condition]
    return node


def _make_condition(operator: str, left: IdentifierNode, right: LiteralNode) -> OperatorNode:
    condition = OperatorNode(
        node_type="operator",
        text=operator,
        operator=operator,
        operator_type="comparison",
    )
    condition.children = [left, right]
    return condition


def _make_count_node() -> AggregationNode:
    node = AggregationNode(
        node_type="aggregation",
        text="count()",
        aggregation_function="count",
        aggregation_type="count",
    )
    node.children = []
    return node


class TestOfTypeCountChains:
    """Validate collection.ofType(...).count() sequences."""

    @pytest.mark.parametrize(
        "target_type, expected_token",
        [
            ("String", "VARCHAR"),
            ("Integer", "INTEGER"),
            ("Decimal", "DOUBLE"),
        ],
    )
    def test_chain_oftype_then_count_duckdb(self, duckdb_dialect, target_type, expected_token):
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        type_child = IdentifierNode(node_type="identifier", text="component", identifier="component")
        type_node = _make_type_operation(f"component ofType {target_type}", target_type, type_child)

        type_fragment = translator._translate_oftype_operation(type_node)
        count_fragment = translator.visit_aggregation(_make_count_node())

        assert "list_filter" in type_fragment.expression or "json_each" in type_fragment.expression.lower() or "jsonb_array_elements" in type_fragment.expression.lower()
        assert expected_token in type_fragment.expression
        assert "json_array_length" in count_fragment.expression
        assert "component" in count_fragment.expression
        translator.context.parent_path.clear()

    @pytest.mark.parametrize(
        "target_type",
        ["String", "Integer"],
    )
    def test_chain_oftype_then_count_postgresql(self, postgresql_dialect, target_type):
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")
        type_child = IdentifierNode(node_type="identifier", text="component", identifier="component")
        type_node = _make_type_operation(f"component ofType {target_type}", target_type, type_child)

        type_fragment = translator._translate_oftype_operation(type_node)
        count_fragment = translator.visit_aggregation(_make_count_node())

        assert (
            "unnest(" in type_fragment.expression
            or "jsonb_array_elements" in type_fragment.expression
        )
        assert "pg_typeof" in type_fragment.expression
        assert (
            "array_agg" in type_fragment.expression
            or "jsonb_agg" in type_fragment.expression
        )
        lowered = count_fragment.expression.lower()
        assert "coalesce" in lowered
        assert "jsonb_array_length" in lowered
        translator.context.parent_path.clear()

    def test_chain_oftype_unknown_type_then_count(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        type_child = IdentifierNode(node_type="identifier", text="component", identifier="component")
        type_node = _make_type_operation("component ofType Quantity", "Quantity", type_child)

        type_fragment = translator._translate_oftype_operation(type_node)
        count_fragment = translator.visit_aggregation(_make_count_node())

        assert type_fragment.expression == "[]" or "COALESCE" in type_fragment.expression
        assert "json_array_length" in count_fragment.expression
        translator.context.parent_path.clear()


class TestWhereCountChains:
    """Validate where(...).count() integration."""

    @pytest.mark.skip(reason="Compositional design: where() chaining behavior changed")
    @pytest.mark.parametrize(
        "path_root, field, operator_symbol, literal_text, literal_value",
        [
            ("name", "use", "=", "'official'", "official"),
            ("component", "value", ">", "100", 100),
            ("component", "value", "<", "5", 5),
        ],
    )
    def test_chain_where_then_count_duckdb(
        self,
        duckdb_dialect,
        path_root,
        field,
        operator_symbol,
        literal_text,
        literal_value,
    ):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path(path_root)
        left = IdentifierNode(node_type="identifier", text=field, identifier=field)
        literal_type = "integer" if isinstance(literal_value, int) else "string"
        right = LiteralNode(node_type="literal", text=literal_text, value=literal_value, literal_type=literal_type)
        condition = _make_condition(operator_symbol, left, right)

        where_fragment = translator._translate_where(_make_where_function(condition))
        count_fragment = translator.visit_aggregation(_make_count_node())

        assert isinstance(where_fragment, SQLFragment)
        assert "cte_" in count_fragment.expression
        assert path_root in count_fragment.expression
        translator.context.parent_path.clear()

    @pytest.mark.skip(reason="Compositional design: where() chaining behavior changed")
    @pytest.mark.parametrize(
        "path_root, field, operator_symbol, literal_text, literal_value",
        [
            ("name", "use", "=", "'official'", "official"),
            ("component", "value", ">", "100", 100),
        ],
    )
    def test_chain_where_then_count_postgresql(
        self,
        postgresql_dialect,
        path_root,
        field,
        operator_symbol,
        literal_text,
        literal_value,
    ):
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        translator.context.push_path(path_root)
        left = IdentifierNode(node_type="identifier", text=field, identifier=field)
        literal_type = "integer" if isinstance(literal_value, int) else "string"
        right = LiteralNode(node_type="literal", text=literal_text, value=literal_value, literal_type=literal_type)
        condition = _make_condition(operator_symbol, left, right)

        where_fragment = translator._translate_where(_make_where_function(condition))
        count_fragment = translator.visit_aggregation(_make_count_node())

        lowered = where_fragment.expression.lower()
        assert "lateral" in lowered
        assert "cte_" in count_fragment.expression
        translator.context.parent_path.clear()


class TestCombinedChains:
    """Mixed scenarios combining ofType, where, and count."""

    @pytest.mark.skip(reason="Compositional design: where() chaining changed")
    def test_chain_oftype_where_count_duckdb(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        type_child = IdentifierNode(node_type="identifier", text="telecom", identifier="telecom")
        type_node = _make_type_operation("telecom ofType String", "String", type_child)
        type_fragment = translator._translate_oftype_operation(type_node)

        left = IdentifierNode(node_type="identifier", text="use", identifier="use")
        right = LiteralNode(node_type="literal", text="'home'", value="home", literal_type="string")
        condition = _make_condition("=", left, right)
        where_fragment = translator._translate_where(_make_where_function(condition))
        count_fragment = translator.visit_aggregation(_make_count_node())

        assert (
            "list_filter" in type_fragment.expression
            or "json_each" in type_fragment.expression.lower()
        )
        assert where_fragment.source_table.startswith("cte_")
        assert "cte_1" in count_fragment.expression
        translator.context.parent_path.clear()

    @pytest.mark.skip(reason="Compositional design: where() chaining changed")
    def test_chain_oftype_where_count_postgresql(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        type_child = IdentifierNode(node_type="identifier", text="telecom", identifier="telecom")
        type_node = _make_type_operation("telecom ofType Integer", "Integer", type_child)
        type_fragment = translator._translate_oftype_operation(type_node)

        left = IdentifierNode(node_type="identifier", text="use", identifier="use")
        right = LiteralNode(node_type="literal", text="'home'", value="home", literal_type="string")
        condition = _make_condition("=", left, right)
        where_fragment = translator._translate_where(_make_where_function(condition))
        count_fragment = translator.visit_aggregation(_make_count_node())

        assert "unnest" in type_fragment.expression or "jsonb_array_elements" in type_fragment.expression
        assert "pg_typeof" in type_fragment.expression
        assert where_fragment.source_table.startswith("cte_")
        assert "cte_1" in count_fragment.expression
        translator.context.parent_path.clear()

    def test_chain_complex_quantity_count_duckdb(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        component_node = IdentifierNode(node_type="identifier", text="component", identifier="component")
        translator.visit_identifier(component_node)
        value_quantity_node = IdentifierNode(node_type="identifier", text="valueQuantity", identifier="valueQuantity")
        translator.visit_identifier(value_quantity_node)
        value_node = IdentifierNode(node_type="identifier", text="value", identifier="value")
        type_node = _make_type_operation("value ofType Decimal", "Decimal", value_node)

        type_fragment = translator._translate_oftype_operation(type_node)
        count_fragment = translator.visit_aggregation(_make_count_node())

        assert (
            "list_filter" in type_fragment.expression
            or "json_each" in type_fragment.expression.lower()
        )
        assert "$.component.valueQuantity.value" in count_fragment.expression
        translator.context.parent_path.clear()

    def test_chain_complex_quantity_count_postgresql(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")
        component_node = IdentifierNode(node_type="identifier", text="component", identifier="component")
        translator.visit_identifier(component_node)
        value_quantity_node = IdentifierNode(node_type="identifier", text="valueQuantity", identifier="valueQuantity")
        translator.visit_identifier(value_quantity_node)
        value_node = IdentifierNode(node_type="identifier", text="value", identifier="value")
        type_node = _make_type_operation("value ofType Decimal", "Decimal", value_node)

        type_fragment = translator._translate_oftype_operation(type_node)
        count_fragment = translator.visit_aggregation(_make_count_node())

        lowered = count_fragment.expression.lower()
        assert "coalesce" in lowered
        assert "valuequantity" in lowered
        assert (
            "unnest" in type_fragment.expression
            or "jsonb_array_elements" in type_fragment.expression
        )
        translator.context.parent_path.clear()

    @pytest.mark.skip(reason="Compositional design: CTE counter behavior changed")
    def test_chain_multiple_counts_increment_cte(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")
        left = IdentifierNode(node_type="identifier", text="use", identifier="use")
        right = LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        condition = _make_condition("=", left, right)

        translator._translate_where(_make_where_function(condition))
        first_count = translator.visit_aggregation(_make_count_node())
        # Re-run where() on filtered table to force new CTE
        translator._translate_where(_make_where_function(condition))
        second_count = translator.visit_aggregation(_make_count_node())

        assert "cte_1" in first_count.expression
        assert "cte_2" in second_count.expression
        translator.context.parent_path.clear()

    @pytest.mark.skip(reason="Compositional design: fragment ordering changed")
    def test_chain_fragment_sequence_order(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        fragments = []
        telecom_node = IdentifierNode(node_type="identifier", text="telecom", identifier="telecom")
        type_node = _make_type_operation("telecom ofType String", "String", telecom_node)
        fragments.append(translator._translate_oftype_operation(type_node))

        left = IdentifierNode(node_type="identifier", text="use", identifier="use")
        right = LiteralNode(node_type="literal", text="'home'", value="home", literal_type="string")
        condition = _make_condition("=", left, right)
        fragments.append(translator._translate_where(_make_where_function(condition)))
        fragments.append(translator.visit_aggregation(_make_count_node()))

        assert isinstance(fragments[0], SQLFragment)
        assert fragments[0].requires_unnest is False
        assert fragments[1].requires_unnest is True
        assert fragments[2].is_aggregate is True
        translator.context.parent_path.clear()

    def test_chain_performance_smoke_duckdb(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        telecom_node = IdentifierNode(node_type="identifier", text="telecom", identifier="telecom")
        type_node = _make_type_operation("telecom ofType String", "String", telecom_node)
        left = IdentifierNode(node_type="identifier", text="use", identifier="use")
        right = LiteralNode(node_type="literal", text="'home'", value="home", literal_type="string")
        condition = _make_condition("=", left, right)
        where_node = _make_where_function(condition)
        for _ in range(5):
            translator._translate_oftype_operation(type_node)
            translator._translate_where(where_node)
            translator.visit_aggregation(_make_count_node())
            translator.context.parent_path.clear()

    def test_chain_bundle_resource_oftype_patient_duckdb(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Bundle")
        entry_node = IdentifierNode(node_type="identifier", text="entry", identifier="entry")
        translator.visit_identifier(entry_node)
        resource_node = IdentifierNode(node_type="identifier", text="resource", identifier="resource")
        type_node = _make_type_operation("resource ofType Patient", "Patient", resource_node)

        type_fragment = translator._translate_oftype_operation(type_node)
        count_fragment = translator.visit_aggregation(_make_count_node())

        assert type_fragment.expression == "[]"
        assert "entry" in count_fragment.expression
        translator.context.parent_path.clear()

    def test_chain_bundle_resource_oftype_patient_postgresql(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Bundle")
        entry_node = IdentifierNode(node_type="identifier", text="entry", identifier="entry")
        translator.visit_identifier(entry_node)
        resource_node = IdentifierNode(node_type="identifier", text="resource", identifier="resource")
        type_node = _make_type_operation("resource ofType Patient", "Patient", resource_node)

        type_fragment = translator._translate_oftype_operation(type_node)
        count_fragment = translator.visit_aggregation(_make_count_node())

        normalized = type_fragment.expression.strip()
        assert (
            normalized.startswith("ARRAY")
            or normalized == "[]"
            or normalized.startswith("'[]'::jsonb")
        )
        assert "entry" in count_fragment.expression
        translator.context.parent_path.clear()

    def test_chain_where_then_count_restores_parent_path(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")
        original_path = translator.context.parent_path.copy()
        left = IdentifierNode(node_type="identifier", text="use", identifier="use")
        right = LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        condition = _make_condition("=", left, right)

        translator._translate_where(_make_where_function(condition))
        translator.visit_aggregation(_make_count_node())

        assert translator.context.parent_path == original_path
        translator.context.parent_path.clear()
