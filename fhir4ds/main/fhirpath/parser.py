"""
FHIRPath Parser - Enhanced Implementation with fhirpath-py Integration

Production FHIRPath parser integrating fhirpath-py with FHIR4DS-specific
AST extensions and metadata for CTE generation and population analytics.
"""

from typing import Dict, Any, List, Optional, Tuple
from .exceptions import FHIRPathParseError
from .parser_core.enhanced_parser import EnhancedFHIRPathParser, ParseResult, create_enhanced_parser, ExpressionValidator
from .parser_core.semantic_validator import SemanticValidator, FHIRPathExpressionWrapper


class FHIRPathExpression:
    """
    FHIRPath Expression - Enhanced Implementation

    Represents a parsed FHIRPath expression with enhanced AST and analysis capabilities.
    """

    def __init__(self, parse_result: ParseResult):
        """Initialize from enhanced parser result"""
        self.parse_result = parse_result
        self.expression = parse_result.ast.text if parse_result.ast else ""
        self._extract_components()

    def _extract_components(self) -> None:
        """Extract path components and functions from enhanced AST"""
        self.path_components = []
        self.functions = []

        if not self.parse_result.ast:
            return

        # Extract path components - with safe fallback
        try:
            if hasattr(self.parse_result.ast, 'find_nodes_by_category'):
                from .parser_core.metadata_types import NodeCategory

                # Extract functions first
                func_nodes = self.parse_result.ast.find_nodes_by_category(NodeCategory.FUNCTION_CALL)
                agg_nodes = self.parse_result.ast.find_nodes_by_category(NodeCategory.AGGREGATION)
                conditional_nodes = self.parse_result.ast.find_nodes_by_category(NodeCategory.CONDITIONAL)

                # Filter for actual function calls (not full expressions)
                self.functions = []
                for node in func_nodes + agg_nodes + conditional_nodes:
                    if node.text and '(' in node.text and '.' not in node.text:
                        # This is a function call like "first()", not a path like "Patient.telecom.first()"
                        self.functions.append(node.text)

                # Extract function names (without parentheses) to filter from path components
                function_names = set()
                for func_text in self.functions:
                    if '(' in func_text:
                        func_name = func_text.split('(')[0]
                        function_names.add(func_name)

                # Extract path components, filtering out function names and duplicates
                path_nodes = self.parse_result.ast.find_nodes_by_category(NodeCategory.PATH_EXPRESSION)
                seen_components = set()
                self.path_components = []
                for node in path_nodes:
                    if (node.text and node.text not in function_names and
                        node.text not in seen_components):
                        seen_components.add(node.text)
                        self.path_components.append(node.text)
            else:
                # Simple fallback if enhanced metadata not available
                self._simple_extraction()
        except Exception:
            # Fallback if metadata extraction fails
            self._simple_extraction()

    def _simple_extraction(self) -> None:
        """Simple fallback extraction without enhanced metadata"""
        # Extract path components
        if '.' in self.expression:
            self.path_components = self.expression.split('.')
        else:
            self.path_components = [self.expression] if self.expression else []

        # Extract functions using regex
        import re
        self.functions = re.findall(r'(\w+)\s*\(', self.expression)

    def is_valid(self) -> bool:
        """Check if the parsed expression is valid."""
        return self.parse_result.is_valid

    def get_path_components(self) -> List[str]:
        """Get the path components of the expression."""
        return self.path_components

    def get_functions(self) -> List[str]:
        """Get the functions used in the expression."""
        return self.functions

    def get_ast(self):
        """Get the enhanced AST node"""
        return self.parse_result.ast

    def get_complexity_analysis(self) -> Optional[Dict[str, Any]]:
        """Get complexity analysis if available"""
        return self.parse_result.complexity_analysis

    def get_optimization_opportunities(self) -> Optional[List[Dict[str, Any]]]:
        """Get optimization opportunities if available"""
        return self.parse_result.optimization_opportunities

    def accept(self, visitor):
        """
        Accept a visitor following the visitor pattern.

        Delegates to the underlying AST node's accept method to enable
        proper visitor pattern traversal for SQL translation.

        Args:
            visitor: The visitor instance (e.g., ASTToSQLTranslator)

        Returns:
            Result of visitor operation on the AST

        Raises:
            AttributeError: If the underlying AST node doesn't have an accept method
        """
        if self.parse_result.ast and hasattr(self.parse_result.ast, 'accept'):
            return self.parse_result.ast.accept(visitor)
        else:
            # Fallback: call visitor.visit directly
            return visitor.visit_generic(self.parse_result.ast) if self.parse_result.ast else None


class FHIRPathParser:
    """
    FHIRPath Parser - Enhanced Implementation

    Production FHIRPath parser providing enhanced parsing capabilities
    with AST metadata for CTE generation and population analytics.
    """

    def __init__(self, database_type: str = "duckdb"):
        """Initialize the FHIRPath parser with database type."""
        self.database_type = database_type
        self.enhanced_parser = create_enhanced_parser(database_type)
        self.semantic_validator = SemanticValidator()

    @staticmethod
    def _validate_comment_structure(expression: str) -> None:
        """Ensure expressions do not contain unterminated block comments."""
        if not expression:
            return

        in_single_quote = False
        in_double_quote = False
        in_backtick = False
        comment_stack: List[Tuple[int, int]] = []

        index = 0
        length = len(expression)
        line = 1
        column = 1

        def advance(step: int = 1) -> None:
            nonlocal index, line, column
            for _ in range(step):
                if index >= length:
                    return
                ch = expression[index]
                index += 1
                if ch == "\r":
                    if index < length and expression[index] == "\n":
                        index += 1
                    line += 1
                    column = 1
                elif ch == "\n":
                    line += 1
                    column = 1
                else:
                    column += 1

        while index < length:
            current = expression[index]
            next_char = expression[index + 1] if index + 1 < length else ""
            current_line, current_column = line, column

            if comment_stack:
                if current == "/" and next_char == "*":
                    raise FHIRPathParseError(
                        f"Nested block comments are not supported (found '/*' at line {current_line}, column {current_column})."
                    )
                if current == "*" and next_char == "/":
                    comment_stack.pop()
                    advance(2)
                    continue
                advance()
                continue

            if in_single_quote:
                if current == "\\":
                    advance(2)
                    continue
                if current == "'":
                    in_single_quote = False
                advance()
                continue

            if in_double_quote:
                if current == "\\":
                    advance(2)
                    continue
                if current == '"':
                    in_double_quote = False
                advance()
                continue

            if in_backtick:
                if current == "\\":
                    advance(2)
                    continue
                if current == "`":
                    in_backtick = False
                advance()
                continue

            if current == "'":
                in_single_quote = True
                advance()
                continue

            if current == '"':
                in_double_quote = True
                advance()
                continue

            if current == "`":
                in_backtick = True
                advance()
                continue

            if current == "/" and next_char == "/":
                advance(2)
                while index < length:
                    if expression[index] in ("\n", "\r"):
                        advance()
                        break
                    advance()
                continue

            if current == "/" and next_char == "*":
                comment_stack.append((current_line, current_column))
                advance(2)
                continue

            if current == "*" and next_char == "/":
                raise FHIRPathParseError(
                    f"Unexpected block comment terminator at line {current_line}, column {current_column}."
                )

            advance()

        if comment_stack:
            start_line, start_column = comment_stack[-1]
            raise FHIRPathParseError(
                f"Unterminated block comment starting at line {start_line}, column {start_column}."
            )

    def parse(self, expression: str, context: Optional[Dict[str, Any]] = None) -> FHIRPathExpression:
        """
        Parse a FHIRPath expression.

        Args:
            expression: The FHIRPath expression to parse

        Returns:
            Parsed FHIRPath expression object

        Raises:
            FHIRPathParseError: If expression cannot be parsed
        """
        if not expression or expression.strip() == "":
            raise FHIRPathParseError("Empty expression")

        self._validate_comment_structure(expression)

        # Additional validation for clearly invalid syntax
        if ".." in expression:
            raise FHIRPathParseError("Invalid syntax: consecutive dots not allowed")

        # Use enhanced parser
        parse_result = self.enhanced_parser.parse(
            expression,
            analyze_complexity=True,
            find_optimizations=True
        )

        if not parse_result.is_valid:
            raise FHIRPathParseError(parse_result.error_message or "Parse failed")

        parsed_expression = FHIRPathExpression(parse_result)

        # Execute semantic validation to catch invalid-but-syntactically-correct expressions
        self.semantic_validator.validate(
            expression,
            parsed_expression=FHIRPathExpressionWrapper(
                parsed_expression.get_ast(),
                functions=parsed_expression.get_functions(),
                path_components=parsed_expression.get_path_components()
            ),
            context=context
        )

        return parsed_expression

    def evaluate(self, expression: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Evaluate a FHIRPath expression against FHIR data.

        Args:
            expression: The FHIRPath expression to evaluate
            context: FHIR data context for evaluation

        Returns:
            Evaluation result (enhanced implementation returns analysis info)
        """
        try:
            parsed = self.parse(expression, context=context)

            if not parsed.is_valid():
                return None

            # Return enhanced evaluation result with metadata
            result = {
                "expression": expression,
                "is_valid": parsed.is_valid(),
                "path_components": parsed.get_path_components(),
                "functions": parsed.get_functions(),
                "complexity_analysis": parsed.get_complexity_analysis(),
                "optimization_opportunities": parsed.get_optimization_opportunities()
            }

            # Add AST information if available
            if parsed.get_ast():
                result["ast_info"] = {
                    "node_type": parsed.get_ast().node_type,
                    "children_count": len(parsed.get_ast().children),
                    "has_metadata": parsed.get_ast().metadata is not None
                }

            return result

        except FHIRPathParseError:
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get parser usage statistics."""
        enhanced_stats = self.enhanced_parser.get_statistics()
        return {
            "parse_count": enhanced_stats["parse_count"],
            "database_type": self.database_type,
            "average_parse_time_ms": enhanced_stats["average_parse_time_ms"],
            "fhirpathpy_available": enhanced_stats["fhirpathpy_available"]
        }

    def validate_expression(self, expression: str) -> Dict[str, Any]:
        """
        Validate a FHIRPath expression without full parsing

        Args:
            expression: Expression to validate

        Returns:
            Validation result with issues and suggestions
        """
        return ExpressionValidator.validate_expression(expression)

    def get_enhanced_parser(self) -> EnhancedFHIRPathParser:
        """Get the underlying enhanced parser for advanced operations"""
        return self.enhanced_parser
