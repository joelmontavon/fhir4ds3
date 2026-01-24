# Unified SQLGenerator Design

**Task ID**: SP-023-001
**Sprint**: 023
**Created**: 2025-12-16
**Status**: Design Review
**Author**: Junior Developer

---

## Overview

The Unified SQLGenerator is a proposed architectural consolidation that replaces the current 4-component FHIRPath-to-SQL pipeline with a single cohesive component. This design eliminates intermediate data formats and the metadata loss problems that occur at component boundaries.

### Problem Statement

The current architecture has 4 components with metadata being passed between them:

```
┌─────────────┐    ┌────────────┐    ┌─────────────┐    ┌───────────────┐
│ AST Adapter │ → │ Translator │ → │ CTE Builder │ → │ CTE Assembler │
└─────────────┘    └────────────┘    └─────────────┘    └───────────────┘
     │                   │                  │                   │
     ▼                   ▼                  ▼                   ▼
 Core AST          SQLFragments          CTEs             Final SQL
```

**Identified Problems:**
1. **Metadata Loss**: Information like `function_name`, `result_type` gets lost at component boundaries
2. **Limited Context**: Translator produces fragments without knowing how they'll be assembled
3. **Fragile Fixes**: CTE Builder doesn't know original expression intent, requiring heuristics
4. **Collection Aggregation Bug**: Had to add complex logic to CTE Assembler (SP-022-001) to detect when unnested collections need aggregation

### Solution: Unified Component

Consolidate into a single `SQLGenerator` class that has complete context throughout the translation process:

```
┌───────────────────────────────────────────────────┐
│                  SQLGenerator                      │
│                                                    │
│  Expression → Parse → Translate → Assemble → SQL  │
└───────────────────────────────────────────────────┘
```

---

## Interface

### Public Methods

```python
class SQLGenerator:
    """Unified FHIRPath expression to SQL generator.

    Combines AST traversal, SQL translation, and CTE assembly into a single
    component with complete context throughout the translation process.
    """

    def __init__(
        self,
        dialect: DatabaseDialect,
        resource_type: str,
        *,
        parser: Optional[FHIRPathParser] = None
    ) -> None:
        """Initialize the SQL generator.

        Args:
            dialect: Database dialect for syntax generation (DuckDB/PostgreSQL)
            resource_type: FHIR resource type (e.g., "Patient", "Observation")
            parser: Optional custom parser instance for testing
        """

    def generate(self, expression: str) -> str:
        """Convert FHIRPath expression to executable SQL.

        This is the primary entry point. Takes a FHIRPath expression string
        and returns a complete SQL query ready for execution.

        Args:
            expression: FHIRPath expression string (e.g., "Patient.name.given.first()")

        Returns:
            Complete SQL query string with CTEs as needed

        Raises:
            FHIRPathParseError: If expression cannot be parsed
            FHIRPathTranslationError: If expression cannot be translated to SQL

        Example:
            >>> generator = SQLGenerator(DuckDBDialect(), "Patient")
            >>> sql = generator.generate("Patient.name.given.first()")
            >>> # Returns: WITH cte_1 AS (...) SELECT * FROM cte_1;
        """

    def generate_with_diagnostics(self, expression: str) -> GenerationResult:
        """Generate SQL with detailed diagnostic information.

        Returns structured result including:
        - Generated SQL
        - Parse tree (for debugging)
        - CTE chain information
        - Timing metrics per stage

        Args:
            expression: FHIRPath expression string

        Returns:
            GenerationResult dataclass with SQL and diagnostics
        """
```

### Constructor Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dialect` | `DatabaseDialect` | Yes | Database dialect for SQL syntax |
| `resource_type` | `str` | Yes | FHIR resource type being queried |
| `parser` | `FHIRPathParser` | No | Custom parser for testing |

### Return Types

```python
@dataclass
class GenerationResult:
    """Result of SQL generation with diagnostics."""

    sql: str                    # Complete generated SQL
    expression: str             # Original FHIRPath expression
    cte_count: int              # Number of CTEs generated
    requires_unnest: bool       # Whether array operations present
    is_aggregate: bool          # Whether aggregation present
    timings_ms: Dict[str, float]  # Per-stage timing

    # Optional debug info
    parse_tree: Optional[Any] = None
    cte_chain: Optional[List[str]] = None
```

---

## Internal Architecture

### Class Structure

```
┌──────────────────────────────────────────────────────────────────┐
│                         SQLGenerator                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Attributes:                                                      │
│  ─────────────                                                    │
│    dialect: DatabaseDialect       # Syntax generation             │
│    resource_type: str             # FHIR resource type            │
│    parser: FHIRPathParser         # Expression parser             │
│    type_registry: TypeRegistry    # FHIR type metadata            │
│    structure_loader: StructureDefinitionLoader  # Array detection │
│                                                                   │
│  Generation State (per-call):                                     │
│  ────────────────────────────                                     │
│    _ctes: List[CTEDefinition]     # Accumulated CTEs              │
│    _cte_counter: int              # Unique naming                 │
│    _current_source: str           # Current table/CTE reference   │
│    _path_stack: List[str]         # JSON path components          │
│    _variable_bindings: Dict[str, VariableBinding]  # $this, etc   │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Public API:                                                      │
│  ──────────                                                       │
│    generate(expression: str) -> str                               │
│    generate_with_diagnostics(expression: str) -> GenerationResult │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Path Navigation:                                                 │
│  ────────────────                                                 │
│    _generate_path(node: IdentifierNode) -> str                    │
│    _generate_path_with_arrays(components: List[str]) -> str       │
│    _generate_polymorphic_path(property: str) -> str               │
│                                                                   │
│  Function Handling:                                               │
│  ──────────────────                                               │
│    _generate_function(node: FunctionCallNode) -> str              │
│    _generate_where(node: FunctionCallNode) -> str                 │
│    _generate_first(node: FunctionCallNode) -> str                 │
│    _generate_last(node: FunctionCallNode) -> str                  │
│    _generate_count(node: FunctionCallNode) -> str                 │
│    _generate_exists(node: FunctionCallNode) -> str                │
│    _generate_empty(node: FunctionCallNode) -> str                 │
│    ... (other FHIRPath functions)                                 │
│                                                                   │
│  Operators:                                                       │
│  ──────────                                                       │
│    _generate_comparison(node: OperatorNode) -> str                │
│    _generate_boolean(node: OperatorNode) -> str                   │
│    _generate_arithmetic(node: OperatorNode) -> str                │
│    _generate_union(node: OperatorNode) -> str                     │
│                                                                   │
│  CTE Management:                                                  │
│  ───────────────                                                  │
│    _add_cte(name: str, query: str, depends_on: List[str]) -> None │
│    _generate_unnest_cte(array_expr: str, alias: str) -> str       │
│    _assemble_final_sql() -> str                                   │
│    _generate_with_clause() -> str                                 │
│    _generate_final_select() -> str                                │
│                                                                   │
│  Helpers:                                                         │
│  ────────                                                         │
│    _next_cte_name() -> str                                        │
│    _build_json_path() -> str                                      │
│    _is_array_element(resource_type: str, path: str) -> bool       │
│    _needs_aggregation(function_name: str) -> bool                 │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Method Categories

#### 1. Path Navigation Methods

Handle identifier and path expressions:

```python
def _generate_path(self, node: IdentifierNode) -> str:
    """Generate SQL for path navigation.

    Handles:
    - Simple paths: Patient.birthDate
    - Nested paths: Patient.name.family
    - Polymorphic paths: Observation.value (→ COALESCE of variants)
    - Array paths: Patient.name.given (→ UNNEST)
    """

def _generate_path_with_arrays(self, components: List[str]) -> str:
    """Handle path that traverses arrays.

    Generates UNNEST CTEs inline when arrays are encountered.
    Tracks ordering columns for proper array element ordering.
    """
```

#### 2. Function Handling Methods

Each FHIRPath function has a dedicated handler:

```python
def _generate_function(self, node: FunctionCallNode) -> str:
    """Dispatch to specific function handler based on function name."""
    handlers = {
        "where": self._generate_where,
        "first": self._generate_first,
        "last": self._generate_last,
        "count": self._generate_count,
        "exists": self._generate_exists,
        "empty": self._generate_empty,
        "select": self._generate_select,
        # ... other functions
    }
    return handlers[node.function_name.lower()](node)

def _generate_where(self, node: FunctionCallNode) -> str:
    """Generate WHERE filtering with LATERAL UNNEST if on array."""

def _generate_count(self, node: FunctionCallNode) -> str:
    """Generate COUNT aggregation.

    KEY FIX: When counting an unnested collection, generates proper
    aggregation CTE inline (not as separate assembly step).
    """
```

#### 3. Operator Methods

Handle FHIRPath operators:

```python
def _generate_comparison(self, node: OperatorNode) -> str:
    """Generate comparison operators (=, !=, <, >, <=, >=)."""

def _generate_boolean(self, node: OperatorNode) -> str:
    """Generate boolean operators (and, or, not, implies)."""

def _generate_arithmetic(self, node: OperatorNode) -> str:
    """Generate arithmetic operators (+, -, *, /, div, mod)."""
```

#### 4. CTE Management Methods

Generate CTEs inline during traversal:

```python
@dataclass
class CTEDefinition:
    """Internal CTE tracking structure."""
    name: str
    query: str
    depends_on: List[str]
    has_ordering: bool = False
    ordering_column: Optional[str] = None

def _add_cte(self, name: str, query: str, depends_on: List[str]) -> None:
    """Register a CTE in the generation chain."""
    self._ctes.append(CTEDefinition(name=name, query=query, depends_on=depends_on))

def _generate_unnest_cte(self, array_expr: str, alias: str) -> str:
    """Generate UNNEST CTE with ordering preservation.

    Creates CTE with:
    - id column preservation
    - ROW_NUMBER() for array ordering
    - Proper alias for unnested item
    """
    cte_name = self._next_cte_name()
    order_col = f"{cte_name}_order"

    unnest_clause = self.dialect.generate_lateral_unnest(
        self._current_source, array_expr, alias
    )

    query = f"""
        SELECT {self._current_source}.id,
               {self._current_source}.resource,
               ROW_NUMBER() OVER () AS {order_col},
               {alias}
        FROM {self._current_source}, {unnest_clause}
    """

    self._add_cte(cte_name, query, [self._current_source])
    self._current_source = cte_name
    return cte_name
```

---

## Data Flow

### Simple Expression: `Patient.birthDate`

```
Input: "Patient.birthDate"

1. Parse → IdentifierNode(identifier="Patient.birthDate")

2. _generate_path()
   - Skip "Patient" (root resource type)
   - Check: is "birthDate" an array? → No
   - Generate: json_extract_string(resource, '$.birthDate')

3. _assemble_final_sql()
   - No CTEs needed (no arrays, no functions)
   - Direct query: SELECT id, json_extract_string(resource, '$.birthDate') AS result FROM resource

Output:
    SELECT id, json_extract_string(resource, '$.birthDate') AS result
    FROM resource;
```

### Path with Array: `Patient.name.given`

```
Input: "Patient.name.given"

1. Parse → IdentifierNode(identifier="Patient.name.given")

2. _generate_path_with_arrays()
   - Skip "Patient"
   - Check "name": is array? → Yes
     → _generate_unnest_cte()
       Creates cte_1 with LATERAL UNNEST
   - Check "given": is array? → Yes
     → _generate_unnest_cte()
       Creates cte_2 with LATERAL UNNEST

3. _assemble_final_sql()
   - Build WITH clause from accumulated CTEs
   - Generate final SELECT from cte_2

Output:
    WITH
      cte_1 AS (
        SELECT resource.id, resource.resource,
               ROW_NUMBER() OVER () AS cte_1_order,
               name_item
        FROM resource, LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item
      ),
      cte_2 AS (
        SELECT cte_1.id, cte_1.resource,
               cte_1_order,
               ROW_NUMBER() OVER (PARTITION BY cte_1.id, cte_1_order) AS cte_2_order,
               given_item AS result
        FROM cte_1, LATERAL UNNEST(json_extract(name_item, '$.given')) AS given_item
      )
    SELECT * FROM cte_2 ORDER BY cte_1_order, cte_2_order;
```

### Complex Expression: `Patient.name.given.count()`

```
Input: "Patient.name.given.count()"

1. Parse → FunctionCallNode(
     function_name="count",
     target=IdentifierNode("Patient.name.given")
   )

2. _generate_function() → _generate_count()
   - First, generate target: Patient.name.given
     → Creates cte_1 (name UNNEST) and cte_2 (given UNNEST)

   - count() on unnested collection needs aggregation
   - KEY: We have full context here, know we're counting unnested items

   → Create aggregation CTE inline:
     cte_3: SELECT id, resource, COUNT(*) as result
            FROM cte_2
            GROUP BY id, resource

3. _assemble_final_sql()
   - Assemble all 3 CTEs
   - Final SELECT from cte_3

Output:
    WITH
      cte_1 AS (...name unnest...),
      cte_2 AS (...given unnest...),
      cte_3 AS (
        SELECT cte_2.id, cte_2.resource, COUNT(*) AS result
        FROM cte_2
        GROUP BY cte_2.id, cte_2.resource
      )
    SELECT * FROM cte_3;
```

### Chained Functions: `Patient.name.where(use='official').given.first()`

```
Input: "Patient.name.where(use='official').given.first()"

1. Parse → FunctionCallNode chain

2. Process chain left-to-right:

   a) Patient.name → cte_1 (UNNEST names)

   b) where(use='official') → cte_2
      SELECT ... FROM cte_1 WHERE json_extract(name_item, '$.use') = 'official'

   c) .given → cte_3 (UNNEST given from filtered names)

   d) first() → cte_4
      KEY: first() on unnested collection
      → Filter by ordering column: WHERE cte_3_order = 1

3. _assemble_final_sql()

Output:
    WITH
      cte_1 AS (...unnest names...),
      cte_2 AS (
        SELECT * FROM cte_1 WHERE json_extract(name_item, '$.use') = 'official'
      ),
      cte_3 AS (...unnest given from cte_2...),
      cte_4 AS (
        SELECT * FROM cte_3 WHERE cte_3_order = 1
      )
    SELECT * FROM cte_4 ORDER BY cte_1_order;
```

---

## Key Design Decisions

### Decision 1: Single Component vs Pipeline

**Context**: Current architecture has 4 separate components with intermediate data formats.

**Decision**: Consolidate into single SQLGenerator class.

**Rationale**:
- Eliminates metadata loss at component boundaries
- Full context available throughout translation
- Simpler to understand and maintain
- Enables proper handling of collection aggregation

**Consequences**:
- Larger single class (~2000-3000 lines estimated)
- Requires careful internal organization
- Testing must cover end-to-end scenarios

### Decision 2: Inline CTE Generation

**Context**: Current approach generates all CTEs in separate step after translation.

**Decision**: Generate CTEs inline during AST traversal.

**Rationale**:
- CTEs are created at point of need with full context
- Can immediately add aggregation when count() on collection
- Ordering columns tracked naturally through traversal

**Consequences**:
- CTEs accumulated in list during traversal
- Assembly step only formats the WITH clause
- More complex traversal logic

### Decision 3: No Intermediate SQLFragment

**Context**: Current translator produces SQLFragment objects that CTE Builder consumes.

**Decision**: Remove SQLFragment as public interface. Keep simple internal tracking only.

**Rationale**:
- SQLFragment was designed for cross-component communication
- With single component, simpler internal state suffices
- Eliminates need to encode all context in fragment metadata

**Consequences**:
- Breaking change for any code depending on SQLFragment
- Executor.py will need updates to use new interface
- Simplifies mental model

### Decision 4: Preserve Thin Dialect Principle

**Context**: Dialects must contain only syntax, no business logic.

**Decision**: Maintain strict thin dialect boundary.

**Rationale**:
- Consistent with unified FHIRPath architecture
- Enables easy database portability
- Business logic stays testable in one place

**Consequences**:
- Dialect interface unchanged
- All new business logic in SQLGenerator
- Same syntax methods: `json_extract`, `generate_lateral_unnest`, etc.

### Decision 5: Keep Parser and AST Adapter External

**Context**: Could potentially merge parser into generator.

**Decision**: Keep FHIRPathParser and ASTAdapter as separate components.

**Rationale**:
- Parser is well-tested and stable (PEP-002)
- AST Adapter handles complex node type conversion
- Generator focuses on SQL generation only

**Consequences**:
- SQLGenerator depends on parser and adapter
- Maintains separation of parsing from translation
- Parser can evolve independently

---

## Migration Path

### Phase 1: Create SQLGenerator (New Component)

1. Create `fhir4ds/fhirpath/sql/generator.py`
2. Implement core interface: `generate()` method
3. Port path navigation logic from Translator
4. Add inline CTE generation
5. Unit tests for new component

### Phase 2: Port Function Handlers

1. Port function handlers from Translator one by one
2. Integrate collection aggregation logic
3. Test each function against compliance suite
4. Document any behavior changes

### Phase 3: Port Operators

1. Port operator handlers from Translator
2. Handle temporal operations
3. Handle collection operators (union, intersect)
4. Comprehensive operator tests

### Phase 4: Update Executor

1. Modify `FHIRPathExecutor` to use `SQLGenerator`
2. Update `execute_with_details()` for new diagnostics
3. Backward compatibility for existing tests
4. Performance validation

### Phase 5: Deprecate Old Components

1. Mark Translator, CTEBuilder, CTEAssembler as deprecated
2. Update documentation
3. Migration guide for any external users
4. Remove after deprecation period

---

## Testing Strategy

### Unit Tests

1. **Path Navigation**
   - Simple paths: `Patient.birthDate`
   - Nested paths: `Patient.name.family`
   - Array paths: `Patient.name.given`
   - Polymorphic paths: `Observation.value`

2. **Function Handlers**
   - Test each function in isolation
   - Test on scalar vs collection inputs
   - Test chained functions

3. **Operators**
   - All comparison operators
   - Boolean operators
   - Arithmetic operators
   - Union operator

4. **CTE Generation**
   - Correct WITH clause formatting
   - Proper dependency ordering
   - Ordering column preservation

### Integration Tests

1. **End-to-End**
   - Parse → Generate → Execute
   - Both DuckDB and PostgreSQL
   - Verify identical results

2. **Compliance Tests**
   - Official FHIRPath test suite
   - SQL-on-FHIR test cases
   - Regression tests

### Performance Tests

1. **Generation Speed**
   - < 10ms for typical expressions
   - < 50ms for complex expressions

2. **SQL Execution**
   - Verify population-scale performance
   - 10x+ improvement over naive approach

---

## Appendix: Current vs New Architecture Comparison

### Current: 4 Components

```python
# Current executor.py (simplified)
def execute_with_details(self, expression: str):
    parsed = self.parser.parse(expression)
    enhanced_ast = parsed.get_ast()
    fhirpath_ast = self.adapter.convert(enhanced_ast)
    fragments = self.translator.translate(fhirpath_ast)  # List[SQLFragment]
    ctes = self.cte_builder.build_cte_chain(fragments)   # List[CTE]
    sql = self.cte_assembler.assemble_query(ctes)        # str
    results = self.dialect.execute_query(sql)
    return results
```

**Problems:**
- 3 handoffs where metadata can be lost
- `fragments` doesn't capture full context
- CTE Builder infers intent from fragment metadata
- Assembler needs heuristics for aggregation detection

### New: Single Component

```python
# New executor.py (simplified)
def execute_with_details(self, expression: str):
    result = self.generator.generate_with_diagnostics(expression)
    results = self.dialect.execute_query(result.sql)
    return {
        "sql": result.sql,
        "results": results,
        "timings_ms": result.timings_ms,
        # ... other diagnostics
    }
```

**Benefits:**
- Single component has full context
- No intermediate formats to maintain
- Aggregation generated at point of need
- Simpler executor code

---

## References

- **Task**: `project-docs/plans/tasks/SP-023-001-design-unified-sql-generator.md`
- **Current Translator**: `fhir4ds/fhirpath/sql/translator.py`
- **Current CTE Infrastructure**: `fhir4ds/fhirpath/sql/cte.py`
- **Executor**: `fhir4ds/fhirpath/sql/executor.py`
- **Collection Aggregation Fix**: SP-022-001

---

**Document Status**: Ready for Review
**Next Steps**: Senior Architect review and approval before implementation begins
