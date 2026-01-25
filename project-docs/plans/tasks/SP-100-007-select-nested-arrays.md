# Task: SP-100-007 - Select() Nested Array Flattening

**Created**: 2026-01-24
**Status**: Pending
**Priority**: P1 (High)
**Estimated Effort**: 15-20 hours

---

## Task Description

Implement nested array flattening in select() function. Currently, union in select projection is not handled correctly.

## Current State

**Location**: `/mnt/d/fhir4ds3/fhirpath/main/fhirpath/sql/translator.py`

**Issues**:
- Nested array flattening not implemented
- Union in select projection not handled
- SQL syntax issues partially resolved in SP-022-019

**Impact**: ~11 tests failing

## Requirements

### Functional Requirements

1. **Nested array flattening**: Flatten multi-dimensional arrays
2. **Union handling**: Support union operator in select projections
3. **Projection logic**: Generate correct SQL for array projections
4. **Filtering**: Combine select() with where() correctly

### Use Cases

```fhirpath
# Nested arrays
Patient.name.select(given & family)  # Flatten nested arrays

# Union projection
Patient.name.select(use | system)  # Union of fields

# With filtering
Patient.name.where(use='official').select(family, given)  # Combine
```

## Implementation Plan

### Step 1: Analyze Current select() Implementation

Review `_translate_select()` method to understand current behavior:

```python
# Find _translate_select or select() handler
# Understand current projection logic
# Identify where nested arrays break
```

### Step 2: Implement Nested Array Detection

Add logic to detect nested array structures:

```python
def _has_nested_arrays(self, target_path: List[str]) -> bool:
    """Check if target path contains nested arrays."""
    # Detect patterns like: given.family, name.given
    pass
```

### Step 3: Implement Array Flattening

Generate SQL for flattening nested arrays:

```python
# DuckDB: Use UNNEST with multiple levels
# PostgreSQL: Use jsonb_array_elements() recursively
```

### Step 4: Implement Union Projection

Handle union operator in select() projections:

```python
# Generate JSON arrays that combine multiple fields
# Handle different array lengths
# Ensure proper null handling
```

### Step 5: Combine with Filtering

Ensure select() + where() combinations work correctly:

```python
# WHERE clause filters before SELECT projection
# CTE dependencies properly tracked
# Both filters and projections work together
```

## Acceptance Criteria

1. ✅ Nested arrays flatten correctly
2. ✅ Union in select projections works
3. ✅ All select() tests pass (~11 tests)
4. ✅ select() + where() combinations work
5. ✅ No regression on existing functionality
6. ✅ Both dialects supported
7. ✅ Performance: Nested array operations complete in <500ms

## Testing Strategy

### Unit Tests

Create unit tests in `tests/unit/fhirpath/sql/test_select_nested_arrays.py`:

- Nested array flattening
- Union projections
- select() + where() combinations
- Edge cases: empty arrays, null values

### Integration Tests

Run official test suite with select filter:

```bash
python -m tests.integration.fhirpath.official_test_runner --test_filter "select"
```

### Multi-Database Testing

```bash
# DuckDB
python -m tests.integration.fhirpath.official_test_runner --database_type duckdb

# PostgreSQL
python -m tests.integration.fhirpath.official_test_runner --database_type postgresql
```

## Dependencies

- May overlap with SP-100-004 (CTE column propagation)
- May help resolve SP-100-005 (collection functions)

## References

- Translator location: `fhir4ds/main/fhirpath/sql/translator.py`
- Compliance report: SP-022-019 partially resolved issues
- Test suite: `tests/compliance/fhirpath/official_tests.xml`

---

**Task Owner**: TBD
**Reviewers**: Architect, Code Reviewer
**Blocked By**: None
**Blocking**: May help resolve collection function issues
