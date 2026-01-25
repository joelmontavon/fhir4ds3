# Task: SP-100-001 - Implement Aggregation Functions

**Created**: 2026-01-24
**Status**: Pending
**Priority**: P0 (Critical)
**Estimated Effort**: 12-15 hours

---

## Task Description

Implement the four missing FHIRPath aggregation functions: `sum()`, `avg()`, `min()`, and `max()`. These functions currently raise `NotImplementedError` in the translator.

## Current State

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:1835-1838`

```python
elif function_name in ["sum", "avg", "min", "max"]:
    raise NotImplementedError(
        f"Function '{node.function_name}' implementation pending in future tasks"
    )
```

**Note**: `count()` IS already implemented. Only these four aggregation functions are missing.

## Requirements

### Functional Requirements

1. **sum(collection)** - Returns sum of all numeric values in collection
2. **avg(collection)** - Returns average of all numeric values in collection
3. **min(collection)** - Returns minimum value in collection
4. **max(collection)** - Returns maximum value in collection

### Edge Cases to Handle

1. **Empty collections**: `{}.sum()`, `{}.avg()`, `{}.min()`, `{}.max()`
2. **Null values**: Collections containing null/empty values
3. **Mixed types**: Collections with mixed numeric types
4. **Single element**: Collections with one element
5. **Large collections**: Performance testing

### SQL Generation Requirements

- Use SQL aggregate functions: SUM(), AVG(), MIN(), MAX()
- For array collections: Combine with UNNEST for population-scale analytics
- Set `is_aggregate=True` flag on SQLFragment
- Handle CTE generation for complex expressions
- Support both DuckDB and PostgreSQL dialects

### Examples

| FHIRPath Expression | Expected SQL (DuckDB) |
|---------------------|---------------------|
| `Patient.name.count()` | `COUNT(json_array_length(json_extract(resource, '$.name')))`
| `Observation.value.ofType(Quantity).value.sum()` | `SUM(json_extract(UNNEST(json_extract(resource, '$.value[ofType(@1, 'Quantity')].value')))`

## Implementation Plan

### Step 1: Add Translation Methods

Create new methods in `ASTToSQLTranslator` class:

```python
def _translate_sum(self, node: FunctionCallNode) -> SQLFragment:
    """Translate sum() function to SQL."""

def _translate_avg(self, node: FunctionCallNode) -> SQLFragment:
    """Translate avg() function to SQL."""

def _translate_min(self, node: FunctionCallNode) -> SQLFragment:
    """Translate min() function to SQL."""

def _translate_max(self, node: FunctionCallNode) -> SQLFragment:
    """Translate max() function to SQL."""
```

### Step 2: Update Function Router

Remove NotImplementedError from translator.py:1835-1838:

```python
elif function_name == "sum":
    return self._translate_sum(node)
elif function_name == "avg":
    return self._translate_avg(node)
elif function_name == "min":
    return self._translate_min(node)
elif function_name == "max":
    return self._translate_max(node)
```

### Step 3: Implementation Pattern

Follow existing pattern from `_translate_count_function_call()`:

```python
def _translate_sum(self, node: FunctionCallNode) -> SQLFragment:
    target_expr, dependencies, literal_value, snapshot, target_ast, target_path = self._resolve_function_target(node)

    # Build SQL fragment
    sql = f"SUM({target_expr})"

    return SQLFragment(
        expression=sql,
        source_table=self.context.current_table,
        is_aggregate=True,
        dependencies=dependencies
    )
```

### Step 4: Handle Edge Cases

**Empty collections**: Return NULL or 0 based on function semantics
**Array unnesting**: Use UNNEST for JSON arrays
**Type coercion**: Ensure numeric type compatibility

## Acceptance Criteria

1. ✅ All aggregation function tests pass (~15-20 tests)
2. ✅ Empty collection handling works correctly
3. ✅ Both DuckDB and PostgreSQL dialects supported
4. ✅ CTE integration works correctly
5. ✅ No regression on existing passing tests (469 tests)
6. ✅ Performance: Aggregation queries complete in <100ms

## Testing Strategy

### Unit Tests

Create unit tests in `tests/unit/fhirpath/sql/test_translator_aggregation.py`:

- Test sum() with integer collections
- Test avg() with decimal collections
- Test min() and max() with mixed types
- Test empty collection edge cases
- Test null value handling

### Integration Tests

Run official test suite with aggregation filter:

```bash
python -m tests.integration.fhirpath.official_test_runner --test_filter sum
python -m tests.integration.fhirpath.official_test_runner --test_filter avg
python -m tests.integration.fhirpath.official_test_runner --test_filter min
python -m tests.integration.fhirpath.official_test_runner --test_filter max
```

### Multi-Database Testing

Validate both dialects:

```bash
# DuckDB
python -m tests.integration.fhirpath.official_test_runner --database_type duckdb

# PostgreSQL
python -m tests.integration.fhirpath.official_test_runner --database_type postgresql
```

## Dependencies

- None - can be implemented independently
- Does not block or depend on other Phase 1 tasks

## References

- FHIRPath Specification: https://build.fhir.org/ig/HL7/FHIRPath/
- Translator location: `fhir4ds/main/fhirpath/sql/translator.py:1835-1838`
- Existing count() implementation: `translator.py` (search for `_translate_count_function_call`)

---

**Task Owner**: TBD
**Reviewers**: Architect, Code Reviewer
**Blocked By**: None
**Blocking**: None
