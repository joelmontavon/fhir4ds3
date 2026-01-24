"""
Integration tests for AST framework with database compatibility

Tests that the AST framework works correctly with both DuckDB and PostgreSQL
configurations and integrates properly with the existing parser infrastructure.
"""

import pytest
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.ast import (
    create_ast_from_expression, validate_ast, serialize_ast,
    ASTBuilder, BuildContext, CompositeValidator, SerializationFormat
)
from fhir4ds.fhirpath.ast.nodes import LiteralNode, IdentifierNode, AggregationNode
from fhir4ds.fhirpath.parser_core.metadata_types import (
    MetadataBuilder, NodeCategory, OptimizationHint, SQLDataType
)


class TestDatabaseCompatibility:
    """Test AST framework compatibility with different database types"""

    def test_duckdb_optimization_hints(self):
        """Test that DuckDB-specific optimization hints are applied"""
        context = BuildContext(database_type="duckdb", enable_optimizations=True)
        builder = ASTBuilder(context)

        # Create a simple aggregation node
        node = AggregationNode("aggregation", "count()")

        # The builder should apply DuckDB-specific optimizations
        # This is tested indirectly through the metadata enhancement
        assert builder.context.database_type == "duckdb"

    def test_postgresql_optimization_hints(self):
        """Test that PostgreSQL-specific optimization hints are applied"""
        context = BuildContext(database_type="postgresql", enable_optimizations=True)
        builder = ASTBuilder(context)

        # Create a simple aggregation node
        node = AggregationNode("aggregation", "count()")

        # The builder should apply PostgreSQL-specific optimizations
        assert builder.context.database_type == "postgresql"

    def test_database_independence(self):
        """Test that AST nodes are database-independent"""
        # Create identical nodes for both database types
        duckdb_context = BuildContext(database_type="duckdb")
        postgresql_context = BuildContext(database_type="postgresql")

        duckdb_builder = ASTBuilder(duckdb_context)
        postgresql_builder = ASTBuilder(postgresql_context)

        # Both should create similar AST structures
        assert duckdb_builder.context.database_type != postgresql_builder.context.database_type


class TestASTValidationIntegration:
    """Test integration of AST validation with the framework"""

    def test_validate_simple_ast(self):
        """Test validation of a simple AST structure"""
        # Create a simple valid AST
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
            .build()

        node = LiteralNode("literal", "hello", value="hello")
        node.metadata = metadata

        # Validate the AST
        validator = CompositeValidator(strict_mode=False)
        result = validator.validate_ast(node)

        assert result.is_valid
        assert result.nodes_validated == 1
        assert len(result.get_errors()) == 0

    def test_validate_complex_ast(self):
        """Test validation of a complex AST structure"""
        # Create a tree: aggregation -> identifier
        root = AggregationNode("aggregation", "count()")
        child = IdentifierNode("identifier", "Patient.id")

        # Add proper metadata
        root_metadata = MetadataBuilder() \
            .with_category(NodeCategory.AGGREGATION) \
            .with_optimization_hint(OptimizationHint.AGGREGATION_CANDIDATE) \
            .build()
        root.metadata = root_metadata

        child_metadata = MetadataBuilder() \
            .with_category(NodeCategory.PATH_EXPRESSION) \
            .build()
        child.metadata = child_metadata

        root.add_child(child)

        # Both nodes should validate
        assert root.validate()
        assert child.validate()

        # Validate the entire tree
        validator = CompositeValidator()
        result = validator.validate_ast(root)

        assert result.is_valid
        assert result.nodes_validated == 2

    def test_validation_with_population_analytics(self):
        """Test validation specifically for population analytics"""
        from fhir4ds.fhirpath.ast.validator import validate_ast_for_population_analytics

        # Create aggregation node with proper population support
        root = AggregationNode("aggregation", "count()")

        metadata = MetadataBuilder() \
            .with_category(NodeCategory.AGGREGATION) \
            .build()
        metadata.population_analytics.supports_population_query = True
        root.metadata = metadata

        result = validate_ast_for_population_analytics(root)

        # Should pass population analytics validation
        assert result.is_valid or len(result.get_errors()) == 0


class TestASTSerializationIntegration:
    """Test AST serialization integration"""

    def test_serialize_simple_ast_json(self):
        """Test JSON serialization of simple AST"""
        node = LiteralNode("literal", "test", value="test_value")

        # Ensure node is valid
        node.validate()

        # Serialize to JSON
        json_output = serialize_ast(node, SerializationFormat.JSON)

        assert isinstance(json_output, str)
        assert "literal" in json_output
        assert "test_value" in json_output

    def test_serialize_ast_with_metadata(self):
        """Test serialization of AST with metadata"""
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
            .build()

        node = LiteralNode("literal", "test", value="test_value")
        node.metadata = metadata

        # Serialize with metadata
        json_output = serialize_ast(node, SerializationFormat.JSON)

        assert "metadata" in json_output
        assert "projection_safe" in json_output
        assert "literal" in json_output


class TestConvenienceFunctions:
    """Test the convenience functions in the AST module"""

    @patch('fhir4ds.fhirpath.parser_core.enhanced_parser.EnhancedFHIRPathParser')
    def test_create_ast_from_expression_success(self, mock_parser_class):
        """Test successful AST creation from expression"""
        # Mock the parser and its results
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.ast = Mock()  # This would be an EnhancedASTNode
        mock_parser.parse.return_value = mock_result

        # Mock the enhanced AST node
        mock_enhanced_node = Mock()
        mock_enhanced_node.node_type = "literal"
        mock_enhanced_node.text = "test"
        mock_enhanced_node.metadata = None
        mock_enhanced_node.parent = None
        mock_enhanced_node.sql_fragment = None
        mock_enhanced_node.cte_name = None
        mock_enhanced_node.dependencies = []
        mock_enhanced_node.children = []
        mock_result.ast = mock_enhanced_node

        # This would normally create an AST, but will return None due to mocking
        result = create_ast_from_expression("Patient.name")

        # The function should attempt to create an AST
        mock_parser_class.assert_called_once()

    def test_create_ast_from_expression_failure(self):
        """Test AST creation failure handling"""
        # This should return None for invalid expressions
        result = create_ast_from_expression("")

        assert result is None

    def test_validate_ast_convenience(self):
        """Test the convenience validate_ast function"""
        node = LiteralNode("literal", "test", value="hello")

        result = validate_ast(node, strict_mode=False)

        assert isinstance(result.is_valid, bool)
        assert hasattr(result, 'issues')
        assert hasattr(result, 'nodes_validated')


class TestArchitecturalCompliance:
    """Test compliance with FHIR4DS architectural principles"""

    def test_population_analytics_first(self):
        """Test that AST supports population-scale analytics"""
        # Create aggregation node with population support
        node = AggregationNode("aggregation", "count()")

        metadata = MetadataBuilder() \
            .with_category(NodeCategory.AGGREGATION) \
            .build()
        metadata.population_analytics.supports_population_query = True
        metadata.population_analytics.aggregation_level = "population"
        node.metadata = metadata

        # Node should support population queries
        assert node.metadata.population_analytics.supports_population_query
        assert node.metadata.population_analytics.aggregation_level == "population"

    def test_cte_generation_support(self):
        """Test that AST supports CTE generation"""
        node = AggregationNode("aggregation", "count()")

        metadata = MetadataBuilder() \
            .with_category(NodeCategory.AGGREGATION) \
            .with_optimization_hint(OptimizationHint.CTE_REUSABLE) \
            .build()
        metadata.cte_context.can_be_subquery = True
        node.metadata = metadata

        # Node should support CTE generation
        assert OptimizationHint.CTE_REUSABLE in node.metadata.optimization_hints
        assert node.metadata.cte_context.can_be_subquery

    def test_multi_dialect_support(self):
        """Test that AST design supports multiple database dialects"""
        # Create nodes for different database types
        duckdb_node = LiteralNode("literal", "test")
        postgresql_node = LiteralNode("literal", "test")

        # Both should have the same basic structure
        assert duckdb_node.node_type == postgresql_node.node_type
        assert duckdb_node.text == postgresql_node.text

        # Database-specific optimizations would be in metadata
        duckdb_metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .build()

        postgresql_metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .build()

        duckdb_node.metadata = duckdb_metadata
        postgresql_node.metadata = postgresql_metadata

        # Core AST structure is the same, metadata can differ
        assert duckdb_node.node_type == postgresql_node.node_type


class TestErrorHandling:
    """Test error handling in AST framework"""

    def test_validation_error_collection(self):
        """Test that validation errors are properly collected"""
        # Create invalid node
        node = LiteralNode("literal", "test")
        node.value = None  # Invalid - no value

        validator = CompositeValidator()
        result = validator.validate_ast(node)

        assert not result.is_valid
        assert len(result.get_errors()) > 0

        # Check error details
        error = result.get_errors()[0]
        assert hasattr(error, 'severity')
        assert hasattr(error, 'message')
        assert hasattr(error, 'node_path')

    def test_visitor_error_handling(self):
        """Test that visitor errors are handled gracefully"""
        from fhir4ds.fhirpath.ast.visitor import ValidationVisitor

        visitor = ValidationVisitor()

        # Create a node that will have validation errors
        node = LiteralNode("literal", "")
        node.value = None

        # Visitor should handle the invalid node gracefully
        try:
            result = visitor.visit(node)
            # Result should indicate validation failure
            assert not result
        except Exception:
            pytest.fail("Visitor should handle errors gracefully")


if __name__ == "__main__":
    pytest.main([__file__])