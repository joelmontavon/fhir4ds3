"""
FHIR4DS FHIRPath AST Framework

This module provides a comprehensive AST framework for FHIRPath expressions,
building on the enhanced parser from SP-003-001 with additional validation,
visitor patterns, and serialization capabilities.

Key Components:
- Node Types: Strongly-typed AST nodes with validation
- Visitor Pattern: Framework for tree traversal and operations
- Validation: Comprehensive AST validation with error reporting
- Builder: AST construction from parser output
- Serialization: Enhanced serialization with metadata support

Example Usage:
    from fhir4ds.fhirpath.ast import ASTBuilder, CompositeValidator
    from fhir4ds.fhirpath.parser_core.enhanced_parser import EnhancedFHIRPathParser

    # Parse and build AST
    parser = EnhancedFHIRPathParser()
    parse_result = parser.parse("Patient.name.given")

    builder = ASTBuilder()
    ast = builder.build_from_enhanced_ast(parse_result.ast)

    # Validate AST
    validator = CompositeValidator()
    validation_result = validator.validate_ast(ast)

    if validation_result.is_valid:
        print("AST is valid!")
    else:
        for error in validation_result.get_errors():
            print(f"Error: {error.message}")
"""

from .nodes import (
    FHIRPathASTNode,
    LiteralNode,
    IdentifierNode,
    FunctionCallNode,
    OperatorNode,
    ConditionalNode,
    AggregationNode,
    TypeOperationNode,
    NodeTypeFactory
)

from .visitor import (
    ASTVisitor,
    DepthFirstTraversalVisitor,
    MetadataExtractionVisitor,
    ValidationVisitor,
    OptimizationAnalysisVisitor,
    create_visitor_chain
)

from .builder import (
    ASTBuilder,
    BuildContext,
    MetadataEnhancer,
    ASTRebuilder
)

from .validator import (
    CompositeValidator,
    MetadataValidator,
    StructuralValidator,
    ComplianceValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    validate_ast_for_sql_generation,
    validate_ast_for_population_analytics
)

from .serialization import (
    ASTSerializer,
    ASTDeserializer,
    SerializationFormat,
    serialize_ast_for_debugging,
    serialize_ast_for_caching,
    deserialize_ast_from_cache
)

# Version information
__version__ = "1.0.0"
__author__ = "FHIR4DS Development Team"

# Module-level convenience functions
def create_ast_from_expression(expression: str, database_type: str = "duckdb") -> FHIRPathASTNode:
    """
    Convenience function to create AST from FHIRPath expression

    Args:
        expression: FHIRPath expression string
        database_type: Target database type for optimizations

    Returns:
        Root AST node or None if parsing/building fails
    """
    try:
        from ..parser_core.enhanced_parser import EnhancedFHIRPathParser

        # Parse expression
        parser = EnhancedFHIRPathParser(database_type=database_type)
        parse_result = parser.parse(expression)

        if not parse_result.is_valid or not parse_result.ast:
            return None

        # Build typed AST
        context = BuildContext(database_type=database_type)
        builder = ASTBuilder(context)
        ast = builder.build_from_enhanced_ast(parse_result.ast)

        return ast

    except Exception:
        return None


def validate_ast(ast: FHIRPathASTNode, strict_mode: bool = False) -> ValidationResult:
    """
    Convenience function to validate an AST

    Args:
        ast: AST root node to validate
        strict_mode: Whether to treat warnings as errors

    Returns:
        ValidationResult with validation details
    """
    validator = CompositeValidator(strict_mode=strict_mode)
    return validator.validate_ast(ast)


def serialize_ast(ast: FHIRPathASTNode, format_type: str = SerializationFormat.JSON) -> str:
    """
    Convenience function to serialize an AST

    Args:
        ast: AST root node to serialize
        format_type: Target serialization format

    Returns:
        Serialized AST representation
    """
    serializer = ASTSerializer(include_metadata=True, include_stats=True)
    return serializer.serialize(ast, format_type)


# Public API
__all__ = [
    # Node classes
    "FHIRPathASTNode",
    "LiteralNode",
    "IdentifierNode",
    "FunctionCallNode",
    "OperatorNode",
    "ConditionalNode",
    "AggregationNode",
    "TypeOperationNode",
    "NodeTypeFactory",

    # Visitor classes
    "ASTVisitor",
    "DepthFirstTraversalVisitor",
    "MetadataExtractionVisitor",
    "ValidationVisitor",
    "OptimizationAnalysisVisitor",
    "create_visitor_chain",

    # Builder classes
    "ASTBuilder",
    "BuildContext",
    "MetadataEnhancer",
    "ASTRebuilder",

    # Validator classes
    "CompositeValidator",
    "MetadataValidator",
    "StructuralValidator",
    "ComplianceValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "validate_ast_for_sql_generation",
    "validate_ast_for_population_analytics",

    # Serialization classes
    "ASTSerializer",
    "ASTDeserializer",
    "SerializationFormat",
    "serialize_ast_for_debugging",
    "serialize_ast_for_caching",
    "deserialize_ast_from_cache",

    # Convenience functions
    "create_ast_from_expression",
    "validate_ast",
    "serialize_ast"
]