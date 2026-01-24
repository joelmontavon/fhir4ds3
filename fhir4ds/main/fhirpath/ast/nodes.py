"""
AST Node Type Definitions for FHIR4DS FHIRPath Engine

This module defines the complete node type hierarchy for FHIRPath expressions,
extending the enhanced AST from SP-003-001 with additional node types and
validation capabilities.
"""

from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json

from ..parser_core.ast_extensions import EnhancedASTNode
from ..parser_core.metadata_types import (
    ASTNodeMetadata, NodeCategory, OptimizationHint,
    TypeInformation, SQLDataType
)


class FHIRPathASTNode(EnhancedASTNode):
    """
    Base class for all FHIRPath AST nodes with enhanced validation and metadata

    Extends EnhancedASTNode from SP-003-001 with additional validation methods
    and standardized interfaces for FHIR4DS integration.
    """

    def __init__(self, node_type: str, text: str, **kwargs):
        super().__init__(node_type, text, **kwargs)
        self._validation_errors: List[str] = []
        self._is_validated: bool = False

    @abstractmethod
    def validate(self) -> bool:
        """Validate this node and its children. Returns True if valid."""
        pass

    @abstractmethod
    def accept(self, visitor: 'ASTVisitor') -> Any:
        """Accept a visitor for traversal operations"""
        pass

    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors for this node"""
        return self._validation_errors.copy()

    def is_valid(self) -> bool:
        """Check if node has been validated and is valid"""
        return self._is_validated and len(self._validation_errors) == 0

    def add_validation_error(self, error: str) -> None:
        """Add a validation error"""
        self._validation_errors.append(error)

    def clear_validation_errors(self) -> None:
        """Clear validation errors"""
        self._validation_errors.clear()
        self._is_validated = False


@dataclass
class LiteralNode(FHIRPathASTNode):
    """Node representing literal values (strings, numbers, booleans)"""

    value: Any = None
    literal_type: str = "unknown"

    def __post_init__(self):
        if self.node_type != "literal":
            self.node_type = "literal"
        # Initialize validation attributes if not already set
        if not hasattr(self, '_validation_errors'):
            self._validation_errors = []
        if not hasattr(self, '_is_validated'):
            self._is_validated = False
        self._infer_literal_type()

    def _infer_literal_type(self):
        """Infer the literal type from the value"""
        if isinstance(self.value, bool):
            self.literal_type = "boolean"
        elif isinstance(self.value, int):
            self.literal_type = "integer"
        elif isinstance(self.value, float):
            self.literal_type = "decimal"
        elif isinstance(self.value, str):
            self.literal_type = "string"
        else:
            self.literal_type = "unknown"

    def validate(self) -> bool:
        """Validate literal node"""
        self.clear_validation_errors()

        if self.value is None and self.text != "{}":
            self.add_validation_error("Literal node must have a value or be empty")

        if self.literal_type == "unknown" and self.value is not None:
            self.add_validation_error(f"Unknown literal type for value: {self.value}")

        self._is_validated = True
        return len(self._validation_errors) == 0

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_literal(self)


@dataclass
class IdentifierNode(FHIRPathASTNode):
    """Node representing identifiers and path expressions"""

    identifier: str = ""
    is_qualified: bool = False

    def __post_init__(self):
        if self.node_type != "identifier":
            self.node_type = "identifier"
        # Initialize validation attributes if not already set
        if not hasattr(self, '_validation_errors'):
            self._validation_errors = []
        if not hasattr(self, '_is_validated'):
            self._is_validated = False
        if not self.identifier:
            self.identifier = self.text

    def validate(self) -> bool:
        """Validate identifier node"""
        self.clear_validation_errors()

        if not self.identifier:
            self.add_validation_error("Identifier cannot be empty")

        # Basic identifier validation (alphanumeric + underscore, no spaces)
        sanitized = self.identifier.replace("_", "").replace(".", "").replace("`", "")
        if sanitized and not sanitized.isalnum():
            self.add_validation_error(f"Invalid identifier format: {self.identifier}")

        self._is_validated = True
        return len(self._validation_errors) == 0

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_identifier(self)


@dataclass
class FunctionCallNode(FHIRPathASTNode):
    """Node representing function calls"""

    function_name: str = ""
    arguments: List[FHIRPathASTNode] = field(default_factory=list)
    target: Optional[FHIRPathASTNode] = None

    def __post_init__(self):
        if self.node_type != "functionCall":
            self.node_type = "functionCall"
        # Initialize validation attributes if not already set
        if not hasattr(self, '_validation_errors'):
            self._validation_errors = []
        if not hasattr(self, '_is_validated'):
            self._is_validated = False
        if not self.function_name:
            # Extract function name from text
            if "(" in self.text:
                self.function_name = self.text.split("(")[0].strip()
            else:
                self.function_name = self.text

    def validate(self) -> bool:
        """Validate function call node"""
        self.clear_validation_errors()

        if not self.function_name:
            self.add_validation_error("Function name cannot be empty")

        # Validate function name format
        if not self.function_name.replace("_", "").isalnum():
            self.add_validation_error(f"Invalid function name: {self.function_name}")

        # Validate arguments
        for i, arg in enumerate(self.arguments):
            if not arg.validate():
                self.add_validation_error(f"Invalid argument {i}: {arg.get_validation_errors()}")

        # Validate target expression if provided
        if self.target is not None and not self.target.validate():
            self.add_validation_error(f"Invalid target expression: {self.target.get_validation_errors()}")

        self._is_validated = True
        return len(self._validation_errors) == 0

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_function_call(self)


@dataclass
class OperatorNode(FHIRPathASTNode):
    """Node representing operators (binary, unary)"""

    operator: str = ""
    operator_type: str = "unknown"  # "binary", "unary", "comparison", "logical"
    left_operand: Optional[FHIRPathASTNode] = None
    right_operand: Optional[FHIRPathASTNode] = None

    def __post_init__(self):
        if self.node_type != "operator":
            self.node_type = "operator"
        # Initialize validation attributes if not already set
        if not hasattr(self, '_validation_errors'):
            self._validation_errors = []
        if not hasattr(self, '_is_validated'):
            self._is_validated = False
        if not self.operator:
            self.operator = self.text
        self._classify_operator()

    def _classify_operator(self):
        """Classify the operator type"""
        comparison_ops = {"=", "!=", "<", ">", "<=", ">=", "~", "!~"}
        logical_ops = {"and", "or", "xor", "implies"}
        union_ops = {"|", "union"}
        unary_only_ops = {"not"}  # Operators that are only unary

        # First check for operators that have specific types regardless of children
        if self.operator in comparison_ops:
            self.operator_type = "comparison"
        elif self.operator in logical_ops:
            self.operator_type = "logical"
        elif self.operator in union_ops:
            self.operator_type = "union"
        elif self.operator in unary_only_ops:
            self.operator_type = "unary"
        # For operators that can be both unary and binary (like +, -), check children count
        elif len(self.children) == 1:
            self.operator_type = "unary"
        elif len(self.children) == 2:
            self.operator_type = "binary"
        else:
            self.operator_type = "unknown"

    def validate(self) -> bool:
        """Validate operator node"""
        self.clear_validation_errors()

        if not self.operator:
            self.add_validation_error("Operator cannot be empty")

        # Validate operands based on operator type
        if self.operator_type == "unary":
            if len(self.children) != 1:
                self.add_validation_error("Unary operator must have exactly one operand")
        elif self.operator_type in ["binary", "comparison", "logical", "union"]:
            if len(self.children) != 2:
                self.add_validation_error(f"{self.operator_type} operator must have exactly two operands")

        # Validate child nodes
        for child in self.children:
            if not child.validate():
                self.add_validation_error(f"Invalid operand: {child.get_validation_errors()}")

        self._is_validated = True
        return len(self._validation_errors) == 0

    def add_child(self, child: 'FHIRPathASTNode') -> None:
        """Add a child node and reclassify operator type"""
        super().add_child(child)
        # Reclassify operator type now that we have children
        self._classify_operator()

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_operator(self)


@dataclass
class ConditionalNode(FHIRPathASTNode):
    """Node representing conditional expressions (where, select)"""

    condition: Optional[FHIRPathASTNode] = None
    condition_type: str = "where"  # "where", "select", "exists"

    def __post_init__(self):
        if self.node_type != "conditional":
            self.node_type = "conditional"
        # Initialize validation attributes if not already set
        if not hasattr(self, '_validation_errors'):
            self._validation_errors = []
        if not hasattr(self, '_is_validated'):
            self._is_validated = False
        # Extract condition type from function name if applicable
        if self.text.startswith(("where", "select", "exists")):
            self.condition_type = self.text.split("(")[0].strip()

    def validate(self) -> bool:
        """Validate conditional node"""
        self.clear_validation_errors()

        if self.condition_type not in ["where", "select", "exists"]:
            self.add_validation_error(f"Invalid condition type: {self.condition_type}")

        # For where/select, we need a condition
        if self.condition_type in ["where", "select"]:
            if not self.condition and len(self.children) == 0:
                self.add_validation_error("Conditional expression requires a condition")

        # Validate condition if present
        if self.condition and not self.condition.validate():
            self.add_validation_error(f"Invalid condition: {self.condition.get_validation_errors()}")

        # Validate children
        for child in self.children:
            if not child.validate():
                self.add_validation_error(f"Invalid child: {child.get_validation_errors()}")

        self._is_validated = True
        return len(self._validation_errors) == 0

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_conditional(self)


@dataclass
class AggregationNode(FHIRPathASTNode):
    """Node representing aggregation functions (count, sum, avg, etc.)"""

    aggregation_function: str = ""
    aggregation_type: str = "count"  # "count", "sum", "avg", "min", "max"

    def __post_init__(self):
        if self.node_type != "aggregation":
            self.node_type = "aggregation"
        # Initialize validation attributes if not already set
        if not hasattr(self, '_validation_errors'):
            self._validation_errors = []
        if not hasattr(self, '_is_validated'):
            self._is_validated = False
        if not self.aggregation_function:
            self.aggregation_function = self.text.split("(")[0].strip()
        self.aggregation_type = self.aggregation_function.lower()

    def validate(self) -> bool:
        """Validate aggregation node"""
        self.clear_validation_errors()

        valid_functions = {"count", "sum", "avg", "min", "max", "distinct"}
        if self.aggregation_type not in valid_functions:
            self.add_validation_error(f"Invalid aggregation function: {self.aggregation_function}")

        # Validate children
        for child in self.children:
            if not child.validate():
                self.add_validation_error(f"Invalid child: {child.get_validation_errors()}")

        self._is_validated = True
        return len(self._validation_errors) == 0

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_aggregation(self)


@dataclass
class TypeOperationNode(FHIRPathASTNode):
    """Node representing type operations (as, is, ofType)"""

    operation: str = ""
    target_type: str = ""

    def __post_init__(self):
        if self.node_type != "typeOperation":
            self.node_type = "typeOperation"
        # Initialize validation attributes if not already set
        if not hasattr(self, '_validation_errors'):
            self._validation_errors = []
        if not hasattr(self, '_is_validated'):
            self._is_validated = False
        # Extract operation from text
        if " as " in self.text:
            self.operation = "as"
            parts = self.text.split(" as ")
            if len(parts) > 1:
                self.target_type = parts[1].strip()
        elif " is " in self.text:
            self.operation = "is"
            parts = self.text.split(" is ")
            if len(parts) > 1:
                self.target_type = parts[1].strip()
        elif "ofType(" in self.text:
            self.operation = "ofType"
            # Extract type from function call
            start = self.text.find("ofType(") + 7
            end = self.text.find(")", start)
            if end > start:
                self.target_type = self.text[start:end].strip()

    def validate(self) -> bool:
        """Validate type operation node"""
        self.clear_validation_errors()

        valid_operations = {"as", "is", "ofType"}
        if self.operation not in valid_operations:
            self.add_validation_error(f"Invalid type operation: {self.operation}")

        if not self.target_type:
            self.add_validation_error("Type operation must specify a target type")

        # Validate children
        for child in self.children:
            if not child.validate():
                self.add_validation_error(f"Invalid child: {child.get_validation_errors()}")

        self._is_validated = True
        return len(self._validation_errors) == 0

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_type_operation(self)


# Factory for creating appropriate node types
class NodeTypeFactory:
    """Factory for creating appropriate AST node types based on content"""

    @staticmethod
    def create_node_from_enhanced(enhanced_node: EnhancedASTNode) -> FHIRPathASTNode:
        """Create typed node from EnhancedASTNode"""
        node_type = enhanced_node.node_type.lower()
        text = enhanced_node.text

        # Determine specific node type
        if node_type == "literal":
            node = LiteralNode(
                node_type=enhanced_node.node_type,
                text=text,
                metadata=enhanced_node.metadata,
                children=[],
                value=NodeTypeFactory._parse_literal_value(text)
            )
        elif node_type in ["identifier", "pathexpression"]:
            node = IdentifierNode(
                node_type=enhanced_node.node_type,
                text=text,
                metadata=enhanced_node.metadata,
                children=[]
            )
        elif node_type == "functioncall" or "function" in text.lower():
            # Check if it's an aggregation function
            function_name = text.split("(")[0].strip().lower()
            if function_name in ["count", "sum", "avg", "min", "max"]:
                node = AggregationNode(
                    node_type="aggregation",
                    text=text,
                    metadata=enhanced_node.metadata,
                    children=[]
                )
            elif function_name in ["where", "select", "exists"]:
                node = ConditionalNode(
                    node_type="conditional",
                    text=text,
                    metadata=enhanced_node.metadata,
                    children=[]
                )
            else:
                node = FunctionCallNode(
                    node_type=enhanced_node.node_type,
                    text=text,
                    metadata=enhanced_node.metadata,
                    children=[]
                )
        elif node_type == "operator" or NodeTypeFactory._is_operator(text):
            node = OperatorNode(
                node_type="operator",
                text=text,
                metadata=enhanced_node.metadata,
                children=[]
            )
        elif " as " in text or " is " in text or "ofType(" in text:
            node = TypeOperationNode(
                node_type="typeOperation",
                text=text,
                metadata=enhanced_node.metadata,
                children=[]
            )
        else:
            # Default to base node type
            node = FHIRPathASTNode.__new__(FHIRPathASTNode)
            FHIRPathASTNode.__init__(node, enhanced_node.node_type, text)
            node.metadata = enhanced_node.metadata

        # Copy other properties
        node.parent = enhanced_node.parent
        node.sql_fragment = enhanced_node.sql_fragment
        node.cte_name = enhanced_node.cte_name
        node.dependencies = enhanced_node.dependencies.copy()

        # Recursively convert children
        for child in enhanced_node.children:
            typed_child = NodeTypeFactory.create_node_from_enhanced(child)
            node.add_child(typed_child)

        return node

    @staticmethod
    def _parse_literal_value(text: str) -> Any:
        """Parse literal value from text representation"""
        text = text.strip()

        # Boolean literals
        if text.lower() == "true":
            return True
        elif text.lower() == "false":
            return False

        # String literals (quoted)
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            return text[1:-1]

        # Numeric literals
        try:
            if "." in text:
                return float(text)
            else:
                return int(text)
        except ValueError:
            pass

        # Empty/null literals
        if text in ["{}", "null", ""]:
            return None

        # Default to string
        return text

    @staticmethod
    def _is_operator(text: str) -> bool:
        """Check if text represents an operator"""
        operators = {
            "=", "!=", "<", ">", "<=", ">=", "~", "!~",
            "and", "or", "xor", "implies", "not",
            "+", "-", "*", "/", "div", "mod"
        }
        return text.strip() in operators

    @staticmethod
    def _classify_node_category(node_type: str, text: str) -> NodeCategory:
        """Classify a node into appropriate category based on type and text"""
        node_type_lower = node_type.lower()
        text_lower = text.lower()

        if 'literal' in node_type_lower:
            return NodeCategory.LITERAL
        elif 'identifier' in node_type_lower:
            return NodeCategory.PATH_EXPRESSION
        elif 'invocation' in node_type_lower or 'function' in node_type_lower:
            # Check if it's an aggregation function
            if any(func in text_lower for func in ['count', 'sum', 'avg', 'min', 'max']):
                return NodeCategory.AGGREGATION
            else:
                return NodeCategory.FUNCTION_CALL
        elif 'expression' in node_type_lower:
            # Check for conditional expressions
            if any(keyword in text_lower for keyword in ['where', 'select', 'exists']):
                return NodeCategory.CONDITIONAL
            else:
                return NodeCategory.PATH_EXPRESSION
        elif any(op in text for op in ['=', '!=', '<', '>', '<=', '>=']):
            return NodeCategory.OPERATOR
        else:
            return NodeCategory.PATH_EXPRESSION  # Default fallback
