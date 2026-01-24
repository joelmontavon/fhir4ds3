"""
Tests for FHIRPath AST Visitor Pattern

Tests the visitor pattern implementation for AST traversal,
including depth-first traversal, metadata extraction, validation,
and optimization analysis.
"""

import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from fhir4ds.fhirpath.ast.visitor import (
    ASTVisitor, DepthFirstTraversalVisitor, MetadataExtractionVisitor,
    ValidationVisitor, OptimizationAnalysisVisitor, create_visitor_chain
)
from fhir4ds.fhirpath.ast.nodes import (
    LiteralNode, IdentifierNode, FunctionCallNode, OperatorNode,
    ConditionalNode, AggregationNode, TypeOperationNode
)
from fhir4ds.fhirpath.parser_core.metadata_types import (
    ASTNodeMetadata, NodeCategory, OptimizationHint, SQLDataType,
    MetadataBuilder, TypeInformation, PerformanceMetadata,
    CTEGenerationContext, PopulationAnalyticsMetadata
)


class MockVisitor(ASTVisitor[str]):
    """Mock visitor for testing base visitor functionality"""

    def visit_literal(self, node):
        return f"literal:{node.text}"

    def visit_identifier(self, node):
        return f"identifier:{node.text}"

    def visit_function_call(self, node):
        return f"function:{node.text}"

    def visit_operator(self, node):
        return f"operator:{node.text}"

    def visit_conditional(self, node):
        return f"conditional:{node.text}"

    def visit_aggregation(self, node):
        return f"aggregation:{node.text}"

    def visit_type_operation(self, node):
        return f"type_op:{node.text}"


class TestASTVisitor:
    """Test the base ASTVisitor class"""

    def test_visitor_initialization(self):
        """Test visitor initialization"""
        visitor = MockVisitor()
        assert visitor._visit_count == 0
        assert visitor._error_count == 0

    def test_visit_counts_tracking(self):
        """Test that visit counts are tracked properly"""
        visitor = MockVisitor()
        node = LiteralNode("literal", "test")

        result = visitor.visit(node)
        assert visitor._visit_count == 1
        assert visitor._error_count == 0
        assert result == "literal:test"

    def test_visit_error_handling(self):
        """Test visitor error handling"""
        visitor = MockVisitor()
        # Mock a node that raises exception
        node = Mock()
        node.accept.side_effect = Exception("Test error")

        with pytest.raises(Exception):
            visitor.visit(node)

        assert visitor._error_count == 1

    def test_get_visit_stats(self):
        """Test getting visitor statistics"""
        visitor = MockVisitor()
        node = LiteralNode("literal", "test")

        visitor.visit(node)
        stats = visitor.get_visit_stats()

        assert stats["total_visits"] == 1
        assert stats["error_count"] == 0

    def test_generic_visit_not_implemented(self):
        """Test that generic visit raises NotImplementedError"""
        visitor = MockVisitor()

        # Create a custom node that doesn't match any specific visitor methods
        class CustomNode:
            def accept(self, visitor):
                return visitor.visit_generic(self)

        node = CustomNode()
        with pytest.raises(NotImplementedError):
            visitor.visit(node)


class TestDepthFirstTraversalVisitor:
    """Test DepthFirstTraversalVisitor"""

    def test_simple_traversal(self):
        """Test simple depth-first traversal"""
        visitor = DepthFirstTraversalVisitor()

        # Create simple tree
        root = LiteralNode("literal", "root")
        child1 = LiteralNode("literal", "child1")
        child2 = LiteralNode("literal", "child2")

        root.add_child(child1)
        root.add_child(child2)

        results = visitor.visit(root)

        # Should return nodes in depth-first order
        assert len(results) == 3
        assert results[0] == root
        assert child1 in results
        assert child2 in results

    def test_traversal_with_custom_processor(self):
        """Test traversal with custom node processor"""
        visitor = DepthFirstTraversalVisitor()

        def text_processor(node):
            return node.text

        visitor.set_node_processor(text_processor)

        root = LiteralNode("literal", "root")
        child = LiteralNode("literal", "child")
        root.add_child(child)

        results = visitor.visit(root)

        assert "root" in results
        assert "child" in results

    def test_complex_tree_traversal(self):
        """Test traversal of more complex tree structure"""
        visitor = DepthFirstTraversalVisitor()

        # Build tree: root -> [func -> [lit1, lit2], ident]
        root = FunctionCallNode("functionCall", "where()")
        literal1 = LiteralNode("literal", "value1")
        literal2 = LiteralNode("literal", "value2")
        identifier = IdentifierNode("identifier", "Patient")

        root.add_child(literal1)
        root.add_child(literal2)
        root.add_child(identifier)

        results = visitor.visit(root)

        assert len(results) == 4  # root + 3 children
        assert results[0] == root  # Root visited first


class TestMetadataExtractionVisitor:
    """Test MetadataExtractionVisitor"""

    def test_metadata_extraction_no_metadata(self):
        """Test metadata extraction when nodes have no metadata"""
        visitor = MetadataExtractionVisitor()
        node = LiteralNode("literal", "test")

        result = visitor.visit(node)

        assert result["node"]["has_metadata"] is False
        assert result["node"]["node_type"] == "literal"
        assert result["node"]["text"] == "test"

    def test_metadata_extraction_with_metadata(self):
        """Test metadata extraction when nodes have metadata"""
        visitor = MetadataExtractionVisitor()

        # Create node with metadata
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
            .with_source_location("test", 1, 1) \
            .build()

        node = LiteralNode("literal", "test")
        node.metadata = metadata

        result = visitor.visit(node)

        assert result["node"]["has_metadata"] is True
        assert result["node"]["category"] == "literal"
        assert "projection_safe" in result["node"]["optimization_hints"]
        assert result["node"]["source_text"] == "test"
        assert result["node"]["line_number"] == 1

    def test_metadata_summary_accumulation(self):
        """Test that metadata summary accumulates correctly"""
        visitor = MetadataExtractionVisitor()

        # Create nodes with different metadata
        literal_metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
            .build()

        agg_metadata = MetadataBuilder() \
            .with_category(NodeCategory.AGGREGATION) \
            .with_optimization_hint(OptimizationHint.AGGREGATION_CANDIDATE) \
            .build()

        literal_node = LiteralNode("literal", "test")
        literal_node.metadata = literal_metadata

        agg_node = AggregationNode("aggregation", "count()")
        agg_node.metadata = agg_metadata

        literal_node.add_child(agg_node)

        visitor.visit(literal_node)
        summary = visitor.get_metadata_summary()

        assert summary["node_categories"]["literal"] == 1
        assert summary["node_categories"]["aggregation"] == 1
        assert summary["optimization_hints"]["projection_safe"] == 1
        assert summary["optimization_hints"]["aggregation_candidate"] == 1

    def test_literal_node_specific_metadata(self):
        """Test literal node specific metadata extraction"""
        visitor = MetadataExtractionVisitor()
        node = LiteralNode("literal", "test", value="hello")

        result = visitor.visit(node)

        assert result["node"]["literal_type"] == "string"
        assert result["node"]["literal_value"] == "hello"

    def test_function_node_specific_metadata(self):
        """Test function node specific metadata extraction"""
        visitor = MetadataExtractionVisitor()
        node = FunctionCallNode("functionCall", "count()")

        result = visitor.visit(node)

        assert result["node"]["function_name"] == "count"
        assert result["node"]["argument_count"] == 0


class TestValidationVisitor:
    """Test ValidationVisitor"""

    def test_validation_visitor_valid_tree(self):
        """Test validation of valid AST tree"""
        visitor = ValidationVisitor()

        # Create valid tree
        root = LiteralNode("literal", "test", value="hello")
        child = IdentifierNode("identifier", "Patient")
        child.identifier = "Patient"
        root.add_child(child)

        # Manually validate nodes to set up proper state
        root.validate()
        child.validate()

        result = visitor.visit(root)

        assert result is True
        assert len(visitor.get_validation_errors()) == 0

    def test_validation_visitor_invalid_tree(self):
        """Test validation of invalid AST tree"""
        visitor = ValidationVisitor()

        # Create invalid tree
        root = LiteralNode("literal", "test")
        root.value = None  # This should make it invalid

        invalid_child = IdentifierNode("identifier", "")
        invalid_child.identifier = ""  # Empty identifier is invalid
        root.add_child(invalid_child)

        result = visitor.visit(root)

        assert result is False
        errors = visitor.get_validation_errors()
        assert len(errors) > 0

        # Check that error information is captured
        error = errors[0]
        assert "path" in error
        assert "node_type" in error
        assert "error" in error

    def test_validation_path_tracking(self):
        """Test that validation tracks node paths correctly"""
        visitor = ValidationVisitor()

        root = LiteralNode("literal", "root")
        root.value = None  # Invalid

        child = LiteralNode("literal", "child")
        child.value = None  # Invalid
        root.add_child(child)

        visitor.visit(root)
        errors = visitor.get_validation_errors()

        # Should have errors for both nodes with different paths
        assert len(errors) >= 2
        paths = [error["path"] for error in errors]
        assert any("root" in path for path in paths)
        assert any("child" in path for path in paths)


class TestOptimizationAnalysisVisitor:
    """Test OptimizationAnalysisVisitor"""

    def test_optimization_analysis_basic(self):
        """Test basic optimization analysis"""
        visitor = OptimizationAnalysisVisitor()
        node = LiteralNode("literal", "test")

        result = visitor.visit(node)

        assert "node_info" in result
        assert "opportunities" in result
        assert result["node_info"]["type"] == "literal"
        assert result["node_info"]["text"] == "test"

    def test_cte_optimization_detection(self):
        """Test detection of CTE optimization opportunities"""
        visitor = OptimizationAnalysisVisitor()

        # Create node with CTE-reusable hint
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.FUNCTION_CALL) \
            .with_optimization_hint(OptimizationHint.CTE_REUSABLE) \
            .build()

        node = FunctionCallNode("functionCall", "complex_function()")
        node.metadata = metadata

        result = visitor.visit(node)

        opportunities = result["opportunities"]
        assert len(opportunities) > 0
        assert any(opp["type"] == "cte_extraction" for opp in opportunities)

    def test_population_filter_detection(self):
        """Test detection of population filter opportunities"""
        visitor = OptimizationAnalysisVisitor()

        # Create conditional node
        node = ConditionalNode("conditional", "where(condition)")

        result = visitor.visit(node)

        opportunities = result["opportunities"]
        assert any(opp["type"] == "population_filter" for opp in opportunities)

    def test_aggregation_optimization_detection(self):
        """Test detection of aggregation optimization opportunities"""
        visitor = OptimizationAnalysisVisitor()

        node = AggregationNode("aggregation", "count()")

        result = visitor.visit(node)

        opportunities = result["opportunities"]
        assert any(opp["type"] == "sql_aggregation" for opp in opportunities)

    def test_function_specific_optimizations(self):
        """Test function-specific optimization detection"""
        visitor = OptimizationAnalysisVisitor()

        # Where function should suggest condition pushdown
        where_node = FunctionCallNode("functionCall", "where(condition)")
        where_node.function_name = "where"

        result = visitor.visit(where_node)

        opportunities = result["opportunities"]
        assert any(opp["type"] == "condition_pushdown" for opp in opportunities)

    def test_operator_index_optimization(self):
        """Test operator index optimization detection"""
        visitor = OptimizationAnalysisVisitor()

        node = OperatorNode("operator", "=")
        node.operator = "="

        result = visitor.visit(node)

        opportunities = result["opportunities"]
        assert any(opp["type"] == "index_optimization" for opp in opportunities)

    def test_optimization_opportunities_collection(self):
        """Test that optimization opportunities are collected globally"""
        visitor = OptimizationAnalysisVisitor()

        # Create tree with multiple optimization opportunities
        root = AggregationNode("aggregation", "count()")
        child = ConditionalNode("conditional", "where(condition)")
        root.add_child(child)

        visitor.visit(root)
        opportunities = visitor.get_optimization_opportunities()

        # Should have opportunities from both nodes
        assert len(opportunities) >= 2
        types = [opp["type"] for opp in opportunities]
        assert "sql_aggregation" in types
        assert "population_filter" in types


class TestVisitorChain:
    """Test visitor chain functionality"""

    def test_create_visitor_chain(self):
        """Test creating and using visitor chain"""
        visitor1 = MetadataExtractionVisitor()
        visitor2 = ValidationVisitor()

        chain = create_visitor_chain(visitor1, visitor2)

        node = LiteralNode("literal", "test", value="hello")
        node.validate()  # Ensure it's valid

        results = chain(node)

        assert len(results) == 2
        assert results[0] is not None  # Metadata extraction result
        assert results[1] is True      # Validation result

    def test_visitor_chain_error_handling(self):
        """Test visitor chain error handling"""
        # Create a visitor that will fail
        failing_visitor = Mock()
        failing_visitor.visit.side_effect = Exception("Test error")

        working_visitor = MockVisitor()

        chain = create_visitor_chain(failing_visitor, working_visitor)

        node = LiteralNode("literal", "test")

        results = chain(node)

        assert len(results) == 2
        assert results[0] is None       # Failed visitor
        assert results[1] == "literal:test"  # Working visitor


class TestVisitorIntegration:
    """Test visitor integration with AST nodes"""

    def test_visitor_with_complex_tree(self):
        """Test visitors with complex AST tree"""
        # Build complex tree
        root = FunctionCallNode("functionCall", "where()")
        condition = OperatorNode("operator", "=")
        left = IdentifierNode("identifier", "Patient.active")
        right = LiteralNode("literal", "true", value=True)

        condition.add_child(left)
        condition.add_child(right)
        root.add_child(condition)

        # Test with metadata extraction visitor
        visitor = MetadataExtractionVisitor()
        result = visitor.visit(root)

        assert result["child_count"] == 1
        assert result["children"][0]["node"]["node_type"] == "operator"
        assert result["children"][0]["child_count"] == 2

    def test_visitor_with_metadata_rich_tree(self):
        """Test visitors with metadata-rich AST tree"""
        # Create tree with rich metadata
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.AGGREGATION) \
            .with_optimization_hint(OptimizationHint.AGGREGATION_CANDIDATE) \
            .with_optimization_hint(OptimizationHint.POPULATION_FILTER) \
            .build()

        root = AggregationNode("aggregation", "count()")
        root.metadata = metadata

        # Test optimization analysis
        visitor = OptimizationAnalysisVisitor()
        result = visitor.visit(root)

        opportunities = result["opportunities"]
        assert len(opportunities) >= 2  # Multiple optimization opportunities

    def test_all_node_types_with_visitors(self):
        """Test that all node types work with all visitors"""
        nodes = [
            LiteralNode("literal", "test", value="hello"),
            IdentifierNode("identifier", "Patient"),
            FunctionCallNode("functionCall", "count()"),
            OperatorNode("operator", "="),
            ConditionalNode("conditional", "where"),
            AggregationNode("aggregation", "sum()"),
            TypeOperationNode("typeOperation", "Patient as Patient")
        ]

        visitors = [
            DepthFirstTraversalVisitor(),
            MetadataExtractionVisitor(),
            ValidationVisitor(),
            OptimizationAnalysisVisitor()
        ]

        # Each visitor should work with each node type
        for node in nodes:
            # Ensure node is valid for validation visitor
            if hasattr(node, 'validate'):
                node.validate()

            for visitor in visitors:
                try:
                    result = visitor.visit(node)
                    assert result is not None
                except Exception as e:
                    pytest.fail(f"Visitor {visitor.__class__.__name__} failed with node {node.__class__.__name__}: {e}")


if __name__ == "__main__":
    pytest.main([__file__])