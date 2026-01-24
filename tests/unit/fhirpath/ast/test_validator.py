"""
Tests for FHIRPath AST Validation Framework

Tests the comprehensive validation system for AST nodes,
including metadata validation, structural validation, and
compliance validation.
"""

import pytest
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.ast.validator import (
    CompositeValidator, MetadataValidator, StructuralValidator, ComplianceValidator,
    ValidationResult, ValidationIssue, ValidationSeverity,
    validate_ast_for_sql_generation, validate_ast_for_population_analytics
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


class TestValidationIssue:
    """Test ValidationIssue data class"""

    def test_validation_issue_creation(self):
        """Test creating validation issue"""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code="TEST_ERROR",
            message="Test error message",
            node_path="root.child",
            node_type="literal",
            node_text="test"
        )

        assert issue.severity == ValidationSeverity.ERROR
        assert issue.code == "TEST_ERROR"
        assert issue.message == "Test error message"
        assert issue.node_path == "root.child"
        assert issue.node_type == "literal"
        assert issue.node_text == "test"


class TestValidationResult:
    """Test ValidationResult functionality"""

    def test_validation_result_creation(self):
        """Test creating validation result"""
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "ERR1", "Error 1", "path1", "type1", "text1"),
            ValidationIssue(ValidationSeverity.WARNING, "WARN1", "Warning 1", "path2", "type2", "text2"),
            ValidationIssue(ValidationSeverity.INFO, "INFO1", "Info 1", "path3", "type3", "text3")
        ]

        result = ValidationResult(is_valid=False, issues=issues, nodes_validated=3)

        assert not result.is_valid
        assert len(result.issues) == 3
        assert result.nodes_validated == 3

    def test_get_errors(self):
        """Test getting only error-level issues"""
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "ERR1", "Error 1", "path1", "type1", "text1"),
            ValidationIssue(ValidationSeverity.WARNING, "WARN1", "Warning 1", "path2", "type2", "text2"),
            ValidationIssue(ValidationSeverity.ERROR, "ERR2", "Error 2", "path3", "type3", "text3")
        ]

        result = ValidationResult(is_valid=False, issues=issues)
        errors = result.get_errors()

        assert len(errors) == 2
        assert all(issue.severity == ValidationSeverity.ERROR for issue in errors)

    def test_get_warnings(self):
        """Test getting only warning-level issues"""
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "ERR1", "Error 1", "path1", "type1", "text1"),
            ValidationIssue(ValidationSeverity.WARNING, "WARN1", "Warning 1", "path2", "type2", "text2"),
            ValidationIssue(ValidationSeverity.WARNING, "WARN2", "Warning 2", "path3", "type3", "text3")
        ]

        result = ValidationResult(is_valid=False, issues=issues)
        warnings = result.get_warnings()

        assert len(warnings) == 2
        assert all(issue.severity == ValidationSeverity.WARNING for issue in warnings)

    def test_has_errors(self):
        """Test checking if result has errors"""
        # Result with errors
        error_result = ValidationResult(
            is_valid=False,
            issues=[ValidationIssue(ValidationSeverity.ERROR, "ERR1", "Error", "path", "type", "text")]
        )
        assert error_result.has_errors()

        # Result without errors
        warning_result = ValidationResult(
            is_valid=True,
            issues=[ValidationIssue(ValidationSeverity.WARNING, "WARN1", "Warning", "path", "type", "text")]
        )
        assert not warning_result.has_errors()


class TestMetadataValidator:
    """Test MetadataValidator"""

    def test_validate_node_with_no_metadata(self):
        """Test validating node with no metadata"""
        validator = MetadataValidator()
        node = LiteralNode("literal", "test")
        node.metadata = None

        issues = validator.validate_metadata(node, "root")

        assert len(issues) > 0
        assert any(issue.code == "METADATA_MISSING" for issue in issues)
        assert any(issue.severity == ValidationSeverity.WARNING for issue in issues)

    def test_validate_node_with_complete_metadata(self):
        """Test validating node with complete metadata"""
        validator = MetadataValidator()

        metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_type_info(TypeInformation(sql_data_type=SQLDataType.TEXT)) \
            .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
            .build()

        node = LiteralNode("literal", "test", value="hello")
        node.metadata = metadata

        issues = validator.validate_metadata(node, "root")

        # Should have minimal issues for complete metadata
        error_issues = [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 0

    def test_validate_missing_category(self):
        """Test validation when category is missing"""
        validator = MetadataValidator()

        # Create metadata without category (should not be possible with builder, but test anyway)
        metadata = Mock()
        metadata.node_category = None
        metadata.type_info = None
        metadata.optimization_hints = set()
        metadata.population_analytics = None
        metadata.cte_context = None

        node = LiteralNode("literal", "test")
        node.metadata = metadata

        issues = validator.validate_metadata(node, "root")

        assert any(issue.code == "CATEGORY_MISSING" for issue in issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in issues)

    def test_validate_unknown_sql_type(self):
        """Test validation when SQL type is unknown"""
        validator = MetadataValidator()

        metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_type_info(TypeInformation(sql_data_type=SQLDataType.UNKNOWN)) \
            .build()

        node = LiteralNode("literal", "test")
        node.metadata = metadata

        issues = validator.validate_metadata(node, "root")

        assert any(issue.code == "SQL_TYPE_UNKNOWN" for issue in issues)
        assert any(issue.severity == ValidationSeverity.WARNING for issue in issues)

    def test_validate_type_mismatch(self):
        """Test validation of type mismatches"""
        validator = MetadataValidator()

        # Create literal with string value but integer SQL type
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_type_info(TypeInformation(sql_data_type=SQLDataType.INTEGER)) \
            .build()

        node = LiteralNode("literal", "test", value="hello")  # String value
        node.metadata = metadata

        issues = validator.validate_metadata(node, "root")

        assert any(issue.code == "TYPE_MISMATCH" for issue in issues)

    def test_validate_aggregation_hints(self):
        """Test validation of aggregation-specific hints"""
        validator = MetadataValidator()

        # Aggregation node without aggregation hint
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.AGGREGATION) \
            .build()

        node = AggregationNode("aggregation", "count()")
        node.metadata = metadata

        issues = validator.validate_metadata(node, "root")

        assert any(issue.code == "MISSING_AGGREGATION_HINT" for issue in issues)

    def test_validate_conditional_hints(self):
        """Test validation of conditional node hints"""
        validator = MetadataValidator()

        metadata = MetadataBuilder() \
            .with_category(NodeCategory.CONDITIONAL) \
            .build()

        node = ConditionalNode("conditional", "where")
        node.metadata = metadata

        issues = validator.validate_metadata(node, "root")

        assert any(issue.code == "MISSING_FILTER_HINT" for issue in issues)


class TestStructuralValidator:
    """Test StructuralValidator"""

    def test_validate_parent_child_relationships(self):
        """Test validation of parent-child relationships"""
        validator = StructuralValidator()

        parent = LiteralNode("literal", "parent")
        child = LiteralNode("literal", "child")

        # Manually break parent-child relationship
        parent.children.append(child)
        # Don't set child.parent = parent

        issues = validator.validate_structure(parent, "root")

        assert any(issue.code == "PARENT_CHILD_MISMATCH" for issue in issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in issues)

    def test_validate_binary_operator_structure(self):
        """Test validation of binary operator structure"""
        validator = StructuralValidator()

        node = OperatorNode("operator", "=")

        # Add only one child (should need two)
        child = LiteralNode("literal", "test")
        node.add_child(child)

        # Set operator_type after adding child (add_child reclassifies)
        node.operator_type = "binary"

        issues = validator.validate_structure(node, "root")

        assert any(issue.code == "BINARY_OPERATOR_CHILDREN" for issue in issues)

    def test_validate_unary_operator_structure(self):
        """Test validation of unary operator structure"""
        validator = StructuralValidator()

        node = OperatorNode("operator", "not")
        node.operator_type = "unary"

        # Add two children (should need only one)
        child1 = LiteralNode("literal", "test1")
        child2 = LiteralNode("literal", "test2")
        node.add_child(child1)
        node.add_child(child2)

        issues = validator.validate_structure(node, "root")

        assert any(issue.code == "UNARY_OPERATOR_CHILDREN" for issue in issues)

    def test_validate_function_structure(self):
        """Test validation of function call structure"""
        validator = StructuralValidator()

        node = FunctionCallNode("functionCall", "test()")
        node.arguments = ["arg1", "arg2"]  # Two arguments
        # But add only one child
        child = LiteralNode("literal", "test")
        node.add_child(child)

        issues = validator.validate_structure(node, "root")

        assert any(issue.code == "FUNCTION_ARGS_CHILDREN_MISMATCH" for issue in issues)

    def test_validate_conditional_structure(self):
        """Test validation of conditional structure"""
        validator = StructuralValidator()

        node = ConditionalNode("conditional", "where")
        node.condition_type = "where"
        # No children (should have condition)

        issues = validator.validate_structure(node, "root")

        assert any(issue.code == "CONDITIONAL_NO_CONDITION" for issue in issues)


class TestComplianceValidator:
    """Test ComplianceValidator"""

    def test_validate_population_compliance(self):
        """Test population analytics compliance validation"""
        validator = ComplianceValidator()

        # Aggregation node that doesn't support population queries
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.AGGREGATION) \
            .build()
        metadata.population_analytics.supports_population_query = False

        node = AggregationNode("aggregation", "count()")
        node.metadata = metadata

        issues = validator.validate_compliance(node, "root")

        assert any(issue.code == "AGGREGATION_NOT_POPULATION_READY" for issue in issues)

    def test_validate_patient_context_consistency(self):
        """Test patient context consistency validation"""
        validator = ComplianceValidator()

        # Node requires patient context but doesn't support population queries
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.PATH_EXPRESSION) \
            .build()
        metadata.population_analytics.requires_patient_context = True
        metadata.population_analytics.supports_population_query = False

        node = IdentifierNode("identifier", "Patient.id")
        node.metadata = metadata

        issues = validator.validate_compliance(node, "root")

        assert any(issue.code == "PATIENT_CONTEXT_INCONSISTENT" for issue in issues)

    def test_validate_database_specific_logic(self):
        """Test detection of database-specific logic in AST"""
        validator = ComplianceValidator()

        node = LiteralNode("literal", "test")
        node.sql_fragment = "SELECT * FROM postgres_specific_table"

        issues = validator.validate_compliance(node, "root")

        assert any(issue.code == "DATABASE_SPECIFIC_LOGIC" for issue in issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in issues)


class TestCompositeValidator:
    """Test CompositeValidator"""

    def test_validate_valid_ast(self):
        """Test validation of completely valid AST"""
        validator = CompositeValidator(strict_mode=False)

        # Create valid AST
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_type_info(TypeInformation(sql_data_type=SQLDataType.TEXT)) \
            .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
            .build()

        root = LiteralNode("literal", "test", value="hello")
        root.metadata = metadata

        # Ensure validation passes
        root.validate()

        result = validator.validate_ast(root)

        assert result.is_valid
        assert len(result.get_errors()) == 0
        assert result.nodes_validated == 1
        assert result.validation_time_ms is not None

    def test_validate_invalid_ast(self):
        """Test validation of invalid AST"""
        validator = CompositeValidator(strict_mode=False)

        # Create invalid AST
        root = LiteralNode("literal", "test")
        root.value = None  # Invalid - no value

        result = validator.validate_ast(root)

        assert not result.is_valid
        assert len(result.get_errors()) > 0

    def test_strict_mode_validation(self):
        """Test validation in strict mode"""
        validator = CompositeValidator(strict_mode=True)

        # Create AST that has warnings
        node = LiteralNode("literal", "test", value="hello")
        node.metadata = None  # This will generate warnings

        result = validator.validate_ast(node)

        # In strict mode, warnings make AST invalid
        assert not result.is_valid

    def test_custom_validator_addition(self):
        """Test adding custom validators"""
        validator = CompositeValidator()

        # Add custom validator that always reports an issue
        def custom_validator(node, path):
            return [ValidationIssue(
                ValidationSeverity.INFO,
                "CUSTOM_ISSUE",
                "Custom validation issue",
                path,
                node.node_type,
                node.text
            )]

        validator.add_custom_validator(custom_validator)

        root = LiteralNode("literal", "test", value="hello")
        root.validate()

        result = validator.validate_ast(root)

        # Should have custom issue
        assert any(issue.code == "CUSTOM_ISSUE" for issue in result.issues)

    def test_exception_handling(self):
        """Test validation exception handling"""
        validator = CompositeValidator()

        # Mock a node that raises exception during validation
        root = Mock()
        root.validate.side_effect = Exception("Test error")
        root.children = []

        result = validator.validate_ast(root)

        assert not result.is_valid
        assert any(issue.code == "VALIDATION_EXCEPTION" for issue in result.issues)

    def test_complex_tree_validation(self):
        """Test validation of complex AST tree"""
        validator = CompositeValidator()

        # Build complex tree
        root = FunctionCallNode("functionCall", "where()")
        condition = OperatorNode("operator", "=")
        condition.operator = "="
        condition.operator_type = "binary"

        left = IdentifierNode("identifier", "Patient.active")
        left.identifier = "Patient.active"
        right = LiteralNode("literal", "true", value=True)

        condition.add_child(left)
        condition.add_child(right)
        root.add_child(condition)

        # Validate all nodes
        root.validate()
        condition.validate()
        left.validate()
        right.validate()

        result = validator.validate_ast(root)

        assert result.nodes_validated == 4  # All 4 nodes


class TestUtilityFunctions:
    """Test utility validation functions"""

    def test_validate_ast_for_sql_generation(self):
        """Test SQL generation specific validation"""
        # Create AST with unknown SQL type
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_type_info(TypeInformation(sql_data_type=SQLDataType.UNKNOWN)) \
            .build()

        root = LiteralNode("literal", "test", value="hello")
        root.metadata = metadata
        root.validate()

        result = validate_ast_for_sql_generation(root)

        # Should have warning about SQL type
        assert any(issue.code == "SQL_TYPE_REQUIRED" for issue in result.issues)

    def test_validate_ast_for_population_analytics(self):
        """Test population analytics specific validation"""
        # Create aggregation node without population support
        root = AggregationNode("aggregation", "count()")
        root.validate()

        result = validate_ast_for_population_analytics(root)

        # Should have error about population readiness
        assert any(issue.code == "AGGREGATION_NOT_POPULATION_READY" for issue in result.issues)

    def test_node_count_calculation(self):
        """Test node counting in validation"""
        validator = CompositeValidator()

        # Create tree with known number of nodes
        root = LiteralNode("literal", "root", value="root")
        child1 = LiteralNode("literal", "child1", value="child1")
        child2 = LiteralNode("literal", "child2", value="child2")

        root.add_child(child1)
        root.add_child(child2)

        # Validate all nodes
        root.validate()
        child1.validate()
        child2.validate()

        result = validator.validate_ast(root)

        assert result.nodes_validated == 3


if __name__ == "__main__":
    pytest.main([__file__])