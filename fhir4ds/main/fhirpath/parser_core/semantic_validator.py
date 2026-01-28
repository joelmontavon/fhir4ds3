"""
Semantic validation utilities for FHIRPath expressions.

Provides lightweight semantic checks ahead of full evaluator integration to
prevent invalid expressions from being treated as successful parses. The
validator focuses on the scenarios uncovered in Sprint 008 investigations:

- Prevent direct access to choice-type aliases like ``valueQuantity``
- Detect invalid identifier suffixes such as ``given1``
- Enforce context resource consistency (e.g., Encounter expressions on Patient data)
- Guard against invalid property access following ``as(Period)``
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from ..exceptions import FHIRPathParseError
from ..types import FHIRTypeSystem, get_type_registry
from .ast_extensions import EnhancedASTNode

_ESCAPED_SEGMENT = r"(?:`[^`]+`|[A-Za-z_][A-Za-z0-9_]*)"
_ABSOLUTE_ROOT_SEGMENT = r"(?:`[^`]+`|[A-Z][A-Za-z0-9_]*)"
_RELATIVE_ROOT_SEGMENT = r"(?:`[^`]+`|[a-z_][A-Za-z0-9_]*)"
_ABSOLUTE_PATH_REGEX = re.compile(rf"\b({_ABSOLUTE_ROOT_SEGMENT}(?:\.{_ESCAPED_SEGMENT})+)")
_RELATIVE_PATH_REGEX = re.compile(rf"\b({_RELATIVE_ROOT_SEGMENT}(?:\.{_ESCAPED_SEGMENT})+)")

# Standard FHIRPath built-in functions
# This list is maintained separately from the SQL translator to support semantic validation
_FHIRPATH_BUILTIN_FUNCTIONS = {
    # Collection operations
    'where', 'select', 'all', 'any', 'exists', 'empty', 'count', 'distinct',
    'combine', 'first', 'last', 'tail', 'skip', 'take', 'single', 'iif',
    # Type conversion functions
    'convertsToBoolean', 'toBoolean', 'convertsToInteger', 'toInteger',
    'convertsToDecimal', 'toDecimal', 'convertsToString', 'toString',
    'convertsToQuantity', 'toQuantity', 'convertsToDate', 'toDate',
    'convertsToDateTime', 'toDateTime', 'convertsToTime', 'toTime',
    # String functions
    'startsWith', 'endsWith', 'contains', 'substring', 'length', 'upper',
    'lower', 'matches', 'replace', 'replaceMatches', 'split', 'join', 'indexOf',
    'toChars',
    # Math functions
    'abs', 'ceiling', 'exp', 'floor', 'ln', 'log', 'power', 'round', 'sqrt', 'truncate',
    # Type functions
    'is', 'as', 'ofType', 'conformsTo',
    # Date/time functions
    'now', 'today',
    # Additional functions not in base FunctionLibrary
    'exclude', 'isDistinct', 'intersect', 'repeat', 'aggregate',
    'extension', 'allTrue', 'anyTrue', 'allFalse', 'anyFalse',
    'sum', 'average', 'subsetOf', 'supersetOf',
}


@dataclass
class SemanticValidator:
    """
    Lightweight semantic validator for parsed FHIRPath expressions.

    The validator focuses on high-impact failure modes identified during
    SP-008 investigations. It is *not* a full StructureDefinition driven
    validator yet, but it blocks the incorrect success paths that masked
    compliance failures in the official test suite.
    """

    _choice_type_suffixes: Sequence[str] = field(default_factory=list)
    _period_properties: Set[str] = field(default_factory=lambda: {"start", "end"})

    _alias_pattern_template: str = ".value{suffix}"
    _identifier_with_digit_rgx: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"\.([A-Za-z_]+[0-9]+)(?=[^A-Za-z0-9_]|$)")
    )
    _period_function_rgx: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"\.as\(Period\)\.([A-Za-z_][A-Za-z0-9_]*)")
    )
    _period_cast_rgx: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"asPeriod\)\.([A-Za-z_][A-Za-z0-9_]*)")
    )
    _absolute_path_rgx: re.Pattern[str] = field(default=_ABSOLUTE_PATH_REGEX, init=False, repr=False)
    _relative_path_rgx: re.Pattern[str] = field(default=_RELATIVE_PATH_REGEX, init=False, repr=False)
    _special_operation_names: Set[str] = field(
        default_factory=lambda: {"as", "is", "oftype", "not"}
    )

    _type_registry: "TypeRegistry" = field(init=False)
    _valid_functions: Set[str] = field(default_factory=set)
    _valid_functions_lower: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Warm up choice-type suffix list from the global type registry."""
        self._type_registry = get_type_registry()

        if not self._choice_type_suffixes:
            # Choice-type aliases follow the FHIR [x] naming convention where
            # the suffix is a FHIR data type with an initial uppercase letter.
            self._choice_type_suffixes = tuple(
                name for name in self._type_registry.get_all_type_names()
                if name and name[0].isupper()
            )

        if not self._valid_functions:
            # Use static function list instead of importing from evaluator
            self._valid_functions = set(_FHIRPATH_BUILTIN_FUNCTIONS)
            # Normalise for case-insensitive lookups while preserving canonical casing
            self._valid_functions_lower = {
                func.lower(): func for func in self._valid_functions
            }
            self._special_operation_names = {name.lower() for name in self._special_operation_names}

    def validate(
        self,
        raw_expression: str,
        parsed_expression: Optional["FHIRPathExpressionWrapper"] = None,
        context: Optional[Dict[str, object]] = None,
    ) -> None:
        """
        Execute semantic validation rules.

        Args:
            raw_expression: Original FHIRPath expression text.
            parsed_expression: Optional parsed expression wrapper (provides AST access).
            context: Optional evaluation context metadata (expects ``resourceType``).

        Raises:
            FHIRPathParseError: When a semantic rule is violated.
        """
        collapsed = re.sub(r"\s+", "", raw_expression or "")

        self._validate_context_root(raw_expression, context)
        self._validate_choice_aliases(collapsed)
        self._validate_identifier_suffixes(raw_expression)
        self._validate_period_property_access(collapsed)
        self._validate_time_literal_timezones(raw_expression)

        masked_expression = self._mask_expression(raw_expression or "")
        masked_with_backticks = self._mask_expression(raw_expression or "", preserve_backticks=True)
        snippet_state: Dict[str, int] = {}

        if parsed_expression is not None and parsed_expression.ast is not None:
            # SP-102-004: Validate incomplete expressions
            self._validate_incomplete_expressions(raw_expression, parsed_expression.ast)

            # SP-106-007: Validate temporal comparison type compatibility
            self._validate_temporal_comparison_compatibility(raw_expression, parsed_expression.ast)

            self._validate_function_definitions(
                raw_expression,
                parsed_expression,
                masked_expression,
                snippet_state
            )
            self._validate_numeric_operations(
                parsed_expression.ast,
                raw_expression,
                masked_expression,
                snippet_state
            )
            self._validate_element_access(
                raw_expression,
                parsed_expression,
                context,
                masked_expression,
                masked_with_backticks,
            )

    # ------------------------------------------------------------------ #
    # Individual rule implementations
    # ------------------------------------------------------------------ #

    def _validate_context_root(
        self, expression: str, context: Optional[Dict[str, object]]
    ) -> None:
        """Ensure that absolute expressions match the provided resource context."""
        if not context:
            return

        resource_type = context.get("resourceType")
        if not isinstance(resource_type, str) or not resource_type:
            return

        root_identifier = self._extract_root_identifier(expression)
        if not root_identifier or not root_identifier[0].isupper():
            # Relative or function-based paths are evaluated relative to context
            return

        if root_identifier != resource_type:
            raise FHIRPathParseError(
                f"Expression root '{root_identifier}' is invalid for resource type "
                f"'{resource_type}'."
            )

    def _validate_choice_aliases(self, collapsed_expression: str) -> None:
        """Disallow direct access to [x] choice aliases such as valueQuantity.

        SP-106-001: Allow generic '.value' access (choice field) while blocking
        specific aliases like '.valueQuantity'. The FHIRPath specification supports
        accessing choice fields directly (e.g., Observation.value), but requires
        type functions for specific type access (e.g., value.as(Quantity)).
        """
        for suffix in self._choice_type_suffixes:
            alias = self._alias_pattern_template.format(suffix=suffix)
            # Only block if the specific alias appears (e.g., .valueQuantity)
            # Allow generic .value (choice field without type suffix)
            if alias in collapsed_expression:
                raise FHIRPathParseError(
                    f"Direct access to choice-type alias '{alias.lstrip('.')}' is not "
                    "supported. Use type functions like value.as(Quantity) instead."
                )

    def _validate_identifier_suffixes(self, expression: str) -> None:
        """Detect identifiers that end with digits (e.g., given1)."""
        for match in self._identifier_with_digit_rgx.finditer(expression):
            identifier = match.group(1)
            raise FHIRPathParseError(
                f"Invalid element name '{identifier}'. FHIR element names do not end with digits."
            )

    def _validate_period_property_access(self, collapsed_expression: str) -> None:
        """
        Ensure that Period casts only access supported properties (start, end).
        """
        for regex in (self._period_function_rgx, self._period_cast_rgx):
            for match in regex.finditer(collapsed_expression):
                property_name = match.group(1)
                if property_name not in self._period_properties:
                    raise FHIRPathParseError(
                        f"Property '{property_name}' is invalid for Period. "
                        "Allowed properties are: start, end."
                    )

    @staticmethod
    def _extract_root_identifier(expression: str) -> Optional[str]:
        """Extract the leading identifier before the first path separator."""
        if not expression:
            return None

        trimmed = expression.lstrip()
        # Remove balanced leading parentheses to reach the underlying identifier.
        while trimmed.startswith("("):
            trimmed = trimmed[1:].lstrip()

        match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", trimmed)
        return match.group(1) if match else None

    # ------------------------------------------------------------------ #
    # Internal helper utilities
    # ------------------------------------------------------------------ #

    def _mask_expression(self, expression: str, *, preserve_backticks: bool = False) -> str:
        """Replace strings and comments with spaces to simplify substring searches."""
        if not expression:
            return ""

        chars = list(expression)
        length = len(chars)
        index = 0
        in_single_quote = False
        in_double_quote = False
        in_backtick = False
        block_depth = 0

        while index < length:
            current = expression[index]
            next_char = expression[index + 1] if index + 1 < length else ""

            if block_depth > 0:
                chars[index] = " "
                if current == "/" and next_char == "*":
                    chars[index + 1] = " "
                    block_depth += 1
                    index += 2
                    continue
                if current == "*" and next_char == "/":
                    chars[index + 1] = " "
                    block_depth -= 1
                    index += 2
                    continue
                index += 1
                continue

            if in_single_quote:
                chars[index] = " "
                if current == "\\" and index + 1 < length:
                    chars[index + 1] = " "
                    index += 2
                    continue
                if current == "'":
                    in_single_quote = False
                index += 1
                continue

            if in_double_quote:
                chars[index] = " "
                if current == "\\" and index + 1 < length:
                    chars[index + 1] = " "
                    index += 2
                    continue
                if current == '"':
                    in_double_quote = False
                index += 1
                continue

            if in_backtick:
                if not preserve_backticks:
                    chars[index] = " "
                if current == "\\" and index + 1 < length:
                    if not preserve_backticks:
                        chars[index + 1] = " "
                    index += 2
                    continue
                if current == "`":
                    in_backtick = False
                index += 1
                continue

            if current == "'":
                chars[index] = " "
                in_single_quote = True
                index += 1
                continue

            if current == '"':
                chars[index] = " "
                in_double_quote = True
                index += 1
                continue

            if current == "`":
                if not preserve_backticks:
                    chars[index] = " "
                in_backtick = True
                index += 1
                continue

            if current == "/" and next_char == "/":
                chars[index] = chars[index + 1] = " "
                index += 2
                while index < length:
                    next_current = expression[index]
                    if next_current in ("\n", "\r"):
                        break
                    chars[index] = " "
                    index += 1
                continue

            if current == "/" and next_char == "*":
                chars[index] = chars[index + 1] = " "
                block_depth = 1
                index += 2
                continue

            index += 1

        return "".join(chars)

    @staticmethod
    def _compute_position(expression: str, index: int) -> Tuple[int, int]:
        """Compute 1-based line and column numbers for a character index."""
        if index <= 0:
            return 1, 1

        line = 1
        column = 1
        cursor = 0
        length = min(index, len(expression))

        while cursor < length:
            char = expression[cursor]

            if char == "\r":
                if cursor + 1 < len(expression) and expression[cursor + 1] == "\n":
                    cursor += 1
                line += 1
                column = 1
            elif char == "\n":
                line += 1
                column = 1
            else:
                column += 1

            cursor += 1

        return line, column

    @staticmethod
    def _iterate_nodes(root: EnhancedASTNode) -> List[EnhancedASTNode]:
        """Depth-first traversal yielding all nodes."""
        nodes: List[EnhancedASTNode] = []
        stack = [root]

        while stack:
            node = stack.pop()
            nodes.append(node)
            stack.extend(reversed(node.children))

        return nodes

    def _infer_literal_type(self, node: EnhancedASTNode) -> Optional[str]:
        """Infer the literal type (string, number, boolean) if node contains a literal."""
        literal_node = self._find_literal_node(node)
        if literal_node is None:
            return None

        token = literal_node.text.strip()
        if not token:
            return None

        if token[0] in {"'", '"'} and token[-1] == token[0]:
            return "string"

        if re.fullmatch(r"-?\d+(\.\d+)?", token):
            return "number"

        if token.lower() in {"true", "false"}:
            return "boolean"

        if token.startswith("@"):
            return "temporal"

        return "unknown"

    def _find_literal_node(self, node: EnhancedASTNode) -> Optional[EnhancedASTNode]:
        """Find the first descendant literal node."""
        if node.node_type == "literal":
            return node

        for child in node.children:
            result = self._find_literal_node(child)
            if result is not None:
                return result

        return None

    def _is_known_function(self, name: str) -> bool:
        """Check whether a function or operation name is recognised."""
        if not name:
            return False

        lowered = name.lower()
        return (
            lowered in self._valid_functions_lower
            or lowered in self._special_operation_names
        )

    def _suggest_function(self, name: str) -> Optional[str]:
        """Return the closest known function name for suggestion purposes."""
        possibilities = list(self._valid_functions) + [
            op for op in {"as", "is", "ofType"}
        ]
        matches = difflib.get_close_matches(name, possibilities, n=1, cutoff=0.6)
        return matches[0] if matches else None

    def _next_snippet_index(
        self,
        masked_expression: str,
        snippet: str,
        state: Dict[str, int]
    ) -> Optional[int]:
        """Locate the next occurrence of snippet outside strings/comments."""
        if not snippet:
            return None

        start = state.get(snippet, 0)
        index = masked_expression.find(snippet, start)

        if index == -1:
            index = masked_expression.find(snippet)
            if index == -1:
                return None

        state[snippet] = index + len(snippet)
        return index

    # ------------------------------------------------------------------ #
    # Enhanced validation routines
    # ------------------------------------------------------------------ #

    def _validate_function_definitions(
        self,
        expression: str,
        parsed_expression: "FHIRPathExpressionWrapper",
        masked_expression: str,
        snippet_state: Dict[str, int]
    ) -> None:
        """Ensure all function invocations reference known functions."""
        for function_call in parsed_expression.functions:
            name = function_call.split("(", 1)[0].strip()
            if not name or self._is_known_function(name):
                continue

            snippet = f"{name}("
            index = self._next_snippet_index(masked_expression, snippet, snippet_state)
            if index is None:
                index = expression.find(name)

            line, column = self._compute_position(expression, index)
            suggestion = self._suggest_function(name)

            message = (
                f"Unknown function '{name}' at line {line}, column {column}."
            )
            if suggestion:
                message += f" Did you mean '{suggestion}'?"
            else:
                message += " Refer to the FHIRPath specification for supported functions."

            raise FHIRPathParseError(message)

    def _validate_numeric_operations(
        self,
        ast: EnhancedASTNode,
        expression: str,
        masked_expression: str,
        snippet_state: Dict[str, int]
    ) -> None:
        """Detect clearly invalid literal arithmetic operations."""
        for node in self._iterate_nodes(ast):
            if node.node_type not in {"AdditiveExpression", "MultiplicativeExpression"}:
                continue

            operator = node.text.strip()
            if operator not in {"+", "-", "*", "/"}:
                continue

            if len(node.children) < 2:
                continue

            left_type = self._infer_literal_type(node.children[0])
            right_type = self._infer_literal_type(node.children[1])

            # Restrict to literal-literal checks to avoid false positives on dynamic paths
            if left_type is None or right_type is None:
                continue

            if "string" not in {left_type, right_type}:
                continue

            index = self._next_snippet_index(masked_expression, operator, snippet_state)
            if index is None:
                index = expression.find(operator)

            line, column = self._compute_position(expression, index)
            raise FHIRPathParseError(
                f"Operator '{operator}' does not support string literals at line {line}, column {column}. "
                "Use '&' for string concatenation or cast values to numbers."
            )

    def _validate_element_access(
        self,
        expression: str,
        parsed_expression: "FHIRPathExpressionWrapper",
        context: Optional[Dict[str, object]],
        masked_expression: str,
        masked_with_backticks: str,
    ) -> None:
        """Validate element navigation against the type registry."""
        # SP-103-005: Check if expression contains type-changing functions
        # These functions (ofType, as, etc.) make static validation unreliable
        # without full type inference, so we skip path validation when present.
        collapsed = re.sub(r'\s+', '', expression or '')
        has_type_changing_function = any(
            f'{func}(' in collapsed for func in ('ofType', 'as(', 'asType(', 'convertsTo(')
        )

        if has_type_changing_function:
            # Skip path validation - type changes make it unreliable
            return

        # Absolute paths (Patient.name.given)
        for match in self._absolute_path_rgx.finditer(masked_with_backticks):
            path = match.group(1)
            self._validate_path_segments(
                expression,
                path,
                match.start(1),
                root_override=None
            )

        # Relative paths when a resource type context is supplied
        resource_type = None
        if context and isinstance(context.get("resourceType"), str):
            resource_type = context["resourceType"]

        if resource_type:
            for match in self._relative_path_rgx.finditer(masked_with_backticks):
                path = match.group(1)
                # Avoid re-validating absolute paths that start with uppercase identifiers
                if path and path[0].isupper():
                    continue
                # SP-106: Skip validation for variable references ($this, $variable)
                # Variables are not part of the resource type schema
                # Check original expression at match position for $ prefix (regex \b excludes it)
                if masked_expression[match.start()-1:match.start()] == '$':
                    continue
                self._validate_path_segments(
                    expression,
                    path,
                    match.start(1),
                    root_override=resource_type
                )

    def _validate_path_segments(
        self,
        expression: str,
        path: str,
        path_start_index: int,
        root_override: Optional[str]
    ) -> None:
        """Validate a dot-delimited path sequence against the type registry."""
        if not path:
            return

        segments = path.split(".")
        if not segments:
            return

        registry = self._type_registry

        if root_override:
            current_type = registry.get_canonical_name(root_override)
            segment_range = range(0, len(segments))
        else:
            root_type = segments[0]
            if not registry.is_registered_type(root_type):
                return
            current_type = registry.get_canonical_name(root_type)
            segment_range = range(1, len(segments))

        for idx in segment_range:
            raw_segment = segments[idx]
            if self._is_known_function(raw_segment):
                break

            segment = raw_segment.strip("`")
            if not segment:
                continue

            # SP-103-007: Skip validation for boolean literals (true, false)
            # These are not path elements but literal values
            if segment.lower() in {"true", "false"}:
                break

            element_type = registry.get_element_type(current_type, segment)
            if element_type is None:
                if current_type in {"BackboneElement", "Element"}:
                    # BackboneElement slots are often expanded dynamically (e.g., value[x])
                    return
                available_elements = registry.get_element_names(current_type)
                choice_candidate = f"{segment}[x]"
                if choice_candidate in available_elements:
                    # Choice-type placeholder (e.g., value → value[x]); type will be refined by casts.
                    continue

                offset = sum(len(segments[i]) for i in range(idx)) + idx
                if not root_override:
                    # Account for the root segment and dot when computing offsets
                    offset += len(segments[0]) + 1
                segment_index = path_start_index + offset
                line, column = self._compute_position(expression, segment_index)

                suggestions = available_elements
                hint = ""
                if suggestions:
                    close_matches = difflib.get_close_matches(segment, suggestions, n=3, cutoff=0.5)
                    if close_matches:
                        hint = f" Did you mean: {', '.join(close_matches)}?"

                raise FHIRPathParseError(
                    f"Unknown element '{segment}' on type '{current_type}' at line {line}, column {column}.{hint}"
                )

            current_type = registry.get_canonical_name(element_type)

    def _validate_incomplete_expressions(
        self,
        raw_expression: str,
        parsed_ast: EnhancedASTNode
    ) -> None:
        """
        SP-102-004: Validate that expressions are complete and well-formed.

        Detects incomplete expressions such as trailing operators:
        - "2 + 2 /" (missing right operand)
        - "1 + " (missing right operand)
        - "5 * " (missing right operand)

        Args:
            raw_expression: Original expression text
            parsed_ast: Parsed AST node

        Raises:
            FHIRPathParseError: When expression is incomplete
        """
        # Check for trailing operators that indicate incomplete expressions
        # Pattern: ends with operator (+, -, *, /, |, &, =, !=, <, >, <=, >=, ~, etc.)
        trimmed = raw_expression.strip()

        # Special case: if expression ends with '*/' (comment terminator), skip validation
        # The '/' is part of the comment terminator, not a division operator
        if re.search(r'\*/\s*$', trimmed):
            return

        # List of binary operators that should not appear at the end of an expression
        binary_operators = [
            '+', '-', '*', '/', '|', '&', '=', '!=',
            '<', '>', '<=', '>=', '~', '!', 'or', 'and',
            'in', 'contains', 'is', 'as'
        ]

        # Check if expression ends with an operator (possibly with whitespace)
        for op in binary_operators:
            # Match operator at end of expression (with optional whitespace)
            pattern = rf'\s*{re.escape(op)}\s*$'
            if re.search(pattern, trimmed):
                # Special case: negative numbers like "-1" are valid
                if op == '-' and re.match(r'^\s*-\s*\d+\s*$', trimmed):
                    continue
                raise FHIRPathParseError(
                    f"Incomplete expression: expression ends with '{op}' operator"
                )

        # Check for division without right operand (e.g., "2 + 2 /")
        # This catches cases where the parser treats "/" as a binary operator
        # but there's no right operand
        if '/' in trimmed and not re.search(r'/\s*[^\s*/)]', trimmed):
            # Check if "/" is followed by something other than another operator
            parts = trimmed.split('/')
            if len(parts) > 1:
                # Get the part after the last "/"
                last_part = parts[-1].strip()
                if not last_part or last_part in ['+', '-', '*', '|', '&', '=', '!=', '<', '>', '<=', '>=', '~']:
                    raise FHIRPathParseError(
                        "Incomplete expression: missing right operand for division operator"
                    )

    def _validate_time_literal_timezones(self, raw_expression: str) -> None:
        """
        SP-103-001: Validate that Time literals do not have timezone suffixes.

        According to the FHIRPath specification, Time literals (@THH:MM:SS) cannot
        have timezone suffixes (Z or +/-HH:MM). If a time-like literal has a
        timezone suffix, it's considered invalid.

        Args:
            raw_expression: Original expression text

        Raises:
            FHIRPathParseError: When a Time literal has a timezone suffix
        """
        # Match time literals with timezone suffixes
        # Pattern: @T followed by time (HH:MM:SS or partial) and timezone (Z or +/-HH:MM)
        # Group 1: optional fractional seconds
        # Group 2: timezone suffix
        pattern = r'@T\d{2}(?::\d{2})?(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:\d{2})'

        match = re.search(pattern, raw_expression)
        if match:
            tz_suffix = match.group(1)  # Timezone is now group 1
            literal = match.group(0)

            raise FHIRPathParseError(
                f"Time literal '{literal}' is invalid: Time literals cannot have timezone suffixes. "
                f"Use DateTime literal format (e.g., @2015-02-04T{tz_suffix}) for time with timezone."
            )

    def _validate_temporal_comparison_compatibility(
        self,
        raw_expression: str,
        parsed_ast: EnhancedASTNode
    ) -> None:
        """
        SP-106-007: Validate that temporal comparisons are between compatible types.

        TIME literals cannot be compared with DATE or TIMESTAMP fields because they
        represent fundamentally different concepts:
        - TIME: Represents a time of day (HH:MM:SS) without date context
        - DATE: Represents a calendar date (YYYY-MM-DD) without time context
        - TIMESTAMP: Represents a specific point in time (date + time)

        Comparing TIME with DATE/TIMESTAMP would require an implicit cast that
        doesn't make semantic sense (what date should a TIME be cast to?).

        This method detects such incompatible comparisons and rejects them at
        parse time with a clear error message.

        Args:
            raw_expression: Original expression text
            parsed_ast: Parsed AST node

        Raises:
            FHIRPathParseError: When a TIME literal is compared with DATE/TIMESTAMP
        """
        # Check if expression contains a TIME literal pattern
        # TIME literals start with @T (e.g., @T12:14:15, @T12:14)
        time_literal_pattern = r'@T\d{2}(?::\d{2})?(?::\d{2}(\.\d+)?)?'
        has_time_literal = re.search(time_literal_pattern, raw_expression)

        if not has_time_literal:
            return  # No TIME literal, nothing to validate

        # Check if expression contains comparison operators
        comparison_operators = ['=', '!=', '<', '>', '<=', '>=', '~', '!~']
        has_comparison = any(
            f' {op} ' in raw_expression or
            raw_expression.endswith(f' {op}') or
            raw_expression.startswith(f'{op} ')
            for op in comparison_operators
        )

        if not has_comparison:
            return  # No comparison, nothing to validate

        # Walk the AST to find comparison nodes and check their operands
        for node in self._iterate_nodes(parsed_ast):
            # Check for various comparison/operation node types
            if node.node_type not in {"EqualityExpression", "InequalityExpression",
                                      "ComparisonExpression", "AdditiveExpression"}:
                continue

            # Check if this is a comparison operator
            operator = node.text.strip()
            if operator not in comparison_operators:
                continue

            # Check operands for incompatible temporal types
            if len(node.children) < 2:
                continue

            left_child = node.children[0]
            right_child = node.children[1]

            # Get temporal info for both operands
            # This checks both: 1) temporal literals, 2) field types from registry
            left_temporal = self._get_temporal_type_of_operand(left_child)
            right_temporal = self._get_temporal_type_of_operand(right_child)

            # Check if one is TIME and the other is DATE or DATETIME
            if left_temporal and right_temporal:
                if left_temporal == "time" and right_temporal in {"date", "datetime"}:
                    raise FHIRPathParseError(
                        f"Cannot compare TIME literal with {right_temporal.upper()} field/value. "
                        f"TIME and {right_temporal.upper()} are incompatible types for comparison. "
                        f"TIME represents time-of-day without date context, while {right_temporal.upper()} "
                        f"represents a calendar date or timestamp. Use compatible temporal types or "
                        f"extract components explicitly."
                    )
                elif right_temporal == "time" and left_temporal in {"date", "datetime"}:
                    raise FHIRPathParseError(
                        f"Cannot compare {left_temporal.upper()} field/value with TIME literal. "
                        f"{left_temporal.upper()} and TIME are incompatible types for comparison. "
                        f"{left_temporal.upper()} represents a calendar date or timestamp, while TIME "
                        f"represents time-of-day without date context. Use compatible temporal types or "
                        f"extract components explicitly."
                    )

    def _get_temporal_type_of_operand(self, node: EnhancedASTNode) -> Optional[str]:
        """
        Determine the temporal type of an operand (literal or field).

        This method checks:
        1. If the operand is a temporal literal (time, date, datetime)
        2. If the operand is a field reference, looks up its type from the type registry

        Args:
            node: AST node representing the operand

        Returns:
            "time", "date", "datetime", or None if not a temporal type
        """
        # First, check if it's a temporal literal
        temporal_literal_type = self._find_temporal_literal_in_subtree(node)
        if temporal_literal_type:
            return temporal_literal_type

        # Not a literal - check if it's a field reference with temporal type
        # Extract the path from the node text (e.g., "Patient.birthDate")
        path_text = node.text.strip() if hasattr(node, "text") and node.text else ""

        # Try to extract field path (remove trailing whitespace)
        if path_text and "." in path_text:
            # Split into resource type and field path
            # e.g., "Patient.birthDate" -> resource="Patient", field="birthDate"
            parts = path_text.split(".")
            if len(parts) >= 2:
                resource_type = parts[0]
                # Get the last field name (e.g., "birthDate" from "Patient.birthDate")
                field_name = parts[-1]

                # Look up the field type in the type registry
                try:
                    element_type = self._type_registry.get_element_type(resource_type, field_name)
                    if element_type:
                        # Map FHIR types to temporal categories
                        element_type_lower = element_type.lower()
                        if element_type_lower == "date":
                            return "date"
                        elif element_type_lower in {"datetime", "instant"}:
                            return "datetime"
                        elif element_type_lower == "time":
                            return "time"
                except Exception:
                    # Type lookup failed - continue with other checks
                    pass

        return None

    def _find_temporal_literal_in_subtree(self, node: EnhancedASTNode) -> Optional[str]:
        """
        Search a subtree for temporal literals and return the type.

        Args:
            node: Root node of the subtree to search

        Returns:
            "time", "date", "datetime", or None if no temporal literal found
        """
        # Check current node
        temporal_type = self._get_temporal_literal_type(node)
        if temporal_type:
            return temporal_type

        # Recursively check children
        for child in node.children:
            result = self._find_temporal_literal_in_subtree(child)
            if result:
                return result

        return None

    def _get_temporal_literal_type(self, node: EnhancedASTNode) -> Optional[str]:
        """
        Determine if a node represents a temporal literal and its type.

        Args:
            node: AST node to check

        Returns:
            "time", "date", "datetime", or None if not a temporal literal
        """
        # Get node text - check both direct text and child text for nested structures
        text = node.text.strip() if hasattr(node, "text") and node.text else ""

        if not text:
            return None

        # Check for temporal_info attribute (set by parser for temporal literals)
        temporal_info = getattr(node, "temporal_info", None)
        if temporal_info and "kind" in temporal_info:
            kind = temporal_info["kind"]
            if kind == "time":
                return "time"
            elif kind == "date":
                return "date"
            elif kind == "datetime":
                return "datetime"

        # Fallback: check text for temporal patterns
        # TIME literals: @THH:MM:SS or @THH:MM
        if text.startswith("@T"):
            return "time"
        # DATETIME literals: @YYYY-MM-DDTHH:MM:SS or contains T after @
        elif text.startswith("@") and "T" in text and not text.startswith("@T"):
            return "datetime"
        # DATE literals: @YYYY-MM-DD or @YYYY-MM or @YYYY
        elif text.startswith("@") and re.match(r'@\d{4}(-\d{2})?(-\d{2})?$', text):
            return "date"

        return None

    def _validate_unary_operators_on_literals(
        self,
        raw_expression: str,
        parsed_ast: EnhancedASTNode
    ) -> None:
        """
        SP-102-004: Validate that unary operators are not used on literals inappropriately.

        Detects invalid patterns like:
        - "-1.convertsToInteger()" (unary minus on literal with method call)

        Note: In FHIRPath, negative literals like "-1" are valid, but they should
        be treated as literal values, not as expressions with unary operators that
        can have methods chained to them.

        Args:
            raw_expression: Original expression text
            parsed_ast: Parsed AST node

        Raises:
            FHIRPathParseError: When unary operator is used inappropriately on literal
        """
        # Check for patterns like "-1.method()" or "+1.method()"
        # The pattern is: unary operator, number, then method call
        pattern = r'^\s*([+-])\s*(\d+(?:\.\d+)?)\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\('

        match = re.search(pattern, raw_expression)
        if match:
            operator = match.group(1)
            literal = match.group(2)
            method = match.group(3)

            raise FHIRPathParseError(
                f"Invalid expression: unary operator '{operator}' cannot be applied to "
                f"literal '{literal}' with method call '{method}()'. "
                f"Use '{operator}{literal}' as a literal value or wrap in parentheses."
            )


class FHIRPathExpressionWrapper:
    """
    Minimal wrapper interface for semantic validation compatibility.

    Allows the validator to access AST information without importing the
    heavier `FHIRPathExpression` implementation (avoids circular imports).
    """

    def __init__(
        self,
        ast: Optional[EnhancedASTNode],
        functions: Optional[List[str]] = None,
        path_components: Optional[List[str]] = None
    ):
        self.ast = ast
        self.functions = functions or []
        self.path_components = path_components or []
