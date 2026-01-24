"""
AST Builder for constructing FHIRPath AST from Parser Output

This module provides builders for automatically constructing enhanced AST
nodes from fhirpath-py parser output with proper metadata population.
"""

from typing import Dict, Any, List, Optional, Union
import logging
from dataclasses import dataclass

from .nodes import (
    FHIRPathASTNode, LiteralNode, IdentifierNode, FunctionCallNode,
    OperatorNode, ConditionalNode, AggregationNode, TypeOperationNode,
    NodeTypeFactory
)
from ..parser_core.ast_extensions import EnhancedASTNode, ASTNodeFactory
from ..parser_core.metadata_types import (
    ASTNodeMetadata, NodeCategory, OptimizationHint,
    MetadataBuilder, TypeInformation, SQLDataType
)


@dataclass
class BuildContext:
    """Context information for AST building process"""
    database_type: str = "duckdb"
    enable_optimizations: bool = True
    strict_validation: bool = True
    preserve_source_locations: bool = True


class ASTBuilder:
    """
    Builder for constructing enhanced FHIRPath AST from parser output

    Converts parser output into strongly-typed AST nodes with comprehensive
    metadata for CTE generation and population-scale analytics.
    """

    def __init__(self, context: Optional[BuildContext] = None):
        self.context = context or BuildContext()
        self.logger = logging.getLogger(__name__)
        self._build_count = 0
        self._error_count = 0

    def build_from_parse_tree(self, parse_tree: Union[Dict[str, Any], Any]) -> Optional[FHIRPathASTNode]:
        """
        Build AST from fhirpath-py parse tree

        Args:
            parse_tree: Parse tree from fhirpath-py parser

        Returns:
            Root node of constructed AST or None if build fails
        """
        try:
            self._build_count += 1

            # First, convert to enhanced AST using existing factory
            enhanced_ast = ASTNodeFactory.create_from_fhirpath_node(parse_tree)

            if enhanced_ast is None:
                self.logger.error("Failed to create enhanced AST from parse tree")
                return None

            # Then convert to typed AST nodes
            typed_ast = self._convert_to_typed_ast(enhanced_ast)

            if typed_ast and self.context.strict_validation:
                # Validate the constructed AST
                if not typed_ast.validate():
                    self.logger.warning(f"AST validation failed: {typed_ast.get_validation_errors()}")
                    if self.context.strict_validation:
                        return None

            return typed_ast

        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Error building AST from parse tree: {e}")
            return None

    def build_from_enhanced_ast(self, enhanced_ast: EnhancedASTNode) -> Optional[FHIRPathASTNode]:
        """
        Build typed AST from existing enhanced AST

        Args:
            enhanced_ast: Enhanced AST node from SP-003-001

        Returns:
            Typed AST node or None if conversion fails
        """
        try:
            return self._convert_to_typed_ast(enhanced_ast)
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Error converting enhanced AST: {e}")
            return None

    def _convert_to_typed_ast(self, enhanced_node: EnhancedASTNode) -> Optional[FHIRPathASTNode]:
        """Convert enhanced AST node to typed AST node"""
        try:
            # Use the NodeTypeFactory to create appropriate typed node
            typed_node = NodeTypeFactory.create_node_from_enhanced(enhanced_node)

            # Enhance metadata based on context
            self._enhance_metadata_for_context(typed_node)

            # Apply optimization hints based on context
            if self.context.enable_optimizations:
                self._apply_optimization_hints(typed_node)

            return typed_node

        except Exception as e:
            self.logger.error(f"Error converting node {enhanced_node}: {e}")
            return None

    def _enhance_metadata_for_context(self, node: FHIRPathASTNode) -> None:
        """Enhance node metadata based on build context"""
        if not node.metadata:
            return

        metadata = node.metadata

        # Database-specific enhancements
        if self.context.database_type == "duckdb":
            self._apply_duckdb_optimizations(node, metadata)
        elif self.context.database_type == "postgresql":
            self._apply_postgresql_optimizations(node, metadata)

    def _apply_duckdb_optimizations(self, node: FHIRPathASTNode, metadata: ASTNodeMetadata) -> None:
        """Apply DuckDB-specific optimization hints"""
        # DuckDB is excellent at JSON operations
        if metadata.type_info.sql_data_type == SQLDataType.JSON:
            metadata.optimization_hints.add(OptimizationHint.PROJECTION_SAFE)

        # DuckDB has good aggregation performance
        if isinstance(node, AggregationNode):
            metadata.optimization_hints.add(OptimizationHint.AGGREGATION_CANDIDATE)

        # DuckDB supports vectorization well
        if node.node_type in ["functionCall", "operator"]:
            metadata.optimization_hints.add(OptimizationHint.VECTORIZABLE)

    def _apply_postgresql_optimizations(self, node: FHIRPathASTNode, metadata: ASTNodeMetadata) -> None:
        """Apply PostgreSQL-specific optimization hints"""
        # PostgreSQL has excellent indexing support
        if isinstance(node, OperatorNode) and hasattr(node, 'operator'):
            if node.operator in ['=', '!=', '<', '>', '<=', '>=']:
                metadata.optimization_hints.add(OptimizationHint.INDEX_FRIENDLY)

        # PostgreSQL JSONB operations are efficient
        if metadata.type_info.sql_data_type == SQLDataType.JSON:
            metadata.optimization_hints.add(OptimizationHint.PROJECTION_SAFE)

    def _apply_optimization_hints(self, node: FHIRPathASTNode) -> None:
        """Apply general optimization hints based on node analysis"""
        if not node.metadata:
            return

        # Analyze node for population-scale optimizations
        if self._is_population_filterable(node):
            node.metadata.optimization_hints.add(OptimizationHint.POPULATION_FILTER)

        # Check for CTE extraction opportunities
        if self._is_cte_candidate(node):
            node.metadata.optimization_hints.add(OptimizationHint.CTE_REUSABLE)

        # Check for aggregation opportunities
        if isinstance(node, AggregationNode):
            node.metadata.optimization_hints.add(OptimizationHint.AGGREGATION_CANDIDATE)

    def _is_population_filterable(self, node: FHIRPathASTNode) -> bool:
        """Check if node can be optimized for population filtering"""
        if isinstance(node, ConditionalNode):
            return True

        if isinstance(node, OperatorNode) and hasattr(node, 'operator'):
            # Comparison operators are good candidates
            return node.operator in ['=', '!=', '<', '>', '<=', '>=']

        if isinstance(node, FunctionCallNode) and hasattr(node, 'function_name'):
            # Where/select functions are filterable
            return node.function_name.lower() in ['where', 'select', 'exists']

        return False

    def _is_cte_candidate(self, node: FHIRPathASTNode) -> bool:
        """Check if node is a good candidate for CTE extraction"""
        # Complex function calls can benefit from CTE extraction
        if isinstance(node, FunctionCallNode):
            return len(node.children) > 2

        # Aggregation nodes are good CTE candidates
        if isinstance(node, AggregationNode):
            return True

        # Complex conditional expressions
        if isinstance(node, ConditionalNode):
            return len(node.children) > 1

        return False

    def get_build_stats(self) -> Dict[str, int]:
        """Get builder statistics"""
        return {
            "total_builds": self._build_count,
            "error_count": self._error_count,
            "success_rate": (self._build_count - self._error_count) / max(self._build_count, 1)
        }


class MetadataEnhancer:
    """
    Enhances AST nodes with additional metadata for specific use cases

    Provides specialized metadata enhancement for different optimization
    scenarios and database targets.
    """

    def __init__(self, database_type: str = "duckdb"):
        self.database_type = database_type
        self.logger = logging.getLogger(__name__)

    def enhance_for_sql_generation(self, node: FHIRPathASTNode) -> None:
        """Enhance node metadata for SQL generation"""
        if not node.metadata:
            return

        # Add SQL generation context
        self._populate_sql_hints(node)

        # Recursively enhance children
        for child in node.children:
            self.enhance_for_sql_generation(child)

    def enhance_for_population_analytics(self, node: FHIRPathASTNode) -> None:
        """Enhance node metadata for population-scale analytics"""
        if not node.metadata:
            return

        # Configure population analytics metadata
        pop_metadata = node.metadata.population_analytics

        if isinstance(node, ConditionalNode):
            pop_metadata.supports_population_query = True
            pop_metadata.can_be_population_filtered = True

        elif isinstance(node, AggregationNode):
            pop_metadata.supports_population_query = True
            pop_metadata.aggregation_level = "population"

        elif isinstance(node, IdentifierNode) and hasattr(node, 'identifier'):
            if 'patient' in node.identifier.lower():
                pop_metadata.requires_patient_context = True
                pop_metadata.aggregation_level = "patient"

        # Recursively enhance children
        for child in node.children:
            self.enhance_for_population_analytics(child)

    def enhance_for_performance(self, node: FHIRPathASTNode) -> None:
        """Enhance node metadata for performance optimization"""
        if not node.metadata:
            return

        performance = node.metadata.performance

        # Analyze performance characteristics
        if isinstance(node, AggregationNode):
            performance.cpu_intensive = True

        elif isinstance(node, FunctionCallNode) and hasattr(node, 'function_name'):
            func_name = node.function_name.lower()
            if func_name in ['where', 'select']:
                performance.io_intensive = True  # May require data scanning

        elif len(node.children) > 5:
            performance.memory_intensive = True  # Complex expressions

        # Recursively enhance children
        for child in node.children:
            self.enhance_for_performance(child)

    def _populate_sql_hints(self, node: FHIRPathASTNode) -> None:
        """Populate SQL-specific optimization hints"""
        if not node.metadata:
            return

        cte_context = node.metadata.cte_context

        # Configure CTE generation context
        if isinstance(node, AggregationNode):
            cte_context.can_be_subquery = True
            cte_context.requires_window_function = True

        elif isinstance(node, ConditionalNode):
            cte_context.can_be_subquery = True

        elif isinstance(node, FunctionCallNode):
            if len(node.children) > 0:
                cte_context.requires_join = True

        # Database-specific SQL hints
        if self.database_type == "duckdb":
            self._apply_duckdb_sql_hints(node)
        elif self.database_type == "postgresql":
            self._apply_postgresql_sql_hints(node)

    def _apply_duckdb_sql_hints(self, node: FHIRPathASTNode) -> None:
        """Apply DuckDB-specific SQL hints"""
        if node.metadata and node.metadata.type_info.sql_data_type == SQLDataType.JSON:
            # DuckDB has excellent JSON support
            node.metadata.optimization_hints.add(OptimizationHint.PROJECTION_SAFE)

    def _apply_postgresql_sql_hints(self, node: FHIRPathASTNode) -> None:
        """Apply PostgreSQL-specific SQL hints"""
        if node.metadata and isinstance(node, OperatorNode):
            # PostgreSQL has excellent indexing
            node.metadata.optimization_hints.add(OptimizationHint.INDEX_FRIENDLY)


class ASTRebuilder:
    """
    Rebuilds AST with enhanced metadata and optimizations

    Provides functionality to rebuild existing AST trees with updated
    metadata, optimization hints, and structural improvements.
    """

    def __init__(self, context: Optional[BuildContext] = None):
        self.context = context or BuildContext()
        self.enhancer = MetadataEnhancer(context.database_type)
        self.logger = logging.getLogger(__name__)

    def rebuild_with_enhancements(self, root: FHIRPathASTNode) -> FHIRPathASTNode:
        """
        Rebuild AST with enhanced metadata and optimizations

        Args:
            root: Root node of AST to rebuild

        Returns:
            Rebuilt AST with enhancements
        """
        try:
            # Create a copy of the AST structure
            rebuilt_root = self._deep_copy_ast(root)

            # Apply enhancements
            self.enhancer.enhance_for_sql_generation(rebuilt_root)
            self.enhancer.enhance_for_population_analytics(rebuilt_root)
            self.enhancer.enhance_for_performance(rebuilt_root)

            # Validate if required
            if self.context.strict_validation:
                if not rebuilt_root.validate():
                    self.logger.warning("Rebuilt AST failed validation")

            return rebuilt_root

        except Exception as e:
            self.logger.error(f"Error rebuilding AST: {e}")
            return root  # Return original on error

    def _deep_copy_ast(self, node: FHIRPathASTNode) -> FHIRPathASTNode:
        """Create a deep copy of an AST node and its children"""
        # Create new instance of the same type
        node_class = type(node)

        # Copy basic properties
        copy_node = node_class.__new__(node_class)
        FHIRPathASTNode.__init__(copy_node, node.node_type, node.text)

        # Copy metadata
        if node.metadata:
            # Create a new metadata instance (this creates a shallow copy)
            copy_node.metadata = ASTNodeMetadata(
                node_category=node.metadata.node_category,
                type_info=node.metadata.type_info,
                optimization_hints=node.metadata.optimization_hints.copy(),
                performance=node.metadata.performance,
                cte_context=node.metadata.cte_context,
                population_analytics=node.metadata.population_analytics,
                source_text=node.metadata.source_text,
                line_number=node.metadata.line_number,
                column_number=node.metadata.column_number,
                custom_attributes=node.metadata.custom_attributes.copy()
            )

        # Copy other properties specific to node types
        self._copy_node_specific_properties(node, copy_node)

        # Recursively copy children
        for child in node.children:
            child_copy = self._deep_copy_ast(child)
            copy_node.add_child(child_copy)

        return copy_node

    def _copy_node_specific_properties(self, source: FHIRPathASTNode, target: FHIRPathASTNode) -> None:
        """Copy properties specific to different node types"""
        if isinstance(source, LiteralNode) and isinstance(target, LiteralNode):
            target.value = source.value
            target.literal_type = source.literal_type

        elif isinstance(source, IdentifierNode) and isinstance(target, IdentifierNode):
            target.identifier = source.identifier
            target.is_qualified = source.is_qualified

        elif isinstance(source, FunctionCallNode) and isinstance(target, FunctionCallNode):
            target.function_name = source.function_name
            target.arguments = source.arguments.copy()

        elif isinstance(source, OperatorNode) and isinstance(target, OperatorNode):
            target.operator = source.operator
            target.operator_type = source.operator_type
            target.left_operand = source.left_operand
            target.right_operand = source.right_operand

        elif isinstance(source, ConditionalNode) and isinstance(target, ConditionalNode):
            target.condition = source.condition
            target.condition_type = source.condition_type

        elif isinstance(source, AggregationNode) and isinstance(target, AggregationNode):
            target.aggregation_function = source.aggregation_function
            target.aggregation_type = source.aggregation_type

        elif isinstance(source, TypeOperationNode) and isinstance(target, TypeOperationNode):
            target.operation = source.operation
            target.target_type = source.target_type