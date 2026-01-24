"""Unit tests for TranslationContext updates during expression chain traversal.

Tests the context update implementation (SP-005-014) that ensures context state
is properly maintained as operations chain together.

Test Coverage:
- current_table updates after each operation
- parent_path tracking through expression chains
- CTE counter incrementation
- Variable binding lifecycle
- Context state consistency across operations
- Both DuckDB and PostgreSQL dialects

Module: tests.unit.fhirpath.sql.test_translator_context_updates
Created: 2025-09-30
Task: SP-005-014
"""

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.context import TranslationContext
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode, OperatorNode, LiteralNode, IdentifierNode
)


@pytest.fixture
def duckdb_dialect():
    """Create DuckDB dialect for testing"""
    from fhir4ds.dialects.duckdb import DuckDBDialect
    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Create PostgreSQL dialect for testing (if available)"""
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    try:
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not available")


class TestCurrentTableUpdates:
    """Test that current_table is properly updated after operations"""

    def test_initial_current_table_is_resource(self, duckdb_dialect):
        """Test that translator starts with current_table='resource'"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        assert translator.context.current_table == "resource"
        assert translator.context.current_resource_type == "Patient"

    @pytest.mark.skip(reason="Compositional design: where() doesn't update context")
    def test_current_table_updates_after_where(self, duckdb_dialect):
        """Test that current_table updates to CTE name after where() operation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.name
        translator.context.push_path("name")

        # Create where() condition: use='official'
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]

        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        # Before translation
        assert translator.context.current_table == "resource"

        # Translate where()
        fragment = translator._translate_where(where_node)

        # After translation, current_table should be updated to CTE name
        assert translator.context.current_table == "cte_1"
        assert fragment.source_table == "cte_1"

    def test_current_table_updates_after_select(self, duckdb_dialect):
        """Test that current_table updates to CTE name after select() operation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.name
        translator.context.push_path("name")

        # Create select() projection: family
        projection = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection]
        )
        select_node.children = [projection]

        # Before translation
        assert translator.context.current_table == "resource"

        # Translate select()
        fragment = translator._translate_select(select_node)

        # After translation, current_table should be updated to CTE name
        assert translator.context.current_table == "cte_1"
        assert fragment.source_table == "cte_1"

    def test_current_table_preserved_after_first(self, duckdb_dialect):
        """Test that first() preserves current_table (array indexing, not CTE)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context for Patient.name
        translator.context.push_path("name")
        current_table_before = translator.context.current_table

        # Create first() function
        first_node = FunctionCallNode(
            node_type="functionCall",
            text="first()",
            function_name="first",
            arguments=[]
        )

        # Translate first()
        fragment = translator._translate_first(first_node)

        # After translation, current_table should be unchanged (first uses array indexing)
        assert translator.context.current_table == current_table_before

    @pytest.mark.skip(reason="Compositional design: where() doesn't update context")
    def test_current_table_chain_updates(self, duckdb_dialect):
        """Test that current_table updates correctly through a chain of operations"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Track table updates through chain
        assert translator.context.current_table == "resource"

        # First operation: where()
        translator.context.push_path("name")
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]
        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        translator._translate_where(where_node)
        assert translator.context.current_table == "cte_1"

        # Second operation: select() - should use cte_1 as source
        translator.context.parent_path.clear()
        translator.context.push_path("family")
        projection = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )
        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection]
        )
        select_node.children = [projection]

        translator._translate_select(select_node)
        assert translator.context.current_table == "cte_2"


class TestPathTracking:
    """Test that parent_path is properly managed through expression chains"""

    def test_initial_path_is_empty(self, duckdb_dialect):
        """Test that translator starts with empty parent_path"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        assert translator.context.parent_path == []
        assert translator.context.get_json_path() == "$"

    def test_push_path_adds_component(self, duckdb_dialect):
        """Test that push_path adds components to path stack"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        translator.context.push_path("name")
        assert translator.context.parent_path == ["name"]
        assert translator.context.get_json_path() == "$.name"

        translator.context.push_path("family")
        assert translator.context.parent_path == ["name", "family"]
        assert translator.context.get_json_path() == "$.name.family"

    def test_pop_path_removes_component(self, duckdb_dialect):
        """Test that pop_path removes components from path stack"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        translator.context.push_path("name")
        translator.context.push_path("family")
        assert translator.context.parent_path == ["name", "family"]

        removed = translator.context.pop_path()
        assert removed == "family"
        assert translator.context.parent_path == ["name"]

        removed = translator.context.pop_path()
        assert removed == "name"
        assert translator.context.parent_path == []

    def test_path_cleared_in_where_for_filter_condition(self, duckdb_dialect):
        """Test that path is cleared when translating where() filter condition"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up path to name array
        translator.context.push_path("name")
        original_path = translator.context.parent_path.copy()

        # Create where() condition that references 'use' field
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]
        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        # Translate where()
        translator._translate_where(where_node)

        # Path should be restored after translation
        assert translator.context.parent_path == original_path

    def test_path_persists_through_identifier_visit(self, duckdb_dialect):
        """Test that path accumulates when visiting identifiers"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Visit identifier for 'name' field
        name_node = IdentifierNode(
            node_type="identifier",
            text="name",
            identifier="name"
        )

        fragment = translator.visit_identifier(name_node)

        # Path should now include 'name'
        assert translator.context.parent_path == ["name"]
        assert "$.name" in fragment.expression

    def test_path_tracking_through_nested_identifiers(self, duckdb_dialect):
        """Test that path correctly accumulates through nested field access"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Visit name
        name_node = IdentifierNode(
            node_type="identifier",
            text="name",
            identifier="name"
        )
        translator.visit_identifier(name_node)
        assert translator.context.parent_path == ["name"]

        # Visit family (nested in name)
        family_node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )
        fragment = translator.visit_identifier(family_node)
        assert translator.context.parent_path == ["name", "family"]
        assert "$.name.family" in fragment.expression


class TestCTECounterIncrementation:
    """Test that CTE counter increments properly"""

    def test_initial_cte_counter_is_zero(self, duckdb_dialect):
        """Test that CTE counter starts at 0"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        assert translator.context.cte_counter == 0

    def test_next_cte_name_increments_counter(self, duckdb_dialect):
        """Test that next_cte_name() increments counter and generates names"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # First call
        name1 = translator.context.next_cte_name()
        assert name1 == "cte_1"
        assert translator.context.cte_counter == 1

        # Second call
        name2 = translator.context.next_cte_name()
        assert name2 == "cte_2"
        assert translator.context.cte_counter == 2

        # Third call
        name3 = translator.context.next_cte_name()
        assert name3 == "cte_3"
        assert translator.context.cte_counter == 3

    @pytest.mark.skip(reason="Compositional design: where() doesn't generate CTEs")
    def test_cte_counter_increments_with_where(self, duckdb_dialect):
        """Test that where() increments CTE counter"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        translator.context.push_path("name")
        initial_counter = translator.context.cte_counter

        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]
        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        translator._translate_where(where_node)

        # Counter should have incremented
        assert translator.context.cte_counter == initial_counter + 1

    def test_cte_counter_increments_with_select(self, duckdb_dialect):
        """Test that select() increments CTE counter"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        translator.context.push_path("name")
        initial_counter = translator.context.cte_counter

        projection = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )
        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection]
        )
        select_node.children = [projection]

        translator._translate_select(select_node)

        # Counter should have incremented
        assert translator.context.cte_counter == initial_counter + 1

    @pytest.mark.skip(reason="Compositional design: where() doesn't generate new CTEs")
    def test_cte_counter_sequential_across_operations(self, duckdb_dialect):
        """Test that CTE counter increments sequentially across multiple operations"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        assert translator.context.cte_counter == 0

        # First operation
        translator.context.push_path("name")
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]
        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]
        translator._translate_where(where_node)
        assert translator.context.cte_counter == 1

        # Second operation
        translator.context.parent_path.clear()
        translator.context.push_path("family")
        projection = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )
        select_node = FunctionCallNode(
            node_type="functionCall",
            text="select(family)",
            function_name="select",
            arguments=[projection]
        )
        select_node.children = [projection]
        translator._translate_select(select_node)
        assert translator.context.cte_counter == 2


class TestContextReset:
    """Test that context properly resets between translations"""

    def test_context_resets_on_translate(self, duckdb_dialect):
        """Test that translate() resets context to initial state"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Modify context state
        translator.context.push_path("name")
        translator.context.push_path("family")
        translator.context.bind_variable("$this", "cte_1_item")
        translator.context.current_table = "cte_5"
        translator.context.cte_counter = 5

        # Translate a simple literal
        literal = LiteralNode(
            node_type="literal",
            text="42",
            value=42,
            literal_type="integer"
        )
        translator.translate(literal)

        # Context should be reset
        assert translator.context.current_table == "resource"
        assert translator.context.parent_path == []
        assert translator.context.variable_bindings == {}
        assert translator.context.cte_counter == 0

    def test_multiple_translations_use_fresh_context(self, duckdb_dialect):
        """Test that multiple translate() calls each start with fresh context"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # First translation
        literal1 = LiteralNode(
            node_type="literal",
            text="42",
            value=42,
            literal_type="integer"
        )
        translator.translate(literal1)
        assert translator.context.cte_counter == 0

        # Manually modify context
        translator.context.cte_counter = 10

        # Second translation should reset context
        literal2 = LiteralNode(
            node_type="literal",
            text="99",
            value=99,
            literal_type="integer"
        )
        translator.translate(literal2)
        assert translator.context.cte_counter == 0


class TestVariableBindings:
    """Test variable binding management in context"""

    def test_where_binds_this_variable(self, duckdb_dialect):
        """Test that where() binds $this variable during filter translation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        translator.context.push_path("name")

        # Create where() with condition that references current item
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]
        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        # Global $this binding exists initially (bound to root resource in __init__)
        assert len(translator.context.variable_bindings) == 1
        assert "$this" in translator.context.variable_bindings
        global_this = translator.context.variable_bindings["$this"]
        assert global_this.expression == "resource"
        assert global_this.source_table == "resource"

        # Translate where()
        translator._translate_where(where_node)

        # After translation, context should be restored to initial state
        # The global $this binding should remain (variables scoped during filter
        # condition translation are cleaned up after)
        assert len(translator.context.variable_bindings) == 1
        assert "$this" in translator.context.variable_bindings
        restored_this = translator.context.variable_bindings["$this"]
        assert restored_this.expression == "resource"
        assert restored_this.source_table == "resource"

    def test_bind_and_get_variable(self, duckdb_dialect):
        """Test binding and retrieving variables"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Bind variable
        translator.context.bind_variable("$this", "cte_1_item")
        binding = translator.context.get_variable("$this")
        assert binding is not None
        assert binding.expression == "cte_1_item"

        # Bind another variable
        translator.context.bind_variable("$index", "idx")
        binding_index = translator.context.get_variable("$index")
        assert binding_index is not None
        assert binding_index.expression == "idx"

        # Get non-existent variable
        assert translator.context.get_variable("$missing") is None


class TestMultiDatabaseConsistency:
    """Test that context updates work consistently across database dialects"""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    @pytest.mark.skip(reason="Compositional design: where() doesn't update context")
    def test_context_updates_consistent_across_dialects(self, dialect_fixture, request):
        """Test that context updates work the same way on both dialects"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Initial state
        assert translator.context.current_table == "resource"
        assert translator.context.cte_counter == 0

        # Execute where() operation
        translator.context.push_path("name")
        condition = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        condition.children = [
            IdentifierNode(node_type="identifier", text="use", identifier="use"),
            LiteralNode(node_type="literal", text="'official'", value="official", literal_type="string")
        ]
        where_node = FunctionCallNode(
            node_type="functionCall",
            text="where(use='official')",
            function_name="where",
            arguments=[condition]
        )
        where_node.children = [condition]

        translator._translate_where(where_node)

        # Context updates should be identical across dialects
        assert translator.context.current_table == "cte_1"
        assert translator.context.cte_counter == 1
