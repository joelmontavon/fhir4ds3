# PEP-003: FHIRPath AST-to-SQL Translator

```
PEP: 003
Title: FHIRPath AST-to-SQL Translator - Foundation for CTE-First SQL Generation
Author: Senior Solution Architect/Engineer <architect@fhir4ds.org>
Status: Accepted
Type: Standard
Created: 29-09-2025
Updated: 29-09-2025
Approved: 29-09-2025
Version: 1.0
```

---

## Abstract

This PEP proposes implementing the **AST-to-SQL Translator**, the critical component that converts FHIRPath Abstract Syntax Trees (AST) into database-specific SQL fragments. This translator serves as the foundation of FHIR4DS's CTE-first SQL generation architecture, enabling population-scale healthcare analytics by transforming FHIRPath expressions into optimized Common Table Expressions (CTEs).

The AST-to-SQL Translator bridges the gap between the FHIRPath parser (PEP-002, completed) and the SQL execution layer, using the visitor pattern to traverse AST nodes and generate SQL by calling database dialect methods. The translator outputs a sequence of SQL fragments representing each logical operation, which subsequent components (CTE Builder, CTE Optimizer, CTE Assembler - planned in future PEPs) will combine into monolithic SQL queries.

This implementation delivers the core translation logic needed to achieve FHIR4DS's architectural goal of converting N FHIRPath expressions into 1 optimized SQL query, enabling 10x+ performance improvements for population-scale healthcare analytics. The translator handles complex FHIRPath operations including path navigation, array unnesting, filtering, aggregation, and type operations while maintaining the thin dialect architecture principle.

**Key Benefits**: Completes the unified FHIRPath execution pipeline, enables SQL-on-FHIR and CQL implementations, maintains population-scale analytics capability, and provides database-agnostic translation through dialect methods.

## Motivation

### Current Situation and Limitations

FHIR4DS has completed the FHIRPath parser implementation (PEP-002) that creates enhanced AST structures with metadata for SQL generation. However, **no component exists to convert these AST trees into SQL**. The current `sql/generator.py` only handles simple SQL-on-FHIR ViewDefinitions through basic JSON path extraction - it cannot translate general FHIRPath expressions or generate the CTE-based SQL needed for population-scale analytics.

This creates critical gaps:

1. **No FHIRPath Expression Execution**: Cannot execute FHIRPath expressions like `Patient.name.where(use='official').family` against database
2. **No Population-Scale Analytics**: Missing CTE generation means cannot achieve 10x+ performance improvements promised by architecture
3. **SQL-on-FHIR Blocked**: Cannot process ViewDefinitions with embedded FHIRPath expressions
4. **CQL Translation Blocked**: Cannot translate CQL defines to SQL (CQL uses FHIRPath for path navigation)
5. **Architecture Gap**: Parser → ??? → Database execution (missing critical translation layer)

### The Architectural Context

The unified FHIRPath architecture requires this translation pipeline:

```
┌─────────────────────────────────────────────┐
│  FHIRPath Expression String                 │
│  "Patient.name.where(use='official')"       │
└─────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│  PARSER (PEP-002 ✅ COMPLETE)               │
│  Creates Enhanced AST with metadata         │
└─────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│  AST-to-SQL Translator (PEP-003 ❌ MISSING) │
│  Converts AST nodes → SQL fragments         │
└─────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│  CTE Builder (Future PEP-004 - Not Started) │
│  Wraps SQL fragments in CTE structures      │
└─────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│  CTE Assembler (Future PEP-004)             │
│  Combines CTEs into monolithic SQL query    │
└─────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│  Dialect Layer (PEP-002 ✅ COMPLETE)        │
│  Database-specific SQL execution            │
└─────────────────────────────────────────────┘
```

**PEP-003 fills the critical gap between parser and SQL generation.**

### Consequences of Not Implementing

Without the AST-to-SQL Translator:

- **Cannot execute FHIRPath expressions** beyond trivial path navigation
- **Cannot achieve population-scale performance** (no CTE generation = no 10x improvements)
- **Cannot implement SQL-on-FHIR v2.0** (requires FHIRPath expression translation)
- **Cannot implement CQL framework** (CQL depends on FHIRPath translation)
- **Cannot implement quality measures** (eCQI measures require CQL execution)
- **Architecture incomplete** (missing critical component in unified FHIRPath design)

### Strategic Benefits

Implementing the AST-to-SQL Translator provides:

1. **Completes Execution Pipeline**: Parser (done) → Translator (PEP-003) → CTE Builder (future) → Execution (done)
2. **Enables Population Analytics**: Foundation for CTE-first SQL generation and 10x+ performance improvements
3. **Unblocks Higher Specifications**: Enables SQL-on-FHIR and CQL implementations (next PEPs)
4. **Maintains Architecture Principles**: Thin dialects (translator calls dialect methods for syntax)
5. **Database Agnostic**: Translation logic separate from SQL syntax (handled by dialects)
6. **Foundation for Optimization**: Subsequent PEPs can optimize SQL fragments without changing translator

### Use Cases

#### Use Case 1: FHIRPath Expression Execution
- **Current behavior**: Cannot execute `Patient.name.where(use='official').family` - no translation to SQL
- **Proposed behavior**: Translator converts expression to SQL fragments, executes against database
- **Benefit**: Enables FHIRPath-based queries for population health analytics

**Example Translation**:
```
Expression: Patient.name.where(use='official').family

Translator Output (SQL Fragments):
Fragment 1: SELECT id, json_extract(resource, '$.name') as names FROM patient_resources
Fragment 2: SELECT id, name_item FROM <cte_1>, LATERAL UNNEST(names) WHERE json_extract(name_item, '$.use') = 'official'
Fragment 3: SELECT id, json_extract(name_item, '$.family') as family FROM <cte_2>
```

#### Use Case 2: SQL-on-FHIR ViewDefinition Processing
- **Current behavior**: ViewDefinitions with FHIRPath expressions cannot be processed (only basic JSON paths)
- **Proposed behavior**: Translator converts embedded FHIRPath expressions to SQL for ViewDefinition execution
- **Benefit**: Complete SQL-on-FHIR v2.0 specification compliance

**Example**:
```json
{
  "select": [{
    "column": [{
      "path": "name.where(use='official').family.first()",
      "name": "official_family_name"
    }]
  }]
}
```
Translator converts `name.where(...).family.first()` to SQL fragments.

#### Use Case 3: CQL Expression Translation Foundation
- **Current behavior**: Cannot translate CQL expressions (CQL uses FHIRPath for navigation)
- **Proposed behavior**: CQL translator uses AST-to-SQL Translator for path navigation
- **Benefit**: Enables CQL-based quality measure calculation

**Example CQL**:
```cql
define "Diabetes Patients":
  [Condition: "Diabetes"] C
  where C.clinicalStatus = 'active'
```
The path `C.clinicalStatus` is FHIRPath, translated to SQL by this component.

## Rationale

### Design Principles

#### 1. **Separation of Concerns**
- **Translator handles logic**: What operations to perform (filter, extract, aggregate)
- **Dialects handle syntax**: How to express operations in SQL (DuckDB vs PostgreSQL)
- **CTE Builder handles structure**: How to organize SQL into CTEs (future PEP)

#### 2. **Visitor Pattern Implementation**
- Follows established AST visitor pattern from PEP-002 evaluator
- Each AST node type has corresponding `visit_*` method
- Maintains traversal context (current table, path, variables)
- Enables clean separation of node types and translation logic

#### 3. **SQL Fragment Output**
- Translator outputs `SQLFragment` objects, not complete SQL queries
- Fragments are self-contained units representing single operations
- Fragments carry metadata (source table, dependencies, flags)
- Future components (CTE Builder, Assembler) combine fragments into complete queries

#### 4. **Database-Agnostic Translation**
- Translator calls dialect methods for database-specific syntax
- Example: `dialect.extract_json_field(column, path)` instead of hardcoded `json_extract()`
- Maintains thin dialect architecture (no business logic in dialects)
- Enables consistent behavior across DuckDB and PostgreSQL

#### 5. **Population-First Design**
- Array operations use indexing (`[0]`), not LIMIT 1
- Maintains population-scale capability (no per-patient queries)
- Unnesting handled in SQL (LATERAL UNNEST), not application layer
- Default to bulk operations over entire resource collections

#### 6. **Sequential Operation Chain**
- Multi-step expressions emit sequence of fragments
- Each fragment represents one logical operation
- Dependencies explicit (Fragment N depends on Fragment N-1)
- Simpler than nested tree structure for CTE generation

### Why This Solution Over Alternatives

**Alternative 1: Extend In-Memory Evaluator to Generate SQL**
- **Rejected**: Mixing concerns (memory execution + SQL generation) in single component
- **This solution**: Separate translator focuses solely on SQL generation, cleaner architecture

**Alternative 2: String-Based SQL Template System**
- **Rejected**: Template strings difficult to maintain, test, and optimize
- **This solution**: Structured visitor pattern with strongly-typed SQL fragments

**Alternative 3: Generate Complete SQL Immediately**
- **Rejected**: Translator would need to handle CTE structure, assembly, optimization
- **This solution**: Translator produces fragments, future components handle structure/optimization

**Alternative 4: Single SQLFragment per Expression**
- **Rejected**: Complex expressions need multiple CTEs, single fragment insufficient
- **This solution**: Sequence of fragments naturally maps to CTE chain

### Architectural Alignment

This implementation directly supports FHIR4DS's unified FHIRPath architecture:

- ✅ **FHIRPath-First**: Translator is the core component enabling FHIRPath execution via SQL
- ✅ **CTE-First Design**: Translator outputs designed for CTE wrapping (by future CTE Builder)
- ✅ **Thin Dialects**: Translator calls dialect methods, dialects contain only syntax differences
- ✅ **Population Analytics**: Translation preserves population-scale capability (no LIMIT 1 anti-patterns)
- ✅ **Database Agnostic**: Same translator works with DuckDB and PostgreSQL via dialect abstraction

### Relationship to Future PEPs

This PEP focuses specifically on **AST → SQL Fragment translation**. Future PEPs will build on this foundation:

**PEP-004: CTE Generation System** (Planned)
- **CTE Builder**: Wraps SQL fragments in CTE structures
- **CTE Optimizer**: Optimizes CTE chains (merge simple CTEs, push predicates)
- **CTE Assembler**: Combines CTEs into monolithic SQL queries
- **CTE Dependency Resolver**: Handles complex CQL dependency graphs

**Why separate PEPs?**
- **Focused scope**: Each PEP tackles one well-defined component
- **Incremental delivery**: Can implement and test translator independently
- **Clear dependencies**: PEP-004 depends on PEP-003 translator output
- **Parallel development**: Different developers can work on each PEP

**Design decisions applicable to future PEPs** (documented here for architectural context):
- Translator outputs list of fragments (not nested structure)
- Translator generates complete unnest SQL (not just marking "needs unnest")
- Fragments carry metadata for optimization (aggregation, unnesting, dependencies)
- Future CTE Builder will wrap fragments, not modify translation logic

## Specification

### Overview

The AST-to-SQL Translator is a visitor-based component that traverses FHIRPath AST nodes (created by PEP-002 parser) and generates database-specific SQL fragments by calling dialect methods. The translator maintains translation context (current table, path, variables) and outputs a sequence of `SQLFragment` objects representing the logical operations in the expression.

### Core Components

#### 1. SQLFragment Data Structure

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SQLFragment:
    """
    Represents a SQL fragment generated from an AST node

    This is the fundamental output unit of the translator
    """
    expression: str                          # The SQL expression
    source_table: str = "resource"           # Source table/CTE this refers to
    requires_unnest: bool = False            # Array operation needing unnesting
    is_aggregate: bool = False               # Aggregation function (COUNT, SUM, etc.)
    dependencies: List[str] = field(default_factory=list)  # CTE dependencies
    metadata: Dict[str, Any] = field(default_factory=dict) # Additional metadata
```

**Design Decision**: SQLFragment is a simple dataclass containing:
- The SQL expression (the actual SQL code)
- Source table reference (which table/CTE to query from)
- Flags for special handling (unnesting, aggregation)
- Dependencies (which other fragments this depends on)
- Metadata dictionary for extensibility

#### 2. TranslationContext

```python
@dataclass
class TranslationContext:
    """
    Context maintained during AST traversal

    Tracks current state of translation for proper SQL generation
    """
    current_table: str = "resource"              # Current source table/CTE
    current_resource_type: str = "Patient"       # FHIR resource type
    parent_path: List[str] = field(default_factory=list)  # Path components
    variable_bindings: Dict[str, str] = field(default_factory=dict)  # Variables
    cte_counter: int = 0                         # For unique CTE naming

    def next_cte_name(self) -> str:
        """Generate unique CTE name"""
        self.cte_counter += 1
        return f"cte_{self.cte_counter}"

    def push_path(self, component: str) -> None:
        """Add path component to context"""
        self.parent_path.append(component)

    def pop_path(self) -> str:
        """Remove last path component"""
        return self.parent_path.pop() if self.parent_path else None
```

**Design Decision**: Context is mutable state maintained during traversal, tracking:
- Where we are in the path (for building JSON paths)
- Which table/CTE we're currently querying from
- Variable bindings (for `$this`, `$index`, etc.)
- CTE counter for unique naming

#### 3. ASTToSQLTranslator Class

```python
from ..ast.visitor import ASTVisitor
from ..ast.nodes import *
from ...dialects.base import DatabaseDialect

class ASTToSQLTranslator(ASTVisitor[SQLFragment]):
    """
    Translates FHIRPath AST to SQL fragments using visitor pattern

    Core component that converts each AST node type to database-specific SQL
    by calling dialect methods.
    """

    def __init__(self, dialect: DatabaseDialect, resource_type: str = "Patient"):
        super().__init__()
        self.dialect = dialect
        self.context = TranslationContext(current_resource_type=resource_type)
        self.fragments: List[SQLFragment] = []

    def translate(self, ast_root: FHIRPathASTNode) -> List[SQLFragment]:
        """
        Main entry point: translate AST to list of SQL fragments

        Returns list of fragments representing the operation chain
        """
        self.fragments = []
        self._translate_node(ast_root)
        return self.fragments

    def _translate_node(self, node: FHIRPathASTNode) -> SQLFragment:
        """Internal: translate single node and accumulate fragments"""
        fragment = self.visit(node)
        self.fragments.append(fragment)
        return fragment

    # Visitor methods for each AST node type (detailed below)
    def visit_literal(self, node: LiteralNode) -> SQLFragment: ...
    def visit_identifier(self, node: IdentifierNode) -> SQLFragment: ...
    def visit_function_call(self, node: FunctionCallNode) -> SQLFragment: ...
    def visit_operator(self, node: OperatorNode) -> SQLFragment: ...
    def visit_conditional(self, node: ConditionalNode) -> SQLFragment: ...
    def visit_aggregation(self, node: AggregationNode) -> SQLFragment: ...
    def visit_type_operation(self, node: TypeOperationNode) -> SQLFragment: ...
```

### API Changes

#### New APIs

```python
# Primary Translation Interface
from fhir4ds.fhirpath.sql import ASTToSQLTranslator, SQLFragment

# Create translator for specific database dialect
translator = ASTToSQLTranslator(dialect=duckdb_dialect, resource_type="Patient")

# Translate AST to SQL fragments
fragments = translator.translate(ast_root)

# Each fragment contains SQL and metadata
for fragment in fragments:
    print(f"SQL: {fragment.expression}")
    print(f"Source: {fragment.source_table}")
    print(f"Aggregate: {fragment.is_aggregate}")
```

```python
# SQLFragment Data Structure
@dataclass
class SQLFragment:
    expression: str                    # SQL expression
    source_table: str                  # Source table/CTE
    requires_unnest: bool              # Needs array unnesting
    is_aggregate: bool                 # Aggregation operation
    dependencies: List[str]            # CTE dependencies
    metadata: Dict[str, Any]           # Extensible metadata
```

```python
# TranslationContext for maintaining state
@dataclass
class TranslationContext:
    current_table: str
    current_resource_type: str
    parent_path: List[str]
    variable_bindings: Dict[str, str]
    cte_counter: int

    def next_cte_name(self) -> str
    def push_path(self, component: str) -> None
    def pop_path(self) -> str
```

#### Modified APIs

**No existing APIs are modified**. This is new functionality that extends the FHIRPath engine.

#### Dialect API Extensions

New dialect methods required for SQL generation:

```python
class DatabaseDialect(ABC):
    # JSON extraction (existing, used by translator)
    @abstractmethod
    def extract_json_field(self, column: str, path: str) -> str: ...

    @abstractmethod
    def extract_json_object(self, column: str, path: str) -> str: ...

    # Array operations (NEW - required by translator)
    @abstractmethod
    def unnest_json_array(self, column: str, path: str, alias: str) -> str:
        """Generate SQL for unnesting JSON array with alias"""
        pass

    @abstractmethod
    def json_array_length(self, column: str, path: str) -> str:
        """Generate SQL for getting JSON array length"""
        pass

    # Date/time literals (NEW)
    @abstractmethod
    def generate_date_literal(self, date_value: str) -> str:
        """Generate SQL date literal: @2024-01-01 → DATE '2024-01-01'"""
        pass

    @abstractmethod
    def generate_datetime_literal(self, datetime_value: str) -> str:
        """Generate SQL datetime literal"""
        pass

    # Comparison operations (NEW)
    @abstractmethod
    def generate_comparison(self, left: str, operator: str, right: str,
                          left_type: str = None, right_type: str = None) -> str:
        """Generate type-aware comparison SQL"""
        pass
```

### Configuration Changes

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sql.translation.population_first` | boolean | `true` | Use population-friendly patterns (array indexing vs LIMIT 1) |
| `sql.translation.unnest_threshold` | integer | `1000` | Array size threshold for unnesting strategy |
| `sql.translation.enable_optimization_hints` | boolean | `true` | Add SQL optimization hints to fragments |
| `sql.translation.max_cte_depth` | integer | `50` | Maximum CTE nesting depth before error |

### Translation Behavior by Node Type

#### Literal Nodes

**FHIRPath**: `42`, `"text"`, `true`, `@2024-01-01`

**Translation**:
```python
def visit_literal(self, node: LiteralNode) -> SQLFragment:
    if node.literal_type == "string":
        sql_expr = f"'{node.value.replace('\'', '\'\'')}'"  # Escape quotes
    elif node.literal_type == "integer":
        sql_expr = str(node.value)
    elif node.literal_type == "boolean":
        sql_expr = "TRUE" if node.value else "FALSE"
    elif node.literal_type == "date":
        sql_expr = self.dialect.generate_date_literal(node.value)
    elif node.literal_type == "datetime":
        sql_expr = self.dialect.generate_datetime_literal(node.value)

    return SQLFragment(expression=sql_expr, source_table=self.context.current_table)
```

#### Identifier Nodes (Path Navigation)

**FHIRPath**: `Patient.name.family`

**Translation**:
```python
def visit_identifier(self, node: IdentifierNode) -> SQLFragment:
    identifier = node.identifier

    # Root resource reference (no-op)
    if identifier == self.context.current_resource_type:
        return SQLFragment(
            expression=self.context.current_table,
            source_table=self.context.current_table
        )

    # Build JSON path from context
    self.context.push_path(identifier)
    json_path = "$." + ".".join(self.context.parent_path)

    # Call dialect method for extraction
    sql_expr = self.dialect.extract_json_field(
        column=self.context.current_table,
        path=json_path
    )

    return SQLFragment(expression=sql_expr, source_table=self.context.current_table)
```

**Example Output**:
- `Patient` → `resource` (current table)
- `name` → `json_extract(resource, '$.name')`
- `name.family` → `json_extract(resource, '$.name.family')`

#### Function Call Nodes (where, select, first, exists)

**FHIRPath**: `Patient.name.where(use='official')`

**Translation** (where function):
```python
def _translate_where(self, node: FunctionCallNode) -> SQLFragment:
    """
    Translate where() to SQL with LATERAL UNNEST

    KEY DESIGN DECISION: Translator generates complete unnest SQL,
    not just a flag. This keeps fragment self-contained.
    """
    # Get array path from context
    array_path = "$." + ".".join(self.context.parent_path)

    # Translate filter condition
    condition_node = node.arguments[0]
    condition_fragment = self.visit(condition_node)

    # Generate unique CTE name and alias
    cte_name = self.context.next_cte_name()
    array_alias = f"{cte_name}_item"

    # Generate complete SQL with unnesting using dialect method
    unnest_expr = self.dialect.unnest_json_array(
        column=self.context.current_table,
        path=array_path,
        alias=array_alias
    )

    sql = f"""
        SELECT {self.context.current_table}.id, {array_alias}
        FROM {self.context.current_table}, LATERAL {unnest_expr}
        WHERE {condition_fragment.expression}
    """

    # Update context: next operations use this CTE
    self.context.current_table = cte_name

    return SQLFragment(
        expression=sql,
        source_table=cte_name,
        requires_unnest=True,  # Metadata for CTE Builder
        dependencies=[self.context.current_table]
    )
```

**Example Output**:
```sql
SELECT resource.id, cte_1_item
FROM resource, LATERAL UNNEST(json_extract(resource, '$.name')) AS cte_1_item
WHERE json_extract(cte_1_item, '$.use') = 'official'
```

**FHIRPath**: `Patient.name.first()`

**Translation** (first function):
```python
def _translate_first(self, node: FunctionCallNode) -> SQLFragment:
    """
    Translate first() using array indexing (population-friendly!)

    KEY DESIGN DECISION: Use [0] indexing, NOT LIMIT 1.
    This maintains population-scale analytics capability.
    """
    # Build JSON path with [0] index
    json_path = "$." + ".".join(self.context.parent_path) + "[0]"

    sql_expr = self.dialect.extract_json_field(
        column=self.context.current_table,
        path=json_path
    )

    return SQLFragment(
        expression=sql_expr,
        source_table=self.context.current_table
    )
```

**Example Output**:
- `name.first()` → `json_extract(resource, '$.name[0]')`
- **NOT**: `SELECT * FROM ... LIMIT 1` (anti-pattern for population analytics)

#### Operator Nodes

**FHIRPath**: `age > 18`, `active and deceased`

**Translation**:
```python
def visit_operator(self, node: OperatorNode) -> SQLFragment:
    # Translate operands
    left_fragment = self.visit(node.left_operand)
    right_fragment = self.visit(node.right_operand) if node.right_operand else None

    operator = node.operator

    # Comparison operators
    if operator in ["=", "!=", ">", "<", ">=", "<="]:
        # Use dialect method for type-aware comparison
        sql_expr = self.dialect.generate_comparison(
            left=left_fragment.expression,
            operator=operator,
            right=right_fragment.expression,
            left_type=node.left_operand.metadata.type_info.fhir_type if node.left_operand.metadata else None,
            right_type=node.right_operand.metadata.type_info.fhir_type if node.right_operand.metadata else None
        )

    # Logical operators
    elif operator in ["and", "or"]:
        sql_expr = f"({left_fragment.expression}) {operator.upper()} ({right_fragment.expression})"

    # Arithmetic operators
    elif operator in ["+", "-", "*", "/"]:
        sql_expr = f"({left_fragment.expression}) {operator} ({right_fragment.expression})"

    return SQLFragment(expression=sql_expr, source_table=self.context.current_table)
```

#### Aggregation Nodes

**FHIRPath**: `Patient.count()`, `Observation.value.sum()`

**Translation**:
```python
def visit_aggregation(self, node: AggregationNode) -> SQLFragment:
    func_name = node.function_name.upper()

    if func_name == "COUNT":
        sql_expr = "COUNT(*)"
    else:
        # Get value to aggregate
        value_node = node.arguments[0]
        value_fragment = self.visit(value_node)
        sql_expr = f"{func_name}({value_fragment.expression})"

    return SQLFragment(
        expression=sql_expr,
        source_table=self.context.current_table,
        is_aggregate=True  # Flag for CTE Builder
    )
```

### Multi-Step Expression Handling

**Design Decision**: Translator emits **list of fragments** (one per operation), not nested structure.

**Example**: `Patient.name.where(use='official').family.first()`

**Translation produces 4 fragments**:

```python
fragments = translator.translate(ast_root)

# Fragment 1: Extract name array
fragments[0] = SQLFragment(
    expression="SELECT id, json_extract(resource, '$.name') as names FROM patient_resources",
    source_table="patient_resources"
)

# Fragment 2: Unnest and filter where(use='official')
fragments[1] = SQLFragment(
    expression="""
        SELECT cte_1.id, cte_1_item
        FROM cte_1, LATERAL UNNEST(cte_1.names) AS cte_1_item
        WHERE json_extract(cte_1_item, '$.use') = 'official'
    """,
    source_table="cte_1",
    dependencies=["cte_1"],
    requires_unnest=True
)

# Fragment 3: Extract family field
fragments[2] = SQLFragment(
    expression="SELECT id, json_extract(cte_1_item, '$.family') as family FROM cte_2",
    source_table="cte_2",
    dependencies=["cte_2"]
)

# Fragment 4: Get first element using array indexing
fragments[3] = SQLFragment(
    expression="SELECT id, family[0] as first_family FROM cte_3",
    source_table="cte_3",
    dependencies=["cte_3"]
)
```

**Rationale**: Sequential list is simpler than nested tree, maps naturally to CTE chain.

### Behavioral Changes

- **New Capability**: FHIRPath expressions can be translated to SQL (previously impossible)
- **SQL Generation**: Calling translator on AST produces SQL fragments (new behavior)
- **Dialect Integration**: Dialects now invoked during translation (new dialect method calls)
- **No Breaking Changes**: Existing in-memory evaluator unchanged, translator is new component

## Implementation

### Development Plan

#### Phase 1: Core Infrastructure (Week 1)
- [ ] Create `fhir4ds/fhirpath/sql/` module structure
- [ ] Implement `SQLFragment` dataclass with metadata support
- [ ] Implement `TranslationContext` with path tracking and CTE naming
- [ ] Create `ASTToSQLTranslator` base class with visitor pattern setup
- [ ] Add unit tests for data structures (SQLFragment, TranslationContext)

#### Phase 2: Basic Node Translation (Week 2)
- [ ] Implement `visit_literal()` - all literal types (string, number, boolean, date)
- [ ] Implement `visit_identifier()` - path navigation and JSON extraction
- [ ] Implement `visit_operator()` - comparison, logical, arithmetic operators
- [ ] Add dialect method extensions (date literals, comparison operations)
- [ ] Unit tests for basic node types (100+ test cases)

#### Phase 3: Complex Operations (Week 3-4)
- [ ] Implement `visit_function_call()` dispatch to function handlers
- [ ] Implement `_translate_where()` - array filtering with LATERAL UNNEST
- [ ] Implement `_translate_select()` - array transformation
- [ ] Implement `_translate_first()` - array indexing (population-friendly [0])
- [ ] Implement `_translate_exists()` - existence checking
- [ ] Implement `visit_aggregation()` - COUNT, SUM, AVG, MIN, MAX
- [ ] Add dialect methods for array operations (`unnest_json_array`, `json_array_length`)
- [ ] Unit tests for complex operations (150+ test cases)

#### Phase 4: Multi-Step Expression Handling (Week 5)
- [ ] Implement expression chain traversal (generate fragment sequence)
- [ ] Handle context updates between operations (table references, path tracking)
- [ ] Implement dependency tracking between fragments
- [ ] Test complex multi-operation expressions (50+ integration tests)
- [ ] Validate against official FHIRPath test cases

#### Phase 5: Dialect Implementations (Week 6)
- [ ] Complete DuckDB dialect methods for translation
- [ ] Complete PostgreSQL dialect methods for translation
- [ ] Validate SQL syntax correctness for both dialects
- [ ] Test multi-database consistency (identical fragment output modulo syntax)
- [ ] Performance benchmarking for translation speed

#### Phase 6: Integration and Documentation (Week 7)
- [ ] Integration with FHIRPath parser (PEP-002 output → translator input)
- [ ] Integration testing with real FHIRPath expressions from test suite
- [ ] API documentation and usage examples
- [ ] Architecture documentation for future PEP-004 integration
- [ ] Developer guide for extending translator (new functions, operators)

### Resource Requirements

- **Development Time**: 7 weeks
- **Developer Resources**: 1 full-time senior developer
- **Infrastructure**: Multi-database testing environment (DuckDB, PostgreSQL)
- **Dependencies**:
  - PEP-002 (FHIRPath Parser) - completed
  - Database dialect infrastructure - completed
  - Official FHIRPath test suite - available

### Testing Strategy

#### Unit Testing
- **Data Structures**: SQLFragment, TranslationContext serialization and behavior
- **Node Translation**: Each `visit_*` method tested independently (300+ tests)
- **Dialect Methods**: All new dialect methods tested for correct SQL syntax
- **Edge Cases**: Empty expressions, null values, invalid operators, deeply nested paths

#### Integration Testing
- **Expression Chains**: Multi-step expressions producing fragment sequences
- **Parser Integration**: Parser output → translator input → SQL fragments
- **Dialect Consistency**: DuckDB and PostgreSQL produce equivalent logic (50+ tests)
- **FHIRPath Test Suite**: Official test cases for translation accuracy

#### Performance Testing
- **Translation Speed**: <10ms for typical expression translation
- **Memory Usage**: <50MB for complex expression ASTs
- **Scalability**: Handle expressions with 20+ operations without degradation

#### Compliance Testing
- **FHIRPath Specification**: Validate translation preserves FHIRPath semantics
- **SQL Correctness**: Generated SQL executes successfully on target databases
- **Type Safety**: FHIR type system properly mapped to SQL types

### Rollout Plan

1. **Development Environment**: Complete implementation with comprehensive unit testing
2. **Testing Environment**: Integration with parser and dialect layers
3. **Validation Environment**: Execute against FHIRPath official test suite
4. **Documentation**: Complete API docs and integration guides
5. **Ready for PEP-004**: Output (SQL fragments) ready for CTE Builder integration

**Note**: This component does not directly execute SQL, so no production rollout. It's a library component used by higher-level systems (SQL-on-FHIR, CQL).

## Impact Analysis

### Backwards Compatibility

- **No Breaking Changes**: This is new functionality, existing code unaffected
- **Additive API**: New `ASTToSQLTranslator` class and `SQLFragment` types
- **Dialect Extensions**: New dialect methods, existing methods unchanged
- **Migration Requirements**: None - optional new capability

### Performance Impact

| Metric | Current | Expected | Improvement |
|--------|---------|----------|-------------|
| FHIRPath to SQL | Not supported | <10ms translation | New capability |
| Expression Complexity | N/A | 20+ operations supported | N/A |
| Memory Usage | N/A | <50MB per expression | Efficient |
| Dialect Translation | N/A | Identical for DuckDB/PostgreSQL | Consistent |

**Note**: This PEP focuses on translation speed, not SQL execution performance. SQL execution performance (10x+ improvements) will come from PEP-004 (CTE generation).

### Security Considerations

- **SQL Injection Protection**: All values parameterized through dialect methods, no string concatenation
- **Input Validation**: AST structure validated by parser (PEP-002), translator assumes valid input
- **Resource Limits**: Configuration for max CTE depth prevents infinite translation loops
- **Type Safety**: FHIR type system prevents type confusion in SQL generation

### Resource Impact

- **Development**: 7 weeks for complete implementation
- **Infrastructure**: No new infrastructure (uses existing dialect testing)
- **Documentation**: API documentation, integration guides, developer tutorials
- **Maintenance**: Minimal - well-defined visitor pattern easy to extend

### User Experience Impact

**For Developers Using FHIR4DS**:
- **Positive**: Can now translate FHIRPath expressions to SQL (new capability)
- **Positive**: Database-agnostic translation (works with DuckDB and PostgreSQL)
- **Training**: Understanding SQL fragment output structure

**For FHIR4DS Library Developers**:
- **Positive**: Clear extension points for new FHIRPath functions
- **Positive**: Structured SQL fragments easy to optimize in future PEPs
- **Training**: Visitor pattern and dialect integration concepts

## Alternatives Considered

### Alternative 1: Extend In-Memory Evaluator to Generate SQL
**Description**: Add SQL generation mode to existing FHIRPath evaluator (PEP-002)

**Pros**:
- Single component for both in-memory and SQL execution
- Reuse existing visitor pattern implementation
- Less code duplication

**Cons**:
- Mixing concerns (memory execution + SQL generation) in one class
- Hard to optimize each mode independently
- Complicated class with dual responsibilities
- Difficult to test SQL generation in isolation

**Why Rejected**: Violates single responsibility principle. Clean separation (evaluator = memory, translator = SQL) is architecturally superior.

### Alternative 2: String Template-Based SQL Generation
**Description**: Use string templates for SQL with placeholder substitution

**Example**:
```python
sql_template = "SELECT {columns} FROM {table} WHERE {condition}"
sql = sql_template.format(columns=cols, table=tbl, condition=cond)
```

**Pros**:
- Simple to implement initially
- Easy to understand for simple cases

**Cons**:
- Difficult to maintain for complex expressions
- Hard to validate SQL correctness at compile time
- Dialect differences require duplicate template sets
- No structured representation for optimization
- SQL injection risk if not careful with string escaping

**Why Rejected**: Structured visitor pattern with typed fragments is more maintainable, testable, and optimizable.

### Alternative 3: Generate Complete SQL Query Immediately
**Description**: Translator outputs final SQL query, not fragments

**Pros**:
- Simple API (AST → complete SQL string)
- No need for fragment concept

**Cons**:
- Translator responsible for CTE structure, assembly, optimization (too many responsibilities)
- Cannot optimize SQL across multiple expressions (needed for CQL)
- Difficult to support different query patterns (subquery vs CTE vs inline)
- Hard to extend for future optimizations

**Why Rejected**: Fragment-based approach provides better separation of concerns and enables future optimization (PEP-004).

### Alternative 4: Single SQLFragment per Expression
**Description**: Complex expressions produce one fragment with nested dependencies

**Example**:
```python
fragment = SQLFragment(
    expression="...",
    dependencies=[
        SQLFragment(expression="...", dependencies=[...])  # Nested
    ]
)
```

**Pros**:
- Single return value from translator
- Dependencies explicitly modeled in structure

**Cons**:
- Complex nested tree structure hard to work with
- Difficult to optimize or reorder operations
- CTE Builder needs recursive flattening logic
- Harder to debug and understand

**Why Rejected**: Sequential list of fragments is simpler and maps naturally to CTE chain. Expression chains are inherently sequential, not tree-structured.

### Status Quo (No Implementation)
**Description**: Do not implement AST-to-SQL translator, keep current limitations

**Pros**:
- No development cost
- No risk of implementation issues

**Cons**:
- Cannot execute FHIRPath expressions beyond basic paths
- Cannot implement SQL-on-FHIR (blocked)
- Cannot implement CQL framework (blocked)
- Cannot achieve population-scale performance (10x improvements blocked)
- Architecture incomplete (gap between parser and execution)
- No path to 100% specification compliance

**Why Rejected**: This component is essential for achieving project goals. Without it, FHIR4DS cannot deliver on its core value proposition of population-scale healthcare analytics.

## Success Metrics

### Primary Metrics
- **Translation Coverage**: 80%+ of FHIRPath operations supported by Week 7
- **Translation Speed**: <10ms for typical healthcare expressions (Patient.name.where(...))
- **Multi-Database Consistency**: 100% equivalent logic across DuckDB and PostgreSQL
- **Test Coverage**: 90%+ code coverage for translator module

### Secondary Metrics
- **Official Test Pass Rate**: 70%+ of applicable FHIRPath tests translate correctly
- **Expression Complexity**: Support 20+ operation chains without failure
- **Memory Efficiency**: <50MB for complex expression translation
- **Dialect Method Coverage**: 100% of required dialect methods implemented

### Monitoring Plan
- **Tools**: pytest for unit/integration tests, pytest-benchmark for performance
- **Dashboards**: Translation coverage metrics, test pass rates, performance benchmarks
- **Alerts**: Test failures, performance regressions >20%, memory spikes
- **Review Cadence**: Weekly during implementation, monthly post-completion

## Documentation Plan

### New Documentation Required
- [ ] **API Documentation**: Complete API reference for ASTToSQLTranslator, SQLFragment, TranslationContext
- [ ] **Integration Guide**: How to use translator with parser output
- [ ] **Dialect Extension Guide**: Adding new dialect methods for SQL generation
- [ ] **Translation Examples**: Common FHIRPath patterns and their SQL translations
- [ ] **Troubleshooting Guide**: Common issues and debugging techniques

### Existing Documentation Updates
- [ ] **Architecture Overview**: Update pipeline diagram to include translator
- [ ] **FHIRPath Engine Documentation**: Add SQL generation mode documentation
- [ ] **Database Dialect Guide**: Document new required dialect methods
- [ ] **Testing Guide**: Add translator testing patterns and examples

### Training Materials
- [ ] **Developer Tutorial**: Step-by-step guide to extending translator
- [ ] **Architecture Deep-Dive**: Video walkthrough of translation pipeline
- [ ] **Code Examples**: Jupyter notebook with translation examples

## Timeline

| Milestone | Date | Owner | Dependencies |
|-----------|------|-------|--------------|
| PEP Review & Approval | Week 1 | Senior Architect | Draft review process |
| Phase 1: Infrastructure | Week 1 | Developer | PEP approval |
| Phase 2: Basic Nodes | Week 2 | Developer | Phase 1 complete |
| Phase 3: Complex Operations | Week 3-4 | Developer | Phase 2 complete |
| Phase 4: Multi-Step Expressions | Week 5 | Developer | Phase 3 complete |
| Phase 5: Dialect Implementations | Week 6 | Developer | Phase 4 complete |
| Phase 6: Integration & Docs | Week 7 | Developer | Phase 5 complete |
| PEP-003 Complete | Week 7 | Developer | All phases complete |
| Ready for PEP-004 | Week 8 | Developer | Documentation complete |

## References

### External Links
- [FHIRPath R4 Specification](https://hl7.org/fhirpath/) - Specification for FHIRPath expressions
- [SQL-on-FHIR v2.0 Specification](https://sql-on-fhir-v2.readthedocs.io/) - Uses FHIRPath expressions in ViewDefinitions
- [CQL R1.5 Specification](https://cql.hl7.org/) - Uses FHIRPath for path navigation
- [Visitor Pattern](https://refactoring.guru/design-patterns/visitor) - Design pattern used for AST traversal

### Internal Documents
- [PEP-001: Testing Infrastructure](../implemented/pep-001-testing-infrastructure.md) - Testing framework for validation
- [PEP-002: FHIRPath Core Implementation](../implemented/pep-002-fhirpath-core-implementation.md) - Parser that creates AST input
- [Architecture Overview](../../architecture/README.md) - Unified FHIRPath architecture principles
- [Architecture Goals](../../architecture/goals.md) - 100% specification compliance targets
- [Database Dialect Architecture](../../architecture/README.md#thin-dialect-layer) - Thin dialect principles

---

## Appendices

### Appendix A: Complete Translation Example

**FHIRPath Expression**: `Patient.name.where(use='official').family.first()`

**Input AST Structure** (from PEP-002 parser):
```
FunctionCallNode(first)
└── IdentifierNode(family)
    └── FunctionCallNode(where)
        └── OperatorNode(=)
            ├── IdentifierNode(use)
            └── LiteralNode('official')
        └── IdentifierNode(name)
            └── IdentifierNode(Patient)
```

**Translation Process**:

1. **Visit IdentifierNode(Patient)** → Fragment 0
```python
SQLFragment(
    expression="resource",  # Root context
    source_table="patient_resources"
)
```

2. **Visit IdentifierNode(name)** → Fragment 1
```python
SQLFragment(
    expression="json_extract(resource, '$.name')",
    source_table="patient_resources"
)
```

3. **Visit FunctionCallNode(where)** → Fragment 2
```python
# Generates complete unnest SQL
SQLFragment(
    expression="""
        SELECT resource.id, cte_1_item
        FROM resource, LATERAL UNNEST(json_extract(resource, '$.name')) AS cte_1_item
        WHERE json_extract(cte_1_item, '$.use') = 'official'
    """,
    source_table="cte_1",
    requires_unnest=True,
    dependencies=["patient_resources"]
)
```

4. **Visit IdentifierNode(family)** → Fragment 3
```python
SQLFragment(
    expression="SELECT id, json_extract(cte_1_item, '$.family') as family FROM cte_1",
    source_table="cte_1"
)
```

5. **Visit FunctionCallNode(first)** → Fragment 4
```python
# Population-friendly [0] indexing
SQLFragment(
    expression="SELECT id, family[0] as first_family FROM cte_2",
    source_table="cte_2"
)
```

**Translator Output**: `List[SQLFragment]` with 5 fragments

**Note**: Future PEP-004 (CTE Builder) will wrap these fragments into CTEs and assemble into final SQL.

### Appendix B: Dialect Implementation Examples

#### DuckDB Dialect Methods

```python
class DuckDBDialect(DatabaseDialect):
    def extract_json_field(self, column: str, path: str) -> str:
        return f"json_extract_string({column}, '{path}')"

    def unnest_json_array(self, column: str, path: str, alias: str) -> str:
        return f"UNNEST(json_extract({column}, '{path}')) AS {alias}"

    def generate_date_literal(self, date_value: str) -> str:
        return f"DATE '{date_value}'"

    def generate_comparison(self, left: str, operator: str, right: str,
                          left_type: str = None, right_type: str = None) -> str:
        # Type-aware casting for comparisons
        if left_type == "date" and right_type == "date":
            return f"CAST({left} AS DATE) {operator} CAST({right} AS DATE)"
        return f"{left} {operator} {right}"
```

#### PostgreSQL Dialect Methods

```python
class PostgreSQLDialect(DatabaseDialect):
    def extract_json_field(self, column: str, path: str) -> str:
        # PostgreSQL uses different JSON operators
        json_path = path.replace('$', '').replace('.', ',')
        return f"jsonb_extract_path_text({column}, {json_path})"

    def unnest_json_array(self, column: str, path: str, alias: str) -> str:
        return f"jsonb_array_elements({column}->'{path}') AS {alias}"

    def generate_date_literal(self, date_value: str) -> str:
        return f"DATE '{date_value}'"

    def generate_comparison(self, left: str, operator: str, right: str,
                          left_type: str = None, right_type: str = None) -> str:
        if left_type == "date" and right_type == "date":
            return f"{left}::DATE {operator} {right}::DATE"
        return f"{left} {operator} {right}"
```

### Appendix C: Future PEP Integration

This PEP (003) provides the foundation for future PEP-004. Here's how they integrate:

**PEP-003 Output** (SQL Fragments):
```python
fragments = [
    SQLFragment(expression="SELECT ...", source_table="resource"),
    SQLFragment(expression="SELECT ... WHERE ...", source_table="cte_1", requires_unnest=True),
    SQLFragment(expression="SELECT ...", source_table="cte_2")
]
```

**PEP-004 CTE Builder** (Wraps fragments in CTEs):
```python
class CTEBuilder:
    def build_cte_chain(self, fragments: List[SQLFragment]) -> List[CTE]:
        ctes = []
        for i, fragment in enumerate(fragments):
            cte_name = f"cte_{i+1}"
            cte = CTE(
                name=cte_name,
                query=fragment.expression,
                dependencies=fragment.dependencies
            )
            ctes.append(cte)
        return ctes
```

**PEP-004 CTE Assembler** (Combines into final SQL):
```python
class CTEAssembler:
    def assemble_query(self, ctes: List[CTE]) -> str:
        with_clause = "WITH " + ",\n".join([
            f"{cte.name} AS (\n{cte.query}\n)"
            for cte in ctes
        ])
        final_select = f"SELECT * FROM {ctes[-1].name}"
        return f"{with_clause}\n{final_select}"
```

**Final SQL Output**:
```sql
WITH
cte_1 AS (
    SELECT id, json_extract(resource, '$.name') as names
    FROM patient_resources
),
cte_2 AS (
    SELECT cte_1.id, cte_1_item
    FROM cte_1, LATERAL UNNEST(cte_1.names) AS cte_1_item
    WHERE json_extract(cte_1_item, '$.use') = 'official'
),
cte_3 AS (
    SELECT id, json_extract(cte_1_item, '$.family') as family
    FROM cte_2
)
SELECT * FROM cte_3;
```

**Design Decision Documentation**:

These design decisions are documented here for architectural consistency across PEPs:

1. **Fragment Sequence over Nested Structure**: PEP-003 emits `List[SQLFragment]`, not nested `SQLFragment` with dependencies. Rationale: Simpler for PEP-004 to process, matches sequential nature of expression chains.

2. **Complete Unnest SQL in Fragments**: PEP-003 generates full `LATERAL UNNEST` SQL, not just flag. Rationale: Keeps fragments self-contained, translator has all context needed.

3. **Population-First Design**: Use `[0]` indexing not `LIMIT 1`. Rationale: Maintains population-scale analytics capability across entire pipeline.

4. **Dialect Method Calls**: PEP-003 calls dialect methods during translation, not post-processing. Rationale: Database-specific SQL from the start, cleaner separation.

These decisions enable PEP-004 to focus on CTE structure/optimization without changing translation logic.

---

## Author Notes

**Implementation Priority**: This PEP is critical for achieving FHIR4DS's core value proposition. Without the AST-to-SQL translator, we cannot:
- Execute FHIRPath expressions against databases
- Implement SQL-on-FHIR or CQL specifications
- Achieve population-scale performance (10x+ improvements)
- Complete the unified FHIRPath architecture

**Technical Risk**: Medium. Well-defined problem with clear patterns (visitor pattern, dialect abstraction). Main risks are:
- Complexity of array unnesting across dialects (mitigated by dialect methods)
- Edge cases in FHIRPath specification (mitigated by official test suite)
- Performance of translation (mitigated by benchmarking, <10ms target reasonable)

**Dependencies**:
- PEP-002 (Parser) ✅ Complete - provides AST input
- Dialect infrastructure ✅ Complete - provides SQL syntax methods
- Ready to implement immediately

**Future Work**: PEP-004 will build on this foundation to add:
- CTE Builder (wraps fragments)
- CTE Optimizer (merges, pushes predicates)
- CTE Assembler (combines into monolithic SQL)
- CQL dependency resolver (handles define dependencies)

**Success Criteria Review**:
- [ ] 80%+ FHIRPath operations translate to SQL
- [ ] <10ms translation speed for typical expressions
- [ ] 100% multi-database consistency (DuckDB/PostgreSQL)
- [ ] 90%+ test coverage
- [ ] Ready for PEP-004 integration

---

**Status**: Draft - Ready for Senior Solution Architect review and team discussion
**Next Step**: Review and approval, then begin Phase 1 implementation