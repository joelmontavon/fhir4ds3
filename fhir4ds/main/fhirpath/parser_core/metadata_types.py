"""
FHIRPath AST Metadata Types for FHIR4DS CTE Generation

This module defines metadata types that enhance AST nodes with information
needed for SQL/CTE generation and population-scale analytics optimization.
"""

from typing import Dict, Any, List, Optional, Set, Union
from dataclasses import dataclass
from enum import Enum


class OptimizationHint(Enum):
    """Optimization hints for SQL generation"""
    POPULATION_FILTER = "population_filter"  # Can be pushed to WHERE clause
    PROJECTION_SAFE = "projection_safe"      # Safe for SELECT projection
    AGGREGATION_CANDIDATE = "aggregation_candidate"  # Can use SQL aggregation
    INDEX_FRIENDLY = "index_friendly"        # Benefits from database indexing
    CTE_REUSABLE = "cte_reusable"            # Should be extracted to CTE
    VECTORIZABLE = "vectorizable"            # Can be vectorized for performance


class NodeCategory(Enum):
    """Categories of FHIRPath AST nodes for CTE generation"""
    PATH_EXPRESSION = "path_expression"      # Resource navigation paths
    FUNCTION_CALL = "function_call"          # Function invocations
    LITERAL = "literal"                      # Literal values
    OPERATOR = "operator"                    # Binary/unary operators
    CONDITIONAL = "conditional"              # where(), select() conditions
    AGGREGATION = "aggregation"              # count(), sum(), etc.
    TYPE_OPERATION = "type_operation"        # as(), is(), ofType()


class SQLDataType(Enum):
    """SQL data types for type inference"""
    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    JSON = "json"
    ARRAY = "array"
    UNKNOWN = "unknown"


@dataclass
class TypeInformation:
    """Type information for FHIRPath expressions"""
    expected_input_type: Optional[str] = None
    expected_output_type: Optional[str] = None
    sql_data_type: SQLDataType = SQLDataType.UNKNOWN
    is_collection: bool = False
    is_nullable: bool = True
    fhir_type: Optional[str] = None


@dataclass
class PerformanceMetadata:
    """Performance-related metadata for optimization"""
    estimated_selectivity: Optional[float] = None  # 0.0 to 1.0
    supports_indexing: bool = False
    memory_intensive: bool = False
    cpu_intensive: bool = False
    io_intensive: bool = False


@dataclass
class CTEGenerationContext:
    """Context information for CTE generation"""
    requires_join: bool = False
    join_conditions: List[str] = None
    dependent_tables: Set[str] = None
    can_be_subquery: bool = True
    requires_window_function: bool = False

    def __post_init__(self):
        if self.join_conditions is None:
            self.join_conditions = []
        if self.dependent_tables is None:
            self.dependent_tables = set()


@dataclass
class PopulationAnalyticsMetadata:
    """Metadata specific to population-scale analytics"""
    supports_population_query: bool = True
    requires_patient_context: bool = False
    can_be_population_filtered: bool = False
    aggregation_level: Optional[str] = None  # "patient", "encounter", "population"


@dataclass
class ASTNodeMetadata:
    """Comprehensive metadata for AST nodes in FHIR4DS"""
    node_category: NodeCategory
    type_info: TypeInformation
    optimization_hints: Set[OptimizationHint]
    performance: PerformanceMetadata
    cte_context: CTEGenerationContext
    population_analytics: PopulationAnalyticsMetadata

    # Additional metadata
    source_text: str = ""
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    custom_attributes: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_attributes is None:
            self.custom_attributes = {}


class MetadataBuilder:
    """Builder for creating AST node metadata"""

    def __init__(self):
        self.reset()

    def reset(self) -> 'MetadataBuilder':
        """Reset builder to default state"""
        self._node_category = NodeCategory.PATH_EXPRESSION
        self._type_info = TypeInformation()
        self._optimization_hints = set()
        self._performance = PerformanceMetadata()
        self._cte_context = CTEGenerationContext()
        self._population_analytics = PopulationAnalyticsMetadata()
        self._source_text = ""
        self._line_number = None
        self._column_number = None
        self._custom_attributes = {}
        return self

    def with_category(self, category: NodeCategory) -> 'MetadataBuilder':
        """Set node category"""
        self._node_category = category
        return self

    def with_type_info(self, type_info: TypeInformation) -> 'MetadataBuilder':
        """Set type information"""
        self._type_info = type_info
        return self

    def with_optimization_hint(self, hint: OptimizationHint) -> 'MetadataBuilder':
        """Add optimization hint"""
        self._optimization_hints.add(hint)
        return self

    def with_performance(self, performance: PerformanceMetadata) -> 'MetadataBuilder':
        """Set performance metadata"""
        self._performance = performance
        return self

    def with_cte_context(self, cte_context: CTEGenerationContext) -> 'MetadataBuilder':
        """Set CTE generation context"""
        self._cte_context = cte_context
        return self

    def with_population_analytics(self, pop_analytics: PopulationAnalyticsMetadata) -> 'MetadataBuilder':
        """Set population analytics metadata"""
        self._population_analytics = pop_analytics
        return self

    def with_source_location(self, text: str, line: Optional[int] = None,
                           column: Optional[int] = None) -> 'MetadataBuilder':
        """Set source location information"""
        self._source_text = text
        self._line_number = line
        self._column_number = column
        return self

    def with_custom_attribute(self, key: str, value: Any) -> 'MetadataBuilder':
        """Add custom attribute"""
        self._custom_attributes[key] = value
        return self

    def build(self) -> ASTNodeMetadata:
        """Build the metadata object"""
        return ASTNodeMetadata(
            node_category=self._node_category,
            type_info=self._type_info,
            optimization_hints=self._optimization_hints.copy(),
            performance=self._performance,
            cte_context=self._cte_context,
            population_analytics=self._population_analytics,
            source_text=self._source_text,
            line_number=self._line_number,
            column_number=self._column_number,
            custom_attributes=self._custom_attributes.copy()
        )

    @staticmethod
    def create_node_metadata(node_type: str, text: str) -> ASTNodeMetadata:
        """
        Create metadata for a node based on node_type and text.

        Categorizes nodes properly for visitor pattern routing.

        Args:
            node_type: The AST node type (e.g., "AdditiveExpression", "NumberLiteral")
            text: The text content of the node

        Returns:
            ASTNodeMetadata with appropriate categorization
        """
        builder = MetadataBuilder()

        # Categorize based on node_type
        if node_type in ['NumberLiteral', 'StringLiteral', 'BooleanLiteral', 'DateLiteral',
                          'DateTimeLiteral', 'TimeLiteral', 'QuantityLiteral']:
            # Literal nodes
            builder.with_category(NodeCategory.LITERAL)
        elif node_type in ['AdditiveExpression', 'MultiplicativeExpression', 'UnaryExpression',
                           'InequalityExpression', 'EqualityExpression', 'AndExpression',
                           'OrExpression', 'XorExpression', 'ImpliesExpression', 'UnionExpression']:
            # Operator nodes
            builder.with_category(NodeCategory.OPERATOR)
        elif node_type in ['FunctionInvocation', 'MemberInvocation']:
            # Function call nodes
            builder.with_category(NodeCategory.FUNCTION_CALL)
        elif node_type in ['Identifier', 'InvocationExpression', 'TermExpression',
                           'IndexerExpression']:
            # Check if InvocationExpression is actually a conditional or complex chain
            # If it contains where/select/exists OR any function call (indicated by parentheses),
            # treat as CONDITIONAL to force generic traversal instead of simple path extraction
            if node_type == 'InvocationExpression' and ('(' in text and ')' in text):
                builder.with_category(NodeCategory.CONDITIONAL)
            else:
                # Path expression / identifier nodes
                builder.with_category(NodeCategory.PATH_EXPRESSION)
        elif node_type == 'PolarityExpression':
            # SP-024-001: PolarityExpression is a unary operator (+/-) not a path expression
            builder.with_category(NodeCategory.OPERATOR)
        elif node_type in ['TypeSpecifier', 'TypeExpression']:
            # Type operation nodes
            builder.with_category(NodeCategory.TYPE_OPERATION)
        else:
            # Default to PATH_EXPRESSION for unknown types
            builder.with_category(NodeCategory.PATH_EXPRESSION)

        return builder.with_source_location(text).build()


# Predefined metadata template functions for common node types
def _create_patient_path_template():
    return MetadataBuilder() \
        .with_category(NodeCategory.PATH_EXPRESSION) \
        .with_type_info(TypeInformation(
            expected_input_type="Patient",
            expected_output_type="Patient",
            sql_data_type=SQLDataType.JSON,
            fhir_type="Patient"
        )) \
        .with_optimization_hint(OptimizationHint.POPULATION_FILTER) \
        .with_population_analytics(PopulationAnalyticsMetadata(
            supports_population_query=True,
            requires_patient_context=True,
            can_be_population_filtered=True,
            aggregation_level="patient"
        )) \
        .build()

def _create_count_function_template():
    return MetadataBuilder() \
        .with_category(NodeCategory.AGGREGATION) \
        .with_type_info(TypeInformation(
            expected_output_type="integer",
            sql_data_type=SQLDataType.INTEGER,
            is_collection=False
        )) \
        .with_optimization_hint(OptimizationHint.AGGREGATION_CANDIDATE) \
        .with_optimization_hint(OptimizationHint.VECTORIZABLE) \
        .with_population_analytics(PopulationAnalyticsMetadata(
            supports_population_query=True,
            aggregation_level="population"
        )) \
        .build()

def _create_string_literal_template():
    return MetadataBuilder() \
        .with_category(NodeCategory.LITERAL) \
        .with_type_info(TypeInformation(
            expected_output_type="string",
            sql_data_type=SQLDataType.TEXT,
            is_collection=False,
            is_nullable=False
        )) \
        .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
        .build()

# Template factory dictionary
METADATA_TEMPLATES = {
    "patient_path": _create_patient_path_template,
    "count_function": _create_count_function_template,
    "string_literal": _create_string_literal_template,
}