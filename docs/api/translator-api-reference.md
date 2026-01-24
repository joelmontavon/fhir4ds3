# FHIRPath AST-to-SQL Translator API Reference

**Version**: 0.1.0
**Module**: `fhir4ds.fhirpath.sql`
**PEP**: PEP-003 - FHIRPath AST-to-SQL Translator

---

## Overview

The FHIRPath AST-to-SQL Translator provides the core translation layer that converts FHIRPath Abstract Syntax Trees (AST) into database-specific SQL fragments. This is a critical component of FHIR4DS's unified FHIRPath architecture, enabling population-scale healthcare analytics.

### Key Components

1. **ASTToSQLTranslator**: Main translator class using the visitor pattern
2. **SQLFragment**: Data structure representing SQL fragment output
3. **TranslationContext**: Context manager tracking state during AST traversal

### Architecture Principles

- **CTE-First Design**: All operations designed for Common Table Expression wrapping
- **Thin Dialects**: Database-specific syntax only, no business logic in dialects
- **Population-First**: All patterns maintain population-scale analytics capability
- **Database Agnostic**: Same translation logic works with DuckDB and PostgreSQL

---

## Core Classes

### ASTToSQLTranslator

**Class**: `fhir4ds.fhirpath.sql.ASTToSQLTranslator`

Translates FHIRPath AST to SQL fragments using the visitor pattern.

#### Constructor

```python
ASTToSQLTranslator(dialect: DatabaseDialect, resource_type: str = "Patient")
```

**Parameters**:
- `dialect` (`DatabaseDialect`): Database dialect instance for SQL generation (e.g., `DuckDBDialect()`, `PostgreSQLDialect()`)
- `resource_type` (`str`, optional): FHIR resource type being translated. Default: `"Patient"`

**Example**:
```python
from fhir4ds.fhirpath.sql import ASTToSQLTranslator
from fhir4ds.dialects import DuckDBDialect

# Create translator for DuckDB
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")

# Create translator for PostgreSQL
from fhir4ds.dialects import PostgreSQLDialect
pg_translator = ASTToSQLTranslator(
    PostgreSQLDialect("postgresql://user:pass@localhost:5432/db"),
    "Observation"
)
```

#### Methods

##### `translate(ast_root: FHIRPathASTNode) -> List[SQLFragment]`

Translate FHIRPath AST to SQL fragments.

**Parameters**:
- `ast_root` (`FHIRPathASTNode`): Root node of the FHIRPath AST to translate

**Returns**:
- `List[SQLFragment]`: List of SQL fragments representing the translated expression chain

**Raises**:
- `NotImplementedError`: If visitor method not yet implemented for node type
- `ValueError`: If AST is invalid or cannot be translated

**Example**:
```python
# Parse and translate a FHIRPath expression
from fhir4ds.fhirpath.parser import FHIRPathParser

parser = FHIRPathParser()
expression = parser.parse("Patient.name.where(use='official')")
ast = expression.get_ast()

# SP-023-006: Translate directly - no adapter needed
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

for fragment in fragments:
    print(f"SQL: {fragment.expression}")
    print(f"Source: {fragment.source_table}")
    print(f"Requires Unnest: {fragment.requires_unnest}")
```

#### Attributes

- `dialect` (`DatabaseDialect`): Database dialect instance for generating database-specific SQL
- `context` (`TranslationContext`): Translation context tracking current state during traversal
- `fragments` (`List[SQLFragment]`): List of generated SQL fragments accumulated during translation
- `resource_type` (`str`): FHIR resource type being translated

---

### SQLFragment

**Class**: `fhir4ds.fhirpath.sql.SQLFragment`

Represents a SQL fragment generated from an AST node.

#### Constructor

```python
SQLFragment(
    expression: str,
    source_table: str = "resource",
    requires_unnest: bool = False,
    is_aggregate: bool = False,
    dependencies: List[str] = [],
    metadata: Dict[str, Any] = {}
)
```

**Parameters**:
- `expression` (`str`, required): The SQL expression representing this operation
- `source_table` (`str`, optional): Source table or CTE that this fragment queries from. Default: `"resource"`
- `requires_unnest` (`bool`, optional): Flag indicating whether this fragment involves array unnesting. Default: `False`
- `is_aggregate` (`bool`, optional): Flag indicating whether this fragment contains aggregation operations. Default: `False`
- `dependencies` (`List[str]`, optional): List of table/CTE names that this fragment depends on. Default: `[]`
- `metadata` (`Dict[str, Any]`, optional): Extensible dictionary for additional metadata. Default: `{}`

**Raises**:
- `ValueError`: If expression or source_table are empty or invalid

**Example**:
```python
from fhir4ds.fhirpath.sql import SQLFragment

# Simple path extraction
fragment = SQLFragment(
    expression="json_extract(resource, '$.name')",
    source_table="patient_resources"
)

# Array filtering with unnesting
fragment = SQLFragment(
    expression="""
        SELECT resource.id, cte_1_item
        FROM resource, LATERAL UNNEST(json_extract(resource, '$.name')) AS cte_1_item
        WHERE json_extract(cte_1_item, '$.use') = 'official'
    """,
    source_table="cte_1",
    requires_unnest=True,
    dependencies=["patient_resources"]
)

# Aggregation
fragment = SQLFragment(
    expression="SELECT COUNT(*) as patient_count FROM patient_resources",
    source_table="patient_resources",
    is_aggregate=True
)
```

#### Methods

##### `add_dependency(dependency: str) -> None`

Add a CTE dependency to this fragment.

**Parameters**:
- `dependency` (`str`): Name of the table or CTE this fragment depends on

**Example**:
```python
fragment = SQLFragment(expression="SELECT * FROM cte_1", source_table="cte_2")
fragment.add_dependency("cte_1")
print(fragment.dependencies)  # ['cte_1']
```

##### `set_metadata(key: str, value: Any) -> None`

Set a metadata value for extensibility.

**Parameters**:
- `key` (`str`): Metadata key
- `value` (`Any`): Metadata value (can be any type)

**Example**:
```python
fragment = SQLFragment(expression="SELECT * FROM patient", source_table="patient")
fragment.set_metadata("estimated_rows", 1000000)
fragment.set_metadata("optimization_hint", "use_index")
print(fragment.metadata)
# {'estimated_rows': 1000000, 'optimization_hint': 'use_index'}
```

##### `get_metadata(key: str, default: Any = None) -> Any`

Get a metadata value with optional default.

**Parameters**:
- `key` (`str`): Metadata key to retrieve
- `default` (`Any`, optional): Default value if key not found. Default: `None`

**Returns**:
- `Any`: Metadata value or default if not found

**Example**:
```python
fragment = SQLFragment(expression="SELECT * FROM patient", source_table="patient")
fragment.set_metadata("rows", 1000)
print(fragment.get_metadata("rows"))  # 1000
print(fragment.get_metadata("missing_key", "not_found"))  # not_found
```

#### Attributes

- `expression` (`str`): The SQL expression representing this operation
- `source_table` (`str`): Source table or CTE that this fragment queries from
- `requires_unnest` (`bool`): Flag indicating whether this fragment involves array unnesting
- `is_aggregate` (`bool`): Flag indicating whether this fragment contains aggregation operations
- `dependencies` (`List[str]`): List of table/CTE names that this fragment depends on
- `metadata` (`Dict[str, Any]`): Extensible dictionary for additional metadata

---

### TranslationContext

**Class**: `fhir4ds.fhirpath.sql.TranslationContext`

Context maintained during AST traversal for SQL generation.

#### Constructor

```python
TranslationContext(
    current_table: str = "resource",
    current_resource_type: str = "Patient",
    parent_path: List[str] = [],
    variable_bindings: Dict[str, str] = {},
    cte_counter: int = 0
)
```

**Parameters**:
- `current_table` (`str`, optional): Current source table or CTE name. Default: `"resource"`
- `current_resource_type` (`str`, optional): FHIR resource type being processed. Default: `"Patient"`
- `parent_path` (`List[str]`, optional): Stack of path components used to build JSON paths. Default: `[]`
- `variable_bindings` (`Dict[str, str]`, optional): Dictionary mapping FHIRPath variable names to SQL representations. Default: `{}`
- `cte_counter` (`int`, optional): Counter for generating unique CTE names. Default: `0`

**Example**:
```python
from fhir4ds.fhirpath.sql import TranslationContext

# Basic initialization
context = TranslationContext(current_resource_type="Patient")
print(context.current_table)  # resource
print(context.current_resource_type)  # Patient

# With custom values
context = TranslationContext(
    current_table="cte_1",
    current_resource_type="Observation",
    parent_path=["component", "value"]
)
```

#### Methods

##### `next_cte_name() -> str`

Generate the next unique CTE name.

**Returns**:
- `str`: Unique CTE name (e.g., `"cte_1"`, `"cte_2"`, `"cte_3"`)

**Example**:
```python
context = TranslationContext()
print(context.next_cte_name())  # cte_1
print(context.next_cte_name())  # cte_2
print(context.next_cte_name())  # cte_3
```

##### `push_path(component: str) -> None`

Add a path component to the path stack.

**Parameters**:
- `component` (`str`): Path component to add (e.g., `"name"`, `"family"`, `"use"`)

**Example**:
```python
context = TranslationContext()
context.push_path("name")
print(context.parent_path)  # ['name']
context.push_path("family")
print(context.parent_path)  # ['name', 'family']
```

##### `pop_path() -> Optional[str]`

Remove and return the last path component from the stack.

**Returns**:
- `Optional[str]`: The removed path component, or `None` if path stack is empty

**Example**:
```python
context = TranslationContext()
context.push_path("name")
context.push_path("family")
print(context.pop_path())  # family
print(context.pop_path())  # name
print(context.pop_path())  # None
```

##### `get_json_path() -> str`

Build a JSON path from the current path stack.

**Returns**:
- `str`: JSON path string with `"$."` prefix (e.g., `"$.name.family"`)
  Returns `"$"` if path stack is empty

**Example**:
```python
context = TranslationContext()
context.push_path("name")
context.push_path("family")
print(context.get_json_path())  # $.name.family
context.pop_path()
print(context.get_json_path())  # $.name
```

##### `bind_variable(variable_name: str, sql_reference: str) -> None`

Bind a FHIRPath variable to its SQL representation.

**Parameters**:
- `variable_name` (`str`): FHIRPath variable name (usually starts with `"$"`)
- `sql_reference` (`str`): SQL expression that represents this variable

**Example**:
```python
context = TranslationContext()
context.bind_variable("$this", "cte_1_item")
context.bind_variable("$index", "idx")
print(context.variable_bindings)
# {'$this': 'cte_1_item', '$index': 'idx'}
```

##### `get_variable(variable_name: str) -> Optional[str]`

Get the SQL representation for a FHIRPath variable.

**Parameters**:
- `variable_name` (`str`): FHIRPath variable name to look up

**Returns**:
- `Optional[str]`: SQL expression for the variable, or `None` if not bound

**Example**:
```python
context = TranslationContext()
context.bind_variable("$this", "cte_1_item")
print(context.get_variable("$this"))  # cte_1_item
print(context.get_variable("$missing"))  # None
```

##### `clear_variables() -> None`

Clear all variable bindings.

**Example**:
```python
context = TranslationContext()
context.bind_variable("$this", "cte_1_item")
context.bind_variable("$index", "idx")
print(len(context.variable_bindings))  # 2
context.clear_variables()
print(len(context.variable_bindings))  # 0
```

##### `reset() -> None`

Reset context to initial state.

Resets all context state to default values: clears path stack, clears variable bindings, resets current table to `"resource"`, and resets CTE counter to `0`.

**Example**:
```python
context = TranslationContext()
context.push_path("name")
context.bind_variable("$this", "cte_1_item")
context.next_cte_name()  # cte_1
context.reset()
print(context.parent_path)  # []
print(context.variable_bindings)  # {}
print(context.cte_counter)  # 0
print(context.next_cte_name())  # cte_1
```

#### Attributes

- `current_table` (`str`): Current source table or CTE name being queried from
- `current_resource_type` (`str`): FHIR resource type being processed
- `parent_path` (`List[str]`): Stack of path components used to build JSON paths
- `variable_bindings` (`Dict[str, str]`): Dictionary mapping FHIRPath variable names to SQL representations
- `cte_counter` (`int`): Counter for generating unique CTE names

---

## Note: Direct Translation (SP-023-006)

As of SP-023-006, the translator works **directly** with `EnhancedASTNode` from the parser.
The `ASTAdapter` class and `convert_enhanced_ast_to_fhirpath_ast()` function have been removed.

**New Workflow**:
```python
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql import ASTToSQLTranslator
from fhir4ds.dialects import DuckDBDialect

parser = FHIRPathParser()
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")

# Parse and translate directly
ast = parser.parse("Patient.name").get_ast()
fragments = translator.translate(ast)  # No adapter needed!
```

---

## Complete Workflow Example

### End-to-End Translation

```python
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql import (
    ASTToSQLTranslator,
    # (Removed - SP-023-006)
)
from fhir4ds.dialects import DuckDBDialect

# Step 1: Parse FHIRPath expression
parser = FHIRPathParser()
expression = parser.parse("Patient.name.where(use='official').first()")

# Step 2: Get enhanced AST from parser
enhanced_ast = expression.get_ast()

# Step 3: Convert to translator-compatible AST
ast = enhanced_ast  # SP-023-006: Direct translation

# Step 4: Create translator with database dialect
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")

# Step 5: Translate to SQL fragments
fragments = translator.translate(ast)

# Step 6: Process fragments
for i, fragment in enumerate(fragments):
    print(f"Fragment {i+1}:")
    print(f"  Expression: {fragment.expression}")
    print(f"  Source Table: {fragment.source_table}")
    print(f"  Requires Unnest: {fragment.requires_unnest}")
    print(f"  Is Aggregate: {fragment.is_aggregate}")
    print(f"  Dependencies: {fragment.dependencies}")
    print()
```

### Multi-Database Translation

```python
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql import (
    ASTToSQLTranslator,
    # (Removed - SP-023-006)
)
from fhir4ds.dialects import DuckDBDialect, PostgreSQLDialect

# Parse expression once
parser = FHIRPathParser()
expression = parser.parse("Patient.active = true")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

# Translate for DuckDB
duckdb_translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
duckdb_fragments = duckdb_translator.translate(ast)
print("DuckDB SQL:")
print(duckdb_fragments[0].expression)

# Translate for PostgreSQL
pg_connection = "postgresql://user:pass@localhost:5432/db"
pg_translator = ASTToSQLTranslator(PostgreSQLDialect(pg_connection), "Patient")
pg_fragments = pg_translator.translate(ast)
print("\nPostgreSQL SQL:")
print(pg_fragments[0].expression)
```

---

## Error Handling

### Common Exceptions

#### NotImplementedError

Raised when translator encounters an AST node type that doesn't have a corresponding visitor method implemented yet.

```python
try:
    fragments = translator.translate(ast)
except NotImplementedError as e:
    print(f"Node type not yet supported: {e}")
```

#### ValueError

Raised when AST is invalid or cannot be translated.

```python
try:
    fragment = SQLFragment(expression="", source_table="table")
except ValueError as e:
    print(f"Invalid SQLFragment: {e}")
```

### Best Practices

1. **Always validate input**: Ensure AST is not `None` before translation
2. **Handle exceptions gracefully**: Wrap translation in try-except blocks
3. **Check fragment flags**: Verify `requires_unnest` and `is_aggregate` before processing
4. **Validate SQL syntax**: Test generated SQL against target database

---

## Performance Considerations

### Translation Performance

- **Translation Speed**: <10ms for typical FHIRPath expressions
- **Memory Usage**: <1KB per SQLFragment
- **Scalability**: Linear time complexity O(n) for n AST nodes

### Optimization Tips

1. **Reuse translator instances**: Create once, translate multiple times
2. **Batch translations**: Process multiple expressions in sequence
3. **Cache parsed ASTs**: Avoid re-parsing identical expressions
4. **Use appropriate dialect**: Match database dialect to target environment

---

## Thread Safety

- **ASTToSQLTranslator**: NOT thread-safe. Create separate instances per thread.
- **TranslationContext**: NOT thread-safe. Each translation should use its own context.
- **SQLFragment**: Immutable after creation. Thread-safe for reading.
- **ASTAdapter**: Stateless. Thread-safe.

---

## Version Compatibility

- **Python**: 3.8+
- **Dependencies**:
  - `fhir4ds.fhirpath.parser` (PEP-002)
  - `fhir4ds.dialects` (Database dialect support)
  - `fhir4ds.fhirpath.ast` (AST node definitions)

---

## See Also

- [FHIRPath Parser Integration Guide](../fhirpath-parser-integration.md)
- [Usage Examples](translator-usage-examples.md)
- [Integration Guide for PEP-004](translator-integration-guide.md)
- [Troubleshooting Guide](translator-troubleshooting.md)
- [PEP-003 Specification](../../project-docs/peps/accepted/pep-003-ast-to-sql-translator.md)

---

**Last Updated**: 2025-10-02
**Task**: SP-005-023 - API Documentation and Examples
