"""
Tests for FHIRPath AST Node Types

Tests the strongly-typed AST nodes and their validation capabilities,
ensuring proper node construction, metadata handling, and relationships.
"""

import pytest
from unittest.mock import Mock, patch
from typing import List

from fhir4ds.fhirpath.ast.nodes import (
    FHIRPathASTNode, LiteralNode, IdentifierNode, FunctionCallNode,
    OperatorNode, ConditionalNode, AggregationNode, TypeOperationNode,
    NodeTypeFactory
)
from fhir4ds.fhirpath.parser_core.ast_extensions import EnhancedASTNode
from fhir4ds.fhirpath.parser_core.metadata_types import (
    ASTNodeMetadata, NodeCategory, OptimizationHint, SQLDataType,
    MetadataBuilder, TypeInformation
)


class TestFHIRPathASTNode:
    """Test the base FHIRPathASTNode class"""

    def test_initialization(self):
        """Test basic node initialization"""
        node = LiteralNode("literal", "test")
        assert node.node_type == "literal"
        assert node.text == "test"
        assert node.children == []
        assert node.parent is None
        assert not node._is_validated
        assert node._validation_errors == []

    def test_add_child(self):
        """Test adding child nodes"""
        parent = LiteralNode("literal", "parent")
        child = LiteralNode("literal", "child")

        parent.add_child(child)

        assert len(parent.children) == 1
        assert parent.children[0] == child
        assert child.parent == parent

    def test_remove_child(self):
        """Test removing child nodes"""
        parent = LiteralNode("literal", "parent")
        child = LiteralNode("literal", "child")

        parent.add_child(child)
        parent.remove_child(child)

        assert len(parent.children) == 0
        assert child.parent is None

    def test_get_root(self):
        """Test finding root node"""
        root = LiteralNode("literal", "root")
        child1 = LiteralNode("literal", "child1")
        child2 = LiteralNode("literal", "child2")

        root.add_child(child1)
        child1.add_child(child2)

        assert child2.get_root() == root
        assert child1.get_root() == root
        assert root.get_root() == root

    def test_get_depth(self):
        """Test calculating node depth"""
        root = LiteralNode("literal", "root")
        child1 = LiteralNode("literal", "child1")
        child2 = LiteralNode("literal", "child2")

        root.add_child(child1)
        child1.add_child(child2)

        assert root.get_depth() == 0
        assert child1.get_depth() == 1
        assert child2.get_depth() == 2

    def test_find_nodes_by_type(self):
        """Test finding nodes by type"""
        root = LiteralNode("literal", "root")
        child1 = IdentifierNode("identifier", "child1")
        child2 = LiteralNode("literal", "child2")

        root.add_child(child1)
        root.add_child(child2)

        literal_nodes = root.find_nodes_by_type("literal")
        assert len(literal_nodes) == 2
        assert root in literal_nodes
        assert child2 in literal_nodes

        identifier_nodes = root.find_nodes_by_type("identifier")
        assert len(identifier_nodes) == 1
        assert child1 in identifier_nodes

    def test_validation_error_handling(self):
        """Test validation error handling"""
        node = LiteralNode("literal", "test")

        assert len(node.get_validation_errors()) == 0
        assert not node.is_valid()

        node.add_validation_error("Test error")
        assert len(node.get_validation_errors()) == 1
        assert "Test error" in node.get_validation_errors()

        node.clear_validation_errors()
        assert len(node.get_validation_errors()) == 0


class TestLiteralNode:
    """Test LiteralNode functionality"""

    def test_literal_node_creation(self):
        """Test literal node creation with different value types"""
        # String literal
        string_node = LiteralNode("literal", "test", value="hello")
        assert string_node.value == "hello"
        assert string_node.literal_type == "string"

        # Integer literal
        int_node = LiteralNode("literal", "42", value=42)
        assert int_node.value == 42
        assert int_node.literal_type == "integer"

        # Boolean literal
        bool_node = LiteralNode("literal", "true", value=True)
        assert bool_node.value is True
        assert bool_node.literal_type == "boolean"

        # Float literal
        float_node = LiteralNode("literal", "3.14", value=3.14)
        assert float_node.value == 3.14
        assert float_node.literal_type == "decimal"

    def test_literal_type_inference(self):
        """Test automatic literal type inference"""
        node = LiteralNode("literal", "test")

        node.value = "string"
        node._infer_literal_type()
        assert node.literal_type == "string"

        node.value = 42
        node._infer_literal_type()
        assert node.literal_type == "integer"

        node.value = True
        node._infer_literal_type()
        assert node.literal_type == "boolean"

        node.value = 3.14
        node._infer_literal_type()
        assert node.literal_type == "decimal"

    def test_literal_validation(self):
        """Test literal node validation"""
        # Valid literal with value
        node = LiteralNode("literal", "test", value="hello")
        assert node.validate()
        assert node.is_valid()

        # Valid empty literal
        empty_node = LiteralNode("literal", "{}")
        assert empty_node.validate()

        # Invalid literal without value
        invalid_node = LiteralNode("literal", "test")
        invalid_node.value = None
        assert not invalid_node.validate()
        assert len(invalid_node.get_validation_errors()) > 0

    def test_literal_visitor_pattern(self):
        """Test literal node visitor pattern"""
        node = LiteralNode("literal", "test", value="hello")

        # Mock visitor
        visitor = Mock()
        visitor.visit_literal.return_value = "visited"

        result = node.accept(visitor)
        visitor.visit_literal.assert_called_once_with(node)
        assert result == "visited"


class TestIdentifierNode:
    """Test IdentifierNode functionality"""

    def test_identifier_creation(self):
        """Test identifier node creation"""
        node = IdentifierNode("identifier", "Patient.name")
        assert node.identifier == "Patient.name"
        assert not node.is_qualified

        qualified_node = IdentifierNode("identifier", "qualified", identifier="Patient.name", is_qualified=True)
        assert qualified_node.identifier == "Patient.name"
        assert qualified_node.is_qualified

    def test_identifier_validation(self):
        """Test identifier validation"""
        # Valid identifier
        valid_node = IdentifierNode("identifier", "Patient")
        valid_node.identifier = "Patient"
        assert valid_node.validate()

        # Valid identifier with underscore
        underscore_node = IdentifierNode("identifier", "patient_name")
        underscore_node.identifier = "patient_name"
        assert underscore_node.validate()

        # Valid qualified identifier
        qualified_node = IdentifierNode("identifier", "Patient.name")
        qualified_node.identifier = "Patient.name"
        assert qualified_node.validate()

        # Invalid empty identifier
        empty_node = IdentifierNode("identifier", "")
        empty_node.identifier = ""
        assert not empty_node.validate()

        # Invalid identifier with spaces
        invalid_node = IdentifierNode("identifier", "invalid identifier")
        invalid_node.identifier = "invalid identifier"
        assert not invalid_node.validate()

    def test_identifier_visitor_pattern(self):
        """Test identifier node visitor pattern"""
        node = IdentifierNode("identifier", "Patient")

        visitor = Mock()
        visitor.visit_identifier.return_value = "visited"

        result = node.accept(visitor)
        visitor.visit_identifier.assert_called_once_with(node)
        assert result == "visited"


class TestFunctionCallNode:
    """Test FunctionCallNode functionality"""

    def test_function_call_creation(self):
        """Test function call node creation"""
        node = FunctionCallNode("functionCall", "count()")
        assert node.function_name == "count"
        assert node.arguments == []

        # With explicit function name
        named_node = FunctionCallNode("functionCall", "where(condition)", function_name="where")
        assert named_node.function_name == "where"

    def test_function_name_extraction(self):
        """Test function name extraction from text"""
        node = FunctionCallNode("functionCall", "where(Patient.active = true)")
        assert node.function_name == "where"

        simple_node = FunctionCallNode("functionCall", "count")
        assert simple_node.function_name == "count"

    def test_function_validation(self):
        """Test function call validation"""
        # Valid function
        valid_node = FunctionCallNode("functionCall", "count()")
        valid_node.function_name = "count"
        assert valid_node.validate()

        # Invalid empty function name
        empty_node = FunctionCallNode("functionCall", "")
        empty_node.function_name = ""
        assert not empty_node.validate()

        # Invalid function name with special characters
        invalid_node = FunctionCallNode("functionCall", "invalid-function")
        invalid_node.function_name = "invalid-function"
        assert not invalid_node.validate()

    def test_function_visitor_pattern(self):
        """Test function call visitor pattern"""
        node = FunctionCallNode("functionCall", "count()")

        visitor = Mock()
        visitor.visit_function_call.return_value = "visited"

        result = node.accept(visitor)
        visitor.visit_function_call.assert_called_once_with(node)
        assert result == "visited"


class TestOperatorNode:
    """Test OperatorNode functionality"""

    def test_operator_creation(self):
        """Test operator node creation"""
        node = OperatorNode("operator", "=")
        assert node.operator == "="
        assert node.operator_type in ["comparison", "binary"]

    def test_operator_classification(self):
        """Test operator type classification"""
        comparison_node = OperatorNode("operator", "=")
        assert comparison_node.operator_type == "comparison"

        logical_node = OperatorNode("operator", "and")
        assert logical_node.operator_type == "logical"

        unary_node = OperatorNode("operator", "not")
        assert unary_node.operator_type == "unary"

    def test_operator_validation(self):
        """Test operator validation"""
        # Valid binary operator with two children
        binary_node = OperatorNode("operator", "=")
        binary_node.operator_type = "binary"
        child1 = LiteralNode("literal", "1", value=1)
        child2 = LiteralNode("literal", "2", value=2)
        binary_node.add_child(child1)
        binary_node.add_child(child2)
        assert binary_node.validate()

        # Invalid binary operator with wrong number of children
        invalid_binary = OperatorNode("operator", "=")
        invalid_binary.operator_type = "binary"
        invalid_binary.add_child(LiteralNode("literal", "1", value=1))
        assert not invalid_binary.validate()

        # Valid unary operator with one child
        unary_node = OperatorNode("operator", "not")
        unary_node.operator_type = "unary"
        unary_node.add_child(LiteralNode("literal", "true", value=True))
        assert unary_node.validate()

    def test_operator_visitor_pattern(self):
        """Test operator node visitor pattern"""
        node = OperatorNode("operator", "=")

        visitor = Mock()
        visitor.visit_operator.return_value = "visited"

        result = node.accept(visitor)
        visitor.visit_operator.assert_called_once_with(node)
        assert result == "visited"


class TestConditionalNode:
    """Test ConditionalNode functionality"""

    def test_conditional_creation(self):
        """Test conditional node creation"""
        node = ConditionalNode("conditional", "where(condition)")
        assert node.condition_type == "where"

        select_node = ConditionalNode("conditional", "select(expression)")
        assert select_node.condition_type == "select"

    def test_conditional_validation(self):
        """Test conditional validation"""
        # Valid where with condition
        where_node = ConditionalNode("conditional", "where")
        where_node.condition_type = "where"
        where_node.add_child(LiteralNode("literal", "true", value=True))
        assert where_node.validate()

        # Invalid where without condition
        empty_where = ConditionalNode("conditional", "where")
        empty_where.condition_type = "where"
        assert not empty_where.validate()

    def test_conditional_visitor_pattern(self):
        """Test conditional node visitor pattern"""
        node = ConditionalNode("conditional", "where")

        visitor = Mock()
        visitor.visit_conditional.return_value = "visited"

        result = node.accept(visitor)
        visitor.visit_conditional.assert_called_once_with(node)
        assert result == "visited"


class TestAggregationNode:
    """Test AggregationNode functionality"""

    def test_aggregation_creation(self):
        """Test aggregation node creation"""
        node = AggregationNode("aggregation", "count()")
        assert node.aggregation_function == "count"
        assert node.aggregation_type == "count"

        sum_node = AggregationNode("aggregation", "sum(value)")
        assert sum_node.aggregation_function == "sum"
        assert sum_node.aggregation_type == "sum"

    def test_aggregation_validation(self):
        """Test aggregation validation"""
        # Valid aggregation function
        valid_node = AggregationNode("aggregation", "count()")
        assert valid_node.validate()

        # Invalid aggregation function
        invalid_node = AggregationNode("aggregation", "invalid()")
        invalid_node.aggregation_function = "invalid"
        invalid_node.aggregation_type = "invalid"
        assert not invalid_node.validate()

    def test_aggregation_visitor_pattern(self):
        """Test aggregation node visitor pattern"""
        node = AggregationNode("aggregation", "count()")

        visitor = Mock()
        visitor.visit_aggregation.return_value = "visited"

        result = node.accept(visitor)
        visitor.visit_aggregation.assert_called_once_with(node)
        assert result == "visited"


class TestTypeOperationNode:
    """Test TypeOperationNode functionality"""

    def test_type_operation_creation(self):
        """Test type operation node creation"""
        as_node = TypeOperationNode("typeOperation", "Patient as Patient")
        assert as_node.operation == "as"
        assert as_node.target_type == "Patient"

        is_node = TypeOperationNode("typeOperation", "value is Patient")
        assert is_node.operation == "is"
        assert is_node.target_type == "Patient"

        oftype_node = TypeOperationNode("typeOperation", "ofType(Patient)")
        assert oftype_node.operation == "ofType"
        assert oftype_node.target_type == "Patient"

    def test_type_operation_validation(self):
        """Test type operation validation"""
        # Valid type operation
        valid_node = TypeOperationNode("typeOperation", "Patient as Patient")
        assert valid_node.validate()

        # Invalid operation
        invalid_node = TypeOperationNode("typeOperation", "invalid operation")
        invalid_node.operation = "invalid"
        invalid_node.target_type = ""
        assert not invalid_node.validate()

    def test_type_operation_visitor_pattern(self):
        """Test type operation visitor pattern"""
        node = TypeOperationNode("typeOperation", "Patient as Patient")

        visitor = Mock()
        visitor.visit_type_operation.return_value = "visited"

        result = node.accept(visitor)
        visitor.visit_type_operation.assert_called_once_with(node)
        assert result == "visited"


class TestNodeTypeFactory:
    """Test NodeTypeFactory functionality"""

    def test_create_literal_node_from_enhanced(self):
        """Test creating literal node from enhanced AST"""
        # Create mock enhanced node
        enhanced_node = Mock(spec=EnhancedASTNode)
        enhanced_node.node_type = "literal"
        enhanced_node.text = "42"
        enhanced_node.metadata = None
        enhanced_node.parent = None
        enhanced_node.sql_fragment = None
        enhanced_node.cte_name = None
        enhanced_node.dependencies = []
        enhanced_node.children = []

        result = NodeTypeFactory.create_node_from_enhanced(enhanced_node)
        assert isinstance(result, LiteralNode)
        assert result.node_type == "literal"
        assert result.text == "42"

    def test_create_function_node_from_enhanced(self):
        """Test creating function node from enhanced AST"""
        enhanced_node = Mock(spec=EnhancedASTNode)
        enhanced_node.node_type = "functionCall"
        enhanced_node.text = "empty()"  # Use non-aggregation, non-conditional function
        enhanced_node.metadata = None
        enhanced_node.parent = None
        enhanced_node.sql_fragment = None
        enhanced_node.cte_name = None
        enhanced_node.dependencies = []
        enhanced_node.children = []

        result = NodeTypeFactory.create_node_from_enhanced(enhanced_node)
        assert isinstance(result, FunctionCallNode)
        assert result.function_name == "empty"

    def test_create_aggregation_node_from_enhanced(self):
        """Test creating aggregation node from enhanced AST for aggregation functions"""
        enhanced_node = Mock(spec=EnhancedASTNode)
        enhanced_node.node_type = "functionCall"
        enhanced_node.text = "sum(value)"
        enhanced_node.metadata = None
        enhanced_node.parent = None
        enhanced_node.sql_fragment = None
        enhanced_node.cte_name = None
        enhanced_node.dependencies = []
        enhanced_node.children = []

        result = NodeTypeFactory.create_node_from_enhanced(enhanced_node)
        assert isinstance(result, AggregationNode)
        assert result.aggregation_function == "sum"

    def test_parse_literal_value(self):
        """Test literal value parsing"""
        # Boolean values
        assert NodeTypeFactory._parse_literal_value("true") is True
        assert NodeTypeFactory._parse_literal_value("false") is False

        # String values
        assert NodeTypeFactory._parse_literal_value('"hello"') == "hello"
        assert NodeTypeFactory._parse_literal_value("'world'") == "world"

        # Numeric values
        assert NodeTypeFactory._parse_literal_value("42") == 42
        assert NodeTypeFactory._parse_literal_value("3.14") == 3.14

        # Empty/null values
        assert NodeTypeFactory._parse_literal_value("{}") is None
        assert NodeTypeFactory._parse_literal_value("null") is None

        # Default to string
        assert NodeTypeFactory._parse_literal_value("unknown") == "unknown"

    def test_is_operator(self):
        """Test operator detection"""
        assert NodeTypeFactory._is_operator("=")
        assert NodeTypeFactory._is_operator("and")
        assert NodeTypeFactory._is_operator("not")
        assert not NodeTypeFactory._is_operator("Patient")
        assert not NodeTypeFactory._is_operator("count")

    def test_classify_node_category(self):
        """Test node category classification"""
        assert NodeTypeFactory._classify_node_category("literal", "42") == NodeCategory.LITERAL
        assert NodeTypeFactory._classify_node_category("identifier", "Patient") == NodeCategory.PATH_EXPRESSION
        assert NodeTypeFactory._classify_node_category("invocation", "count()") == NodeCategory.AGGREGATION
        assert NodeTypeFactory._classify_node_category("invocation", "empty()") == NodeCategory.FUNCTION_CALL
        assert NodeTypeFactory._classify_node_category("unknown", "=") == NodeCategory.OPERATOR


if __name__ == "__main__":
    pytest.main([__file__])