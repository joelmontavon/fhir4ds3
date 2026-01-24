"""
Visitor Pattern Implementation for FHIRPath AST Traversal

This module provides a comprehensive visitor pattern framework for traversing
and operating on FHIRPath AST trees with metadata access and type safety.
"""

from typing import Any, Dict, List, Optional, TypeVar, Generic, Callable
from abc import ABC, abstractmethod
import logging

# Forward declaration to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .nodes import (
        FHIRPathASTNode, LiteralNode, IdentifierNode, FunctionCallNode,
        OperatorNode, ConditionalNode, AggregationNode, TypeOperationNode
    )

T = TypeVar('T')
R = TypeVar('R')


class ASTVisitor(ABC, Generic[T]):
    """
    Abstract base visitor for FHIRPath AST traversal

    Implements the visitor pattern allowing separation of tree structure
    from operations performed on the tree. Visitors can accumulate results
    and maintain state during traversal.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._visit_count = 0
        self._error_count = 0

    @abstractmethod
    def visit_literal(self, node: 'LiteralNode') -> T:
        """Visit a literal node"""
        pass

    @abstractmethod
    def visit_identifier(self, node: 'IdentifierNode') -> T:
        """Visit an identifier node"""
        pass

    @abstractmethod
    def visit_function_call(self, node: 'FunctionCallNode') -> T:
        """Visit a function call node"""
        pass

    @abstractmethod
    def visit_operator(self, node: 'OperatorNode') -> T:
        """Visit an operator node"""
        pass

    @abstractmethod
    def visit_conditional(self, node: 'ConditionalNode') -> T:
        """Visit a conditional node"""
        pass

    @abstractmethod
    def visit_aggregation(self, node: 'AggregationNode') -> T:
        """Visit an aggregation node"""
        pass

    @abstractmethod
    def visit_type_operation(self, node: 'TypeOperationNode') -> T:
        """Visit a type operation node"""
        pass

    def visit_generic(self, node: 'FHIRPathASTNode') -> T:
        """
        Generic visit method for unknown or base node types
        Default implementation raises NotImplementedError
        """
        raise NotImplementedError(f"No visit method for node type: {type(node).__name__}")

    def visit(self, node: 'FHIRPathASTNode') -> T:
        """
        Main visit entry point that dispatches to appropriate visit method
        Tracks visit statistics and handles errors gracefully
        """
        self._visit_count += 1

        try:
            return node.accept(self)
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Error visiting node {node}: {e}")
            raise

    def get_visit_stats(self) -> Dict[str, int]:
        """Get visitor statistics"""
        return {
            "total_visits": self._visit_count,
            "error_count": self._error_count
        }


class DepthFirstTraversalVisitor(ASTVisitor[List[T]]):
    """
    Depth-first traversal visitor that visits all nodes in depth-first order
    Collects results from all visited nodes into a list
    """

    def __init__(self):
        super().__init__()
        self.results: List[T] = []
        self._node_processor: Optional[Callable[['FHIRPathASTNode'], T]] = None

    def set_node_processor(self, processor: Callable[['FHIRPathASTNode'], T]) -> None:
        """Set a custom processor function for each visited node"""
        self._node_processor = processor

    def _visit_children_and_collect(self, node: 'FHIRPathASTNode') -> List[T]:
        """Visit all children and collect their results"""
        child_results = []
        for child in node.children:
            result = self.visit(child)
            if isinstance(result, list):
                child_results.extend(result)
            else:
                child_results.append(result)
        return child_results

    def _process_node(self, node: 'FHIRPathASTNode') -> T:
        """Process a node using the configured processor or default behavior"""
        if self._node_processor:
            return self._node_processor(node)
        return node  # Default: return the node itself

    def visit_literal(self, node: 'LiteralNode') -> List[T]:
        result = self._process_node(node)
        child_results = self._visit_children_and_collect(node)
        return [result] + child_results

    def visit_identifier(self, node: 'IdentifierNode') -> List[T]:
        result = self._process_node(node)
        child_results = self._visit_children_and_collect(node)
        return [result] + child_results

    def visit_function_call(self, node: 'FunctionCallNode') -> List[T]:
        result = self._process_node(node)
        child_results = self._visit_children_and_collect(node)
        return [result] + child_results

    def visit_operator(self, node: 'OperatorNode') -> List[T]:
        result = self._process_node(node)
        child_results = self._visit_children_and_collect(node)
        return [result] + child_results

    def visit_conditional(self, node: 'ConditionalNode') -> List[T]:
        result = self._process_node(node)
        child_results = self._visit_children_and_collect(node)
        return [result] + child_results

    def visit_aggregation(self, node: 'AggregationNode') -> List[T]:
        result = self._process_node(node)
        child_results = self._visit_children_and_collect(node)
        return [result] + child_results

    def visit_type_operation(self, node: 'TypeOperationNode') -> List[T]:
        result = self._process_node(node)
        child_results = self._visit_children_and_collect(node)
        return [result] + child_results


class MetadataExtractionVisitor(ASTVisitor[Dict[str, Any]]):
    """
    Visitor that extracts and analyzes metadata from AST nodes
    Returns comprehensive metadata analysis for the entire tree
    """

    def __init__(self):
        super().__init__()
        self.metadata_summary = {
            "node_categories": {},
            "optimization_hints": {},
            "sql_data_types": {},
            "population_analytics": {
                "supports_population_query": 0,
                "requires_patient_context": 0,
                "can_be_population_filtered": 0
            },
            "performance_flags": {
                "memory_intensive": 0,
                "cpu_intensive": 0,
                "io_intensive": 0
            }
        }

    def _extract_metadata(self, node: 'FHIRPathASTNode') -> Dict[str, Any]:
        """Extract metadata from a node and update summary statistics"""
        result = {
            "node_type": node.node_type,
            "text": node.text,
            "has_metadata": node.metadata is not None
        }

        if node.metadata:
            metadata = node.metadata

            # Update category counts
            category = metadata.node_category.value
            self.metadata_summary["node_categories"][category] = \
                self.metadata_summary["node_categories"].get(category, 0) + 1

            # Update optimization hints
            for hint in metadata.optimization_hints:
                hint_name = hint.value
                self.metadata_summary["optimization_hints"][hint_name] = \
                    self.metadata_summary["optimization_hints"].get(hint_name, 0) + 1

            # Update SQL data types
            if metadata.type_info:
                sql_type = metadata.type_info.sql_data_type.value
                self.metadata_summary["sql_data_types"][sql_type] = \
                    self.metadata_summary["sql_data_types"].get(sql_type, 0) + 1

            # Update population analytics
            pop_analytics = metadata.population_analytics
            if pop_analytics.supports_population_query:
                self.metadata_summary["population_analytics"]["supports_population_query"] += 1
            if pop_analytics.requires_patient_context:
                self.metadata_summary["population_analytics"]["requires_patient_context"] += 1
            if pop_analytics.can_be_population_filtered:
                self.metadata_summary["population_analytics"]["can_be_population_filtered"] += 1

            # Update performance flags
            performance = metadata.performance
            if performance.memory_intensive:
                self.metadata_summary["performance_flags"]["memory_intensive"] += 1
            if performance.cpu_intensive:
                self.metadata_summary["performance_flags"]["cpu_intensive"] += 1
            if performance.io_intensive:
                self.metadata_summary["performance_flags"]["io_intensive"] += 1

            result.update({
                "category": category,
                "optimization_hints": [hint.value for hint in metadata.optimization_hints],
                "sql_data_type": sql_type,
                "source_text": metadata.source_text,
                "line_number": metadata.line_number,
                "column_number": metadata.column_number
            })

        return result

    def _visit_and_combine(self, node: 'FHIRPathASTNode') -> Dict[str, Any]:
        """Visit node, extract metadata, and combine with children results"""
        node_metadata = self._extract_metadata(node)

        # Visit children
        children_metadata = []
        for child in node.children:
            child_result = self.visit(child)
            children_metadata.append(child_result)

        return {
            "node": node_metadata,
            "children": children_metadata,
            "child_count": len(children_metadata)
        }

    def visit_literal(self, node: 'LiteralNode') -> Dict[str, Any]:
        result = self._visit_and_combine(node)
        result["node"]["literal_type"] = getattr(node, 'literal_type', 'unknown')
        result["node"]["literal_value"] = getattr(node, 'value', None)
        return result

    def visit_identifier(self, node: 'IdentifierNode') -> Dict[str, Any]:
        result = self._visit_and_combine(node)
        result["node"]["identifier"] = getattr(node, 'identifier', '')
        result["node"]["is_qualified"] = getattr(node, 'is_qualified', False)
        return result

    def visit_function_call(self, node: 'FunctionCallNode') -> Dict[str, Any]:
        result = self._visit_and_combine(node)
        result["node"]["function_name"] = getattr(node, 'function_name', '')
        result["node"]["argument_count"] = len(getattr(node, 'arguments', []))
        return result

    def visit_operator(self, node: 'OperatorNode') -> Dict[str, Any]:
        result = self._visit_and_combine(node)
        result["node"]["operator"] = getattr(node, 'operator', '')
        result["node"]["operator_type"] = getattr(node, 'operator_type', 'unknown')
        return result

    def visit_conditional(self, node: 'ConditionalNode') -> Dict[str, Any]:
        result = self._visit_and_combine(node)
        result["node"]["condition_type"] = getattr(node, 'condition_type', 'where')
        return result

    def visit_aggregation(self, node: 'AggregationNode') -> Dict[str, Any]:
        result = self._visit_and_combine(node)
        result["node"]["aggregation_function"] = getattr(node, 'aggregation_function', '')
        result["node"]["aggregation_type"] = getattr(node, 'aggregation_type', 'count')
        return result

    def visit_type_operation(self, node: 'TypeOperationNode') -> Dict[str, Any]:
        result = self._visit_and_combine(node)
        result["node"]["operation"] = getattr(node, 'operation', '')
        result["node"]["target_type"] = getattr(node, 'target_type', '')
        return result

    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get comprehensive metadata summary for the entire tree"""
        return self.metadata_summary.copy()


class ValidationVisitor(ASTVisitor[bool]):
    """
    Visitor that validates AST nodes and collects validation errors
    Returns True if entire tree is valid, False otherwise
    """

    def __init__(self):
        super().__init__()
        self.validation_errors: List[Dict[str, Any]] = []
        self._current_path: List[str] = []

    def _validate_node(self, node: 'FHIRPathASTNode') -> bool:
        """Validate a single node and track path"""
        self._current_path.append(f"{node.node_type}({node.text})")

        try:
            is_valid = node.validate()

            if not is_valid:
                for error in node.get_validation_errors():
                    self.validation_errors.append({
                        "path": " -> ".join(self._current_path),
                        "node_type": node.node_type,
                        "node_text": node.text,
                        "error": error
                    })

            # Validate children
            children_valid = True
            for child in node.children:
                if not self.visit(child):
                    children_valid = False

            return is_valid and children_valid

        finally:
            self._current_path.pop()

    def visit_literal(self, node: 'LiteralNode') -> bool:
        return self._validate_node(node)

    def visit_identifier(self, node: 'IdentifierNode') -> bool:
        return self._validate_node(node)

    def visit_function_call(self, node: 'FunctionCallNode') -> bool:
        return self._validate_node(node)

    def visit_operator(self, node: 'OperatorNode') -> bool:
        return self._validate_node(node)

    def visit_conditional(self, node: 'ConditionalNode') -> bool:
        return self._validate_node(node)

    def visit_aggregation(self, node: 'AggregationNode') -> bool:
        return self._validate_node(node)

    def visit_type_operation(self, node: 'TypeOperationNode') -> bool:
        return self._validate_node(node)

    def get_validation_errors(self) -> List[Dict[str, Any]]:
        """Get all validation errors found during traversal"""
        return self.validation_errors.copy()


class OptimizationAnalysisVisitor(ASTVisitor[Dict[str, Any]]):
    """
    Visitor that analyzes AST for optimization opportunities
    Identifies CTE extraction candidates, population filters, etc.
    """

    def __init__(self):
        super().__init__()
        self.optimization_opportunities = []

    def _analyze_optimization(self, node: 'FHIRPathASTNode') -> Dict[str, Any]:
        """Analyze a node for optimization opportunities"""
        result = {
            "node_info": {
                "type": node.node_type,
                "text": node.text,
                "depth": node.get_depth() if hasattr(node, 'get_depth') else 0
            },
            "opportunities": []
        }

        if node.metadata:
            metadata = node.metadata

            # Check for optimization opportunities based on hints
            from ..parser_core.metadata_types import OptimizationHint

            # Check for CTE extraction opportunities
            if OptimizationHint.CTE_REUSABLE in metadata.optimization_hints:
                result["opportunities"].append({
                    "type": "cte_extraction",
                    "reason": "Node marked as CTE reusable",
                    "benefit": "high"
                })

            # Check for population filter opportunities
            if OptimizationHint.POPULATION_FILTER in metadata.optimization_hints:
                result["opportunities"].append({
                    "type": "population_filter",
                    "reason": "Node can be optimized for population queries",
                    "benefit": "medium"
                })

            # Check for aggregation opportunities
            if OptimizationHint.AGGREGATION_CANDIDATE in metadata.optimization_hints:
                result["opportunities"].append({
                    "type": "aggregation_optimization",
                    "reason": "Node can leverage SQL aggregation functions",
                    "benefit": "high"
                })

            # Check for vectorization opportunities
            if OptimizationHint.VECTORIZABLE in metadata.optimization_hints:
                result["opportunities"].append({
                    "type": "vectorization",
                    "reason": "Node can be vectorized for performance",
                    "benefit": "medium"
                })

        # Analyze children
        children_analysis = []
        for child in node.children:
            child_result = self.visit(child)
            children_analysis.append(child_result)

            # Collect opportunities from children
            for opp in child_result.get("opportunities", []):
                self.optimization_opportunities.append(opp)

        result["children"] = children_analysis

        # Add our opportunities to global list
        for opp in result["opportunities"]:
            self.optimization_opportunities.append(opp)

        return result

    def visit_literal(self, node: 'LiteralNode') -> Dict[str, Any]:
        return self._analyze_optimization(node)

    def visit_identifier(self, node: 'IdentifierNode') -> Dict[str, Any]:
        return self._analyze_optimization(node)

    def visit_function_call(self, node: 'FunctionCallNode') -> Dict[str, Any]:
        result = self._analyze_optimization(node)

        # Additional analysis for function calls
        function_name = getattr(node, 'function_name', '').lower()
        if function_name in ['where', 'select']:
            pushdown_opportunity = {
                "type": "condition_pushdown",
                "reason": f"'{function_name}' can potentially be pushed to database WHERE clause",
                "benefit": "high"
            }
            result["opportunities"].append(pushdown_opportunity)
            self.optimization_opportunities.append(pushdown_opportunity)

        return result

    def visit_operator(self, node: 'OperatorNode') -> Dict[str, Any]:
        result = self._analyze_optimization(node)

        # Additional analysis for operators
        operator = getattr(node, 'operator', '')
        if operator in ['=', '!=', '<', '>', '<=', '>=']:
            index_opportunity = {
                "type": "index_optimization",
                "reason": f"Comparison operator '{operator}' can benefit from database indexing",
                "benefit": "medium"
            }
            result["opportunities"].append(index_opportunity)
            self.optimization_opportunities.append(index_opportunity)

        return result

    def visit_conditional(self, node: 'ConditionalNode') -> Dict[str, Any]:
        result = self._analyze_optimization(node)

        # Conditional expressions are good candidates for population filtering
        pop_filter_opportunity = {
            "type": "population_filter",
            "reason": "Conditional expression can be optimized for population queries",
            "benefit": "high"
        }
        result["opportunities"].append(pop_filter_opportunity)

        # Add to global list as well
        self.optimization_opportunities.append(pop_filter_opportunity)

        return result

    def visit_aggregation(self, node: 'AggregationNode') -> Dict[str, Any]:
        result = self._analyze_optimization(node)

        # Aggregations are prime optimization targets
        sql_agg_opportunity = {
            "type": "sql_aggregation",
            "reason": "Aggregation function can leverage database aggregation capabilities",
            "benefit": "very_high"
        }
        result["opportunities"].append(sql_agg_opportunity)

        # Add to global list as well
        self.optimization_opportunities.append(sql_agg_opportunity)

        return result

    def visit_type_operation(self, node: 'TypeOperationNode') -> Dict[str, Any]:
        return self._analyze_optimization(node)

    def get_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Get all optimization opportunities found"""
        return self.optimization_opportunities.copy()


# Utility function for creating visitor chains
def create_visitor_chain(*visitors: ASTVisitor) -> Callable[['FHIRPathASTNode'], List[Any]]:
    """
    Create a visitor chain that applies multiple visitors in sequence
    Returns a function that applies all visitors to a given node
    """
    def apply_visitors(node: 'FHIRPathASTNode') -> List[Any]:
        results = []
        for visitor in visitors:
            try:
                result = visitor.visit(node)
                results.append(result)
            except Exception as e:
                logging.error(f"Error in visitor {visitor.__class__.__name__}: {e}")
                results.append(None)
        return results

    return apply_visitors