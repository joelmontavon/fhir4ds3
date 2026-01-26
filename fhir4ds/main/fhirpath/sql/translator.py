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
from ..exceptions import FHIRPathTranslationError, FHIRPathValidationError, FHIRPathEvaluationError
from ..types.type_registry import TypeRegistry, get_type_registry
from ..types import (
    get_element_type_resolver,
    get_temporal_parser,
    ParsedTemporal
)
from ..types.fhir_types import resolve_polymorphic_property, is_polymorphic_property, resolve_polymorphic_field_for_type
from ..types.type_discriminators import get_type_discriminator
from ..types.structure_loader import StructureDefinitionLoader
from pathlib import Path
from .fragments import SQLFragment
from .context import TranslationContext, VariableBinding
from .cte import CTEManager
from ...dialects.base import DatabaseDialect


logger = logging.getLogger(__name__)


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

        logger.debug(f"Starting translation of AST: {ast_root.node_type}")

        # Visit root node to start translation
        # The visit may accumulate multiple fragments for expression chains
        fragment = self.visit(ast_root)

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

    def _resolve_canonical_type(self, type_name: Any) -> str:
        """Resolve provided type name to canonical FHIR type, enforcing validation."""
        raw_value = "" if type_name is None else str(type_name).strip()
        canonical = self.type_registry.get_canonical_type_name(raw_value)

        if canonical is None:
            display_name = raw_value or str(type_name)
            valid_types = ", ".join(self.type_registry.get_all_type_names())
            raise FHIRPathTranslationError(
                f"Unknown FHIR type '{display_name}'. Valid types: {valid_types}"
            )

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

        Args:
            expression: SQL expression string

        Returns:
            True if expression is a SQL literal (integer, decimal, string, boolean)
        """
        expr = expression.strip()

        # Boolean literals
        if expr.upper() in ('TRUE', 'FALSE'):
            return True

        # String literal: starts and ends with single quotes
        if expr.startswith("'") and expr.endswith("'"):
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

    def _generate_literal_type_check(self, expression: str, target_type: str) -> str:
        """Generate SQL type check for literal values.

        SP-022-003: This method generates simplified type checks for SQL literals
        that don't involve json_type() which fails on non-JSON values in DuckDB.

        For literals, we use typeof() directly without the JSON handling branches,
        since we know the value is a native SQL type (not JSON).

        Args:
            expression: SQL literal expression (e.g., "1", "1.0", "'hello'", "TRUE")
            target_type: FHIRPath type name to check (e.g., "Integer", "Decimal", "String")

        Returns:
            SQL expression that evaluates to boolean
        """
        normalized_type = (target_type or "").lower().replace("system.", "")

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

        # Handle temporal types with regex (partial dates like @2015 are strings)
        temporal_regex = {
            'date': r'^\d{4}(-\d{2}(-\d{2})?)?$',
            'datetime': r'^\d{4}(-\d{2}(-\d{2})?)?T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$',
            'time': r'^\d{2}:\d{2}:\d{2}(\.\d+)?$',
        }
        if normalized_type in temporal_regex:
            pattern = temporal_regex[normalized_type].replace("'", "''")
            if dialect_name == 'DUCKDB':
                native_types = {'date': 'DATE', 'datetime': 'TIMESTAMP', 'time': 'TIME'}
                native_type = native_types.get(normalized_type, 'DATE')
                return (
                    f"(typeof({expression}) = '{native_type}' OR "
                    f"regexp_matches(CAST({expression} AS VARCHAR), '{pattern}'))"
                )
            else:  # PostgreSQL
                native_types = {'date': 'date', 'datetime': 'timestamp', 'time': 'time'}
                native_type = native_types.get(normalized_type, 'date')
                return (
                    f"(pg_typeof({expression})::text LIKE '{native_type}%' OR "
                    f"CAST({expression} AS VARCHAR) ~ '{pattern}')"
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

        if target_ast is None:
            # SP-022-015: Check for pending fragment result FIRST from invocation chain
            # This handles expressions like (1|2|3).aggregate() where the union result
            # is a complete expression that should take priority over pending_literal_value.
            # SP-100-002: pending_fragment_result is now a tuple (expression, parent_path, is_multi_item)
            if self.context.pending_fragment_result is not None:
                target_expression, target_path, is_multi_item_collection = self.context.pending_fragment_result
                # If the pending fragment is from a multi-item collection, this is an error for iif()
                # We need to pass this information to the caller
                # Store this in a temporary attribute for _translate_iif to check
                self._pending_target_is_multi_item = is_multi_item_collection
                # Clear both pending values after consuming (fragment result takes priority)
                self.context.pending_fragment_result = None
                self.context.pending_literal_value = None
            # SP-022-009: Check for pending literal value from invocation chain
            # This handles expressions like 1.convertsToInteger() where the literal
            # was visited in visit_generic before this function call
            elif self.context.pending_literal_value is not None:
                literal_value, target_expression = self.context.pending_literal_value
                # Clear the pending value after consuming it
                self.context.pending_literal_value = None
            else:
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
        """Evaluate toString() for literal values."""
        if value is None:
            return None
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
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
        """Evaluate toQuantity() for literal values."""
        if value is None:
            return None
        # For now, return None - Quantity conversion is complex
        # Will need full UCUM library support
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
        if isinstance(node, LiteralNode):
            # Check for empty collection marker: text is '{}' or value is {}
            return (node.text == '{}' or
                    (isinstance(node.value, str) and node.value == '{}'))
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

        # SP-100-003: Check for empty collection literal before type-based handling
        if self._is_empty_collection_literal(node):
            logger.debug("Detected empty collection literal {}")

            # Store empty collection marker in context for functions
            self.context.pending_literal_value = ("{}[]", "[]")

            # Return SQL fragment marked as empty collection
            # The actual SQL expression depends on context (handled by consumers)
            return SQLFragment(
                expression="NULL",  # Default - consumers will override
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                metadata={
                    "literal_type": "empty_collection",
                    "is_literal": True,
                    "is_empty_collection": True
                }
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
            # Direct string conversion for decimals (preserves precision)
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
        return SQLFragment(
            expression=sql_expr,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            metadata={"literal_type": node.literal_type, "is_literal": True}
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

            final_fragment = SQLFragment(
                expression=sql_expr,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
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
                array_column = self.dialect.extract_json_object(
                    column=actual_element_column,
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

            fragment = SQLFragment(
                expression=sql_expr,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                metadata={"from_element_column": True}
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

        if polymorphic_idx is not None:
            poly_prop = normalized_components[polymorphic_idx]
            remaining = normalized_components[polymorphic_idx + 1:]
            variants = resolve_polymorphic_property(poly_prop) or []

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

                return SQLFragment(
                    expression=sql_expr,
                    source_table=self.context.current_table,
                    requires_unnest=False,
                    is_aggregate=False,
                    metadata={"is_json_string": True}
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

        # Return SQL fragment with JSON extraction expression
        # This is not an unnest operation and not an aggregate
        # Mark as JSON-extracted string for type-aware comparison casting
        return SQLFragment(
            expression=sql_expr,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            metadata={"is_json_string": True}
        )

    def visit_generic(self, node: Any) -> SQLFragment:
        """
        Generic visitor for AST nodes when no specific adapter matches.
        Used for container nodes like InvocationExpression that wrap chains.
        Overrides ASTVisitor.visit_generic.
        """
        logger.debug(f"Visiting generic node: {type(node).__name__}")

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
                    if not hasattr(child, 'node_type') or child.node_type not in ('function_call', 'functionCall'):
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
            return self._translate_contains(node)
        elif function_name == "startswith":
            return self._translate_startswith(node)
        elif function_name == "endswith":
            return self._translate_endswith(node)
        elif function_name == "matches":
            return self._translate_matches(node)
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
        elif function_name == "todatetime":
            return self._translate_to_datetime(node)
        elif function_name == "totime":
            return self._translate_to_time(node)
        elif function_name == "distinct":
            return self._translate_distinct(node)
        elif function_name == "isdistinct":
            return self._translate_is_distinct(node)
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
        # Type functions (temporary handlers until AST adapter is fixed in SP-007-XXX)
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
                # {} implies true -> true (empty antecedent is true)
                # Also handles {} implies (non-false expression) -> (NOT NULL) OR expr -> expr
                return right_sql
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

        return SQLFragment(
            expression=sql_expr,
            source_table=operand_fragment.source_table,
            requires_unnest=operand_fragment.requires_unnest,
            is_aggregate=operand_fragment.is_aggregate
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

        # Translate both operands
        left_fragment = self.visit(node.children[0])
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

        # Handle temporal arithmetic (e.g., date - quantity with time unit)
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
                sql_expr = self.dialect.generate_logical_combine(
                    left_fragment.expression,
                    sql_operator,
                    right_fragment.expression
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

                # SP-100-003: Handle empty collections in comparisons
                # Empty collections don't match anything in comparisons
                if left_is_empty or right_is_empty:
                    # Empty collections compared with anything return FALSE
                    # {} = 5 -> FALSE, {} = {} -> FALSE, 5 = {} -> FALSE
                    sql_expr = "FALSE"
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
            metadata = {}
            left_meta = left_fragment.metadata if isinstance(left_fragment.metadata, dict) else {}
            right_meta = right_fragment.metadata if isinstance(right_fragment.metadata, dict) else {}
            # Copy relevant metadata but exclude array-specific keys
            array_keys = {"array_column", "result_alias", "source_path", "projection_expression",
                          "from_element_column", "unnest_level"}
            for key, value in left_meta.items():
                if key not in array_keys:
                    metadata[key] = value
            for key, value in right_meta.items():
                if key not in array_keys and key not in metadata:
                    metadata[key] = value
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

        for fragment in operand_fragments:
            if fragment.source_table and fragment.source_table != "resource":
                source_table = fragment.source_table
            requires_unnest = requires_unnest or fragment.requires_unnest
            is_aggregate = is_aggregate or fragment.is_aggregate
            for dep in fragment.dependencies:
                if dep not in dependencies:
                    dependencies.append(dep)

        return SQLFragment(
            expression=union_sql,
            source_table=source_table,
            requires_unnest=requires_unnest,
            is_aggregate=is_aggregate,
            dependencies=dependencies,
            metadata={"operator": "union", "operator_text": node.text, "is_collection": True}
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
        """Normalize expression to JSON array, preserving NULL semantics."""
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

    def _generate_collection_comparison(self, left_expr: str, right_expr: str, sql_operator: str) -> str:
        """Generate SQL comparison between two collection expressions."""
        normalized_left = self._normalize_collection_expression(left_expr)
        normalized_right = self._normalize_collection_expression(right_expr)
        serialized_left = self.dialect.serialize_json_value(normalized_left)
        serialized_right = self.dialect.serialize_json_value(normalized_right)
        return f"({serialized_left} {sql_operator} {serialized_right})"

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
            # SP-022-007: For JSON values compared to string literals, extract as string
            # UNNEST produces JSON-typed values; use json_extract_string to get plain text
            return self.dialect.extract_json_string(expression, "$")
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

        # Check if either operand is a string type
        left_is_string = self._is_string_operand(left_node)
        right_is_string = self._is_string_operand(right_node)

        if left_is_string or right_is_string:
            # String equivalence: case-insensitive comparison
            # Use LOWER() on both operands, casting to string if needed
            left_lower = f"LOWER(CAST({left_expr} AS VARCHAR))"
            right_lower = f"LOWER(CAST({right_expr} AS VARCHAR))"
            comparison = f"({left_lower} {operator} {right_lower})"
        else:
            # Non-string equivalence: same as equality
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
            SELECT id, resource, json_agg(x) as result FROM ... GROUP BY id, resource

        We need to modify it to:
            SELECT id, resource, json_agg(DISTINCT x) as result FROM ... GROUP BY id, resource

        Preserves order by using ROW_NUMBER() to track first occurrence.
        """
        # Find the aggregation function call (json_agg, json_group_array, list())
        # and wrap the value to add DISTINCT while preserving order

        # Pattern 1: json_agg(value ORDER BY idx) -> use DISTINCT ON or subquery
        # Pattern 2: json_group_array(value ORDER BY idx) -> similar for DuckDB
        # Pattern 3: list(value ORDER BY idx) -> DuckDB LIST aggregate

        import re

        # For json_agg with ORDER BY, we need a subquery with DISTINCT ON
        if "json_agg(" in select_sql:
            # Extract the aggregation expression
            match = re.search(r'json_agg\(([^)]+)(\s+ORDER\s+BY\s+[^)]+)?\)', select_sql)
            if match:
                inner_expr = match.group(1).strip()
                order_clause = match.group(2) or ""

                # Create a wrapper that uses DISTINCT ON (value) ORDER BY idx
                # This preserves first occurrence order while removing duplicates
                table_alias = self._generate_internal_alias("distinct_wrapper")
                column_alias = self._generate_internal_alias("distinct_val")

                # Build the new aggregation with DISTINCT
                new_agg = f"json_agg(DISTINCT {inner_expr}{order_clause})"

                # Replace the aggregation in the SQL
                new_sql = select_sql.replace(
                    f"json_agg({inner_expr}{order_clause})",
                    new_agg
                )
                return new_sql

        # For DuckDB list() or json_group_array
        if "list(" in select_sql or "json_group_array(" in select_sql:
            # Similar approach for DuckDB
            func_name = "list(" if "list(" in select_sql else "json_group_array("
            match = re.search(re.escape(func_name) + r'([^)]+)(\s+ORDER\s+BY\s+[^)]+)?\)', select_sql)
            if match:
                inner_expr = match.group(1).strip()
                order_clause = match.group(2) or ""

                # DuckDB LIST supports DISTINCT directly
                new_agg = f"{func_name.rstrip('(')}(DISTINCT {inner_expr}{order_clause})"

                new_sql = select_sql.replace(
                    f"{func_name.rstrip('(')}({inner_expr}{order_clause})",
                    new_agg
                )
                return new_sql

        # Fallback: try to add DISTINCT to the aggregation function
        # Simple pattern: find aggregate( and add DISTINCT after it
        for agg_func in ['json_agg(', 'json_group_array(', 'list(']:
            if agg_func in select_sql:
                # Check if DISTINCT is already present
                if f'{agg_func}DISTINCT' in select_sql:
                    return select_sql  # Already has DISTINCT

                # Add DISTINCT after the function name
                new_sql = select_sql.replace(agg_func, f'{agg_func}DISTINCT ')
                return new_sql

        # If we can't modify it, return as-is and let the SQL execution handle it
        logger.warning(f"Could not add DISTINCT to SELECT statement: {select_sql[:200]}")
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

        Returns:
            SQL expression evaluating to boolean

        Example:
            subset_expr = json_extract(resource, '$.name[0]')  # Single name
            superset_expr = json_extract(resource, '$.name')    # All names
            Result: TRUE (single element is in collection)
        """
        prefix = self._generate_internal_alias("subset")
        empty_array = self.dialect.empty_json_array()

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
        # If source table is provided, use LATERAL to bring it into scope for CTE column references
        if subset_source_table:
            subset_enumeration = (
                f"SELECT * FROM {subset_source_table}, LATERAL ("
                f"{self.dialect.enumerate_json_array(safe_subset, subset_value, subset_index)}"
                f") AS {subset_enum_alias}"
            )
        else:
            subset_enumeration = self.dialect.enumerate_json_array(safe_subset, subset_value, subset_index)

        if superset_source_table:
            superset_enumeration = (
                f"SELECT * FROM {superset_source_table}, LATERAL ("
                f"{self.dialect.enumerate_json_array(safe_superset, superset_value, superset_index)}"
                f") AS {superset_enum_alias}"
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
        prefers_decimal = "decimal" in {left_type, right_type}
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

    def _translate_temporal_quantity_subtraction(
        self,
        left_fragment: SQLFragment,
        right_fragment: SQLFragment,
        left_node: FHIRPathASTNode,
        right_node: FHIRPathASTNode
    ) -> Optional[SQLFragment]:
        """Translate temporal literal minus quantity expressions to SQL."""
        temporal_type = self._detect_temporal_type(left_node)
        if temporal_type is None:
            return None

        quantity = self._parse_quantity_literal(right_node)
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

    def _parse_quantity_literal(self, node: FHIRPathASTNode) -> Optional[Tuple[Decimal, str]]:
        """Parse quantity literal expressed as <number>'unit'."""
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
        """Convert Decimal to SQL-friendly string without scientific notation."""
        normalized = amount.normalize()
        if normalized == normalized.to_integral():
            return str(normalized.to_integral())
        return format(normalized, "f").rstrip("0").rstrip(".")

    def _translate_temporal_literal_comparison_if_applicable(self, node: OperatorNode) -> Optional[SQLFragment]:
        """Translate temporal literal comparisons that require precision-aware semantics."""
        if len(node.children) != 2:
            return None

        left_info = self._extract_temporal_info(node.children[0])
        right_info = self._extract_temporal_info(node.children[1])

        if not left_info or not right_info:
            return None

        # Only apply range-based semantics when at least one operand has reduced precision
        if not (left_info.get("is_partial") or right_info.get("is_partial")):
            return None

        operator = (node.operator or "").strip()
        conditions = self._build_temporal_conditions(left_info, right_info, operator)
        if conditions is None:
            return None

        true_condition, false_condition = conditions

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
        """Extract temporal metadata from AST node if available."""
        temporal_info = getattr(node, "temporal_info", None)
        if temporal_info:
            return temporal_info

        metadata = getattr(node, "metadata", None)
        if metadata and getattr(metadata, "custom_attributes", None):
            return metadata.custom_attributes.get("temporal_info")
        return None

    def _build_temporal_conditions(
        self,
        left_info: Dict[str, Any],
        right_info: Dict[str, Any],
        operator: str
    ) -> Optional[tuple[str, str]]:
        """Build true/false SQL conditions for temporal comparisons."""
        left_range = self._temporal_range_to_sql(left_info)
        right_range = self._temporal_range_to_sql(right_info)

        if left_range is None or right_range is None:
            return None

        left_start, left_end = left_range
        right_start, right_end = right_range

        op = operator.strip()
        if op == "<":
            conditions = (
                f"({left_end} <= {right_start})",
                f"({left_start} >= {right_end})"
            )
        elif op == "<=":
            conditions = (
                f"({left_end} <= {right_start})",
                f"({left_start} > {right_end})"
            )
        elif op == ">":
            conditions = (
                f"({left_start} >= {right_end})",
                f"({left_end} <= {right_start})"
            )
        elif op == ">=":
            conditions = (
                f"({left_start} >= {right_end})",
                f"({left_end} < {right_start})"
            )
        else:
            return None

        return conditions

    def _temporal_range_to_sql(self, temporal_info: Dict[str, Any]) -> Optional[tuple[str, str]]:
        """Convert temporal range start/end into SQL literal expressions."""
        kind = temporal_info.get("kind")
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
            # Check if we have a path (counting elements in a field)
            if json_path and json_path != "$":
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

            return SQLFragment(
                expression=sql_expr,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=[],
                metadata={"function": "count", "result_type": "integer"}
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
        """Handle count() when represented as a function call node."""
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
                    is_aggregate=False
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
                dependencies=dependencies
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
        """Translate conformsTo() profile membership function."""
        if not node.arguments or len(node.arguments) != 1:
            raise ValueError("conformsTo() requires exactly one argument (profile URL)")

        profile_fragment = self.visit(node.arguments[0])
        profile_dependencies = getattr(profile_fragment, "dependencies", []) or []

        (
            resource_expr,
            dependencies,
            _,
            snapshot,
            _,
            _,
        ) = self._resolve_function_target(node)

        source_table = snapshot["current_table"]
        combined_dependencies = list(dependencies or []) + list(profile_dependencies)

        try:
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

            metadata = {"function": "conformsTo"}
            if isinstance(node.arguments[0], LiteralNode):
                metadata["profile_url"] = node.arguments[0].value

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

        # Get function target (the collection iif is called on, if any)
        (
            target_expr,
            dependencies,
            _,
            snapshot,
            target_ast,
            target_path,
        ) = self._resolve_function_target(node)

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

            # Translate criterion to SQL
            criterion_fragment = self.visit(criterion_node)
            criterion_sql = criterion_fragment.expression

            # SP-100-002-Enhanced: Handle empty collections and union expressions in criterion
            # Empty collections {} should evaluate to FALSE in boolean context
            # Union expressions like {} | true should reduce to the first non-empty value
            criterion_is_empty_collection = (
                criterion_fragment.metadata.get('literal_type') == 'empty_collection'
            )
            criterion_is_union = criterion_fragment.metadata.get('operator') == 'union'

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
            elif criterion_is_union:
                # SP-100-002-Enhanced: Union expression in criterion
                # Extract the first element from the union for boolean evaluation
                # This handles cases like: iif({} | true, true, false) -> iif(true, true, false)
                # Wrap the union expression and extract the first element
                normalized_criterion = self._normalize_collection_expression(criterion_sql)
                # Use dialect's extract_json_field with [0] to get first element
                criterion_sql = f"({self.dialect.extract_json_field(normalized_criterion, '$[0]')})"

            # Translate true-result to SQL
            true_result_fragment = self.visit(true_result_node)
            true_result_sql = true_result_fragment.expression

            # Translate false-result to SQL (or NULL if omitted)
            if false_result_node:
                false_result_fragment = self.visit(false_result_node)
                false_result_sql = false_result_fragment.expression
            else:
                false_result_sql = "NULL"

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

            # If iif is called on a collection (e.g., collection.iif(...)), validate cardinality
            # The collection must have 0 or 1 items (execution validation - testIif10)
            if target_expr and (target_ast is not None or target_path is not None or hasattr(self, '_pending_target_is_multi_item')):
                # Check if target is a multi-item literal union (e.g., 'item1' | 'item2')
                # This can be detected at translation time or from pending fragment
                is_multi_target = False
                if target_ast and self._is_multi_item_collection(target_ast):
                    is_multi_target = True
                elif hasattr(self, '_pending_target_is_multi_item') and self._pending_target_is_multi_item:
                    is_multi_target = True
                    # Clear the flag after checking
                    self._pending_target_is_multi_item = False

                if is_multi_target:
                    raise FHIRPathEvaluationError(
                        "iif() cannot be called on a collection with multiple items"
                    )

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
            'InvocationTerm',
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
            # For now, return False - Quantity conversion needs UCUM support
            # Will be enhanced in future iterations
            return False

        if target_type == "DateTime":
            if isinstance(value, str):
                stripped = value.strip()
                # SP-101-003: Support partial DateTime formats
                # Accepts: YYYY, YYYY-MM, YYYY-MM-DD, YYYYT, YYYY-MMT, YYYY-MM-DDT, YYYY-MM-DDTHH:MM:SS...
                # Pattern: Year required, month/day optional, 'T' suffix optional (with or without time)
                return bool(re.match(r'^\d{4}(-\d{2}(-\d{2})?)?T?.*$', stripped))
            return False

        if target_type == "Time":
            if isinstance(value, str):
                stripped = value.strip()
                # SP-101-003: Support hour-only format and standard time formats
                # Accepts: HH, HH:MM, HH:MM:SS, HH:MM:SS.sss
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
        """Generate SQL for convertsToInteger() checks."""
        integer_cast = self.dialect.generate_type_cast(value_expr, "Integer")
        decimal_cast = self.dialect.generate_type_cast(value_expr, "Decimal")
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        trimmed_string = self.dialect.generate_trim(string_cast)
        lowered_string = f"LOWER({trimmed_string})"

        numeric_condition = (
            f"({integer_cast} IS NOT NULL AND "
            f"({decimal_cast} IS NULL OR {decimal_cast} = {integer_cast}))"
        )
        boolean_condition = (
            f"({string_cast} IS NOT NULL AND {lowered_string} IN ('true', 'false', 't', 'f'))"
        )

        return (
            "CASE "
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

    def _build_converts_to_quantity_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToQuantity() checks."""
        # For now, always return FALSE - Quantity conversion needs UCUM support
        # Will be enhanced in future iterations
        return "FALSE"

    def _build_converts_to_datetime_expression(self, value_expr: str) -> str:
        """Generate SQL for convertsToDateTime() checks.

        SP-101-003: Use regex pattern matching instead of casting to support
        partial DateTime formats like '2015', '2015-02', '2015-02-04'.

        FHIRPath spec allows convertsToDateTime() to return true for strings that
        match the DateTime format, even if they're partial dates.
        """
        # First, try to cast as string
        string_cast = self.dialect.generate_type_cast(value_expr, "String")
        # Use regex to check if it matches a DateTime pattern
        # Pattern: YYYY(-MM(-DD(T(HH(:MM(:SS)?)?)?)?)?
        # Matches: 2015, 2015-02, 2015-02-04, 2015T, 2015-02T, 2015-02-04T, 2015-02-04T10:00:00
        datetime_pattern = r"'^[0-9]{4}(-[0-9]{2})?(-[0-9]{2})?(T([0-9]{2}(:[0-9]{2})?(:[0-9]{2})?)?)?$'"
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
        """Translate toString() function to SQL conversion."""
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
                result = self._evaluate_literal_to_string(literal_value)
                sql_expr = self._to_sql_literal(result, "string")
                return SQLFragment(
                    expression=sql_expr,
                    source_table=source_table,
                    requires_unnest=False,
                    is_aggregate=False
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
                sql_expr = self._to_sql_literal(result, "string") if result else "NULL"
                return SQLFragment(
                    expression=sql_expr,
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
            if left_is_cte_ref:
                subset_expr = left_expr
            else:
                base_expr = self._extract_collection_source(left_expr, target_path, snapshot)
                subset_expr = self._normalize_collection_expression(base_expr)

            if right_is_cte_ref:
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

            return SQLFragment(
                expression=subset_check_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "subsetOf", "result_type": "boolean"}
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
            if left_is_cte_ref:
                normalized_left = left_expr
            else:
                base_expr = self._extract_collection_source(left_expr, target_path, snapshot)
                normalized_left = self._normalize_collection_expression(base_expr)

            if right_is_cte_ref:
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

            return SQLFragment(
                expression=superset_check_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "supersetOf", "result_type": "boolean"}
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

        # Optimization: if the iteration expression is a literal (doesn't reference $this),
        # just return that literal directly
        from fhir4ds.fhirpath.ast.nodes import LiteralNode
        if isinstance(node.arguments[0], LiteralNode):
            logger.debug("Repeat argument is a literal - returning literal directly")
            return self.visit(node.arguments[0])

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

        # Translate the iteration expression with $this binding
        with self._variable_scope({
            "$this": VariableBinding(
                expression=element_cast,
                source_table=enum_cte
            )
        }):
            iter_fragment = self.visit(node.arguments[0])

        logger.debug(f"Iteration expression SQL: {iter_fragment.expression}")

        # For recursive case, we need to apply same expression to results
        # $this will be bound to r.element (the element from previous iteration)
        # Cast for recursive case as well
        recursive_element_cast = self.dialect.cast_to_double(f"r.{element_alias}")

        with self._variable_scope({
            "$this": VariableBinding(
                expression=recursive_element_cast,
                source_table="r"
            )
        }):
            recursive_iter_fragment = self.visit(node.arguments[0])

        logger.debug(f"Recursive iteration expression SQL: {recursive_iter_fragment.expression}")

        # Restore context
        self.context.current_table = old_table
        self.context.parent_path = old_path

        # Build RECURSIVE CTE SQL with cycle detection
        # Base case: initial collection (depth = 0)
        # Recursive case: apply iteration expression to elements from previous level
        # Continue until no new elements, max depth (100), or cycle detected
        path_alias = f"{element_alias}_path"

        # Use aggregate_to_json_array to convert results to JSON array
        aggregate_expr = self.dialect.aggregate_to_json_array(f"{element_alias}")
        empty_array = self.dialect.empty_json_array()

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
            SELECT {recursive_iter_fragment.expression} as {result_alias}
        ) iteration
        WHERE r.{depth_alias} < 100
        AND iteration.{result_alias} IS NOT NULL
        AND NOT ({result_alias} = ANY(r.{path_alias}))
    )
    SELECT COALESCE({aggregate_expr}, {empty_array})
    FROM (SELECT DISTINCT {element_alias} FROM {recursive_cte}) AS distinct_results
)"""

        logger.debug(f"Complete repeat() SQL generated with RECURSIVE CTE and $this binding")

        return SQLFragment(
            expression=sql,
            source_table=old_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=iter_fragment.dependencies if hasattr(iter_fragment, 'dependencies') else []
        )

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

            return SQLFragment(
                expression=combine_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=dependencies,
                metadata={"function": "combine", "is_collection": True}
            )
        finally:
            self._restore_context(snapshot)

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
        logger.debug(f"Translating type operation: {node.operation} with target type: {node.target_type}")

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

        expr_fragment = self.visit(node.children[0])
        canonical_type = self._resolve_canonical_type(node.target_type)
        normalized = canonical_type.lower()

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
            dependencies=expr_fragment.dependencies
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
        """
        # Type operation should have exactly one child (the expression to cast)
        if not node.children:
            raise ValueError("as() operation requires an expression to cast")

        # Snapshot context so polymorphic path traversal does not leak state
        snapshot = self._snapshot_context()
        try:
            child_node = node.children[0]
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

        # POLYMORPHIC FIELD HANDLING:
        # If the child is a polymorphic property (e.g., "value"), use type-specific field resolution
        # instead of type filtering. In FHIR, polymorphic fields encode the type in the field name.
        # Example: value.ofType(integer) → extract $.valueInteger
        #          value.ofType(Range) → extract $.valueRange
        # IMPORTANT: Only apply this for direct property access (e.g., $.value), not nested
        # (e.g., $.component.value) to avoid breaking collection filtering
        if property_name and is_polymorphic_property(property_name):
            # Check if this is a direct property access by checking if parent_path was empty
            # before we visited the child node
            # Direct access: parent_path_before_child is empty (e.g., value.ofType(integer))
            # Nested access: parent_path_before_child has elements (e.g., component.value.ofType(integer))
            is_direct_access = len(parent_path_before_child) == 0

            if is_direct_access:
                polymorphic_field = resolve_polymorphic_field_for_type(property_name, canonical_type)
                if polymorphic_field:
                    logger.debug(f"Resolved polymorphic field: {property_name} + {canonical_type} → {polymorphic_field}")

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

    # Type function call handlers (temporary until AST adapter fix in SP-007-XXX)

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
            This is a temporary adapter until SP-007-XXX fixes AST adapter
            to generate TypeOperationNode for type functions.
        """
        # Validate argument count
        if not node.arguments or len(node.arguments) == 0:
            raise ValueError(f"is() requires exactly 1 argument, got {len(node.arguments) if node.arguments else 0}")

        target_type = self._extract_type_name_from_function_call(node)

        # Extract the path from node.text
        # The adapter loses path context, so we parse it from the text
        # Example: "Observation.value.is(Quantity)" → path="Observation.value"
        path_expr = self._extract_path_before_function(node.text, node.function_name)

        # Get the value expression
        # SP-022-003: When is() is called as a method on a literal (e.g., 1.is(Integer)),
        # the function call node only contains "is()" as text, not "1.is(Integer)".
        # In this case, check if there's a previous fragment that contains the
        # expression we should be type-checking.
        if path_expr:
            # Parse and translate the path expression to update context
            # SP-023-004B: Use EnhancedASTNode directly - accept() handles dispatch
            from ..parser import FHIRPathParser
            path_parser = FHIRPathParser()
            path_ast = path_parser.parse(path_expr).get_ast()

            # Visit the path to update context
            path_fragment = self.visit(path_ast)
            value_expr = path_fragment.expression
        elif self.fragments:
            # SP-022-003: No path in node.text, but we have previous fragments.
            # This happens with invocation patterns like "1.is(Integer)" where
            # the AST has the literal as a sibling node that was already visited.
            # Use the previous fragment's expression as the value to type-check.
            value_expr = self.fragments[-1].expression
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
        if self._is_sql_literal_expression(value_expr):
            type_check_sql = self._generate_literal_type_check(value_expr, canonical_type)
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
        # Validate argument count
        if not node.arguments or len(node.arguments) == 0:
            raise ValueError(f"as() requires exactly 1 argument, got {len(node.arguments) if node.arguments else 0}")

        target_type = self._extract_type_name_from_function_call(node)
        canonical_type = self._resolve_canonical_type(target_type)

        # Extract the path from node.text (before .as())
        path_expr = self._extract_path_before_function(node.text, node.function_name)

        # ALSO extract any path AFTER .as() - e.g., ".unit" in "value.as(Quantity).unit"
        # Find the closing paren of .as(...) and get everything after it
        path_after = None
        if node.text and '.as(' in node.text:
            # Find the .as( and then find the matching closing paren
            as_start = node.text.find('.as(')
            if as_start >= 0:
                # Find closing paren
                paren_count = 1
                i = as_start + 4  # Start after '.as('
                while i < len(node.text) and paren_count > 0:
                    if node.text[i] == '(':
                        paren_count += 1
                    elif node.text[i] == ')':
                        paren_count -= 1
                    i += 1
                # i now points after the closing paren
                if i < len(node.text) and node.text[i] == '.':
                    path_after = node.text[i+1:]  # Get everything after the dot
                    logger.debug(f"Extracted path after .as(): {path_after}")

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

                    # Create and return the fragment
                    fragment = SQLFragment(
                        expression=sql_expr,
                        source_table=self.context.current_table,
                        requires_unnest=False,
                        is_aggregate=False,
                        dependencies=[],
                        metadata={
                            'type_operation': 'as',
                            'target_type': canonical_type,
                            'polymorphic_resolution': polymorphic_field,
                            'json_path': json_path,
                            'path_after_as': path_after
                        }
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
        sql = f"""(
    SELECT {array_alias}.value
    FROM (
        SELECT
            {array_alias}_unnest.value,
            ROW_NUMBER() OVER () - 1 AS row_index
        FROM LATERAL {unnest_sql}
    ) AS {array_alias}
    WHERE {condition_fragment.expression}
)"""

        logger.debug(f"Complete where() subquery fragment generated")

        # Return SQL fragment with metadata
        # Note: Does NOT update context.current_table since this returns a collection expression
        return SQLFragment(
            expression=sql,
            source_table=old_table,  # Still depends on source table
            requires_unnest=False,  # Subquery is self-contained
            is_aggregate=False,
            dependencies=[old_table]  # Track dependency on source table
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

        with self._variable_scope({
            "$this": VariableBinding(
                expression=this_expression,
                source_table=source_table
            )
        }):
            # Translate the filter condition argument
            condition_fragment = self.visit(node.arguments[0])

        # SP-102-001: Restore pending_fragment_result after lambda scope exits
        self.context.pending_fragment_result = old_pending

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

        # Return a fragment with filter metadata for the CTE builder
        # The CTE builder will add a WHERE clause to filter the CTE results
        return SQLFragment(
            expression=result_col,  # The column we're filtering
            source_table=source_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=[source_table],
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

        # Ensure context path reflects the function target
        self._prefill_path_from_function(node)

        # Get the array path from current context
        array_path = self.context.get_json_path()

        logger.debug(f"Array path for select(): {array_path}")

        # Generate unique CTE and array element alias names
        cte_name = self.context.next_cte_name()
        array_alias = f"{cte_name}_item"

        logger.debug(f"Generated CTE name: {cte_name}, array alias: {array_alias}")

        # Save current context state for restoration
        old_table = self.context.current_table
        old_path = self.context.parent_path.copy()

        # Update context to reference array elements for projection expression translation
        self.context.current_table = array_alias
        self.context.parent_path.clear()

        # Translate the projection expression argument
        total_expr = self.dialect.get_json_array_length(
            column=old_table,
            path=array_path if array_path and array_path != "$" else None
        )

        # For $index support, we need to use enumerate_json_array instead of simple unnest
        # Define aliases for index and value
        index_alias = f"{array_alias}_idx"

        with self._variable_scope({
            "$this": VariableBinding(
                expression=array_alias,
                source_table=array_alias
            ),
            "$index": VariableBinding(
                expression=index_alias,
                source_table=array_alias
            ),
            "$total": VariableBinding(
                expression=total_expr,
                source_table=old_table,
                dependencies=[old_table]
            )
        }):
            projection_fragment = self.visit(node.arguments[0])

        logger.debug(f"Projection expression SQL: {projection_fragment.expression}")

        # SP-022-019: Do NOT restore old path - after select(), the context represents
        # the projected result (stored in 'result' column), not the original path.
        # Clear parent_path so count() won't try to extract from a JSON path.
        self.context.parent_path.clear()

        # Use enumerate_json_array to get both value and index
        # This generates: SELECT index, value FROM enumerate_json_array(...)
        array_expr = self.dialect.extract_json_object(old_table, array_path) if array_path and array_path != "$" else old_table
        enumerate_sql = self.dialect.enumerate_json_array(array_expr, array_alias, index_alias)

        logger.debug(f"Enumerate SQL: {enumerate_sql}")

        # Generate database-specific JSON array aggregation
        # Need to order by index to preserve array order
        aggregate_expr = self.dialect.aggregate_to_json_array(f"{projection_fragment.expression} ORDER BY {index_alias}")

        # Construct complete SQL fragment with SELECT, FROM, LATERAL enumeration, GROUP BY
        # This is population-friendly: processes entire array without row-by-row iteration
        # SP-022-019: Include resource column for subsequent CTEs to reference
        sql = f"""SELECT {old_table}.id, {old_table}.resource,
       {aggregate_expr} as result
FROM {old_table}, LATERAL ({enumerate_sql}) AS enum_table
GROUP BY {old_table}.id, {old_table}.resource"""

        logger.debug(f"Complete select() SQL fragment generated")

        # Update context to reference the new CTE for subsequent operations
        self.context.current_table = cte_name

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
            dependencies=[old_table]  # Track dependency on source table
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

            return SQLFragment(
                expression=sql_expr,
                source_table=self.context.current_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=[],
                metadata={"function": "exists", "result_type": "boolean"}
            )

        # Case 2: exists(criteria) - check if any element satisfies condition
        else:
            # Generate unique alias for array elements
            array_alias = f"exists_{self.context.cte_counter}_item"

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
            unnest_sql = self.dialect.unnest_json_array(
                column=old_table,
                path=array_path,
                alias=f"{array_alias}_unnest"
            )

            logger.debug(f"UNNEST SQL: {unnest_sql}")

            # Construct SQL fragment with EXISTS subquery
            # Use subquery with ROW_NUMBER() for $index support
            sql_expr = f"""CASE WHEN EXISTS (
    SELECT 1
    FROM (
        SELECT
            {array_alias}_unnest.value,
            ROW_NUMBER() OVER () - 1 AS row_index
        FROM LATERAL {unnest_sql}
    ) AS {array_alias}
    WHERE {condition_fragment.expression}
) THEN TRUE ELSE FALSE END"""

            logger.debug(f"Generated exists() SQL (with criteria): {sql_expr}")

            return SQLFragment(
                expression=sql_expr,
                source_table=self.context.current_table,
                requires_unnest=False,  # EXISTS subquery is self-contained
                is_aggregate=False,
                dependencies=[old_table],
                metadata={"function": "exists", "result_type": "boolean"}
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

            return SQLFragment(
                expression=empty_check_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "empty", "result_type": "boolean"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_not(self, node: FunctionCallNode) -> SQLFragment:
        """Translate not() function to SQL for boolean negation.

        The not() function returns the opposite boolean value of the input.
        It operates on boolean values only, returning the logical negation.

        FHIRPath Specification:
            not() : Boolean
            - Input true → Returns false
            - Input false → Returns true
            - Input {} (empty) → Returns {} (empty/NULL)
            - Input collection with multiple values → Returns {} (empty/NULL)

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
            value_expr = self.fragments[-1].expression
            source_table = self.fragments[-1].source_table or self.context.current_table
            dependencies = list(self.fragments[-1].dependencies) if self.fragments[-1].dependencies else []

            not_sql = self.dialect.generate_boolean_not(value_expr)

            logger.debug(f"Generated not() SQL (from previous fragment): {not_sql}")

            return SQLFragment(
                expression=not_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "not", "result_type": "boolean"}
            )

        # Standard path - use _resolve_function_target
        value_expr, dependencies, literal_value, snapshot, _, _ = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if literal_value is not None:
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

        Implementation Strategy:
            The all() function can be implemented using several SQL approaches:
            1. BOOL_AND aggregate (PostgreSQL, DuckDB): BOOL_AND(condition) = true
            2. NOT EXISTS negation: NOT EXISTS (SELECT ... WHERE NOT condition)
            3. COUNT comparison: COUNT(*) = COUNT(*) FILTER (WHERE condition)

            We use approach #1 (BOOL_AND) as it's most direct and supported by both
            DuckDB and PostgreSQL dialects.

        Args:
            node: FunctionCallNode representing all() function call

        Returns:
            SQLFragment with boolean universal quantification SQL

        Raises:
            ValueError: If all() doesn't have exactly 1 argument (criteria expression)

        Example:
            Input: Patient.name.all(use = 'official')

            Output SQL (DuckDB):
                COALESCE(
                    (SELECT bool_and(json_extract_string(elem, '$.use') = 'official')
                     FROM (SELECT unnest(json_extract(resource, '$.name')) as elem)),
                    true
                )

            Input: Patient.telecom.all(system = 'phone')

            Output SQL (PostgreSQL):
                COALESCE(
                    (SELECT bool_and(jsonb_extract_path_text(elem, 'system') = 'phone')
                     FROM jsonb_array_elements(jsonb_extract_path(resource, 'telecom')) as elem),
                    true
                )

            Note: COALESCE handles empty arrays (NULL result from bool_and) → returns true
        """
        logger.debug(f"Translating all() function with {len(node.arguments)} arguments")

        # Validate all() has exactly one argument (the criteria expression)
        if len(node.arguments) != 1:
            raise ValueError(
                f"all() function requires exactly 1 argument (criteria expression), "
                f"got {len(node.arguments)}"
            )

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

        # Get the target collection/value to trace
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
                raise ValueError("trace() requires a target expression to operate on")

            # trace() is a pass-through in SQL execution
            # The target expression is returned unchanged
            # Note: In a full implementation with logging, we could inject
            # logging SQL here, but for compliance testing, pass-through is sufficient

            logger.info(f"trace() pass-through for expression: {collection_expr}")

            # Simply return the target expression unchanged
            return SQLFragment(
                expression=collection_expr,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=False,
                dependencies=list(dict.fromkeys(dependencies)),
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

                # Get array length using dialect-specific function
                length_expr = self.dialect.get_json_array_length(
                    column=source_table,
                    path=target_path if target_path and target_path != "$" else None
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

        if node.target is not None:
            target_snapshot = self._snapshot_context()
            target_fragment = self.visit(node.target)
            string_expr = target_fragment.expression
            source_table = target_fragment.source_table or target_snapshot["current_table"]
            requires_unnest = getattr(target_fragment, "requires_unnest", False)
            is_aggregate = getattr(target_fragment, "is_aggregate", False)
            if hasattr(target_fragment, "dependencies"):
                dependencies.extend(target_fragment.dependencies)
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
            args = args[1:]

        if string_expr is None:
            # SP-022-012: Check for pending_fragment_result from InvocationExpression chain
            # This handles cases like $this.length() where $this was visited before length()
            # and its expression was stored in pending_fragment_result
            # SP-102-001: pending_fragment_result is a tuple (sql_expression, parent_path, is_multi_item)
            if self.context.pending_fragment_result is not None:
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
                # Clear the pending result after consuming it
                self.context.pending_fragment_result = None
                if source_table is None:
                    source_table = self.context.current_table
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
                    logger.debug(
                        f"SP-102-001: Using $this as implicit string argument for {func_name}"
                    )
            else:
                current_path = self.context.get_json_path()
                if current_path and current_path != "$":
                    string_expr = self.dialect.extract_json_field(
                        column=self.context.current_table,
                        path=current_path
                    )
                else:
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

            # SP-025-002: Return empty string for out-of-bounds (not NULL)
            # Per FHIRPath spec, substring with negative start or zero length returns empty string
            empty_sql = "''"

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

            start_condition = f"({start_expr})"
            start_plus_one = f"({start_condition} + 1)"

            if length_expr is not None:
                substring_sql = self.dialect.generate_string_function(
                    'substring',
                    string_expr,
                    start_plus_one,
                    length_expr
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
            dependencies=list(dict.fromkeys(dependencies))
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
            "regexp_matches(json_extract(resource, '$.name[0].family'), '[A-Z][a-z]+')"
            >>> fragment.expression  # PostgreSQL
            "(jsonb_extract_path_text(resource, 'name', '0', 'family') ~ '[A-Z][a-z]+')"

        Note:
            - Operates on current context (implicit string)
            - Takes exactly 1 argument (regex pattern)
            - Returns boolean (true if matches, false if not)
            - NULL handling: null input → null output (both databases)
            - Regex syntax: Both DuckDB (PCRE) and PostgreSQL (POSIX) tested compatible
        """
        logger.debug(f"Translating matches() function")

        # Validate arguments
        if len(node.arguments) != 1:
            raise ValueError(
                f"matches() function requires exactly 1 argument (regex pattern), "
                f"got {len(node.arguments)}"
            )

        # Get target string expression from current context
        # For chained expressions like "name.family.matches('[A-Z]+')"
        current_path = self.context.get_json_path()
        target_expr = self.dialect.extract_json_field(
            column=self.context.current_table,
            path=current_path
        )

        # Get regex pattern argument
        regex_pattern_node = node.arguments[0]
        regex_fragment = self.visit(regex_pattern_node)
        regex_pattern = regex_fragment.expression

        # Generate regex matching SQL using dialect
        matches_sql = self.dialect.generate_regex_match(
            target_expr,
            regex_pattern
        )

        logger.debug(f"Generated matches() SQL: {matches_sql}")

        # Collect dependencies
        dependencies = regex_fragment.dependencies if hasattr(regex_fragment, 'dependencies') else []

        return SQLFragment(
            expression=matches_sql,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=dependencies
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
            "regexp_replace(json_extract(resource, '$.name[0].family'), '[0-9]', 'X', 'g')"

        Note:
            - Operates on current context (implicit string)
            - Takes exactly 2 arguments (regex pattern, substitution)
            - Returns transformed string
            - NULL handling: null input → null output (both databases)
            - Regex syntax: Both DuckDB (PCRE) and PostgreSQL (POSIX) support regexp_replace
            - Global replacement: 'g' flag replaces all matches, not just first
            - Capture groups: Both support $1, $2 in substitution (DuckDB) or \1, \2 (PostgreSQL)
        """
        logger.debug(f"Translating replaceMatches() function")

        # Validate arguments
        if len(node.arguments) != 2:
            raise ValueError(
                f"replaceMatches() function requires exactly 2 arguments (regex pattern, substitution), "
                f"got {len(node.arguments)}"
            )

        # Get target string expression from current context
        # For chained expressions like "name.family.replaceMatches('[0-9]', 'X')"
        current_path = self.context.get_json_path()
        target_expr = self.dialect.extract_json_field(
            column=self.context.current_table,
            path=current_path
        )

        # Get regex pattern argument
        regex_pattern_node = node.arguments[0]
        regex_fragment = self.visit(regex_pattern_node)
        regex_pattern = regex_fragment.expression

        # Get substitution argument
        substitution_node = node.arguments[1]
        substitution_fragment = self.visit(substitution_node)
        substitution = substitution_fragment.expression

        # Generate regex replacement SQL using dialect
        replace_sql = self.dialect.generate_regex_replace(
            target_expr,
            regex_pattern,
            substitution
        )

        logger.debug(f"Generated replaceMatches() SQL: {replace_sql}")

        # Collect dependencies from both arguments
        dependencies = []
        if hasattr(regex_fragment, 'dependencies'):
            dependencies.extend(regex_fragment.dependencies)
        if hasattr(substitution_fragment, 'dependencies'):
            dependencies.extend(substitution_fragment.dependencies)

        return SQLFragment(
            expression=replace_sql,
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False,
            dependencies=dependencies
        )

    def _translate_all_true(self, node: FunctionCallNode) -> SQLFragment:
        """Translate allTrue() function to SQL using BOOL_AND aggregate.
        
        FHIRPath Specification: Section 5.3.5
        Returns TRUE if all elements are TRUE. Empty collections return TRUE.
        """
        logger.debug("Translating allTrue() function")
        
        if node.arguments:
            raise ValueError(f"allTrue() takes no arguments, got {len(node.arguments)}")
        
        (collection_expr, dependencies, _, snapshot, _, target_path) = self._resolve_function_target(node)
        source_table = snapshot["current_table"]
        
        try:
            if not collection_expr:
                raise ValueError("allTrue() requires a collection expression")
            
            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            all_true_sql = self.dialect.generate_all_true(normalized_expr)
            
            return SQLFragment(
                expression=all_true_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "allTrue", "result_type": "boolean"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_any_true(self, node: FunctionCallNode) -> SQLFragment:
        """Translate anyTrue() function to SQL using BOOL_OR aggregate.
        
        FHIRPath Specification: Section 5.3.6
        Returns TRUE if any element is TRUE. Empty collections return FALSE.
        """
        logger.debug("Translating anyTrue() function")
        
        if node.arguments:
            raise ValueError(f"anyTrue() takes no arguments, got {len(node.arguments)}")
        
        (collection_expr, dependencies, _, snapshot, _, target_path) = self._resolve_function_target(node)
        source_table = snapshot["current_table"]
        
        try:
            if not collection_expr:
                raise ValueError("anyTrue() requires a collection expression")
            
            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            any_true_sql = self.dialect.generate_any_true(normalized_expr)
            
            return SQLFragment(
                expression=any_true_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "anyTrue", "result_type": "boolean"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_all_false(self, node: FunctionCallNode) -> SQLFragment:
        """Translate allFalse() function to SQL using BOOL_AND(NOT value).
        
        FHIRPath Specification: Section 5.3.7
        Returns TRUE if all elements are FALSE. Empty collections return TRUE.
        """
        logger.debug("Translating allFalse() function")
        
        if node.arguments:
            raise ValueError(f"allFalse() takes no arguments, got {len(node.arguments)}")
        
        (collection_expr, dependencies, _, snapshot, _, target_path) = self._resolve_function_target(node)
        source_table = snapshot["current_table"]
        
        try:
            if not collection_expr:
                raise ValueError("allFalse() requires a collection expression")
            
            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            all_false_sql = self.dialect.generate_all_false(normalized_expr)
            
            return SQLFragment(
                expression=all_false_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "allFalse", "result_type": "boolean"}
            )
        finally:
            self._restore_context(snapshot)

    def _translate_any_false(self, node: FunctionCallNode) -> SQLFragment:
        """Translate anyFalse() function to SQL using BOOL_OR(NOT value).

        FHIRPath Specification: Section 5.3.8
        Returns TRUE if any element is FALSE. Empty collections return FALSE.
        """
        logger.debug("Translating anyFalse() function")

        if node.arguments:
            raise ValueError(f"anyFalse() takes no arguments, got {len(node.arguments)}")

        (collection_expr, dependencies, _, snapshot, _, target_path) = self._resolve_function_target(node)
        source_table = snapshot["current_table"]

        try:
            if not collection_expr:
                raise ValueError("anyFalse() requires a collection expression")

            base_expr = self._extract_collection_source(collection_expr, target_path, snapshot)
            normalized_expr = self._normalize_collection_expression(base_expr)
            any_false_sql = self.dialect.generate_any_false(normalized_expr)

            return SQLFragment(
                expression=any_false_sql,
                source_table=source_table,
                requires_unnest=False,
                is_aggregate=True,
                dependencies=list(dict.fromkeys(dependencies)),
                metadata={"function": "anyFalse", "result_type": "boolean"}
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
