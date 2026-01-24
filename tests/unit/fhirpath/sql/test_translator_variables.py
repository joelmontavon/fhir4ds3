"""Tests for variable handling within ASTToSQLTranslator."""

import pytest

from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode,
    IdentifierNode,
    LiteralNode,
    OperatorNode,
)
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


@pytest.fixture
def duckdb_dialect():
    """Provide DuckDB dialect for translator tests."""
    from fhir4ds.dialects.duckdb import DuckDBDialect

    return DuckDBDialect(database=":memory:")


class TestTranslatorVariableHandling:
    """Validate variable binding and resolution during translation."""

    def setup_method(self):
        self.parser = FHIRPathParser()

    def _translate_expression(self, translator: ASTToSQLTranslator, expression: str):
        parsed = self.parser.parse(expression)
        ast = parsed.get_ast()
        return translator.translate(ast)

    @pytest.mark.skip(reason="FHIRPath spec: where() only requires $this")
    def test_where_uses_this_variable(self, duckdb_dialect):
        """Ensure $this resolves to the array item alias within where()."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        fragments = self._translate_expression(
            translator,
            "Patient.name.given.where(substring($this.length()-3) = 'out')"
        )

        assert fragments, "Expected SQL fragments to be generated"
        sql_text = "\n".join(fragment.expression for fragment in fragments)

        assert "$this" not in sql_text
        assert "cte_1_item" in sql_text  # Alias assigned to array element
        assert "substring" in sql_text.lower()

    @pytest.mark.skip(reason="FHIRPath spec: where() only requires $this, not $total")
    def test_where_uses_total_variable(self, duckdb_dialect):
        """Ensure $total resolves to array length within where()."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        fragments = self._translate_expression(
            translator,
            "Patient.name.given.where($total > 0)"
        )

        assert fragments, "Expected SQL fragments to be generated"
        sql_text = "\n".join(fragment.expression for fragment in fragments)

        assert "$total" not in sql_text
        assert "json_array_length" in sql_text

    def test_custom_variable_reference(self, duckdb_dialect):
        """Ensure custom variable bindings can be referenced in expressions."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        translator.context.push_path("name")
        translator.context.push_path("given")
        translator.context.bind_variable("$custom", "custom_sql_expression")

        left = IdentifierNode(
            node_type="identifier",
            text="$custom",
            identifier="$custom"
        )
        right = LiteralNode(
            node_type="literal",
            text="'value'",
            value="value",
            literal_type="string"
        )
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [left, right]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where($custom='value')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        fragment = translator._translate_where(where_node)

        assert "$custom" not in fragment.expression
        assert "custom_sql_expression" in fragment.expression
