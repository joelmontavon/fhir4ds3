"""Unit tests for TranslationContext data structure.

This test module provides comprehensive coverage of the TranslationContext dataclass,
including instantiation, path management, CTE naming, variable bindings, and state
management.

Test Coverage:
- TranslationContext instantiation with default and custom values
- CTE name generation and uniqueness
- Path stack management (push, pop, get_json_path)
- Variable binding and retrieval
- Context reset functionality
- Edge cases (empty stacks, deep nesting, etc.)

Module: tests.unit.fhirpath.sql.test_context
Related: fhir4ds.fhirpath.sql.context
PEP: PEP-003 - FHIRPath AST-to-SQL Translator
Created: 2025-09-29
"""

import pytest
from fhir4ds.fhirpath.sql.context import TranslationContext, VariableBinding


class TestTranslationContextInstantiation:
    """Test TranslationContext instantiation and initialization."""

    def test_default_instantiation(self):
        """Test TranslationContext with all default values."""
        context = TranslationContext()

        assert context.current_table == "resource"
        assert context.current_resource_type == "Patient"
        assert context.parent_path == []
        assert context.variable_bindings == {}
        assert context.cte_counter == 0

    def test_custom_resource_type(self):
        """Test TranslationContext with custom resource type."""
        context = TranslationContext(current_resource_type="Observation")

        assert context.current_resource_type == "Observation"
        assert context.current_table == "resource"

    def test_custom_table(self):
        """Test TranslationContext with custom current table."""
        context = TranslationContext(current_table="patient_resources")

        assert context.current_table == "patient_resources"
        assert context.current_resource_type == "Patient"

    def test_full_custom_instantiation(self):
        """Test TranslationContext with all custom values."""
        context = TranslationContext(
            current_table="cte_1",
            current_resource_type="Condition",
            parent_path=["code", "coding"],
            variable_bindings={"$this": VariableBinding(expression="item")},
            cte_counter=5
        )

        assert context.current_table == "cte_1"
        assert context.current_resource_type == "Condition"
        assert context.parent_path == ["code", "coding"]
        binding = context.get_variable("$this")
        assert binding is not None
        assert binding.expression == "item"
        assert context.cte_counter == 5


class TestCTENameGeneration:
    """Test CTE name generation functionality."""

    def test_first_cte_name(self):
        """Test generating the first CTE name."""
        context = TranslationContext()
        name = context.next_cte_name()

        assert name == "cte_1"
        assert context.cte_counter == 1

    def test_sequential_cte_names(self):
        """Test generating multiple sequential CTE names."""
        context = TranslationContext()

        name1 = context.next_cte_name()
        name2 = context.next_cte_name()
        name3 = context.next_cte_name()

        assert name1 == "cte_1"
        assert name2 == "cte_2"
        assert name3 == "cte_3"
        assert context.cte_counter == 3

    def test_cte_name_uniqueness(self):
        """Test that CTE names are unique within a context."""
        context = TranslationContext()
        names = [context.next_cte_name() for _ in range(100)]

        # All names should be unique
        assert len(names) == len(set(names))

    def test_cte_name_format(self):
        """Test CTE name format is consistent."""
        context = TranslationContext()

        for i in range(1, 11):
            name = context.next_cte_name()
            assert name == f"cte_{i}"
            assert name.startswith("cte_")

    def test_cte_counter_initialized(self):
        """Test CTE counter can be initialized to non-zero value."""
        context = TranslationContext(cte_counter=10)

        name = context.next_cte_name()
        assert name == "cte_11"


class TestPathManagement:
    """Test path stack management functionality."""

    def test_push_single_path(self):
        """Test pushing a single path component."""
        context = TranslationContext()
        context.push_path("name")

        assert context.parent_path == ["name"]

    def test_push_multiple_paths(self):
        """Test pushing multiple path components."""
        context = TranslationContext()
        context.push_path("name")
        context.push_path("family")

        assert context.parent_path == ["name", "family"]

    def test_push_deep_path(self):
        """Test pushing many path components (deep nesting)."""
        context = TranslationContext()
        components = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]

        for component in components:
            context.push_path(component)

        assert context.parent_path == components

    def test_pop_single_path(self):
        """Test popping a single path component."""
        context = TranslationContext()
        context.push_path("name")

        popped = context.pop_path()

        assert popped == "name"
        assert context.parent_path == []

    def test_pop_multiple_paths(self):
        """Test popping multiple path components."""
        context = TranslationContext()
        context.push_path("name")
        context.push_path("family")

        popped1 = context.pop_path()
        popped2 = context.pop_path()

        assert popped1 == "family"
        assert popped2 == "name"
        assert context.parent_path == []

    def test_pop_empty_stack_returns_none(self):
        """Test popping from empty stack returns None."""
        context = TranslationContext()

        popped = context.pop_path()

        assert popped is None
        assert context.parent_path == []

    def test_push_pop_sequence(self):
        """Test sequence of push and pop operations."""
        context = TranslationContext()

        context.push_path("a")
        context.push_path("b")
        assert context.parent_path == ["a", "b"]

        context.pop_path()
        assert context.parent_path == ["a"]

        context.push_path("c")
        assert context.parent_path == ["a", "c"]

        context.pop_path()
        context.pop_path()
        assert context.parent_path == []


class TestJSONPathGeneration:
    """Test JSON path generation from path stack."""

    def test_empty_path_returns_root(self):
        """Test get_json_path with empty stack returns '$'."""
        context = TranslationContext()

        json_path = context.get_json_path()

        assert json_path == "$"

    def test_single_component_path(self):
        """Test get_json_path with single component."""
        context = TranslationContext()
        context.push_path("name")

        json_path = context.get_json_path()

        assert json_path == "$.name"

    def test_multiple_component_path(self):
        """Test get_json_path with multiple components."""
        context = TranslationContext()
        context.push_path("name")
        context.push_path("family")

        json_path = context.get_json_path()

        assert json_path == "$.name.family"

    def test_deep_nested_path(self):
        """Test get_json_path with deeply nested components."""
        context = TranslationContext()
        components = ["patient", "name", "given", "first"]

        for component in components:
            context.push_path(component)

        json_path = context.get_json_path()

        assert json_path == "$.patient.name.given.first"

    def test_json_path_after_pop(self):
        """Test get_json_path after popping components."""
        context = TranslationContext()
        context.push_path("name")
        context.push_path("family")

        assert context.get_json_path() == "$.name.family"

        context.pop_path()
        assert context.get_json_path() == "$.name"

        context.pop_path()
        assert context.get_json_path() == "$"

    def test_json_path_with_numeric_components(self):
        """Test get_json_path with numeric path components."""
        context = TranslationContext()
        context.push_path("name")
        context.push_path("0")
        context.push_path("family")

        json_path = context.get_json_path()

        assert json_path == "$.name.0.family"


class TestVariableBindings:
    """Test variable binding and retrieval functionality."""

    def test_bind_single_variable(self):
        """Test binding a single variable."""
        context = TranslationContext()
        context.bind_variable("$this", "cte_1_item")

        assert context.variable_bindings["$this"].expression == "cte_1_item"

    def test_bind_multiple_variables(self):
        """Test binding multiple variables."""
        context = TranslationContext()
        context.bind_variable("$this", "cte_1_item")
        context.bind_variable("$index", "idx")
        context.bind_variable("$total", "total_count")

        assert context.variable_bindings["$this"].expression == "cte_1_item"
        assert context.variable_bindings["$index"].expression == "idx"
        assert context.variable_bindings["$total"].expression == "total_count"

    def test_get_bound_variable(self):
        """Test retrieving a bound variable."""
        context = TranslationContext()
        context.bind_variable("$this", "cte_1_item")

        value = context.get_variable("$this")

        assert value is not None
        assert value.expression == "cte_1_item"

    def test_get_unbound_variable_returns_none(self):
        """Test retrieving unbound variable returns None."""
        context = TranslationContext()

        value = context.get_variable("$missing")

        assert value is None

    def test_rebind_variable(self):
        """Test rebinding a variable to new value."""
        context = TranslationContext()
        context.bind_variable("$this", "old_value")
        context.bind_variable("$this", "new_value")

        rebinding = context.get_variable("$this")
        assert rebinding is not None
        assert rebinding.expression == "new_value"

    def test_clear_variables(self):
        """Test clearing all variable bindings."""
        context = TranslationContext()
        context.bind_variable("$this", "cte_1_item")
        context.bind_variable("$index", "idx")

        assert len(context.variable_bindings) == 2

        context.clear_variables()

        assert len(context.variable_bindings) == 0
        assert context.get_variable("$this") is None

    def test_clear_empty_variables(self):
        """Test clearing variables when none are bound."""
        context = TranslationContext()

        context.clear_variables()  # Should not raise error

        assert len(context.variable_bindings) == 0


class TestVariableScopes:
    """Test push/pop behaviour for variable scopes."""

    def test_push_scope_preserves_by_default(self):
        context = TranslationContext()
        context.bind_variable("$this", "root")

        context.push_variable_scope()
        context.bind_variable("$this", "child")

        child_binding = context.get_variable("$this")
        assert child_binding is not None
        assert child_binding.expression == "child"

        context.pop_variable_scope()
        root_binding = context.get_variable("$this")
        assert root_binding is not None
        assert root_binding.expression == "root"

    def test_push_scope_without_preserve(self):
        context = TranslationContext()
        context.bind_variable("$this", "root")

        context.push_variable_scope(preserve=False)
        context.bind_variable("$child", "value")

        child_binding = context.get_variable("$child")
        assert child_binding is not None
        assert child_binding.expression == "value"

        context.pop_variable_scope()
        assert context.get_variable("$child") is None
        root_binding = context.get_variable("$this")
        assert root_binding is not None
        assert root_binding.expression == "root"

    def test_pop_scope_exception_on_root(self):
        context = TranslationContext()
        with pytest.raises(RuntimeError):
            context.pop_variable_scope()

class TestContextReset:
    """Test context reset functionality."""

    def test_reset_clears_path(self):
        """Test reset clears path stack."""
        context = TranslationContext()
        context.push_path("name")
        context.push_path("family")

        context.reset()

        assert context.parent_path == []

    def test_reset_clears_variables(self):
        """Test reset clears variable bindings."""
        context = TranslationContext()
        context.bind_variable("$this", "item")
        context.bind_variable("$index", "idx")

        context.reset()

        assert context.variable_bindings == {}

    def test_reset_clears_cte_counter(self):
        """Test reset clears CTE counter."""
        context = TranslationContext()
        context.next_cte_name()
        context.next_cte_name()

        assert context.cte_counter == 2

        context.reset()

        assert context.cte_counter == 0
        assert context.next_cte_name() == "cte_1"

    def test_reset_restores_current_table(self):
        """Test reset restores current_table to default."""
        context = TranslationContext()
        context.current_table = "cte_5"

        context.reset()

        assert context.current_table == "resource"

    def test_reset_preserves_resource_type(self):
        """Test reset does NOT change current_resource_type."""
        context = TranslationContext(current_resource_type="Observation")
        context.push_path("code")
        context.bind_variable("$this", "item")

        context.reset()

        # Resource type is NOT reset (it's set during initialization)
        assert context.current_resource_type == "Observation"

    def test_full_reset(self):
        """Test reset clears all mutable state."""
        context = TranslationContext()

        # Add various state
        context.current_table = "cte_3"
        context.push_path("name")
        context.push_path("family")
        context.bind_variable("$this", "item")
        context.bind_variable("$index", "idx")
        context.next_cte_name()
        context.next_cte_name()

        # Reset
        context.reset()

        # Verify all state cleared
        assert context.current_table == "resource"
        assert context.parent_path == []
        assert context.variable_bindings == {}
        assert context.cte_counter == 0


class TestContextEdgeCases:
    """Test TranslationContext edge cases and boundary conditions."""

    def test_very_deep_path_nesting(self):
        """Test handling very deep path nesting (100+ levels)."""
        context = TranslationContext()

        # Push 100 path components
        for i in range(100):
            context.push_path(f"level_{i}")

        assert len(context.parent_path) == 100

        json_path = context.get_json_path()
        assert json_path.startswith("$.")
        assert "level_0" in json_path
        assert "level_99" in json_path

    def test_many_variables(self):
        """Test binding many variables (100+)."""
        context = TranslationContext()

        # Bind 100 variables
        for i in range(100):
            context.bind_variable(f"$var_{i}", f"value_{i}")

        assert len(context.variable_bindings) == 100

        # All variables retrievable
        for i in range(100):
            binding = context.get_variable(f"$var_{i}")
            assert binding is not None
            assert binding.expression == f"value_{i}"

    def test_many_cte_names(self):
        """Test generating many CTE names (1000+)."""
        context = TranslationContext()

        # Generate 1000 CTE names
        names = [context.next_cte_name() for _ in range(1000)]

        assert len(names) == 1000
        assert names[0] == "cte_1"
        assert names[999] == "cte_1000"
        assert len(set(names)) == 1000  # All unique

    def test_unicode_in_path_components(self):
        """Test path components with Unicode characters."""
        context = TranslationContext()
        context.push_path("名前")  # Japanese for "name"
        context.push_path("família")  # Portuguese for "family"

        json_path = context.get_json_path()

        assert "名前" in json_path
        assert "família" in json_path

    def test_special_characters_in_path(self):
        """Test path components with special characters."""
        context = TranslationContext()
        context.push_path("name-with-dash")
        context.push_path("name_with_underscore")

        json_path = context.get_json_path()

        assert "name-with-dash" in json_path
        assert "name_with_underscore" in json_path

    def test_empty_string_path_component(self):
        """Test pushing empty string as path component."""
        context = TranslationContext()
        context.push_path("")

        json_path = context.get_json_path()

        # Empty component still included in path
        assert json_path == "$."

    def test_variable_name_without_dollar(self):
        """Test variable names without $ prefix (allowed but not recommended)."""
        context = TranslationContext()
        context.bind_variable("this", "value")

        binding = context.get_variable("this")
        assert binding is not None
        assert binding.expression == "value"


class TestContextDataclassFeatures:
    """Test TranslationContext dataclass-specific features."""

    def test_context_is_mutable(self):
        """Test that TranslationContext fields are mutable."""
        context = TranslationContext()

        # Modify fields
        context.current_table = "new_table"
        context.current_resource_type = "Observation"
        context.cte_counter = 10

        assert context.current_table == "new_table"
        assert context.current_resource_type == "Observation"
        assert context.cte_counter == 10

    def test_repr_output(self):
        """Test TranslationContext __repr__ output."""
        context = TranslationContext()

        repr_str = repr(context)

        assert "TranslationContext" in repr_str
        assert "current_table" in repr_str

    def test_equality_comparison(self):
        """Test TranslationContext equality comparison."""
        context1 = TranslationContext(
            current_table="resource",
            current_resource_type="Patient"
        )
        context2 = TranslationContext(
            current_table="resource",
            current_resource_type="Patient"
        )

        assert context1 == context2

    def test_inequality_comparison(self):
        """Test TranslationContext inequality comparison."""
        context1 = TranslationContext(current_resource_type="Patient")
        context2 = TranslationContext(current_resource_type="Observation")

        assert context1 != context2


class TestContextIntegrationScenarios:
    """Test realistic integration scenarios for TranslationContext."""

    def test_simple_path_navigation_scenario(self):
        """Test context for simple path navigation: Patient.name.family."""
        context = TranslationContext(current_resource_type="Patient")

        # Traverse Patient (no path push for root)
        # Traverse name
        context.push_path("name")
        assert context.get_json_path() == "$.name"

        # Traverse family
        context.push_path("family")
        assert context.get_json_path() == "$.name.family"

        # Pop back up
        context.pop_path()
        assert context.get_json_path() == "$.name"

    def test_where_function_scenario(self):
        """Test context for where() function with variable binding."""
        context = TranslationContext()

        # Processing: Patient.name.where(use='official')
        context.push_path("name")

        # Generate CTE for unnesting
        cte_name = context.next_cte_name()
        assert cte_name == "cte_1"

        # Bind $this variable for where condition
        context.bind_variable("$this", f"{cte_name}_item")

        # Update current table to CTE
        context.current_table = cte_name

        # Variable is available
        binding = context.get_variable("$this")
        assert binding is not None
        assert binding.expression == "cte_1_item"

    def test_multi_step_expression_scenario(self):
        """Test context for multi-step expression with multiple CTEs."""
        context = TranslationContext()

        # Step 1: Patient.name
        context.push_path("name")
        cte1 = context.next_cte_name()
        context.current_table = cte1
        assert cte1 == "cte_1"

        # Step 2: where(use='official')
        cte2 = context.next_cte_name()
        context.current_table = cte2
        assert cte2 == "cte_2"

        # Step 3: family
        context.push_path("family")
        cte3 = context.next_cte_name()
        context.current_table = cte3
        assert cte3 == "cte_3"

        # Final state
        assert context.get_json_path() == "$.name.family"
        assert context.current_table == "cte_3"
        assert context.cte_counter == 3
