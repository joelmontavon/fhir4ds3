"""
AST Validation Framework for FHIR4DS FHIRPath Engine

This module provides comprehensive validation capabilities for FHIRPath AST
trees, ensuring metadata completeness, structural integrity, and compliance
with FHIR4DS architectural requirements.
"""

from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import logging

from .nodes import (
    FHIRPathASTNode, LiteralNode, IdentifierNode, FunctionCallNode,
    OperatorNode, ConditionalNode, AggregationNode, TypeOperationNode
)
from .visitor import ValidationVisitor
from ..parser_core.metadata_types import (
    ASTNodeMetadata, NodeCategory, OptimizationHint, SQLDataType
)


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue found in the AST"""
    severity: ValidationSeverity
    code: str
    message: str
    node_path: str
    node_type: str
    node_text: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    suggested_fix: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of AST validation"""
    is_valid: bool
    issues: List[ValidationIssue]
    validation_time_ms: Optional[float] = None
    nodes_validated: int = 0

    def get_errors(self) -> List[ValidationIssue]:
        """Get only error-level issues"""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues"""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]

    def has_errors(self) -> bool:
        """Check if validation result has errors"""
        return len(self.get_errors()) > 0


class MetadataValidator:
    """Validates AST node metadata for completeness and correctness"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_metadata(self, node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        """Validate metadata for a single node"""
        issues = []

        if not node.metadata:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="METADATA_MISSING",
                message="Node has no metadata",
                node_path=path,
                node_type=node.node_type,
                node_text=node.text,
                suggested_fix="Add metadata using MetadataBuilder"
            ))
            return issues

        metadata = node.metadata

        # Validate node category
        if not metadata.node_category:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CATEGORY_MISSING",
                message="Node category is missing",
                node_path=path,
                node_type=node.node_type,
                node_text=node.text
            ))

        # Validate type information
        if not metadata.type_info:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="TYPE_INFO_MISSING",
                message="Type information is missing",
                node_path=path,
                node_type=node.node_type,
                node_text=node.text
            ))
        else:
            issues.extend(self._validate_type_info(metadata.type_info, node, path))

        # Validate optimization hints
        issues.extend(self._validate_optimization_hints(metadata.optimization_hints, node, path))

        # Validate population analytics metadata
        if not metadata.population_analytics:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="POPULATION_METADATA_MISSING",
                message="Population analytics metadata is missing",
                node_path=path,
                node_type=node.node_type,
                node_text=node.text
            ))

        # Validate CTE context
        if not metadata.cte_context:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="CTE_CONTEXT_MISSING",
                message="CTE generation context is missing",
                node_path=path,
                node_type=node.node_type,
                node_text=node.text
            ))

        return issues

    def _validate_type_info(self, type_info, node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        """Validate type information"""
        issues = []

        # Validate SQL data type
        if type_info.sql_data_type == SQLDataType.UNKNOWN:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="SQL_TYPE_UNKNOWN",
                message="SQL data type is unknown",
                node_path=path,
                node_type=node.node_type,
                node_text=node.text,
                suggested_fix="Specify appropriate SQL data type"
            ))

        # Validate type consistency
        if isinstance(node, LiteralNode):
            expected_sql_type = self._infer_literal_sql_type(node)
            if expected_sql_type and type_info.sql_data_type != expected_sql_type:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="TYPE_MISMATCH",
                    message=f"SQL type {type_info.sql_data_type.value} doesn't match inferred type {expected_sql_type.value}",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text
                ))

        return issues

    def _validate_optimization_hints(self, hints: Set[OptimizationHint], node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        """Validate optimization hints"""
        issues = []

        # Check for conflicting hints
        if OptimizationHint.PROJECTION_SAFE in hints and OptimizationHint.AGGREGATION_CANDIDATE in hints:
            # This could be valid for some functions, so just warn
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="HINT_COMBINATION",
                message="Node has both projection_safe and aggregation_candidate hints",
                node_path=path,
                node_type=node.node_type,
                node_text=node.text
            ))

        # Validate hint appropriateness for node type
        if isinstance(node, AggregationNode):
            if OptimizationHint.AGGREGATION_CANDIDATE not in hints:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_AGGREGATION_HINT",
                    message="Aggregation node should have AGGREGATION_CANDIDATE hint",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text,
                    suggested_fix="Add OptimizationHint.AGGREGATION_CANDIDATE"
                ))

        if isinstance(node, ConditionalNode):
            if OptimizationHint.POPULATION_FILTER not in hints:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="MISSING_FILTER_HINT",
                    message="Conditional node could benefit from POPULATION_FILTER hint",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text,
                    suggested_fix="Consider adding OptimizationHint.POPULATION_FILTER"
                ))

        return issues

    def _infer_literal_sql_type(self, literal_node: LiteralNode) -> Optional[SQLDataType]:
        """Infer SQL data type from literal value"""
        if not hasattr(literal_node, 'value') or literal_node.value is None:
            return None

        value = literal_node.value
        if isinstance(value, bool):
            return SQLDataType.BOOLEAN
        elif isinstance(value, int):
            return SQLDataType.INTEGER
        elif isinstance(value, float):
            return SQLDataType.DECIMAL
        elif isinstance(value, str):
            return SQLDataType.TEXT

        return None


class StructuralValidator:
    """Validates AST structural integrity"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_structure(self, node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        """Validate structural integrity of a node"""
        issues = []

        # Validate parent-child relationships
        for i, child in enumerate(node.children):
            child_path = f"{path}[{i}]"

            if child.parent != node:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="PARENT_CHILD_MISMATCH",
                    message="Child node parent reference doesn't match actual parent",
                    node_path=child_path,
                    node_type=child.node_type,
                    node_text=child.text,
                    suggested_fix="Fix parent-child relationship"
                ))

        # Validate node-specific structure
        issues.extend(self._validate_node_specific_structure(node, path))

        return issues

    def _validate_node_specific_structure(self, node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        """Validate structure specific to node type"""
        issues = []

        if isinstance(node, OperatorNode):
            issues.extend(self._validate_operator_structure(node, path))
        elif isinstance(node, FunctionCallNode):
            issues.extend(self._validate_function_structure(node, path))
        elif isinstance(node, ConditionalNode):
            issues.extend(self._validate_conditional_structure(node, path))

        return issues

    def _validate_operator_structure(self, node: OperatorNode, path: str) -> List[ValidationIssue]:
        """Validate operator node structure"""
        issues = []

        if hasattr(node, 'operator_type'):
            if node.operator_type == "binary" and len(node.children) != 2:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="BINARY_OPERATOR_CHILDREN",
                    message=f"Binary operator has {len(node.children)} children, expected 2",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text
                ))
            elif node.operator_type == "unary" and len(node.children) != 1:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="UNARY_OPERATOR_CHILDREN",
                    message=f"Unary operator has {len(node.children)} children, expected 1",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text
                ))

        return issues

    def _validate_function_structure(self, node: FunctionCallNode, path: str) -> List[ValidationIssue]:
        """Validate function call node structure"""
        issues = []

        if hasattr(node, 'arguments') and hasattr(node, 'children'):
            if len(node.arguments) != len(node.children):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="FUNCTION_ARGS_CHILDREN_MISMATCH",
                    message=f"Function has {len(node.arguments)} arguments but {len(node.children)} children",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text
                ))

        return issues

    def _validate_conditional_structure(self, node: ConditionalNode, path: str) -> List[ValidationIssue]:
        """Validate conditional node structure"""
        issues = []

        if hasattr(node, 'condition_type'):
            if node.condition_type in ["where", "select"] and len(node.children) == 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="CONDITIONAL_NO_CONDITION",
                    message=f"Conditional '{node.condition_type}' has no condition",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text
                ))

        return issues


class ComplianceValidator:
    """Validates AST compliance with FHIR4DS architecture requirements"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_compliance(self, node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        """Validate architectural compliance"""
        issues = []

        # Validate population-scale analytics compliance
        issues.extend(self._validate_population_compliance(node, path))

        # Validate CTE generation compliance
        issues.extend(self._validate_cte_compliance(node, path))

        # Validate database dialect compliance
        issues.extend(self._validate_dialect_compliance(node, path))

        return issues

    def _validate_population_compliance(self, node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        """Validate population-scale analytics compliance"""
        issues = []

        if node.metadata and node.metadata.population_analytics:
            pop_metadata = node.metadata.population_analytics

            # Check for population-scale readiness
            if isinstance(node, AggregationNode):
                if not pop_metadata.supports_population_query:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="AGGREGATION_NOT_POPULATION_READY",
                        message="Aggregation node should support population queries",
                        node_path=path,
                        node_type=node.node_type,
                        node_text=node.text,
                        suggested_fix="Set supports_population_query=True"
                    ))

            # Check for proper patient context handling
            if pop_metadata.requires_patient_context and not pop_metadata.supports_population_query:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="PATIENT_CONTEXT_INCONSISTENT",
                    message="Node requires patient context but doesn't support population queries",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text
                ))

        return issues

    def _validate_cte_compliance(self, node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        """Validate CTE generation compliance"""
        issues = []

        if node.metadata and node.metadata.cte_context:
            cte_context = node.metadata.cte_context

            # Check for CTE extraction appropriateness
            if OptimizationHint.CTE_REUSABLE in node.metadata.optimization_hints:
                if not cte_context.can_be_subquery:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        code="CTE_REUSABLE_NOT_SUBQUERY",
                        message="Node marked as CTE reusable but cannot be subquery",
                        node_path=path,
                        node_type=node.node_type,
                        node_text=node.text
                    ))

        return issues

    def _validate_dialect_compliance(self, node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        """Validate database dialect compliance"""
        issues = []

        # Ensure no database-specific business logic in AST
        if hasattr(node, 'sql_fragment') and node.sql_fragment:
            if any(db in node.sql_fragment.lower() for db in ['postgres', 'duckdb', 'sqlite']):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DATABASE_SPECIFIC_LOGIC",
                    message="AST contains database-specific logic - violates thin dialect principle",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text,
                    suggested_fix="Move database-specific logic to dialect layer"
                ))

        return issues


class CompositeValidator:
    """
    Comprehensive AST validator that combines all validation types

    Orchestrates metadata, structural, and compliance validation to provide
    complete AST validation with detailed reporting.
    """

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.metadata_validator = MetadataValidator()
        self.structural_validator = StructuralValidator()
        self.compliance_validator = ComplianceValidator()
        self.logger = logging.getLogger(__name__)

        # Custom validation rules
        self.custom_validators: List[Callable[[FHIRPathASTNode, str], List[ValidationIssue]]] = []

    def add_custom_validator(self, validator: Callable[[FHIRPathASTNode, str], List[ValidationIssue]]) -> None:
        """Add a custom validation function"""
        self.custom_validators.append(validator)

    def validate_ast(self, root: FHIRPathASTNode) -> ValidationResult:
        """
        Perform comprehensive validation of an AST tree

        Args:
            root: Root node of the AST to validate

        Returns:
            ValidationResult with comprehensive validation information
        """
        import time
        start_time = time.time()

        all_issues = []
        nodes_validated = 0

        try:
            # Use visitor pattern for thorough traversal
            validation_visitor = ValidationVisitor()
            tree_is_valid = validation_visitor.visit(root)

            # Add visitor errors to our issues
            for error_info in validation_visitor.get_validation_errors():
                all_issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="NODE_VALIDATION_FAILED",
                    message=error_info["error"],
                    node_path=error_info["path"],
                    node_type=error_info["node_type"],
                    node_text=error_info["node_text"]
                ))

            # Perform detailed validation using depth-first traversal
            self._validate_tree_recursive(root, "root", all_issues)
            nodes_validated = self._count_nodes(root)

            # Determine overall validity
            is_valid = not any(issue.severity == ValidationSeverity.ERROR for issue in all_issues)

            if self.strict_mode:
                # In strict mode, warnings also make the AST invalid
                is_valid = is_valid and not any(issue.severity == ValidationSeverity.WARNING for issue in all_issues)

            validation_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            return ValidationResult(
                is_valid=is_valid,
                issues=all_issues,
                validation_time_ms=validation_time,
                nodes_validated=nodes_validated
            )

        except Exception as e:
            self.logger.error(f"Error during AST validation: {e}")
            all_issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VALIDATION_EXCEPTION",
                message=f"Validation failed with exception: {str(e)}",
                node_path="unknown",
                node_type="unknown",
                node_text="unknown"
            ))

            return ValidationResult(
                is_valid=False,
                issues=all_issues,
                validation_time_ms=(time.time() - start_time) * 1000,
                nodes_validated=nodes_validated
            )

    def _validate_tree_recursive(self, node: FHIRPathASTNode, path: str, issues: List[ValidationIssue]) -> None:
        """Recursively validate tree nodes"""
        # Validate metadata
        issues.extend(self.metadata_validator.validate_metadata(node, path))

        # Validate structure
        issues.extend(self.structural_validator.validate_structure(node, path))

        # Validate compliance
        issues.extend(self.compliance_validator.validate_compliance(node, path))

        # Apply custom validators
        for custom_validator in self.custom_validators:
            try:
                issues.extend(custom_validator(node, path))
            except Exception as e:
                self.logger.error(f"Custom validator failed: {e}")
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CUSTOM_VALIDATOR_FAILED",
                    message=f"Custom validator failed: {str(e)}",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text
                ))

        # Recursively validate children
        for i, child in enumerate(node.children):
            child_path = f"{path}.{child.node_type}[{i}]"
            self._validate_tree_recursive(child, child_path, issues)

    def _count_nodes(self, node: FHIRPathASTNode) -> int:
        """Count total nodes in tree"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count


# Utility functions for common validation scenarios
def validate_ast_for_sql_generation(root: FHIRPathASTNode) -> ValidationResult:
    """Validate AST specifically for SQL generation readiness"""
    validator = CompositeValidator(strict_mode=False)

    # Add SQL-specific validation
    def sql_readiness_validator(node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        issues = []

        if node.metadata and node.metadata.type_info:
            if node.metadata.type_info.sql_data_type == SQLDataType.UNKNOWN:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="SQL_TYPE_REQUIRED",
                    message="SQL data type must be specified for SQL generation",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text
                ))

        return issues

    validator.add_custom_validator(sql_readiness_validator)
    return validator.validate_ast(root)


def validate_ast_for_population_analytics(root: FHIRPathASTNode) -> ValidationResult:
    """Validate AST specifically for population-scale analytics"""
    validator = CompositeValidator(strict_mode=False)

    # Add population analytics specific validation
    def population_readiness_validator(node: FHIRPathASTNode, path: str) -> List[ValidationIssue]:
        issues = []

        if isinstance(node, AggregationNode):
            if not node.metadata or not node.metadata.population_analytics.supports_population_query:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="AGGREGATION_NOT_POPULATION_READY",
                    message="Aggregation nodes must support population queries",
                    node_path=path,
                    node_type=node.node_type,
                    node_text=node.text
                ))

        return issues

    validator.add_custom_validator(population_readiness_validator)
    return validator.validate_ast(root)