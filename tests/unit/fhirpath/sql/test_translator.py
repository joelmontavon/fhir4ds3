"""Unit tests for ASTToSQLTranslator base class.

Tests the core translator structure, initialization, visitor pattern setup,
and base functionality without testing actual translation logic (which will
be tested in subsequent tasks).

Test Coverage:
- Class instantiation and initialization
- Dialect storage and access
- Context initialization and management
- translate() method structure
- Visitor method stubs raise NotImplementedError
- Fragment accumulation
- Logging and error handling

Module: tests.unit.fhirpath.sql.test_translator
Created: 2025-09-30
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import logging

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.sql.context import TranslationContext, VariableBinding
from fhir4ds.fhirpath.ast.nodes import (
    FHIRPathASTNode, LiteralNode, IdentifierNode, FunctionCallNode,
    OperatorNode, ConditionalNode, AggregationNode, TypeOperationNode
)
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.exceptions import FHIRPathParseError


@pytest.fixture
def dialect():
    """Create a test dialect instance using DuckDB"""
    from fhir4ds.dialects.duckdb import DuckDBDialect
    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Create PostgreSQL dialect instance when available."""
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    try:
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not available")


class TestASTToSQLTranslatorInstantiation:
    """Test translator class instantiation and initialization"""

    def test_instantiation_with_dialect(self, dialect):
        """Test translator can be instantiated with a dialect"""
        translator = ASTToSQLTranslator(dialect)

        assert translator is not None
        assert isinstance(translator, ASTToSQLTranslator)

    def test_instantiation_with_resource_type(self, dialect):
        """Test translator can be instantiated with custom resource type"""
        translator = ASTToSQLTranslator(dialect, "Observation")

        assert translator.resource_type == "Observation"

    def test_default_resource_type(self, dialect):
        """Test default resource type is Patient"""
        translator = ASTToSQLTranslator(dialect)

        assert translator.resource_type == "Patient"

    def test_dialect_storage(self, dialect):
        """Test dialect is stored correctly"""
        translator = ASTToSQLTranslator(dialect)

        assert translator.dialect is dialect

    def test_context_initialization(self, dialect):
        """Test TranslationContext is initialized correctly"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        assert translator.context is not None
        assert isinstance(translator.context, TranslationContext)
        assert translator.context.current_resource_type == "Patient"
        assert translator.context.current_table == "resource"

    def test_fragments_list_initialization(self, dialect):
        """Test fragments list is initialized empty"""
        translator = ASTToSQLTranslator(dialect)

        assert translator.fragments is not None
        assert isinstance(translator.fragments, list)
        assert len(translator.fragments) == 0

    def test_logging_initialization(self, dialect):
        """Test logger is set up correctly"""
        with patch('fhir4ds.fhirpath.sql.translator.logger') as mock_logger:
            translator = ASTToSQLTranslator(dialect, "Observation")
            mock_logger.info.assert_called_once()
            assert "Observation" in str(mock_logger.info.call_args)


class TestTranslateMethod:
    """Test the translate() method structure"""

    def test_translate_clears_fragments(self, dialect):
        """Test translate() clears fragments from previous translation"""
        
        translator = ASTToSQLTranslator(dialect)

        # Add some fragments manually
        translator.fragments.append(
            SQLFragment(expression="SELECT * FROM test", source_table="test")
        )
        assert len(translator.fragments) > 0

        # Create a mock AST node that returns a fragment
        mock_node = Mock(spec=FHIRPathASTNode)
        mock_node.node_type = "literal"
        mock_node.accept = Mock(return_value=SQLFragment(
            expression="'test'",
            source_table="resource"
        ))

        # Translate should clear and repopulate
        translator.translate(mock_node)

        # Should have only the new fragment
        assert len(translator.fragments) == 1
        assert translator.fragments[0].expression == "'test'"

    def test_translate_resets_context(self, dialect):
        """Test translate() resets context to initial state"""
        
        translator = ASTToSQLTranslator(dialect)

        # Modify context
        translator.context.push_path("modified")
        translator.context.current_table = "modified_table"
        translator.context.cte_counter = 5

        # Create mock node
        mock_node = Mock(spec=FHIRPathASTNode)
        mock_node.node_type = "literal"
        mock_node.accept = Mock(return_value=SQLFragment(
            expression="'test'",
            source_table="resource"
        ))

        # Translate should reset context
        translator.translate(mock_node)

        assert translator.context.current_table == "resource"
        assert translator.context.cte_counter == 0
        assert len(translator.context.parent_path) == 0

    def test_translate_resets_variable_bindings(self, dialect):
        """Translate should clear previously bound variables to avoid leaks."""
        translator = ASTToSQLTranslator(dialect)
        translator.context.bind_variable("$temp", VariableBinding(expression="temp_alias"))
        translator.context.push_path("name")

        literal_node = LiteralNode(
            node_type="literal",
            text="'value'",
            value="value",
            literal_type="string"
        )

        translator.translate(literal_node)

        assert translator.context.get_variable("$temp") is None
        assert translator.context.parent_path == []

    def test_translate_calls_visit(self, dialect):
        """Test translate() calls visit on root node"""
        
        translator = ASTToSQLTranslator(dialect)

        mock_node = Mock(spec=FHIRPathASTNode)
        mock_node.node_type = "literal"
        mock_fragment = SQLFragment(expression="'test'", source_table="resource")
        mock_node.accept = Mock(return_value=mock_fragment)

        translator.translate(mock_node)

        # Verify visit was called (accept should be called)
        mock_node.accept.assert_called_once()

    def test_translate_accumulates_fragment(self, dialect):
        """Test translate() accumulates returned fragment"""
        
        translator = ASTToSQLTranslator(dialect)

        mock_node = Mock(spec=FHIRPathASTNode)
        mock_node.node_type = "literal"
        mock_fragment = SQLFragment(expression="SELECT 1", source_table="resource")
        mock_node.accept = Mock(return_value=mock_fragment)

        result = translator.translate(mock_node)

        assert len(result) == 1
        assert result[0].expression == "SELECT 1"
        assert result[0].source_table == "resource"

    def test_translate_returns_fragments_list(self, dialect):
        """Test translate() returns list of fragments"""
        
        translator = ASTToSQLTranslator(dialect)

        mock_node = Mock(spec=FHIRPathASTNode)
        mock_node.node_type = "literal"
        mock_node.accept = Mock(return_value=SQLFragment(
            expression="'value'",
            source_table="resource"
        ))

        result = translator.translate(mock_node)

        assert isinstance(result, list)
        assert all(isinstance(f, SQLFragment) for f in result)

    def test_translate_handles_none_fragment(self, dialect):
        """Test translate() handles None fragment gracefully"""
        
        translator = ASTToSQLTranslator(dialect)

        mock_node = Mock(spec=FHIRPathASTNode)
        mock_node.node_type = "literal"
        mock_node.accept = Mock(return_value=None)

        result = translator.translate(mock_node)

        # Should not add None to fragments
        assert len(result) == 0

    def test_translate_logs_start_and_completion(self, dialect):
        """Test translate() logs translation start and completion"""
        
        translator = ASTToSQLTranslator(dialect)

        mock_node = Mock(spec=FHIRPathASTNode)
        mock_node.node_type = "literal"
        mock_node.accept = Mock(return_value=SQLFragment(
            expression="'test'",
            source_table="resource"
        ))

        with patch('fhir4ds.fhirpath.sql.translator.logger') as mock_logger:
            translator.translate(mock_node)

            # Check debug and info calls
            assert mock_logger.debug.called
            assert mock_logger.info.called


class TestVisitorMethodStubs:
    """Test that all visitor methods are present and raise NotImplementedError"""

    # test_visit_literal_raises_not_implemented removed - implementation complete in SP-005-004

    # test_visit_identifier_raises_not_implemented removed - implementation complete in SP-005-005

    # test_visit_function_call_raises_not_implemented_for_exists removed - exists() implementation complete in SP-005-010

    def test_visit_function_call_raises_not_implemented(self, dialect):
        """Test visit_function_call raises NotImplementedError for unimplemented functions"""

        translator = ASTToSQLTranslator(dialect)

        # Use sum() which hasn't been implemented yet
        node = FunctionCallNode(
            node_type="function_call",
            text="sum()",
            function_name="sum"
        )

        with pytest.raises(NotImplementedError) as exc_info:
            translator.visit_function_call(node)

        assert "pending in future tasks" in str(exc_info.value)

    # test_visit_operator_raises_not_implemented removed - implementation complete in SP-005-006

    def test_visit_conditional_raises_not_implemented(self, dialect):
        """Test visit_conditional raises NotImplementedError"""
        
        translator = ASTToSQLTranslator(dialect)

        node = ConditionalNode(
            node_type="conditional",
            text="if condition then true else false"
        )

        with pytest.raises(NotImplementedError) as exc_info:
            translator.visit_conditional(node)

        assert "future sprint" in str(exc_info.value).lower()

    def test_visit_aggregation_implemented(self, dialect):
        """Test visit_aggregation is implemented (SP-005-011)"""

        translator = ASTToSQLTranslator(dialect)

        # Set up context for aggregation
        translator.context.push_path("name")

        node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        node.children = []

        # Should not raise NotImplementedError anymore
        fragment = translator.visit_aggregation(node)

        # Should return a SQLFragment with is_aggregate=True
        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True

    def test_visit_type_operation_oftype_implemented(self, dialect):
        """Test visit_type_operation handles ofType() correctly"""

        translator = ASTToSQLTranslator(dialect)

        # Create identifier node as child
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="collection",
            identifier="collection"
        )

        node = TypeOperationNode(
            node_type="type_operation",
            text="collection ofType Integer",
            operation="ofType",
            target_type="Integer"
        )
        node.children = [identifier_node]

        # Should not raise NotImplementedError anymore
        fragment = translator.visit_type_operation(node)

        # Should return a SQLFragment
        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is False
        assert fragment.requires_unnest is False


class TestVisitorPatternIntegration:
    """Test visitor pattern integration with AST nodes"""

    def test_visitor_inherits_from_ast_visitor(self, dialect):
        """Test ASTToSQLTranslator inherits from ASTVisitor"""
        from fhir4ds.fhirpath.ast.visitor import ASTVisitor

        
        translator = ASTToSQLTranslator(dialect)

        assert isinstance(translator, ASTVisitor)

    def test_visitor_has_all_required_methods(self, dialect):
        """Test translator has all required visitor methods"""
        
        translator = ASTToSQLTranslator(dialect)

        required_methods = [
            'visit_literal',
            'visit_identifier',
            'visit_function_call',
            'visit_operator',
            'visit_conditional',
            'visit_aggregation',
            'visit_type_operation'
        ]

        for method_name in required_methods:
            assert hasattr(translator, method_name)
            assert callable(getattr(translator, method_name))

    def test_visitor_pattern_accept_calls_correct_method(self, dialect):
        """Test AST node accept() calls correct visitor method"""

        translator = ASTToSQLTranslator(dialect)

        # Test that visiting a LiteralNode calls visit_literal and returns SQLFragment
        node = LiteralNode(
            node_type="literal",
            text="'test'",
            value="test"
        )

        # visit_literal is now implemented in SP-005-004, so it returns SQLFragment
        result = translator.visit(node)
        assert isinstance(result, SQLFragment)


class TestContextManagement:
    """Test context management during translation"""

    def test_context_accessible_during_translation(self, dialect):
        """Test context is accessible during translation"""
        
        translator = ASTToSQLTranslator(dialect, "Patient")

        assert translator.context is not None
        assert translator.context.current_resource_type == "Patient"

    def test_context_resource_type_matches_translator(self, dialect):
        """Test context resource type matches translator resource type"""
        
        translator = ASTToSQLTranslator(dialect, "Observation")

        assert translator.resource_type == translator.context.current_resource_type
        assert translator.resource_type == "Observation"

    def test_multiple_translators_have_independent_contexts(self, dialect):
        """Test multiple translator instances have independent contexts"""
        
        translator1 = ASTToSQLTranslator(dialect, "Patient")
        translator2 = ASTToSQLTranslator(dialect, "Observation")

        # Modify first translator's context
        translator1.context.push_path("test")

        # Second translator's context should be unaffected
        assert len(translator1.context.parent_path) == 1
        assert len(translator2.context.parent_path) == 0
        assert translator1.context.current_resource_type == "Patient"
        assert translator2.context.current_resource_type == "Observation"


class TestDialectIntegration:
    """Test dialect integration"""

    def test_dialect_methods_accessible(self, dialect):
        """Test dialect methods are accessible from translator"""
        
        translator = ASTToSQLTranslator(dialect)

        # Should be able to call dialect methods
        result = translator.dialect.extract_json_field("resource", "$.name")
        assert "json_extract" in result
        assert "resource" in result
        assert "$.name" in result

    def test_translator_works_with_different_dialects(self, dialect):
        """Test translator can work with different dialect implementations"""
        from fhir4ds.dialects.duckdb import DuckDBDialect

        dialect1 = DuckDBDialect(database=":memory:")
        dialect2 = DuckDBDialect(database=":memory:")

        translator1 = ASTToSQLTranslator(dialect1)
        translator2 = ASTToSQLTranslator(dialect2)

        assert translator1.dialect is dialect1
        assert translator2.dialect is dialect2
        assert translator1.dialect is not translator2.dialect


class TestErrorHandling:
    """Test error handling in translator"""

    def test_translate_with_invalid_node_type(self, dialect):
        """Test translate handles invalid node types gracefully"""
        
        translator = ASTToSQLTranslator(dialect)

        # Create a node with unknown type
        mock_node = Mock(spec=FHIRPathASTNode)
        mock_node.node_type = "unknown_type"
        mock_node.accept = Mock(side_effect=NotImplementedError("Unknown node type"))

        with pytest.raises(NotImplementedError):
            translator.translate(mock_node)

    def test_visitor_error_count_tracked(self, dialect):
        """Test visitor tracks error count from base class"""
        
        translator = ASTToSQLTranslator(dialect)

        # Base ASTVisitor should track errors
        assert hasattr(translator, '_error_count')
        assert translator._error_count == 0


class TestFragmentAccumulation:
    """Test fragment accumulation during translation"""

    def test_empty_fragments_after_initialization(self, dialect):
        """Test fragments list is empty after initialization"""
        
        translator = ASTToSQLTranslator(dialect)

        assert len(translator.fragments) == 0

    def test_fragments_cleared_between_translations(self, dialect):
        """Test fragments are cleared between translations"""
        
        translator = ASTToSQLTranslator(dialect)

        # First translation
        mock_node1 = Mock(spec=FHIRPathASTNode)
        mock_node1.node_type = "literal"
        mock_node1.accept = Mock(return_value=SQLFragment(
            expression="'first'",
            source_table="resource"
        ))
        translator.translate(mock_node1)
        assert len(translator.fragments) == 1

        # Second translation should clear previous fragments
        mock_node2 = Mock(spec=FHIRPathASTNode)
        mock_node2.node_type = "literal"
        mock_node2.accept = Mock(return_value=SQLFragment(
            expression="'second'",
            source_table="resource"
        ))
        translator.translate(mock_node2)
        assert len(translator.fragments) == 1
        assert translator.fragments[0].expression == "'second'"


class TestDocstrings:
    """Test that all methods have proper docstrings"""

    def test_class_has_docstring(self, dialect):
        """Test ASTToSQLTranslator class has docstring"""
        assert ASTToSQLTranslator.__doc__ is not None
        assert len(ASTToSQLTranslator.__doc__) > 100

    def test_init_has_docstring(self, dialect):
        """Test __init__ has docstring"""
        assert ASTToSQLTranslator.__init__.__doc__ is not None

    def test_translate_has_docstring(self, dialect):
        """Test translate has docstring"""
        assert ASTToSQLTranslator.translate.__doc__ is not None

    def test_visitor_methods_have_docstrings(self, dialect):
        """Test all visitor methods have docstrings"""
        visitor_methods = [
            'visit_literal',
            'visit_identifier',
            'visit_function_call',
            'visit_operator',
            'visit_conditional',
            'visit_aggregation',
            'visit_type_operation'
        ]

        for method_name in visitor_methods:
            method = getattr(ASTToSQLTranslator, method_name)
            assert method.__doc__ is not None
            assert len(method.__doc__) > 50


class TestVisitLiteralImplementation:
    """Test visit_literal() implementation for all literal types"""

    def test_visit_literal_string_basic(self, dialect):
        """Test translating basic string literal"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="'John'",
            value="John",
            literal_type="string"
        )

        fragment = translator.visit_literal(node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression == "'John'"
        assert fragment.source_table == "resource"
        assert not fragment.requires_unnest
        assert not fragment.is_aggregate

    def test_visit_literal_string_with_single_quote(self, dialect):
        """Test translating string literal with single quote (escaping)"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="'John''s'",
            value="John's",
            literal_type="string"
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == "'John''s'"  # Single quote escaped by doubling

    def test_visit_literal_string_empty(self, dialect):
        """Test translating empty string literal"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="''",
            value="",
            literal_type="string"
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == "''"

    def test_visit_literal_integer_positive(self, dialect):
        """Test translating positive integer literal"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="42",
            value=42,
            literal_type="integer"
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == "42"
        assert not fragment.requires_unnest
        assert not fragment.is_aggregate

    def test_visit_literal_integer_negative(self, dialect):
        """Test translating negative integer literal"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="-100",
            value=-100,
            literal_type="integer"
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == "-100"

    def test_visit_literal_integer_zero(self, dialect):
        """Test translating zero integer literal"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="0",
            value=0,
            literal_type="integer"
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == "0"

    def test_visit_literal_decimal_basic(self, dialect):
        """Test translating basic decimal literal"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="3.14",
            value=3.14,
            literal_type="decimal"
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == "3.14"

    def test_visit_literal_decimal_negative(self, dialect):
        """Test translating negative decimal literal"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="-2.5",
            value=-2.5,
            literal_type="decimal"
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == "-2.5"

    def test_visit_literal_boolean_true(self, dialect):
        """Test translating boolean TRUE literal"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="true",
            value=True,
            literal_type="boolean"
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == "TRUE"

    def test_visit_literal_boolean_false(self, dialect):
        """Test translating boolean FALSE literal"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="false",
            value=False,
            literal_type="boolean"
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == "FALSE"

    def test_visit_literal_date(self, dialect):
        """Test translating date literal (calls dialect method)"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="@2024-01-01",
            value="2024-01-01"
        )
        # Override the inferred type to test date handling
        node.literal_type = "date"

        fragment = translator.visit_literal(node)

        # Should call dialect.generate_date_literal()
        assert "DATE" in fragment.expression
        assert "2024-01-01" in fragment.expression

    def test_visit_literal_datetime(self, dialect):
        """Test translating datetime literal (calls dialect method)"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="@2024-01-01T12:30:00",
            value="2024-01-01T12:30:00"
        )
        # Override the inferred type to test datetime handling
        node.literal_type = "datetime"

        fragment = translator.visit_literal(node)

        # Should call dialect.generate_datetime_literal()
        assert "TIMESTAMP" in fragment.expression or "DATETIME" in fragment.expression
        assert "2024-01-01" in fragment.expression
        assert "12:30:00" in fragment.expression

    def test_visit_literal_unknown_type_raises_error(self, dialect):
        """Test translating unknown literal type raises ValueError"""
        translator = ASTToSQLTranslator(dialect)

        # Create node with a None value so it stays as unknown type
        node = LiteralNode(
            node_type="literal",
            text="unknown",
            value=None
        )
        # Force unknown type
        node.literal_type = "unsupported_type"

        with pytest.raises(ValueError) as exc_info:
            translator.visit_literal(node)

        assert "Unknown or unsupported literal type" in str(exc_info.value)

    @pytest.mark.parametrize("literal_type,value,expected", [
        ("string", "test", "'test'"),
        ("string", "a'b", "'a''b'"),  # Escaping
        ("integer", 1, "1"),
        ("integer", 999, "999"),
        ("decimal", 1.5, "1.5"),
        ("decimal", 0.001, "0.001"),
        ("boolean", True, "TRUE"),
        ("boolean", False, "FALSE"),
    ])
    def test_visit_literal_parametrized(self, dialect, literal_type, value, expected):
        """Test various literal types with parametrized inputs"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text=str(value),
            value=value,
            literal_type=literal_type
        )

        fragment = translator.visit_literal(node)

        assert fragment.expression == expected

    def test_visit_literal_with_custom_resource_type(self, dialect):
        """Test visit_literal respects translator resource type context"""
        translator = ASTToSQLTranslator(dialect, "Observation")

        node = LiteralNode(
            node_type="literal",
            text="'test'",
            value="test",
            literal_type="string"
        )

        fragment = translator.visit_literal(node)

        # Source table should still be 'resource' (default from context)
        assert fragment.source_table == "resource"

    def test_visit_literal_logging(self, dialect):
        """Test visit_literal logs translation activity"""
        translator = ASTToSQLTranslator(dialect)

        node = LiteralNode(
            node_type="literal",
            text="42",
            value=42,
            literal_type="integer"
        )

        with patch('fhir4ds.fhirpath.sql.translator.logger') as mock_logger:
            translator.visit_literal(node)

            # Should log debug messages
            assert mock_logger.debug.call_count >= 2  # Start and end
            # Check that literal type and value are mentioned
            calls_str = str(mock_logger.debug.call_args_list)
            assert "integer" in calls_str
            assert "42" in calls_str


class TestVisitIdentifierImplementation:
    """Test visit_identifier() implementation for all identifier scenarios"""

    def test_visit_identifier_root_resource_reference(self, dialect):
        """Test translating root resource reference (e.g., Patient)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        node = IdentifierNode(
            node_type="identifier",
            text="Patient",
            identifier="Patient"
        )

        fragment = translator.visit_identifier(node)

        assert isinstance(fragment, SQLFragment)
        # Root resource reference should just return the current table
        assert fragment.expression == "resource"
        assert fragment.source_table == "resource"
        assert not fragment.requires_unnest
        assert not fragment.is_aggregate

    def test_visit_identifier_simple_field(self, dialect):
        """Test translating simple scalar field identifier"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        node = IdentifierNode(
            node_type="identifier",
            text="birthDate",
            identifier="birthDate"
        )

        fragment = translator.visit_identifier(node)

        assert isinstance(fragment, SQLFragment)
        # Should generate JSON extraction for $.birthDate
        assert "json_extract" in fragment.expression
        assert "resource" in fragment.expression
        assert "$.birthDate" in fragment.expression
        assert fragment.source_table == "resource"
        assert not fragment.requires_unnest
        assert not fragment.is_aggregate

    def test_visit_identifier_nested_field(self, dialect):
        """Test translating nested field with existing path context"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Set up context with existing path
        translator.context.push_path("name")

        node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        fragment = translator.visit_identifier(node)

        # Should generate JSON extraction for $.name.family
        assert "json_extract" in fragment.expression
        assert "$.name.family" in fragment.expression

    def test_visit_identifier_deeply_nested_field(self, dialect):
        """Test translating deeply nested field (3+ levels)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Set up deep nesting
        translator.context.push_path("contact")
        translator.context.push_path("address")

        node = IdentifierNode(
            node_type="identifier",
            text="city",
            identifier="city"
        )

        fragment = translator.visit_identifier(node)

        # Should generate JSON extraction for $.contact.address.city
        assert "json_extract" in fragment.expression
        assert "$.contact.address.city" in fragment.expression

    def test_visit_identifier_updates_context_path(self, dialect):
        """Test that visit_identifier updates context.parent_path"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        initial_path_length = len(translator.context.parent_path)

        node = IdentifierNode(
            node_type="identifier",
            text="name",
            identifier="name"
        )

        translator.visit_identifier(node)

        # Path should have one more component
        assert len(translator.context.parent_path) == initial_path_length + 1
        assert translator.context.parent_path[-1] == "name"

    def test_visit_identifier_with_different_resource_types(self, dialect):
        """Test identifier translation for different resource types"""
        test_cases = [
            ("Patient", "birthDate"),
            ("Observation", "valueQuantity"),
            ("Condition", "onsetDateTime"),
            ("Medication", "code")
        ]

        for resource_type, field in test_cases:
            translator = ASTToSQLTranslator(dialect, resource_type)

            node = IdentifierNode(
                node_type="identifier",
                text=field,
                identifier=field
            )

            fragment = translator.visit_identifier(node)

            # All should generate JSON extraction
            assert "json_extract" in fragment.expression
            assert f"$.{field}" in fragment.expression

    def test_visit_identifier_observation_root_reference(self, dialect):
        """Test root reference for Observation resource type"""
        translator = ASTToSQLTranslator(dialect, "Observation")

        node = IdentifierNode(
            node_type="identifier",
            text="Observation",
            identifier="Observation"
        )

        fragment = translator.visit_identifier(node)

        # Should return table reference without JSON extraction
        assert fragment.expression == "resource"
        assert fragment.source_table == "resource"

    def test_visit_identifier_condition_root_reference(self, dialect):
        """Test root reference for Condition resource type"""
        translator = ASTToSQLTranslator(dialect, "Condition")

        node = IdentifierNode(
            node_type="identifier",
            text="Condition",
            identifier="Condition"
        )

        fragment = translator.visit_identifier(node)

        assert fragment.expression == "resource"

    def test_visit_identifier_logging(self, dialect):
        """Test visit_identifier logs translation activity"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        node = IdentifierNode(
            node_type="identifier",
            text="name",
            identifier="name"
        )

        with patch('fhir4ds.fhirpath.sql.translator.logger') as mock_logger:
            translator.visit_identifier(node)

            # Should log debug messages
            assert mock_logger.debug.call_count >= 2
            # Check that identifier is mentioned
            calls_str = str(mock_logger.debug.call_args_list)
            assert "name" in calls_str

    def test_visit_identifier_multiple_sequential_calls(self, dialect):
        """Test multiple sequential identifier translations build correct paths"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        # First identifier
        node1 = IdentifierNode(
            node_type="identifier",
            text="name",
            identifier="name"
        )
        fragment1 = translator.visit_identifier(node1)
        assert "$.name" in fragment1.expression

        # Second identifier (should build on first)
        node2 = IdentifierNode(
            node_type="identifier",
            text="given",
            identifier="given"
        )
        fragment2 = translator.visit_identifier(node2)
        assert "$.name.given" in fragment2.expression

        # Third identifier (should build on both)
        node3 = IdentifierNode(
            node_type="identifier",
            text="first",
            identifier="first"
        )
        fragment3 = translator.visit_identifier(node3)
        assert "$.name.given.first" in fragment3.expression

    def test_visit_identifier_context_isolation_between_translators(self, dialect):
        """Test that different translator instances have isolated contexts"""
        translator1 = ASTToSQLTranslator(dialect, "Patient")
        translator2 = ASTToSQLTranslator(dialect, "Patient")

        # Translate identifier in first translator
        node1 = IdentifierNode(
            node_type="identifier",
            text="name",
            identifier="name"
        )
        translator1.visit_identifier(node1)

        # Second translator should have empty path
        assert len(translator2.context.parent_path) == 0

        # Translate in second translator
        node2 = IdentifierNode(
            node_type="identifier",
            text="birthDate",
            identifier="birthDate"
        )
        fragment2 = translator2.visit_identifier(node2)

        # Should generate $.birthDate (not affected by first translator)
        assert "$.birthDate" in fragment2.expression

    @pytest.mark.parametrize("field_name,expected_path", [
        ("id", "$.id"),
        ("name", "$.name"),
        ("birthDate", "$.birthDate"),
        ("gender", "$.gender"),
        ("active", "$.active"),
        ("address", "$.address"),
        ("telecom", "$.telecom"),
        ("maritalStatus", "$.maritalStatus"),
        ("multipleBirthBoolean", "$.multipleBirthBoolean"),
        ("photo", "$.photo"),
    ])
    def test_visit_identifier_various_field_names(self, dialect, field_name, expected_path):
        """Test various FHIR field names are translated correctly"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        node = IdentifierNode(
            node_type="identifier",
            text=field_name,
            identifier=field_name
        )

        fragment = translator.visit_identifier(node)

        assert expected_path in fragment.expression

    def test_visit_identifier_with_custom_table(self, dialect):
        """Test identifier translation with custom source table"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Change current table to simulate CTE scenario
        translator.context.current_table = "cte_1"

        node = IdentifierNode(
            node_type="identifier",
            text="value",
            identifier="value"
        )

        fragment = translator.visit_identifier(node)

        # Should use cte_1 instead of resource
        assert "cte_1" in fragment.expression
        assert fragment.source_table == "cte_1"


class TestVisitIdentifierArrayDetection:
    """Array detection and metadata propagation for identifier translation."""

    def test_array_field_sets_requires_unnest(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        node = IdentifierNode(node_type="identifier", text="name", identifier="name")

        fragment = translator.visit_identifier(node)

        assert fragment.requires_unnest is True
        assert fragment.metadata["array_column"] == "json_extract(resource, '$.name[*]')"
        assert fragment.metadata["result_alias"] == "name_item"
        assert fragment.metadata["source_path"] == "$.name"
        assert fragment.metadata["projection_expression"] == "name_item.unnest"

    def test_array_fragment_expression_matches_metadata(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        node = IdentifierNode(node_type="identifier", text="identifier", identifier="identifier")

        fragment = translator.visit_identifier(node)

        assert fragment.expression == fragment.metadata["array_column"]
        assert "$.identifier[*]" in fragment.expression

    def test_translate_array_expression_returns_single_fragment(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        parser = FHIRPathParser()
        ast = parser.parse("Patient.name".get_ast())

        fragments = translator.translate(ast)

        assert len(fragments) == 1
        assert fragments[0].requires_unnest is True

    def test_nested_array_generates_multiple_fragments(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        parser = FHIRPathParser()
        ast = parser.parse("Patient.name.given".get_ast())

        fragments = translator.translate(ast)

        assert len(fragments) == 2
        assert fragments[0].requires_unnest is True
        assert fragments[1].requires_unnest is True
        assert fragments[1].metadata["array_column"].startswith("json_extract(name_item")
        assert "$.given[*]" in fragments[1].metadata["array_column"]
        assert fragments[1].metadata["source_path"] == "$.name.given"
        assert fragments[1].metadata["result_alias"] == "given_item"
        assert fragments[1].metadata["unnest_level"] == 2
        assert fragments[1].metadata["projection_expression"] == "given_item.unnest"

    def test_array_then_scalar_generates_scalar_fragment(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        parser = FHIRPathParser()
        ast = parser.parse("Patient.name.family".get_ast())

        fragments = translator.translate(ast)

        assert len(fragments) == 2
        assert fragments[0].requires_unnest is True
        assert fragments[0].metadata["source_path"] == "$.name"
        assert fragments[1].requires_unnest is False
        assert "json_extract_string(name_item, '$.family')" in fragments[1].expression

    def test_address_line_nested_arrays_metadata(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        parser = FHIRPathParser()
        ast = parser.parse("Patient.address.line".get_ast())

        fragments = translator.translate(ast)

        assert len(fragments) == 2
        first, second = fragments
        assert first.metadata["array_column"] == "json_extract(resource, '$.address[*]')"
        assert first.metadata["result_alias"] == "address_item"
        assert first.metadata["unnest_level"] == 1
        assert second.metadata["array_column"].startswith("json_extract(address_item")
        assert "$.line[*]" in second.metadata["array_column"]
        assert second.metadata["result_alias"] == "line_item"
        assert second.metadata["source_path"] == "$.address.line"
        assert second.metadata["unnest_level"] == 2
        assert second.metadata["projection_expression"] == "line_item.unnest"

    def test_array_detection_resets_between_translations(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        parser = FHIRPathParser()
        ast_name = parser.parse("Patient.name".get_ast())
        ast_telecom = parser.parse("Patient.telecom".get_ast())

        fragments_first = translator.translate(ast_name)
        fragments_second = translator.translate(ast_telecom)

        assert len(fragments_first) == 1
        assert len(fragments_second) == 1
        assert fragments_second[0].metadata["result_alias"] == "telecom_item"

    def test_structure_loader_absent_treats_path_as_scalar(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        translator._structure_loader = None  # Simulate missing definitions
        node = IdentifierNode(node_type="identifier", text="name", identifier="name")

        fragment = translator.visit_identifier(node)

        assert fragment.requires_unnest is False
        assert fragment.metadata == {}

    def test_aliases_unique_for_repeated_array_components(self, dialect, monkeypatch):
        translator = ASTToSQLTranslator(dialect, "Patient")

        def always_array(*_args, **_kwargs):
            return True

        monkeypatch.setattr(translator, "_structure_loader", MagicMock())
        translator._structure_loader.is_array_element.side_effect = always_array  # type: ignore[attr-defined]
        translator.element_type_resolver.resolve_element_type = MagicMock(return_value="HumanName")  # type: ignore[assignment]

        node = IdentifierNode(node_type="identifier", text="name.name", identifier="name.name")
        translator.visit_identifier(node)

        aliases = [
            fragment.metadata["result_alias"]
            for fragment in translator.fragments
            if fragment.requires_unnest
        ]

        assert aliases[0] == "name_item"
        assert aliases[1] != "name_item"

    def test_array_fragment_appended_before_scalar_fragment(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        node = IdentifierNode(node_type="identifier", text="name.family", identifier="name.family")

        translator.visit_identifier(node)

        assert len(translator.fragments) == 2
        assert translator.fragments[0].requires_unnest is True
        assert translator.fragments[1].requires_unnest is False

    def test_nested_array_array_column_uses_alias(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        node = IdentifierNode(node_type="identifier", text="name.given", identifier="name.given")

        translator.visit_identifier(node)

        assert len(translator.fragments) == 2
        second_fragment = translator.fragments[1]
        assert "name_item" in second_fragment.metadata["array_column"]
        assert "[*]" in second_fragment.metadata["array_column"]

    def test_multiple_array_paths_do_not_reuse_aliases(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")

        parser = FHIRPathParser()
        name_fragments = list(
            translator.translate(
                parser.parse("Patient.name".get_ast())
            )
        )
        identifier_fragments = list(
            translator.translate(
                parser.parse("Patient.identifier".get_ast())
            )
        )

        name_aliases = {
            fragment.metadata["result_alias"]
            for fragment in name_fragments
            if fragment.requires_unnest
        }
        identifier_aliases = {
            fragment.metadata["result_alias"]
            for fragment in identifier_fragments
            if fragment.requires_unnest
        }

        assert "name_item" in name_aliases
        assert "identifier_item" in identifier_aliases

    def test_nested_array_final_fragment_expression_contains_alias(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        parser = FHIRPathParser()
        ast = parser.parse("Patient.address.city".get_ast())

        fragments = translator.translate(ast)

        assert fragments[-1].requires_unnest is False
        assert "address_item" in fragments[-1].expression

    def test_array_metadata_includes_source_path(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        node = IdentifierNode(node_type="identifier", text="telecom", identifier="telecom")

        fragment = translator.visit_identifier(node)

        assert fragment.metadata["source_path"] == "$.telecom"
        assert fragment.metadata["unnest_level"] == 1

    def test_nested_array_metadata_levels_increment(self, dialect):
        translator = ASTToSQLTranslator(dialect, "Patient")
        parser = FHIRPathParser()
        ast = parser.parse("Patient.name.given".get_ast())

        fragments = translator.translate(ast)

        assert fragments[0].metadata["unnest_level"] == 1
        assert fragments[1].metadata["unnest_level"] == 2


class TestVisitIdentifierDialectCompatibility:
    """Test visit_identifier works correctly with different dialects"""

    def test_visit_identifier_duckdb_syntax(self):
        """Test identifier translation generates correct DuckDB syntax"""
        from fhir4ds.dialects.duckdb import DuckDBDialect

        dialect = DuckDBDialect(database=":memory:")
        translator = ASTToSQLTranslator(dialect, "Patient")

        node = IdentifierNode(
            node_type="identifier",
            text="name",
            identifier="name"
        )

        fragment = translator.visit_identifier(node)

        # Array navigation uses json_extract to preserve JSON structure for UNNEST
        assert fragment.expression == "json_extract(resource, '$.name[*]')"
        assert fragment.requires_unnest is True
        assert fragment.metadata["result_alias"] == "name_item"

    def test_visit_identifier_postgresql_syntax(self):
        """Test identifier translation generates correct PostgreSQL syntax"""
        from fhir4ds.dialects.postgresql import PostgreSQLDialect

        # Use a test connection string
        connection_string = "postgresql://postgres:postgres@localhost:5432/postgres"

        try:
            dialect = PostgreSQLDialect(connection_string)
            translator = ASTToSQLTranslator(dialect, "Patient")

            node = IdentifierNode(
                node_type="identifier",
                text="name",
                identifier="name"
            )

            fragment = translator.visit_identifier(node)

            # PostgreSQL uses jsonb_extract_path_text
            assert "jsonb_extract_path_text" in fragment.expression
            assert "resource" in fragment.expression
            # PostgreSQL uses separate path arguments
            assert "'name'" in fragment.expression

        except Exception as e:
            # PostgreSQL might not be available in test environment
            pytest.skip(f"PostgreSQL not available: {e}")

    @pytest.mark.parametrize("dialect_class,expected_function", [
        ("DuckDBDialect", "json_extract_string"),
    ])
    def test_visit_identifier_dialect_specific_functions(self, dialect_class, expected_function):
        """Test that correct dialect-specific functions are used"""
        if dialect_class == "DuckDBDialect":
            from fhir4ds.dialects.duckdb import DuckDBDialect
            dialect = DuckDBDialect(database=":memory:")
        else:
            pytest.skip(f"Dialect {dialect_class} not available")

        translator = ASTToSQLTranslator(dialect, "Patient")

        node = IdentifierNode(
            node_type="identifier",
            text="birthDate",
            identifier="birthDate"
        )

        fragment = translator.visit_identifier(node)

        assert expected_function in fragment.expression


class TestIdentifierValidation:
    """Tests for identifier validation and escaped identifier handling."""

    def test_invalid_relative_path_detected_during_parsing(self):
        parser = FHIRPathParser()
        with pytest.raises(FHIRPathParseError) as excinfo:
            parser.parse("name.givn", context={"resourceType": "Patient"})

        message = str(excinfo.value)
        assert "Unknown element 'givn'" in message
        assert "HumanName" in message

    def test_escaped_identifier_translates_successfully(self, dialect):
        parser = FHIRPathParser()
        parsed = parser.parse("name.`given`", context={"resourceType": "Patient"})
        ast = parsed.get_ast()
        translator = ASTToSQLTranslator(dialect, "Patient")

        fragments = translator.translate(ast)
        assert len(fragments) >= 2
        assert "given" in fragments[-1].expression


class _StringConcatCaptureDialect:
    """Minimal dialect stub to capture string concatenation operands."""

    def __init__(self):
        self.cast_calls = []
        self.concat_args = None

    def string_concat(self, left: str, right: str) -> str:
        self.concat_args = (left, right)
        return f"({left} || {right})"

    def generate_type_cast(self, expression: str, target_type: str) -> str:
        self.cast_calls.append((expression, target_type))
        return f"CAST_TO_STRING({expression})"


class TestVisitOperatorImplementation:
    """Test visit_operator() implementation for all operator types"""

    def test_visit_operator_comparison_equals(self, dialect):
        """Test translating equality operator (=)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Create operands
        left_node = LiteralNode(
            node_type="literal",
            text="'John'",
            value="John",
            literal_type="string"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="'Doe'",
            value="Doe",
            literal_type="string"
        )

        # Create operator node
        node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="comparison"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert isinstance(fragment, SQLFragment)
        assert "=" in fragment.expression
        assert "'John'" in fragment.expression
        assert "'Doe'" in fragment.expression
        assert not fragment.is_aggregate

    def test_visit_operator_comparison_not_equals(self, dialect):
        """Test translating not equals operator (!=)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="42",
            value=42,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="100",
            value=100,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="!=",
            operator="!=",
            operator_type="comparison"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "!=" in fragment.expression
        assert "42" in fragment.expression
        assert "100" in fragment.expression

    def test_visit_operator_comparison_less_than(self, dialect):
        """Test translating less than operator (<)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="10",
            value=10,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="20",
            value=20,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="<",
            operator="<",
            operator_type="comparison"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "<" in fragment.expression
        assert "10" in fragment.expression
        assert "20" in fragment.expression

    def test_visit_operator_comparison_greater_than(self, dialect):
        """Test translating greater than operator (>)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="100",
            value=100,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="50",
            value=50,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text=">",
            operator=">",
            operator_type="comparison"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert ">" in fragment.expression
        assert "100" in fragment.expression
        assert "50" in fragment.expression

    def test_visit_operator_comparison_less_or_equal(self, dialect):
        """Test translating less than or equal operator (<=)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="10",
            value=10,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="<=",
            operator="<=",
            operator_type="comparison"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "<=" in fragment.expression
        assert "5" in fragment.expression
        assert "10" in fragment.expression

    def test_visit_operator_comparison_greater_or_equal(self, dialect):
        """Test translating greater than or equal operator (>=)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="15",
            value=15,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="10",
            value=10,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text=">=",
            operator=">=",
            operator_type="comparison"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert ">=" in fragment.expression
        assert "15" in fragment.expression
        assert "10" in fragment.expression

    def test_visit_operator_union_generates_union_all(self, dialect):
        """Test translating union operator (|) preserves ordering and collection metadata."""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="1",
            value=1,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="2",
            value=2,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="|",
            operator="|",
            operator_type="union"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "UNION ALL" in fragment.expression
        assert "COALESCE" in fragment.expression
        assert fragment.metadata.get("operator") == "union"
        assert fragment.metadata.get("is_collection") is True

    def test_visit_operator_logical_and(self, dialect):
        """Test translating AND logical operator"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="true",
            value=True,
            literal_type="boolean"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="false",
            value=False,
            literal_type="boolean"
        )

        node = OperatorNode(
            node_type="operator",
            text="and",
            operator="and",
            operator_type="logical"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "AND" in fragment.expression.upper()
        assert "TRUE" in fragment.expression
        assert "FALSE" in fragment.expression

    def test_visit_operator_logical_or(self, dialect):
        """Test translating OR logical operator"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="true",
            value=True,
            literal_type="boolean"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="false",
            value=False,
            literal_type="boolean"
        )

        node = OperatorNode(
            node_type="operator",
            text="or",
            operator="or",
            operator_type="logical"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "OR" in fragment.expression.upper()
        assert "TRUE" in fragment.expression
        assert "FALSE" in fragment.expression

    def test_visit_operator_arithmetic_addition(self, dialect):
        """Test translating addition operator (+)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="10",
            value=10,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="+",
            operator="+",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "+" in fragment.expression
        assert "10" in fragment.expression
        assert "5" in fragment.expression

    def test_visit_operator_arithmetic_subtraction(self, dialect):
        """Test translating subtraction operator (-)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="20",
            value=20,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="7",
            value=7,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="-",
            operator="-",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "-" in fragment.expression
        assert "20" in fragment.expression
        assert "7" in fragment.expression

    def test_visit_operator_arithmetic_multiplication(self, dialect):
        """Test translating multiplication operator (*)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="6",
            value=6,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="7",
            value=7,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="*",
            operator="*",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "*" in fragment.expression
        assert "6" in fragment.expression
        assert "7" in fragment.expression

    def test_visit_operator_arithmetic_division(self, dialect):
        """Test translating division operator (/)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="100",
            value=100,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="/",
            operator="/",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "/" in fragment.expression
        assert "100" in fragment.expression
        assert "5" in fragment.expression

    def test_visit_operator_string_concatenation(self, dialect):
        """Test translating string concatenation operator (&)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="'Hello'",
            value="Hello",
            literal_type="string"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="'World'",
            value="World",
            literal_type="string"
        )

        node = OperatorNode(
            node_type="operator",
            text="&",
            operator="&",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "||" in fragment.expression
        assert fragment.expression.count("COALESCE") == 2
        assert "'Hello'" in fragment.expression
        assert "'World'" in fragment.expression

    def test_visit_operator_string_concatenation_normalizes_operands(self):
        """Ensure concatenation coerces operands to strings and handles NULL conversion."""
        dialect = _StringConcatCaptureDialect()
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="'Hello'",
            value="Hello",
            literal_type="string"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="&",
            operator="&",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert fragment.expression.count("COALESCE") == 2
        assert "CAST_TO_STRING('Hello')" in fragment.expression
        assert "CAST_TO_STRING(5)" in fragment.expression
        assert dialect.concat_args is not None
        left_arg, right_arg = dialect.concat_args
        assert left_arg.startswith("COALESCE")
        assert right_arg.startswith("COALESCE")
        assert dialect.cast_calls == [
            ("'Hello'", "String"),
            ("5", "String")
        ]

    @pytest.mark.parametrize("dialect_fixture", ["dialect", "postgresql_dialect"])
    def test_visit_operator_division_uses_nullif_guard(self, request, dialect_fixture):
        """Division should guard against zero denominators using NULLIF."""
        dialect_instance = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect_instance, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="10",
            value=10,
            literal_type="integer"
        )
        left_node.children = []

        right_node = LiteralNode(
            node_type="literal",
            text="2",
            value=2,
            literal_type="integer"
        )
        right_node.children = []

        node = OperatorNode(
            node_type="operator",
            text="/",
            operator="/",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        expression = fragment.expression.upper()
        assert "NULLIF(" in expression or "= 0 THEN NULL" in expression
        assert (
            "/ NULLIF(" in fragment.expression
            or ("WHEN (" in expression and ") = 0 THEN NULL" in expression)
        )

    @pytest.mark.parametrize("dialect_fixture", ["dialect", "postgresql_dialect"])
    def test_visit_operator_integer_division_casts_and_guards(self, request, dialect_fixture):
        """div operator should cast result to integer and guard denominator."""
        dialect_instance = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect_instance, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="10",
            value=10,
            literal_type="integer"
        )
        left_node.children = []

        right_node = LiteralNode(
            node_type="literal",
            text="3",
            value=3,
            literal_type="integer"
        )
        right_node.children = []

        node = OperatorNode(
            node_type="operator",
            text="div",
            operator="div",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        expression = fragment.expression.upper()
        assert "CAST(" in expression
        assert "AS INTEGER" in expression or "AS BIGINT" in expression
        assert (
            "/ NULLIF(" in expression
            or ("WHEN (" in expression and ") = 0 THEN NULL" in expression)
        )

    @pytest.mark.parametrize("dialect_fixture", ["dialect", "postgresql_dialect"])
    def test_visit_operator_modulo_uses_nullif_guard(self, request, dialect_fixture):
        """Modulo should also guard against zero denominators."""
        dialect_instance = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect_instance, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="10",
            value=10,
            literal_type="integer"
        )
        left_node.children = []

        right_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )
        right_node.children = []

        node = OperatorNode(
            node_type="operator",
            text="mod",
            operator="mod",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        expression = fragment.expression.upper()
        assert "% NULLIF(" in expression or ("WHEN (" in expression and ") = 0 THEN NULL" in expression)

    def test_visit_operator_arithmetic_modulo(self, dialect):
        """Test translating modulo operator (mod)"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="17",
            value=17,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="mod",
            operator="mod",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert "%" in fragment.expression
        assert "17" in fragment.expression
        assert "5" in fragment.expression

    def test_visit_operator_temporal_minus_quantity_generates_interval(self, dialect):
        """Temporal subtraction should emit SQL interval arithmetic."""
        translator = ASTToSQLTranslator(dialect, "Patient")

        date_literal = LiteralNode(
            node_type="literal",
            text="@1974-12-25",
            value="1974-12-25"
        )
        date_literal.literal_type = "date"
        quantity_literal = LiteralNode(
            node_type="literal",
            text="1 'month'",
            value="1 'month'",
            literal_type="string"
        )

        operator_node = OperatorNode(
            node_type="operator",
            text="-",
            operator="-"
        )
        operator_node.add_child(date_literal)
        operator_node.add_child(quantity_literal)

        fragment = translator.visit_operator(operator_node)

        normalized_sql = fragment.expression.replace(" ", "").upper()
        assert "CAST((" in normalized_sql
        assert "DATE'1974-12-25'" in normalized_sql
        assert "INTERVAL'1MONTH'" in normalized_sql
        assert "ASDATE" in normalized_sql

    def test_translate_round_on_division_expression_preserves_operand(self, dialect):
        """round() invoked on arithmetic expression should include the operand SQL."""
        parser = FHIRPathParser()
        enhanced_ast = parser.parse("(1.2 / 1.8).round(2) = 0.67").get_ast()
        ast = enhanced_ast

        translator = ASTToSQLTranslator(dialect, "Patient")
        fragments = translator.translate(ast)

        assert fragments, "Translator should return at least one fragment"
        final_sql = fragments[-1].expression.replace(" ", "").lower()

        assert final_sql.startswith("(")
        assert "round((" in final_sql
        assert "/(1.8)" in final_sql
        assert "casewhen" in final_sql or "nullif" in final_sql
        assert "=0.67" in final_sql

    def test_visit_operator_unary_not(self, dialect):
        """Test translating unary NOT operator"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        operand_node = LiteralNode(
            node_type="literal",
            text="true",
            value=True,
            literal_type="boolean"
        )

        node = OperatorNode(
            node_type="operator",
            text="not",
            operator="not",
            operator_type="unary"
        )
        node.children = [operand_node]

        fragment = translator.visit_operator(node)

        assert "NOT" in fragment.expression
        assert "TRUE" in fragment.expression

    def test_visit_operator_unary_minus(self, dialect):
        """Test translating unary minus operator"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        operand_node = LiteralNode(
            node_type="literal",
            text="42",
            value=42,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="-",
            operator="-",
            operator_type="unary"
        )
        node.children = [operand_node]
        # Re-classify after adding children to ensure proper type detection
        node._classify_operator()

        fragment = translator.visit_operator(node)

        assert "- 42" in fragment.expression.replace("(", "").replace(")", "")

    def test_visit_operator_with_identifier_operands(self, dialect):
        """Test operator with identifier operands"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Left: Patient.age
        left_node = IdentifierNode(
            node_type="identifier",
            text="age",
            identifier="age"
        )

        # Right: 18
        right_node = LiteralNode(
            node_type="literal",
            text="18",
            value=18,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text=">=",
            operator=">=",
            operator_type="comparison"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert ">=" in fragment.expression
        assert "json_extract" in fragment.expression  # From identifier
        assert "18" in fragment.expression

    def test_visit_operator_nested_operators(self, dialect):
        """Test nested operator expressions"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Create (5 + 3)
        inner_left = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )
        inner_right = LiteralNode(
            node_type="literal",
            text="3",
            value=3,
            literal_type="integer"
        )
        inner_op = OperatorNode(
            node_type="operator",
            text="+",
            operator="+",
            operator_type="binary"
        )
        inner_op.children = [inner_left, inner_right]

        # Create (5 + 3) * 2
        outer_right = LiteralNode(
            node_type="literal",
            text="2",
            value=2,
            literal_type="integer"
        )
        outer_op = OperatorNode(
            node_type="operator",
            text="*",
            operator="*",
            operator_type="binary"
        )
        outer_op.children = [inner_op, outer_right]

        fragment = translator.visit_operator(outer_op)

        # Should contain both operations
        assert "*" in fragment.expression
        assert "+" in fragment.expression
        assert "5" in fragment.expression
        assert "3" in fragment.expression
        assert "2" in fragment.expression

    def test_visit_operator_preserves_fragment_flags(self, dialect):
        """Test that operator preserves requires_unnest and is_aggregate flags"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="1",
            value=1,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="2",
            value=2,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="+",
            operator="+",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        # Literals don't require unnest or aggregate
        assert not fragment.requires_unnest
        assert not fragment.is_aggregate

    def test_visit_operator_unknown_operator_raises_error(self, dialect):
        """Test that unknown operator raises ValueError"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="1",
            value=1,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="2",
            value=2,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="???",
            operator="???",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        with pytest.raises(ValueError) as exc_info:
            translator.visit_operator(node)

        assert "Unknown binary operator" in str(exc_info.value)

    def test_visit_operator_invalid_operand_count_raises_error(self, dialect):
        """Test that invalid operand count raises ValueError"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Binary operator with only one child (invalid)
        node = OperatorNode(
            node_type="operator",
            text="=",
            operator="=",
            operator_type="binary"
        )
        node.children = [LiteralNode(
            node_type="literal",
            text="1",
            value=1,
            literal_type="integer"
        )]

        with pytest.raises(ValueError) as exc_info:
            translator.visit_operator(node)

        assert "requires exactly 2 operands" in str(exc_info.value)

    @pytest.mark.parametrize("operator,expected_sql", [
        ("=", "="),
        ("!=", "!="),
        ("<", "<"),
        (">", ">"),
        ("<=", "<="),
        (">=", ">="),
        ("+", "+"),
        ("-", "-"),
        ("*", "*"),
        ("/", "/"),
    ])
    def test_visit_operator_parametrized(self, dialect, operator, expected_sql):
        """Test various operators with parametrized inputs"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="10",
            value=10,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text=operator,
            operator=operator,
            operator_type="binary" if operator in ["+", "-", "*", "/"] else "comparison"
        )
        node.children = [left_node, right_node]

        fragment = translator.visit_operator(node)

        assert expected_sql in fragment.expression

    def test_visit_operator_logging(self, dialect):
        """Test that operator translation logs activity"""
        translator = ASTToSQLTranslator(dialect, "Patient")

        left_node = LiteralNode(
            node_type="literal",
            text="1",
            value=1,
            literal_type="integer"
        )
        right_node = LiteralNode(
            node_type="literal",
            text="2",
            value=2,
            literal_type="integer"
        )

        node = OperatorNode(
            node_type="operator",
            text="+",
            operator="+",
            operator_type="binary"
        )
        node.children = [left_node, right_node]

        with patch('fhir4ds.fhirpath.sql.translator.logger') as mock_logger:
            translator.visit_operator(node)

            # Should log operator translation
            assert mock_logger.debug.call_count >= 2
