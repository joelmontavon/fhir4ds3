"""SQL Fragment Data Structures for FHIRPath Translation.

This module defines the SQLFragment dataclass, which represents the fundamental output
unit of the AST-to-SQL translator. Each SQLFragment encapsulates a single SQL operation
along with metadata needed for CTE generation and optimization.

The SQLFragment design follows these principles:
- **Self-Contained**: Each fragment represents one complete logical operation
- **Metadata-Rich**: Carries flags and dependencies for CTE Builder (PEP-004)
- **Extensible**: Metadata dictionary allows future additions without breaking changes
- **Lightweight**: Minimal memory overhead (<1KB per instance)

Module: fhir4ds.fhirpath.sql.fragments
PEP: PEP-003 - FHIRPath AST-to-SQL Translator
Created: 2025-09-29
Author: FHIR4DS Development Team
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SQLFragment:
    """Represents a SQL fragment generated from an AST node.

    SQLFragment is the fundamental output unit of the AST-to-SQL translator. Each
    fragment encapsulates a single SQL operation (e.g., path extraction, filtering,
    aggregation) along with metadata needed for subsequent processing by the CTE
    Builder (PEP-004).

    Attributes:
        expression: The SQL expression representing this operation. This is the actual
            SQL code that will be executed (or wrapped in a CTE).
        source_table: The source table or CTE that this fragment queries from. Used
            to track dependencies and build correct JOIN/FROM clauses.
        requires_unnest: Flag indicating whether this fragment involves array unnesting
            operations (e.g., LATERAL UNNEST). This helps the CTE Builder determine
            whether special handling is needed.
        is_aggregate: Flag indicating whether this fragment contains aggregation
            operations (COUNT, SUM, AVG, MIN, MAX). Aggregates require GROUP BY
            clauses and special ordering in CTEs.
        dependencies: List of table/CTE names that this fragment depends on. Used
            by the CTE Builder for dependency resolution and topological sorting.
        metadata: Extensible dictionary for additional metadata. Allows future
            enhancements without breaking changes to the dataclass structure.

    Design Decisions:
        1. **Mutability**: SQLFragment is mutable to allow post-creation updates if
           needed (e.g., adding dependencies discovered during later processing).
        2. **Metadata Dictionary**: Provides extensibility without structural changes.
           Future optimizations can add metadata without modifying the dataclass.
        3. **Flags vs Methods**: Uses boolean flags (requires_unnest, is_aggregate)
           rather than methods to keep the dataclass simple and serializable.

    Example:
        Basic path extraction fragment:
        >>> fragment = SQLFragment(
        ...     expression="SELECT id, json_extract(resource, '$.name') as name FROM patient_resources",
        ...     source_table="patient_resources"
        ... )
        >>> print(fragment.expression)
        SELECT id, json_extract(resource, '$.name') as name FROM patient_resources

        Array filtering fragment with unnesting:
        >>> fragment = SQLFragment(
        ...     expression='''
        ...         SELECT resource.id, cte_1_item
        ...         FROM resource, LATERAL UNNEST(json_extract(resource, '$.name')) AS cte_1_item
        ...         WHERE json_extract(cte_1_item, '$.use') = 'official'
        ...     ''',
        ...     source_table="cte_1",
        ...     requires_unnest=True,
        ...     dependencies=["patient_resources"]
        ... )
        >>> print(fragment.requires_unnest)
        True

        Aggregation fragment:
        >>> fragment = SQLFragment(
        ...     expression="SELECT COUNT(*) as patient_count FROM patient_resources",
        ...     source_table="patient_resources",
        ...     is_aggregate=True
        ... )
        >>> print(fragment.is_aggregate)
        True

    Future Considerations:
        - Performance metadata (estimated row counts, query cost)
        - Optimization hints (index usage, join strategies)
        - Type information (FHIR type system mapping)
        - Debugging information (source FHIRPath expression, AST node reference)

    See Also:
        - TranslationContext: Manages state during AST traversal
        - ASTToSQLTranslator: Main translator class that generates SQLFragments
        - PEP-003: Complete specification for AST-to-SQL translation
    """

    expression: str
    source_table: str = "resource"
    requires_unnest: bool = False
    is_aggregate: bool = False
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate SQLFragment after initialization.

        Performs basic validation to ensure the fragment is well-formed:
        - Expression must be non-empty string
        - Source table must be non-empty string
        - Dependencies must be a list (even if empty)
        - Metadata must be a dictionary (even if empty)

        Raises:
            ValueError: If validation fails
        """
        if not self.expression or not isinstance(self.expression, str):
            raise ValueError("expression must be a non-empty string")

        if not self.source_table or not isinstance(self.source_table, str):
            raise ValueError("source_table must be a non-empty string")

        if not isinstance(self.dependencies, list):
            raise ValueError("dependencies must be a list")

        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary")

    def add_dependency(self, dependency: str) -> None:
        """Add a CTE dependency to this fragment.

        Args:
            dependency: Name of the table or CTE this fragment depends on

        Example:
            >>> fragment = SQLFragment(expression="SELECT * FROM cte_1", source_table="cte_2")
            >>> fragment.add_dependency("cte_1")
            >>> print(fragment.dependencies)
            ['cte_1']
        """
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value for extensibility.

        Args:
            key: Metadata key
            value: Metadata value (can be any type)

        Example:
            >>> fragment = SQLFragment(expression="SELECT * FROM patient", source_table="patient")
            >>> fragment.set_metadata("estimated_rows", 1000000)
            >>> fragment.set_metadata("optimization_hint", "use_index")
            >>> print(fragment.metadata)
            {'estimated_rows': 1000000, 'optimization_hint': 'use_index'}
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value with optional default.

        Args:
            key: Metadata key to retrieve
            default: Default value if key not found

        Returns:
            Metadata value or default if not found

        Example:
            >>> fragment = SQLFragment(expression="SELECT * FROM patient", source_table="patient")
            >>> fragment.set_metadata("rows", 1000)
            >>> print(fragment.get_metadata("rows"))
            1000
            >>> print(fragment.get_metadata("missing_key", "not_found"))
            not_found
        """
        return self.metadata.get(key, default)