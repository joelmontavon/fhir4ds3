"""FHIRPath AST-to-SQL Translator.

This module implements the core translator class that converts FHIRPath Abstract
Syntax Trees (AST) into SQL fragments using the visitor pattern. The translator
bridges the gap between the parser (PEP-002) and SQL execution, generating
database-specific SQL by calling dialect methods.

The ASTToSQLTranslator class is the foundation of PEP-003's translation layer,
implementing the visitor pattern to traverse AST nodes and accumulate SQL fragments
that will later be wrapped in CTEs by the CTE Builder (PEP-004).

Key Principles:
- **Visitor Pattern**: Uses visitor pattern to separate tree structure from operations
- **Dialect Integration**: Calls dialect methods for database-specific SQL syntax
- **Population-First**: Maintains population-scale capability in all translations
- **Context Management**: Tracks state through TranslationContext during traversal

Module: fhir4ds.fhirpath.sql.translator
PEP: PEP-003 - FHIRPath AST-to-SQL Translator
Created: 2025-09-30
Author: FHIR4DS Development Team
"""

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Any, Dict, List, Optional, Tuple

from ..ast.visitor import ASTVisitor
from ..ast.nodes import (
    FHIRPathASTNode, LiteralNode, IdentifierNode, FunctionCallNode,
    OperatorNode, ConditionalNode, AggregationNode, TypeOperationNode
)
from ..parser_core.ast_extensions import EnhancedASTNode
from ..parser_core.metadata_types import SQLDataType
from ..exceptions import (
    FHIRPathTranslationError,
    FHIRPathValidationError,
    FHIRPathEvaluationError,
    FHIRPathTypeError
)
from ..types.type_registry import TypeRegistry, get_type_registry
from ..types import (
    get_element_type_resolver,
    get_temporal_parser,
    ParsedTemporal
)
from ..types.fhir_types import resolve_polymorphic_property, is_polymorphic_property, resolve_polymorphic_field_for_type
from ..types.type_discriminators import get_type_discriminator
from ..types.structure_loader import StructureDefinitionLoader
from ..types.quantity_builder import build_quantity_json_string
from pathlib import Path
from .fragments import SQLFragment
from .context import TranslationContext, VariableBinding
from .cte import CTEManager
from ...dialects.base import DatabaseDialect


logger = logging.getLogger(__name__)


@dataclass
class NegatedQuantityMarker:
    """Marker for a negated quantity literal value.

    Used to track when a quantity has been negated (e.g., -5 'mm' becomes -5 with unit 'mm').
    This marker preserves both the numeric value and the unit string for proper type conversion.
    """
    value: Decimal
    unit: str
    is_quantity_literal: bool = True


class ASTToSQLTranslator(ASTVisitor[SQLFragment]):
    """Translates FHIRPath AST to SQL fragments using visitor pattern.

    Core component that converts each AST node type to database-specific SQL
    by calling dialect methods. Outputs sequence of SQL fragments representing
    logical operations, which future PEP-004 (CTE Builder) will wrap in CTEs.

    The translator implements the visitor pattern to traverse the AST tree and
    generate SQL for each node type. It maintains translation context to track
    the current table, path components, variable bindings, and CTE counter.

    Architecture Notes:
        - **Visitor Pattern**: Each node type has corresponding visit_* method
        - **Dialect Integration**: All database-specific SQL generated via dialect
        - **Context Management**: TranslationContext tracks state during traversal
        - **Fragment Accumulation**: Collects SQLFragments for later CTE generation

    Business Logic Location:
        - **In Translator**: Path resolution, context management, operation logic
        - **In Dialect**: ONLY database syntax differences (json_extract, etc.)
        - **NOT in Dialect**: Business logic, filtering, aggregation logic

    Attributes:
        dialect: DatabaseDialect instance for generating database-specific SQL
        context: TranslationContext tracking current state during traversal
        fragments: List of generated SQLFragments accumulated during translation
        resource_type: FHIR resource type being translated (e.g., "Patient")

    Example:
        Basic usage:
        >>> from fhir4ds.dialects import DuckDBDialect
        >>> dialect = DuckDBDialect()
        >>> translator = ASTToSQLTranslator(dialect, "Patient")
        >>> fragments = translator.translate(ast_root)
        >>> for fragment in fragments:
        ...     print(fragment.expression)

        With PostgreSQL:
        >>> from fhir4ds.dialects import PostgreSQLDialect
        >>> dialect = PostgreSQLDialect()
        >>> translator = ASTToSQLTranslator(dialect, "Observation")
        >>> fragments = translator.translate(observation_ast)

    See Also:
        - SQLFragment: Output data structure for SQL fragments
        - TranslationContext: Context state maintained during traversal
        - DatabaseDialect: Base class for database-specific SQL generation
        - PEP-003: Complete specification for AST-to-SQL translation
    """

    def __init__(self, dialect: DatabaseDialect, resource_type: str = "Patient"):
        """Initialize the AST-to-SQL translator.

        Args:
            dialect: Database dialect instance for SQL generation
            resource_type: FHIR resource type being translated (default: "Patient")

        Example:
            >>> from fhir4ds.dialects import DuckDBDialect
            >>> dialect = DuckDBDialect()
            >>> translator = ASTToSQLTranslator(dialect, "Patient")
        """
        super().__init__()
        self.dialect = dialect
        self.resource_type = resource_type
        self.context = TranslationContext(current_resource_type=resource_type)
        self.fragments: List[SQLFragment] = []
        self.type_registry: TypeRegistry = get_type_registry()
        self.element_type_resolver = get_element_type_resolver()
        self.temporal_parser = get_temporal_parser()
        self._internal_alias_counter = 0

        # Initialize CTE manager for SQL generation (SP-023-003)
        self._cte_manager = CTEManager(dialect)

        # Initialize StructureDefinition loader for array cardinality detection
        self._structure_loader: Optional[StructureDefinitionLoader] = None
        self._init_structure_loader()

        # Bind $this globally to the root resource context (without pushing new scope)
        # This enables expressions like: Patient.name.first().subsetOf($this.name)
        # where $this refers to the root Patient resource.
        # Lambda functions (like where()) will shadow this with local bindings.
        self.context.bind_variable("$this", VariableBinding(
            expression="resource",  # Points to root resource table
            source_table="resource"
        ))

        logger.info(f"Initialized ASTToSQLTranslator for resource type: {resource_type}")

    def _init_structure_loader(self) -> None:
        """Initialize FHIR R4 StructureDefinition loader if definitions are available."""
        try:
            # Find definitions path relative to types module
            types_module_path = Path(__file__).parent.parent / "types"
            definitions_path = types_module_path / "fhir_r4_definitions"

            if definitions_path.exists():
                self._structure_loader = StructureDefinitionLoader(definitions_path)
                self._structure_loader.load_all_definitions()
                logger.debug(f"Loaded FHIR R4 StructureDefinitions for array detection")
            else:
                logger.warning(f"FHIR R4 StructureDefinitions not found at {definitions_path}")
        except Exception as e:
            logger.warning(f"Failed to load StructureDefinitions: {e}")

    def _is_primitive_field_access(self, field_path: str, parent_type: str) -> bool:
        """Check if field access is for a FHIR primitive type.

        Args:
            field_path: Field path (e.g., 'birthDate', 'name.given')
            parent_type: Parent resource or element type (e.g., 'Patient', 'HumanName')

        Returns:
            True if field is a primitive type, False otherwise
        """
        # Use TypeRegistry to resolve field type
        field_type = self.type_registry.get_element_type(parent_type, field_path)
        if not field_type:
            return False

        # Check if the resolved type is a primitive type
        metadata = self.type_registry.get_type_metadata(field_type)
        if metadata and metadata.get('is_primitive', False):
            return True

        return False

    def _get_element_type_for_path(self, path_components: List[str]) -> Optional[str]:
        """Resolve element type for a navigation path.

        Walks through path components to determine the final element type,
        handling navigation through complex types and arrays.

        Args:
            path_components: List of path components (e.g., ['name'] or ['name', 'given'])

        Returns:
            Element type name (e.g., 'HumanName' for ['name'], 'string' for ['name', 'given'])
            or None if type cannot be resolved

        Example:
            >>> translator._get_element_type_for_path(['name'])
            'HumanName'
            >>> translator._get_element_type_for_path(['name', 'given'])
            'string'
            >>> translator._get_element_type_for_path(['address', 'city'])
            'string'
        """
        if not path_components:
            return None

        current_type = self.resource_type

        for component in path_components:
            # Resolve the element type for this component within the current type
            element_type = self.type_registry.get_element_type(current_type, component)
            if not element_type:
                logger.debug(
                    f"Could not resolve element type for '{component}' within '{current_type}'"
                )
                return None
            current_type = element_type

        return current_type

    def _get_sort_element_type(self, fhir_type: Optional[str]) -> Optional[str]:
        """Map FHIR data type to sort element type.

        Maps FHIR primitive types to the element_type values used by
        generate_array_sort for proper type-aware sorting.

        Args:
            fhir_type: FHIR type name (e.g., 'string', 'integer', 'dateTime')

        Returns:
            Element type string ('string', 'integer', 'decimal') or None
        """
        if not fhir_type:
            return None

        # Map FHIR types to sort element types
        # String-based types that sort lexicographically
        string_types = {
            'string', 'code', 'uri', 'url', 'canonical', 'id',
            'oid', 'uuid', 'idString', 'markdown', 'base64Binary',
            'boolean',  # Booleans sort as strings in FHIRPath
            'date', 'dateTime', 'time', 'instant',  # Temporal types sort as strings
        }

        # Integer types
        integer_types = {
            'integer', 'unsignedInt', 'positiveInt', 'integer64',
        }

        # Decimal types
        decimal_types = {
            'decimal', 'unsignedLong', 'negativeInt',
        }

        fhir_type_lower = fhir_type.lower()

        if fhir_type_lower in string_types:
            return 'string'
        elif fhir_type_lower in integer_types:
            return 'integer'
        elif fhir_type_lower in decimal_types:
            return 'decimal'

        return None

    def translate(self, ast_root: FHIRPathASTNode) -> List[SQLFragment]:
        """Translate FHIRPath AST to SQL fragments.

        Main entry point that coordinates translation. Visits the AST root node,
        accumulates fragments during traversal, and returns the complete list
        of SQL fragments for later CTE generation.

        For expression chains (e.g., Patient.name.where(use='official').first()),
        this method generates multiple fragments representing each operation in
        the chain. Each fragment depends on the previous one, enabling CTE-based
        SQL generation in future PEP-004.

        Args:
            ast_root: Root node of the FHIRPath AST to translate

        Returns:
            List of SQLFragments representing the translated expression chain

        Raises:
            NotImplementedError: If visitor method not yet implemented for node type
            ValueError: If AST is invalid or cannot be translated

        Example:
            Simple expression (single fragment):
            >>> translator = ASTToSQLTranslator(dialect, "Patient")
            >>> fragments = translator.translate(literal_node)
            >>> len(fragments)
            1

            Expression chain (multiple fragments):
            >>> fragments = translator.translate(chain_node)
            >>> len(fragments)
            3  # e.g., path + where + first
        """
        # Clear fragments from previous translation
        self.fragments.clear()

        # Reset context to initial state
        self.context.reset()

        # Handle FHIRPathExpression wrapper - extract the underlying AST
        if hasattr(ast_root, 'parse_result') and hasattr(ast_root, 'get_ast'):
            # This is a FHIRPathExpression wrapper, get the actual AST
            logger.debug(f"Starting translation of FHIRPathExpression: {ast_root.expression if hasattr(ast_root, 'expression') else 'unknown'}")
            actual_ast = ast_root.get_ast()
        else:
            actual_ast = ast_root
            logger.debug(f"Starting translation of AST: {actual_ast.node_type if hasattr(actual_ast, 'node_type') else type(actual_ast).__name__}")

        # Visit root node to start translation
        # The visit may accumulate multiple fragments for expression chains
        fragment = self.visit(actual_ast)

        # Accumulate the final fragment if it wasn't already added
        # (Some visitor methods add fragments during traversal)
        if fragment and (not self.fragments or self.fragments[-1] != fragment):
            self.fragments.append(fragment)

        logger.info(f"Translation complete: generated {len(self.fragments)} fragments")

        return self.fragments

    def translate_to_sql(self, ast_root: FHIRPathASTNode) -> str:
        """Translate FHIRPath AST directly to SQL.

        Main entry point that coordinates translation and generates complete SQL.
        This method combines AST traversal with CTE generation into a single operation,
        eliminating the need for external CTEManager usage.

        For expression chains (e.g., Patient.name.where(use='official').first()),
        this method generates a complete SQL query with appropriate CTEs for each
        operation in the chain.

        Args:
            ast_root: Root node of the FHIRPath AST to translate

        Returns:
            Complete SQL query string ready for execution

        Raises:
            NotImplementedError: If visitor method not yet implemented for node type
            ValueError: If AST is invalid or cannot be translated

        Example:
            Simple expression:
            >>> translator = ASTToSQLTranslator(dialect, "Patient")
            >>> sql = translator.translate_to_sql(literal_node)
            >>> print(sql)
            WITH
              cte_1 AS (...)
            SELECT * FROM cte_1;

            Expression chain:
            >>> sql = translator.translate_to_sql(chain_node)
            >>> # Returns SQL with multiple CTEs for path + where + first
        """
        # First, generate fragments using the existing translate method
        fragments = self.translate(ast_root)

        if not fragments:
            raise ValueError("Translation produced no SQL fragments")

        # Use the internal CTE manager to generate the final SQL
        sql = self._cte_manager.generate_sql(fragments)

        logger.info(f"Generated SQL from {len(fragments)} fragments")

        return sql

    def _resolve_canonical_type(self, type_name: Any, strict: bool = False) -> str:
        """Resolve provided type name to canonical FHIR type, enforcing validation.

        SP-110-003: Changed strict=False by default to allow unknown types during translation.
        Unknown types should fail at execution time (FHIRPath spec), not translation time.

        Args:
            type_name: Type name or alias to resolve
            strict: If True, raise translation error for unknown types.
                   If False, return the original type name for execution-time validation.

        Returns:
            Canonical type name if known, otherwise the original type name (if not strict)
        """
        raw_value = "" if type_name is None else str(type_name).strip()
        canonical = self.type_registry.get_canonical_type_name(raw_value)

        if canonical is None:
            if strict:
                display_name = raw_value or str(type_name)
                valid_types = ", ".join(self.type_registry.get_all_type_names())
                raise FHIRPathTranslationError(
                    f"Unknown FHIR type '{display_name}'. Valid types: {valid_types}"
                )
            # SP-110-003: Return original type name for unknown types
            # This allows translation to succeed, and execution will fail if the type is truly invalid
            return raw_value

        return canonical

    def _get_type_metadata(self, canonical_type: str) -> Dict[str, Any]:
        """Retrieve metadata for a canonical type name."""
        return self.type_registry.get_type_metadata(canonical_type) or {}

    def _is_primitive_type(self, canonical_type: str) -> bool:
        """Check whether the canonical type is a primitive FHIR type."""
        metadata = self._get_type_metadata(canonical_type)
        return bool(metadata.get("is_primitive", False))

    def _is_sql_literal_expression(self, expression: str) -> bool:
        """Check if the expression is a SQL literal value (not a JSON field).

        SP-022-003: When type-checking literal values like 1, 1.0, 'hello', TRUE,
        we need to use simpler type checks that don't involve json_type() which
        fails on non-JSON values in DuckDB.

        SP-104-002: Also recognize temporal literals (DATE, TIMESTAMP, TIME) for
        type checking in is() function calls.

        Args:
            expression: SQL expression string

        Returns:
            True if expression is a SQL literal (integer, decimal, string, boolean, temporal)
        """
        expr = expression.strip()

        # Boolean literals
        if expr.upper() in ('TRUE', 'FALSE'):
            return True

        # String literal: starts and ends with single quotes
        if expr.startswith("'") and expr.endswith("'"):
            return True

        # SP-104-002: Temporal literals (DATE, TIMESTAMP, TIME)
        # Pattern: DATE '...', TIMESTAMP '...', TIME '...'
        temporal_patterns = [
            r"^DATE\s+'",
            r"^TIMESTAMP\s+'",
            r"^TIME\s+'",
        ]
        for pattern in temporal_patterns:
            if re.match(pattern, expr, re.IGNORECASE):
                return True

        # Numeric literal: digits, possibly with decimal point and leading minus
        # Remove potential leading minus
        num_part = expr.lstrip('-')
        if num_part:
            # Check for integer
            if num_part.isdigit():
                return True
            # Check for decimal (digits.digits)
            if '.' in num_part:
                parts = num_part.split('.')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    return True

        return False

    def _generate_literal_type_check(self, expression: str, target_type: str, original_literal: Optional[str] = None, node: Optional[TypeOperationNode] = None) -> str:
        """Generate SQL type check for literal values.

        SP-022-003: This method generates simplified type checks for SQL literals
        that don't involve json_type() which fails on non-JSON values in DuckDB.

        For literals, we use typeof() directly without the JSON handling branches,
        since we know the value is a native SQL type (not JSON).

        SP-103-001: Time literals with timezone suffixes (Z or +/-HH:MM) should
        NOT pass .is(Time) checks because FHIRPath Time literals cannot have
        timezones. Such literals are treated as DateTime, not Time.

        Args:
            expression: SQL literal expression (e.g., "1", "1.0", "'hello'", "TRUE")
            target_type: FHIRPath type name to check (e.g., "Integer", "Decimal", "String")
            original_literal: Optional original FHIRPath literal text (e.g., "@T14:34:28Z")

        Returns:
            SQL expression that evaluates to boolean
        """
        normalized_type = (target_type or "").lower().replace("system.", "")

        # SP-103-001: Special handling for Time type check
        # Time literals with timezone suffixes should cause execution error
        if normalized_type == 'time' and original_literal:
            # Check if the original literal has a timezone suffix
            import re
            # Patterns for timezone: Z or +/-HH:MM
            has_tz = bool(re.search(r'[Z]|[+-]\d{2}:\d{2}$', original_literal))
            if has_tz:
                # Time literal with timezone is invalid - generate SQL that will fail
                # Cast an invalid time string to TIME type - this will cause a conversion error
                return "CAST('INVALID_TIME_WITH_TIMEZONE' AS TIME)"

        # Map FHIRPath types to SQL type checks
        # Use dialect's generate_scalar_type_check if available, otherwise construct directly
        if hasattr(self.dialect, 'generate_scalar_type_check'):
            return self.dialect.generate_scalar_type_check(expression, normalized_type)

        # Fallback: construct type check based on dialect name
        dialect_name = getattr(self.dialect, 'name', 'UNKNOWN').upper()

        if dialect_name == 'DUCKDB':
            type_map = {
                'integer': ['INTEGER', 'BIGINT', 'UBIGINT', 'SMALLINT', 'TINYINT'],
                'decimal': ['DECIMAL', 'DOUBLE', 'FLOAT', 'REAL', 'HUGEINT'],
                'string': ['VARCHAR', 'STRING', 'TEXT', 'CHAR'],
                'boolean': ['BOOLEAN'],
            }
        else:  # PostgreSQL and others
            type_map = {
                'integer': ['integer', 'bigint', 'smallint', 'int', 'int2', 'int4', 'int8'],
                'decimal': ['numeric', 'decimal', 'double precision', 'real', 'float8', 'float4'],
                'string': ['text', 'character varying', 'varchar', 'character', 'char', 'unknown'],
                'boolean': ['boolean', 'bool'],
            }

        # Handle temporal types (SP-104-002: Fix for temporal literal type checks)
        # Temporal literals (@2015, @2015-02-04T14:34, @T14:34:28) are converted to native
        # SQL types (DATE, TIMESTAMP, TIME), not strings. The type check must handle both:
        # 1. Native SQL temporal types (typeof() returns DATE, TIMESTAMP, TIME)
        # 2. String representations (for partial dates or edge cases)
        temporal_types = {
            'date': ('DATE', 'date'),
            'datetime': ('TIMESTAMP', 'timestamp'),
            'time': ('TIME', 'time'),
        }
        if normalized_type in temporal_types:
            duckdb_type, pg_type = temporal_types[normalized_type]
            if dialect_name == 'DUCKDB':
                # SP-104-002: Check typeof() first for native types, then fallback to regex
                # SP-106-001: Check T-suffix mapping for partial DateTimes
                # The ANTLR lexer strips 'T' from @YYYYT, making it look like @YYYY (a Date).
                # We use metadata to track the original form and restore correct type checking.
                # Key rules:
                # - @YYYY is Date (NOT DateTime)
                # - @YYYYT is DateTime (NOT Date)
                # - The .is() operator checks EXACT type, not type compatibility
                if original_literal and original_literal.startswith('@'):
                    type_check = self._check_temporal_literal_type(original_literal, normalized_type, node)
                    if type_check is not None:
                        return type_check

                # Default: Check typeof() for native SQL types
                return (
                    f"typeof({expression}) = '{duckdb_type}'"
                )
            else:  # PostgreSQL
                # SP-106-001: Check T-suffix mapping for partial DateTimes
                # Same logic as DuckDB - use shared helper method
                if original_literal and original_literal.startswith('@'):
                    type_check = self._check_temporal_literal_type(original_literal, normalized_type, node)
                    if type_check is not None:
                        return type_check

                return (
                    f"pg_typeof({expression})::text LIKE '{pg_type}%'"
                )

        sql_types = type_map.get(normalized_type, [])
        if not sql_types:
            # Unknown type - return false
            return "false"

        # Format type list for IN clause
        type_list = ", ".join(f"'{t}'" for t in sql_types)

        # Use appropriate typeof function based on dialect
        if dialect_name == 'DUCKDB':
            # SP-022-003: For Decimal types, DuckDB returns "DECIMAL(p,s)" not just "DECIMAL"
            # Use LIKE pattern matching for these parametric types
            if normalized_type == 'decimal':
                return (
                    f"(typeof({expression}) LIKE 'DECIMAL%' OR "
                    f"typeof({expression}) IN ('DOUBLE', 'FLOAT', 'REAL', 'HUGEINT'))"
                )
            return f"(typeof({expression}) IN ({type_list}))"
        else:  # PostgreSQL
            # PostgreSQL also returns parametric types like "numeric(10,2)"
            if normalized_type == 'decimal':
                return (
                    f"(pg_typeof({expression})::text LIKE 'numeric%' OR "
                    f"pg_typeof({expression})::text IN ('double precision', 'real', 'float8', 'float4'))"
                )
            return f"(pg_typeof({expression})::text IN ({type_list}))"

    def _is_complex_type(self, canonical_type: str) -> bool:
        """Check whether the canonical type is a complex FHIR type."""
        metadata = self._get_type_metadata(canonical_type)
        return bool(metadata.get("is_complex", False))

    def _is_resource_type(self, canonical_type: str) -> bool:
        """Check whether the canonical type represents a FHIR resource."""
        metadata = self._get_type_metadata(canonical_type)
        return bool(metadata.get("is_resource", False))

    def _check_temporal_literal_type(self, original_literal: str, normalized_type: str, node: Optional[TypeOperationNode] = None) -> Optional[str]:
        """Check if a temporal literal matches the target type.

        This implements SP-106-001: Correct type checking for Date vs DateTime.
        The ANTLR lexer strips 'T' from @YYYYT, making both @YYYY and @YYYYT
        appear as @YYYY in original_literal. We use metadata tracking to restore
        the original form and determine the correct type.

        Type Rules:
        - @YYYY (or @YYYY-MM-DD) is Date, NOT DateTime
        - @YYYYT (or @YYYY-MM-DDT...) is DateTime, NOT Date
        - The .is() operator checks EXACT type, not type compatibility

        Args:
            original_literal: The literal with @ prefix (e.g., '@2015', '@2015-02-03T')
            normalized_type: The target type to check against ('date', 'datetime', 'time')

        Returns:
            "CASE WHEN TRUE THEN TRUE ELSE FALSE END" if type matches
            "CASE WHEN FALSE THEN TRUE ELSE FALSE END" if type doesn't match
            None if cannot determine from literal (should fall back to typeof check)
        """
        # Step 1: Check datetime_t_mapping for T-suffix restoration
        # This tracks literals that were originally @YYYYT but lexer made them @YYYY
        datetime_t_mapping = None
        if node:
            try:
                # The node might be an adapter with an enhanced_node attribute
                root_node = None
                if hasattr(node, 'get_root'):
                    root_node = node.get_root()
                elif hasattr(node, 'enhanced_node') and hasattr(node.enhanced_node, 'get_root'):
                    root_node = node.enhanced_node.get_root()

                if root_node and hasattr(root_node, 'metadata') and root_node.metadata:
                    if hasattr(root_node.metadata, 'custom_attributes'):
                        datetime_t_mapping = root_node.metadata.custom_attributes.get('datetime_t_mapping')
            except Exception:
                pass  # If we can't get root, fall back to literal parsing

        # Step 2: If checking for DateTime and literal was originally @YYYYT, it's a match
        if normalized_type == 'datetime' and datetime_t_mapping and original_literal in datetime_t_mapping:
            return "CASE WHEN TRUE THEN TRUE ELSE FALSE END"

        # Step 3: Parse the temporal literal to determine its actual type
        parsed = self.temporal_parser.parse(original_literal)
        if parsed:
            parsed_type = parsed.temporal_type.lower()  # 'date', 'datetime', 'time', 'instant'

            # Exact type match (including instant -> datetime mapping)
            if parsed_type == normalized_type:
                return "CASE WHEN TRUE THEN TRUE ELSE FALSE END"

            # FHIRPath treats 'instant' as a subtype of 'datetime' for .is() checks
            if normalized_type == 'datetime' and parsed_type == 'instant':
                return "CASE WHEN TRUE THEN TRUE ELSE FALSE END"

            # Explicitly NOT treating Date as DateTime - they are distinct types
            # This is the key fix for SP-106-001
            if normalized_type == 'datetime' and parsed_type == 'date':
                return "CASE WHEN FALSE THEN TRUE ELSE FALSE END"

            if normalized_type == 'date' and parsed_type == 'datetime':
                return "CASE WHEN FALSE THEN TRUE ELSE FALSE END"

        # Step 4: Cannot determine from literal - let caller fall back to typeof check
        return None

    def _is_temporal_type_mismatch(self, left_metadata: Dict[str, Any], right_metadata: Dict[str, Any]) -> bool:
        """Check if two temporal literals have mismatched types or precision.

        SP-110-FIX-012: According to FHIRPath specification, comparisons between
        different temporal types (date, datetime, time) or different precisions
        should return empty collection {}.

        Type Mismatch Rules:
        - date vs datetime → mismatch (e.g., @2012-04-15 vs @2012-04-15T10:00:00)
        - date vs time → mismatch (e.g., @2012-04-15 vs @T10:30)
        - datetime vs time → mismatch (e.g., @2012-04-15T10:00:00 vs @T10:30)
        - Different precision within same type → mismatch (e.g., @T10:30 vs @T10:30:00)

        Valid Comparisons:
        - Same type, same precision (e.g., @2012-04-15 vs @2012-04-15, @T10:30:00 vs @T10:30:00)
        - datetime with timezone vs datetime without timezone (both are datetime)

        Args:
            left_metadata: Metadata from left fragment (contains literal_type, temporal_info)
            right_metadata: Metadata from right fragment (contains literal_type, temporal_info)

        Returns:
            True if types/precision mismatch (should return empty collection)
            False if types are compatible (comparison should proceed)
        """
        # Both operands must be temporal literals with temporal_info
        left_temporal = left_metadata.get("temporal_info")
        right_temporal = right_metadata.get("temporal_info")

        if not left_temporal or not right_temporal:
            # At least one is not a temporal literal - no type mismatch
            return False

        left_kind = left_temporal.get("kind", "")
        right_kind = right_temporal.get("kind", "")

        # Check for type mismatch (date vs datetime vs time)
        # These are three distinct types in FHIRPath and cannot be compared
        if left_kind != right_kind:
            return True

        # Same kind (date, datetime, or time) - check for precision mismatch
        left_precision = left_temporal.get("precision", "")
        right_precision = right_temporal.get("precision", "")

        # For time literals: different precision means mismatch
        # @T10:30 (minute precision) vs @T10:30:00 (second precision) → mismatch
        if left_kind == "time":
            return left_precision != right_precision

        # For datetime literals: different precision means mismatch
        # @2015T (year precision) vs @2015-02T (month precision) → mismatch
        # @2012-04-15T15:00:00Z (with timezone) vs @2012-04-15T10:00:00 (without) → mismatch
        if left_kind == "datetime":
            # Check if one has timezone and the other doesn't
            left_has_tz = "timezone" in left_temporal or left_temporal.get("original", "").endswith("Z")
            right_has_tz = "timezone" in right_temporal or right_temporal.get("original", "").endswith("Z")

            if left_has_tz != right_has_tz:
                return True

            # Check precision mismatch for datetime
            # Note: Fractions of seconds are considered same precision as seconds
            # for comparison purposes (they're both second-level precision)
            left_prec_normalized = "second" if left_precision in ("second", "fraction") else left_precision
            right_prec_normalized = "second" if right_precision in ("second", "fraction") else right_precision

            return left_prec_normalized != right_prec_normalized

        # For date literals: different precision means mismatch
        # @2015 (year precision) vs @2015-02 (month precision) → mismatch
        if left_kind == "date":
            return left_precision != right_precision

        # Unknown kind - no mismatch check
        return False

    def _is_temporal_info_mismatch(self, left_info: Dict[str, Any], right_info: Dict[str, Any]) -> bool:
        """Check if two temporal info dicts have mismatched types or precision.

        SP-110-FIX-012: Variant of _is_temporal_type_mismatch that works with
        temporal_info dicts extracted from AST nodes (before translation to fragments).

        Type Mismatch Rules:
        - date vs datetime → mismatch (e.g., @2012-04-15 vs @2012-04-15T10:00:00)
        - date vs time → mismatch (e.g., @2012-04-15 vs @T10:30)
        - datetime vs time → mismatch (e.g., @2012-04-15T10:00:00 vs @T10:30)
        - Different precision within same type → mismatch (e.g., @T10:30 vs @T10:30:00)
        - Different timezone presence → mismatch (e.g., @2012-04-15T10:00:00Z vs @2012-04-15T10:00:00)

        Valid Comparisons:
        - Same type, same precision (e.g., @2012-04-15 vs @2012-04-15, @T10:30:00 vs @T10:30:00)

        Note: Field references (is_field_reference=True) are exempt from strict type checking
        because database fields can be compared with any compatible temporal literal.

        Args:
            left_info: Temporal info from left operand
            right_info: Temporal info from right operand

        Returns:
            True if types/precision mismatch (should return empty collection)
            False if types are compatible or one is a field reference
        """
        # Field references are exempt from strict type checking
        # Database temporal fields can be compared with any compatible temporal literal
        if left_info.get("is_field_reference") or right_info.get("is_field_reference"):
            return False

        # Temporal functions are exempt from strict type checking
        # They can be compared with temporal literals of compatible types
        if left_info.get("is_temporal_function") or right_info.get("is_temporal_function"):
            return False

        left_kind = left_info.get("kind", "")
        right_kind = right_info.get("kind", "")

        # Check for type mismatch (date vs datetime vs time)
        if left_kind != right_kind:
            return True

        # Same kind - check for precision mismatch
        left_precision = left_info.get("precision", "")
        right_precision = right_info.get("precision", "")

        # For time literals: different precision means mismatch
        if left_kind == "time":
            return left_precision != right_precision

        # For datetime literals: check timezone and precision
        if left_kind == "datetime":
            # Check if one has timezone and the other doesn't
            left_has_tz = "timezone" in left_info or left_info.get("timezone_offset") is not None
            right_has_tz = "timezone" in right_info or right_info.get("timezone_offset") is not None

            if left_has_tz != right_has_tz:
                return True

            # Check precision mismatch for datetime
            left_prec_normalized = "second" if left_precision in ("second", "fraction") else left_precision
            right_prec_normalized = "second" if right_precision in ("second", "fraction") else right_precision

            return left_prec_normalized != right_prec_normalized

        # For date literals: different precision means mismatch
        if left_kind == "date":
            return left_precision != right_precision

        return False

    def _should_accumulate_as_separate_fragment(self, node: FHIRPathASTNode) -> bool:
        """Determine if a node should generate a separate fragment in the chain.

        Expression chains consist of operations that transform data through
        multiple steps. Each "significant" operation should generate its own
        SQL fragment that will become a CTE in the final query.

        Significant operations include:
        - Function calls (where, select, first, exists, etc.) - transform data
        - Type operations (as, is, ofType) - type filtering/conversion

        Non-significant operations (don't need separate fragments):
        - Literals - just values, no transformation
        - Identifiers - path references, combined with parent operation
        - Operators within conditions - part of parent operation's logic
        - Conditional expressions within larger expressions

        Args:
            node: AST node to check

        Returns:
            True if node should generate a separate fragment in the chain

        Example:
            For "Patient.name.where(use='official').first()":
            - Patient.name: identifier path (no separate fragment)
            - where(...): function call (YES - separate fragment)
            - first(): function call (YES - separate fragment)
            Result: 2 fragments in chain (where + first)
        """
        # Function calls represent operations that transform data
        # Each should be a separate step in the CTE chain
        if isinstance(node, FunctionCallNode):
            return True

        # Type operations perform type checking/conversion
        # These should also be separate steps
        if isinstance(node, TypeOperationNode):
            return True

        # All other nodes (literals, identifiers, operators, conditionals)
        # are typically part of a larger operation's logic
        return False

    def _traverse_expression_chain(self, node: FHIRPathASTNode, accumulate: bool = True) -> SQLFragment:
        """Traverse an expression chain and accumulate fragments for each operation.

        This method handles expression chains where multiple operations are applied
        sequentially (e.g., Patient.name.where(use='official').first()). It visits
        the node tree, identifies significant operations, and accumulates a fragment
        for each one.

        The method works recursively:
        1. Visit children first (depth-first traversal)
        2. Accumulate fragments for significant child operations
        3. Generate and return fragment for current node
        4. Optionally accumulate current fragment

        Args:
            node: Current AST node to process
            accumulate: If True, add this node's fragment to self.fragments list

        Returns:
            SQLFragment for the current node

        Example:
            For chain: Patient.name.where(use='official').first()
            1. Traverse to base path (Patient.name)
            2. Process where() - accumulate fragment
            3. Process first() - accumulate fragment
            Result: 2 fragments in self.fragments

        Implementation Note:
            This method orchestrates fragment accumulation. The actual SQL
            generation is delegated to specific visit_* methods. This maintains
            separation of concerns: orchestration here, SQL logic in visitors.
        """
        logger.debug(f"Traversing expression chain for node: {node.node_type}")

        # For function calls and other operations with children,
        # we need to process children first to build up the chain
        if hasattr(node, 'children') and node.children:
            logger.debug(f"Node has {len(node.children)} children")

            # Process each child that represents a chained operation
            # This builds fragments from left to right (base to operations)
            for i, child in enumerate(node.children):
                # Check if this child is a significant operation that should
                # generate its own fragment in the chain
                if self._should_accumulate_as_separate_fragment(child):
                    logger.debug(f"Child {i} ({child.node_type}) is significant operation")
                    # Recursively traverse and accumulate child's fragment
                    child_fragment = self._traverse_expression_chain(child, accumulate=True)
                else:
                    logger.debug(f"Child {i} ({child.node_type}) is part of parent operation")
                    # For non-significant children (literals, identifiers, etc.),
                    # just visit them without accumulating as separate fragments
                    # Their SQL will be incorporated into parent operation
                    child_fragment = self.visit(child)

        # Now generate fragment for current node using appropriate visitor
        current_fragment = self.visit(node)

        # Accumulate current fragment if requested
        if accumulate and current_fragment:
            logger.debug(f"Accumulating fragment for {node.node_type}")
            self.fragments.append(current_fragment)

        return current_fragment

    def _snapshot_context(self) -> dict:
        """Create a shallow snapshot of the current translation context.

        NOTE: Variable scopes are NOT snapshotted/restored here because they are
        managed by the _variable_scope() context manager. Snapshotting/restoring
        variable scopes would incorrectly clear bindings when visiting nested
        expressions like $this.length() inside a where() function.
        """
        return {
            "current_table": self.context.current_table,
            "parent_path": self.context.parent_path.copy(),
            "cte_counter": self.context.cte_counter,
            "current_element_column": self.context.current_element_column,
            "current_element_type": self.context.current_element_type,
        }

    def _restore_context(self, snapshot: dict) -> None:
        """Restore translation context from a snapshot.

        NOTE: Variable scopes are NOT restored here because they are managed
        by the _variable_scope() context manager. Restoring variable scopes
        would incorrectly clear bindings that are still active.
        """
        self.context.current_table = snapshot["current_table"]
        self.context.parent_path = snapshot["parent_path"].copy()
        self.context.cte_counter = snapshot["cte_counter"]
        self.context.current_element_column = snapshot.get("current_element_column")
        self.context.current_element_type = snapshot.get("current_element_type")

    @contextmanager
    def _variable_scope(
        self,
        bindings: Optional[Dict[str, VariableBinding]] = None,
        preserve_parent: bool = True
    ):
        """Context manager to push/pop variable scopes with optional bindings."""
        self.context.push_variable_scope(preserve=preserve_parent)
        try:
            if bindings:
                for name, binding in bindings.items():
                    self.context.bind_variable(name, binding)
            yield
        finally:
            self.context.pop_variable_scope()

    def _prefill_path_from_function(self, node: FunctionCallNode) -> None:
        """Ensure context path reflects the expression preceding the function."""
        path_expr = self._extract_path_before_function(node.text, node.function_name)
        if not path_expr:
            return

        first_char = path_expr[0]
        if not first_char.isalpha():
            # Skip literals, numeric prefixes, and special cases (e.g., quoted strings)
            return

        # Normalize and split path components
        components = [part for part in path_expr.split('.') if part]

        if components and components[0] == self.context.current_resource_type:
            components = components[1:]

        if not components:
            return

        # Only extend path if additional components are needed
        existing = self.context.parent_path
        common_length = 0
        while (common_length < len(existing) and
               common_length < len(components) and
               existing[common_length] == components[common_length]):
            common_length += 1

        for component in components[common_length:]:
            self.context.push_path(component)

    def _parse_function_target_ast(self, node: FunctionCallNode) -> Optional[FHIRPathASTNode]:
        """Parse the expression preceding a function call into a FHIRPath AST node."""
        path_expr = self._extract_path_before_function(node.text, node.function_name)
        if not path_expr:
            return None

        from ..parser import FHIRPathParser  # Local import to avoid circular dependency
        path_parser = FHIRPathParser()
        # SP-023-004B: Return EnhancedASTNode directly - accept() handles dispatch
        return path_parser.parse(path_expr).get_ast()

    def _resolve_function_target(
        self,
        node: FunctionCallNode,
    ) -> tuple[str, List[str], Optional[Any], dict, Optional[FHIRPathASTNode], Optional[List[str]]]:
        """Resolve the implicit value a function operates on.

        Returns:
            Tuple containing:
                - SQL expression for the target value
                - Collected dependencies
                - Literal value (if the target expression is a literal)
                - Context snapshot (caller should restore when done)
        """
        snapshot = self._snapshot_context()
        dependencies: List[str] = []
        literal_value: Optional[Any] = None
        target_path: Optional[List[str]] = None

        target_ast = self._parse_function_target_ast(node)

        # SP-110-002: Check if this is a literal conversion function that needs literal evaluation
        # For to* and convertsTo* functions, we need to use pending_literal_value instead of
        # pending_fragment_result because these functions evaluate literals at parse time.
        # Get function name from node if available
        needs_literal_value = False
        if hasattr(node, 'function_name'):
            func_name_lower = node.function_name.lower()
            # These functions need literal value evaluation for proper type conversion
            needs_literal_value = func_name_lower in (
                'tointeger', 'todecimal', 'tostring', 'toquantity', 'todate', 'todatetime', 'totime',
                'convertstointeger', 'convertstodecimal', 'convertstostring', 'convertstoquantity',
                'convertstodate', 'convertstodatetime', 'convertstotime', 'convertstoboolean'
            )

        # SP-110-002: For literal conversion functions, check pending_literal_value first
        if needs_literal_value and self.context.pending_literal_value is not None:
            literal_value, target_expression = self.context.pending_literal_value
            # Clear the pending value after consuming it
            self.context.pending_literal_value = None
            # Also clear pending_fragment_result if it exists (they're mutually exclusive)
            self.context.pending_fragment_result = None
        # SP-022-015: Check for pending fragment result from invocation chain
        # This handles expressions like (1|2|3).aggregate() where the union result
        # is a complete expression that should use the SQL result, not literal evaluation.
        # SP-100-002: pending_fragment_result is now a tuple (expression, parent_path, is_multi_item)
        elif self.context.pending_fragment_result is not None:
            target_expression, target_path, is_multi_item_collection = self.context.pending_fragment_result
            # If the pending fragment is from a multi-item collection, this is an error for iif()
            # We need to pass this information to the caller
            # Store this in a temporary attribute for _translate_iif to check
            self._pending_target_is_multi_item = is_multi_item_collection
            # Clear both pending values after consuming (fragment result takes priority)
            self.context.pending_fragment_result = None
            # SP-110-002: Don't clear pending_literal_value here - it might still be needed
            # Only clear it if we actually used pending_fragment_result and the function doesn't need literal value
            if not needs_literal_value:
                self.context.pending_literal_value = None
        # SP-022-009: Check for pending literal value from invocation chain
        # This handles expressions like 1.convertsToInteger() where the literal
        # was visited in visit_generic before this function call
        elif self.context.pending_literal_value is not None:
            literal_value, target_expression = self.context.pending_literal_value
            # Clear the pending value after consuming it
            self.context.pending_literal_value = None
        elif target_ast is None:
            # No explicit path provided; rely on current context
            json_path = self.context.get_json_path()
            if json_path and json_path != "$":
                target_expression = self.dialect.extract_json_field(
                    column=self.context.current_table,
                    path=json_path
                )
                # SP-101-002: Set target_path from current context when using context path
                # This allows first(), last(), etc. to work on the current path
                target_path = self.context.parent_path.copy()
            else:
                target_expression = self.context.current_table
        elif isinstance(target_ast, LiteralNode):
            # Literal expressions can be evaluated directly
            literal_value = target_ast.value
            literal_fragment = self.visit_literal(target_ast)
            target_expression = literal_fragment.expression
        else:
            # Translate the path expression to update context and get SQL
            fragment = self.visit(target_ast)
            target_expression = fragment.expression
            if hasattr(fragment, "dependencies"):
                dependencies.extend(fragment.dependencies)
            target_path = self.context.parent_path.copy()
            # SP-024-003: Extract literal value if visit_literal set pending_literal_value
            # This handles EnhancedASTNode -> LiteralNodeAdapter conversion where
            # the literal value is stored in pending_literal_value but needs to be
            # returned as literal_value for convertsTo* functions to evaluate at parse time
            if self.context.pending_literal_value is not None:
                literal_value, _ = self.context.pending_literal_value
                self.context.pending_literal_value = None

        return target_expression, dependencies, literal_value, snapshot, target_ast, target_path

    def _to_sql_literal(self, value: Optional[Any], value_type: str) -> str:
        """Convert a Python literal to a SQL literal string."""
        if value is None:
            return "NULL"
        if value_type == "boolean":
            return "TRUE" if bool(value) else "FALSE"
        if value_type == "integer":
            return str(int(value))
        if value_type == "string":
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"
        raise ValueError(f"Unsupported literal type for SQL conversion: {value_type}")

    def _evaluate_literal_to_boolean(self, value: Any) -> Optional[bool]:
        """Evaluate toBoolean() for literal values."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if value == 1:
                return True
            if value == 0:
                return False
            return None
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "t", "1"}:
                return True
            if normalized in {"false", "f", "0"}:
                return False
            return None
        return None

    def _evaluate_literal_to_integer(self, value: Any) -> Optional[int]:
        """Evaluate toInteger() for literal values."""
        if value is None:
            return None
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            sign = 1
            if stripped[0] in {"+", "-"}:
                if stripped[0] == "-":
                    sign = -1
                stripped = stripped[1:]
            if stripped.isdigit():
                return sign * int(stripped)
            return None
        return None

    def _evaluate_literal_to_string(self, value: Any) -> Optional[str]:
        """Evaluate toString() for literal values.

        SP-110-FIX-014: Handle QuantityLiteralMarker objects for quantity literals.
        Returns formatted quantity string like "1 'wk'" or "1 week".
        """
        if value is None:
            return None
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)

        # SP-110-FIX-014: Handle QuantityLiteralMarker from quantity literals
        # Check if this is a QuantityLiteralMarker (duck-typed check)
        if hasattr(value, 'value') and hasattr(value, 'unit') and hasattr(value, 'is_quantity_literal'):
            # Format quantity as "value 'unit'" matching FHIRPath spec
            # e.g., 1 'wk', 5 'mg', etc.
            quantity_value = value.value
            quantity_unit = value.unit
            return f"{quantity_value} '{quantity_unit}'"

        return str(value)

    def _evaluate_literal_to_decimal(self, value: Any) -> Optional[float]:
        """Evaluate toDecimal() for literal values."""
        if value is None:
            return None
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            try:
                return float(stripped)
            except ValueError:
                return None
        return None

    def _evaluate_literal_to_quantity(self, value: Any) -> Optional[str]:
        """Evaluate toQuantity() for literal values.

        Converts a value to a FHIR Quantity JSON string representation.
        Per FHIRPath spec:
        - Integer/Decimal: Creates Quantity with that value and unit '1' (default unit)
        - Boolean: Converts to 1.0 '1' (true) or 0.0 '1' (false)
        - String: Parses as number with optional unit (e.g., '1 day' -> value:1, unit:'day')
        - Quantity literal: Returns as-is (already in Quantity format)

        Returns JSON string: '{"value": "1.0", "unit": "day", "system": "http://unitsofmeasure.org", "code": "day"}'
        """
        if value is None:
            return None

        # SP-110-002: Check if it's already a QuantityLiteralMarker (from quantity literals like "5 'mg'")
        if hasattr(value, 'value') and hasattr(value, 'unit'):
            # It's already a quantity literal marker
            # SP-110-FIX-013: Normalize unit before building quantity JSON
            from ..types.quantity_builder import build_quantity_json_string
            normalized_unit = self._normalize_quantity_unit(value.unit) if value.unit else value.unit
            unit_to_use = normalized_unit if normalized_unit else (value.unit or '1')
            return build_quantity_json_string(value.value, unit_to_use)

        # SP-110-002: Check for NegatedQuantityMarker (from negated quantity literals like "-5 'mg'")
        if hasattr(value, 'is_negated_quantity') and value.is_negated_quantity:
            from ..types.quantity_builder import build_quantity_json_string
            # SP-110-FIX-013: Normalize unit before building quantity JSON
            normalized_unit = self._normalize_quantity_unit(value.unit) if value.unit else value.unit
            unit_to_use = normalized_unit if normalized_unit else (value.unit or '1')
            return build_quantity_json_string(value.value, unit_to_use)

        # Boolean -> Quantity: true -> 1.0 '1', false -> 0.0 '1'
        if isinstance(value, bool):
            from ..types.quantity_builder import build_quantity_json_string
            quantity_value = 1.0 if value else 0.0
            return build_quantity_json_string(quantity_value, '1')

        # Integer/Decimal -> Quantity: value with unit '1' (default unit in FHIR)
        if isinstance(value, (int, float)):
            from ..types.quantity_builder import build_quantity_json_string
            return build_quantity_json_string(float(value), '1')

        # String -> Quantity: Parse "number unit" format
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None

            # Try to parse as "number [unit]" format
            # Supports: '1', '1.0', '1 day', '4 days', '1 'wk'', etc.
            import re
            # Pattern: optional sign, digits with decimal, optional space, optional unit (quoted or unquoted)
            # The unit can be in single quotes, double quotes, or plain text
            quantity_pattern = r'^[\+\-]?(\d+\.?\d*|\.\d+)(?:\s+(\'[^\']+\'|\"[^\"]+\"|[a-zA-Z]+))?$'
            match = re.match(quantity_pattern, stripped)

            if match:
                number_str = match.group(1)
                unit_part = match.group(2)

                try:
                    quantity_value = float(number_str)

                    # Extract unit from quotes if present
                    if unit_part:
                        unit_part = unit_part.strip()
                        if unit_part.startswith("'") and unit_part.endswith("'"):
                            unit = unit_part[1:-1]
                        elif unit_part.startswith('"') and unit_part.endswith('"'):
                            unit = unit_part[1:-1]
                        else:
                            unit = unit_part
                        # SP-110-FIX-013: Normalize unit to canonical form
                        normalized_unit = self._normalize_quantity_unit(unit)
                        unit = normalized_unit if normalized_unit else unit
                    else:
                        # No unit specified, use '1' as default (FHIR convention)
                        unit = '1'

                    from ..types.quantity_builder import build_quantity_json_string
                    return build_quantity_json_string(quantity_value, unit)
                except ValueError:
                    return None

        return None

    def _extract_preserved_columns(self, *fragments: SQLFragment) -> List[str]:
        """Extract column names that need to be preserved through CTEs.

        SP-105: Analyzes fragments to find columns from UNNEST operations (ending with _item)
        that must be preserved in CTE SELECT clauses. This fixes "column not found" errors
        in combine() and exclude() operations.

        Args:
            *fragments: Variable number of SQLFragments to analyze

        Returns:
            List of column names to preserve (e.g., ['name_item', 'given_item'])
        """
        preserved = set()

        for frag in fragments:
            # Check source_table for _item columns
            if frag.source_table and frag.source_table.endswith('_item'):
                preserved.add(frag.source_table)

            # Check dependencies for _item columns
            for dep in frag.dependencies:
                if dep.endswith('_item'):
                    preserved.add(dep)

            # Check expression for direct column references
            # Pattern: matches column_name followed by punctuation or space
            # Specifically looks for _item suffix which indicates UNNEST results
            import re
            # Find all potential column references
            # This regex matches identifiers ending with _item
            column_refs = re.findall(r'\b(\w+_item)\b', frag.expression)
            preserved.update(column_refs)

        return list(preserved)

    def _evaluate_literal_to_date(self, value: Any) -> Optional[str]:
        """Evaluate toDate() for literal values.

        SP-103-006: Implement toDate() literal evaluation.
        Converts a valid date string to ISO 8601 date format.
        Only accepts date strings without time component.
        """
        if value is None:
            return None
        if isinstance(value, str):
            # Validate ISO 8601 date format (no time component)
            stripped = value.strip()
            # Pattern: YYYY, YYYY-MM, or YYYY-MM-DD (no 'T' or time allowed)
            if re.match(r'^\d{4}(-\d{2}(-\d{2})?)?$', stripped):
                # Ensure it doesn't have time component
                if 'T' not in stripped:
                    return stripped
            return None
        return None

    def _evaluate_literal_to_datetime(self, value: Any) -> Optional[str]:
        """Evaluate toDateTime() for literal values."""
        if value is None:
            return None
        if isinstance(value, str):
            # Validate ISO 8601 format
            stripped = value.strip()
            # Basic ISO 8601 pattern check
            if re.match(r'^\d{4}(-\d{2}(-\d{2}(T.*)?)?)?$', stripped):
                return stripped
            return None
        return None

    def _evaluate_literal_to_time(self, value: Any) -> Optional[str]:
        """Evaluate toTime() for literal values."""
        if value is None:
            return None
        if isinstance(value, str):
            # Validate ISO 8601 time format (HH:MM:SS or HH:MM)
            stripped = value.strip()
            if re.match(r'^\d{2}:\d{2}(:\d{2})?$', stripped):
                return stripped
            return None
        return None

    # Visitor methods for each node type
    # These are stubs that will be implemented in subsequent tasks

    def _is_empty_collection_literal(self, node) -> bool:
        """Check if node represents empty collection literal {}.

        SP-100-003: Empty collections are represented as string literals with
        text value '{}'. We need to detect them to apply proper semantics.

        Args:
            node: AST node to check

        Returns:
            True if node is an empty collection literal
        """
        # Check for empty collection by text or literal_type attribute
        # This handles both LiteralNode and LiteralNodeAdapter
        text = getattr(node, 'text', None)
        literal_type = getattr(node, 'literal_type', None)

        # Check by text value
        if text == '{}':
            return True

        # Check by literal_type (for LiteralNodeAdapter)
        if literal_type == 'empty_collection':
            return True

        # Check by value attribute
        value = getattr(node, 'value', None)
        if isinstance(value, str) and value == '{}':
            return True

        return False

    def _translate_empty_collection(self, context: str = "default") -> str:
        """Generate SQL for empty collection handling.

        SP-100-003: Empty collections have special semantics in FHIRPath:
        - Boolean context: Returns FALSE (empty collections are falsy)
        - Comparison context: Returns NULL (won't match anything)
        - Default: Returns empty JSON array

        Args:
            context: Translation context ('boolean', 'comparison', 'default')

        Returns:
            SQL expression for empty collection in given context
        """
        if context == "boolean":
            return "FALSE"
        elif context == "comparison":
            return "NULL"
        else:
            # Default empty collection representation as JSON array
            return "[]"

    def visit_literal(self, node: LiteralNode) -> SQLFragment:
        """Translate literal values to SQL.

        Converts literal values (strings, numbers, booleans, dates) to their SQL
        representations. Handles proper escaping and type conversion. For date and
        datetime literals, delegates to dialect methods for database-specific syntax.

        SP-100-003: Empty collections {} are handled specially - they are detected
        and translated based on context (boolean FALSE, comparison NULL, etc.)

        SQL Escaping Rules:
            - Strings: Single quotes escaped by doubling ('John''s' for "John's")
            - Booleans: TRUE/FALSE SQL keywords
            - Numbers: Direct string conversion
            - Dates/DateTimes: Dialect-specific methods for proper formatting

        Args:
            node: LiteralNode representing a literal value

        Returns:
            SQLFragment containing the SQL literal expression

        Raises:
            ValueError: If literal type is unknown or value is incompatible

        Example:
            String literal:
            >>> node = LiteralNode(value="John", literal_type="string")
            >>> fragment = translator.visit_literal(node)
            >>> fragment.expression
            "'John'"

            Boolean literal:
            >>> node = LiteralNode(value=True, literal_type="boolean")
            >>> fragment = translator.visit_literal(node)
            >>> fragment.expression
            "TRUE"

            Integer literal:
            >>> node = LiteralNode(value=42, literal_type="integer")
            >>> fragment = translator.visit_literal(node)
            >>> fragment.expression
            "42"

            Date literal:
            >>> node = LiteralNode(value="2024-01-01", literal_type="date")
            >>> fragment = translator.visit_literal(node)
            >>> fragment.expression
            "DATE '2024-01-01'"

            Empty collection (SP-100-003):
            >>> node = LiteralNode(value="{}", literal_type="string")
            >>> node.text = "{}"
            >>> fragment = translator.visit_literal(node)
            >>> fragment.metadata["is_empty_collection"]
            True
        """
        logger.debug(f"Translating literal: type={node.literal_type}, value={node.value}, text={node.text}")

        # SP-106-003: Check for quantity literals that weren't properly identified by parser
        # The parser may treat quantity literals (e.g., "10 'mg'") as string literals
        # We detect them here and handle them appropriately
        if node.literal_type == "string" and node.text:
            quantity_info = self._extract_quantity_from_text(node.text)
            if quantity_info:
                # This is actually a quantity literal - handle it as such
                return self._handle_quantity_literal(node, quantity_info)

        # SP-100-003: Check for empty collection literal before type-based handling
        if self._is_empty_collection_literal(node):
            logger.debug("Detected empty collection literal {}")

            # Store empty collection marker in context for functions
            self.context.pending_literal_value = ("{}[]", "[]")

            # Return SQL fragment marked as empty collection
            # The actual SQL expression depends on context (handled by consumers)
            # SP-104-002: Include source text for consistency
            empty_metadata = {
                "literal_type": "empty_collection",
                "is_literal": True,
                "is_empty_collection": True
            }
            if node.text:
                empty_metadata["source_text"] = node.text
                empty_metadata["text"] = node.text

            return SQLFragment(
                expression="NULL",  # Default - consumers will override
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                metadata=empty_metadata
            )

        # Handle different literal types
        if node.literal_type == "string":
            # Escape single quotes by doubling them (SQL standard)
            escaped_value = str(node.value).replace("'", "''")
            sql_expr = f"'{escaped_value}'"

        elif node.literal_type == "integer":
            # Direct string conversion for integers
            sql_expr = str(node.value)

        elif node.literal_type == "decimal":
            # SP-108-001: Use node.text instead of node.value to preserve precision
            # node.value is a Python float which loses precision for large decimals
            # node.text is the original string representation which preserves precision
            if node.text:
                # Validate that text is a valid decimal literal before using
                # This provides safety without breaking legitimate decimal values
                try:
                    # Basic validation - check if it can be parsed as a number
                    float(node.text)
                    sql_expr = node.text
                except (ValueError, TypeError):
                    # If text is invalid, fall back to value conversion
                    sql_expr = str(node.value)
            else:
                sql_expr = str(node.value)

        elif node.literal_type == "boolean":
            # SQL standard boolean literals
            sql_expr = "TRUE" if node.value else "FALSE"

        elif node.literal_type == "date":
            # Delegate to dialect for database-specific date literal syntax
            sql_expr = self.dialect.generate_date_literal(str(node.value))

        elif node.literal_type == "datetime":
            # Delegate to dialect for database-specific datetime literal syntax
            sql_expr = self.dialect.generate_datetime_literal(str(node.value))

        elif node.literal_type == "time":
            # Delegate to dialect for time literal syntax
            sql_expr = self.dialect.generate_time_literal(str(node.value))

        elif node.literal_type == "quantity":
            # SP-104-003: Handle quantity literals (duration literals like "7 days")
            # If temporal_info is present, generate INTERVAL SQL
            if hasattr(node, 'temporal_info') and node.temporal_info:
                temporal_info = node.temporal_info
                if temporal_info.get('kind') == 'duration':
                    # Generate INTERVAL SQL: INTERVAL '7 days'
                    value = temporal_info.get('value', str(node.value))
                    unit = temporal_info.get('unit', 'days')
                    sql_expr = f"INTERVAL '{value} {unit}'"
                else:
                    # Fall back to numeric value
                    sql_expr = str(node.value)
            else:
                # Fall back to numeric value
                sql_expr = str(node.value)

        elif node.literal_type == "empty_collection":
            # Empty collection literal {} - generate SQL for empty JSON array
            # SP-100-003: Empty collections are represented as empty JSON arrays
            # SP-100-003-fix: Removed inline comment that caused syntax errors
            # Use dialect-agnostic SQL for empty array
            sql_expr = "'[]'"

        else:
            # Unknown or unsupported literal type
            raise ValueError(
                f"Unknown or unsupported literal type: {node.literal_type} "
                f"for value: {node.value}"
            )

        logger.debug(f"Generated SQL expression: {sql_expr}")

        # SP-022-009: Store literal value in context for chained function calls
        # This enables expressions like 1.convertsToInteger() where the literal
        # needs to flow to the subsequent function call in the invocation chain
        self.context.pending_literal_value = (node.value, sql_expr)

        # Return SQL fragment with literal expression
        # Literals don't require unnesting and are not aggregate operations
        # Include literal_type in metadata for type-aware comparison casting
        # SP-104-002: Include source text and temporal_info for type checking
        fragment_metadata = {
            "literal_type": node.literal_type,
            "is_literal": True
        }
        # Include source text for temporal literals to support type checking
        if node.text:
            fragment_metadata["source_text"] = node.text
        if node.text:
            fragment_metadata["text"] = node.text
        # Include temporal_info if available (for date/time literals)
        if hasattr(node, 'temporal_info') and node.temporal_info:
            fragment_metadata["temporal_info"] = node.temporal_info
        # SP-110-001: Include quantity_value and quantity_unit for all quantity literals
        # This enables _generate_quantity_comparison() to detect and normalize quantities
        # (e.g., "7 days" vs "1 'wk'" -> both normalized to days for comparison)
        # Also supports regular Quantity literals like "185 '[lb_av]'"
        if node.literal_type == "quantity":
            # Check for temporal quantities (durations) first
            if (hasattr(node, 'temporal_info') and node.temporal_info and
                node.temporal_info.get('kind') == 'duration'):
                value = node.temporal_info.get('value', str(node.value))
                unit = node.temporal_info.get('unit', 'days')
                fragment_metadata["quantity_value"] = str(value)
                fragment_metadata["quantity_unit"] = self._normalize_quantity_unit(unit) if unit else unit
            # Then check for regular Quantity literals (value/unit in custom_attributes)
            elif hasattr(node, 'custom_attributes'):
                quantity_value = node.custom_attributes.get('quantity_value')
                quantity_unit = node.custom_attributes.get('quantity_unit')
                if quantity_value is not None:
                    fragment_metadata["quantity_value"] = quantity_value
                if quantity_unit is not None:
                    fragment_metadata["quantity_unit"] = quantity_unit

        return SQLFragment(
            expression=sql_expr,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            metadata=fragment_metadata
        )

    def _path_requires_unnest(self, path_components: List[str]) -> bool:
        """
        Check if a path requires UNNEST for array flattening.

        Uses FHIR StructureDefinition metadata to detect array-valued elements.

        Args:
            path_components: List of path components (e.g., ['name', 'given'])

        Returns:
            True if any component in the path is an array
        """
        if not self._structure_loader or not path_components:
            return False

        # Check each component in the path to see if it's an array
        # We need to track the current type as we navigate
        current_type = self.resource_type

        for i, component in enumerate(path_components):
            # Check if this specific component is an array in the current type
            if self._structure_loader.is_array_element(current_type, component):
                logger.debug(f"Path component '{component}' is an array in {current_type}")
                return True

            # Resolve the type of this element for the next iteration
            # E.g., Patient.name has type HumanName, so for next component we check HumanName
            try:
                resolved_type = self.element_type_resolver.resolve_element_type(
                    current_type, component
                )
                if resolved_type:
                    current_type = resolved_type
                    logger.debug(f"Resolved {current_type}.{component} -> type {resolved_type}")
            except Exception as e:
                # If we can't resolve the type, we can't check further
                logger.debug(f"Could not resolve type for {current_type}.{component}: {e}")
                break

        return False

    def _build_json_path(self, components: List[str], *, wildcard_last: bool = False) -> str:
        """Build a JSON path string from path components.

        Args:
            components: Ordered JSON path components.
            wildcard_last: When True, append ``[*]`` to the final component to
                reference all array elements at that position.
        """
        if not components:
            return "$"

        # Build path with [*] for array elements
        resource_type = self.context.current_resource_type
        path_parts = []

        for i, component in enumerate(components):
            # Build incremental path to check cardinality
            element_path = ".".join(components[:i+1])

            # Check if this element is an array
            is_array = False
            if resource_type:
                try:
                    is_array = self.type_registry.is_array_element(resource_type, element_path)
                except Exception:
                    # If we can't determine, assume not an array
                    pass

            # Add [*] for array elements (or last element if wildcard_last is True)
            if is_array or (wildcard_last and i == len(components) - 1):
                path_parts.append(component + "[*]")
            else:
                path_parts.append(component)

        return "$." + ".".join(path_parts)

    def _generate_result_alias(
        self,
        component: str,
        alias_counts: Dict[str, int],
    ) -> str:
        """Generate a stable alias name for an unnested array component."""
        sanitized = re.sub(r"[^0-9A-Za-z_]", "_", component or "item")
        if not sanitized:
            sanitized = "item"
        if sanitized[0].isdigit():
            sanitized = f"_{sanitized}"
        sanitized = sanitized.lower()

        count = alias_counts.get(sanitized, 0)
        alias_counts[sanitized] = count + 1

        if count == 0:
            return f"{sanitized}_item"
        return f"{sanitized}_item_{count + 1}"

    def _generate_array_metadata(
        self,
        *,
        array_column: str,
        result_alias: str,
        source_path: str,
        projection_expression: Optional[str] = None,
        unnest_level: int = 0,
    ) -> Dict[str, Any]:
        """Create metadata payload for UNNEST-aware SQL fragments."""
        metadata: Dict[str, Any] = {
            "array_column": array_column,
            "result_alias": result_alias,
            "source_path": source_path,
            "unnest_level": unnest_level,
        }
        if projection_expression:
            metadata["projection_expression"] = projection_expression
        return metadata

    def _generate_unnest_fragment(self, json_path: str) -> SQLFragment:
        """
        Generate SQL fragment metadata for array unnesting.

        Args:
            json_path: Full JSON path (from root) for the array extraction.

        Returns:
            SQLFragment configured for UNNEST handling.

        Notes:
            This helper is retained for backward compatibility with legacy code
            paths that expect a direct call when only the JSON path is known.
            Modern code paths should prefer _build_identifier_fragments().
        """
        array_column = self.dialect.extract_json_object(
            column=self.context.current_table,
            path=json_path,
        )

        metadata = self._generate_array_metadata(
            array_column=array_column,
            result_alias="item",
            source_path=json_path,
            unnest_level=len(self.context.parent_path),
        )

        fragment = SQLFragment(
            expression=array_column,
            source_table=self.context.current_table,
            requires_unnest=True,
            is_aggregate=False,
            metadata=metadata,
        )

        logger.debug(
            "Generated legacy UNNEST fragment for path %s with array_column %s",
            json_path,
            array_column,
        )

        return fragment

    def _translate_identifier_components(
        self,
        components: List[str],
        json_path: str,
    ) -> Optional[SQLFragment]:
        """Translate identifier components with array-aware semantics.

        Returns:
            SQLFragment representing the final path evaluation when arrays are
            present; otherwise None to signal scalar handling.
        """
        if not components:
            return None

        if not self._structure_loader:
            logger.debug(
                "StructureDefinition metadata unavailable; treating '%s' as scalar path",
                json_path,
            )
            return None

        alias_counts: Dict[str, int] = {}
        current_type = self.resource_type
        current_source = self.context.current_table
        processed_components: List[str] = []
        relative_components: List[str] = []
        arrays_detected = False
        last_fragment: Optional[SQLFragment] = None

        for component in components:
            processed_components.append(component)
            relative_components.append(component)

            is_array = False
            try:
                is_array = self._structure_loader.is_array_element(current_type, component)
            except Exception as exc:
                logger.debug(
                    "Array detection failed for %s.%s: %s",
                    current_type,
                    component,
                    exc,
                )

            source_path = self._build_json_path(processed_components)

            if is_array:
                arrays_detected = True

                array_json_path = self._build_json_path(relative_components, wildcard_last=True)
                array_column = self.dialect.extract_json_object(
                    column=current_source,
                    path=array_json_path,
                )

                result_alias = self._generate_result_alias(component, alias_counts)
                metadata = self._generate_array_metadata(
                    array_column=array_column,
                    result_alias=result_alias,
                    source_path=source_path,
                    projection_expression=f"{result_alias}.unnest",
                    unnest_level=len(processed_components),
                )

                # SP-110-SORT: Add element_type for array fragments
                # Determine the type of elements in this array for type-aware sorting
                try:
                    # Resolve the type of elements in this array using type_registry
                    # (element_type_resolver doesn't work for all cases)
                    element_fhir_type = self.type_registry.get_element_type(
                        current_type,
                        component
                    )
                    if element_fhir_type:
                        # For primitive arrays (e.g., HumanName.given is string[]),
                        # set element_type to the primitive type
                        element_sort_type = self._get_sort_element_type(element_fhir_type)
                        if element_sort_type:
                            metadata["element_type"] = element_sort_type
                            logger.debug(
                                f"SP-110-SORT: Array '{component}' in '{current_type}' has elements "
                                f"of type '{element_fhir_type}', element_type '{element_sort_type}'"
                            )
                except Exception as exc:
                    logger.debug(
                        f"SP-110-SORT: Could not resolve element type for array '{component}': {exc}"
                    )

                fragment = SQLFragment(
                    expression=array_column,
                    source_table=self.context.current_table,
                    requires_unnest=True,
                    is_aggregate=False,
                    metadata=metadata,
                )

                self.fragments.append(fragment)
                last_fragment = fragment

                # SP-101-002: Register the column alias for CTE output tracking
                # The CTE will output the column as 'result_alias' (e.g., "name_item")
                # but subsequent operations may reference it as "result" or by logical name
                self.context.register_column_alias(result_alias, result_alias)

                current_source = result_alias
                relative_components = []

                logger.debug(
                    "SP-101-002: Detected array path '%s'; generated fragment with alias '%s'",
                    source_path,
                    result_alias,
                )

            try:
                resolved_type = self.element_type_resolver.resolve_element_type(
                    current_type,
                    component,
                )
                if resolved_type:
                    current_type = resolved_type
            except Exception as exc:
                logger.debug(
                    "Failed to resolve element type for %s.%s: %s",
                    current_type,
                    component,
                    exc,
                )

        if not arrays_detected:
            return None

        if relative_components:
            relative_path = self._build_json_path(relative_components)

            # SP-021-001: Check if final component is a primitive type
            # For array navigation like "name.given", we need to extract primitive values
            # not objects. Determine the parent type for the final component and check
            # if it's a primitive.
            is_primitive = False
            if len(processed_components) >= 1:
                # Get the parent type for the final component
                # Example: for "name.given", parent_components is ["name"], parent type is "HumanName"
                # Then check if "given" within "HumanName" is a primitive
                parent_components = processed_components[:-1] if len(processed_components) > 1 else []
                final_component = processed_components[-1]

                if parent_components:
                    # Resolve parent type through the path
                    parent_type = self._get_element_type_for_path(parent_components)
                    if parent_type:
                        # Check if the final component is a primitive within the parent type
                        is_primitive = self._is_primitive_field_access(final_component, parent_type)
                        logger.debug(
                            f"Array context: checking if '{final_component}' in '{parent_type}' is primitive: {is_primitive}"
                        )
                else:
                    # No parent components means we're at resource level
                    # Check if final component is primitive within the resource type
                    is_primitive = self._is_primitive_field_access(final_component, self.resource_type)
                    logger.debug(
                        f"Array context: checking if '{final_component}' in '{self.resource_type}' is primitive: {is_primitive}"
                    )

            # Use extract_primitive_value for primitives, extract_json_field for complex types
            if is_primitive:
                sql_expr = self.dialect.extract_primitive_value(
                    column=current_source,
                    path=relative_path,
                )
                logger.debug(
                    f"Extracting primitive value in array context for '{self._build_json_path(processed_components)}': {sql_expr}"
                )
            else:
                sql_expr = self.dialect.extract_json_field(
                    column=current_source,
                    path=relative_path,
                )

            # SP-110-SORT: Determine element type for type-aware sorting
            # When extracting a primitive field from an UNNEST result, we need to set
            # element_type so sort() knows what type to cast to
            sort_element_type = None
            if is_primitive:
                parent_components = processed_components[:-1] if len(processed_components) > 1 else []
                final_component = processed_components[-1]

                if parent_components:
                    parent_type = self._get_element_type_for_path(parent_components)
                    if parent_type:
                        try:
                            fhir_type = self.type_registry.get_element_type(parent_type, final_component)
                            if fhir_type:
                                sort_element_type = self._get_sort_element_type(fhir_type)
                                logger.debug(
                                    f"SP-110-SORT: Array context field '{final_component}' in '{parent_type}' "
                                    f"has FHIR type '{fhir_type}', element_type '{sort_element_type}'"
                                )
                        except Exception as e:
                            logger.debug(f"SP-110-SORT: Could not resolve element type: {e}")

            metadata = {"source_path": self._build_json_path(processed_components)}
            if sort_element_type:
                metadata["element_type"] = sort_element_type

            final_fragment = SQLFragment(
                expression=sql_expr,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                metadata=metadata,
            )

            self.fragments.append(final_fragment)

            logger.debug(
                "Generated trailing scalar fragment for path '%s' using source '%s'",
                self._build_json_path(processed_components),
                current_source,
            )

            return final_fragment

        return last_fragment

    def visit_identifier(self, node: IdentifierNode) -> SQLFragment:
        """Translate identifier/path navigation to SQL.

        Converts FHIRPath identifiers and path expressions to JSON extraction
        SQL. Builds JSON paths from context and generates dialect-specific
        extraction calls.

        This method handles two types of identifiers:
        1. Root resource references (e.g., "Patient", "Observation"): These refer
           to the resource table itself and don't require path navigation.
        2. Field identifiers (e.g., "name", "birthDate"): These are translated
           to JSON extraction operations using the current path context.

        Path Management:
            - The context.parent_path stack tracks the current position in the
              JSON structure as we traverse the AST.
            - This method adds the current identifier to the path for JSON extraction.
            - The path is built as "$.component1.component2.identifier" format.

        Args:
            node: IdentifierNode representing an identifier or path component

        Returns:
            SQLFragment containing the JSON extraction SQL

        Example:
            Root resource reference:
            >>> node = IdentifierNode(identifier="Patient")
            >>> fragment = translator.visit_identifier(node)
            >>> # Returns fragment referencing the resource table directly

            Simple field access:
            >>> # Context: parent_path = []
            >>> node = IdentifierNode(identifier="name")
            >>> fragment = translator.visit_identifier(node)
            >>> fragment.expression
            "json_extract_string(resource, '$.name')"  # DuckDB syntax

            Nested field access:
            >>> # Context: parent_path = ["name"]
            >>> node = IdentifierNode(identifier="family")
            >>> fragment = translator.visit_identifier(node)
            >>> fragment.expression
            "json_extract_string(resource, '$.name.family')"  # DuckDB syntax
        """
        identifier_value = node.identifier or node.text
        logger.debug(f"Translating identifier: {identifier_value}")
        logger.debug(f"SP-103-005: visit_identifier: identifier_value='{identifier_value}', parent_path={self.context.parent_path}")

        # SP-110 FIX: Special handling for identifier navigation after repeat() results
        # When the previous fragment is a repeat() result, we need to UNNEST the result array
        # and then extract the property from each element. The result column contains a JSON array.

        # Check ALL fragments for a repeat_result, not just the last one
        # This handles cases where fragments might be in a different order
        repeat_result_fragment = None
        for i in range(len(self.fragments) - 1, -1, -1):  # Search from the end
            if hasattr(self.fragments[i], 'metadata') and self.fragments[i].metadata:
                if self.fragments[i].metadata.get('repeat_result'):
                    repeat_result_fragment = self.fragments[i]
                    break

        if repeat_result_fragment:
            result_column = repeat_result_fragment.metadata.get('result_column', 'result')
            # Use the source_table from the repeat result fragment
            repeat_source_table = repeat_result_fragment.source_table
            logger.info(
                f"SP-110: Detected identifier navigation after repeat() result. "
                f"Source table: {repeat_source_table}, Result column: {result_column}, Property: {identifier_value}"
            )
            # Clear the parent path since we're starting fresh from the repeat() result
            self.context.parent_path = []
            # Build UNNEST operation for the result array
            # The result column contains a JSON array, we need to UNNEST it and extract the property
            array_column = self.dialect.extract_json_object(
                column=f"{repeat_source_table}.{result_column}",
                path=f"$.{identifier_value}"
            )
            logger.info(f"SP-110: Created array_column={array_column}")
            # Return a fragment that extracts the property from the UNNESTed array
            fragment = SQLFragment(
                expression=array_column,
                source_table=repeat_source_table,
                requires_unnest=True,  # This requires UNNEST to access array elements
                is_aggregate=False,
                metadata={
                    "from_repeat_result": True,
                    "array_column": array_column,
                    "result_alias": "item"  # Explicitly set result_alias for UNNEST wrapper
                }
            )
            logger.info(f"SP-110: Returning fragment with metadata array_column={fragment.metadata.get('array_column')}")
            return fragment
            if self.fragments:
                logger.debug(
                    f"SP-110-DEBUG: Special handling NOT triggered. "
                    f"Fragments count: {len(self.fragments)}, "
                    f"Searched all fragments, no repeat_result found"
                )
                for i, frag in enumerate(self.fragments):
                    meta_keys = list(frag.metadata.keys()) if hasattr(frag, 'metadata') and frag.metadata else 'None'
                    has_repeat = frag.metadata.get('repeat_result') if hasattr(frag, 'metadata') and frag.metadata else 'N/A'
                    logger.debug(f"SP-110-DEBUG: Fragment {i}: metadata keys={meta_keys}, has repeat_result={has_repeat}")

        # SP-103-005: Skip empty identifiers and structural nodes (parentheses, etc.)
        # These are part of the AST structure but not actual path components
        if not identifier_value or identifier_value in ['( )', 'ofType', 'as', 'is']:
            logger.debug(f"SP-103-005: Skipping structural identifier: '{identifier_value}'")
            # Return a placeholder that doesn't modify the path
            return SQLFragment(
                expression=self.context.current_table,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False
            )

        # SP-110-001: Handle FHIRPath terminology system prefixes (e.g., %sct, %loinc, %ucum)
        # These prefixes expand to their corresponding terminology system URLs
        if identifier_value.startswith('%'):
            system_name = identifier_value[1:].strip()  # Remove the % prefix
            # Map common terminology system prefixes to their URLs
            terminology_urls = {
                'sct': 'http://snomed.info/sct',
                'snomed': 'http://snomed.info/sct',
                'loinc': 'http://loinc.org',
                'ucum': 'http://unitsofmeasure.org',
            }
            # Check for known system
            if system_name in terminology_urls:
                url = terminology_urls[system_name]
                logger.debug(f"Terminology prefix {identifier_value} -> {url}")
                return SQLFragment(
                    expression=f"'{url}'",
                    source_table=self.context.current_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    metadata={"literal_type": "string", "is_literal": True}
                )
            # For unknown prefixes, keep them as-is (they might be custom systems)
            # The identifier_value itself (e.g., %sct) will be used as a literal
            return SQLFragment(
                expression=f"'{identifier_value}'",
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                metadata={"literal_type": "string", "is_literal": True}
            )

        # Split compound identifiers (e.g., "Patient.name.family", "$this.given") into components
        components = [part.strip().strip('`') for part in identifier_value.split('.') if part.strip()]

        # Handle FHIRPath variables with member access (e.g., $this.given, $index)
        # Check if the FIRST component is a variable (starts with $)
        if components and components[0].startswith("$"):
            variable_name = components[0]
            binding = self.context.get_variable(variable_name)
            if binding is None:
                raise ValueError(f"Unbound FHIRPath variable referenced: {variable_name}")

            # If this is just a variable reference (no member access), return the binding directly
            if len(components) == 1:
                dependencies = binding.dependencies.copy()
                source_table = binding.source_table or self.context.current_table

                # SP-102-001: When $this is referenced in a lambda scope and will be used
                # as the base for a function call (e.g., $this.length()), we need to ensure
                # the expression is properly formatted for SQL consumption.
                # For variable bindings that reference column names (not expressions),
                # we need to ensure they're treated as column references, not nested expressions.
                expression = binding.expression

                # Check if the expression is a simple column reference (no parentheses, no function calls)
                # If it is, it can be used directly. Otherwise, wrap it as a subquery alias.
                if expression and not any(c in expression for c in '()'):
                    # Simple column reference - use directly
                    pass
                elif expression and '(' in expression:
                    # Complex expression - wrap as subquery for safety
                    # This shouldn't happen with $this bindings, but handle it defensively
                    pass

                return SQLFragment(
                    expression=expression,
                    source_table=source_table,
                    requires_unnest=binding.requires_unnest,
                    is_aggregate=binding.is_aggregate,
                    dependencies=dependencies,
                    metadata={"is_variable_reference": True}  # Mark as variable reference
                )

            # Variable with member access (e.g., $this.given)
            # Start with the variable's expression as the base
            current_expression = binding.expression
            current_source = binding.source_table or self.context.current_table
            member_components = components[1:]  # Everything after the variable

            # Build JSON path for member access: $.member1.member2...
            json_path = "$." + ".".join(member_components)

            # Generate JSON extraction for the member access
            result_expression = self.dialect.extract_json_field(
                column=current_expression,
                path=json_path
            )

            logger.debug(
                f"Variable member access: {variable_name}.{'.'.join(member_components)} "
                f"→ {result_expression}"
            )

            return SQLFragment(
                expression=result_expression,
                source_table=current_source,
                requires_unnest=False,  # Member access on variable doesn't require unnest
                is_aggregate=binding.is_aggregate,
                dependencies=binding.dependencies.copy()
            )

        # SP-110: Handle special Type object properties (.namespace, .name)
        # These are used after type() function calls: e.g., 1.type().namespace
        if self.fragments and self.fragments[-1].metadata.get('function') == 'type':
            # Check if this is accessing .namespace or .name on a Type object
            if identifier_value in ('namespace', 'name'):
                # Extract the field from the JSON Type object returned by type()
                # Type object format: {"namespace": "System", "name": "Integer"}
                type_object_expr = self.fragments[-1].expression
                field_extraction = self.dialect.extract_json_field(
                    column=f"({type_object_expr})",
                    path=f"$.{identifier_value}"
                )
                return SQLFragment(
                    expression=field_extraction,
                    source_table=self.context.current_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=self.fragments[-1].dependencies.copy(),
                    metadata={"function": "type", "property": identifier_value}
                )

        # Check if this is a root resource reference (e.g., "Patient", "Observation")
        # Root resource references don't require JSON extraction; they refer to the
        # resource table itself
        if identifier_value == self.context.current_resource_type:
            logger.debug(f"Identifier is root resource type: {identifier_value}")
            # Return a fragment that references the resource table
            # This allows expressions like "Patient.name" where "Patient" is the root
            return SQLFragment(
                expression=self.context.current_table,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False
            )

        # SP-022-004: Handle field access after first()/last()/skip()/take() on UNNEST
        # When current_element_column is set, we're accessing a field on an extracted
        # element (e.g., .family after Patient.name.first()). In this case, extract
        # from the element column, not from the original resource JSON.
        # SP-101-002: Resolve the column name through the alias registry to handle
        # CTE column renames (e.g., "result" -> "name_item")
        if self.context.current_element_column:
            # Build JSON path for field access on the element
            # The element is already a JSON object, so we just need $.field
            field_name = ".".join(components)
            element_path = "$." + field_name

            # SP-101-002: Resolve the column alias to get the actual column name
            actual_element_column = self.context.resolve_column_alias(
                self.context.current_element_column
            )

            logger.debug(
                f"SP-101-002: Extracting from element column '{self.context.current_element_column}' "
                f"(resolved to '{actual_element_column}'): {element_path}"
            )

            # Use the element type if available, otherwise fall back to current resource type
            element_type = self.context.current_element_type or self.context.current_resource_type

            # SP-022-008: Check if the accessed field is an array type
            # Array fields need UNNEST, not just json_extract
            is_array = False
            if element_type:
                try:
                    is_array = self.type_registry.is_array_element(element_type, field_name)
                except Exception as e:
                    logger.debug(f"Array detection failed for {element_type}.{field_name}: {e}")

            if is_array:
                # SP-022-008: Array field after subset - generate UNNEST fragment
                # Build array extraction path with [*] for unnesting
                array_path = element_path + "[*]"

                # SP-102-002: Use logical column name instead of resolved alias for element columns
                # When extracting from an element column (e.g., after skip()), we need to use
                # the logical column name (e.g., "result") rather than the actual column name
                # from the previous CTE (e.g., "name_item"), because the CTE builder will
                # handle the column reference correctly.
                # Only resolve the alias if it's not coming from an element column.
                if self.context.current_element_column:
                    # Use the logical element column name directly
                    column_for_extraction = self.context.current_element_column
                    logger.debug(
                        f"SP-102-002: Using logical element column '{column_for_extraction}' "
                        f"instead of resolving alias '{actual_element_column}'"
                    )
                else:
                    # No element column, use the resolved alias
                    column_for_extraction = actual_element_column

                array_column = self.dialect.extract_json_object(
                    column=column_for_extraction,
                    path=array_path
                )

                # Generate unique result alias for the unnested items
                alias_counts: Dict[str, int] = {}
                result_alias = self._generate_result_alias(components[-1], alias_counts)

                # Build source path for metadata
                source_path = "$." + field_name

                metadata = self._generate_array_metadata(
                    array_column=array_column,
                    result_alias=result_alias,
                    source_path=source_path,
                    projection_expression=f"{result_alias}.unnest",
                    unnest_level=1,
                )
                metadata["from_element_column"] = True

                fragment = SQLFragment(
                    expression=array_column,
                    source_table=self.context.current_table,
                    requires_unnest=True,
                    is_aggregate=False,
                    metadata=metadata,
                )

                logger.debug(
                    f"SP-022-008: Generated UNNEST fragment for array field '{field_name}' "
                    f"in element type '{element_type}' with alias '{result_alias}'"
                )

                # Clear the element column since we've used it
                self.context.current_element_column = None
                self.context.current_element_type = None

                # Update path for potential subsequent access
                for component in components:
                    self.context.push_path(component)

                self.fragments.append(fragment)
                return fragment

            # Check if this field is a primitive type
            is_primitive = self._is_primitive_field_access(field_name, element_type)

            # SP-110-SORT: Determine element type for type-aware sorting
            # When accessing a field from an element column (e.g., after [0] or first()),
            # we need to set element_type metadata so sort() knows what type to cast to
            sort_element_type = None
            if is_primitive:
                try:
                    fhir_type = self.type_registry.get_element_type(element_type, field_name)
                    if fhir_type:
                        sort_element_type = self._get_sort_element_type(fhir_type)
                        logger.debug(
                            f"SP-110-SORT: Element column field '{field_name}' in '{element_type}' "
                            f"has FHIR type '{fhir_type}', element_type '{sort_element_type}'"
                        )
                except Exception as e:
                    logger.debug(f"SP-110-SORT: Could not resolve element type for '{field_name}': {e}")

            # Generate JSON extraction from the element column
            if is_primitive:
                sql_expr = self.dialect.extract_primitive_value(
                    column=actual_element_column,
                    path=element_path
                )
            else:
                sql_expr = self.dialect.extract_json_field(
                    column=actual_element_column,
                    path=element_path
                )

            # Clear the element column since we've used it
            # (subsequent field access will build on this result)
            self.context.current_element_column = None
            self.context.current_element_type = None

            # Update path for potential subsequent access
            for component in components:
                self.context.push_path(component)

            # SP-110-SORT: Include element_type in metadata for sort()
            metadata = {"from_element_column": True}
            if sort_element_type:
                metadata["element_type"] = sort_element_type

            fragment = SQLFragment(
                expression=sql_expr,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                metadata=metadata
            )
            self.fragments.append(fragment)
            return fragment

        # Build JSON path from current context and identifier
        # The path format is "$.component1.component2.identifier"
        # For example: "$.name.family" or "$.birthDate"

        # Merge polymorphic base + type suffix produced by parenthesized type expressions
        merged_components: List[str] = []
        for component in components:
            if merged_components:
                base_component = merged_components[-1]
                variants = resolve_polymorphic_property(base_component) or []
                if variants:
                    candidate = f"{base_component}{component}"
                    # Match exact variant (case-insensitive to tolerate parser alterations)
                    if any(candidate.lower() == variant.lower() for variant in variants):
                        merged_components[-1] = next(
                            variant for variant in variants if candidate.lower() == variant.lower()
                        )
                        continue
            merged_components.append(component)
        components = merged_components

        # Track whether we pushed any component to the path to avoid duplicate extraction
        pushed_any = False
        normalized_components: List[str] = []

        for component in components:
            # Skip root resource references embedded in identifier
            if component == self.context.current_resource_type:
                continue
            self.context.push_path(component)
            normalized_components.append(component)
            pushed_any = True

        # If identifier referenced only the resource type (e.g., "Patient"), ensure path stack stays unchanged
        if not pushed_any and components and components[0] == self.context.current_resource_type:
            # No path components to push; handle as root reference
            json_path = "$"
        else:
            json_path = self.context.get_json_path()

        logger.debug(f"Built JSON path: {json_path} from parent_path: {self.context.parent_path}")
        if json_path == "$" and pushed_any:
            # If path resulted in root due to empty stack, reset to resource table reference
            return SQLFragment(
                expression=self.context.current_table,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False
            )

        # Handle array-aware path translation, returning early when fragments were generated
        fragment_with_arrays = self._translate_identifier_components(
            normalized_components,
            json_path,
        )
        if fragment_with_arrays is not None:
            return fragment_with_arrays

        # Check for polymorphic properties and generate COALESCE to try all variants
        # For example: Observation.value.unit should try $.valueQuantity.unit, $.valueString.unit, etc.
        polymorphic_idx = None
        for idx, comp in enumerate(normalized_components):
            if is_polymorphic_property(comp):
                polymorphic_idx = idx
                break

        logger.debug(f"SP-103-005: visit_identifier checking for polymorphic: identifier={identifier_value}, parent_path={self.context.parent_path}, polymorphic_idx={polymorphic_idx}")

        if polymorphic_idx is not None:
            poly_prop = normalized_components[polymorphic_idx]
            remaining = normalized_components[polymorphic_idx + 1:]
            variants = resolve_polymorphic_property(poly_prop) or []

            # SP-103-005: Check if there's a resolved polymorphic field from ofType()
            if hasattr(self.context, 'polymorphic_field_mappings') and poly_prop in self.context.polymorphic_field_mappings:
                resolved_field = self.context.polymorphic_field_mappings[poly_prop]
                logger.debug(f"SP-103-005: Found resolved polymorphic field: {poly_prop} -> {resolved_field}")
                logger.debug(f"SP-103-005: normalized_components={normalized_components}, polymorphic_idx={polymorphic_idx}, remaining={remaining}")

                # SP-105-004: Use parent_path instead of normalized_components when available
                # This handles cases where ofType() has resolved the polymorphic field and
                # subsequent navigation has built up the parent_path (e.g., ['valueRange', 'low'])
                # We need to use the full parent_path to build the correct JSON path
                if self.context.parent_path and len(self.context.parent_path) > 0:
                    # parent_path contains the resolved field (e.g., ['valueRange', 'low'])
                    # Build path from parent_path
                    path_parts = ["$"] + self.context.parent_path
                    resolved_path = ".".join(path_parts)
                    resolved_expr = self.dialect.extract_json_field(
                        column=self.context.current_table,
                        path=resolved_path
                    )
                    logger.debug(f"SP-105-004: Using parent_path to build resolved path: {resolved_path}")
                else:
                    # Fallback to original logic using normalized_components
                    # Build path using the resolved field instead of COALESCE
                    path_parts = ["$"] + normalized_components[:polymorphic_idx] + [resolved_field] + remaining
                    resolved_path = ".".join(path_parts)
                    resolved_expr = self.dialect.extract_json_field(
                        column=self.context.current_table,
                        path=resolved_path
                    )
                logger.debug(f"SP-103-005: Generated resolved field extraction: {resolved_expr}")
                logger.debug(f"SP-103-005: Resolved path: {resolved_path}")

                field_path = '.'.join(normalized_components) if normalized_components else ''
                source_path = "$." + field_path
                return SQLFragment(
                    expression=resolved_expr,
                    source_table=self.context.current_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    metadata={"is_json_string": True, "source_path": source_path}
                )

            if variants:
                # Build paths for all variants
                variant_exprs = []
                for variant in variants:
                    # Build path: $.prefix.variant.suffix
                    path_parts = ["$"] + normalized_components[:polymorphic_idx] + [variant] + remaining
                    variant_path = ".".join(path_parts)
                    variant_exprs.append(
                        self.dialect.extract_json_field(
                            column=self.context.current_table,
                            path=variant_path
                        )
                    )

                # Use COALESCE to try all variants
                sql_expr = f"COALESCE({', '.join(variant_exprs)})"
                logger.debug(f"Generated polymorphic COALESCE for {poly_prop}: {sql_expr}")

                # SP-103-004: Include source_path for type validation
                field_path = '.'.join(normalized_components) if normalized_components else ''
                source_path = "$." + field_path
                return SQLFragment(
                    expression=sql_expr,
                    source_table=self.context.current_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    metadata={"is_json_string": True, "source_path": source_path}
                )

        # Check if we're accessing a FHIR primitive type field
        # Build the field path from normalized components
        field_path = '.'.join(normalized_components) if normalized_components else ''
        is_primitive = False
        if field_path:
            is_primitive = self._is_primitive_field_access(field_path, self.context.current_resource_type)

        # Call dialect method to generate database-specific JSON extraction SQL
        # For primitive types, use extract_primitive_value to handle both simple and complex representations
        # This ensures we maintain the "thin dialect" architecture principle:
        # business logic here, only syntax differences in dialects
        if is_primitive:
            sql_expr = self.dialect.extract_primitive_value(
                column=self.context.current_table,
                path=json_path
            )
            logger.debug(f"Extracting primitive value for {field_path}: {sql_expr}")
        else:
            sql_expr = self.dialect.extract_json_field(
                column=self.context.current_table,
                path=json_path
            )

        logger.debug(f"Generated SQL expression: {sql_expr}")

        # SP-110-SORT: Determine element type for type-aware sorting
        # Resolve the FHIR type for this field and map to sort element type
        element_type = None
        if field_path:
            try:
                # SP-110-SORT: For paths with indexers (e.g., name[0].given), we need to
                # clean the indexer suffixes and resolve the type from the correct parent.
                # Extract the final field name and resolve parent type from the path.

                # Split field_path into components and remove indexers
                path_components = field_path.split('.')
                clean_components = []
                for component in path_components:
                    match = re.match(r'([^\[]+)', component)
                    if match:
                        clean_components.append(match.group(1))

                if len(clean_components) >= 1:
                    # Get the final field name
                    final_field = clean_components[-1]

                    # Get parent components (all except final)
                    parent_components = clean_components[:-1]

                    # Resolve parent type from parent components
                    parent_type = None
                    if parent_components:
                        parent_type = self._get_element_type_for_path(parent_components)
                    else:
                        parent_type = self.resource_type

                    # Get field type from parent type
                    if parent_type and final_field:
                        fhir_type = self.type_registry.get_element_type(parent_type, final_field)
                        if fhir_type:
                            element_type = self._get_sort_element_type(fhir_type)
                            logger.debug(
                                f"SP-110-SORT: Field '{final_field}' in parent '{parent_type}' "
                                f"has FHIR type '{fhir_type}', element_type '{element_type}'"
                            )
            except Exception as e:
                logger.debug(f"SP-110-SORT: Could not resolve element type for '{field_path}': {e}")

        # Return SQL fragment with JSON extraction expression
        # This is not an unnest operation and not an aggregate
        # Mark as JSON-extracted string for type-aware comparison casting
        # SP-103-004: Include source_path in metadata for type validation
        # SP-110-SORT: Include element_type for type-aware sorting
        source_path = "$." + field_path if field_path else json_path
        metadata = {"is_json_string": True, "source_path": source_path}
        if element_type:
            metadata["element_type"] = element_type

        return SQLFragment(
            expression=sql_expr,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            metadata=metadata
        )

    def visit_generic(self, node: Any) -> SQLFragment:
        """
        Generic visitor for AST nodes when no specific adapter matches.
        Used for container nodes like InvocationExpression that wrap chains.
        Overrides ASTVisitor.visit_generic.
        """
        logger.debug(f"Visiting generic node: {type(node).__name__}")

        # SP-110-001: Handle terminology system prefixes (e.g., %sct, %loinc)
        # These appear as TermExpression with text like '%sct'
        if hasattr(node, 'node_type') and node.node_type == 'TermExpression':
            text = getattr(node, 'text', '')
            if text and text.startswith('%'):
                system_name = text[1:].strip()  # Remove the % prefix
                # Map common terminology system prefixes to their URLs
                terminology_urls = {
                    'sct': 'http://snomed.info/sct',
                    'snomed': 'http://snomed.info/sct',
                    'loinc': 'http://loinc.org',
                    'ucum': 'http://unitsofmeasure.org',
                }
                # Check for known system
                if system_name in terminology_urls:
                    url = terminology_urls[system_name]
                    logger.debug(f"Terminology prefix {text} -> {url}")
                    return SQLFragment(
                        expression=f"'{url}'",
                        source_table=self.context.current_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        metadata={"literal_type": "string", "is_literal": True}
                    )
                # For unknown prefixes, keep them as-is (they might be custom systems)
                return SQLFragment(
                    expression=f"'{text}'",
                    source_table=self.context.current_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    metadata={"literal_type": "string", "is_literal": True}
                )

        # SP-110-001: Handle MembershipExpression for 'in' operator
        # The expression 'a in (b|c)' is parsed as MembershipExpression with two children:
        # - Child 0: the value to check (e.g., 'a')
        # - Child 1: the collection to check in (e.g., 'b'|'c')
        # This should be translated as: collection contains value
        if hasattr(node, 'node_type') and node.node_type == 'MembershipExpression':
            return self._translate_membership_expression(node)

        # If it's an EnhancedASTNode (or similar), visit children
        if hasattr(node, 'children'):
            last_fragment = None
            for child in node.children:
                # Visit child to generate fragment
                fragment = self.visit(child)

                if fragment:
                    last_fragment = fragment
                    # Append to fragments list if not already there
                    if not self.fragments or self.fragments[-1] != fragment:
                        self.fragments.append(fragment)
                    # SP-022-009: Store the fragment result for the next child in the chain
                    # This enables expressions like '1.1'.toInteger().empty() where the result
                    # of toInteger() needs to flow to the subsequent empty() function call
                    # SP-100-002: Only set pending values for non-function-call children
                    # Function calls should consume pending values, not overwrite them
                    # SP-106-003: Don't set pending_fragment_result for quantity literals - they use pending_literal_value instead
                    if (not hasattr(child, 'node_type') or child.node_type not in ('function_call', 'functionCall')) and \
                       fragment.metadata.get('literal_type') != 'quantity':
                        # SP-100-002: Check if this child is a multi-item collection (e.g., union operator)
                        is_multi_item = self._is_multi_item_collection(child)
                        # Store as tuple (expression, parent_path, is_multi_item) for cardinality validation
                        self.context.pending_fragment_result = (
                            fragment.expression,
                            self.context.parent_path.copy(),
                            is_multi_item
                        )

            return last_fragment

        raise NotImplementedError(f"No visit method for node type: {type(node).__name__}")

    def visit_function_call(self, node: FunctionCallNode) -> SQLFragment:
        """Translate function calls to SQL.

        Dispatches to specific function translation methods based on function name.
        Handles FHIRPath functions like where(), select(), first(), exists(), etc.

        Args:
            node: FunctionCallNode representing a function call

        Returns:
            SQLFragment containing the function SQL

        Raises:
            NotImplementedError: If function is not yet implemented
            ValueError: If function arguments are invalid

        Example:
            where() function:
            >>> node = FunctionCallNode(function_name="where", arguments=[condition_node])
            >>> fragment = translator.visit_function_call(node)
            >>> # Returns SQLFragment with LATERAL UNNEST SQL
        """
        logger.debug(f"Translating function call: {node.function_name}")

        # Dispatch to specific function translation method
        function_name = node.function_name.lower()

        if function_name == "where":
            return self._translate_where(node)
        elif function_name == "select":
            return self._translate_select(node)
        elif function_name == "first":
            return self._translate_first(node)
        elif function_name == "exists":
            return self._translate_exists(node)
        elif function_name == "empty":
            return self._translate_empty(node)
        elif function_name == "not":
            return self._translate_not(node)
        elif function_name == "all":
            return self._translate_all(node)
        elif function_name == "last":
            return self._translate_last(node)
        elif function_name == "skip":
            return self._translate_skip(node)
        elif function_name == "tail":
            return self._translate_tail(node)
        elif function_name == "trace":
            return self._translate_trace(node)
        elif function_name == "single":
            return self._translate_single(node)
        elif function_name == "take":
            return self._translate_take(node)
        elif function_name in ["abs", "ceiling", "floor", "round", "truncate", "sqrt", "exp", "ln", "log", "power"]:
            return self._translate_math_function(node)
        elif function_name in ["substring", "indexof", "length", "replace", "split"]:
            return self._translate_string_function(node)
        elif function_name == "upper":
            return self._translate_upper(node)
        elif function_name == "lower":
            return self._translate_lower(node)
        elif function_name == "trim":
            return self._translate_trim(node)
        elif function_name == "contains":
            # SP-108-003: Check if this is membership contains (collection contains value)
            # vs string contains (string.contains(substring))
            # Membership contains has 2 explicit arguments, string contains has 1
            if len(node.arguments) == 2 and node.target is None:
                return self._translate_contains_membership(node)
            else:
                return self._translate_contains(node)
        elif function_name == "startswith":
            return self._translate_startswith(node)
        elif function_name == "endswith":
            return self._translate_endswith(node)
        elif function_name == "matches":
            return self._translate_matches(node)
        elif function_name == "matchesfull":
            return self._translate_matchesfull(node)
        elif function_name == "replacematches":
            return self._translate_replacematches(node)
        elif function_name == "tochars":
            return self._translate_tochars(node)
        elif function_name == "highboundary":
            return self._translate_high_boundary(node)
        elif function_name == "lowboundary":
            return self._translate_low_boundary(node)
        elif function_name == "count":
            return self._translate_count_function_call(node)
        elif function_name == "convertstoboolean":
            return self._translate_converts_to_function(node, target_type="Boolean")
        elif function_name == "convertstointeger":
            return self._translate_converts_to_function(node, target_type="Integer")
        elif function_name == "convertstostring":
            return self._translate_converts_to_function(node, target_type="String")
        elif function_name == "convertstodecimal":
            return self._translate_converts_to_function(node, target_type="Decimal")
        elif function_name == "convertstoquantity":
            return self._translate_converts_to_function(node, target_type="Quantity")
        elif function_name == "convertstodate":
            return self._translate_converts_to_function(node, target_type="Date")
        elif function_name == "convertstodatetime":
            return self._translate_converts_to_function(node, target_type="DateTime")
        elif function_name == "convertstotime":
            return self._translate_converts_to_function(node, target_type="Time")
        elif function_name == "toboolean":
            return self._translate_to_boolean(node)
        elif function_name == "tointeger":
            return self._translate_to_integer(node)
        elif function_name == "tostring":
            return self._translate_to_string(node)
        elif function_name == "todecimal":
            return self._translate_to_decimal(node)
        elif function_name == "toquantity":
            return self._translate_to_quantity(node)
        elif function_name == "todate":
            return self._translate_to_date(node)
        elif function_name == "todatetime":
            return self._translate_to_datetime(node)
        elif function_name == "totime":
            return self._translate_to_time(node)
        elif function_name == "distinct":
            return self._translate_distinct(node)
        elif function_name == "isdistinct":
            return self._translate_is_distinct(node)
        elif function_name == "union":
            # SP-110-FIX: union() function call - combines collections like | operator
            return self._translate_union_function(node)
        elif function_name == "intersect":
            return self._translate_intersect(node)
        elif function_name == "join":
            return self._translate_join(node)
        elif function_name == "exclude":
            return self._translate_exclude(node)
        elif function_name == "subsetof":
            return self._translate_subsetof(node)
        elif function_name == "supersetof":
            return self._translate_supersetof(node)
        elif function_name == "repeat":
            return self._translate_repeat(node)
        elif function_name == "combine":
            return self._translate_combine(node)
        elif function_name == "conformsto":
            return self._translate_conforms_to(node)
        elif function_name == "extension":
            return self._translate_extension_function(node)
        elif function_name == "iif":
            return self._translate_iif(node)
        elif function_name == "alltrue":
            return self._translate_all_true(node)
        elif function_name == "anytrue":
            return self._translate_any_true(node)
        elif function_name == "allfalse":
            return self._translate_all_false(node)
        elif function_name == "anyfalse":
            return self._translate_any_false(node)
        elif function_name == "aggregate":
            return self._translate_aggregate(node)
        elif function_name == "sum":
            return self._translate_sum(node)
        elif function_name == "avg":
            return self._translate_avg(node)
        elif function_name == "min":
            return self._translate_min(node)
        elif function_name == "max":
            return self._translate_max(node)
        # Type functions - handlers for function call syntax type operations
        # These bridge FunctionCallNode (from AST adapter) to type operation implementations
        elif function_name == "type":
            return self._translate_type(node)
        elif function_name == "is":
            return self._translate_is_from_function_call(node)
        elif function_name == "as":
            return self._translate_as_from_function_call(node)
        elif function_name == "oftype":
            return self._translate_oftype_from_function_call(node)
        # Temporal functions
        elif function_name == "today":
            return self._translate_today(node)
        elif function_name == "now":
            return self._translate_now(node)
        elif function_name == "timeofday":
            return self._translate_timeofday(node)
        elif function_name == "children":
            return self._translate_children(node)
        elif function_name == "encode":
            return self._translate_encode(node)
        elif function_name == "decode":
            return self._translate_decode(node)
        elif function_name == "escape":
            return self._translate_escape(node)
        elif function_name == "unescape":
            return self._translate_unescape(node)
        elif function_name == "sort":
            return self._translate_sort(node)
        elif function_name == "descendants":
            return self._translate_descendants(node)
        else:
            raise ValueError(f"Unknown or unsupported function: {node.function_name}")

    def _translate_high_boundary(self, node: FunctionCallNode) -> SQLFragment:
        """Translate highBoundary() function to SQL with type-aware routing."""
        (
            target_expr,
            dependencies,
            literal_value,
            snapshot,
            target_ast,
            target_path,
        ) = self._resolve_function_target(node)

        if not target_expr:
            raise FHIRPathTranslationError(
                "Unable to resolve input expression for highBoundary()"
            )

        try:
            precision = self._extract_boundary_precision(node)
            input_type = self._determine_boundary_input_type(
                target_ast,
                literal_value,
                target_path,
            )

            logger.debug(
                "highBoundary() input resolved: expr=%s, type=%s, precision=%s",
                target_expr,
                input_type,
                precision,
            )

            sql_expr: str
            if input_type in {"integer", "decimal", "number"}:
                sql_expr = self._translate_decimal_boundary(
                    base_expr=target_expr,
                    precision_param=precision,
                    boundary_type="high",
                )
            elif input_type in {"quantity", "age", "duration"}:
                sql_expr = self._translate_quantity_boundary(
                    base_expr=target_expr,
                    precision_param=precision,
                    boundary_type="high",
                    literal_node=target_ast if isinstance(target_ast, LiteralNode) else None,
                )
            elif input_type in {"date", "datetime", "time", "instant"}:
                sql_expr = self._translate_temporal_boundary(
                    base_expr=target_expr,
                    precision_param=precision,
                    input_type=input_type,
                    boundary_type="high",
                    literal_node=target_ast if isinstance(target_ast, LiteralNode) else None,
                )
            else:
                raise FHIRPathTranslationError(
                    f"highBoundary() not supported for input type '{input_type}'"
                )

            fragment = SQLFragment(
                expression=sql_expr,
                source_table=snapshot["current_table"],
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
            )

            return fragment

        finally:
            self._restore_context(snapshot)

    def _translate_low_boundary(self, node: FunctionCallNode) -> SQLFragment:
        """Translate lowBoundary() function to SQL with type-aware routing."""
        (
            target_expr,
            dependencies,
            literal_value,
            snapshot,
            target_ast,
            target_path,
        ) = self._resolve_function_target(node)

        if not target_expr:
            raise FHIRPathTranslationError(
                "Unable to resolve input expression for lowBoundary()"
            )

        try:
            precision = self._extract_boundary_precision(node)
            input_type = self._determine_boundary_input_type(
                target_ast,
                literal_value,
                target_path,
            )

            logger.debug(
                "lowBoundary() input resolved: expr=%s, type=%s, precision=%s",
                target_expr,
                input_type,
                precision,
            )

            sql_expr: str
            if input_type in {"integer", "decimal", "number"}:
                sql_expr = self._translate_decimal_boundary(
                    base_expr=target_expr,
                    precision_param=precision,
                    boundary_type="low",
                )
            elif input_type in {"quantity", "age", "duration"}:
                sql_expr = self._translate_quantity_boundary(
                    base_expr=target_expr,
                    precision_param=precision,
                    boundary_type="low",
                    literal_node=target_ast if isinstance(target_ast, LiteralNode) else None,
                )
            elif input_type in {"date", "datetime", "time", "instant"}:
                sql_expr = self._translate_temporal_boundary(
                    base_expr=target_expr,
                    precision_param=precision,
                    input_type=input_type,
                    boundary_type="low",
                    literal_node=target_ast if isinstance(target_ast, LiteralNode) else None,
                )
            else:
                raise FHIRPathTranslationError(
                    f"lowBoundary() not supported for input type '{input_type}'"
                )

            fragment = SQLFragment(
                expression=sql_expr,
                source_table=snapshot["current_table"],
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
            )

            return fragment

        finally:
            self._restore_context(snapshot)

    def _extract_boundary_precision(self, node: FunctionCallNode) -> Optional[int]:
        """Extract precision argument for boundary functions, if provided."""
        if not node.arguments:
            return None

        precision_arg = node.arguments[0]

        if isinstance(precision_arg, LiteralNode) and isinstance(precision_arg.value, int):
            return precision_arg.value

        # Attempt to parse integer from literal text (handles cases like "6")
        text = getattr(precision_arg, "text", None)
        if text is not None:
            stripped = text.strip().strip("'\"")
            if stripped.lstrip("-").isdigit():
                return int(stripped)

        logger.warning("Unable to parse precision argument for highBoundary(); ignoring parameter")
        return None

    def _determine_boundary_input_type(
        self,
        target_ast: Optional[FHIRPathASTNode],
        literal_value: Optional[Any],
        target_path: Optional[List[str]],
    ) -> str:
        """Determine the FHIR type of the boundary input expression."""
        from ..ast.nodes import LiteralNode, IdentifierNode, FunctionCallNode

        if isinstance(target_ast, LiteralNode):
            return self._determine_literal_type(target_ast)

        if literal_value is not None:
            return self._infer_literal_type(literal_value)

        if isinstance(target_ast, IdentifierNode):
            return self._resolve_path_type(target_ast, target_path)

        if isinstance(target_ast, FunctionCallNode) and target_ast.target is not None:
            return self._determine_boundary_input_type(
                target_ast.target,
                None,
                target_path,
            )

        if target_path:
            resolver_path = ".".join(target_path)
            resolved = self.element_type_resolver.resolve_element_type(
                self.context.current_resource_type,
                resolver_path,
            )
            if resolved:
                return resolved.lower()

        return "decimal"

    def _determine_literal_type(self, literal_node: LiteralNode) -> str:
        """Determine input type from literal node."""
        value = getattr(literal_node, "value", None)
        text = getattr(literal_node, "text", None)
        return self._infer_literal_type(value, text)

    def _infer_literal_type(self, value: Any, text: Optional[str] = None) -> str:
        """Infer literal type from value/text representation."""
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, (float, Decimal)):
            return "decimal"
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("@"):
                detected = self.temporal_parser.detect_type(stripped)
                if detected:
                    return detected.lower()
            quantity_match = self._match_quantity_literal(value)
            if quantity_match:
                return "quantity"
            return "string"

        if text:
            temporal_text = text.strip()
            if temporal_text.startswith("@"):
                detected = self.temporal_parser.detect_type(temporal_text)
                if detected:
                    return detected.lower()
            if self._match_quantity_literal(text):
                return "quantity"

        return "decimal"

    def _resolve_path_type(
        self,
        identifier_node: IdentifierNode,
        target_path: Optional[List[str]],
    ) -> str:
        """Resolve FHIR element type using element type resolver."""
        resource_type = self.context.current_resource_type

        identifier = identifier_node.identifier or ""
        if identifier.startswith(f"{resource_type}."):
            relative_path = identifier[len(resource_type) + 1 :]
        else:
            relative_path = identifier

        if target_path:
            relative_path = ".".join(target_path)

        resolved = self.element_type_resolver.resolve_element_type(
            resource_type,
            relative_path,
        )

        if resolved:
            return resolved.lower()

        logger.warning(
            "Unable to resolve type for %s.%s, defaulting to decimal",
            resource_type,
            relative_path,
        )
        return "decimal"

    def _translate_decimal_boundary(
        self,
        base_expr: str,
        precision_param: Optional[int],
        boundary_type: str,
    ) -> str:
        """Delegate decimal boundary generation to dialect."""
        return self.dialect.generate_decimal_boundary(
            base_expr=base_expr,
            target_precision=precision_param,
            boundary_type=boundary_type,
        )

    def _translate_quantity_boundary(
        self,
        base_expr: str,
        precision_param: Optional[int],
        boundary_type: str,
        literal_node: Optional[LiteralNode] = None,
    ) -> str:
        """Translate quantity boundary handling literals and dynamic expressions."""
        if literal_node is not None:
            literal_sql = self._compute_quantity_literal_boundary(
                literal_node,
                precision_param,
                boundary_type,
            )
            return literal_sql

        raise FHIRPathTranslationError(
            "highBoundary() currently supports quantity literals only; "
            "dynamic quantity boundaries require dedicated path handling."
        )

    def _translate_temporal_boundary(
        self,
        base_expr: str,
        precision_param: Optional[int],
        input_type: str,
        boundary_type: str,
        literal_node: Optional[LiteralNode] = None,
    ) -> str:
        """Delegate temporal boundary handling to dialect with timezone context."""
        has_timezone = False
        if literal_node is not None:
            value = getattr(literal_node, "value", None)
            text = getattr(literal_node, "text", None)
            literal_text = text or (value if isinstance(value, str) else None)
            if literal_text:
                parsed = self.temporal_parser.parse(literal_text.strip())
                has_timezone = bool(parsed and parsed.timezone_offset)

        return self.dialect.generate_temporal_boundary(
            base_expr=base_expr,
            input_type=input_type,
            precision=precision_param,
            boundary_type=boundary_type,
            has_timezone=has_timezone,
        )

    def _compute_quantity_literal_boundary(
        self,
        literal_node: LiteralNode,
        precision_param: Optional[int],
        boundary_type: str,
    ) -> str:
        """Compute boundary for quantity literal at translation time."""
        quantity_components = self._parse_quantity_literal_components(literal_node)
        if quantity_components is None:
            raise FHIRPathTranslationError(
                f"Invalid quantity literal for boundary function: {literal_node.text}"
            )

        value_str, unit = quantity_components
        amount = Decimal(value_str)
        input_precision = self._count_decimal_places(value_str)
        target_precision = self._normalize_target_precision(
            precision_param,
            input_precision,
        )

        if target_precision is None:
            return "NULL"

        boundary_value = self._compute_boundary_decimal_value(
            amount,
            input_precision,
            target_precision,
            boundary_type,
        )
        formatted = self._format_decimal(boundary_value, target_precision)
        unit_escaped = unit.replace("'", "''")
        return f"'{formatted} ''{unit_escaped}'''"

    def _normalize_target_precision(
        self,
        explicit_precision: Optional[int],
        input_precision: int,
    ) -> Optional[int]:
        """Normalize precision parameter according to specification limits."""
        if explicit_precision is not None:
            if explicit_precision < 0 or explicit_precision > 31:
                return None
            return explicit_precision

        target = input_precision + 5
        if target < 8:
            target = 8
        if target > 31:
            target = 31
        return target

    def _compute_boundary_decimal_value(
        self,
        value: Decimal,
        input_precision: int,
        target_precision: int,
        boundary_type: str,
    ) -> Decimal:
        """Compute boundary value using uncertainty interval."""
        uncertainty = Decimal("0.5") * (Decimal("10") ** (-input_precision))
        if boundary_type == "high":
            boundary = value + uncertainty
        else:
            boundary = value - uncertainty

        quantize_exp = Decimal("1") if target_precision == 0 else Decimal(f"1E-{target_precision}")
        quantized = boundary.quantize(quantize_exp, rounding=ROUND_HALF_UP)
        if quantized == 0:
            quantized = abs(quantized)
        return quantized

    def _format_decimal(self, value: Decimal, precision: int) -> str:
        """Format decimal with fixed precision preserving trailing zeros."""
        format_spec = f"{{0:.{precision}f}}" if precision > 0 else "{0:.0f}"
        return format_spec.format(value)

    def _count_decimal_places(self, value_str: str) -> int:
        """Count decimal places from textual numeric representation."""
        if "." not in value_str:
            return 0
        fractional = value_str.split(".", 1)[1]
        return len(fractional)

    def _parse_quantity_literal_components(
        self,
        literal_node: LiteralNode,
    ) -> Optional[Tuple[str, str]]:
        """Extract numeric string and unit from quantity literal."""
        text = getattr(literal_node, "text", "") or ""
        match = self._match_quantity_literal(text)
        if not match:
            return None
        number_str, unit = match.groups()
        return number_str, unit

    @staticmethod
    def _match_quantity_literal(value: str) -> Optional[re.Match]:
        """Match quantity literal pattern."""
        pattern = r"\s*(-?\d+(?:\.\d+)?)\s*'([^']+)'\s*"
        return re.fullmatch(pattern, value or "")

    def _extract_quantity_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract quantity information from text that may represent a quantity literal.

        SP-106-003: Detect quantity literals that were not properly identified by the parser.
        The parser treats expressions like "10 'mg'" as string literals, but we can
        detect the pattern and extract the quantity value and unit.

        Args:
            text: The text representation of the literal (e.g., "10'mg'", "10.5 'kg'")

        Returns:
            Dictionary with 'value' (Decimal) and 'unit' (str) if text matches quantity pattern,
            None otherwise

        Example:
            >>> self._extract_quantity_from_text("10'mg'")
            {'value': Decimal('10'), 'unit': 'mg'}
            >>> self._extract_quantity_from_text("10.5 'kg'")
            {'value': Decimal('10.5'), 'unit': 'kg'}
        """
        if not text:
            return None

        # Try to match the quantity pattern: NUMBER 'UNIT'
        # The parser may remove spaces, so we handle both "10'mg'" and "10 'mg'"
        match = self._match_quantity_literal(text)
        if match:
            try:
                value_str = match.group(1)
                unit = match.group(2)
                return {
                    'value': Decimal(value_str),
                    'unit': unit
                }
            except (ValueError, InvalidOperation):
                return None

        return None

    def _handle_quantity_literal(self, node: LiteralNode, quantity_info: Dict[str, Any]) -> SQLFragment:
        """Handle a quantity literal by generating proper FHIR Quantity JSON structure.

        SP-106-003: Generate SQL that creates a FHIR Quantity JSON object for literals
        like "10 'mg'". This enables proper type checking and comparison operations.

        Delegates to FHIR-specific business logic layer (quantity_builder) to maintain
        thin dialect principle - the translator contains only syntax translation logic.

        Args:
            node: The literal node (still has literal_type="string" from parser)
            quantity_info: Dict with 'value' (Decimal) and 'unit' (str)

        Returns:
            SQLFragment with the quantity represented as JSON

        Example:
            >>> # For "10 'mg'"
            >>> fragment = self._handle_quantity_literal(node, {'value': Decimal('10'), 'unit': 'mg'})
            >>> fragment.expression
            '{"value": 10, "unit": "mg", "system": "http://unitsofmeasure.org", "code": "mg"}'
        """
        value = quantity_info['value']
        unit = quantity_info['unit']

        # Generate FHIR Quantity JSON structure using FHIR-specific business logic
        # This ensures the translator remains "thin" - only syntax translation, no FHIR rules
        quantity_json_str = build_quantity_json_string(value, unit)

        # Convert to SQL expression
        sql_expr = f"'{quantity_json_str}'"

        # Store quantity info in context for function calls like convertsToQuantity()
        # SP-106-003: Store a special marker to indicate this is a quantity literal
        # This allows convertsToQuantity() to recognize it and return TRUE
        class QuantityLiteralMarker:
            def __init__(self, value, unit):
                self.value = value
                self.unit = unit
                self.is_quantity_literal = True

        self.context.pending_literal_value = (QuantityLiteralMarker(value, unit), sql_expr)

        # Create metadata with quantity information
        # SP-110-001: Normalize unit to enable unit conversion in comparisons
        normalized_unit = self._normalize_quantity_unit(unit) if unit else unit
        fragment_metadata = {
            'literal_type': 'quantity',
            'is_literal': True,
            'quantity_value': str(value),
            'quantity_unit': normalized_unit if normalized_unit else unit
        }
        if node.text:
            fragment_metadata['source_text'] = node.text
            fragment_metadata['text'] = node.text

        logger.debug(f"Generated quantity literal SQL: {sql_expr}")

        return SQLFragment(
            expression=sql_expr,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            metadata=fragment_metadata
        )

    def _convert_to_boolean(self, expr: str, literal_type: Optional[str] = None) -> str:
        """Convert any expression to boolean using FHIRPath truthiness rules.

        FHIRPath ToBoolean() semantics:
        - Boolean: the value itself
        - Integer/Decimal: false if 0, true otherwise
        - String: false if empty, true otherwise
        - NULL (empty collection): false

        Args:
            expr: SQL expression to convert to boolean
            literal_type: The literal type if known (boolean, integer, decimal, string)

        Returns:
            SQL expression that evaluates to TRUE/FALSE based on truthiness

        Example:
            >>> self._convert_to_boolean("'foo'", "string")
            "CASE WHEN 'foo' IS NULL THEN FALSE WHEN LENGTH('foo') > 0 THEN TRUE ELSE FALSE END"

            >>> self._convert_to_boolean("TRUE", "boolean")
            "TRUE"
        """
        expr_stripped = str(expr).strip()
        expr_upper = expr_stripped.upper()

        # CRITICAL: Check if expression is already a boolean expression FIRST
        # This must happen BEFORE checking literal_type, because expressions like
        # (CAST(x AS VARCHAR) = 'P') are boolean but might have literal_type='string'
        # from their operands.
        #
        # Boolean expressions include:
        # 1. TRUE/FALSE literals
        # 2. CASE/COALESCE/EXISTS expressions
        # 3. Comparison operators (=, !=, <, >, <=, >=, ~)
        # 4. Logical operators (AND, OR, XOR, NOT)
        # 5. IS [NOT] NULL/TRUE/FALSE expressions
        is_boolean_expr = (
            expr_upper in ("TRUE", "FALSE") or
            expr_upper.startswith(("CASE WHEN ", "COALESCE(", "NOT ", "EXISTS(")) or
            " IS NULL" in expr_upper or " IS NOT NULL" in expr_upper or
            " IS TRUE" in expr_upper or " IS FALSE" in expr_upper or
            # Check for comparison operators (=, !=, <, >, <=, >=, ~) and logical operators (AND, OR, XOR)
            any(op in expr_stripped for op in (" = ", " != ", " < ", " > ", " <= ", " >= ", " AND ", " OR ", " XOR "))
        )

        if is_boolean_expr:
            # Expression is already boolean - return as-is to avoid TRIM(BOOLEAN) error
            # This fixes the bug where comparison results were incorrectly wrapped in LENGTH(TRIM(...))
            return expr
        elif literal_type == "boolean":
            # Boolean expressions are already boolean
            return expr
        elif literal_type == "integer" or literal_type == "decimal":
            # Numbers: 0 is false, non-zero is true
            return f"CASE WHEN {expr} IS NULL THEN FALSE WHEN CAST({expr} AS DOUBLE) <> 0 THEN TRUE ELSE FALSE END"
        elif literal_type == "string":
            # Strings: empty is false, non-empty is true
            return f"CASE WHEN {expr} IS NULL THEN FALSE WHEN LENGTH(TRIM({expr})) > 0 THEN TRUE ELSE FALSE END"
        else:
            # Unknown type - try to infer from expression
            # If it's a string literal (single-quoted), check length
            if expr_stripped.startswith("'") and expr_stripped.endswith("'"):
                return f"CASE WHEN LENGTH(TRIM({expr})) > 0 THEN TRUE ELSE FALSE END"
            # If it's a number literal (no quotes, all digits or decimal)
            if expr_stripped.replace(".", "", 1).replace("-", "", 1).isdigit():
                return f"CASE WHEN CAST({expr} AS DOUBLE) <> 0 THEN TRUE ELSE FALSE END"
            # Default: try to cast and check non-zero
            return f"CASE WHEN {expr} IS NULL THEN FALSE WHEN COALESCE(CAST({expr} AS BOOLEAN), FALSE) THEN TRUE ELSE FALSE END"

    def _get_fhirpath_truthiness_sql(self, value_var: str = "value", elem_var: str = "elem") -> str:
        """Generate SQL for FHIRPath truthiness check on collection elements.

        FHIRPath truthiness rules (from specification):
        - Strings: empty string = false, non-empty = true
        - Numbers: 0 = false, non-zero = true
        - Booleans: actual value (true/false)
        - Arrays/Objects: non-empty = true, empty = false
        - null/missing: false

        This is BUSINESS LOGIC (FHIRPath specification), not database syntax.
        Dialects provide only the type detection primitives (json_type/jsonb_typeof).

        Args:
            value_var: Variable name for json_each() context (default: "value" for DuckDB)
            elem_var: Variable name for jsonb_array_elements() context (default: "elem" for PostgreSQL)

        Returns:
            SQL CASE expression implementing FHIRPath truthiness rules

        Example:
            DuckDB: CASE WHEN json_type(value) = 'VARCHAR' THEN LENGTH(json_extract_string(value, '$')) > 0 ...
            PostgreSQL: CASE WHEN jsonb_typeof(elem) = 'string' THEN LENGTH(elem) > 0 ...
        """
        # Get type detection SQL from dialect (syntax-only: json_type() vs jsonb_typeof())
        type_check_sql = self.dialect.generate_truthiness_type_check(value_var, elem_var)
        return type_check_sql

    def _build_implies_sql(
        self,
        left_sql: str,
        left_is_empty: bool,
        left_is_true_literal: bool,
        left_is_false_literal: bool,
        right_sql: str,
        right_is_empty: bool,
        right_metadata: dict,
    ) -> str:
        """Build SQL expression for Implies operator with empty collection handling.

        The Implies operator (a implies b) is logically equivalent to (NOT a) OR b.
        This method handles the complex empty collection semantics as specified in
        the FHIRPath specification.

        Empty collection handling:
        - {} implies true -> true (empty antecedent is true)
        - {} implies false -> {} (propagate empty)
        - {} implies {} -> {} (propagate empty)
        - true implies {} -> {} (propagate empty)
        - false implies {} -> true (false implies anything)
        - false implies anything -> true (false implies anything)

        Args:
            left_sql: SQL expression for the left operand (antecedent)
            left_is_empty: Whether the left operand is an empty collection
            left_is_true_literal: Whether the left operand is a TRUE boolean literal
            left_is_false_literal: Whether the left operand is a FALSE boolean literal
            right_sql: SQL expression for the right operand (consequent)
            right_is_empty: Whether the right operand is an empty collection
            right_metadata: Metadata dictionary for the right operand

        Returns:
            SQL expression implementing the Implies operator with proper empty
            collection handling
        """
        if left_is_empty and right_is_empty:
            # {} implies {} -> {} (propagate empty)
            return "NULL"
        elif left_is_empty and not right_is_empty:
            # Check if right is false literal
            right_is_false_literal = (
                right_metadata.get("is_literal") is True
                and right_metadata.get("literal_type") == "boolean"
                and str(right_sql).upper() == "FALSE"
            )
            if right_is_false_literal:
                # {} implies false -> {} (propagate empty)
                return "NULL"
            else:
                # {} implies true -> (NOT left) OR right
                # Empty antecedent is treated as true, but we generate the full expression
                # to properly demonstrate empty collection handling in SQL
                not_left = self.dialect.generate_boolean_not(left_sql)
                return f"({not_left}) OR ({right_sql})"
        elif left_is_true_literal and right_is_empty:
            # true implies {} -> {} (propagate empty)
            return "NULL"
        elif left_is_false_literal:
            # false implies anything -> true
            return "TRUE"
        else:
            # Standard implies: (NOT left) OR right
            not_left = self.dialect.generate_boolean_not(left_sql)
            return f"({not_left}) OR ({right_sql})"

    def visit_operator(self, node: OperatorNode) -> SQLFragment:
        """Translate operators to SQL.

        Converts FHIRPath operators (=, !=, <, >, and, or, etc.) to SQL
        equivalents. Handles operator precedence and type conversion.

        This method handles four categories of operators:
        1. Comparison operators: =, !=, <, >, <=, >=, ~, !~
        2. Logical operators: and, or, xor, implies
        3. Arithmetic operators: +, -, *, /, div, mod
        4. Collection operators: union (|)

        The method translates both operands recursively and then combines them
        with the appropriate SQL operator syntax. Type-aware comparisons use
        dialect methods when needed.

        Args:
            node: OperatorNode representing an operator

        Returns:
            SQLFragment containing the operator SQL

        Raises:
            ValueError: If operator is unknown or operands are invalid

        Example:
            Comparison operator:
            >>> node = OperatorNode(operator="=", children=[left_node, right_node])
            >>> fragment = translator.visit_operator(node)
            >>> fragment.expression
            "(left_expr = right_expr)"

            Logical operator:
            >>> node = OperatorNode(operator="and", children=[left_node, right_node])
            >>> fragment = translator.visit_operator(node)
            >>> fragment.expression
            "(left_expr AND right_expr)"

            Arithmetic operator:
            >>> node = OperatorNode(operator="+", children=[left_node, right_node])
            >>> fragment = translator.visit_operator(node)
            >>> fragment.expression
            "(left_expr + right_expr)"
        """
        logger.debug(f"Translating operator: {node.operator} (type: {node.operator_type})")

        # Validate operator has required operands
        if node.operator_type == "unary":
            if len(node.children) != 1:
                raise ValueError(f"Unary operator '{node.operator}' requires exactly 1 operand, got {len(node.children)}")
        elif node.operator_type in ["binary", "comparison", "logical", "union"]:
            if len(node.children) != 2:
                raise ValueError(f"Binary operator '{node.operator}' requires exactly 2 operands, got {len(node.children)}")

        # Handle unary operators
        if node.operator_type == "unary":
            return self._translate_unary_operator(node)

        # Handle binary operators (comparison, logical, arithmetic, collection)
        return self._translate_binary_operator(node)

    def _translate_unary_operator(self, node: OperatorNode) -> SQLFragment:
        """Translate unary operators to SQL.

        Handles unary operators like 'not', unary '+', and unary '-'.

        Args:
            node: OperatorNode with operator_type="unary"

        Returns:
            SQLFragment containing the unary operator SQL

        Example:
            >>> node = OperatorNode(operator="not", children=[operand_node])
            >>> fragment = translator._translate_unary_operator(node)
            >>> fragment.expression
            "(NOT operand_expr)"
        """
        # Translate the operand
        operand_fragment = self.visit(node.children[0])

        # Map FHIRPath unary operators to SQL
        sql_operator_map = {
            "not": "NOT",
            "+": "+",
            "-": "-"
        }

        sql_operator = sql_operator_map.get(node.operator.lower())
        if sql_operator is None:
            raise ValueError(f"Unknown unary operator: {node.operator}")

        # Generate SQL expression
        sql_expr = f"({sql_operator} {operand_fragment.expression})"

        logger.debug(f"Generated unary operator SQL: {sql_expr}")

        # SP-108-001: Preserve metadata from operand for unary operators
        # This ensures CTE builder can recognize when unary operator is applied to
        # aggregate functions (e.g., -count() should be treated as aggregate)
        # Initialize metadata as empty dict to ensure consistent handling
        metadata = {}
        if isinstance(operand_fragment.metadata, dict):
            metadata = dict(operand_fragment.metadata)

        return SQLFragment(
            expression=sql_expr,
            source_table=operand_fragment.source_table,
            requires_unnest=operand_fragment.requires_unnest,
            is_aggregate=operand_fragment.is_aggregate,
            metadata=metadata
        )

    def _translate_binary_operator(self, node: OperatorNode) -> SQLFragment:
        """Translate binary operators to SQL.

        Handles comparison, logical, and arithmetic operators.

        Args:
            node: OperatorNode with binary operator

        Returns:
            SQLFragment containing the binary operator SQL

        Example:
            >>> node = OperatorNode(operator="=", children=[left_node, right_node])
            >>> fragment = translator._translate_binary_operator(node)
            >>> fragment.expression
            "(left_expr = right_expr)"
        """
        # SP-022-013: Handle union operators BEFORE visiting children to prevent
        # exponential SQL growth. Union chains like (1|2|3|4) parse as nested
        # UnionExpressions. If we visit children first, each level duplicates
        # the SQL 6+ times, causing exponential growth (10x per element).
        # Instead, we collect all operands from the AST and translate each once.
        if node.operator_type == "union" or node.operator in {"|", "union"}:
            return self._translate_union_chain(node)

        # Attempt specialized handling for temporal literals before generic translation
        if node.operator_type == "comparison":
            temporal_fragment = self._translate_temporal_literal_comparison_if_applicable(node)
            if temporal_fragment is not None:
                return temporal_fragment

        # SP-103-005: Save context state before translating operands
        # This prevents path pollution where the right operand inherits
        # parent_path modifications from the left operand.
        # Example: value.ofType(Range).low.value + value.ofType(Range).high.value
        # Without this isolation, the right operand incorrectly starts with
        # parent_path=['valueRange', 'low', 'value'] instead of [].
        saved_path = self.context.parent_path.copy()
        saved_table = self.context.current_table
        saved_element_column = self.context.current_element_column
        saved_element_type = self.context.current_element_type

        # Translate left operand
        left_fragment = self.visit(node.children[0])

        # Restore context before translating right operand
        self.context.parent_path = saved_path.copy()
        self.context.current_table = saved_table
        self.context.current_element_column = saved_element_column
        self.context.current_element_type = saved_element_type

        # Translate right operand with clean context
        right_fragment = self.visit(node.children[1])

        # SP-022-007: Fix column reference for first()/last()/skip()/take() + comparison
        # When a subset filter operation (e.g., first()) precedes a comparison, the CTE
        # builder renames the output column to "result". The fragment's expression still
        # references the original column name (e.g., "given_item"), which causes a
        # "column not found" error. We need to use "result" instead.
        # Additionally, UNNEST produces JSON-typed values that need casting for comparison.
        left_metadata = getattr(left_fragment, "metadata", {}) or {}
        if left_metadata.get("subset_filter"):
            # The CTE wrapping this fragment will output the column as "result"
            # Also mark as JSON string since UNNEST produces JSON-typed values
            updated_metadata = dict(left_metadata)
            updated_metadata["is_json_string"] = True
            left_fragment = SQLFragment(
                expression="result",
                source_table=left_fragment.source_table,
                requires_unnest=left_fragment.requires_unnest,
                is_aggregate=left_fragment.is_aggregate,
                dependencies=left_fragment.dependencies,
                metadata=updated_metadata,
            )

        # SP-022-017: Fix column reference for chained path navigation + comparison
        # When path navigation follows a collection function (e.g., first().given), the
        # UNNEST fragment has from_element_column=True and its expression is a json_extract
        # from "result". But in the comparison context, we should reference the UNNEST
        # result column (e.g., "given_item"), not the raw json_extract expression.
        # The result_alias metadata contains the correct column name.
        if (left_metadata.get("from_element_column") and
                left_fragment.requires_unnest and
                left_metadata.get("result_alias")):
            # Use the UNNEST result column name for the comparison
            result_alias = left_metadata["result_alias"]
            updated_metadata = dict(left_metadata)
            updated_metadata["is_json_string"] = True
            left_fragment = SQLFragment(
                expression=result_alias,
                source_table=left_fragment.source_table,
                requires_unnest=left_fragment.requires_unnest,
                is_aggregate=left_fragment.is_aggregate,
                dependencies=left_fragment.dependencies,
                metadata=updated_metadata,
            )

        # Note: Union operators are handled at the start of _translate_binary_operator
        # before visiting children (see SP-022-013). This dead code block is kept for
        # reference but should never be reached.

        # Handle temporal arithmetic (e.g., date + quantity, date - quantity with time unit)
        if node.operator == "+":
            temporal_fragment = self._translate_temporal_quantity_addition(
                left_fragment,
                right_fragment,
                node.children[0],
                node.children[1]
            )
            if temporal_fragment is not None:
                return temporal_fragment

        if node.operator == "-":
            temporal_fragment = self._translate_temporal_quantity_subtraction(
                left_fragment,
                right_fragment,
                node.children[0],
                node.children[1]
            )
            if temporal_fragment is not None:
                return temporal_fragment

        # Handle string concatenation with thin dialect support
        if node.operator == "&":
            def _normalize_concat_operand(expr: str) -> str:
                """Cast operand to string and ensure NULL/empty collections become empty strings."""
                string_expr = self._build_to_string_expression(expr)
                return f"COALESCE({string_expr}, '')"

            left_operand = _normalize_concat_operand(left_fragment.expression)
            right_operand = _normalize_concat_operand(right_fragment.expression)

            sql_expr = self.dialect.string_concat(left_operand, right_operand)
        else:
            # Map FHIRPath operators to SQL operators
            operator_map = {
                # Comparison operators
                "=": "=",
                "!=": "!=",
                "<": "<",
                ">": ">",
                "<=": "<=",
                ">=": ">=",
                # Equivalence operators (handled specially by _generate_equivalence_sql)
                "~": "~",
                "!~": "!~",

                # Logical operators
                "and": "AND",
                "or": "OR",
                "xor": "XOR",
                "implies": "IMPLIES",  # Handled specially below with empty collection semantics

                # Arithmetic operators
                "+": "+",
                "-": "-",
                "*": "*",
                "/": "/",
                "div": "/",  # Integer division (SQL / handles this)
                "mod": "%"   # Modulo operator
            }

            operator_lower = node.operator.lower()
            sql_operator = operator_map.get(operator_lower)
            if sql_operator is None:
                raise ValueError(f"Unknown binary operator: {node.operator}")

            # Use dialect methods for operator-specific SQL generation
            if node.operator_type == "logical" and operator_lower in ["and", "or"]:
                # SP-110-001: Handle empty collection semantics for AND/OR operators
                # According to FHIRPath spec:
                # - AND: false and {} = false, {} and false = false, {} and true = {}, {} and {} = {}
                # - OR: true or {} = true, {} or true = true, {} or false = {}, {} or {} = {}
                # Empty collections propagate: false AND {} = false, true OR {} = true
                # But: {} AND true = {} (empty), true AND {} = {} (empty)
                #     {} OR false = {} (empty), false OR {} = {} (empty)

                left_metadata = getattr(left_fragment, "metadata", {}) or {}
                right_metadata = getattr(right_fragment, "metadata", {}) or {}
                left_is_empty = left_metadata.get("is_empty_collection") is True
                right_is_empty = right_metadata.get("is_empty_collection") is True

                # Determine if operands are boolean literals for short-circuit evaluation
                left_is_true_literal = (left_metadata.get("is_literal") is True and
                                        left_metadata.get("literal_type") == "boolean" and
                                        str(left_fragment.expression).upper() == "TRUE")
                left_is_false_literal = (left_metadata.get("is_literal") is True and
                                         left_metadata.get("literal_type") == "boolean" and
                                         str(left_fragment.expression).upper() == "FALSE")
                right_is_true_literal = (right_metadata.get("is_literal") is True and
                                         right_metadata.get("literal_type") == "boolean" and
                                         str(right_fragment.expression).upper() == "TRUE")
                right_is_false_literal = (right_metadata.get("is_literal") is True and
                                          right_metadata.get("literal_type") == "boolean" and
                                          str(right_fragment.expression).upper() == "FALSE")

                if operator_lower == "and":
                    # AND operator: false AND anything = false
                    # Empty collection propagation:
                    # - false AND {} = false (left is false, result is false)
                    # - {} AND false = false (right is false, result is false)
                    # - true AND {} = {} (right is empty, result is empty)
                    # - {} AND true = {} (left is empty, result is empty)
                    # - {} AND {} = {} (both empty, result is empty)
                    if left_is_false_literal:
                        # Short-circuit: false AND anything = false
                        sql_expr = "FALSE"
                        # Clear is_empty_collection since result is a boolean literal
                        left_metadata = dict(left_metadata)
                        left_metadata.pop("is_empty_collection", None)
                        left_fragment = SQLFragment(
                            expression=left_fragment.expression,
                            source_table=left_fragment.source_table,
                            requires_unnest=left_fragment.requires_unnest,
                            is_aggregate=left_fragment.is_aggregate,
                            dependencies=left_fragment.dependencies,
                            metadata=left_metadata
                        )
                    elif right_is_false_literal:
                        # Short-circuit: anything AND false = false
                        sql_expr = "FALSE"
                        # Clear is_empty_collection since result is a boolean literal
                        right_metadata = dict(right_metadata)
                        right_metadata.pop("is_empty_collection", None)
                        right_fragment = SQLFragment(
                            expression=right_fragment.expression,
                            source_table=right_fragment.source_table,
                            requires_unnest=right_fragment.requires_unnest,
                            is_aggregate=right_fragment.is_aggregate,
                            dependencies=right_fragment.dependencies,
                            metadata=right_metadata
                        )
                    elif left_is_empty and right_is_empty:
                        # Both empty: result is empty
                        sql_expr = "NULL"
                    elif left_is_empty:
                        # Left is empty, right is not false (must be true or non-literal)
                        # {} AND true = {} (empty result)
                        sql_expr = "NULL"
                    elif right_is_empty:
                        # Right is empty, left is not false (must be true or non-literal)
                        # true AND {} = {} (empty result)
                        sql_expr = "NULL"
                    else:
                        # Standard AND: convert operands to boolean and combine
                        # FHIRPath truthiness: strings, numbers, etc. must be converted to boolean
                        left_literal_type = left_metadata.get("literal_type")
                        right_literal_type = right_metadata.get("literal_type")

                        # Only convert non-boolean literals to boolean
                        left_bool = left_fragment.expression
                        right_bool = right_fragment.expression

                        if left_literal_type and left_literal_type != "boolean":
                            left_bool = self._convert_to_boolean(left_fragment.expression, left_literal_type)
                        if right_literal_type and right_literal_type != "boolean":
                            right_bool = self._convert_to_boolean(right_fragment.expression, right_literal_type)

                        sql_expr = self.dialect.generate_logical_combine(
                            left_bool,
                            sql_operator,
                            right_bool
                        )
                else:  # operator_lower == "or"
                    # OR operator: true OR anything = true
                    # Empty collection propagation:
                    # - true OR {} = true (left is true, result is true)
                    # - {} OR true = true (right is true, result is true)
                    # - false OR {} = {} (right is empty, result is empty)
                    # - {} OR false = {} (left is empty, result is empty)
                    # - {} OR {} = {} (both empty, result is empty)
                    if left_is_true_literal:
                        # Short-circuit: true OR anything = true
                        sql_expr = "TRUE"
                        # Clear is_empty_collection since result is a boolean literal
                        left_metadata = dict(left_metadata)
                        left_metadata.pop("is_empty_collection", None)
                        left_fragment = SQLFragment(
                            expression=left_fragment.expression,
                            source_table=left_fragment.source_table,
                            requires_unnest=left_fragment.requires_unnest,
                            is_aggregate=left_fragment.is_aggregate,
                            dependencies=left_fragment.dependencies,
                            metadata=left_metadata
                        )
                    elif right_is_true_literal:
                        # Short-circuit: anything OR true = true
                        sql_expr = "TRUE"
                        # Clear is_empty_collection since result is a boolean literal
                        right_metadata = dict(right_metadata)
                        right_metadata.pop("is_empty_collection", None)
                        right_fragment = SQLFragment(
                            expression=right_fragment.expression,
                            source_table=right_fragment.source_table,
                            requires_unnest=right_fragment.requires_unnest,
                            is_aggregate=right_fragment.is_aggregate,
                            dependencies=right_fragment.dependencies,
                            metadata=right_metadata
                        )
                    elif left_is_empty and right_is_empty:
                        # Both empty: result is empty
                        sql_expr = "NULL"
                    elif left_is_empty:
                        # Left is empty, right is not true (must be false or non-literal)
                        # {} OR false = {} (empty result)
                        sql_expr = "NULL"
                    elif right_is_empty:
                        # Right is empty, left is not true (must be false or non-literal)
                        # false OR {} = {} (empty result)
                        sql_expr = "NULL"
                    else:
                        # Standard OR: convert operands to boolean and combine
                        # FHIRPath truthiness: strings, numbers, etc. must be converted to boolean
                        left_literal_type = left_metadata.get("literal_type")
                        right_literal_type = right_metadata.get("literal_type")

                        # Only convert non-boolean literals to boolean
                        left_bool = left_fragment.expression
                        right_bool = right_fragment.expression

                        if left_literal_type and left_literal_type != "boolean":
                            left_bool = self._convert_to_boolean(left_fragment.expression, left_literal_type)
                        if right_literal_type and right_literal_type != "boolean":
                            right_bool = self._convert_to_boolean(right_fragment.expression, right_literal_type)

                        sql_expr = self.dialect.generate_logical_combine(
                            left_bool,
                            sql_operator,
                            right_bool
                        )
            elif node.operator_type == "logical" and operator_lower == "xor":
                # SP-100-009: XOR operator with empty collection semantics
                # XOR returns true if operands have different boolean values
                # Empty collections are treated as false
                # Truth table with empty collections:
                # - true xor false = true
                # - false xor true = true
                # - true xor true = false
                # - false xor false = false
                # - {} xor true -> false xor true = true (empty is false)
                # - {} xor false -> false xor false = false (empty is false)
                # - true xor {} -> true xor false = true (empty is false)
                # - false xor {} -> false xor false = false (empty is false)
                # - {} xor {} -> false xor false = false (both empty are false)

                left_metadata = getattr(left_fragment, "metadata", {}) or {}
                right_metadata = getattr(right_fragment, "metadata", {}) or {}
                left_is_empty = left_metadata.get("is_empty_collection") is True
                right_is_empty = right_metadata.get("is_empty_collection") is True

                # For XOR, empty collections are treated as false
                if left_is_empty and right_is_empty:
                    # {} xor {} -> false xor false = false
                    sql_expr = "FALSE"
                elif left_is_empty:
                    # {} xor right -> false xor right = NOT right (when right is boolean)
                    # This simplifies to just NOT right since false XOR true = true
                    # But we need to handle the actual XOR logic
                    # false xor right = right (when right is boolean literal)
                    # For non-literal expressions, use COALESCE to treat NULL as FALSE
                    sql_expr = self.dialect.generate_xor(
                        "FALSE",
                        f"COALESCE({right_fragment.expression}, FALSE)"
                    )
                elif right_is_empty:
                    # left xor {} -> left xor false = left (when left is boolean)
                    sql_expr = self.dialect.generate_xor(
                        f"COALESCE({left_fragment.expression}, FALSE)",
                        "FALSE"
                    )
                else:
                    # Standard XOR: use dialect method
                    sql_expr = self.dialect.generate_xor(
                        left_fragment.expression,
                        right_fragment.expression
                    )
            elif node.operator_type == "logical" and operator_lower == "implies":
                # SP-100-010: Implies operator with empty collection semantics
                # a implies b is logically equivalent to (NOT a) OR b
                # Empty collection handling is encapsulated in _build_implies_sql helper

                left_metadata = getattr(left_fragment, "metadata", {}) or {}
                right_metadata = getattr(right_fragment, "metadata", {}) or {}
                left_is_empty = left_metadata.get("is_empty_collection") is True
                right_is_empty = right_metadata.get("is_empty_collection") is True
                left_is_true_literal = (left_metadata.get("is_literal") is True and
                                        left_metadata.get("literal_type") == "boolean" and
                                        str(left_fragment.expression).upper() == "TRUE")
                left_is_false_literal = (left_metadata.get("is_literal") is True and
                                         left_metadata.get("literal_type") == "boolean" and
                                         str(left_fragment.expression).upper() == "FALSE")

                # Build implies SQL using helper method
                sql_expr = self._build_implies_sql(
                    left_sql=left_fragment.expression,
                    left_is_empty=left_is_empty,
                    left_is_true_literal=left_is_true_literal,
                    left_is_false_literal=left_is_false_literal,
                    right_sql=right_fragment.expression,
                    right_is_empty=right_is_empty,
                    right_metadata=right_metadata,
                )
            elif node.operator_type == "comparison":
                left_metadata = getattr(left_fragment, "metadata", {}) or {}
                right_metadata = getattr(right_fragment, "metadata", {}) or {}
                left_is_collection = left_metadata.get("is_collection") is True
                right_is_collection = right_metadata.get("is_collection") is True
                left_is_empty = left_metadata.get("is_empty_collection") is True
                right_is_empty = right_metadata.get("is_empty_collection") is True

                # SP-103-007: Validate that comparison operators (<, >, <=, >=) are not used on booleans
                # According to FHIRPath spec, only = and != are allowed for boolean comparisons
                comparison_operators = {"<", ">", "<=", ">="}
                if operator_lower in comparison_operators:
                    left_literal_type = left_metadata.get("literal_type")
                    right_literal_type = right_metadata.get("literal_type")
                    if left_literal_type == "boolean" or right_literal_type == "boolean":
                        from ..exceptions import FHIRPathEvaluationError
                        raise FHIRPathEvaluationError(
                            f"Comparison operator '{operator_lower}' cannot be used with boolean values. "
                            f"Only equality operators (=, !=) are supported for boolean comparisons."
                        )

                # SP-100-003: Handle empty collections in comparisons
                # SP-103-007: Comparisons with empty collections return empty collections
                # According to FHIRPath spec, comparisons involving empty collections
                # should return empty collections (not FALSE)
                # {} = 5 -> {}, {} = {} -> {}, 5 = {} -> {}
                if left_is_empty or right_is_empty:
                    # Return NULL to represent empty collection result
                    # This will be filtered out in the final result
                    sql_expr = "NULL"
                # SP-110-FIX-012: Handle DateTime Type Strictness in comparisons
                # According to FHIRPath spec, comparisons between different temporal types
                # (date, datetime, time) or different precisions should return empty collection.
                # Examples:
                #   @2012-04-15 = @2012-04-15T10:00:00 -> {} (date vs datetime)
                #   @T10:30 >= @T10:30:00 -> {} (time minute vs time second precision)
                #   @2012-04-15 = @2012-04-15 -> true (same type, same precision)
                elif self._is_temporal_type_mismatch(left_metadata, right_metadata):
                    # Return NULL to represent empty collection result
                    # This will be filtered out in the final result
                    sql_expr = "NULL"
                # SP-110-001: Handle quantity unit conversion for comparisons
                # When comparing quantities with different units (e.g., "7 days = 1 'wk'"),
                # normalize units to canonical form before comparison
                elif (left_metadata.get("literal_type") == "quantity" and
                      right_metadata.get("literal_type") == "quantity"):
                    sql_expr = self._generate_quantity_comparison(
                        left_fragment, right_fragment, sql_operator, node
                    )
                # SP-110-XXX: Handle Quantity literal vs JSON Quantity field comparison
                # When comparing a Quantity literal (e.g., "185 '[lb_av]'") with a
                # Quantity field (e.g., Observation.value), extract the numeric .value
                # from the JSON for comparison.
                elif (left_metadata.get("literal_type") == "quantity" and
                      right_metadata.get("is_json_string") is True):
                    # Left is Quantity literal, right is JSON field - extract .value from JSON
                    sql_expr = self._generate_quantity_field_comparison(
                        left_fragment, right_fragment, sql_operator, is_left_literal=True
                    )
                elif (right_metadata.get("literal_type") == "quantity" and
                      left_metadata.get("is_json_string") is True):
                    # Right is Quantity literal, left is JSON field - extract .value from JSON
                    sql_expr = self._generate_quantity_field_comparison(
                        right_fragment, left_fragment, sql_operator, is_left_literal=False
                    )
                elif operator_lower in {"=", "!="} and (left_is_collection or right_is_collection):
                    sql_expr = self._generate_collection_comparison(
                        left_fragment.expression,
                        right_fragment.expression,
                        sql_operator
                    )
                elif operator_lower in {"~", "!~"}:
                    # Equivalence operator: use proper equivalence logic
                    sql_expr = self._generate_equivalence_sql(
                        left_fragment.expression,
                        right_fragment.expression,
                        node.children[0],
                        node.children[1],
                        is_negated=(operator_lower == "!~")
                    )
                else:
                    # Apply type casting for JSON-extracted strings compared to typed literals
                    left_expr = left_fragment.expression
                    right_expr = right_fragment.expression

                    # Check if we need to cast JSON string to match literal type
                    left_is_json = left_metadata.get("is_json_string") is True
                    right_is_json = right_metadata.get("is_json_string") is True
                    left_is_literal = left_metadata.get("is_literal") is True
                    right_is_literal = right_metadata.get("is_literal") is True
                    left_literal_type = left_metadata.get("literal_type")
                    right_literal_type = right_metadata.get("literal_type")

                    # SP-103-004: Handle comparison of numeric JSON values with string literals
                    # When comparing a path ending in .value (which should be numeric) with a
                    # string literal, we need to cast to numeric type first to ensure proper
                    # type validation. If the string literal is not a valid number, this will
                    # cause a SQL execution error as expected by FHIRPath semantics.
                    #
                    # SP-110-011: Don't apply numeric cast when in lambda context (select(), where(), etc.)
                    # When inside a lambda, the current_table points to enum_table.value which contains
                    # the actual JSON element, and we should determine the type from the content,
                    # not from the field name pattern. For example, telecom.value is a string,
                    # not a numeric type.

                    # Check if we're in a lambda context (current_table starts with "enum_table")
                    is_in_lambda_context = self.context.current_table.startswith("enum_table")

                    # Check if left is JSON numeric value and right is string literal
                    if (left_is_json and right_is_literal and
                        right_literal_type == "string" and
                        self._is_numeric_value_field(left_metadata.get("source_path", "")) and
                        not is_in_lambda_context):
                        # Try strict cast to DECIMAL - will error if right is not numeric
                        left_expr = self.dialect.strict_cast_to_decimal(left_expr)

                    # Check if right is JSON numeric value and left is string literal
                    elif (right_is_json and left_is_literal and
                          left_literal_type == "string" and
                          self._is_numeric_value_field(right_metadata.get("source_path", "")) and
                          not is_in_lambda_context):
                        # Try strict cast to DECIMAL - will error if left is not numeric
                        right_expr = self.dialect.strict_cast_to_decimal(right_expr)

                    else:
                        # Standard safe casting for non-error cases
                        # Cast left JSON string to match right literal type
                        if left_is_json and right_is_literal and right_literal_type:
                            left_expr = self._apply_safe_cast_for_type(
                                left_expr, right_literal_type
                            )

                        # Cast right JSON string to match left literal type
                        if right_is_json and left_is_literal and left_literal_type:
                            right_expr = self._apply_safe_cast_for_type(
                                right_expr, left_literal_type
                            )

                    # SP-022-010: Handle datetime function comparisons
                    # When comparing a datetime function (today(), now(), timeOfDay())
                    # with a JSON-extracted field, cast the JSON value to match
                    left_datetime_type = self._get_datetime_function_type(left_fragment)
                    right_datetime_type = self._get_datetime_function_type(right_fragment)

                    if right_datetime_type and self._is_json_extraction(left_fragment):
                        # Right is datetime function, left is JSON extraction
                        left_expr = self._apply_safe_cast_for_type(
                            left_expr, right_datetime_type
                        )
                    elif left_datetime_type and self._is_json_extraction(right_fragment):
                        # Left is datetime function, right is JSON extraction
                        right_expr = self._apply_safe_cast_for_type(
                            right_expr, left_datetime_type
                        )

                    sql_expr = self.dialect.generate_comparison(
                        left_expr,
                        sql_operator,
                        right_expr
                    )
            else:
                if operator_lower in {"+", "-", "*", "/", "div", "mod"}:
                    sql_expr = self._generate_arithmetic_sql(
                        operator_lower,
                        left_fragment,
                        right_fragment,
                        node.children[0],
                        node.children[1],
                        sql_operator
                    )
                else:
                    # Standard arithmetic expression
                    sql_expr = f"({left_fragment.expression} {sql_operator} {right_fragment.expression})"

        logger.debug(f"Generated binary operator SQL: {sql_expr}")

        # Determine source table (prefer non-literal sources)
        source_table = left_fragment.source_table
        if source_table is None or source_table == "resource":
            source_table = right_fragment.source_table

        # SP-022-017: Comparison and logical operators produce scalar boolean results,
        # not collections that need unnesting. The operands may have required UNNEST
        # (which generates earlier CTEs), but the comparison result itself is a scalar
        # that doesn't need UNNEST processing. Setting requires_unnest=True on the
        # comparison fragment causes incorrect duplicate CTE generation.
        if node.operator_type in ("comparison", "logical"):
            requires_unnest = False
            is_aggregate = left_fragment.is_aggregate or right_fragment.is_aggregate
        else:
            # For arithmetic operators, inherit unnest requirement from operands
            requires_unnest = left_fragment.requires_unnest or right_fragment.requires_unnest
            is_aggregate = left_fragment.is_aggregate or right_fragment.is_aggregate

        # Merge dependencies while preserving order
        dependencies: List[str] = []
        for dependency in (*left_fragment.dependencies, *right_fragment.dependencies):
            if dependency not in dependencies:
                dependencies.append(dependency)

        # Merge metadata from both operands, but for comparison/logical operators,
        # don't copy array-related metadata since the result is a scalar boolean
        if node.operator_type in ("comparison", "logical"):
            # For comparison/logical, only copy non-array metadata
            # SP-108-001: Keep 'function' metadata if present in either operand to allow
            # CTE builder to recognize aggregation is needed for expressions like count() > 5
            metadata = {}
            left_meta = left_fragment.metadata if isinstance(left_fragment.metadata, dict) else {}
            right_meta = right_fragment.metadata if isinstance(right_fragment.metadata, dict) else {}
            # Copy relevant metadata but exclude array-specific keys
            # Note: We keep 'function' metadata to signal CTE builder about aggregate functions
            array_keys = {"array_column", "result_alias", "source_path", "projection_expression",
                          "from_element_column", "unnest_level"}
            # Check if either operand is an aggregate function
            has_function = False
            function_name = None
            for meta in [left_meta, right_meta]:
                if "function" in meta:
                    has_function = True
                    function_name = meta["function"]
                    break

            # SP-110-001: For logical operators (AND/OR), check if we short-circuited to a boolean literal
            # If so, don't copy is_empty_collection from operands since the result is a definite boolean
            did_short_circuit = False
            if node.operator_type == "logical" and operator_lower in ["and", "or"]:
                # Check if we short-circuited (result is TRUE or FALSE literal)
                if sql_expr in ("TRUE", "FALSE"):
                    did_short_circuit = True

            for key, value in left_meta.items():
                if key not in array_keys:
                    # SP-110-001: Don't copy is_empty_collection if we short-circuited
                    if not (did_short_circuit and key == "is_empty_collection"):
                        metadata[key] = value
            for key, value in right_meta.items():
                if key not in array_keys and key not in metadata:
                    # SP-110-001: Don't copy is_empty_collection if we short-circuited
                    if not (did_short_circuit and key == "is_empty_collection"):
                        metadata[key] = value

            # SP-108-001: Mark comparison operators with result_type boolean
            metadata["result_type"] = "boolean"

            # SP-108-001: Mark as comparison if it involves an aggregate function
            # This signals the CTE builder to extract comparison parts from source_expression
            if has_function:
                metadata["is_comparison"] = True
                metadata["aggregate_function"] = function_name
        else:
            # For other operators (arithmetic), use existing metadata merge logic
            metadata = dict(left_fragment.metadata) if isinstance(left_fragment.metadata, dict) else {}
            if isinstance(right_fragment.metadata, dict):
                for key, value in right_fragment.metadata.items():
                    metadata.setdefault(key, value)

            # If this operation requires unnest but metadata is missing array_column,
            # try to inherit from either operand (prefer left operand)
            if requires_unnest and "array_column" not in metadata:
                left_meta = left_fragment.metadata if isinstance(left_fragment.metadata, dict) else {}
                right_meta = right_fragment.metadata if isinstance(right_fragment.metadata, dict) else {}

                if "array_column" in left_meta:
                    metadata["array_column"] = left_meta["array_column"]
                elif "array_column" in right_meta:
                    metadata["array_column"] = right_meta["array_column"]

        return SQLFragment(
            expression=sql_expr,
            source_table=source_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=dependencies,
            metadata=metadata
        )

    def _translate_union_chain(self, node: OperatorNode) -> SQLFragment:
        """Translate a chain of union operators with linear SQL growth.

        SP-022-013: Union chains like (1|2|3|4) parse as nested UnionExpressions.
        The old implementation visited each child, which caused each level to duplicate
        the SQL 6+ times in CASE WHEN statements, resulting in exponential growth
        (~10x per element). This led to OOM errors for unions with more than 5 elements.

        This method solves the problem by:
        1. Collecting all operands from the AST before any translation
        2. Translating each operand exactly once
        3. Building a single SQL expression that combines all elements linearly

        SP-100-007: Save and restore context for each operand to prevent path pollution.
        When translating union operands like (given | family), each operand must be
        evaluated from the same base context, not accumulating path modifications.

        Args:
            node: The top-level OperatorNode for the union chain

        Returns:
            SQLFragment containing the union SQL with O(N) size for N operands

        Example:
            For expression (1|2|3):
            - Old: 13,454 chars (exponential growth)
            - New: ~800 chars (linear growth)
        """
        # Collect all operands by walking the AST (not translated SQL)
        operand_nodes = self._collect_union_operands(node)
        logger.debug("Collected %d union operands from chain", len(operand_nodes))

        # SP-100-007: Save context state before translating operands
        # This prevents path pollution where each operand accumulates
        # the path modifications from previous operands.
        saved_path = self.context.parent_path.copy()
        saved_table = self.context.current_table

        # Translate each operand exactly once
        operand_fragments: List[SQLFragment] = []
        for operand_node in operand_nodes:
            # SP-100-007: Restore context before each translation
            # Each operand starts from the same base context
            self.context.parent_path = saved_path.copy()
            self.context.current_table = saved_table

            fragment = self.visit(operand_node)
            operand_fragments.append(fragment)

        # SP-100-007: Restore context after all translations
        # The final context should reflect the original state before union processing
        self.context.parent_path = saved_path
        self.context.current_table = saved_table

        # Handle degenerate cases
        if len(operand_fragments) == 0:
            return SQLFragment(
                expression="NULL",
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=[],
                metadata={"operator": "union", "is_collection": True}
            )

        if len(operand_fragments) == 1:
            # Single operand: normalize to array
            single_fragment = operand_fragments[0]
            normalized = self._normalize_collection_expression(single_fragment.expression)
            return SQLFragment(
                expression=normalized,
                source_table=single_fragment.source_table,
                requires_unnest=single_fragment.requires_unnest,
                is_aggregate=single_fragment.is_aggregate,
                dependencies=single_fragment.dependencies,
                metadata={"operator": "union", "is_collection": True}
            )

        # Build linear-growth SQL for multiple operands
        union_sql = self._build_linear_union_sql(operand_fragments)

        # Aggregate metadata from all operands
        source_table = self.context.current_table
        requires_unnest = False
        is_aggregate = False
        dependencies: List[str] = []

        # SP-110-XXX: Detect element type if all operands have same literal_type
        # This enables sort() to use correct type casting (VARCHAR for strings, INTEGER for integers)
        element_type: Optional[str] = None
        first_type: Optional[str] = None

        for fragment in operand_fragments:
            if fragment.source_table and fragment.source_table != "resource":
                source_table = fragment.source_table
            requires_unnest = requires_unnest or fragment.requires_unnest
            is_aggregate = is_aggregate or fragment.is_aggregate
            for dep in fragment.dependencies:
                if dep not in dependencies:
                    dependencies.append(dep)

            # Check literal_type to determine element type
            literal_type = fragment.metadata.get("literal_type") if fragment.metadata else None
            if literal_type in ("string", "integer", "decimal"):
                if first_type is None:
                    first_type = literal_type
                    element_type = literal_type
                elif literal_type != first_type:
                    element_type = None

        return SQLFragment(
            expression=union_sql,
            source_table=source_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=dependencies,
            metadata={"operator": "union", "operator_text": node.text, "is_collection": True, "element_type": element_type}
        )

    def _collect_union_operands(self, node: FHIRPathASTNode) -> List[FHIRPathASTNode]:
        """Recursively collect all operands from a union chain.

        For expression (1|2|3|4) which parses as (((1|2)|3)|4), this method
        returns [node_1, node_2, node_3, node_4] in order.

        Args:
            node: A FHIRPath AST node (may or may not be a union operator)

        Returns:
            List of non-union operand nodes in left-to-right order
        """
        # Check if this is a union operator
        is_union = False
        if isinstance(node, OperatorNode):
            is_union = node.operator_type == "union" or node.operator in {"|", "union"}
        elif hasattr(node, 'node_type') and node.node_type == "UnionExpression":
            is_union = True

        if not is_union:
            # Base case: not a union, return this node as an operand
            return [node]

        # Recursive case: collect operands from both children
        operands: List[FHIRPathASTNode] = []
        if hasattr(node, 'children') and len(node.children) >= 2:
            # Left child comes first (preserves order)
            operands.extend(self._collect_union_operands(node.children[0]))
            operands.extend(self._collect_union_operands(node.children[1]))

        return operands

    def _build_linear_union_sql(self, fragments: List[SQLFragment]) -> str:
        """Build SQL that unions multiple fragments with O(N) size.

        Uses UNION ALL with SELECT statements to combine all values while
        preserving order. Each fragment's value is normalized to handle
        scalars, arrays, and NULLs correctly.

        Args:
            fragments: List of SQLFragment objects to union

        Returns:
            SQL string that combines all fragments into a single JSON array
        """
        # Build individual SELECT statements for each operand
        select_statements: List[str] = []
        value_alias = "union_val"
        source_alias = "union_src"
        index_alias = "union_idx"

        for src_idx, fragment in enumerate(fragments):
            expr = fragment.expression
            normalized = self._normalize_collection_expression(expr)

            # Enumerate the array elements with their position
            enumeration = self.dialect.enumerate_json_array(
                normalized, value_alias, index_alias
            )

            # Add source index to maintain order across operands
            select_statements.append(
                f"SELECT {value_alias}, {src_idx} AS {source_alias}, {index_alias} "
                f"FROM ({enumeration}) AS operand_{src_idx}"
            )

        # Combine all operands with UNION ALL
        combined_rows = " UNION ALL ".join(select_statements)

        # Aggregate into final JSON array, ordered by source then index
        aggregate_expr = self.dialect.aggregate_to_json_array(
            f"{value_alias} ORDER BY {source_alias}, {index_alias}"
        )

        empty_array = self.dialect.empty_json_array()

        # Wrap in COALESCE to return empty array if all operands are NULL/empty
        return f"(COALESCE((SELECT {aggregate_expr} FROM ({combined_rows}) AS union_combined), {empty_array}))"

    def _translate_union_operator(
        self,
        node: OperatorNode,
        left_fragment: SQLFragment,
        right_fragment: SQLFragment,
    ) -> SQLFragment:
        """Translate union (|) operator to SQL.

        NOTE: This method is deprecated for chain handling. Union operators are now
        intercepted before child translation in _translate_binary_operator, and the
        _translate_union_chain method is used instead. This method is kept for
        potential direct calls but should not be reached in normal execution paths.
        """
        logger.debug("Translating union operator with operands: %s and %s",
                     left_fragment.expression, right_fragment.expression)

        left_expression = left_fragment.expression
        right_expression = right_fragment.expression

        normalized_left = self._normalize_collection_expression(left_expression)
        normalized_right = self._normalize_collection_expression(right_expression)

        union_sql = self._compose_union_expression(
            left_expression,
            right_expression,
            normalized_left,
            normalized_right
        )

        source_table = left_fragment.source_table
        if not source_table or source_table == "resource":
            source_table = right_fragment.source_table or self.context.current_table

        requires_unnest = left_fragment.requires_unnest or right_fragment.requires_unnest
        is_aggregate = left_fragment.is_aggregate or right_fragment.is_aggregate

        dependencies: List[str] = []
        for dependency in (*left_fragment.dependencies, *right_fragment.dependencies):
            if dependency not in dependencies:
                dependencies.append(dependency)

        metadata = dict(left_fragment.metadata) if isinstance(left_fragment.metadata, dict) else {}
        if isinstance(right_fragment.metadata, dict):
            for key, value in right_fragment.metadata.items():
                metadata.setdefault(key, value)
        metadata["operator"] = "union"
        metadata["operator_text"] = node.text
        metadata["is_collection"] = True

        return SQLFragment(
            expression=union_sql,
            source_table=source_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=dependencies,
            metadata=metadata
        )

    def _normalize_collection_expression(self, expression: str) -> str:
        """Normalize expression to JSON array, preserving NULL semantics.

        SP-108-003: Now uses dialect methods that properly handle scalar values.
        The dialect's is_json_array() and wrap_json_array() use to_json() which
        converts all types (including VARCHAR from json_extract_string) to JSON format.
        """
        is_array_predicate = self.dialect.is_json_array(expression)
        wrapped_scalar = self.dialect.wrap_json_array(expression)

        return (
            "("
            "CASE "
            f"WHEN {expression} IS NULL THEN NULL "
            f"WHEN {is_array_predicate} THEN {expression} "
            f"ELSE {wrapped_scalar} "
            "END"
            ")"
        )

    def _is_simple_column_reference(self, expression: Optional[str]) -> bool:
        """Check if an expression is a simple column reference.

        A simple column reference:
        - Contains only alphanumeric characters and underscores
        - Does not contain operators, parentheses, brackets, or function calls
        - Typically ends with _item (from UNNEST) or _result (from CTE outputs)

        Args:
            expression: The SQL expression to check

        Returns:
            True if the expression is a simple column reference, False otherwise
        """
        if not expression:
            return False

        # Remove leading/trailing whitespace
        expr = expression.strip()

        # Check for SQL operators and function calls (indicates complex expression)
        sql_operators = '()[]{}+-*/%=<>!&|^~'
        if any(char in expr for char in sql_operators):
            return False

        # Check for SQL keywords (indicates function call or complex expression)
        sql_keywords = {'SELECT', 'FROM', 'WHERE', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
                        'CAST', 'COALESCE', 'NULLIF', 'EXISTS', 'IN', 'LIKE', 'BETWEEN'}
        # Only check if the word appears as a whole token (avoid false positives in column names)
        tokens = set(re.findall(r'\b\w+\b', expr.upper()))
        if not tokens.isdisjoint(sql_keywords):
            return False

        # At this point, it's a simple identifier
        # Optionally check for common CTE column suffixes
        return expr.endswith('_item') or expr.endswith('_result') or '_' in expr

    def _generate_collection_comparison(self, left_expr: str, right_expr: str, sql_operator: str) -> str:
        """Generate SQL comparison between two collection expressions."""
        normalized_left = self._normalize_collection_expression(left_expr)
        normalized_right = self._normalize_collection_expression(right_expr)
        serialized_left = self.dialect.serialize_json_value(normalized_left)
        serialized_right = self.dialect.serialize_json_value(normalized_right)
        return f"({serialized_left} {sql_operator} {serialized_right})"

    def _generate_quantity_comparison(
        self,
        left_fragment: SQLFragment,
        right_fragment: SQLFragment,
        sql_operator: str,
        node: OperatorNode,
    ) -> str:
        """Generate SQL comparison between two quantity literals with unit normalization.

        SP-110-001: Handle quantity comparisons with unit conversion.
        When comparing quantities with different but compatible units (e.g., "7 days = 1 'wk'"),
        normalize both quantities to a common unit before comparison.

        This supports:
        - Temporal units: days <-> weeks, hours <-> days, etc.
        - UCUM canonical units for medical quantities
        - Direct value comparison when units are the same

        Args:
            left_fragment: Left operand SQL fragment (quantity literal)
            right_fragment: Right operand SQL fragment (quantity literal)
            sql_operator: SQL comparison operator (=, !=, <, >, <=, >=)
            node: Original operator node for accessing child nodes

        Returns:
            SQL expression for comparing quantities with normalized units
        """
        left_metadata = getattr(left_fragment, "metadata", {}) or {}
        right_metadata = getattr(right_fragment, "metadata", {}) or {}

        # Extract quantity information from metadata
        left_value = left_metadata.get("quantity_value")
        left_unit = left_metadata.get("quantity_unit")
        right_value = right_metadata.get("quantity_value")
        right_unit = right_metadata.get("quantity_unit")

        # Parse quantity values as Decimals
        try:
            left_amount = Decimal(str(left_value)) if left_value else None
            right_amount = Decimal(str(right_value)) if right_value else None
        except (InvalidOperation, TypeError):
            # If we can't parse as Decimal, fall back to simple string comparison
            return f"({left_fragment.expression} {sql_operator} {right_fragment.expression})"

        if left_amount is None or right_amount is None:
            # Fall back to simple comparison if we can't extract values
            return f"({left_fragment.expression} {sql_operator} {right_fragment.expression})"

        # Normalize units to canonical form
        left_unit_normalized = self._normalize_quantity_unit(left_unit) if left_unit else None
        right_unit_normalized = self._normalize_quantity_unit(right_unit) if right_unit else None

        # Check if units are compatible (both temporal or both canonicalizable to same unit)
        if left_unit_normalized and right_unit_normalized and left_unit_normalized == right_unit_normalized:
            # Units are the same after normalization - compare values directly
            return f"({left_amount} {sql_operator} {right_amount})"

        # Handle temporal unit conversions (days <-> weeks, hours <-> days, etc.)
        temporal_units = {
            "year": 365,  # Approximate
            "month": 30,   # Approximate
            "week": 7,
            "day": 1,
            "hour": 1/24,
            "minute": 1/(24*60),
            "second": 1/(24*60*60),
        }

        if (left_unit_normalized in temporal_units and
            right_unit_normalized in temporal_units):
            # Convert both to days for comparison
            left_in_days = float(left_amount) * temporal_units[left_unit_normalized]
            right_in_days = float(right_amount) * temporal_units[right_unit_normalized]
            return f"({left_in_days} {sql_operator} {right_in_days})"

        # For non-temporal quantities, we can't do unit conversion without UCUM
        # Fall back to string comparison of the JSON representations
        return f"({left_fragment.expression} {sql_operator} {right_fragment.expression})"

    def _generate_quantity_field_comparison(
        self,
        quantity_literal_fragment: SQLFragment,
        json_field_fragment: SQLFragment,
        sql_operator: str,
        is_left_literal: bool,
    ) -> str:
        """Generate SQL comparison between a Quantity literal and a JSON Quantity field.

        SP-110-XXX: Handle Quantity literal vs JSON Quantity field comparisons.
        When comparing a Quantity literal (e.g., "185 '[lb_av]'") with a Quantity field
        (e.g., Observation.value), extract the numeric .value field from the JSON
        for numeric comparison.

        Args:
            quantity_literal_fragment: The Quantity literal fragment (has literal_type='quantity')
            json_field_fragment: The JSON field fragment (has is_json_string=true)
            sql_operator: SQL comparison operator (=, !=, <, >, <=, >=)
            is_left_literal: True if literal is on left, False if literal is on right

        Returns:
            SQL expression comparing the numeric .value extracted from JSON with the literal value
        """
        quantity_metadata = getattr(quantity_literal_fragment, "metadata", {}) or {}
        json_metadata = getattr(json_field_fragment, "metadata", {}) or {}

        # Extract quantity literal value
        literal_value = quantity_metadata.get("quantity_value")
        literal_unit = quantity_metadata.get("quantity_unit")

        if literal_value is None:
            # Fall back to simple comparison if we can't extract the literal value
            if is_left_literal:
                return f"({quantity_literal_fragment.expression} {sql_operator} {json_field_fragment.expression})"
            else:
                return f"({json_field_fragment.expression} {sql_operator} {quantity_literal_fragment.expression})"

        # Get the JSON field expression and check if it's a polymorphic property
        json_expr = json_field_fragment.expression
        source_path = json_metadata.get("source_path", "")

        # SP-110-FIX: Detect polymorphic properties and use the specific Quantity variant
        # When the source_path is a polymorphic property like $.value, the COALESCE might
        # return a non-Quantity variant (e.g., valuePeriod) when valueQuantity is NULL.
        # We need to directly extract from valueQuantity instead of using the COALESCE result.
        if source_path and self._is_polymorphic_path(source_path):
            # Replace the polymorphic base with the Quantity-specific variant
            # e.g., $.value -> $.valueQuantity
            quantity_path = source_path.replace('.value', '.valueQuantity')

            # SP-110-FIX-2: Extract the numeric value directly from valueQuantity
            # Instead of using the COALESCE result, we directly extract from valueQuantity
            # and then extract the .value field and cast to DECIMAL.
            # This avoids the polymorphic COALESCE that might return a non-Quantity variant.
            # SP-110-FIX-3: Use TRY_CAST to handle potential type conversion issues
            # The JSON value might be stored as a string in some cases, so we use
            # TRY_CAST to DECIMAL which returns NULL for invalid conversions instead of errors.
            value_extract = f"TRY_CAST(json_extract(json_extract({self.context.current_table}, '{quantity_path}'), '$.value') AS DECIMAL)"

            # Build the comparison: extracted_value <op> literal_value
            if is_left_literal:
                # literal <op> field -> literal_value <op> extracted_value
                sql_expr = f"({literal_value} {sql_operator} {value_extract})"
            else:
                # field <op> literal -> extracted_value <op> literal_value
                sql_expr = f"({value_extract} {sql_operator} {literal_value})"

            return sql_expr

        # Extract the .value field from the Quantity JSON
        # Quantity JSON structure: {"value": 185, "unit": "[lb_av]", "system": "...", "code": "..."}
        # We need to extract the 'value' field and cast it to DECIMAL for comparison
        # The json_expr is a JSON string (from json_extract_string or COALESCE thereof)
        # For DuckDB: json_extract(CAST(json_expr AS JSON), '$.value')::DECIMAL
        # For PostgreSQL: (json_expr::JSON->>'value')::DECIMAL
        value_extract = self.dialect.extract_json_decimal_from_string(json_expr)

        # Build the comparison: extracted_value <op> literal_value
        if is_left_literal:
            # literal <op> field -> literal_value <op> extracted_value
            sql_expr = f"({literal_value} {sql_operator} {value_extract})"
        else:
            # field <op> literal -> extracted_value <op> literal_value
            sql_expr = f"({value_extract} {sql_operator} {literal_value})"

        return sql_expr

    def _apply_safe_cast_for_type(self, expression: str, target_type: str) -> str:
        """Apply safe type casting to an expression based on target literal type.

        This method is used when comparing JSON-extracted VARCHAR values with
        typed literals. It applies the appropriate dialect-specific safe cast
        to convert the VARCHAR to the target type, returning NULL for invalid
        values instead of raising errors.

        Args:
            expression: The SQL expression to cast (typically a JSON extraction)
            target_type: The target literal type (integer, decimal, date, datetime, boolean)

        Returns:
            The expression wrapped with appropriate safe cast, or unchanged if no
            cast is needed (e.g., for string types)

        Example:
            >>> translator._apply_safe_cast_for_type("json_extract(...)", "decimal")
            "TRY_CAST(json_extract(...) AS DECIMAL)"  # DuckDB
        """
        if target_type == "integer":
            return self.dialect.safe_cast_to_integer(expression)
        elif target_type == "decimal":
            return self.dialect.safe_cast_to_decimal(expression)
        elif target_type == "date":
            return self.dialect.safe_cast_to_date(expression)
        elif target_type in ("datetime", "instant"):
            return self.dialect.safe_cast_to_timestamp(expression)
        elif target_type == "boolean":
            return self.dialect.safe_cast_to_boolean(expression)
        elif target_type == "time":
            # Time comparisons - cast to timestamp for comparison
            return self.dialect.safe_cast_to_timestamp(expression)
        elif target_type == "string":
            # SP-022-007: For JSON values compared to string literals, cast to VARCHAR
            # The expression is already a JSON string from json_extract_string, we just need
            # to cast it to VARCHAR so DuckDB doesn't try to parse the string literal as JSON
            return f"CAST({expression} AS VARCHAR)"
        else:
            # For other types, no casting needed
            return expression

    def _get_datetime_function_type(self, fragment: SQLFragment) -> Optional[str]:
        """Detect if a fragment is from a datetime function and return its target type.

        SP-022-010: When comparing FHIR date/time fields with datetime functions
        like today() or now(), we need to cast the JSON-extracted VARCHAR to the
        appropriate type. This method identifies fragments from datetime functions.

        Args:
            fragment: SQLFragment to check for datetime function metadata

        Returns:
            The target type for casting ("date", "datetime", or "time"), or None
            if the fragment is not from a datetime function.

        Example:
            >>> fragment = translator._translate_today(node)
            >>> translator._get_datetime_function_type(fragment)
            'date'
        """
        if fragment.metadata and isinstance(fragment.metadata, dict):
            fhir_type = fragment.metadata.get("fhir_type")
            if fhir_type == "Date":
                return "date"
            elif fhir_type == "DateTime":
                return "datetime"
            elif fhir_type == "Time":
                return "time"
        return None

    def _is_numeric_value_field(self, source_path: str) -> bool:
        """Check if .value field is on a numeric primitive type.

        FHIR uses .value for many primitive types, but only numeric types
        (valueQuantity, valueInteger, valueDecimal) should be cast to DECIMAL.
        Non-numeric types (valueString, valuePeriod, etc.) should not be cast.

        Args:
            source_path: FHIRPath source path (e.g., "Observation.value.value")

        Returns:
            True if .value is on a numeric primitive, False otherwise.
        """
        if not source_path or not source_path.endswith(".value"):
            return False

        # Use string slicing to correctly remove the trailing ".value" suffix.
        # rstrip() would remove characters, not the suffix string.
        # Slicing approach: source_path[:-6] removes the last 6 characters (".value")
        if source_path.endswith(".value"):
            parent_path = source_path[:-6]  # Remove ".value" (6 characters)
        else:
            return False

        # Get the parent field name (the field before the last .value)
        path_parts = parent_path.split(".")
        if not path_parts:
            return False

        parent_field = path_parts[-1]

        # List of non-numeric value fields that should NOT be cast to DECIMAL
        # Includes specific valueX fields and the generic 'value' field itself
        non_numeric_primitives = {
            "valuePeriod", "valueString", "valueUri", "valueBoolean",
            "valueBase64Binary", "valueCode", "valueDate", "valueDateTime",
            "valueTime", "valueId", "valueOid", "valueUuid", "valueCanonical",
            "valueUrl", "valueMarkdown", "valueXhtml", "valueAttachment",
            "valueCodeableConcept", "valueCoding", "valueQuantity",  # Quantity has its own unit/value structure
            "valueRange", "valueRatio", "valueSampledData", "valueSignature",
            "valueTiming", "valueHumanName", "valueAddress", "valueContactPoint",
            "valueReference", "valueAnnotation",
            "value"  # Generic value field - when used as a standalone field, it's a choice type
        }

        # If parent is in non-numeric list, don't cast
        if parent_field in non_numeric_primitives:
            return False

        # Default to True for ambiguous cases (conservative approach)
        # This handles numeric-specific fields like valueQuantity, valueInteger, etc.
        return True

    def _is_polymorphic_path(self, source_path: str) -> bool:
        """Check if a source path contains a polymorphic property.

        SP-110-FIX: Detect polymorphic properties like 'value', 'onset', 'deceased', etc.
        These properties have [x] suffix in FHIR and can be multiple types (e.g.,
        valueQuantity, valueString, valuePeriod). When comparing with typed literals,
        we need to use the specific variant instead of the COALESCE of all variants.

        Args:
            source_path: FHIRPath source path (e.g., "$.value", "Observation.value")

        Returns:
            True if the path contains a polymorphic property, False otherwise.
        """
        if not source_path:
            return False

        # Normalize the path and extract components
        # Remove leading "$" if present
        normalized = source_path.lstrip('$.')

        # Get the last component (the field being accessed)
        components = normalized.split('.')
        if not components:
            return False

        # Check if any component is a known polymorphic property
        from ..types.fhir_types import POLYMORPHIC_PROPERTIES
        for component in components:
            if component in POLYMORPHIC_PROPERTIES:
                return True

        return False

    def _is_json_extraction(self, fragment: SQLFragment) -> bool:
        """Detect if a fragment represents a JSON extraction that yields VARCHAR.

        SP-022-010: JSON-extracted values from FHIR resources are VARCHAR strings.
        When comparing these with native DATE/TIMESTAMP types from functions like
        today() or now(), we need to cast the JSON value appropriately.

        Args:
            fragment: SQLFragment to check for JSON extraction

        Returns:
            True if the fragment is a JSON extraction, False otherwise.

        Example:
            >>> fragment = translator._translate_path_expression(node)  # Patient.birthDate
            >>> translator._is_json_extraction(fragment)
            True
        """
        # Check metadata for explicit JSON string marker
        if fragment.metadata and isinstance(fragment.metadata, dict):
            if fragment.metadata.get("is_json_string") is True:
                return True

        # Check expression patterns for JSON extraction functions
        expr_lower = fragment.expression.lower()
        json_patterns = [
            "json_extract",      # DuckDB json_extract_string
            "jsonb_extract",     # PostgreSQL jsonb_extract_path_text
            "->",                # PostgreSQL JSON operators
            "->>",               # PostgreSQL JSON text extraction
        ]

        for pattern in json_patterns:
            if pattern in expr_lower:
                return True

        return False

    def _is_string_operand(self, ast_node: FHIRPathASTNode) -> bool:
        """Check if an AST node represents a string type operand.

        Used to determine whether to apply case-insensitive comparison for
        equivalence operators (~, !~).

        Args:
            ast_node: The AST node to check

        Returns:
            True if the operand is a string type, False otherwise
        """
        # Check for EnhancedASTNode with text attribute (handles string literals)
        # String literals are enclosed in single or double quotes in the AST text
        if hasattr(ast_node, 'text') and ast_node.text:
            text = ast_node.text.strip()
            if (text.startswith("'") and text.endswith("'")) or \
               (text.startswith('"') and text.endswith('"')):
                return True

        # Check children for string literals (handles wrapper nodes like TermExpression)
        if hasattr(ast_node, 'children') and ast_node.children:
            for child in ast_node.children:
                if self._is_string_operand(child):
                    return True

        # Check if it's a LiteralNode (for backwards compatibility)
        if isinstance(ast_node, LiteralNode):
            return getattr(ast_node, "literal_type", None) == "string"

        # For function calls, check if it returns a string
        if isinstance(ast_node, FunctionCallNode):
            string_functions = {
                "tostring", "lower", "upper", "trim", "substring",
                "replace", "replaceMatches", "encode", "decode",
                "combine", "distinct", "isdistinct"
            }
            return ast_node.function_name.lower() in string_functions

        return False

    def _is_decimal_operand(self, ast_node: FHIRPathASTNode) -> bool:
        """Check if an AST node represents a decimal/numeric type operand.

        SP-110-FIX-013: Used to determine whether to apply tolerance-based
        comparison for equivalence operators (~, !~) on decimal/quantity types.

        Args:
            ast_node: The AST node to check

        Returns:
            True if the operand is a decimal/numeric type, False otherwise
        """
        # SP-110-FIX-013: Check metadata for quantity literal type
        # This handles quantities that have been converted to JSON literals
        if hasattr(ast_node, 'metadata') and ast_node.metadata:
            literal_type = ast_node.metadata.custom_attributes.get('literal_type') if ast_node.metadata.custom_attributes else None
            if literal_type == 'quantity':
                return True

        # Check for EnhancedASTNode with text attribute (handles decimal literals and functions)
        if hasattr(ast_node, 'text') and ast_node.text:
            text = ast_node.text.strip()
            # Check if it's a decimal literal (contains '.')
            if '.' in text and text.replace('.', '').replace('-', '').isdigit():
                return True
            # SP-110-FIX-013: Check for function calls that produce decimals
            # This handles EnhancedASTNode which stores function names in text
            # Do this BEFORE checking children, to catch wrapper nodes like "toQuantity()"
            if text.endswith('()'):
                function_name = text[:-2].lower()  # Remove "()" and lowercase
                decimal_functions = {"toquantity", "abs", "ceiling", "floor", "truncate",
                                     "exp", "log", "ln", "power", "sqrt"}
                if function_name in decimal_functions:
                    return True

        # Check children for decimal literals (handles wrapper nodes)
        if hasattr(ast_node, 'children') and ast_node.children:
            for child in ast_node.children:
                if self._is_decimal_operand(child):
                    return True

        # Check if it's a LiteralNode (for backwards compatibility)
        if isinstance(ast_node, LiteralNode):
            literal_type = getattr(ast_node, "literal_type", None)
            return literal_type in ("decimal", "integer", "quantity")

        # Check for operator nodes that produce decimal results (arithmetic operators)
        if hasattr(ast_node, 'operator'):
            # Arithmetic operators: +, -, *, /, div, mod
            arithmetic_ops = {'+', '-', '*', '/', 'div', 'mod'}
            if ast_node.operator in arithmetic_ops:
                return True

        # Functions that produce decimals/quantities (for FunctionCallNode)
        if isinstance(ast_node, FunctionCallNode):
            decimal_functions = {"toquantity", "abs", "ceiling", "floor", "truncate",
                                 "exp", "log", "ln", "power", "sqrt"}
            return ast_node.function_name.lower() in decimal_functions

        return False

    def _generate_equivalence_sql(
        self,
        left_expr: str,
        right_expr: str,
        left_node: FHIRPathASTNode,
        right_node: FHIRPathASTNode,
        is_negated: bool = False
    ) -> str:
        """Generate SQL for FHIRPath equivalence operator (~) or not-equivalent (!~).

        Equivalence differs from equality in several ways:
        - For strings: case-insensitive comparison
        - For simple types (integers, decimals, booleans): same as equality
        - For null handling: null ~ null is true, value ~ null is false

        Args:
            left_expr: SQL expression for left operand
            right_expr: SQL expression for right operand
            left_node: AST node for left operand (used for type inference)
            right_node: AST node for right operand (used for type inference)
            is_negated: True for !~ operator, False for ~ operator

        Returns:
            SQL expression implementing equivalence comparison
        """
        operator = "!=" if is_negated else "="

        # SP-110-FIX-013: Check if either operand is a decimal/numeric type for tolerance
        # Check this BEFORE string check, since quantities should use tolerance-based comparison
        left_is_decimal = self._is_decimal_operand(left_node)
        right_is_decimal = self._is_decimal_operand(right_node)

        # Check if either operand is a string type (used if not decimal)
        left_is_string = self._is_string_operand(left_node)
        right_is_string = self._is_string_operand(right_node)

        # SP-110-FIX-013: Decimal/Quantity equivalence takes precedence over string equivalence
        # This handles cases like '1.0'.toQuantity() which might be detected as string due to quotes
        if left_is_decimal or right_is_decimal:
            # SP-110-FIX-013: Decimal/Quantity equivalence: tolerance-based comparison
            # For decimals and quantities, use tolerance to handle floating-point precision
            # FHIRPath specification defines equivalence for decimals as approximately equal
            # Tolerance of 0.01 (2 decimal places) is commonly used for UCUM comparisons

            # SP-110-FIX-013: Check if operands are quantity JSON strings
            # If so, extract the value field for comparison
            def extract_value_if_quantity(expr: str, node: FHIRPathASTNode) -> str:
                """Extract quantity value from JSON string if it's a quantity."""
                # Check if the expression looks like a quantity JSON string
                # Pattern: '{"value": ..., "unit": ..., ...}' (SQL string literal with JSON inside)
                expr_stripped = expr.strip()
                # The expression is a SQL string literal: '{"value": 1.0, ...}'
                # It starts with single quote, then open brace
                starts_with_pattern = expr_stripped.startswith("'{") and '"value"' in expr_stripped[:20]
                has_unit = '"unit"' in expr_stripped
                if starts_with_pattern and has_unit:
                    # This is a quantity JSON string - extract the value
                    return f"CAST(JSON_EXTRACT({expr}, '$.value') AS DECIMAL(18,10))"
                return expr

            left_value_expr = extract_value_if_quantity(left_expr, left_node)
            right_value_expr = extract_value_if_quantity(right_expr, right_node)

            tolerance_expr = f"ABS(({left_value_expr} - {right_value_expr}))"
            if is_negated:
                comparison = f"({tolerance_expr} >= 0.01)"
            else:
                comparison = f"({tolerance_expr} < 0.01)"
        elif left_is_string or right_is_string:
            # String equivalence: case-insensitive comparison
            # Use LOWER() on both operands, casting to string if needed
            left_lower = f"LOWER(CAST({left_expr} AS VARCHAR))"
            right_lower = f"LOWER(CAST({right_expr} AS VARCHAR))"
            comparison = f"({left_lower} {operator} {right_lower})"
        else:
            # Non-string, non-decimal equivalence: same as equality
            comparison = f"({left_expr} {operator} {right_expr})"

        # Handle null semantics for equivalence:
        # null ~ null → true, value ~ null → false, null ~ value → false
        if is_negated:
            # For !~ (not equivalent):
            # null !~ null → false, value !~ null → true, null !~ value → true
            null_handling = f"""(
                CASE
                    WHEN {left_expr} IS NULL AND {right_expr} IS NULL THEN false
                    WHEN {left_expr} IS NULL OR {right_expr} IS NULL THEN true
                    ELSE {comparison}
                END
            )"""
        else:
            # For ~ (equivalent):
            # null ~ null → true, value ~ null → false, null ~ value → false
            null_handling = f"""(
                CASE
                    WHEN {left_expr} IS NULL AND {right_expr} IS NULL THEN true
                    WHEN {left_expr} IS NULL OR {right_expr} IS NULL THEN false
                    ELSE {comparison}
                END
            )"""

        return null_handling

    def _generate_internal_alias(self, prefix: str) -> str:
        """Generate a unique alias for inline set-operation queries."""
        self._internal_alias_counter += 1
        return f"{prefix}_{self._internal_alias_counter}"

    def _extract_collection_source(
        self,
        base_expr: str,
        target_path: Optional[List[str]],
        snapshot: Dict[str, Any],
    ) -> str:
        """Resolve the SQL expression for the collection input."""
        stripped = base_expr.strip()
        if stripped.upper().startswith("SELECT"):
            return base_expr
        if target_path:
            json_path = "$" if not target_path else "$." + ".".join(target_path)
            base_table = snapshot["current_table"]
            current_table = self.context.current_table
            column_expr = self.dialect.extract_json_object(
                column=base_table,
                path=json_path,
            )
            if base_table == current_table:
                return column_expr
            return (
                "("
                f"SELECT {column_expr} "
                f"FROM {base_table} "
                f"WHERE {base_table}.id = {current_table}.id"
                ")"
            )

        # SP-025-003: Handle simple column references from CTEs
        # If base_expr is a simple column name (not a function call or complex expression)
        # and it references a CTE, wrap it in a subquery that includes the CTE
        if not target_path and not any(op in stripped for op in ['(', ')', '+', '-', '*', '/', ' ']):
            # This looks like a simple identifier (column reference)
            # Check if it's from a different table/CTE
            base_table = snapshot["current_table"]
            current_table = self.context.current_table
            if base_table != current_table and not '.' in stripped:
                # Simple column reference from a different table/CTE
                # Wrap it to make the column accessible
                return (
                    "("
                    f"SELECT {stripped} "
                    f"FROM {base_table} "
                    f"WHERE {base_table}.id = {current_table}.id"
                    ")"
                )

        return base_expr

    def _detach_simple_target_fragment(self, collection_expr: str) -> bool:
        """Remove trailing fragment when simple path already evaluated."""
        if not collection_expr:
            return False
        if collection_expr.strip().upper().startswith("SELECT"):
            return False
        if not self.fragments:
            return False
        self.fragments.pop()
        return True

    def _build_distinct_array(self, normalized_expr: str) -> str:
        """Construct SQL that removes duplicates while preserving original order."""
        prefix = self._generate_internal_alias("distinct")
        empty_array = self.dialect.empty_json_array()
        safe_expr = f"COALESCE({normalized_expr}, {empty_array})"

        value_column = f"{prefix}_val"
        index_column = f"{prefix}_idx"
        enum_alias = f"{prefix}_enum"
        rank_column = f"{prefix}_rank"
        dedup_alias = f"{prefix}_dedup"
        ordered_alias = f"{prefix}_ordered"

        enumeration_sql = self.dialect.enumerate_json_array(safe_expr, value_column, index_column)
        serialized_expr = self.dialect.serialize_json_value(f"{enum_alias}.{value_column}")

        ranked_rows = (
            f"SELECT {enum_alias}.{value_column} AS {value_column}, "
            f"{enum_alias}.{index_column} AS {index_column}, "
            f"ROW_NUMBER() OVER ("
            f"PARTITION BY {serialized_expr} "
            f"ORDER BY {enum_alias}.{index_column}"
            f") AS {rank_column} "
            f"FROM ({enumeration_sql}) AS {enum_alias}"
        )

        deduplicated_rows = (
            f"SELECT {value_column}, {index_column} "
            f"FROM ({ranked_rows}) AS {dedup_alias} "
            f"WHERE {rank_column} = 1 "
            f"ORDER BY {index_column}"
        )

        aggregate_expr = self.dialect.aggregate_to_json_array(
            f"{value_column} ORDER BY {index_column}"
        )

        return (
            f"COALESCE("
            f"(SELECT {aggregate_expr} FROM ({deduplicated_rows}) AS {ordered_alias}), "
            f"{empty_array}"
            ")"
        )

    def _add_distinct_to_aggregate_select(self, select_sql: str) -> str:
        """Add DISTINCT to the aggregation in a SELECT statement.

        This handles cases where distinct() chains after select(), combine(), etc.
        The input is a complete SELECT statement with aggregation like:
            SELECT id, resource, json_agg(x ORDER BY idx) as result FROM ... GROUP BY id, resource

        We need to modify it to remove duplicates while preserving order:
            SELECT id, resource, json_agg(x) FROM (
                SELECT DISTINCT ON (x) x ORDER BY x, idx
            ) subq GROUP BY id, resource

        For simple cases without ORDER BY, we can use DISTINCT directly:
            SELECT id, resource, json_agg(DISTINCT x) as result FROM ... GROUP BY id, resource

        SP-105: Fixed ORDER BY issue with DISTINCT aggregates.
        """
        import re

        # SP-105: Use a more robust approach to remove ORDER BY from DISTINCT aggregates
        # The issue is that ORDER BY can appear at any nesting level, and simple regex
        # doesn't handle nested parentheses well. We'll use a recursive approach to find
        # and remove ORDER BY clauses at all nesting levels.

        def remove_order_by_in_aggregates(sql, agg_func):
            """Recursively remove ORDER BY clauses in aggregate functions."""
            pattern = f"{agg_func}\\s*\\("

            # Find all aggregate function calls
            results = []
            pos = 0
            while True:
                match = re.search(pattern, sql[pos:], re.IGNORECASE)
                if not match:
                    break

                func_start = pos + match.start()
                paren_depth = 1
                i = func_start + len(match.group(0))

                # Find the matching closing parenthesis
                while i < len(sql) and paren_depth > 0:
                    if sql[i] == '(':
                        paren_depth += 1
                    elif sql[i] == ')':
                        paren_depth -= 1
                    i += 1

                if paren_depth == 0:
                    func_content = sql[func_start + len(match.group(0)):i-1]

                    # Check if there's an ORDER BY clause in this function
                    # We need to be careful not to remove ORDER BY in nested SELECTs
                    order_by_match = re.search(
                        r'ORDER\s+BY\s+[^)]+(?=\s*\)\s*(?:AS\s+\w+)?$',
                        func_content,
                        re.IGNORECASE
                    )

                    if order_by_match and "SELECT" not in func_content:
                        # Remove the ORDER BY clause
                        new_content = func_content[:order_by_match.start()]
                        new_func = f"{agg_func}({new_content})"

                        # Replace in the SQL
                        sql = sql[:func_start] + new_func + sql[i:]

                        # Update position to continue searching after the replacement
                        pos = func_start + len(new_func)
                        logger.info(
                            f"SP-105: Removed ORDER BY from DISTINCT aggregate: "
                            f"{agg_func}(...{order_by_match.group(0)[:50]}...) -> {new_func[:80]}"
                        )
                    else:
                        pos = i
                else:
                    break

            return sql

        # Try to fix list() with DISTINCT
        if "list(" in select_sql and "DISTINCT" in select_sql:
            # Check if there's an ORDER BY still present
            if "ORDER BY" in select_sql:
                # Try to remove ORDER BY clauses in list() functions
                select_sql = remove_order_by_in_aggregates(select_sql, "list")

        # Try to fix json_agg() with DISTINCT
        if "json_agg(" in select_sql and "DISTINCT" in select_sql:
            if "ORDER BY" in select_sql:
                select_sql = remove_order_by_in_aggregates(select_sql, "json_agg")

        # Try to fix json_group_array() with DISTINCT
        if "json_group_array(" in select_sql and "DISTINCT" in select_sql:
            if "ORDER BY" in select_sql:
                select_sql = remove_order_by_in_aggregates(select_sql, "json_group_array")

        return select_sql

    def _check_select_is_distinct(self, select_sql: str) -> str:
        """Check if a SELECT statement's result is distinct.

        This handles cases where isDistinct() chains after select(), combine(), etc.
        The input is a complete SELECT statement with aggregation. We need to check
        if the aggregated values are all unique.

        Approach: Wrap the SELECT in a subquery and check if
        count(distinct result) = count(result).
        """
        import re

        # Find the result column name (typically "result")
        result_col = "result"  # Default convention

        # Wrap the SELECT in a subquery and check for duplicates
        subquery_alias = self._generate_internal_alias("isdistinct_wrapper")
        distinct_check = (
            f"("
            f"SELECT COUNT(*) = COUNT(DISTINCT {subquery_alias}.{result_col}) "
            f"FROM ({select_sql}) AS {subquery_alias}"
            f")"
        )

        return distinct_check

    def _build_is_distinct_condition(self, normalized_expr: str) -> str:
        """Construct SQL that checks whether a collection contains duplicates."""
        prefix = self._generate_internal_alias("isdistinct")
        empty_array = self.dialect.empty_json_array()
        safe_expr = f"COALESCE({normalized_expr}, {empty_array})"

        value_column = f"{prefix}_val"
        index_column = f"{prefix}_idx"
        enum_alias = f"{prefix}_enum"
        enumeration_sql = self.dialect.enumerate_json_array(safe_expr, value_column, index_column)
        serialized_expr = self.dialect.serialize_json_value(value_column)

        return (
            "(\n"
            "SELECT CASE \n"
            "    WHEN COUNT(*) = 0 THEN TRUE \n"
            f"    WHEN COUNT(*) = COUNT(DISTINCT {serialized_expr}) THEN TRUE \n"
            "    ELSE FALSE \n"
            "END \n"
            f"FROM ({enumeration_sql}) AS {enum_alias}\n"
            ")"
        )

    def _build_intersection_array(self, left_normalized: str, right_normalized: str) -> str:
        """Construct SQL that returns the intersection of two collections."""
        prefix = self._generate_internal_alias("intersect")
        empty_array = self.dialect.empty_json_array()
        safe_left = f"COALESCE({left_normalized}, {empty_array})"
        safe_right = f"COALESCE({right_normalized}, {empty_array})"

        left_value = f"{prefix}_lval"
        left_index = f"{prefix}_lidx"
        right_value = f"{prefix}_rval"
        right_index = f"{prefix}_ridx"
        left_enum_alias = f"{prefix}_lenum"
        right_enum_alias = f"{prefix}_renum"
        rank_column = f"{prefix}_rank"
        key_alias = f"{prefix}_key"
        dedup_alias = f"{prefix}_dedup"
        ordered_alias = f"{prefix}_ordered"

        left_enumeration = self.dialect.enumerate_json_array(safe_left, left_value, left_index)
        right_enumeration = self.dialect.enumerate_json_array(safe_right, right_value, right_index)

        right_serialized = self.dialect.serialize_json_value(f"{right_enum_alias}.{right_value}")
        right_keys = (
            f"SELECT DISTINCT {right_serialized} AS {key_alias} "
            f"FROM ({right_enumeration}) AS {right_enum_alias}"
        )

        left_serialized = self.dialect.serialize_json_value(f"{left_enum_alias}.{left_value}")
        filtered_rows = (
            f"SELECT {left_enum_alias}.{left_value} AS {left_value}, "
            f"{left_enum_alias}.{left_index} AS {left_index}, "
            f"ROW_NUMBER() OVER ("
            f"PARTITION BY {left_serialized} "
            f"ORDER BY {left_enum_alias}.{left_index}"
            f") AS {rank_column} "
            f"FROM ({left_enumeration}) AS {left_enum_alias} "
            f"WHERE {left_serialized} IN ("
            f"SELECT {key_alias} FROM ({right_keys}) AS {prefix}_keys"
            ")"
        )

        deduplicated_rows = (
            f"SELECT {left_value}, {left_index} "
            f"FROM ({filtered_rows}) AS {dedup_alias} "
            f"WHERE {rank_column} = 1 "
            f"ORDER BY {left_index}"
        )

        aggregate_expr = self.dialect.aggregate_to_json_array(
            f"{left_value} ORDER BY {left_index}"
        )

        return (
            f"COALESCE("
            f"(SELECT {aggregate_expr} FROM ({deduplicated_rows}) AS {ordered_alias}), "
            f"{empty_array}"
            ")"
        )

    def _build_exclusion_array(self, left_normalized: str, right_normalized: str) -> str:
        """Construct SQL that removes right-collection values from the left collection.

        Per FHIRPath specification, exclude() does NOT remove duplicates.
        It only removes elements that are present in the other collection.
        """
        prefix = self._generate_internal_alias("exclude")
        empty_array = self.dialect.empty_json_array()
        safe_left = f"COALESCE({left_normalized}, {empty_array})"
        safe_right = f"COALESCE({right_normalized}, {empty_array})"

        left_value = f"{prefix}_lval"
        left_index = f"{prefix}_lidx"
        right_value = f"{prefix}_rval"
        right_index = f"{prefix}_ridx"
        left_enum_alias = f"{prefix}_lenum"
        right_enum_alias = f"{prefix}_renum"
        key_alias = f"{prefix}_key"
        filtered_alias = f"{prefix}_filtered"

        left_enumeration = self.dialect.enumerate_json_array(safe_left, left_value, left_index)
        right_enumeration = self.dialect.enumerate_json_array(safe_right, right_value, right_index)

        right_serialized = self.dialect.serialize_json_value(f"{right_enum_alias}.{right_value}")
        right_keys = (
            f"SELECT DISTINCT {right_serialized} AS {key_alias} "
            f"FROM ({right_enumeration}) AS {right_enum_alias}"
        )

        left_serialized = self.dialect.serialize_json_value(f"{left_enum_alias}.{left_value}")
        filtered_rows = (
            f"SELECT {left_enum_alias}.{left_value} AS {left_value}, "
            f"{left_enum_alias}.{left_index} AS {left_index} "
            f"FROM ({left_enumeration}) AS {left_enum_alias} "
            f"WHERE {left_serialized} NOT IN ("
            f"SELECT {key_alias} FROM ({right_keys}) AS {prefix}_keys"
            f") "
            f"ORDER BY {left_index}"
        )

        aggregate_expr = self.dialect.aggregate_to_json_array(
            f"{left_value} ORDER BY {left_index}"
        )

        return (
            f"COALESCE("
            f"(SELECT {aggregate_expr} FROM ({filtered_rows}) AS {filtered_alias}), "
            f"{empty_array}"
            f")"
        )

    def _build_subset_check(
        self,
        subset_expr: str,
        superset_expr: str,
        subset_source_table: Optional[str] = None,
        superset_source_table: Optional[str] = None,
        normalize_subset: bool = True,
        normalize_superset: bool = True
    ) -> str:
        """Build SQL that checks if subset_expr is a subset of superset_expr.

        Returns TRUE if all elements in subset_expr exist in superset_expr.
        Returns TRUE if subset_expr is empty (empty set is subset of any set).
        Returns FALSE otherwise.

        Args:
            subset_expr: Normalized collection expression (potential subset)
            superset_expr: Normalized collection expression (potential superset)
            subset_source_table: Source table for subset (if it's a column reference)
            superset_source_table: Source table for superset (if it's a column reference)
            normalize_subset: Whether to normalize subset expression
            normalize_superset: Whether to normalize superset expression

        Returns:
            SQL expression evaluating to boolean

        Example:
            subset_expr = json_extract(resource, '$.name[0]')  # Single name
            superset_expr = json_extract(resource, '$.name')    # All names
            Result: TRUE (single element is in collection)

        SP-110-002: Handle the case where subset_expr is a simple column reference
        (like cte_2.name_item) that represents a single element, not an array.
        In this case, we just need to check if that single element exists in the
        superset collection, not enumerate it.
        """
        prefix = self._generate_internal_alias("subset")
        empty_array = self.dialect.empty_json_array()

        # SP-110-002: Check if subset_expr is a simple column reference (single element)
        # This happens when first()/last() creates a fragment with expression="name_item"
        # and subsetOf() is called. The subset is a single element, not an array.
        subset_is_single_element = (
            subset_source_table and
            subset_expr.endswith('_item') and
            '.' in subset_expr
        )

        if subset_is_single_element:
            # Subset is a single element - just check if it exists in superset
            # No need to enumerate the subset
            logger.debug(f"SP-110-002: Subset is single element {subset_expr}, using direct comparison")

            # Safe superset with NULL handling
            if normalize_superset:
                safe_superset = f"COALESCE({self._normalize_collection_expression(superset_expr)}, {empty_array})"
            else:
                safe_superset = f"COALESCE({superset_expr}, {empty_array})"

            # Serialize the single element for comparison
            subset_serialized = self.dialect.serialize_json_value(subset_expr)

            # Build enumeration for superset only
            if superset_source_table:
                # Superset is also a column reference - enumerate it
                lateral_clause = self.dialect.generate_lateral_json_enumeration(safe_superset, "enum_table", "value", "key")

                if self.dialect.name == "POSTGRESQL":
                    superset_enumeration = (
                        f"SELECT {superset_source_table}.id, (enum_table.ordinality - 1) AS idx, enum_table.value AS val "
                        f"FROM {superset_source_table}, {lateral_clause}"
                    )
                else:
                    superset_enumeration = (
                        f"SELECT {superset_source_table}.id, enum_table.key AS idx, enum_table.value AS val "
                        f"FROM {superset_source_table}, {lateral_clause}"
                    )
            else:
                # Superset is a JSON array expression - enumerate it
                superset_enumeration = self.dialect.enumerate_json_array(safe_superset, "val", "idx")

            # Check if the single element exists in the superset
            superset_serialized = self.dialect.serialize_json_value("val")
            superset_values = (
                f"SELECT DISTINCT {superset_serialized} AS value "
                f"FROM ({superset_enumeration}) AS enum_table"
            )

            # Return TRUE if the single element is in the superset, FALSE otherwise
            # Handle NULL subset as TRUE (empty set is subset of any set)
            return (
                f"COALESCE("
                f"(SELECT CASE WHEN {subset_expr} IS NULL THEN TRUE "
                f"WHEN EXISTS (SELECT 1 FROM ({superset_values}) AS sup WHERE sup.value = {subset_serialized}) "
                f"THEN TRUE ELSE FALSE END), "
                "TRUE"
                ")"
            )

        # Original logic for array-to-array comparison
        # Safe versions with NULL handling
        # For CTE references, normalization is deferred to the LATERAL subquery
        if normalize_subset:
            safe_subset = f"COALESCE({self._normalize_collection_expression(subset_expr)}, {empty_array})"
        else:
            safe_subset = f"COALESCE({subset_expr}, {empty_array})"

        if normalize_superset:
            safe_superset = f"COALESCE({self._normalize_collection_expression(superset_expr)}, {empty_array})"
        else:
            safe_superset = f"COALESCE({superset_expr}, {empty_array})"

        # Aliases for enumeration
        subset_value = f"{prefix}_subval"
        subset_index = f"{prefix}_subidx"
        superset_value = f"{prefix}_supval"
        superset_index = f"{prefix}_supidx"
        subset_enum_alias = f"{prefix}_subenum"
        superset_enum_alias = f"{prefix}_supenum"

        # Enumerate both arrays
        # SP-110 Phase 2: If source table is provided, use proper LATERAL table function syntax
        # to avoid parser errors with "LATERAL (SELECT ...)" pattern
        if subset_source_table:
            # Use dialect polymorphic method for LATERAL JSON enumeration
            lateral_clause = self.dialect.generate_lateral_json_enumeration(safe_subset, "enum_table", "value", "key")

            # Build SELECT with appropriate column references based on dialect
            if self.dialect.name == "POSTGRESQL":
                # PostgreSQL uses ordinality (1-based), need to convert to 0-based
                subset_enumeration = (
                    f"SELECT {subset_source_table}.id, (enum_table.ordinality - 1) AS {subset_index}, enum_table.value AS {subset_value} "
                    f"FROM {subset_source_table}, {lateral_clause}"
                )
            else:
                # DuckDB and others use key column directly (0-based)
                subset_enumeration = (
                    f"SELECT {subset_source_table}.id, enum_table.key AS {subset_index}, enum_table.value AS {subset_value} "
                    f"FROM {subset_source_table}, {lateral_clause}"
                )
        else:
            subset_enumeration = self.dialect.enumerate_json_array(safe_subset, subset_value, subset_index)

        if superset_source_table:
            # Use dialect polymorphic method for LATERAL JSON enumeration
            lateral_clause = self.dialect.generate_lateral_json_enumeration(safe_superset, "enum_table", "value", "key")

            # Build SELECT with appropriate column references based on dialect
            if self.dialect.name == "POSTGRESQL":
                # PostgreSQL uses ordinality (1-based), need to convert to 0-based
                superset_enumeration = (
                    f"SELECT {superset_source_table}.id, (enum_table.ordinality - 1) AS {superset_index}, enum_table.value AS {superset_value} "
                    f"FROM {superset_source_table}, {lateral_clause}"
                )
            else:
                # DuckDB and others use key column directly (0-based)
                superset_enumeration = (
                    f"SELECT {superset_source_table}.id, enum_table.key AS {superset_index}, enum_table.value AS {superset_value} "
                    f"FROM {superset_source_table}, {lateral_clause}"
                )
        else:
            superset_enumeration = self.dialect.enumerate_json_array(safe_superset, superset_value, superset_index)

        # Serialize values for comparison
        subset_serialized = self.dialect.serialize_json_value(f"{subset_enum_alias}.{subset_value}")
        superset_serialized = self.dialect.serialize_json_value(f"{superset_enum_alias}.{superset_value}")

        # Build set of all values in superset
        superset_values = (
            f"SELECT DISTINCT {superset_serialized} AS value "
            f"FROM ({superset_enumeration}) AS {superset_enum_alias}"
        )

        # Check if any element from subset is NOT in superset
        # If count > 0, then NOT a subset
        elements_not_in_superset = (
            f"SELECT COUNT(*) AS not_in_count "
            f"FROM ({subset_enumeration}) AS {subset_enum_alias} "
            f"WHERE {subset_serialized} NOT IN ("
            f"SELECT value FROM ({superset_values}) AS {prefix}_supset"
            ")"
        )

        # Return TRUE if all elements are in superset (count = 0), FALSE otherwise
        # Empty subset returns TRUE (0 elements not in superset)
        return (
            f"COALESCE("
            f"(SELECT CASE WHEN not_in_count = 0 THEN TRUE ELSE FALSE END "
            f"FROM ({elements_not_in_superset}) AS {prefix}_check), "
            "FALSE"
            ")"
        )

    def _compose_union_expression(
        self,
        left_original: str,
        right_original: str,
        normalized_left: str,
        normalized_right: str,
    ) -> str:
        """Compose final SQL for union operator."""
        merged_arrays = self._build_union_array_expression(normalized_left, normalized_right)
        empty_array = self.dialect.empty_json_array()

        return (
            "("
            "CASE "
            f"WHEN {left_original} IS NULL AND {right_original} IS NULL THEN NULL "
            f"WHEN {left_original} IS NULL THEN {normalized_right} "
            f"WHEN {right_original} IS NULL THEN {normalized_left} "
            f"ELSE COALESCE({merged_arrays}, {empty_array}) "
            "END"
            ")"
        )

    def _build_union_array_expression(self, left_array_expr: str, right_array_expr: str) -> str:
        """Build SQL that merges two JSON arrays preserving order and duplicates."""
        value_alias = "union_value"
        index_alias = "union_index"
        source_alias = "union_source"

        left_enumeration = self.dialect.enumerate_json_array(left_array_expr, value_alias, index_alias)
        right_enumeration = self.dialect.enumerate_json_array(right_array_expr, value_alias, index_alias)

        combined_rows = f"""
            SELECT {value_alias}, 0 AS {source_alias}, {index_alias}
            FROM ({left_enumeration}) AS left_enumerated
            UNION ALL
            SELECT {value_alias}, 1 AS {source_alias}, {index_alias}
            FROM ({right_enumeration}) AS right_enumerated
        """

        ordered_values = f"""
            SELECT {value_alias}, {source_alias}, {index_alias}
            FROM (
                {combined_rows}
            ) combined_union
            ORDER BY {source_alias}, {index_alias}
        """

        aggregate_expr = self.dialect.aggregate_to_json_array(
            f"{value_alias} ORDER BY {source_alias}, {index_alias}"
        )

        return (
            f"(SELECT {aggregate_expr} "
            f"FROM ({ordered_values}) ordered_union)"
        )

    def _generate_arithmetic_sql(
        self,
        operator: str,
        left_fragment: SQLFragment,
        right_fragment: SQLFragment,
        left_node: FHIRPathASTNode,
        right_node: FHIRPathASTNode,
        sql_operator: str,
    ) -> str:
        """Generate SQL for arithmetic operators with FHIRPath spec-compliant type coercion.

        SP-101-001: Implements proper type promotion rules per FHIRPath specification:
        - Addition/Subtraction/Multiplication: integer+integer=integer, integer+decimal=decimal
        - Division (/): Always returns decimal
        - Integer Division (div): Truncates to integer
        - Modulo (mod): integer mod integer = integer, otherwise decimal

        Args:
            operator: FHIRPath operator (+, -, *, /, div, mod)
            left_fragment: Left operand SQL fragment
            right_fragment: Right operand SQL fragment
            left_node: Left operand AST node
            right_node: Right operand AST node
            sql_operator: SQL operator symbol

        Returns:
            SQL expression for the arithmetic operation
        """
        left_expr = left_fragment.expression
        right_expr = right_fragment.expression

        # Infer operand types using enhanced type inference
        left_type = self._infer_numeric_type(left_node)
        right_type = self._infer_numeric_type(right_node)

        # Division (/) always returns decimal per FHIRPath spec
        if operator == "/":
            numerator = self._ensure_decimal_expression(left_expr, left_type)
            denominator = self._ensure_decimal_expression(right_expr, right_type)
            division_expr = self.dialect.generate_decimal_division(numerator, denominator)
            return self._wrap_division_expression(numerator, denominator, division_expr)

        # Integer division (div) truncates to integer
        if operator == "div":
            # Both operands cast to decimal first, then result truncated
            numerator = self._ensure_decimal_expression(left_expr, left_type)
            denominator = self._ensure_decimal_expression(right_expr, right_type)
            division_expr = self.dialect.generate_integer_division(numerator, denominator)
            return self._wrap_division_expression(numerator, denominator, division_expr)

        # Modulo operator: integer mod integer = integer, otherwise decimal
        if operator == "mod":
            prefers_decimal = "decimal" in {left_type, right_type}
            if prefers_decimal:
                left_numeric = self._ensure_decimal_expression(left_expr, left_type)
                right_numeric = self._ensure_decimal_expression(right_expr, right_type)
            else:
                left_numeric = left_expr
                right_numeric = right_expr
            modulo_expr = self.dialect.generate_modulo(left_numeric, right_numeric)
            return self._wrap_modulo_expression(left_numeric, right_numeric, modulo_expr)

        # Addition, subtraction, multiplication: apply type promotion
        # integer op integer = integer
        # integer op decimal = decimal
        # decimal op decimal = decimal
        # unknown op * = decimal (safe cast for JSON-extracted numeric values)
        prefers_decimal = "decimal" in {left_type, right_type} or "unknown" in {left_type, right_type}
        if prefers_decimal:
            left_numeric = self._ensure_decimal_expression(left_expr, left_type)
            right_numeric = self._ensure_decimal_expression(right_expr, right_type)
        else:
            left_numeric = left_expr
            right_numeric = right_expr

        return f"({left_numeric} {sql_operator} {right_numeric})"

    def _wrap_division_expression(self, numerator: str, denominator: str, core_expr: str) -> str:
        """Wrap division expression with NULL propagation and zero checks."""
        return (
            "(CASE "
            f"WHEN {numerator} IS NULL THEN NULL "
            f"WHEN {denominator} IS NULL THEN NULL "
            f"WHEN ({denominator}) = 0 THEN NULL "
            f"ELSE {core_expr} "
            "END)"
        )

    def _wrap_modulo_expression(self, left_expr: str, right_expr: str, core_expr: str) -> str:
        """Wrap modulo expression with NULL propagation and zero checks."""
        return (
            "(CASE "
            f"WHEN {left_expr} IS NULL THEN NULL "
            f"WHEN {right_expr} IS NULL THEN NULL "
            f"WHEN ({right_expr}) = 0 THEN NULL "
            f"ELSE {core_expr} "
            "END)"
        )

    def _infer_numeric_type(self, node: Optional[FHIRPathASTNode]) -> str:
        """Infer numeric type (integer/decimal) from AST node metadata and value.

        SP-101-001: Enhanced type inference for FHIRPath spec-compliant arithmetic.
        Handles multiple sources of type information:
        1. Explicit literal_type attribute on LiteralNode
        2. Python value type (Decimal, float, int)
        3. SQL data type metadata
        4. FHIR type information
        5. Literal text analysis (fallback for numeric literals)
        """
        if node is None:
            return "unknown"

        # Check for explicit literal_type attribute (from LiteralNode)
        literal_type = getattr(node, "literal_type", None)
        if literal_type == "decimal":
            return "decimal"
        if literal_type == "integer":
            return "integer"

        # Check Python value type
        value = getattr(node, "value", None)
        if isinstance(value, Decimal) or isinstance(value, float):
            return "decimal"
        if isinstance(value, int) and not isinstance(value, bool):
            return "integer"

        # Check SQL data type from metadata
        sql_data_type = (
            node.get_sql_data_type() if hasattr(node, "get_sql_data_type") else SQLDataType.UNKNOWN
        )
        if sql_data_type == SQLDataType.DECIMAL:
            return "decimal"
        if sql_data_type == SQLDataType.INTEGER:
            return "integer"

        # Check FHIR type information
        metadata = getattr(node, "metadata", None)
        type_info = getattr(metadata, "type_info", None) if metadata else None
        if type_info and getattr(type_info, "fhir_type", None):
            fhir_type = type_info.fhir_type.lower()
            if fhir_type in {"decimal"}:
                return "decimal"
            if fhir_type in {"integer", "positiveint", "unsignedint"}:
                return "integer"

        # SP-101-001: Fallback to text analysis for numeric literals ONLY
        # This handles cases where the parser hasn't set proper metadata on literals.
        # IMPORTANT: Only apply text-based inference to literal nodes to avoid
        # incorrectly typing column references as integers/decimals based on name.
        if getattr(node, "node_type", None) == "literal":
            text = getattr(node, "text", "").strip()
            if text and self._is_numeric_literal(text):
                if "." in text or "e" in text.lower():
                    return "decimal"
                return "integer"

        return "unknown"

    def _is_numeric_literal(self, text: str) -> bool:
        """Check if text represents a numeric literal.

        Handles integers (123, -456) and decimals (1.5, -0.25, 3.14e-10).

        Args:
            text: The text to check

        Returns:
            True if text is a valid numeric literal, False otherwise
        """
        if not text:
            return False

        # Remove leading/trailing whitespace
        text = text.strip()

        # Check for numeric pattern: optional minus, digits, optional decimal, optional exponent
        # Pattern matches: 123, -456, 1.5, -0.25, 3.14e-10, -1E5
        return bool(re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", text))

    def _ensure_decimal_expression(self, expression: str, inferred_type: str) -> str:
        """Cast expression to decimal when required for arithmetic operations.

        SP-101-001: Enhanced casting for FHIRPath spec-compliant type coercion.
        - If type is decimal, use expression as-is
        - If type is integer or unknown, cast to decimal
        - Uses TRY_CAST for safe conversion (returns NULL on failure)

        Args:
            expression: SQL expression to cast
            inferred_type: Inferred type ("integer", "decimal", or "unknown")

        Returns:
            SQL expression that evaluates to a decimal value
        """
        if inferred_type == "decimal":
            return expression
        return self.dialect.generate_type_cast(expression, "Decimal")

    def _translate_temporal_quantity_addition(
        self,
        left_fragment: SQLFragment,
        right_fragment: SQLFragment,
        left_node: FHIRPathASTNode,
        right_node: FHIRPathASTNode
    ) -> Optional[SQLFragment]:
        """Translate temporal literal plus quantity expressions to SQL.

        Handles expressions like:
        - @2023-01-01 + 1 'day'
        - @1973-12-25T00:00:00.000+10:00 + 10 'ms'
        - @2023-01-01 + 7 days

        Returns None if this is not a temporal + quantity expression.
        """
        # SP-105-005: Detect temporal type from fragment metadata first, then node
        temporal_type = None

        # Check fragment metadata (set after visiting the node)
        left_metadata = getattr(left_fragment, "metadata", {}) or {}
        fragment_literal_type = left_metadata.get("literal_type")
        if fragment_literal_type in {"date", "datetime", "time"}:
            temporal_type = fragment_literal_type
        else:
            # Fall back to node-based detection
            temporal_type = self._detect_temporal_type(left_node)

        if temporal_type is None:
            return None

        # SP-105-005: Parse quantity from fragment metadata first, then node
        quantity = self._parse_quantity_literal_from_fragment(right_fragment, right_node)
        if quantity is None:
            return None

        amount, unit = quantity
        normalized_unit = self._normalize_quantity_unit(unit)
        if normalized_unit is None:
            return None

        # Months and years require whole-number adjustments
        if normalized_unit in {"year", "month"} and amount % 1 != 0:
            return None

        interval_expr = self._build_interval_expression(amount, normalized_unit)
        if interval_expr is None:
            return None

        sql_expr = f"({left_fragment.expression} + {interval_expr})"
        if temporal_type == "date":
            sql_expr = f"CAST({sql_expr} AS DATE)"
        elif temporal_type == "datetime":
            sql_expr = f"CAST({sql_expr} AS TIMESTAMP)"
        elif temporal_type == "time":
            sql_expr = f"CAST({sql_expr} AS TIME)"

        dependencies: List[str] = []
        for dep in (*left_fragment.dependencies, *right_fragment.dependencies):
            if dep not in dependencies:
                dependencies.append(dep)

        source_table = (
            left_fragment.source_table
            or right_fragment.source_table
            or self.context.current_table
        )

        return SQLFragment(
            expression=sql_expr,
            source_table=source_table,
            requires_unnest=left_fragment.requires_unnest or right_fragment.requires_unnest,
            is_aggregate=left_fragment.is_aggregate or right_fragment.is_aggregate,
            dependencies=dependencies
        )

    def _translate_temporal_quantity_subtraction(
        self,
        left_fragment: SQLFragment,
        right_fragment: SQLFragment,
        left_node: FHIRPathASTNode,
        right_node: FHIRPathASTNode
    ) -> Optional[SQLFragment]:
        """Translate temporal literal minus quantity expressions to SQL."""
        # SP-105-005: Detect temporal type from fragment metadata first, then node
        temporal_type = None

        # Check fragment metadata (set after visiting the node)
        left_metadata = getattr(left_fragment, "metadata", {}) or {}
        fragment_literal_type = left_metadata.get("literal_type")
        if fragment_literal_type in {"date", "datetime", "time"}:
            temporal_type = fragment_literal_type
        else:
            # Fall back to node-based detection
            temporal_type = self._detect_temporal_type(left_node)

        if temporal_type is None:
            return None

        # SP-105-005: Parse quantity from fragment metadata first, then node
        quantity = self._parse_quantity_literal_from_fragment(right_fragment, right_node)
        if quantity is None:
            return None

        amount, unit = quantity
        normalized_unit = self._normalize_quantity_unit(unit)
        if normalized_unit is None:
            return None

        # Months and years require whole-number adjustments
        if normalized_unit in {"year", "month"} and amount % 1 != 0:
            return None

        interval_expr = self._build_interval_expression(amount, normalized_unit)
        if interval_expr is None:
            return None

        sql_expr = f"({left_fragment.expression} - {interval_expr})"
        if temporal_type == "date":
            sql_expr = f"CAST({sql_expr} AS DATE)"
        elif temporal_type == "datetime":
            sql_expr = f"CAST({sql_expr} AS TIMESTAMP)"
        elif temporal_type == "time":
            sql_expr = f"CAST({sql_expr} AS TIME)"

        dependencies: List[str] = []
        for dep in (*left_fragment.dependencies, *right_fragment.dependencies):
            if dep not in dependencies:
                dependencies.append(dep)

        source_table = (
            left_fragment.source_table
            or right_fragment.source_table
            or self.context.current_table
        )

        return SQLFragment(
            expression=sql_expr,
            source_table=source_table,
            requires_unnest=left_fragment.requires_unnest or right_fragment.requires_unnest,
            is_aggregate=left_fragment.is_aggregate or right_fragment.is_aggregate,
            dependencies=dependencies
        )

    def _detect_temporal_type(self, node: FHIRPathASTNode) -> Optional[str]:
        """Detect if a node represents a temporal (date/datetime/time) value."""
        literal_type = getattr(node, "literal_type", None)
        if literal_type in {"date", "datetime", "time"}:
            return literal_type

        value = getattr(node, "value", None)
        if isinstance(value, str) and value.startswith("@"):
            return "datetime" if "T" in value else "date"

        metadata = getattr(node, "metadata", None)
        type_info = getattr(metadata, "type_info", None)
        if type_info and getattr(type_info, "fhir_type", None):
            fhir_type = type_info.fhir_type.lower()
            if fhir_type in {"date", "datetime", "time"}:
                return fhir_type

        return None

    def _parse_quantity_literal_from_fragment(
        self,
        fragment: SQLFragment,
        node: FHIRPathASTNode
    ) -> Optional[Tuple[Decimal, str]]:
        """Parse quantity literal from SQL fragment metadata or AST node.

        SP-105-005: Check fragment metadata first for temporal_info, then fall back
        to node-based parsing. This handles both quoted units (1'd') and unquoted
        units (7days, 1 second).
        """
        # First check fragment metadata (set after visiting the node)
        fragment_metadata = getattr(fragment, "metadata", {}) or {}
        temporal_info = fragment_metadata.get("temporal_info")
        if temporal_info and temporal_info.get("kind") == "duration":
            value = temporal_info.get("value")
            unit = temporal_info.get("unit")
            if value and unit:
                try:
                    amount = Decimal(str(value))
                    return amount, unit
                except (InvalidOperation, TypeError):
                    pass

        # Fall back to node-based parsing
        return self._parse_quantity_literal(node)

    def _parse_quantity_literal(self, node: FHIRPathASTNode) -> Optional[Tuple[Decimal, str]]:
        """Parse quantity literal expressed as <number>'unit' or <number><unit>.

        SP-105-005: Enhanced to extract quantity from temporal_info in fragment metadata.
        The quantity literal may have already been visited and converted to a SQLFragment,
        so we check the node's temporal_info metadata first.
        """
        # SP-105-005: Check if the node has temporal_info (set by literal visitor)
        # This handles both quoted units (1'd') and unquoted units (7days)
        metadata = getattr(node, "metadata", None)
        if metadata:
            custom_attrs = getattr(metadata, "custom_attributes", {})
            temporal_info = custom_attrs.get("temporal_info")
            if temporal_info and temporal_info.get("kind") == "duration":
                value = temporal_info.get("value")
                unit = temporal_info.get("unit")
                if value and unit:
                    try:
                        amount = Decimal(str(value))
                        return amount, unit
                    except (InvalidOperation, TypeError):
                        pass

        # Fall back to text-based parsing for quoted units
        value = getattr(node, "value", None)
        unit = None
        number = None

        if isinstance(value, dict):
            number = value.get("value")
            unit = value.get("unit")
        else:
            text = getattr(node, "text", "") or ""
            match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*'([^']+)'\s*", text)
            if match:
                number, unit = match.groups()

        if number is None or unit is None:
            return None

        try:
            amount = Decimal(str(number))
        except (InvalidOperation, TypeError):
            return None

        return amount, unit

    @staticmethod
    def _normalize_quantity_unit(unit: str) -> Optional[str]:
        """Normalize quantity unit synonyms to canonical form."""
        unit_map = {
            "year": "year", "years": "year", "a": "year",
            "month": "month", "months": "month", "mo": "month",
            "week": "week", "weeks": "week", "wk": "week",
            "day": "day", "days": "day", "d": "day",
            "hour": "hour", "hours": "hour", "h": "hour",
            "minute": "minute", "minutes": "minute", "min": "minute",
            "second": "second", "seconds": "second", "s": "second",
            "millisecond": "millisecond", "milliseconds": "millisecond", "ms": "millisecond"
        }
        return unit_map.get(unit.strip().lower())

    def _build_interval_expression(self, amount: Decimal, unit: str) -> Optional[str]:
        """Build SQL INTERVAL expression for supported temporal units."""
        if unit == "millisecond":
            seconds = amount / Decimal("1000")
            seconds_str = self._decimal_to_sql_str(seconds)
            return f"INTERVAL '{seconds_str} second'"

        if unit in {"year", "month", "week", "day"}:
            if amount % 1 != 0:
                return None
            amount_str = str(int(amount))
            return f"INTERVAL '{amount_str} {unit}'"

        if unit in {"hour", "minute", "second"}:
            amount_str = self._decimal_to_sql_str(amount)
            return f"INTERVAL '{amount_str} {unit}'"

        return None

    @staticmethod
    def _decimal_to_sql_str(amount: Decimal) -> str:
        """Convert Decimal to SQL-friendly string without scientific notation.

        SP-105-005: Use format() with 'f' to avoid scientific notation that can
        occur with normalize() for values >= 10.
        """
        # Check if it's an integer value
        if amount == amount.to_integral():
            # For integers, use format to avoid scientific notation
            return format(amount.to_integral(), "f")
        # For decimals, use format and strip trailing zeros
        return format(amount, "f").rstrip("0").rstrip(".")

    def _translate_temporal_literal_comparison_if_applicable(self, node: OperatorNode) -> Optional[SQLFragment]:
        """Translate temporal literal comparisons that require precision-aware semantics.

        This handles comparisons involving:
        1. Temporal literals with reduced precision (e.g., @2018-03, @T10:30)
        2. Field references to temporal types (e.g., Patient.birthDate which is a date)

        For field references, we visit the node to get the SQL expression and use it
        directly in comparisons, rather than trying to convert to a literal.
        """
        if len(node.children) != 2:
            return None

        left_info = self._extract_temporal_info(node.children[0])
        right_info = self._extract_temporal_info(node.children[1])

        if not left_info or not right_info:
            return None

        # SP-110-FIX-012: Check for temporal type mismatch before processing
        # When comparing different temporal types (date vs datetime vs time) or
        # different precisions, return NULL (empty collection) per FHIRPath spec.
        if self._is_temporal_info_mismatch(left_info, right_info):
            # Return NULL to represent empty collection result
            return SQLFragment(
                expression="NULL",
                source_table=self.context.current_table or "resource",
                requires_unnest=False,
                is_aggregate=False
            )

        # SP-110-008: Apply range-based semantics when:
        # 1. At least one operand has reduced precision (is_partial)
        # 2. At least one operand is a temporal function (now(), today(), timeOfDay())
        # 3. At least one operand is a field reference (which has implicit precision)
        # 4. At least one operand has timezone offset (requires UTC conversion)
        # This ensures proper comparison between temporal functions and date fields,
        # as well as timezone-aware DateTime comparisons
        has_partial = left_info.get("is_partial") or right_info.get("is_partial")
        has_temporal_function = left_info.get("is_temporal_function") or right_info.get("is_temporal_function")
        has_field_reference = left_info.get("is_field_reference") or right_info.get("is_field_reference")
        has_timezone = left_info.get("timezone_offset") or right_info.get("timezone_offset")

        if not (has_partial or has_temporal_function or has_field_reference or has_timezone):
            return None

        operator = (node.operator or "").strip()
        conditions = self._build_temporal_conditions(
            left_info, right_info, operator,
            node.children[0], node.children[1]
        )
        if conditions is None:
            return None

        true_condition, false_condition = conditions

        # Determine if we need existential semantics (NULL for false) or standard boolean (FALSE for false)
        # Existential semantics apply when comparing against data from a table (field references)
        # Standard boolean applies for literal-to-literal comparisons
        use_existential_semantics = has_field_reference

        if use_existential_semantics:
            # When the comparison is true, return TRUE
            # When the comparison is false, return NULL (empty result)
            # This filters out non-matching rows from the result set
            sql_expr = (
                "CASE "
                f"WHEN {true_condition} THEN TRUE "
                "ELSE NULL "
                "END"
            )
        else:
            # For literal-to-literal comparisons, return TRUE or FALSE
            sql_expr = (
                "CASE "
                f"WHEN {true_condition} THEN TRUE "
                f"WHEN {false_condition} THEN FALSE "
                "ELSE NULL "
                "END"
            )

        return SQLFragment(
            expression=sql_expr,
            source_table=self.context.current_table or "resource",
            requires_unnest=False,
            is_aggregate=False
        )

    def _extract_temporal_info(self, node: FHIRPathASTNode) -> Optional[Dict[str, Any]]:
        """Extract temporal metadata from AST node if available.

        This method handles:
        1. Nodes that have already been visited and have temporal_info attribute
        2. Raw AST nodes that need temporal info parsed from their text (literals)
        3. Field references that resolve to temporal types (date, dateTime, time)

        For field references, we resolve the element type to determine if it's a temporal field.
        """
        # First, check if temporal_info is already set (visited node)
        temporal_info = getattr(node, "temporal_info", None)
        if temporal_info:
            return temporal_info

        # Check metadata for temporal_info
        metadata = getattr(node, "metadata", None)
        if metadata and getattr(metadata, "custom_attributes", None):
            temporal_info = metadata.custom_attributes.get("temporal_info")
            if temporal_info:
                return temporal_info

        # For raw nodes, parse temporal info from text
        # Traverse to find the actual literal node (deepest nested literal)
        literal_node = self._find_literal_node(node)
        if literal_node and hasattr(literal_node, 'text'):
            text = literal_node.text
            if text and text.startswith('@'):
                return self._parse_temporal_literal_from_text(text)

        # Check if this is a field reference that resolves to a temporal type
        # This handles cases like Patient.birthDate where birthDate is a date field
        temporal_field_info = self._extract_temporal_field_info(node)
        if temporal_field_info:
            return temporal_field_info

        # SP-110-008: Check if this is a temporal function call (now(), today(), timeOfDay())
        # These functions return temporal values with specific precision
        temporal_function_info = self._extract_temporal_function_info(node)
        if temporal_function_info:
            return temporal_function_info

        return None

    def _find_literal_node(self, node: FHIRPathASTNode) -> Optional[FHIRPathASTNode]:
        """Find the actual literal node by traversing TermExpression wrappers.

        AST structure for literals is often:
        TermExpression -> literal -> literal (actual literal)
        """
        if not hasattr(node, 'children') or not node.children:
            # This is a leaf node, check if it's a literal
            node_type = getattr(node, 'node_type', '')
            if node_type == 'literal':
                return node
            return None

        # If there's exactly one child, traverse deeper
        if len(node.children) == 1:
            return self._find_literal_node(node.children[0])

        # Multiple children - not a simple literal wrapper
        return None

    def _extract_temporal_field_info(self, node: FHIRPathASTNode) -> Optional[Dict[str, Any]]:
        """Extract temporal metadata from a field reference node.

        This handles cases where the node is a field reference (not a literal) that
        resolves to a temporal type like date, dateTime, or time.

        For example: Patient.birthDate resolves to a 'date' type, which has day precision.

        Args:
            node: AST node representing a field reference

        Returns:
            Dict with temporal info including kind, precision, start, end, is_partial
            or None if not a temporal field reference
        """
        from ..types.element_type_resolver import resolve_element_type

        # SP-110-008: Handle multiple node types that can represent field references
        # The parser may represent Patient.birthDate as different node types depending
        # on the context (e.g., IdentifierNode, InvocationExpression, etc.)
        # We accept any node that has a text attribute with a dot-separated path
        node_type = getattr(node, 'node_type', '')
        # Don't restrict to just InvocationExpression - accept any node with path text

        # Get the field name from the node
        # For Patient.birthDate, we need to extract "birthDate"
        text = getattr(node, 'text', '')
        if not text or '.' not in text:
            return None

        # Split the path to get the field name
        parts = text.split('.')
        if len(parts) < 2:
            return None

        field_name = parts[-1]  # Last part is the field name
        resource_type = self.resource_type  # Current resource type being queried

        # Resolve the element type
        element_type = resolve_element_type(resource_type, field_name)
        if not element_type:
            return None

        # Map FHIR types to temporal kinds and precisions
        temporal_type_map = {
            'date': ('date', 'day'),
            'dateTime': ('datetime', 'second'),
            'time': ('time', 'second'),
            'instant': ('datetime', 'subsecond'),
        }

        type_info = temporal_type_map.get(element_type)
        if not type_info:
            return None

        kind, precision = type_info

        # For field references, we don't have a specific value, so we can't create
        # start/end boundaries. Instead, we indicate the field's temporal type
        # so the comparison logic knows how to handle it.
        # The is_partial flag is True because field references have implicit precision
        # (e.g., birthDate has day precision, not full timestamp precision)
        return {
            "kind": kind,
            "precision": precision,
            "is_partial": True,  # Field references have implicit precision
            "is_field_reference": True,  # Flag to distinguish from literals
            "field_type": element_type,
            "field_name": field_name,
            "original": text
        }

    def _extract_temporal_function_info(self, node: FHIRPathASTNode) -> Optional[Dict[str, Any]]:
        """Extract temporal metadata from temporal function calls.

        This handles cases where the node is a function call like now(), today(), or timeOfDay()
        which return temporal values with specific precision.

        Args:
            node: AST node representing a function call

        Returns:
            Dict with temporal info including kind, precision, is_partial
            or None if not a temporal function
        """
        from ..ast.nodes import FunctionCallNode

        # Check if this is a FunctionCallNode
        if not isinstance(node, FunctionCallNode):
            return None

        function_name = getattr(node, 'function_name', '').lower()

        # Define temporal functions and their return types
        temporal_functions = {
            'now': {
                'kind': 'datetime',
                'precision': 'full',
                'is_partial': False,
                'literal_type': 'datetime',
                'function_name': 'now'
            },
            'today': {
                'kind': 'date',
                'precision': 'day',
                'is_partial': False,
                'literal_type': 'date',
                'function_name': 'today'
            },
            'timeofday': {
                'kind': 'time',
                'precision': 'millisecond',
                'is_partial': False,
                'literal_type': 'time',
                'function_name': 'timeofday'
            }
        }

        if function_name in temporal_functions:
            info = temporal_functions[function_name].copy()
            info['original'] = function_name + '()'
            info['is_temporal_function'] = True
            return info

        return None

    def _parse_temporal_literal_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse FHIR temporal literal from text, returning metadata for range comparisons.

        This replicates the temporal literal parsing logic from ast_extensions.py
        to handle raw AST nodes before they're visited.

        Args:
            text: The temporal literal text (e.g., "@2018-03", "@T10:30")

        Returns:
            Dict with temporal info including kind, precision, start, end, is_partial
            or None if not a temporal literal
        """
        if not text or not text.startswith("@"):
            return None

        import re
        from datetime import datetime, timedelta

        if text.startswith("@T"):
            return self._parse_time_literal_from_text(text)

        body = text[1:]
        if "T" in body:
            # Check for partial DateTime pattern first (@YYYYT, @YYYY-MMT, @YYYY-MM-DDT)
            partial_datetime_match = re.fullmatch(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?T$", body)
            if partial_datetime_match:
                return self._parse_partial_datetime_literal_from_text(text, body, partial_datetime_match)
            return self._parse_datetime_literal_from_text(text, body)
        return self._parse_date_literal_from_text(text, body)

    def _parse_date_literal_from_text(self, original: str, body: str) -> Optional[Dict[str, Any]]:
        """Parse FHIR date literal with optional reduced precision."""
        import re
        from datetime import datetime, timedelta

        if re.fullmatch(r"\d{4}$", body):
            year = int(body)
            start_dt = datetime(year, 1, 1)
            end_dt = datetime(year + 1, 1, 1)
            precision = "year"
            normalized = f"{year:04d}"
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

    def _parse_time_literal_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse FHIR time literal with optional reduced precision."""
        import re
        from datetime import datetime, timedelta

        body = text[2:]  # Remove "@T"

        # Match various time precisions
        if re.fullmatch(r"\d{2}$", body):
            # Hour precision: T10 -> 10:00:00 to 10:59:59.999...
            hour = int(body)
            start_dt = datetime(1, 1, 1, hour, 0, 0)
            end_dt = datetime(1, 1, 1, hour + 1, 0, 0)
            precision = "hour"
            normalized = f"{hour:02d}"
            is_partial = True
        elif re.fullmatch(r"\d{2}:\d{2}$", body):
            # Minute precision: T10:30 -> 10:30:00 to 10:30:59.999...
            hour, minute = map(int, body.split(":"))
            start_dt = datetime(1, 1, 1, hour, minute, 0)
            end_dt = datetime(1, 1, 1, hour, minute + 1, 0)
            precision = "minute"
            normalized = f"{hour:02d}:{minute:02d}"
            is_partial = True
        elif re.fullmatch(r"\d{2}:\d{2}:\d{2}$", body):
            # Second precision: T10:30:00 -> 10:30:00 to 10:30:00.999...
            hour, minute, second = map(int, body.split(":"))
            start_dt = datetime(1, 1, 1, hour, minute, second)
            end_dt = start_dt + timedelta(seconds=1)
            precision = "second"
            normalized = f"{hour:02d}:{minute:02d}:{second:02d}"
            is_partial = False
        else:
            return None

        return {
            "kind": "time",
            "precision": precision,
            "normalized": normalized,
            "start": self._format_time_iso(start_dt),
            "end": self._format_time_iso(end_dt),
            "is_partial": is_partial,
            "literal_type": "time",
            "original": text
        }

    def _parse_datetime_literal_from_text(self, original: str, body: str) -> Optional[Dict[str, Any]]:
        """Parse FHIR dateTime literal with optional reduced precision and timezone."""
        import re
        from datetime import datetime, timedelta, timezone

        # Pattern with optional timezone suffix: Z or +/-HH:MM
        # Capture the timezone offset for proper comparison
        pattern = re.compile(
            r"^(\d{4})-(\d{2})-(\d{2})T"
            r"(\d{2})(?::(\d{2})(?::(\d{2})(?:\.(\d+))?)?)?"
            r"(?:(?P<tz>Z)|(?P<tz_offset>[+-]\d{2}:\d{2}))?$"
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

        # Extract timezone offset
        tz_match = match.group('tz')
        tz_offset_match = match.group('tz_offset')
        timezone_offset = None
        tz_delta = None

        if tz_match == 'Z':
            timezone_offset = '+00:00'
            tz_delta = timedelta(hours=0)
        elif tz_offset_match:
            timezone_offset = tz_offset_match
            # Parse +/-HH:MM to timedelta
            sign = 1 if tz_offset_match[0] == '+' else -1
            tz_hours = int(tz_offset_match[1:3])
            tz_minutes = int(tz_offset_match[4:6])
            tz_delta = timedelta(hours=sign * tz_hours, minutes=sign * tz_minutes)

        # Build naive datetime first
        if fraction:
            microsecond = int(fraction.ljust(6, '0')[:6])
            naive_dt = datetime(year, month, day, hour, minute, second, microsecond)
        else:
            naive_dt = datetime(year, month, day, hour, minute, second)

        # Apply timezone offset to get UTC datetime for comparison
        # If the datetime is 01:30-04:00, that means it's 01:30 in a timezone that's 4 hours behind UTC
        # So in UTC, it would be 05:30. We subtract the offset to get UTC time.
        if tz_delta is not None:
            start_dt = naive_dt - tz_delta
        else:
            start_dt = naive_dt

        # Determine precision and end value
        if fraction:
            precision = "subsecond"
            end_dt = start_dt + timedelta(microseconds=1)
        elif second > 0:
            precision = "second"
            end_dt = start_dt + timedelta(seconds=1)
        elif minute > 0:
            precision = "minute"
            end_dt = start_dt + timedelta(minutes=1)
        elif hour > 0:
            precision = "hour"
            end_dt = start_dt + timedelta(hours=1)
        else:
            precision = "day"
            end_dt = start_dt + timedelta(days=1)

        # Use UTC datetime for normalization and comparisons
        normalized = start_dt.isoformat()

        return {
            "kind": "datetime",
            "precision": precision,
            "normalized": normalized,
            "start": self._format_datetime_iso(start_dt),
            "end": self._format_datetime_iso(end_dt),
            "is_partial": precision != "subsecond",
            "literal_type": "datetime",
            "original": original,
            "timezone_offset": timezone_offset  # Store for reference
        }

    def _parse_partial_datetime_literal_from_text(self, original: str, body: str, match) -> Optional[Dict[str, Any]]:
        """Parse partial dateTime literal (@YYYYT, @YYYY-MMT, @YYYY-MM-DDT)."""
        from datetime import datetime, timedelta

        year = int(match.group(1))
        month = int(match.group(2)) if match.group(2) else None
        day = int(match.group(3)) if match.group(3) else None

        if day is not None:
            # @YYYY-MM-DDT: day precision
            start_dt = datetime(year, month, day)
            end_dt = start_dt + timedelta(days=1)
            precision = "day"
            normalized = f"{year:04d}-{month:02d}-{day:02d}"
        elif month is not None:
            # @YYYY-MMT: month precision
            start_dt = datetime(year, month, 1)
            if month == 12:
                end_dt = datetime(year + 1, 1, 1)
            else:
                end_dt = datetime(year, month + 1, 1)
            precision = "month"
            normalized = f"{year:04d}-{month:02d}"
        else:
            # @YYYYT: year precision
            start_dt = datetime(year, 1, 1)
            end_dt = datetime(year + 1, 1, 1)
            precision = "year"
            normalized = f"{year:04d}"

        return {
            "kind": "datetime",
            "precision": precision,
            "normalized": normalized,
            "start": self._format_datetime_iso(start_dt),
            "end": self._format_datetime_iso(end_dt),
            "is_partial": True,
            "literal_type": "datetime",
            "original": original
        }

    def _format_datetime_iso(self, dt: datetime) -> str:
        """Format datetime to ISO string for SQL."""
        return dt.isoformat()

    def _format_time_iso(self, dt: datetime) -> str:
        """Format time to ISO string for SQL."""
        return dt.strftime("%H:%M:%S")

    def _build_temporal_conditions(
        self,
        left_info: Dict[str, Any],
        right_info: Dict[str, Any],
        operator: str,
        left_node: Optional[FHIRPathASTNode] = None,
        right_node: Optional[FHIRPathASTNode] = None
    ) -> Optional[tuple[str, str]]:
        """Build true/false SQL conditions for temporal comparisons.

        Args:
            left_info: Temporal metadata for left operand
            right_info: Temporal metadata for right operand
            operator: Comparison operator (<, <=, >, >=, =, !=)
            left_node: Optional AST node for left operand (for field references)
            right_node: Optional AST node for right operand (for field references)

        Returns:
            Tuple of (true_condition, false_condition) or None if not applicable

        For field references, we visit the node to get the SQL expression.
        For literals, we use the pre-computed start/end boundaries.
        """
        # Check for incompatible temporal types (e.g., date vs time)
        # According to FHIRPath spec, different temporal types cannot be compared
        left_kind = left_info.get("kind")
        right_kind = right_info.get("kind")

        # Date and Time are incompatible types - comparisons always return false/empty
        if (left_kind == "date" and right_kind == "time") or \
           (left_kind == "time" and right_kind == "date"):
            op = operator.strip()
            if op == "=":
                # Equality of date and time is always false
                return ("FALSE", "TRUE")
            elif op == "!=":
                # Inequality of date and time is always true
                return ("TRUE", "FALSE")
            else:
                # Ordering comparisons (<, >, <=, >=) return empty (NULL)
                return ("FALSE", "FALSE")

        left_range = self._temporal_range_to_sql(left_info, left_node)
        right_range = self._temporal_range_to_sql(right_info, right_node)

        if left_range is None or right_range is None:
            return None

        left_start, left_end = left_range
        right_start, right_end = right_range

        op = operator.strip()
        if op == "<":
            # True if left is entirely before right (no overlap)
            conditions = (
                f"({left_end} <= {right_start})",
                f"({left_start} >= {right_end})"
            )
        elif op == "<=":
            # True if left is before right OR overlaps with right
            # In interval terms: left_end <= right_end (left ends before or at right's end)
            conditions = (
                f"({left_end} <= {right_end})",
                f"({left_start} > {right_end})"
            )
        elif op == ">":
            # True if left is entirely after right (no overlap)
            conditions = (
                f"({left_start} >= {right_end})",
                f"({left_end} <= {right_start})"
            )
        elif op == ">=":
            # True if left is after right OR overlaps with right
            # In interval terms: left_start >= right_start (left starts after or at right's start)
            conditions = (
                f"({left_start} >= {right_start})",
                f"({left_end} < {right_start})"
            )
        elif op == "=" or op == "!=":
            # For equality/inequality, check if intervals overlap
            # Intervals overlap if: left_start < right_end AND left_end > right_start
            overlap_condition = f"({left_start} < {right_end} AND {left_end} > {right_start})"

            if op == "=":
                # Equal if intervals overlap (existential comparison)
                conditions = (overlap_condition, f"NOT ({overlap_condition})")
            else:  # !=
                # Not equal if intervals do NOT overlap
                conditions = (f"NOT ({overlap_condition})", overlap_condition)
        else:
            return None

        return conditions

    def _temporal_range_to_sql(
        self,
        temporal_info: Dict[str, Any],
        node: Optional[FHIRPathASTNode] = None
    ) -> Optional[tuple[str, str]]:
        """Convert temporal range start/end into SQL literal expressions.

        Args:
            temporal_info: Temporal metadata with kind, precision, start, end, is_field_reference
            node: Optional AST node (for field references that need to be visited)

        Returns:
            Tuple of (start_expr, end_expr) or None if not applicable

        For field references (is_field_reference=True), we visit the node to get the SQL
        expression and cast it appropriately. For literals, we use the pre-computed
        start/end values directly.
        """
        kind = temporal_info.get("kind")

        # Check if this is a field reference
        is_field_ref = temporal_info.get("is_field_reference", False)
        is_temporal_function = temporal_info.get("is_temporal_function", False)

        if is_field_ref and node:
            # Visit the node to get its SQL expression
            # This handles cases like Patient.birthDate where we need the actual SQL
            fragment = self.visit(node)

            # For date fields, we need to handle the comparison carefully
            # A date field like birthDate has day precision, so:
            # - start: The date itself (at midnight)
            # - end: The next day (exclusive)
            if kind == "date":
                # SP-110-008: json_extract_string returns the JSON value including quotes
                # (e.g., '"1974-12-25"'). We need to strip the quotes before casting to TIMESTAMP.
                # Try-catch approach: first try to parse as-is, if that fails strip quotes
                # Use a CASE expression to handle both quoted and unquoted values
                json_extracted = fragment.expression
                # Strip leading and trailing quotes from JSON string before casting
                # json_extract_string returns '"value"' - we need to extract just 'value'
                start_expr = f"CAST(CASE WHEN {json_extracted} LIKE '\"\"%' THEN NULL ELSE try_cast({json_extracted} AS TIMESTAMP) END AS TIMESTAMP)"
                # For quoted strings, strip the quotes and cast
                start_expr = f"CAST( CASE WHEN LEFT({json_extracted}, 1) = '\"' THEN SUBSTRING({json_extracted}, 2, LENGTH({json_extracted}) - 2) ELSE {json_extracted} END AS TIMESTAMP)"
                end_expr = f"({start_expr} + INTERVAL '1 day')"
            elif kind == "datetime":
                # For datetime fields, use the expression directly
                # The field already has second precision
                start_expr = fragment.expression
                end_expr = f"({fragment.expression} + INTERVAL '1 second')"
            elif kind == "time":
                # For time fields, use the expression directly
                start_expr = fragment.expression
                end_expr = f"({fragment.expression} + INTERVAL '1 second')"
            else:
                return None

            return start_expr, end_expr

        # SP-110-008: Handle temporal functions (now(), today(), timeOfDay())
        if is_temporal_function and node:
            # Visit the node to get its SQL expression
            fragment = self.visit(node)

            function_name = temporal_info.get("function_name", "")

            if function_name == "now":
                # now() returns a full precision timestamp
                # For comparison purposes, we treat it as an instant (no duration)
                # start = end = now() to indicate it's a point in time
                start_expr = fragment.expression
                end_expr = fragment.expression
            elif function_name == "today":
                # today() returns the current date at day precision
                # - start: Today at midnight
                # - end: Tomorrow at midnight
                # For comparisons with timestamps, we need to cast today() to timestamp range
                start_expr = f"CAST({fragment.expression} AS TIMESTAMP)"
                end_expr = f"CAST({fragment.expression} AS TIMESTAMP) + INTERVAL '1 day'"
            elif function_name == "timeofday":
                # timeOfDay() returns current time with millisecond precision
                # Treat as point in time (no duration)
                start_expr = fragment.expression
                end_expr = fragment.expression
            else:
                return None

            return start_expr, end_expr

        # For literals, use the pre-computed start/end values
        start_value = temporal_info.get("start")
        end_value = temporal_info.get("end")

        if not start_value or not end_value:
            return None

        if kind in {"date", "datetime"}:
            start_expr = self.dialect.generate_datetime_literal(str(start_value))
            end_expr = self.dialect.generate_datetime_literal(str(end_value))
        elif kind == "time":
            start_expr = self.dialect.generate_time_literal(str(start_value))
            end_expr = self.dialect.generate_time_literal(str(end_value))
        else:
            return None

        return start_expr, end_expr

    def visit_conditional(self, node: ConditionalNode) -> SQLFragment:
        """Translate conditional expressions to SQL.

        Converts FHIRPath conditional expressions (if-then-else, case) to SQL
        CASE statements or conditional logic.

        Args:
            node: ConditionalNode representing a conditional expression

        Returns:
            SQLFragment containing the conditional SQL

        Raises:
            NotImplementedError: Implementation pending in future tasks

        Example (future implementation):
            Input: ConditionalNode with condition and branches
            Output: SQLFragment with SQL CASE statement
        """
        raise NotImplementedError(
            "visit_conditional implementation pending in future sprint"
        )

    def visit_aggregation(self, node: AggregationNode) -> SQLFragment:
        """Translate aggregation functions to SQL.

        Converts FHIRPath aggregation functions (count(), sum(), avg(), min(), max())
        to SQL aggregation expressions. Aggregation functions operate on collections
        and return a single scalar value.

        Population-First Design:
            Generates aggregate SQL that can be used in population-scale queries.
            For array collections, combines with UNNEST to aggregate over array elements.
            For scalar values, applies aggregation to grouped resource collections.

        Supported Aggregation Functions:
            - count(): Returns number of elements in collection
            - sum(): Returns sum of numeric values in collection
            - avg(): Returns average of numeric values in collection
            - min(): Returns minimum value in collection
            - max(): Returns maximum value in collection

        Args:
            node: AggregationNode representing an aggregation function

        Returns:
            SQLFragment containing the aggregation SQL with is_aggregate=True

        Raises:
            ValueError: If aggregation function is unsupported

        Examples:
            Input: Patient.name.count()
            Context: parent_path = ["name"]

            Output SQL (DuckDB):
                COUNT(json_array_length(json_extract(resource, '$.name')))

            Input: Observation.value.ofType(Quantity).value.sum()
            Context: parent_path = ["value", "value"]

            Output SQL:
                SUM(CAST(json_extract_string(resource, '$.value.value') AS DECIMAL))

            Input: Patient.address.count()

            Output SQL (PostgreSQL):
                COUNT(jsonb_array_length(jsonb_extract_path(resource, 'address')))
        """
        logger.debug(
            f"Translating aggregation: function={node.aggregation_function}, "
            f"type={node.aggregation_type}"
        )

        # Get aggregation function type
        agg_type = node.aggregation_type.lower()

        # Validate aggregation function
        valid_functions = {"count", "sum", "avg", "min", "max"}
        if agg_type not in valid_functions:
            raise ValueError(
                f"Unsupported aggregation function: {node.aggregation_function}. "
                f"Supported functions: {', '.join(valid_functions)}"
            )

        # Get the current path to determine what we're aggregating
        json_path = self.context.get_json_path()

        logger.debug(f"JSON path for aggregation: {json_path}")

        # For count(), we count array elements or non-null values
        if agg_type == "count":
            # SP-110-GROUP-BY-FIX: Check if we're counting a filtered collection (from where())
            # When count() is called after where(), we need to count the filtered rows,
            # not the JSON array length. Check if the previous fragment has where_filter.
            has_where_filter = False
            if self.fragments:
                prev_fragment = self.fragments[-1]
                has_where_filter = bool(prev_fragment.metadata.get("where_filter"))
                logger.debug(
                    f"SP-110-GROUP-BY-FIX: count() detected previous where_filter={has_where_filter}"
                )

            # Check if we have a path (counting elements in a field)
            if json_path and json_path != "$" and not has_where_filter:
                # Retrieve the JSON value so we can inspect its type before counting.
                json_value_expr = self.dialect.extract_json_object(
                    column=self.context.current_table,
                    path=json_path
                )

                # Determine the JSON type (array vs scalar/object) in a dialect-safe way.
                json_type_expr = self.dialect.get_json_type(json_value_expr)

                # Generate dialect-specific expression for counting array elements.
                array_length_expr = self.dialect.get_json_array_length(
                    column=self.context.current_table,
                    path=json_path
                )

                # Handle null/empty collections and single values per FHIRPath specification:
                # - Null or missing values produce 0
                # - Arrays return their length
                # - Scalar/object values return 1 when present
                sql_expr = (
                    "COALESCE("
                    "CASE "
                    f"WHEN {json_value_expr} IS NULL THEN 0 "
                    f"WHEN LOWER({json_type_expr}) = 'array' THEN {array_length_expr} "
                    "ELSE 1 "
                    "END, 0)"
                )

                logger.debug(f"Generated count SQL: {sql_expr}")

            else:
                # No path - check if we have a pending fragment result (from chained expression)
                # SP-022-018: When count() is called on a non-resource collection (like a union,
                # combine, or split result), we need to count elements in that collection,
                # not count rows. The pending_fragment_result contains the SQL expression
                # that produces the collection.
                #
                # We need to distinguish between:
                # 1. Collection expressions (union, combine, split): "(COALESCE(...", "CASE WHEN..."
                #    These are self-contained subqueries that produce JSON arrays
                # 2. Column aliases (from UNNEST): "name_item", "address_item"
                #    These are simple identifiers that reference columns in the CTE chain
                #
                # We should only use pending_fragment_result for case 1 (collection expressions)
                # SP-100-fix: pending_fragment_result is a 3-tuple (expression, parent_path, is_multi_item)
                pending_result = self.context.pending_fragment_result
                # Extract expression from tuple if it's a tuple, otherwise use as-is
                pending_expr = pending_result[0] if pending_result and isinstance(pending_result, tuple) else pending_result
                pending_upper = pending_expr.upper().strip() if pending_expr else ""
                is_collection_expr = (
                    pending_expr is not None and (
                        pending_expr.strip().startswith("(") or  # Subquery or grouped expression
                        pending_expr.strip().startswith("COALESCE") or  # Combine/union result
                        pending_expr.strip().startswith("CASE") or  # Conditional expression
                        "SELECT" in pending_upper or  # Contains SQL subquery
                        pending_upper.startswith("STRING_SPLIT") or  # split() result
                        pending_upper.startswith("REGEXP_SPLIT") or  # PostgreSQL split
                        pending_upper.startswith("JSON_ARRAY")  # JSON array constructor
                    )
                )

                if is_collection_expr:
                    # SP-022-019: Check if this is a SELECT statement from select() function
                    # In this case, the result is stored in the 'result' column of the CTE,
                    # and we should count elements in that result array.
                    if pending_upper.startswith("SELECT"):
                        # The previous fragment is a full SELECT (from select() function).
                        # The result will be in the 'result' column of the CTE.
                        # Use the result column to count elements.
                        result_column = "result"

                        # Get the JSON type to determine if it's an array
                        json_type_expr = self.dialect.get_json_type(result_column)

                        # Get the array length
                        length_expr = self.dialect.get_json_array_length(result_column)

                        sql_expr = (
                            "COALESCE("
                            "CASE "
                            f"WHEN {result_column} IS NULL THEN 0 "
                            f"WHEN LOWER({json_type_expr}) = 'array' THEN {length_expr} "
                            "ELSE 1 "
                            "END, 0)"
                        )

                        # Clear the pending result since we've handled it
                        self.context.pending_fragment_result = None

                        logger.debug(f"Generated count SQL for select() result: {sql_expr}")

                        # SP-022-019: Use function name "array_length" instead of "count"
                        # to prevent CTEAssembler from replacing this with COUNT(*)
                        return SQLFragment(
                            expression=sql_expr,
                            source_table=self.context.current_table,
                            requires_unnest=False,
                            is_aggregate=False,
                            dependencies=[],
                            metadata={"function": "array_length", "result_type": "integer"}
                        )

                    # Otherwise, it's a collection expression (union, combine, etc.)
                    # SP-100-fix: Use pending_expr (extracted from tuple)
                    collection_expr = pending_expr

                    # Get the JSON type to determine if it's an array
                    json_type_expr = self.dialect.get_json_type(collection_expr)

                    # Get the array length
                    length_expr = self.dialect.get_json_array_length(collection_expr)

                    # Generate count expression that handles arrays and scalars
                    sql_expr = (
                        "COALESCE("
                        "CASE "
                        f"WHEN {collection_expr} IS NULL THEN 0 "
                        f"WHEN LOWER({json_type_expr}) = 'array' THEN {length_expr} "
                        "ELSE 1 "  # Non-null scalar counts as 1
                        "END, 0)"
                    )

                    # Clear the pending result since we've used it
                    self.context.pending_fragment_result = None

                    logger.debug(f"Generated count SQL for pending collection: {sql_expr}")

                    # SP-022-018: When counting a collection, we're computing array length
                    # per row, not aggregating across rows. This is NOT a SQL aggregate.
                    return SQLFragment(
                        expression=sql_expr,
                        source_table=self.context.current_table,
                        requires_unnest=False,
                        is_aggregate=False,  # Not a SQL aggregate - just array length
                        dependencies=[],
                        metadata={"function": "count", "result_type": "integer"}
                    )
                else:
                    # No collection expression (might be a column alias or no pending result)
                    # Use COUNT(*) and let CTE assembler handle aggregation
                    sql_expr = "COUNT(*)"
                    logger.debug("Generated count(*) SQL")

            # SP-110-GROUP-BY-FIX: Build metadata for count() after where()
            # When counting filtered rows, exclude ordering columns from GROUP BY
            count_metadata = {"function": "count", "result_type": "integer"}
            if has_where_filter:
                count_metadata["exclude_order_from_group_by"] = True
                logger.debug(
                    "SP-110-GROUP-BY-FIX: Setting exclude_order_from_group_by=True for count() after where()"
                )

            return SQLFragment(
                expression=sql_expr,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=[],
                metadata=count_metadata
            )

        # For sum(), avg(), min(), max() - operate on numeric/comparable values
        else:
            # Extract the field value
            field_expr = self.dialect.extract_json_field(
                column=self.context.current_table,
                path=json_path
            )

            # For sum() and avg(), cast to numeric type
            if agg_type in ("sum", "avg"):
                # Cast to DECIMAL for numeric aggregation
                field_expr = f"CAST({field_expr} AS DECIMAL)"

            # Generate the aggregate function SQL using dialect method
            sql_expr = self.dialect.generate_aggregate_function(
                function_name=agg_type,
                expression=field_expr,
                filter_condition=None,
                distinct=False
            )

        logger.debug(f"Generated {agg_type} SQL: {sql_expr}")

        # Determine result type based on aggregation function
        result_type = "decimal" if agg_type in ("sum", "avg") else agg_type

        return SQLFragment(
            expression=sql_expr,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=True,
            dependencies=[],
            metadata={"function": agg_type, "result_type": result_type}
        )

    def _translate_count_function_call(self, node: FunctionCallNode) -> SQLFragment:
        """Handle count() when represented as a function call node.

        SP-110-004 FIX: When count() is called on a where() result (or other filtered
        collection), we need to count the filtered rows, not get the JSON array length.
        This happens when the previous fragment has where_filter metadata or when
        the collection_expr is a simple column reference from a CTE.
        """
        collection_expr, dependencies, literal_value, snapshot, target_ast, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]
        try:
            if literal_value is not None:
                if literal_value is None:
                    return SQLFragment(
                        expression="0",
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "count", "result_type": "integer"}
                    )
                if isinstance(literal_value, (list, tuple, set)):
                    return SQLFragment(
                        expression=str(len(literal_value)),
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "count", "result_type": "integer"}
                    )

            if not collection_expr:
                raise ValueError("count() requires a resolvable target expression")

            # SP-110-004: Check if the previous fragment has where_filter or subset_filter metadata
            # This indicates we're counting a filtered collection, not a raw JSON array
            has_previous_filter = False
            previous_fragment_result_col = None
            if self.fragments:
                prev_fragment = self.fragments[-1]
                has_previous_filter = prev_fragment.metadata.get("where_filter") or prev_fragment.metadata.get("subset_filter")
                previous_fragment_result_col = prev_fragment.metadata.get("result_alias")

            logger.debug(f"SP-110-004 count(): has_previous_filter={has_previous_filter}")

            # SP-110-004: Check if collection_expr is a simple column reference (like name_item)
            # If so, and we have a filter, count the rows instead of getting JSON array length
            is_simple_column_ref = self._is_simple_column_reference(collection_expr)

            logger.debug(f"SP-110-004 count(): is_simple_column_ref={is_simple_column_ref}")

            if has_previous_filter and is_simple_column_ref:
                # Count filtered rows using COUNT(*) with the filter applied
                # The CTEManager will handle the WHERE clause application
                count_sql = f"COUNT(*)"

                return SQLFragment(
                    expression=count_sql,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=True,  # This is an aggregate operation
                    dependencies=list(dict.fromkeys(dependencies)),
                    metadata={"function": "count", "result_type": "integer", "exclude_order_from_group_by": True}
                )

            # Default: count JSON array length
            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            length_expr = self.dialect.get_json_array_length(normalized_expr)
            count_sql = (
                "("
                "CASE "
                f"WHEN {normalized_expr} IS NULL THEN 0 "
                f"ELSE {length_expr} "
                "END"
                ")"
            )

            return SQLFragment(
                expression=count_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "count", "result_type": "integer"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_sum(self, node: FunctionCallNode) -> SQLFragment:
        """Translate sum() aggregation function to SQL.

        Generates SQL for summing numeric values in a collection.
        Handles empty collections and null values per FHIRPath spec.

        Args:
            node: FunctionCallNode representing sum() function call

        Returns:
            SQLFragment with sum aggregation SQL and is_aggregate=True

        Raises:
            ValueError: If target expression cannot be resolved
        """
        value_expr, dependencies, literal_value, snapshot, target_ast, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]
        try:
            # Handle literal values
            if literal_value is not None:
                if literal_value is None or isinstance(literal_value, (list, tuple)) and len(literal_value) == 0:
                    return SQLFragment(
                        expression="0",
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "sum", "result_type": "decimal"}
                    )
                if isinstance(literal_value, (list, tuple, set)):
                    # Sum numeric values in the list
                    total = sum(v for v in literal_value if isinstance(v, (int, float)) and v is not None)
                    return SQLFragment(
                        expression=str(total),
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "sum", "result_type": "decimal"}
                    )
                if isinstance(literal_value, (int, float)):
                    return SQLFragment(
                        expression=str(literal_value),
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "sum", "result_type": "decimal"}
                    )

            if not value_expr and not target_path:
                raise ValueError("sum() requires a resolvable target expression")

            # Get JSON path from context (for chained expressions like Patient.name.given.sum())
            json_path = self.context.get_json_path()
            field_expr = self.dialect.extract_json_field(
                column=source_table,
                path=json_path
            )

            # Cast to DECIMAL for numeric aggregation
            field_expr = f"CAST({field_expr} AS DECIMAL)"

            # Generate sum() SQL
            sql_expr = self.dialect.generate_aggregate_function(
                function_name="sum",
                expression=field_expr,
                filter_condition=None,
                distinct=False
            )

            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "sum", "result_type": "decimal"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_avg(self, node: FunctionCallNode) -> SQLFragment:
        """Translate avg() aggregation function to SQL.

        Generates SQL for averaging numeric values in a collection.
        Handles empty collections and null values per FHIRPath spec.

        Args:
            node: FunctionCallNode representing avg() function call

        Returns:
            SQLFragment with avg aggregation SQL and is_aggregate=True

        Raises:
            ValueError: If target expression cannot be resolved
        """
        value_expr, dependencies, literal_value, snapshot, target_ast, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]
        try:
            # Handle literal values
            if literal_value is not None:
                if literal_value is None or isinstance(literal_value, (list, tuple)) and len(literal_value) == 0:
                    return SQLFragment(
                        expression="0",
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "avg", "result_type": "decimal"}
                    )
                if isinstance(literal_value, (list, tuple, set)):
                    # Average numeric values in the list
                    numeric_values = [v for v in literal_value if isinstance(v, (int, float)) and v is not None]
                    if numeric_values:
                        avg = sum(numeric_values) / len(numeric_values)
                        return SQLFragment(
                            expression=str(avg),
                            source_table=source_table,
                            requires_unnest=False,
                            is_aggregate=False,
                            dependencies=list(dict.fromkeys(dependencies)),
                            metadata={"function": "avg", "result_type": "decimal"}
                        )
                    return SQLFragment(
                        expression="0",
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "avg", "result_type": "decimal"}
                    )
                if isinstance(literal_value, (int, float)):
                    return SQLFragment(
                        expression=str(literal_value),
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "avg", "result_type": "decimal"}
                    )

            if not value_expr and not target_path:
                raise ValueError("avg() requires a resolvable target expression")

            # Get JSON path from context (for chained expressions like Patient.name.given.avg())
            json_path = self.context.get_json_path()
            field_expr = self.dialect.extract_json_field(
                column=source_table,
                path=json_path
            )

            # Cast to DECIMAL for numeric aggregation
            field_expr = f"CAST({field_expr} AS DECIMAL)"

            # Generate avg() SQL
            sql_expr = self.dialect.generate_aggregate_function(
                function_name="avg",
                expression=field_expr,
                filter_condition=None,
                distinct=False
            )

            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "avg", "result_type": "decimal"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_min(self, node: FunctionCallNode) -> SQLFragment:
        """Translate min() aggregation function to SQL.

        Generates SQL for finding minimum value in a collection.
        Handles empty collections and null values per FHIRPath spec.

        Args:
            node: FunctionCallNode representing min() function call

        Returns:
            SQLFragment with min aggregation SQL and is_aggregate=True

        Raises:
            ValueError: If target expression cannot be resolved
        """
        value_expr, dependencies, literal_value, snapshot, target_ast, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]
        try:
            # Handle literal values
            if literal_value is not None:
                if literal_value is None or isinstance(literal_value, (list, tuple)) and len(literal_value) == 0:
                    return SQLFragment(
                        expression="NULL",
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "min", "result_type": "any"}
                    )
                if isinstance(literal_value, (list, tuple, set)):
                    # Find minimum value in the list
                    valid_values = [v for v in literal_value if v is not None]
                    if valid_values:
                        min_val = min(valid_values)
                        return SQLFragment(
                            expression=f"'{min_val}'" if isinstance(min_val, str) else str(min_val),
                            source_table=source_table,
                            requires_unnest=False,
                            is_aggregate=False,
                            dependencies=list(dict.fromkeys(dependencies)),
                            metadata={"function": "min", "result_type": "any"}
                        )
                    return SQLFragment(
                        expression="NULL",
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "min", "result_type": "any"}
                    )
                return SQLFragment(
                    expression=f"'{literal_value}'" if isinstance(literal_value, str) else str(literal_value),
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=list(dict.fromkeys(dependencies)),
                    metadata={"function": "min", "result_type": "any"}
                )

            if not value_expr and not target_path:
                raise ValueError("min() requires a resolvable target expression")

            # Get JSON path from context (for chained expressions like Patient.name.given.min())
            json_path = self.context.get_json_path()
            field_expr = self.dialect.extract_json_field(
                column=source_table,
                path=json_path
            )

            # Generate min() SQL
            sql_expr = self.dialect.generate_aggregate_function(
                function_name="min",
                expression=field_expr,
                filter_condition=None,
                distinct=False
            )

            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "min", "result_type": "any"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_max(self, node: FunctionCallNode) -> SQLFragment:
        """Translate max() aggregation function to SQL.

        Generates SQL for finding maximum value in a collection.
        Handles empty collections and null values per FHIRPath spec.

        Args:
            node: FunctionCallNode representing max() function call

        Returns:
            SQLFragment with max aggregation SQL and is_aggregate=True

        Raises:
            ValueError: If target expression cannot be resolved
        """
        value_expr, dependencies, literal_value, snapshot, target_ast, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]
        try:
            # Handle literal values
            if literal_value is not None:
                if literal_value is None or isinstance(literal_value, (list, tuple)) and len(literal_value) == 0:
                    return SQLFragment(
                        expression="NULL",
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "max", "result_type": "any"}
                    )
                if isinstance(literal_value, (list, tuple, set)):
                    # Find maximum value in the list
                    valid_values = [v for v in literal_value if v is not None]
                    if valid_values:
                        max_val = max(valid_values)
                        return SQLFragment(
                            expression=f"'{max_val}'" if isinstance(max_val, str) else str(max_val),
                            source_table=source_table,
                            requires_unnest=False,
                            is_aggregate=False,
                            dependencies=list(dict.fromkeys(dependencies)),
                            metadata={"function": "max", "result_type": "any"}
                        )
                    return SQLFragment(
                        expression="NULL",
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=list(dict.fromkeys(dependencies)),
                        metadata={"function": "max", "result_type": "any"}
                    )
                return SQLFragment(
                    expression=f"'{literal_value}'" if isinstance(literal_value, str) else str(literal_value),
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=list(dict.fromkeys(dependencies)),
                    metadata={"function": "max", "result_type": "any"}
                )

            if not value_expr and not target_path:
                raise ValueError("max() requires a resolvable target expression")

            # Get JSON path from context (for chained expressions like Patient.name.given.max())
            json_path = self.context.get_json_path()
            field_expr = self.dialect.extract_json_field(
                column=source_table,
                path=json_path
            )

            # Generate max() SQL
            sql_expr = self.dialect.generate_aggregate_function(
                function_name="max",
                expression=field_expr,
                filter_condition=None,
                distinct=False
            )

            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "max", "result_type": "any"}
            )
        finally:
            self._restore_context(snapshot)

    def _get_json_path_from_target(self, target_path: Optional[List[str]]) -> str:
        """Helper method to construct JSON path from target path list.

        Args:
            target_path: List of path components

        Returns:
            JSON path string (e.g., "$.name.given")
        """
        if not target_path:
            return "$"
        return "$." + ".".join(target_path)

    def _translate_converts_to_function(self, node: FunctionCallNode, target_type: str) -> SQLFragment:
        """Translate convertsTo*() functions to SQL boolean expressions."""
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                result = self._evaluate_literal_converts_to(literal_value, target_type)
                sql_expr = "TRUE" if result else "FALSE"
                return SQLFragment(
                    expression=sql_expr,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    metadata={
                        "function": f"convertsTo{target_type}",
                        "result_type": "boolean"
                    }
                )

            if not value_expr:
                raise ValueError(
                    f"Unable to resolve target expression for {node.function_name}()"
                )

            sql_expr = self._build_converts_to_expression(value_expr, target_type)
            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies,
                metadata={
                    "function": f"convertsTo{target_type}",
                    "result_type": "boolean"
                }
            )
        finally:
            self._restore_context(snapshot)

    def _translate_extension_function(self, node: FunctionCallNode) -> SQLFragment:
        """Translate extension(url) function to SQL array filtering.

        SP-100-EXT: Enhanced to handle EnhancedASTNode arguments that haven't
        been converted to LiteralNode yet. The parser creates a nested structure:
        TermExpression > literal > literal for string arguments.
        """
        if len(node.arguments) != 1:
            raise ValueError(
                "extension() function requires exactly 1 argument (extension URL)"
            )

        url_arg = node.arguments[0]

        # SP-100-EXT: Try to extract URL from various node types
        extension_url = None

        # Case 1: Already converted LiteralNode
        if isinstance(url_arg, LiteralNode) and isinstance(url_arg.value, str):
            extension_url = url_arg.value
        # Case 2: IdentifierNode
        elif isinstance(url_arg, IdentifierNode) and url_arg.identifier:
            extension_url = url_arg.identifier.strip('`')
        # Case 3: EnhancedASTNode - extract from nested structure
        elif hasattr(url_arg, 'text'):
            # The text contains the URL with quotes, e.g., "'http://example.com/test'"
            text = url_arg.text.strip()
            # Remove surrounding quotes
            if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
                extension_url = text[1:-1]
            else:
                extension_url = text

        if not extension_url:
            raise ValueError("extension() argument must be a string literal or identifier")

        (
            _,
            dependencies,
            _,
            snapshot,
            _,
            target_path,
        ) = self._resolve_function_target(node)

        try:
            path_components = list(target_path or [])
            path_components.append("extension")
            extension_path = self._build_json_path_from_components(path_components)

            extension_source = self.dialect.extract_json_object(
                column=snapshot["current_table"],
                path=extension_path
            )

            filtered_extensions = self.dialect.filter_extension_by_url(
                extension_source,
                extension_url
            )

            remainder_path = self._extract_path_after_function(node.text, node.function_name)
            remainder_components = self._split_function_path(remainder_path)

            result_expression = filtered_extensions
            if remainder_components:
                components = remainder_components
                if components and components[0] == "value":
                    result_expression = self.dialect.extract_extension_values(result_expression)
                    components = components[1:]

                for component in components:
                    if component.startswith("ofType(") and component.endswith(")"):
                        target = component[len("ofType("):-1]
                        canonical_target = self._resolve_canonical_type(target)
                        result_expression = self.dialect.generate_collection_type_filter(
                            result_expression,
                            canonical_target
                        )
                    else:
                        result_expression = self.dialect.project_json_array(
                            result_expression,
                            [component]
                        )

            fragment_dependencies = dependencies.copy() if dependencies else []

            return SQLFragment(
                expression=result_expression,
                source_table=snapshot["current_table"],
                requires_unnest=False,
                is_aggregate=False,
                dependencies=fragment_dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_conforms_to(self, node: FunctionCallNode) -> SQLFragment:
        """Translate conformsTo() profile membership function.

        FHIRPath SP-110-011: conformsTo() supports two URL patterns:
        1. StructureDefinition URLs: http://hl7.org/fhir/StructureDefinition/{ResourceType}
           - Extract resource type from URL
           - Compare against resourceType field
        2. Profile URLs: Any other URL
           - Check if URL exists in meta.profile array

        Handles EnhancedASTNode arguments that haven't been converted to LiteralNode yet.
        The parser creates a nested structure: TermExpression > literal > literal for
        string arguments.
        """
        if not node.arguments or len(node.arguments) != 1:
            raise ValueError("conformsTo() requires exactly one argument (profile URL)")

        (
            resource_expr,
            dependencies,
            _,
            snapshot,
            _,
            _,
        ) = self._resolve_function_target(node)

        source_table = snapshot["current_table"]

        try:
            metadata = {"function": "conformsTo"}

            # SP-110-011: Try to extract URL from various node types
            url_value = None
            url_arg = node.arguments[0]

            # Case 1: Already converted LiteralNode
            if isinstance(url_arg, LiteralNode) and isinstance(url_arg.value, str):
                url_value = url_arg.value
            # Case 2: EnhancedASTNode - extract from text attribute
            elif hasattr(url_arg, 'text'):
                # The text contains the URL with quotes, e.g., "'http://hl7.org/fhir/StructureDefinition/Patient'"
                text = url_arg.text.strip()
                # Remove surrounding quotes
                if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
                    url_value = text[1:-1]
                else:
                    url_value = text

            if url_value:
                metadata["profile_url"] = url_value

                # SP-110-011: Detect StructureDefinition URLs
                # Pattern: http://hl7.org/fhir/StructureDefinition/{ResourceType}
                if '/StructureDefinition/' in url_value:
                    # Extract resource type from URL
                    # e.g., "http://hl7.org/fhir/StructureDefinition/Patient" -> "Patient"
                    parts = url_value.split('/StructureDefinition/')
                    if len(parts) == 2:
                        resource_type = parts[1].split('/')[0]  # Get last segment, ignore trailing paths

                        # Compare resourceType field with extracted type
                        resource_type_expr = self.dialect.extract_json_field(
                            resource_expr,
                            "resourceType"
                        )

                        # Properly escape the resource type string for SQL comparison
                        escaped_type = resource_type.replace("'", "''")

                        result_sql = (
                            "CASE "
                            f"WHEN {resource_expr} IS NULL THEN false "
                            f"WHEN {resource_type_expr} IS NULL THEN false "
                            f"ELSE {resource_type_expr} = '{escaped_type}' "
                            "END"
                        )

                        return SQLFragment(
                            expression=result_sql,
                            source_table=source_table,
                            requires_unnest=False,
                            is_aggregate=False,
                            dependencies=list(dependencies or []),
                            metadata=metadata,
                        )

            # For non-literal arguments or non-StructureDefinition URLs,
            # check against meta.profile array (original behavior)
            profile_fragment = self.visit(url_arg)
            profile_dependencies = getattr(profile_fragment, "dependencies", []) or []
            combined_dependencies = list(dependencies or []) + list(profile_dependencies)

            profiles_expr = self.dialect.extract_json_object(
                resource_expr,
                "$.meta.profile",
            )
            normalized_profiles = self._normalize_collection_expression(profiles_expr)
            membership_check = self.dialect.json_array_contains(
                normalized_profiles,
                profile_fragment.expression,
            )

            result_sql = (
                "CASE "
                f"WHEN {resource_expr} IS NULL THEN false "
                f"ELSE {membership_check} "
                "END"
            )

            return SQLFragment(
                expression=result_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=combined_dependencies,
                metadata=metadata,
            )
        finally:
            self._restore_context(snapshot)

    def _translate_iif(self, node: FunctionCallNode) -> SQLFragment:
        """
        Translate iif() function to SQL CASE expression with validation.

        The iif() function implements conditional logic: iif(criterion, true-result [, false-result])

        FHIRPath Specification Requirements:
        1. Criterion must be a boolean expression (semantic validation)
        2. When used as collection.iif(), collection must have 0 or 1 items (execution validation)
        3. False-result parameter is optional; if omitted and criterion is false, returns empty collection
        4. The function evaluates only the branch that is taken (short-circuit evaluation)

        Args:
            node: FunctionCallNode representing iif() function call

        Returns:
            SQLFragment with CASE expression SQL

        Raises:
            FHIRPathValidationError: If criterion is not a boolean expression (semantic error)
            FHIRPathEvaluationError: If called on multi-item collection (execution error)

        Example:
            Input: iif(Patient.name.exists(), 'named', 'unnamed')
            Output SQL: CASE WHEN (json_array_length(...) > 0) THEN 'named' ELSE 'unnamed' END

            Input: iif(false, 'true-result')
            Output SQL: CASE WHEN FALSE THEN 'true-result' ELSE NULL END

            Input: {}.iif(true, 'result')
            Output SQL: CASE WHEN (json_array_length(...) = 0 OR ... = 1)
                        THEN (CASE WHEN TRUE THEN 'result' ELSE NULL END)
                        ELSE NULL END  -- Multi-item validation
        """
        logger.debug(f"Translating iif() function with {len(node.arguments)} arguments")

        # Validate argument count: 2 or 3 arguments (criterion, true-result, optional false-result)
        if len(node.arguments) < 2 or len(node.arguments) > 3:
            raise ValueError(
                f"iif() function requires 2 or 3 arguments (criterion, true-result [, false-result]), "
                f"got {len(node.arguments)}"
            )

        # SP-110-004: Save and clear _pending_target_is_multi_item flag before resolving target
        # This ensures that nested function calls (like toString() inside iif arguments)
        # don't incorrectly set this flag for the outer iif() call
        saved_pending_multi_item = getattr(self, '_pending_target_is_multi_item', False)
        self._pending_target_is_multi_item = False

        # Get function target (the collection iif is called on, if any)
        (
            target_expr,
            dependencies,
            _,
            snapshot,
            target_ast,
            target_path,
        ) = self._resolve_function_target(node)

        # SP-110-004: Capture the _pending_target_is_multi_item flag IMMEDIATELY after
        # _resolve_function_target returns, before processing any arguments.
        # This ensures the flag reflects whether the TARGET of iif() is a multi-item
        # collection, not whether nested function calls have multi-item collections.
        target_is_multi_item = getattr(self, '_pending_target_is_multi_item', False)

        # SP-110-004: Only use target_is_multi_item if there's an actual target
        # For standalone iif(...) calls without a target, this flag should be False
        if not target_expr and not target_ast and not target_path:
            target_is_multi_item = False
        elif not target_is_multi_item and target_ast:
            # Check if target_ast is a multi-item collection
            target_is_multi_item = self._is_multi_item_collection(target_ast)

        try:
            # Extract arguments
            criterion_node = node.arguments[0]
            true_result_node = node.arguments[1]
            false_result_node = node.arguments[2] if len(node.arguments) == 3 else None

            # Validate criterion is boolean (semantic validation - testIif6)
            # This is a compile-time check based on the AST
            if not self._is_boolean_expression(criterion_node):
                raise FHIRPathValidationError(
                    message=f"iif() criterion must be a boolean expression, got: {criterion_node.node_type}",
                    validation_rule="iif_criterion_must_be_boolean"
                )

            # FHIRPath iif() criterion semantics per specification:
            # 1. Empty collection → return alternative result (evaluates to FALSE)
            # 2. Single boolean → use it directly
            # 3. Multi-item collection → error (single-value boolean required)
            criterion_is_multi_item = self._is_multi_item_collection_excluding_empty_unions(criterion_node)

            # SP-110: Check if criterion is a multi-item collection before evaluation
            # Per FHIRPath spec, iif() criterion must be a single-value boolean expression
            # Multi-item collections like (1 | 2 | 3) are not valid
            if criterion_is_multi_item:
                raise FHIRPathTypeError(
                    message="iif() criterion must be a single-value boolean expression, got multi-item collection"
                )

            # Translate criterion to SQL
            criterion_fragment = self.visit(criterion_node)
            criterion_sql = criterion_fragment.expression

            # Handle empty collections: {} should evaluate to FALSE
            criterion_is_empty_collection = (
                criterion_fragment.metadata.get('literal_type') == 'empty_collection'
            )

            if criterion_is_empty_collection:
                # Empty collection {} evaluates to FALSE in boolean context
                # Directly return the false-result branch
                if false_result_node:
                    false_result_fragment = self.visit(false_result_node)
                    return SQLFragment(
                        expression=false_result_fragment.expression,
                        source_table=snapshot["current_table"],
                        requires_unnest=false_result_fragment.requires_unnest,
                        is_aggregate=false_result_fragment.is_aggregate,
                        dependencies=false_result_fragment.dependencies,
                        metadata={"function": "iif", "optimized": "empty_collection_false"}
                    )
                else:
                    # No false-result, return NULL (empty collection)
                    return SQLFragment(
                        expression="NULL",
                        source_table=snapshot["current_table"],
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=[],
                        metadata={"function": "iif", "optimized": "empty_collection_null"}
                    )

            # Translate true-result to SQL
            true_result_fragment = self.visit(true_result_node)
            true_result_sql = true_result_fragment.expression

            # Translate false-result to SQL (or NULL if omitted)
            if false_result_node:
                false_result_fragment = self.visit(false_result_node)
                false_result_sql = false_result_fragment.expression
            else:
                false_result_sql = "NULL"

            # SP-110-AUTOPILOT: Enhanced type coercion for iif() CASE expressions
            # When branches have different types (e.g., DOUBLE vs BOOLEAN, VARCHAR vs BOOLEAN),
            # cast both to VARCHAR for compatibility. This prevents "Cannot mix values of type
            # X and Y in CASE expression" errors.
            coerced_result_type = None  # Initialize before conditional block

            if false_result_node:
                # Check if we need type coercion by examining fragment metadata
                true_result_type = true_result_fragment.metadata.get('result_type', '')
                false_result_type = false_result_fragment.metadata.get('result_type', '')

                # SP-110-AUTOPILOT: Comprehensive type detection
                # Detect various type patterns in SQL expressions
                def detect_sql_type(sql_expr: str, metadata_type: str = '') -> str:
                    """Detect the SQL type of an expression from patterns and metadata."""
                    # Start with metadata type if available
                    if metadata_type:
                        return metadata_type

                    sql_upper = sql_expr.upper()

                    # Boolean literals
                    if sql_upper.strip() in ('TRUE', 'FALSE'):
                        return 'boolean'

                    # Numeric type casts (TRY_CAST AS DECIMAL, CAST AS DOUBLE, etc.)
                    # This handles arithmetic operations like 1/0 which generate DECIMAL casts
                    if 'DECIMAL' in sql_upper or 'DOUBLE' in sql_upper or 'NUMERIC' in sql_upper:
                        return 'numeric'

                    # Arithmetic operators in expressions (indicate numeric result)
                    # Check for division, multiplication, addition, subtraction
                    if any(op in sql_upper for op in (' / ', ' * ', ' + ', ' - ', ') / ', ') * ', ') + ', ') - ')):
                        return 'numeric'

                    # String/cast operations (toString, CAST AS VARCHAR, etc.)
                    if 'TO_STRING' in sql_upper or ('CAST' in sql_upper and 'VARCHAR' in sql_upper):
                        return 'varchar'

                    # String literals (quoted)
                    if sql_expr.strip().startswith("'") or sql_expr.strip().startswith('"'):
                        return 'varchar'

                    # Numeric functions
                    if any(p in sql_upper for p in ['AVG(', 'SUM(', 'COUNT(', 'MIN(', 'MAX(']):
                        # These can return numeric or varchar depending on context
                        if 'TRY_CAST' in sql_upper and 'VARCHAR' in sql_upper:
                            return 'varchar'
                        return 'numeric'

                    # Numeric literals (digits with optional decimal point)
                    if re.match(r'^\s*\d+(\.\d+)?\s*$', sql_expr):
                        return 'numeric'

                    # Boolean functions
                    if any(p in sql_upper for p in ['EXISTS(', 'EMPTY(', 'IS_DISTINCT(']):
                        return 'boolean'

                    # JSON operations (often return strings)
                    if 'JSON_EXTRACT' in sql_upper or '->>' in sql_upper:
                        return 'varchar'

                    # Default: unknown (will be detected dynamically)
                    return 'unknown'

                true_detected_type = detect_sql_type(true_result_sql, true_result_type)
                false_detected_type = detect_sql_type(false_result_sql, false_result_type)

                logger.debug(
                    f"iif() type detection: true={true_detected_type}, false={false_detected_type}"
                )

                # SP-110-AUTOPILOT: Determine if we need type coercion
                needs_coercion = False

                # Explicit type mismatch from metadata
                if true_result_type and false_result_type and true_result_type != false_result_type:
                    needs_coercion = True
                    logger.debug(f"iif() type coercion: metadata mismatch {true_result_type} vs {false_result_type}")

                # Detected type mismatch (excluding unknown types)
                elif (true_detected_type != 'unknown' and false_detected_type != 'unknown' and
                      true_detected_type != false_detected_type):
                    # Only coerce if types are actually different and incompatible
                    incompatible_pairs = {
                        ('boolean', 'numeric'), ('numeric', 'boolean'),
                        ('boolean', 'varchar'), ('varchar', 'boolean'),
                        ('numeric', 'varchar'), ('varchar', 'numeric'),
                    }
                    if (true_detected_type, false_detected_type) in incompatible_pairs:
                        needs_coercion = True
                        logger.debug(f"iif() type coercion: detected mismatch {true_detected_type} vs {false_detected_type}")

                # SP-110-AUTOPILOT: Additional heuristic - check for function calls that return strings
                # like toString() which may not be detected above
                elif 'toString' in str(true_result_node) or 'toString' in str(false_result_node):
                    # If one branch uses toString(), both should be VARCHAR
                    needs_coercion = True
                    logger.debug("iif() type coercion: toString() detected, casting both to VARCHAR")

                # Apply type coercion if needed
                # Track the result type for final CAST
                coerced_result_type = None

                if needs_coercion:
                    # Determine the common type for coercion
                    # Per FHIRPath spec:
                    # - Boolean + numeric -> numeric (true->1, false->0)
                    #   Then cast entire result to BOOLEAN to preserve FHIRPath semantics
                    # - Other incompatible types -> string
                    types_pair = (true_detected_type, false_detected_type)
                    if types_pair in [('boolean', 'numeric'), ('numeric', 'boolean')]:
                        # Cast both to numeric: boolean -> 1.0 or 0.0
                        true_result_sql = f"(CASE WHEN {true_result_sql} THEN 1.0 ELSE 0.0 END)" if true_detected_type == 'boolean' else true_result_sql
                        false_result_sql = f"(CASE WHEN {false_result_sql} THEN 1.0 ELSE 0.0 END)" if false_detected_type == 'boolean' else false_result_sql
                        # Mark that result should be cast back to BOOLEAN
                        coerced_result_type = 'boolean'
                        logger.info("iif() type coercion applied: boolean+numeric -> numeric (will cast to BOOLEAN)")
                    else:
                        # Other incompatible types: cast both to VARCHAR
                        true_result_sql = self.dialect.cast_to_string(true_result_sql)
                        false_result_sql = self.dialect.cast_to_string(false_result_sql)
                        coerced_result_type = 'varchar'
                        logger.info("iif() type coercion applied: both branches cast to VARCHAR")

            # Build CASE expression with explicit empty-condition handling
            null_check_clause = f"WHEN {criterion_sql} IS NULL THEN NULL"
            true_clause = f"WHEN {criterion_sql} THEN {true_result_sql}"
            else_clause = f"ELSE {false_result_sql}"
            case_expression = (
                "CASE "
                f"{null_check_clause} "
                f"{true_clause} "
                f"{else_clause} "
                "END"
            )

            # SP-110: Apply final type cast to preserve FHIRPath semantics
            # When boolean and numeric were coerced to numeric, cast result back to BOOLEAN
            if coerced_result_type == 'boolean':
                case_expression = f"CAST({case_expression} AS BOOLEAN)"
                logger.debug("iif() result cast to BOOLEAN to preserve semantics")

            # FHIRPath iif() on multi-item collections:
            # When iif() is called ON a multi-item collection (e.g., (1 | 2 | 3).iif(true, 'a', 'b')),
            # the collection is checked for existence (non-empty = TRUE, empty = FALSE)
            # This aligns with FHIRPath semantics where collections in boolean context use exists()
            if target_is_multi_item and target_expr:
                # Wrap the CASE expression to check if target collection is non-empty
                # If target has items (exists() = TRUE), use the CASE expression
                # If target is empty, return false-result (or NULL if no false-result)
                if false_result_node:
                    case_expression = f"""CASE
                        WHEN EXISTS({target_expr}) THEN {case_expression}
                        ELSE {false_result_sql}
                    END"""
                else:
                    case_expression = f"""CASE
                        WHEN EXISTS({target_expr}) THEN {case_expression}
                        ELSE NULL
                    END"""
                logger.debug(f"iif() called on multi-item collection - wrapped with EXISTS check")

            # For dynamic collections, add runtime validation
            if target_path:
                # Get the JSON path for the target collection
                json_path = self._build_json_path_from_components(target_path)

                # Extract the collection
                collection_expr = self.dialect.extract_json_object(
                    column=snapshot["current_table"],
                    path=json_path
                )

                array_length_expr = self.dialect.get_json_array_length(collection_expr)

                # Validate cardinality: must be 0 or 1 items
                # Wrap the CASE expression with validation check
                validation_clauses = [
                    f"WHEN {collection_expr} IS NULL THEN {case_expression}",
                    f"WHEN {array_length_expr} <= 1 THEN {case_expression}",
                    "ELSE NULL  -- Error: collection has multiple items",
                ]
                case_expression = "CASE\n" + "\n".join(
                    f"    {clause}" for clause in validation_clauses
                ) + "\nEND"

            # Combine dependencies from all fragments
            all_dependencies = dependencies.copy() if dependencies else []
            all_dependencies.extend(criterion_fragment.dependencies)
            all_dependencies.extend(true_result_fragment.dependencies)
            if false_result_node:
                all_dependencies.extend(false_result_fragment.dependencies)

            unique_dependencies: List[str] = []
            for dependency in all_dependencies:
                if dependency and dependency not in unique_dependencies:
                    unique_dependencies.append(dependency)

            return SQLFragment(
                expression=case_expression,
                source_table=snapshot["current_table"],
                requires_unnest=False,
                is_aggregate=False,
                dependencies=unique_dependencies,
                metadata={"function": "iif"}
            )

        finally:
            self._restore_context(snapshot)

    def _unwrap_expression_node(self, node) -> Any:
        """
        Unwrap wrapper AST nodes to get the actual expression content.

        The FHIRPath parser wraps expressions in container nodes like
        TermExpression, InvocationExpression, etc. This method recursively
        unwraps these containers to find the underlying expression node
        for type checking purposes.

        Args:
            node: AST node to unwrap

        Returns:
            The innermost non-wrapper node
        """
        wrapper_types = {
            'TermExpression',
            'TermExpressionTerm',
            'InvocationTerm',
            'InvocationExpression',
            'PolarityExpression',
        }

        max_depth = 10  # Prevent infinite loops
        current = node

        for _ in range(max_depth):
            if not hasattr(current, 'node_type'):
                break
            if current.node_type not in wrapper_types:
                break
            # Get the single child (wrapper nodes typically have one child)
            if hasattr(current, 'children') and len(current.children) == 1:
                current = current.children[0]
            else:
                break

        return current

    def _is_boolean_expression(self, node) -> bool:
        """
        Check if an AST node represents a boolean expression.

        This is used for semantic validation of iif() criterion parameter.
        Per FHIRPath spec, the criterion can be any expression that converts
        to a boolean singleton at runtime (including empty collections).

        Args:
            node: AST node to check

        Returns:
            True if node is a boolean expression, False otherwise
        """
        # First, unwrap any wrapper nodes (TermExpression, etc.)
        unwrapped = self._unwrap_expression_node(node)

        # Literal values
        if hasattr(unwrapped, 'node_type') and unwrapped.node_type == "literal":
            # Check for boolean value
            if isinstance(getattr(unwrapped, 'value', None), bool):
                return True
            # Check for boolean text ('true' or 'false')
            text = getattr(unwrapped, 'text', '')
            if text in ('true', 'false'):
                return True
            # Empty collection {} - valid per FHIRPath spec, evaluates to false
            if text == '{}':
                return True
            # String literals are not boolean
            return False

        # Boolean operators
        if hasattr(unwrapped, 'node_type') and unwrapped.node_type == "operator":
            # Comparison operators return boolean
            if hasattr(unwrapped, 'operator') and unwrapped.operator in ['=', '!=', '>', '<', '>=', '<=', '~', '!~']:
                return True
            # Logical operators return boolean
            if hasattr(unwrapped, 'operator') and unwrapped.operator in ['and', 'or', 'xor', 'implies']:
                return True
            # Arithmetic operators do not return boolean
            return False

        # Boolean functions (direct function call)
        if hasattr(unwrapped, 'node_type') and unwrapped.node_type == "functionCall":
            boolean_functions = [
                'exists', 'empty', 'not', 'all', 'convertstoboolean',
                'isboolean', 'isinteger', 'isstring', 'isdecimal', 'isquantity',
                'isdate', 'isdatetime', 'istime', 'hasvalue', 'matches',
                'contains', 'startswith', 'endswith', 'is', 'as',
                'subsetof', 'supersetof', 'in', 'iif',
            ]
            if hasattr(unwrapped, 'function_name') and unwrapped.function_name.lower() in boolean_functions:
                return True
            return False

        # Check if original node is an expression type that returns boolean
        # (EqualityExpression, InequalityExpression, etc.)
        if hasattr(node, 'node_type'):
            boolean_expression_types = {
                'EqualityExpression',
                'InequalityExpression',
                'ComparisonExpression',
                'MembershipExpression',
                'AndExpression',
                'OrExpression',
                'XorExpression',
                'ImpliesExpression',
                'TypeExpression',
                'UnionExpression',  # SP-100-002-Enhanced: Union can reduce to single boolean value
            }
            if node.node_type in boolean_expression_types:
                return True

            # InvocationExpression ending with a boolean function
            if node.node_type == 'InvocationExpression':
                # Check if the last child is a boolean function call
                if hasattr(node, 'children') and node.children:
                    last_child = node.children[-1]
                    if hasattr(last_child, 'node_type') and last_child.node_type == 'functionCall':
                        # Check function name
                        boolean_functions = [
                            'exists', 'empty', 'not', 'all', 'convertstoboolean',
                            'isboolean', 'isinteger', 'isstring', 'isdecimal', 'isquantity',
                            'isdate', 'isdatetime', 'istime', 'hasvalue', 'matches',
                            'contains', 'startswith', 'endswith', 'is', 'as',
                            'subsetof', 'supersetof', 'in',
                        ]
                        # Get function name from text (e.g., "exists()")
                        func_text = getattr(last_child, 'text', '')
                        func_name = func_text.split('(')[0].strip().lower() if func_text else ''
                        if func_name in boolean_functions:
                            return True
                        # Also check function_name attribute
                        if hasattr(last_child, 'function_name'):
                            if last_child.function_name.lower() in boolean_functions:
                                return True

        # Default: cannot determine, assume non-boolean (conservative approach)
        return False

    def _is_multi_item_collection(self, node) -> bool:
        """
        Check if an AST node represents a multi-item collection.

        This is used for execution validation of iif() to detect multi-item collections
        that would cause a runtime error.

        Args:
            node: AST node to check

        Returns:
            True if node represents a multi-item collection (e.g., literal union), False otherwise
        """
        # Check for union operator (|) which creates multi-item collections
        # The parser creates a UnionExpression node with node_type='UnionExpression'
        if hasattr(node, 'node_type') and node.node_type == "UnionExpression":
            # Union operator - check if both sides are single items
            # If both are single literals, this is a multi-item collection
            left = node.children[0] if hasattr(node, 'children') and len(node.children) > 0 else None
            right = node.children[1] if hasattr(node, 'children') and len(node.children) > 1 else None

            if left and right:
                # Both sides exist - this is definitely a multi-item collection
                return True

        # Also check for legacy operator node type
        if hasattr(node, 'node_type') and node.node_type == "operator":
            if hasattr(node, 'operator') and node.operator == '|':
                # Union operator - check if both sides are single items
                # If both are single literals, this is a multi-item collection
                left = node.children[0] if hasattr(node, 'children') and len(node.children) > 0 else None
                right = node.children[1] if hasattr(node, 'children') and len(node.children) > 1 else None

                if left and right:
                    # Both sides exist - this is definitely a multi-item collection
                    return True

        # SP-100-002: Recursively check children for union expressions
        # This handles cases like ('a' | 'b') where the union is nested inside
        # wrapper nodes like TermExpression, ParenthesizedTerm, etc.
        if hasattr(node, 'children'):
            for child in node.children:
                if self._is_multi_item_collection(child):
                    return True

        # Empty collection literal {}
        if hasattr(node, 'node_type') and node.node_type == "literal":
            # Empty collection is OK (0 items)
            return False

        # Single item is OK
        return False

    def _is_multi_item_collection_excluding_empty_unions(self, node) -> bool:
        """
        Check if an AST node represents a multi-item collection, excluding unions with empty collections.

        This is a stricter version of _is_multi_item_collection that allows unions like
        {} | true which reduce to a single value (the first non-empty value).

        Args:
            node: AST node to check

        Returns:
            True if node represents a multi-item collection with no empty collections, False otherwise
        """
        # Check for union operator (|) which creates multi-item collections
        if hasattr(node, 'node_type') and node.node_type == "UnionExpression":
            # Check if this union contains only non-empty literals
            # If it has an empty collection {}, it's allowed (reduces to single value)
            return self._union_has_only_non_empty_items(node)

        # Also check for legacy operator node type
        if hasattr(node, 'node_type') and node.node_type == "operator":
            if hasattr(node, 'operator') and node.operator == '|':
                return self._union_has_only_non_empty_items(node)

        # SP-100-002: Recursively check children for union expressions
        if hasattr(node, 'children'):
            for child in node.children:
                if self._is_multi_item_collection_excluding_empty_unions(child):
                    return True

        return False

    def _union_has_only_non_empty_items(self, node) -> bool:
        """
        Check if a union expression contains only non-empty items.

        Returns True if the union has multiple non-empty items (invalid for iif criterion).
        Returns False if the union contains at least one empty collection or has only one item.

        Args:
            node: Union expression node to check

        Returns:
            True if union has multiple non-empty items, False otherwise
        """
        if not hasattr(node, 'children') or len(node.children) < 2:
            return False

        # Check each side of the union
        non_empty_count = 0
        for child in node.children:
            if self._is_empty_collection_literal(child):
                # Empty collection found - this union reduces to single value
                return False
            elif hasattr(child, 'node_type') and child.node_type == "UnionExpression":
                # Nested union - recursively check
                if self._union_has_only_non_empty_items(child):
                    # Nested union has multiple non-empty items
                    non_empty_count += 2  # At least 2 items in nested union
                else:
                    # Nested union has empty collection or single item
                    return False
            elif not self._is_multi_item_collection(child):
                # This is a non-empty single item
                non_empty_count += 1

        # If we have 2+ non-empty items, this is a multi-item collection
        return non_empty_count >= 2

    def _is_empty_collection_literal(self, node) -> bool:
        """
        Check if an AST node represents an empty collection literal {}.

        Args:
            node: AST node to check

        Returns:
            True if node is an empty collection literal, False otherwise
        """
        if hasattr(node, 'node_type') and node.node_type == "literal":
            text = getattr(node, 'text', '')
            return text == '{}'

        # Recursively check wrapper nodes
        if hasattr(node, 'children') and len(node.children) == 1:
            return self._is_empty_collection_literal(node.children[0])

        return False

    def _split_function_path(self, path: str) -> List[str]:
        """Split path string respecting nested function parentheses."""
        components: List[str] = []
        current = []
        depth = 0
        for char in path:
            if char == '.' and depth == 0:
                component = ''.join(current).strip()
                if component:
                    components.append(component)
                current = []
                continue
            if char == '(':
                depth += 1
            elif char == ')':
                depth = max(depth - 1, 0)
            current.append(char)
        tail = ''.join(current).strip()
        if tail:
            components.append(tail)
        return components

    def _apply_collection_remainder(
        self,
        node: FunctionCallNode,
        base_expression: str,
        base_metadata: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """Apply chained collection operations (e.g., empty(), count(), not())."""
        remainder_path = self._extract_path_after_function(node.text, node.function_name)
        if not remainder_path:
            return base_expression, base_metadata

        components = self._split_function_path(remainder_path)
        current_expr = base_expression
        current_metadata = dict(base_metadata)

        for component in components:
            normalized = component.strip()
            lower_component = normalized.lower()

            if lower_component == "empty()":
                normalized_expr = self._normalize_collection_expression(current_expr)
                length_expr = self.dialect.get_json_array_length(normalized_expr)
                current_expr = (
                    "("
                    "CASE "
                    f"WHEN {normalized_expr} IS NULL THEN TRUE "
                    f"ELSE ({length_expr} = 0) "
                    "END"
                    ")"
                )
                current_metadata = {"function": "empty", "result_type": "boolean"}
            elif lower_component == "count()":
                normalized_expr = self._normalize_collection_expression(current_expr)
                length_expr = self.dialect.get_json_array_length(normalized_expr)
                current_expr = (
                    "("
                    "CASE "
                    f"WHEN {normalized_expr} IS NULL THEN 0 "
                    f"ELSE {length_expr} "
                    "END"
                    ")"
                )
                current_metadata = {"function": "count", "result_type": "integer"}
            elif lower_component == "not()":
                current_expr = self.dialect.generate_boolean_not(current_expr)
                current_metadata = {"function": "not", "result_type": "boolean"}
            else:
                path_components = [part for part in normalized.split('.') if part]
                if not path_components:
                    raise NotImplementedError(
                        f"Unsupported chained operation '{component}' after {node.function_name}()"
                    )

                if current_metadata.get("is_collection", False):
                    array_expr = current_metadata.get("array_column", current_expr)
                    projected = self.dialect.project_json_array(array_expr, path_components)
                    current_expr = projected
                    current_metadata = dict(current_metadata)
                    current_metadata["array_column"] = projected
                    result_alias = current_metadata.get("result_alias", "item")
                    serialized_alias = self.dialect.serialize_json_value(
                        f"{result_alias}.unnest"
                    )
                    quote_char = '"'
                    current_metadata["projection_expression"] = (
                        f"TRIM(BOTH '{quote_char}' FROM {serialized_alias})"
                    )
                else:
                    json_path = "$"
                    for part in path_components:
                        if part.startswith("["):
                            json_path += part
                        else:
                            json_path += f".{part}"
                    current_expr = self.dialect.extract_json_field(
                        column=current_expr,
                        path=json_path
                    )
                    current_metadata = {"function": "property", "is_collection": False}

        return current_expr, current_metadata

    def _evaluate_literal_converts_to(self, value: Any, target_type: str) -> bool:
        """Evaluate convertsTo* for literal values at translation time."""
        if value is None:
            return False

        if target_type == "Boolean":
            if isinstance(value, bool):
                return True
            if isinstance(value, (int,)):
                return value in (0, 1)
            if isinstance(value, float):
                return value in (0.0, 1.0)
            if isinstance(value, str):
                normalized = value.strip().lower()
                return normalized in {"true", "false", "t", "f", "1", "0"}
            return False

        if target_type == "Integer":
            if isinstance(value, bool):
                return True
            if isinstance(value, int):
                return True
            if isinstance(value, float):
                return value.is_integer()
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return False
                if stripped[0] in {"+", "-"}:
                    stripped = stripped[1:]
                return stripped.isdigit()
            return False

        if target_type == "String":
            return value is not None

        if target_type == "Decimal":
            if isinstance(value, bool):
                return True
            if isinstance(value, (int, float)):
                return True
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return False
                try:
                    float(stripped)
                    return True
                except ValueError:
                    return False
            return False

        if target_type == "Quantity":
            # SP-103-003: Implement Quantity type conversion
            # SP-106-003: Quantity literals (e.g., "10 'mg'") are marked with QuantityLiteralMarker
            # According to FHIRPath spec, the following can convert to Quantity:
            # - Integer literals (e.g., 1, 5, 10)
            # - Decimal literals (e.g., 1.0, 5.5, 10.25)
            # - Boolean literals (true, false) - convert to 1.0 and 0.0
            # - String representations of integers (e.g., '1', '5')
            # - String representations of decimals (e.g., '1.0', '5.5')
            # - String representations of quantities (e.g., '1 day', '4 days', '1 \'wk\'')

            # SP-106-003: Check for quantity literal marker first
            if hasattr(value, 'is_quantity_literal') and value.is_quantity_literal:
                return True

            if isinstance(value, bool):
                # Booleans can convert to Quantity (true -> 1.0, false -> 0.0)
                return True
            if isinstance(value, (int, float)):
                # Numbers can convert to Quantity
                return True
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return False

                # Check if it's a valid quantity string
                # Format: <number> [<unit>] or <number> '<unit>'
                # Examples: '1', '1.0', '1 day', '4 days', '1 \'wk\''

                # Try to match: number followed by optional unit
                # Pattern: optional +/-, digits with optional decimal, optional space, optional unit in quotes or plain text
                quantity_pattern = r'^[\+\-]?(\d+\.?\d*|\.\d+)(\s+[a-zA-Z]+|\s+\'[a-zA-Z]+\'|\s+\"[a-zA-Z]+\")?$'
                if re.match(quantity_pattern, stripped):
                    return True

            return False

        if target_type == "Date":
            if isinstance(value, str):
                stripped = value.strip()
                # SP-103-006: Support Date formats (no time component)
                # Accepts: YYYY, YYYY-MM, YYYY-MM-DD
                # Pattern: Year required, month/day optional, no 'T' or time allowed
                return bool(re.match(r'^\d{4}(-\d{2}(-\d{2})?)(?!T)$', stripped))
            return False

        if target_type == "DateTime":
            if isinstance(value, str):
                stripped = value.strip()
                # SP-101-003: Support partial DateTime formats
                # SP-108-002: Support milliseconds and timezone
                # Accepts: YYYY, YYYY-MM, YYYY-MM-DD, YYYYT, YYYY-MMT, YYYY-MM-DDT, YYYY-MM-DDTHH:MM:SS...
                #          YYYY-MM-DDTHH:MM:SS.sss, YYYY-MM-DDTHH:MM:SSZ, YYYY-MM-DDTHH:MM:SS+10:00
                # Pattern: Year required, month/day optional, 'T' suffix optional (with or without time)
                #          Time can include milliseconds and timezone
                return bool(re.match(r'^\d{4}(-\d{2}(-\d{2})?)?(T(\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?(Z|[+-]\d{2}:\d{2})?)?)?$', stripped))
            return False

        if target_type == "Time":
            if isinstance(value, str):
                stripped = value.strip()
                # SP-101-003: Support hour-only format and standard time formats
                # SP-108-002: Support timezone suffix (Z or +/-HH:MM)
                # Accepts: HH, HH:MM, HH:MM:SS, HH:MM:SS.sss
                #          Note: FHIRPath Time literals cannot have timezones (returns false)
                #          But for string conversion checking, we accept the format
                if bool(re.search(r'[Z]|[+-]\d{2}:\d{2}$', stripped)):
                    # Time with timezone is not a valid FHIRPath Time
                    return False
                return bool(re.match(r'^\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?$', stripped))
            return False

        raise ValueError(f"Unsupported convertsTo target type: {target_type}")

    def _build_converts_to_expression(self, value_expr: str, target_type: str) -> str:
        """Build SQL boolean expression for convertsTo* functions."""
        if target_type == "Boolean":
            return self._build_converts_to_boolean_expression(value_expr)
        if target_type == "Integer":
            return self._build_converts_to_integer_expression(value_expr)
        if target_type == "String":
            return self._build_converts_to_string_expression(value_expr)
        if target_type == "Decimal":
            return self._build_converts_to_decimal_expression(value_expr)
        if target_type == "Quantity":
            return self._build_converts_to_quantity_expression(value_expr)
        if target_type == "Date":
            return self._build_converts_to_date_expression(value_expr)
        if target_type == "DateTime":
            return self._build_converts_to_datetime_expression(value_expr)
        if target_type == "Time":
            return self._build_converts_to_time_expression(value_expr)
        raise ValueError(f"Unsupported convertsTo target type: {target_type}")

    def _build_converts_to_boolean_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToBoolean() checks."""
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        trimmed_string = self.dialect.generate_trim(string_cast)
        lowered_string = f"LOWER({trimmed_string})"
        decimal_cast = self.dialect.generate_type_cast(value_expr, "Decimal")

        numeric_condition = f"({decimal_cast} IS NOT NULL AND ({decimal_cast} = 0 OR {decimal_cast} = 1))"
        string_condition = (
            f"({string_cast} IS NOT NULL AND "
            f"{lowered_string} IN ('true', 'false', 't', 'f', '1', '0'))"
        )

        return (
            "CASE "
            f"WHEN {string_cast} IS NULL AND {decimal_cast} IS NULL THEN FALSE "
            f"WHEN {numeric_condition} THEN TRUE "
            f"WHEN {string_condition} THEN TRUE "
            "ELSE FALSE "
            "END"
        )

    def _build_converts_to_integer_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToInteger() checks.

        SP-110-010: Strings containing decimal points should NOT convert to integer.
        For example, '3.14'.convertsToInteger() should return FALSE.
        """
        integer_cast = self.dialect.generate_type_cast(value_expr, "Integer")
        decimal_cast = self.dialect.generate_type_cast(value_expr, "Decimal")
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        trimmed_string = self.dialect.generate_trim(string_cast)
        lowered_string = f"LOWER({trimmed_string})"

        # SP-110-010: Check if string contains a decimal point - if so, it cannot convert to integer
        contains_decimal = f"POSITION('.' IN {trimmed_string}) > 0"

        numeric_condition = (
            f"({integer_cast} IS NOT NULL AND "
            f"({decimal_cast} IS NULL OR {decimal_cast} = {integer_cast}))"
        )
        boolean_condition = (
            f"({string_cast} IS NOT NULL AND {lowered_string} IN ('true', 'false', 't', 'f'))"
        )

        # SP-110-010: Add check for decimal point - strings with '.' should return FALSE
        return (
            "CASE "
            f"WHEN {string_cast} IS NOT NULL AND {contains_decimal} THEN FALSE "
            f"WHEN {numeric_condition} THEN TRUE "
            f"WHEN {boolean_condition} THEN TRUE "
            f"WHEN {integer_cast} IS NULL THEN FALSE "
            "ELSE FALSE "
            "END"
        )

    def _build_converts_to_string_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToString() checks."""
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        return f"CASE WHEN {string_cast} IS NOT NULL THEN TRUE ELSE FALSE END"

    def _build_converts_to_decimal_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToDecimal() checks."""
        decimal_cast = self.dialect.generate_type_cast(value_expr, "Decimal")
        return f"CASE WHEN {decimal_cast} IS NOT NULL THEN TRUE ELSE FALSE END"

    def _build_converts_to_date_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToDate() checks.

        SP-103-006: Implement date conversion checking.
        A value can convert to Date if:
        - It's a string matching ISO 8601 date format (YYYY, YYYY-MM, YYYY-MM-DD)
        - Does NOT include time component (no 'T' or time allowed)

        According to FHIRPath spec:
        - '2015' converts to Date (year only)
        - '2015-02' converts to Date (year-month)
        - '2015-02-04' converts to Date (full date)
        - '2015T' does NOT convert to Date (has time separator)
        - '2015-02-04T10:00' does NOT convert to Date (has time)
        """
        # First, try to cast as string
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        trimmed_string = self.dialect.generate_trim(string_cast)

        # Use regex to check if it matches a Date pattern
        # Pattern: YYYY(-MM(-DD)?)? without 'T' (time separator)
        # Matches: 2015, 2015-02, 2015-02-04
        # Does NOT match: 2015T, 2015-02T, 2015-02-04T10:00:00
        # Note: Using simple string matching instead of regex for better compatibility
        # Check for: starts with 4 digits, optionally followed by -MM, optionally followed by -DD, and no 'T'
        # The negative lookahead (?!T) doesn't work well in all SQL regex engines, so we use a different approach

        # First check: matches basic date pattern (YYYY-MM-DD with optional parts)
        date_pattern_basic = "^[0-9]{4}(-[0-9]{2})?(-[0-9]{2})?$"
        # Second check: does NOT contain 'T' (time separator)
        contains_t = "POSITION('T' IN " + trimmed_string + ") > 0"
        regex_match = self.dialect.generate_regex_match(trimmed_string, "'" + date_pattern_basic + "'")

        return (
            "CASE "
            "WHEN " + trimmed_string + " IS NULL THEN FALSE "
            "WHEN " + regex_match + " AND NOT " + contains_t + " THEN TRUE "
            "ELSE FALSE "
            "END"
        )

    def _build_converts_to_quantity_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToQuantity() checks.

        SP-103-003: Implement quantity conversion checking.
        A value can convert to Quantity if:
        - It's a number (integer or decimal)
        - It's a boolean
        - It's a string that represents a number or number with unit

        According to FHIRPath spec and test cases:
        - '1' converts to Quantity (just a number)
        - '1.0' converts to Quantity (decimal number)
        - '1 day' converts to Quantity (number + space + date/time precision unit)
        - '1 'wk'' converts to Quantity (number + space + single-quoted unit)
        - '1 wk' does NOT convert to Quantity (unquoted non-date/time unit)
        """
        # Cast to string first
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        trimmed_string = self.dialect.generate_trim(string_cast)

        # Check if it's a valid quantity string using regex
        # Pattern: optional +/-, digits with optional decimal, optional space, optional unit
        # Units allowed:
        # 1. Date/time precision words (year, month, week, day, hour, minute, second, millisecond)
        # 2. Plural date/time precision words (years, months, weeks, days, hours, minutes, seconds, milliseconds)
        # 3. Single-quoted units (e.g., '1 'wk'')
        # 4. Double-quoted units (e.g., '1 "kg"')
        #
        # Note: Unquoted non-date/time units like '1 wk' should NOT match (per test cases)
        #
        # IMPORTANT: In SQL string literals, single quotes are escaped by doubling them
        # So \s+'[a-zA-Z]+' becomes \s+''[a-zA-Z]+''
        quantity_pattern = r"^[\+\-]?(\d+\.?\d*|\.\d+)(\s+(year|years|month|months|week|weeks|day|days|hour|hours|minute|minutes|second|seconds|millisecond|milliseconds)|\s+''[a-zA-Z]+''|\s+\"[a-zA-Z]+\")?$"

        # Also check if it's a boolean
        lowered_string = f"LOWER({trimmed_string})"
        is_boolean = f"({lowered_string} IN ('true', 'false', 't', 'f', '1', '0'))"

        # Check if it matches quantity pattern - need to quote the pattern as a string literal
        # SQL escaping: single quotes within string are doubled
        is_quantity = self.dialect.generate_regex_match(trimmed_string, f"'{quantity_pattern}'")

        # Combine checks: boolean OR matches quantity pattern OR is a number
        decimal_cast = self.dialect.generate_type_cast(value_expr, "Decimal")
        is_number = f"({decimal_cast} IS NOT NULL)"

        return (
            f"CASE "
            f"WHEN {value_expr} IS NULL THEN FALSE "
            f"WHEN {is_boolean} THEN TRUE "
            f"WHEN {is_number} THEN TRUE "
            f"WHEN {is_quantity} THEN TRUE "
            f"ELSE FALSE "
            f"END"
        )

    def _build_converts_to_datetime_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToDateTime() checks.

        SP-101-003: Use regex pattern matching instead of casting to support
        partial DateTime formats like '2015', '2015-02', '2015-02-04'.

        SP-108-002: Support milliseconds and timezone in DateTime format.
        Pattern now includes:
        - Milliseconds: (\.[0-9]+)?
        - Timezone: (Z|[+-][0-9]{2}:[0-9]{2})?

        FHIRPath spec allows convertsToDateTime() to return true for strings that
        match the DateTime format, even if they're partial dates.
        """
        # First, try to cast as string
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        # Use regex to check if it matches a DateTime pattern
        # Pattern: YYYY(-MM(-DD(T(HH(:MM(:SS(\.SSS)?)?)?)?(Z|[+-]HH:MM)?)?)?
        # Matches: 2015, 2015-02, 2015-02-04, 2015T, 2015-02T, 2015-02-04T, 2015-02-04T10:00:00
        #          2015-02-04T14:34:28.123, 2015-02-04T14:34:28Z, 2015-02-04T14:34:28+10:00
        datetime_pattern = r"'^[0-9]{4}(-[0-9]{2})?(-[0-9]{2})?(T([0-9]{2}(:[0-9]{2})?(:[0-9]{2}(\.[0-9]+)?)?)?(Z|[+-][0-9]{2}:[0-9]{2})?)?$'"
        return (
            f"CASE "
            f"WHEN {string_cast} IS NULL THEN FALSE "
            f"WHEN {self.dialect.generate_regex_match(string_cast, datetime_pattern)} THEN TRUE "
            f"ELSE FALSE "
            f"END"
        )

    def _build_converts_to_time_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToTime() checks.

        SP-101-003: Use regex pattern matching to support hour-only time format.
        """
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        # Pattern: HH(:MM(:SS(.sss)?)?)?
        # Note: Use escaped backslash for literal period in regex
        time_pattern = r"'^[0-9]{2}(:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?)?$'"
        return (
            f"CASE "
            f"WHEN {string_cast} IS NULL THEN FALSE "
            f"WHEN {self.dialect.generate_regex_match(string_cast, time_pattern)} THEN TRUE "
            f"ELSE FALSE "
            f"END"
        )

    def _translate_to_boolean(self, node: FunctionCallNode) -> SQLFragment:
        """Translate toBoolean() function to SQL conversion."""
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                result = self._evaluate_literal_to_boolean(literal_value)
                sql_expr = self._to_sql_literal(result, "boolean")
                return SQLFragment(
                    expression=sql_expr,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False
                )

            if not value_expr:
                raise ValueError("toBoolean() requires a resolvable target expression")

            sql_expr = self._build_to_boolean_expression(value_expr)
            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_to_integer(self, node: FunctionCallNode) -> SQLFragment:
        """Translate toInteger() function to SQL conversion."""
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                result = self._evaluate_literal_to_integer(literal_value)
                sql_expr = self._to_sql_literal(result, "integer")
                return SQLFragment(
                    expression=sql_expr,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False
                )

            if not value_expr:
                raise ValueError("toInteger() requires a resolvable target expression")

            sql_expr = self._build_to_integer_expression(value_expr)
            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_to_string(self, node: FunctionCallNode) -> SQLFragment:
        """Translate toString() function to SQL conversion.

        SP-110-FIX-014: For literal values, ensure proper string casting by using
        value_expr (the SQL expression) rather than just the literal value.
        This prevents strings like 'true' from being interpreted as booleans.
        """
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            # SP-110-FIX-014: Even for literal values, we need to cast to string type
            # to ensure SQL returns the value as a string, not as inferred boolean/number
            if literal_value is not None:
                # Evaluate the literal to get the string value
                result = self._evaluate_literal_to_string(literal_value)
                # But use the value_expr (SQL expression) and cast it to ensure proper type
                # The value_expr already contains the proper SQL literal (e.g., 'true')
                sql_expr = self.dialect.generate_type_cast(value_expr, "String")
                return SQLFragment(
                    expression=sql_expr,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=dependencies
                )

            if not value_expr:
                raise ValueError("toString() requires a resolvable target expression")

            sql_expr = self._build_to_string_expression(value_expr)
            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_to_decimal(self, node: FunctionCallNode) -> SQLFragment:
        """Translate toDecimal() function to SQL conversion."""
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                result = self._evaluate_literal_to_decimal(literal_value)
                if result is not None:
                    sql_expr = str(result)
                else:
                    sql_expr = "NULL"
                return SQLFragment(
                    expression=sql_expr,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False
                )

            if not value_expr:
                raise ValueError("toDecimal() requires a resolvable target expression")

            sql_expr = self._build_to_decimal_expression(value_expr)
            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_to_quantity(self, node: FunctionCallNode) -> SQLFragment:
        """Translate toQuantity() function to SQL conversion."""
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                result = self._evaluate_literal_to_quantity(literal_value)
                if result:
                    sql_expr = self._to_sql_literal(result, "string")
                    # SP-110-XXX: Parse the quantity JSON to extract value and unit for metadata
                    # This enables proper quantity comparisons (e.g., '1 day'.toQuantity() = 1 day)
                    metadata = {'is_literal': True}
                    try:
                        import json
                        quantity_data = json.loads(result)
                        quantity_value = quantity_data.get('value')
                        quantity_unit = quantity_data.get('unit')
                        if quantity_value is not None:
                            metadata['literal_type'] = 'quantity'
                            metadata['quantity_value'] = str(quantity_value)
                            if quantity_unit:
                                normalized_unit = self._normalize_quantity_unit(quantity_unit)
                                metadata['quantity_unit'] = normalized_unit if normalized_unit else quantity_unit
                    except (json.JSONDecodeError, TypeError):
                        # If we can't parse as JSON, just return without quantity metadata
                        pass
                    return SQLFragment(
                        expression=sql_expr,
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        metadata=metadata
                    )
                else:
                    return SQLFragment(
                        expression="NULL",
                        source_table=source_table,
                        requires_unnest=False,
                        is_aggregate=False
                    )

            if not value_expr:
                raise ValueError("toQuantity() requires a resolvable target expression")

            sql_expr = self._build_to_quantity_expression(value_expr)
            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_to_date(self, node: FunctionCallNode) -> SQLFragment:
        """Translate toDate() function to SQL conversion.

        SP-103-006: Implement toDate() conversion.
        Converts a value to a Date string (ISO 8601 format).
        """
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                result = self._evaluate_literal_to_date(literal_value)
                sql_expr = self._to_sql_literal(result, "string") if result else "NULL"
                return SQLFragment(
                    expression=sql_expr,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False
                )

            if not value_expr:
                raise ValueError("toDate() requires a resolvable target expression")

            sql_expr = self._build_to_date_expression(value_expr)
            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_to_datetime(self, node: FunctionCallNode) -> SQLFragment:
        """Translate toDateTime() function to SQL conversion."""
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                result = self._evaluate_literal_to_datetime(literal_value)
                sql_expr = self._to_sql_literal(result, "string") if result else "NULL"
                return SQLFragment(
                    expression=sql_expr,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False
                )

            if not value_expr:
                raise ValueError("toDateTime() requires a resolvable target expression")

            sql_expr = self._build_to_datetime_expression(value_expr)
            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_to_time(self, node: FunctionCallNode) -> SQLFragment:
        """Translate toTime() function to SQL conversion."""
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                result = self._evaluate_literal_to_time(literal_value)
                sql_expr = self._to_sql_literal(result, "string") if result else "NULL"
                return SQLFragment(
                    expression=sql_expr,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False
                )

            if not value_expr:
                raise ValueError("toTime() requires a resolvable target expression")

            sql_expr = self._build_to_time_expression(value_expr)
            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_distinct(self, node: FunctionCallNode) -> SQLFragment:
        """Translate distinct() set operation to SQL.

        Handles two cases:
        1. Simple expressions: wraps in CASE and applies distinct logic
        2. SELECT statements (from select(), combine(), etc.): modifies aggregation to use DISTINCT
        """
        if node.arguments:
            raise ValueError(f"distinct() does not accept arguments; got {len(node.arguments)}")

        collection_expr, dependencies, _, snapshot, _, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if not collection_expr:
                raise ValueError("distinct() requires a collection to operate on")

            # Check if collection_expr is a SELECT statement (from select(), combine(), etc.)
            # These cannot be wrapped in CASE expressions - we need to modify them directly
            if isinstance(collection_expr, str) and collection_expr.strip().upper().startswith("SELECT"):
                # Modify the SELECT to add DISTINCT to the aggregation
                distinct_sql = self._add_distinct_to_aggregate_select(collection_expr)
            else:
                # Standard case: wrap expression in CASE and apply distinct logic
                base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
                normalized_expr = self._normalize_collection_expression(base_expr)
                distinct_sql = (
                    "("
                    "CASE "
                    f"WHEN {normalized_expr} IS NULL THEN NULL "
                    f"ELSE {self._build_distinct_array(normalized_expr)} "
                    "END"
                    ")"
                )

            final_expr, metadata = self._apply_collection_remainder(
                node,
                distinct_sql,
                {"function": "distinct", "is_collection": True}
            )

            return SQLFragment(
                expression=final_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata=metadata
            )
        finally:
            self._restore_context(snapshot)

    def _translate_is_distinct(self, node: FunctionCallNode) -> SQLFragment:
        """Translate isDistinct() predicate to SQL.

        Handles two cases:
        1. Simple expressions: wraps in CASE and checks for duplicates
        2. SELECT statements (from select(), combine(), etc.): wraps in subquery and checks
        """
        if node.arguments:
            raise ValueError(f"isDistinct() does not accept arguments; got {len(node.arguments)}")

        collection_expr, dependencies, _, snapshot, _, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if not collection_expr:
                raise ValueError("isDistinct() requires a collection to operate on")

            # Check if collection_expr is a SELECT statement (from select(), combine(), etc.)
            if isinstance(collection_expr, str) and collection_expr.strip().upper().startswith("SELECT"):
                # Wrap the SELECT in a subquery and check if count(distinct) = count(all)
                is_distinct_sql = self._check_select_is_distinct(collection_expr)
            else:
                # Standard case: wrap expression in CASE and check for duplicates
                base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
                normalized_expr = self._normalize_collection_expression(base_expr)
                is_distinct_sql = (
                    "("
                    "CASE "
                    f"WHEN {normalized_expr} IS NULL THEN TRUE "
                    f"ELSE {self._build_is_distinct_condition(normalized_expr)} "
                    "END"
                    ")"
                )

            return SQLFragment(
                expression=is_distinct_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "isDistinct", "result_type": "boolean"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_intersect(self, node: FunctionCallNode) -> SQLFragment:
        """Translate intersect() set operation to SQL."""
        if len(node.arguments) != 1:
            raise ValueError(f"intersect() requires exactly 1 argument; got {len(node.arguments)}")

        left_expr, dependencies, _, snapshot, _, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if not left_expr:
                raise ValueError("intersect() requires a collection to operate on")

            right_fragment = self.visit(node.arguments[0])
            right_expr = right_fragment.expression
            if not right_expr:
                raise ValueError("intersect() argument must resolve to a collection")
            if hasattr(right_fragment, "dependencies"):
                dependencies.extend(right_fragment.dependencies)

            base_expr = self._extract_collection_source(left_expr, target_path, snapshot)
            normalized_left = self._normalize_collection_expression(base_expr)
            normalized_right = self._normalize_collection_expression(right_expr)
            intersect_sql = (
                "("
                "CASE "
                f"WHEN {normalized_left} IS NULL THEN NULL "
                f"ELSE {self._build_intersection_array(normalized_left, normalized_right)} "
                "END"
                ")"
            )

            final_expr, metadata = self._apply_collection_remainder(
                node,
                intersect_sql,
                {"function": "intersect", "is_collection": True}
            )

            return SQLFragment(
                expression=final_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata=metadata
            )
        finally:
            self._restore_context(snapshot)

    def _translate_union_function(self, node: FunctionCallNode) -> SQLFragment:
        """Translate union() function call to SQL.

        SP-110-FIX: union() function combines two collections, equivalent to the | operator.
        For example: 1.union(2) is equivalent to 1 | 2.

        The union() function is called as: target.union(argument)
        The target is stored in pending_fragment_result (set when visiting the target TermExpression)
        The argument is in node.arguments[0]
        """
        if len(node.arguments) != 1:
            raise ValueError(f"union() requires exactly 1 argument; got {len(node.arguments)}")

        # SP-110-FIX-2: For union() function call, the target is the pending_fragment_result
        # (the left operand of the dot invocation), not node.target (which is None)
        # For example: 1.union(2) has target=1 and argument=2

        # Get the target fragment from pending_fragment_result
        # This was set by visit_generic when it visited the TermExpression child before the functionCall
        target_fragment = None
        if hasattr(self.context, 'pending_fragment_result') and self.context.pending_fragment_result:
            # pending_fragment_result is a tuple: (expression, parent_path, is_multi_item)
            # We need to reconstruct a SQLFragment from this
            target_expr, target_path, target_is_multi = self.context.pending_fragment_result
            target_fragment = SQLFragment(
                expression=target_expr,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=[],
                metadata={"is_multi_item": target_is_multi}
            )
        else:
            raise ValueError("union() function requires a target (e.g., 1.union(2))")

        # Translate the argument (right operand)
        arg_fragment = self.visit(node.arguments[0])

        # Now build union SQL from the two fragments
        all_operands = [target_fragment, arg_fragment]

        # Build linear union SQL from all operand fragments
        union_sql = self._build_linear_union_sql(all_operands)

        # Apply collection remainder processing
        final_expr, metadata = self._apply_collection_remainder(
            node,
            union_sql,
            {"function": "union", "is_collection": True}
        )

        return SQLFragment(
            expression=final_expr,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=[],
            metadata=metadata
        )

    def _build_to_boolean_expression(self, value_expr: str) -> str:
        """Generate SQL for toBoolean() conversion."""
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        trimmed_string = self.dialect.generate_trim(string_cast)
        lowered_string = f"LOWER({trimmed_string})"
        decimal_cast = self.dialect.generate_type_cast(value_expr, "Decimal")

        return (
            "CASE "
            f"WHEN {value_expr} IS NULL THEN NULL "
            f"WHEN {decimal_cast} IS NOT NULL AND {decimal_cast} = 1 THEN TRUE "
            f"WHEN {decimal_cast} IS NOT NULL AND {decimal_cast} = 0 THEN FALSE "
            f"WHEN {string_cast} IS NOT NULL AND {lowered_string} IN ('true', 't', '1') THEN TRUE "
            f"WHEN {string_cast} IS NOT NULL AND {lowered_string} IN ('false', 'f', '0') THEN FALSE "
            "ELSE NULL "
            "END"
        )

    def _build_to_integer_expression(self, value_expr: str) -> str:
        """Generate SQL for toInteger() conversion."""
        integer_cast = self.dialect.generate_type_cast(value_expr, "Integer")
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        trimmed_string = self.dialect.generate_trim(string_cast)
        lowered_string = f"LOWER({trimmed_string})"
        decimal_cast = self.dialect.generate_type_cast(value_expr, "Decimal")

        return (
            "CASE "
            f"WHEN {integer_cast} IS NOT NULL THEN {integer_cast} "
            f"WHEN {decimal_cast} IS NOT NULL AND {string_cast} IS NULL "
            f"AND CAST({decimal_cast} AS INTEGER) = {decimal_cast} THEN CAST({decimal_cast} AS INTEGER) "
            f"WHEN {string_cast} IS NOT NULL AND {lowered_string} IN ('true', 't') THEN 1 "
            f"WHEN {string_cast} IS NOT NULL AND {lowered_string} IN ('false', 'f') THEN 0 "
            "ELSE NULL "
            "END"
        )

    def _build_to_string_expression(self, value_expr: str) -> str:
        """Generate SQL for toString() conversion."""
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        return string_cast

    def _build_to_decimal_expression(self, value_expr: str) -> str:
        """Generate SQL for toDecimal() conversion."""
        decimal_cast = self.dialect.generate_type_cast(value_expr, "Decimal")
        return decimal_cast

    def _build_to_quantity_expression(self, value_expr: str) -> str:
        """Generate SQL for toQuantity() conversion."""
        # For now, always return NULL - Quantity conversion needs UCUM support
        # Will be enhanced in future iterations
        return "NULL"

    def _build_to_date_expression(self, value_expr: str) -> str:
        """Generate SQL for toDate() conversion.

        SP-103-006: Implement toDate() SQL conversion.
        Converts a value to a Date string (ISO 8601 format).
        Only converts strings that match date format without time component.
        """
        # Cast to string first
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        trimmed_string = self.dialect.generate_trim(string_cast)

        # Check if it matches date pattern (YYYY, YYYY-MM, YYYY-MM-DD) without 'T'
        # Use regex to validate and return the trimmed string if valid, NULL otherwise
        date_pattern_basic = "^[0-9]{4}(-[0-9]{2})?(-[0-9]{2})?$"
        # Check for time separator 'T'
        contains_t = "POSITION('T' IN " + trimmed_string + ") > 0"
        regex_match = self.dialect.generate_regex_match(trimmed_string, "'" + date_pattern_basic + "'")

        return (
            "CASE "
            "WHEN " + regex_match + " AND NOT " + contains_t + " THEN " + trimmed_string + " "
            "ELSE NULL "
            "END"
        )

    def _build_to_datetime_expression(self, value_expr: str) -> str:
        """Generate SQL for toDateTime() conversion."""
        datetime_cast = self.dialect.generate_type_cast(value_expr, "DateTime")
        return datetime_cast

    def _build_to_time_expression(self, value_expr: str) -> str:
        """Generate SQL for toTime() conversion."""
        time_cast = self.dialect.generate_type_cast(value_expr, "Time")
        return time_cast

    def _translate_join(self, node: FunctionCallNode) -> SQLFragment:
        """Translate join() function for string collections."""
        collection_expr, dependencies, _, snapshot, target_ast, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if not collection_expr:
                raise ValueError("join() requires a collection to operate on")

            if len(node.arguments) > 1:
                raise ValueError(f"join() accepts at most 1 argument, got {len(node.arguments)}")

            if node.arguments:
                delimiter_fragment = self.visit(node.arguments[0])
                delimiter_expr = delimiter_fragment.expression
                if hasattr(delimiter_fragment, "dependencies"):
                    dependencies.extend(delimiter_fragment.dependencies)
            else:
                delimiter_expr = "''"

            join_source_expr = collection_expr
            is_json_collection = False
            if target_path:
                json_path = "$" if not target_path else "$." + ".".join(target_path)
                join_source_expr = self.dialect.extract_json_object(
                    column=snapshot["current_table"],
                    path=json_path
                )
                is_json_collection = True

            null_check_expr = join_source_expr if is_json_collection else collection_expr

            join_sql = self.dialect.generate_string_join(
                collection_expr=null_check_expr,
                delimiter_expr=delimiter_expr,
                is_json_collection=is_json_collection
            )

            return SQLFragment(
                expression=join_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies
            )
        finally:
            self._restore_context(snapshot)

    def _translate_exclude(self, node: FunctionCallNode) -> SQLFragment:
        """Translate exclude() set operation to SQL."""
        if len(node.arguments) != 1:
            raise ValueError(f"exclude() requires exactly 1 argument; got {len(node.arguments)}")

        collection_expr, dependencies, _, snapshot, _, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if not collection_expr:
                raise ValueError("exclude() requires a collection to operate on")

            exclusion_fragment = self.visit(node.arguments[0])
            exclusion_expr = exclusion_fragment.expression
            if not exclusion_expr:
                raise ValueError("exclude() argument must resolve to a collection")
            if hasattr(exclusion_fragment, "dependencies"):
                dependencies.extend(exclusion_fragment.dependencies)

            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_left = self._normalize_collection_expression(base_expr)
            normalized_right = self._normalize_collection_expression(exclusion_expr)
            exclude_sql = (
                "("
                "CASE "
                f"WHEN {normalized_left} IS NULL THEN NULL "
                f"ELSE {self._build_exclusion_array(normalized_left, normalized_right)} "
                "END"
                ")"
            )

            final_expr, metadata = self._apply_collection_remainder(
                node,
                exclude_sql,
                {"function": "exclude", "is_collection": True}
            )

            # SP-105: Extract columns that need to be preserved through CTEs
            # This fixes "column not found" errors when exclude() references columns
            # from previous CTEs (e.g., name_item, given_item)
            preserved_columns = self._extract_preserved_columns(
                SQLFragment(expression=base_expr, source_table=source_table),
                exclusion_fragment
            )

            return SQLFragment(
                expression=final_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata=metadata,
                preserved_columns=preserved_columns
            )
        finally:
            self._restore_context(snapshot)

    def _translate_subsetof(self, node: FunctionCallNode) -> SQLFragment:
        """Translate subsetOf() set comparison to SQL (returns boolean).

        The subsetOf() function returns true if all elements in this collection
        are also members of the other collection. Empty collections are considered
        subsets of any collection.

        FHIRPath Specification:
            collection.subsetOf(other : collection) : Boolean
            - Returns true if all elements in collection are in other
            - Empty collection is subset of any collection (returns true)
            - Uses value equality for comparison

        Args:
            node: FunctionCallNode representing subsetOf() function call

        Returns:
            SQLFragment with boolean result of subset check

        Raises:
            ValueError: If subsetOf() doesn't have exactly 1 argument

        Example:
            Input: Patient.name.first().subsetOf($this.name)
            - first() returns 1 name → check if that name is in all names
            - Result: true (single element is subset of collection containing it)

            Input: Patient.name.subsetOf($this.name.first())
            - All 3 names subset of just first name?
            - Result: false (collection not subset of single element)
        """
        logger.debug(f"Translating subsetOf() function with {len(node.arguments)} arguments")

        if len(node.arguments) != 1:
            raise ValueError(
                f"subsetOf() requires exactly 1 argument (comparison collection), "
                f"got {len(node.arguments)}"
            )

        # Get the left collection (this collection)
        left_expr, dependencies, _, snapshot, _, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if not left_expr:
                raise ValueError("subsetOf() requires a collection to operate on")

            # Get the right collection (other collection to compare against)
            right_fragment = self.visit(node.arguments[0])
            right_expr = right_fragment.expression
            if not right_expr:
                raise ValueError("subsetOf() argument must resolve to a collection")
            if hasattr(right_fragment, "dependencies"):
                dependencies.extend(right_fragment.dependencies)

            # Determine if expressions reference CTE output columns
            # Simple identifiers without parentheses are likely CTE column references
            left_is_cte_ref = (
                left_expr and
                left_expr.replace('`', '').replace('"', '').isidentifier() and
                '(' not in left_expr and
                not left_expr.startswith('json_')
            )
            right_is_cte_ref = (
                right_expr and
                right_expr.replace('`', '').replace('"', '').isidentifier() and
                '(' not in right_expr and
                not right_expr.startswith('json_')
            )

            # Get source tables for CTE references
            left_source = source_table if left_is_cte_ref else None
            right_source = right_fragment.source_table if right_is_cte_ref and hasattr(right_fragment, 'source_table') else None

            # Prepare expressions - normalize non-CTE refs, leave CTE refs as-is
            # SP-110-002: When left_expr is a simple column reference (like name_item),
            # it will be aliased as 'result' in the CTE output. We need to reference it
            # with the source_table qualifier to make it accessible in the current scope.
            if left_is_cte_ref:
                # Check if this is a simple _item column reference that needs qualification
                if left_expr.endswith('_item'):
                    # Qualify with source_table for proper reference in SQL
                    subset_expr = f"{source_table}.{left_expr}"
                else:
                    subset_expr = left_expr
            else:
                base_expr = self._extract_collection_source(left_expr, target_path, snapshot)
                subset_expr = self._normalize_collection_expression(base_expr)

            if right_is_cte_ref:
                # Check if this is a simple _item column reference that needs qualification
                if right_expr.endswith('_item') and right_fragment.source_table:
                    # Qualify with source_table for proper reference in SQL
                    superset_expr = f"{right_fragment.source_table}.{right_expr}"
                else:
                    superset_expr = right_expr
            else:
                superset_expr = self._normalize_collection_expression(right_expr)

            # Generate SQL to check if left is subset of right
            # Strategy: For each element in left, check if it exists in right
            # If all elements exist, return true; otherwise false
            subset_check_sql = self._build_subset_check(
                subset_expr,
                superset_expr,
                subset_source_table=left_source,
                superset_source_table=right_source,
                normalize_subset=not left_is_cte_ref,
                normalize_superset=not right_is_cte_ref
            )

            # SP-106: Extract columns that need to be preserved through CTEs
            # This fixes "column not found" errors when subsetOf() references columns
            # from previous CTEs (e.g., name_item, given_item)
            preserved_columns = self._extract_preserved_columns(
                SQLFragment(expression=subset_expr, source_table=source_table),
                right_fragment
            )

            return SQLFragment(
                expression=subset_check_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "subsetOf", "result_type": "boolean"},
                preserved_columns=preserved_columns
            )
        finally:
            self._restore_context(snapshot)

    def _translate_supersetof(self, node: FunctionCallNode) -> SQLFragment:
        """Translate supersetOf() set comparison to SQL (returns boolean).

        The supersetOf() function returns true if all elements in the other collection
        are also members of this collection. It's the inverse of subsetOf().

        FHIRPath Specification:
            collection.supersetOf(other : collection) : Boolean
            - Returns true if all elements in other are in collection
            - Any collection is superset of empty collection (returns true)
            - Uses value equality for comparison

        Args:
            node: FunctionCallNode representing supersetOf() function call

        Returns:
            SQLFragment with boolean result of superset check

        Raises:
            ValueError: If supersetOf() doesn't have exactly 1 argument

        Example:
            Input: Patient.name.supersetOf($this.name.first())
            - All 3 names superset of just first name?
            - Result: true (collection contains the single element)

            Input: Patient.name.first().supersetOf($this.name)
            - Single name superset of all 3 names?
            - Result: false (single element not superset of larger collection)
        """
        logger.debug(f"Translating supersetOf() function with {len(node.arguments)} arguments")

        if len(node.arguments) != 1:
            raise ValueError(
                f"supersetOf() requires exactly 1 argument (comparison collection), "
                f"got {len(node.arguments)}"
            )

        # Get the left collection (this collection)
        left_expr, dependencies, _, snapshot, _, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if not left_expr:
                raise ValueError("supersetOf() requires a collection to operate on")

            # Get the right collection (other collection to compare against)
            right_fragment = self.visit(node.arguments[0])
            right_expr = right_fragment.expression
            if not right_expr:
                raise ValueError("supersetOf() argument must resolve to a collection")
            if hasattr(right_fragment, "dependencies"):
                dependencies.extend(right_fragment.dependencies)

            # Determine if expressions reference CTE output columns
            left_is_cte_ref = (
                left_expr and
                left_expr.replace('`', '').replace('"', '').isidentifier() and
                '(' not in left_expr and
                not left_expr.startswith('json_')
            )
            right_is_cte_ref = (
                right_expr and
                right_expr.replace('`', '').replace('"', '').isidentifier() and
                '(' not in right_expr and
                not right_expr.startswith('json_')
            )

            left_source = source_table if left_is_cte_ref else None
            right_source = right_fragment.source_table if right_is_cte_ref and hasattr(right_fragment, 'source_table') else None

            # Prepare expressions - note: supersetOf swaps the arguments
            # (right is subset of left)
            # SP-110-002: When expressions are simple _item column references,
            # qualify them with their source tables for proper SQL reference.
            if left_is_cte_ref:
                if left_expr.endswith('_item'):
                    normalized_left = f"{source_table}.{left_expr}"
                else:
                    normalized_left = left_expr
            else:
                base_expr = self._extract_collection_source(left_expr, target_path, snapshot)
                normalized_left = self._normalize_collection_expression(base_expr)

            if right_is_cte_ref:
                if right_expr.endswith('_item') and right_fragment.source_table:
                    normalized_right = f"{right_fragment.source_table}.{right_expr}"
                else:
                    normalized_right = right_expr
            else:
                normalized_right = self._normalize_collection_expression(right_expr)

            # Generate SQL to check if left is superset of right
            # Strategy: Check if right is subset of left (inverse operation)
            superset_check_sql = self._build_subset_check(
                normalized_right,  # subset (swapped)
                normalized_left,   # superset (swapped)
                subset_source_table=right_source,
                superset_source_table=left_source,
                normalize_subset=not right_is_cte_ref,
                normalize_superset=not left_is_cte_ref
            )

            # SP-106: Extract columns that need to be preserved through CTEs
            # This fixes "column not found" errors when supersetOf() references columns
            # from previous CTEs (e.g., name_item, given_item)
            preserved_columns = self._extract_preserved_columns(
                SQLFragment(expression=normalized_left, source_table=source_table),
                right_fragment
            )

            return SQLFragment(
                expression=superset_check_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "supersetOf", "result_type": "boolean"},
                preserved_columns=preserved_columns
            )
        finally:
            self._restore_context(snapshot)

    def _translate_repeat(self, node: FunctionCallNode) -> SQLFragment:
        """Translate repeat() function to SQL with $this lambda variable support.

        The repeat() function performs recursive iteration over a collection, applying
        an expression to each element and collecting all results until no new elements
        are found. This is commonly used for traversing hierarchical structures like
        organization hierarchies or location partOf relationships.

        FHIRPath Specification:
            repeat(iteration : expression) : collection
            - Recursively applies iteration expression to each element
            - $this: current element being processed in iteration
            - Collects all elements encountered during recursion
            - Stops when no new elements are produced

        Implementation Strategy:
            Uses RECURSIVE CTE to implement recursive iteration semantics.
            The base case starts with the initial collection.
            The recursive case applies the iteration expression with $this bound
            to each element, continuing until no new elements are found or max depth reached.

        Args:
            node: FunctionCallNode representing repeat() function call

        Returns:
            SQLFragment with recursive SQL

        Raises:
            ValueError: If repeat() has invalid arguments

        Example:
            Input: Organization.repeat(partOf)
            - Iteration 0: Initial organizations
            - Iteration 1: Apply partOf to each org ($this = each org)
            - Iteration 2: Apply partOf to new orgs found
            - Continue until no new organizations or depth limit (100)
            - Return ALL organizations encountered
        """
        logger.debug(f"Translating repeat() function with {len(node.arguments)} arguments")

        # Validate arguments: repeat(iteration_expr)
        if len(node.arguments) != 1:
            raise ValueError(
                f"repeat() requires exactly 1 argument (iteration expression), "
                f"got {len(node.arguments)}"
            )

        # SP-110-XXX: Check if the iteration expression is a simple literal that doesn't use $this.
        # If the iteration expression is a literal (e.g., 'test', 1, true), then repeat()
        # should return just that literal. This is a degenerate case where the expression
        # doesn't reference $this, so no recursion is needed.
        # Example: Patient.name.repeat('test') returns 'test' (not an array)
        iter_arg = node.arguments[0]

        # Check if the argument is a literal (either direct node_type or contains a literal child)
        is_simple_literal = False
        if hasattr(iter_arg, 'node_type'):
            if iter_arg.node_type == 'Literal':
                is_simple_literal = True
            elif iter_arg.node_type == 'TermExpression' and hasattr(iter_arg, 'children'):
                # TermExpression wraps the actual literal node
                for child in iter_arg.children:
                    if hasattr(child, 'node_type') and child.node_type == 'literal':
                        is_simple_literal = True
                        break

        if is_simple_literal:
            logger.debug("repeat() with simple literal - returning literal directly")
            # Translate the literal and return it directly
            iter_fragment = self.visit(iter_arg)
            return iter_fragment

        # Get the collection to iterate over
        self._prefill_path_from_function(node)
        collection_path = self.context.get_json_path()

        logger.debug(f"Collection path for repeat(): {collection_path}")

        # Generate unique aliases for CTEs and columns
        cte_counter = self.context.cte_counter
        element_alias = f"repeat_elem_{cte_counter}"
        index_alias = f"{element_alias}_idx"
        depth_alias = f"{element_alias}_depth"
        enum_cte = f"repeat_enum_{cte_counter}"
        recursive_cte = f"repeat_recursive_{cte_counter}"
        result_alias = f"repeat_result_{cte_counter}"

        self.context.cte_counter += 1

        # Save current context for restoration
        old_table = self.context.current_table
        old_path = self.context.parent_path.copy()

        # Generate SQL for enumerating array elements from initial collection
        array_expr = self.dialect.extract_json_object(old_table, collection_path) if collection_path and collection_path != "$" else old_table

        # Use dialect method to enumerate array elements
        enumerate_sql = self.dialect.enumerate_json_array(array_expr, element_alias, index_alias)

        # Translate iteration expression with $this bound to current element
        # For base case and recursive case
        self.context.current_table = element_alias
        self.context.parent_path.clear()

        # Cast element from JSON to appropriate type for expression evaluation
        # Use dialect-specific cast to handle various JSON value types gracefully
        # This matches the pattern from aggregate() implementation
        # Use DOUBLE for numeric operations, can be extended for other types later
        element_cast = self.dialect.cast_to_double(element_alias)

        # SP-110 FIX: Save fragments length to prevent iteration expression fragments
        # from being added to self.fragments. These fragments reference internal CTE
        # variables (repeat_elem_N) that are only available inside the RECURSIVE CTE,
        # not in the wrapping CTE. By restoring the fragments length, we ensure these
        # fragments are only used for their SQL expressions in the template.
        fragments_before_iter = len(self.fragments)

        # Translate the iteration expression with $this binding
        with self._variable_scope({
            "$this": VariableBinding(
                expression=element_cast,
                source_table=enum_cte
            )
        }):
            iter_fragment = self.visit(node.arguments[0])

        # Remove any fragments created during iteration expression visit
        # These fragments reference internal CTE variables and should not be processed as separate CTEs
        del self.fragments[fragments_before_iter:]

        logger.debug(f"Iteration expression SQL: {iter_fragment.expression}")

        # For recursive case, we need to apply same expression to results
        # $this will be bound to r.element (the element from previous iteration)
        # Cast for recursive case as well
        recursive_element_cast = self.dialect.cast_to_double(f"r.{element_alias}")

        fragments_before_recursive = len(self.fragments)

        with self._variable_scope({
            "$this": VariableBinding(
                expression=recursive_element_cast,
                source_table="r"
            )
        }):
            recursive_iter_fragment = self.visit(node.arguments[0])

        # Remove any fragments created during recursive iteration expression visit
        del self.fragments[fragments_before_recursive:]

        logger.debug(f"Recursive iteration expression SQL: {recursive_iter_fragment.expression}")

        # Restore context
        self.context.current_table = old_table
        # SP-110 FIX: Clear parent_path after repeat() since it returns a complete new collection
        # Subsequent path navigation (like .code) should start from the result array,
        # not continue the path that was used inside the repeat() iteration.
        self.context.parent_path = []

        # Build RECURSIVE CTE SQL with cycle detection
        # Base case: initial collection (depth = 0)
        # Recursive case: apply iteration expression to elements from previous level
        # Continue until no new elements, max depth (100), or cycle detected
        path_alias = f"{element_alias}_path"

        # SP-110-XXX: Check if the iteration expression is a string literal
        # If so, we need to wrap it in to_json() to convert SQL string literal to JSON
        is_string_literal = (
            hasattr(iter_fragment, 'metadata') and
            iter_fragment.metadata.get('literal_type') == 'string'
        )

        # Wrap the iteration expression in to_json() if it's a string literal
        # This converts SQL string literal 'test' to JSON string "test"
        if is_string_literal:
            iter_expr_wrapped = f"to_json({iter_fragment.expression})"
            recursive_iter_expr_wrapped = f"to_json({recursive_iter_fragment.expression})"
        else:
            iter_expr_wrapped = iter_fragment.expression
            recursive_iter_expr_wrapped = recursive_iter_fragment.expression

        # Use aggregate_to_json_array to convert results to JSON array
        aggregate_expr = self.dialect.aggregate_to_json_array(f"{element_alias}")
        empty_array = self.dialect.empty_json_array()

        # SP-110-002: For repeat() with non-JSON values (like strings), we need to convert
        # the value to JSON before aggregation. The iteration expression might return
        # a string that's not valid JSON (e.g., "test" instead of "\"test\"").
        # Use to_json() to ensure proper JSON serialization.
        aggregate_expr = self.dialect.aggregate_to_json_array(f"to_json({element_alias})")

        sql = f"""(
    WITH RECURSIVE {enum_cte} AS (
        {enumerate_sql}
    ),
    {recursive_cte} AS (
        -- Base case: initial collection at depth 0 with path tracking
        SELECT
            {element_alias},
            0 as {depth_alias},
            ARRAY[{element_alias}] as {path_alias}
        FROM {enum_cte}

        UNION

        -- Recursive case: apply iteration expression to each element
        -- Continue until no new elements, max depth (100), or cycle detected
        SELECT DISTINCT
            {result_alias},
            r.{depth_alias} + 1 as {depth_alias},
            array_append(r.{path_alias}, {result_alias}) as {path_alias}
        FROM {recursive_cte} r
        CROSS JOIN LATERAL (
            SELECT {recursive_iter_expr_wrapped} as {result_alias}
        ) iteration
        WHERE r.{depth_alias} < 100
        AND iteration.{result_alias} IS NOT NULL
        AND NOT ({result_alias} = ANY(r.{path_alias}))
    )
    SELECT COALESCE({aggregate_expr}, {empty_array})
    FROM (SELECT DISTINCT {element_alias} FROM {recursive_cte}) AS distinct_results
)"""

        logger.debug(f"Complete repeat() SQL generated with RECURSIVE CTE and $this binding")

        # SP-110 FIX: Use a marker for the source table instead of a hardcoded CTE name.
        # The CTE manager's counter is separate from the translator's counter, so we can't
        # predict the exact CTE name. Instead, we use a marker that the CTE manager will
        # resolve to the actual previous CTE name during query generation.
        # Marker format: :marker: to distinguish from actual table names
        REPEAT_RESULT_MARKER = ":repeat_result_cte:"

        # SP-110 FIX: Update the current table to point to the marker
        # This ensures that subsequent operations like .code use the correct source
        self.context.current_table = REPEAT_RESULT_MARKER

        fragment = SQLFragment(
            expression=sql,
            source_table=REPEAT_RESULT_MARKER,  # Marker that CTE manager will resolve
            requires_unnest=False,   # The expression is self-contained
            is_aggregate=False,
            dependencies=iter_fragment.dependencies if hasattr(iter_fragment, 'dependencies') else [],
            metadata={
                "repeat_result": True,      # Mark this as a repeat() result
                "result_column": "result",  # The result column contains the array
                "clear_path_on_next": True, # Signal to clear path context for next operation
                "use_previous_cte": True    # Signal to use previous CTE as source
            }
        )
        # SP-110 FIX: Add fragment to self.fragments so subsequent identifier processing
        # can detect the repeat() result and handle it properly
        self.fragments.append(fragment)
        logger.info(f"SP-110: Added repeat_result fragment to self.fragments. Total fragments: {len(self.fragments)}, metadata keys={list(fragment.metadata.keys())}")
        return fragment

    def _translate_combine(self, node: FunctionCallNode) -> SQLFragment:
        """Translate combine() function for quick win scenarios."""
        if len(node.arguments) != 1:
            raise ValueError(
                f"combine() requires exactly 1 argument (collection to combine), got {len(node.arguments)}"
            )

        collection_expr, dependencies, _, snapshot, target_ast, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if not collection_expr:
                raise ValueError("combine() requires a source collection expression")

            # Bind $this to root resource when evaluating combine() argument
            # This enables expressions like: name.given.combine($this.name.family)
            # where $this refers to the root Patient resource
            with self._variable_scope({
                "$this": VariableBinding(
                    expression="resource",
                    source_table="resource"
                )
            }):
                other_fragment = self.visit(node.arguments[0])
                other_expr = other_fragment.expression
            if hasattr(other_fragment, 'dependencies'):
                dependencies.extend(other_fragment.dependencies)

            base_expr = collection_expr
            if target_path:
                json_path = "$" if not target_path else "$." + ".".join(target_path)
                base_expr = self.dialect.extract_json_object(
                    column=snapshot["current_table"],
                    path=json_path
                )

            normalized_left = self._normalize_collection_expression(base_expr)
            normalized_right = self._normalize_collection_expression(other_expr)

            combine_sql = self._compose_union_expression(
                base_expr,
                other_expr,
                normalized_left,
                normalized_right,
            )

            # SP-105: Extract columns that need to be preserved through CTEs
            # This fixes "column not found" errors when combine() references columns
            # from previous CTEs (e.g., name_item, given_item)
            preserved_columns = self._extract_preserved_columns(
                SQLFragment(expression=base_expr, source_table=source_table),
                other_fragment
            )

            return SQLFragment(
                expression=combine_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies,
                metadata={"function": "combine", "is_collection": True},
                preserved_columns=preserved_columns
            )
        finally:
            self._restore_context(snapshot)

    def visit_polarity_expression(self, node: Any) -> SQLFragment:
        """Translate unary polarity expressions (+, -) to SQL.

        Handles unary plus and minus operators applied to expressions.
        In FHIRPath, unary operators have high precedence and bind tightly
        to their operands.

        This method ensures that expressions like (-1) are correctly translated
        as negative literals, and that attempting to negate a boolean results
        in a type error (as expected by FHIRPath semantics).

        Grammar:
            PolarityExpression: ('+' | '-') Expression

        Examples:
            (-1) -> -1 (SQL negative literal)
            (-Patient.value.count()) -> -(COUNT(...)) (negated count)

        Args:
            node: EnhancedASTNode with node_type='PolarityExpression'

        Returns:
            SQLFragment with the unary operator applied to the operand

        Raises:
            FHIRPathTranslationError: If trying to negate a boolean value

        Note:
            The polarity operator is stored in node.text ('+' or '-')
            The operand is the first child node
        """
        logger.debug(f"Translating polarity expression: {node.text}")

        # Get the operator from the node text
        operator = node.text if hasattr(node, 'text') else None

        if not operator or operator not in ('+', '-'):
            logger.warning(f"Invalid polarity operator: {operator}")
            # Fall back to generic visitor
            return self.visit_generic(node)

        # Visit the child expression to get the operand
        if not hasattr(node, 'children') or len(node.children) == 0:
            raise FHIRPathTranslationError(
                f"PolarityExpression has no child operand"
            )

        child = node.children[0]

        # SP-110-R3: Special handling for polarity before invocation on literal
        # In FHIRPath, -1.convertsToInteger() should return -1, not error
        # But the grammar parses it as -(1.convertsToInteger()) which would try to negate the boolean result
        # Solution: Detect when child is invocation on a literal, modify the literal text, then visit normally
        if (operator == '-' and
            hasattr(child, 'node_type') and
            child.node_type == 'InvocationExpression' and
            len(child.children) > 0):
            # Check if the invocation target is a TermExpression with a literal
            target = child.children[0]
            if (hasattr(target, 'node_type') and
                target.node_type == 'TermExpression' and
                len(target.children) > 0):
                term_child = target.children[0]
                # Handle both 'literal' and 'LiteralExpression' node types
                if (hasattr(term_child, 'node_type') and
                    term_child.node_type in ('literal', 'LiteralExpression') and
                    hasattr(term_child, 'text')):
                    # Check if this is a numeric literal (starts with digit)
                    literal_text = term_child.text
                    if literal_text and literal_text[0].isdigit():
                        # Modify the literal text to include the minus sign
                        # This way when the invocation is visited, it sees -1 instead of 1
                        original_text = term_child.text
                        term_child.text = f"-{literal_text}"

                        # Also need to update the invocation's text for consistency
                        if hasattr(child, 'text'):
                            child.text = f"-{child.text}"

                        # Now visit the child - it will see the negated literal
                        result = self.visit(child)

                        # Restore original text (optional, since node is discarded)
                        term_child.text = original_text

                        return result

        # Visit the child expression to get the operand
        child_fragment = self.visit(child)

        if operator == '-':
            # Check if the child is a literal (simple numeric negation)
            if (hasattr(child_fragment, 'metadata') and
                child_fragment.metadata.get('is_literal')):
                # SP-110-003: Direct literal negation for numeric types
                # For numeric literals (integer, decimal), produce negative literal directly
                # e.g., -1, -0.1 instead of -("1"), -("0.1")
                # This ensures convertsToInteger() and convertsToDecimal() work correctly
                # SP-110-005: Handle quantity literals with negation (e.g., (-5.5 'mg').abs())
                literal_type = child_fragment.metadata.get('literal_type', '')

                # Reject unary minus on boolean literals (semantic error per FHIRPath spec)
                if literal_type == 'boolean':
                    raise FHIRPathTranslationError(
                        f"Cannot apply unary minus operator to non-numeric result. "
                        f"Operator '-' requires numeric operand, but got 'boolean'."
                    )

                if literal_type in ('integer', 'decimal'):
                    # Strip quotes if expression is quoted (shouldn't happen but safety check)
                    expr = child_fragment.expression
                    if expr.startswith("'") and expr.endswith("'"):
                        expr = expr[1:-1]
                    # Direct negation: -1, -0.1
                    negated_expr = f"-{expr}"

                    # SP-110-003: Update pending_literal_value with negated value
                    # This ensures convertsTo*() functions get the correct negated literal
                    if self.context.pending_literal_value is not None:
                        old_value, old_expr = self.context.pending_literal_value
                        # Negate the value
                        if literal_type == 'integer':
                            new_value = -int(old_value) if isinstance(old_value, (int, float)) else old_value
                        else:  # decimal
                            new_value = -float(old_value) if isinstance(old_value, (int, float)) else old_value
                        self.context.pending_literal_value = (new_value, negated_expr)
                elif literal_type == 'quantity':
                    # SP-110-005: Handle quantity literal negation
                    # For quantities like "5.5 'mg'", we need to negate the value but keep the unit
                    quantity_value = child_fragment.metadata.get('quantity_value')
                    quantity_unit = child_fragment.metadata.get('quantity_unit')

                    if quantity_value is not None:
                        # Negate the quantity value
                        try:
                            negated_value = -Decimal(str(quantity_value))
                            # Build new quantity JSON with negated value
                            from ..types.quantity_builder import build_quantity_json_string
                            quantity_json = build_quantity_json_string(negated_value, quantity_unit)
                            negated_expr = f"'{quantity_json}'"

                            # Update pending_literal_value with negated quantity
                            self.context.pending_literal_value = (NegatedQuantityMarker(negated_value, quantity_unit), negated_expr)

                            # Update metadata with negated value
                            result_metadata = dict(child_fragment.metadata)
                            result_metadata['quantity_value'] = str(negated_value)

                            return SQLFragment(
                                expression=negated_expr,
                                source_table=child_fragment.source_table,
                                requires_unnest=child_fragment.requires_unnest,
                                is_aggregate=child_fragment.is_aggregate,
                                metadata=result_metadata
                            )
                        except (InvalidOperation, TypeError):
                            # Fall through to default negation
                            pass
                else:
                    # For other literals, use parenthesized negation
                    negated_expr = f"-({child_fragment.expression})"

                # Create new fragment with negated expression
                result_metadata = dict(child_fragment.metadata)
                # Keep is_literal flag for downstream functions
                result_metadata['is_literal'] = True
                return SQLFragment(
                    expression=negated_expr,
                    source_table=child_fragment.source_table,
                    requires_unnest=child_fragment.requires_unnest,
                    is_aggregate=child_fragment.is_aggregate,
                    metadata=result_metadata
                )
            else:
                # Complex expression negation: -(COUNT(...)), etc.
                # We need to check if the result type is numeric
                # If it's a boolean, this should fail (FHIRPath semantic error)
                metadata = getattr(child_fragment, 'metadata', {})
                result_type = metadata.get('result_type') or metadata.get('type')

                # Check if this is a boolean expression (e.g., convertsToInteger() result)
                # If so, negation should fail
                if result_type == 'boolean' or metadata.get('function') in ('convertsToBoolean', 'convertsToInteger', 'convertsToString', 'convertsToDecimal', 'convertsToDateTime', 'convertsToDate', 'convertsToTime'):
                    # The child expression returns a boolean or type conversion result
                    # Negating a boolean is a semantic error in FHIRPath
                    raise FHIRPathTranslationError(
                        f"Cannot apply unary minus operator to non-numeric result. "
                        f"Operator '-' requires numeric operand, but got '{result_type or 'unknown'}'."
                    )

                # For other expressions, apply the negation
                negated_expr = f"-({child_fragment.expression})"

                result_metadata = dict(metadata)
                return SQLFragment(
                    expression=negated_expr,
                    source_table=child_fragment.source_table,
                    requires_unnest=child_fragment.requires_unnest,
                    is_aggregate=child_fragment.is_aggregate,
                    metadata=result_metadata
                )
        else:  # operator == '+'
            # Unary plus is a no-op in SQL, just return the child fragment
            return child_fragment

    def visit_type_operation(self, node: TypeOperationNode) -> SQLFragment:
        """Translate type operations to SQL.

        Converts FHIRPath type operations (is, as, ofType) to SQL type checking
        and casting expressions.

        Args:
            node: TypeOperationNode representing a type operation

        Returns:
            SQLFragment containing the type operation SQL

        Raises:
            NotImplementedError: If operation type is not yet implemented
            ValueError: If type operation is invalid

        Example:
            is() operation:
            >>> node = TypeOperationNode(operation="is", target_type="String", children=[expr_node])
            >>> fragment = translator.visit_type_operation(node)
            >>> # Returns SQLFragment with SQL type checking expression

        Business Logic (in Translator):
            - Type mapping from FHIRPath types to SQL constructs
            - Collection handling (test first element only for is())
            - Operation dispatch (is, as, ofType)

        Syntax Only (in Dialect):
            - Database-specific type checking functions (json_type vs jsonb_typeof)
            - Database-specific casting syntax
        """
        # SP-103-005: Debug node structure
        logger.debug(f"Translating type operation: {node.operation} with target type: {node.target_type}")
        logger.debug(f"SP-103-005: node type: {type(node).__name__}")
        logger.debug(f"SP-103-005: node.text: {getattr(node, 'text', 'N/A')}")
        logger.debug(f"SP-103-005: node.children: {len(node.children) if hasattr(node, 'children') else 'N/A'}")
        logger.debug(f"SP-103-005: hasattr enhanced_node: {hasattr(node, 'enhanced_node')}")
        if hasattr(node, 'enhanced_node'):
            logger.debug(f"SP-103-005: enhanced_node.parent: {node.enhanced_node.parent}")
            logger.debug(f"SP-103-005: enhanced_node.parent.text: {getattr(node.enhanced_node.parent, 'text', 'N/A') if node.enhanced_node.parent else 'N/A'}")
            if node.enhanced_node.parent and hasattr(node.enhanced_node.parent, 'children'):
                logger.debug(f"SP-103-005: enhanced_node.parent.children: {len(node.enhanced_node.parent.children)}")
                for i, child in enumerate(node.enhanced_node.parent.children):
                    logger.debug(f"SP-103-005: enhanced_node.parent child {i}: '{child.text}'")

        # Validate operation
        if not node.operation:
            raise ValueError("Type operation must specify an operation (is, as, ofType)")
        if not node.target_type:
            raise ValueError("Type operation must specify a target type")

        # Dispatch based on operation type
        if node.operation == "is":
            return self._translate_is_operation(node)
        elif node.operation == "as":
            return self._translate_as_operation(node)
        elif node.operation == "ofType":
            return self._translate_oftype_operation(node)
        else:
            raise ValueError(f"Unknown type operation: {node.operation}")

    def _translate_is_operation(self, node: TypeOperationNode) -> SQLFragment:
        """Translate is() type checking operation to SQL.

        The is() function tests if a value is of a specific type. It returns true
        if the value matches the specified type, false otherwise. For collections,
        it tests only the first element.

        Args:
            node: TypeOperationNode with operation="is"

        Returns:
            SQLFragment containing SQL type checking expression

        Raises:
            ValueError: If node has no children (expression to check)

        Example:
            Input: 5 is Integer
            Output: SQL that checks if 5 is an integer type
        """
        if not node.children:
            raise ValueError("is() operation requires an expression to check")

        # SP-104-002: Check if node has value_expression attribute (from parent InvocationExpression)
        # This handles cases like "@2015.is(Date)" where the literal is a sibling in the parent
        if hasattr(node, 'value_expression') and node.value_expression is not None:
            # Visit the value expression from the parent
            expr_fragment = self.visit(node.value_expression)
        elif node.children:
            # Fall back to visiting the first child
            expr_fragment = self.visit(node.children[0])
        else:
            raise ValueError("is() operation requires an expression to check")

        canonical_type = self._resolve_canonical_type(node.target_type)
        normalized = canonical_type.lower()

        # SP-104-002: Extract original literal for temporal type checking
        original_literal = None
        if hasattr(expr_fragment, 'metadata') and expr_fragment.metadata:
            if expr_fragment.metadata.get('is_literal'):
                original_literal = (
                    expr_fragment.metadata.get('source_text') or
                    expr_fragment.metadata.get('text') or
                    expr_fragment.metadata.get('temporal_info', {}).get('original') if expr_fragment.metadata.get('temporal_info') else None
                )

        primitive_families = {
            "uri",
            "url",
            "canonical",
            "oid",
            "uuid",
            "id",
            "code",
            "markdown",
        }

        if normalized == "any":
            type_check_sql = (
                f"CASE WHEN {expr_fragment.expression} IS NULL THEN false ELSE true END"
            )
        elif normalized == "collection":
            type_check_sql = (
                f"CASE WHEN {expr_fragment.expression} IS NULL THEN false ELSE true END"
            )
        # SP-104-002: Check for temporal literals first
        elif original_literal and original_literal.startswith('@'):
            # Temporal literal - use literal type check
            type_check_sql = self._generate_literal_type_check(
                expr_fragment.expression,
                canonical_type,
                original_literal,
                node  # Pass node for metadata access
            )
        # SP-108-002: Check for SQL literal expressions (numeric, string, boolean)
        # This avoids calling json_type() on non-JSON values which causes SQL errors
        elif self._is_sql_literal_expression(expr_fragment.expression):
            type_check_sql = self._generate_literal_type_check(
                expr_fragment.expression,
                canonical_type,
                original_literal,
                node
            )
        elif self._is_primitive_type(canonical_type) or normalized in primitive_families:
            type_check_sql = self.dialect.generate_type_check(
                expr_fragment.expression,
                canonical_type,
            )
        elif self._is_complex_type(canonical_type) or self._is_resource_type(canonical_type):
            type_check_sql = self._generate_complex_type_check(
                expr_fragment.expression,
                canonical_type,
            )
        else:
            # Fallback for unknown types: check if it's a complex FHIR type
            # This maintains thin dialect principle - business logic stays in translator
            from fhir4ds.fhirpath.types.fhir_type_constants import is_complex_fhir_type
            if is_complex_fhir_type(normalized):
                type_check_sql = self._generate_complex_type_check(
                    expr_fragment.expression,
                    canonical_type,
                )
            else:
                # Assume primitive for truly unknown types
                type_check_sql = self.dialect.generate_type_check(
                    expr_fragment.expression,
                    canonical_type,
                )

        logger.debug(f"Generated is() type check SQL for type '{canonical_type}'")

        return SQLFragment(
            expression=type_check_sql,
            source_table=expr_fragment.source_table,
            requires_unnest=False,  # Type check returns boolean, not collection
            is_aggregate=False,  # Type check is scalar operation
            dependencies=expr_fragment.dependencies,
            metadata={"function": "is", "result_type": "boolean"}
        )

    def _translate_as_operation(self, node: TypeOperationNode) -> SQLFragment:
        """Translate as() type casting operation to SQL.

        The as() function converts a value to a specific type. It returns the converted
        value if the conversion is successful, or null if the conversion fails.
        For collections, it casts only the first element.

        Args:
            node: TypeOperationNode with operation="as"

        Returns:
            SQLFragment containing SQL type casting expression

        Raises:
            ValueError: If node has no children (expression to cast)

        Example:
            Input: '123' as Integer
            Output: SQL that casts '123' to integer type

            Input: Procedure.performed as DateTime
            Output: SQL that casts Procedure.performed to datetime type

        SP-107-001: Handles path navigation after .as() operation
        """
        # Type operation should have exactly one child (the expression to cast)
        # SP-104-002: Check for value_expression attribute (from parent InvocationExpression)
        # This handles cases like "@2015.as(Date)" where the literal is a sibling in the parent
        if hasattr(node, 'value_expression') and node.value_expression is not None:
            # Use the value expression from the parent
            child_node = node.value_expression
        elif node.children:
            # Fall back to the first child
            child_node = node.children[0]
        else:
            raise ValueError("as() operation requires an expression to cast")

        # Snapshot context so polymorphic path traversal does not leak state
        snapshot = self._snapshot_context()
        try:
            expr_fragment = self.visit(child_node)
        finally:
            # Always restore - downstream operations assume original context
            self._restore_context(snapshot)

        canonical_type = self._resolve_canonical_type(node.target_type)
        logger.debug(
            "Casting expression '%s' to canonical type '%s'",
            expr_fragment.expression,
            canonical_type,
        )

        fragment = self._build_type_cast_fragment(
            source_node=child_node,
            expr_fragment=expr_fragment,
            canonical_type=canonical_type,
            original_expression=node.text,
        )

        self._reapply_parent_path_for_type_cast(
            previous_parent_path=snapshot["parent_path"],
            child_node=child_node,
            fragment=fragment,
        )

        # SP-107-001: Handle path navigation after .as() operation
        # For expressions like "Observation.value.as(Quantity).unit", we need to:
        # 1. Detect that there's a ".unit" after the .as() operation
        # 2. Set up the polymorphic field mapping so subsequent field access uses the resolved field
        if hasattr(node, 'enhanced_node') and node.enhanced_node.parent:
            parent = node.enhanced_node.parent
            # Check if parent's parent has more children (indicating additional navigation after .as())
            if hasattr(parent, 'parent') and parent.parent:
                grandparent = parent.parent
                if hasattr(grandparent, 'children') and len(grandparent.children) >= 2:
                    # The grandparent is the root invocation with the full expression
                    # child[0] is the .as() invocation (or its parent), child[1]+ are subsequent navigations
                    # Check if the first child is our parent (the .as() part)
                    if grandparent.children[0] == parent and len(grandparent.children) > 1:
                        next_child = grandparent.children[1]
                        if hasattr(next_child, 'text') and next_child.text:
                            # Extract the path from the next child
                            path_after = next_child.text.lstrip('.')
                            logger.debug(f"SP-107-001: Detected path after .as(): {path_after}")

                            # Get the property name from the child node
                            property_name = None
                            if isinstance(child_node, IdentifierNode):
                                identifier_value = child_node.identifier or child_node.text or ""
                                if identifier_value:
                                    property_name = identifier_value.split(".")[-1].strip("`")
                            elif hasattr(child_node, 'text') and child_node.text:
                                property_name = child_node.text.split(".")[-1].strip("`")

                            # Check if it's a polymorphic property
                            if property_name and is_polymorphic_property(property_name):
                                # Resolve to type-specific field
                                polymorphic_field = resolve_polymorphic_field_for_type(property_name, canonical_type)

                                if polymorphic_field:
                                    logger.debug(
                                        f"SP-107-001: Setting up polymorphic mapping for .as(): {property_name} -> {polymorphic_field}"
                                    )

                                    # Set up the mapping for subsequent navigation
                                    if not hasattr(self.context, 'polymorphic_field_mappings'):
                                        self.context.polymorphic_field_mappings = {}
                                    self.context.polymorphic_field_mappings[property_name] = polymorphic_field

                                    # Update parent_path to include the resolved field and subsequent path
                                    self.context.push_path(polymorphic_field)
                                    if path_after:
                                        # Split by dots in case there are multiple levels
                                        after_components = path_after.split('.')
                                        for component in after_components:
                                            self.context.push_path(component)

                                    logger.debug(
                                        f"SP-107-001: Updated parent_path after .as(): {self.context.parent_path}"
                                    )

        logger.debug(
            "Generated as() SQL for type '%s': %s",
            canonical_type,
            fragment.expression,
        )
        return fragment

    def _translate_oftype_operation(self, node: TypeOperationNode) -> SQLFragment:
        """Translate ofType() type filtering operation to SQL.

        The ofType() function filters a collection to return only items that match
        the specified type. For single values, it returns the value if it matches
        the type, or an empty collection if not. For collections, it filters to
        include only items of the specified type.

        This is implemented using SQL array filtering with type checking. The
        translator generates the filtering logic, and the dialect provides the
        database-specific syntax for array filtering and type checking.

        Args:
            node: TypeOperationNode with operation="ofType"

        Returns:
            SQLFragment containing SQL type filtering expression

        Raises:
            ValueError: If node has no children (expression to filter)

        Example:
            Input: Observation.component.value.ofType(Quantity)
            Output: SQL that filters component.value array to only Quantity types

            Input: Bundle.entry.resource.ofType(Patient)
            Output: SQL that filters resources to only Patient types
        """
        # Type operation should have exactly one child (the expression to filter)
        if not node.children:
            raise ValueError("ofType() operation requires an expression to filter")

        # Capture parent_path BEFORE visiting child to detect if we're at root level
        parent_path_before_child = self.context.parent_path.copy()

        logger.debug(f"SP-103-005: _translate_oftype_operation: parent_path_before_child={parent_path_before_child}")

        # Get the collection expression to filter
        expr_fragment = self.visit(node.children[0])

        logger.debug(f"Filtering collection '{expr_fragment.expression}' by type '{node.target_type}'")

        canonical_type = self._resolve_canonical_type(node.target_type)
        filter_target_type = canonical_type

        child_node = node.children[0]
        property_name: Optional[str] = None
        if isinstance(child_node, IdentifierNode):
            identifier_value = child_node.identifier or child_node.text or ""
            if identifier_value:
                property_name = identifier_value.split(".")[-1].strip("`")
        else:
            # SP-103-005: Handle TypeOperationNodeAdapter wrapping EnhancedASTNode
            # The adapter wraps the ofType() node, which is child 1 of the parent.
            # Child 0 of the parent is the identifier (e.g., 'value').
            logger.debug(f"SP-103-005: child_node type: {type(child_node).__name__}, text: {getattr(child_node, 'text', 'N/A')}")

            # Access the parent through enhanced_node
            if hasattr(node, 'enhanced_node') and node.enhanced_node.parent:
                parent = node.enhanced_node.parent
                logger.debug(f"SP-103-005: Found parent through enhanced_node: {parent.text}")

                # The parent should have 2 children: [identifier, ofType()]
                if hasattr(parent, 'children') and len(parent.children) >= 1:
                    identifier_child = parent.children[0]
                    identifier_text = getattr(identifier_child, 'text', '')
                    if identifier_text and 'ofType' not in identifier_text:
                        property_name = identifier_text.split(".")[-1].strip("`")
                        logger.debug(f"SP-103-005: Extracted property_name from parent child 0: {property_name}")

        logger.debug(f"SP-103-005: _translate_oftype_operation: property_name={property_name}, is_polymorphic={is_polymorphic_property(property_name) if property_name else False}")

        # POLYMORPHIC FIELD HANDLING:
        # If the child is a polymorphic property (e.g., "value"), use type-specific field resolution
        # instead of type filtering. In FHIR, polymorphic fields encode the type in the field name.
        # Example: value.ofType(integer) → extract $.valueInteger
        #          value.ofType(Range) → extract $.valueRange
        # IMPORTANT: Only apply this for direct property access (e.g., $.value), not nested
        # (e.g., $.component.value) to avoid breaking collection filtering
        if property_name and is_polymorphic_property(property_name):
            # Check if this is a direct property access
            # Direct access: parent_path contains only the property name (e.g., ['value'])
            # Nested access: parent_path contains multiple elements (e.g., ['component', 'value'])
            # SP-105-004: Also treat empty parent_path as direct access when property_name matches
            # This handles cases where the identifier hasn't been visited yet in the current context
            is_direct_access = (
                (len(parent_path_before_child) == 0 or len(parent_path_before_child) == 1) and
                (len(parent_path_before_child) == 0 or parent_path_before_child[0] == property_name)
            )

            if is_direct_access:
                polymorphic_field = resolve_polymorphic_field_for_type(property_name, canonical_type)
                if polymorphic_field:
                    logger.debug(f"Resolved polymorphic field: {property_name} + {canonical_type} → {polymorphic_field}")
                    logger.debug(f"Parent path before: {self.context.parent_path}")

                    # SP-105-004: Check if there's subsequent navigation after ofType()
                    # We need to look at the parent's parent to see if there are MemberInvocations
                    has_subsequent_navigation = False
                    if hasattr(node, 'enhanced_node') and node.enhanced_node:
                        enhanced_node = node.enhanced_node
                        if hasattr(enhanced_node, 'parent') and enhanced_node.parent:
                            grandparent = enhanced_node.parent
                            # Check if grandparent has more children after the current parent
                            # This indicates there's more navigation (e.g., .low.value)
                            if hasattr(grandparent, 'children') and len(grandparent.children) > 1:
                                has_subsequent_navigation = True
                                logger.debug(f"SP-105-004: Detected subsequent navigation after ofType(), will continue chain")

                    if has_subsequent_navigation:
                        # SP-105-004: When there's subsequent navigation, update parent_path to use
                        # the resolved polymorphic field, but DON'T return early. Let the navigation
                        # continue from the resolved field.
                        if self.context.parent_path and self.context.parent_path[-1] == property_name:
                            # Replace the last element
                            self.context.parent_path[-1] = polymorphic_field
                        else:
                            # Append if the structure is different than expected
                            self.context.parent_path.append(polymorphic_field)
                        logger.debug(f"SP-105-004: Updated parent_path for subsequent navigation: {self.context.parent_path}")

                        # Store the polymorphic field mapping for subsequent identifier visits
                        if not hasattr(self.context, 'polymorphic_field_mappings'):
                            self.context.polymorphic_field_mappings = {}
                        self.context.polymorphic_field_mappings[property_name] = polymorphic_field
                        logger.debug(f"SP-105-004: Stored polymorphic mapping for chain: {property_name} -> {polymorphic_field}")

                        # Fall through to continue with navigation after updating context
                        # Don't return early - let subsequent identifiers build the full path
                    else:
                        # No subsequent navigation - return the polymorphic field extraction
                        # Build JSON path for the polymorphic field
                        # Need to extract the source table from the expression
                        source_table = expr_fragment.source_table or self.context.current_table
                        json_path = f"$.{polymorphic_field}"

                        # Extract the polymorphic field directly - no type filtering needed
                        # because the field name already guarantees the type!
                        poly_field_sql = self.dialect.extract_json_object(
                            column=source_table,
                            path=json_path
                        )

                        logger.debug(f"Generated polymorphic field extraction SQL for {polymorphic_field}")

                        # SP-103-005: Update parent_path to reflect the resolved type
                        # The current path ends with the base property name (e.g., 'value'),
                        # and we need to replace it with the polymorphic field (e.g., 'valueRange')
                        if self.context.parent_path and self.context.parent_path[-1] == property_name:
                            # Replace the last element
                            self.context.parent_path[-1] = polymorphic_field
                        else:
                            # Append if the structure is different than expected
                            self.context.parent_path.append(polymorphic_field)
                        logger.debug(f"Parent path after: {self.context.parent_path}")

                        # SP-103-005: Store the polymorphic field mapping in context for subsequent identifier visits
                        # This allows identifiers like 'low' to know that 'value' was resolved to 'valueRange'
                        if not hasattr(self.context, 'polymorphic_field_mappings'):
                            self.context.polymorphic_field_mappings = {}
                        self.context.polymorphic_field_mappings[property_name] = polymorphic_field
                        logger.debug(f"SP-103-005: Stored polymorphic mapping: {property_name} -> {polymorphic_field}")

                        return SQLFragment(
                            expression=poly_field_sql,
                            source_table=source_table,
                            requires_unnest=False,
                            is_aggregate=False,
                            dependencies=expr_fragment.dependencies
                        )

        type_metadata: Dict[str, Any] = {}
        if canonical_type:
            type_metadata = self.type_registry.get_type_metadata(canonical_type) or {}

        if expr_fragment.requires_unnest and not type_metadata.get("is_primitive", False):
            filter_target_type = None

        if property_name:
            variants = resolve_polymorphic_property(property_name)
            if variants and not type_metadata.get("is_primitive", False):
                filter_target_type = None

        # Generate database-specific collection type filtering SQL using dialect method
        # Business logic: ofType filters collections by type
        # Dialect provides: database-specific array filtering and type checking syntax
        normalized_collection_expr = self._normalize_collection_expression(expr_fragment.expression)

        type_filter_sql = self.dialect.generate_collection_type_filter(
            expression=normalized_collection_expr,
            target_type=filter_target_type
        )

        logger.debug(f"Generated ofType() type filter SQL for type '{canonical_type}'")

        return SQLFragment(
            expression=type_filter_sql,
            source_table=expr_fragment.source_table,
            requires_unnest=False,  # Filtering returns collection, doesn't require additional unnest
            is_aggregate=False,  # Type filtering is not an aggregation
            dependencies=expr_fragment.dependencies
        )

    def _generate_complex_type_check(self, expression: str, canonical_type: str) -> str:
        """Generate SQL that validates structural requirements for complex types."""
        discriminator = get_type_discriminator(canonical_type) or {}
        required_fields = discriminator.get("required_fields", []) if discriminator else []

        if required_fields:
            existence_checks = [
                self.dialect.check_json_exists(expression, f"$.{field}")
                for field in required_fields
            ]
            condition = " AND ".join(existence_checks)
            return (
                f"CASE "
                f"WHEN {expression} IS NULL THEN false "
                f"WHEN {condition} THEN true "
                f"ELSE false "
                f"END"
            )

        return f"CASE WHEN {expression} IS NOT NULL THEN true ELSE false END"

    # -------------------------------------------------------------------------
    # Type casting helpers
    # -------------------------------------------------------------------------

    def _build_type_cast_fragment(
        self,
        source_node: FHIRPathASTNode,
        expr_fragment: SQLFragment,
        canonical_type: str,
        original_expression: str = "",
    ) -> SQLFragment:
        """Build SQL fragment for type casting with primitive/complex routing."""
        type_metadata = self.type_registry.get_type_metadata(canonical_type) or {}
        is_complex = type_metadata.get("is_complex", False)
        is_resource = type_metadata.get("is_resource", False)

        if is_complex:
            # SP-024-003: Check if source_node is an IdentifierNode or an EnhancedASTNode with identifier text
            is_identifier = isinstance(source_node, IdentifierNode)
            is_path_expression = (
                isinstance(source_node, EnhancedASTNode) and
                hasattr(source_node, 'text') and
                source_node.text and
                '.' in source_node.text  # Contains dots, indicating a path expression
            )

            if is_identifier or is_path_expression:
                # If it's an EnhancedASTNode, create a fake IdentifierNode for processing
                identifier_node = source_node if is_identifier else IdentifierNode(
                    node_type="identifier",
                    text=source_node.text,
                    identifier=source_node.text
                )
                return self._build_complex_type_cast_fragment(
                    identifier_node=identifier_node,
                    expr_fragment=expr_fragment,
                    canonical_type=canonical_type,
                    type_metadata=type_metadata,
                    original_expression=original_expression,
                )
            logger.warning(
                "Complex type cast for '%s' requires identifier node (expr: %s)",
                canonical_type,
                original_expression,
            )
            return self._build_null_fragment(expr_fragment, canonical_type)

        if is_resource:
            logger.warning(
                "Resource type cast not implemented for '%s' in expression '%s'",
                canonical_type,
                original_expression,
            )
            return self._build_null_fragment(expr_fragment, canonical_type)

        # Default to dialect primitive casting
        type_cast_sql = self.dialect.generate_type_cast(
            expression=expr_fragment.expression,
            target_type=canonical_type,
        )

        metadata = {
            "type_operation": "as",
            "target_type": canonical_type,
            "original_expression": original_expression,
            "mode": "primitive",
        }

        return SQLFragment(
            expression=type_cast_sql,
            source_table=expr_fragment.source_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=list(expr_fragment.dependencies or []),
            metadata=metadata,
        )

    def _build_complex_type_cast_fragment(
        self,
        identifier_node: IdentifierNode,
        expr_fragment: SQLFragment,
        canonical_type: str,
        type_metadata: Dict[str, Any],
        original_expression: str,
    ) -> SQLFragment:
        """Generate complex type casting SQL using polymorphic property metadata."""
        # SP-024-003: Extract the identifier from the node to resolve polymorphic variants
        # The parser doesn't set metadata on identifier nodes, so we need to resolve
        # the polymorphic variants at runtime using the identifier value
        identifier_value = identifier_node.identifier or identifier_node.text or ""

        # Get the last component of the identifier (e.g., "value" from "Observation.value")
        components = [part.strip().strip('`') for part in identifier_value.split('.') if part.strip()]

        # SP-024-003: If the identifier_value contains SQL functions (COALESCE, json_extract, etc.),
        # it's not a plain path. In this case, check the parent_path for polymorphic properties.
        base_property = ""
        sql_keywords = {'coalesce', 'json_extract', 'json_extract_string', 'case', 'when', 'then', 'else', 'end'}
        is_sql_expression = any(keyword in identifier_value.lower() for keyword in sql_keywords)

        if is_sql_expression:
            # The identifier is a SQL expression, not a path
            # Check if parent_path has a polymorphic property
            if self.context.parent_path:
                base_property = self.context.parent_path[-1]
                logger.debug(f"SP-024-003 DEBUG: Using parent_path, base_property='{base_property}'")
        else:
            base_property = components[-1] if components else ""
            logger.debug(f"SP-024-003 DEBUG: Using components, base_property='{base_property}'")

        # SP-024-003: Resolve polymorphic variants at runtime instead of relying on metadata
        variants: Optional[List[str]] = None
        if base_property and is_polymorphic_property(base_property):
            variants = resolve_polymorphic_property(base_property)

        if not variants:
            logger.warning(
                "Complex type cast for '%s' lacks polymorphic variants (expr: %s, base_property: %s)",
                canonical_type,
                original_expression,
                base_property,
            )
            return self._build_null_fragment(expr_fragment, canonical_type)

        variant_property = self._match_polymorphic_variant(variants, canonical_type)
        if not variant_property:
            logger.debug(
                "Target type '%s' not present in polymorphic variants %s (expr: %s)",
                canonical_type,
                variants,
                original_expression,
            )
            return self._build_null_fragment(expr_fragment, canonical_type)

        source_info = self._parse_json_source_and_components(expr_fragment.expression)

        # SP-024-003: If we can't parse the SQL expression (e.g., it's a COALESCE),
        # build the variant path directly from the identifier components
        if source_info is None:
            logger.debug(
                "Unable to parse JSON source for complex type cast '%s', building from identifier (expr: %s)",
                canonical_type,
                expr_fragment.expression,
            )

            # Build the variant JSON path from the identifier components
            # For example, if we have "Observation.value", we want to build "$.valueQuantity"
            # The identifier_value contains the path (e.g., "Observation.value")
            if base_property:
                # Build path from identifier components
                # For "Observation.value", extract just "value" and replace with "valueQuantity"
                variant_json_path = '$.' + variant_property

                base_variant_expression = self.dialect.extract_json_object(
                    column=self.context.current_table,
                    path=variant_json_path,
                )

                discriminator = get_type_discriminator(canonical_type)
                required_fields = []
                variant_expression = base_variant_expression

                if discriminator:
                    required_fields = discriminator.get("required_fields", []) or []
                    if required_fields:
                        checks: List[str] = []
                        for field in required_fields:
                            field_path = f"$.{field}"
                            checks.append(
                                self.dialect.check_json_exists(
                                    base_variant_expression,
                                    field_path,
                                )
                            )

                        condition = " AND ".join(checks)
                        variant_expression = (
                            "CASE WHEN "
                            f"{condition} THEN {base_variant_expression} "
                            "ELSE NULL END"
                        )

                metadata = {
                    "type_operation": "as",
                    "target_type": canonical_type,
                    "variant_property": variant_property,
                    "json_path": variant_json_path,
                    "mode": "complex",
                    "original_expression": original_expression,
                    "source_expression": expr_fragment.expression,
                    "discriminator_fields": required_fields,
                }

                return SQLFragment(
                    expression=variant_expression,
                    source_table=expr_fragment.source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=list(expr_fragment.dependencies or []),
                    metadata=metadata,
                )

            return self._build_null_fragment(expr_fragment, canonical_type)

        source_alias, components = source_info
        if not components:
            # SP-024-003: Use the base_property we extracted earlier
            if base_property:
                components = [base_property]
            else:
                logger.debug(
                    "No path components available for complex type cast '%s'",
                    canonical_type,
                )
                return self._build_null_fragment(expr_fragment, canonical_type)

        # Replace final component with polymorphic variant
        variant_components = components[:-1] + [variant_property]
        variant_json_path = self._build_json_path_from_components(variant_components)

        base_variant_expression = self.dialect.extract_json_object(
            column=source_alias,
            path=variant_json_path,
        )

        discriminator = get_type_discriminator(canonical_type)
        required_fields = []
        variant_expression = base_variant_expression

        if discriminator:
            required_fields = discriminator.get("required_fields", []) or []
            if required_fields:
                checks: List[str] = []
                for field in required_fields:
                    field_path = f"$.{field}"
                    checks.append(
                        self.dialect.check_json_exists(
                            base_variant_expression,
                            field_path,
                        )
                    )

                condition = " AND ".join(checks)
                variant_expression = (
                    "CASE WHEN "
                    f"{condition} THEN {base_variant_expression} "
                    "ELSE NULL END"
                )

        metadata = {
            "type_operation": "as",
            "target_type": canonical_type,
            "variant_property": variant_property,
            "json_path": variant_json_path,
            "mode": "complex",
            "original_expression": original_expression,
            "source_expression": expr_fragment.expression,
            "discriminator_fields": required_fields,
        }

        return SQLFragment(
            expression=variant_expression,
            source_table=expr_fragment.source_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=list(expr_fragment.dependencies or []),
            metadata=metadata,
        )

    def _build_null_fragment(self, expr_fragment: SQLFragment, canonical_type: str) -> SQLFragment:
        """Construct NULL fragment for unsupported type casts."""
        metadata = {
            "type_operation": "as",
            "target_type": canonical_type,
            "mode": "null",
        }
        return SQLFragment(
            expression="NULL",
            source_table=expr_fragment.source_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=list(expr_fragment.dependencies or []),
            metadata=metadata,
        )

    def _reapply_parent_path_for_type_cast(
        self,
        previous_parent_path: List[str],
        child_node: FHIRPathASTNode,
        fragment: SQLFragment,
    ) -> None:
        """Update translation context path after a type cast operation."""
        mode = fragment.metadata.get("mode") if isinstance(fragment.metadata, dict) else None

        # SP-024-003: Handle complex type cast mode
        if mode == "complex":
            # For complex type casts, use the variant_property from metadata
            variant_property = fragment.metadata.get("variant_property")
            json_path = fragment.metadata.get("json_path", "")

            if variant_property and json_path:
                # Extract the path components from the json_path
                # For example, "$.valueQuantity" -> ["valueQuantity"]
                path_components = json_path.lstrip("$.").split(".") if json_path else []

                # Update parent_path to include the variant
                # If previous_parent_path was ["value"], replace last component with variant
                if previous_parent_path:
                    self.context.parent_path = previous_parent_path[:-1] + path_components
                else:
                    self.context.parent_path = path_components

                return

        if mode == "null":
            self.context.parent_path = previous_parent_path.copy()
            return

        # Original logic for non-complex modes
        components: List[str] = []
        if isinstance(child_node, IdentifierNode):
            identifier_value = child_node.identifier or child_node.text or ""
            # SP-024-003: Skip SQL expressions
            sql_keywords = {'coalesce', 'json_extract', 'json_extract_string', 'case', 'when'}
            if not any(keyword in identifier_value.lower() for keyword in sql_keywords):
                components = [
                    part.strip().strip("`")
                    for part in identifier_value.split(".")
                    if part.strip()
                ]
                if components and components[0] == self.context.current_resource_type:
                    components = components[1:]

        if mode == "complex" and components:
            variant_property = fragment.metadata.get("variant_property")
            if variant_property:
                components = components[:-1] + [variant_property]

        if components:
            self.context.parent_path = previous_parent_path + components
        else:
            self.context.parent_path = previous_parent_path.copy()

    def _match_polymorphic_variant(
        self,
        variants: List[str],
        canonical_type: str,
    ) -> Optional[str]:
        """Match target type to polymorphic variant name (valueQuantity, onsetPeriod, etc.)."""
        normalized_type = canonical_type.lower()

        # Direct suffix match (handles Quantity, Period, Coding, etc.)
        for variant in variants:
            if variant.lower().endswith(normalized_type):
                return variant

        # Additional aliases for common profiles (Duration, Age behave like Quantity)
        alias_map = {
            "duration": "quantity",
            "age": "quantity",
        }
        alias = alias_map.get(normalized_type)
        if alias:
            for variant in variants:
                if variant.lower().endswith(alias):
                    return variant

        return None

    def _parse_json_source_and_components(
        self,
        expression: str,
    ) -> Optional[Tuple[str, List[str]]]:
        """Extract JSON source alias and path components from dialect expression."""
        expr = expression.strip()

        def normalise_path_literals(path_literal: str) -> List[str]:
            literal = path_literal.strip().strip("'\"")
            if not literal:
                return []
            literal = literal.lstrip("$")
            if literal.startswith("."):
                literal = literal[1:]
            if not literal:
                return []
            parts = [part.strip() for part in literal.split(".") if part.strip()]
            return parts

        if expr.startswith("json_extract_string(") or expr.startswith("json_extract("):
            inside = expr[expr.find("(") + 1: expr.rfind(")")]
            args = self._split_sql_arguments(inside)
            if len(args) < 2:
                return None
            source = args[0].strip()
            path_literal = args[1].strip()
            components = normalise_path_literals(path_literal)
            return source, components

        if expr.startswith("jsonb_extract_path_text(") or expr.startswith("jsonb_extract_path("):
            inside = expr[expr.find("(") + 1: expr.rfind(")")]
            args = self._split_sql_arguments(inside)
            if len(args) < 2:
                return None
            source = args[0].strip()
            components = [
                arg.strip().strip("'\"")
                for arg in args[1:]
                if arg.strip()
            ]
            return source, components

        return None

    def _split_sql_arguments(self, arg_string: str) -> List[str]:
        """Split SQL function arguments respecting nested parentheses and quotes."""
        args: List[str] = []
        current: List[str] = []
        depth = 0
        in_single_quote = False
        escape = False

        for char in arg_string:
            if char == "'" and not escape:
                in_single_quote = not in_single_quote
            elif char == "(" and not in_single_quote:
                depth += 1
            elif char == ")" and not in_single_quote and depth > 0:
                depth -= 1

            if char == "," and depth == 0 and not in_single_quote:
                args.append(''.join(current).strip())
                current = []
                continue

            if char == "\\" and not escape:
                escape = True
            else:
                escape = False

            current.append(char)

        if current:
            args.append(''.join(current).strip())

        return args

    # Type function call handlers - bridge function call syntax to type operations
    # The AST adapter creates FunctionCallNode for type functions; these handlers
    # convert them to the appropriate type checking SQL.

    def _translate_is_from_function_call(self, node: FunctionCallNode) -> SQLFragment:
        """Translate is() function call to type checking SQL.

        Temporary handler for type function called via function call syntax.
        This bridges the gap between AST adapter (creates FunctionCallNode) and
        existing type operation implementation (expects TypeOperationNode).

        Function call pattern: value.is(Type)
        - Extract path from node.text (e.g., "Observation.value" from "Observation.value.is(Quantity)")
        - node.arguments[0] = Type literal

        Args:
            node: FunctionCallNode with function_name='is'

        Returns:
            SQLFragment containing type checking SQL

        Example:
            Input: Observation.value.is(Quantity)
            Output: SQL type check for Quantity type

        Note:
            The AST adapter creates FunctionCallNode for type functions.
            This handler bridges to the type operation implementation.
        """
        # Validate argument count
        if not node.arguments or len(node.arguments) == 0:
            raise ValueError(f"is() requires exactly 1 argument, got {len(node.arguments) if node.arguments else 0}")

        target_type = self._extract_type_name_from_function_call(node)

        # Extract the path from node.text
        # The adapter loses path context, so we parse it from the text
        # Example: "Observation.value.is(Quantity)" → path="Observation.value"
        path_expr = self._extract_path_before_function(node.text, node.function_name)

        # SP-104-002: Track original literal text for temporal type checking
        original_literal = None

        # Get the value expression
        # SP-022-003: When is() is called as a method on a literal (e.g., 1.is(Integer)),
        # the function call node only contains "is()" as text, not "1.is(Integer)".
        # SP-104-002: Check pending_literal_value first for temporal literals
        if self.context.pending_literal_value is not None:
            # Use the pending literal value
            literal_value, value_expr = self.context.pending_literal_value
            # The pending_literal_value is a tuple (value, sql_expr)
            # For temporal literals, the sql_expr contains the DATE/TIMESTAMP/TIME literal
            # We need to preserve the original literal text for type checking
            # Check if there's temporal_info in the most recent fragment
            if self.fragments and len(self.fragments) > 0:
                last_frag = self.fragments[-1]
                if hasattr(last_frag, 'metadata') and last_frag.metadata:
                    original_literal = (
                        last_frag.metadata.get('source_text') or
                        last_frag.metadata.get('text') or
                        last_frag.metadata.get('temporal_info', {}).get('original') if last_frag.metadata.get('temporal_info') else None
                    )
            # Clear the pending value after using it
            self.context.pending_literal_value = None
        elif path_expr:
            # Parse and translate the path expression to update context
            # SP-023-004B: Use EnhancedASTNode directly - accept() handles dispatch
            from ..parser import FHIRPathParser
            path_parser = FHIRPathParser()
            path_ast = path_parser.parse(path_expr).get_ast()

            # Visit the path to update context
            path_fragment = self.visit(path_ast)
            value_expr = path_fragment.expression
            # Check if path_fragment has temporal literal metadata
            if hasattr(path_fragment, 'metadata') and path_fragment.metadata:
                original_literal = (
                    path_fragment.metadata.get('source_text') or
                    path_fragment.metadata.get('text') or
                    path_fragment.metadata.get('temporal_info', {}).get('original') if path_fragment.metadata.get('temporal_info') else None
                )
        elif self.fragments:
            # SP-022-003: No path in node.text, but we have previous fragments.
            # This happens with invocation patterns like "1.is(Integer)" where
            # the AST has the literal as a sibling node that was already visited.
            # Use the previous fragment's expression as the value to type-check.
            value_expr = self.fragments[-1].expression
            # Check if the last fragment has temporal literal metadata
            if hasattr(self.fragments[-1], 'metadata') and self.fragments[-1].metadata:
                original_literal = (
                    self.fragments[-1].metadata.get('source_text') or
                    self.fragments[-1].metadata.get('text') or
                    self.fragments[-1].metadata.get('temporal_info', {}).get('original') if self.fragments[-1].metadata.get('temporal_info') else None
                )
        else:
            # No explicit path and no previous fragments, use current context
            current_path = self.context.get_json_path()
            value_expr = self.dialect.extract_json_field(
                column=self.context.current_table,
                path=current_path
            )

        canonical_type = self._resolve_canonical_type(target_type)
        normalized = (canonical_type or "").lower()

        # SP-022-003: For literal values, use simplified type checking that
        # doesn't involve json_type() which fails on non-JSON values
        # SP-104-002: Check if value_expr is a literal or if we have original_literal
        if self._is_sql_literal_expression(value_expr) or original_literal:
            type_check_sql = self._generate_literal_type_check(value_expr, canonical_type, original_literal)
        # Route to appropriate type check based on type classification
        # Maintains thin dialect principle - business logic in translator
        elif self._is_primitive_type(canonical_type):
            type_check_sql = self.dialect.generate_type_check(
                value_expr,
                canonical_type
            )
        elif self._is_complex_type(canonical_type) or self._is_resource_type(canonical_type):
            type_check_sql = self._generate_complex_type_check(
                value_expr,
                canonical_type
            )
        else:
            # Fallback for unknown types
            from fhir4ds.fhirpath.types.fhir_type_constants import is_complex_fhir_type
            if is_complex_fhir_type(normalized):
                type_check_sql = self._generate_complex_type_check(
                    value_expr,
                    canonical_type
                )
            else:
                # Assume primitive
                type_check_sql = self.dialect.generate_type_check(
                    value_expr,
                    canonical_type
                )

        logger.debug(f"Generated is() type check SQL for type '{canonical_type}'")

        return SQLFragment(
            expression=type_check_sql,
            source_table=self.context.current_table,
            requires_unnest=False,  # Type check returns boolean, not collection
            is_aggregate=False  # Type check is scalar operation
        )

    def _extract_path_before_function(self, full_text: str, function_name: str) -> str:
        """Extract the path expression before a function call from full text.

        Examples:
            "Observation.value.is(Quantity)" → "Observation.value"
            "5.is(Integer)" → "5"
            "Patient.name.where(use='official')" → "Patient.name"

        Args:
            full_text: Full expression text (e.g., "Observation.value.is(Quantity)")
            function_name: Function name (e.g., "is")

        Returns:
            Path expression before the function, or empty string if no path
        """
        # Find the function call pattern: .function_name(
        pattern = f".{function_name}("
        idx = full_text.find(pattern)

        if idx == -1:
            # No explicit path before function (shouldn't happen in normal cases)
            return ""

        # Extract everything before .function_name(
        path = full_text[:idx]
        return path if path else ""

    def _extract_path_after_function(self, full_text: str, function_name: str) -> str:
        """Extract path components appearing after a function call."""
        pattern = f".{function_name}("
        start = full_text.find(pattern)
        if start == -1:
            return ""

        idx = start + len(pattern)
        depth = 1
        while idx < len(full_text) and depth > 0:
            char = full_text[idx]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            idx += 1

        if depth != 0 or idx >= len(full_text):
            return ""

        remainder = full_text[idx:]
        return remainder[1:] if remainder.startswith(".") else remainder

    def _build_json_path_from_components(self, components: List[str]) -> str:
        """Convert path component list to JSON path string."""
        path = "$"
        for component in components:
            if not component:
                continue
            if component.startswith("["):
                path += component
            else:
                path += f".{component}"
        return path

    def _translate_as_from_function_call(self, node: FunctionCallNode) -> SQLFragment:
        """Translate as() function call to type casting SQL.

        Temporary handler for type function called via function call syntax.

        Function call pattern: value.as(Type)
        - Extract path from node.text
        - node.arguments[0] = Type literal

        Args:
            node: FunctionCallNode with function_name='as'

        Returns:
            SQLFragment containing type casting SQL
        """
        # SP-107-001: Debug logging
        logger.debug(f"SP-107: _translate_as_from_function_call called: node.text={node.text}, node.function_name={node.function_name}")

        # Validate argument count
        if not node.arguments or len(node.arguments) == 0:
            raise ValueError(f"as() requires exactly 1 argument, got {len(node.arguments) if node.arguments else 0}")

        target_type = self._extract_type_name_from_function_call(node)
        canonical_type = self._resolve_canonical_type(target_type)

        # Extract the path from node.text (before .as())
        path_expr = self._extract_path_before_function(node.text, node.function_name)

        # ALSO extract any path AFTER .as() - e.g., ".unit" in "value.as(Quantity).unit"
        # SP-107-001: Check parent and grandparent nodes for additional path navigation
        # The AST structure for "Observation.value.as(Quantity).unit" is:
        #   - Root: InvocationExpression with text="Observation.value.as(Quantity).unit"
        #     - child[0]: InvocationExpression with text="Observation.value.as(Quantity)"
        #       - child[0]: "Observation.value"
        #       - child[1]: as() function call (current node)
        #     - child[1]: ".unit" (this is what we need to find)
        path_after = None
        if hasattr(node, 'parent') and node.parent:
            # Check if parent's parent has more children (indicating additional navigation)
            grandparent = node.parent.parent if hasattr(node.parent, 'parent') else None
            if grandparent and hasattr(grandparent, 'children') and len(grandparent.children) >= 2:
                # The second child of grandparent should be the path after .as()
                # child[0] is the .as() invocation, child[1]+ are subsequent navigations
                parent_invocation = node.parent  # This is "Observation.value.as(Quantity)"
                if grandparent.children[0] == parent_invocation and len(grandparent.children) > 1:
                    # There's a child after the .as() invocation
                    next_child = grandparent.children[1]
                    # Extract the path from the next child's text
                    if hasattr(next_child, 'text') and next_child.text:
                        # Remove leading dot if present
                        path_after = next_child.text.lstrip('.')
                        logger.debug(f"SP-107-001: Extracted path after .as() from parent: {path_after}")

        # POLYMORPHIC PROPERTY HANDLING FOR .as():
        # Check if path ends with a polymorphic property (e.g., "Observation.value")
        # If so, resolve directly to the type-specific field (e.g., "Observation.valueQuantity")
        # This avoids generating COALESCE which _build_type_cast_fragment cannot parse
        if path_expr:
            from fhir4ds.fhirpath.types.fhir_types import is_polymorphic_property, resolve_polymorphic_field_for_type

            # Extract the last component of the path
            path_components = path_expr.split('.')
            last_component = path_components[-1] if path_components else None

            if last_component and is_polymorphic_property(last_component):
                # Resolve the polymorphic property to specific field based on target type
                polymorphic_field = resolve_polymorphic_field_for_type(last_component, canonical_type)

                if polymorphic_field:
                    logger.debug(
                        f"Resolved polymorphic property in .as(): {last_component} + {canonical_type} → {polymorphic_field}"
                    )

                    # Build JSON path with resolved polymorphic field
                    # For "Observation.value" → "Observation.valueQuantity"
                    # Plus any path after .as(), e.g., ".unit" → "Observation.valueQuantity.unit"
                    json_path_components = []
                    if len(path_components) > 1:
                        # Skip first component (resource type) and build from second onward
                        json_path_components = path_components[1:-1] + [polymorphic_field]
                    else:
                        json_path_components = [polymorphic_field]

                    # Add path components AFTER .as() if any (e.g., "unit")
                    if path_after:
                        # Split by dots in case there are multiple levels like ".unit.value"
                        after_components = path_after.split('.')
                        json_path_components.extend(after_components)

                    json_path = '$.' + '.'.join(json_path_components)

                    # Generate SQL fragment directly with the complete path
                    sql_expr = self.dialect.extract_json_field(
                        column=self.context.current_table,
                        path=json_path
                    )

                    logger.debug(
                        f"Generated polymorphic .as() SQL with path_after: {sql_expr}"
                    )

                    # Build a proper expression fragment for type casting
                    # This ensures we get the full complex type metadata
                    expr_fragment = SQLFragment(
                        expression=sql_expr,
                        source_table=self.context.current_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=[],
                        metadata={}
                    )

                    # Use _build_type_cast_fragment to get proper metadata including mode='complex'
                    # Create an identifier node representing the polymorphic field
                    identifier_node = IdentifierNode(
                        node_type="identifier",
                        text=path_expr,
                        identifier=last_component
                    )

                    # Get type metadata
                    type_metadata = self.type_registry.get_type_metadata(canonical_type) or {}

                    # Build complex type cast fragment with proper metadata
                    fragment = self._build_complex_type_cast_fragment(
                        identifier_node=identifier_node,
                        expr_fragment=expr_fragment,
                        canonical_type=canonical_type,
                        type_metadata=type_metadata,
                        original_expression=node.text,
                    )

                    # SP-107-001: Set up polymorphic field mapping for subsequent navigation
                    # When .as() resolves a polymorphic property (e.g., "value" -> "valueQuantity"),
                    # subsequent field accesses need to use the resolved field.
                    # For example: "Observation.value.as(Quantity).unit" should access "valueQuantity.unit"
                    if not hasattr(self.context, 'polymorphic_field_mappings'):
                        self.context.polymorphic_field_mappings = {}
                    self.context.polymorphic_field_mappings[last_component] = polymorphic_field

                    # Update parent_path to include the resolved polymorphic field
                    # This ensures subsequent field navigation (e.g., .unit) uses the correct path
                    if path_after:
                        # Split by dots in case there are multiple levels like ".unit.value"
                        after_components = path_after.split('.')
                        # Push the resolved polymorphic field first, then the components after .as()
                        self.context.push_path(polymorphic_field)
                        for component in after_components:
                            self.context.push_path(component)
                    else:
                        # Just push the resolved polymorphic field
                        self.context.push_path(polymorphic_field)

                    logger.debug(
                        f"SP-107-001: Set up polymorphic mapping for .as(): {last_component} -> {polymorphic_field}, parent_path={self.context.parent_path}"
                    )

                    return fragment

        # Get the value expression fragment
        # SP-023-004B: Use EnhancedASTNode directly - accept() handles dispatch
        if path_expr:
            from ..parser import FHIRPathParser
            path_parser = FHIRPathParser()
            path_ast = path_parser.parse(path_expr).get_ast()

            snapshot = self._snapshot_context()
            try:
                path_fragment = self.visit(path_ast)
            finally:
                self._restore_context(snapshot)
            source_node = path_ast
            expr_fragment = path_fragment
            previous_parent_path = snapshot["parent_path"]
        elif self.fragments:
            # SP-022-003: No path in node.text, but we have previous fragments.
            # This happens with invocation patterns like "1.as(String)" where
            # the AST has the literal as a sibling node that was already visited.
            # Use the previous fragment's expression as the value to cast.
            previous_parent_path = self.context.parent_path.copy()
            expr_fragment = self.fragments[-1]
            source_node = IdentifierNode(
                node_type="identifier",
                text=expr_fragment.expression,
                identifier=expr_fragment.expression
            )
        else:
            # No explicit path and no previous fragments, use current context (treat as $this)
            previous_parent_path = self.context.parent_path.copy()
            current_path = self.context.get_json_path()
            value_expr = self.dialect.extract_json_field(
                column=self.context.current_table,
                path=current_path
            )
            expr_fragment = SQLFragment(
                expression=value_expr,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False
            )
            source_node = IdentifierNode(
                node_type="identifier",
                text=current_path,
                identifier=current_path
            )

        # canonical_type already resolved earlier (line 5524)
        fragment = self._build_type_cast_fragment(
            source_node=source_node,
            expr_fragment=expr_fragment,
            canonical_type=canonical_type,
            original_expression=node.text,
        )

        self._reapply_parent_path_for_type_cast(
            previous_parent_path=previous_parent_path,
            child_node=source_node,
            fragment=fragment,
        )

        logger.debug(
            "Generated as() SQL for function-call syntax, type '%s': %s",
            canonical_type,
            fragment.expression,
        )
        return fragment

    def _extract_type_name_from_function_call(self, node: FunctionCallNode) -> str:
        """Extract target type name from a type function call node."""
        if node.arguments:
            type_arg = node.arguments[0]
            if type_arg is not None:
                # Try identifier first (for IdentifierNode)
                if hasattr(type_arg, "identifier") and type_arg.identifier:
                    return str(type_arg.identifier)
                # Try value (for LiteralNode)
                if hasattr(type_arg, "value") and type_arg.value is not None:
                    return str(type_arg.value)
                # Try text (for EnhancedASTNode)
                if hasattr(type_arg, "text") and type_arg.text:
                    return str(type_arg.text)

        text = node.text or ""
        open_paren = text.find("(")
        close_paren = text.rfind(")")
        if 0 <= open_paren < close_paren:
            candidate = text[open_paren + 1:close_paren].strip().strip("`")
            if candidate:
                return candidate

        raise ValueError(
            f"Unable to determine type argument for {node.function_name}() call"
        )

    def _translate_oftype_from_function_call(self, node: FunctionCallNode) -> SQLFragment:
        """Translate ofType() function call to type filtering SQL.

        Temporary handler for type function called via function call syntax.

        Function call pattern: collection.ofType(Type)
        - Extract path from node.text
        - node.arguments[0] = Type literal

        Args:
            node: FunctionCallNode with function_name='ofType'

        Returns:
            SQLFragment containing type filtering SQL
        """
        # Validate argument count
        if len(node.arguments) != 1:
            raise ValueError(
                f"ofType() requires exactly 1 argument (type name), got {len(node.arguments)}"
            )

        # Extract type name from argument
        type_arg = node.arguments[0]

        # SP-023-004B: Support EnhancedASTNode which uses .text attribute
        if hasattr(type_arg, 'identifier') and type_arg.identifier:
            target_type = type_arg.identifier
        elif hasattr(type_arg, 'value') and type_arg.value is not None:
            target_type = type_arg.value
        elif hasattr(type_arg, 'text') and type_arg.text:
            target_type = type_arg.text
        else:
            raise ValueError(f"Unexpected type argument node: {type(type_arg)}")

        # Extract the path from node.text
        path_expr = self._extract_path_before_function(node.text, node.function_name)

        # Get the collection expression
        # SP-023-004B: Use EnhancedASTNode directly - accept() handles dispatch
        if path_expr:
            # Parse and translate the path expression
            from ..parser import FHIRPathParser
            path_parser = FHIRPathParser()
            path_ast = path_parser.parse(path_expr).get_ast()

            # Visit the path to update context
            path_fragment = self.visit(path_ast)
            collection_expr = path_fragment.expression
        elif self.fragments:
            # SP-022-003: No path in node.text, but we have previous fragments.
            # This happens with invocation patterns where the AST has the
            # collection as a sibling node that was already visited.
            collection_expr = self.fragments[-1].expression
        else:
            # No explicit path and no previous fragments, use current context
            current_path = self.context.get_json_path()
            collection_expr = self.dialect.extract_json_field(
                column=self.context.current_table,
                path=current_path
            )

        canonical_type = self._resolve_canonical_type(target_type)

        # POLYMORPHIC FIELD HANDLING:
        # Check if the path is a polymorphic property (e.g., "value")
        # If so, resolve to the type-specific field (e.g., "valueInteger")
        # IMPORTANT: Only apply this for direct property access (e.g., $.value), not nested
        # (e.g., $.component.value) to avoid breaking collection filtering
        if path_expr and is_polymorphic_property(path_expr):
            # For function call form, path_expr should be just the property name
            # If it contains dots or other path components, it's not a direct access
            is_direct_access = "." not in path_expr

            if is_direct_access:
                polymorphic_field = resolve_polymorphic_field_for_type(path_expr, canonical_type)
                if polymorphic_field:
                    logger.debug(f"Resolved polymorphic field: {path_expr} + {canonical_type} → {polymorphic_field}")

                    # Extract the polymorphic field directly
                    json_path = f"$.{polymorphic_field}"
                    poly_field_sql = self.dialect.extract_json_object(
                        column=self.context.current_table,
                        path=json_path
                    )

                    logger.debug(f"Generated polymorphic field extraction SQL for {polymorphic_field}")

                    return SQLFragment(
                        expression=poly_field_sql,
                        source_table=self.context.current_table,
                        requires_unnest=False,
                        is_aggregate=False
                    )

        # Use dialect method to generate collection type filtering SQL
        # Business logic: ofType filters collections by type
        # Dialect provides: database-specific array filtering and type checking syntax
        type_filter_sql = self.dialect.generate_collection_type_filter(
            expression=collection_expr,
            target_type=canonical_type
        )

        logger.debug(f"Generated ofType() type filter SQL for type '{canonical_type}'")

        return SQLFragment(
            expression=type_filter_sql,
            source_table=self.context.current_table,
            requires_unnest=False,  # Filtering returns collection, doesn't require additional unnest
            is_aggregate=False  # Type filtering is not an aggregation
        )

    def _translate_type(self, node: FunctionCallNode) -> SQLFragment:
        """Translate type() function to SQL that returns a Type structure.

        The type() function returns a Type object with namespace and name properties.
        For single values, it returns a Type describing the value's type.
        For collections, it returns Type objects for each element.

        FHIRPath Specification:
            - type() : Type - returns a Type object with .namespace and .name
            - The Type object has properties: namespace (e.g., 'System') and name (e.g., 'Integer')

        Args:
            node: FunctionCallNode representing type() function call (no arguments)

        Returns:
            SQLFragment with Type structure as JSON object

        Raises:
            ValueError: If type() has arguments (should have 0)

        Example:
            Input: 1.type()
            Output: {"namespace": "System", "name": "Integer"} as JSON

            Input: 1.type().namespace
            Output: 'System'

            Input: 1.type().name
            Output: 'Integer'
        """
        logger.debug("Translating type() function")

        # Validate no arguments
        if node.arguments:
            raise ValueError(
                f"type() function takes no arguments, got {len(node.arguments)}"
            )

        # Get the target expression (what we're getting the type of)
        (
            target_expr,
            dependencies,
            _,
            snapshot,
            target_ast,
            target_path,
        ) = self._resolve_function_target(node)

        source_table = snapshot["current_table"]

        try:
            # Determine the type based on the target AST
            if target_ast:
                # Check for literal nodes
                if hasattr(target_ast, 'literal_type'):
                    # For literals, we can directly return the type as a JSON structure
                    literal_type = target_ast.literal_type
                    if literal_type:
                        # Map FHIRPath types to their canonical forms
                        type_mapping = {
                            'Integer': 'Integer',
                            'Decimal': 'Decimal',
                            'String': 'String',
                            'Boolean': 'Boolean',
                            'Date': 'Date',
                            'DateTime': 'DateTime',
                            'Time': 'Time',
                            'Quantity': 'Quantity',
                        }
                        canonical_type = type_mapping.get(literal_type, literal_type)

                        # Return as JSON object with namespace and name
                        type_json = f"{{'namespace': 'System', 'name': '{canonical_type}'}}"
                        return SQLFragment(
                            expression=type_json,
                            source_table=source_table,
                            requires_unnest=False,
                            is_aggregate=False,
                            dependencies=dependencies or [],
                            metadata={"function": "type", "result_type": "Type"}
                        )

                # Check for identifier nodes (field references)
                if hasattr(target_ast, 'identifier') and target_ast.identifier:
                    # For field references, we need to determine the type from the schema
                    field_name = target_ast.identifier
                    current_type = self.resource_type

                    # Walk through the path to get the final type
                    if target_path:
                        element_type = self._get_element_type_for_path(target_path)
                    else:
                        element_type = self.type_registry.get_element_type(
                            current_type, field_name
                        )

                    if element_type:
                        # Validate element_type contains only safe characters (alphanumeric, underscore, hyphen)
                        # This prevents potential SQL injection if type definitions are compromised
                        if not re.match(r'^[A-Za-z][A-Za-z0-9_\-]*$', element_type):
                            logger.warning(f"Invalid element type format: {element_type}")
                            element_type = "Any"  # Safe fallback

                        # Return as JSON object with namespace and name
                        type_json = f"{{'namespace': 'FHIR', 'name': '{element_type}'}}"
                        return SQLFragment(
                            expression=type_json,
                            source_table=source_table,
                            requires_unnest=False,
                            is_aggregate=False,
                            dependencies=dependencies or [],
                            metadata={"function": "type", "result_type": "Type"}
                        )

            # For complex expressions or when we can't determine statically,
            # we need to construct a Type object from the runtime type
            # Use CASE statement to map typeof() results to FHIRPath types
            if target_expr:
                # Get the runtime type using dialect's typeof function
                runtime_type = self.dialect.get_json_typeof(target_expr)

                # Map SQL types to FHIRPath Type objects
                # This creates a JSON object with namespace and name
                type_mapping_sql = f"""
CASE
    WHEN {runtime_type} = 'INTEGER' THEN '{{"namespace": "System", "name": "Integer"}}'
    WHEN {runtime_type} = 'VARCHAR' THEN '{{"namespace": "System", "name": "String"}}'
    WHEN {runtime_type} = 'BOOLEAN' THEN '{{"namespace": "System", "name": "Boolean"}}'
    WHEN {runtime_type} = 'DOUBLE' THEN '{{"namespace": "System", "name": "Decimal"}}'
    WHEN {runtime_type} = 'DATE' THEN '{{"namespace": "System", "name": "Date"}}'
    WHEN {runtime_type} = 'TIMESTAMP' THEN '{{"namespace": "System", "name": "DateTime"}}'
    WHEN {runtime_type} = 'TIME' THEN '{{"namespace": "System", "name": "Time"}}'
    ELSE '{{"namespace": "System", "name": "Any"}}'
END
                """.strip()

                return SQLFragment(
                    expression=type_mapping_sql,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=dependencies or [],
                    metadata={"function": "type", "result_type": "Type"}
                )

            # Fallback: return System.Any as the most general type
            type_json = "{'namespace': 'System', 'name': 'Any'}"
            return SQLFragment(
                expression=type_json,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies or [],
                metadata={"function": "type", "result_type": "Type"}
            )

        finally:
            self._restore_context(snapshot)

    # Function translation methods

    def _translate_where(self, node: FunctionCallNode) -> SQLFragment:
        """Translate where() function to filtered collection.

        Compositional Design (Approved by Senior Architect):
        The where() function filters a collection and returns a filtered collection.
        This allows natural composition with other functions:
        - .where().exists() → EXISTS(filtered subquery)
        - .where().empty() → NOT EXISTS(filtered subquery)
        - .where().count() → COUNT from filtered subquery

        SP-022-012 FIX: When the collection has already been unnested in previous
        CTEs (e.g., Patient.name.given.where(...)), we use the CTE result column
        directly instead of re-extracting from the original resource. This ensures
        $this correctly references the already-unnested elements.

        Args:
            node: FunctionCallNode representing where() function call

        Returns:
            SQLFragment with filtered collection

        Raises:
            ValueError: If where() has no arguments or invalid condition

        Example:
            Input: name.where(use='official')
            Output: Fragment with filter metadata for CTE builder

            Input: Patient.name.given.where($this = 'Peter')
            Output: Fragment referencing already-unnested given_item
        """
        logger.debug(f"Translating where() function with {len(node.arguments)} arguments")

        # Validate where() has exactly one argument (the filter condition)
        if len(node.arguments) != 1:
            raise ValueError(
                f"where() function requires exactly 1 argument (filter condition), "
                f"got {len(node.arguments)}"
            )

        # Ensure context path reflects the function target when invoked via parser output
        self._prefill_path_from_function(node)

        # SP-022-012: Check if we have UNNEST fragments from previous path navigation
        # If so, we should filter those results rather than re-extracting from resource
        unnest_fragments = [f for f in self.fragments if f.requires_unnest]
        has_unnest_fragments = len(unnest_fragments) > 0

        if has_unnest_fragments:
            # SP-022-012: Collection is already unnested - use CTE-based filtering
            # The CTE builder will handle the actual filter application
            return self._translate_where_on_unnested(node, unnest_fragments)

        # No previous UNNEST - use the original inline subquery approach
        # Get the array path from current context
        array_path = self.context.get_json_path()

        logger.debug(f"Array path for where(): {array_path}")

        # Generate unique alias for array elements
        alias_counter = self.context.cte_counter
        array_alias = f"where_{alias_counter}_item"

        logger.debug(f"Generated array alias: {array_alias}")

        # Save current context state for restoration
        old_table = self.context.current_table
        old_path = self.context.parent_path.copy()

        # Update context to reference array elements for filter condition translation
        # This allows the filter condition to reference fields within array elements
        # SP-021-010: Point to .value column so string functions get the value, not the struct
        self.context.current_table = f"{array_alias}.value"
        self.context.parent_path.clear()  # Reset path since we're now at array element level

        # Generate array length expression for $total binding
        # This gives the total count of items in the original array
        array_length_expr = self.dialect.get_json_array_length(old_table, array_path)

        # Bind FHIRPath lambda variables for the where() context:
        # - $this: current array element value
        # - $index: zero-based index of current element (ROW_NUMBER() - 1)
        # - $total: total number of elements in the array
        with self._variable_scope({
            "$this": VariableBinding(
                expression=f"{array_alias}.value",
                source_table=array_alias
            ),
            "$index": VariableBinding(
                expression=f"{array_alias}.row_index",
                source_table=array_alias
            ),
            "$total": VariableBinding(
                expression=array_length_expr,
                source_table=old_table
            )
        }):
            # Translate the filter condition argument
            condition_fragment = self.visit(node.arguments[0])

        logger.debug(f"Filter condition SQL: {condition_fragment.expression}")

        # Restore context
        self.context.current_table = old_table
        self.context.parent_path = old_path

        # Use dialect-specific unnest method to generate array iteration
        unnest_sql = self.dialect.unnest_json_array(
            column=old_table,
            path=array_path,
            alias=f"{array_alias}_unnest"
        )

        logger.debug(f"UNNEST SQL: {unnest_sql}")

        # Construct subquery that returns filtered collection
        # Use a CTE to add row numbering for $index support
        # ROW_NUMBER() - 1 gives zero-based indexing as required by FHIRPath
        # SP-110 FIX: Include <<SOURCE_TABLE>> marker in FROM clause so UNNEST can reference its columns
        # The CTE builder will substitute <<SOURCE_TABLE>> with the actual source table name
        sql = f"""(
    SELECT {array_alias}.value
    FROM (
        SELECT
            {array_alias}_unnest.value,
            ROW_NUMBER() OVER () - 1 AS row_index
        FROM <<SOURCE_TABLE>>, LATERAL {unnest_sql}
    ) AS {array_alias}
    WHERE {condition_fragment.expression}
)"""

        logger.debug(f"Complete where() subquery fragment generated")

        # SP-110-XXX: Merge dependencies from condition fragment to handle nested functions
        # If condition contains nested function calls, those CTEs must be included in dependencies
        dependencies = [old_table]
        if hasattr(condition_fragment, "dependencies") and condition_fragment.dependencies:
            for dep in condition_fragment.dependencies:
                if dep and dep not in dependencies:
                    dependencies.append(dep)

        # Return SQL fragment with metadata
        # Note: Does NOT update context.current_table since this returns a collection expression
        return SQLFragment(
            expression=sql,
            source_table=old_table,  # Still depends on source table
            requires_unnest=False,  # Subquery is self-contained
            is_aggregate=False,
            dependencies=dependencies  # Track dependency on source table and nested CTEs
        )

    def _translate_where_on_unnested(
        self,
        node: FunctionCallNode,
        unnest_fragments: List[SQLFragment]
    ) -> SQLFragment:
        """Translate where() when operating on already-unnested collection.

        SP-022-012: When where() is called after path navigation that involved
        UNNEST operations (e.g., Patient.name.given.where(...)), we generate
        a fragment that filters the CTE results rather than re-extracting from
        the original resource.

        The $this variable binds to the result column from the last UNNEST CTE,
        allowing predicates like $this = 'Peter' or $this.length() > 3 to work
        correctly on the already-extracted values.

        IMPORTANT: UNNEST produces JSON-typed values (e.g., '"Peter"' not 'Peter').
        For primitive types like strings, we need to unwrap the JSON to get the
        actual string value for comparisons to work correctly.

        Args:
            node: FunctionCallNode for the where() call
            unnest_fragments: List of UNNEST fragments from previous path navigation

        Returns:
            SQLFragment with filter condition for CTE builder to apply
        """
        # Get the result column from the last UNNEST fragment
        last_unnest = unnest_fragments[-1]
        result_col = last_unnest.metadata.get("result_alias", "result")
        source_table = last_unnest.source_table or self.context.current_table

        logger.debug(
            f"SP-022-012: where() on unnested collection, "
            f"$this binds to '{result_col}'"
        )

        # SP-022-012: UNNEST produces JSON-typed values. For primitive arrays
        # (like string arrays), we need to extract the scalar value using
        # json_extract_string with path '$' to unwrap the JSON.
        # This allows comparisons like `$this = 'Peter'` to work correctly.
        #
        # For complex types (like HumanName), we keep the JSON value since
        # field access (like $this.family) will use json_extract_string.
        #
        # Determine if this is a primitive type by checking the source path
        is_primitive_array = self._is_primitive_collection(last_unnest)

        if is_primitive_array:
            # For primitive types, unwrap JSON to get scalar value
            # Use dialect method to extract string from JSON value
            this_expression = self.dialect.extract_json_string(result_col, "$")
            logger.debug(
                f"SP-022-012: Primitive array detected, $this = {this_expression}"
            )
        else:
            # For complex types, keep JSON for field access
            this_expression = result_col
            logger.debug(
                f"SP-022-012: Complex type array, $this = {result_col}"
            )

        # Save current context state for restoration
        old_table = self.context.current_table
        old_path = self.context.parent_path.copy()

        # Set context to point to the unnested result column
        # This is what $this should reference
        self.context.current_table = result_col
        self.context.parent_path.clear()

        # Bind FHIRPath lambda variables for the where() context:
        # - $this: references the CTE result column (e.g., given_item), possibly unwrapped
        # Note: $index and $total are not easily available in this CTE context
        # since ordering is managed by the CTE builder, not inline
        #
        # SP-022-012: Save the current fragment list before translating the condition.
        # When translating expressions like `$this.length() > 4`, intermediate fragments
        # may be added (e.g., for $this access, for length() call). We need to prevent
        # these from becoming separate CTEs, as they would lose the original column names.
        # The condition expression should be self-contained and reference the source columns.
        fragments_before = len(self.fragments)

        # SP-102-001: Clear pending_fragment_result to prevent stale values from outer scope
        # from leaking into the lambda scope. This fixes issues like substring($this.length()-3)
        # where substring was incorrectly using the pending_fragment_result from name.given
        # instead of using the $this variable from the lambda scope.
        old_pending = self.context.pending_fragment_result
        self.context.pending_fragment_result = None

        # SP-106-002: Store the old current_table and current_element_column to restore later
        # This ensures that nested expressions like $this.length() use the correct context
        old_current_table = self.context.current_table
        old_current_element_column = self.context.current_element_column

        # Set current_table to result_col so that $this references are resolved correctly
        self.context.current_table = result_col
        self.context.current_element_column = None

        with self._variable_scope({
            "$this": VariableBinding(
                expression=this_expression,
                source_table=result_col,  # Use result_col as source_table for correct scoping
                requires_unnest=False,
                is_aggregate=False
            )
        }):
            # Translate the filter condition argument
            condition_fragment = self.visit(node.arguments[0])

        # SP-102-001: Restore pending_fragment_result after lambda scope exits
        self.context.pending_fragment_result = old_pending

        # SP-106-002: Restore the old current_table and current_element_column
        self.context.current_table = old_current_table
        self.context.current_element_column = old_current_element_column

        # SP-022-012: Remove any intermediate fragments that were added during
        # condition translation. The condition expression is self-contained.
        if len(self.fragments) > fragments_before:
            self.fragments = self.fragments[:fragments_before]
            logger.debug(
                f"SP-022-012: Removed {len(self.fragments) - fragments_before + (len(self.fragments) - fragments_before)} "
                f"intermediate fragments from where() condition translation"
            )

        logger.debug(f"SP-022-012: Filter condition SQL: {condition_fragment.expression}")

        # Restore context
        self.context.current_table = old_table
        self.context.parent_path = old_path

        # SP-110-GROUP-BY-FIX: Track the column being filtered for GROUP BY when aggregated
        # When where() is followed by count() or other aggregate, the filtered column
        # must be included in GROUP BY clause. We track it in preserved_columns.
        preserved_cols = []
        # If result_col is an _item column from UNNEST, it needs to be in GROUP BY for aggregates
        if result_col.endswith('_item'):
            preserved_cols.append(result_col)

        # Return a fragment with filter metadata for the CTE builder
        # The CTE builder will add a WHERE clause to filter the CTE results
        return SQLFragment(
            expression=result_col,  # The column we're filtering
            source_table=source_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=[source_table],
            preserved_columns=preserved_cols,  # Track for GROUP BY when aggregated
            metadata={
                "function": "where",
                "where_filter": condition_fragment.expression,  # The filter condition
                "result_alias": result_col,  # Column being filtered
            }
        )

    def _is_primitive_collection(self, fragment: SQLFragment) -> bool:
        """Check if an UNNEST fragment represents a primitive type collection.

        SP-022-012: Used to determine whether $this should be JSON-unwrapped
        for string comparisons vs. kept as JSON for field access.

        Args:
            fragment: An UNNEST fragment from path navigation

        Returns:
            True if the collection elements are primitive types (string, integer, etc.)
            False if they are complex types (HumanName, Address, etc.)
        """
        source_path = fragment.metadata.get("source_path", "")
        if not source_path:
            return False

        # Parse the source path to determine the element type
        # Example: "$.name[*].given[*]" -> check if "given" in "HumanName" is primitive
        path_parts = source_path.replace("$", "").strip(".").split(".")
        path_parts = [p.replace("[*]", "").strip() for p in path_parts if p.strip()]

        if not path_parts:
            return False

        # Determine the element type
        element_type = self._get_element_type_for_path(path_parts)

        if element_type:
            # Check if the element type is a FHIR primitive type
            try:
                type_metadata = self.type_registry.get_type_metadata(element_type)
                if type_metadata and type_metadata.get("is_primitive"):
                    return True
            except Exception:
                pass

        # Default: assume primitive if no type info available and path ends with
        # known primitive field names
        primitive_field_names = {"given", "family", "value", "text", "display", "code", "system"}
        if path_parts and path_parts[-1].lower() in primitive_field_names:
            return True

        return False

    def _translate_select(self, node: FunctionCallNode) -> SQLFragment:
        """Translate select() function to SQL with LATERAL UNNEST and projection.

        The select() function transforms each array element by applying an expression
        to it. This requires unnesting the array, applying the transformation, and
        aggregating results back into an array.

        Population-First Design:
            Uses array operations and CTEs to process entire arrays at once, NOT
            row-by-row processing. This maintains population-scale performance.

        Args:
            node: FunctionCallNode representing select() function call

        Returns:
            SQLFragment with complete LATERAL UNNEST and projection SQL

        Raises:
            ValueError: If select() has no arguments or invalid expression

        Example:
            Input: Patient.name.select(family)

            Output SQL (DuckDB):
                SELECT resource.id,
                       json_group_array(json_extract_string(cte_1_item, '$.family')) as result
                FROM resource, LATERAL UNNEST(json_extract(resource, '$.name')) AS cte_1_item
                GROUP BY resource.id

            Input: Patient.telecom.select(value)

            Output SQL (PostgreSQL):
                SELECT resource.id,
                       json_agg(jsonb_extract_path_text(cte_1_item, 'value')) as result
                FROM resource, LATERAL jsonb_array_elements(jsonb_extract_path(resource, 'telecom')) AS cte_1_item
                GROUP BY resource.id
        """
        logger.debug(f"Translating select() function with {len(node.arguments)} arguments")

        # Validate select() has exactly one argument (the projection expression)
        if len(node.arguments) != 1:
            raise ValueError(
                f"select() function requires exactly 1 argument (projection expression), "
                f"got {len(node.arguments)}"
            )

        # SP-109-004: Use _resolve_function_target to get correct source table from context
        # This fixes CTE chaining issue where select() was using 'resource' instead of
        # the previous CTE when called after functions like take()
        (
            collection_expr,
            dependencies,
            _,
            snapshot,
            _,
            target_path,
        ) = self._resolve_function_target(node)

        # SP-109-004: Determine the correct source table for select()
        # The key insight is that we need to check if fragments have already been generated
        # for the target expression. If so, we should use the last fragment's source_table.
        # If not, we use the current context's table.

        # SP-110-010: Check if there are UNNEST fragments that need special handling
        # When there's a previous UNNEST, we need to enumerate from the _item column
        unnest_fragments = [f for f in self.fragments if f.requires_unnest]
        has_unnest_fragments = len(unnest_fragments) > 0

        # Check the current context AFTER _resolve_function_target has processed the target
        current_table_after_target = self.context.current_table

        # SP-110-010: If there are UNNEST fragments, the source_table should be the CTE marker
        # because we'll be enumerating from the _item column of the previous UNNEST CTE
        if has_unnest_fragments:
            # Use <<SOURCE_TABLE>> marker - the CTE builder will substitute it with the actual CTE name
            # and we'll enumerate from the _item column in the LATERAL clause
            source_table = "<<SOURCE_TABLE>>"
        elif current_table_after_target and current_table_after_target not in ("resource", "patient_resources"):
            # Context has been updated to a CTE
            source_table = current_table_after_target
        else:
            # Fall back to snapshot's current_table
            source_table = snapshot["current_table"]

        # Get the array path from current context
        array_path = self.context.get_json_path()

        # Generate unique CTE and array element alias names
        cte_name = self.context.next_cte_name()
        array_alias = f"{cte_name}_item"

        logger.debug(f"Generated CTE name: {cte_name}, array alias: {array_alias}")

        # Save current context state for restoration
        old_table = source_table
        old_path = self.context.parent_path.copy()

        # SP-109-004: Determine what to enumerate for select()
        # If there's a subset_filter (take/first/last/skip/where), the data is in the 'result' column
        # Otherwise, extract from JSON path or use the table directly

        # Also check if there's a subset_filter in recent fragments (indicating take/first/last/where)
        has_subset_filter = any(
            f.metadata.get("subset_filter") or f.metadata.get("function") in ["take", "first", "last", "skip", "where"]
            for f in self.fragments
        )

        # Get the array source expression for enumeration
        # SP-110-010: Use <<SOURCE_TABLE>> marker consistently for proper CTE substitution
        # This must be calculated BEFORE lateral_clause is generated

        # SP-110-FUNCTION: Check if there's a pending UNNEST fragment that will create a CTE
        # If so, select() should enumerate from that CTE's result column after unnesting
        pending_unnest_fragment = None
        if self.fragments and self.fragments[-1].requires_unnest:
            pending_unnest_fragment = self.fragments[-1]

        # SP-110-FUNCTION: Check if source is a CTE with a result column to enumerate
        # This happens when select() is called after an aggregation like take(), first(), etc.
        # We only enumerate from items if the source is a CTE that was already built
        has_cte_result = source_table.startswith("cte_") and any(
            f.source_table == source_table and f.metadata.get("function") in ["take", "first", "last", "skip", "where"]
            for f in self.fragments
        )
        enumerate_from_items = has_subset_filter or has_cte_result

        if has_subset_filter:
            # After a subset filter, data is in the 'result' column
            array_source_expr = "<<SOURCE_TABLE>>.result"
        elif pending_unnest_fragment:
            # There's a pending UNNEST fragment that will create a CTE with unnested rows
            # select() needs to enumerate from the array column before UNNEST
            # Use the array_column from the fragment metadata
            array_column = pending_unnest_fragment.metadata.get("array_column", "")
            if array_column:
                # Extract the array from the source table using the array_column expression
                # The array_column is like "json_extract(resource, '$.telecom[*]')"
                # We need to replace the table name with <<SOURCE_TABLE>>
                array_source_expr = array_column.replace(source_table, "<<SOURCE_TABLE>>", 1)
            else:
                # Fallback to JSON path extraction
                array_source_expr = self.dialect.extract_json_object("<<SOURCE_TABLE>>", array_path)
        elif source_table.startswith("cte_"):
            # Source is a CTE from aggregate - check if we have a result column to enumerate
            # The result column contains the aggregated JSON array from select()
            array_source_expr = "<<SOURCE_TABLE>>.result"
        elif array_path and array_path != "$":
            # Original resource table - extract from JSON path
            array_source_expr = self.dialect.extract_json_object("<<SOURCE_TABLE>>", array_path)
        else:
            # Root level table - use table directly
            array_source_expr = "<<SOURCE_TABLE>>"

        logger.debug(f"Array source expression for select(): {array_source_expr}, enumerate_from_items: {enumerate_from_items}")

        # SP-110 Phase 2: Update context to reference array elements for projection expression translation
        # Use 'value' as the element alias (from json_each/jsonb_array_elements)
        # This matches what the LATERAL clause actually produces
        element_alias = "enum_table.value"
        index_alias = "key"  # For DuckDB; PostgreSQL will use (ordinality - 1)

        self.context.current_table = element_alias
        self.context.parent_path.clear()

        # Translate the projection expression argument
        total_expr = self.dialect.get_json_array_length(
            column=old_table,
            path=array_path if array_path and array_path != "$" else None
        )

        # SP-110-FUNCTION: When enumerating from CTE result (subset filter),
        # we need to handle the case where the result is already an array
        if enumerate_from_items:
            # The source is a CTE with a result column that's already an array
            # We still need LATERAL json_each to enumerate it
            lateral_clause = self.dialect.generate_lateral_json_enumeration(array_source_expr, "enum_table", "value", "key")

            # Set index column and binding expression based on dialect
            if self.dialect.name == "POSTGRESQL":
                # PostgreSQL uses ordinality (1-based), need to convert to 0-based
                index_col = "(enum_table.ordinality - 1)"
                index_binding_expr = "(enum_table.ordinality - 1)"
            else:
                # DuckDB and others use key column directly (0-based)
                index_col = "enum_table.key"
                index_binding_expr = "enum_table.key"
        else:
            # Build LATERAL UNNEST clause for array enumeration
            # SP-110-010: Keep <<SOURCE_TABLE>> marker in lateral clause for CTE builder substitution
            lateral_clause = self.dialect.generate_lateral_json_enumeration(array_source_expr, "enum_table", "value", "key")

            # Set index column and binding expression based on dialect
            if self.dialect.name == "POSTGRESQL":
                # PostgreSQL uses ordinality (1-based), need to convert to 0-based
                index_col = "(enum_table.ordinality - 1)"
                index_binding_expr = "(enum_table.ordinality - 1)"
            else:
                # DuckDB and others use key column directly (0-based)
                index_col = "enum_table.key"
                index_binding_expr = "enum_table.key"

        with self._variable_scope({
            "$this": VariableBinding(
                expression=element_alias,
                source_table=element_alias
            ),
            "$index": VariableBinding(
                expression=index_binding_expr,
                source_table="enum_table"
            ),
            "$total": VariableBinding(
                expression=total_expr,
                source_table=old_table,
                dependencies=[old_table]
            )
        }):
            # SP-110-010: Save fragments count to prevent intermediate fragments from projection
            # from becoming separate CTEs. The projection expression should be inlined in the select().
            fragments_before_projection = len(self.fragments)
            projection_fragment = self.visit(node.arguments[0])
            # Remove any fragments added during projection translation - they should be inlined
            fragments_after_projection = len(self.fragments)
            if fragments_after_projection > fragments_before_projection:
                # Pop the intermediate fragments that were added during projection
                # These will be inlined in the select() SQL instead
                intermediate_fragments = self.fragments[fragments_before_projection:]
                self.fragments = self.fragments[:fragments_before_projection]
                logger.debug(f"SP-110-010: Removed {len(intermediate_fragments)} intermediate fragments from projection")

        logger.debug(f"Projection expression SQL: {projection_fragment.expression}")

        # SP-022-019: Do NOT restore old path - after select(), the context represents
        # the projected result (stored in 'result' column), not the original path.
        # Clear parent_path so count() won't try to extract from a JSON path.
        self.context.parent_path.clear()

        # SP-110 Phase 2: Generate database-specific JSON array aggregation
        # Need to order by index to preserve array order
        # SP-108-003: Wrap projection in to_json() to handle scalar values correctly
        # When projection extracts strings (via json_extract_string), they're VARCHAR type
        # to_json() converts them to JSON format (e.g., "Chalmers" -> "\"Chalmers\"")

        aggregate_expr = self.dialect.aggregate_to_json_array(f"to_json({projection_fragment.expression}) ORDER BY {index_col}")

        # SP-110-010: Use <<SOURCE_TABLE>> marker for proper CTE substitution
        # The CTE builder will replace <<SOURCE_TABLE>> with the actual source CTE name
        # This fixes the issue where select() was using 'resource' instead of the proper CTE
        sql = f"""SELECT <<SOURCE_TABLE>>.id, <<SOURCE_TABLE>>.resource,
       {aggregate_expr} as result
FROM <<SOURCE_TABLE>>, {lateral_clause}
GROUP BY <<SOURCE_TABLE>>.id, <<SOURCE_TABLE>>.resource"""

        logger.debug(f"Complete select() SQL fragment generated: {sql}")

        # Update context to reference the new CTE for subsequent operations
        self.context.current_table = cte_name

        # SP-109-004: Restore context from snapshot to maintain proper CTE chaining
        # This is needed for proper CTE chain management
        self._restore_context(snapshot)

        # SP-110-010: Determine correct dependencies for select()
        # If old_table is a CTE (starts with cte_), depend on it
        # Otherwise, depend on the original source from context
        if old_table.startswith("cte_"):
            select_dependencies = [old_table]
        else:
            select_dependencies = list(dict.fromkeys(dependencies))

        # Return SQL fragment with metadata
        # SP-022-019: Set requires_unnest=False since select() generates a complete
        # SELECT statement with GROUP BY. This prevents CTEBuilder from trying to add
        # ordering columns to the pre-built SELECT, which would cause subsequent CTEs
        # to expect ordering columns that don't exist in the output.
        return SQLFragment(
            expression=sql,
            source_table=cte_name,
            requires_unnest=False,  # Complete SELECT statement, no additional UNNEST needed
            is_aggregate=True,      # Flag that this involves aggregation
            dependencies=select_dependencies,  # SP-110-010: Proper dependency tracking
            metadata={"function": "select"}  # SP-110-003: Mark as select result for allTrue()/anyTrue() detection
        )

    def _translate_first(self, node: FunctionCallNode) -> SQLFragment:
        """Translate first() function to SQL.

        The first() function returns the first element of a collection. The
        implementation depends on whether the collection has been unnested:

        1. For non-unnested collections (JSON arrays): Uses json_extract with [0]
           indexing to get the first element directly from JSON.

        2. For unnested collections (multiple rows from UNNEST): Uses row filtering
           with ordering columns to select only the first row.

        Population-First Design:
            Both approaches maintain population-scale capability by operating
            within each patient's data context.

        Args:
            node: FunctionCallNode representing first() function call

        Returns:
            SQLFragment with appropriate SQL for first element extraction

        Raises:
            ValueError: If first() has arguments (it should not)

        Example:
            Input: Patient.name.first()
            Output SQL: json_extract(resource, '$.name[0]')

            Input: Patient.name.given.first() (after name and given are unnested)
            Output SQL: Adds filter for ordering columns = 1
        """
        logger.debug(f"Translating first() function with {len(node.arguments)} arguments")

        # Validate first() has no arguments
        if len(node.arguments) != 0:
            raise ValueError(
                f"first() function requires 0 arguments, got {len(node.arguments)}"
            )

        # Resolve the function target - this processes the collection expression
        # (e.g., Patient.name.given) and may generate UNNEST fragments
        (
            collection_expr,
            dependencies,
            literal_value,
            snapshot,
            target_ast,
            target_path,
        ) = self._resolve_function_target(node)

        source_table = snapshot["current_table"]

        # Check if UNNEST fragments were generated for the target
        # This indicates the collection is now represented as multiple rows
        unnest_fragments = [f for f in self.fragments if f.requires_unnest]
        has_unnest_fragments = len(unnest_fragments) > 0

        if has_unnest_fragments:
            # Collection is unnested - use row filtering
            # Get the result column from the last UNNEST fragment
            last_unnest = unnest_fragments[-1]
            result_col = last_unnest.metadata.get("result_alias", "result")

            # Count the unnest levels to know how many ordering columns there are
            unnest_count = len(unnest_fragments)

            # SP-022-004: Determine the element type for subsequent field access
            # The element type is derived from the source path (e.g., "name" -> "HumanName")
            element_type = None
            if target_path:
                element_type = self._get_element_type_for_path(target_path)

            # SP-022-008: Fallback to derive element type from UNNEST fragment source_path
            if element_type is None and last_unnest.metadata:
                source_path = last_unnest.metadata.get("source_path", "")
                if source_path:
                    path_parts = source_path.replace("$", "").strip(".").split(".")
                    path_parts = [p.replace("[*]", "").strip() for p in path_parts if p.strip()]
                    if path_parts:
                        element_type = self._get_element_type_for_path(path_parts)
                        logger.debug(
                            f"SP-022-008: Derived element_type '{element_type}' from "
                            f"UNNEST source_path '{source_path}' in first()"
                        )

            first_fragment = SQLFragment(
                expression=result_col,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={
                    "function": "first",
                    "subset_filter": "first",  # Tell CTE builder to filter to first row
                    "unnest_count": unnest_count,  # Number of ordering columns to filter
                    "element_type": element_type,  # SP-022-004: Type of element for field access
                }
            )

            # Add the fragment to the chain so subsequent operations
            # (like count()) operate on the filtered result
            self.fragments.append(first_fragment)

            # SP-101-002: Register column alias for CTE output
            # The CTE builder will output this as "result" column, but we need to track
            # that the actual data comes from result_col (e.g., "name_item")
            # This allows subsequent field access to properly reference the column
            self.context.register_column_alias("result", result_col)

            # SP-022-004: Update context for subsequent field access
            # After first() on UNNEST, subsequent field access should:
            # 1. Use the "result" column (the filtered element), not the original resource
            # 2. Clear the parent path since we're now at the element level
            # 3. Track the element type for proper type resolution
            self.context.current_element_column = "result"
            self.context.current_element_type = element_type
            self.context.parent_path.clear()
            # Note: We don't restore context here because we want these changes to persist

            return first_fragment

        # No UNNEST - use JSON path indexing as before
        # SP-101-002: Determine if we're working on the current context path
        # If the snapshot has a non-empty parent_path, it means the caller set up
        # a path before calling first(), and we should preserve our modifications
        working_on_context_path = bool(snapshot.get("parent_path"))

        try:
            if working_on_context_path:
                # SP-101-002: Build path without [*] markers for first() indexing
                # get_json_path() adds [*] for arrays, but first() needs [0] indexing
                # So we build the path manually without [*]
                current_path = "$." + ".".join(self.context.parent_path) if self.context.parent_path else "$"
            else:
                # Build path from target
                current_path = self._build_json_path_from_components(target_path or [])

            first_path = current_path + "[0]" if current_path else "$[0]"

            sql_expr = self.dialect.extract_json_field(
                column=source_table,
                path=first_path
            )

            # Update context path for subsequent operations
            self.context.parent_path.append("[0]")

            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "first"}
            )
        finally:
            # SP-101-002: Only restore context if we're not working on the current context path
            # When working on context path, we want to preserve the path modifications
            if not working_on_context_path:
                self._restore_context(snapshot)

    def _translate_exists(self, node: FunctionCallNode) -> SQLFragment:
        """Translate exists() function to SQL for existence checking.

        Compositional Design (Approved by Senior Architect):
        The exists() function checks whether a collection contains any elements.
        It has three forms:
        1. Simple path: collection.exists() - checks if collection is non-empty
        2. Filtered collection: collection.where(...).exists() - wraps filtered subquery in EXISTS
        3. With criteria: collection.exists(criteria) - checks if any element satisfies criteria

        The key compositional feature: When the source is a function call that returns
        a subquery (like .where()), .exists() automatically wraps it in EXISTS.

        Population-First Design:
            Uses CASE expressions with JSON array checks or COUNT subqueries to
            determine existence. This maintains population-scale capability by
            checking existence within each patient's data rather than using
            row-level patterns.

        Args:
            node: FunctionCallNode representing exists() function call

        Returns:
            SQLFragment with boolean existence check SQL

        Raises:
            ValueError: If exists() has more than 1 argument

        Example:
            Input: Patient.name.exists()
            Output SQL (DuckDB):
                CASE WHEN json_array_length(json_extract(resource, '$.name')) > 0
                     THEN TRUE ELSE FALSE END

            Input: Patient.name.where(use='official').exists()
            Output SQL (DuckDB):
                EXISTS((
                    SELECT item.value
                    FROM json_each(json_extract(resource, '$.name')) AS item
                    WHERE json_extract_string(item.value, '$.use') = 'official'
                ))

            Input: Patient.name.exists(use='official')
            Output SQL (DuckDB):
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM UNNEST(json_extract(resource, '$.name')) AS item
                    WHERE json_extract_string(item, '$.use') = 'official'
                ) THEN TRUE ELSE FALSE END
        """
        logger.debug(f"Translating exists() function with {len(node.arguments)} arguments")

        # Validate exists() has 0 or 1 arguments
        if len(node.arguments) > 1:
            raise ValueError(
                f"exists() function requires 0 or 1 arguments (optional criteria), "
                f"got {len(node.arguments)}"
            )

        # SP-100-003: Check if target is an empty collection literal directly
        if hasattr(node, 'target') and self._is_empty_collection_literal(node.target):
            # Empty collections don't exist: {}.exists() -> FALSE
            logger.debug("Empty collection literal target - exists() returns FALSE")
            return SQLFragment(
                expression="FALSE",
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=[],
                metadata={"function": "exists", "result_type": "boolean"}
            )

        # COMPOSITIONAL DESIGN: Check if target is a function call (e.g., .where())
        # If so, translate it first and detect if it returns a subquery
        if hasattr(node, 'target') and isinstance(node.target, FunctionCallNode):
            logger.debug(f"Target is function call: {node.target.function_name}")

            # Translate target function first
            target_fragment = self.visit(node.target)

            # SP-100-003: Check if target is an empty collection literal
            target_metadata = getattr(target_fragment, "metadata", {}) or {}
            if target_metadata.get("is_empty_collection"):
                # Empty collections don't exist: {}.exists() -> FALSE
                logger.debug("Empty collection literal - exists() returns FALSE")
                return SQLFragment(
                    expression="FALSE",
                    source_table=target_fragment.source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=target_fragment.dependencies,
                    metadata={"function": "exists", "result_type": "boolean"}
                )

            # Check if target returned a subquery (starts with opening parenthesis)
            if target_fragment.expression.strip().startswith('('):
                # Target returned a subquery (e.g., from .where()) - wrap in EXISTS
                sql_expr = f"EXISTS{target_fragment.expression}"

                logger.debug(f"Wrapped filtered subquery in EXISTS: {sql_expr[:100]}...")

                return SQLFragment(
                    expression=sql_expr,
                    source_table=target_fragment.source_table,
                    requires_unnest=False,  # Subquery is self-contained
                    is_aggregate=False,
                    dependencies=target_fragment.dependencies,
                    metadata={"function": "exists", "result_type": "boolean"}
                )

        # Original logic for simple paths and exists(criteria)
        # Ensure context path reflects the function target
        self._prefill_path_from_function(node)

        # Get the array path from current context
        array_path = self.context.get_json_path()

        logger.debug(f"Array path for exists(): {array_path}")

        # Case 1: exists() without criteria - simple non-empty check
        if len(node.arguments) == 0:
            # Use dialect-specific method to check if JSON array has elements
            # This generates CASE WHEN json_array_length(...) > 0 THEN TRUE ELSE FALSE END
            array_expr = self.dialect.extract_json_field(
                column=self.context.current_table,
                path=array_path
            )

            # Check if the extracted value is non-null and non-empty
            # For arrays: check json_array_length > 0
            # For scalars: check IS NOT NULL
            sql_expr = f"""CASE WHEN {array_expr} IS NOT NULL
     AND json_array_length({array_expr}) > 0
     THEN TRUE
     ELSE FALSE
END"""

            logger.debug(f"Generated exists() SQL (no criteria): {sql_expr}")

            # SP-108-003: When operating on an unnested collection, exists() should aggregate
            # back to patient level (one boolean per patient, not per row)
            source_table = self.context.current_table
            is_aggregate = source_table.startswith("cte_")
            metadata = {"function": "exists", "result_type": "boolean"}
            if is_aggregate:
                # Exclude ordering columns from GROUP BY - we aggregate to patient level
                metadata["exclude_order_from_group_by"] = True
                logger.debug(f"exists() on unnested collection {source_table} - setting is_aggregate=True")

            return SQLFragment(
                expression=sql_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=is_aggregate,
                dependencies=[],
                metadata=metadata
            )

        # Case 2: exists(criteria) - check if any element satisfies condition
        else:
            # Generate unique alias for array elements
            array_alias = f"exists_{self.context.cte_counter}_item"

            # Increment counter for next exists() call (SP-110-FIX: nested exists support)
            self.context.cte_counter += 1

            logger.debug(f"Generated array alias: {array_alias}")

            # Save current context state for restoration
            old_table = self.context.current_table
            old_path = self.context.parent_path.copy()

            # Update context to reference array elements for criteria translation
            self.context.current_table = array_alias
            self.context.parent_path.clear()

            # Translate the filter condition argument
            total_expr = self.dialect.get_json_array_length(
                column=old_table,
                path=array_path if array_path and array_path != "$" else None
            )

            # Bind FHIRPath lambda variables for the exists(criteria) context
            with self._variable_scope({
                "$this": VariableBinding(
                    expression=f"{array_alias}.value",
                    source_table=array_alias
                ),
                "$index": VariableBinding(
                    expression=f"{array_alias}.row_index",
                    source_table=array_alias
                ),
                "$total": VariableBinding(
                    expression=total_expr,
                    source_table=old_table,
                    dependencies=[old_table]
                )
            }):
                condition_fragment = self.visit(node.arguments[0])

            logger.debug(f"Criteria condition SQL: {condition_fragment.expression}")

            # Restore context
            self.context.current_table = old_table
            self.context.parent_path = old_path

            # Generate database-specific UNNEST SQL using dialect method
            # SP-110 FIX: Use <<SOURCE_TABLE>> marker instead of old_table so the CTE builder
            # can substitute it with the actual source table name. This allows the EXISTS subquery
            # to work correctly when embedded in a CTE that references the previous CTE.
            unnest_sql = self.dialect.unnest_json_array(
                column="<<SOURCE_TABLE>>",
                path=array_path,
                alias=f"{array_alias}_unnest"
            )

            logger.debug(f"UNNEST SQL: {unnest_sql}")

            # Construct SQL fragment with EXISTS subquery
            # Use subquery with ROW_NUMBER() for $index support
            # SP-110 FIX: Include <<SOURCE_TABLE>> marker in FROM clause so UNNEST can reference its columns
            # The CTE builder will substitute <<SOURCE_TABLE>> with the actual source table name
            sql_expr = f"""CASE WHEN EXISTS (
    SELECT 1
    FROM (
        SELECT
            {array_alias}_unnest.value,
            ROW_NUMBER() OVER () - 1 AS row_index
        FROM <<SOURCE_TABLE>>, LATERAL {unnest_sql}
    ) AS {array_alias}
    WHERE {condition_fragment.expression}
) THEN TRUE ELSE FALSE END"""

            logger.debug(f"Generated exists() SQL (with criteria): {sql_expr}")

            # SP-110 FIX: Use the actual underlying table for dependencies, not the temporary array_alias
            # The array_alias (e.g., exists_0_item) is only used as a table alias in the EXISTS subquery,
            # not as a CTE. We should only depend on the old_table (the actual data source).
            dependencies = [old_table]

            # Filter dependencies from condition_fragment
            # SP-110 Round 8 FIX: Handle nested exists() dependencies correctly
            # When we have nested exists() like: category.exists(coding.exists(...))
            # - The inner exists() will have dependencies like ['exists_0_item'] (the outer lambda's table)
            # - We SHOULD include exists_0_item in our dependencies because the inner EXISTS subquery
            #   needs to reference the outer exists()'s table in its FROM clause
            # - Only skip the current array_alias (our own temp alias) since it's created within this EXISTS subquery
            if hasattr(condition_fragment, "dependencies") and condition_fragment.dependencies:
                for dep in condition_fragment.dependencies:
                    # Skip if this is the current array_alias (our own temp alias within this EXISTS subquery)
                    # But DO include parent exists_N_item patterns - they are legitimate dependencies
                    # that need to be available in the FROM clause for nested EXISTS subqueries
                    is_current_array_alias = (dep == array_alias)
                    if dep and dep != old_table and not is_current_array_alias and dep not in dependencies:
                        dependencies.append(dep)

            return SQLFragment(
                expression=sql_expr,
                source_table=self.context.current_table,
                requires_unnest=False,  # EXISTS subquery is self-contained
                is_aggregate=False,
                dependencies=dependencies,
                metadata={
                    "function": "exists",
                    "result_type": "boolean",
                    "skip_aggregation": True  # SP-110 FIX: EXISTS subquery already handles aggregation
                }
            )

    def _translate_empty(self, node: FunctionCallNode) -> SQLFragment:
        """Translate empty() function to SQL for empty collection checking.

        Compositional Design (Approved by Senior Architect):
        The empty() function checks whether a collection is empty (contains no elements).
        It has two forms:
        1. Simple path: collection.empty() - checks if collection is empty
        2. Filtered collection: collection.where(...).empty() - wraps filtered subquery in NOT EXISTS

        The key compositional feature: When the source is a function call that returns
        a subquery (like .where()), .empty() automatically wraps it in NOT EXISTS.

        Population-First Design:
            Uses dialect-specific JSON array length checks to determine emptiness.
            This maintains population-scale capability by checking collection size
            within each patient's data rather than using row-level patterns.

        Args:
            node: FunctionCallNode representing empty() function call

        Returns:
            SQLFragment with boolean empty check SQL

        Raises:
            ValueError: If empty() has any arguments (empty() takes no arguments)

        Example:
            Input: Patient.name.empty()
            Output SQL (DuckDB):
                (json_array_length(json_extract(resource, '$.name')) = 0)

            Input: Patient.name.where(use='official').empty()
            Output SQL (DuckDB):
                NOT EXISTS((
                    SELECT item.value
                    FROM json_each(json_extract(resource, '$.name')) AS item
                    WHERE json_extract_string(item.value, '$.use') = 'official'
                ))

            Input: Patient.telecom.empty()
            Output SQL (PostgreSQL):
                (jsonb_array_length(jsonb_extract_path(resource, 'telecom')) = 0)
        """
        logger.debug(f"Translating empty() function with {len(node.arguments)} arguments")

        # Validate empty() has no arguments
        if len(node.arguments) > 0:
            raise ValueError(
                f"empty() function requires 0 arguments, got {len(node.arguments)}"
            )

        # SP-100-003: Check if target is an empty collection literal directly
        if hasattr(node, 'target') and self._is_empty_collection_literal(node.target):
            # Empty collections are empty: {}.empty() -> TRUE
            logger.debug("Empty collection literal target - empty() returns TRUE")
            return SQLFragment(
                expression="TRUE",
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=[],
                metadata={"function": "empty", "result_type": "boolean"}
            )

        # COMPOSITIONAL DESIGN: Check if target is a function call (e.g., .where())
        # If so, translate it first and detect if it returns a subquery
        if hasattr(node, 'target') and isinstance(node.target, FunctionCallNode):
            logger.debug(f"Target is function call: {node.target.function_name}")

            # Translate target function first
            target_fragment = self.visit(node.target)

            # SP-100-003: Check if target is an empty collection literal
            target_metadata = getattr(target_fragment, "metadata", {}) or {}
            if target_metadata.get("is_empty_collection"):
                # Empty collections are empty: {}.empty() -> TRUE
                logger.debug("Empty collection literal - empty() returns TRUE")
                return SQLFragment(
                    expression="TRUE",
                    source_table=target_fragment.source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=target_fragment.dependencies,
                    metadata={"function": "empty", "result_type": "boolean"}
                )

            # Check if target returned a subquery (starts with opening parenthesis)
            # SP-021-010: Stricter check to avoid treating (CASE ... END) as subquery
            expression_stripped = target_fragment.expression.strip()
            if expression_stripped.startswith('(') and (
                'SELECT' in expression_stripped[:20].upper() or
                'WITH' in expression_stripped[:20].upper()
            ):
                # Target returned a subquery (e.g., from .where()) - wrap in NOT EXISTS
                sql_expr = f"NOT EXISTS{target_fragment.expression}"

                logger.debug(f"Wrapped filtered subquery in NOT EXISTS: {sql_expr[:100]}...")

                return SQLFragment(
                    expression=sql_expr,
                    source_table=target_fragment.source_table,
                    requires_unnest=False,  # Subquery is self-contained
                    is_aggregate=False,
                    dependencies=target_fragment.dependencies,
                    metadata={"function": "empty", "result_type": "boolean"}
                )

        # Original logic for simple paths

        collection_expr, dependencies, literal_value, snapshot, _, target_path = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                # FHIRPath empty() semantics:
                # - NULL → TRUE (empty)
                # - Empty collection {} → TRUE (empty)
                # - Empty collection [] → TRUE (empty)
                # - Single value (not a collection) → FALSE ({value} has 1 element)
                # - Collection with elements → FALSE
                if isinstance(literal_value, (list, tuple, set)):
                    is_empty = len(literal_value) == 0
                elif literal_value == "{}[]" or literal_value == "[]":
                    # SP-100-003: Empty collection literal marker
                    is_empty = True
                else:
                    # Single value is treated as a singleton collection {value}
                    # which is NOT empty
                    is_empty = False

                sql_literal = "TRUE" if is_empty else "FALSE"
                return SQLFragment(
                    expression=sql_literal,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=list(dict.fromkeys(dependencies)),
                    metadata={"function": "empty", "result_type": "boolean"}
                )

            if not collection_expr:
                raise ValueError("empty() requires a collection expression to evaluate")

            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            length_expr = self.dialect.get_json_array_length(normalized_expr)
            empty_check_sql = (
                "("
                "CASE "
                f"WHEN {normalized_expr} IS NULL THEN TRUE "
                f"ELSE ({length_expr} = 0) "
                "END"
                ")"
            )

            logger.debug(f"Generated empty() SQL: {empty_check_sql}")

            # SP-108-003: When operating on an unnested collection (source_table is a CTE),
            # empty() should aggregate back to patient level (one boolean per patient, not per row)
            # This handles cases like Patient.name.given.empty() where given has been unnested
            is_aggregate = source_table.startswith("cte_")
            metadata = {"function": "empty", "result_type": "boolean"}
            if is_aggregate:
                # Exclude ordering columns from GROUP BY - we aggregate to patient level
                metadata["exclude_order_from_group_by"] = True
                logger.debug(f"empty() on unnested collection {source_table} - setting is_aggregate=True")

            return SQLFragment(
                expression=empty_check_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=is_aggregate,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata=metadata
            )
        finally:
            self._restore_context(snapshot)

    def _handle_not_on_collection(
        self, prev_fragment: SQLFragment, source_table: str, dependencies: List[str]
    ) -> Optional[SQLFragment]:
        """Handle not() function when applied to a collection.

        According to FHIRPath spec, not() on collections:
        - Empty collection → Empty collection (NULL)
        - Single boolean → Negated boolean
        - Multiple values → Implicitly apply exists() first, then negate (SP-110-011)

        SP-110-011: Multi-item collections use implicit exists() semantics.
        For example, (1|2).not() is equivalent to (1|2).exists().not().

        Args:
            prev_fragment: The previous SQLFragment to check
            source_table: The source table for the SQL fragment
            dependencies: List of dependencies for the SQL fragment

        Returns:
            SQLFragment with appropriate expression, None if not a collection case
        """
        prev_metadata = prev_fragment.metadata or {}
        is_collection = prev_metadata.get('is_collection') is True
        operator = prev_metadata.get('operator')

        # SP-110-010: Check for empty collection first
        is_empty_collection = prev_metadata.get('is_empty_collection') is True
        if is_empty_collection:
            logger.debug("SP-110-010: not() on empty collection returning NULL")
            return SQLFragment(
                expression="NULL",
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "not", "result_type": "boolean"}
            )

        if is_collection:
            # SP-110-011: Multi-item collections use implicit exists() semantics
            if operator == 'union':
                logger.debug("SP-110-011: not() on multi-item collection using implicit exists()")
                # Apply implicit exists() check: if collection has items, it's true
                # Then negate: true -> false, false -> true
                # For (1|2).not(): collection is non-empty -> exists() = true -> not() = false
                value_expr = prev_fragment.expression
                exists_sql = f"CASE WHEN {value_expr} IS NOT NULL THEN TRUE ELSE FALSE END"
                not_sql = self.dialect.generate_boolean_not(exists_sql)

                return SQLFragment(
                    expression=not_sql,
                    source_table=source_table,
                    requires_unnest=prev_fragment.requires_unnest,
                    is_aggregate=False,
                    dependencies=list(dict.fromkeys(dependencies)),
                    metadata={"function": "not", "result_type": "boolean"}
                )

            # Empty or single-item collection returns NULL
            logger.debug("SP-110-008: not() on collection returning NULL")
            return SQLFragment(
                expression="NULL",
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "not", "result_type": "boolean"}
            )
        return None

    def _translate_not(self, node: FunctionCallNode) -> SQLFragment:
        """Translate not() function to SQL for boolean negation.

        The not() function returns the opposite boolean value of the input.
        It operates on boolean values only, returning the logical negation.

        FHIRPath Specification:
            not() : Boolean
            - Input true → Returns false
            - Input false → Returns true
            - Input {} (empty) → Returns {} (empty/NULL)
            - Input collection with multiple values → Implicitly apply exists() first, then negate (SP-110-011)

        SP-110-011: Multi-item collections (e.g., from union operations) use implicit exists()
        semantics. For example, (1|2).not() is equivalent to (1|2).exists().not(), which evaluates
        to false (since the collection has items, exists() returns true, then not() negates to false).

        Population-First Design:
            Uses standard SQL NOT operator to negate boolean expressions.
            This maintains population-scale capability by applying NOT to
            entire boolean column expressions rather than row-by-row evaluation.

        Args:
            node: FunctionCallNode representing not() function call

        Returns:
            SQLFragment with boolean NOT SQL

        Raises:
            ValueError: If not() has any arguments (not() takes no arguments)

        Example:
            Input: true.not()

            Output SQL:
                NOT (TRUE)

            Input: Patient.active.not()

            Output SQL (DuckDB):
                NOT (CAST(json_extract(resource, '$.active') AS BOOLEAN))

            Input: Patient.name.empty().not()

            Output SQL:
                NOT (json_array_length(json_extract(resource, '$.name')) = 0)

            Input: (1|2).not()  (SP-110-011)

            Output SQL:
                NOT (CASE WHEN <union_expr> IS NOT NULL THEN TRUE ELSE FALSE END)
        """
        logger.debug(f"Translating not() function with {len(node.arguments)} arguments")

        # Validate not() has no arguments
        if len(node.arguments) > 0:
            raise ValueError(
                f"not() function requires 0 arguments, got {len(node.arguments)}"
            )

        # SP-022-003: Check if we have previous fragments to operate on.
        # This handles cases like "1.is(Integer).not()" where the AST structure
        # has the preceding expression as a sibling node that was already visited.
        path_expr = self._extract_path_before_function(node.text, node.function_name)

        if not path_expr and self.fragments:
            # No path in node.text, but we have previous fragments.
            # Use the previous fragment's expression as the value to negate.
            prev_fragment = self.fragments[-1]
            value_expr = prev_fragment.expression
            source_table = prev_fragment.source_table or self.context.current_table
            dependencies = list(prev_fragment.dependencies) if prev_fragment.dependencies else []

            # SP-110-008: Handle collections for not() function
            collection_result = self._handle_not_on_collection(prev_fragment, source_table, dependencies)
            if collection_result:
                return collection_result

            not_sql = self.dialect.generate_boolean_not(value_expr)

            logger.debug(f"Generated not() SQL (from previous fragment): {not_sql}")

            # SP-108-003: Propagate aggregate_function metadata from the previous fragment
            # This ensures that expressions like empty().not() or exists().not() still trigger
            # aggregation when operating on unnested collections
            prev_metadata = self.fragments[-1].metadata or {}
            aggregate_function = prev_metadata.get("function", "")
            metadata = {"function": "not", "result_type": "boolean"}
            if aggregate_function in {"empty", "exists", "count"}:
                metadata["aggregate_function"] = aggregate_function
                logger.debug(f"not() propagating aggregate_function={aggregate_function}")

            return SQLFragment(
                expression=not_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata=metadata
            )

        # Standard path - use _resolve_function_target
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            # SP-110-008: Handle collections for not() function
            if value_expr and self.fragments:
                prev_fragment = self.fragments[-1]
                collection_result = self._handle_not_on_collection(prev_fragment, source_table, dependencies)
                if collection_result:
                    return collection_result

            if literal_value is not None:
                # SP-110-010: Handle integer literals (0 and 1)
                if isinstance(literal_value, (int, float)):
                    if literal_value == 0:
                        # 0.not() -> TRUE (0 is falsy, not(0) is truthy)
                        sql_literal = "TRUE"
                    elif literal_value == 1:
                        # 1.not() -> FALSE (1 is truthy, not(1) is falsy)
                        sql_literal = "FALSE"
                    else:
                        # Other integers - evaluate as boolean
                        bool_value = self._evaluate_literal_to_boolean(literal_value)
                        if bool_value is None:
                            sql_literal = "NULL"
                        else:
                            sql_literal = "TRUE" if not bool_value else "FALSE"
                else:
                    bool_value = self._evaluate_literal_to_boolean(literal_value)
                    if bool_value is None:
                        sql_literal = "NULL"
                    else:
                        sql_literal = "TRUE" if not bool_value else "FALSE"
                return SQLFragment(
                    expression=sql_literal,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    dependencies=list(dict.fromkeys(dependencies)),
                    metadata={"function": "not", "result_type": "boolean"}
                )

            if not value_expr:
                raise ValueError("not() requires a target expression to negate")

            not_sql = self.dialect.generate_boolean_not(value_expr)

            logger.debug(f"Generated not() SQL: {not_sql}")

            return SQLFragment(
                expression=not_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "not", "result_type": "boolean"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_all(self, node: FunctionCallNode) -> SQLFragment:
        """Translate all() function to SQL for universal quantification.

        The all() function returns true if the criteria expression evaluates to
        true for ALL elements in the collection. Returns true for empty collections
        (vacuous truth).

        FHIRPath Specification:
            all(criteria : expression) : Boolean
            - Returns true if every element meets criteria
            - Returns false if any element fails criteria
            - Returns true if collection is empty

        Population-First Design:
            Uses SQL aggregation with BOOL_AND (or equivalent) to check if all
            elements satisfy the condition. This maintains population-scale capability
            by processing entire collections without row-by-row iteration.

        SP-108-003: Handle two cases:
        1. Direct path: Patient.name.all(...) - Creates subquery with UNNEST
        2. After path navigation: Patient.name.all(...) where path already created UNNEST

        Args:
            node: FunctionCallNode representing all() function call

        Returns:
            SQLFragment with boolean universal quantification SQL

        Raises:
            ValueError: If all() doesn't have exactly 1 argument (criteria expression)
        """
        logger.debug(f"Translating all() function with {len(node.arguments)} arguments")

        # Validate all() has exactly one argument (the criteria expression)
        if len(node.arguments) != 1:
            raise ValueError(
                f"all() function requires exactly 1 argument (criteria expression), "
                f"got {len(node.arguments)}"
            )

        # SP-108-003: Check if there's already a UNNEST fragment from path navigation
        unnest_fragments = [f for f in self.fragments if f.requires_unnest]
        has_unnest = len(unnest_fragments) > 0

        if has_unnest:
            # Case 2: Work on already-unnested collection
            logger.debug("all() operating on unnested collection")

            # Get the last UNNEST fragment
            last_unnest = unnest_fragments[-1]

            # Get the result column from the last UNNEST fragment
            result_col = last_unnest.metadata.get("result_alias", "result")
            source_table = last_unnest.source_table or self.context.current_table

            # Determine if this is a primitive type array
            is_primitive_array = self._is_primitive_collection(last_unnest)

            if is_primitive_array:
                # For primitive types, unwrap JSON to get scalar value
                this_expression = self.dialect.extract_json_string(result_col, "$")
            else:
                # For complex types, keep JSON for field access
                this_expression = result_col

            # Save context and fragments
            old_table = source_table
            old_path = self.context.parent_path.copy()
            saved_fragments = self.fragments.copy()
            self.fragments.clear()

            # Translate criteria expression with context pointing to the unnested element
            self.context.current_table = this_expression
            self.context.parent_path.clear()

            with self._variable_scope({
                "$this": VariableBinding(
                    expression=this_expression,
                    source_table=this_expression
                )
            }):
                criteria_fragment = self.visit(node.arguments[0])

            # Restore fragments
            self.fragments.clear()
            self.fragments.extend(saved_fragments)

            # Restore context - keep current_table as is for CTE builder
            # SP-110-009: Use old_table as source_table but don't add dependencies
            # The CTE builder will use previous_cte which is the UNNEST CTE
            self.context.current_table = old_table
            self.context.parent_path = old_path

            all_check_sql = f"COALESCE(bool_and({criteria_fragment.expression}), true)"

            return SQLFragment(
                expression=all_check_sql,
                source_table=self.context.current_table,  # Use current context table
                requires_unnest=False,
                is_aggregate=True,
                dependencies=[],  # SP-110-009: CTE builder will add previous_cte as dependency
                metadata={
                    "function": "all",
                    "result_type": "boolean",
                    "exclude_order_from_group_by": True  # SP-108-003: Don't group by order columns
                }
            )

        # Case 1: Direct path - create subquery with UNNEST
        # Ensure context path reflects the function target
        self._prefill_path_from_function(node)

        # Get the collection path from current context
        collection_path = self.context.get_json_path()

        logger.debug(f"Collection path for all(): {collection_path}")

        # Generate unique alias for array elements
        element_alias = f"elem_{self.context.cte_counter}"

        # Save current context state for restoration
        old_table = self.context.current_table
        old_path = self.context.parent_path.copy()

        # Update context to reference array elements for criteria expression translation
        # This allows the criteria to reference fields within array elements
        self.context.current_table = element_alias
        self.context.parent_path.clear()  # Reset path since we're now at array element level

        # SP-108-003: Save fragments list to prevent criteria expression from creating CTEs
        # The criteria should be an inline expression within the subquery, not separate CTEs
        saved_fragments = self.fragments.copy()
        self.fragments.clear()

        # Translate the criteria expression argument
        # This recursively visits the criteria AST and generates SQL
        total_expr = self.dialect.get_json_array_length(
            column=old_table,
            path=collection_path if collection_path and collection_path != "$" else None
        )

        with self._variable_scope({
            "$this": VariableBinding(
                expression=element_alias,
                source_table=element_alias
            ),
            "$total": VariableBinding(
                expression=total_expr,
                source_table=old_table,
                dependencies=[old_table]
            )
        }):
            criteria_fragment = self.visit(node.arguments[0])

        # SP-108-003: Restore fragments list - criteria translation should not create CTEs
        self.fragments.clear()
        self.fragments.extend(saved_fragments)

        logger.debug(f"Criteria expression SQL: {criteria_fragment.expression}")

        # Restore context
        self.context.current_table = old_table
        self.context.parent_path = old_path

        # Use dialect method to generate all() check SQL
        # This maintains the thin dialect architecture: business logic here, syntax in dialect
        all_check_sql = self.dialect.generate_all_check(
            column=old_table,
            path=collection_path,
            element_alias=element_alias,
            criteria_expr=criteria_fragment.expression
        )

        logger.debug(f"Generated all() SQL: {all_check_sql}")

        return SQLFragment(
            expression=all_check_sql,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=[]
        )

    def _translate_last(self, node: FunctionCallNode) -> SQLFragment:
        """Translate last() function to SQL using ORDER BY ... LIMIT 1 semantics.

        The last() function returns the final element from a collection. When the
        collection is empty, the result is an empty collection (NULL in SQL terms).

        Population-First Design:
            Generates SQL that orders elements by their array ordinality and uses
            LIMIT 1 to pick the final element. This executes entirely within the
            database engine without row-by-row iteration.

        SP-022-004: For UNNESTED collections, uses row filtering with MAX ordering
        column value to select the last element.

        Args:
            node: FunctionCallNode representing last() invocation

        Returns:
            SQLFragment yielding the final element expression

        Raises:
            ValueError: If last() receives any arguments
        """
        logger.debug(f"Translating last() function with {len(node.arguments)} arguments")

        if node.arguments:
            raise ValueError(f"last() function takes no arguments, got {len(node.arguments)}")

        (
            collection_expr,
            dependencies,
            _,
            snapshot,
            _,
            target_path,
        ) = self._resolve_function_target(node)

        source_table = snapshot["current_table"]

        # SP-022-004: Check if UNNEST fragments were generated for the target
        unnest_fragments = [f for f in self.fragments if f.requires_unnest]
        has_unnest_fragments = len(unnest_fragments) > 0

        if has_unnest_fragments:
            # Collection is unnested - use row filtering for last element
            # Get the result column from the last UNNEST fragment
            last_unnest = unnest_fragments[-1]
            result_col = last_unnest.metadata.get("result_alias", "result")

            # Count the unnest levels to know how many ordering columns there are
            unnest_count = len(unnest_fragments)

            # SP-022-004: Determine the element type for subsequent field access
            element_type = None
            if target_path:
                element_type = self._get_element_type_for_path(target_path)

            # SP-022-008: Fallback to derive element type from UNNEST fragment source_path
            if element_type is None and last_unnest.metadata:
                source_path = last_unnest.metadata.get("source_path", "")
                if source_path:
                    path_parts = source_path.replace("$", "").strip(".").split(".")
                    path_parts = [p.replace("[*]", "").strip() for p in path_parts if p.strip()]
                    if path_parts:
                        element_type = self._get_element_type_for_path(path_parts)
                        logger.debug(
                            f"SP-022-008: Derived element_type '{element_type}' from "
                            f"UNNEST source_path '{source_path}' in last()"
                        )

            last_fragment = SQLFragment(
                expression=result_col,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={
                    "function": "last",
                    "subset_filter": "last",  # Tell CTE builder to filter to last row
                    "unnest_count": unnest_count,
                    "element_type": element_type,
                }
            )

            self.fragments.append(last_fragment)

            # SP-101-002: Register column alias for CTE output
            self.context.register_column_alias("result", result_col)

            # Update context for subsequent field access
            self.context.current_element_column = "result"
            self.context.current_element_type = element_type
            self.context.parent_path.clear()

            return last_fragment

        # No UNNEST - use JSON array last element extraction
        detached = self._detach_simple_target_fragment(collection_expr)
        if detached:
            dependencies = []

        try:
            if not collection_expr:
                raise ValueError("last() requires a collection expression to operate on")

            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            last_sql = self.dialect.generate_array_last(normalized_expr)
            final_expr, metadata = self._apply_collection_remainder(
                node,
                last_sql,
                {"function": "last", "is_collection": False}
            )

            return SQLFragment(
                expression=final_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata=metadata
            )
        finally:
            self._restore_context(snapshot)

    def _translate_skip(self, node: FunctionCallNode) -> SQLFragment:
        """Translate skip() function to SQL using OFFSET semantics.

        skip(n) returns the collection with the first ``n`` elements removed.
        The implementation emits SQL that enumerates array elements, orders them
        by their natural index, and applies OFFSET to discard the requested prefix.

        SP-022-004: For UNNESTED collections, uses row filtering instead of JSON
        manipulation for better performance and correct chaining with subsequent
        field access.

        Args:
            node: FunctionCallNode representing skip() invocation

        Returns:
            SQLFragment containing population-scale SQL for skip()

        Raises:
            ValueError: If skip() does not receive exactly one argument
        """
        logger.debug(f"Translating skip() function with {len(node.arguments)} arguments")

        if len(node.arguments) != 1:
            raise ValueError(
                f"skip() function requires exactly 1 argument (skip count), "
                f"got {len(node.arguments)}"
            )

        (
            collection_expr,
            dependencies,
            _,
            snapshot,
            _,
            target_path,
        ) = self._resolve_function_target(node)

        source_table = snapshot["current_table"]

        # SP-022-004: Check if UNNEST fragments were generated for the target
        unnest_fragments = [f for f in self.fragments if f.requires_unnest]
        has_unnest_fragments = len(unnest_fragments) > 0

        if has_unnest_fragments:
            # Collection is unnested - use row filtering
            last_unnest = unnest_fragments[-1]
            result_col = last_unnest.metadata.get("result_alias", "result")
            unnest_count = len(unnest_fragments)

            # Get the skip count
            skip_fragment = self.visit(node.arguments[0])
            skip_count = skip_fragment.expression

            # Determine element type for subsequent field access
            element_type = None
            if target_path:
                element_type = self._get_element_type_for_path(target_path)

            # SP-022-008: Fallback to derive element type from UNNEST fragment source_path
            # When target_path is not available (e.g., empty after translation), we can
            # infer the element type from the UNNEST fragment's source_path metadata
            if element_type is None and last_unnest.metadata:
                source_path = last_unnest.metadata.get("source_path", "")
                # Parse source_path like '$.name[*]' to get element name
                if source_path:
                    path_parts = source_path.replace("$", "").strip(".").split(".")
                    path_parts = [p.replace("[*]", "").strip() for p in path_parts if p.strip()]
                    if path_parts:
                        # Derive element type from the parsed path
                        element_type = self._get_element_type_for_path(path_parts)
                        logger.debug(
                            f"SP-022-008: Derived element_type '{element_type}' from "
                            f"UNNEST source_path '{source_path}'"
                        )

            skip_result_fragment = SQLFragment(
                expression=result_col,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={
                    "function": "skip",
                    "subset_filter": "skip",
                    "subset_count": int(skip_count) if skip_count.isdigit() else None,
                    "unnest_count": unnest_count,
                    "element_type": element_type,
                    "is_collection": True,  # skip returns multiple elements
                }
            )

            self.fragments.append(skip_result_fragment)

            # SP-101-002: Register column alias for CTE output
            self.context.register_column_alias("result", result_col)

            # SP-022-004: Update context for subsequent field access
            # Even though skip returns a collection, each row has an element in
            # the "result" column, so field access should extract from that
            self.context.current_element_column = "result"
            self.context.current_element_type = element_type
            self.context.parent_path.clear()

            return skip_result_fragment

        # No UNNEST - use JSON array skip
        detached = self._detach_simple_target_fragment(collection_expr)
        if detached:
            dependencies = []
        try:
            if not collection_expr:
                raise ValueError("skip() requires a collection expression to operate on")

            skip_fragment = self.visit(node.arguments[0])
            skip_expr = skip_fragment.expression
            if hasattr(skip_fragment, "dependencies"):
                dependencies.extend(skip_fragment.dependencies)

            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            skip_sql = self.dialect.generate_array_skip(normalized_expr, skip_expr)
            element_alias = self._generate_internal_alias("skip")
            result_alias = f"{element_alias}_item"
            final_expr, metadata = self._apply_collection_remainder(
                node,
                skip_sql,
                {
                    "function": "skip",
                    "is_collection": True,
                    "array_column": skip_sql,
                    "result_alias": result_alias,
                    "projection_expression": result_alias,
                    "source_path": node.text
                }
            )
            requires_unnest = bool(metadata.get("is_collection")) and bool(metadata.get("array_column"))

            return SQLFragment(
                expression=final_expr,
                source_table=source_table,
                requires_unnest=requires_unnest,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata=metadata
            )
        finally:
            self._restore_context(snapshot)

    def _translate_tail(self, node: FunctionCallNode) -> SQLFragment:
        """Translate tail() function to SQL (syntactic sugar for skip(1)).

        SP-022-004: For UNNESTED collections, uses row filtering with ordering
        column > 1 to skip the first element.
        """
        logger.debug(f"Translating tail() function with {len(node.arguments)} arguments")

        if node.arguments:
            raise ValueError(f"tail() function takes no arguments, got {len(node.arguments)}")

        (
            collection_expr,
            dependencies,
            _,
            snapshot,
            _,
            target_path,
        ) = self._resolve_function_target(node)

        source_table = snapshot["current_table"]

        # SP-022-004: Check if UNNEST fragments were generated for the target
        unnest_fragments = [f for f in self.fragments if f.requires_unnest]
        has_unnest_fragments = len(unnest_fragments) > 0

        if has_unnest_fragments:
            # Collection is unnested - use row filtering (tail = skip(1))
            last_unnest = unnest_fragments[-1]
            result_col = last_unnest.metadata.get("result_alias", "result")
            unnest_count = len(unnest_fragments)

            # Determine element type for subsequent field access
            element_type = None
            if target_path:
                element_type = self._get_element_type_for_path(target_path)

            # SP-022-008: Fallback to derive element type from UNNEST fragment source_path
            if element_type is None and last_unnest.metadata:
                source_path = last_unnest.metadata.get("source_path", "")
                if source_path:
                    path_parts = source_path.replace("$", "").strip(".").split(".")
                    path_parts = [p.replace("[*]", "").strip() for p in path_parts if p.strip()]
                    if path_parts:
                        element_type = self._get_element_type_for_path(path_parts)
                        logger.debug(
                            f"SP-022-008: Derived element_type '{element_type}' from "
                            f"UNNEST source_path '{source_path}' in tail()"
                        )

            tail_result_fragment = SQLFragment(
                expression=result_col,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={
                    "function": "tail",
                    "subset_filter": "skip",  # tail is skip(1)
                    "subset_count": 1,
                    "unnest_count": unnest_count,
                    "element_type": element_type,
                    "is_collection": True,
                }
            )

            self.fragments.append(tail_result_fragment)

            # SP-101-002: Register column alias for CTE output
            self.context.register_column_alias("result", result_col)

            # SP-022-004: Update context for subsequent field access
            self.context.current_element_column = "result"
            self.context.current_element_type = element_type
            self.context.parent_path.clear()

            return tail_result_fragment

        # No UNNEST - use JSON array skip
        detached = self._detach_simple_target_fragment(collection_expr)
        if detached:
            dependencies = []

        try:
            if not collection_expr:
                raise ValueError("tail() requires a collection expression to operate on")

            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            tail_sql = self.dialect.generate_array_skip(normalized_expr, "1")
            element_alias = self._generate_internal_alias("tail")
            result_alias = f"{element_alias}_item"
            final_expr, metadata = self._apply_collection_remainder(
                node,
                tail_sql,
                {
                    "function": "tail",
                    "is_collection": True,
                    "array_column": tail_sql,
                    "result_alias": result_alias,
                    "projection_expression": result_alias,
                    "source_path": node.text
                }
            )
            requires_unnest = bool(metadata.get("is_collection")) and bool(metadata.get("array_column"))

            return SQLFragment(
                expression=final_expr,
                source_table=source_table,
                requires_unnest=requires_unnest,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata=metadata
            )
        finally:
            self._restore_context(snapshot)

    def _translate_trace(self, node: FunctionCallNode) -> SQLFragment:
        """Translate trace() function to SQL (pass-through for debugging).

        The trace() function is used for debugging FHIRPath expressions. It logs
        the current collection/value and returns it unchanged. In SQL translation,
        we implement this as a pass-through that returns the target expression.

        FHIRPath Specification:
            trace(name : string [, projection : expression]) : collection
            - name: identifier for the trace output (for logging)
            - projection: optional expression to project before tracing
            - Returns: the input collection unchanged

        Args:
            node: FunctionCallNode representing trace() function call

        Returns:
            SQLFragment with the target expression (pass-through)

        Raises:
            ValueError: If trace() has invalid arguments

        Example:
            Input: name.given.trace('test')
            Output: Returns name.given unchanged (in production SQL execution)

            Input: name.trace('test', given)
            Output: Returns name unchanged (projection argument ignored in SQL)
        """
        logger.debug(f"Translating trace() function with {len(node.arguments)} arguments")

        # trace() requires 1 or 2 arguments: trace(name) or trace(name, projection)
        if len(node.arguments) not in [1, 2]:
            raise ValueError(
                f"trace() function requires 1 or 2 arguments (name [, projection]), "
                f"got {len(node.arguments)}"
            )

        # SP-110-010: trace() needs to visit the target directly to get the full fragment
        # including preserved_columns. We cannot use _resolve_function_target because it
        # doesn't return the full fragment with metadata.
        snapshot = self._snapshot_context()

        try:
            if node.target is not None:
                # Visit the target directly to get the full fragment
                target_fragment = self.visit(node.target)

                # Add trace-specific metadata
                metadata = dict(getattr(target_fragment, "metadata", {}) or {})
                metadata["function"] = "trace"
                metadata["pass_through"] = True

                # Return the target fragment unchanged (pass-through)
                # This preserves all properties including preserved_columns
                return SQLFragment(
                    expression=target_fragment.expression,
                    source_table=target_fragment.source_table,
                    requires_unnest=getattr(target_fragment, "requires_unnest", False),
                    is_aggregate=getattr(target_fragment, "is_aggregate", False),
                    dependencies=list(dict.fromkeys(getattr(target_fragment, "dependencies", []))),
                    metadata=metadata,
                    preserved_columns=getattr(target_fragment, "preserved_columns", None)
                )
            else:
                # No explicit target - this shouldn't happen for trace()
                # but handle it gracefully
                source_table = snapshot["current_table"]
                return SQLFragment(
                    expression=source_table,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    metadata={"function": "trace", "pass_through": True}
                )
        finally:
            self._restore_context(snapshot)

    def _translate_single(self, node: FunctionCallNode) -> SQLFragment:
        """Translate single() function to SQL with cardinality check.

        The single() function returns the collection if and only if it contains
        exactly one element. If the collection is empty or contains more than one
        element, it returns an empty collection.

        FHIRPath Specification:
            single() : collection
            - Returns the collection if it has exactly 1 element
            - Returns empty collection {} otherwise

        Population-First Design:
            Uses array_length() check with CASE expression to conditionally return
            the collection based on size. This operates on each patient's data
            independently, maintaining population-scale capability.

        Args:
            node: FunctionCallNode representing single() function call

        Returns:
            SQLFragment with conditional SQL based on collection size

        Raises:
            ValueError: If single() has arguments (it should not)

        Example:
            Input: Patient.name.first().single()
            - first() returns 1 element → single() returns that element

            Input: Patient.name.single()
            - Patient.name has 3 elements → single() returns empty collection

            SQL Output (DuckDB):
                CASE
                    WHEN json_array_length(json_extract(resource, '$.name')) = 1
                    THEN json_extract(resource, '$.name')
                    ELSE NULL
                END
        """
        logger.debug(f"Translating single() function with {len(node.arguments)} arguments")

        # Validate single() has no arguments
        if len(node.arguments) != 0:
            raise ValueError(
                f"single() function requires 0 arguments, got {len(node.arguments)}"
            )

        # Get the target collection
        (
            collection_expr,
            dependencies,
            _,
            snapshot,
            _,
            target_path,
        ) = self._resolve_function_target(node)

        source_table = snapshot["current_table"]

        try:
            if not collection_expr:
                raise ValueError("single() requires a collection expression to operate on")

            # SP-022-017: When single() follows a collection function (first/last/take/tail),
            # the previous function's output is renamed to "result" in the CTE. We need to
            # use "result" instead of the original expression.
            # Check if there's a pending fragment from a collection function
            unnest_fragments = [f for f in self.fragments if f.requires_unnest]
            subset_fragments = [f for f in self.fragments if f.metadata.get("subset_filter")]

            if subset_fragments:
                # After a subset filter (first/last/take/tail), use "result" as the collection
                # and check length against a normalized version
                normalized_expr = self._normalize_collection_expression("result")
                length_expr = self.dialect.get_json_array_length(
                    column=source_table,
                    path=None  # Result is already the collection, no path needed
                )
            else:
                # Extract base collection source for length check
                base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
                normalized_expr = self._normalize_collection_expression(base_expr)

                # Build JSON path string from target_path list for length check
                json_path = None
                if target_path and target_path != "$":
                    json_path = self._build_json_path(target_path)

                # Get array length using dialect-specific function
                length_expr = self.dialect.get_json_array_length(
                    column=source_table,
                    path=json_path
                )

            # Generate conditional: return collection if length == 1, else NULL (empty)
            single_sql = f"CASE WHEN {length_expr} = 1 THEN {normalized_expr} ELSE NULL END"

            logger.debug(f"Generated single() SQL with cardinality check")

            return SQLFragment(
                expression=single_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "single", "has_cardinality_check": True}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_take(self, node: FunctionCallNode) -> SQLFragment:
        """Translate take() function to SQL using LIMIT semantics.

        take(n) returns the first ``n`` elements from a collection. The generated
        SQL enumerates array elements, orders them, and applies LIMIT to obtain
        the requested prefix while preserving population-scale execution.

        SP-022-004: For UNNESTED collections, uses row filtering with ordering
        column <= n to take the first n elements.

        Args:
            node: FunctionCallNode representing take() invocation

        Returns:
            SQLFragment implementing take() in SQL

        Raises:
            ValueError: If take() does not receive exactly one argument
        """
        logger.debug(f"Translating take() function with {len(node.arguments)} arguments")

        if len(node.arguments) != 1:
            raise ValueError(
                f"take() function requires exactly 1 argument (take count), "
                f"got {len(node.arguments)}"
            )

        (
            collection_expr,
            dependencies,
            _,
            snapshot,
            _,
            target_path,
        ) = self._resolve_function_target(node)

        source_table = snapshot["current_table"]

        # SP-022-004: Check if UNNEST fragments were generated for the target
        unnest_fragments = [f for f in self.fragments if f.requires_unnest]
        has_unnest_fragments = len(unnest_fragments) > 0

        if has_unnest_fragments:
            # Collection is unnested - use row filtering
            last_unnest = unnest_fragments[-1]
            result_col = last_unnest.metadata.get("result_alias", "result")
            unnest_count = len(unnest_fragments)

            # Get the take count
            take_fragment = self.visit(node.arguments[0])
            take_count = take_fragment.expression

            # Determine element type for subsequent field access
            element_type = None
            if target_path:
                element_type = self._get_element_type_for_path(target_path)

            # SP-022-008: Fallback to derive element type from UNNEST fragment source_path
            if element_type is None and last_unnest.metadata:
                source_path = last_unnest.metadata.get("source_path", "")
                if source_path:
                    path_parts = source_path.replace("$", "").strip(".").split(".")
                    path_parts = [p.replace("[*]", "").strip() for p in path_parts if p.strip()]
                    if path_parts:
                        element_type = self._get_element_type_for_path(path_parts)
                        logger.debug(
                            f"SP-022-008: Derived element_type '{element_type}' from "
                            f"UNNEST source_path '{source_path}' in take()"
                        )

            take_result_fragment = SQLFragment(
                expression=result_col,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={
                    "function": "take",
                    "subset_filter": "take",
                    "subset_count": int(take_count) if take_count.isdigit() else None,
                    "unnest_count": unnest_count,
                    "element_type": element_type,
                    "is_collection": True,
                }
            )

            self.fragments.append(take_result_fragment)

            # SP-101-002: Register column alias for CTE output
            self.context.register_column_alias("result", result_col)

            # SP-022-004: Update context for subsequent field access
            self.context.current_element_column = "result"
            self.context.current_element_type = element_type
            self.context.parent_path.clear()

            return take_result_fragment

        # No UNNEST - use JSON array take
        detached = self._detach_simple_target_fragment(collection_expr)
        if detached:
            dependencies = []

        try:
            if not collection_expr:
                raise ValueError("take() requires a collection expression to operate on")

            take_fragment = self.visit(node.arguments[0])
            take_expr = take_fragment.expression
            if hasattr(take_fragment, "dependencies"):
                dependencies.extend(take_fragment.dependencies)

            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            take_sql = self.dialect.generate_array_take(normalized_expr, take_expr)
            element_alias = self._generate_internal_alias("take")
            result_alias = f"{element_alias}_item"
            final_expr, metadata = self._apply_collection_remainder(
                node,
                take_sql,
                {
                    "function": "take",
                    "is_collection": True,
                    "array_column": take_sql,
                    "result_alias": result_alias,
                    "projection_expression": result_alias,
                    "source_path": node.text
                }
            )
            requires_unnest = bool(metadata.get("is_collection")) and bool(metadata.get("array_column"))

            return SQLFragment(
                expression=final_expr,
                source_table=source_table,
                requires_unnest=requires_unnest,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata=metadata
            )
        finally:
            self._restore_context(snapshot)

    def _translate_math_function(self, node: FunctionCallNode) -> SQLFragment:
        """Translate math functions to SQL.

        Implements FHIRPath mathematical functions using dialect-specific SQL.
        These functions work on Integer and Decimal types and return the same type.

        Math functions can be called in two ways:
        1. With argument(s): abs(-5), power(2, 3) -> node.arguments[0], node.arguments[1]
        2. On current context: value.abs() -> use current path from context

        The business logic (determining which function to call, validating arguments)
        is in this translator. The dialect provides only syntax differences for
        database-specific function names.

        Args:
            node: FunctionCallNode representing a math function call

        Returns:
            SQLFragment containing the math function SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            abs() function with argument:
            >>> node = FunctionCallNode(function_name="abs", arguments=[value_node])
            >>> fragment = translator._translate_math_function(node)
            >>> fragment.expression
            "abs(value_expr)"

            power() function with two arguments:
            >>> node = FunctionCallNode(function_name="power", arguments=[base_node, exp_node])
            >>> fragment = translator._translate_math_function(node)
            >>> fragment.expression
            "pow(base_expr, exp_expr)"  # DuckDB syntax

            ceiling() function on context:
            >>> node = FunctionCallNode(function_name="ceiling", arguments=[])
            >>> fragment = translator._translate_math_function(node)
            >>> fragment.expression
            "ceil(json_extract(...))"  # operates on current context

        Note:
            Basic math functions (0-1 arguments):
            - abs(): returns absolute value
            - ceiling(): rounds up to nearest integer
            - floor(): rounds down to nearest integer
            - round(): rounds to nearest integer (with optional precision)
            - truncate(): removes decimal part
            - sqrt(): square root
            - exp(): exponential (e^x)
            - ln(): natural logarithm
            - log(): logarithm base 10

            Advanced math functions (2 arguments):
            - power(): exponentiation (base, exponent)
        """
        logger.debug(f"Translating math function: {node.function_name}")

        function_name = node.function_name.lower()

        if function_name == "power":
            return self._translate_power_function(node)

        remaining_args = list(node.arguments)
        dependencies: List[str] = []
        value_fragment: Optional[SQLFragment] = None
        value_expression: Optional[str] = None

        if node.target is not None:
            snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            value_fragment = target_fragment
            value_expression = target_fragment.expression
            if hasattr(target_fragment, "dependencies"):
                for dep in target_fragment.dependencies:
                    if dep not in dependencies:
                        dependencies.append(dep)
            self._restore_context(snapshot)

            # Some invocation forms may redundantly include the target as the
            # first argument; drop exact matches to avoid double counting.
            if remaining_args and remaining_args[0] is node.target:
                remaining_args = remaining_args[1:]
        elif self.fragments:
            # SP-022-014: No target, but we have previous fragments from an invocation chain.
            # This happens with invocation patterns like "(-5).abs()" or "(1.2/1.8).round(2)"
            # where the AST has the value as a sibling node that was already visited.
            # Use the previous fragment's expression as the value.
            # Any remaining_args are treated as optional parameters (e.g., precision for round).
            value_fragment = self.fragments[-1]
            value_expression = value_fragment.expression
            if hasattr(value_fragment, "dependencies") and value_fragment.dependencies:
                for dep in value_fragment.dependencies:
                    if dep not in dependencies:
                        dependencies.append(dep)
            # Remove the previous fragment since we're incorporating it into the math function
            self.fragments.pop()
        elif remaining_args:
            # No target and no previous fragments - treat first argument as the value.
            # This handles standalone calls like abs(-5) where -5 is the value.
            first_arg_fragment = self.visit(remaining_args[0])
            value_fragment = first_arg_fragment
            value_expression = first_arg_fragment.expression
            if hasattr(first_arg_fragment, "dependencies"):
                for dep in first_arg_fragment.dependencies:
                    if dep not in dependencies:
                        dependencies.append(dep)
            remaining_args = remaining_args[1:]
        else:
            current_path = self.context.get_json_path()
            if current_path and current_path != "$":
                value_expression = self.dialect.extract_json_field(
                    column=self.context.current_table,
                    path=current_path
                )
            else:
                value_expression = self.context.current_table
            value_fragment = SQLFragment(
                expression=value_expression,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False
            )

        if value_expression is None:
            raise ValueError(f"Unable to resolve target for {node.function_name}()")

        # SP-110-008: Detect and fix unary minus literals that were incorrectly parsed as JSON paths
        # When the parser sees (-5).abs(), it may incorrectly treat the '-' as a path component
        # resulting in expressions like "json_extract_string(resource, '$.-')" instead of "-5"
        # We detect this pattern and extract the actual numeric value
        if "json_extract" in value_expression and "'$.-'" in value_expression:
            logger.debug(f"Detected unary minus JSON path in math function: {value_expression}")
            # This is a unary minus literal mis-parsed as JSON path - extract the numeric value
            # The expression should be a simple negative number, not a JSON extraction
            if value_fragment and value_fragment.metadata:
                # Check if we have a literal value in metadata
                if "text" in value_fragment.metadata:
                    text_value = value_fragment.metadata.get("text", "")
                    # Extract numeric value from text like "-5" or "-5.5"
                    if text_value and text_value.startswith("-"):
                        try:
                            # Parse the numeric value
                            numeric_value = float(text_value) if "." in text_value else int(text_value)
                            # Use the direct numeric value instead of JSON path
                            value_expression = str(numeric_value)
                            logger.debug(f"Extracted numeric value from unary minus: {value_expression}")
                        except (ValueError, TypeError):
                            logger.debug(f"Could not parse numeric value from text: {text_value}")

        # Functions that accept an optional additional argument (e.g., precision for round/truncate)
        functions_with_optional_arg = {"round", "truncate", "log"}

        # Validate argument count based on function type
        if function_name in functions_with_optional_arg:
            # These functions can have 0-1 additional arguments
            if len(remaining_args) > 1:
                raise ValueError(
                    f"Math function '{node.function_name}' takes at most 1 argument, got {len(remaining_args)}"
                )
        else:
            # All other math functions (abs, ceiling, floor, sqrt, exp, ln, log) take no additional arguments
            if len(remaining_args) > 0:
                raise ValueError(
                    f"Math function '{node.function_name}' takes at most 1 argument, got {len(remaining_args) + 1}"
                )

        additional_exprs: List[str] = []
        for arg_node in remaining_args:
            arg_fragment = self.visit(arg_node)
            additional_exprs.append(arg_fragment.expression)
            if hasattr(arg_fragment, "dependencies"):
                for dep in arg_fragment.dependencies:
                    if dep not in dependencies:
                        dependencies.append(dep)

        # SP-110-005: Special handling for abs() on quantity literals
        # When abs() is called on a quantity literal like (-5.5 'mg'),
        # we need to extract the value, apply abs(), and reconstruct the quantity JSON
        if function_name == "abs" and value_fragment and value_fragment.metadata:
            literal_type = value_fragment.metadata.get('literal_type')
            if literal_type == 'quantity':
                # Extract quantity value and unit
                quantity_value = value_fragment.metadata.get('quantity_value')
                quantity_unit = value_fragment.metadata.get('quantity_unit')

                if quantity_value is not None and quantity_unit is not None:
                    try:
                        # Parse the value and apply abs()
                        value_decimal = Decimal(str(quantity_value))
                        abs_value = abs(value_decimal)

                        # Build new quantity JSON with absolute value
                        from ..types.quantity_builder import build_quantity_json_string
                        quantity_json = build_quantity_json_string(abs_value, quantity_unit)
                        math_sql = f"'{quantity_json}'"

                        # Prepare dependency list (before dependency_list is defined later)
                        abs_dependency_list = list(dict.fromkeys(dependencies))

                        # Determine source table before the early return
                        abs_source_table = (
                            value_fragment.source_table
                            if value_fragment and value_fragment.source_table
                            else self.context.current_table
                        )
                        abs_requires_unnest = value_fragment.requires_unnest if value_fragment else False
                        abs_is_aggregate = value_fragment.is_aggregate if value_fragment else False

                        return SQLFragment(
                            expression=math_sql,
                            source_table=abs_source_table,
                            requires_unnest=abs_requires_unnest,
                            is_aggregate=abs_is_aggregate,
                            dependencies=abs_dependency_list,
                            metadata={
                                'literal_type': 'quantity',
                                'quantity_value': str(abs_value),
                                'quantity_unit': quantity_unit,
                                'is_literal': True
                            }
                        )
                    except (InvalidOperation, TypeError):
                        # Fall through to default handling
                        pass

        if function_name == "sqrt":
            value_as_double = self.dialect.cast_to_double(value_expression)
            finite_check = self.dialect.is_finite(value_as_double)
            sqrt_call = self.dialect.generate_math_function(node.function_name, value_as_double)
            math_sql = (
                "("
                "CASE "
                f"WHEN {value_as_double} IS NULL THEN NULL "
                f"WHEN NOT {finite_check} THEN NULL "
                f"WHEN {value_as_double} < 0 THEN NULL "
                f"ELSE {sqrt_call} "
                "END)"
            )
        elif function_name == "log" and additional_exprs:
            base_expression = additional_exprs[0]
            value_as_double = self.dialect.cast_to_double(value_expression)
            base_as_double = self.dialect.cast_to_double(base_expression)
            value_finite_check = self.dialect.is_finite(value_as_double)
            base_finite_check = self.dialect.is_finite(base_as_double)
            ln_value = self.dialect.generate_math_function("ln", value_as_double)
            ln_base = self.dialect.generate_math_function("ln", base_as_double)
            math_sql = (
                "("
                "CASE "
                f"WHEN {value_as_double} IS NULL OR {base_as_double} IS NULL THEN NULL "
                f"WHEN NOT {value_finite_check} OR NOT {base_finite_check} THEN NULL "
                f"WHEN {value_as_double} <= 0 THEN NULL "
                f"WHEN {base_as_double} <= 0 OR {base_as_double} = 1 THEN NULL "
                # Change of base: log_b(x) = ln(x) / ln(b)
                f"ELSE ({ln_value} / {ln_base}) "
                "END)"
            )
        else:
            math_sql = self.dialect.generate_math_function(
                node.function_name,
                value_expression,
                *additional_exprs
            )

        source_table = (
            value_fragment.source_table
            if value_fragment and value_fragment.source_table
            else self.context.current_table
        )
        requires_unnest = value_fragment.requires_unnest if value_fragment else False
        is_aggregate = value_fragment.is_aggregate if value_fragment else False
        dependency_list = list(dict.fromkeys(dependencies))

        logger.debug(f"Generated {node.function_name}() SQL: {math_sql}")

        return SQLFragment(
            expression=math_sql,
            source_table=source_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=dependency_list
        )

    def _translate_power_function(self, node: FunctionCallNode) -> SQLFragment:
        """Translate power() math function with domain safety checks."""
        args = list(node.arguments)
        dependencies: List[str] = []

        base_fragment: Optional[SQLFragment] = None
        base_expr: Optional[str] = None

        if node.target is not None:
            snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            base_fragment = target_fragment
            base_expr = target_fragment.expression
            if hasattr(target_fragment, "dependencies"):
                for dep in target_fragment.dependencies:
                    if dep not in dependencies:
                        dependencies.append(dep)
            self._restore_context(snapshot)

            if len(args) != 1:
                raise ValueError(
                    f"Function 'power' invoked as method requires exactly 1 argument, got {len(args)}"
                )
            exponent_node = args[0]
        elif self.fragments:
            # Method invocation like 2.power(3) where base is in fragments
            base_fragment = self.fragments[-1]
            base_expr = base_fragment.expression
            if hasattr(base_fragment, "dependencies"):
                for dep in base_fragment.dependencies:
                    if dep not in dependencies:
                        dependencies.append(dep)
            # Remove the base fragment since we're incorporating it into power()
            self.fragments.pop()

            if len(args) != 1:
                raise ValueError(
                    f"Function 'power' invoked as method on context requires exactly 1 argument, got {len(args)}"
                )
            exponent_node = args[0]
        else:
            if len(args) != 2:
                raise ValueError(
                    f"Function 'power' requires exactly 2 arguments, got {len(args)}"
                )
            base_fragment = self.visit(args[0])
            base_expr = base_fragment.expression
            if hasattr(base_fragment, "dependencies"):
                for dep in base_fragment.dependencies:
                    if dep not in dependencies:
                        dependencies.append(dep)
            exponent_node = args[1]

        if base_expr is None:
            raise ValueError("Unable to resolve base expression for power()")

        exponent_fragment = self.visit(exponent_node)
        exponent_expr = exponent_fragment.expression
        if hasattr(exponent_fragment, "dependencies"):
            for dep in exponent_fragment.dependencies:
                if dep not in dependencies:
                    dependencies.append(dep)

        base_as_double = self.dialect.cast_to_double(base_expr)
        exponent_as_double = self.dialect.cast_to_double(exponent_expr)
        finite_base_check = self.dialect.is_finite(base_as_double)
        finite_exponent_check = self.dialect.is_finite(exponent_as_double)

        floor_exponent = self.dialect.generate_math_function("floor", exponent_as_double)
        power_call = self.dialect.generate_math_function(
            "power",
            base_as_double,
            exponent_as_double
        )
        finite_power_check = self.dialect.is_finite(power_call)

        guarded_power_sql = (
            "("
            "CASE "
            f"WHEN {base_as_double} IS NULL OR {exponent_as_double} IS NULL THEN NULL "
            f"WHEN NOT ({finite_base_check}) OR NOT ({finite_exponent_check}) THEN NULL "
            f"WHEN {base_as_double} = 0 AND {exponent_as_double} = 0 THEN 1 "
            f"WHEN {base_as_double} = 0 AND {exponent_as_double} < 0 THEN NULL "
            f"WHEN {base_as_double} < 0 AND {exponent_as_double} <> {floor_exponent} THEN NULL "
            f"WHEN NOT {finite_power_check} THEN NULL "
            f"ELSE {power_call} "
            "END)"
        )

        logger.debug(f"Generated power() SQL: {guarded_power_sql}")

        return SQLFragment(
            expression=guarded_power_sql,
            source_table=(
                base_fragment.source_table
                if base_fragment and base_fragment.source_table
                else self.context.current_table
            ),
            requires_unnest=base_fragment.requires_unnest if base_fragment else False,
            is_aggregate=base_fragment.is_aggregate if base_fragment else False,
            dependencies=list(dict.fromkeys(dependencies))
        )

    def _translate_string_function(self, node: FunctionCallNode) -> SQLFragment:
        """Translate string functions to SQL.

        Implements FHIRPath string manipulation functions using dialect-specific SQL.
        These functions work on String types and handle common string operations.

        String functions can be called in two ways:
        1. With argument(s): substring('hello', 1, 3) -> node.arguments contains all args
        2. On current context: name.substring(1, 3) -> use current path from context

        The business logic (determining arguments, validating counts, index conversion)
        is in this translator. The dialect provides only syntax differences for
        database-specific function names and syntax.

        Args:
            node: FunctionCallNode representing a string function call

        Returns:
            SQLFragment containing the string function SQL

        Raises:
            ValueError: If function has invalid number of arguments
        """
        logger.debug(f"Translating string function: {node.function_name}")

        func_name = node.function_name.lower()

        # Ensure context path reflects target when invoked as method
        self._prefill_path_from_function(node)

        def _argument_is_string(arg_node: FHIRPathASTNode) -> bool:
            """Check if an argument node represents a string literal.

            SP-025-002: Enhanced to handle EnhancedASTNode by checking if text
            is a quoted string literal (starts and ends with single quotes).

            For non-literal nodes (identifiers, paths), returns True to allow
            expressions like indexOf(name.family, 'Sm') where the first arg
            is an identifier.
            """
            if isinstance(arg_node, LiteralNode):
                return arg_node.literal_type == "string"
            # For EnhancedASTNode, check if it's clearly NOT a string
            # (e.g., numeric literal like 0 or 4)
            text = getattr(arg_node, 'text', '').strip()
            if text and text.startswith("'") and text.endswith("'"):
                return True
            # Check if it's a numeric literal (digits or decimal point)
            if text and text.replace('.', '').replace('-', '').isdigit():
                return False
            # For identifiers, paths, and other expressions, allow them
            return True

        original_arg_count = len(node.arguments)
        dependencies: List[str] = []
        args = list(node.arguments)
        string_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        metadata: Dict[str, Any] = {}  # SP-110-007: Initialize metadata for preserving array_column etc.

        if node.target is not None:
            target_snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            string_expr = target_fragment.expression
            source_table = target_fragment.source_table or target_snapshot["current_table"]
            requires_unnest = getattr(target_fragment, "requires_unnest", False)
            is_aggregate = getattr(target_fragment, "is_aggregate", False)
            if hasattr(target_fragment, "dependencies"):
                dependencies.extend(target_fragment.dependencies)
            # SP-110-007: Preserve metadata from target fragment
            if hasattr(target_fragment, "metadata") and target_fragment.metadata:
                metadata = target_fragment.metadata.copy()
            self._restore_context(target_snapshot)

        string_arg_allowed = func_name in {"substring", "length", "replace", "indexof"}

        should_consume_string_arg = (
            string_arg_allowed
            and string_expr is None
            and args
            and _argument_is_string(args[0])
            and (func_name != "substring" or original_arg_count >= 2)  # substring needs 2+ args to consume first as string
            and (func_name != "indexof" or original_arg_count > 1)
            and (
                func_name != "replace" or original_arg_count == 3
            )
        )

        if should_consume_string_arg:
            string_fragment = self.visit(args[0])
            string_expr = string_fragment.expression
            source_table = string_fragment.source_table or self.context.current_table
            requires_unnest = getattr(string_fragment, "requires_unnest", False)
            is_aggregate = getattr(string_fragment, "is_aggregate", False)
            if hasattr(string_fragment, "dependencies"):
                dependencies.extend(string_fragment.dependencies)
            # SP-110-007: Preserve metadata from string fragment
            if hasattr(string_fragment, "metadata") and string_fragment.metadata:
                metadata = string_fragment.metadata.copy()
            args = args[1:]

        if string_expr is None:
            # SP-022-012: Check for pending_fragment_result from InvocationExpression chain
            # This handles cases like $this.length() where $this was visited before length()
            # and its expression was stored in pending_fragment_result
            # SP-102-001: pending_fragment_result is a tuple (sql_expression, parent_path, is_multi_item)
            # SP-110-007: metadata is initialized here to ensure it exists for all code paths
            if self.context.pending_fragment_result is not None:
                # Ensure metadata is initialized if not already set
                if not metadata:
                    metadata = {}
                logger.debug(f"SP-102-001 DEBUG: substring found pending_fragment_result = {self.context.pending_fragment_result}")
                # Extract the SQL expression from the tuple
                pending_result = self.context.pending_fragment_result
                if isinstance(pending_result, tuple):
                    string_expr = pending_result[0]  # sql_expression is first element
                else:
                    # Legacy behavior: if it's not a tuple, use it directly
                    string_expr = pending_result

                # SP-025-002: Find the fragment that generated this expression and track dependencies
                # This ensures the CTE manager properly chains fragments together
                if self.fragments:
                    # The most recent fragment should be the one that generated pending_fragment_result
                    pending_fragment = self.fragments[-1]
                    # Compare with the actual expression, not the tuple
                    fragment_expr = pending_fragment.expression
                    if isinstance(fragment_expr, str) and fragment_expr == string_expr:
                        # Add dependencies from the pending fragment
                        if hasattr(pending_fragment, "dependencies") and pending_fragment.dependencies:
                            dependencies.extend(pending_fragment.dependencies)
                        # Update source table from the pending fragment
                        source_table = pending_fragment.source_table or source_table
                        requires_unnest = getattr(pending_fragment, "requires_unnest", requires_unnest)
                        is_aggregate = getattr(pending_fragment, "is_aggregate", is_aggregate)
                        # SP-110-007: Preserve metadata including array_column for UNNEST operations
                        # This is critical for CTE manager to properly handle the fragment
                        if hasattr(pending_fragment, "metadata") and pending_fragment.metadata:
                            metadata = pending_fragment.metadata.copy()
                            # SP-110-007 CRITICAL FIX: When processing a UNNEST result, use the CTE column name
                            # directly. The projection_expression contains 'given_item.unnest' which is how
                            # we get the UNNEST result in the CTE SELECT clause. But once we're in the next CTE,
                            # the column is available directly as 'given_item' (the result_alias).
                            # So we should use the result_alias to reference the CTE column.
                            pending_metadata = pending_fragment.metadata
                            if metadata.get("unnest_level", 0) > 0:
                                # This fragment came from a UNNEST operation
                                # Use the result_alias to reference the CTE column
                                result_alias = metadata.get("result_alias")
                                if result_alias:
                                    # Use the result_alias which is the CTE column name (e.g., 'given_item')
                                    # This is the column that contains the UNNEST result
                                    string_expr = result_alias
                                    # Mark that we're not requiring UNNEST since we're using the CTE column
                                    requires_unnest = False
                                    logger.debug(f"SP-110-007: Using CTE column {string_expr} (result_alias) instead of re-extracting")
                # Clear the pending result after consuming it
                self.context.pending_fragment_result = None
                if source_table is None:
                    source_table = self.context.current_table
            else:
                # SP-107-005: Check context path BEFORE $this to avoid using default $this binding
                # when there's a meaningful context path available
                current_path = self.context.get_json_path()
                if current_path and current_path != "$":
                    # Use the context path if available
                    string_expr = self.dialect.extract_json_field(
                        column=self.context.current_table,
                        path=current_path
                    )
                    source_table = self.context.current_table
                    requires_unnest = False
                    is_aggregate = False
                    # SP-110-007: Initialize empty metadata for context path case
                    metadata = {}
                    logger.debug(
                        f"Using context path for string function: {current_path} -> {string_expr}"
                    )
                # SP-102-001: Check if we're in a lambda scope with $this bound
                # This handles cases like substring($this.length()-3) where the string
                # argument is implicit and should be $this
                elif func_name in ("substring", "indexof", "replace"):
                    logger.debug(f"SP-102-001 DEBUG: substring checking for $this, func_name={func_name}")
                    this_binding = self.context.get_variable("$this")
                    if this_binding is not None:
                        # Use $this as the implicit string argument
                        # SP-102-001: $this might be a column reference (like 'given_item') or an expression
                        # For column references from UNNEST, we need to unwrap the JSON to get the string value
                        this_expr = this_binding.expression
                        # Check if this is a simple column reference (no parentheses, no function calls)
                        is_simple_column = this_expr and not any(c in this_expr for c in '()')

                        if is_simple_column:
                            # Simple column reference - need to unwrap JSON
                            # Use extract_json_string to get the scalar value from the JSON column
                            string_expr = self.dialect.extract_json_string(this_expr, "$")
                            logger.debug(
                                f"SP-102-001: Unwrapped $this column {this_expr} -> {string_expr}"
                            )
                        else:
                            # Complex expression - use as-is
                            string_expr = this_expr
                            logger.debug(
                                f"SP-102-001: Using $this expression directly: {string_expr}"
                            )

                        source_table = this_binding.source_table or self.context.current_table
                        requires_unnest = this_binding.requires_unnest
                        is_aggregate = this_binding.is_aggregate
                        if this_binding.dependencies:
                            dependencies.extend(this_binding.dependencies)
                        # SP-110-007: Preserve metadata from $this binding
                        if hasattr(this_binding, "metadata") and this_binding.metadata:
                            metadata = this_binding.metadata.copy()
                        logger.debug(
                            f"SP-102-001: Using $this as implicit string argument for {func_name}"
                        )
                    else:
                        # No context path and no $this, use current table directly
                        string_expr = self.context.current_table
                        source_table = self.context.current_table
                        requires_unnest = False
                        is_aggregate = False
                else:
                    # For other functions (length), use current table if no context path
                    string_expr = self.context.current_table
                    source_table = self.context.current_table
                    requires_unnest = False
                    is_aggregate = False

        if source_table is None:
            source_table = self.context.current_table

        if func_name == 'substring':
            if original_arg_count < 1 or original_arg_count > 3:
                raise ValueError(
                    f"substring() requires 1-3 arguments, got {original_arg_count}"
                )

            # SP-110-005: Return NULL for out-of-bounds (not empty string)
            # Per FHIRPath spec compliance, substring with negative start or start >= length
            # should return NULL so that .empty() correctly returns TRUE.
            # Returning empty string '' would make .empty() return FALSE (incorrect).
            empty_sql = "NULL"

            if args:
                start_fragment = self.visit(args[0])
                start_expr = start_fragment.expression
                if hasattr(start_fragment, "dependencies"):
                    dependencies.extend(start_fragment.dependencies)
                args = args[1:]
            else:
                start_expr = "0"

            length_expr: Optional[str] = None
            if args:
                if len(args) > 1:
                    raise ValueError("substring() accepts at most one length argument")
                length_fragment = self.visit(args[0])
                length_expr = length_fragment.expression
                if hasattr(length_fragment, "dependencies"):
                    dependencies.extend(length_fragment.dependencies)

            # SP-106-003: Cast start expression to BIGINT for substring compatibility
            # length() returns DOUBLE, but substring expects BIGINT
            start_cast = f"TRY_CAST({start_expr} AS BIGINT)"
            start_condition = f"({start_cast})"
            start_plus_one = f"({start_condition} + 1)"

            if length_expr is not None:
                # SP-106-003: Cast length expression to BIGINT
                length_cast = f"TRY_CAST({length_expr} AS BIGINT)"
                substring_sql = self.dialect.generate_string_function(
                    'substring',
                    string_expr,
                    start_plus_one,
                    length_cast
                )
            else:
                substring_sql = self.dialect.generate_string_function(
                    'substring',
                    string_expr,
                    start_plus_one
                )

            # Calculate string length for bounds checking
            string_length = self.dialect.generate_string_function('length', string_expr)

            case_clauses = [
                f"WHEN {string_expr} IS NULL THEN NULL",
                f"WHEN {start_condition} IS NULL THEN NULL",
                f"WHEN {start_condition} < 0 THEN {empty_sql}",
                f"WHEN {start_condition} >= {string_length} THEN {empty_sql}",
            ]

            if length_expr is not None:
                length_condition = f"({length_expr})"
                case_clauses.append(f"WHEN {length_condition} IS NULL THEN NULL")
                case_clauses.append(f"WHEN {length_condition} <= 0 THEN {empty_sql}")

            case_clauses.append(f"ELSE {substring_sql}")
            string_sql = f"(CASE {' '.join(case_clauses)} END)"

        elif func_name == 'indexof':
            if len(args) != 1:
                raise ValueError(
                    f"indexOf() requires exactly 1 argument (substring), got {original_arg_count}"
                )

            search_fragment = self.visit(args[0])
            search_expr = search_fragment.expression
            if hasattr(search_fragment, "dependencies"):
                dependencies.extend(search_fragment.dependencies)

            index_sql = self.dialect.generate_string_function(
                'indexOf',
                string_expr,
                search_expr
            )

            string_sql = (
                "("
                "CASE "
                f"WHEN {string_expr} IS NULL THEN NULL "
                f"WHEN {search_expr} IS NULL THEN NULL "
                f"ELSE {index_sql} "
                "END)"
            )

        elif func_name == 'length':
            if original_arg_count > 1:
                raise ValueError(
                    f"length() takes at most 1 argument, got {original_arg_count}"
                )

            string_sql = self.dialect.generate_string_function(
                'length',
                string_expr
            )

        elif func_name == 'split':
            if len(args) != 1:
                raise ValueError(
                    f"split() requires exactly 1 argument (delimiter), got {original_arg_count}"
                )

            delimiter_fragment = self.visit(args[0])
            if hasattr(delimiter_fragment, "dependencies"):
                dependencies.extend(delimiter_fragment.dependencies)

            string_sql = self.dialect.split_string(
                expression=string_expr,
                delimiter=delimiter_fragment.expression
            )

        elif func_name == 'replace':
            if len(args) != 2:
                raise ValueError(
                    f"replace() requires exactly 2 arguments (pattern, substitution), got {original_arg_count}"
                )

            search_fragment = self.visit(args[0])
            replace_fragment = self.visit(args[1])

            string_sql = self.dialect.generate_string_function(
                'replace',
                string_expr,
                search_fragment.expression,
                replace_fragment.expression
            )

            if hasattr(search_fragment, 'dependencies'):
                dependencies.extend(search_fragment.dependencies)
            if hasattr(replace_fragment, 'dependencies'):
                dependencies.extend(replace_fragment.dependencies)

        elif func_name == 'combine':
            # SP-025-002: Implement combine(separator) function
            # Joins collection elements with a separator
            if len(args) != 1:
                raise ValueError(
                    f"combine() requires exactly 1 argument (separator), got {original_arg_count}"
                )

            separator_fragment = self.visit(args[0])
            separator_expr = separator_fragment.expression

            if hasattr(separator_fragment, 'dependencies'):
                dependencies.extend(separator_fragment.dependencies)

            # combine() is an aggregate function that joins array elements
            # Use dialect-specific array to string conversion
            string_sql = self.dialect.generate_array_to_string(
                string_expr,
                separator_expr
            )
            is_aggregate = True

        elif func_name == 'distinct':
            # SP-025-002: Implement distinct() function
            # Removes duplicate values from a collection while preserving order
            if original_arg_count != 0:
                raise ValueError(
                    f"distinct() takes no arguments, got {original_arg_count}"
                )

            # distinct() operates on the current collection expression
            # Use dialect-specific distinct operation
            string_sql = self.dialect.generate_distinct(string_expr)
            # Mark as requiring special handling for collection operations
            requires_unnest = True

        elif func_name == 'isdistinct':
            # SP-025-002: Implement isDistinct() function
            # Returns true if all elements in the collection are unique
            if original_arg_count != 0:
                raise ValueError(
                    f"isDistinct() takes no arguments, got {original_arg_count}"
                )

            # isDistinct() checks if the collection has only unique values
            # Use dialect-specific uniqueness check
            string_sql = self.dialect.generate_is_distinct(string_expr)
            is_aggregate = True

        else:
            raise ValueError(f"Unknown string function: {func_name}")

        logger.debug(f"Generated {node.function_name}() SQL: {string_sql}")

        return SQLFragment(
            expression=string_sql,
            source_table=source_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata=metadata  # SP-110-007: Preserve metadata including array_column for UNNEST operations
        )


    def _resolve_string_target_and_args(
        self,
        node: FunctionCallNode,
        *,
        function_label: str,
        allow_explicit_argument: bool = False
    ) -> Tuple[str, List[str], str, bool, bool, Optional[dict], List[FHIRPathASTNode]]:
        """Resolve the string input and remaining arguments for string predicates."""
        args = list(node.arguments)
        dependencies: List[str] = []
        string_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        restore_snapshot: Optional[dict] = None

        def _argument_is_string(arg_node: FHIRPathASTNode) -> bool:
            """Check if an argument node represents a string literal.

            SP-025-002: Enhanced to handle EnhancedASTNode by checking if text
            is a quoted string literal (starts and ends with single quotes).

            For non-literal nodes (identifiers, paths), returns True to allow
            expressions like indexOf(name.family, 'Sm') where the first arg
            is an identifier.
            """
            if isinstance(arg_node, LiteralNode):
                return arg_node.literal_type == "string"
            # For EnhancedASTNode, check if it's clearly NOT a string
            # (e.g., numeric literal like 0 or 4)
            text = getattr(arg_node, 'text', '').strip()
            if text and text.startswith("'") and text.endswith("'"):
                return True
            # Check if it's a numeric literal (digits or decimal point)
            if text and text.replace('.', '').replace('-', '').isdigit():
                return False
            # For identifiers, paths, and other expressions, allow them
            return True

        if node.target is not None:
            target_snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            string_expr = target_fragment.expression
            source_table = target_fragment.source_table or target_snapshot["current_table"]
            requires_unnest = getattr(target_fragment, "requires_unnest", False)
            is_aggregate = getattr(target_fragment, "is_aggregate", False)
            if hasattr(target_fragment, "dependencies") and target_fragment.dependencies:
                dependencies.extend(target_fragment.dependencies)
            self._restore_context(target_snapshot)
        elif (
            allow_explicit_argument
            and len(args) >= 2
            and _argument_is_string(args[0])
            and not (
                isinstance(args[0], LiteralNode)
                and args[0].literal_type == "string"
            )
        ):
            string_fragment = self.visit(args[0])
            string_expr = string_fragment.expression
            source_table = string_fragment.source_table or self.context.current_table
            requires_unnest = getattr(string_fragment, "requires_unnest", False)
            is_aggregate = getattr(string_fragment, "is_aggregate", False)
            if hasattr(string_fragment, "dependencies") and string_fragment.dependencies:
                dependencies.extend(string_fragment.dependencies)
            args = args[1:]
        else:
            (
                string_expr,
                target_dependencies,
                _,
                snapshot,
                _,
                _
            ) = self._resolve_function_target(node)
            dependencies.extend(target_dependencies)
            source_table = snapshot["current_table"]
            restore_snapshot = snapshot

        if not string_expr:
            raise ValueError(f"{function_label}() requires a string input")

        return (
            string_expr,
            list(dict.fromkeys(dependencies)),
            source_table or self.context.current_table,
            requires_unnest,
            is_aggregate,
            restore_snapshot,
            args
        )

    def _translate_contains(self, node: FunctionCallNode) -> SQLFragment:
        """Translate contains() function to SQL for substring detection.

        FHIRPath: string.contains(substring)
        SQL: (string LIKE '%' || substring || '%') [Both DuckDB & PostgreSQL]

        The contains() function tests if a string contains a substring.
        This is a method call where the string is the implicit target (from context)
        and the substring is the explicit argument.

        Args:
            node: FunctionCallNode representing contains() function call

        Returns:
            SQLFragment containing the substring check SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            Patient.name.family.contains('Smith'):
            >>> node = FunctionCallNode(function_name="contains", arguments=[substring_node])
            >>> fragment = translator._translate_contains(node)
            >>> fragment.expression  # Both databases
            "(json_extract(resource, '$.name[0].family') LIKE '%' || 'Smith' || '%')"

        Note:
            - Operates on current context (implicit string)
            - Takes exactly 1 argument (substring)
            - Returns boolean (true if substring found, false if not)
            - Case-sensitive matching
            - Empty substring returns true
            - NULL handling: null input → null output (both databases)
        """
        logger.debug(f"Translating contains() function")

        original_arg_count = len(node.arguments)

        self._prefill_path_from_function(node)

        (
            string_expr,
            dependencies,
            source_table,
            requires_unnest,
            is_aggregate,
            restore_snapshot,
            remaining_args
        ) = self._resolve_string_target_and_args(
            node,
            function_label="contains",
            allow_explicit_argument=True
        )

        try:
            if len(remaining_args) != 1:
                raise ValueError(
                    f"contains() function requires exactly 1 argument (substring), "
                    f"got {original_arg_count}"
                )

            substring_fragment = self.visit(remaining_args[0])
            substring_expr = substring_fragment.expression

            if hasattr(substring_fragment, "dependencies") and substring_fragment.dependencies:
                dependencies.extend(substring_fragment.dependencies)

            contains_sql = self.dialect.generate_substring_check(
                string_expr,
                substring_expr
            )

            requires_unnest = (
                requires_unnest or getattr(substring_fragment, "requires_unnest", False)
            )
            is_aggregate = (
                is_aggregate or getattr(substring_fragment, "is_aggregate", False)
            )

            logger.debug(f"Generated contains() SQL: {contains_sql}")

            return SQLFragment(
                expression=contains_sql,
                source_table=source_table,
                requires_unnest=requires_unnest,
                is_aggregate=is_aggregate,
                dependencies=list(dict.fromkeys(dependencies))
            )
        finally:
            if restore_snapshot is not None:
                self._restore_context(restore_snapshot)

    def _translate_membership_expression(self, node: Any) -> SQLFragment:
        """Translate membership 'in' expression to SQL.

        FHIRPath: value in collection
        SQL: collection contains value (reversed)

        The 'in' operator tests if a value is a member of a collection.
        In FHIRPath, this is semantically equivalent to: collection contains value
        Note the reversal of operands compared to SQL IN clause.

        Args:
            node: MembershipExpression node with two children (value, collection)

        Returns:
            SQLFragment containing the membership test SQL
        """
        logger.debug(f"Translating membership 'in' expression")

        if not hasattr(node, 'children') or len(node.children) != 2:
            raise ValueError(
                f"MembershipExpression requires exactly 2 children (value, collection), "
                f"got {len(getattr(node, 'children', []))}"
            )

        # Child 0: value to check (left side of 'in')
        value_fragment = self.visit(node.children[0])

        # Child 1: collection to check in (right side of 'in')
        collection_fragment = self.visit(node.children[1])

        # Combine dependencies
        dependencies = list(collection_fragment.dependencies or [])
        if value_fragment.dependencies:
            dependencies.extend(value_fragment.dependencies)

        # Use dialect to generate membership test
        # For 'in' operator, we need: collection contains value
        contains_sql = self.dialect.generate_membership_test(
            collection_fragment.expression,
            value_fragment.expression
        )

        logger.debug(f"Generated membership 'in' SQL: {contains_sql}")

        return SQLFragment(
            expression=contains_sql,
            source_table=collection_fragment.source_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata={"function": "contains", "result_type": "boolean"}
        )

    def _translate_contains_membership(self, node: FunctionCallNode) -> SQLFragment:
        """Translate membership contains operator to SQL.

        FHIRPath: collection contains value
        SQL: EXISTS (SELECT 1 FROM json_each(collection) WHERE value = target)

        The membership contains operator tests if a value is a member of a collection.
        This is a binary operator where both the collection and value are explicit arguments.

        Args:
            node: FunctionCallNode representing contains() function call with 2 arguments

        Returns:
            SQLFragment containing the membership test SQL

        Raises:
            ValueError: If function doesn't have exactly 2 arguments

        Example:
            (1 | 2 | 3) contains 1:
            >>> node = FunctionCallNode(function_name="contains", arguments=[collection_node, value_node])
            >>> fragment = translator._translate_contains_membership(node)
            >>> fragment.expression
            "EXISTS (SELECT 1 FROM json_each(...) WHERE value = 1)"
        """
        logger.debug(f"Translating membership contains() operator")

        if len(node.arguments) != 2:
            raise ValueError(
                f"Membership contains() operator requires exactly 2 arguments (collection, value), "
                f"got {len(node.arguments)}"
            )

        # Translate collection (left operand)
        collection_fragment = self.visit(node.arguments[0])
        collection_expr = collection_fragment.expression

        # Translate value (right operand)
        value_fragment = self.visit(node.arguments[1])
        value_expr = value_fragment.expression

        # Combine dependencies
        dependencies = list(collection_fragment.dependencies or [])
        if value_fragment.dependencies:
            dependencies.extend(value_fragment.dependencies)

        # Use dialect to generate membership test
        # For simple cases, we can use: value_expr IN (collection_expr)
        # For JSON arrays, we need: EXISTS (SELECT 1 FROM json_each(collection) WHERE value = value_expr)
        contains_sql = self.dialect.generate_membership_test(
            collection_expr,
            value_expr
        )

        logger.debug(f"Generated membership contains() SQL: {contains_sql}")

        return SQLFragment(
            expression=contains_sql,
            source_table=collection_fragment.source_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata={"function": "contains", "result_type": "boolean"}
        )

    def _translate_startswith(self, node: FunctionCallNode) -> SQLFragment:
        """Translate startsWith() function to SQL for prefix matching.

        FHIRPath: string.startsWith(prefix)
        SQL: (string LIKE prefix || '%') [Both DuckDB & PostgreSQL]

        The startsWith() function tests if a string begins with a specified prefix.
        This is a method call where the string is the implicit target (from context)
        and the prefix is the explicit argument.

        Args:
            node: FunctionCallNode representing startsWith() function call

        Returns:
            SQLFragment containing the prefix check SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            Patient.name.family.startsWith('Mc'):
            >>> node = FunctionCallNode(function_name="startsWith", arguments=[prefix_node])
            >>> fragment = translator._translate_startswith(node)
            >>> fragment.expression  # Both databases
            "(json_extract(resource, '$.name[0].family') LIKE 'Mc' || '%')"

        Note:
            - Operates on current context (implicit string)
            - Takes exactly 1 argument (prefix)
            - Returns boolean (true if starts with prefix, false if not)
            - Case-sensitive matching
            - Empty prefix returns true
            - NULL handling: null input → null output (both databases)
        """
        logger.debug(f"Translating startsWith() function")

        original_arg_count = len(node.arguments)
        self._prefill_path_from_function(node)

        (
            string_expr,
            dependencies,
            source_table,
            requires_unnest,
            is_aggregate,
            restore_snapshot,
            remaining_args
        ) = self._resolve_string_target_and_args(
            node,
            function_label="startsWith",
            allow_explicit_argument=True
        )

        try:
            if len(remaining_args) != 1:
                raise ValueError(
                    f"startsWith() function requires exactly 1 argument (prefix), "
                    f"got {original_arg_count}"
                )

            prefix_fragment = self.visit(remaining_args[0])
            prefix_expr = prefix_fragment.expression

            if hasattr(prefix_fragment, "dependencies") and prefix_fragment.dependencies:
                dependencies.extend(prefix_fragment.dependencies)

            startswith_sql = self.dialect.generate_prefix_check(
                string_expr,
                prefix_expr
            )

            requires_unnest = (
                requires_unnest or getattr(prefix_fragment, "requires_unnest", False)
            )
            is_aggregate = (
                is_aggregate or getattr(prefix_fragment, "is_aggregate", False)
            )

            logger.debug(f"Generated startsWith() SQL: {startswith_sql}")

            return SQLFragment(
                expression=startswith_sql,
                source_table=source_table,
                requires_unnest=requires_unnest,
                is_aggregate=is_aggregate,
                dependencies=list(dict.fromkeys(dependencies))
            )
        finally:
            if restore_snapshot is not None:
                self._restore_context(restore_snapshot)

    def _translate_endswith(self, node: FunctionCallNode) -> SQLFragment:
        """Translate endsWith() function to SQL for suffix matching.

        FHIRPath: string.endsWith(suffix)
        SQL: (string LIKE '%' || suffix) [Both DuckDB & PostgreSQL]

        The endsWith() function tests if a string ends with a specified suffix.
        This is a method call where the string is the implicit target (from context)
        and the suffix is the explicit argument.

        Args:
            node: FunctionCallNode representing endsWith() function call

        Returns:
            SQLFragment containing the suffix check SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            Patient.name.family.endsWith('son'):
            >>> node = FunctionCallNode(function_name="endsWith", arguments=[suffix_node])
            >>> fragment = translator._translate_endswith(node)
            >>> fragment.expression  # Both databases
            "(json_extract(resource, '$.name[0].family') LIKE '%' || 'son')"

        Note:
            - Operates on current context (implicit string)
            - Takes exactly 1 argument (suffix)
            - Returns boolean (true if ends with suffix, false if not)
            - Case-sensitive matching
            - Empty suffix returns true
            - NULL handling: null input → null output (both databases)
        """
        logger.debug(f"Translating endsWith() function")

        original_arg_count = len(node.arguments)
        self._prefill_path_from_function(node)

        (
            string_expr,
            dependencies,
            source_table,
            requires_unnest,
            is_aggregate,
            restore_snapshot,
            remaining_args
        ) = self._resolve_string_target_and_args(
            node,
            function_label="endsWith",
            allow_explicit_argument=True
        )

        try:
            if len(remaining_args) != 1:
                raise ValueError(
                    f"endsWith() function requires exactly 1 argument (suffix), "
                    f"got {original_arg_count}"
                )

            suffix_fragment = self.visit(remaining_args[0])
            suffix_expr = suffix_fragment.expression

            if hasattr(suffix_fragment, "dependencies") and suffix_fragment.dependencies:
                dependencies.extend(suffix_fragment.dependencies)

            endswith_sql = self.dialect.generate_suffix_check(
                string_expr,
                suffix_expr
            )

            requires_unnest = (
                requires_unnest or getattr(suffix_fragment, "requires_unnest", False)
            )
            is_aggregate = (
                is_aggregate or getattr(suffix_fragment, "is_aggregate", False)
            )

            logger.debug(f"Generated endsWith() SQL: {endswith_sql}")

            return SQLFragment(
                expression=endswith_sql,
                source_table=source_table,
                requires_unnest=requires_unnest,
                is_aggregate=is_aggregate,
                dependencies=list(dict.fromkeys(dependencies))
            )
        finally:
            if restore_snapshot is not None:
                self._restore_context(restore_snapshot)

    def _translate_upper(self, node: FunctionCallNode) -> SQLFragment:
        """Translate upper() function to SQL for uppercase conversion.

        FHIRPath: string.upper()
        SQL: UPPER(string) [Both DuckDB & PostgreSQL]

        The upper() function converts a string to uppercase.
        This is a method call where the string is the implicit target (from context)
        and the function takes no arguments.

        Args:
            node: FunctionCallNode representing upper() function call

        Returns:
            SQLFragment containing the uppercase conversion SQL

        Raises:
            ValueError: If function has any arguments

        Example:
            Patient.name.family.upper():
            >>> node = FunctionCallNode(function_name="upper", arguments=[])
            >>> fragment = translator._translate_upper(node)
            >>> fragment.expression  # Both databases
            "UPPER(json_extract(resource, '$.name[0].family'))"

        Note:
            - Operates on current context (implicit string)
            - Takes no arguments
            - Returns string in uppercase
            - NULL handling: null input → null output (both databases)
        """
        logger.debug(f"Translating upper() function")

        self._prefill_path_from_function(node)

        (
            target_expr,
            dependencies,
            source_table,
            requires_unnest,
            is_aggregate,
            restore_snapshot
        ) = self._resolve_single_string_input(node, "upper")

        try:
            upper_sql = self.dialect.generate_case_conversion(target_expr, "upper")
            logger.debug(f"Generated upper() SQL: {upper_sql}")

            return SQLFragment(
                expression=upper_sql,
                source_table=source_table,
                requires_unnest=requires_unnest,
                is_aggregate=is_aggregate,
                dependencies=dependencies
            )
        finally:
            if restore_snapshot is not None:
                self._restore_context(restore_snapshot)

    def _resolve_single_string_input(
        self,
        node: FunctionCallNode,
        function_label: str
    ) -> Tuple[str, List[str], str, bool, bool, Optional[dict]]:
        """Resolve the string input for simple unary string functions.

        Supports both method invocations (name.upper()) and global invocations
        (upper(name)) by accepting either the implicit target or a single
        explicit argument.
        """
        args = list(node.arguments)
        if node.target is not None:
            args = [arg for arg in args if arg is not node.target]

        if len(args) > 1:
            raise ValueError(
                f"{function_label}() takes at most 1 argument, got {len(args)}"
            )

        dependencies: List[str] = []
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        restore_snapshot: Optional[dict] = None
        target_expr: Optional[str] = None

        if args:
            arg_snapshot = self._snapshot_context()
            arg_fragment: Optional[SQLFragment] = None
            try:
                arg_fragment = self.visit(args[0])
            finally:
                self._restore_context(arg_snapshot)

            if arg_fragment is None:
                raise FHIRPathTranslationError(
                    f"Unable to resolve argument for {function_label}()"
                )

            target_expr = arg_fragment.expression
            if hasattr(arg_fragment, "dependencies") and arg_fragment.dependencies:
                dependencies.extend(arg_fragment.dependencies)
            source_table = arg_fragment.source_table or arg_snapshot["current_table"]
            requires_unnest = getattr(arg_fragment, "requires_unnest", False)
            is_aggregate = getattr(arg_fragment, "is_aggregate", False)
        else:
            (
                resolved_expr,
                target_dependencies,
                _,
                snapshot,
                _,
                _
            ) = self._resolve_function_target(node)
            target_expr = resolved_expr
            if target_dependencies:
                dependencies.extend(target_dependencies)
            source_table = snapshot["current_table"]
            restore_snapshot = snapshot

        if not target_expr:
            raise ValueError(f"{function_label}() requires a string input")

        return (
            target_expr,
            list(dict.fromkeys(dependencies)),
            source_table or self.context.current_table,
            requires_unnest,
            is_aggregate,
            restore_snapshot
        )

    def _translate_lower(self, node: FunctionCallNode) -> SQLFragment:
        """Translate lower() function to SQL for lowercase conversion.

        FHIRPath: string.lower()
        SQL: LOWER(string) [Both DuckDB & PostgreSQL]

        The lower() function converts a string to lowercase.
        This is a method call where the string is the implicit target (from context)
        and the function takes no arguments.

        Args:
            node: FunctionCallNode representing lower() function call

        Returns:
            SQLFragment containing the lowercase conversion SQL

        Raises:
            ValueError: If function has any arguments

        Example:
            Patient.name.family.lower():
            >>> node = FunctionCallNode(function_name="lower", arguments=[])
            >>> fragment = translator._translate_lower(node)
            >>> fragment.expression  # Both databases
            "LOWER(json_extract(resource, '$.name[0].family'))"

        Note:
            - Operates on current context (implicit string)
            - Takes no arguments
            - Returns string in lowercase
            - NULL handling: null input → null output (both databases)
        """
        logger.debug(f"Translating lower() function")

        self._prefill_path_from_function(node)

        (
            target_expr,
            dependencies,
            source_table,
            requires_unnest,
            is_aggregate,
            restore_snapshot
        ) = self._resolve_single_string_input(node, "lower")

        try:
            lower_sql = self.dialect.generate_case_conversion(target_expr, "lower")
            logger.debug(f"Generated lower() SQL: {lower_sql}")

            return SQLFragment(
                expression=lower_sql,
                source_table=source_table,
                requires_unnest=requires_unnest,
                is_aggregate=is_aggregate,
                dependencies=dependencies
            )
        finally:
            if restore_snapshot is not None:
                self._restore_context(restore_snapshot)

    def _translate_trim(self, node: FunctionCallNode) -> SQLFragment:
        """Translate trim() function to SQL for whitespace removal.

        FHIRPath: string.trim()
        SQL: TRIM(string) [Both DuckDB & PostgreSQL]

        The trim() function removes leading and trailing whitespace from a string.
        This is a method call where the string is the implicit target (from context)
        and the function takes no arguments.

        Args:
            node: FunctionCallNode representing trim() function call

        Returns:
            SQLFragment containing the trim SQL

        Raises:
            ValueError: If function has any arguments

        Example:
            Patient.name.family.trim():
            >>> node = FunctionCallNode(function_name="trim", arguments=[])
            >>> fragment = translator._translate_trim(node)
            >>> fragment.expression  # Both databases
            "TRIM(json_extract(resource, '$.name[0].family'))"

        Note:
            - Operates on current context (implicit string)
            - Takes no arguments
            - Returns string with leading and trailing whitespace removed
            - NULL handling: null input → null output (both databases)
        """
        logger.debug(f"Translating trim() function")

        self._prefill_path_from_function(node)

        (
            target_expr,
            dependencies,
            source_table,
            requires_unnest,
            is_aggregate,
            restore_snapshot
        ) = self._resolve_single_string_input(node, "trim")

        try:
            trim_sql = self.dialect.generate_trim(target_expr)
            logger.debug(f"Generated trim() SQL: {trim_sql}")

            return SQLFragment(
                expression=trim_sql,
                source_table=source_table,
                requires_unnest=requires_unnest,
                is_aggregate=is_aggregate,
                dependencies=dependencies
            )
        finally:
            if restore_snapshot is not None:
                self._restore_context(restore_snapshot)

    def _translate_tochars(self, node: FunctionCallNode) -> SQLFragment:
        """Translate toChars() function to SQL for character array conversion.

        FHIRPath: string.toChars()
        SQL: CASE WHEN length(string) = 0 THEN [] ELSE regexp_split_to_array(string, '') END [DuckDB]
             CASE WHEN length(string) = 0 THEN ARRAY[]::text[] ELSE regexp_split_to_array(string, '') END [PostgreSQL]

        The toChars() function converts a string into an array of single-character strings.
        This enables character-level string processing in FHIRPath expressions.
        This is a method call where the string is the implicit target (from context)
        and the function takes no arguments.

        Args:
            node: FunctionCallNode representing toChars() function call

        Returns:
            SQLFragment containing the character array conversion SQL

        Raises:
            ValueError: If function has any arguments

        Example:
            'hello'.toChars():
            >>> node = FunctionCallNode(function_name="toChars", arguments=[])
            >>> fragment = translator._translate_tochars(node)
            >>> fragment.expression  # DuckDB
            "CASE WHEN length('hello') = 0 THEN [] ELSE regexp_split_to_array('hello', '') END"
            >>> fragment.expression  # PostgreSQL
            "CASE WHEN length('hello') = 0 THEN ARRAY[]::text[] ELSE regexp_split_to_array('hello', '') END"

        Note:
            - Operates on current context (implicit string)
            - Takes no arguments
            - Returns array of single-character strings
            - Empty string returns empty array (not array with empty string)
            - NULL handling: NULL input → empty array (both databases)
        """
        logger.debug(f"Translating toChars() function")

        # Validate arguments
        if len(node.arguments) != 0:
            raise ValueError(
                f"toChars() function takes no arguments, got {len(node.arguments)}"
            )

        # Get target string expression from current context
        current_path = self.context.get_json_path()
        target_expr = self.dialect.extract_json_field(
            column=self.context.current_table,
            path=current_path
        )

        # Generate character array SQL using dialect
        chars_sql = self.dialect.generate_char_array(target_expr)

        logger.debug(f"Generated toChars() SQL: {chars_sql}")

        return SQLFragment(
            expression=chars_sql,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=[]
        )

    def _translate_matches(self, node: FunctionCallNode) -> SQLFragment:
        """Translate matches() function to SQL for regex matching.

        FHIRPath: string.matches(regex)
        SQL: regexp_matches(string, regex) [DuckDB]
              string ~ regex [PostgreSQL]

        The matches() function tests if a string matches a regular expression pattern.
        This is a method call where the string is the implicit target (from context)
        and the regex pattern is the explicit argument.

        Args:
            node: FunctionCallNode representing matches() function call

        Returns:
            SQLFragment containing the regex matching SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            Patient.name.family.matches('[A-Z][a-z]+'):
            >>> node = FunctionCallNode(function_name="matches", arguments=[regex_node])
            >>> fragment = translator._translate_matches(node)
            >>> fragment.expression  # DuckDB
            "regexp_matches(json_extract(name_item, '$.family'), '[A-Z][a-z]+')"
            >>> fragment.expression  # PostgreSQL
            "(jsonb_extract_path_text(name_item, 'family') ~ '[A-Z][a-z]+')"

        Note:
            - Operates on current context (implicit string)
            - Takes exactly 1 argument (regex pattern)
            - Returns boolean (true if matches, false if not)
            - NULL handling: null input → null output (both databases)
            - Regex syntax: Both DuckDB (PCRE) and PostgreSQL (POSIX) tested compatible
            - SP-110-007: Uses pending_fragment_result to get string from CTEs
        """
        logger.debug(f"Translating matches() function")

        # Validate arguments
        if len(node.arguments) != 1:
            raise ValueError(
                f"matches() function requires exactly 1 argument (regex pattern), "
                f"got {len(node.arguments)}"
            )

        # SP-110-007: Get target string expression from pending_fragment_result or current context
        # This handles cases like "Patient.name.family.matches(...)" where the family
        # field is in a CTE (name_item), not the base resource
        string_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        dependencies: List[str] = []
        metadata: Dict[str, Any] = {}

        # Check for pending_fragment_result from InvocationExpression chain
        if self.context.pending_fragment_result is not None:
            pending_result = self.context.pending_fragment_result
            if isinstance(pending_result, tuple):
                string_expr = pending_result[0]  # sql_expression is first element
            else:
                string_expr = pending_result

            # Track dependencies from the pending fragment
            if self.fragments:
                pending_fragment = self.fragments[-1]
                fragment_expr = pending_fragment.expression
                if isinstance(fragment_expr, str) and fragment_expr == string_expr:
                    if hasattr(pending_fragment, "dependencies") and pending_fragment.dependencies:
                        dependencies.extend(pending_fragment.dependencies)
                    source_table = pending_fragment.source_table or source_table
                    requires_unnest = getattr(pending_fragment, "requires_unnest", requires_unnest)
                    is_aggregate = getattr(pending_fragment, "is_aggregate", is_aggregate)
                    # SP-110-007: Preserve metadata including array_column for UNNEST operations
                    if hasattr(pending_fragment, "metadata") and pending_fragment.metadata:
                        metadata = pending_fragment.metadata.copy()

            # Clear the pending result after consuming it
            self.context.pending_fragment_result = None
            if source_table is None:
                source_table = self.context.current_table
        else:
            # Fallback to current context path
            current_path = self.context.get_json_path()
            if current_path and current_path != "$":
                string_expr = self.dialect.extract_json_field(
                    column=self.context.current_table,
                    path=current_path
                )
                source_table = self.context.current_table

        if string_expr is None:
            string_expr = self.context.current_table
            source_table = self.context.current_table

        # Get regex pattern argument
        regex_pattern_node = node.arguments[0]
        regex_fragment = self.visit(regex_pattern_node)
        regex_pattern = regex_fragment.expression

        # Collect regex pattern dependencies
        if hasattr(regex_fragment, 'dependencies'):
            dependencies.extend(regex_fragment.dependencies)

        # Generate regex matching SQL using dialect
        matches_sql = self.dialect.generate_regex_match(
            string_expr,
            regex_pattern
        )

        logger.debug(f"Generated matches() SQL: {matches_sql}")

        return SQLFragment(
            expression=matches_sql,
            source_table=source_table or self.context.current_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata=metadata
        )

    def _translate_matchesfull(self, node: FunctionCallNode) -> SQLFragment:
        """Translate matchesFull() function to SQL for full-string regex matching.

        FHIRPath: string.matchesFull(regex)
        SQL: regexp_matches(string, '^' || regex || '$') [DuckDB]
             (string ~ ('^' || regex || '$')) [PostgreSQL]

        The matchesFull() function tests if a string matches a regular expression pattern
        across the ENTIRE string (not just a substring). This differs from matches() which
        returns true if the pattern matches anywhere in the string.

        This is a method call where the string is the implicit target (from context)
        and the regex pattern is the explicit argument.

        Args:
            node: FunctionCallNode representing matchesFull() function call

        Returns:
            SQLFragment containing the full-string regex matching SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            'hello'.matchesFull('ll'):
            >>> node = FunctionCallNode(function_name="matchesFull", arguments=[regex_node])
            >>> fragment = translator._translate_matchesfull(node)
            >>> fragment.expression  # DuckDB
            "regexp_matches('hello', '^ll$')"
            >>> fragment.expression  # PostgreSQL
            "('hello' ~ ('^ll$'))"

        Note:
            - Operates on current context (implicit string)
            - Takes exactly 1 argument (regex pattern)
            - Returns boolean (true if full string matches, false if not)
            - NULL handling: null input → null output (both databases)
            - Regex syntax: Both DuckDB (PCRE) and PostgreSQL (POSIX) tested compatible
            - The regex is anchored with ^ and $ to ensure full-string matching
            - SP-110-007: Uses pending_fragment_result to get string from CTEs
        """
        logger.debug(f"Translating matchesFull() function")

        # Validate arguments
        if len(node.arguments) != 1:
            raise ValueError(
                f"matchesFull() function requires exactly 1 argument (regex pattern), "
                f"got {len(node.arguments)}"
            )

        # SP-110-007: Get target string expression from pending_fragment_result or current context
        # This handles cases like "Patient.name.family.matchesFull(...)" where the family
        # field is in a CTE (name_item), not the base resource
        string_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        dependencies: List[str] = []
        metadata: Dict[str, Any] = {}

        # Check for pending_fragment_result from InvocationExpression chain
        if self.context.pending_fragment_result is not None:
            pending_result = self.context.pending_fragment_result
            if isinstance(pending_result, tuple):
                string_expr = pending_result[0]  # sql_expression is first element
            else:
                string_expr = pending_result

            # Track dependencies from the pending fragment
            if self.fragments:
                pending_fragment = self.fragments[-1]
                fragment_expr = pending_fragment.expression
                if isinstance(fragment_expr, str) and fragment_expr == string_expr:
                    if hasattr(pending_fragment, "dependencies") and pending_fragment.dependencies:
                        dependencies.extend(pending_fragment.dependencies)
                    source_table = pending_fragment.source_table or source_table
                    requires_unnest = getattr(pending_fragment, "requires_unnest", requires_unnest)
                    is_aggregate = getattr(pending_fragment, "is_aggregate", is_aggregate)
                    # SP-110-007: Preserve metadata including array_column for UNNEST operations
                    if hasattr(pending_fragment, "metadata") and pending_fragment.metadata:
                        metadata = pending_fragment.metadata.copy()

            # Clear the pending result after consuming it
            self.context.pending_fragment_result = None
            if source_table is None:
                source_table = self.context.current_table
        else:
            # Fallback to current context path
            current_path = self.context.get_json_path()
            if current_path and current_path != "$":
                string_expr = self.dialect.extract_json_field(
                    column=self.context.current_table,
                    path=current_path
                )
                source_table = self.context.current_table

        if string_expr is None:
            string_expr = self.context.current_table
            source_table = self.context.current_table

        # Get regex pattern argument
        regex_pattern_node = node.arguments[0]
        regex_fragment = self.visit(regex_pattern_node)
        regex_pattern = regex_fragment.expression

        # Collect regex pattern dependencies
        if hasattr(regex_fragment, 'dependencies'):
            dependencies.extend(regex_fragment.dependencies)

        # Anchor the regex pattern to match the full string
        # We need to wrap the pattern with ^ and $ anchors
        # Use concatenation to avoid modifying the user's pattern
        anchored_pattern = f"('^' || {regex_pattern} || '$')"

        # Generate regex matching SQL using dialect
        matchesfull_sql = self.dialect.generate_regex_match(
            string_expr,
            anchored_pattern
        )

        logger.debug(f"Generated matchesFull() SQL: {matchesfull_sql}")

        return SQLFragment(
            expression=matchesfull_sql,
            source_table=source_table or self.context.current_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata=metadata
        )

    def _translate_children(self, node: FunctionCallNode) -> SQLFragment:
        """Translate children() function to SQL for direct child access.

        FHIRPath: resource.children()
        SQL: Returns all direct child elements of the current node as a JSON array

        The children() function returns the direct children of the current node in a
        tree structure. For FHIR resources, this returns all child elements of the
        current resource or element as a collection.

        Args:
            node: FunctionCallNode representing children() function call

        Returns:
            SQLFragment containing the children extraction SQL

        Raises:
            ValueError: If function has any arguments (takes none)

        Example:
            Patient.children():
            >>> node = FunctionCallNode(function_name="children", arguments=[])
            >>> fragment = translator._translate_children(node)
            >>> fragment.expression  # Both databases
            Returns all child elements of Patient resource

        Note:
            - Operates on current context (implicit resource/element)
            - Takes no arguments
            - Returns collection of child elements
            - For FHIR resources, returns direct child fields/elements
            - NULL handling: null input → empty collection
            - SP-110-XXX: Use current_element_column when operating on UNNEST results
        """
        logger.debug(f"Translating children() function")

        # Validate arguments - children() takes no arguments
        if len(node.arguments) != 0:
            raise ValueError(
                f"children() function requires no arguments, got {len(node.arguments)}"
            )

        # SP-110-XXX: Check if we're operating on an UNNEST result
        # If current_element_column is set, we need to use that column instead of resource
        element_column = self.context.current_element_column
        source_table = self.context.current_table

        # Determine the source expression for children()
        # If we have an element_column (e.g., name_item from UNNEST), use it
        # Otherwise use the current table (resource or CTE)
        if element_column and element_column != source_table:
            # We're operating on an UNNEST result (e.g., Patient.name.children())
            current_expr = element_column
            logger.debug(f"SP-110-XXX: children() using element_column '{element_column}'")
        else:
            # We're at the resource level
            current_expr = source_table

        # For FHIR resources stored as JSON, children() returns all keys
        # We need to extract all child elements from the JSON structure
        # Both DuckDB and PostgreSQL support JSON key extraction

        # Use duckdb_postgres_json_keys to get all keys from the JSON object
        # Then for each key, extract the value
        # This creates a collection of child elements

        # Get the current JSON path (if any)
        current_path = self.context.get_json_path()

        if current_path and current_path != "$":
            # We're navigating within a resource, extract children from the current path
            parent_json = self.dialect.extract_json_field(
                column=current_expr,
                path=current_path
            )

            # Get all keys from this JSON object
            # DuckDB: json_keys(json), PostgreSQL: SELECT jsonb_object_keys(json)
            children_sql = self.dialect.generate_json_children(parent_json)
        else:
            # We're at the resource level or element level, get all children directly
            children_sql = self.dialect.generate_json_children(current_expr)

        logger.debug(f"Generated children() SQL: {children_sql}")

        # children() returns a complete SQL expression (subquery) that produces a JSON array
        # Unlike simple array path expressions that need UNNEST, this is a scalar array result
        # Similar to repeat() - requires_unnest=False because the expression is self-contained
        return SQLFragment(
            expression=children_sql,
            source_table=source_table,
            requires_unnest=False,  # Returns a scalar array result, not requiring UNNEST
            is_aggregate=False,
            dependencies=[],
            metadata={
                "function": "children",
                "result_type": "collection",
            }
        )

    def _translate_replacematches(self, node: FunctionCallNode) -> SQLFragment:
        """Translate replaceMatches() function to SQL for regex replacement.

        FHIRPath: string.replaceMatches(regex, substitution)
        SQL: regexp_replace(string, regex, substitution, 'g') [Both DuckDB & PostgreSQL]

        The replaceMatches() function replaces all occurrences of a regex pattern
        with a substitution string. This is a method call where the string is the
        implicit target (from context) and the regex pattern and substitution are
        explicit arguments.

        Args:
            node: FunctionCallNode representing replaceMatches() function call

        Returns:
            SQLFragment containing the regex replacement SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            Patient.name.family.replaceMatches('[0-9]', 'X'):
            >>> node = FunctionCallNode(function_name="replaceMatches", arguments=[regex_node, subst_node])
            >>> fragment = translator._translate_replacematches(node)
            >>> fragment.expression  # Both databases
            "regexp_replace(json_extract(name_item, '$.family'), '[0-9]', 'X', 'g')"

        Note:
            - Operates on current context (implicit string)
            - Takes exactly 2 arguments (regex pattern, substitution)
            - Returns transformed string
            - NULL handling: null input → null output (both databases)
            - Regex syntax: Both DuckDB (PCRE) and PostgreSQL (POSIX) support regexp_replace
            - Global replacement: 'g' flag replaces all matches, not just first
            - Capture groups: Both support $1, $2 in substitution (DuckDB) or \1, \2 (PostgreSQL)
            - SP-110-007: Uses pending_fragment_result to get string from CTEs
        """
        logger.debug(f"Translating replaceMatches() function")

        # Validate arguments
        if len(node.arguments) != 2:
            raise ValueError(
                f"replaceMatches() function requires exactly 2 arguments (regex pattern, substitution), "
                f"got {len(node.arguments)}"
            )

        # SP-110-007: Get target string expression from pending_fragment_result or current context
        string_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        dependencies: List[str] = []
        metadata: Dict[str, Any] = {}

        # Check for pending_fragment_result from InvocationExpression chain
        if self.context.pending_fragment_result is not None:
            pending_result = self.context.pending_fragment_result
            if isinstance(pending_result, tuple):
                string_expr = pending_result[0]  # sql_expression is first element
            else:
                string_expr = pending_result

            # Track dependencies from the pending fragment
            if self.fragments:
                pending_fragment = self.fragments[-1]
                fragment_expr = pending_fragment.expression
                if isinstance(fragment_expr, str) and fragment_expr == string_expr:
                    if hasattr(pending_fragment, "dependencies") and pending_fragment.dependencies:
                        dependencies.extend(pending_fragment.dependencies)
                    source_table = pending_fragment.source_table or source_table
                    requires_unnest = getattr(pending_fragment, "requires_unnest", requires_unnest)
                    is_aggregate = getattr(pending_fragment, "is_aggregate", is_aggregate)
                    # SP-110-007: Preserve metadata including array_column for UNNEST operations
                    if hasattr(pending_fragment, "metadata") and pending_fragment.metadata:
                        metadata = pending_fragment.metadata.copy()

            # Clear the pending result after consuming it
            self.context.pending_fragment_result = None
            if source_table is None:
                source_table = self.context.current_table
        else:
            # Fallback to current context path
            current_path = self.context.get_json_path()
            if current_path and current_path != "$":
                string_expr = self.dialect.extract_json_field(
                    column=self.context.current_table,
                    path=current_path
                )
                source_table = self.context.current_table

        if string_expr is None:
            string_expr = self.context.current_table
            source_table = self.context.current_table

        # Get regex pattern argument
        regex_pattern_node = node.arguments[0]
        regex_fragment = self.visit(regex_pattern_node)
        regex_pattern = regex_fragment.expression

        # Get substitution argument
        substitution_node = node.arguments[1]
        substitution_fragment = self.visit(substitution_node)
        substitution = substitution_fragment.expression

        # Collect dependencies from both arguments
        if hasattr(regex_fragment, 'dependencies'):
            dependencies.extend(regex_fragment.dependencies)
        if hasattr(substitution_fragment, 'dependencies'):
            dependencies.extend(substitution_fragment.dependencies)

        # Generate regex replacement SQL using dialect
        replace_sql = self.dialect.generate_regex_replace(
            string_expr,
            regex_pattern,
            substitution
        )

        logger.debug(f"Generated replaceMatches() SQL: {replace_sql}")

        return SQLFragment(
            expression=replace_sql,
            source_table=source_table or self.context.current_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata=metadata
        )

    def _translate_all_true(self, node: FunctionCallNode) -> SQLFragment:
        """Translate allTrue() function to SQL using BOOL_AND aggregate.

        FHIRPath Specification: Section 5.3.5
        Returns TRUE if all elements are TRUE. Empty collections return TRUE.

        SP-110-002: Handle both JSON arrays (via json_each) and UNNESTed collections
        (via direct aggregation on rows). When collection_expr is a simple column
        reference that's already a JSON array from a previous CTE, we need to
        enumerate it first.
        """
        logger.debug("Translating allTrue() function")

        if node.arguments:
            raise ValueError(f"allTrue() takes no arguments, got {len(node.arguments)}")

        (collection_expr, dependencies, _, snapshot, _, target_path) = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        # SP-110-002: Check if there's a pre-built SELECT from select()
        # In this case, the result column is already a JSON array
        has_select_result = any(
            f.metadata.get("function") == "select" for f in self.fragments
        )

        # SP-110-010: If there's a select result, use its source_table for dependencies
        # This fixes the issue where allTrue() was using 'resource' instead of the select() CTE
        if has_select_result and self.fragments:
            # Find the last select fragment and use its source_table
            for frag in reversed(self.fragments):
                if frag.metadata.get("function") == "select":
                    source_table = frag.source_table
                    # Also update dependencies to include the select fragment's dependencies
                    if frag.dependencies:
                        dependencies.extend(frag.dependencies)
                    break

        # SP-110-003: Also check if collection_expr itself is a SELECT statement
        # This handles edge cases where metadata might not be set correctly
        is_select_statement = collection_expr and collection_expr.strip().upper().startswith("SELECT")

        try:
            if not collection_expr:
                raise ValueError("allTrue() requires a collection expression")

            # SP-110-002: If the collection comes from select(), it's already in 'result' column
            # as a JSON array. We need to enumerate it with json_each.
            # SP-110-003: Also check if collection_expr is a SELECT statement directly
            if has_select_result or is_select_statement:
                # SP-110-003: Use <<SOURCE_TABLE>> marker which CTE builder will substitute
                # with the correct CTE name that contains the result column
                # The result column contains the aggregated JSON array from select()
                # Use centralized FHIRPath truthiness rules via dialect
                truthiness = self.dialect.generate_truthiness_type_check("value", "elem")
                all_true_sql = f"COALESCE((SELECT BOOL_AND({truthiness}) FROM json_each(<<SOURCE_TABLE>>.result)), TRUE)"
            else:
                base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
                normalized_expr = self._normalize_collection_expression(base_expr)
                all_true_sql = self.dialect.generate_all_true(normalized_expr)

            return SQLFragment(
                expression=all_true_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "allTrue", "result_type": "boolean", "skip_group_by": True}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_any_true(self, node: FunctionCallNode) -> SQLFragment:
        """Translate anyTrue() function to SQL using BOOL_OR aggregate.

        FHIRPath Specification: Section 5.3.6
        Returns TRUE if any element is TRUE. Empty collections return FALSE.

        SP-110-002: Handle both JSON arrays (via json_each) and UNNESTed collections
        (via direct aggregation on rows). When collection_expr is a simple column
        reference that's already a JSON array from a previous CTE, we need to
        enumerate it first.
        """
        logger.debug("Translating anyTrue() function")

        if node.arguments:
            raise ValueError(f"anyTrue() takes no arguments, got {len(node.arguments)}")

        (collection_expr, dependencies, _, snapshot, _, target_path) = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        # SP-110-002: Check if there's a pre-built SELECT from select()
        # In this case, the result column is already a JSON array
        has_select_result = any(
            f.metadata.get("function") == "select" for f in self.fragments
        )

        # SP-110-010: If there's a select result, use its source_table for dependencies
        if has_select_result and self.fragments:
            for frag in reversed(self.fragments):
                if frag.metadata.get("function") == "select":
                    source_table = frag.source_table
                    if frag.dependencies:
                        dependencies.extend(frag.dependencies)
                    break

        # SP-110-003: Also check if collection_expr itself is a SELECT statement
        is_select_statement = collection_expr and collection_expr.strip().upper().startswith("SELECT")

        try:
            if not collection_expr:
                raise ValueError("anyTrue() requires a collection expression")

            # SP-110-002: If the collection comes from select(), it's already in 'result' column
            # as a JSON array. We need to enumerate it with json_each.
            # SP-110-003: Also check if collection_expr is a SELECT statement directly
            if has_select_result or is_select_statement:
                # SP-110-003: Use <<SOURCE_TABLE>> marker which CTE builder will substitute
                any_true_sql = f"COALESCE((SELECT BOOL_OR(CAST(value AS BOOLEAN)) FROM json_each(<<SOURCE_TABLE>>.result)), FALSE)"
            else:
                base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
                normalized_expr = self._normalize_collection_expression(base_expr)
                any_true_sql = self.dialect.generate_any_true(normalized_expr)

            return SQLFragment(
                expression=any_true_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "anyTrue", "result_type": "boolean", "skip_group_by": True}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_all_false(self, node: FunctionCallNode) -> SQLFragment:
        """Translate allFalse() function to SQL using BOOL_AND(NOT value).

        FHIRPath Specification: Section 5.3.7
        Returns TRUE if all elements are FALSE. Empty collections return TRUE.

        SP-110-002: Handle both JSON arrays (via json_each) and UNNESTed collections
        (via direct aggregation on rows). When collection_expr is a simple column
        reference that's already a JSON array from a previous CTE, we need to
        enumerate it first.
        """
        logger.debug("Translating allFalse() function")

        if node.arguments:
            raise ValueError(f"allFalse() takes no arguments, got {len(node.arguments)}")

        (collection_expr, dependencies, _, snapshot, _, target_path) = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        # SP-110-002: Check if there's a pre-built SELECT from select()
        # In this case, the result column is already a JSON array
        has_select_result = any(
            f.metadata.get("function") == "select" for f in self.fragments
        )

        # SP-110-010: If there's a select result, use its source_table for dependencies
        if has_select_result and self.fragments:
            for frag in reversed(self.fragments):
                if frag.metadata.get("function") == "select":
                    source_table = frag.source_table
                    if frag.dependencies:
                        dependencies.extend(frag.dependencies)
                    break

        # SP-110-003: Also check if collection_expr itself is a SELECT statement
        is_select_statement = collection_expr and collection_expr.strip().upper().startswith("SELECT")

        try:
            if not collection_expr:
                raise ValueError("allFalse() requires a collection expression")

            # SP-110-002: If the collection comes from select(), it's already in 'result' column
            # as a JSON array. We need to enumerate it with json_each.
            # SP-110-003: Also check if collection_expr is a SELECT statement directly
            if has_select_result or is_select_statement:
                # SP-110-003: Use <<SOURCE_TABLE>> marker which CTE builder will substitute
                # Use centralized FHIRPath truthiness rules via dialect
                truthiness = self.dialect.generate_truthiness_type_check("value", "elem")
                all_false_sql = f"COALESCE((SELECT BOOL_AND(NOT {truthiness}) FROM json_each(<<SOURCE_TABLE>>.result)), TRUE)"
            else:
                base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
                normalized_expr = self._normalize_collection_expression(base_expr)
                all_false_sql = self.dialect.generate_all_false(normalized_expr)

            return SQLFragment(
                expression=all_false_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "allFalse", "result_type": "boolean", "skip_group_by": True}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_any_false(self, node: FunctionCallNode) -> SQLFragment:
        """Translate anyFalse() function to SQL using BOOL_OR(NOT value).

        FHIRPath Specification: Section 5.3.8
        Returns TRUE if any element is FALSE. Empty collections return FALSE.

        SP-110-002: Handle both JSON arrays (via json_each) and UNNESTed collections
        (via direct aggregation on rows). When collection_expr is a simple column
        reference that's already a JSON array from a previous CTE, we need to
        enumerate it first.
        """
        logger.debug("Translating anyFalse() function")

        if node.arguments:
            raise ValueError(f"anyFalse() takes no arguments, got {len(node.arguments)}")

        (collection_expr, dependencies, _, snapshot, _, target_path) = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        # SP-110-002: Check if there's a pre-built SELECT from select()
        # In this case, the result column is already a JSON array
        has_select_result = any(
            f.metadata.get("function") == "select" for f in self.fragments
        )

        # SP-110-010: If there's a select result, use its source_table for dependencies
        if has_select_result and self.fragments:
            for frag in reversed(self.fragments):
                if frag.metadata.get("function") == "select":
                    source_table = frag.source_table
                    if frag.dependencies:
                        dependencies.extend(frag.dependencies)
                    break

        # SP-110-003: Also check if collection_expr itself is a SELECT statement
        is_select_statement = collection_expr and collection_expr.strip().upper().startswith("SELECT")

        try:
            if not collection_expr:
                raise ValueError("anyFalse() requires a collection expression")

            # SP-110-002: If the collection comes from select(), it's already in 'result' column
            # as a JSON array. We need to enumerate it with json_each.
            # SP-110-003: Also check if collection_expr is a SELECT statement directly
            if has_select_result or is_select_statement:
                # SP-110-003: Use <<SOURCE_TABLE>> marker which CTE builder will substitute
                # Use centralized FHIRPath truthiness rules via dialect
                truthiness = self.dialect.generate_truthiness_type_check("value", "elem")
                any_false_sql = f"COALESCE((SELECT BOOL_OR(NOT {truthiness}) FROM json_each(<<SOURCE_TABLE>>.result)), FALSE)"
            else:
                base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
                normalized_expr = self._normalize_collection_expression(base_expr)
                any_false_sql = self.dialect.generate_any_false(normalized_expr)

            return SQLFragment(
                expression=any_false_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "anyFalse", "result_type": "boolean", "skip_group_by": True}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_aggregate(self, node: FunctionCallNode) -> SQLFragment:
        """Translate aggregate() function to SQL with $this and $total lambda variables.

        The aggregate() function performs a custom aggregation on a collection by iteratively
        applying an aggregator expression. The $this variable is bound to the current element,
        and $total is bound to the accumulated value from previous iterations.

        FHIRPath Specification:
            aggregate(aggregator : expression [, init : value]) : value
            - Iterates through collection applying aggregator expression
            - $this: current element being processed
            - $total: accumulated value from previous iterations
            - init: optional initial value (defaults to empty/0)

        Implementation Strategy:
            Uses RECURSIVE CTE to properly implement iterative accumulation.
            The base case initializes with the first element + init value.
            The recursive case joins each subsequent element with the accumulated total.

        Args:
            node: FunctionCallNode representing aggregate() function call

        Returns:
            SQLFragment with aggregation SQL

        Raises:
            ValueError: If aggregate() has invalid arguments

        Example:
            Input: (1|2|3|4).aggregate($total + $this, 0)
            - Starts with init=0
            - Iteration 1: $total=0, $this=1 → result=1
            - Iteration 2: $total=1, $this=2 → result=3
            - Iteration 3: $total=3, $this=3 → result=6
            - Iteration 4: $total=6, $this=4 → result=10
            - Final result: 10
        """
        logger.debug(f"Translating aggregate() function with {len(node.arguments)} arguments")

        # Validate arguments: aggregate(aggregator) or aggregate(aggregator, init)
        if len(node.arguments) not in [1, 2]:
            raise ValueError(
                f"aggregate() function requires 1 or 2 arguments (aggregator [, init]), "
                f"got {len(node.arguments)}"
            )

        # SP-022-015: Use _resolve_function_target() to properly resolve the input collection
        # This handles all expression types including union expressions like (1|2|3)
        collection_expr, dependencies, literal_value, snapshot, target_ast, target_path = self._resolve_function_target(node)
        old_table = snapshot["current_table"]

        logger.debug(f"Collection expression for aggregate(): {collection_expr}")

        # Generate unique aliases for CTEs and columns
        cte_counter = self.context.cte_counter
        element_alias = f"agg_elem_{cte_counter}"
        index_alias = f"{element_alias}_idx"
        enum_cte = f"agg_enum_{cte_counter}"
        recursive_cte = f"agg_recursive_{cte_counter}"

        self.context.cte_counter += 1

        # Get initial value if provided (second argument)
        # SP-024-002: Track whether init was provided to handle first iteration correctly
        # When init is not provided, the first iteration should use just the first element
        # (not NULL + first element, which would be NULL)
        init_value = None  # No init provided by default
        init_provided = len(node.arguments) == 2
        if init_provided:
            # Translate the init value expression
            init_fragment = self.visit(node.arguments[1])
            init_value = init_fragment.expression

        # SP-022-015: Build the array expression for enumeration
        # For literal collections, wrap them in a JSON array
        # For path expressions, extract from the resolved collection
        # For other expressions (unions, etc.), normalize to JSON array format
        if literal_value is not None:
            # Handle literal values (e.g., empty collection {})
            if literal_value == [] or literal_value is None:
                # Empty collection - return init value directly (or 0 if no init provided)
                return SQLFragment(
                    expression=init_value if init_provided else '0',
                    source_table=old_table,
                    requires_unnest=False,
                    is_aggregate=True,
                    dependencies=dependencies
                )
            # Single literal or list
            if isinstance(literal_value, (list, tuple)):
                array_expr = self.dialect.wrap_json_array(str(list(literal_value)))
            else:
                array_expr = self.dialect.wrap_json_array(f"[{literal_value}]")
        elif target_path:
            # Path expression - use _extract_collection_source pattern
            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            array_expr = self._normalize_collection_expression(base_expr)
        else:
            # Non-path expression (union, etc.) - normalize the collection expression
            array_expr = self._normalize_collection_expression(collection_expr)

        enumerate_sql = self.dialect.enumerate_json_array(array_expr, element_alias, index_alias)

        try:
            # SP-022-016: Save fragment list before translating aggregator expressions
            # The aggregator expression (e.g., iif($total.empty(), ...)) may contain
            # subexpressions that would normally add intermediate fragments to the chain.
            # However, these expressions use variable bindings ($this, $total) that are
            # only valid inside the recursive CTE scope. We need to prevent these
            # intermediate fragments from being added to the main fragment list, since
            # they would become separate CTEs that reference the CTE alias 'a' outside
            # its scope (causing "Referenced table 'a' not found" errors).
            saved_fragments = self.fragments.copy()

            # Translate aggregator expression for BASE CASE (first element)
            # In base case: $this = first element, $total = init_value
            # SP-024-002: When no init is provided, $total is NULL (empty) per FHIRPath spec
            # Use COALESCE to handle NULL $total in the base case aggregator expression
            # This allows expressions like $total + $this to work correctly when $total is NULL
            # by treating NULL as the identity value (0 for addition, 1 for multiplication, etc.)
            # Note: Cast element from JSON to DOUBLE for arithmetic operations
            self.context.current_table = element_alias
            self.context.parent_path.clear()

            element_cast = self.dialect.cast_to_double(element_alias)
            base_init = init_value if init_provided else "NULL"

            with self._variable_scope({
                "$this": VariableBinding(
                    expression=element_cast,
                    source_table=element_alias
                ),
                "$total": VariableBinding(
                    expression=base_init,
                    source_table=element_alias
                )
            }):
                base_aggregator_fragment = self.visit(node.arguments[0])

            # SP-024-002: Wrap base aggregator with COALESCE when no init provided
            # This ensures NULL + value = value (identity for addition)
            if not init_provided:
                base_aggregator_expr = f"COALESCE({base_aggregator_fragment.expression}, {element_cast})"
            else:
                base_aggregator_expr = base_aggregator_fragment.expression

            # Translate aggregator expression for RECURSIVE CASE
            # In recursive case: $this = current element, $total = previous accumulated value
            recursive_element_cast = self.dialect.cast_to_double(f"e.{element_alias}")

            with self._variable_scope({
                "$this": VariableBinding(
                    expression=recursive_element_cast,
                    source_table="e"
                ),
                "$total": VariableBinding(
                    expression="a.total",
                    source_table="a"
                )
            }):
                recursive_aggregator_fragment = self.visit(node.arguments[0])

            # SP-022-016: Restore original fragments list, discarding any intermediate
            # fragments added during aggregator expression translation. The final
            # aggregator SQL is embedded directly in the recursive CTE, not as separate CTEs.
            self.fragments = saved_fragments

            logger.debug(f"Base aggregator expression SQL: {base_aggregator_fragment.expression}")
            logger.debug(f"Recursive aggregator expression SQL: {recursive_aggregator_fragment.expression}")

            # Build RECURSIVE CTE SQL
            # This properly implements aggregate without circular references
            sql = f"""(
    WITH RECURSIVE {enum_cte} AS (
        {enumerate_sql}
    ),
    {recursive_cte} AS (
        -- Base case: first element with init value
        SELECT
            {index_alias},
            {element_alias},
            {base_aggregator_expr} as total
        FROM {enum_cte}
        WHERE {index_alias} = (SELECT MIN({index_alias}) FROM {enum_cte})

        UNION ALL

        -- Recursive case: accumulate with previous total
        SELECT
            e.{index_alias},
            e.{element_alias},
            {recursive_aggregator_fragment.expression} as total
        FROM {enum_cte} e
        JOIN {recursive_cte} a ON e.{index_alias} = a.{index_alias} + 1
    )
    SELECT COALESCE(
        (SELECT total FROM {recursive_cte} ORDER BY {index_alias} DESC LIMIT 1),
        {init_value if init_provided else '0'}
    ) as result
)"""

            logger.debug(f"Complete aggregate() SQL generated with RECURSIVE CTE")

            # Combine dependencies
            all_dependencies = list(dependencies)
            if hasattr(base_aggregator_fragment, 'dependencies'):
                all_dependencies.extend(base_aggregator_fragment.dependencies)

            return SQLFragment(
                expression=sql,
                source_table=old_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(all_dependencies))
            )
        finally:
            # SP-022-015: Properly restore context using snapshot
            self._restore_context(snapshot)

    def _translate_today(self, node: FunctionCallNode) -> SQLFragment:
        """Translate today() function to SQL.

        Returns current date without time component (day precision only).
        FHIRPath spec: Returns system date at day precision.

        Args:
            node: FunctionCallNode representing today() call

        Returns:
            SQLFragment containing database-specific current date SQL

        Raises:
            FHIRPathValidationError: If today() is called with arguments

        Example:
            FHIRPath: today()
            SQL (DuckDB): current_date
            SQL (PostgreSQL): CURRENT_DATE
        """
        logger.debug("Translating today() function")

        # Verify no arguments (today() takes no parameters)
        if node.arguments:
            raise FHIRPathValidationError(
                f"today() function takes no arguments, got {len(node.arguments)}"
            )

        # Get database-specific current date SQL
        date_sql = self.dialect.generate_current_date()

        logger.debug(f"Generated today() SQL: {date_sql}")

        return SQLFragment(
            expression=date_sql,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            metadata={
                'function': 'today',
                'fhir_type': 'Date',
                'returns_scalar': True,
                'temporal_precision': 'day'
            }
        )

    def _translate_now(self, node: FunctionCallNode) -> SQLFragment:
        """Translate now() function to SQL.

        Returns current date and time with full precision including timezone.
        FHIRPath spec: Returns system datetime at full precision.

        Args:
            node: FunctionCallNode representing now() call

        Returns:
            SQLFragment containing database-specific current timestamp SQL

        Raises:
            FHIRPathValidationError: If now() is called with arguments

        Example:
            FHIRPath: now()
            SQL (DuckDB): now()
            SQL (PostgreSQL): CURRENT_TIMESTAMP
        """
        logger.debug("Translating now() function")

        # Verify no arguments (now() takes no parameters)
        if node.arguments:
            raise FHIRPathValidationError(
                f"now() function takes no arguments, got {len(node.arguments)}"
            )

        # Get database-specific current timestamp SQL
        timestamp_sql = self.dialect.generate_current_timestamp()

        logger.debug(f"Generated now() SQL: {timestamp_sql}")

        return SQLFragment(
            expression=timestamp_sql,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            metadata={
                'function': 'now',
                'fhir_type': 'DateTime',
                'returns_scalar': True,
                'temporal_precision': 'full',
                'has_timezone': True
            }
        )

    def _translate_timeofday(self, node: FunctionCallNode) -> SQLFragment:
        """Translate timeOfDay() function to SQL.

        Returns current time without date component.
        FHIRPath spec: Returns system time at millisecond precision.

        Args:
            node: FunctionCallNode representing timeOfDay() call

        Returns:
            SQLFragment containing database-specific current time SQL

        Raises:
            FHIRPathValidationError: If timeOfDay() is called with arguments

        Example:
            FHIRPath: timeOfDay()
            SQL (DuckDB): current_time
            SQL (PostgreSQL): CURRENT_TIME
        """
        logger.debug("Translating timeOfDay() function")

        # Verify no arguments (timeOfDay() takes no parameters)
        if node.arguments:
            raise FHIRPathValidationError(
                f"timeOfDay() function takes no arguments, got {len(node.arguments)}"
            )

        # Get database-specific current time SQL
        time_sql = self.dialect.generate_current_time()

        logger.debug(f"Generated timeOfDay() SQL: {time_sql}")

        return SQLFragment(
            expression=time_sql,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            metadata={
                'function': 'timeOfDay',
                'fhir_type': 'Time',
                'returns_scalar': True,
                'temporal_precision': 'millisecond'
            }
        )

    def _translate_encode(self, node: FunctionCallNode) -> SQLFragment:
        """Translate encode() function to SQL for encoding strings.

        FHIRPath: string.encode(encoding)
        SQL: Database-specific encode function (base64, hex, urlbase64)

        The encode() function encodes a string using the specified encoding.

        Args:
            node: FunctionCallNode representing encode() function call

        Returns:
            SQLFragment containing the encoding SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            'test'.encode('base64') → 'dGVzdA=='
            'test'.encode('hex') → '74657374'
        """
        logger.debug(f"Translating encode() function")

        # Validate arguments - encode() takes exactly 1 argument (encoding type)
        if len(node.arguments) != 1:
            raise ValueError(
                f"encode() function requires exactly 1 argument (encoding type: base64, hex, urlbase64), "
                f"got {len(node.arguments)}"
            )

        # Get the target string expression
        string_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        dependencies: List[str] = []

        if node.target is not None:
            snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            string_expr = target_fragment.expression
            source_table = target_fragment.source_table
            requires_unnest = getattr(target_fragment, "requires_unnest", False)
            is_aggregate = getattr(target_fragment, "is_aggregate", False)
            if hasattr(target_fragment, "dependencies"):
                dependencies.extend(target_fragment.dependencies)
            self._restore_context(snapshot)
        elif self.fragments:
            string_expr = self.fragments[-1].expression
            source_table = self.fragments[-1].source_table
            requires_unnest = getattr(self.fragments[-1], "requires_unnest", False)
            is_aggregate = getattr(self.fragments[-1], "is_aggregate", False)
            if hasattr(self.fragments[-1], "dependencies"):
                dependencies.extend(self.fragments[-1].dependencies)
            self.fragments.pop()
        else:
            raise ValueError("encode() requires a target string expression")

        # Get the encoding type argument
        encoding_arg = node.arguments[0]

        # Extract encoding type from various node types (LiteralNode or EnhancedASTNode)
        encoding_type = None
        if isinstance(encoding_arg, LiteralNode) and isinstance(encoding_arg.value, str):
            encoding_type = encoding_arg.value
        elif hasattr(encoding_arg, 'text'):
            # EnhancedASTNode - extract from text attribute
            text = encoding_arg.text.strip()
            # Remove surrounding quotes
            if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
                encoding_type = text[1:-1]
            else:
                encoding_type = text

        if not encoding_type:
            raise ValueError("encode() encoding type must be a string literal")

        encoding_type = encoding_type.lower()
        if encoding_type not in ("base64", "hex", "urlbase64"):
            raise ValueError(f"encode() unsupported encoding type: {encoding_type}. Supported: base64, hex, urlbase64")

        # Generate encoding SQL based on encoding type
        if encoding_type == "base64":
            encode_sql = self.dialect.generate_base64_encode(string_expr)
        elif encoding_type == "hex":
            encode_sql = self.dialect.generate_hex_encode(string_expr)
        else:  # urlbase64
            encode_sql = self.dialect.generate_urlbase64_encode(string_expr)

        logger.debug(f"Generated encode() SQL: {encode_sql}")

        return SQLFragment(
            expression=encode_sql,
            source_table=source_table or self.context.current_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata={"function": "encode", "encoding": encoding_type}
        )

    def _translate_decode(self, node: FunctionCallNode) -> SQLFragment:
        """Translate decode() function to SQL for decoding strings.

        FHIRPath: string.decode(encoding)
        SQL: Database-specific decode function (base64, hex, urlbase64)

        The decode() function decodes a string using the specified encoding.

        Args:
            node: FunctionCallNode representing decode() function call

        Returns:
            SQLFragment containing the decoding SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            'dGVzdA=='.decode('base64') → 'test'
            '74657374'.decode('hex') → 'test'
        """
        logger.debug(f"Translating decode() function")

        # Validate arguments - decode() takes exactly 1 argument (encoding type)
        if len(node.arguments) != 1:
            raise ValueError(
                f"decode() function requires exactly 1 argument (encoding type: base64, hex, urlbase64), "
                f"got {len(node.arguments)}"
            )

        # Get the target string expression
        string_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        dependencies: List[str] = []

        if node.target is not None:
            snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            string_expr = target_fragment.expression
            source_table = target_fragment.source_table
            requires_unnest = getattr(target_fragment, "requires_unnest", False)
            is_aggregate = getattr(target_fragment, "is_aggregate", False)
            if hasattr(target_fragment, "dependencies"):
                dependencies.extend(target_fragment.dependencies)
            self._restore_context(snapshot)
        elif self.fragments:
            string_expr = self.fragments[-1].expression
            source_table = self.fragments[-1].source_table
            requires_unnest = getattr(self.fragments[-1], "requires_unnest", False)
            is_aggregate = getattr(self.fragments[-1], "is_aggregate", False)
            if hasattr(self.fragments[-1], "dependencies"):
                dependencies.extend(self.fragments[-1].dependencies)
            self.fragments.pop()
        else:
            raise ValueError("decode() requires a target string expression")

        # Get the encoding type argument
        encoding_arg = node.arguments[0]

        # Extract encoding type from various node types (LiteralNode or EnhancedASTNode)
        encoding_type = None
        if isinstance(encoding_arg, LiteralNode) and isinstance(encoding_arg.value, str):
            encoding_type = encoding_arg.value
        elif hasattr(encoding_arg, 'text'):
            # EnhancedASTNode - extract from text attribute
            text = encoding_arg.text.strip()
            # Remove surrounding quotes
            if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
                encoding_type = text[1:-1]
            else:
                encoding_type = text

        if not encoding_type:
            raise ValueError("decode() encoding type must be a string literal")

        encoding_type = encoding_type.lower()
        if encoding_type not in ("base64", "hex", "urlbase64"):
            raise ValueError(f"decode() unsupported encoding type: {encoding_type}. Supported: base64, hex, urlbase64")

        # Generate decoding SQL based on encoding type
        if encoding_type == "base64":
            decode_sql = self.dialect.generate_base64_decode(string_expr)
        elif encoding_type == "hex":
            decode_sql = self.dialect.generate_hex_decode(string_expr)
        else:  # urlbase64
            decode_sql = self.dialect.generate_urlbase64_decode(string_expr)

        logger.debug(f"Generated decode() SQL: {decode_sql}")

        return SQLFragment(
            expression=decode_sql,
            source_table=source_table or self.context.current_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata={"function": "decode", "encoding": encoding_type}
        )

    def _translate_escape(self, node: FunctionCallNode) -> SQLFragment:
        """Translate escape() function to SQL for escaping strings.

        FHIRPath: string.escape(format)
        SQL: Database-specific escape function (html, json)

        The escape() function escapes special characters in a string.

        Args:
            node: FunctionCallNode representing escape() function call

        Returns:
            SQLFragment containing the escape SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            '"test"'.escape('html') → '&quot;test&quot;'
            '"test"'.escape('json') → '\\"test\\"'
        """
        logger.debug(f"Translating escape() function")

        # Validate arguments - escape() takes exactly 1 argument (format type)
        if len(node.arguments) != 1:
            raise ValueError(
                f"escape() function requires exactly 1 argument (format type: html, json), "
                f"got {len(node.arguments)}"
            )

        # Get the target string expression
        string_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        dependencies: List[str] = []

        if node.target is not None:
            snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            string_expr = target_fragment.expression
            source_table = target_fragment.source_table
            requires_unnest = getattr(target_fragment, "requires_unnest", False)
            is_aggregate = getattr(target_fragment, "is_aggregate", False)
            if hasattr(target_fragment, "dependencies"):
                dependencies.extend(target_fragment.dependencies)
            self._restore_context(snapshot)
        elif self.fragments:
            string_expr = self.fragments[-1].expression
            source_table = self.fragments[-1].source_table
            requires_unnest = getattr(self.fragments[-1], "requires_unnest", False)
            is_aggregate = getattr(self.fragments[-1], "is_aggregate", False)
            if hasattr(self.fragments[-1], "dependencies"):
                dependencies.extend(self.fragments[-1].dependencies)
            self.fragments.pop()
        else:
            raise ValueError("escape() requires a target string expression")

        # Get the format type argument
        format_arg = node.arguments[0]

        # Extract format type from various node types (LiteralNode or EnhancedASTNode)
        format_type = None
        if isinstance(format_arg, LiteralNode) and isinstance(format_arg.value, str):
            format_type = format_arg.value
        elif hasattr(format_arg, 'text'):
            # EnhancedASTNode - extract from text attribute
            text = format_arg.text.strip()
            # Remove surrounding quotes
            if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
                format_type = text[1:-1]
            else:
                format_type = text

        if not format_type:
            raise ValueError("escape() format type must be a string literal")

        format_type = format_type.lower()
        if format_type not in ("html", "json"):
            raise ValueError(f"escape() unsupported format type: {format_type}. Supported: html, json")

        # Generate escape SQL based on format type
        if format_type == "html":
            escape_sql = self.dialect.generate_html_escape(string_expr)
        else:  # json
            escape_sql = self.dialect.generate_json_escape(string_expr)

        logger.debug(f"Generated escape() SQL: {escape_sql}")

        return SQLFragment(
            expression=escape_sql,
            source_table=source_table or self.context.current_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata={"function": "escape", "format": format_type}
        )

    def _translate_unescape(self, node: FunctionCallNode) -> SQLFragment:
        """Translate unescape() function to SQL for unescaping strings.

        FHIRPath: string.unescape(format)
        SQL: Database-specific unescape function (html, json)

        The unescape() function unescapes special characters in a string.

        Args:
            node: FunctionCallNode representing unescape() function call

        Returns:
            SQLFragment containing the unescape SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            '&quot;test&quot;'.unescape('html') → '"test"'
            '\\"test\\"'.unescape('json') → '"test"'
        """
        logger.debug(f"Translating unescape() function")

        # Validate arguments - unescape() takes exactly 1 argument (format type)
        if len(node.arguments) != 1:
            raise ValueError(
                f"unescape() function requires exactly 1 argument (format type: html, json), "
                f"got {len(node.arguments)}"
            )

        # Get the target string expression
        string_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        dependencies: List[str] = []

        if node.target is not None:
            snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            string_expr = target_fragment.expression
            source_table = target_fragment.source_table
            requires_unnest = getattr(target_fragment, "requires_unnest", False)
            is_aggregate = getattr(target_fragment, "is_aggregate", False)
            if hasattr(target_fragment, "dependencies"):
                dependencies.extend(target_fragment.dependencies)
            self._restore_context(snapshot)
        elif self.fragments:
            string_expr = self.fragments[-1].expression
            source_table = self.fragments[-1].source_table
            requires_unnest = getattr(self.fragments[-1], "requires_unnest", False)
            is_aggregate = getattr(self.fragments[-1], "is_aggregate", False)
            if hasattr(self.fragments[-1], "dependencies"):
                dependencies.extend(self.fragments[-1].dependencies)
            self.fragments.pop()
        else:
            raise ValueError("unescape() requires a target string expression")

        # Get the format type argument
        format_arg = node.arguments[0]

        # Extract format type from various node types (LiteralNode or EnhancedASTNode)
        format_type = None
        if isinstance(format_arg, LiteralNode) and isinstance(format_arg.value, str):
            format_type = format_arg.value
        elif hasattr(format_arg, 'text'):
            # EnhancedASTNode - extract from text attribute
            text = format_arg.text.strip()
            # Remove surrounding quotes
            if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
                format_type = text[1:-1]
            else:
                format_type = text

        if not format_type:
            raise ValueError("unescape() format type must be a string literal")

        format_type = format_type.lower()
        if format_type not in ("html", "json"):
            raise ValueError(f"unescape() unsupported format type: {format_type}. Supported: html, json")

        # Generate unescape SQL based on format type
        if format_type == "html":
            unescape_sql = self.dialect.generate_html_unescape(string_expr)
        else:  # json
            unescape_sql = self.dialect.generate_json_unescape(string_expr)

        logger.debug(f"Generated unescape() SQL: {unescape_sql}")

        return SQLFragment(
            expression=unescape_sql,
            source_table=source_table or self.context.current_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata={"function": "unescape", "format": format_type}
        )

    def _translate_sort(self, node: FunctionCallNode) -> SQLFragment:
        """Translate sort() function to SQL for sorting collections.

        FHIRPath: collection.sort([criteria])
        SQL: Database-specific array sort function

        The sort() function sorts a collection. Optional criteria can specify
        the sort key and direction (ascending/descending).

        Args:
            node: FunctionCallNode representing sort() function call

        Returns:
            SQLFragment containing the sort SQL

        Raises:
            ValueError: If function has invalid number of arguments

        Example:
            (3 | 2 | 1).sort() → (1 | 2 | 3)
            (1 | 2 | 3).sort(-$this) → (3 | 2 | 1)
        """
        logger.debug(f"Translating sort() function")

        # Get the target collection expression
        collection_expr: Optional[str] = None
        source_table: Optional[str] = None
        requires_unnest = False
        is_aggregate = False
        dependencies: List[str] = []
        element_type: Optional[str] = None

        if node.target is not None:
            snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            collection_expr = target_fragment.expression
            source_table = target_fragment.source_table
            requires_unnest = getattr(target_fragment, "requires_unnest", False)
            is_aggregate = getattr(target_fragment, "is_aggregate", False)
            if hasattr(target_fragment, "dependencies"):
                dependencies.extend(target_fragment.dependencies)
            # SP-110-XXX: Extract element_type for type-aware sorting
            if hasattr(target_fragment, "metadata") and target_fragment.metadata:
                element_type = target_fragment.metadata.get("element_type")
            self._restore_context(snapshot)
        elif self.fragments:
            collection_expr = self.fragments[-1].expression
            source_table = self.fragments[-1].source_table
            requires_unnest = getattr(self.fragments[-1], "requires_unnest", False)
            is_aggregate = getattr(self.fragments[-1], "is_aggregate", False)
            if hasattr(self.fragments[-1], "dependencies"):
                dependencies.extend(self.fragments[-1].dependencies)
            # SP-110-XXX: Extract element_type for type-aware sorting
            if hasattr(self.fragments[-1], "metadata") and self.fragments[-1].metadata:
                element_type = self.fragments[-1].metadata.get("element_type")
            self.fragments.pop()
        else:
            raise ValueError("sort() requires a target collection expression")

        # Determine sort direction based on criteria
        # Default is ascending (no criteria or $this)
        # Criteria with -$this indicates descending
        ascending = True

        if len(node.arguments) > 0:
            criteria_arg = node.arguments[0]
            # Check if criteria is a unary minus expression (descending sort)
            # The AST should represent -$this as a unary operation
            # For now, we'll check if the argument expression contains a minus
            # This is a simplified check - in production we'd properly inspect the AST
            if hasattr(criteria_arg, 'operator') and criteria_arg.operator == '-':
                ascending = False

        # Generate sort SQL with element type
        sort_sql = self.dialect.generate_array_sort(collection_expr, ascending=ascending, element_type=element_type)

        logger.debug(f"Generated sort() SQL: {sort_sql}")

        # SP-110 FIX: sort() returns a complete SQL expression that doesn't require additional UNNESTing
        # The generate_array_sort() method returns a self-contained array expression
        # Even if the target collection required UNNEST, the sorted result is a complete array
        return SQLFragment(
            expression=sort_sql,
            source_table=source_table or self.context.current_table,
            requires_unnest=False,  # sort() returns a complete array expression, not requiring UNNEST
            is_aggregate=is_aggregate,
            dependencies=list(dict.fromkeys(dependencies)),
            metadata={"function": "sort", "ascending": ascending, "element_type": element_type}
        )

    def _translate_descendants(self, node: FunctionCallNode) -> SQLFragment:
        """Translate descendants() function to SQL for hierarchical traversal.

        FHIRPath: resource.descendants()
        SQL: Database-specific recursive CTE for JSON tree traversal

        The descendants() function returns all descendant elements of the current
        node in a hierarchical structure, traversing recursively through all
        nested objects and arrays.

        Args:
            node: FunctionCallNode representing descendants() function call

        Returns:
            SQLFragment containing the descendants SQL

        Raises:
            ValueError: If function has any arguments (takes none)

        Example:
            Questionnaire.descendants() → All nested elements
            Patient.name.descendants() → All nested elements within all names
        """
        logger.debug(f"Translating descendants() function")

        # Validate arguments - descendants() takes no arguments
        if len(node.arguments) != 0:
            raise ValueError(
                f"descendants() function requires no arguments, got {len(node.arguments)}"
            )

        # Get the current resource/element expression
        current_expr = self.context.current_table
        source_table = self.context.current_table

        # Get the current JSON path (if any)
        current_path = self.context.get_json_path()

        if current_path and current_path != "$":
            # We're navigating within a resource, extract descendants from the current path
            parent_json = self.dialect.extract_json_field(
                column=source_table,
                path=current_path
            )
            descendants_sql = self.dialect.generate_json_descendants(parent_json)
        else:
            # We're at the resource level, get all descendants from the resource JSON
            descendants_sql = self.dialect.generate_json_descendants(current_expr)

        logger.debug(f"Generated descendants() SQL: {descendants_sql}")

        # descendants() returns a complete SQL expression (recursive CTE subquery) that produces a JSON array
        # Unlike simple array path expressions that need UNNEST, this is a scalar array result
        # Similar to repeat() - requires_unnest=False because the expression is self-contained
        return SQLFragment(
            expression=descendants_sql,
            source_table=source_table,
            requires_unnest=False,  # Returns a scalar array result, not requiring UNNEST
            is_aggregate=False,
            dependencies=[],
            metadata={
                "function": "descendants",
                "result_type": "collection",
            }
        )
