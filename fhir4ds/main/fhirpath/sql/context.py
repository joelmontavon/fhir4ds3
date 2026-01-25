"""Translation Context for FHIRPath AST Traversal.

This module defines the TranslationContext dataclass, which maintains state during
AST traversal by the translator. The context tracks the current position in the
path, source table references, variable bindings, and CTE naming.

The TranslationContext design follows these principles:
- **Mutable State**: Explicitly mutable to track state changes during traversal
- **Path Management**: Stack-based path tracking for building JSON paths
- **CTE Naming**: Generates unique CTE names for multi-step expressions
- **Variable Bindings**: Tracks FHIRPath variables ($this, $index, etc.)

Module: fhir4ds.fhirpath.sql.context
PEP: PEP-003 - FHIRPath AST-to-SQL Translator
Created: 2025-09-29
Author: FHIR4DS Development Team
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from .fragments import SQLFragment


@dataclass
class VariableBinding:
    """Represents a bound FHIRPath variable within the translation context."""

    expression: str
    source_table: Optional[str] = None
    requires_unnest: bool = False
    is_aggregate: bool = False
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TranslationContext:
    """Context maintained during AST traversal for SQL generation.

    TranslationContext tracks the current state of translation as the translator
    walks the AST tree. This includes the current table being queried, the path
    components being built, variable bindings, and a counter for generating unique
    CTE names.

    The context is explicitly mutable and designed to be updated as the translator
    visits each AST node. This allows the translator to maintain state across
    multiple node visits without complex parameter passing.

    Attributes:
        current_table: The current source table or CTE name being queried from.
            Starts as "resource" (the FHIR resource table) and updates as CTEs
            are generated. For example, after a where() operation, this becomes
            the name of the CTE containing filtered results.
        current_resource_type: The FHIR resource type being processed (e.g.,
            "Patient", "Observation", "Condition"). Used for root identifier
            resolution and type validation.
        parent_path: Stack of path components used to build JSON paths. For
            example, when traversing "Patient.name.family", this would be
            ["name", "family"]. Used to construct paths like "$.name.family".
        variable_bindings: Dictionary mapping FHIRPath variable names to their
            SQL representations. For example, {"$this": "cte_1_item", "$index": "idx"}.
            Used for resolving variable references in FHIRPath expressions.
        cte_counter: Counter for generating unique CTE names. Increments each
            time next_cte_name() is called, ensuring all CTEs have unique names
            like "cte_1", "cte_2", etc.

    Design Decisions:
        1. **Mutability**: Context is explicitly mutable because it tracks state
           that changes during AST traversal. Immutability would require creating
           new contexts at each step, which is inefficient and complex.
        2. **CTE Counter**: Simple integer counter generates predictable, debuggable
           CTE names. Alternative approaches (UUIDs, hash-based) would make SQL
           harder to read and debug.
        3. **Path Stack**: List-based stack allows easy push/pop operations as
           the translator descends/ascends the AST tree.

    Example:
        Basic context initialization:
        >>> context = TranslationContext(current_resource_type="Patient")
        >>> print(context.current_table)
        resource
        >>> print(context.current_resource_type)
        Patient

        Path management:
        >>> context = TranslationContext()
        >>> context.push_path("name")
        >>> context.push_path("family")
        >>> print(context.parent_path)
        ['name', 'family']
        >>> print(context.pop_path())
        family
        >>> print(context.parent_path)
        ['name']

        CTE name generation:
        >>> context = TranslationContext()
        >>> print(context.next_cte_name())
        cte_1
        >>> print(context.next_cte_name())
        cte_2
        >>> print(context.next_cte_name())
        cte_3

        Variable bindings:
        >>> context = TranslationContext()
        >>> context.bind_variable("$this", "cte_1_item")
        >>> context.bind_variable("$index", "idx")
        >>> print(context.get_variable("$this"))
        cte_1_item
        >>> print(context.get_variable("$missing"))
        None

        Current table updates:
        >>> context = TranslationContext()
        >>> print(context.current_table)
        resource
        >>> context.current_table = "cte_1"
        >>> print(context.current_table)
        cte_1

    Thread Safety:
        TranslationContext is NOT thread-safe. Each translation operation should
        use its own context instance. Do not share contexts across multiple
        concurrent translations.

    See Also:
        - SQLFragment: Output data structure for SQL fragments
        - ASTToSQLTranslator: Main translator class that uses TranslationContext
        - PEP-003: Complete specification for AST-to-SQL translation
    """

    current_table: str = "resource"
    current_resource_type: str = "Patient"
    parent_path: List[str] = field(default_factory=list)
    variable_bindings: Dict[str, VariableBinding] = field(default_factory=dict)
    cte_counter: int = 0
    _variable_scope_stack: List[Dict[str, VariableBinding]] = field(init=False, repr=False)
    # SP-022-004: Track when operating on an extracted element from UNNEST
    # After first()/last()/skip()/take() on an unnested collection, subsequent
    # field access should be relative to this column, not the original resource.
    current_element_column: Optional[str] = None
    # Track the FHIR type of the current element (for proper type resolution)
    current_element_type: Optional[str] = None
    # SP-022-009: Track pending literal value from previous fragment in invocation chain
    # Used for expressions like 1.convertsToInteger() where the literal needs to flow
    # to the subsequent function call
    pending_literal_value: Optional[tuple] = None  # (literal_value, sql_expression)
    # SP-022-009: Track pending fragment result from previous step in invocation chain
    # Used for expressions like '1.1'.toInteger().empty() where the result of toInteger()
    # needs to flow to the subsequent empty() function call
    # SP-100-002: Now stores a tuple (expression, parent_path, is_multi_item_collection)
    # for cardinality validation
    pending_fragment_result: Optional[tuple] = None  # (sql_expression, parent_path, is_multi_item) from previous fragment
    # SP-101-002: CTE column alias registry for tracking column renames in CTE chains
    # Maps logical column names (like "result") to actual column aliases in CTE output
    # This is critical for chained operations like Patient.name.first().given where
    # the CTE outputs a column named "name_item" but subsequent code references "result"
    cte_column_aliases: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialise variable scope stack after dataclass creation."""
        self._variable_scope_stack = [self.variable_bindings]

    def next_cte_name(self) -> str:
        """Generate the next unique CTE name.

        Increments the internal counter and returns a unique CTE name. CTE names
        follow the pattern "cte_N" where N is a sequential integer starting from 1.

        This method is called each time the translator generates a new CTE (e.g.,
        for where(), select(), or other operations that require intermediate results).

        Returns:
            Unique CTE name (e.g., "cte_1", "cte_2", "cte_3")

        Example:
            >>> context = TranslationContext()
            >>> context.next_cte_name()
            'cte_1'
            >>> context.next_cte_name()
            'cte_2'
            >>> context.next_cte_name()
            'cte_3'

        Design Note:
            Sequential naming (cte_1, cte_2, ...) makes generated SQL easy to read
            and debug. Alternative approaches (UUIDs, hash-based names) would make
            SQL harder to understand without providing meaningful benefits.
        """
        self.cte_counter += 1
        return f"cte_{self.cte_counter}"

    def push_path(self, component: str) -> None:
        """Add a path component to the path stack.

        Appends a path component to the parent_path list. This is used when
        descending into nested structures in the AST. For example, when visiting
        an identifier node for "family" after "name", this would push "family"
        onto the stack.

        Args:
            component: Path component to add (e.g., "name", "family", "use")

        Example:
            >>> context = TranslationContext()
            >>> context.push_path("name")
            >>> print(context.parent_path)
            ['name']
            >>> context.push_path("family")
            >>> print(context.parent_path)
            ['name', 'family']

        Design Note:
            Stack-based path management allows the translator to build JSON paths
            incrementally as it traverses the AST. This is more efficient than
            passing path strings down the recursion stack.
        """
        self.parent_path.append(component)

    def pop_path(self) -> Optional[str]:
        """Remove and return the last path component from the stack.

        Removes the most recently added path component from parent_path. This is
        used when ascending back up the AST tree after visiting child nodes.

        Returns:
            The removed path component, or None if path stack is empty

        Example:
            >>> context = TranslationContext()
            >>> context.push_path("name")
            >>> context.push_path("family")
            >>> print(context.pop_path())
            family
            >>> print(context.pop_path())
            name
            >>> print(context.pop_path())
            None

        Design Note:
            Returns None for empty stack rather than raising an exception. This
            makes the API more forgiving and allows the translator to safely call
            pop_path without checking stack depth.
        """
        return self.parent_path.pop() if self.parent_path else None

    def get_json_path(self) -> str:
        """Build a JSON path from the current path stack.

        Constructs a JSON path expression (e.g., "$.name[*].family") from the current
        parent_path components. Automatically adds [*] for array fields based on FHIR
        schema cardinality.

        Returns:
            JSON path string with "$." prefix (e.g., "$.name[*].family")
            Returns "$" if path stack is empty

        Example:
            >>> context = TranslationContext()
            >>> context.push_path("name")
            >>> context.push_path("family")
            >>> print(context.get_json_path())
            $.name[*].family  # name is an array in Patient
            >>> context.pop_path()
            'family'
            >>> print(context.get_json_path())
            $.name[*]
            >>> context.pop_path()
            'name'
            >>> print(context.get_json_path())
            $

        Design Note:
            Always includes "$" prefix to match JSON path syntax expected by
            database JSON extraction functions (json_extract, jsonb_extract_path, etc.).
        """
        if not self.parent_path:
            return "$"

        # Import here to avoid circular dependency
        from ..types.type_registry import get_type_registry

        # Build path with [*] for array elements
        resource_type = self.current_resource_type
        path_parts = []
        type_registry = get_type_registry()

        for i, component in enumerate(self.parent_path):
            # Build incremental path to check cardinality
            element_path = ".".join(self.parent_path[:i+1])

            # Check if this element is an array
            is_array = False
            if resource_type:
                try:
                    is_array = type_registry.is_array_element(resource_type, element_path)
                except Exception:
                    # If we can't determine, assume not an array
                    pass

            # Add [*] for array elements
            if is_array:
                path_parts.append(component + "[*]")
            else:
                path_parts.append(component)

        return "$." + ".".join(path_parts)

    def push_variable_scope(self, preserve: bool = True) -> None:
        """Push a new variable scope onto the stack.

        Args:
            preserve: Whether to copy bindings from the current scope into the new scope.
        """
        current_scope = self.variable_bindings if preserve else {}
        new_scope: Dict[str, VariableBinding] = current_scope.copy()
        self._variable_scope_stack.append(new_scope)
        self.variable_bindings = new_scope

    def pop_variable_scope(self) -> Dict[str, VariableBinding]:
        """Pop the current variable scope, restoring the parent scope.

        Returns:
            The popped variable scope dictionary.

        Raises:
            RuntimeError: If attempting to pop the root scope.
        """
        if len(self._variable_scope_stack) == 1:
            raise RuntimeError("Cannot pop the root variable scope")

        popped = self._variable_scope_stack.pop()
        self.variable_bindings = self._variable_scope_stack[-1]
        return popped

    def _coerce_variable_binding(
        self,
        sql_reference: Union[VariableBinding, SQLFragment, str]
    ) -> VariableBinding:
        """Normalize variable binding inputs into a VariableBinding instance."""
        if isinstance(sql_reference, VariableBinding):
            return sql_reference

        if isinstance(sql_reference, SQLFragment):
            return VariableBinding(
                expression=sql_reference.expression,
                source_table=sql_reference.source_table,
                requires_unnest=sql_reference.requires_unnest,
                is_aggregate=sql_reference.is_aggregate,
                dependencies=sql_reference.dependencies.copy(),
            )

        if isinstance(sql_reference, str):
            return VariableBinding(expression=sql_reference)

        raise TypeError(
            "sql_reference must be a VariableBinding, SQLFragment, or string"
        )

    def bind_variable(
        self,
        variable_name: str,
        sql_reference: Union[VariableBinding, SQLFragment, str]
    ) -> None:
        """Bind a FHIRPath variable to its SQL representation.

        Stores a mapping from a FHIRPath variable name (e.g., "$this", "$index")
        to a VariableBinding that captures the SQL expression and metadata used to
        resolve variable references when translating FHIRPath expressions.

        Args:
            variable_name: FHIRPath variable name (usually starts with "$")
            sql_reference: SQL representation or metadata for the variable

        Example:
            >>> context = TranslationContext()
            >>> context.bind_variable("$this", "cte_1_item")
            >>> context.bind_variable("$index", SQLFragment("idx"))
            >>> context.get_variable("$this").expression
            'cte_1_item'

        Design Note:
            Variable names include the "$" prefix to match FHIRPath syntax. This
            makes it clear that these are FHIRPath variables, not SQL identifiers.
        """
        binding = self._coerce_variable_binding(sql_reference)
        self.variable_bindings[variable_name] = binding

    def get_variable(self, variable_name: str) -> Optional[VariableBinding]:
        """Get the binding metadata for a FHIRPath variable.

        Searches variable scopes from innermost to outermost and returns the first
        binding found.

        Args:
            variable_name: FHIRPath variable name to look up

        Returns:
            VariableBinding for the variable, or None if not bound

        Design Note:
            Returns None rather than raising an exception to allow graceful
            handling of unbound variables. The translator can decide how to
            handle missing variables (error, default value, etc.).
        """
        for scope in reversed(self._variable_scope_stack):
            binding = scope.get(variable_name)
            if binding is not None:
                return binding
        return None

    def clear_variables(self) -> None:
        """Clear all variable bindings.

        Removes all variable bindings from the context. This is useful when
        exiting a scope where variables were bound (e.g., after processing a
        where() function that binds $this).

        Example:
            >>> context = TranslationContext()
            >>> context.bind_variable("$this", "cte_1_item")
            >>> context.bind_variable("$index", "idx")
            >>> print(len(context.variable_bindings))
            2
            >>> context.clear_variables()
            >>> print(len(context.variable_bindings))
            0

        Design Note:
            Provides explicit scope management for variables rather than automatic
            garbage collection. This gives the translator fine-grained control over
            variable lifetime.
        """
        self.variable_bindings.clear()

    def snapshot_variable_scopes(self) -> List[Dict[str, VariableBinding]]:
        """Create a shallow copy of the variable scope stack."""
        return [scope.copy() for scope in self._variable_scope_stack]

    def restore_variable_scopes(self, scopes: List[Dict[str, VariableBinding]]) -> None:
        """Restore variable scopes from a snapshot."""
        if not scopes:
            scopes = [{}]
        self._variable_scope_stack = [scope.copy() for scope in scopes]
        self.variable_bindings = self._variable_scope_stack[-1]

    def reset(self) -> None:
        """Reset context to initial state.

        Resets all context state to default values: clears path stack, clears
        variable bindings, resets current table to "resource", and resets CTE
        counter to 0. This is useful for reusing a context instance across
        multiple translations (though creating new instances is preferred).

        Example:
            >>> context = TranslationContext()
            >>> context.push_path("name")
            >>> context.bind_variable("$this", "cte_1_item")
            >>> context.next_cte_name()
            'cte_1'
            >>> context.reset()
            >>> print(context.parent_path)
            []
            >>> print(context.variable_bindings)
            {}
            >>> print(context.cte_counter)
            0
            >>> print(context.next_cte_name())
            cte_1

        Design Note:
            Reset allows context reuse but creates a new instance is generally
            preferred for clarity and to avoid state pollution between translations.
        """
        # Preserve global variable bindings (e.g., $this bound to root resource)
        global_bindings = {
            name: binding for name, binding in self.variable_bindings.items()
            if name == "$this"  # Only preserve $this as a global binding
        }

        self.current_table = "resource"
        self.parent_path.clear()
        self.variable_bindings = global_bindings.copy()
        self._variable_scope_stack = [self.variable_bindings]
        self.cte_counter = 0
        self.current_element_column = None
        self.current_element_type = None
        self.pending_literal_value = None
        self.pending_fragment_result = None
        self.cte_column_aliases.clear()

    def register_column_alias(self, logical_name: str, actual_column: str) -> None:
        """Register a CTE column alias mapping.

        SP-101-002: When a CTE is generated, the output column may have a specific
        alias (e.g., "name_item") that needs to be tracked so subsequent operations
        can reference it correctly.

        Args:
            logical_name: The logical column name (e.g., "result")
            actual_column: The actual column alias in the CTE output (e.g., "name_item")

        Example:
            >>> context = TranslationContext()
            >>> context.register_column_alias("result", "name_item")
            >>> context.resolve_column_alias("result")
            'name_item'
        """
        self.cte_column_aliases[logical_name] = actual_column

    def resolve_column_alias(self, column_name: str) -> str:
        """Resolve a column name through the alias registry.

        SP-101-002: When accessing a column that may have been aliased in a CTE,
        this method returns the actual column name to use.

        Args:
            column_name: The column name to resolve (may be logical or actual)

        Returns:
            The actual column name to use in SQL generation

        Example:
            >>> context = TranslationContext()
            >>> context.register_column_alias("result", "name_item")
            >>> context.resolve_column_alias("result")
            'name_item'
            >>> context.resolve_column_alias("other_column")
            'other_column'
        """
        return self.cte_column_aliases.get(column_name, column_name)

    def clear_column_aliases(self) -> None:
        """Clear all registered column aliases.

        SP-101-002: Called when starting a new translation or when aliases
        from a previous expression should not propagate.
        """
        self.cte_column_aliases.clear()
