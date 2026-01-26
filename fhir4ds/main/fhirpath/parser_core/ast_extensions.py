"""
Extended AST Nodes for FHIR4DS FHIRPath Parser

This module extends the basic fhirpath-py AST nodes with metadata required
for CTE generation and population-scale analytics optimization.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from .metadata_types import (
    ASTNodeMetadata, NodeCategory, OptimizationHint,
    MetadataBuilder, TypeInformation, SQLDataType
)


@dataclass
class EnhancedASTNode:
    """
    Enhanced AST node with FHIR4DS-specific metadata

    Extends the basic fhirpath-py AST node structure with metadata
    required for SQL/CTE generation and population analytics.
    """
    # Core node properties from fhirpath-py
    node_type: str
    text: str
    children: List['EnhancedASTNode'] = field(default_factory=list)

    # FHIR4DS enhancements
    metadata: Optional[ASTNodeMetadata] = None
    parent: Optional['EnhancedASTNode'] = None

    # SQL generation context
    sql_fragment: Optional[str] = None
    cte_name: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

    def add_child(self, child: 'EnhancedASTNode') -> None:
        """Add a child node and set parent relationship"""
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: 'EnhancedASTNode') -> None:
        """Remove a child node"""
        if child in self.children:
            child.parent = None
            self.children.remove(child)

    def get_root(self) -> 'EnhancedASTNode':
        """Get the root node of the tree"""
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    def get_depth(self) -> int:
        """Get the depth of this node in the tree"""
        depth = 0
        node = self.parent
        while node is not None:
            depth += 1
            node = node.parent
        return depth

    def find_nodes_by_type(self, node_type: str) -> List['EnhancedASTNode']:
        """Find all descendant nodes of a specific type"""
        result = []
        if self.node_type == node_type:
            result.append(self)
        for child in self.children:
            result.extend(child.find_nodes_by_type(node_type))
        return result

    def find_nodes_by_category(self, category: NodeCategory) -> List['EnhancedASTNode']:
        """Find all descendant nodes of a specific category"""
        result = []
        if self.metadata and self.metadata.node_category == category:
            result.append(self)
        for child in self.children:
            result.extend(child.find_nodes_by_category(category))
        return result

    def has_optimization_hint(self, hint: OptimizationHint) -> bool:
        """Check if node has a specific optimization hint"""
        return (self.metadata is not None and
                hint in self.metadata.optimization_hints)

    def is_population_optimizable(self) -> bool:
        """Check if node supports population-scale optimization"""
        return (self.metadata is not None and
                self.metadata.population_analytics.supports_population_query)

    def requires_patient_context(self) -> bool:
        """Check if node requires patient context"""
        return (self.metadata is not None and
                self.metadata.population_analytics.requires_patient_context)

    def can_generate_cte(self) -> bool:
        """Check if node can be extracted to a CTE"""
        return (self.metadata is not None and
                OptimizationHint.CTE_REUSABLE in self.metadata.optimization_hints)

    def get_sql_data_type(self) -> SQLDataType:
        """Get the SQL data type for this node"""
        if self.metadata and self.metadata.type_info:
            return self.metadata.type_info.sql_data_type
        return SQLDataType.UNKNOWN

    def is_aggregation_node(self) -> bool:
        """Check if this is an aggregation node"""
        return (self.metadata is not None and
                self.metadata.node_category == NodeCategory.AGGREGATION)

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation"""
        result = {
            "node_type": self.node_type,
            "text": self.text,
            "children": [child.to_dict() for child in self.children]
        }

        if self.metadata:
            result["metadata"] = {
                "category": self.metadata.node_category.value,
                "optimization_hints": [hint.value for hint in self.metadata.optimization_hints],
                "sql_data_type": self.metadata.type_info.sql_data_type.value,
                "source_text": self.metadata.source_text,
                "line_number": self.metadata.line_number,
                "column_number": self.metadata.column_number
            }

        if self.sql_fragment:
            result["sql_fragment"] = self.sql_fragment

        if self.cte_name:
            result["cte_name"] = self.cte_name

        if self.dependencies:
            result["dependencies"] = self.dependencies

        return result

    def accept(self, visitor):
        """
        Accept a visitor following the visitor pattern.

        Maps the EnhancedASTNode to the appropriate visitor method based
        on node_type and metadata category. Enhanced in SP-023-006 to fully
        replicate the conversion logic from ASTAdapter.convert().

        Args:
            visitor: The visitor instance (e.g., ASTToSQLTranslator)

        Returns:
            Result of visitor operation on this node
        """
        # Import here to avoid circular imports
        from .metadata_types import NodeCategory
        import re
        from datetime import datetime, timedelta

        # SP-023-006: Handle wrapper nodes by unwrapping first
        # ParenthesizedTerm nodes should be unwrapped to preserve inner expression semantics
        if self.node_type == "ParenthesizedTerm":
            if self.children and len(self.children) == 1:
                return self.children[0].accept(visitor)
            elif self.children:
                # Multiple children - visit last child
                return self.children[-1].accept(visitor)

        # SP-023-006: TermExpression unwrapping - check if it wraps a single child
        if self.node_type == "TermExpression" and self.children and len(self.children) == 1:
            return self.children[0].accept(visitor)

        # Map node types to visitor methods based on metadata category
        if self.metadata:
            category = self.metadata.node_category

            if category == NodeCategory.LITERAL:
                # Create a literal node adapter with all required attributes
                # SP-023-006: Enhanced with FHIR temporal literal parsing
                class LiteralNodeAdapter:
                    def __init__(self, enhanced_node):
                        self.text = enhanced_node.text
                        self.node_type = enhanced_node.node_type
                        self.enhanced_node = enhanced_node
                        self.metadata = enhanced_node.metadata
                        # Add required literal attributes
                        self.value, self.literal_type, self.temporal_info = self._parse_value_and_type(enhanced_node.text)

                    def _parse_value_and_type(self, text):
                        """Parse literal value, type, and temporal info from text.

                        SP-023-006: Enhanced to handle FHIR temporal literals.
                        SP-100-003: Enhanced to handle empty collection literals.
                        SP-103-003: Enhanced to properly process escape sequences in string literals.
                        SP-104-007: Enhanced to detect partial datetime literals from original source.
                        """
                        if not text:
                            return None, "unknown", None

                        text = text.strip()

                        # SP-100-003: Handle empty collection literal {}
                        if text == "{}":
                            # Empty collection marker - use special value to signal empty collection
                            return "{}[]", "empty_collection", None

                        # SP-104-007: Check for partial datetime literals from original source
                        # The ANTLR DATETIME lexer strips the 'T' suffix from @YYYYT patterns
                        # We need to check the original expression to detect this
                        original_source = self._get_original_source()
                        if original_source and text.startswith('@'):
                            # Check if the original source has a 'T' suffix that was stripped
                            # Pattern: @YYYYT, @YYYY-MMT, @YYYY-MM-DDT (without time components)
                            temporal_from_source = self._parse_partial_datetime_from_source(original_source)
                            if temporal_from_source:
                                literal_type = temporal_from_source.get("literal_type", "string")
                                normalized_value = temporal_from_source.get("normalized", text.lstrip("@"))
                                # Store the original source in temporal_info for the translator
                                temporal_from_source["original_source"] = original_source
                                return normalized_value, literal_type, temporal_from_source

                        # Handle FHIR temporal literals
                        temporal_info = self._parse_temporal_literal(text)
                        if temporal_info:
                            literal_type = temporal_info.get("literal_type", "string")
                            normalized_value = temporal_info.get("normalized", text.lstrip("@"))
                            # Also preserve original source if available
                            if original_source:
                                temporal_info["original_source"] = original_source
                            return normalized_value, literal_type, temporal_info

                        # Handle string literals (quoted)
                        if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
                            # SP-103-003: Use ast.literal_eval to properly process escape sequences
                            # The parser returns strings like "'1 \\'wk\\''" which need to be evaluated
                            # to get the actual string value "1 'wk'"
                            import ast as python_ast
                            try:
                                # Evaluate the string literal to process escape sequences
                                evaluated_value = python_ast.literal_eval(text)
                                return evaluated_value, "string", None
                            except (ValueError, SyntaxError):
                                # Fallback to simple stripping if evaluation fails
                                return text[1:-1], "string", None

                        # Handle boolean literals
                        if text.lower() == 'true':
                            return True, "boolean", None
                        if text.lower() == 'false':
                            return False, "boolean", None

                        # SP-104-003: Handle duration/quantity literals (e.g., "7days", "1 second")
                        # Pattern: number followed by temporal unit (days, weeks, months, years, hours, minutes, seconds)
                        duration_match = re.match(r'^(\d+(?:\.\d+)?)\s*(' +
                                                r'day|days|week|weeks|month|months|year|years|' +
                                                r'hour|hours|minute|minutes|second|seconds|millisecond|milliseconds)$',
                                                text, re.IGNORECASE)
                        if duration_match:
                            value = duration_match.group(1)
                            unit = duration_match.group(2)
                            # Return as quantity literal with temporal unit info
                            temporal_info = {
                                'kind': 'duration',
                                'value': value,
                                'unit': unit,
                                'original': text
                            }
                            # Return the value as the parsed value, but mark as quantity
                            # The translator will use the temporal_info to generate INTERVAL SQL
                            if '.' in value:
                                return float(value), "quantity", temporal_info
                            else:
                                return int(value), "quantity", temporal_info

                        # Handle numeric literals
                        try:
                            if '.' in text and not text.startswith('@'):
                                return float(text), "decimal", None
                            return int(text), "integer", None
                        except ValueError:
                            pass

                        # Default to string for unrecognized
                        return text, "string", None

                    def _get_original_source(self):
                        """Get the original FHIRPath expression source text.

                        SP-104-007: Retrieve the original expression from the enhanced_node's
                        metadata to detect partial datetime literals that were stripped by ANTLR.

                        The original_expression is now propagated to all child nodes during
                        metadata creation, so it should be directly available in the current node.
                        """
                        if (hasattr(self, 'enhanced_node') and
                            self.enhanced_node and
                            self.enhanced_node.metadata and
                            hasattr(self.enhanced_node.metadata, 'custom_attributes')):
                            # Get original_expression from the current node's metadata
                            return self.enhanced_node.metadata.custom_attributes.get('original_expression')
                        return None

                    def _parse_partial_datetime_from_source(self, original_source: str):
                        """Detect partial datetime literal from original source text.

                        SP-104-007: Check if the original source contains a partial datetime
                        pattern (@YYYYT, @YYYY-MMT, @YYYY-MM-DDT) that was stripped by ANTLR.

                        Args:
                            original_source: The original FHIRPath expression string

                        Returns:
                            Temporal info dict if partial datetime detected, None otherwise
                        """
                        import re
                        if not original_source or not original_source.startswith('@'):
                            return None

                        # Look for temporal literal pattern in the source
                        # Find all @... patterns in the source
                        temporal_matches = re.finditer(r'@(\d{4}(?:-\d{2})?(?:-\d{2})?T?)(?![\d:-])', original_source)
                        for match in temporal_matches:
                            temporal_text = match.group(0)  # Full match including @
                            body = match.group(1)  # Without @

                            # Check if it ends with 'T' (partial datetime pattern)
                            if body.endswith('T'):
                                # Remove the trailing T to parse the date part
                                body_without_t = body[:-1]
                                # Parse as partial datetime
                                partial_match = re.fullmatch(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", body_without_t)
                                if partial_match:
                                    return self._parse_partial_datetime_literal(temporal_text, body_without_t, partial_match)

                        return None

                    def _parse_temporal_literal(self, text):
                        """Parse FHIR temporal literal returning metadata for range comparisons.

                        SP-023-006: Replicated from ASTAdapter._parse_temporal_literal().
                        SP-100-012: Enhanced to handle partial DateTime literals (@2015T, @2015-02T).
                        """
                        if not text.startswith("@"):
                            return None

                        if text.startswith("@T"):
                            return self._parse_time_literal(text)

                        body = text[1:]
                        if "T" in body:
                            # SP-100-012: Check for partial DateTime pattern first
                            # (@YYYYT, @YYYY-MMT, @YYYY-MM-DDT without time components)
                            partial_datetime_match = re.fullmatch(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?T$", body)
                            if partial_datetime_match:
                                return self._parse_partial_datetime_literal(text, body, partial_datetime_match)
                            return self._parse_datetime_literal(text, body)
                        return self._parse_date_literal(text, body)

                    def _parse_date_literal(self, original, body):
                        """Parse FHIR date literal with optional reduced precision."""
                        if re.fullmatch(r"\d{4}$", body):
                            year = int(body)
                            start_dt = datetime(year, 1, 1)
                            end_dt = datetime(year + 1, 1, 1)
                            precision = "year"
                            normalized = f"{year:04d}"
                            # SP-104-004: Use "date" literal_type for all date literals, including partial dates
                            # This ensures they're converted to DATE SQL literals for proper comparison
                            literal_type = "date"
                            is_partial = True
                        elif re.fullmatch(r"\d{4}-\d{2}$", body):
                            year, month = map(int, body.split("-"))
                            start_dt = datetime(year, month, 1)
                            if month == 12:
                                end_dt = datetime(year + 1, 1, 1)
                            else:
                                end_dt = datetime(year, month + 1, 1)
                            precision = "month"
                            normalized = f"{year:04d}-{month:02d}"
                            # SP-104-004: Use "date" literal_type for all date literals, including partial dates
                            literal_type = "date"
                            is_partial = True
                        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}$", body):
                            year, month, day = map(int, body.split("-"))
                            start_dt = datetime(year, month, day)
                            end_dt = start_dt + timedelta(days=1)
                            precision = "day"
                            normalized = f"{year:04d}-{month:02d}-{day:02d}"
                            literal_type = "date"
                            is_partial = False
                        else:
                            return None

                        return {
                            "kind": "date",
                            "precision": precision,
                            "normalized": normalized,
                            "start": self._format_datetime_iso(start_dt),
                            "end": self._format_datetime_iso(end_dt),
                            "is_partial": is_partial,
                            "literal_type": literal_type,
                            "original": original
                        }

                    def _parse_datetime_literal(self, original, body):
                        """Parse FHIR dateTime literal with optional reduced precision and timezone.

                        SP-100-012: Enhanced to handle timezone suffixes (Z, +/-HH:MM).
                        """
                        # Pattern with optional timezone suffix: Z or +/-HH:MM
                        pattern = re.compile(
                            r"^(\d{4})-(\d{2})-(\d{2})T"
                            r"(\d{2})(?::(\d{2})(?::(\d{2})(?:\.(\d+))?)?)?"
                            r"(?:Z|[+-]\d{2}:\d{2})?$"
                        )
                        match = pattern.fullmatch(body)
                        if not match:
                            return None

                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))
                        hour = int(match.group(4))
                        minute = int(match.group(5) or 0)
                        second = int(match.group(6) or 0)
                        fraction = match.group(7)

                        # Extract timezone from original text
                        timezone = None
                        if "Z" in body:
                            timezone = "Z"
                        elif "+" in body or "-" in body and body.rfind("-") > 10:
                            # Find timezone offset at the end
                            tz_match = re.search(r"([+-]\d{2}:\d{2})$", body)
                            if tz_match:
                                timezone = tz_match.group(1)

                        microseconds = self._fraction_to_microseconds(fraction)
                        start_dt = datetime(year, month, day, hour, minute, second, microseconds)

                        if fraction:
                            precision = "fraction"
                            end_dt = start_dt + timedelta(microseconds=self._fraction_step(fraction))
                            is_partial = False
                            normalized = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}.{fraction}"
                        elif match.group(6):
                            precision = "second"
                            end_dt = start_dt + timedelta(seconds=1)
                            is_partial = False
                            normalized = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"
                        elif match.group(5):
                            precision = "minute"
                            end_dt = start_dt + timedelta(minutes=1)
                            is_partial = True
                            normalized = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}"
                        else:
                            precision = "hour"
                            end_dt = start_dt + timedelta(hours=1)
                            is_partial = True
                            normalized = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}"

                        # Append timezone to normalized value if present
                        if timezone:
                            normalized = f"{normalized}{timezone}"

                        result = {
                            "kind": "datetime",
                            "precision": precision,
                            "normalized": normalized,
                            "start": self._format_datetime_iso(start_dt),
                            "end": self._format_datetime_iso(end_dt),
                            "is_partial": is_partial,
                            "literal_type": "datetime",
                            "original": original,
                            "fraction_digits": len(fraction) if fraction else 0
                        }

                        # Add timezone information if present
                        if timezone:
                            result["timezone"] = timezone

                        return result

                    def _parse_partial_datetime_literal(self, original, body, match):
                        """Parse FHIR partial dateTime literal (date components with 'T' suffix).

                        SP-100-012: Handles @YYYYT, @YYYY-MMT, @YYYY-MM-DDT as partial DateTime literals.
                        These are distinct from Date literals because they include the 'T' suffix.
                        """
                        year = int(match.group(1))
                        month_str = match.group(2)
                        day_str = match.group(3)

                        month = int(month_str) if month_str else 1
                        day = int(day_str) if day_str else 1

                        # Determine precision and calculate boundaries
                        if not month_str:
                            # Year only: @2015T
                            start_dt = datetime(year, 1, 1)
                            end_dt = datetime(year + 1, 1, 1)
                            precision = "year"
                            is_partial = True
                            normalized = f"{year:04d}"
                        elif not day_str:
                            # Year-month: @2015-02T
                            start_dt = datetime(year, month, 1)
                            if month == 12:
                                end_dt = datetime(year + 1, 1, 1)
                            else:
                                end_dt = datetime(year, month + 1, 1)
                            precision = "month"
                            is_partial = True
                            normalized = f"{year:04d}-{month:02d}"
                        else:
                            # Year-month-day: @2015-02-04T
                            start_dt = datetime(year, month, day)
                            end_dt = start_dt + timedelta(days=1)
                            precision = "day"
                            is_partial = False
                            normalized = f"{year:04d}-{month:02d}-{day:02d}"

                        return {
                            "kind": "datetime",
                            "precision": precision,
                            "normalized": normalized,
                            "start": self._format_datetime_iso(start_dt),
                            "end": self._format_datetime_iso(end_dt),
                            "is_partial": is_partial,
                            "literal_type": "datetime",
                            "original": original
                        }

                    def _parse_time_literal(self, text):
                        """Parse FHIR time literal with optional reduced precision."""
                        pattern = re.compile(
                            r"^@T(\d{2})(?::(\d{2})(?::(\d{2})(?:\.(\d+))?)?)?$"
                        )
                        match = pattern.fullmatch(text)
                        if not match:
                            return None

                        hour = int(match.group(1))
                        minute = int(match.group(2) or 0)
                        second = int(match.group(3) or 0)
                        fraction = match.group(4)

                        microseconds = self._fraction_to_microseconds(fraction)
                        start_dt = datetime(1970, 1, 1, hour, minute, second, microseconds)

                        if fraction:
                            precision = "fraction"
                            step = timedelta(microseconds=self._fraction_step(fraction))
                            is_partial = False
                            normalized = f"{hour:02d}:{minute:02d}:{second:02d}.{fraction}"
                        elif match.group(3):
                            precision = "second"
                            step = timedelta(seconds=1)
                            is_partial = False
                            normalized = f"{hour:02d}:{minute:02d}:{second:02d}"
                        elif match.group(2):
                            precision = "minute"
                            step = timedelta(minutes=1)
                            is_partial = True
                            normalized = f"{hour:02d}:{minute:02d}"
                        else:
                            precision = "hour"
                            step = timedelta(hours=1)
                            is_partial = True
                            normalized = f"{hour:02d}"

                        end_dt = start_dt + step

                        return {
                            "kind": "time",
                            "precision": precision,
                            "normalized": normalized,
                            "start": self._format_time_value(start_dt),
                            "end": self._format_time_value(end_dt),
                            "is_partial": is_partial,
                            "literal_type": "time",
                            "original": text,
                            "fraction_digits": len(fraction) if fraction else 0
                        }

                    def _format_datetime_iso(self, value):
                        """Format datetime in ISO string with seconds precision."""
                        base = value.strftime("%Y-%m-%dT%H:%M:%S")
                        if value.microsecond:
                            micro = f"{value.microsecond:06d}".rstrip("0")
                            if micro:
                                return f"{base}.{micro}"
                        return base

                    def _format_time_value(self, value):
                        """Format time component from datetime with seconds precision."""
                        base = value.strftime("%H:%M:%S")
                        if value.microsecond:
                            micro = f"{value.microsecond:06d}".rstrip("0")
                            if micro:
                                return f"{base}.{micro}"
                        return base

                    @staticmethod
                    def _fraction_to_microseconds(fraction):
                        """Convert fractional second string to microseconds."""
                        if not fraction:
                            return 0
                        frac = fraction[:6].ljust(6, "0")
                        try:
                            return int(frac)
                        except ValueError:
                            return 0

                    @staticmethod
                    def _fraction_step(fraction):
                        """Calculate microsecond step for a given fractional precision."""
                        digits = max(0, min(len(fraction), 6))
                        return 10 ** (6 - digits) if digits < 6 else 1

                    def accept(self, v):
                        return v.visit_literal(self)
                return LiteralNodeAdapter(self).accept(visitor)

            elif category == NodeCategory.OPERATOR:
                class OperatorNodeAdapter:
                    def __init__(self, enhanced_node):
                        self.text = enhanced_node.text
                        self.node_type = enhanced_node.node_type
                        self.enhanced_node = enhanced_node
                        self.children = enhanced_node.children
                        # Add required operator attributes
                        self.operator = enhanced_node.text
                        self.operator_type = self._infer_operator_type(enhanced_node.text, enhanced_node.children)
                        # Map to left_operand/right_operand for binary operators
                        if len(enhanced_node.children) >= 2:
                            self.left_operand = enhanced_node.children[0]
                            self.right_operand = enhanced_node.children[1]
                        elif len(enhanced_node.children) == 1:
                            self.left_operand = enhanced_node.children[0]
                            self.right_operand = None
                        else:
                            self.left_operand = None
                            self.right_operand = None

                    def _infer_operator_type(self, operator, children):
                        """Infer operator type from operator symbol and children count"""
                        if len(children) == 1:
                            return "unary"
                        elif operator.lower() in ('and', 'or', 'xor', 'implies'):
                            return "logical"
                        elif operator in ('=', '!=', '<', '>', '<=', '>=', '~', '!~'):
                            return "comparison"
                        elif operator in ('+', '-', '*', '/', 'div', 'mod'):
                            return "binary"  # arithmetic
                        elif operator == '|':
                            return "union"
                        return "binary"

                    def accept(self, v):
                        return v.visit_operator(self)
                return OperatorNodeAdapter(self).accept(visitor)

            elif category in [NodeCategory.FUNCTION_CALL, NodeCategory.CONDITIONAL]:
                # SP-103-008: Special handling for CONDITIONAL category
                # Check if this is an InvocationExpression containing a type operation
                if category == NodeCategory.CONDITIONAL and self.node_type == 'InvocationExpression':
                    # SP-103-008: Check if any child is a TYPE_OPERATION (e.g., is(), as(), ofType())
                    # If so, unwrap to that child instead of visiting generically
                    if self.children:
                        for child in self.children:
                            if (child.metadata and
                                child.metadata.node_category == NodeCategory.TYPE_OPERATION):
                                # Unwrap to the type operation child
                                return child.accept(visitor)

                    # Container node marked as CONDITIONAL should be visited generically to traverse children
                    return visitor.visit_generic(self)

                # SP-022-006: TypeExpression nodes (is/as operations) should be handled as type operations,
                # not as wrapper nodes or function calls.
                if self.node_type == 'TypeExpression':
                    class TypeExpressionAdapter:
                        """Adapter for TypeExpression nodes to route them to visit_type_operation."""
                        def __init__(self, enhanced_node):
                            self.text = enhanced_node.text
                            self.node_type = "typeOperation"
                            self.enhanced_node = enhanced_node
                            self.metadata = enhanced_node.metadata
                            self.children = enhanced_node.children
                            self.operation, self.target_type = self._extract_operation_and_type(enhanced_node)

                        def _extract_operation_and_type(self, node):
                            """Extract the type operation and target type."""
                            text = node.text or ""
                            # Check custom_attributes first
                            if (node.metadata and
                                hasattr(node.metadata, 'custom_attributes') and
                                node.metadata.custom_attributes):
                                op = node.metadata.custom_attributes.get('operation')
                                if op:
                                    target_type = self._extract_type_from_children(node)
                                    return op, target_type or 'Unknown'
                            # Parse from text
                            if ' is ' in text:
                                return 'is', text.split(' is ')[-1].strip()
                            elif ' as ' in text:
                                return 'as', text.split(' as ')[-1].strip()
                            # Try children
                            target_type = self._extract_type_from_children(node)
                            return 'is', target_type or 'Unknown'

                        def _extract_type_from_children(self, node):
                            """Extract target type from TypeSpecifier child."""
                            if len(node.children) >= 2:
                                type_spec = node.children[1]
                                if type_spec.text:
                                    return type_spec.text.strip()
                                if type_spec.children:
                                    for child in type_spec.children:
                                        if child.text:
                                            return child.text.strip()
                            return None

                        def accept(self, v):
                            return v.visit_type_operation(self)
                    return TypeExpressionAdapter(self).accept(visitor)

                # SP-023-004A: Handle wrapper nodes with FUNCTION_CALL category but no actual function
                # MemberInvocation nodes with empty text are wrappers for path expressions
                elif (not self.text or not self.text.strip() or '(' not in self.text) and self.children:
                    # This is a wrapper node (like MemberInvocation with empty text)
                    # Unwrap to child instead of treating as function call
                    if len(self.children) == 1:
                        return self.children[0].accept(visitor)
                    # Multiple children - visit generically
                    return visitor.visit_generic(self)

                class FunctionCallNodeAdapter:
                    def __init__(self, enhanced_node):
                        self.text = enhanced_node.text
                        self.node_type = enhanced_node.node_type
                        self.enhanced_node = enhanced_node
                        self.children = enhanced_node.children
                        # Add required function call attributes
                        self.function_name = self._extract_function_name(enhanced_node.text)
                        self.arguments = self._extract_arguments(enhanced_node)
                        self.target = None  # Will be set by caller if needed

                    def _extract_function_name(self, text):
                        """Extract function name from text"""
                        if '(' in text:
                            return text.split('(')[0].strip()
                        return text.strip()

                    def _extract_arguments(self, node):
                        """Extract actual arguments from ParamList"""
                        # Look for Functn -> ParamList pattern
                        for child in node.children:
                            # Check if child is Functn (by type or structure)
                            if child.node_type == 'Functn' or (child.text.startswith('(') and child.text.endswith(')')):
                                for grandchild in child.children:
                                    if grandchild.node_type == 'ParamList':
                                        return grandchild.children
                                # If Functn found but no ParamList, it means empty arguments
                                return []
                        
                        # If no Functn found, fallback to filtering children
                        # This handles cases where arguments might be direct children (unlikely in this parser)
                        return [c for c in node.children if c.node_type != 'Identifier' and c.text != self.function_name]

                    def accept(self, v):
                        return v.visit_function_call(self)
                return FunctionCallNodeAdapter(self).accept(visitor)

            elif category == NodeCategory.PATH_EXPRESSION:
                # SP-022-009: Handle PolarityExpression (unary minus) before other PATH_EXPRESSION handling
                # PolarityExpression needs special handling for negation
                if self.node_type == "PolarityExpression" and self.children:
                    child = self.children[0]
                    # Recursively unwrap to find the actual literal
                    actual_child = child
                    while (actual_child.children and len(actual_child.children) == 1 and
                           actual_child.node_type in ['TermExpression', 'InvocationExpression', 'InvocationTerm']):
                        actual_child = actual_child.children[0]

                    # Check if the actual child is a literal
                    if (actual_child.metadata and
                        actual_child.metadata.node_category == NodeCategory.LITERAL):
                        # Create negated literal
                        class NegatedLiteralAdapter:
                            def __init__(self, enhanced_node, original_child):
                                child_text = original_child.text or ""
                                self.text = f"-{child_text}"
                                self.node_type = "literal"
                                self.enhanced_node = enhanced_node
                                self.metadata = original_child.metadata

                                # Parse and negate the value
                                try:
                                    if '.' in child_text:
                                        self.value = -float(child_text)
                                        self.literal_type = "decimal"
                                    else:
                                        self.value = -int(child_text)
                                        self.literal_type = "integer"
                                except ValueError:
                                    self.value = child_text
                                    self.literal_type = "string"

                                self.temporal_info = None

                            def accept(self, v):
                                return v.visit_literal(self)
                        return NegatedLiteralAdapter(self, actual_child).accept(visitor)
                    else:
                        # General case: create unary operator
                        class UnaryMinusAdapter:
                            def __init__(self, enhanced_node):
                                self.text = enhanced_node.text
                                self.node_type = "operator"
                                self.enhanced_node = enhanced_node
                                self.metadata = enhanced_node.metadata
                                self.children = enhanced_node.children
                                self.operator = "unary_minus"
                                self.operator_type = "unary"
                                self.left_operand = enhanced_node.children[0] if enhanced_node.children else None
                                self.right_operand = None

                            def accept(self, v):
                                return v.visit_operator(self)
                        return UnaryMinusAdapter(self).accept(visitor)

                # Special case: If this is a wrapper node (like TermExpression) with a single
                # child, unwrap it and visit the child directly. This prevents wrapper nodes
                # from being treated as identifiers when they contain other logic.
                if (self.node_type in ['TermExpression', 'InvocationExpression', 'InvocationTerm'] and
                    len(self.children) == 1):
                    # Unwrap and visit the child directly
                    return self.children[0].accept(visitor)

                # Normal path expression handling
                class IdentifierNodeAdapter:
                    def __init__(self, enhanced_node):
                        self.text = enhanced_node.text
                        self.node_type = enhanced_node.node_type
                        self.enhanced_node = enhanced_node
                        self.metadata = enhanced_node.metadata
                        # Add required identifier attributes
                        self.identifier = self._normalize_identifier(enhanced_node.text)
                        self.is_qualified = '.' in enhanced_node.text or '::' in enhanced_node.text

                    def _normalize_identifier(self, text):
                        """Normalize identifier, handling escaped names.

                        SP-023-006: Replicated from ASTAdapter._normalize_identifier_text().
                        """
                        if not text:
                            return ""

                        # Handle backtick-escaped identifiers
                        text = text.strip()
                        if text.startswith("`") and text.endswith("`"):
                            text = text[1:-1]

                        # Unescape embedded backticks
                        text = text.replace("``", "`")
                        return text

                    def accept(self, v):
                        return v.visit_identifier(self)
                return IdentifierNodeAdapter(self).accept(visitor)

            elif category == NodeCategory.TYPE_OPERATION:
                # SP-022-006: TypeSpecifier is metadata for TypeExpression, not a standalone expression.
                # If a TypeSpecifier is visited directly (e.g., when parent iterates children),
                # it should NOT be processed as a type operation. Return a placeholder that signals
                # the visitor should skip this node.
                if self.node_type == 'TypeSpecifier':
                    class TypeSpecifierPlaceholder:
                        """Placeholder for TypeSpecifier nodes visited outside their parent context."""
                        def __init__(self, enhanced_node):
                            self.text = enhanced_node.text
                            self.node_type = "typeSpecifierPlaceholder"
                            self.enhanced_node = enhanced_node
                            self.is_placeholder = True

                        def accept(self, v):
                            # Return None or call a placeholder handler
                            if hasattr(v, 'visit_type_specifier_placeholder'):
                                return v.visit_type_specifier_placeholder(self)
                            # Default: return None to signal "skip this node"
                            return None
                    return TypeSpecifierPlaceholder(self).accept(visitor)

                # SP-023-006: Handle type operations (is, as, ofType)
                class TypeOperationNodeAdapter:
                    def __init__(self, enhanced_node):
                        self.text = enhanced_node.text
                        self.node_type = "typeOperation"
                        self.enhanced_node = enhanced_node
                        self.metadata = enhanced_node.metadata
                        self.children = enhanced_node.children

                        # SP-104-002: Extract value expression from parent if available
                        # For InvocationExpression like "@2015.is(Date)", the value expression (@2015)
                        # is a sibling of the type operation in the parent's children
                        self.value_expression = None
                        if (hasattr(enhanced_node, 'parent') and
                            enhanced_node.parent and
                            enhanced_node.parent.node_type == 'InvocationExpression' and
                            len(enhanced_node.parent.children) >= 2):
                            # The parent is an InvocationExpression with multiple children
                            # The first child should be the value expression
                            for child in enhanced_node.parent.children:
                                # Skip the type operation node itself
                                if child is not enhanced_node and child.metadata:
                                    # Check if this is the value expression (not another type operation)
                                    if child.metadata.node_category != NodeCategory.TYPE_OPERATION:
                                        self.value_expression = child
                                        break

                        # Extract operation and target type
                        self.operation, self.target_type = self._extract_operation_and_type(enhanced_node)

                    def _extract_operation_and_type(self, node):
                        """Extract the type operation and target type.

                        SP-023-006: Replicated from ASTAdapter._convert_type_expression().
                        SP-103-005: Enhanced to handle ofType() with nested type structure.
                        """
                        text = node.text or ""

                        # Check custom_attributes first
                        if (node.metadata and
                            hasattr(node.metadata, 'custom_attributes') and
                            node.metadata.custom_attributes):
                            op = node.metadata.custom_attributes.get('operation')
                            if op:
                                target_type = self._extract_type_from_children(node)
                                return op, target_type

                        # SP-103-005: Check for ofType operation first
                        # The text for ofType() is 'ofType()' so we check for that pattern
                        if text == 'ofType()' or 'ofType(' in text:
                            target_type = self._extract_type_from_children(node)
                            return 'ofType', target_type or 'Unknown'

                        # Parse from text for other operations
                        if ' is ' in text:
                            return 'is', text.split(' is ')[-1].strip()
                        elif ' as ' in text:
                            return 'as', text.split(' as ')[-1].strip()

                        # Try to get type from children (TypeSpecifier)
                        target_type = self._extract_type_from_children(node)

                        # Default to 'is' operation
                        return 'is', target_type or 'Unknown'

                    def _extract_type_from_children(self, node):
                        """Extract target type from TypeSpecifier child node."""
                        # SP-103-005: Handle nested structure for type operations like ofType(Range)
                        # The AST structure for ofType(Range) is:
                        # - node (ofType())
                        #   - children[0] (parentheses)
                        #     - children[0] (operation name: ofType)
                        #     - children[1] (type specifier)
                        #       - children[0] (type name: Range)

                        # First, try the original structure (TypeSpecifier as second child)
                        if len(node.children) >= 2:
                            type_spec = node.children[1]
                            if type_spec.text:
                                return type_spec.text.strip()
                            if type_spec.children:
                                for child in type_spec.children:
                                    if child.text:
                                        return child.text.strip()

                        # SP-103-005: Try nested structure (parentheses as first child)
                        if len(node.children) >= 1 and node.children[0].children:
                            parens_node = node.children[0]
                            # Look for the type in the second child of the parentheses node
                            if len(parens_node.children) >= 2:
                                type_spec = parens_node.children[1]
                                if type_spec.text:
                                    return type_spec.text.strip()
                                # Recursively search for the type name
                                if type_spec.children:
                                    for child in type_spec.children:
                                        if child.text and child.text not in ['(', ')', '']:
                                            return child.text.strip()
                                        # Search deeper
                                        if child.children:
                                            for grandchild in child.children:
                                                if grandchild.text and grandchild.text not in ['(', ')', '']:
                                                    return grandchild.text.strip()

                        return None

                    def accept(self, v):
                        return v.visit_type_operation(self)
                return TypeOperationNodeAdapter(self).accept(visitor)

            elif category == NodeCategory.AGGREGATION:
                # SP-023-006: Handle aggregation functions (count, sum, avg, min, max)
                class AggregationNodeAdapter:
                    def __init__(self, enhanced_node):
                        self.text = enhanced_node.text
                        self.node_type = "aggregation"
                        self.enhanced_node = enhanced_node
                        self.metadata = enhanced_node.metadata
                        self.children = enhanced_node.children

                        # Extract aggregation function name
                        self.aggregation_function = self._extract_aggregation_function(enhanced_node.text)
                        self.aggregation_type = self.aggregation_function.lower()

                    def _extract_aggregation_function(self, text):
                        """Extract aggregation function name from text."""
                        if not text:
                            return "count"
                        if "(" in text:
                            return text.split("(")[0].strip()
                        return text.strip()

                    def accept(self, v):
                        return v.visit_aggregation(self)
                return AggregationNodeAdapter(self).accept(visitor)

        # SP-023-006: Handle specific node types by node_type before falling back to generic
        # TypeExpression nodes should be handled as type operations
        if self.node_type == "TypeExpression":
            # Create a TYPE_OPERATION handler
            class TypeExpressionAdapter:
                def __init__(self, enhanced_node):
                    self.text = enhanced_node.text
                    self.node_type = "typeOperation"
                    self.enhanced_node = enhanced_node
                    self.metadata = enhanced_node.metadata
                    self.children = enhanced_node.children

                    # Extract operation from children
                    self.operation, self.target_type = self._extract_operation_and_type(enhanced_node)

                def _extract_operation_and_type(self, node):
                    """Extract the type operation and target type."""
                    text = node.text or ""

                    # Check custom_attributes
                    if (node.metadata and
                        hasattr(node.metadata, 'custom_attributes') and
                        node.metadata.custom_attributes):
                        op = node.metadata.custom_attributes.get('operation')
                        if op:
                            target_type = self._extract_type_from_children(node)
                            return op, target_type or 'Unknown'

                    # Parse from text
                    if ' is ' in text:
                        return 'is', text.split(' is ')[-1].strip()
                    elif ' as ' in text:
                        return 'as', text.split(' as ')[-1].strip()

                    # Try children
                    target_type = self._extract_type_from_children(node)
                    return 'is', target_type or 'Unknown'

                def _extract_type_from_children(self, node):
                    """Extract target type from TypeSpecifier child."""
                    if len(node.children) >= 2:
                        type_spec = node.children[1]
                        if type_spec.text:
                            return type_spec.text.strip()
                        if type_spec.children:
                            for child in type_spec.children:
                                if child.text:
                                    return child.text.strip()
                    return None

                def accept(self, v):
                    return v.visit_type_operation(self)
            return TypeExpressionAdapter(self).accept(visitor)

        # SP-023-006: Handle MembershipExpression (in, contains)
        if self.node_type == "MembershipExpression":
            class MembershipExpressionAdapter:
                def __init__(self, enhanced_node):
                    self.text = enhanced_node.text
                    self.node_type = "function_call"
                    self.enhanced_node = enhanced_node
                    self.metadata = enhanced_node.metadata
                    self.children = enhanced_node.children
                    self.function_name = "contains"
                    self.target = None

                    # Determine arguments based on operator
                    self.arguments = self._extract_arguments(enhanced_node)

                def _extract_arguments(self, node):
                    """Extract arguments, converting 'in' to contains() form."""
                    if len(node.children) < 2:
                        return node.children

                    left = node.children[0]
                    right = node.children[1]

                    # Infer operator from text
                    text = node.text or ""
                    if ' in ' in text:
                        # "x in collection" → contains(collection, x)
                        return [right, left]
                    else:
                        # "collection contains x" → contains(collection, x)
                        return [left, right]

                def accept(self, v):
                    return v.visit_function_call(self)
            return MembershipExpressionAdapter(self).accept(visitor)

        # SP-023-006: Handle PolarityExpression (unary minus)
        if self.node_type == "PolarityExpression":
            if self.children and len(self.children) == 1:
                # Check if we can fold negation into a literal
                child = self.children[0]
                if (child.metadata and
                    child.metadata.node_category == NodeCategory.LITERAL):
                    # Create negated literal
                    class NegatedLiteralAdapter:
                        def __init__(self, enhanced_node, original_child):
                            child_text = original_child.text or ""
                            self.text = f"-{child_text}"
                            self.node_type = "literal"
                            self.enhanced_node = enhanced_node
                            self.metadata = original_child.metadata

                            # Parse and negate the value
                            try:
                                if '.' in child_text:
                                    self.value = -float(child_text)
                                    self.literal_type = "decimal"
                                else:
                                    self.value = -int(child_text)
                                    self.literal_type = "integer"
                            except ValueError:
                                self.value = child_text
                                self.literal_type = "string"

                            self.temporal_info = None

                        def accept(self, v):
                            return v.visit_literal(self)
                    return NegatedLiteralAdapter(self, child).accept(visitor)
                else:
                    # General case: create unary operator
                    class UnaryMinusAdapter:
                        def __init__(self, enhanced_node):
                            self.text = enhanced_node.text
                            self.node_type = "operator"
                            self.enhanced_node = enhanced_node
                            self.metadata = enhanced_node.metadata
                            self.children = enhanced_node.children
                            self.operator = "unary_minus"
                            self.operator_type = "unary"
                            self.left_operand = enhanced_node.children[0] if enhanced_node.children else None
                            self.right_operand = None

                        def accept(self, v):
                            return v.visit_operator(self)
                    return UnaryMinusAdapter(self).accept(visitor)

        # Fallback: call generic visit
        return visitor.visit_generic(self)

    def __str__(self) -> str:
        """String representation of the node"""
        return f"{self.node_type}({self.text})"

    def __repr__(self) -> str:
        """Detailed string representation"""
        metadata_info = ""
        if self.metadata:
            metadata_info = f", category={self.metadata.node_category.value}"
        return f"EnhancedASTNode(type={self.node_type}, text='{self.text}'{metadata_info})"


class ASTNodeFactory:
    """Factory for creating enhanced AST nodes with appropriate metadata"""

    @staticmethod
    def create_path_node(text: str, fhir_type: Optional[str] = None) -> EnhancedASTNode:
        """Create a path expression node"""
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.PATH_EXPRESSION) \
            .with_type_info(TypeInformation(
                expected_output_type=fhir_type,
                sql_data_type=SQLDataType.JSON if fhir_type else SQLDataType.UNKNOWN,
                fhir_type=fhir_type
            )) \
            .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
            .with_source_location(text) \
            .build()

        return EnhancedASTNode(
            node_type="pathExpression",
            text=text,
            metadata=metadata
        )

    @staticmethod
    def create_function_node(function_name: str, text: str) -> EnhancedASTNode:
        """Create a function call node"""
        # Determine metadata based on function type
        category = NodeCategory.FUNCTION_CALL
        hints = {OptimizationHint.PROJECTION_SAFE}
        sql_type = SQLDataType.UNKNOWN

        # SP-103-005: Check for type operations before other categories
        if function_name.lower() in ['is', 'as', 'oftype']:
            category = NodeCategory.TYPE_OPERATION
        elif function_name in ['count', 'sum', 'avg', 'min', 'max']:
            category = NodeCategory.AGGREGATION
            hints.add(OptimizationHint.AGGREGATION_CANDIDATE)
            sql_type = SQLDataType.INTEGER if function_name == 'count' else SQLDataType.DECIMAL
        elif function_name in ['where', 'select']:
            category = NodeCategory.CONDITIONAL
            hints.add(OptimizationHint.POPULATION_FILTER)
        elif function_name in ['first', 'last', 'tail', 'take']:
            hints.add(OptimizationHint.VECTORIZABLE)

        metadata = MetadataBuilder() \
            .with_category(category) \
            .with_type_info(TypeInformation(sql_data_type=sql_type)) \
            .with_source_location(text) \
            .build()

        for hint in hints:
            metadata.optimization_hints.add(hint)

        return EnhancedASTNode(
            node_type="functionCall",
            text=text,
            metadata=metadata
        )

    @staticmethod
    def create_literal_node(value: Any, text: str) -> EnhancedASTNode:
        """Create a literal value node"""
        sql_type = SQLDataType.UNKNOWN

        if isinstance(value, bool):  # Check bool before int since bool is subclass of int
            sql_type = SQLDataType.BOOLEAN
        elif isinstance(value, str):
            sql_type = SQLDataType.TEXT
        elif isinstance(value, int):
            sql_type = SQLDataType.INTEGER
        elif isinstance(value, float):
            sql_type = SQLDataType.DECIMAL

        metadata = MetadataBuilder() \
            .with_category(NodeCategory.LITERAL) \
            .with_type_info(TypeInformation(
                sql_data_type=sql_type,
                is_collection=False,
                is_nullable=False
            )) \
            .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
            .with_source_location(text) \
            .build()

        return EnhancedASTNode(
            node_type="literal",
            text=text,
            metadata=metadata
        )

    @staticmethod
    def create_operator_node(operator: str, text: str) -> EnhancedASTNode:
        """Create an operator node"""
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.OPERATOR) \
            .with_type_info(TypeInformation(
                sql_data_type=SQLDataType.BOOLEAN if operator in ['=', '!=', '<', '>', '<=', '>='] else SQLDataType.UNKNOWN
            )) \
            .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
            .with_source_location(text) \
            .build()

        return EnhancedASTNode(
            node_type="operator",
            text=text,
            metadata=metadata
        )

    @staticmethod
    def create_from_fhirpath_node(fhirpath_node: Union[Dict[str, Any], Any]) -> EnhancedASTNode:
        """Create enhanced node from original fhirpath-py node"""
        # Handle dictionary-based AST structure from fhirpath-py
        if isinstance(fhirpath_node, dict):
            node_type = fhirpath_node.get('type', 'unknown')
            text = fhirpath_node.get('text', '')
            children = fhirpath_node.get('children', [])
            terminal_node_text = fhirpath_node.get('terminalNodeText', [])

            if not text and terminal_node_text:
                text = " ".join(token.strip() for token in terminal_node_text if token)

            # Handle case where top-level node is just a wrapper (no type/text)
            if not node_type or node_type == 'unknown':
                if children and len(children) == 1:
                    # If there's exactly one child, use that as the root
                    return ASTNodeFactory.create_from_fhirpath_node(children[0])
        else:
            # Fallback for object-based structure
            node_type = getattr(fhirpath_node, 'type', 'unknown')
            text = getattr(fhirpath_node, 'text', '')
            children = getattr(fhirpath_node, 'children', [])
            terminal_node_text = getattr(fhirpath_node, 'terminalNodeText', [])

            if not text and terminal_node_text:
                text = " ".join(token.strip() for token in terminal_node_text if token)

        # Create appropriate enhanced node based on type
        if node_type.lower() == 'functioninvocation':
            # This is a function call - need to extract function name from children
            function_name = ASTNodeFactory._extract_function_name(fhirpath_node)
            function_text = f"{function_name}()"
            node = ASTNodeFactory.create_function_node(function_name, function_text)
        elif node_type == 'TypeExpression':
            # TypeExpression: preserve operation (is/as) in custom_attributes
            category = NodeCategory.FUNCTION_CALL  # Type expressions are function-like
            metadata = MetadataBuilder() \
                .with_category(category) \
                .with_source_location(text) \
                .build()

            # Extract operation from terminalNodeText
            operation = terminal_node_text[0] if terminal_node_text else 'is'

            # Store operation in custom_attributes for ast_adapter to access
            metadata.custom_attributes['operation'] = operation

            node = EnhancedASTNode(
                node_type=node_type,
                text=text,
                metadata=metadata
            )
        elif 'invocation' in node_type.lower() and 'function' not in node_type.lower():
            # Regular invocation expression (not a function call)
            metadata = MetadataBuilder.create_node_metadata(node_type, text)
            node = EnhancedASTNode(
                node_type=node_type,
                text=text,
                metadata=metadata
            )
        elif 'literal' in node_type.lower():
            # Special handling for QuantityLiteral nodes
            if node_type == 'QuantityLiteral':
                # Extract value and unit from the quantity literal structure
                value_str, unit_str = ASTNodeFactory._extract_quantity_info(fhirpath_node)

                # Create quantity metadata
                metadata = MetadataBuilder() \
                    .with_category(NodeCategory.LITERAL) \
                    .with_type_info(TypeInformation(
                        sql_data_type=SQLDataType.TEXT,  # Quantities stored as text
                        is_collection=False,
                        is_nullable=False,
                        fhir_type='Quantity'
                    )) \
                    .with_optimization_hint(OptimizationHint.PROJECTION_SAFE) \
                    .with_source_location(text) \
                    .build()

                # Store quantity info in custom_attributes for later use
                metadata.custom_attributes['literal_type'] = 'quantity'
                metadata.custom_attributes['quantity_value'] = value_str
                metadata.custom_attributes['quantity_unit'] = unit_str

                node = EnhancedASTNode(
                    node_type="literal",
                    text=text,
                    metadata=metadata
                )
            else:
                # Regular literal (string, number, boolean, etc.)
                node = ASTNodeFactory.create_literal_node(text, text)
        elif 'identifier' in node_type.lower() or 'path' in node_type.lower():
            node = ASTNodeFactory.create_path_node(text)
        else:
            # Generic node with appropriate category classification
            # Use the enhanced metadata builder that properly categorizes arithmetic operators
            metadata = MetadataBuilder.create_node_metadata(node_type, text)
            node = EnhancedASTNode(
                node_type=node_type,
                text=text,
                metadata=metadata
            )

        # Recursively process children if they exist
        for child in children:
            enhanced_child = ASTNodeFactory.create_from_fhirpath_node(child)
            node.add_child(enhanced_child)

        if (node.metadata and
                node.metadata.custom_attributes is not None and
                node.metadata.node_category == NodeCategory.OPERATOR and
                node.text):
            node.metadata.custom_attributes['operator'] = node.text.strip()

        return node

    @staticmethod
    def _extract_function_name(fhirpath_node: Union[Dict[str, Any], Any]) -> str:
        """Extract function name from a FunctionInvocation node"""
        if isinstance(fhirpath_node, dict):
            children = fhirpath_node.get('children', [])
        else:
            children = getattr(fhirpath_node, 'children', [])

        # Look for Functn -> Identifier pattern
        for child in children:
            if isinstance(child, dict):
                child_type = child.get('type', '')
                child_children = child.get('children', [])
            else:
                child_type = getattr(child, 'type', '')
                child_children = getattr(child, 'children', [])

            if child_type == 'Functn':
                # Look for Identifier in Functn children
                for grandchild in child_children:
                    if isinstance(grandchild, dict):
                        gc_type = grandchild.get('type', '')
                        gc_text = grandchild.get('text', '')
                    else:
                        gc_type = getattr(grandchild, 'type', '')
                        gc_text = getattr(grandchild, 'text', '')

                    if gc_type == 'Identifier' and gc_text:
                        return gc_text

        return 'unknown'

    @staticmethod
    def _extract_quantity_info(fhirpath_node: Union[Dict[str, Any], Any]) -> tuple[Optional[str], Optional[str]]:
        """Extract quantity value and unit from a QuantityLiteral node.

        Returns:
            Tuple of (value_str, unit_str) where value_str is the numeric value as string
            and unit_str is the unit (e.g., 'days', 'wk'). Returns (None, None) if not found.
        """
        if isinstance(fhirpath_node, dict):
            children = fhirpath_node.get('children', [])
            terminal_node_text = fhirpath_node.get('terminalNodeText', [])
        else:
            children = getattr(fhirpath_node, 'children', [])
            terminal_node_text = getattr(fhirpath_node, 'terminalNodeText', [])

        # Extract value from terminalNodeText (should be the number)
        value_str = None
        if terminal_node_text and len(terminal_node_text) > 0:
            value_str = terminal_node_text[0].strip()

        # Extract unit from children (look for Unit node)
        unit_str = None
        for child in children:
            if isinstance(child, dict):
                child_type = child.get('type', '')
                child_children = child.get('children', [])
            else:
                child_type = getattr(child, 'type', '')
                child_children = getattr(child, 'children', [])

            if child_type == 'Unit':
                # Look for DateTimePrecision or PluralDateTimePrecision
                for grandchild in child_children:
                    if isinstance(grandchild, dict):
                        gc_type = grandchild.get('type', '')
                        gc_terminal = grandchild.get('terminalNodeText', [])
                    else:
                        gc_type = getattr(grandchild, 'type', '')
                        gc_terminal = getattr(grandchild, 'terminalNodeText', [])

                    if gc_type in ['DateTimePrecision', 'PluralDateTimePrecision']:
                        if gc_terminal and len(gc_terminal) > 0:
                            unit_str = gc_terminal[0].strip()
                            break

                # Also check if unit is a string literal (e.g., '1 \'wk\'')
                if not unit_str:
                    for grandchild in child_children:
                        if isinstance(grandchild, dict):
                            gc_type = grandchild.get('type', '')
                            gc_terminal = grandchild.get('terminalNodeText', [])
                        else:
                            gc_type = getattr(grandchild, 'type', '')
                            gc_terminal = getattr(grandchild, 'terminalNodeText', [])

                        if gc_type == 'StringLiteral' and gc_terminal and len(gc_terminal) > 0:
                            # Remove quotes from string literal
                            unit_str = gc_terminal[0].strip().strip('\'"')
                            break

        return value_str, unit_str

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
            # SP-103-005: Check for type operations (is, as, ofType) before aggregation
            # Match patterns like "is(", "as(", "oftype(", "is()", "as()", "oftype()"
            if any(pattern in text_lower for pattern in ['is(', 'as(', 'oftype(', 'is()', 'as()', 'oftype()']):
                return NodeCategory.TYPE_OPERATION
            # Check if it's an aggregation function
            elif any(func in text_lower for func in ['count', 'sum', 'avg', 'min', 'max']):
                return NodeCategory.AGGREGATION
            else:
                return NodeCategory.FUNCTION_CALL
        elif 'expression' in node_type_lower:
            # Check for conditional expressions
            if any(keyword in text_lower for keyword in ['where', 'select', 'exists']):
                return NodeCategory.CONDITIONAL
            else:
                return NodeCategory.PATH_EXPRESSION
        elif any(op in text for op in ['=', '!=', '<', '>', '<=', '>=', '|']):
            return NodeCategory.OPERATOR
        else:
            return NodeCategory.PATH_EXPRESSION  # Default fallback


class ASTAnalyzer:
    """Analyzer for enhanced AST trees"""

    @staticmethod
    def analyze_complexity(root: EnhancedASTNode) -> Dict[str, Any]:
        """Analyze the complexity of an AST tree"""
        def count_nodes_by_category(node: EnhancedASTNode) -> Dict[NodeCategory, int]:
            counts = {}
            if node.metadata:
                category = node.metadata.node_category
                counts[category] = counts.get(category, 0) + 1

            for child in node.children:
                child_counts = count_nodes_by_category(child)
                for cat, count in child_counts.items():
                    counts[cat] = counts.get(cat, 0) + count
            return counts

        category_counts = count_nodes_by_category(root)
        total_nodes = sum(category_counts.values())

        return {
            "total_nodes": total_nodes,
            "max_depth": ASTAnalyzer._get_max_depth(root),
            "category_distribution": {cat.value: count for cat, count in category_counts.items()},
            "has_aggregations": NodeCategory.AGGREGATION in category_counts,
            "has_functions": (NodeCategory.FUNCTION_CALL in category_counts or
                            NodeCategory.AGGREGATION in category_counts),
            "complexity_score": ASTAnalyzer._calculate_complexity_score(category_counts, total_nodes)
        }

    @staticmethod
    def _get_max_depth(node: EnhancedASTNode) -> int:
        """Get maximum depth of the tree"""
        if not node.children:
            return 1
        return 1 + max(ASTAnalyzer._get_max_depth(child) for child in node.children)

    @staticmethod
    def _calculate_complexity_score(category_counts: Dict[NodeCategory, int], total_nodes: int) -> float:
        """Calculate a complexity score for the AST"""
        # Weight different node types by complexity
        weights = {
            NodeCategory.LITERAL: 1.0,
            NodeCategory.PATH_EXPRESSION: 2.0,
            NodeCategory.OPERATOR: 2.0,
            NodeCategory.FUNCTION_CALL: 3.0,
            NodeCategory.CONDITIONAL: 4.0,
            NodeCategory.AGGREGATION: 5.0,
            NodeCategory.TYPE_OPERATION: 3.0
        }

        weighted_sum = sum(
            counts * weights.get(category, 3.0)
            for category, counts in category_counts.items()
        )

        return weighted_sum / max(total_nodes, 1)

    @staticmethod
    def find_optimization_opportunities(root: EnhancedASTNode) -> List[Dict[str, Any]]:
        """Find optimization opportunities in the AST"""
        opportunities = []

        # Find CTE extraction candidates
        cte_candidates = root.find_nodes_by_category(NodeCategory.FUNCTION_CALL)
        for node in cte_candidates:
            if node.has_optimization_hint(OptimizationHint.CTE_REUSABLE):
                opportunities.append({
                    "type": "cte_extraction",
                    "node": node,
                    "reason": "Function call can be extracted to CTE for reuse"
                })

        # Find population filter opportunities
        filter_candidates = []
        for node in root.find_nodes_by_category(NodeCategory.CONDITIONAL):
            if node.has_optimization_hint(OptimizationHint.POPULATION_FILTER):
                filter_candidates.append(node)

        if filter_candidates:
            opportunities.append({
                "type": "population_filter",
                "nodes": filter_candidates,
                "reason": "Conditional expressions can be optimized for population queries"
            })

        # Find aggregation opportunities
        agg_nodes = root.find_nodes_by_category(NodeCategory.AGGREGATION)
        if agg_nodes:
            opportunities.append({
                "type": "aggregation_optimization",
                "nodes": agg_nodes,
                "reason": "Aggregation operations can leverage SQL aggregation functions"
            })

        return opportunities
