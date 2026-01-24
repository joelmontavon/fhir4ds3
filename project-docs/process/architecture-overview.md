## Proposed Architecture

### Core Principle: **FHIRPath-First, CTE-Based, Population-Optimized**
### Implementation: **Forked Pure Python Parser + Separate CTE Generator**

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT LAYER                              │
├─────────────────┬─────────────────┬─────────────────────────┤
│  SQL-on-FHIR    │      CQL        │      FHIRPath           │
│ ViewDefinition  │   Expression    │     Expression          │
└─────────────────┴─────────────────┴─────────────────────────┘
         │                 │                   │
         ▼                 ▼                   │
┌─────────────────┐┌─────────────────┐        │
│ViewDef→FHIRPath ││  CQL→FHIRPath   │        │
│   Translator    ││   Translator    │        │
└─────────────────┘└─────────────────┘        │
         │                 │                   │
         └─────────────────┼───────────────────┘
                          ▼
              ┌─────────────────────────┐
              │  Forked FHIRPath Parser │
              │   (Pure Python + MIT)   │
              │   • Zero Java deps      │
              │   • ANTLR4-generated    │
              │   • Proven compliance   │
              └─────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   Custom FHIRPath Engine│
              │   (Operation Sequences) │
              │   • Expression → Ops    │
              │   • CQL dependencies    │
              │   • Population metadata │
              └─────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   CTE Generator         │
              │ (Expression → CTEs)     │
              │   • Template library    │
              │   • Dependency ordering │
              │   • Population CTEs     │
              └─────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │  SQL Assembler          │
              │ (CTEs → Monolithic SQL) │
              │   • CTE dependency sort │
              │   • Monolithic output   │
              │   • CQL multi-define    │
              └─────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   Thin Dialect Layer    │
              │  (PostgreSQL/DuckDB)    │
              │   • Syntax only         │
              │   • No business logic   │
              └─────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │  Database Execution     │
              │ (Population Results)    │
              └─────────────────────────┘
```

### Architecture Layers

#### **Layer 1: Input Translators**
Responsible for converting domain-specific languages to FHIRPath AST.

**ViewDefinition Translator**:
```python
class ViewDefinitionTranslator:
    """Converts SQL-on-FHIR ViewDefinitions to FHIRPath expressions."""

    def translate(self, view_def: ViewDefinition) -> List[FHIRPathExpression]:
        """
        Converts ViewDefinition columns to FHIRPath expressions.

        Example:
        {"name": "patient_name", "path": "name.family.first()"}
        → FHIRPathExpression("name.family.first()")
        """
        pass
```

**CQL Translator**:
```python
class CQLTranslator:
    """Converts CQL expressions to FHIRPath expressions."""

    def translate(self, cql_ast: CQLAST) -> List[FHIRPathExpression]:
        """
        Converts CQL define statements to FHIRPath expressions.

        Example:
        define "HasDiabetes": exists([Condition: "Diabetes"])
        → FHIRPathExpression with dependency graph
        """
        pass
```

#### **Layer 2A: Forked FHIRPath Parser (Foundation)**
Pure Python parser forked from fhirpathpy (MIT license) with zero Java dependencies.

```python
class ForkedFHIRPathParser:
    """
    Forked from beda-software/fhirpath-py for enterprise accessibility.

    Benefits:
    - Zero Java dependencies (pure Python)
    - ANTLR4-generated parser (proven compliance)
    - MIT license (modification allowed)
    - Production-tested foundation
    """

    def parse(self, expression: str) -> FHIRPathAST:
        """Parse FHIRPath string into AST using forked ANTLR4 parser."""
        # Uses forked ANTLR4-generated parser
        return self._antlr_parser.parse(expression)

    def get_ast_nodes(self) -> List[ASTNode]:
        """Access parsed AST nodes for custom processing."""
        pass
```

#### **Layer 2B: Custom FHIRPath Engine (CTE-Optimized)**
Custom engine that converts parsed AST into operation sequences optimized for CTE generation.

```python
class FHIRPathEngine:
    """Custom FHIRPath engine optimized for CTE generation."""

    def __init__(self, parser: ForkedFHIRPathParser):
        self.parser = parser
        self.operation_mapper = OperationMapper()

    def process_expression(self, expression: str) -> OperationSequence:
        """Convert FHIRPath expression to operation sequence."""
        ast = self.parser.parse(expression)
        return self.operation_mapper.ast_to_operations(ast)

    def resolve_dependencies(self, expressions: List[str]) -> DependencyGraph:
        """Resolve cross-expression dependencies (critical for CQL)."""
        pass

    def add_population_metadata(self, ops: OperationSequence) -> OperationSequence:
        """Add metadata for population-scale optimization."""
        pass
```

#### **Layer 3: CTE Generator**
Converts FHIRPath expressions into CTE (Common Table Expression) chains.

```python
class CTEGenerator:
    """Generates CTE chains from FHIRPath expressions."""

    def __init__(self):
        self.operation_templates = CTEOperationTemplates()
        self.dependency_resolver = CTEDependencyResolver()

    def generate_from_expression(self, expression: FHIRPathExpression) -> CTEChain:
        """
        Convert FHIRPath expression to CTE chain.

        Example:
        "Patient.name.given.first()" →

        Generated CTE Chain:
        """
        # Parse expression into operation sequence
        ops = self.parse_expression(expression)

        # Generate CTE for each operation
        ctes = []
        for i, operation in enumerate(ops):
            template = self.operation_templates.get_template(operation.type)
            cte = template.generate(operation, previous_cte=ctes[-1] if ctes else None)
            ctes.append(cte)

        return CTEChain(ctes)

    def generate_multi_expression(self, expressions: List[FHIRPathExpression]) -> MonolithicCTE:
        """Generate monolithic CTE for multiple expressions (CQL support)."""
        # Resolve dependencies between expressions
        dependency_graph = self.dependency_resolver.build_graph(expressions)
        ordered_expressions = self.dependency_resolver.topological_sort(dependency_graph)

        # Generate CTEs in dependency order
        all_ctes = []
        for expr in ordered_expressions:
            cte_chain = self.generate_from_expression(expr)
            all_ctes.extend(cte_chain.ctes)

        return MonolithicCTE(all_ctes)
```

**CTE Operation Templates**:
```python
class CTEOperationTemplates:
    """Template library for FHIRPath operations → CTE conversion."""

    def path_navigation(self, operation: PathOperation, previous_cte: str) -> CTE:
        """Template for path navigation like .name, .given"""
        return CTE(
            name=f"{operation.path}_extraction",
            query=f"""
            SELECT id,
                   json_extract({previous_cte}.result, '$.{operation.path}') as result
            FROM {previous_cte}
            """
        )

    def function_first(self, operation: FunctionOperation, previous_cte: str) -> CTE:
        """Template for .first() function"""
        return CTE(
            name=f"first_result",
            query=f"""
            SELECT id,
                   json_extract({previous_cte}.result, '$[0]') as result
            FROM {previous_cte}
            """
        )

    def function_where(self, operation: WhereOperation, previous_cte: str) -> CTE:
        """Template for .where() function"""
        return CTE(
            name=f"where_filtered",
            query=f"""
            SELECT id, result
            FROM {previous_cte}
            WHERE {operation.condition.to_sql()}
            """
        )

    def resource_filter(self, operation: ResourceOperation, previous_cte: str) -> CTE:
        """Template for resource type filtering"""
        return CTE(
            name=f"{operation.resource_type.lower()}_resources",
            query=f"""
            SELECT id, data as result
            FROM fhir_resources
            WHERE resourceType = '{operation.resource_type}'
            """
        )
```

**CTE Generation Principles**:
1. **One CTE per FHIRPath operation** (first(), where(), combine(), etc.)
2. **Population-first**: Each CTE operates on full dataset
3. **Dependency-aware**: CTEs ordered by dependency graph
4. **Optimizable**: Database engine optimizes CTE chains
5. **Debuggable**: Each CTE can be inspected independently

#### **Layer 4: SQL Assembler (Monolithic Query Builder)**
Combines CTEs into dependency-ordered monolithic SQL queries.

```python
class SQLAssembler:
    """Assembles CTE chains into monolithic SQL queries."""

    def __init__(self):
        self.dependency_resolver = CTEDependencyResolver()

    def assemble_single_expression(self, cte_chain: CTEChain) -> MonolithicSQL:
        """
        Assemble single FHIRPath expression into complete SQL.

        Example Input: CTEChain([patient_cte, name_cte, given_cte, first_cte])

        Example Output:
        WITH
          patient_resources AS (...),
          name_extraction AS (...),
          given_extraction AS (...),
          first_result AS (...)
        SELECT id, result FROM first_result;
        """
        with_clauses = []
        for cte in cte_chain.ctes:
            with_clauses.append(f"{cte.name} AS ({cte.query})")

        final_cte = cte_chain.ctes[-1].name
        return MonolithicSQL(
            with_clause=",\n".join(with_clauses),
            main_query=f"SELECT id, result FROM {final_cte}"
        )

    def assemble_multi_expression(self, expressions: Dict[str, CTEChain]) -> MonolithicSQL:
        """
        Assemble multiple expressions (CQL defines) into single monolithic query.

        Critical for CQL execution where defines reference each other.

        Example:
        expressions = {
            "HasDiabetes": cte_chain_1,
            "RecentA1c": cte_chain_2,
            "InInitialPopulation": cte_chain_3  # References HasDiabetes
        }

        Output: Single SQL with all CTEs in dependency order
        """
        # Flatten all CTEs from all expressions
        all_ctes = []
        expression_final_ctes = {}

        for expr_name, cte_chain in expressions.items():
            all_ctes.extend(cte_chain.ctes)
            expression_final_ctes[expr_name] = cte_chain.ctes[-1].name

        # Resolve dependencies and order CTEs
        ordered_ctes = self.dependency_resolver.order_ctes(all_ctes)

        # Build monolithic query
        with_clauses = []
        for cte in ordered_ctes:
            with_clauses.append(f"{cte.name} AS ({cte.query})")

        # Final SELECT returns all expression results
        select_clauses = []
        for expr_name, final_cte in expression_final_ctes.items():
            select_clauses.append(f'{final_cte}.result as "{expr_name}"')

        main_query = f"""
        SELECT patient_id,
               {', '.join(select_clauses)}
        FROM {list(expression_final_ctes.values())[0]}
        """

        return MonolithicSQL(
            with_clause=",\n".join(with_clauses),
            main_query=main_query
        )

    def optimize_for_population(self, sql: MonolithicSQL) -> MonolithicSQL:
        """Add population-scale optimizations to generated SQL."""
        # Add appropriate indexing hints, partitioning, etc.
        pass
```

#### **Layer 5: Thin Dialect Layer**
Pure syntax translation without business logic.

```python
class SQLDialect:
    """Base class for database-specific syntax."""

    def json_extract(self, obj: str, path: str) -> str:
        """Database-specific JSON extraction."""
        raise NotImplementedError

    def json_array_agg(self, expr: str) -> str:
        """Database-specific JSON array aggregation."""
        raise NotImplementedError

    def with_clause(self, name: str, query: str) -> str:
        """Database-specific WITH clause syntax."""
        return f"{name} AS ({query})"
```

**DuckDB Dialect Example**:
```python
class DuckDBDialect(SQLDialect):
    def json_extract(self, obj: str, path: str) -> str:
        return f"json_extract({obj}, '{path}')"

    def json_array_agg(self, expr: str) -> str:
        return f"json_group_array({expr})"
```

**No business logic in dialects - only syntax differences.**

---

## CTE-First Design Pattern

### Philosophy: Every FHIRPath Function = CTE Template

Instead of complex operation chains, each FHIRPath function maps directly to a CTE template:

```python
class FHIRPathFunctions:
    """CTE templates for FHIRPath functions."""

    def first(self, input_cte: str, array_column: str) -> str:
        """first() function as CTE template."""
        return f"""
        SELECT *,
               json_extract({array_column}, '$[0]') as result
        FROM {input_cte}
        """

    def where(self, input_cte: str, condition: str) -> str:
        """where() function as CTE template."""
        return f"""
        SELECT *
        FROM {input_cte}
        WHERE {condition}
        """

    def combine(self, input_cte: str, array_column: str) -> str:
        """combine() function as CTE template."""
        return f"""
        SELECT id,
               json_group_array({array_column}) as result
        FROM {input_cte}
        GROUP BY id
        """
```

### CTE Chain Example

**FHIRPath Expression**: `Patient.name.given.where(startsWith('J')).first()`

**Generated CTE Chain**:
```sql
WITH
  -- Step 1: Extract names array
  patient_names AS (
    SELECT id, json_extract(resource, '$.name') as names
    FROM fhir_resources
    WHERE resourceType = 'Patient'
  ),

  -- Step 2: Extract given names (flattened)
  given_names AS (
    SELECT id,
           json_extract(name_item.value, '$.given') as given_array
    FROM patient_names
    CROSS JOIN json_each(names) AS name_item
  ),

  -- Step 3: Apply where() filter
  filtered_given AS (
    SELECT id, given_array
    FROM given_names
    WHERE json_extract(given_array, '$[0]') LIKE 'J%'
  ),

  -- Step 4: Apply first()
  first_given AS (
    SELECT id,
           json_extract(given_array, '$[0]') as result
    FROM filtered_given
  )

SELECT id, result FROM first_given
```

**Benefits**:
- **Readable**: Each step is clear and inspectable
- **Debuggable**: Can test each CTE individually
- **Optimizable**: Database engine optimizes the entire chain
- **Population-scale**: Operates on full dataset efficiently

---

## Population-Scale Analytics Design

### Core Principle: Population-First, Not Row-by-Row

**Traditional Approach (Row-by-Row)**:
```python
# Anti-pattern: Process one patient at a time
for patient in patients:
    result = evaluate_fhirpath(patient, expression)
    results.append(result)
```

**Population-First Approach**:
```sql
-- Process all patients in single query
WITH population_results AS (
  SELECT id,
         json_extract(resource, '$.name[0].family') as family_name
  FROM fhir_resources
  WHERE resourceType = 'Patient'
)
SELECT * FROM population_results
```

### ❌ PROHIBITED: fhirpathpy for Evaluation

**NEVER use fhirpathpy (or any Python-based FHIRPath evaluator) for runtime expression evaluation in FHIR4DS.**

This prohibition is **absolute and non-negotiable** for the following architectural reasons:

1. **Population-First Design**: fhirpathpy operates on single resources in Python memory, which:
   - Cannot scale to population-level analytics
   - Processes one patient at a time (row-by-row anti-pattern)
   - Defeats the entire purpose of SQL translation
   - Creates 100x+ performance degradation vs. SQL

2. **SQL Translation Architecture**: FHIR4DS translates ALL expressions to SQL:
   - FHIRPath → SQL (via CTE generator)
   - CQL → FHIRPath → SQL
   - SQL-on-FHIR → FHIRPath → SQL
   - Using fhirpathpy bypasses this architecture entirely

3. **False Compliance Metrics**: Using fhirpathpy as fallback:
   - Masks translator limitations
   - Inflates compliance percentages
   - Provides false confidence in system maturity
   - Prevents identification of gaps that need fixing

4. **Dual Execution Path Problems**: Having both SQL and Python paths:
   - Creates semantic divergence (SQL ≠ Python edge case behavior)
   - Makes debugging harder (which path produced this result?)
   - Complicates maintenance (two implementations to keep in sync)
   - Violates architectural simplicity

**Permitted Uses of fhirpathpy**:
- ✅ **Parser Development**: Studying ANTLR grammar and parser structure
- ✅ **Test Case Reference**: Comparing expected behavior during development
- ✅ **Compliance Research**: Understanding FHIRPath specification edge cases
- ✅ **Code Generation**: Using fhirpathpy as reference for SQL generation templates

**Prohibited Uses of fhirpathpy**:
- ❌ **Runtime Evaluation**: Never evaluate expressions via fhirpathpy in production code
- ❌ **Fallback Mechanism**: Never use fhirpathpy when translator cannot handle expression
- ❌ **Test Runner Execution**: Never import fhirpathpy in test execution path
- ❌ **Hybrid Execution**: Never mix SQL and Python evaluation in same workflow

**What This Means in Practice**:

```python
# ❌ WRONG - Using fhirpathpy fallback
def evaluate_expression(expr: str, resource: dict):
    try:
        return translator.translate_and_execute(expr, resource)
    except TranslatorUnsupported:
        # NEVER DO THIS - defeats entire architecture
        return fhirpathpy.evaluate(resource, expr)

# ✅ CORRECT - Fail explicitly when translator cannot handle expression
def evaluate_expression(expr: str, resource: dict):
    try:
        return translator.translate_and_execute(expr, resource)
    except TranslatorUnsupported as e:
        # Translator limitation = test failure = gap identified = good!
        raise FHIRPathTranslatorUnsupported(
            f"Translator does not yet support: {expr}. "
            f"This identifies a gap that needs implementation."
        ) from e
```

**Why Failing Tests Are Good**:
- Failing tests identify translator gaps that need fixing
- Compliance metrics must reflect genuine translator capability
- Cannot hide limitations from production deployments
- Clear visibility into what functionality remains to be implemented

**From Architecture Goals**:
> "Achieve 100% compliance with FHIRPath, SQL on FHIR, and CQL specifications **through SQL translation**"

The key phrase is "through SQL translation" - not through Python evaluation, not through hybrid approaches, but exclusively through SQL translation.

### Monolithic CQL Execution

**CQL with Multiple Defines**:
```cql
define "HasDiabetes":
  exists([Condition: "Diabetes"])

define "RecentA1c":
  [Observation: "HbA1c"] O
  where O.effective during "Measurement Period"

define "InInitialPopulation":
  "HasDiabetes" and exists("RecentA1c")
```

**Generated Monolithic SQL**:
```sql
WITH
  -- CTE for HasDiabetes define
  has_diabetes AS (
    SELECT patient_id,
           COUNT(*) > 0 as result
    FROM conditions
    WHERE code = 'diabetes_code'
    GROUP BY patient_id
  ),

  -- CTE for RecentA1c define
  recent_a1c AS (
    SELECT patient_id,
           json_group_array(resource) as observations
    FROM observations
    WHERE code = 'a1c_code'
      AND effective_date >= '2024-01-01'
    GROUP BY patient_id
  ),

  -- CTE for InInitialPopulation define
  initial_population AS (
    SELECT h.patient_id,
           h.result AND (r.observations IS NOT NULL) as result
    FROM has_diabetes h
    LEFT JOIN recent_a1c r ON h.patient_id = r.patient_id
  )

-- Final results for all defines
SELECT
  patient_id,
  has_diabetes.result as "HasDiabetes",
  recent_a1c.observations as "RecentA1c",
  initial_population.result as "InInitialPopulation"
FROM initial_population
LEFT JOIN has_diabetes USING (patient_id)
LEFT JOIN recent_a1c USING (patient_id)
```

**Benefits**:
- **Single query execution** instead of N separate queries
- **Database optimization** across entire measure
- **Massive performance gains** (10x+ improvement demonstrated)
- **Simplified debugging** - one query to inspect

---
