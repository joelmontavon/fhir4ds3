# FHIRPath Translator Integration Guide for PEP-004 (CTE Builder)

**Version**: 0.1.0
**Module**: `fhir4ds.fhirpath.sql`
**Task**: SP-005-023 - API Documentation and Examples
**Target Audience**: Developers implementing PEP-004 CTE Builder

---

## Overview

This guide explains how to integrate the FHIRPath AST-to-SQL Translator (PEP-003) with the future CTE Builder (PEP-004). The translator generates SQL fragments designed specifically for CTE-based query construction, and this document details the integration contract, patterns, and best practices.

### Integration Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  FHIRPath       │         │  AST-to-SQL      │         │  CTE Builder    │
│  Parser         │────────▶│  Translator      │────────▶│  (PEP-004)      │
│  (PEP-002)      │         │  (PEP-003)       │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                     │                             │
                                     │ SQLFragments                │
                                     └─────────────────────────────┘
                                            Monolithic SQL
```

### Key Concepts

1. **SQL Fragments**: Self-contained SQL operations with metadata
2. **CTE Generation**: Wrapping fragments in Common Table Expressions
3. **Dependency Resolution**: Ordering CTEs based on dependencies
4. **Monolithic Query Assembly**: Combining CTEs into single executable query

---

## SQLFragment Integration Contract

### Fragment Structure

Each `SQLFragment` provides the following information for CTE Builder:

```python
@dataclass
class SQLFragment:
    expression: str              # SQL expression (ready to wrap in CTE)
    source_table: str            # Source table/CTE this queries from
    requires_unnest: bool        # Whether fragment uses LATERAL UNNEST
    is_aggregate: bool           # Whether fragment contains aggregations
    dependencies: List[str]      # List of tables/CTEs this depends on
    metadata: Dict[str, Any]     # Extensible metadata for future needs
```

### Integration Points

#### 1. Fragment Collection

The translator returns a list of fragments representing an expression chain:

```python
from fhir4ds.fhirpath.sql import ASTToSQLTranslator
from fhir4ds.dialects import DuckDBDialect

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast_root)

# fragments is a List[SQLFragment]
# Each fragment represents one step in the expression chain
```

#### 2. Dependency Analysis

Each fragment declares its dependencies explicitly:

```python
for fragment in fragments:
    print(f"Fragment queries from: {fragment.source_table}")
    print(f"Fragment depends on: {fragment.dependencies}")

    # CTE Builder uses this information for topological sorting
```

#### 3. CTE Naming

Fragment `source_table` attribute provides CTE names:

```python
# Fragments use predictable CTE names
# cte_1, cte_2, cte_3, etc.

# Example fragment sequence for "Patient.name.where(use='official').first()":
# Fragment 1: source_table = "cte_1" (where operation)
# Fragment 2: source_table = "cte_2" (first operation)
```

#### 4. Special Handling Flags

Fragments provide flags for special SQL handling:

```python
if fragment.requires_unnest:
    # Fragment contains LATERAL UNNEST - already complete
    # Don't add additional unnesting logic
    pass

if fragment.is_aggregate:
    # Fragment contains COUNT/SUM/AVG/etc.
    # May need GROUP BY clause
    pass
```

---

## CTE Builder Implementation Guidance

### Step 1: Fragment Ordering (Dependency Resolution)

CTE Builder must order fragments based on dependencies:

```python
def order_fragments(fragments: List[SQLFragment]) -> List[SQLFragment]:
    """
    Order fragments for CTE generation using topological sort.

    Ensures dependencies appear before fragments that depend on them.
    """
    # Build dependency graph
    graph = {}
    for i, fragment in enumerate(fragments):
        graph[i] = {
            'fragment': fragment,
            'depends_on': []
        }

        # Find which fragments this depends on
        for j, other_fragment in enumerate(fragments):
            if other_fragment.source_table in fragment.dependencies:
                graph[i]['depends_on'].append(j)

    # Topological sort
    ordered_indices = topological_sort(graph)

    # Return ordered fragments
    return [fragments[i] for i in ordered_indices]
```

### Step 2: CTE Generation

Wrap each fragment in a CTE:

```python
def generate_cte(fragment: SQLFragment, cte_name: str) -> str:
    """
    Generate CTE SQL for a fragment.

    Args:
        fragment: SQLFragment to wrap
        cte_name: Name for this CTE (e.g., "cte_1")

    Returns:
        CTE SQL string
    """
    # Basic CTE wrapper
    cte_sql = f"{cte_name} AS (\n"
    cte_sql += f"  {fragment.expression}\n"
    cte_sql += ")"

    return cte_sql
```

### Step 3: Monolithic Query Assembly

Combine ordered CTEs into final query:

```python
def assemble_monolithic_query(fragments: List[SQLFragment]) -> str:
    """
    Assemble fragments into monolithic CTE-based query.

    Args:
        fragments: Ordered list of SQLFragments

    Returns:
        Complete SQL query with CTEs
    """
    # Order fragments by dependencies
    ordered_fragments = order_fragments(fragments)

    # Generate CTEs
    ctes = []
    for i, fragment in enumerate(ordered_fragments):
        cte_name = f"cte_{i+1}"
        cte_sql = generate_cte(fragment, cte_name)
        ctes.append(cte_sql)

    # Assemble final query
    if not ctes:
        return ""

    query = "WITH " + ",\n".join(ctes) + "\n"

    # Final SELECT from last CTE
    last_cte = f"cte_{len(ctes)}"
    query += f"SELECT * FROM {last_cte};"

    return query
```

---

## Complete Integration Example

### End-to-End: FHIRPath to Monolithic SQL

```python
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql import (
    ASTToSQLTranslator,
    # (Removed - SP-023-006)
)
from fhir4ds.dialects import DuckDBDialect

# Step 1: Parse FHIRPath expression
parser = FHIRPathParser()
expression = parser.parse("Patient.name.where(use='official').first().family")

# Step 2: Convert AST
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

# Step 3: Translate to SQL fragments
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

# Step 4: CTE Builder processes fragments
ordered_fragments = order_fragments(fragments)
monolithic_sql = assemble_monolithic_query(ordered_fragments)

print("Generated SQL:")
print(monolithic_sql)
```

### Expected Output

```sql
WITH cte_1 AS (
  SELECT resource.id, cte_1_item
  FROM resource,
  LATERAL UNNEST(json_extract(resource, '$.name')) AS cte_1_item
  WHERE json_extract(cte_1_item, '$.use') = 'official'
),
cte_2 AS (
  SELECT json_extract(cte_1_item, '$[0]') as first_item
  FROM cte_1
),
cte_3 AS (
  SELECT json_extract(first_item, '$.family') as family
  FROM cte_2
)
SELECT * FROM cte_3;
```

---

## Advanced Integration Patterns

### Pattern 1: Handling UNNEST Fragments

Fragments with `requires_unnest=True` already contain complete UNNEST SQL:

```python
def process_unnest_fragment(fragment: SQLFragment) -> str:
    """Handle fragment that requires unnesting"""
    if not fragment.requires_unnest:
        return fragment.expression

    # Fragment already has LATERAL UNNEST SQL
    # Don't add additional unnesting logic
    # Just wrap in CTE as-is
    return fragment.expression
```

### Pattern 2: Handling Aggregate Fragments

Fragments with `is_aggregate=True` may need GROUP BY:

```python
def process_aggregate_fragment(fragment: SQLFragment) -> str:
    """Handle fragment with aggregation"""
    if not fragment.is_aggregate:
        return fragment.expression

    # Determine if GROUP BY needed
    # Based on context from previous CTEs
    if needs_group_by(fragment):
        # Add GROUP BY clause
        return fragment.expression + "\nGROUP BY resource.id"
    else:
        return fragment.expression
```

### Pattern 3: Optimizing CTE Chains

Collapse simple CTEs for performance:

```python
def optimize_cte_chain(fragments: List[SQLFragment]) -> List[SQLFragment]:
    """
    Optimize CTE chain by collapsing simple operations.

    Example: Multiple path extractions can be collapsed into single CTE
    """
    optimized = []
    current_batch = []

    for fragment in fragments:
        # If fragment is simple path extraction, batch it
        if is_simple_path_extraction(fragment):
            current_batch.append(fragment)
        else:
            # Flush batched fragments as single CTE
            if current_batch:
                optimized.append(collapse_fragments(current_batch))
                current_batch = []

            # Add complex fragment as-is
            optimized.append(fragment)

    # Flush remaining
    if current_batch:
        optimized.append(collapse_fragments(current_batch))

    return optimized
```

---

## Metadata Usage

### Standard Metadata Keys

CTE Builder can use fragment metadata for optimization:

```python
# Metadata keys provided by translator
fragment.metadata = {
    'source_expression': 'Patient.name.where(use="official")',  # Original FHIRPath
    'estimated_cardinality': 'one-to-many',                     # Cardinality hint
    'requires_patient_id': True,                                 # Needs patient ID join
}

# CTE Builder can add its own metadata
fragment.set_metadata('cte_name', 'cte_1')
fragment.set_metadata('optimization_applied', 'index_scan')
```

### Custom Metadata for Optimization

```python
def apply_optimization_hints(fragment: SQLFragment) -> SQLFragment:
    """Apply optimization hints based on metadata"""

    # Check cardinality
    cardinality = fragment.get_metadata('estimated_cardinality')
    if cardinality == 'one-to-many':
        fragment.set_metadata('join_strategy', 'hash_join')

    # Check if patient ID needed
    if fragment.get_metadata('requires_patient_id', False):
        fragment.set_metadata('must_preserve_patient_id', True)

    return fragment
```

---

## Error Handling

### Handling Translation Errors

```python
from fhir4ds.fhirpath.sql import ASTToSQLTranslator

try:
    fragments = translator.translate(ast_root)
except NotImplementedError as e:
    # Node type not yet supported
    print(f"Unsupported FHIRPath operation: {e}")
    # Fallback to in-memory evaluation or return error

except ValueError as e:
    # Invalid AST or translation issue
    print(f"Translation error: {e}")
    # Log and handle gracefully
```

### Validating Fragment Integrity

```python
def validate_fragments(fragments: List[SQLFragment]) -> bool:
    """
    Validate fragments before CTE generation.

    Returns:
        True if fragments are valid, False otherwise
    """
    if not fragments:
        return False

    for fragment in fragments:
        # Check required fields
        if not fragment.expression:
            return False
        if not fragment.source_table:
            return False

        # Validate dependencies exist
        available_tables = {'resource'} | {f.source_table for f in fragments}
        for dep in fragment.dependencies:
            if dep not in available_tables:
                print(f"Missing dependency: {dep}")
                return False

    return True
```

---

## Performance Considerations

### Fragment Caching

Cache translated fragments for reuse:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def translate_expression_cached(expression_text: str, dialect_name: str) -> tuple:
    """Cache translated fragments by expression and dialect"""
    parser = FHIRPathParser()
    expression = parser.parse(expression_text)
    enhanced_ast = expression.get_ast()
    ast = enhanced_ast  # SP-023-006: Direct translation

    dialect = get_dialect(dialect_name)
    translator = ASTToSQLTranslator(dialect, "Patient")
    fragments = translator.translate(ast)

    # Convert to tuple for caching
    return tuple(fragments)
```

### Lazy CTE Evaluation

Generate CTEs lazily for better performance:

```python
class LazyC TEGenerator:
    """Generate CTEs on-demand"""

    def __init__(self, fragments: List[SQLFragment]):
        self.fragments = fragments
        self._cte_cache = {}

    def get_cte(self, index: int) -> str:
        """Get CTE for fragment at index (lazy generation)"""
        if index in self._cte_cache:
            return self._cte_cache[index]

        fragment = self.fragments[index]
        cte_name = f"cte_{index+1}"
        cte_sql = generate_cte(fragment, cte_name)

        self._cte_cache[index] = cte_sql
        return cte_sql
```

---

## Testing Integration

### Unit Tests for CTE Builder

```python
import pytest
from fhir4ds.fhirpath.sql import SQLFragment

def test_cte_generation():
    """Test CTE generation from fragments"""
    fragment = SQLFragment(
        expression="SELECT * FROM resource WHERE active = TRUE",
        source_table="resource"
    )

    cte_sql = generate_cte(fragment, "cte_1")

    assert "cte_1 AS" in cte_sql
    assert "SELECT * FROM resource" in cte_sql

def test_dependency_ordering():
    """Test fragments are ordered by dependencies"""
    # Fragment 2 depends on Fragment 1
    fragment1 = SQLFragment(
        expression="SELECT * FROM resource",
        source_table="cte_1"
    )

    fragment2 = SQLFragment(
        expression="SELECT * FROM cte_1",
        source_table="cte_2",
        dependencies=["cte_1"]
    )

    ordered = order_fragments([fragment2, fragment1])

    # fragment1 should come first
    assert ordered[0] == fragment1
    assert ordered[1] == fragment2
```

### Integration Tests

```python
def test_end_to_end_translation_to_cte():
    """Test complete flow from FHIRPath to CTE SQL"""
    parser = FHIRPathParser()
    expression = parser.parse("Patient.name.where(use='official')")

    enhanced_ast = expression.get_ast()
    ast = enhanced_ast  # SP-023-006: Direct translation

    translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
    fragments = translator.translate(ast)

    # CTE Builder processes fragments
    monolithic_sql = assemble_monolithic_query(fragments)

    # Validate SQL
    assert "WITH cte_" in monolithic_sql
    assert "LATERAL UNNEST" in monolithic_sql
    assert "SELECT * FROM cte_" in monolithic_sql
```

---

## Migration Path from Individual Queries

### Before: Individual Query per Patient (Anti-Pattern)

```python
# ❌ Old approach - N queries for N patients
for patient in patients:
    query = f"SELECT * FROM resource WHERE id = '{patient.id}' AND active = TRUE"
    result = execute_query(query)
    # Process result...
```

### After: Population-Scale CTE Query

```python
# ✅ New approach - 1 query for all patients
fragments = translator.translate(ast_root)
monolithic_sql = assemble_monolithic_query(fragments)

# Single query processes entire population
results = execute_query(monolithic_sql)

# 10x+ performance improvement validated
```

---

## Future Enhancements

### Planned PEP-004 Features

1. **Automatic Index Hints**: Fragment metadata guides index selection
2. **Query Plan Caching**: Cache execution plans for repeated queries
3. **Parallel CTE Execution**: Execute independent CTEs in parallel
4. **Adaptive Query Optimization**: Adjust CTE structure based on runtime statistics

### Extension Points for CTE Builder

```python
# Fragment metadata supports future extensions
fragment.set_metadata('parallel_execution', True)
fragment.set_metadata('materialization_hint', 'materialize')
fragment.set_metadata('index_hint', 'use_index_on_patient_id')
```

---

## Best Practices

### 1. Always Validate Fragments

```python
# Before generating CTEs, validate fragments
if not validate_fragments(fragments):
    raise ValueError("Invalid fragments - cannot generate CTEs")
```

### 2. Preserve Fragment Order

```python
# Don't reorder fragments arbitrarily
# Use dependency-based topological sort
ordered_fragments = order_fragments(fragments)
```

### 3. Handle Empty Fragment Lists

```python
# Check for empty fragments
if not fragments:
    return "SELECT * FROM resource"  # Default fallback
```

### 4. Log CTE Generation

```python
import logging

logger = logging.getLogger(__name__)

def assemble_monolithic_query(fragments: List[SQLFragment]) -> str:
    logger.info(f"Assembling query from {len(fragments)} fragments")

    # Generate CTEs...

    logger.debug(f"Generated SQL:\n{query}")
    return query
```

### 5. Test Both Dialects

```python
# Always test CTE generation for both DuckDB and PostgreSQL
def test_cte_generation_both_dialects():
    for dialect in [DuckDBDialect(), PostgreSQLDialect("...")]:
        translator = ASTToSQLTranslator(dialect, "Patient")
        fragments = translator.translate(ast_root)
        sql = assemble_monolithic_query(fragments)
        # Validate SQL syntax for dialect
```

---

## Troubleshooting

### Issue: Circular Dependencies

**Problem**: Fragments have circular dependencies

**Solution**:
```python
def detect_circular_dependencies(fragments: List[SQLFragment]) -> bool:
    """Detect circular dependencies in fragments"""
    # Build dependency graph and check for cycles
    # If cycles found, raise error with diagnostic info
    pass
```

### Issue: Missing Dependencies

**Problem**: Fragment depends on CTE that doesn't exist

**Solution**:
```python
def validate_dependencies(fragments: List[SQLFragment]) -> List[str]:
    """Return list of missing dependencies"""
    available = {'resource'} | {f.source_table for f in fragments}
    missing = []

    for fragment in fragments:
        for dep in fragment.dependencies:
            if dep not in available:
                missing.append(dep)

    return missing
```

### Issue: Performance Degradation

**Problem**: CTE query slower than expected

**Solution**:
- Check for CTE materialization in database
- Verify indexes on join columns
- Review EXPLAIN ANALYZE output
- Consider collapsing simple CTEs

---

## Reference Implementation

See complete CTE Builder reference implementation in:
- `fhir4ds/sql/cte_builder.py` (planned PEP-004)
- `tests/integration/test_cte_builder_integration.py` (planned)

---

## Additional Resources

- [API Reference](translator-api-reference.md)
- [Usage Examples](translator-usage-examples.md)
- [Troubleshooting Guide](translator-troubleshooting.md)
- [PEP-003 Specification](../../project-docs/peps/accepted/pep-003-ast-to-sql-translator.md)
- [PEP-004 Specification](../../project-docs/peps/accepted/pep-004-cte-builder.md) (planned)

---

**Last Updated**: 2025-10-02
**Task**: SP-005-023 - API Documentation and Examples
**Target Audience**: PEP-004 CTE Builder Implementers
